import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Animated,
  useWindowDimensions,
  Platform,
  BackHandler,
  ActivityIndicator,
  Modal,
  StatusBar,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../theme/colors';
import YatraLogo from './YatraLogo';
import {
  PlusIcon,
  SearchIcon,
  ClockIcon,
  MessageSquareIcon,
  TicketIcon,
  BuildingIcon,
  TrainIcon,
  MountainIcon,
  CloudSunIcon,
  SettingsIcon,
  UserIcon,
  LogOutIcon,
  CloseIcon,
} from './Icons';
import { fetchChatHistory } from '../services/api';
import { getLocalGuestConversations, getLocalChatMessages } from '../utils/storage';

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
  const { width: windowWidth } = useWindowDimensions();

  // Guarantee readable width on all Android screens (minimum 280dp, maximum 340dp, or 82% of width)
  const drawerWidth = Math.min(Math.max((windowWidth || 360) * 0.82, 280), 340);

  const [searchQuery, setSearchQuery] = useState('');
  const [conversations, setConversations] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isRendered, setIsRendered] = useState(isOpen);
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const searchInputRef = useRef(null);

  // Animation values
  const slideAnim = useRef(new Animated.Value(-340)).current;
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
          toValue: -drawerWidth,
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
  }, [isOpen, drawerWidth]);

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

  // Safe status bar and navigation bar clearance
  const statusBarHeight = StatusBar.currentHeight || 28;
  const safeTop = insets.top > 0 ? insets.top : statusBarHeight;
  const topPadding = safeTop + 8;
  const bottomPadding = Math.max(insets.bottom, Platform.OS === 'android' ? 24 : 16);

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
              width: drawerWidth,
              paddingTop: topPadding,
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

          {/* Unified Scrollable Container: Contains all 12 navigation options + history */}
          <ScrollView
            style={styles.scrollBody}
            contentContainerStyle={[
              styles.scrollBodyContent,
              { paddingBottom: bottomPadding + 28 },
            ]}
            showsVerticalScrollIndicator={true}
            keyboardShouldPersistTaps="handled"
          >
            {/* ========================================================
                SECTION 1: CHAT MANAGEMENT (Items 1, 2, 3)
            ======================================================== */}
            <View style={styles.sectionBlock}>
              <Text style={styles.sectionTitle}>CHAT</Text>

              {/* 1. New Chat */}
              <TouchableOpacity
                style={styles.newChatButton}
                onPress={() => {
                  onClose();
                  if (onNewChat) onNewChat();
                }}
                activeOpacity={0.8}
                accessibilityLabel="New Chat"
              >
                <View style={styles.newChatIconWrapper}>
                  <PlusIcon size={16} color="#FFFFFF" strokeWidth={2.5} />
                </View>
                <Text style={styles.newChatText}>New Chat</Text>
              </TouchableOpacity>

              {/* 2. Search Conversations */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  isSearchFocused && styles.navItemActive,
                ]}
                onPress={() => {
                  searchInputRef.current?.focus();
                }}
                activeOpacity={0.7}
                accessibilityLabel="Search Conversations"
              >
                <View style={styles.navIconWrapper}>
                  <SearchIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={2.2}
                  />
                </View>
                <Text style={styles.navItemLabel}>Search Conversations</Text>
              </TouchableOpacity>

              {/* Search Conversations Input Field */}
              <View
                style={[
                  styles.searchContainer,
                  isSearchFocused && styles.searchContainerFocused,
                ]}
              >
                <SearchIcon size={14} color={colors.textSecondary} strokeWidth={2} />
                <TextInput
                  ref={searchInputRef}
                  style={styles.searchInput}
                  placeholder="Search conversations..."
                  placeholderTextColor={colors.textMuted}
                  value={searchQuery}
                  onChangeText={setSearchQuery}
                  onFocus={() => setIsSearchFocused(true)}
                  onBlur={() => setIsSearchFocused(false)}
                  returnKeyType="search"
                  clearButtonMode="while-editing"
                  accessibilityLabel="Search conversations input field"
                />
                {searchQuery ? (
                  <TouchableOpacity
                    onPress={() => setSearchQuery('')}
                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                    accessibilityLabel="Clear search text"
                  >
                    <CloseIcon size={13} color={colors.textSecondary} />
                  </TouchableOpacity>
                ) : null}
              </View>

              {/* 3. Previous Conversations */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'History' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('History');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Previous Conversations (Chat History)"
              >
                <View style={styles.navIconWrapper}>
                  <ClockIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'History' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, activeRoute === 'History' && styles.navItemLabelActive]}>Previous Conversations</Text>
                {activeRoute === 'History' && <View style={styles.activeIndicator} />}
              </TouchableOpacity>

              {/* Recent Conversations List */}
              <View style={styles.recentSubSection}>
                <View style={styles.sectionHeaderRow}>
                  <ClockIcon size={11} color={colors.champagneTaupe} strokeWidth={2} />
                  <Text style={styles.subSectionTitle}>RECENT CONVERSATIONS</Text>
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
                  filteredConversations.slice(0, 5).map((item, idx) => {
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
                          if (onSelectConversation) onSelectConversation(item);
                        }}
                        activeOpacity={0.7}
                        accessibilityLabel={`Resume conversation ${item.title || 'Consultation'}`}
                      >
                        <MessageSquareIcon
                          size={14}
                          color={isActive ? colors.royalPlum : colors.textSecondary}
                          strokeWidth={isActive ? 2.2 : 1.8}
                        />
                        <View style={styles.conversationInfo}>
                          <Text
                            style={[
                              styles.conversationTitle,
                              isActive && styles.conversationTitleActive,
                            ]}
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
            </View>

            {/* ========================================================
                SECTION 2: YATRA SERVICES & EXPLORE (Items 4-9)
            ======================================================== */}
            <View style={styles.sectionBlock}>
              <Text style={styles.sectionTitle}>YATRA SERVICES & EXPLORE</Text>

              {/* 4. Assistant */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'Assistant' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Assistant');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Assistant"
              >
                <View style={styles.navIconWrapper}>
                  <MessageSquareIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'Assistant' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, activeRoute === 'Assistant' && styles.navItemLabelActive]}>Assistant</Text>
                {activeRoute === 'Assistant' && <View style={styles.activeIndicator} />}
              </TouchableOpacity>

              {/* 5. Booking / Parchi */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'Booking' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Booking');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Booking / Parchi (Pilgrimage & Parchi Booking)"
              >
                <View style={styles.navIconWrapper}>
                  <TicketIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'Booking' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, activeRoute === 'Booking' && styles.navItemLabelActive]}>Booking / Parchi</Text>
                {activeRoute === 'Booking' && <View style={styles.activeIndicator} />}
              </TouchableOpacity>

              {/* 6. Accommodation / Bhawans */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  (activeRoute === 'Stay' || activeRoute === 'Accommodation') && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Stay');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Accommodation / Bhawans (Shrine Board Bhawans)"
              >
                <View style={styles.navIconWrapper}>
                  <BuildingIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'Stay' || activeRoute === 'Accommodation' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, (activeRoute === 'Stay' || activeRoute === 'Accommodation') && styles.navItemLabelActive]}>Accommodation / Bhawans</Text>
                {(activeRoute === 'Stay' || activeRoute === 'Accommodation') && (
                  <View style={styles.activeIndicator} />
                )}
              </TouchableOpacity>

              {/* 7. Transport / Schedules */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'Transport' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Transport');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Transport / Schedules (Transport & Schedules)"
              >
                <View style={styles.navIconWrapper}>
                  <TrainIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'Transport' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, activeRoute === 'Transport' && styles.navItemLabelActive]}>Transport / Schedules</Text>
                {activeRoute === 'Transport' && <View style={styles.activeIndicator} />}
              </TouchableOpacity>

              {/* 8. Sightseeing / Destinations */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  (activeRoute === 'Destinations' || activeRoute === 'Tourism') &&
                    styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Destinations');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Sightseeing / Destinations (Holy Sites & Shrines)"
              >
                <View style={styles.navIconWrapper}>
                  <MountainIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={
                      activeRoute === 'Destinations' || activeRoute === 'Tourism' ? 2.4 : 2
                    }
                  />
                </View>
                <Text style={[styles.navItemLabel, (activeRoute === 'Destinations' || activeRoute === 'Tourism') && styles.navItemLabelActive]}>Sightseeing / Destinations</Text>
                {(activeRoute === 'Destinations' || activeRoute === 'Tourism') && (
                  <View style={styles.activeIndicator} />
                )}
              </TouchableOpacity>

              {/* 9. Weather Guidance */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'Weather' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onNavigate) onNavigate('Weather');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Weather Guidance"
              >
                <View style={styles.navIconWrapper}>
                  <CloudSunIcon
                    size={18}
                    color={colors.royalPlum}
                    strokeWidth={activeRoute === 'Weather' ? 2.4 : 2}
                  />
                </View>
                <Text style={[styles.navItemLabel, activeRoute === 'Weather' && styles.navItemLabelActive]}>Weather Guidance</Text>
                {activeRoute === 'Weather' && <View style={styles.activeIndicator} />}
              </TouchableOpacity>
            </View>

            {/* ========================================================
                SECTION 3: SETTINGS & ACCOUNT (Items 10, 11, 12)
            ======================================================== */}
            <View style={[styles.sectionBlock, styles.drawerFooter]}>
              <Text style={styles.sectionTitle}>SETTINGS & ACCOUNT</Text>

              {/* 10. Settings / Server */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  (activeRoute === 'Settings' || activeRoute === 'SettingsModal') &&
                    styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onOpenSettings) onOpenSettings();
                  else if (onNavigate) onNavigate('SettingsModal');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Settings / Server (Settings & Server)"
              >
                <View style={styles.navIconWrapper}>
                  <SettingsIcon size={18} color={colors.royalPlum} strokeWidth={2} />
                </View>
                <Text style={styles.navItemLabel}>Settings / Server</Text>
              </TouchableOpacity>

              {/* 11. Devotee Profile / Sign In */}
              <TouchableOpacity
                style={[
                  styles.navItem,
                  activeRoute === 'Auth' && styles.navItemActive,
                ]}
                onPress={() => {
                  onClose();
                  if (onOpenAuth) onOpenAuth();
                  else if (onNavigate) onNavigate('Auth');
                }}
                activeOpacity={0.7}
                accessibilityLabel="Devotee Profile / Sign In (Devotee Profile)"
              >
                <View style={styles.navIconWrapper}>
                  <UserIcon size={18} color={colors.royalPlum} strokeWidth={2} />
                </View>
                <View style={styles.labelCol}>
                  <Text style={styles.navItemLabel}>Devotee Profile / Sign In</Text>
                  {user ? (
                    <Text style={styles.userSubtitle} numberOfLines={1}>
                      {user.name || user.email || user.phone || 'Devotee Account'}
                    </Text>
                  ) : null}
                </View>
              </TouchableOpacity>

              {/* 12. Sign Out */}
              <TouchableOpacity
                style={styles.navItem}
                onPress={() => {
                  onClose();
                  if (onLogout) onLogout();
                }}
                activeOpacity={0.7}
                accessibilityLabel="Sign Out"
              >
                <View style={styles.navIconWrapper}>
                  <LogOutIcon size={18} color={colors.danger || '#C75A60'} strokeWidth={2} />
                </View>
                <Text style={[styles.navItemLabel, styles.logoutLabel]}>Sign Out</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
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
  scrollBody: {
    flex: 1,
  },
  scrollBodyContent: {
    paddingTop: 10,
  },
  sectionBlock: {
    marginBottom: 16,
  },
  drawerFooter: {
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
    paddingTop: 12,
  },
  sectionTitle: {
    fontSize: 10.5,
    fontWeight: '800',
    color: colors.champagneTaupe,
    letterSpacing: 0.8,
    marginBottom: 6,
    marginTop: 4,
  },
  newChatButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.royalPlum,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginBottom: 8,
    gap: 10,
    borderWidth: 1,
    borderColor: colors.mutedPlum,
    minHeight: 44,
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
    paddingVertical: Platform.OS === 'ios' ? 7 : 5,
    gap: 8,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    marginBottom: 8,
    marginTop: 2,
    minHeight: 38,
  },
  searchContainerFocused: {
    borderColor: colors.champagneTaupe,
    backgroundColor: colors.surfaceWhite,
  },
  searchInput: {
    flex: 1,
    fontSize: 13,
    color: colors.textPrimary,
    padding: 0,
  },
  navItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    paddingHorizontal: 10,
    borderRadius: 10,
    marginBottom: 2,
    minHeight: 44,
  },
  navItemActive: {
    backgroundColor: colors.softPlum,
    borderWidth: 1,
    borderColor: colors.borderDefault,
  },
  navIconWrapper: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    flexShrink: 0,
  },
  navItemLabel: {
    fontSize: 13.5,
    color: colors.textPrimary,
    fontWeight: '600',
    flex: 1,
    includeFontPadding: false,
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
    marginLeft: 6,
  },
  labelCol: {
    flex: 1,
    justifyContent: 'center',
  },
  userSubtitle: {
    fontSize: 10.5,
    color: colors.textSecondary,
    fontWeight: '500',
    marginTop: 1,
  },
  logoutLabel: {
    color: colors.danger || '#C75A60',
    fontWeight: '700',
  },
  recentSubSection: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderSubtle,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginBottom: 6,
  },
  subSectionTitle: {
    fontSize: 10,
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
    minHeight: 38,
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
});
