import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { register } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Phase 8.8.49 — Non-Destructive AsyncStorage Recovery & Data-Loss Prevention Tests
 *
 * NOTE: These tests execute application logic against an in-memory mock store
 * to verify recovery patterns and call contracts. They DO NOT reproduce native
 * Android SQLite / CursorWindow behavior.
 */

// Global mock state accessible to tests
const mockStorageState = {
  store: new Map(),
  getItemError: null,
  removeItemCalls: [],
  setItemCalls: [],
  reset() {
    this.store.clear();
    this.getItemError = null;
    this.removeItemCalls = [];
    this.setItemCalls = [];
  },
};

// ESM Loader hook to mock @react-native-async-storage/async-storage and native dependencies
const loaderCode = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === '@react-native-async-storage/async-storage') {
    return {
      url: 'data:text/javascript,' + encodeURIComponent(\`
        import { getMockState } from './mockBridge.mjs';
        const state = getMockState();
        export default {
          getItem: async (k) => {
            if (state.getItemError) {
              throw state.getItemError;
            }
            return state.store.has(k) ? state.store.get(k) : null;
          },
          setItem: async (k, v) => {
            state.setItemCalls.push({ key: k, value: v });
            state.store.set(k, v);
          },
          removeItem: async (k) => {
            state.removeItemCalls.push(k);
            state.store.delete(k);
          },
          clear: async () => {
            state.store.clear();
          },
        };
      \`),
      shortCircuit: true,
    };
  }
  if (specifier === './mockBridge.mjs') {
    return {
      url: 'data:text/javascript,' + encodeURIComponent(\`
        export const getMockState = () => globalThis.__PHASE8849_MOCK_STORAGE__;
      \`),
      shortCircuit: true,
    };
  }
  if (specifier === 'expo-secure-store') {
    return {
      url: 'data:text/javascript,export const isAvailableAsync = async () => true; export const getItemAsync = async () => null; export const setItemAsync = async () => {}; export const deleteItemAsync = async () => {};',
      shortCircuit: true,
    };
  }
  if (specifier === 'react-native') {
    return {
      url: 'data:text/javascript,export const Platform = { OS: "android", select: (obj) => obj.android || obj.default }; export const StyleSheet = { create: (s) => s }; export const Linking = { openURL: async () => {} }; export const Keyboard = { addListener: () => ({ remove: () => {} }), dismiss: () => {} }; export default {};',
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}
`;

globalThis.__PHASE8849_MOCK_STORAGE__ = mockStorageState;
register(`data:text/javascript,${encodeURIComponent(loaderCode)}`);

const {
  getLocalChatMessages,
  saveLocalChatMessages,
  getLocalGuestConversations,
  saveLocalGuestConversation,
  sanitizeMessageForStorage,
} = await import('../utils/storage.js');

/* =========================================================================
 * TESTS
 * ========================================================================= */

test('1. A temporary getItem failure does not call removeItem', async () => {
  mockStorageState.reset();
  const validData = JSON.stringify([
    { id: 'msg-1', role: 'user', content: 'Jai Mata Di' },
    { id: 'msg-2', role: 'assistant', content: 'Welcome to Yatra AI' },
  ]);
  mockStorageState.store.set('yatra_local_chat_history', validData);
  mockStorageState.store.set('yatra_guest_conversations', validData);

  // Simulate temporary native SQLite lock exception
  mockStorageState.getItemError = new Error('android.database.sqlite.SQLiteDatabaseLockedException: database is locked');

  // Attempt reading local chat messages
  const chatMessages = await getLocalChatMessages();
  assert.deepStrictEqual(chatMessages, [], 'Should return safe fallback array');
  assert.strictEqual(
    mockStorageState.removeItemCalls.length,
    0,
    'MUST NOT call removeItem on getItem failure'
  );

  // Attempt reading guest conversations
  const guestConvs = await getLocalGuestConversations();
  assert.deepStrictEqual(guestConvs, [], 'Should return safe fallback array');
  assert.strictEqual(
    mockStorageState.removeItemCalls.length,
    0,
    'MUST NOT call removeItem on getItem failure for guest conversations'
  );
});

test('2. A temporary getItem failure does not overwrite existing storage', async () => {
  mockStorageState.reset();
  const preservedData = JSON.stringify([
    { id: 'msg-saved', role: 'user', content: 'Preserved pilgrimage message' },
  ]);
  mockStorageState.store.set('yatra_local_chat_history', preservedData);

  mockStorageState.getItemError = new Error('Disk IO busy');

  await getLocalChatMessages();

  // Verify the stored value is completely unmodified
  assert.strictEqual(
    mockStorageState.store.get('yatra_local_chat_history'),
    preservedData,
    'Original data in AsyncStorage must be preserved when getItem fails'
  );
  assert.strictEqual(mockStorageState.setItemCalls.length, 0, 'No write operations must occur during read failure');
});

test('3. Invalid JSON does not trigger destructive deletion', async () => {
  mockStorageState.reset();
  const corruptedPayload = '{"incomplete_json": [1, 2, 3'; // Truncated/corrupted JSON string
  mockStorageState.store.set('yatra_local_chat_history', corruptedPayload);
  mockStorageState.store.set('yatra_guest_conversations', corruptedPayload);

  const msgs = await getLocalChatMessages();
  assert.deepStrictEqual(msgs, [], 'Must return safe fallback array on JSON syntax error');
  assert.strictEqual(
    mockStorageState.store.get('yatra_local_chat_history'),
    corruptedPayload,
    'Corrupted string must NOT be removed from disk automatically'
  );
  assert.strictEqual(
    mockStorageState.removeItemCalls.length,
    0,
    'removeItem must NOT be called on JSON parse failure'
  );

  const convs = await getLocalGuestConversations();
  assert.deepStrictEqual(convs, [], 'Must return safe fallback array on JSON syntax error for guest conversations');
  assert.strictEqual(
    mockStorageState.store.get('yatra_guest_conversations'),
    corruptedPayload,
    'Corrupted string must NOT be removed from disk automatically'
  );
  assert.strictEqual(
    mockStorageState.removeItemCalls.length,
    0,
    'removeItem must NOT be called on JSON parse failure for guest conversations'
  );
});

test('4. Valid conversations remain readable', async () => {
  mockStorageState.reset();
  const validList = [
    { id: 'u-1', role: 'user', content: 'What are the darshan timings?' },
    { id: 'a-1', role: 'assistant', content: 'The sanctum sanctorum remains open throughout the day...' },
  ];
  mockStorageState.store.set('yatra_local_chat_history', JSON.stringify(validList));

  const msgs = await getLocalChatMessages();
  assert.strictEqual(msgs.length, 2);
  assert.strictEqual(msgs[0].content, 'What are the darshan timings?');
  assert.strictEqual(msgs[1].content, 'The sanctum sanctorum remains open throughout the day...');
});

test('5. One malformed record does not destroy unrelated valid records', async () => {
  mockStorageState.reset();

  // Guest conversations list with one valid session, one null/corrupted session, and one string entry
  const mixedConversations = [
    {
      conversation_id: 'session-good-1',
      title: 'Valid Katra Trip',
      messages: [
        { id: 'm-1', role: 'user', content: 'Book a room' },
        null, // Malformed individual message inside conversation
        { id: 'm-2', role: 'assistant', content: 'Confirmed room details' },
      ],
    },
    null, // Malformed record 1
    'not an object', // Malformed record 2
    {
      conversation_id: 'session-good-2',
      title: 'Valid Patnitop Excursion',
      messages: [{ id: 'm-3', role: 'user', content: 'Weather at Patnitop' }],
    },
  ];

  mockStorageState.store.set('yatra_guest_conversations', JSON.stringify(mixedConversations));

  const convs = await getLocalGuestConversations();

  // Valid conversations must be rescued, not discarded
  assert.strictEqual(convs.length, 2, 'Must recover the 2 valid conversations');
  assert.strictEqual(convs[0].conversation_id, 'session-good-1');
  assert.strictEqual(convs[1].conversation_id, 'session-good-2');

  // Malformed message inside session-good-1 must be filtered without discarding good messages
  assert.strictEqual(convs[0].messages.length, 2);
  assert.strictEqual(convs[0].messages[0].id, 'm-1');
  assert.strictEqual(convs[0].messages[1].id, 'm-2');
});

test('6. Large itinerary messages remain sanitized', () => {
  const samplePath = path.join(__dirname, 'sample_itinerary_response.json');
  assert.ok(fs.existsSync(samplePath), 'sample_itinerary_response.json must exist');
  const rawBackendResponse = JSON.parse(fs.readFileSync(samplePath, 'utf8'));

  const rawMessage = {
    id: 'ai-raw-test',
    role: 'assistant',
    content: rawBackendResponse.reply,
    recommendation: rawBackendResponse.recommendation,
    itinerary: rawBackendResponse.itinerary,
    plan: rawBackendResponse.plan, // 63 KB blob!
    request: rawBackendResponse.request,
    destination_images: rawBackendResponse.destination_images,
    matched_destination: rawBackendResponse.matched_destination,
    timestamp: '10:00 AM',
  };

  const rawSize = JSON.stringify(rawMessage).length;
  assert.ok(rawSize > 70000, `Raw message size was ${rawSize} bytes, expected >70KB`);

  const sanitized = sanitizeMessageForStorage(rawMessage);
  const sanitizedSize = JSON.stringify(sanitized).length;

  assert.ok(sanitizedSize < 20000, `Sanitized size must be compact (<20KB), got ${sanitizedSize} bytes`);
  assert.ok(sanitizedSize < rawSize * 0.3, 'Sanitized size must achieve >70% reduction in size');
  assert.strictEqual(sanitized.plan.options, undefined, 'Raw options catalog must be stripped');
  assert.strictEqual(sanitized.plan.hotels, undefined, 'Raw hotels must be stripped');
  assert.ok(sanitized.plan.budget_evaluation.grand_total, 'grand_total must be preserved');
  assert.strictEqual(sanitized.itinerary.length, 3, 'All 3 itinerary days must be preserved');
});

test('7. Destination photographs remain preserved after storage sanitization', () => {
  const messageWithPhotos = {
    id: 'ai-photos',
    role: 'assistant',
    content: 'Here are verified photographs of Patnitop.',
    destination_images: [
      {
        title: 'Patnitop Circular Road',
        thumbnail_url: 'https://thumb.wikimedia.org/patnitop1.jpg',
        image_url: 'https://upload.wikimedia.org/patnitop1.jpg',
        photographer: 'Vikram',
        license: 'CC BY-SA 4.0',
      },
      {
        title: 'Patnitop Meadow',
        thumbnail_url: 'https://thumb.wikimedia.org/patnitop2.jpg',
        image_url: 'https://upload.wikimedia.org/patnitop2.jpg',
        photographer: 'Priya',
        license: 'CC BY 3.0',
      },
    ],
    matched_destination: {
      name: 'Patnitop',
      district: 'Udhampur',
    },
  };

  const sanitized = sanitizeMessageForStorage(messageWithPhotos);

  assert.ok(Array.isArray(sanitized.destination_images), 'destination_images must remain an array');
  assert.strictEqual(sanitized.destination_images.length, 2, 'All photos must be preserved');
  assert.strictEqual(sanitized.destination_images[0].thumbnail_url, 'https://thumb.wikimedia.org/patnitop1.jpg');
  assert.strictEqual(sanitized.matched_destination.name, 'Patnitop');
});