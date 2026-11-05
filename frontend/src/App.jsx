import React, { useState, useEffect } from 'react';
import ChatHeader from './components/chat/ChatHeader';
import HistoryDrawer from './components/chat/HistoryDrawer';
import AIChat from './components/AIChat';
import YatraBooking from './pages/YatraBooking';
import SightseeingBrowser from './components/SightseeingBrowser';
import AuthModal from './components/AuthModal';
import SavedTripsModal from './components/SavedTripsModal';
import { getAuthMe, logout, setAuthToken } from './services/api';
import './App.css';

export default function App() {
  // Conversational Assistant is the primary default experience
  const [activeTab, setActiveTab] = useState('assistant'); // 'assistant' | 'booking' | 'sightseeing'
  const [bookingParams, setBookingParams] = useState(null);
  const [assistantInitialQuery, setAssistantInitialQuery] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [hasMountedBooking, setHasMountedBooking] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Optional Passwordless Authentication & User State (Default Guest Mode)
  const [currentUser, setCurrentUser] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showSavedTripsModal, setShowSavedTripsModal] = useState(false);

  // Check existing session silently on load without blocking guest access
  useEffect(() => {
    let isMounted = true;
    getAuthMe()
      .then((res) => {
        if (isMounted && res.authenticated && res.user) {
          setCurrentUser(res.user);
        } else if (isMounted && !res.authenticated) {
          setAuthToken(null);
        }
      })
      .catch(() => {
        // Unauthenticated guest is normal; do not show error
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Ignore
    } finally {
      setAuthToken(null);
    }
    setCurrentUser(null);
    setShowSavedTripsModal(false);
  };

  const handleStartBooking = (params = null) => {
    if (params) {
      setBookingParams(params);
    }
    setHasMountedBooking(true);
    setActiveTab('booking');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleExplorePlaceQuery = (query) => {
    setAssistantInitialQuery(query);
    setActiveTab('assistant');
  };

  const handleOpenConversation = (convData) => {
    setActiveConversation(convData);
    setShowSavedTripsModal(false);
    setIsHistoryOpen(false);
    setActiveTab('assistant');
  };

  const handleStartFreshChat = () => {
    setActiveConversation(null);
    setAssistantInitialQuery(null);
    setActiveTab('assistant');
    try {
      const newSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      sessionStorage.setItem('yatra_session_id', newSid);
      sessionStorage.removeItem('yatra_chat_messages');
      sessionStorage.removeItem('yatra_chat_messages_session_id');
    } catch {
      // ignore
    }
  };

  return (
    <div
      style={{
        height: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--bg-main, #FDFBF7)',
      }}
    >
      {/* Top Header */}
      <ChatHeader
        activeTab={activeTab === 'home' ? 'assistant' : activeTab}
        setActiveTab={(tab) => {
          if (tab === 'booking') {
            setHasMountedBooking(true);
            setActiveTab('booking');
          } else if (tab === 'home' || tab === 'assistant') {
            setActiveTab('assistant');
          } else {
            setActiveTab(tab);
          }
        }}
        user={currentUser}
        onOpenAuthModal={() => setShowAuthModal(true)}
        onOpenSavedTrips={() => setShowSavedTripsModal(true)}
        onLogout={handleLogout}
        onToggleHistory={() => setIsHistoryOpen((prev) => !prev)}
        onStartNewChat={handleStartFreshChat}
        isHistoryOpen={isHistoryOpen}
      />

      {/* Main Conversational Workspace */}
      <main
        style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: activeTab === 'assistant' ? 'hidden' : 'auto',
        }}
      >
        {/* 1. Primary AI Assistant View (Full-Screen Conversational Experience) */}
        {(activeTab === 'assistant' || activeTab === 'home') && (
          <AIChat
            initialMessage={assistantInitialQuery}
            loadedConversation={activeConversation}
            onClearLoadedConversation={() => setActiveConversation(null)}
            sharedSessionId={activeConversation?.conversation_id || null}
            onNavigateToBooking={(payload) => handleStartBooking(payload)}
            onExplorePlace={(placeName) => handleExplorePlaceQuery(`Tell me about ${placeName}`)}
          />
        )}

        {/* 2. Guided Darshan Booking Experience */}
        {(hasMountedBooking || activeTab === 'booking') && (
          <div
            style={{
              display: activeTab === 'booking' ? 'block' : 'none',
              padding: '1rem',
              maxWidth: '1200px',
              margin: '0 auto',
              width: '100%',
            }}
          >
            <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button
                type="button"
                onClick={() => setActiveTab('assistant')}
                className="btn btn-secondary"
                style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}
              >
                <span>←</span>
                <span>Return to Yatra AI Companion</span>
              </button>
            </div>
            <YatraBooking
              initialSearchParams={bookingParams}
              currentUser={currentUser}
              onRequireAuth={() => setShowAuthModal(true)}
              onReturnHome={() => {
                setActiveTab('assistant');
              }}
            />
          </div>
        )}

        {/* 3. Sightseeing Destinations Catalog */}
        {activeTab === 'sightseeing' && (
          <div
            style={{
              padding: '1rem',
              maxWidth: '1200px',
              margin: '0 auto',
              width: '100%',
              paddingBottom: '3rem',
            }}
          >
            <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button
                type="button"
                onClick={() => setActiveTab('assistant')}
                className="btn btn-secondary"
                style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}
              >
                <span>←</span>
                <span>Return to Yatra AI Companion</span>
              </button>
            </div>
            <SightseeingBrowser
              isStandalone={true}
              onExplorePlace={handleExplorePlaceQuery}
              onPlanYatra={(selectedPlaces) => {
                handleStartBooking({
                  sightseeing_choice: 'custom',
                  sightseeing_places: selectedPlaces,
                });
              }}
              onBack={() => {
                setActiveTab('assistant');
              }}
            />
          </div>
        )}
      </main>

      {/* Collapsible History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectConversation={handleOpenConversation}
        onStartNewChat={handleStartFreshChat}
        user={currentUser}
        onOpenAuthModal={() => setShowAuthModal(true)}
        activeSessionId={activeConversation?.conversation_id || null}
      />

      {/* Passwordless Email Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onAuthSuccess={(user, token) => {
          setCurrentUser(user);
          if (token) setAuthToken(token);
        }}
      />

      {/* Authenticated User Saved Trips Modal (Account, Bookings, Itineraries, Conversations) */}
      <SavedTripsModal
        isOpen={showSavedTripsModal}
        onClose={() => setShowSavedTripsModal(false)}
        user={currentUser}
        onLoadItinerary={(itineraryData) => {
          setBookingParams(itineraryData);
          setHasMountedBooking(true);
          setActiveTab('booking');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        onLoadConversation={handleOpenConversation}
      />
    </div>
  );
}
