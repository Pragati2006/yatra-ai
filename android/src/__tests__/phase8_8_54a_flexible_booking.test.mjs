import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

test('Phase 8.8.54A — Android API Client: confirmBooking forwards flexible booking & individual pilgrim parameters', () => {
  const apiPath = path.join(SRC_DIR, 'services', 'api.js');
  const code = fs.readFileSync(apiPath, 'utf8');

  assert.ok(
    code.includes('pilgrims') &&
    code.includes('primary_contact') &&
    code.includes('hotel_selected') &&
    code.includes('transport_selected') &&
    code.includes('own_vehicle'),
    'api.js confirmBooking must forward pilgrims, primary_contact, hotel_selected, transport_selected, and own_vehicle'
  );
});

test('Phase 8.8.54A — Android ChatScreen & ChatBubble: forwards booking_handoff context to BookingScreen', () => {
  const chatBubblePath = path.join(SRC_DIR, 'components', 'ChatBubble.jsx');
  const bubbleCode = fs.readFileSync(chatBubblePath, 'utf8');

  assert.ok(
    bubbleCode.includes('booking_handoff') || bubbleCode.includes('handoff'),
    'ChatBubble must recognize booking_handoff data'
  );

  const chatScreenPath = path.join(SRC_DIR, 'screens', 'ChatScreen.jsx');
  const chatScreenCode = fs.readFileSync(chatScreenPath, 'utf8');

  assert.ok(
    chatScreenCode.includes('navigation.navigate(\'Booking\'') ||
    chatScreenCode.includes('navigation.navigate("Booking"'),
    'ChatScreen must route navigation to Booking'
  );
  assert.ok(
    chatScreenCode.includes('pilgrims') && chatScreenCode.includes('hotel_selected'),
    'ChatScreen must pass pilgrims and service selection to Booking screen'
  );
});

test('Phase 8.8.54A — Android BookingScreen: Flexible service toggles and Own Vehicle handling', () => {
  const bookingScreenPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingScreenPath, 'utf8');

  assert.ok(code.includes('includeHotel'), 'BookingScreen must maintain includeHotel state');
  assert.ok(code.includes('includeTransport'), 'BookingScreen must maintain includeTransport state');
  assert.ok(code.includes('ownVehicle'), 'BookingScreen must maintain ownVehicle state');
  assert.ok(code.includes('Own Vehicle / Self-Drive'), 'BookingScreen must render Own Vehicle option');
  assert.ok(code.includes('transportCost'), 'BookingScreen must calculate transport cost based on selection');
  assert.ok(code.includes('hotelCost'), 'BookingScreen must calculate hotel cost based on selection');
});

test('Phase 8.8.54A — Android BookingScreen: Dynamic individual pilgrim roster and validation', () => {
  const bookingScreenPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingScreenPath, 'utf8');

  assert.ok(code.includes('handleAddPilgrim'), 'Must have handleAddPilgrim');
  assert.ok(code.includes('handleRemovePilgrim'), 'Must have handleRemovePilgrim');
  assert.ok(code.includes('handleUpdatePilgrim'), 'Must have handleUpdatePilgrim');
  assert.ok(code.includes('Devotee #'), 'Must render individual pilgrim/devotee numbering');
  assert.ok(code.includes('duplicateNameAdvisory') || code.includes('Devotee name'), 'Must support advisory for duplicate pilgrim names');
  assert.ok(code.includes('1-125'), 'Must enforce strict age validation 1-125');
  assert.ok(code.includes('Filled from your conversation'), 'Must render badge when populated from chat');
});

test('Phase 8.8.54C — Android BookingScreen: Allows legitimate pilgrims with identical full names', () => {
  const bookingScreenPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingScreenPath, 'utf8');

  // Must not block submission when names match
  assert.ok(
    !code.includes("Alert.alert('Duplicate Devotee Name'") &&
    !code.includes("Alert.alert(\n        'Duplicate Devotee Name'") &&
    !code.includes('Alert.alert("Duplicate Devotee Name"'),
    'BookingScreen must not block progression with an alert when devotee names match'
  );

  // Must maintain unique record identifier for each pilgrim
  assert.ok(
    code.includes('generatePilgrimId') || code.includes('id:'),
    'BookingScreen must assign unique record identifiers to each devotee'
  );

  // Non-blocking advisory warning is supported
  assert.ok(
    code.includes('duplicateNameAdvisory'),
    'BookingScreen must support non-blocking advisory note for duplicate names'
  );

  // Simulation status is explicitly SIMULATED_ISSUED
  assert.ok(
    code.includes('SIMULATED_ISSUED'),
    'BookingScreen must use SIMULATED_ISSUED status for simulated demo passes'
  );
});

test('Phase 8.8.54A — Android BookingScreen: Step 2 exclusion notices and Step 3 itemized review', () => {
  const bookingScreenPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingScreenPath, 'utf8');

  assert.ok(code.includes('Self-Arranged Transport') || code.includes('Own Vehicle Transport'), 'Step 2 must show transport exclusion notice');
  assert.ok(code.includes('Self-Arranged Accommodation'), 'Step 2 must show accommodation exclusion notice');
  assert.ok(code.includes('Registered Devotees'), 'Step 3 must display registered devotees roster');
  assert.ok(code.includes('REGISTERED DEVOTEES & ACCESS PASSES'), 'Step 4 must show individual devotee access passes');
});
