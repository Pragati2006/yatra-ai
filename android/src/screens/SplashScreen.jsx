import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  StatusBar,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import YatraLogo from '../components/YatraLogo';

export default function SplashScreen({ navigation }) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <ScrollView
        contentContainerStyle={[
          styles.scrollContent,
          {
            paddingTop: Math.max(insets.top, spacing.lg),
            paddingBottom: Math.max(insets.bottom, spacing.lg),
          },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Brand Hero Header */}
        <View style={styles.heroSection}>
          <View style={styles.logoWrapper}>
            <YatraLogo size={96} showGlow={true} />
          </View>
          <Text style={styles.appName}>Yatra AI</Text>
          <Text style={styles.appTagline}>
            Unified Pilgrimage & Tourism Assistant
          </Text>
          <View style={styles.editionPill}>
            <Text style={styles.shrineName}>
              MAA VAISHNO DEVI YATRA EDITION
            </Text>
          </View>
          <Text style={styles.introText}>
            Your intelligent companion for a smoother pilgrimage journey.
          </Text>
        </View>

        {/* Action Controls */}
        <View style={styles.ctaSection}>
          <TouchableOpacity
            style={styles.primaryBtn}
            onPress={() => navigation.replace('MainTabs')}
            activeOpacity={0.85}
            accessibilityRole="button"
            accessibilityLabel="Begin Your Journey"
          >
            <Text style={styles.primaryBtnText}>Begin Your Journey</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={() => navigation.navigate('Auth')}
            activeOpacity={0.75}
            accessibilityRole="button"
            accessibilityLabel="Sign In or Devotee Login"
          >
            <Text style={styles.secondaryBtnText}>Sign In / Devotee Login</Text>
          </TouchableOpacity>
        </View>

        {/* Subtle Official Disclaimer */}
        <View style={styles.disclaimerContainer}>
          <Text style={styles.disclaimerText}>
            Dedicated to devotees of Shri Mata Vaishno Devi. Official parchi bookings must be confirmed via maavaishnodevi.org.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroSection: {
    alignItems: 'center',
    width: '100%',
    maxWidth: 380,
    marginTop: spacing.md,
  },
  logoWrapper: {
    marginBottom: spacing.md,
  },
  appName: {
    fontSize: 34,
    fontWeight: '800',
    color: colors.burgundy,
    marginTop: spacing.sm,
    letterSpacing: 2,
    textAlign: 'center',
  },
  appTagline: {
    fontSize: 15.5,
    fontWeight: '600',
    color: colors.textSecondary,
    marginTop: 6,
    textAlign: 'center',
    letterSpacing: 0.3,
  },
  editionPill: {
    marginTop: spacing.md,
    marginBottom: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 5,
    borderRadius: spacing.radiusFull,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  shrineName: {
    fontSize: 11,
    color: colors.goldDark,
    letterSpacing: 1.8,
    fontWeight: '800',
    textAlign: 'center',
  },
  introText: {
    fontSize: 14.5,
    color: colors.textPrimary,
    textAlign: 'center',
    lineHeight: 22,
    marginTop: spacing.sm,
    maxWidth: 300,
  },
  ctaSection: {
    width: '100%',
    maxWidth: 340,
    gap: spacing.md,
    marginTop: spacing.lg,
    marginBottom: spacing.md,
  },
  primaryBtn: {
    backgroundColor: colors.burgundy,
    paddingVertical: 15,
    borderRadius: spacing.radiusFull,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.burgundy,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 4,
  },
  primaryBtnText: {
    color: colors.textWhite,
    fontSize: 15.5,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  secondaryBtn: {
    backgroundColor: 'transparent',
    paddingVertical: 14,
    borderRadius: spacing.radiusFull,
    borderWidth: 1.5,
    borderColor: colors.burgundy,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryBtnText: {
    color: colors.burgundy,
    fontSize: 14.5,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  disclaimerContainer: {
    paddingHorizontal: spacing.md,
    maxWidth: 340,
    marginTop: spacing.sm,
  },
  disclaimerText: {
    fontSize: 11,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 16,
  },
});
