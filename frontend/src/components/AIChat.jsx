import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, AlertTriangle, Sparkles } from 'lucide-react';
import { sendChat, streamChat, getChatHistory, saveConversation, saveLocalGuestConversation } from '../services/api';
import WelcomeScreen from './chat/WelcomeScreen';
import MessageItem from './chat/MessageItem';
import MessageComposer from './chat/MessageComposer';

const DEFAULT_GREETING = {
  id: 'default-greeting',
  role: 'assistant',
  content: '**Jai Mata Di!** Welcome to **Yatra AI**. How may I assist you with your sacred yatra planning, travel routes, weather, accommodation, or darshan booking assistance?',
  created_at: null,
};

const createLocalMessageId = () => `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
const getNowIsoString = () => new Date().toISOString();

export default function AIChat({
  user = null,
  onNavigateToBooking,
  initialMessage = null,
  onExplorePlace = null,
  sharedTripRequest = null,
  sharedSessionId = null,
  sharedPlanVersion = 1,
  onTripUpdated = null,
  onSwitchToForm = null,
  loadedConversation = null,
  onClearLoadedConversation = null,
  onRequestSaveAuth = null,
}) {
  const [messages, setMessages] = useState(() => {
    try {
      const targetSessionId = sharedSessionId || sessionStorage.getItem('yatra_session_id');
      const savedMsgSessionId = sessionStorage.getItem('yatra_chat_messages_session_id');
      if (targetSessionId && savedMsgSessionId && targetSessionId !== savedMsgSessionId) {
        return [DEFAULT_GREETING];
      }
      const saved = sessionStorage.getItem('yatra_chat_messages');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.map((m) => ({ ...m, isPending: false }));
        }
      }
    } catch {
      // ignore
    }
    return [DEFAULT_GREETING];
  });

  const [loading, setLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [historyRetryCount, setHistoryRetryCount] = useState(0);

  const [chatState, setChatState] = useState(() => {
    try {
      const saved = sessionStorage.getItem('yatra_chat_state');
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return {
      session_id: sharedSessionId || sessionStorage.getItem('yatra_session_id') || null,
      plan_version: sharedPlanVersion || parseInt(sessionStorage.getItem('yatra_plan_version') || '1', 10),
      current_request: sharedTripRequest || null,
      current_itinerary: null,
      feasible_places: [],
      infeasible_places: [],
      last_tourism_place: null,
      last_itinerary_context: null,
      pending_options: null,
    };
  });

  const [prevSharedProps, setPrevSharedProps] = useState({
    planVersion: sharedPlanVersion,
    tripRequest: sharedTripRequest,
  });

  if (
    sharedPlanVersion !== prevSharedProps.planVersion ||
    sharedTripRequest !== prevSharedProps.tripRequest
  ) {
    setPrevSharedProps({
      planVersion: sharedPlanVersion,
      tripRequest: sharedTripRequest,
    });
    setChatState((prev) => ({
      ...prev,
      plan_version: sharedPlanVersion || prev.plan_version,
      current_request: sharedTripRequest ? { ...prev.current_request, ...sharedTripRequest } : prev.current_request,
    }));
  }

  const messagesEndRef = useRef(null);
  const latestMessageRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const isSubmittingRef = useRef(false);
  const historyLoadedSessionRef = useRef(null);
  const currentSessionIdRef = useRef(sharedSessionId || sessionStorage.getItem('yatra_session_id') || null);
  const activeFetchRequestIdRef = useRef(0);
  const isFetchingHistoryRef = useRef(false);
  const pendingMessageIdsRef = useRef(new Set());
  const isNearBottomRef = useRef(true);

  const handleMessagesScroll = () => {
    const el = messagesContainerRef.current;
    if (el) {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      isNearBottomRef.current = distanceFromBottom < 80;
    }
  };

  // Synchronize active session prop changes
  useEffect(() => {
    if (loadedConversation && loadedConversation.conversation_id === sharedSessionId) {
      return;
    }
    if (sharedSessionId && sharedSessionId !== currentSessionIdRef.current) {
      currentSessionIdRef.current = sharedSessionId;
      historyLoadedSessionRef.current = null;
      isFetchingHistoryRef.current = false;
      pendingMessageIdsRef.current.clear();
      setHistoryError(false);
      activeFetchRequestIdRef.current += 1;

      setMessages([DEFAULT_GREETING]);
      setChatState((prev) => ({
        ...prev,
        session_id: sharedSessionId,
        plan_version: sharedPlanVersion || 1,
        current_request: sharedTripRequest ? { ...prev.current_request, ...sharedTripRequest } : null,
        current_itinerary: null,
        feasible_places: [],
        infeasible_places: [],
        pending_options: null,
      }));
    }
  }, [sharedSessionId, sharedPlanVersion, sharedTripRequest]);

  // Robust session-aware history restoration
  useEffect(() => {
    const targetSessionId = sharedSessionId || chatState.session_id;
    if (!targetSessionId) return;
    if (historyLoadedSessionRef.current === targetSessionId) return;
    if (isFetchingHistoryRef.current) return;

    currentSessionIdRef.current = targetSessionId;
    isFetchingHistoryRef.current = true;
    const fetchId = ++activeFetchRequestIdRef.current;

    getChatHistory(targetSessionId)
      .then((res) => {
        isFetchingHistoryRef.current = false;
        if (activeFetchRequestIdRef.current !== fetchId) return;
        if (currentSessionIdRef.current !== targetSessionId) return;

        historyLoadedSessionRef.current = targetSessionId;
        setHistoryError(false);

        if (!res || !Array.isArray(res.messages)) {
          return;
        }

        const backendMsgs = res.messages;

        setMessages((prev) => {
          if (backendMsgs.length === 0) {
            const isGreetingOnly = prev.length === 1 && prev[0].id === 'default-greeting';
            if (prev.length === 0 || isGreetingOnly) {
              return [DEFAULT_GREETING];
            }
            return prev;
          }

          const formattedBackend = backendMsgs.map((m) => {
            const meta = m.metadata || {};
            return {
              id: m.id,
              role: m.role,
              content: m.content,
              recommendation: meta.recommendation || null,
              plan: meta.plan || null,
              request: meta.request || null,
              itinerary: meta.itinerary || meta.plan?.itinerary || null,
              feasible_places: meta.feasible_places || [],
              infeasible_places: meta.infeasible_places || [],
              knowledge_sources: meta.knowledge_sources || null,
              source_provenance: meta.source_provenance || meta.data_provenance || null,
              data_provenance: meta.data_provenance || meta.source_provenance || null,
              live_sources: meta.live_sources || null,
              is_cached: Boolean(meta.is_cached),
              tool_executions: meta.tool_executions || null,
              partial_failure: Boolean(meta.partial_failure),
              execution_mode: meta.execution_mode || null,
              weather: meta.weather || meta.live_weather || null,
              destination_images: meta.destination_images || null,
              matched_destination: meta.matched_destination || null,
              created_at: m.created_at,
              persisted: true,
              isPending: false,
            };
          });

          const latestPlanMsg = [...backendMsgs].reverse().find((m) => m.metadata && (m.metadata.plan || m.metadata.itinerary || m.metadata.request));
          if (latestPlanMsg && latestPlanMsg.metadata) {
            const lMeta = latestPlanMsg.metadata;
            setChatState((prev) => ({
              ...prev,
              session_id: targetSessionId,
              plan_version: lMeta.plan_version || prev.plan_version || 1,
              current_request: lMeta.request || prev.current_request,
              current_itinerary: lMeta.itinerary || lMeta.plan?.itinerary || prev.current_itinerary,
              feasible_places: lMeta.feasible_places || prev.feasible_places,
              infeasible_places: lMeta.infeasible_places || prev.infeasible_places,
              pending_options: lMeta.plan?.options || prev.pending_options,
              selected_option: lMeta.plan?.selected_option || prev.selected_option,
              hotel: lMeta.plan?.hotel || prev.hotel,
              budget_evaluation: lMeta.budget_evaluation || lMeta.plan?.budget_evaluation || prev.budget_evaluation,
            }));
          }

          const localPending = prev.filter(
            (p) => Boolean(p.isPending) && pendingMessageIdsRef.current.has(p.id)
          );

          if (localPending.length === 0) {
            return formattedBackend;
          }

          return [...formattedBackend, ...localPending];
        });
      })
      .catch((err) => {
        isFetchingHistoryRef.current = false;
        if (activeFetchRequestIdRef.current !== fetchId) return;
        if (currentSessionIdRef.current !== targetSessionId) return;
        console.warn('Failed to fetch chat history:', err);
        setHistoryError(true);
      });

    return () => {
      isFetchingHistoryRef.current = false;
      if (activeFetchRequestIdRef.current === fetchId) {
        activeFetchRequestIdRef.current += 1;
      }
    };
  }, [sharedSessionId, chatState.session_id, historyRetryCount]);

  const handleRetryHistory = () => {
    setHistoryError(false);
    historyLoadedSessionRef.current = null;
    isFetchingHistoryRef.current = false;
    setHistoryRetryCount((c) => c + 1);
  };

  // Handle restoring a saved conversation when opened from History or SavedTripsModal
  useEffect(() => {
    if (!loadedConversation) return;
    const cid = loadedConversation.conversation_id;
    if (!cid) return;

    currentSessionIdRef.current = cid;
    historyLoadedSessionRef.current = cid;
    isFetchingHistoryRef.current = false;
    setHistoryError(false);
    activeFetchRequestIdRef.current += 1;

    const rawMsgs = Array.isArray(loadedConversation.messages) ? loadedConversation.messages : [];
    const formatted = rawMsgs.map((m, idx) => {
      const meta = m.metadata || {};
      return {
        id: m.id || `restored-${idx}-${Date.now()}`,
        role: m.role || 'assistant',
        content: m.content || '',
        recommendation: m.recommendation || meta.recommendation || null,
        plan: m.plan || meta.plan || null,
        request: m.request || meta.request || null,
        intent: m.intent || meta.intent || null,
        showDatePicker: Boolean(m.showDatePicker || meta.showDatePicker),
        available_hotels: m.available_hotels || meta.available_hotels || null,
        itinerary: m.itinerary || meta.itinerary || meta.plan?.itinerary || null,
        feasible_places: m.feasible_places || meta.feasible_places || [],
        infeasible_places: m.infeasible_places || meta.infeasible_places || [],
        knowledge_sources: m.knowledge_sources || meta.knowledge_sources || null,
        source_provenance: m.source_provenance || meta.source_provenance || m.data_provenance || meta.data_provenance || null,
        data_provenance: m.data_provenance || meta.data_provenance || m.source_provenance || meta.source_provenance || null,
        live_sources: m.live_sources || meta.live_sources || null,
        is_cached: Boolean(m.is_cached !== undefined ? m.is_cached : meta.is_cached),
        tool_executions: m.tool_executions || meta.tool_executions || null,
        partial_failure: Boolean(m.partial_failure !== undefined ? m.partial_failure : meta.partial_failure),
        execution_mode: m.execution_mode || meta.execution_mode || null,
        weather: m.weather || meta.weather || null,
        destination_images: m.destination_images || meta.destination_images || null,
        matched_destination: m.matched_destination || meta.matched_destination || null,
        created_at: m.created_at || getNowIsoString(),
        persisted: true,
        isPending: false,
      };
    });

    setMessages(formatted.length > 0 ? formatted : [DEFAULT_GREETING]);

    const latestPlanMsg = [...rawMsgs].reverse().find((m) => m.metadata && (m.metadata.plan || m.metadata.itinerary || m.metadata.request));
    const lMeta = latestPlanMsg?.metadata || {};
    const tripReq = loadedConversation.trip_request || lMeta.request || null;
    const itin = loadedConversation.itinerary || lMeta.itinerary || lMeta.plan?.itinerary || null;

    setChatState((prev) => ({
      ...prev,
      session_id: cid,
      plan_version: lMeta.plan_version || prev.plan_version || 1,
      current_request: tripReq || prev.current_request,
      current_itinerary: itin || prev.current_itinerary,
      feasible_places: lMeta.feasible_places || prev.feasible_places,
      infeasible_places: lMeta.infeasible_places || prev.infeasible_places,
      pending_options: lMeta.plan?.options || prev.pending_options,
      selected_option: lMeta.plan?.selected_option || prev.selected_option,
      hotel: lMeta.plan?.hotel || prev.hotel,
      budget_evaluation: lMeta.budget_evaluation || lMeta.plan?.budget_evaluation || prev.budget_evaluation,
    }));

    try {
      sessionStorage.setItem('yatra_session_id', cid);
      sessionStorage.setItem('yatra_chat_messages', JSON.stringify(formatted));
      sessionStorage.setItem('yatra_chat_messages_session_id', cid);
    } catch {
      // ignore
    }
  }, [loadedConversation]);

  const handleStartNewChat = () => {
    if (onClearLoadedConversation) {
      onClearLoadedConversation();
    }
    const newSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    currentSessionIdRef.current = newSid;
    historyLoadedSessionRef.current = newSid;
    try {
      sessionStorage.setItem('yatra_session_id', newSid);
      sessionStorage.removeItem('yatra_chat_messages');
      sessionStorage.removeItem('yatra_chat_messages_session_id');
    } catch {
      // ignore
    }
    setMessages([DEFAULT_GREETING]);
    setChatState({
      session_id: newSid,
      plan_version: 1,
      current_request: null,
      current_itinerary: null,
      feasible_places: [],
      infeasible_places: [],
      last_tourism_place: null,
      last_itinerary_context: null,
      pending_options: null,
    });
  };

  // Smooth scroll management
  useEffect(() => {
    if (loading) {
      if (isNearBottomRef.current) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      const isUser = lastMsg && lastMsg.role === 'user';
      if (isUser) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else if (isNearBottomRef.current) {
        latestMessageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    if (isSubmittingRef.current) return;
    const text = (textToSend || '').trim();
    if (!text || loading) return;

    isSubmittingRef.current = true;
    setIsSubmitting(true);

    const userMsg = {
      id: createLocalMessageId(),
      role: 'user',
      content: text,
      created_at: getNowIsoString(),
      persisted: false,
      isPending: true,
    };
    pendingMessageIdsRef.current.add(userMsg.id);
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const assistantMsgId = createLocalMessageId();
      let streamedText = '';
      let hasStreamedToken = false;

      let data;
      try {
        data = await streamChat(
          {
            message: text,
            session_id: chatState.session_id,
            current_request: chatState.current_request,
            current_itinerary: chatState.current_itinerary,
            last_tourism_place: chatState.last_tourism_place,
            last_itinerary_context: chatState.last_itinerary_context,
            pending_options: chatState.pending_options,
          },
          {
            onToken: (chunk) => {
              streamedText += chunk;
              if (!hasStreamedToken) {
                hasStreamedToken = true;
                setLoading(false);
                setMessages((prev) => [
                  ...prev.map((m) => (m.id === userMsg.id ? { ...m, isPending: false } : m)),
                  {
                    id: assistantMsgId,
                    role: 'assistant',
                    content: streamedText,
                    isStreaming: true,
                    created_at: getNowIsoString(),
                    persisted: false,
                    isPending: false,
                  },
                ]);
              } else {
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantMsgId ? { ...m, content: streamedText } : m))
                );
              }
            },
          }
        );
      } catch (streamErr) {
        console.warn('Stream failed or unavailable, falling back to POST /api/chat:', streamErr);
        data = await sendChat({
          message: text,
          session_id: chatState.session_id,
          current_request: chatState.current_request,
          current_itinerary: chatState.current_itinerary,
          last_tourism_place: chatState.last_tourism_place,
          last_itinerary_context: chatState.last_itinerary_context,
          pending_options: chatState.pending_options,
        });
      }

      const feasiblePlaces = data.feasible_places || data.plan?.feasible_places || [];
      const infeasiblePlaces = data.infeasible_places || data.plan?.infeasible_places || [];

      const assistantMsg = {
        id: assistantMsgId,
        role: 'assistant',
        content: data.reply || streamedText || 'Jai Mata Di! How else can I assist your sacred pilgrimage?',
        recommendation: data.recommendation || null,
        plan: data.plan || null,
        request: data.request || null,
        intent: data.intent || null,
        showDatePicker: Boolean(data.showDatePicker),
        available_hotels: data.available_hotels || data.plan?.available_hotels || null,
        operational_notices: data.operational_notices || data.operational_notice || null,
        verified_contacts: data.verified_contacts || data.verified_contact || null,
        action: data.action || null,
        status: data.status || null,
        step: data.step || null,
        options: data.options || null,
        selected_option: data.selected_option || null,
        hotel: data.hotel || null,
        budget_evaluation: data.budget_evaluation || null,
        knowledge_sources: data.knowledge_sources || null,
        source_provenance: data.source_provenance || data.data_provenance || null,
        data_provenance: data.data_provenance || data.source_provenance || null,
        live_sources: data.live_sources || null,
        is_cached: Boolean(data.is_cached),
        tool_executions: data.tool_executions || null,
        partial_failure: Boolean(data.partial_failure),
        execution_mode: data.execution_mode || null,
        weather: data.weather || data.live_weather || null,
        destination_images: data.destination_images || data.images || null,
        matched_destination: data.matched_destination || data.destination || null,
        feasible_places: feasiblePlaces,
        infeasible_places: infeasiblePlaces,
        created_at: getNowIsoString(),
        persisted: false,
        isPending: false,
        isStreaming: false,
      };

      setMessages((prev) => {
        const withoutPending = prev.map((m) => (m.id === userMsg.id ? { ...m, isPending: false } : m));
        const existingIdx = withoutPending.findIndex((m) => m.id === assistantMsgId);
        if (existingIdx !== -1) {
          const updated = [...withoutPending];
          updated[existingIdx] = assistantMsg;
          return updated;
        }
        return [...withoutPending, assistantMsg];
      });

      if (data.session_id) {
        historyLoadedSessionRef.current = data.session_id;
        currentSessionIdRef.current = data.session_id;
      }

      setChatState((prev) => ({
        ...prev,
        session_id: data.session_id || prev.session_id,
        plan_version: data.plan_version || prev.plan_version || 1,
        current_request: data.reset === true ? null : ((data.request !== undefined && data.request !== null) ? data.request : prev.current_request),
        current_itinerary: data.reset === true ? null : ((data.itinerary !== undefined && data.itinerary !== null) ? data.itinerary : prev.current_itinerary),
        feasible_places: feasiblePlaces.length > 0 ? feasiblePlaces : prev.feasible_places,
        infeasible_places: infeasiblePlaces.length > 0 ? infeasiblePlaces : (data.plan ? [] : prev.infeasible_places),
        last_tourism_place: data.last_tourism_place || prev.last_tourism_place,
        last_itinerary_context: data.last_itinerary_context || prev.last_itinerary_context,
        pending_options: data.plan?.options ? data.plan.options : prev.pending_options,
        selected_option: data.plan?.selected_option || (data.plan?.options && data.plan.options[0]) || prev.selected_option || null,
        hotel: data.plan?.hotel || prev.hotel || null,
        budget_evaluation: data.budget_evaluation || data.plan?.budget_evaluation || prev.budget_evaluation || null,
      }));

      if (onTripUpdated) {
        onTripUpdated({
          request: (data.request !== undefined && data.request !== null) ? data.request : (data.reset === true ? null : chatState.current_request),
          plan: data.plan,
          session_id: data.session_id,
          plan_version: data.plan_version,
          itinerary: data.itinerary || data.plan?.itinerary,
          action: data.action || null,
          status: data.status || null,
          step: data.step || null,
          options: data.options || null,
          selected_option: data.selected_option || null,
          hotel: data.hotel || null,
          budget_evaluation: data.budget_evaluation || null,
          feasible_places: feasiblePlaces,
          infeasible_places: infeasiblePlaces,
          recommendation: data.recommendation,
          pending_options: data.plan?.options,
        });
      }

      // Automatic handoff to guided booking flow upon booking intent
      if (data.action === 'NAVIGATE_TO_BOOKING' || data.status === 'NAVIGATE_TO_BOOKING') {
        const planOpts = data.options || data.plan?.options || chatState.pending_options || null;
        const selOpt = data.selected_option || data.plan?.selected_option || chatState.selected_option || (planOpts && planOpts.length > 0 ? planOpts[0] : null);
        const req = data.request || chatState.current_request || null;
        const itin = data.itinerary || data.plan?.itinerary || chatState.current_itinerary || null;
        const htl = data.hotel || data.plan?.hotel || chatState.hotel || null;
        const bgt = data.budget_evaluation || data.plan?.budget_evaluation || chatState.budget_evaluation || null;

        const navPayload = {
          sessionId: data.session_id || chatState.session_id,
          planVersion: data.plan_version || chatState.plan_version || 1,
          feasible_places: feasiblePlaces,
          infeasible_places: infeasiblePlaces,
          itinerary: itin,
          request: req,
          sightseeing_choice: req?.sightseeing_choice || null,
          options: planOpts,
          selected_option: selOpt,
          hotel: htl,
          budget_evaluation: bgt,
          planningMode: 'form',
          step: data.step || ((planOpts && planOpts.length > 0) ? 2 : 1),
        };

        if (onNavigateToBooking) {
          onNavigateToBooking(navPayload);
        } else if (onSwitchToForm) {
          onSwitchToForm(navPayload);
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      const isTimeout = err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'));
      const isMisconfigured = err?.message && (
        err.message.includes('Production API URL') ||
        err.message.includes('Insecure backend URL') ||
        err.message.includes('Malformed API URL')
      );
      const friendlyMessage = isMisconfigured
        ? `**Backend Not Connected:** ${err.message}`
        : (isTimeout
          ? '**Request Timed Out:** The pilgrimage coordinator took longer than expected to respond. Please check your connection and try again.'
          : '**Connection Issue:** Unable to reach the pilgrimage service. Please verify the backend is running and try again.');
      setMessages((prev) => [
        ...prev.map((m) => (m.id === userMsg.id ? { ...m, isPending: false } : m)),
        {
          id: createLocalMessageId(),
          role: 'assistant',
          content: friendlyMessage,
          isError: true,
          failedQuery: text,
          created_at: getNowIsoString(),
          isPending: false,
        },
      ]);
    } finally {
      pendingMessageIdsRef.current.delete(userMsg.id);
      isSubmittingRef.current = false;
      setIsSubmitting(false);
      setLoading(false);
    }
  };

  const handleSendRef = useRef(handleSend);
  useEffect(() => {
    handleSendRef.current = handleSend;
  });
  const lastInitialMessageRef = useRef(null);

  useEffect(() => {
    if (initialMessage && initialMessage !== lastInitialMessageRef.current) {
      lastInitialMessageRef.current = initialMessage;
      const timer = setTimeout(() => {
        handleSendRef.current?.(initialMessage);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [initialMessage]);

  useEffect(() => {
    try {
      sessionStorage.setItem('yatra_chat_messages', JSON.stringify(messages));
      const activeSid = sharedSessionId || chatState.session_id;
      if (activeSid) {
        sessionStorage.setItem('yatra_chat_messages_session_id', activeSid);
      }
    } catch {}
  }, [messages, sharedSessionId, chatState.session_id]);

  // ChatGPT-style auto-save on message updates: saves to MongoDB if authenticated, or localStorage if guest
  useEffect(() => {
    const nonGreetingMsgs = messages.filter((m) => m && m.id !== 'default-greeting');
    if (nonGreetingMsgs.length === 0) return;

    const activeSid = sharedSessionId || chatState.session_id;
    if (!activeSid) return;

    // Derive title from first user message
    const firstUserMsg = nonGreetingMsgs.find((m) => m.role === 'user');
    const firstLine = firstUserMsg?.content ? firstUserMsg.content.split('\n')[0].trim() : '';
    const derivedTitle = firstLine ? (firstLine.length > 45 ? `${firstLine.slice(0, 45)}...` : firstLine) : 'Pilgrimage Consultation';

    const saveObj = {
      conversation_id: activeSid,
      title: loadedConversation?.title || derivedTitle,
      created_at: loadedConversation?.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: messages,
      trip_request: chatState.current_request || null,
      itinerary: chatState.current_itinerary || null,
      message_count: messages.length,
    };

    if (user) {
      saveConversation(
        saveObj.title,
        messages,
        activeSid,
        saveObj.trip_request,
        saveObj.itinerary
      ).catch((err) => {
        console.debug('Background server auto-save notice:', err);
      });
    } else {
      saveLocalGuestConversation(saveObj);
    }
  }, [messages, user, chatState.session_id, sharedSessionId, chatState.current_request, chatState.current_itinerary]);

  useEffect(() => {
    try {
      sessionStorage.setItem('yatra_chat_state', JSON.stringify(chatState));
      if (chatState.session_id) {
        sessionStorage.setItem('yatra_session_id', chatState.session_id);
      }
      if (chatState.plan_version) {
        sessionStorage.setItem('yatra_plan_version', String(chatState.plan_version));
      }
    } catch {}
  }, [chatState]);

  const hasOnlyDefaultGreeting = messages.length <= 1 && (!messages[0] || messages[0].id === 'default-greeting');

  return (
    <div
      data-testid="aichat-full-workspace"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        position: 'relative',
        background: 'var(--bg-main, #FDFBF7)',
      }}
    >
      {/* Resumed Conversation Banner */}
      {loadedConversation && (
        <div
          data-testid="resumed-conversation-banner"
          style={{
            background: 'var(--gold-subtle, #F5ECDA)',
            borderBottom: '1.5px solid var(--gold-border, #E5D2AD)',
            padding: '8px 16px',
            fontSize: '0.8rem',
            color: 'var(--burgundy, #58111A)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
            <MessageSquare size={14} color="var(--burgundy)" />
            <span style={{ fontWeight: 800 }}>Resumed Conversation:</span>
            <span style={{ fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              "{loadedConversation.title || 'Saved Journey'}"
            </span>
          </div>
          <button
            type="button"
            data-testid="start-new-chat-btn"
            onClick={handleStartNewChat}
            style={{
              background: 'var(--burgundy, #58111A)',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '999px',
              padding: '4px 12px',
              fontSize: '0.74rem',
              fontWeight: 700,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            + New Chat
          </button>
        </div>
      )}

      {/* History Error Banner */}
      {historyError && (
        <div
          data-testid="chat-history-error-banner"
          style={{
            background: '#FFF8F6',
            borderBottom: '1px solid #F5C6CB',
            padding: '8px 16px',
            fontSize: '0.8rem',
            color: '#721C24',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={14} color="#721C24" />
            <span>Could not load earlier chat history.</span>
          </span>
          <button
            type="button"
            data-testid="chat-history-retry-btn"
            onClick={handleRetryHistory}
            style={{
              background: '#C0392B',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Message Stream Area */}
      <div
        ref={messagesContainerRef}
        onScroll={handleMessagesScroll}
        data-testid="chat-messages-stream"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: '1.25rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {/* Welcome Screen when conversation is empty / fresh */}
        {hasOnlyDefaultGreeting && (
          <WelcomeScreen onSelectPrompt={(promptText) => handleSend(promptText)} />
        )}

        {/* Conversation Turns (when messages exist) */}
        {!hasOnlyDefaultGreeting &&
          messages.map((m, i) => (
            <MessageItem
              key={m.id || i}
              message={m}
              index={i}
              isLatest={i === messages.length - 1}
              chatState={chatState}
              onSend={handleSend}
              onNavigateToBooking={onNavigateToBooking}
              onSwitchToForm={onSwitchToForm}
              onExplorePlace={onExplorePlace}
              onRequestSaveAuth={onRequestSaveAuth}
              latestMessageRef={latestMessageRef}
            />
          ))}

        {/* Loading / Thinking Indicator */}
        {loading && (
          <div
            role="status"
            aria-live="polite"
            style={{
              alignSelf: 'flex-start',
              background: '#FFFFFF',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              borderRadius: '16px',
              padding: '0.75rem 1.15rem',
              fontSize: '0.86rem',
              color: 'var(--burgundy, #58111A)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 2px 8px rgba(88, 17, 26, 0.04)',
              maxWidth: '820px',
              margin: '0 auto',
              width: '100%',
            }}
          >
            <Sparkles size={18} color="var(--burgundy, #58111A)" />
            <span style={{ fontWeight: 700 }}>Yatra AI is planning your journey...</span>
            <div className="typing-dots" aria-hidden="true" style={{ display: 'inline-flex', gap: '4px', marginLeft: '4px' }}>
              <span className="dot dot-1" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--burgundy)' }} />
              <span className="dot dot-2" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--burgundy)' }} />
              <span className="dot dot-3" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--burgundy)' }} />
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} style={{ height: '12px', flexShrink: 0 }} />
      </div>

      {/* Message Composer Anchored at Bottom */}
      <div style={{ flexShrink: 0, background: 'linear-gradient(to top, var(--bg-main) 70%, transparent 100%)' }}>
        <MessageComposer onSend={handleSend} loading={loading || isSubmitting} />
      </div>
    </div>
  );
}
