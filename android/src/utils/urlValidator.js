/**
 * Host & URL Security Policy Validator for Yatra AI Android
 * Ensures zero credential leakage to arbitrary or rogue backends.
 * Permits HTTP strictly for private local development networks (RFC 1918 / Loopback).
 * Enforces HTTPS for all public network domains.
 */

export const APPROVED_TUNNEL_HOST_PATTERN = /^[a-z0-9][a-z0-9-]{1,62}\.trycloudflare\.com$/;

/**
 * Checks whether a hostname belongs to a private local-development network:
 * - Localhost loopback (localhost, 127.0.0.1, ::1)
 * - Android emulator loopback alias (10.0.2.2)
 * - RFC 1918 Private IPv4 networks:
 *   - 10.0.0.0/8 (10.0.0.0 - 10.255.255.255)
 *   - 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
 *   - 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)
 * - RFC 3927 Link-local IPv4 network:
 *   - 169.254.0.0/16 (169.254.0.0 - 169.254.255.255)
 */
export const isPrivateNetworkHost = (hostname) => {
  if (!hostname || typeof hostname !== 'string') return false;
  const lower = hostname.toLowerCase().trim();

  // Localhost names
  if (lower === 'localhost' || lower === '127.0.0.1' || lower === '::1') {
    return true;
  }

  // Android emulator loopback alias
  if (lower === '10.0.2.2') {
    return true;
  }

  // IPv4 format check: d.d.d.d where 0 <= d <= 255
  const ipv4Regex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
  const match = lower.match(ipv4Regex);
  if (match) {
    const oct1 = parseInt(match[1], 10);
    const oct2 = parseInt(match[2], 10);
    const oct3 = parseInt(match[3], 10);
    const oct4 = parseInt(match[4], 10);

    if (oct1 > 255 || oct2 > 255 || oct3 > 255 || oct4 > 255) {
      return false;
    }

    // 10.0.0.0/8 (10.0.0.0 - 10.255.255.255)
    if (oct1 === 10) return true;

    // 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
    if (oct1 === 172 && oct2 >= 16 && oct2 <= 31) return true;

    // 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)
    if (oct1 === 192 && oct2 === 168) return true;

    // 127.0.0.0/8 Loopback
    if (oct1 === 127) return true;

    // 169.254.0.0/16 Link-Local
    if (oct1 === 169 && oct2 === 254) return true;

    // Any other IPv4 (e.g. 8.8.8.8, 1.1.1.1, 54.210.x.x) is public
    return false;
  }

  return false;
};

export const isApprovedHost = (hostname, { isDev = false, allowedHosts = [] } = {}) => {
  if (!hostname || typeof hostname !== 'string') return false;
  const lower = hostname.toLowerCase().trim();

  // 1. Private local development networks (including emulator, localhost, LAN IPs)
  if (isPrivateNetworkHost(lower)) {
    return true;
  }

  // 2. Custom explicit allowed hosts
  for (const host of allowedHosts) {
    if (host && lower === host.toLowerCase()) return true;
  }

  // 3. Official Cloudflare Quick Tunnel pattern:
  // Must be a valid single subdomain ending in .trycloudflare.com
  if (APPROVED_TUNNEL_HOST_PATTERN.test(lower)) {
    return true;
  }

  // 4. Approved Cloud PaaS patterns (Render & Hugging Face Spaces):
  const renderRegex = /^[a-z0-9][a-z0-9-]{1,62}\.onrender\.com$/;
  if (renderRegex.test(lower)) {
    return true;
  }

  const hfSpacesRegex = /^[a-z0-9][a-z0-9-]{1,62}\.hf\.space$/;
  if (hfSpacesRegex.test(lower)) {
    return true;
  }

  return false;
};

export const normalizeUrl = (url) => {
  if (!url || typeof url !== 'string') return '';
  return url.trim().replace(/\/+$/, '');
};

export const sanitizeBackendUrl = normalizeUrl;

export const getPresetUrls = () => [
  { label: 'Render Cloud Backend (Production)', url: 'https://yatra-ai-smap.onrender.com' },
  { label: 'Host Wi-Fi LAN (192.168.29.176:8000)', url: 'http://192.168.29.176:8000' },
  { label: 'Cloudflare Quick Tunnel', url: 'https://' },
  { label: 'Hugging Face Space', url: 'https://' },
  { label: 'Android Emulator (10.0.2.2:8000)', url: 'http://10.0.2.2:8000' },
  { label: 'Local LAN IP (192.168.x.x:8000)', url: 'http://192.168.1.100:8000' },
  { label: 'Localhost (127.0.0.1:8000)', url: 'http://127.0.0.1:8000' },
];

export const validateBackendUrl = (rawUrl, { isDev = false, allowedHosts = [] } = {}) => {
  const normalized = normalizeUrl(rawUrl);
  if (!normalized) {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: 'Backend URL cannot be empty.',
    };
  }

  let parsed;
  try {
    parsed = new URL(normalized);
  } catch {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: `Malformed backend URL: "${rawUrl}". Please provide a valid absolute URL (e.g. http://192.168.1.5:8000 or https://xyz.trycloudflare.com).`,
    };
  }

  if (!parsed.protocol || !parsed.host) {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: 'Backend URL is missing protocol or host.',
    };
  }

  // Reject credentials in URL
  if (parsed.username || parsed.password) {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: 'Credential-bearing URLs (user:pass@host) are rejected for security.',
    };
  }

  const isPrivate = isPrivateNetworkHost(parsed.hostname);

  // Require HTTPS for public network domains
  if (!isPrivate && parsed.protocol !== 'https:') {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: 'Public backend connections strictly require HTTPS. HTTP is only permitted for private local-network development addresses (e.g. 192.168.x.x, 10.x.x.x, 10.0.2.2).',
    };
  }

  // Check host approval policy
  if (!isApprovedHost(parsed.hostname, { isDev, allowedHosts })) {
    return {
      isValid: false,
      baseUrl: '',
      sanitizedUrl: '',
      error: `Untrusted backend origin rejected: "${parsed.hostname}". Allowed origins are private development networks (192.168.x.x, 10.x.x.x, 10.0.2.2, localhost) or verified *.trycloudflare.com tunnels.`,
    };
  }

  const cleanOrigin = `${parsed.protocol}//${parsed.host}`;
  return {
    isValid: true,
    baseUrl: cleanOrigin,
    sanitizedUrl: cleanOrigin,
    error: '',
  };
};

export default {
  APPROVED_TUNNEL_HOST_PATTERN,
  isPrivateNetworkHost,
  isApprovedHost,
  normalizeUrl,
  sanitizeBackendUrl,
  getPresetUrls,
  validateBackendUrl,
};
