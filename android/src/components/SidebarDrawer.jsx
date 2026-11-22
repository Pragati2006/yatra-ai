import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Animated,
  Dimensions,
  Platform,
  BackHandler,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import YatraLogo from './YatraLogo';
import {
  PlusIcon,
  SearchIcon,
  MessageSquareIcon,
  MountainIcon,
  TrainIcon,
  CloudSunIcon,
  TicketIcon,
  BuildingIcon,
  SettingsIcon,
  UserIcon,
  LogOutIcon,
  CloseIcon,
  ClockIcon,
} from './Icons';
import { fetchChatHistory } from '../services/api';
import { getLocalGuestConversations, getLocalChatMessages } from '../utils/storage';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const DRAWER_WIDTH = Math.min(SCREEN_WIDTH * 0.82, 330);

export default function SidebarDrawer({
  isOpen,
  onClose,
  onNewChat,
  onSelectConversation,
  onNavigate,
  onOpenSettings,
  onOpenAuth,
  onLogout,
  user = null,
  currentSessionId = null,
  activeRoute = 'Assistant',
}) {
  const insets = useSafeAreaInsets();
  const [searchQuery, setSearchQuery] = useState('');
  const [conversations, setConversations] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isRendered, setIsRendered] = useState(isOpen);

  // Animation values
  const slideAnim = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Handle hardware back button on Android
  useEffect(() => {
    if (!isOpen) return;

    const backAction = () => {
      onClose();
      return true;
    };

    const backHandler = BackHandler.addEventListener('hardwareBackPress', backAction);
    return () => backHandler.remove();
  }, [isOpen, onClose]);

  // Trigger smooth slide in/out when isOpen toggles
  useEffect(() => {
    if (isOpen) {
      setIsRendered(true);
      loadHistory();
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: -DRAWER_WIDTH,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start(({ finished }) => {
        if (finished) {
          setIsRendered(false);
        }
      });
    }
  }, [isOpen]);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await fetchChatHistory();
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data?.conversations && Array.isArray(data.conversations)) {
        items = data.conversations;
      } else if (data?.history && Array.isArray(data.history)) {
        items = data.history;
      }

      if (items.length === 0) {
        const guestConvs = await getLocalGuestConversations();
        if (guestConvs && guestConvs.length > 0) {
          items = guestConvs;
        } else {
          const local = await getLocalChatMessages();
          if (local && local.length > 1) {
            const firstUser = local.find((m) => m.role === 'user');
            items = [
              {
                conversation_id: 'guest-local-session',
                title: firstUser?.content
                  ? firstUser.content.slice(0, 42) + (firstUser.content.length > 42 ? '...' : '')
                  : 'Pilgrimage Consultation',
                created_at: new Date().toISOString(),
                messages: local,
              },
            ];
          }
        }
      }
      setConversations(items);
    } catch {
      const guestConvs = await getLocalGuestConversations().catch(() => []);
      setConversations(guestConvs || []);
    } finally {
      setLoadingHistory(false);
    }
  };

  const filteredConversations = conversations.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const title = (c.title || c.preview || '').toLowerCase();
    return title.includes(q);
  });

  if (!isRendered) {
    return null;
  }

  const topPadding = Math.max(insets.top, 14) + 6;
  const bottomPadding = Math.max(insets.bottom, 12) + 6;

  return (
    <Modal
      visible={isRendered}
      transparent
      animationType="none"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <View style={styles.modalOverlay}>
        {/* Semi-transparent Backdrop Overlay */}
      <Animated.View
        style={[
          styles.backdrop,
          {
            opacity: fadeAnim,
          },
        ]}
      >
        <TouchableOpacity
          style={StyleSheet.absoluteFillObject}
          activeOpacity={1}
          onPress={onClose}
          accessibilityLabel="Close navigation drawer"
        />
      </Animated.View>

      {/* Sliding Drawer Container */}
      <Animated.View
        style={[
          styles.drawerContainer,
          {
            width: DRAWER_WIDTH,
            paddingTop: topPadding,
            paddingBottom: bottomPadding,
            transform: [{ translateX: slideAnim }],
          },
        ]}
      >
        {/* 1. Drawer Header */}
        <View style={styles.drawerHeader}>
          <View style={styles.brandGroup}>
            <YatraLogo size={28} />
            <View style={styles.brandTextGroup}>
              <Text style={styles.drawerTitle}>YATRA AI</Text>
              <Text style={styles.drawerSubtitle}>Pilgrimage & Tourism</Text>
            </View>
          </View>
          <TouchableOpacity
            style={styles.closeButton}
            onPress={onClose}
            accessibilityLabel="Close drawer"
            activeOpacity={0.7}
          >
            <CloseIcon size={18} color={colors.royalPlum} strokeWidth={2.2} />
          </TouchableOpacity>
        </View>

        {/* 2. CHAT Section Header & Actions */}
        <View style={styles.chatSectionHeader}>
          <Text style={styles.sectionTitle}>CHAT</Text>
        </View>

        {/* New Chat Action Button */}
        <TouchableOpacity
          style={styles.newChatButton}
          onPress={() => {
            onClose();
            onNewChat();
          }}
          activeOpacity={0.8}
          accessibilityLabel="Start a new chat"
        >
          <View style={styles.newChatIconWrapper}>
            <PlusIcon size={16} color="#FFFFFF" strokeWidth={2.5} />
          </View>
          <Text style={styles.newChatText}>New Chat</Text>
        </TouchableOpacity>

        {/* Chat History Item */}
        <TouchableOpacity
          style={[
            styles.navItem,
            styles.chatHistoryItem,
            activeRoute === 'History' && styles.navItemActive,
          ]}
          onPress={() => {
            onClose();
            onNavigate('History');
          }}
          activeOpacity={0.7}
          accessibilityLabel="View Chat History"
        >
          <ClockIcon
            size={17}
            color={colors.royalPlum}
            strokeWidth={activeRoute === 'History' ? 2.4 : 2}
          />
          <Text
            style={[
              styles.navItemLabel,
              activeRoute === 'History' && styles.navItemLabelActive,
            ]}
          >
            Chat History
          </Text>
          {activeRoute === 'History' && <View style={styles.activeIndicator} />}
        </TouchableOpacity>

        {/* Search Conversations Input */}
        <View style={styles.searchContainer}>
          <SearchIcon size={15} color={colors.textSecondary} strokeWidth={2} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search conversations..."
            placeholderTextColor={colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="search"
            clearButtonMode="while-editing"
          />
        </View>

        {/* Scrollable Middle Body */}
        <ScrollView
          style={styles.scrollBody}
          contentContainerStyle={styles.scrollBodyContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* 4. Recent Conversations Section */}
          <View style={styles.sectionBlock}>
            <View style={styles.sectionHeaderRow}>
              <ClockIcon size={13} color={colors.champagneTaupe} strokeWidth={2} />
              <Text style={styles.sectionTitle}>RECENT CONVERSATIONS</Text>
            </View>

            {loadingHistory ? (
              <View style={styles.loadingBox}>
                <ActivityIndicator size="small" color={colors.royalPlum} />
                <Text style={styles.loadingText}>Loading history...</Text>
              </View>
            ) : filteredConversations.length === 0 ? (
              <Text style={styles.emptyHistoryText}>
                {searchQuery ? 'No matching conversations' : 'No previous consultations yet'}
              </Text>
            ) : (
              filteredConversations.map((item, idx) => {
                const cid = item.conversation_id || item.session_id || `hist-${idx}`;
                const isActive = cid === currentSessionId;
                const dateStr = item.updated_at || item.created_at;
                const formattedDate = dateStr
                  ? new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric' })
                  : '';

                return (
                  <TouchableOpacity
                    key={cid}
                    style={[styles.conversationItem, isActive && styles.conversationItemActive]}
                    onPress={() => {
                      onClose();
                      onSelectConversation(item);
                    }}
                    activeOpacity={0.7}
                  >
                    <MessageSquareIcon
                      size={15}
                      color={isActive ? colors.royalPlum : colors.textSecondary}
                      strokeWidth={isActive ? 2.2 : 1.8}
                    />
                    <View style={styles.conversationInfo}>
                      <Text
                        style={[styles.conversationTitle, isActive && styles.conversationTitleActive]}
                        numberOfLines={1}
                      >
                        {item.title || item.preview || 'Pilgrimage Consultation'}
                      </Text>
                      {formattedDate ? (
                        <Text style={styles.conversationDate}>{formattedDate}</Text>
                      ) : null}
                    </View>
                  </TouchableOpacity>
                );
              })
            )}
          </View>

          {/* 5. Yatra Services Section */}
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionTitle} accessibilityLabel="Explore Yatra Services">
              YATRA SERVICES & EXPLORE
            </Text>

            {/* 1. Assistant */}
            <TouchableOpacity
              style={[
                styles.navItem,
                activeRoute === 'Assistant' && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Assistant');
              }}
              activeOpacity={0.7}
            >
              <MessageSquareIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Assistant' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  activeRoute === 'Assistant' && styles.navItemLabelActive,
                ]}
              >
                Assistant
              </Text>
              {activeRoute === 'Assistant' && <View style={styles.activeIndicator} />}
            </TouchableOpacity>

            {/* 2. Guided Booking & Parchi */}
            <TouchableOpacity
              style={[
                styles.navItem,
                activeRoute === 'Booking' && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Booking');
              }}
              activeOpacity={0.7}
              accessibilityLabel="Booking / Parchi (Pilgrimage & Parchi Booking)"
            >
              <TicketIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Booking' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  activeRoute === 'Booking' && styles.navItemLabelActive,
                ]}
              >
                Booking / Parchi
              </Text>
              {activeRoute === 'Booking' && <View style={styles.activeIndicator} />}
            </TouchableOpacity>

            {/* 3. Accommodation & Bhawans */}
            <TouchableOpacity
              style={[
                styles.navItem,
                (activeRoute === 'Stay' || activeRoute === 'Accommodation') && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Stay');
              }}
              activeOpacity={0.7}
              accessibilityLabel="Accommodation / Bhawans (Shrine Board Bhawans & Stay)"
            >
              <BuildingIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Stay' || activeRoute === 'Accommodation' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  (activeRoute === 'Stay' || activeRoute === 'Accommodation') &&
                    styles.navItemLabelActive,
                ]}
              >
                Accommodation / Bhawans
              </Text>
              {(activeRoute === 'Stay' || activeRoute === 'Accommodation') && (
                <View style={styles.activeIndicator} />
              )}
            </TouchableOpacity>

            {/* 4. Transport & Schedules */}
            <TouchableOpacity
              style={[
                styles.navItem,
                activeRoute === 'Transport' && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Transport');
              }}
              activeOpacity={0.7}
              accessibilityLabel="Transport & Schedules"
            >
              <TrainIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Transport' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  activeRoute === 'Transport' && styles.navItemLabelActive,
                ]}
              >
                Transport / Schedules
              </Text>
              {activeRoute === 'Transport' && <View style={styles.activeIndicator} />}
            </TouchableOpacity>

            {/* 5. Sightseeing & Holy Sites */}
            <TouchableOpacity
              style={[
                styles.navItem,
                (activeRoute === 'Destinations' || activeRoute === 'Tourism') && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Destinations');
              }}
              activeOpacity={0.7}
              accessibilityLabel="Sightseeing / Destinations (Holy Sites & Shrines)"
            >
              <MountainIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Destinations' || activeRoute === 'Tourism' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  (activeRoute === 'Destinations' || activeRoute === 'Tourism') &&
                    styles.navItemLabelActive,
                ]}
              >
                Sightseeing / Destinations
              </Text>
              {(activeRoute === 'Destinations' || activeRoute === 'Tourism') && (
                <View style={styles.activeIndicator} />
              )}
            </TouchableOpacity>

            {/* 6. Weather Guidance */}
            <TouchableOpacity
              style={[
                styles.navItem,
                activeRoute === 'Weather' && styles.navItemActive,
              ]}
              onPress={() => {
                onClose();
                onNavigate('Weather');
              }}
              activeOpacity={0.7}
            >
              <CloudSunIcon
                size={17}
                color={colors.royalPlum}
                strokeWidth={activeRoute === 'Weather' ? 2.4 : 2}
              />
              <Text
                style={[
                  styles.navItemLabel,
                  activeRoute === 'Weather' && styles.navItemLabelActive,
                ]}
              >
                Weather Guidance
              </Text>
              {activeRoute === 'Weather' && <View style={styles.activeIndicator} />}
            </TouchableOpacity>
          </View>
        </ScrollView>

        {/* 6. Settings & Account Section (Pinned to bottom) */}
        <View style={styles.drawerFooter}>
          <TouchableOpacity
            style={styles.footerItem}
            onPress={() => {
              onClose();
              onOpenSettings();
            }}
            activeOpacity={0.7}
            accessibilityLabel="Settings & Server"
          >
            <SettingsIcon size={17} color={colors.textSecondary} strokeWidth={2} />
            <Text style={styles.footerItemText}>Settings / Server</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.footerItem}
            onPress={() => {
              onClose();
              onOpenAuth();
            }}
            activeOpacity={0.7}
            accessibilityLabel="User Profile / Devotee Sign In"
          >
            <UserIcon size={17} color={colors.textSecondary} strokeWidth={2} />
            <Text style={styles.footerItemText} numberOfLines={1}>
              {user ? (user.name || user.email || user.phone || 'Devotee Profile') : 'User Profile / Sign In'}
            </Text>
          </TouchableOpacity>

          {user && onLogout && (
            <TouchableOpacity
              style={styles.logoutItem}
              onPress={() => {
                onClose();
                onLogout();
              }}
              activeOpacity={0.7}
            >
              <LogOutIcon size={16} color={colors.danger || '#EF4444'} strokeWidth={2} />
              <Text style={styles.logoutText}>Sign Out</Text>
            </TouchableOpacity>
          )}
        </View>
      </Animated.View>
    </View>
  </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 9999,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(48, 39, 42, 0.45)',
    zIndex: 1,
  },
  drawerContainer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    backgroundColor: colors.surfaceWhite,
    borderRightWidth: 1,
    borderRightColor: colors.borderDefault,
    paddingHorizontal: 16,
    zIndex: 10,
    ...Platform.select({
      android: { elevation: 16 },
      ios: {
        shadowColor: '#54152D',
        shadowOffset: { width: 4, height: 0 },
        shadowOpacity: 0.12,
        shadowRadius: 10,
      },
    }),
  },
  drawerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSubtle,
  },
  brandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandTextGroup: {
    justifyContent: 'center',
  },
  drawerTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.royalPlum,
    letterSpacing: 0.5,
  },
  drawerSubtitle: {
    fontSize: 10.5,
    fontWeight: '600',
    color: colors.champagneTaupe,
  },
  closeButton: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: colors.surfaceSecondary,
  },
  chatSectionHeader: {
    marginTop: 10,
    marginBottom: 4,
  },
  chatHistoryItem: {
    marginBottom: 8,
  },
  newChatButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.royalPlum,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginTop: 12,
    marginBottom: 10,
    gap: 10,
    borderWidth: 1,
    borderColor: colors.mutedPlum,
  },
  newChatIconWrapper: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  newChatText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: 0.3,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surfaceSecondary,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: Platform.OS === 'ios' ? 7 : 4,
    gap: 8,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    marginBottom: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 13,
    color: colors.textPrimary,
    padding: 0,
  },
  scrollBody: {
    flex: 1,
  },
  scrollBodyContent: {
    paddingVertical: 6,
  },
  sectionBlock: {
    marginBottom: 18,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  sectionTitle: {
    fontSize: 10.5,
    fontWeight: '800',
    color: colors.champagneTaupe,
    letterSpacing: 0.8,
  },
  loadingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  loadingText: {
    fontSize: 12,
    color: colors.textSecondary,
    fontStyle: 'italic',
  },
  emptyHistoryText: {
    fontSize: 12,
    color: colors.textMuted,
    paddingVertical: 6,
    fontStyle: 'italic',
  },
  conversationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRadius: 8,
    gap: 10,
    marginBottom: 2,
  },
  conversationItemActive: {
    backgroundColor: colors.softPlum,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  conversationInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 6,
  },
  conversationTitle: {
    fontSize: 12.5,
    color: colors.textPrimary,
    fontWeight: '500',
    flex: 1,
  },
  conversationTitleActive: {
    color: colors.royalPlum,
    fontWeight: '700',
  },
  conversationDate: {
    fontSize: 10.5,
    color: colors.textMuted,
    fontWeight: '500',
  },
  navItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderRadius: 8,
    gap: 12,
    marginBottom: 2,
  },
  navItemActive: {
    backgroundColor: colors.softPlum,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  navItemLabel: {
    fontSize: 13,
    color: colors.textPrimary,
    fontWeight: '600',
    flex: 1,
  },
  navItemLabelActive: {
    color: colors.royalPlum,
    fontWeight: '800',
  },
  activeIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.royalPlum,
  },
  drawerFooter: {
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    paddingTop: 10,
    gap: 4,
  },
  footerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 6,
    gap: 12,
    borderRadius: 8,
  },
  footerItemText: {
    fontSize: 12.5,
    color: colors.textSecondary,
    fontWeight: '600',
    flex: 1,
  },
  logoutItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 6,
    gap: 12,
    marginTop: 2,
  },
  logoutText: {
    fontSize: 12,
    color: colors.danger,
    fontWeight: '700',
  },
});

