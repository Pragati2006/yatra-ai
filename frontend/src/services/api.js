import axios from 'axios';

// Standard production backend shared across Web and Android
export const DEFAULT_PRODUCTION_BACKEND = 'https://yatra-ai-smap.onrender.com';

// Resolve, normalize, and validate API_BASE_URL
export const normalizeApiUrl = (url) => {
  if (!url || typeof url !== 'string') return '';
  return url.trim().replace(/\/+$/, '');
};

/**
 * Validates whether a hostname satisfies the host security policy:
 * - Development: allows localhost, 127.0.0.1, [::1], and approved tunnels.
 * - Production: allows configured production host, or verified *.trycloudflare.com tunnels.
 * - Strictly rejects arbitrary domains (e.g. attacker.example, arbitrary CDNs, spoofed domains).
 */
export const isApprovedHost = (hostname, { isDev = false, _isProd = false, allowedHosts = [] } = {}) => {
  if (!hostname || typeof hostname !== 'string') return false;
  const lower = hostname.toLowerCase();

  // Development mode allows local loopback addresses
  if (isDev) {
    if (lower === 'localhost' || lower === '127.0.0.1' || lower === '::1' || lower === '[::1]') {
      return true;
    }
  }

  // Check explicit allowed hosts list (e.g. build-time VITE_API_URL host)
  for (const host of allowedHosts) {
    if (host && lower === host.toLowerCase()) return true;
  }

  // Cloudflare Quick Tunnel official pattern:
  // Must be a valid subdomain ending strictly in .trycloudflare.com
  // Rejects: trycloudflare.com (no subdomain), trycloudflare.com.attacker.com, attacker-trycloudflare.com
  const quickTunnelRegex = /^[a-z0-9][a-z0-9-]{1,62}\.trycloudflare\.com$/;
  if (quickTunnelRegex.test(lower)) {
    return true;
  }

  // Approved Cloud PaaS patterns (Render & Hugging Face Spaces):
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

export const resolveApiConfig = (rawUrl, { isDev = false, isProd = false, allowedHosts = [] } = {}) => {
  const normalized = normalizeApiUrl(rawUrl);

  // 1. Explicit URL supplied
  if (normalized) {
    let parsed;
    try {
      parsed = new URL(normalized);
    } catch {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Malformed API URL: "${rawUrl}". Please provide a valid absolute URL (e.g. https://api.yatra.com).`,
      };
    }

    if (!parsed.protocol || !parsed.host) {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Malformed API URL: "${rawUrl}". Missing protocol or host.`,
      };
    }

    // Reject credentials in URL (e.g. https://user:pass@host)
    if (parsed.username || parsed.password) {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Credential-bearing API URLs are rejected for security: "${rawUrl}".`,
      };
    }

    // In production, reject insecure HTTP URLs
    if (isProd && parsed.protocol !== 'https:') {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Insecure backend URL rejected in production: "${rawUrl}". Production builds require a secure HTTPS URL.`,
      };
    }

    // Reject arbitrary untrusted external hosts
    if (isProd && !isApprovedHost(parsed.hostname, { isDev, isProd, allowedHosts })) {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Untrusted backend origin rejected: "${parsed.hostname}". Allowed origins are configured production hosts or verified *.trycloudflare.com tunnels.`,
      };
    }

    if (isDev && !isApprovedHost(parsed.hostname, { isDev, isProd, allowedHosts })) {
      return {
        baseUrl: '',
        isMisconfigured: true,
        errorMessage: `Untrusted development backend origin: "${parsed.hostname}". Allowed origins are localhost, 127.0.0.1, or verified *.trycloudflare.com tunnels.`,
      };
    }

    // Normalize to origin + port (strip path/query/hash to avoid route pollution)
    const cleanOrigin = `${parsed.protocol}//${parsed.host}`;

    return {
      baseUrl: cleanOrigin,
      isMisconfigured: false,
      errorMessage: '',
    };
  }

  // 2. Development default fallback
  if (isDev) {
    return {
      baseUrl: 'http://127.0.0.1:8000',
      isMisconfigured: false,
      errorMessage: '',
    };
  }

  // 3. Production default fallback (shared with Android)
  return {
    baseUrl: DEFAULT_PRODUCTION_BACKEND,
    isMisconfigured: false,
    errorMessage: '',
  };
};

/**
 * Inspects URL query parameter (?backend=... or ?api=...) safely.
 * Returns the validated candidate URL IF approved, or null.
 * NEVER activates or persists candidate automatically.
 * Automatically cleans untrusted/malicious params from the URL bar to prevent phishing.
 */
export const getPendingProposedUrl = () => {
  if (typeof window === 'undefined' || !window.location || !window.location.search) {
    return null;
  }
  try {
    const params = new URLSearchParams(window.location.search);
    const candidate = params.get('backend') || params.get('api');
    if (!candidate) return null;

    const config = resolveApiConfig(candidate, {
      isDev: isDevelopment,
      isProd: isProduction,
    });

    if (config.isMisconfigured) {
      console.warn(`[Security] Untrusted backend URL parameter rejected: "${candidate}"`);
      dismissPendingProposedUrl();
      return null;
    }

    return config.baseUrl;
  } catch {
    return null;
  }
};

/**
 * Removes ?backend= or ?api= from the current window location without triggering a page reload.
 */
export const dismissPendingProposedUrl = () => {
  if (typeof window === 'undefined' || !window.location) return;
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete('backend');
    url.searchParams.delete('api');
    window.history.replaceState({}, '', url.pathname + url.search + url.hash);
  } catch {
    // ignore
  }
};

/**
 * User explicitly confirms connection to proposed URL.
 */
export const confirmProposedUrl = (url) => {
  dismissPendingProposedUrl();
  setRuntimeApiUrl(url);
};

export const getRuntimeApiUrl = () => {
  if (typeof window !== 'undefined') {
    // 1. Check window global override (e.g. config.js or injected script)
    if (window.__YATRA_API_URL__) {
      return window.__YATRA_API_URL__;
    }

    // 2. Check explicitly confirmed sessionStorage
    try {
      const stored = sessionStorage.getItem('yatra_runtime_api_url');
      if (stored) return stored;
    } catch {
      // ignore
    }
  }

  // 3. Fall back to Vite build-time environment variable
  return typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env.VITE_API_URL : '';
};

export const setRuntimeApiUrl = (url) => {
  if (typeof window !== 'undefined') {
    // Switching or resetting backends MUST clear any active authentication tokens
    // to strictly prevent cross-origin token leakage across distinct backends
    setAuthToken(null);

    if (url) {
      const config = resolveApiConfig(url, { isDev: isDevelopment, isProd: isProduction });
      if (config.isMisconfigured) {
        console.error(`[Security] Cannot activate invalid or unapproved backend URL: ${config.errorMessage}`);
        return false;
      }
      sessionStorage.setItem('yatra_runtime_api_url', config.baseUrl);
    } else {
      sessionStorage.removeItem('yatra_runtime_api_url');
    }
    window.location.reload();
    return true;
  }
  return false;
};

const rawApiUrl = getRuntimeApiUrl();
export const isDevelopment = Boolean(typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.DEV || import.meta.env.MODE === 'development'));
export const isProduction = Boolean(typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.PROD);

const { baseUrl: resolvedBaseUrl, isMisconfigured: isApiMisconfigured, errorMessage: configErrorMessage } = resolveApiConfig(rawApiUrl, {
  isDev: isDevelopment,
  isProd: isProduction,
});

if (isApiMisconfigured) {
  console.error(`[Yatra AI Configuration Error] ${configErrorMessage}`);
}

export const getApiBaseUrl = () => resolvedBaseUrl;
export const getApiConfigError = () => configErrorMessage;
export const isApiConfigured = () => !isApiMisconfigured;

const client = axios.create({
  baseURL: resolvedBaseUrl || undefined,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 45000, // 45s for LLM / tool chains
});

// Guard against unconfigured production API calls and foreign origin credential dispatch
client.interceptors.request.use((config) => {
  if (isApiMisconfigured) {
    return Promise.reject(new Error(configErrorMessage));
  }

  // Verify request origin matches approved baseUrl before sending credentials
  if (currentToken && config.headers && resolvedBaseUrl) {
    try {
      const targetUrl = new URL(config.url || '', resolvedBaseUrl);
      const baseOrigin = new URL(resolvedBaseUrl).origin;
      if (targetUrl.origin !== baseOrigin) {
        // Drop Authorization header if request targets a different origin
        delete config.headers['Authorization'];
      }
    } catch {
      delete config.headers['Authorization'];
    }
  }

  return config;
});

// Manage session token for cross-origin and cookie-partitioned requests
const TOKEN_KEY = 'yatra_auth_token';
let currentToken = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
if (currentToken) {
  client.defaults.headers.common['Authorization'] = `Bearer ${currentToken}`;
}

export const setAuthToken = (token) => {
  currentToken = token;
  if (token) {
    if (typeof window !== 'undefined') localStorage.setItem(TOKEN_KEY, token);
    client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    if (typeof window !== 'undefined') localStorage.removeItem(TOKEN_KEY);
    delete client.defaults.headers.common['Authorization'];
  }
};

export const getAuthToken = () => currentToken;

// Centralized API Functions
export const streamChat = async (messageData, { onStart, onToken, onDone, onError, signal } = {}) => {
  const payload = typeof messageData === 'string'
    ? { message: messageData }
    : {
        message: messageData.message,
        session_id: messageData.session_id || null,
        current_request: messageData.current_request || null,
        current_itinerary: messageData.current_itinerary || null,
        last_tourism_place: messageData.last_tourism_place || null,
        last_itinerary_context: messageData.last_itinerary_context || null,
        pending_options: messageData.pending_options || null,
      };

  if (isApiMisconfigured) {
    const misconfigErr = new Error(configErrorMessage || 'Backend API is misconfigured.');
    if (onError) onError(misconfigErr);
    throw misconfigErr;
  }

  const resolvedBase = getApiBaseUrl();
  const baseUrl = resolvedBase ? resolvedBase.replace(/\/+$/, '') : '';
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${baseUrl}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      throw new Error(`Streaming failed: HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalResponse = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.slice(5).trim();
        try {
          const event = JSON.parse(jsonStr);
          if (event.type === 'start') {
            if (onStart) onStart(event);
          } else if (event.type === 'token') {
            if (onToken) onToken(event.content);
          } else if (event.type === 'done') {
            finalResponse = event.response;
            if (onDone) onDone(event.response);
          }
        } catch {
          // Ignore partial chunks
        }
      }
    }

    return finalResponse;
  } catch (err) {
    if (onError) onError(err);
    throw err;
  }
};

export const sendChat = async (messageData) => {
  const payload = typeof messageData === 'string'
    ? { message: messageData }
    : {
        message: messageData.message,
        session_id: messageData.session_id || null,
        current_request: messageData.current_request || null,
        current_itinerary: messageData.current_itinerary || null,
        last_tourism_place: messageData.last_tourism_place || null,
        last_itinerary_context: messageData.last_itinerary_context || null,
        pending_options: messageData.pending_options || null,
      };

  const response = await client.post('/api/chat', payload);
  return response.data;
};

export const getChatHistory = async (sessionId) => {
  if (!sessionId) return { session_id: null, messages: [] };
  const response = await client.get(`/api/chat/history/${encodeURIComponent(sessionId)}`);
  return response.data;
};

export const searchYatra = async (searchData) => {
  const payload = typeof searchData === 'string'
    ? { message: searchData }
    : {
        message: searchData.message,
        session_id: searchData.session_id || null,
        current_request: searchData.current_request || null,
        current_itinerary: searchData.current_itinerary || null,
        last_itinerary_context: searchData.last_itinerary_context || null,
        pending_options: searchData.pending_options || null,
      };

  const response = await client.post('/api/yatra/', payload);
  return response.data;
};

export const getAccommodation = async (accommodationData) => {
  const payload = {
    check_in_date: accommodationData.check_in_date,
    category: accommodationData.category || null,
    min_rooms: accommodationData.min_rooms || 1,
  };

  const response = await client.post('/api/yatra/accommodation', payload);
  return response.data;
};

export const getSightseeing = async (category = null) => {
  const payload = {
    category: category || null,
  };

  const response = await client.post('/api/yatra/sightseeing', payload);
  return response.data;
};

export const generateItinerary = async (itineraryData) => {
  const payload = {
    option: itineraryData.option,
    hotel: itineraryData.hotel || null,
    hotel_nights: itineraryData.hotel_nights !== undefined ? itineraryData.hotel_nights : 2,
    sightseeing_places: itineraryData.sightseeing_places || [],
    request: itineraryData.request || null,
  };

  const response = await client.post('/api/yatra/itinerary', payload);
  return response.data;
};

export const confirmBooking = async (confirmData) => {
  const payload = {
    option: confirmData.option,
    pax: confirmData.pax || 1,
    user_name: confirmData.user_name || 'Guest-User',
    hotel: confirmData.hotel || null,
    hotel_nights: confirmData.hotel_nights !== undefined ? confirmData.hotel_nights : 2,
    sightseeing_places: confirmData.sightseeing_places || [],
    human_authorized: confirmData.human_authorized === true,
    session_id: confirmData.session_id || null,
    plan_version: confirmData.plan_version || null,
    pilgrims: confirmData.pilgrims || null,
    primary_contact: confirmData.primary_contact || null,
    hotel_selected: confirmData.hotel_selected !== undefined ? confirmData.hotel_selected : null,
    transport_selected: confirmData.transport_selected !== undefined ? confirmData.transport_selected : null,
    own_vehicle: confirmData.own_vehicle !== undefined ? confirmData.own_vehicle : null,
    start_date: confirmData.start_date || null,
    return_date: confirmData.return_date || null,
    duration: confirmData.duration || null,
    budget: confirmData.budget || null,
    accessibility_needs: confirmData.accessibility_needs || null,
  };

  const response = await client.post('/api/yatra/confirm', payload);
  return response.data;
};

export const runRPA = async (rpaData) => {
  const payload = {
    user_name: rpaData.user_name || 'Guest-User',
    pax_count: rpaData.pax_count || 1,
    transport_text: rpaData.transport_text,
    slot_text: rpaData.slot_text,
    total_price: parseFloat(rpaData.total_price || 0),
    headless: rpaData.headless !== false,
    session_id: rpaData.session_id || null,
    plan_version: rpaData.plan_version || null,
    human_authorized: rpaData.human_authorized === true,
  };

  const response = await client.post('/api/yatra/rpa', payload);
  return response.data;
};

export const getTourism = async (query, lastPlace = null) => {
  const response = await client.post('/api/tourism/', {
    query,
    last_tourism_place: lastPlace,
  });
  return response.data;
};

export const getWeather = async (location = 'Katra') => {
  const response = await client.post('/api/weather/', { location });
  return response.data;
};

export const authorizePlan = async (authData) => {
  const payload = {
    session_id: authData.session_id,
    plan_version: authData.plan_version,
    user_confirmation: authData.user_confirmation || 'Confirm booking',
  };

  const response = await client.post('/api/yatra/authorize', payload);
  return response.data;
};

export const checkHealth = async () => {
  const response = await client.get('/api/health');
  return response.data;
};

export const checkRPAAvailability = async (availabilityData = {}) => {
  const payload = {
    date: availabilityData.date || '2026-10-20',
    category: availabilityData.category || null,
    headless: availabilityData.headless !== false,
  };
  const response = await client.post('/api/yatra/rpa/availability', payload);
  return response.data;
};

// Week 8: User-Controlled Workflow API functions
export const startRPAWorkflow = async (workflowData) => {
  const payload = {
    session_id: workflowData.session_id,
    user_name: workflowData.user_name || 'Guest-Pilgrim',
    pax_count: workflowData.pax_count || 1,
    transport_text: workflowData.transport_text || 'Train',
    slot_text: workflowData.slot_text || 'Morning Darshan',
    total_price: parseFloat(workflowData.total_price || 0),
    checkpoint_mode: workflowData.checkpoint_mode || null,
    headless: workflowData.headless !== false,
    plan_version: workflowData.plan_version || null,
    human_authorized: workflowData.human_authorized === true,
  };
  const response = await client.post('/api/yatra/rpa/workflow/start', payload);
  return response.data;
};

export const getRPAWorkflowStatus = async (workflowId, sessionId) => {
  const response = await client.get(`/api/yatra/rpa/workflow/${encodeURIComponent(workflowId)}?session_id=${encodeURIComponent(sessionId)}`);
  return response.data;
};

export const resumeRPAWorkflow = async (resumeData) => {
  const payload = {
    session_id: resumeData.session_id,
    workflow_id: resumeData.workflow_id,
    user_confirmed_action: resumeData.user_confirmed_action === true,
    manual_input_value: resumeData.manual_input_value || null,
    simulate_manual_clearance: resumeData.simulate_manual_clearance === true,
    headless: resumeData.headless !== false,
  };
  const response = await client.post('/api/yatra/rpa/workflow/resume', payload);
  return response.data;
};

export const cancelRPAWorkflow = async (cancelData) => {
  const payload = {
    session_id: cancelData.session_id,
    workflow_id: cancelData.workflow_id,
    reason: cancelData.reason || 'Cancelled by user',
  };
  const response = await client.post('/api/yatra/rpa/workflow/cancel', payload);
  return response.data;
};

// ==============================================================================
// WEEK 9: OPTIONAL PASSWORDLESS EMAIL AUTHENTICATION & USER DATA APIs
// ==============================================================================

export const requestOtp = async (email) => {
  const response = await client.post('/api/auth/request-otp', { email });
  return response.data;
};

export const verifyOtp = async (email, otpCode) => {
  const response = await client.post('/api/auth/verify-otp', { email, otp_code: otpCode });
  if (response.data && response.data.session_token) {
    setAuthToken(response.data.session_token);
  }
  return response.data;
};

export const getAuthMe = async () => {
  const response = await client.get('/api/auth/me');
  return response.data;
};

export const logout = async () => {
  try {
    const response = await client.post('/api/auth/logout');
    return response.data;
  } finally {
    setAuthToken(null);
  }
};

export const saveItinerary = async (title, itinerary, itineraryId = null, sourceKey = null) => {
  const payload = { title, itinerary };
  if (itineraryId) payload.itinerary_id = itineraryId;
  if (sourceKey) payload.source_key = sourceKey;
  const response = await client.post('/api/auth/save-itinerary', payload);
  return response.data;
};

export const getSavedItineraries = async () => {
  const response = await client.get('/api/auth/saved-itineraries');
  return response.data;
};

export const deleteSavedItinerary = async (itineraryId) => {
  const response = await client.delete(`/api/auth/saved-itinerary/${encodeURIComponent(itineraryId)}`);
  return response.data;
};

// Phase 8.8.58: Smart Itinerary Management, Partial Editing & Group Collaboration APIs
export const listItineraries = async () => {
  const response = await client.get('/api/itineraries');
  return response.data;
};

export const upsertItinerary = async ({ title, itinerary, itineraryId = null, sourceKey = null, expectedRevision = null }) => {
  const payload = { title, itinerary };
  if (itineraryId) payload.itinerary_id = itineraryId;
  if (sourceKey) payload.source_key = sourceKey;
  if (expectedRevision !== null && expectedRevision !== undefined) payload.expected_revision = expectedRevision;
  const response = await client.post('/api/itineraries', payload);
  return response.data;
};

export const getItineraryDetail = async (itineraryId) => {
  const response = await client.get(`/api/itineraries/${encodeURIComponent(itineraryId)}`);
  return response.data;
};

export const deleteItineraryById = async (itineraryId) => {
  const response = await client.delete(`/api/itineraries/${encodeURIComponent(itineraryId)}`);
  return response.data;
};

export const previewItineraryEdit = async (itineraryId, editPayload) => {
  const response = await client.post(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/preview`, editPayload);
  return response.data;
};

export const applyItineraryEdit = async (itineraryId, editPayload) => {
  const response = await client.post(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/apply`, editPayload);
  return response.data;
};

export const undoItineraryEdit = async (itineraryId, expectedRevision = null) => {
  const response = await client.post(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/undo`, {
    expected_revision: expectedRevision,
  });
  return response.data;
};

export const createItineraryInvite = async (itineraryId, { role = 'VIEWER', expiresInHours = 72 } = {}) => {
  const response = await client.post(`/api/itineraries/${encodeURIComponent(itineraryId)}/shares`, {
    role,
    expires_in_hours: expiresInHours,
  });
  return response.data;
};

export const listItineraryShares = async (itineraryId) => {
  const response = await client.get(`/api/itineraries/${encodeURIComponent(itineraryId)}/shares`);
  return response.data;
};

export const updateItineraryMemberRole = async (itineraryId, memberUserId, role) => {
  const response = await client.patch(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/members/${encodeURIComponent(memberUserId)}`,
    { role }
  );
  return response.data;
};

export const revokeItineraryMember = async (itineraryId, memberUserId) => {
  const response = await client.delete(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/members/${encodeURIComponent(memberUserId)}`
  );
  return response.data;
};

export const revokeItineraryInvite = async (itineraryId, inviteId) => {
  const response = await client.delete(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/invites/${encodeURIComponent(inviteId)}`
  );
  return response.data;
};

export const acceptItineraryInvite = async (token) => {
  const response = await client.post('/api/itineraries/invites/accept', { token });
  return response.data;
};

export const getLocalGuestConversations = () => {
  try {
    const raw = localStorage.getItem('yatra_guest_conversations');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const saveLocalGuestConversation = (conv) => {
  try {
    if (!conv || !conv.conversation_id) return null;
    const list = getLocalGuestConversations();
    const idx = list.findIndex((c) => c.conversation_id === conv.conversation_id);
    const updated = {
      ...conv,
      updated_at: new Date().toISOString(),
      created_at: conv.created_at || (idx >= 0 ? list[idx].created_at : new Date().toISOString()),
    };
    if (idx >= 0) {
      list[idx] = updated;
    } else {
      list.unshift(updated);
    }
    localStorage.setItem('yatra_guest_conversations', JSON.stringify(list));
    return updated;
  } catch {
    return null;
  }
};

export const deleteLocalGuestConversation = (convId) => {
  try {
    const list = getLocalGuestConversations().filter((c) => c.conversation_id !== convId);
    localStorage.setItem('yatra_guest_conversations', JSON.stringify(list));
    return true;
  } catch {
    return false;
  }
};

export const clearLocalGuestConversations = () => {
  try {
    localStorage.removeItem('yatra_guest_conversations');
  } catch {}
};

export const saveConversation = async (title, messages, conversationId = null, tripRequest = null, itinerary = null) => {
  const payload = { title, messages };
  if (conversationId) payload.conversation_id = conversationId;
  if (tripRequest) payload.trip_request = tripRequest;
  if (itinerary) payload.itinerary = itinerary;
  const response = await client.post('/api/auth/save-conversation', payload);
  return response.data;
};

export const getSavedConversations = async () => {
  const response = await client.get('/api/auth/saved-conversations');
  return response.data;
};

export const getSavedConversation = async (conversationId) => {
  const response = await client.get(`/api/auth/saved-conversations/${encodeURIComponent(conversationId)}`);
  return response.data;
};

export const deleteSavedConversation = async (conversationId) => {
  const response = await client.delete(`/api/auth/saved-conversation/${encodeURIComponent(conversationId)}`);
  return response.data;
};

export const getSavedBookings = async () => {
  const response = await client.get('/api/auth/saved-bookings');
  return response.data;
};

export const getSavedBooking = async (bookingId) => {
  const response = await client.get(`/api/auth/saved-bookings/${encodeURIComponent(bookingId)}`);
  return response.data;
};

export const saveBooking = async (bookingData) => {
  const response = await client.post('/api/auth/save-booking', bookingData);
  return response.data;
};

export const transferConversation = async (sessionId, title = null) => {
  const response = await client.post('/api/auth/transfer-conversation', { session_id: sessionId, title });
  return response.data;
};

export const transferTrip = async (sessionId, title = null) => {
  const response = await client.post('/api/auth/transfer-trip', { session_id: sessionId, title });
  return response.data;
};

export const transferBooking = async (bookingId, sessionId = null) => {
  const response = await client.post('/api/auth/transfer-booking', { booking_id: bookingId, session_id: sessionId });
  return response.data;
};

export const getUserProfile = async () => {
  const response = await client.get('/api/auth/profile');
  return response.data;
};

/**
 * Downloads the authentic pilgrim pass PDF generated on the backend.
 * Returns Blob of application/pdf bytes.
 * Requires authenticated session token for non-test bookings.
 */
export const fetchBookingPdf = async (bookingId) => {
  if (!bookingId) {
    throw new Error('Missing booking_id for PDF download');
  }
  const cleanId = encodeURIComponent(String(bookingId).trim());
  const response = await client.get(`/api/yatra/booking/${cleanId}/pdf`, {
    responseType: 'blob',
    timeout: 15000,
  });
  return response.data;
};

export default {
  sendChat,
  streamChat,
  searchYatra,
  getAccommodation,
  getSightseeing,
  generateItinerary,
  authorizePlan,
  confirmBooking,
  runRPA,
  checkRPAAvailability,
  startRPAWorkflow,
  getRPAWorkflowStatus,
  resumeRPAWorkflow,
  cancelRPAWorkflow,
  getTourism,
  getWeather,
  checkHealth,
  requestOtp,
  verifyOtp,
  getAuthMe,
  logout,
  saveItinerary,
  getSavedItineraries,
  deleteSavedItinerary,
  listItineraries,
  upsertItinerary,
  getItineraryDetail,
  deleteItineraryById,
  previewItineraryEdit,
  applyItineraryEdit,
  undoItineraryEdit,
  createItineraryInvite,
  listItineraryShares,
  updateItineraryMemberRole,
  revokeItineraryMember,
  revokeItineraryInvite,
  acceptItineraryInvite,
  saveConversation,
  getSavedConversations,
  getSavedConversation,
  deleteSavedConversation,
  getLocalGuestConversations,
  saveLocalGuestConversation,
  deleteLocalGuestConversation,
  clearLocalGuestConversations,
  getSavedBookings,
  getSavedBooking,
  saveBooking,
  transferConversation,
  transferTrip,
  transferBooking,
  getUserProfile,
  fetchBookingPdf,
  setAuthToken,
  getAuthToken,
};

