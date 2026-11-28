import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { register } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// Register ESM loader to mock React Native / Expo native module bindings
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

// Import utilities
import { resolveDestinationImages, VERIFIED_DESTINATION_GALLERIES } from '../utils/destinationImages.js';
const { sanitizeMessageForStorage } = await import('../utils/storage.js');

/* =========================================================================
 * ANDROID DESTINATION PHOTOGRAPHS DISPLAY TESTS
 * ========================================================================= */

test('Destination Images: All 4 target user queries resolve genuine verified photographs', () => {
  // Query 1: Patnitop
  const r1 = resolveDestinationImages('Show me pictures of Patnitop.');
  assert.ok(r1, 'Must resolve Patnitop');
  assert.strictEqual(r1.destination.name, 'Patnitop');
  assert.ok(r1.images.length >= 3, 'Must have at least 3 photos');
  assert.ok(r1.images[0].thumbnail_url.startsWith('https://'), 'Must have HTTPS thumbnail');
  assert.ok(r1.images[0].photographer, 'Must include photographer attribution');
  assert.ok(r1.images[0].license, 'Must include license');

  // Query 2: Baisaran Valley (suppressed as no verified photo exists yet)
  const r2 = resolveDestinationImages('Tell me about Baisaran Valley and show photographs.');
  assert.strictEqual(r2, null, 'Must suppress photos for unverified Baisaran Valley');

  // Query 2b: Aru Valley resolves to genuine Aru Valley photographs in Kashmir Valley gallery
  const rAru = resolveDestinationImages('Show me pictures of Aru Valley.');
  assert.ok(rAru, 'Must resolve Aru Valley');
  assert.strictEqual(rAru.destination.name, 'Kashmir Valley');
  assert.ok(rAru.images.length >= 2, 'Must have at least 2 Aru Valley photos');
  assert.ok(rAru.images.every((img) => img.title.includes('Aru')), 'Must only return Aru Valley photos, not Golf Course');

  // Query 3: Vaishno Devi Bhawan
  const r3 = resolveDestinationImages('Show pictures of Vaishno Devi Bhawan.');
  assert.ok(r3, 'Must resolve Vaishno Devi Bhawan to Holy Cave Bhawan');
  assert.strictEqual(r3.destination.name, 'Holy Cave Bhawan (Mata Vaishno Devi)');
  assert.strictEqual(r3.images.length, 1, 'Must return ONLY the 1 authentic Bhawan photo');
  assert.strictEqual(r3.images[0].title, 'Holy Cave Bhawan, Shri Mata Vaishno Devi');
  assert.strictEqual(
    r3.images[0].image_url,
    'https://upload.wikimedia.org/wikipedia/commons/d/d4/Mata_Vaishno_Devi_Bhawan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original'
  );
  assert.ok(!r3.images.some((img) => img.title.includes('Katra') || img.title.includes('KATRA TOWN')), 'Must never return Katra town photos for Bhawan queries');

  // Query 3b: Katra town with photo intent resolves to Katra municipal overviews, NEVER Bhawan-only photo
  const rKatraPhotos = resolveDestinationImages('Show me pictures of Katra.');
  assert.ok(rKatraPhotos, 'Must resolve Katra photos');
  assert.strictEqual(rKatraPhotos.destination.name, 'Katra');
  assert.strictEqual(rKatraPhotos.images.length, 2, 'Must return the 2 Katra municipal overview photos');
  assert.ok(rKatraPhotos.images.every((img) => !img.title.includes('Bhawan')), 'Must not contain Bhawan photo');

  // Query 3c: Generic Katra query without photo intent returns null
  const rKatraInfo = resolveDestinationImages('Tell me about Katra.');
  assert.strictEqual(rKatraInfo, null, 'Must suppress photos for generic Katra info query');

  // Query 4: Best places in Pahalgam
  const r4 = resolveDestinationImages('What are the best places to visit in Pahalgam?');
  assert.ok(r4, 'Must resolve Pahalgam');
  assert.strictEqual(r4.destination.name, 'Pahalgam (Valley of Shepherds)');
  assert.ok(r4.images.length >= 3, 'Must have at least 3 photos');

  // Query 5: Standard general chat query should not attach spurious images
  const r5 = resolveDestinationImages('How to book Yatra Parchi online?');
  assert.strictEqual(r5, null, 'Must not attach images to unrelated booking questions');
});

test('API Client: sendChatMessage forwards destination_images and matched_destination', () => {
  const apiPath = path.join(SRC_DIR, 'services', 'api.js');
  const code = fs.readFileSync(apiPath, 'utf8');

  assert.ok(
    code.includes('destination_images: res.destination_images || null'),
    'sendChatMessage must pass destination_images from backend response'
  );
  assert.ok(
    code.includes('matched_destination: res.matched_destination || null'),
    'sendChatMessage must pass matched_destination from backend response'
  );
});

test('ChatManager: Preserves destination_images across formatIncomingMessages and history restoration', async () => {
  // Simulate backend history message structure (MongoDB Atlas stores in metadata)
  const historyMessage = {
    id: 'msg-hist-1',
    role: 'assistant',
    content: 'Here are details and photos of Patnitop.',
    metadata: {
      intent: 'TOURISM',
      destination_images: [
        {
          image_url: 'https://upload.wikimedia.org/wikipedia/commons/3/3b/Patni_top_%2838%29.JPG',
          thumbnail_url: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Patni_top_%2838%29.JPG/960px-Patni_top_%2838%29.JPG',
          title: 'Patni top',
          photographer: 'Guptaele',
          license: 'CC BY-SA 4.0',
        },
      ],
      matched_destination: { name: 'Patnitop', id: '6ac9e42cd1723aa73d3bad30' },
    },
  };

  const { chatManager } = await import('../services/chatManager.js');
  const formatted = chatManager.formatIncomingMessages([historyMessage]);

  assert.strictEqual(formatted.length, 1);
  const msg = formatted[0];
  assert.ok(Array.isArray(msg.destination_images), 'Must extract destination_images from history metadata');
  assert.strictEqual(msg.destination_images.length, 1);
  assert.strictEqual(msg.destination_images[0].title, 'Patni top');
  assert.strictEqual(msg.matched_destination?.name, 'Patnitop');
});

test('Storage: sanitizeMessageForStorage preserves destination_images and matched_destination', () => {
  const testMsg = {
    id: 'msg-1',
    role: 'assistant',
    content: 'Patnitop is a scenic hill station.',
    destination_images: [
      {
        image_url: 'https://upload.wikimedia.org/wikipedia/commons/3/3b/Patni_top_%2838%29.JPG',
        thumbnail_url: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Patni_top_%2838%29.JPG/960px-Patni_top_%2838%29.JPG',
        title: 'Patni top',
        photographer: 'Guptaele',
        license: 'CC BY-SA 4.0',
      },
    ],
    matched_destination: { name: 'Patnitop', id: '6ac9e42cd1723aa73d3bad30' },
  };

  const sanitized = sanitizeMessageForStorage(testMsg);
  assert.ok(Array.isArray(sanitized.destination_images), 'Sanitized message must keep destination_images');
  assert.strictEqual(sanitized.destination_images.length, 1);
  assert.strictEqual(sanitized.matched_destination?.name, 'Patnitop');
});

test('ChatBubble: Uses safe thumbnail URLs in gallery and lightbox to prevent HTTP 429 rate limit', () => {
  const bubblePath = path.join(SRC_DIR, 'components', 'ChatBubble.jsx');
  const code = fs.readFileSync(bubblePath, 'utf8');

  // Verify gallery uses thumbnail_url first
  assert.ok(
    code.includes('uri: item.thumbnail_url || item.image_url'),
    'ChatBubble gallery must prefer thumbnail_url'
  );

  // Verify lightbox uses thumbnail_url first to prevent 429 from Wikimedia
  assert.ok(
    code.includes('uri: activePhoto.thumbnail_url || activePhoto.image_url'),
    'Lightbox must prefer thumbnail_url'
  );

  // Verify strict error handling omits failed image containers cleanly
  assert.ok(code.includes('onError={() =>'), 'Must handle Image onError');
  assert.ok(code.includes('setFailedImages'), 'Must track failed images');
  assert.ok(!code.includes('imageFallbackBox'), 'Must cleanly remove failed image container instead of placeholder box');
  assert.ok(!code.includes('Photo unavailable'), 'Must never display Photo unavailable text');
});
