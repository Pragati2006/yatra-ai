import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../../');

test('Phase 8.8.52 - A1: Booking Date Picker Integration in TravelSearch', () => {
  const travelSearchPath = path.join(projectRoot, 'frontend/src/components/TravelSearch.jsx');
  const code = fs.readFileSync(travelSearchPath, 'utf-8');

  // Must import InteractiveDatePicker
  assert.ok(
    code.includes("import InteractiveDatePicker from './common/InteractiveDatePicker';"),
    'TravelSearch must import InteractiveDatePicker'
  );

  // Must have toggle button for InteractiveDatePicker
  assert.ok(
    code.includes('data-testid="toggle-date-picker-btn"'),
    'TravelSearch must have a visible toggle button for the date picker'
  );

  // Must enforce non-past date constraint with min attribute
  assert.ok(
    code.includes('min={todayISO}'),
    'Date input must enforce min={todayISO} to prevent past date selection'
  );

  // Must calculate todayISO safely
  assert.ok(
    code.includes('todayISO ='),
    'Must calculate todayISO for past date validation'
  );

  // Must render InteractiveDatePicker when opened
  assert.ok(
    code.includes('<InteractiveDatePicker'),
    'Must render InteractiveDatePicker component when toggle is active'
  );
});

test('Phase 8.8.52 - A1: InteractiveDatePicker Date Range & Preset Capabilities', () => {
  const pickerPath = path.join(projectRoot, 'frontend/src/components/common/InteractiveDatePicker.jsx');
  const code = fs.readFileSync(pickerPath, 'utf-8');

  // Disables past dates
  assert.ok(
    code.includes('if (clicked < today) return;'),
    'InteractiveDatePicker must reject clicks on past dates'
  );

  // Supports quick duration presets including 7 and 10 days
  assert.ok(code.includes("label: '7 Days', days: 7"), 'Must include 7 Days preset');
  assert.ok(code.includes("label: '10 Days', days: 10"), 'Must include 10 Days preset');

  // Calculates duration and nights dynamically
  assert.ok(code.includes('durationDays ='), 'Must calculate durationDays dynamically');
  assert.ok(code.includes('hotelNights ='), 'Must calculate hotelNights dynamically');
});

test('Phase 8.8.52 - A2: Uncapped Pilgrim and Duration Controls', () => {
  const travelSearchPath = path.join(projectRoot, 'frontend/src/components/TravelSearch.jsx');
  const code = fs.readFileSync(travelSearchPath, 'utf-8');

  // 1. Pilgrims select includes 10+ options (up to 50)
  assert.ok(code.includes('14, 15, 16, 20, 25, 30, 40, 50'), 'Pax select must support up to 50 pilgrims');
  assert.ok(!code.includes('[1, 2, 3, 4, 5, 6, 8, 10].map'), 'Must remove the hardcoded 10-person max array');

  // 2. Direct numeric input for pilgrims with NO arbitrary max cap
  assert.ok(
    code.includes('id="travel-pax-input"'),
    'Must provide numeric input (travel-pax-input) for direct pilgrim entry'
  );
  assert.ok(
    code.includes('min="1"'),
    'Pilgrim inputs must specify min="1"'
  );
  assert.ok(
    !code.includes('max="100"'),
    'Must not have arbitrary max="100" cap on pilgrim input'
  );

  // 3. Duration select includes 10+ days (up to 30)
  assert.ok(code.includes('9, 10, 11, 12, 14, 15, 20, 30'), 'Duration select must support up to 30 days');
  assert.ok(!code.includes('[2, 3, 4, 5, 6, 7].map'), 'Must remove the hardcoded 7-day max array');

  // 4. Direct numeric input for duration with NO arbitrary max cap
  assert.ok(
    code.includes('id="travel-duration-input"'),
    'Must provide numeric input (travel-duration-input) for direct duration entry'
  );
  assert.ok(
    !code.includes('max="60"'),
    'Must not have arbitrary max="60" cap on duration input'
  );
});

test('Phase 8.8.52 - A3 & A5: All 43 Destinations Have Verified Images & Robust Fallbacks', () => {
  const catalogPath = path.join(projectRoot, 'data/verified_destination_images.json');
  const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf-8'));

  const totalKeys = Object.keys(catalog).length;
  assert.strictEqual(totalKeys, 43, 'Catalog must contain exactly 43 destinations');

  const missingImages = Object.entries(catalog).filter(([k, v]) => {
    return !v.image_url || !Array.isArray(v.image_gallery) || v.image_gallery.length === 0;
  });

  assert.strictEqual(
    missingImages.length,
    0,
    `All 43 destinations must have valid image_url and image_gallery. Missing: ${missingImages.map(([k, v]) => v.destination_name).join(', ')}`
  );

  // Check specific destinations that previously lacked images
  const bhairav = catalog['6ac9e42cd1723aa73d3bad2a'];
  assert.ok(bhairav && bhairav.image_url && bhairav.image_gallery.length > 0, 'Bhairavnath Temple must have image');

  const nauDevi = catalog['6ac9e42cd1723aa73d3bad2d'];
  assert.ok(nauDevi && nauDevi.image_url && nauDevi.image_gallery.length > 0, 'Nau Devi Cave Temple must have image');

  const jhajjar = catalog['6ac9e42cd1723aa73d3bad2f'];
  assert.ok(jhajjar && jhajjar.image_url && jhajjar.image_gallery.length > 0, 'Jhajjar Kotli must have image');

  const raghunath = catalog['6ac9e42dd1723aa73d3bad33'];
  assert.ok(raghunath && raghunath.image_url && raghunath.image_gallery.length > 0, 'Raghunath Temple must have image');

  const himkoti = catalog['6ac9e42dd1723aa73d3bad37'];
  assert.ok(himkoti && himkoti.image_url && himkoti.image_gallery.length > 0, 'Himkoti must have image');

  const peerKho = catalog['6ac9e42dd1723aa73d3bad3a'];
  assert.ok(peerKho && peerKho.image_url && peerKho.image_gallery.length > 0, 'Peer Kho Cave Temple must have image');

  const kishtwar = catalog['dest-kishtwar-national-park'];
  assert.ok(kishtwar && kishtwar.image_url && kishtwar.image_gallery.length > 0, 'Kishtwar National Park must have image');
});

test('Phase 8.8.52 - A3 & A5: SightseeingCard Robust Image Resolution & URL Safety', () => {
  const cardPath = path.join(projectRoot, 'frontend/src/components/SightseeingCard.jsx');
  const code = fs.readFileSync(cardPath, 'utf-8');

  // URL encoding for local images
  assert.ok(code.includes('encodeURI'), 'SightseeingCard must use encodeURI for safe asset paths');

  // Graceful fallback on image error
  assert.ok(code.includes('handleImageError'), 'SightseeingCard must implement handleImageError');
  assert.ok(code.includes('fallbackImage'), 'SightseeingCard must support fallbackImage before landmark icon');
});

test('Phase 8.8.52 - A4: Chat Destination Photo Precision', () => {
  const coordinatorPath = path.join(projectRoot, 'agents/coordinator.py');
  const code = fs.readFileSync(coordinatorPath, 'utf-8');

  // Precision guard suppressing non-destination inquiries
  assert.ok(
    code.includes('is_transport_or_procedural'),
    'coordinator must check is_transport_or_procedural to suppress non-destination inquiries'
  );
  assert.ok(
    code.includes('has_photo_intent'),
    'coordinator must check has_photo_intent'
  );

  // Must NOT rely broadly on "show me" as photo intent
  assert.ok(
    !code.includes('photos?|pictures?|pics?|images?|photographs?|gallery|show me|look like'),
    'coordinator must not rely on broad "show me" as photo intent'
  );

  // Suppresses transport/procedural queries unless photos explicitly requested
  assert.ok(
    code.includes('if is_transport_or_procedural and not has_photo_intent:'),
    'coordinator must return empty images when query is transport/procedural without photo request'
  );

  // Strictly guards Katra town photos: never attaches generic Katra photos
  assert.ok(
    code.includes('Never attach generic Katra photographs'),
    'coordinator must explicitly guard and never attach generic Katra town photographs'
  );
});

test('Phase 8.8.52 - A6: Dashboard Landing Page Spacing', () => {
  const landingPath = path.join(projectRoot, 'frontend/src/components/LandingScreen.jsx');
  const code = fs.readFileSync(landingPath, 'utf-8');

  // Balanced vertical margins
  assert.ok(code.includes("marginBottom: '1rem'"), 'Brand logo margin tightened to 1rem');
  assert.ok(code.includes("marginBottom: '0.3rem'"), 'Title margin tightened to 0.3rem');
  assert.ok(code.includes("marginBottom: '0.6rem'"), 'Subtitle margin tightened to 0.6rem');
  assert.ok(code.includes("marginBottom: '0.85rem'"), 'Edition badge margin tightened to 0.85rem');
  assert.ok(code.includes("marginBottom: '1.25rem'"), 'Introductory text margin tightened to 1.25rem');
  assert.ok(code.includes("marginBottom: '1.5rem'"), 'Action button container margin tightened to 1.5rem');

  // Zero negative margins
  assert.ok(!code.includes('margin: -') && !code.includes('marginTop: -') && !code.includes('marginBottom: -'), 'Must not use negative margins');
});

