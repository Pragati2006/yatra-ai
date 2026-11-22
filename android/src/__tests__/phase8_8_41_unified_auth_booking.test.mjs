import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// ==============================================================================
// PHASE 8.8.41: UNIFIED EMAIL OTP AUTHENTICATION & BOOKING FLOW CONSISTENCY
// ==============================================================================

test('Phase 8.8.41 — BookingScreen: No phone OTP inputs or inline phone auth routines', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  assert.ok(fs.existsSync(bookingPath), 'BookingScreen.jsx must exist');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Verify that inline phone auth state and handlers have been completely removed
  assert.strictEqual(
    code.includes('authIdentifier'),
    false,
    'BookingScreen must NOT use authIdentifier (phone/mobile auth state)'
  );
  assert.strictEqual(
    code.includes('otpSent'),
    false,
    'BookingScreen must NOT have inline otpSent state'
  );
  assert.strictEqual(
    code.includes('setOtpCode'),
    false,
    'BookingScreen must NOT have setOtpCode state setter'
  );
  assert.strictEqual(
    code.includes('handleRequestOtp'),
    false,
    'BookingScreen must NOT define or call handleRequestOtp'
  );
  assert.strictEqual(
    code.includes('handleVerifyOtp'),
    false,
    'BookingScreen must NOT define or call handleVerifyOtp'
  );
  assert.strictEqual(
    code.includes('Please verify your mobile number'),
    false,
    'BookingScreen must NOT prompt users to verify mobile number'
  );
  assert.strictEqual(
    code.includes('Please sign in with your mobile number'),
    false,
    'My Bookings must NOT prompt users to sign in with mobile number'
  );
});

test('Phase 8.8.41 — BookingScreen: Step 3 Auth Gate enforces unified Email OTP with draft preservation', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Must provide Email OTP button and prompt
  assert.ok(
    code.includes('Sign In with Email OTP'),
    'Step 3 Auth Gate must provide Sign In with Email OTP button'
  );
  assert.ok(
    code.includes('handleOpenEmailAuth'),
    'Step 3 Auth Gate must use handleOpenEmailAuth handler'
  );
  assert.ok(
    code.includes('passwordless 6-digit email OTP'),
    'Step 3 must explain authentication is via passwordless 6-digit email OTP'
  );
  assert.ok(
    code.includes('Your draft booking, selected itinerary, and travel choices are preserved'),
    'Step 3 must inform the user that their draft booking is preserved'
  );

  // Authenticated state display
  assert.ok(
    code.includes('Authenticated User Account'),
    'Step 3 must display Authenticated User Account when currentUser is present'
  );
  assert.ok(
    code.includes('currentUser.email || currentUser.name'),
    'Step 3 must display user email as primary identity'
  );
});

test('Phase 8.8.41 — BookingScreen: Navigation listener reloads auth state and restores draft upon focus', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Verify focus event listener
  assert.ok(
    code.includes("navigation.addListener('focus'"),
    'BookingScreen must attach navigation focus listener to refresh auth state when returning'
  );
  assert.ok(
    code.includes('checkUserAuth()'),
    'Focus listener must call checkUserAuth()'
  );
  assert.ok(
    code.includes('loadDraftIfAvailable()'),
    'Focus listener must call loadDraftIfAvailable()'
  );

  // Verify returnStep support
  assert.ok(
    code.includes('route?.params?.returnStep'),
    'BookingScreen must support route.params.returnStep to resume directly at Step 3'
  );
});

test('Phase 8.8.41 — BookingScreen: Draft persistence preserves selections prior to opening Auth', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Verify saveCurrentBookingDraft saves step, transport, hotel, ascent, devotee details
  assert.ok(
    code.includes('const saveCurrentBookingDraft = async'),
    'saveCurrentBookingDraft must be defined'
  );
  assert.ok(
    code.includes('selectedTransport'),
    'saveCurrentBookingDraft must save selectedTransport'
  );
  assert.ok(
    code.includes('selectedHotel'),
    'saveCurrentBookingDraft must save selectedHotel'
  );
  assert.ok(
    code.includes('selectedAscent'),
    'saveCurrentBookingDraft must save selectedAscent'
  );
  assert.ok(
    code.includes('await saveCurrentBookingDraft(3)'),
    'handleOpenEmailAuth must save draft with step 3 before navigating'
  );
  assert.ok(
    code.includes("navigation.navigate('Auth', {"),
    'handleOpenEmailAuth must navigate to Auth screen'
  );
  assert.ok(
    code.includes("returnScreen: 'Booking'"),
    'handleOpenEmailAuth must pass returnScreen: Booking'
  );
  assert.ok(
    code.includes('returnStep: 3'),
    'handleOpenEmailAuth must pass returnStep: 3'
  );
});

test('Phase 8.8.41 — BookingScreen: Contact Phone is optional and strictly for transit updates', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Input label must be Contact Phone (Optional)
  assert.ok(
    code.includes('Contact Phone (Optional)'),
    'Phone input must be labeled as Contact Phone (Optional)'
  );

  // Helper text must clarify it is for transit alerts only, not authentication
  assert.ok(
    code.includes('* Contact phone is optional and used solely for transit SMS updates'),
    'Helper text must explain contact phone is optional and for transit alerts only'
  );
  assert.ok(
    code.includes('Account authentication is strictly via passwordless Email OTP'),
    'Helper text must emphasize authentication is strictly via passwordless Email OTP'
  );

  // Step 1 validation must NOT require phone
  assert.ok(
    code.includes('if (phone.trim() && !/^\\d{10}$/.test(phone.trim().replace(/[\\s+-]/g, \'\')))'),
    'Phone validation must only trigger if phone is non-empty'
  );
});

test('Phase 8.8.41 — BookingScreen: My Bookings empty state prompts Sign In with Email OTP', () => {
  const bookingPath = path.join(SRC_DIR, 'screens', 'BookingScreen.jsx');
  const code = fs.readFileSync(bookingPath, 'utf8');

  // Empty state in "My Bookings" tab
  assert.ok(
    code.includes('Please sign in with your email address to view and manage your verified pilgrimage passes across devices.'),
    'My Bookings must prompt signing in with email address across devices'
  );
  assert.ok(
    code.includes('accessibilityLabel="Sign In with Email OTP"'),
    'My Bookings empty state must have accessible Sign In with Email OTP button'
  );
});

test('Phase 8.8.41 — AuthScreen: Supports returnScreen and returnStep parameters for seamless flow return', () => {
  const authPath = path.join(SRC_DIR, 'screens', 'AuthScreen.jsx');
  assert.ok(fs.existsSync(authPath), 'AuthScreen.jsx must exist');
  const code = fs.readFileSync(authPath, 'utf8');

  // Verify route parameter extraction
  assert.ok(
    code.includes('export default function AuthScreen({ navigation, route })'),
    'AuthScreen must accept both navigation and route props'
  );

  // Verify returnScreen navigation in OTP verification handler
  assert.ok(
    code.includes('if (route?.params?.returnScreen)'),
    'AuthScreen must check for route.params.returnScreen after successful authentication'
  );
  assert.ok(
    code.includes('navigation.navigate(route.params.returnScreen, {'),
    'AuthScreen must navigate back to returnScreen'
  );
  assert.ok(
    code.includes('returnStep: route.params.returnStep || 1'),
    'AuthScreen must pass returnStep when returning to returnScreen'
  );

  // Verify authenticated card also supports returnScreen
  assert.ok(
    code.includes('Return to ${route.params.returnScreen} →'),
    'AuthScreen must show Return to dynamic returnScreen button when returnScreen is provided'
  );
});

test('Phase 8.8.41 — Auth Contract & Backend Consistency: Passwordless Email OTP with Brevo API', () => {
  const apiPath = path.join(SRC_DIR, 'services', 'api.js');
  assert.ok(fs.existsSync(apiPath), 'api.js must exist');
  const apiCode = fs.readFileSync(apiPath, 'utf8');

  // Verify requestOtp signature accepts email
  assert.ok(
    apiCode.includes('requestOtp = async (email)'),
    'api.js requestOtp must accept email'
  );
  assert.ok(
    apiCode.includes("body: { email }"),
    'api.js requestOtp must send email in body payload'
  );

  // Verify verifyOtp signature accepts email and otpCode
  assert.ok(
    apiCode.includes('verifyOtp = async (email, otpCode)'),
    'api.js verifyOtp must accept email and otpCode'
  );
  assert.ok(
    apiCode.includes("body: { email, otp_code: otpCode }"),
    'api.js verifyOtp must send otp_code in body payload'
  );
});

test('Phase 8.8.41 — Storage Service: Booking draft helpers persist across sessions', () => {
  const storagePath = path.join(SRC_DIR, 'utils', 'storage.js');
  assert.ok(fs.existsSync(storagePath), 'storage.js must exist');
  const storageCode = fs.readFileSync(storagePath, 'utf8');

  // Verify draft helpers exist
  assert.ok(
    storageCode.includes('export const saveBookingDraft'),
    'storage.js must export saveBookingDraft'
  );
  assert.ok(
    storageCode.includes('export const getBookingDraft'),
    'storage.js must export getBookingDraft'
  );
  assert.ok(
    storageCode.includes('export const clearBookingDraft'),
    'storage.js must export clearBookingDraft'
  );
});
