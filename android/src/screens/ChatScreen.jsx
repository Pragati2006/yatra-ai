import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import StatusBanner from '../components/StatusBanner';
import ChatBubble from '../components/ChatBubble';
import MessageComposer from '../components/MessageComposer';
import ConnectionModal from '../components/ConnectionModal';
import * as Speech from 'expo-speech';
import { sendChatMessage, checkBackendHealth, getRuntimeApiUrl, saveConversation, getChatHistory } from '../services/api';
import { getStoredUser, getLocalChatMessages, saveLocalChatMessages, saveLocalGuestConversation, getAuthToken } from '../utils/storage';

const QUICK_SUGGESTIONS = [
  'Weather at Bhawan',
  'Helicopter from Katra to Sanjichhat',
  'Vande Bharat Express train schedule',
  'Ardhkuwari cave darshan wait time',
  'How to book Yatra Parchi?',
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
  const [isConnected, setIsConnected] = useState(false);
  const [latency, setLatency] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
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
        // Fetch from backend or storage if messages array wasn't provided in params
        getChatHistory(incomingSid).then((data) => {
          if (data && data.messages && data.messages.length > 0) {
            setMessages(formatIncomingMessages(data.messages));
          }
        }).catch(() => {});
      }
      if (route?.params?.tripRequest) {
        setActiveTripRequest(route.params.tripRequest);
      }
    } else if (route?.params?.loadedAt) {
      // Clean new chat requested
      const freshSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setSessionId(freshSid);
      setMessages([INITIAL_WELCOME_MESSAGE]);
      setActiveTripRequest(null);
    }
  }, [route?.params?.sessionId, route?.params?.loadedAt]);

  const handleStartNewChat = () => {
    const freshSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setSessionId(freshSid);
    setMessages([INITIAL_WELCOME_MESSAGE]);
    setActiveTripRequest(null);
  };

  useEffect(() => {
    if (messages.length > 1 && sessionId) {
      saveLocalChatMessages(messages);
      const firstUserMsg = messages.find((m) => m.role === 'user');
      const title = firstUserMsg?.content
        ? (firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : ''))
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

    // If initial check fails (e.g. Render cold start), auto-retry in background to catch server wake-up
    if (!health.ok && retryCount < 2) {
      setTimeout(() => {
        checkHealth(retryCount + 1);
      }, retryCount === 0 ? 3500 : 8000);
    }
  };

  const handleSend = async (text) => {
    if (!text || !text.trim()) return;

    // Immediately stop ongoing Text-to-Speech audio if active
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
        // Detect if booking intent is present
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
        (err.message && (
          err.message.includes('Network') ||
          err.message.includes('timed out') ||
          err.message.includes('Failed to fetch') ||
          err.message.includes('Network request failed')
        ));

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

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior="padding"
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <Header
        title="Yatra AI Assistant"
        subtitle="Maa Vaishno Devi Guide"
        isConnected={isConnected}
        user={user}
        onNewChatPress={handleStartNewChat}
        onSettingsPress={() => setModalVisible(true)}
        onOpenHistory={() => navigation.navigate('History')}
        onOpenAuth={() => navigation.navigate('Auth')}
      />

      <StatusBanner
        backendUrl={backendUrl}
        isConnected={isConnected}
        latency={latency}
        onPress={() => setModalVisible(true)}
      />

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

      <MessageComposer
        onSend={handleSend}
        disabled={loading}
        isLoading={loading}
        suggestions={messages.length <= 3 ? QUICK_SUGGESTIONS : []}
      />

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
    backgroundColor: colors.background,
  },
  messageList: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.md,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm,
    gap: spacing.xs,
  },
  loadingText: {
    fontSize: 12,
    color: colors.primary,
    fontStyle: 'italic',
  },
});
