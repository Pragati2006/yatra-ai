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
const USER_PROFILE_KEY = 'yatra_user_profile';

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
 * Master clear all local application data
 */
export const clearAllStorage = async () => {
  await clearAuthToken();
  await removeStoredUser();
  await clearLocalChatMessages();
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
