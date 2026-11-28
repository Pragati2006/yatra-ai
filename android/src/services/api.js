/**
 * Centralized REST API Service for Yatra AI Android
 * Reuses identical contracts and payloads as FastAPI backend.
 * Integrates SecureStore token persistence and strict host policy.
 */

import Constants from 'expo-constants';
import { validateBackendUrl } from '../utils/urlValidator.js';
import {
  getAuthToken,
  saveAuthToken,
  clearAuthToken,
  getStoredBackendUrl,
  setStoredBackendUrl,
} from '../utils/storage';
import { CURATED_FLIGHTS, filterAndSortFlights } from '../utils/flightCatalog.js';

const STATIC_CATALOG_TTL_MS = 10 * 60 * 1000; // 10 minutes
const WEATHER_CACHE_TTL_MS = 5 * 60 * 1000;   // 5 minutes
const HISTORY_CACHE_TTL_MS = 45 * 1000;       // 45 seconds (user-scoped)

const responseCache = new Map();
const inFlightRequests = new Map();

const getCachedEntry = (key, ttlMs) => {
  const entry = responseCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > ttlMs) {
    responseCache.delete(key);
    return null;
  }
  return entry.data;
};

const setCachedEntry = (key, data) => {
  responseCache.set(key, { data, timestamp: Date.now() });
  return data;
};

const dedupedFetch = (key, fetcher) => {
  if (inFlightRequests.has(key)) {
    return inFlightRequests.get(key);
  }
  const promise = Promise.resolve()
    .then(fetcher)
    .finally(() => {
      if (inFlightRequests.get(key) === promise) {
        inFlightRequests.delete(key);
      }
    });
  inFlightRequests.set(key, promise);
  return promise;
};

export const clearUserSessionCaches = () => {
  for (const key of Array.from(responseCache.keys())) {
    if (key.startsWith('history:')) {
      responseCache.delete(key);
    }
  }
  for (const key of Array.from(inFlightRequests.keys())) {
    if (key.startsWith('history:')) {
      inFlightRequests.delete(key);
    }
  }
};

export const clearCatalogCaches = () => {
  responseCache.clear();
  inFlightRequests.clear();
};

// Production Render Cloud Backend
export const DEFAULT_PRODUCTION_BACKEND = 'https://yatra-ai-smap.onrender.com';
// Default development endpoint for Android Emulator
export const DEFAULT_EMULATOR_BACKEND = 'http://10.0.2.2:8000';
export const DEFAULT_LOCALHOST_BACKEND = 'http://127.0.0.1:8000';

export const getInitialDefaultBackend = () => {
  // 1. Check EXPO_PUBLIC_API_URL from environment (Expo build-time or runtime)
  if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.trim().replace(/\/+$/, '');
  }
  // 2. Check app.json / eas.json extra config
  const extraApiUrl = Constants?.expoConfig?.extra?.apiUrl;
  if (extraApiUrl && typeof extraApiUrl === 'string') {
    return extraApiUrl.trim().replace(/\/+$/, '');
  }
  // 3. In production mode (standalone APK / release bundle), default to live Render backend
  if (typeof __DEV__ !== 'undefined' && !__DEV__) {
    return DEFAULT_PRODUCTION_BACKEND;
  }
  // 4. Default for local emulator development
  return DEFAULT_EMULATOR_BACKEND;
};

let activeBaseUrl = getInitialDefaultBackend();
let isConfiguredState = false;
let configErrorState = '';

/**
 * Initializes API configuration from persistent device storage
 */
export const initApiConfig = async () => {
  try {
    const stored = await getStoredBackendUrl();
    if (stored) {
      const validation = validateBackendUrl(stored, { isDev: true });
      if (validation.isValid) {
        activeBaseUrl = validation.baseUrl;
        isConfiguredState = true;
        configErrorState = '';
        return { ok: true, baseUrl: activeBaseUrl };
      }
    }
    const defaultUrl = getInitialDefaultBackend();
    activeBaseUrl = defaultUrl;
    isConfiguredState = true;
    configErrorState = '';
    return { ok: true, baseUrl: activeBaseUrl };
  } catch (err) {
    const defaultUrl = getInitialDefaultBackend();
    activeBaseUrl = defaultUrl;
    isConfiguredState = false;
    configErrorState = err.message;
    return { ok: false, error: err.message };
  }
};

/**
 * Updates the backend URL and safely clears previous tokens to prevent leakage
 */
export const setBackendUrl = async (newUrl) => {
  const validation = validateBackendUrl(newUrl, { isDev: true });
  if (!validation.isValid) {
    return { ok: false, error: validation.error };
  }

  // Security Gate: Changing backend MUST clear active tokens and cached data to prevent leakage
  await clearAuthToken();
  clearCatalogCaches();

  activeBaseUrl = validation.baseUrl;
  await setStoredBackendUrl(validation.baseUrl);
  isConfiguredState = true;
  configErrorState = '';

  return { ok: true, baseUrl: activeBaseUrl };
};

export const getBackendUrl = () => activeBaseUrl;
export const isApiConfigured = () => isConfiguredState;
export const getApiConfigError = () => configErrorState;

// Screen Naming Aliases
export const getRuntimeApiUrl = async () => {
  const stored = await getStoredBackendUrl();
  return stored || activeBaseUrl;
};

export const setRuntimeApiUrl = async (url) => {
  const res = await setBackendUrl(url);
  return res.ok;
};

export const getStoredAuthToken = getAuthToken;

/**
 * Core HTTP Request Dispatcher
 */
async function request(endpoint, options = {}) {
  const {
    method = 'GET',
    body = null,
    headers = {},
    timeoutMs = 15000,
    requiresAuth = false,
    overrideBaseUrl = null,
  } = options;

  let cleanBase = (overrideBaseUrl || activeBaseUrl || getInitialDefaultBackend()).trim().replace(/\/+$/, '');
  if (cleanBase.endsWith('/api') && endpoint.startsWith('/api/')) {
    cleanBase = cleanBase.slice(0, -4);
  }
  const url = `${cleanBase}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const requestHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Client-Platform': 'android-react-native',
    ...headers,
  };

  // Attach session token securely if present
  const token = await getAuthToken();
  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  } else if (requiresAuth) {
    clearTimeout(timeoutId);
    throw new Error('Authentication required for this operation.');
  }

  const fetchOptions = {
    method,
    headers: requestHeaders,
    signal: controller.signal,
  };

  if (body && (method === 'POST' || method === 'PUT' || method === 'DELETE')) {
    fetchOptions.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, fetchOptions);
    clearTimeout(timeoutId);

    const contentType = response.headers.get('content-type') || '';
    let responseData = null;
    if (contentType.includes('application/json')) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    if (!response.ok) {
      const errorMsg =
        (responseData && (responseData.detail || responseData.message || responseData.error)) ||
        `HTTP Error ${response.status}: ${response.statusText}`;
      const err = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      err.status = response.status;
      err.data = responseData;
      throw err;
    }

    return responseData;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s. Check backend connectivity.`);
    }
    throw error;
  }
}

// ==============================================================================
// 1. HEALTH & CONNECTIVITY
// ==============================================================================

export const checkHealth = async (overrideUrl = null) => {
  return request('/api/health', { timeoutMs: 12000, overrideBaseUrl: overrideUrl });
};

export const checkReadiness = async (overrideUrl = null) => {
  return request('/api/health/ready', { timeoutMs: 15000, overrideBaseUrl: overrideUrl });
};

export const checkBackendHealth = async (urlToTest = null) => {
  const start = Date.now();
  const targetUrl = urlToTest || activeBaseUrl;
  const cleanTarget = targetUrl.trim().replace(/\/+$/, '');
  try {
    const data = await checkHealth(cleanTarget);
    const latencyMs = Date.now() - start;
    return { ok: true, data, latencyMs };
  } catch (err) {
    // If /api/health timed out or failed on a waking Render server, attempt readiness probe
    try {
      const readyData = await checkReadiness(cleanTarget);
      const latencyMs = Date.now() - start;
      return { ok: true, data: readyData, latencyMs };
    } catch {
      const latencyMs = Date.now() - start;
      return { ok: false, error: err.message, latencyMs };
    }
  }
};

// ==============================================================================
// 2. CONVERSATIONAL AI AGENT
// ==============================================================================

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

  return request('/api/chat', {
    method: 'POST',
    body: payload,
    timeoutMs: 45000, // 45s for LLM orchestration
  });
};

export const sendChatMessage = async (text, sessionId = null) => {
  const res = await sendChat({ message: text, session_id: sessionId });
  if (!res) {
    return {
      response: 'Jai Mata Di',
      session_id: sessionId,
      status: 'ERROR',
    };
  }
  return {
    ...res,
    response: res.response || res.reply || res.message || (typeof res === 'string' ? res : 'Jai Mata Di'),
    session_id: res.session_id || sessionId,
    status: res.status,
    request: res.request || res.requirements,
    plan: res.plan,
    itinerary: res.itinerary,
    recommendation: res.recommendation,
    destination_images: res.destination_images || null,
    matched_destination: res.matched_destination || null,
  };
};

export const getChatHistory = async (sessionId) => {
  if (!sessionId) return { session_id: null, messages: [] };
  return request(`/api/chat/history/${encodeURIComponent(sessionId)}`);
};

export const getCachedChatHistory = async (sessionId = null) => {
  const token = (await getAuthToken()) || 'anon';
  const cacheKey = `history:${activeBaseUrl}:${token.slice(-12)}:${sessionId || 'list'}`;
  return getCachedEntry(cacheKey, HISTORY_CACHE_TTL_MS);
};

export const fetchChatHistory = async (sessionId = null, { forceRefresh = false } = {}) => {
  const token = (await getAuthToken()) || 'anon';
  const cacheKey = `history:${activeBaseUrl}:${token.slice(-12)}:${sessionId || 'list'}`;

  if (!forceRefresh) {
    const cached = getCachedEntry(cacheKey, HISTORY_CACHE_TTL_MS);
    if (cached !== null) return cached;
  }

  return dedupedFetch(cacheKey, async () => {
    try {
      const data = sessionId
        ? await getChatHistory(sessionId)
        : await request('/api/auth/saved-conversations', { timeoutMs: 12000 });
      return setCachedEntry(cacheKey, data);
    } catch (e) {
      return [];
    }
  });
};

// ==============================================================================
// 3. TOURISM & DESTINATIONS
// ==============================================================================

export const getTourism = async (query, lastPlace = null) => {
  return request('/api/tourism/', {
    method: 'POST',
    body: {
      query,
      last_tourism_place: lastPlace,
    },
  });
};

export const getSightseeing = async (category = null) => {
  return request('/api/yatra/sightseeing', {
    method: 'POST',
    timeoutMs: 12000,
    body: { category: category || null },
  });
};

export const getCachedTourismSpots = () => {
  return getCachedEntry(`tourismSpots:${activeBaseUrl}`, STATIC_CATALOG_TTL_MS);
};

export const fetchTourismSpots = async ({ forceRefresh = false } = {}) => {
  const cacheKey = `tourismSpots:${activeBaseUrl}`;
  if (!forceRefresh) {
    const cached = getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS);
    if (cached) return cached;
  }

  return dedupedFetch(cacheKey, async () => {
    try {
      const res = await getSightseeing();
      const places = Array.isArray(res)
        ? res
        : res?.places && Array.isArray(res.places)
        ? res.places
        : null;
      if (places && places.length > 0) {
        return setCachedEntry(cacheKey, places);
      }
      return [];
    } catch (e) {
      return getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS) || [];
    }
  });
};

// ==============================================================================
// 4. WEATHER INTEGRATION
// ==============================================================================

export const getWeather = async (location = 'Katra') => {
  return request('/api/weather/', {
    method: 'POST',
    timeoutMs: 12000,
    body: { location },
  });
};

export const getCachedWeather = (location = 'katra') => {
  const key = `weather:${activeBaseUrl}:${String(location || 'katra').trim().toLowerCase()}`;
  return getCachedEntry(key, WEATHER_CACHE_TTL_MS);
};

export const fetchWeather = async (location = 'katra', { forceRefresh = false } = {}) => {
  const normLoc = String(location || 'katra').trim().toLowerCase();
  const cacheKey = `weather:${activeBaseUrl}:${normLoc}`;
  if (!forceRefresh) {
    const cached = getCachedEntry(cacheKey, WEATHER_CACHE_TTL_MS);
    if (cached) return cached;
  }

  return dedupedFetch(cacheKey, async () => {
    try {
      const res = await getWeather(location);
      if (res) {
        return setCachedEntry(cacheKey, res);
      }
      return null;
    } catch (e) {
      return getCachedEntry(cacheKey, WEATHER_CACHE_TTL_MS) || null;
    }
  });
};

// ==============================================================================
// 5. ACCOMMODATION CATALOGUE
// ==============================================================================

export const getAccommodation = async (accommodationData = {}) => {
  return request('/api/yatra/accommodation', {
    method: 'POST',
    timeoutMs: 12000,
    body: {
      check_in_date: accommodationData.check_in_date || '2026-10-20',
      category: accommodationData.category || null,
      min_rooms: accommodationData.min_rooms || 1,
    },
  });
};

export const getCachedAccommodations = () => {
  return getCachedEntry(`accommodations:${activeBaseUrl}`, STATIC_CATALOG_TTL_MS);
};

export const fetchAccommodations = async ({ forceRefresh = false } = {}) => {
  const cacheKey = `accommodations:${activeBaseUrl}`;
  if (!forceRefresh) {
    const cached = getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS);
    if (cached) return cached;
  }

  return dedupedFetch(cacheKey, async () => {
    try {
      const res = await getAccommodation();
      const items = Array.isArray(res)
        ? res
        : res?.accommodations && Array.isArray(res.accommodations)
        ? res.accommodations
        : null;
      if (items && items.length > 0) {
        return setCachedEntry(cacheKey, items);
      }
      return [];
    } catch (e) {
      return getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS) || [];
    }
  });
};

// ==============================================================================
// 6. TRANSPORT GUIDANCE
// ==============================================================================

export const searchYatra = async (searchData) => {
  const payload = typeof searchData === 'string'
    ? { message: searchData }
    : {
        message: searchData.message,
        session_id: searchData.session_id || null,
      };

  return request('/api/yatra/', {
    method: 'POST',
    body: payload,
  });
};

export const getCachedTransportOptions = (origin = '', destination = '', travelDate = '') => {
  const cacheKey = `transport:${activeBaseUrl}:${origin}:${destination}:${travelDate}`;
  return getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS);
};

export const fetchTransportOptions = async ({
  origin = '',
  destination = '',
  travelDate = '',
  stopsFilter = 'all',
  sortBy = 'price_asc',
  forceRefresh = false,
} = {}) => {
  const cacheKey = `transport:${activeBaseUrl}:${origin}:${destination}:${travelDate}:${stopsFilter}:${sortBy}`;
  if (!forceRefresh) {
    const cached = getCachedEntry(cacheKey, STATIC_CATALOG_TTL_MS);
    if (cached) return cached;
  }

  return dedupedFetch(cacheKey, async () => {
    const curatedMatches = filterAndSortFlights(CURATED_FLIGHTS, {
      origin,
      destination,
      travelDate,
      stopsFilter,
      sortBy,
    });
    return setCachedEntry(cacheKey, curatedMatches);
  });
};

// ==============================================================================
// 7. ITINERARY & GUIDED BOOKING
// ==============================================================================

export const generateItinerary = async (itineraryData) => {
  return request('/api/yatra/itinerary', {
    method: 'POST',
    body: {
      option: itineraryData.option,
      hotel: itineraryData.hotel || null,
      hotel_nights: itineraryData.hotel_nights !== undefined ? itineraryData.hotel_nights : 2,
      sightseeing_places: itineraryData.sightseeing_places || [],
      request: itineraryData.request || null,
    },
  });
};

export const authorizePlan = async (authData) => {
  return request('/api/yatra/authorize', {
    method: 'POST',
    body: {
      session_id: authData.session_id || `session-${Date.now()}`,
      plan_version: authData.plan_version || 1,
      user_confirmation: authData.user_confirmation || 'Confirm booking',
    },
  });
};

export const authorizeBooking = authorizePlan;

export const confirmBooking = async (confirmData) => {
  return request('/api/yatra/confirm', {
    method: 'POST',
    body: {
      option: confirmData.option || 1,
      pax: confirmData.pax || confirmData.devoteeCount || 1,
      user_name: confirmData.user_name || confirmData.fullName || 'Guest-Pilgrim',
      hotel: confirmData.hotel || null,
      hotel_nights: confirmData.hotel_nights !== undefined ? confirmData.hotel_nights : 2,
      sightseeing_places: confirmData.sightseeing_places || [],
      human_authorized: confirmData.human_authorized === true || confirmData.authorized === true,
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
    },
  });
};

export const runRPA = async (rpaData) => {
  return request('/api/yatra/rpa', {
    method: 'POST',
    body: {
      user_name: rpaData.user_name || rpaData.fullName || 'Guest-Pilgrim',
      pax_count: rpaData.pax_count || rpaData.devoteeCount || 1,
      transport_text: rpaData.transport_text || rpaData.transportMode || 'Traditional Trek',
      slot_text: rpaData.slot_text || rpaData.slot || 'Morning',
      total_price: parseFloat(rpaData.total_price || 0),
      headless: true,
      session_id: rpaData.session_id || null,
      plan_version: rpaData.plan_version || null,
      human_authorized: rpaData.human_authorized === true || rpaData.authorized === true,
    },
  });
};

export const triggerRpaBooking = runRPA;

// ==============================================================================
// 8. AUTHENTICATION & USER DATA
// ==============================================================================

export const requestOtp = async (email) => {
  return request('/api/auth/request-otp', {
    method: 'POST',
    body: { email },
  });
};

export const verifyOtp = async (email, otpCode) => {
  const res = await request('/api/auth/verify-otp', {
    method: 'POST',
    body: { email, otp_code: otpCode },
  });

  if (res && res.session_token) {
    clearUserSessionCaches();
    await saveAuthToken(res.session_token);
  }
  return res;
};

export const getAuthMe = async () => {
  return request('/api/auth/me');
};

export const logout = async () => {
  try {
    await request('/api/auth/logout', { method: 'POST' });
  } finally {
    clearUserSessionCaches();
    await clearAuthToken();
  }
};

export const logoutUser = logout;

export const getSavedItineraries = async () => {
  return request('/api/auth/saved-itineraries');
};

export const saveItinerary = async (title, itinerary, itineraryId = null, sourceKey = null) => {
  clearUserSessionCaches();
  const body = { title, itinerary };
  if (itineraryId) body.itinerary_id = itineraryId;
  if (sourceKey) body.source_key = sourceKey;
  return request('/api/auth/save-itinerary', {
    method: 'POST',
    body,
  });
};

// Phase 8.8.58: Smart Itinerary Management, Partial Editing & Group Collaboration
export const listItineraries = async () => {
  return request('/api/itineraries', { timeoutMs: 12000 });
};

export const upsertItinerary = async ({ title, itinerary, itineraryId = null, sourceKey = null, expectedRevision = null }) => {
  clearUserSessionCaches();
  const body = { title, itinerary };
  if (itineraryId) body.itinerary_id = itineraryId;
  if (sourceKey) body.source_key = sourceKey;
  if (expectedRevision !== null && expectedRevision !== undefined) body.expected_revision = expectedRevision;
  return request('/api/itineraries', {
    method: 'POST',
    body,
  });
};

export const getItineraryDetail = async (itineraryId) => {
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}`, { timeoutMs: 12000 });
};

export const deleteItineraryById = async (itineraryId) => {
  clearUserSessionCaches();
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}`, {
    method: 'DELETE',
  });
};

export const previewItineraryEdit = async (itineraryId, editPayload) => {
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/preview`, {
    method: 'POST',
    body: editPayload,
  });
};

export const applyItineraryEdit = async (itineraryId, editPayload) => {
  clearUserSessionCaches();
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/apply`, {
    method: 'POST',
    body: editPayload,
  });
};

export const undoItineraryEdit = async (itineraryId, expectedRevision = null) => {
  clearUserSessionCaches();
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}/edit/undo`, {
    method: 'POST',
    body: { expected_revision: expectedRevision },
  });
};

export const createItineraryInvite = async (itineraryId, { role = 'VIEWER', expiresInHours = 72 } = {}) => {
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}/shares`, {
    method: 'POST',
    body: { role, expires_in_hours: expiresInHours },
  });
};

export const listItineraryShares = async (itineraryId) => {
  return request(`/api/itineraries/${encodeURIComponent(itineraryId)}/shares`);
};

export const updateItineraryMemberRole = async (itineraryId, memberUserId, role) => {
  return request(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/members/${encodeURIComponent(memberUserId)}`,
    { method: 'PATCH', body: { role } }
  );
};

export const revokeItineraryMember = async (itineraryId, memberUserId) => {
  return request(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/members/${encodeURIComponent(memberUserId)}`,
    { method: 'DELETE' }
  );
};

export const revokeItineraryInvite = async (itineraryId, inviteId) => {
  return request(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/shares/invites/${encodeURIComponent(inviteId)}`,
    { method: 'DELETE' }
  );
};

export const acceptItineraryInvite = async (token) => {
  clearUserSessionCaches();
  return request('/api/itineraries/invites/accept', {
    method: 'POST',
    body: { token },
  });
};

export const getSavedConversations = async () => {
  return request('/api/auth/saved-conversations');
};

export const getSavedConversation = async (conversationId) => {
  if (!conversationId) return null;
  return request(`/api/auth/saved-conversations/${encodeURIComponent(conversationId)}`);
};

export const saveConversation = async (title, messages, conversation_id = null, trip_request = null, itinerary = null) => {
  clearUserSessionCaches();
  const body = { title, messages };
  if (conversation_id) body.conversation_id = conversation_id;
  if (trip_request) body.trip_request = trip_request;
  if (itinerary) body.itinerary = itinerary;
  return request('/api/auth/save-conversation', {
    method: 'POST',
    body,
  });
};

export const getSavedBookings = async () => {
  return request('/api/auth/saved-bookings');
};

export const saveBooking = async (bookingData) => {
  return request('/api/auth/save-booking', {
    method: 'POST',
    body: bookingData,
  });
};

export default {
  initApiConfig,
  setBackendUrl,
  getBackendUrl,
  isApiConfigured,
  getApiConfigError,
  getRuntimeApiUrl,
  setRuntimeApiUrl,
  getStoredAuthToken,
  checkHealth,
  checkReadiness,
  checkBackendHealth,
  sendChat,
  sendChatMessage,
  getChatHistory,
  getCachedChatHistory,
  fetchChatHistory,
  getTourism,
  getSightseeing,
  getCachedTourismSpots,
  fetchTourismSpots,
  getWeather,
  getCachedWeather,
  fetchWeather,
  getAccommodation,
  getCachedAccommodations,
  fetchAccommodations,
  searchYatra,
  getCachedTransportOptions,
  fetchTransportOptions,
  clearUserSessionCaches,
  clearCatalogCaches,
  generateItinerary,
  authorizePlan,
  authorizeBooking,
  confirmBooking,
  runRPA,
  triggerRpaBooking,
  requestOtp,
  verifyOtp,
  getAuthMe,
  logout,
  logoutUser,
  getSavedItineraries,
  saveItinerary,
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
  getSavedConversations,
  getSavedConversation,
  saveConversation,
  getSavedBookings,
  saveBooking,
};
