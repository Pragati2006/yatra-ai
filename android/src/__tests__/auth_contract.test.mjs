import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { register } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Register an ESM loader to intercept React Native / Expo native module bindings for pure Node test execution
const loaderCode = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === 'expo-constants') {
    return {
      url: 'data:text/javascript,export default { expoConfig: { extra: { apiUrl: "https://yatra-ai-smap.onrender.com" } } };',
      shortCircuit: true,
    };
  }
  if (specifier === '../utils/storage' || specifier.endsWith('/storage') || specifier.endsWith('/storage.js') || specifier === '@react-native-async-storage/async-storage' || specifier === 'expo-secure-store') {
    return {
      url: 'data:text/javascript,export const getAuthToken = async () => null; export const saveAuthToken = async () => {}; export const clearAuthToken = async () => {}; export const getStoredBackendUrl = async () => null; export const setStoredBackendUrl = async () => {}; export default {};',
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}
`;

register(`data:text/javascript,${encodeURIComponent(loaderCode)}`);

const { requestOtp, verifyOtp } = await import('../services/api.js');

// ==============================================================================
// 1. EMAIL VALIDATION CONTRACT TESTS
// ==============================================================================

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email) {
  if (typeof email !== 'string') return false;
  const clean = email.trim().toLowerCase();
  return clean.length <= 254 && EMAIL_REGEX.test(clean);
}

test('Email Validator: Accepts valid devotee email addresses', () => {
  assert.equal(isValidEmail('devotee@example.com'), true);
  assert.equal(isValidEmail('yatra.pilgrim@domain.co.in'), true);
  assert.equal(isValidEmail('shri.mata@vaishnodevi.org'), true);
});

test('Email Validator: Rejects phone numbers and non-email formats', () => {
  assert.equal(isValidEmail('9876543210'), false);
  assert.equal(isValidEmail('+919876543210'), false);
  assert.equal(isValidEmail('devotee@'), false);
  assert.equal(isValidEmail('@example.com'), false);
  assert.equal(isValidEmail('not-an-email'), false);
  assert.equal(isValidEmail(''), false);
  assert.equal(isValidEmail(null), false);
});

// ==============================================================================
// 2. OTP FORMAT CONTRACT TESTS
// ==============================================================================

function isValidOtpCode(code) {
  if (typeof code !== 'string') return false;
  const clean = code.trim();
  return clean.length === 6 && /^\d+$/.test(clean);
}

test('OTP Validator: Accepts exact 6-digit numeric codes', () => {
  assert.equal(isValidOtpCode('123456'), true);
  assert.equal(isValidOtpCode('000000'), true);
  assert.equal(isValidOtpCode('987654'), true);
});

test('OTP Validator: Rejects invalid lengths and non-numeric codes', () => {
  assert.equal(isValidOtpCode('12345'), false);
  assert.equal(isValidOtpCode('1234567'), false);
  assert.equal(isValidOtpCode('12345a'), false);
  assert.equal(isValidOtpCode('abcdef'), false);
  assert.equal(isValidOtpCode(''), false);
  assert.equal(isValidOtpCode(null), false);
});

// ==============================================================================
// 3. AUTH SCREEN CODE INTEGRITY: NO HARDCODED DEV OTP BYPASS
// ==============================================================================

test('Auth Screen Integrity: Confirms no mock OTP "123456" bypass exists in AuthScreen', () => {
  const authScreenPath = path.resolve(__dirname, '../screens/AuthScreen.jsx');
  const content = fs.readFileSync(authScreenPath, 'utf8');

  // Verify phone state is completely removed
  assert.doesNotMatch(content, /useState\(['"]phone['"]\)/, 'AuthScreen should not have phone step state');
  assert.doesNotMatch(content, /cleanPhone\.length\s*<\s*10/, 'AuthScreen should not validate 10-digit phone');

  // Verify mock OTP bypass is removed
  assert.doesNotMatch(content, /Generated Dev OTP: 123456/, 'Mock dev OTP alert must not exist');
  assert.doesNotMatch(content, /otp\.trim\(\)\s*===\s*['"]123456['"]/, 'Mock OTP 123456 comparison must not exist');

  // Verify email input is present
  assert.match(content, /keyboardType=["']email-address["']/, 'Email input keyboard type must be present');
  assert.match(content, /cleanEmail\.includes\(['"]@['"]\)/, 'Email @ check must be present');
  assert.match(content, /setCooldown/, 'Cooldown timer must be handled');
});

// ==============================================================================
// 4. ACTUAL API FUNCTION CONTRACT TESTS (MOCKED FETCH)
// ==============================================================================

test('API Client: requestOtp sends exact { email } payload with no phone field', async () => {
  const recorded = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (url, options) => {
    const body = options?.body ? JSON.parse(options.body) : null;
    recorded.push({ url, options, body });
    return {
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'success', message: 'OTP sent', cooldown_seconds: 60 }),
    };
  };

  try {
    const devoteeEmail = 'pilgrim@vaishnodevi.org';
    const res = await requestOtp(devoteeEmail);

    assert.equal(res.status, 'success');
    assert.equal(recorded.length, 1);

    const call = recorded[0];
    assert.match(call.url, /\/api\/auth\/request-otp$/);
    assert.equal(call.options.method, 'POST');

    // Verify payload strictly matches { email } and does NOT include phone
    assert.deepEqual(call.body, { email: devoteeEmail });
    assert.equal('phone' in call.body, false, 'requestOtp must NOT include phone field');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API Client: verifyOtp sends exact { email, otp_code } payload with no phone field', async () => {
  const recorded = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (url, options) => {
    const body = options?.body ? JSON.parse(options.body) : null;
    recorded.push({ url, options, body });
    return {
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({
        status: 'authenticated',
        session_token: 'yatra-session-token-live',
        user: { email: 'pilgrim@vaishnodevi.org', user_id: 'usr-123' },
      }),
    };
  };

  try {
    const devoteeEmail = 'pilgrim@vaishnodevi.org';
    const devoteeOtp = '849201';
    const res = await verifyOtp(devoteeEmail, devoteeOtp);

    assert.equal(res.status, 'authenticated');
    assert.equal(recorded.length, 1);

    const call = recorded[0];
    assert.match(call.url, /\/api\/auth\/verify-otp$/);
    assert.equal(call.options.method, 'POST');

    // Verify payload strictly matches { email, otp_code } and does NOT include phone
    assert.deepEqual(call.body, { email: devoteeEmail, otp_code: devoteeOtp });
    assert.equal('phone' in call.body, false, 'verifyOtp must NOT include phone field');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
