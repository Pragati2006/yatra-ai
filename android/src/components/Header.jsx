import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, StatusBar, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import YatraLogo from './YatraLogo';
import { ClockIcon, SettingsIcon, MenuIcon, UserIcon } from './Icons';

export default function Header({
  title = 'YATRA AI',
  subtitle = 'Vaishno Devi Pilgrimage Assistant',
  isConnected = true,
  onMenuPress,
  onOpenSettings,
  onSettingsPress,
  onOpenHistory,
  onOpenAuth,
  onNewChatPress,
  showBack = false,
  onBackPress,
  user = null,
  showLegacyActions = false,
}) {
  const insets = useSafeAreaInsets();
  const handleSettings = onOpenSettings || onSettingsPress;
  const topPadding = Platform.OS === 'android' ? 6 : Math.max(insets.top, 8);

  return (
    <View style={[styles.container, { paddingTop: topPadding }]}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor={colors.surfaceWhite}
        translucent={false}
      />
      <View style={styles.topRow}>
        {/* Left Action: Back button OR Hamburger Menu button */}
        {showBack && onBackPress ? (
          <TouchableOpacity
            style={styles.navButton}
            onPress={onBackPress}
            accessibilityLabel="Go back"
            activeOpacity={0.7}
          >
            <Text style={styles.backButtonText}>←</Text>
          </TouchableOpacity>
        ) : onMenuPress ? (
          <TouchableOpacity
            style={styles.navButton}
            onPress={onMenuPress}
            accessibilityLabel="Open navigation menu"
            accessibilityRole="button"
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            activeOpacity={0.7}
          >
            <MenuIcon size={20} color={colors.royalPlum} strokeWidth={2.2} />
          </TouchableOpacity>
        ) : null}

        <View style={styles.brandRow}>
          <YatraLogo size={32} />
          <View style={styles.titleContainer}>
            <View style={styles.titleRow}>
              <Text style={styles.title} numberOfLines={1}>{title}</Text>
              <View style={[styles.statusDot, { backgroundColor: isConnected ? colors.success || '#3E876C' : colors.danger || '#C75A60' }]} />
            </View>
            <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
          </View>
        </View>

        <View style={styles.actionsRow}>
          {showLegacyActions && onNewChatPress && (
            <TouchableOpacity
              style={styles.newChatButton}
              onPress={onNewChatPress}
              accessibilityLabel="Start fresh chat"
            >
              <Text style={styles.newChatText}>+ New</Text>
            </TouchableOpacity>
          )}

          {showLegacyActions && onOpenHistory && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={onOpenHistory}
              accessibilityLabel="Conversation history"
            >
              <ClockIcon size={16} color={colors.royalPlum} strokeWidth={2.2} />
            </TouchableOpacity>
          )}

          {/* Minimal Profile / Account Chip */}
          {onOpenAuth && (
            <TouchableOpacity
              style={styles.authButton}
              onPress={onOpenAuth}
              accessibilityLabel="User account"
              activeOpacity={0.8}
            >
              <UserIcon size={14} color={colors.royalPlum} strokeWidth={2.2} />
              <Text style={styles.authButtonText} numberOfLines={1}>
                {user ? (user.name || user.email || user.phone || 'Devotee').slice(0, 8) : 'Devotee'}
              </Text>
            </TouchableOpacity>
          )}

          {showLegacyActions && handleSettings && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={handleSettings}
              accessibilityLabel="Settings and backend connection"
            >
              <SettingsIcon size={16} color={colors.royalPlum} strokeWidth={2.2} />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surfaceWhite,
    paddingBottom: 8,
    paddingHorizontal: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderDefault,
    elevation: 1,
    shadowColor: '#54152D',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 40,
  },
  navButton: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    borderRadius: 10,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  backButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 6,
    borderRadius: 8,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  backButtonText: {
    color: colors.royalPlum,
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
    justifyContent: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    color: colors.royalPlum,
    fontSize: 15.5,
    fontWeight: '800',
    letterSpacing: 0.6,
    lineHeight: 19,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginLeft: 6,
  },
  subtitle: {
    color: colors.champagneTaupe,
    fontSize: 10.5,
    fontWeight: '600',
    letterSpacing: 0.2,
    marginTop: 1,
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  iconButton: {
    padding: 6,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  iconText: {
    fontSize: 14,
  },
  newChatButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  newChatText: {
    color: colors.royalPlum,
    fontSize: 11,
    fontWeight: '700',
  },
  authButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: colors.softPlum,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  authButtonText: {
    color: colors.royalPlum,
    fontSize: 11,
    fontWeight: '700',
  },
});
