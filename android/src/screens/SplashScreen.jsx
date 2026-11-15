import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  StatusBar,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import YatraLogo from '../components/YatraLogo';

export default function SplashScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primaryDark} />
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
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
    backgroundColor: colors.primaryDark,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xxl * 1.5,
    paddingBottom: spacing.xl,
    alignItems: 'center',
    justifyContent: 'space-between',
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
    color: colors.goldLight,
    marginTop: spacing.sm,
    letterSpacing: 2,
    textAlign: 'center',
  },
  appTagline: {
    fontSize: 15,
    fontWeight: '500',
    color: colors.surface,
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
    backgroundColor: 'rgba(212, 175, 55, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(212, 175, 55, 0.3)',
  },
  shrineName: {
    fontSize: 11,
    color: colors.goldLight,
    letterSpacing: 1.8,
    fontWeight: '700',
    textAlign: 'center',
  },
  introText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.85)',
    textAlign: 'center',
    lineHeight: 22,
    marginTop: spacing.sm,
    maxWidth: 300,
  },
  ctaSection: {
    width: '100%',
    maxWidth: 340,
    gap: spacing.md,
    marginTop: spacing.xxl,
    marginBottom: spacing.xl,
  },
  primaryBtn: {
    backgroundColor: colors.gold,
    paddingVertical: 15,
    borderRadius: spacing.radiusFull,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 4,
  },
  primaryBtnText: {
    color: colors.primaryDark,
    fontSize: 15.5,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  secondaryBtn: {
    backgroundColor: 'transparent',
    paddingVertical: 14,
    borderRadius: spacing.radiusFull,
    borderWidth: 1.5,
    borderColor: colors.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryBtnText: {
    color: colors.goldLight,
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
    fontSize: 10.5,
    color: 'rgba(255, 255, 255, 0.55)',
    textAlign: 'center',
    lineHeight: 15,
  },
});
