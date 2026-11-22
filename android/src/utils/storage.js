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
 * Local chat conversation cache
 */
export const getLocalChatMessages = async () => {
  try {
    const data = await AsyncStorage.getItem(CHAT_HISTORY_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
};

export const saveLocalChatMessages = async (messages) => {
  try {
    if (Array.isArray(messages)) {
      await AsyncStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages));
    }
  } catch {
    // ignore
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
 */
export const getLocalGuestConversations = async () => {
  try {
    const raw = await AsyncStorage.getItem(GUEST_CONVERSATIONS_KEY);
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
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const saveLocalGuestConversation = async (conv) => {
  if (!conv || !conv.conversation_id) return;
  try {
    const list = await getLocalGuestConversations();
    const idx = list.findIndex((c) => c.conversation_id === conv.conversation_id);
    const entry = {
      ...conv,
      updated_at: new Date().toISOString(),
    };
    if (idx >= 0) {
      list[idx] = entry;
    } else {
      list.unshift(entry);
    }
    // Limit to 25 local sessions
    const capped = list.slice(0, 25);
    await AsyncStorage.setItem(GUEST_CONVERSATIONS_KEY, JSON.stringify(capped));
    // Also keep legacy single session active
    if (conv.messages) {
      await saveLocalChatMessages(conv.messages);
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
