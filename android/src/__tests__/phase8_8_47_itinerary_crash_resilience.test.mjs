import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { register } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// Register ESM loader to mock React Native / Expo dependencies
const loaderCode = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === 'expo-constants') {
    return {
      url: 'data:text/javascript,export default { expoConfig: { extra: { apiUrl: "https://yatra-ai-smap.onrender.com" } } };',
      shortCircuit: true,
    };
  }
  if (specifier === '@react-native-async-storage/async-storage') {
    return {
      url: 'data:text/javascript,const store = new Map(); export default { getItem: async (k) => store.get(k) || null, setItem: async (k, v) => { store.set(k, v); }, removeItem: async (k) => { store.delete(k); }, clear: async () => { store.clear(); } };',
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
  if (specifier.endsWith('/storage') || specifier === '../utils/storage') {
    return nextResolve(specifier + '.js', context);
  }
  return nextResolve(specifier, context);
}
`;

register(`data:text/javascript,${encodeURIComponent(loaderCode)}`);

const { sanitizeMessageForStorage, saveLocalGuestConversation, getLocalGuestConversations, saveLocalChatMessages, getLocalChatMessages } = await import('../utils/storage.js');
const { chatManager } = await import('../services/chatManager.js');
const { parseMarkdownStructure, completeIncompleteStreamingTokens } = await import('../utils/markdownParser.js');

/* =========================================================================
 * PHASE 8.8.47 — ITINERARY GENERATION AND CRASH RESILIENCE TESTS
 * ========================================================================= */

test('Phase 8.8.47 — Storage Compaction: Strips 60+ KB catalog dumps and preserves critical itinerary fields', () => {
  // Load the actual live response from production backend
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

  // Sanitize for storage
  const compactMessage = sanitizeMessageForStorage(rawMessage);
  const compactSize = JSON.stringify(compactMessage).length;

  // Verify dramatic reduction to prevent Android CursorWindow (2MB) SQLite crash
  assert.ok(compactSize < 20000, `Compact message size must be < 20KB, got ${compactSize} bytes`);
  assert.ok(compactSize < rawSize * 0.3, 'Compact message must achieve > 70% reduction in size');

  // Verify critical fields needed for UI and booking handoff are strictly preserved
  assert.strictEqual(compactMessage.content, rawBackendResponse.reply);
  assert.ok(Array.isArray(compactMessage.itinerary), 'Itinerary array must be preserved');
  assert.strictEqual(compactMessage.itinerary.length, 3, 'All 3 itinerary days must be preserved');
  assert.ok(compactMessage.plan.budget_evaluation.grand_total, 'grand_total must be preserved');
  assert.strictEqual(compactMessage.request.destination, 'Katra', 'destination must be preserved');
  assert.strictEqual(compactMessage.request.pax, 2, 'pax must be preserved');
  assert.strictEqual(compactMessage.request.duration_days, 3, 'duration_days must be preserved');

  // Verify bloat is stripped
  assert.strictEqual(compactMessage.plan.options, undefined, 'options array must be stripped');
  assert.strictEqual(compactMessage.plan.hotels, undefined, 'hotels array must be stripped');
  assert.strictEqual(compactMessage.plan.available_hotels, undefined, 'available_hotels must be stripped');
});

test('Phase 8.8.47 — CursorWindow Safety: 10 guest conversations with itineraries remain safely under 250KB', async () => {
  const samplePath = path.join(__dirname, 'sample_itinerary_response.json');
  const rawBackendResponse = JSON.parse(fs.readFileSync(samplePath, 'utf8'));

  const compactMessage = sanitizeMessageForStorage({
    id: 'ai-sample',
    role: 'assistant',
    content: rawBackendResponse.reply,
    recommendation: rawBackendResponse.recommendation,
    itinerary: rawBackendResponse.itinerary,
    plan: rawBackendResponse.plan,
    request: rawBackendResponse.request,
    destination_images: rawBackendResponse.destination_images,
    timestamp: '10:00 AM',
  });

  // Simulate 10 multi-turn conversations stored in guest history
  for (let i = 1; i <= 12; i++) {
    await saveLocalGuestConversation({
      conversation_id: `guest-session-${i}`,
      title: `3-Day Katra Pilgrimage #${i}`,
      messages: [
        { id: `u-${i}`, role: 'user', content: 'Plan a 3-day trip to Mata Vaishno Devi' },
        { ...compactMessage, id: `ai-${i}` },
      ],
      trip_request: { destination: 'Katra', pax: 2, duration_days: 3 },
      preview: 'Plan a 3-day trip to Mata Vaishno Devi',
    });
  }

  const stored = await getLocalGuestConversations();
  // Must be capped to 10 sessions max
  assert.ok(stored.length <= 10, `Stored sessions count must be <= 10, got ${stored.length}`);

  // Total serialized length must be safely under 250KB (well within Android's 2MB CursorWindow limit)
  const totalBytes = JSON.stringify(stored).length;
  assert.ok(totalBytes < 250000, `Total storage payload must be < 250KB, got ${totalBytes} bytes`);
});

test('Phase 8.8.47 — chatManager: formatIncomingMessages compacts bloated messages on load', () => {
  const samplePath = path.join(__dirname, 'sample_itinerary_response.json');
  const rawBackendResponse = JSON.parse(fs.readFileSync(samplePath, 'utf8'));

  const rawList = [
    { id: 'u-1', role: 'user', content: 'Plan a trip' },
    {
      id: 'ai-1',
      role: 'assistant',
      content: rawBackendResponse.reply,
      plan: rawBackendResponse.plan,
      recommendation: rawBackendResponse.recommendation,
      request: rawBackendResponse.request,
    },
  ];

  const formatted = chatManager.formatIncomingMessages(rawList);
  assert.strictEqual(formatted.length, 2);
  const aiFormatted = formatted[1];
  assert.ok(aiFormatted.plan.budget_evaluation, 'budget_evaluation preserved');
  assert.strictEqual(aiFormatted.plan.options, undefined, 'options stripped');
  assert.strictEqual(aiFormatted.plan.hotels, undefined, 'hotels stripped');
});

test('Phase 8.8.47 — Markdown Resilience: 5,000+ character assistant response parses into structured blocks safely', () => {
  const samplePath = path.join(__dirname, 'sample_itinerary_response.json');
  const rawBackendResponse = JSON.parse(fs.readFileSync(samplePath, 'utf8'));

  const reply = rawBackendResponse.reply;
  assert.ok(reply.length > 5000, 'Sample reply must be > 5,000 characters');

  const safe = completeIncompleteStreamingTokens(reply);
  const blocks = parseMarkdownStructure(safe);

  assert.ok(blocks.length >= 60, `Parsed blocks must be >= 60, got ${blocks.length}`);
  const headings = blocks.filter((b) => b.type === 'heading');
  const bullets = blocks.filter((b) => b.type === 'bullet');
  assert.ok(headings.length >= 5, 'Must contain multiple headings');
  assert.ok(bullets.length >= 30, 'Must contain bullet items for itinerary schedule');
});

test('Phase 8.8.47 — Component Defensiveness: ChatScreen, ChatBubble and MarkdownView have error boundaries', () => {
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const chatScreenCode = fs.readFileSync(chatScreenPath, 'utf8');

  // Verify safeScrollToEnd with try-catch exists
  assert.ok(chatScreenCode.includes('safeScrollToEnd'), 'ChatScreen must implement safeScrollToEnd');
  assert.ok(chatScreenCode.includes('safeScrollToEnd(true)'), 'ChatScreen must call safeScrollToEnd on content change');

  // Verify MarkdownView component has try-catch error boundary
  const mdViewPath = path.join(SRC_DIR, 'components', 'MarkdownView.jsx');
  const mdViewCode = fs.readFileSync(mdViewPath, 'utf8');
  assert.ok(mdViewCode.includes('try {'), 'MarkdownView must have try-catch error boundary');
  assert.ok(mdViewCode.includes('React.memo'), 'MarkdownView must be wrapped in React.memo');

  // Verify ChatBubble has React.memo and speech length protection
  const bubblePath = path.join(SRC_DIR, 'components', 'ChatBubble.jsx');
  const bubbleCode = fs.readFileSync(bubblePath, 'utf8');
  assert.ok(bubbleCode.includes('React.memo'), 'ChatBubble must be wrapped in React.memo');
  assert.ok(bubbleCode.includes('cleanText.length > 800'), 'ChatBubble must cap long text before speech synthesis');

  // Verify ItineraryPreviewCard has React.memo and defensive checks
  const cardPath = path.join(SRC_DIR, 'components', 'ItineraryPreviewCard.jsx');
  const cardCode = fs.readFileSync(cardPath, 'utf8');
  assert.ok(cardCode.includes('React.memo'), 'ItineraryPreviewCard must be wrapped in React.memo');
});
