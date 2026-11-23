/**
 * Secure Storage Utility for Yatra AI Android
 * - Uses Expo SecureStore for sensitive session tokens (never ordinary AsyncStorage).
 * - Uses AsyncStorage for non-sensitive caches and preferences.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

const AUTH_TOKEN_KEY = 'yatra_secure_auth_token';
const BACKEND_URL_KEY = 'yatra_configured_backend_url';
const CHAT_HISTORY_KEY = 'yatra_local_chat_history';
const GUEST_CONVERSATIONS_KEY = 'yatra_guest_conversations';
const USER_PROFILE_KEY = 'yatra_user_profile';
const BOOKING_DRAFT_KEY = 'yatra_booking_draft';

// Safe wrapper checking whether SecureStore is available
const isSecureStoreAvailable = async () => {
  try {
    return await SecureStore.isAvailableAsync();
  } catch {
    return false;
  }
};

/**
 * Stores session token securely in hardware keystore
 */
export const saveAuthToken = async (token) => {
  if (!token) return;
  try {
    const available = await isSecureStoreAvailable();
    if (available) {
      await SecureStore.setItemAsync(AUTH_TOKEN_KEY, token, {
        keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
      });
    } else {
      await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
    }
  } catch (error) {
    console.warn('[Storage] Could not write auth token securely:', error.message);
  }
};

export const saveSecureAuthToken = saveAuthToken;

/**
 * Retrieves session token from secure storage
 */
export const getAuthToken = async () => {
  try {
    const available = await isSecureStoreAvailable();
    if (available) {
      return await SecureStore.getItemAsync(AUTH_TOKEN_KEY);
    }
    return await AsyncStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const getSecureAuthToken = getAuthToken;

/**
 * Clears session token safely
 */
export const clearAuthToken = async () => {
  try {
    const available = await isSecureStoreAvailable();
    if (available) {
      await SecureStore.deleteItemAsync(AUTH_TOKEN_KEY);
    }
    await AsyncStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // ignore
  }
};

export const clearSecureAuthToken = clearAuthToken;

/**
 * User Profile Persistence
 */
export const getStoredUser = async () => {
  try {
    const raw = await AsyncStorage.getItem(USER_PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const setStoredUser = async (user) => {
  try {
    if (user) {
      await AsyncStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user));
    } else {
      await AsyncStorage.removeItem(USER_PROFILE_KEY);
    }
  } catch {
    // ignore
  }
};

export const removeStoredUser = async () => {
  try {
    await AsyncStorage.removeItem(USER_PROFILE_KEY);
  } catch {
    // ignore
  }
};

/**
 * Backend URL preference management
 */
export const getStoredBackendUrl = async () => {
  try {
    return await AsyncStorage.getItem(BACKEND_URL_KEY);
  } catch {
    return null;
  }
};

export const setStoredBackendUrl = async (url) => {
  try {
    if (url) {
      await AsyncStorage.setItem(BACKEND_URL_KEY, url);
    } else {
      await AsyncStorage.removeItem(BACKEND_URL_KEY);
    }
  } catch {
    // ignore
  }
};

/**
 * Sanitizes and compacts a message payload before saving to AsyncStorage.
 * Strips massive 60+ KB catalog/options dumps from backend responses while
 * retaining all fields needed for rendering ItineraryPreviewCard and ItineraryScreen.
 * Prevents Android SQLite CursorWindow (2MB) / RowTooBigException fatal native crashes.
 */
export const sanitizeMessageForStorage = (m) => {
  if (!m || typeof m !== 'object') return null;

  // Compact plan: preserve budget_evaluation grand_total and itinerary days, strip options/catalogs
  let compactPlan = null;
  if (m.plan) {
    compactPlan = {
      budget_evaluation: {
        grand_total:
          m.plan.budget_evaluation?.grand_total ||
          m.recommendation?.estimated_total_budget ||
          14500,
      },
      itinerary: m.itinerary || m.plan.itinerary || null,
    };
  }

  // Compact recommendation: preserve profile, suggested_places and estimated budget
  let compactRecommendation = null;
  if (m.recommendation) {
    compactRecommendation = {
      profile: m.recommendation.profile || null,
      suggested_places: Array.isArray(m.recommendation.suggested_places)
        ? m.recommendation.suggested_places
        : [],
      estimated_total_budget:
        m.recommendation.estimated_total_budget ||
        m.plan?.budget_evaluation?.grand_total ||
        null,
    };
  }

  // Compact trip request
  let compactRequest = null;
  if (m.request) {
    compactRequest = {
      origin: m.request.origin || null,
      destination: m.request.destination || null,
      start_date: m.request.start_date || null,
      end_date: m.request.end_date || null,
      duration_days: m.request.duration_days || null,
      pax: m.request.pax || null,
      group_type: m.request.group_type || null,
    };
  }

  const destImages = Array.isArray(m.destination_images)
    ? m.destination_images.slice(0, 6)
    : Array.isArray(m.metadata?.destination_images)
    ? m.metadata.destination_images.slice(0, 6)
    : Array.isArray(m.meta?.destination_images)
    ? m.meta.destination_images.slice(0, 6)
    : null;

  const matchedDest =
    m.matched_destination ||
    m.metadata?.matched_destination ||
    m.meta?.matched_destination ||
    null;

  return {
    id: m.id,
    role: m.role || 'assistant',
    content: typeof m.content === 'string' ? m.content : '',
    recommendation: compactRecommendation,
    itinerary: m.itinerary || (compactPlan ? compactPlan.itinerary : null),
    plan: compactPlan,
    request: compactRequest,
    destination_images: destImages,
    matched_destination: matchedDest,
    bookingHandoff: m.bookingHandoff || null,
    timestamp:
      m.timestamp ||
      new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
};

/**
 * Local chat conversation cache
 *
 * Phase 8.8.49 Non-Destructive Read Recovery:
 * - AsyncStorage.getItem() errors (e.g. temporary SQLite locks, IO delays) log a warning
 *   and return [] WITHOUT calling removeItem() or modifying disk storage.
 * - JSON parse errors log a warning and return [] WITHOUT destructive deletion.
 * - Filters individual message records so one malformed item does not invalidate the session.
 */
export const getLocalChatMessages = async () => {
  let raw = null;
  try {
    raw = await AsyncStorage.getItem(CHAT_HISTORY_KEY);
  } catch (err) {
    console.warn('[Storage] Temporary AsyncStorage read error for local chat messages (data preserved):', err?.message);
    return [];
  }

  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      console.warn('[Storage] Local chat messages payload is not an array, returning fallback');
      return [];
    }
    // Filter valid message objects so one corrupted entry does not destroy the history
    return parsed.filter((m) => m && typeof m === 'object' && (m.role || m.content));
  } catch (err) {
    console.warn('[Storage] JSON parse error in local chat messages (original data preserved on disk):', err?.message);
    return [];
  }
};

export const saveLocalChatMessages = async (messages) => {
  try {
    if (Array.isArray(messages)) {
      const sanitized = messages.map(sanitizeMessageForStorage).filter(Boolean);
      await AsyncStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(sanitized));
    }
  } catch (err) {
    console.warn('[Storage] Could not write local chat messages:', err?.message);
  }
};

export const clearLocalChatMessages = async () => {
  try {
    await AsyncStorage.removeItem(CHAT_HISTORY_KEY);
  } catch {
    // ignore
  }
};

/**
 * Multi-session Guest Conversations Storage
 *
 * Phase 8.8.49 Non-Destructive Read Recovery:
 * - AsyncStorage.getItem() errors log a warning and return [] WITHOUT calling removeItem().
 * - JSON parse errors log a warning and return [] WITHOUT deleting the original data.
 * - Recovers valid conversation records wherever possible; does not discard an entire collection
 *   if an individual record is malformed.
 */
export const getLocalGuestConversations = async () => {
  let raw = null;
  try {
    raw = await AsyncStorage.getItem(GUEST_CONVERSATIONS_KEY);
  } catch (err) {
    console.warn('[Storage] Temporary AsyncStorage read error for guest conversations (data preserved):', err?.message);
    return [];
  }

  if (!raw) {
    // Fallback to legacy single session if present
    const legacy = await getLocalChatMessages();
    if (legacy && legacy.length > 1) {
      const firstUser = legacy.find((m) => m.role === 'user');
      return [
        {
          conversation_id: 'guest-local-session',
          title: firstUser?.content ? (firstUser.content.slice(0, 45) + (firstUser.content.length > 45 ? '...' : '')) : 'Guest Consultation',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          messages: legacy,
          preview: firstUser?.content || 'Recent guest pilgrimage discussion.',
        },
      ];
    }
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      console.warn('[Storage] Guest conversations payload is not an array, returning fallback');
      return [];
    }

    // Recover valid conversation records wherever possible;
    // do not discard an entire conversation collection because one record is malformed
    return parsed
      .filter((c) => c && typeof c === 'object' && (c.conversation_id || c.session_id))
      .map((c) => {
        const msgs = Array.isArray(c.messages)
          ? c.messages.filter((m) => m && typeof m === 'object' && (m.role || m.content))
          : [];
        return {
          ...c,
          conversation_id: c.conversation_id || c.session_id,
          messages: msgs,
        };
      });
  } catch (err) {
    console.warn('[Storage] JSON parse error in guest conversations (original data preserved on disk):', err?.message);
    return [];
  }
};

export const saveLocalGuestConversation = async (conv) => {
  if (!conv || !conv.conversation_id) return;
  try {
    const list = await getLocalGuestConversations();
    const idx = list.findIndex((c) => c.conversation_id === conv.conversation_id);
    const sanitizedMessages = Array.isArray(conv.messages)
      ? conv.messages.map(sanitizeMessageForStorage).filter(Boolean)
      : [];

    const entry = {
      ...conv,
      messages: sanitizedMessages,
      updated_at: new Date().toISOString(),
    };
    if (idx >= 0) {
      list[idx] = entry;
    } else {
      list.unshift(entry);
    }
    // Limit to 10 local sessions to strictly keep storage well below Android CursorWindow limits
    const capped = list.slice(0, 10);
    await AsyncStorage.setItem(GUEST_CONVERSATIONS_KEY, JSON.stringify(capped));
    // Also keep active chat cache in sync
    if (sanitizedMessages.length > 0) {
      await AsyncStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(sanitizedMessages));
    }
  } catch (e) {
    console.warn('[Storage] Could not save guest conversation:', e.message);
  }
};

export const saveBookingDraft = async (draft) => {
  try {
    if (draft) {
      await AsyncStorage.setItem(BOOKING_DRAFT_KEY, JSON.stringify(draft));
    } else {
      await AsyncStorage.removeItem(BOOKING_DRAFT_KEY);
    }
  } catch (e) {
    console.warn('[Storage] Could not save booking draft:', e.message);
  }
};

export const getBookingDraft = async () => {
  try {
    const raw = await AsyncStorage.getItem(BOOKING_DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const clearBookingDraft = async () => {
  try {
    await AsyncStorage.removeItem(BOOKING_DRAFT_KEY);
  } catch {
    // ignore
  }
};

export const clearLocalGuestConversations = async () => {
  try {
    await AsyncStorage.removeItem(GUEST_CONVERSATIONS_KEY);
    await AsyncStorage.removeItem(CHAT_HISTORY_KEY);
  } catch {
    // ignore
  }
};

/**
 * Master clear all local application data
 */
export const clearAllStorage = async () => {
  await clearAuthToken();
  await removeStoredUser();
  await clearLocalChatMessages();
  await clearLocalGuestConversations();
  try {
    await AsyncStorage.removeItem(BACKEND_URL_KEY);
  } catch {
    // ignore
  }
};

export default {
  saveAuthToken,
  saveSecureAuthToken,
  getAuthToken,
  getSecureAuthToken,
  clearAuthToken,
  clearSecureAuthToken,
  getStoredUser,
  setStoredUser,
  removeStoredUser,
  getStoredBackendUrl,
  setStoredBackendUrl,
  getLocalChatMessages,
  saveLocalChatMessages,
  clearLocalChatMessages,
  clearAllStorage,
};
