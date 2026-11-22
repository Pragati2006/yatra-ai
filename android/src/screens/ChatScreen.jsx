import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Keyboard,
  Platform,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import ChatBubble from '../components/ChatBubble';
import MessageComposer from '../components/MessageComposer';
import ConnectionModal from '../components/ConnectionModal';
import SidebarDrawer from '../components/SidebarDrawer';
import YatraLogo from '../components/YatraLogo';
import * as Speech from 'expo-speech';
import {
  sendChatMessage,
  checkBackendHealth,
  getRuntimeApiUrl,
  saveConversation,
  getChatHistory,
} from '../services/api';
import {
  getStoredUser,
  removeStoredUser,
  clearAuthToken,
  saveLocalChatMessages,
  saveLocalGuestConversation,
  getAuthToken,
} from '../utils/storage';

const QUICK_SUGGESTIONS = [
  'Current weather at Bhawan',
  'Vande Bharat Express train schedule',
  'Helicopter from Katra to Sanjichhat',
  'Ardhkuwari cave darshan wait time',
  'How to book Yatra Parchi online?',
];

const INITIAL_WELCOME_MESSAGE = {
  id: 'welcome-1',
  role: 'assistant',
  content:
    'Jai Mata Di! Welcome to Yatra AI — your intelligent pilgrimage guide for Shri Mata Vaishno Devi Ji.\n\nI can assist you with:\n- **Darshan & Aarti Timings**\n- **Live Elevation-Aware Weather**\n- **Train, Bus & Helicopter Schedules**\n- **Verified Accommodation & Shrine Board Bhawans**\n- **Guided Booking Simulation**\n\nHow may I assist your holy pilgrimage today?',
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
};

export default function ChatScreen({ navigation, route }) {
  const [messages, setMessages] = useState([INITIAL_WELCOME_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const [backendUrl, setBackendUrl] = useState('');
  const [isConnected, setIsConnected] = useState(true);
  const [latency, setLatency] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [sessionId, setSessionId] = useState(
    () => route?.params?.sessionId || `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  );
  const [activeTripRequest, setActiveTripRequest] = useState(null);
  const flatListRef = useRef(null);

  const formatIncomingMessages = (rawList) => {
    if (!Array.isArray(rawList) || rawList.length === 0) return [INITIAL_WELCOME_MESSAGE];
    return rawList.map((m, idx) => ({
      id: m.id || `msg-${idx}-${Date.now()}`,
      role: m.role || 'assistant',
      content: m.content || '',
      destination_images: m.destination_images || null,
      matched_destination: m.matched_destination || null,
      timestamp:
        m.timestamp ||
        (m.created_at
          ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
    }));
  };

  useEffect(() => {
    checkHealth();
    loadUser();
  }, []);

  useEffect(() => {
    if (route?.params?.sessionId) {
      const incomingSid = route.params.sessionId;
      setSessionId(incomingSid);
      if (route?.params?.messages && Array.isArray(route.params.messages) && route.params.messages.length > 0) {
        setMessages(formatIncomingMessages(route.params.messages));
      } else {
        getChatHistory(incomingSid)
          .then((data) => {
            if (data && data.messages && data.messages.length > 0) {
              setMessages(formatIncomingMessages(data.messages));
            }
          })
          .catch(() => {});
      }
      if (route?.params?.tripRequest) {
        setActiveTripRequest(route.params.tripRequest);
      }
    } else if (route?.params?.loadedAt) {
      handleStartNewChat();
    }
  }, [route?.params?.sessionId, route?.params?.loadedAt]);

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const sub = Keyboard.addListener(showEvent, () => {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    });
    return () => sub.remove();
  }, []);

  const handleStartNewChat = () => {
    const freshSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setSessionId(freshSid);
    setMessages([INITIAL_WELCOME_MESSAGE]);
    setActiveTripRequest(null);
  };

  const handleSelectConversation = (conv) => {
    const convId = conv.conversation_id || conv.session_id;
    if (!convId) return;
    setSessionId(convId);
    if (conv.messages && Array.isArray(conv.messages) && conv.messages.length > 0) {
      setMessages(formatIncomingMessages(conv.messages));
    } else {
      getChatHistory(convId)
        .then((data) => {
          if (data && data.messages && data.messages.length > 0) {
            setMessages(formatIncomingMessages(data.messages));
          }
        })
        .catch(() => {});
    }
    if (conv.trip_request) {
      setActiveTripRequest(conv.trip_request);
    }
  };

  const handleLogout = async () => {
    await removeStoredUser();
    await clearAuthToken();
    setUser(null);
  };

  useEffect(() => {
    if (messages.length > 1 && sessionId) {
      saveLocalChatMessages(messages);
      const firstUserMsg = messages.find((m) => m.role === 'user');
      const title = firstUserMsg?.content
        ? firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : '')
        : 'Pilgrimage Consultation';

      saveLocalGuestConversation({
        conversation_id: sessionId,
        title,
        messages,
        trip_request: activeTripRequest,
        preview: firstUserMsg?.content || 'Pilgrimage consultation with Yatra AI',
      }).catch(() => {});

      getAuthToken().then((token) => {
        if (token) {
          saveConversation(title, messages, sessionId, activeTripRequest, null).catch(() => {});
        }
      });
    }
  }, [messages, sessionId]);

  const loadUser = async () => {
    const u = await getStoredUser();
    if (u) setUser(u);
  };

  const checkHealth = async (retryCount = 0) => {
    const url = await getRuntimeApiUrl();
    setBackendUrl(url);
    const health = await checkBackendHealth(url);
    setIsConnected(health.ok);
    setLatency(health.latencyMs);

    if (!health.ok && retryCount < 2) {
      setTimeout(() => {
        checkHealth(retryCount + 1);
      }, retryCount === 0 ? 3500 : 8000);
    }
  };

  const handleSend = async (text) => {
    if (!text || !text.trim()) return;

    try {
      Speech.stop();
    } catch {
      // ignore
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await sendChatMessage(text.trim(), sessionId);
      if (response && response.response) {
        if (response.session_id) {
          setSessionId(response.session_id);
        }
        if (response.request) {
          setActiveTripRequest(response.request);
        }

        const hasBooking =
          text.toLowerCase().includes('book') ||
          text.toLowerCase().includes('parchi') ||
          text.toLowerCase().includes('ticket') ||
          text.toLowerCase().includes('helicopter') ||
          response.response.toLowerCase().includes('booking handoff') ||
          response.response.toLowerCase().includes('parchi');

        const aiMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.response,
          destination_images: response.destination_images || null,
          matched_destination: response.matched_destination || null,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          bookingHandoff: hasBooking
            ? {
                title: 'Ready to proceed with Parchi / Service Booking?',
                service: 'Vaishno Devi Yatra Registration',
              }
            : null,
        };
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        throw new Error('Empty response received from assistant');
      }
    } catch (err) {
      const isNetworkIssue =
        err.name === 'AbortError' ||
        (err.message &&
          (err.message.includes('Network') ||
            err.message.includes('timed out') ||
            err.message.includes('Failed to fetch') ||
            err.message.includes('Network request failed')));

      const errorMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: isNetworkIssue
          ? `Connection Notice: Unable to reach Yatra AI server at \`${backendUrl}\`.\n\n*Error: ${err.message}*\n\nPlease check backend connectivity or configure the server URL in Settings.`
          : `🙏 **Jai Mata Di!**\n\nI encountered a temporary processing issue while retrieving that information (*${err.message}*). Please try again or ask about Katra weather, darshan registration, or train schedules.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
      if (isNetworkIssue) {
        setIsConnected(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBookingHandoff = (bookingData) => {
    navigation.navigate('Booking', { initialService: bookingData?.service || 'Yatra Parchi' });
  };

  // Check if there are active user messages in the chat
  const hasUserMessage = messages.some((m) => m.role === 'user');

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      {/* 1. Minimal Header with Hamburger Menu */}
      <Header
        title="Yatra AI"
        subtitle="Pilgrimage & Tourism Assistant"
        isConnected={isConnected}
        user={user}
        onMenuPress={() => setDrawerOpen(true)}
        onOpenAuth={() => navigation.navigate('Auth')}
      />

      {/* 2. Non-intrusive Offline Notice (Only shown if disconnected) */}
      {!isConnected && (
        <TouchableOpacity
          style={styles.offlineNotice}
          onPress={() => setModalVisible(true)}
          activeOpacity={0.8}
        >
          <View style={styles.offlineDot} />
          <Text style={styles.offlineNoticeText}>
            Offline or reconnecting to server... Tap to configure connection
          </Text>
        </TouchableOpacity>
      )}

      {/* 3. Main Content: Welcome Hero (if fresh) OR Conversational Messages (if active) */}
      {!hasUserMessage ? (
        <ScrollView
          style={styles.welcomeScroll}
          contentContainerStyle={styles.welcomeContentContainer}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.welcomeHero}>
            <View style={styles.heroLogoWrapper}>
              <YatraLogo size={48} />
            </View>

            <View style={styles.greetingBadge}>
              <Text style={styles.greetingBadgeText}>🙏 JAI MATA DI</Text>
            </View>

            <Text style={styles.welcomePrompt}>Where would you like to go?</Text>

            <Text style={styles.welcomeSupportingText}>
              Your journey, thoughtfully planned. Pilgrimage guidance, multi-operator transport, live weather & shrine accommodations across Jammu & Kashmir.
            </Text>

            <View style={styles.suggestionsContainer}>
              <Text style={styles.suggestionsTitle}>SUGGESTED CONSULTATIONS</Text>
              <View style={styles.suggestionsWrapper}>
                {QUICK_SUGGESTIONS.map((item, idx) => (
                  <TouchableOpacity
                    key={`hero-sugg-${idx}`}
                    style={styles.suggestionPill}
                    onPress={() => handleSend(item)}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.suggestionPillText}>{item}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          </View>
        </ScrollView>
      ) : (
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item, idx) => item.id || `msg-${idx}`}
          renderItem={({ item }) => (
            <ChatBubble
              message={item}
              onActionPress={handleBookingHandoff}
              onNavigateToBooking={handleBookingHandoff}
            />
          )}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          onLayout={() => flatListRef.current?.scrollToEnd({ animated: true })}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          ListFooterComponent={
            loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="small" color={colors.primary} />
                <Text style={styles.loadingText}>Mata Rani Sahayata... consulting Yatra AI</Text>
              </View>
            ) : null
          }
        />
      )}

      {/* 4. Chat Input Composer fixed at the bottom */}
      <MessageComposer
        onSend={handleSend}
        disabled={loading}
        isLoading={loading}
        suggestions={hasUserMessage && messages.length <= 4 ? QUICK_SUGGESTIONS : []}
      />

      {/* 5. Collapsible Side Navigation Drawer */}
      <SidebarDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onNewChat={handleStartNewChat}
        onSelectConversation={handleSelectConversation}
        onNavigate={(screen) => navigation.navigate(screen)}
        onOpenSettings={() => setModalVisible(true)}
        onOpenAuth={() => navigation.navigate('Auth')}
        onLogout={handleLogout}
        user={user}
        currentSessionId={sessionId}
        activeRoute="Assistant"
      />

      {/* 6. Connection & Settings Modal */}
      <ConnectionModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onConnected={(newUrl) => {
          setBackendUrl(newUrl);
          checkHealth();
        }}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background || '#F7F1EB',
  },
  offlineNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FAF2E6',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E9DED6',
    gap: 8,
  },
  offlineDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.warning || '#C28B42',
  },
  offlineNoticeText: {
    fontSize: 11.5,
    color: '#8A5818',
    fontWeight: '600',
  },
  welcomeScroll: {
    flex: 1,
  },
  welcomeContentContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
  },
  welcomeHero: {
    alignItems: 'center',
    maxWidth: 440,
    alignSelf: 'center',
    width: '100%',
  },
  heroLogoWrapper: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1.5,
    borderColor: colors.borderDefault,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 18,
    marginBottom: 14,
    ...Platform.select({
      android: { elevation: 2 },
      ios: {
        shadowColor: '#54152D',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 6,
      },
    }),
  },
  greetingBadge: {
    backgroundColor: colors.softPlum,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    marginBottom: 12,
  },
  greetingBadgeText: {
    fontSize: 10.5,
    fontWeight: '800',
    color: colors.royalPlum,
    letterSpacing: 0.8,
  },
  welcomePrompt: {
    fontSize: 24,
    fontWeight: '800',
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 10,
    letterSpacing: 0.2,
    lineHeight: 30,
  },
  welcomeSupportingText: {
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 26,
    paddingHorizontal: 8,
  },
  suggestionsContainer: {
    width: '100%',
    alignItems: 'center',
  },
  suggestionsTitle: {
    fontSize: 10.5,
    fontWeight: '800',
    color: colors.champagneTaupe,
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  suggestionsWrapper: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  suggestionPill: {
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.borderDefault,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
    ...Platform.select({
      android: { elevation: 1 },
      ios: {
        shadowColor: '#54152D',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.04,
        shadowRadius: 3,
      },
    }),
  },
  suggestionPillText: {
    fontSize: 12.5,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  messageList: {
    paddingHorizontal: spacing.sm || 8,
    paddingVertical: spacing.md || 12,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm || 8,
    gap: spacing.xs || 4,
  },
  loadingText: {
    fontSize: 12,
    color: colors.royalPlum,
    fontStyle: 'italic',
  },
});
