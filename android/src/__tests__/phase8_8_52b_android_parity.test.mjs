import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.join(__dirname, '..');
const ROOT_DIR = path.join(SRC_DIR, '..', '..');

// Import utilities
import { resolveDestinationImages, VERIFIED_DESTINATION_GALLERIES } from '../utils/destinationImages.js';

/* =========================================================================
 * PHASE 8.8.52B — ANDROID PARITY REGRESSION SUITE
 * ========================================================================= */

test('Phase 8.8.52B — Date Picker: BookingDatePicker component exists and implements native-safe calendar modal', () => {
  const pickerPath = path.join(SRC_DIR, 'components', 'BookingDatePicker.jsx');
  assert.ok(fs.existsSync(pickerPath), 'BookingDatePicker.jsx must exist');

  const code = fs.readFileSync(pickerPath, 'utf8');

  // Verify pure React Native modal implementation
  assert.ok(code.includes('<Modal'), 'Must use React Native Modal');
  assert.ok(code.includes('onRequestClose'), 'Must handle hardware back button');
  assert.ok(code.includes('isPast') && code.includes('disabled: isPast'), 'Must reject/disable past dates');
  assert.ok(code.includes('formatDateToYMD'), 'Must format dates safely');
  assert.ok(code.includes('handleSelectDay'), 'Must implement date selection');
  assert.ok(code.includes('handlePrevMonth') && code.includes('handleNextMonth'), 'Must support month navigation');
  assert.ok(code.includes('colors.burgundy'), 'Must use theme burgundy styling');
  assert.ok(code.includes('Confirm') && code.includes('Cancel'), 'Must have Confirm and Cancel action buttons');
});

test('Phase 8.8.52B — Date Picker: BookingScreen integrates BookingDatePicker with state binding and draft persistence', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  assert.ok(code.includes("import BookingDatePicker from '../components/BookingDatePicker';"), 'BookingScreen must import BookingDatePicker');
  assert.ok(code.includes('<BookingDatePicker'), 'Must render BookingDatePicker component');
  assert.ok(code.includes('value={startDate}'), 'Must bind startDate to BookingDatePicker');
  assert.ok(code.includes('onChange={setStartDate}'), 'Must handle date changes in state');
  assert.ok(code.includes('startDate,'), 'Must persist startDate in draft and booking');
});

test('Phase 8.8.52B — Uncapped Inputs: BookingScreen removes arbitrary caps for pilgrims and duration', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Verify editable numeric text inputs
  assert.ok(code.includes('testID="pax-input"'), 'Must provide editable numeric pax input');
  assert.ok(code.includes('testID="duration-input"'), 'Must provide editable numeric duration input');

  // Verify removal of hardcoded arbitrary caps
  assert.ok(!code.includes('Math.min(6,'), 'Must not clamp pax to 6');
  assert.ok(!code.includes('Math.min(60,'), 'Must not clamp duration to 60');
  assert.ok(!code.includes('Math.min(100,'), 'Must not clamp pax to 100');

  // Verify positive whole number validation
  assert.ok(code.includes('parseInt(pax, 10) < 1'), 'Must validate positive whole number for pilgrims');
  assert.ok(code.includes('parseInt(duration, 10) < 1'), 'Must validate positive whole number for duration');

  // Verify dynamic schedule rendering handles all duration days
  assert.ok(code.includes('Array.from({ length: duration - 3 }'), 'Must dynamically generate days up to user duration');
});

test('Phase 8.8.52B — Uncapped Inputs: ItineraryPreviewCard renders highlights for all duration days', () => {
  const previewPath = path.join(SRC_DIR, 'components', 'ItineraryPreviewCard.jsx');
  const code = fs.readFileSync(previewPath, 'utf8');

  // Must not clamp day highlights to 4
  assert.ok(!code.includes('Math.min(duration, 4)'), 'Must not clamp day highlights to 4');
  assert.ok(code.includes('for (let i = 0; i < duration; i++)'), 'Must generate highlights for all duration days');
});

test('Phase 8.8.52B — All 43 Destinations: Catalogue contains exactly 43 verified destinations and 108 photos', () => {
  const destinationKeys = Object.keys(VERIFIED_DESTINATION_GALLERIES);
  assert.strictEqual(destinationKeys.length, 43, 'Must contain exactly 43 verified destinations');

  let totalPhotos = 0;
  for (const key of destinationKeys) {
    const dest = VERIFIED_DESTINATION_GALLERIES[key];
    assert.ok(dest.name, `Destination ${key} must have name`);
    assert.ok(dest.id, `Destination ${key} must have id`);
    assert.ok(Array.isArray(dest.images) && dest.images.length >= 1, `Destination ${key} must have at least 1 image`);
    totalPhotos += dest.images.length;
    for (const img of dest.images) {
      assert.ok(img.image_url.startsWith('https://') || img.image_url.startsWith('/'), `Photo ${img.title} must have HTTPS or local asset URL`);
      assert.ok(img.thumbnail_url.startsWith('https://') || img.thumbnail_url.startsWith('/'), `Photo ${img.title} must have HTTPS or local asset thumbnail`);
      assert.ok(img.photographer, `Photo ${img.title} must have photographer`);
      assert.ok(img.license, `Photo ${img.title} must have license`);
    }
  }
  assert.strictEqual(totalPhotos, 108, 'Must contain exactly 108 verified photos');
});

test('Phase 8.8.52B — TourismCard: Supports loading state, graceful fallback, safe URI encoding, and lightbox modal', () => {
  const cardPath = path.join(SRC_DIR, 'components', 'TourismCard.jsx');
  const code = fs.readFileSync(cardPath, 'utf8');

  assert.ok(code.includes('imageLoading') && code.includes('ActivityIndicator'), 'Must show loading indicator for images');
  assert.ok(code.includes('imageError') && code.includes('setImageError(true)'), 'Must handle image loading errors gracefully');
  assert.ok(code.includes('VERIFIED_DESTINATION_GALLERIES'), 'Must use local 43-destination catalogue fallback');
  assert.ok(code.includes('encodeURI'), 'Must use safe URI encoding for image URLs');
  assert.ok(code.includes('lightboxOpen') && code.includes('setLightboxOpen(true)'), 'Must support full-screen lightbox modal on press');
});

test('Phase 8.8.52B — TourismScreen: Initializes with all 43 destinations for offline/online parity', () => {
  const screenPath = path.join(SRC_DIR, 'screens', 'TourismScreen.jsx');
  const code = fs.readFileSync(screenPath, 'utf8');

  assert.ok(code.includes('ALL_43_DESTINATIONS'), 'Must define ALL_43_DESTINATIONS catalogue');
  assert.ok(code.includes('VERIFIED_DESTINATION_GALLERIES'), 'Must derive from verified destination galleries');
  assert.ok(code.includes('category:'), 'Must assign categories to destinations');
});

test('Phase 8.8.52B — Chat Photo Precision: Destination photo queries resolve genuine verified photographs', () => {
  // Patnitop
  const r1 = resolveDestinationImages('Show me pictures of Patnitop.');
  assert.ok(r1, 'Must resolve Patnitop');
  assert.strictEqual(r1.destination.name, 'Patnitop');
  assert.strictEqual(r1.images.length, 3);

  // Baisaran Valley (suppressed - no verified photo in catalog)
  const r2 = resolveDestinationImages('Tell me about Baisaran Valley and show photographs.');
  assert.strictEqual(r2, null, 'Must suppress photos for unverified Baisaran Valley');

  // Aru Valley (resolves to Aru Valley photos in Kashmir Valley)
  const rAru = resolveDestinationImages('Show me pictures of Aru Valley.');
  assert.ok(rAru, 'Must resolve Aru Valley');
  assert.strictEqual(rAru.destination.name, 'Kashmir Valley');
  assert.ok(rAru.images.every((img) => img.title.includes('Aru')), 'Must only return Aru Valley photos');

  // Pahalgam
  const r3 = resolveDestinationImages('What are attractions in Pahalgam?');
  assert.ok(r3, 'Must resolve Pahalgam');
  assert.strictEqual(r3.destination.name, 'Pahalgam (Valley of Shepherds)');
  assert.strictEqual(r3.images.length, 3);

  // Doodhpathri (suppressed - no verified photo in catalog)
  const r4 = resolveDestinationImages('Tell me about Doodhpathri and show photos');
  assert.strictEqual(r4, null, 'Must suppress photos for unverified Doodhpathri');

  // Vaishno Devi Bhawan: strictly returns only genuine Bhawan photograph
  const r5 = resolveDestinationImages('Show pictures of Vaishno Devi Bhawan.');
  assert.ok(r5, 'Must resolve Vaishno Devi Bhawan to Holy Cave Bhawan');
  assert.strictEqual(r5.destination.name, 'Holy Cave Bhawan (Mata Vaishno Devi)');
  assert.strictEqual(r5.images.length, 1, 'Must return exactly 1 photo');
  assert.strictEqual(r5.images[0].title, 'Holy Cave Bhawan, Shri Mata Vaishno Devi');
  assert.strictEqual(
    r5.images[0].image_url,
    'https://upload.wikimedia.org/wikipedia/commons/d/d4/Mata_Vaishno_Devi_Bhawan.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original'
  );
  assert.ok(!r5.images.some((img) => img.title.includes('Katra') || img.title.includes('KATRA TOWN')), 'Must never return Katra town photos for Bhawan queries');

  // Katra town query with photo intent: returns 2 Katra town photos, never Bhawan
  const rKatra = resolveDestinationImages('Show me pictures of Katra.');
  assert.ok(rKatra, 'Must resolve Katra town photos');
  assert.strictEqual(rKatra.destination.name, 'Katra');
  assert.strictEqual(rKatra.images.length, 2);
  assert.ok(rKatra.images.every((img) => !img.title.includes('Bhawan')), 'Must not contain Bhawan photo');

  // Generic Katra query without photo intent: suppressed
  const rKatraInfo = resolveDestinationImages('Tell me about Katra.');
  assert.strictEqual(rKatraInfo, null, 'Must suppress photos for generic Katra info query');
});

test('Phase 8.8.52B — Chat Photo Precision: Suppresses photographs for transport, booking, and procedural queries', () => {
  const proceduralQueries = [
    'Show me train timings',
    'Which train should I take from Delhi?',
    'Helicopter booking procedure',
    'Yatra Parchi registration',
    'Bus timetable from Jammu to Katra',
    'Locker charges at Katra',
    'Weather and budget questions for the trip',
    'Show me hotel prices in Katra',
    'How is the weather in Katra?',
    'What is the refund policy for battery cars?',
  ];

  for (const q of proceduralQueries) {
    const res = resolveDestinationImages(q);
    assert.strictEqual(res, null, `Query "${q}" must NOT attach destination photographs`);
  }
});

test('Phase 8.8.52B — Chat Photo Precision: Suppresses generic Katra photos for general inquiries', () => {
  const genericKatraQueries = [
    'Tell me about Katra',
    'Where to stay in Katra?',
    'What shops are near Katra bus stand?',
    'Show me Katra market timings',
  ];

  for (const q of genericKatraQueries) {
    const res = resolveDestinationImages(q);
    assert.strictEqual(res, null, `Generic query "${q}" must NOT attach generic Katra photographs`);
  }
});

test('Phase 8.8.52B — Cross-Turn Leakage: ChatManager and backend coordinator prevent photo leakage', () => {
  // Check chatManager.js
  const chatManagerPath = path.join(SRC_DIR, 'services', 'chatManager.js');
  const chatManagerCode = fs.readFileSync(chatManagerPath, 'utf8');

  // Verify chatManager honors empty array from backend
  assert.ok(
    chatManagerCode.includes('Array.isArray(response.destination_images)'),
    'chatManager must honor explicit empty destination_images array from backend'
  );

  // Check coordinator.py
  const coordinatorPath = path.join(ROOT_DIR, 'agents', 'coordinator.py');
  const coordinatorCode = fs.readFileSync(coordinatorPath, 'utf8');

  // Verify cross-turn leakage guard
  assert.ok(
    coordinatorCode.includes('cross-turn') && coordinatorCode.includes('last_tourism_place'),
    'coordinator.py must implement cross-turn leakage prevention'
  );
});

test('Phase 8.8.52B — Dashboard Spacing: SplashScreen eliminates awkward blank gap between branding and CTA', () => {
  const splashPath = path.join(SRC_DIR, 'screens', 'SplashScreen.jsx');
  const code = fs.readFileSync(splashPath, 'utf8');

  // Verify scrollContent centers content instead of awkward space-between void
  assert.ok(code.includes("justifyContent: 'center'"), 'scrollContent must use justifyContent: center');
  assert.ok(!code.includes("justifyContent: 'space-between'"), 'scrollContent must NOT use space-between');
  assert.ok(code.includes('ctaSection'), 'Must have ctaSection');
  assert.ok(code.includes('Begin Your Journey'), 'Must retain Begin Your Journey CTA');
});

test('Phase 8.8.52B — Preservation: Safety mechanisms from prior phases remain fully intact', () => {
  // 1. Storage data-loss prevention from Phase 8.8.49
  const storagePath = path.join(SRC_DIR, 'utils', 'storage.js');
  const storageCode = fs.readFileSync(storagePath, 'utf8');
  assert.ok(storageCode.includes('Temporary AsyncStorage read error'), 'Must preserve AsyncStorage error handling');
  assert.ok(storageCode.includes('JSON parse error in local chat messages'), 'Must preserve JSON parse safety');

  // 2. Keyboard visibility fix from Phase 8.8.44
  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const chatScreenCode = fs.readFileSync(chatScreenPath, 'utf8');
  assert.ok(chatScreenCode.includes('KeyboardAvoidingView'), 'Must preserve KeyboardAvoidingView');

  // 3. Sidebar drawer visibility from Phase 8.8.45
  const drawerPath = path.join(SRC_DIR, 'components', 'SidebarDrawer.jsx');
  const drawerCode = fs.readFileSync(drawerPath, 'utf8');
  assert.ok(drawerCode.includes('modalOverlay: {'), 'Must preserve sidebar drawer modal overlay');
  assert.ok(drawerCode.includes('drawerContainer: {'), 'Must preserve sidebar drawer container');
});
