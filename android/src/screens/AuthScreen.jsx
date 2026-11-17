import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import YatraLogo from '../components/YatraLogo';
import {
  requestOtp,
  verifyOtp,
  logoutUser,
  getStoredAuthToken,
  saveConversation,
} from '../services/api';
import {
  getStoredUser,
  setStoredUser,
  removeStoredUser,
  getLocalChatMessages,
  clearLocalChatMessages,
} from '../utils/storage';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function AuthScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState('email'); // 'email' | 'otp' | 'authenticated'
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    checkCurrentAuth();
  }, []);

  useEffect(() => {
    let timer;
    if (cooldown > 0) {
      timer = setInterval(() => {
        setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const checkCurrentAuth = async () => {
    const token = await getStoredAuthToken();
    const user = await getStoredUser();
    if (token && user) {
      setCurrentUser(user);
      setStep('authenticated');
    }
  };

  const handleSendOtp = async (isResend = false) => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@') || !EMAIL_REGEX.test(cleanEmail)) {
      Alert.alert('Invalid Email', 'Please enter a valid email address (e.g., devotee@example.com).');
      return;
    }

    if (isResend && cooldown > 0) {
      Alert.alert('Please Wait', `You can request another verification code in ${cooldown} seconds.`);
      return;
    }

    setLoading(true);
    try {
      const res = await requestOtp(cleanEmail);
      setStep('otp');
      setCooldown(res?.cooldown_seconds || 60);
      Alert.alert(
        'Verification Code Sent',
        `A 6-digit verification code has been dispatched to ${cleanEmail}. Please check your inbox and spam folder.`
      );
    } catch (err) {
      const errMsg =
        err?.data?.detail?.message ||
        err?.data?.message ||
        err?.message ||
        'Unable to send verification code. Please verify your email address and check backend connectivity.';
      Alert.alert('Request Failed', errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    const cleanEmail = email.trim().toLowerCase();
    const cleanOtp = otp.trim();

    if (!cleanOtp || cleanOtp.length !== 6 || !/^\d+$/.test(cleanOtp)) {
      Alert.alert('Invalid Code', 'Please enter the 6-digit numeric verification code.');
      return;
    }

    setLoading(true);
    try {
      const res = await verifyOtp(cleanEmail, cleanOtp);

      const userProfile = {
        email: res?.user?.email || cleanEmail,
        user_id: res?.user?.user_id,
        role: 'Devotee Pilgrim (Verified)',
        authenticatedAt: new Date().toISOString(),
      };
      await setStoredUser(userProfile);
      setCurrentUser(userProfile);

      // Non-blocking guest conversation migration to MongoDB Atlas / Cloud
      try {
        const localMsgs = await getLocalChatMessages();
        if (localMsgs && localMsgs.length > 1) {
          const firstUser = localMsgs.find((m) => m.role === 'user');
          const title = firstUser?.content ? firstUser.content.slice(0, 45) : 'Pilgrimage Consultation';
          await saveConversation(title, localMsgs);
          await clearLocalChatMessages();
        }
      } catch {
        // non-blocking guest migration
      }

      setStep('authenticated');
      Alert.alert('Welcome Devotee', 'You are now verified and signed in to Yatra AI.');
    } catch (err) {
      const errMsg =
        err?.data?.detail?.message ||
        err?.data?.message ||
        err?.message ||
        'Incorrect or expired verification code. Please check the code and try again.';
      Alert.alert('Verification Failed', errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    Alert.alert('Confirm Sign Out', 'Are you sure you want to sign out from your Yatra AI session?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await logoutUser();
          await removeStoredUser();
          setCurrentUser(null);
          setStep('email');
          setEmail('');
          setOtp('');
          setCooldown(0);
        },
      },
    ]);
  };

  const handleGuestContinue = () => {
    navigation.replace('MainTabs');
  };

  const handleChangeEmail = () => {
    setStep('email');
    setOtp('');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior="padding"
    >
      <Header
        title="Devotee Authentication"
        subtitle="Passwordless Email Verification"
        showBack={true}
        onBackPress={() => navigation.goBack()}
      />

      <ScrollView
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: Math.max(insets.bottom, spacing.xl) },
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.brandingSection}>
          <YatraLogo size={64} />
          <Text style={styles.brandingTitle}>Shri Mata Vaishno Devi</Text>
          <Text style={styles.brandingSubtitle}>
            Devotee Identity & Verification
          </Text>
        </View>

        {step === 'authenticated' ? (
          <View style={styles.profileCard}>
            <Text style={styles.profileBadge}>Verified Devotee</Text>
            <Text style={styles.profileEmail}>{currentUser?.email || 'devotee@example.com'}</Text>
            <Text style={styles.profileRole}>{currentUser?.role || 'Pilgrim Devotee'}</Text>
            <Text style={styles.profileDate}>
              Signed in: {new Date(currentUser?.authenticatedAt || Date.now()).toLocaleDateString()}
            </Text>

            <View style={styles.profileActions}>
              <TouchableOpacity
                style={styles.continueBtn}
                onPress={() => navigation.replace('MainTabs')}
              >
                <Text style={styles.continueBtnText}>Proceed to Yatra AI →</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.logoutBtn}
                onPress={handleLogout}
              >
                <Text style={styles.logoutBtnText}>Sign Out</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.formCard}>
            {step === 'email' ? (
              <>
                <Text style={styles.formTitle}>Devotee Email Login</Text>
                <Text style={styles.formSubtitle}>
                  Enter your email address to receive a secure 6-digit verification code. No password or phone number required.
                </Text>

                <View style={styles.inputContainer}>
                  <TextInput
                    style={styles.emailInput}
                    value={email}
                    onChangeText={setEmail}
                    placeholder="devotee@example.com"
                    placeholderTextColor={colors.textLight}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoCorrect={false}
                    editable={!loading}
                  />
                </View>

                <TouchableOpacity
                  style={[styles.submitBtn, (loading || !email.trim()) && styles.btnDisabled]}
                  onPress={() => handleSendOtp(false)}
                  disabled={loading || !email.trim()}
                >
                  {loading ? (
                    <ActivityIndicator size="small" color={colors.surface} />
                  ) : (
                    <Text style={styles.submitBtnText}>Send Verification Code →</Text>
                  )}
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.formTitle}>Enter Verification Code</Text>
                <Text style={styles.formSubtitle}>
                  Enter the 6-digit verification code sent to {email.trim().toLowerCase()}
                </Text>

                <TextInput
                  style={styles.otpInput}
                  value={otp}
                  onChangeText={setOtp}
                  placeholder="• • • • • •"
                  placeholderTextColor={colors.textLight}
                  keyboardType="number-pad"
                  maxLength={6}
                  textAlign="center"
                  editable={!loading}
                />

                <TouchableOpacity
                  style={[styles.submitBtn, (loading || otp.trim().length !== 6) && styles.btnDisabled]}
                  onPress={handleVerifyOtp}
                  disabled={loading || otp.trim().length !== 6}
                >
                  {loading ? (
                    <ActivityIndicator size="small" color={colors.surface} />
                  ) : (
                    <Text style={styles.submitBtnText}>Verify & Enter Yatra AI →</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.resendBtn}
                  onPress={() => handleSendOtp(true)}
                  disabled={loading || cooldown > 0}
                >
                  <Text style={[styles.resendBtnText, cooldown > 0 && styles.resendBtnDisabled]}>
                    {cooldown > 0 ? `Resend Code (${cooldown}s)` : 'Resend Verification Code'}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.backToEmailBtn}
                  onPress={handleChangeEmail}
                  disabled={loading}
                >
                  <Text style={styles.backToEmailText}>← Change Email Address</Text>
                </TouchableOpacity>
              </>
            )}

            <View style={styles.divider}>
              <View style={styles.dividerLine} />
              <Text style={styles.dividerText}>OR</Text>
              <View style={styles.dividerLine} />
            </View>

            <TouchableOpacity
              style={styles.guestBtn}
              onPress={handleGuestContinue}
            >
              <Text style={styles.guestBtnText}>Continue as Guest Devotee</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.securityFooter}>
          <Text style={styles.securityText}>
            Authentication tokens are encrypted using device-level hardware keystore (Expo.SecureStore).
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: spacing.lg,
    alignItems: 'center',
  },
  brandingSection: {
    alignItems: 'center',
    marginVertical: spacing.md,
  },
  brandingTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.primary,
    marginTop: spacing.sm,
  },
  brandingSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  formCard: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusLg,
    padding: spacing.lg,
    width: '100%',
    ...spacing.shadowMd,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  formTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.text,
    marginBottom: 4,
  },
  formSubtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: spacing.md,
    lineHeight: 18,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: spacing.radiusMd,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    backgroundColor: colors.surfaceSecondary,
  },
  emailInput: {
    flex: 1,
    height: 48,
    fontSize: 15,
    color: colors.text,
  },
  otpInput: {
    height: 52,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: spacing.radiusMd,
    fontSize: 24,
    letterSpacing: 10,
    backgroundColor: colors.surfaceSecondary,
    color: colors.primary,
    fontWeight: '700',
    marginBottom: spacing.md,
  },
  submitBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
    ...spacing.shadowSm,
  },
  submitBtnText: {
    color: colors.surface,
    fontSize: 15,
    fontWeight: '700',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  resendBtn: {
    marginTop: spacing.sm,
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  resendBtnText: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: '600',
  },
  resendBtnDisabled: {
    color: colors.textMuted,
  },
  backToEmailBtn: {
    marginTop: spacing.xs,
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  backToEmailText: {
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: spacing.md,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.borderLight,
  },
  dividerText: {
    marginHorizontal: spacing.sm,
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: '700',
  },
  guestBtn: {
    borderWidth: 1.5,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldSubtle,
    paddingVertical: 12,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  guestBtnText: {
    color: colors.primary,
    fontSize: 13.5,
    fontWeight: '700',
  },
  profileCard: {
    backgroundColor: colors.surface,
    borderRadius: spacing.radiusLg,
    padding: spacing.lg,
    width: '100%',
    alignItems: 'center',
    ...spacing.shadowMd,
  },
  profileBadge: {
    backgroundColor: '#DEF7EC',
    color: '#03543F',
    fontWeight: '700',
    fontSize: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: spacing.radiusSm,
    marginBottom: spacing.sm,
  },
  profileEmail: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.primary,
    marginBottom: 4,
  },
  profileRole: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  profileDate: {
    fontSize: 11,
    color: colors.textSecondary,
    marginBottom: spacing.lg,
  },
  profileActions: {
    width: '100%',
    gap: spacing.sm,
  },
  continueBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  continueBtnText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '700',
  },
  logoutBtn: {
    borderWidth: 1,
    borderColor: colors.error,
    paddingVertical: 10,
    borderRadius: spacing.radiusMd,
    alignItems: 'center',
  },
  logoutBtnText: {
    color: colors.error,
    fontSize: 13,
    fontWeight: '600',
  },
  securityFooter: {
    marginTop: spacing.xl,
    paddingHorizontal: spacing.md,
  },
  securityText: {
    fontSize: 11.5,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 16,
  },
});
