/**
 * android/src/services/chatManager.js
 *
 * Persistent App-Level Chat & Generation Manager for Yatra AI Android.
 *
 * Architectural Guarantee:
 * - Submitting a prompt initiates a background request that continues even if
 *   the user navigates away to Booking, Transport, Accommodation, Destinations, or Weather.
 * - Navigating back to the Assistant immediately restores the ongoing generation or completed response.
 * - Starting a "New Chat" cleanly isolates the new session without corrupting past conversations.
 */

import {
  sendChatMessage,
  saveConversation,
  getChatHistory,
} from './api.js';
import {
  saveLocalChatMessages,
  saveLocalGuestConversation,
  getAuthToken,
  getLocalChatMessages,
} from '../utils/storage.js';

export const INITIAL_WELCOME_MESSAGE = {
  id: 'welcome-1',
  role: 'assistant',
  content:
    'Jai Mata Di! Welcome to Yatra AI — your intelligent pilgrimage guide for Shri Mata Vaishno Devi Ji.\n\nI can assist you with:\n- **Darshan & Aarti Timings**\n- **Live Elevation-Aware Weather**\n- **Train, Bus & Helicopter Schedules**\n- **Verified Accommodation & Shrine Board Bhawans**\n- **Guided Booking Simulation**\n\nHow may I assist your holy pilgrimage today?',
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
};

class ChatManager {
  constructor() {
    this.activeSessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    this.messages = [INITIAL_WELCOME_MESSAGE];
    this.isGenerating = false;
    this.activeTripRequest = null;
    this.listeners = new Set();
    this.activePromise = null;
  }

  /**
   * Returns a snapshot of the current manager state
   */
  getState() {
    return {
      activeSessionId: this.activeSessionId,
      messages: [...this.messages],
      isGenerating: this.isGenerating,
      activeTripRequest: this.activeTripRequest,
    };
  }

  /**
   * Subscribes a component (e.g. ChatScreen) to state updates.
   * Returns an unsubscribe function.
   */
  subscribe(listener) {
    if (typeof listener !== 'function') return () => {};
    this.listeners.add(listener);
    // Immediately emit current state to newly attached listener
    try {
      listener(this.getState());
    } catch {
      // ignore
    }
    return () => {
      this.listeners.delete(listener);
    };
  }

  notify() {
    const snapshot = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(snapshot);
      } catch {
        // ignore subscriber errors
      }
    });
  }

  /**
   * Starts a clean new chat session without contaminating previous conversations
   */
  startNewChat() {
    this.activeSessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    this.messages = [INITIAL_WELCOME_MESSAGE];
    this.isGenerating = false;
    this.activeTripRequest = null;
    this.notify();
  }

  /**
   * Loads an existing conversation session
   */
  async loadConversation(sessionId, initialMessages = null, tripRequest = null) {
    if (!sessionId) return;
    this.activeSessionId = sessionId;
    if (tripRequest) {
      this.activeTripRequest = tripRequest;
    }

    if (Array.isArray(initialMessages) && initialMessages.length > 0) {
      this.messages = this.formatIncomingMessages(initialMessages);
      this.notify();
      return;
    }

    try {
      const data = await getChatHistory(sessionId);
      if (data && data.messages && data.messages.length > 0) {
        this.messages = this.formatIncomingMessages(data.messages);
      }
      if (data && data.trip_request) {
        this.activeTripRequest = data.trip_request;
      }
    } catch {
      // keep current or fallback
    }
    this.notify();
  }

  formatIncomingMessages(rawList) {
    if (!Array.isArray(rawList) || rawList.length === 0) return [INITIAL_WELCOME_MESSAGE];
    return rawList.map((m, idx) => ({
      id: m.id || `msg-${idx}-${Date.now()}`,
      role: m.role || 'assistant',
      content: m.content || '',
      recommendation: m.recommendation || null,
      itinerary: m.itinerary || (m.plan ? m.plan.itinerary : null),
      plan: m.plan || null,
      request: m.request || null,
      destination_images: m.destination_images || null,
      matched_destination: m.matched_destination || null,
      bookingHandoff: m.bookingHandoff || null,
      timestamp:
        m.timestamp ||
        (m.created_at
          ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
    }));
  }

  /**
   * Sends a prompt to the backend AI assistant.
   * Runs in the background and continues persisting even if the user navigates away.
   */
  async sendMessage(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    const currentSession = this.activeSessionId;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: cleanText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    this.messages = [...this.messages, userMessage];
    this.isGenerating = true;
    this.notify();

    try {
      const response = await sendChatMessage(cleanText, currentSession);

      // Verify that this manager is still on the same session
      if (this.activeSessionId === currentSession && response && response.response) {
        if (response.session_id) {
          this.activeSessionId = response.session_id;
        }
        if (response.request) {
          this.activeTripRequest = response.request;
        }

        const hasBooking =
          cleanText.toLowerCase().includes('book') ||
          cleanText.toLowerCase().includes('parchi') ||
          cleanText.toLowerCase().includes('ticket') ||
          cleanText.toLowerCase().includes('helicopter') ||
          response.response.toLowerCase().includes('booking handoff') ||
          response.response.toLowerCase().includes('parchi');

        const aiMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.response,
          recommendation: response.recommendation || null,
          itinerary: response.itinerary || (response.plan ? response.plan.itinerary : null),
          plan: response.plan || null,
          request: response.request || null,
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

        this.messages = [...this.messages, aiMessage];
        this.isGenerating = false;
        this.notify();

        // Persist messages in local and remote stores
        this.persistMessages(this.messages, this.activeSessionId, this.activeTripRequest);
        return aiMessage;
      }
    } catch (err) {
      if (this.activeSessionId === currentSession) {
        const isNetworkIssue =
          err.name === 'AbortError' ||
          (err.message &&
            (err.message.includes('Network') ||
              err.message.includes('timed out') ||
              err.message.includes('Failed to fetch') ||
              err.message.includes('offline')));

        const errorMsg = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: isNetworkIssue
            ? '⚠️ Could not reach the Yatra AI pilgrimage server. Please verify your connection or backend URL.'
            : `⚠️ ${err.message || 'An error occurred while communicating with Yatra AI.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        this.messages = [...this.messages, errorMsg];
        this.isGenerating = false;
        this.notify();
      }
    }
  }

  async persistMessages(msgs, sid, tripReq) {
    if (!msgs || msgs.length <= 1 || !sid) return;

    try {
      await saveLocalChatMessages(msgs);
      const firstUserMsg = msgs.find((m) => m.role === 'user');
      const title = firstUserMsg?.content
        ? firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : '')
        : 'Pilgrimage Consultation';

      await saveLocalGuestConversation({
        conversation_id: sid,
        title,
        messages: msgs,
        trip_request: tripReq,
        preview: firstUserMsg?.content || 'Pilgrimage consultation with Yatra AI',
      });

      const token = await getAuthToken();
      if (token) {
        await saveConversation(title, msgs, sid, tripReq, null);
      }
    } catch {
      // non-fatal persistence failure
    }
  }
}

// Global Singleton Instance
export const chatManager = new ChatManager();
export default chatManager;
