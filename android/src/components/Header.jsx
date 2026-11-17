import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, StatusBar } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import YatraLogo from './YatraLogo';
import { ClockIcon, SettingsIcon } from './Icons';

export default function Header({
  title = 'YATRA AI',
  subtitle = 'Vaishno Devi Pilgrimage Assistant',
  isConnected = true,
  onOpenSettings,
  onSettingsPress,
  onOpenHistory,
  onOpenAuth,
  onNewChatPress,
  showBack = false,
  onBackPress,
  user = null,
}) {
  const insets = useSafeAreaInsets();
  const handleSettings = onOpenSettings || onSettingsPress;
  const topPadding = Math.max(insets.top, 8) + 4;

  return (
    <View style={[styles.container, { paddingTop: topPadding }]}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <View style={styles.topRow}>
        {showBack && onBackPress && (
          <TouchableOpacity
            style={styles.backButton}
            onPress={onBackPress}
            accessibilityLabel="Go back"
            activeOpacity={0.7}
          >
            <Text style={styles.backButtonText}>←</Text>
          </TouchableOpacity>
        )}

        <View style={styles.brandRow}>
          <YatraLogo size={32} />
          <View style={styles.titleContainer}>
            <View style={styles.titleRow}>
              <Text style={styles.title} numberOfLines={1}>{title}</Text>
              <View style={[styles.statusDot, { backgroundColor: isConnected ? colors.success : colors.danger }]} />
            </View>
            <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
          </View>
        </View>

        <View style={styles.actionsRow}>
          {onNewChatPress && (
            <TouchableOpacity
              style={styles.newChatButton}
              onPress={onNewChatPress}
              accessibilityLabel="Start fresh chat"
            >
              <Text style={styles.newChatText}>+ New</Text>
            </TouchableOpacity>
          )}

          {onOpenHistory && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={onOpenHistory}
              accessibilityLabel="Conversation history"
            >
              <ClockIcon size={16} color={colors.goldLight} strokeWidth={2.2} />
            </TouchableOpacity>
          )}

          {onOpenAuth && (
            <TouchableOpacity
              style={styles.authButton}
              onPress={onOpenAuth}
              accessibilityLabel="User account"
            >
              <Text style={styles.authButtonText}>
                {user ? (user.phone || user.email || 'Devotee').slice(0, 7) : 'Devotee'}
              </Text>
            </TouchableOpacity>
          )}

          {handleSettings && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={handleSettings}
              accessibilityLabel="Settings and backend connection"
            >
              <SettingsIcon size={16} color={colors.goldLight} strokeWidth={2.2} />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.burgundy,
    paddingBottom: 10,
    paddingHorizontal: 14,
    borderBottomWidth: 1.5,
    borderBottomColor: colors.goldBorder,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 6,
    borderRadius: 8,
    backgroundColor: colors.burgundyDark,
    borderWidth: 1,
    borderColor: 'rgba(216, 199, 160, 0.4)',
  },
  backButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
    lineHeight: 20,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  titleContainer: {
    marginLeft: 8,
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    color: '#FFFFFF',
    fontSize: 15.5,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginLeft: 6,
  },
  subtitle: {
    color: '#F5EFE6',
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  iconButton: {
    padding: 6,
    backgroundColor: colors.burgundyDark,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(216, 199, 160, 0.4)',
  },
  iconText: {
    fontSize: 14,
  },
  newChatButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: 'rgba(216, 199, 160, 0.22)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  newChatText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  authButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: colors.goldSubtle,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  authButtonText: {
    color: colors.burgundy,
    fontSize: 11,
    fontWeight: '700',
  },
});
