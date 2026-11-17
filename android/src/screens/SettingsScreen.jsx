import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import ConnectionModal from '../components/ConnectionModal';
import {
  SettingsIcon,
  UserIcon,
  ShieldIcon,
  GlobeIcon,
  MicIcon,
  InfoIcon,
  RefreshIcon,
  TrashIcon,
  CheckIcon,
} from '../components/Icons';
import {
  getRuntimeApiUrl,
  checkBackendHealth,
  logoutUser,
  getStoredAuthToken,
} from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getStoredUser, clearAllStorage } from '../utils/storage';

export default function SettingsScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [backendUrl, setBackendUrl] = useState('');
  const [healthStatus, setHealthStatus] = useState(null);
  const [checking, setChecking] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [hasAuthToken, setHasAuthToken] = useState(false);
  const [user, setUser] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState('English');
  const [voiceLanguage, setVoiceLanguage] = useState('English (IN)');

  useEffect(() => {
    loadSettings();
    AsyncStorage.getItem('yatra_app_lang').then((val) => {
      if (val) setSelectedLanguage(val);
    }).catch(() => {});
    AsyncStorage.getItem('yatra_voice_lang').then((val) => {
      if (val) setVoiceLanguage(val);
    }).catch(() => {});
  }, []);

  const handleSelectLanguage = (lang) => {
    setSelectedLanguage(lang);
    AsyncStorage.setItem('yatra_app_lang', lang).catch(() => {});
  };

  const handleSelectVoiceLanguage = (v) => {
    setVoiceLanguage(v);
    AsyncStorage.setItem('yatra_voice_lang', v).catch(() => {});
  };

  const loadSettings = async () => {
    const url = await getRuntimeApiUrl();
    setBackendUrl(url);
    const token = await getStoredAuthToken();
    setHasAuthToken(!!token);
    const u = await getStoredUser();
    if (u) setUser(u);
    runHealthTest(url);
  };

  const runHealthTest = async (urlToTest) => {
    setChecking(true);
    try {
      const res = await checkBackendHealth(urlToTest || backendUrl);
      setHealthStatus(res);
    } catch (e) {
      setHealthStatus({ ok: false, error: e.message });
    } finally {
      setChecking(false);
    }
  };

  const handleLogout = async () => {
    Alert.alert(
      'Sign Out Devotee',
      'Are you sure you want to sign out from your Yatra AI session?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: async () => {
            await logoutUser();
            setHasAuthToken(false);
            setUser(null);
            Alert.alert('Signed Out', 'You have been signed out. Returned to guest mode.');
          },
        },
      ]
    );
  };

  const handleClearCache = async () => {
    Alert.alert(
      'Clear Application Storage',
      'This will erase saved auth tokens, cached messages, and reset settings to default.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All Data',
          style: 'destructive',
          onPress: async () => {
            await logoutUser();
            await clearAllStorage();
            setHasAuthToken(false);
            setUser(null);
            Alert.alert('Data Cleared', 'All local cached data has been cleared.');
            loadSettings();
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <Header
        title="Settings & System"
        subtitle="Account, Preferences & Security"
      />

      <ScrollView
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: Math.max(insets.bottom, spacing.xxl) + 16 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* A & B: ACCOUNT & AUTHENTICATION */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <UserIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>Account & Authentication</Text>
          </View>
          <Text style={styles.sectionSubtitle}>
            Manage your devotee session credentials and cloud sync.
          </Text>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Account Status:</Text>
            <Text style={styles.infoValue}>
              {hasAuthToken ? 'Authenticated Devotee' : 'Guest Mode (No Token)'}
            </Text>
          </View>

          {user && (
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Registered User:</Text>
              <Text style={styles.infoValue}>{user.email || user.name || 'Devotee'}</Text>
            </View>
          )}

          {hasAuthToken ? (
            <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout} activeOpacity={0.8}>
              <Text style={styles.logoutBtnText}>Sign Out Devotee</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={styles.authActionBtn}
              onPress={() => navigation.navigate('Auth')}
              activeOpacity={0.8}
            >
              <Text style={styles.authActionBtnText}>Sign In with Email OTP</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* C & D: PREFERENCES */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <GlobeIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>Language & Display</Text>
          </View>
          <Text style={styles.sectionSubtitle}>
            Interface presentation and regional settings.
          </Text>

          <View style={styles.preferenceRow}>
            <Text style={styles.infoLabel}>App Language:</Text>
            <View style={styles.pillRow}>
              {['English', 'Hindi', 'Punjabi', 'Urdu'].map((lang) => (
                <TouchableOpacity
                  key={lang}
                  style={[styles.smallPill, selectedLanguage === lang && styles.smallPillActive]}
                  onPress={() => handleSelectLanguage(lang)}
                >
                  <Text
                    style={[styles.smallPillText, selectedLanguage === lang && styles.smallPillTextActive]}
                  >
                    {lang}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={[styles.infoRow, { marginTop: spacing.sm }]}>
            <Text style={styles.infoLabel}>Visual Theme:</Text>
            <Text style={styles.infoValue}>Sacred Burgundy & Warm Ivory</Text>
          </View>
        </View>

        {/* E: VOICE SETTINGS */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <MicIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>Voice Input Settings</Text>
          </View>
          <Text style={styles.sectionSubtitle}>
            Speech typing configuration and platform audio capabilities.
          </Text>

          <View style={styles.preferenceRow}>
            <Text style={styles.infoLabel}>Voice Language:</Text>
            <View style={styles.pillRow}>
              {['English (IN)', 'Hindi', 'Punjabi', 'Urdu'].map((v) => (
                <TouchableOpacity
                  key={v}
                  style={[styles.smallPill, voiceLanguage === v && styles.smallPillActive]}
                  onPress={() => handleSelectVoiceLanguage(v)}
                >
                  <Text
                    style={[styles.smallPillText, voiceLanguage === v && styles.smallPillTextActive]}
                  >
                    {v}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.platformNoticeBox}>
            <Text style={styles.platformNoticeText}>
              Platform Speech Engine: In Expo Go, voice input is powered by your Android system keyboard (Gboard / Samsung Voice Typing) with offline language packs.
            </Text>
          </View>
        </View>

        {/* F: BACKEND CONNECTIVITY */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <SettingsIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>Backend Connectivity</Text>
          </View>
          <Text style={styles.sectionSubtitle}>
            FastAPI endpoint configuration and live health monitoring.
          </Text>

          <View style={styles.urlBox}>
            <Text style={styles.urlLabel}>ACTIVE BACKEND URL:</Text>
            <Text style={styles.urlValue} numberOfLines={1}>
              {backendUrl || 'Loading...'}
            </Text>
          </View>

          <View style={styles.statusRow}>
            <View
              style={[
                styles.statusPill,
                healthStatus?.ok ? styles.statusPillSuccess : styles.statusPillError,
              ]}
            >
              <Text
                style={[
                  styles.statusPillText,
                  healthStatus?.ok ? styles.statusTextSuccess : styles.statusTextError,
                ]}
              >
                {healthStatus?.ok
                  ? `ONLINE (${healthStatus.latencyMs}ms)`
                  : 'OFFLINE / UNREACHABLE'}
              </Text>
            </View>

            <TouchableOpacity
              style={styles.checkBtn}
              onPress={() => runHealthTest(backendUrl)}
              disabled={checking}
              activeOpacity={0.7}
            >
              {checking ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <View style={styles.btnInnerRow}>
                  <RefreshIcon size={12} color={colors.primary} />
                  <Text style={styles.checkBtnText}>Ping</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.configureBtn}
            onPress={() => setModalVisible(true)}
            activeOpacity={0.8}
          >
            <Text style={styles.configureBtnText}>Configure Backend & Tunnel</Text>
          </TouchableOpacity>
        </View>

        {/* G: PRIVACY & DATA MANAGEMENT */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <ShieldIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>Privacy & Storage</Text>
          </View>
          <Text style={styles.sectionSubtitle}>
            Device keystore encryption and local storage isolation.
          </Text>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Token Storage:</Text>
            <Text style={styles.infoValue}>Expo.SecureStore (Encrypted)</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Host Policy:</Text>
            <Text style={styles.infoValue}>10.0.2.2 / *.trycloudflare.com</Text>
          </View>

          <TouchableOpacity style={styles.dangerBtn} onPress={handleClearCache} activeOpacity={0.8}>
            <TrashIcon size={14} color="#C0392B" />
            <Text style={styles.dangerBtnText}>Clear Storage & Reset Tokens</Text>
          </TouchableOpacity>
        </View>

        {/* H: ABOUT YATRA AI */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeaderRow}>
            <InfoIcon size={18} color={colors.primary} />
            <Text style={styles.sectionHeader}>About Yatra AI</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Application:</Text>
            <Text style={styles.infoValue}>Yatra AI — Maa Vaishno Devi Edition</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Version:</Text>
            <Text style={styles.infoValue}>1.0.0 (Phase 16.1 UI/UX Refinement)</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Client Engine:</Text>
            <Text style={styles.infoValue}>React Native 0.88.1 / Expo SDK 58</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>AI LLM:</Text>
            <Text style={styles.infoValue}>Groq / LLaMA / LangChain Agent</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Project Nature:</Text>
            <Text style={styles.infoValue}>Minor Project • Academic Development</Text>
          </View>
        </View>

        <View style={styles.footerNotice}>
          <Text style={styles.footerNoticeText}>
            Yatra AI — Dedicated to Devotees of Shri Mata Vaishno Devi{'\n'}
            Official parchi bookings must be confirmed via maavaishnodevi.org.
          </Text>
        </View>
      </ScrollView>

      <ConnectionModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onConnected={(newUrl) => {
          setBackendUrl(newUrl);
          runHealthTest(newUrl);
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: spacing.md,
    gap: spacing.md,
    paddingBottom: spacing.xxl,
  },
  sectionCard: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusMd,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  sectionHeader: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.primary,
  },
  sectionSubtitle: {
    fontSize: 11.5,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  urlBox: {
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.sm,
    borderRadius: spacing.radiusSm,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
    marginBottom: spacing.sm,
  },
  urlLabel: {
    fontSize: 9.5,
    fontWeight: '700',
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
  urlValue: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginTop: 2,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  statusPill: {
    flex: 1,
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
  },
  statusPillSuccess: {
    backgroundColor: '#ECFDF5',
    borderWidth: 1,
    borderColor: '#10B981',
  },
  statusPillError: {
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  statusPillText: {
    fontSize: 11,
    fontWeight: '700',
  },
  statusTextSuccess: {
    color: '#065F46',
  },
  statusTextError: {
    color: '#991B1B',
  },
  checkBtn: {
    paddingVertical: 6,
    paddingHorizontal: spacing.md,
    borderRadius: spacing.radiusSm,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnInnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  checkBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
  },
  configureBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 10,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
  },
  configureBtnText: {
    color: colors.goldLight,
    fontSize: 12.5,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 0.5,
    borderBottomColor: colors.borderLight,
  },
  infoLabel: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  infoValue: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  preferenceRow: {
    marginVertical: 4,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 6,
  },
  smallPill: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
    backgroundColor: colors.bgSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  smallPillActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  smallPillText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  smallPillTextActive: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  platformNoticeBox: {
    backgroundColor: colors.bgSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: spacing.radiusSm,
    padding: spacing.sm,
    marginTop: spacing.sm,
  },
  platformNoticeText: {
    fontSize: 10.5,
    color: colors.textSecondary,
    lineHeight: 15,
  },
  authActionBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 10,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  authActionBtnText: {
    color: '#FFFFFF',
    fontSize: 12.5,
    fontWeight: '700',
  },
  logoutBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#C0392B',
    paddingVertical: 8,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  logoutBtnText: {
    color: '#C0392B',
    fontSize: 12,
    fontWeight: '700',
  },
  dangerBtn: {
    backgroundColor: '#FFF0F0',
    borderWidth: 1,
    borderColor: '#C0392B',
    paddingVertical: 10,
    borderRadius: spacing.radiusSm,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.md,
    flexDirection: 'row',
    gap: 6,
  },
  dangerBtnText: {
    color: '#C0392B',
    fontSize: 12,
    fontWeight: '700',
  },
  footerNotice: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  footerNoticeText: {
    fontSize: 10.5,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 15,
  },
});
