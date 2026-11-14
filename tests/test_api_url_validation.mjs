import test from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeApiUrl,
  resolveApiConfig,
  isApprovedHost,
  setAuthToken,
  getAuthToken,
} from '../frontend/src/services/api.js';

test('1. normalizeApiUrl strips whitespace and trailing slashes', () => {
  assert.equal(normalizeApiUrl('  https://yatra.example.com///  '), 'https://yatra.example.com');
  assert.equal(normalizeApiUrl('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000');
  assert.equal(normalizeApiUrl(''), '');
  assert.equal(normalizeApiUrl(null), '');
  assert.equal(normalizeApiUrl(undefined), '');
});

test('2. Development mode uses localhost fallback when VITE_API_URL is empty', () => {
  const config = resolveApiConfig('', { isDev: true, isProd: false });
  assert.equal(config.baseUrl, 'http://127.0.0.1:8000');
  assert.equal(config.isMisconfigured, false);
  assert.equal(config.errorMessage, '');
});

test('3. Development mode accepts custom HTTP backend URL on localhost', () => {
  const config = resolveApiConfig('http://127.0.0.1:8000/', { isDev: true, isProd: false });
  assert.equal(config.baseUrl, 'http://127.0.0.1:8000');
  assert.equal(config.isMisconfigured, false);
  assert.equal(config.errorMessage, '');
});

test('4. Production mode requires an explicit backend URL and rejects missing URL', () => {
  const config = resolveApiConfig('', { isDev: false, isProd: true });
  assert.equal(config.baseUrl, '');
  assert.equal(config.isMisconfigured, true);
  assert.match(config.errorMessage, /Production API URL is not configured/);
});

test('5. Production mode does NOT silently fall back to localhost', () => {
  const config = resolveApiConfig(undefined, { isDev: false, isProd: true });
  assert.notEqual(config.baseUrl, 'http://127.0.0.1:8000');
  assert.notEqual(config.baseUrl, 'http://localhost:8000');
  assert.equal(config.baseUrl, '');
  assert.equal(config.isMisconfigured, true);
});

test('6. Production mode rejects insecure HTTP backend URLs', () => {
  const config = resolveApiConfig('http://api.yatra-ai.com', { isDev: false, isProd: true });
  assert.equal(config.baseUrl, '');
  assert.equal(config.isMisconfigured, true);
  assert.match(config.errorMessage, /Insecure backend URL rejected in production/);
});

test('7. Production mode rejects insecure HTTP localhost/127.0.0.1 URLs', () => {
  const config = resolveApiConfig('http://127.0.0.1:8000', { isDev: false, isProd: true });
  assert.equal(config.baseUrl, '');
  assert.equal(config.isMisconfigured, true);
  assert.match(config.errorMessage, /Insecure backend URL rejected in production/);
});

test('8. Production mode rejects malformed URLs', () => {
  const malformedInputs = [
    'not-a-valid-url',
    'ftp://invalid-proto.com',
    'http//missing-colon.com',
    'just-a-string',
  ];

  for (const input of malformedInputs) {
    const config = resolveApiConfig(input, { isDev: false, isProd: true });
    assert.equal(config.baseUrl, '', `Expected empty baseUrl for input: ${input}`);
    assert.equal(config.isMisconfigured, true, `Expected isMisconfigured for input: ${input}`);
    assert.ok(config.errorMessage.length > 0, `Expected error message for input: ${input}`);
  }
});

test('9. Production mode accepts valid secure HTTPS backend URLs when explicitly allowed', () => {
  const allowedHosts = ['yatra-ai-backend.example.com'];
  const config = resolveApiConfig('https://yatra-ai-backend.example.com/', { isDev: false, isProd: true, allowedHosts });
  assert.equal(config.baseUrl, 'https://yatra-ai-backend.example.com');
  assert.equal(config.isMisconfigured, false);
  assert.equal(config.errorMessage, '');
});

test('10. Production mode accepts valid Cloudflare Quick Tunnel HTTPS URLs', () => {
  const config = resolveApiConfig('https://quiet-mountain-123.trycloudflare.com/', { isDev: false, isProd: true });
  assert.equal(config.baseUrl, 'https://quiet-mountain-123.trycloudflare.com');
  assert.equal(config.isMisconfigured, false);
  assert.equal(config.errorMessage, '');
});

test('11. Production mode rejects whitespace-only URLs', () => {
  const config = resolveApiConfig('   ', { isDev: false, isProd: true });
  assert.equal(config.baseUrl, '');
  assert.equal(config.isMisconfigured, true);
  assert.match(config.errorMessage, /Production API URL is not configured/);
});

test('12. Host Policy: isApprovedHost validates approved tunnels and rejects arbitrary domains', () => {
  // Approved Cloudflare Quick Tunnels
  assert.equal(isApprovedHost('quiet-mountain-123.trycloudflare.com'), true);
  assert.equal(isApprovedHost('towers-hebrew-louisiana-divisions.trycloudflare.com'), true);
  assert.equal(isApprovedHost('shrine-ai-2026.trycloudflare.com'), true);

  // Arbitrary untrusted external domains
  assert.equal(isApprovedHost('attacker.example'), false);
  assert.equal(isApprovedHost('evil-corp.com'), false);
  assert.equal(isApprovedHost('google.com'), false);

  // Subdomain spoofing attempts
  assert.equal(isApprovedHost('trycloudflare.com.attacker.example'), false);
  assert.equal(isApprovedHost('attacker-trycloudflare.com'), false);
  assert.equal(isApprovedHost('trycloudflare.com'), false); // Must have subdomain
});

test('13. Security Gate: Arbitrary external HTTPS URLs are STRICTLY REJECTED in production', () => {
  const untrustedInputs = [
    'https://attacker.example',
    'https://attacker.example/api/v1',
    'https://evil-shrine-portal.org',
    'https://trycloudflare.com.attacker.example',
  ];

  for (const untrusted of untrustedInputs) {
    const config = resolveApiConfig(untrusted, { isDev: false, isProd: true });
    assert.equal(config.baseUrl, '', `Expected rejection for: ${untrusted}`);
    assert.equal(config.isMisconfigured, true, `Expected isMisconfigured for: ${untrusted}`);
    assert.match(config.errorMessage, /Untrusted backend origin rejected/);
  }
});

test('14. Security Gate: Credential-bearing URLs (user:pass@host) are STRICTLY REJECTED', () => {
  const credentialInputs = [
    'https://user:password@quiet-mountain-123.trycloudflare.com',
    'https://admin:secret@attacker.example',
    'https://devotee@quiet-mountain-123.trycloudflare.com',
  ];

  for (const credUrl of credentialInputs) {
    const config = resolveApiConfig(credUrl, { isDev: false, isProd: true });
    assert.equal(config.baseUrl, '', `Expected rejection for credential-bearing: ${credUrl}`);
    assert.equal(config.isMisconfigured, true);
    assert.match(config.errorMessage, /Credential-bearing API URLs are rejected/);
  }
});

test('15. Host Policy: Path, query, and hash are stripped to clean origin base URL', () => {
  const dirtyUrl = 'https://quiet-mountain-123.trycloudflare.com/extra/path?query=param#fragment';
  const config = resolveApiConfig(dirtyUrl, { isDev: false, isProd: true });
  assert.equal(config.baseUrl, 'https://quiet-mountain-123.trycloudflare.com');
  assert.equal(config.isMisconfigured, false);
});

test('16. Host Policy: Valid custom HTTPS port on approved tunnel is preserved safely', () => {
  const portUrl = 'https://quiet-mountain-123.trycloudflare.com:8443';
  const config = resolveApiConfig(portUrl, { isDev: false, isProd: true });
  assert.equal(config.baseUrl, 'https://quiet-mountain-123.trycloudflare.com:8443');
  assert.equal(config.isMisconfigured, false);
});

test('17. Token Leakage Defense: Switching or clearing backends revokes active session token', () => {
  // Set an active session token
  setAuthToken('sensitive-devotee-session-token-xyz');
  assert.equal(getAuthToken(), 'sensitive-devotee-session-token-xyz');

  // Explicitly clear token (as setRuntimeApiUrl does)
  setAuthToken(null);
  assert.equal(getAuthToken(), null);
});
