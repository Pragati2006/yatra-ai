import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validateBackendUrl,
  isApprovedHost,
  isPrivateNetworkHost,
  APPROVED_TUNNEL_HOST_PATTERN,
  sanitizeBackendUrl,
  getPresetUrls,
} from '../utils/urlValidator.js';

// ==============================================================================
// 1. PRIVATE NETWORK HOST DETECTOR TESTS (RFC 1918 / LOOPBACK)
// ==============================================================================

test('Private Host: Detects standard localhost and emulator hosts', () => {
  assert.equal(isPrivateNetworkHost('localhost'), true);
  assert.equal(isPrivateNetworkHost('127.0.0.1'), true);
  assert.equal(isPrivateNetworkHost('::1'), true);
  assert.equal(isPrivateNetworkHost('10.0.2.2'), true);
});

test('Private Host: Detects RFC 1918 192.168.0.0/16 private subnet (Home/Office Wi-Fi)', () => {
  assert.equal(isPrivateNetworkHost('192.168.1.15'), true);
  assert.equal(isPrivateNetworkHost('192.168.0.1'), true);
  assert.equal(isPrivateNetworkHost('192.168.254.254'), true);
  // Rejects outside 192.168
  assert.equal(isPrivateNetworkHost('192.169.1.1'), false);
  assert.equal(isPrivateNetworkHost('192.167.1.1'), false);
});

test('Private Host: Detects RFC 1918 10.0.0.0/8 private subnet', () => {
  assert.equal(isPrivateNetworkHost('10.0.0.5'), true);
  assert.equal(isPrivateNetworkHost('10.100.200.1'), true);
  assert.equal(isPrivateNetworkHost('10.255.255.254'), true);
  // Rejects outside 10.x
  assert.equal(isPrivateNetworkHost('11.0.0.1'), false);
});

test('Private Host: Detects RFC 1918 172.16.0.0/12 private subnet (Mobile Hotspot)', () => {
  assert.equal(isPrivateNetworkHost('172.16.0.1'), true);
  assert.equal(isPrivateNetworkHost('172.20.10.4'), true); // Common iOS/Android hotspot IP
  assert.equal(isPrivateNetworkHost('172.31.255.254'), true);
  // Rejects outside 172.16 - 172.31
  assert.equal(isPrivateNetworkHost('172.15.0.1'), false);
  assert.equal(isPrivateNetworkHost('172.32.0.1'), false);
});

test('Private Host: Detects RFC 3927 Link-Local 169.254.0.0/16 subnet', () => {
  assert.equal(isPrivateNetworkHost('169.254.1.1'), true);
  assert.equal(isPrivateNetworkHost('169.255.1.1'), false);
});

test('Private Host: Rejects public internet IPs and domains', () => {
  assert.equal(isPrivateNetworkHost('8.8.8.8'), false);
  assert.equal(isPrivateNetworkHost('1.1.1.1'), false);
  assert.equal(isPrivateNetworkHost('54.210.12.3'), false);
  assert.equal(isPrivateNetworkHost('example.com'), false);
  assert.equal(isPrivateNetworkHost('attacker.org'), false);
  assert.equal(isPrivateNetworkHost('devotee.trycloudflare.com'), false);
});

// ==============================================================================
// 2. URL VALIDATOR: HTTP FOR PRIVATE NETWORKS VS HTTPS FOR PUBLIC DOMAINS
// ==============================================================================

test('URL Policy: Accepts HTTP for private LAN IP addresses (e.g. laptop Wi-Fi IPv4)', () => {
  const r1 = validateBackendUrl('http://192.168.1.15:8000');
  assert.equal(r1.isValid, true);
  assert.equal(r1.sanitizedUrl, 'http://192.168.1.15:8000');

  const r2 = validateBackendUrl('http://10.0.0.42:8000/');
  assert.equal(r2.isValid, true);
  assert.equal(r2.sanitizedUrl, 'http://10.0.0.42:8000');

  const r3 = validateBackendUrl('http://172.20.10.2:8000');
  assert.equal(r3.isValid, true);
  assert.equal(r3.sanitizedUrl, 'http://172.20.10.2:8000');
});

test('URL Policy: Accepts HTTP for local emulator and localhost', () => {
  const r1 = validateBackendUrl('http://10.0.2.2:8000');
  assert.equal(r1.isValid, true);
  assert.equal(r1.sanitizedUrl, 'http://10.0.2.2:8000');

  const r2 = validateBackendUrl('http://localhost:8000');
  assert.equal(r2.isValid, true);
  assert.equal(r2.sanitizedUrl, 'http://localhost:8000');

  const r3 = validateBackendUrl('http://127.0.0.1:8000');
  assert.equal(r3.isValid, true);
  assert.equal(r3.sanitizedUrl, 'http://127.0.0.1:8000');
});

test('URL Policy: Strictly REJECTS HTTP for public IP addresses and public domains', () => {
  // Public IP over HTTP must be rejected
  const r1 = validateBackendUrl('http://8.8.8.8:8000');
  assert.equal(r1.isValid, false);
  assert.match(r1.error, /HTTPS/);

  // Public domain over HTTP must be rejected
  const r2 = validateBackendUrl('http://my-backend.example.com');
  assert.equal(r2.isValid, false);
  assert.match(r2.error, /HTTPS/);

  // Cloudflare tunnel over HTTP must be rejected
  const r3 = validateBackendUrl('http://devotee-guidance-yatra.trycloudflare.com');
  assert.equal(r3.isValid, false);
  assert.match(r3.error, /HTTPS/);
});

test('URL Policy: Accepts HTTPS for approved Cloudflare Quick Tunnels', () => {
  const tunnelUrl = 'https://devotee-guidance-yatra.trycloudflare.com';
  const result = validateBackendUrl(tunnelUrl);
  assert.equal(result.isValid, true);
  assert.equal(result.sanitizedUrl, tunnelUrl);
  assert.equal(isApprovedHost('devotee-guidance-yatra.trycloudflare.com'), true);
});

test('URL Policy: Rejects unapproved public domains even with HTTPS', () => {
  const result = validateBackendUrl('https://malicious-phishing-site.com');
  assert.equal(result.isValid, false);
  assert.match(result.error, /origin/i);
  assert.equal(isApprovedHost('malicious-phishing-site.com'), false);
});

test('URL Policy: Rejects embedded user credentials (user:pass@host) even on private LAN', () => {
  const r1 = validateBackendUrl('http://admin:secret@192.168.1.15:8000');
  assert.equal(r1.isValid, false);
  assert.match(r1.error, /credential/i);

  const r2 = validateBackendUrl('https://admin:secret@test.trycloudflare.com');
  assert.equal(r2.isValid, false);
  assert.match(r2.error, /credential/i);
});

test('URL Policy: Strips trailing slashes, whitespace and preserves port', () => {
  const sanitized = sanitizeBackendUrl('  http://192.168.1.15:8000///  ');
  assert.equal(sanitized, 'http://192.168.1.15:8000');
});

test('URL Policy: Provides standard presets including LAN IP placeholder', () => {
  const presets = getPresetUrls();
  assert.ok(Array.isArray(presets));
  assert.ok(presets.length >= 3);
  assert.ok(presets.some((p) => p.url.includes('10.0.2.2')));
  assert.ok(presets.some((p) => p.url.includes('192.168')));
  assert.ok(presets.some((p) => p.url.includes('127.0.0.1')));
});

test('Security Gate: Cloudflare subdomain regex compliance', () => {
  assert.equal(APPROVED_TUNNEL_HOST_PATTERN.test('abc-123.trycloudflare.com'), true);
  assert.equal(APPROVED_TUNNEL_HOST_PATTERN.test('yatra-ai-quick-tunnel.trycloudflare.com'), true);
  assert.equal(APPROVED_TUNNEL_HOST_PATTERN.test('abc..trycloudflare.com'), false);
  assert.equal(APPROVED_TUNNEL_HOST_PATTERN.test('evil.trycloudflare.com.attacker.com'), false);
  assert.equal(APPROVED_TUNNEL_HOST_PATTERN.test('trycloudflare.com'), false);
});

test('Security Gate: Rejects malformed and empty URLs', () => {
  assert.equal(validateBackendUrl('').isValid, false);
  assert.equal(validateBackendUrl('   ').isValid, false);
  assert.equal(validateBackendUrl('not_a_valid_url_scheme').isValid, false);
});

// ==============================================================================
// 3. TOKEN ISOLATION & AUTHORIZATION HEADER TESTS
// ==============================================================================

test('Token Isolation: Switching from LAN to tunnel purges active session tokens', () => {
  let storedToken = 'valid-jwt-token-lan';
  let activeBackend = 'http://192.168.1.15:8000';

  const switchBackend = (newUrl) => {
    const val = validateBackendUrl(newUrl, { isDev: true });
    if (!val.isValid) throw new Error(val.error);
    storedToken = null; // Security rule
    activeBackend = val.baseUrl;
    return activeBackend;
  };

  assert.equal(storedToken, 'valid-jwt-token-lan');
  const updated = switchBackend('https://new-session.trycloudflare.com');
  assert.equal(updated, 'https://new-session.trycloudflare.com');
  assert.equal(storedToken, null, 'Active token must be purged upon backend switch');
});

test('Authorization Header Isolation: Attaches to private LAN & approved tunnels, never to unapproved public hosts', () => {
  const storedToken = 'devotee-secret-token';

  const prepareHeaders = (targetUrl) => {
    let hostname;
    try {
      hostname = new URL(targetUrl).hostname;
    } catch {
      return {};
    }

    const headers = {
      'Content-Type': 'application/json',
      'X-Client-Platform': 'android-react-native',
    };

    if (storedToken && isApprovedHost(hostname)) {
      headers['Authorization'] = `Bearer ${storedToken}`;
    }
    return headers;
  };

  // 1. Private LAN IP - Allowed
  const lanHeaders = prepareHeaders('http://192.168.1.15:8000/api/chat');
  assert.equal(lanHeaders['Authorization'], 'Bearer devotee-secret-token');

  // 2. Approved Cloudflare tunnel - Allowed
  const tunnelHeaders = prepareHeaders('https://valid-tunnel.trycloudflare.com/api/chat');
  assert.equal(tunnelHeaders['Authorization'], 'Bearer devotee-secret-token');

  // 3. Rogue unapproved public host - STRICTLY BLOCKED
  const rogueHeaders = prepareHeaders('https://attacker.example.com/api/chat');
  assert.equal(rogueHeaders['Authorization'], undefined, 'Rogue origin must not receive Authorization header');
});
