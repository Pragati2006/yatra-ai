import React, { useState, useEffect, lazy, Suspense } from 'react';
import { AlertTriangle, Info, CheckCircle2 } from 'lucide-react';
import ChatHeader from './components/chat/ChatHeader';
import HistoryDrawer from './components/chat/HistoryDrawer';
import AIChat from './components/AIChat';
import LandingScreen from './components/LandingScreen';

// Route-level and screen-level code-splitting for high-performance initial loading
const YatraBooking = lazy(() => import('./pages/YatraBooking'));
const SightseeingBrowser = lazy(() => import('./components/SightseeingBrowser'));
const WeatherView = lazy(() => import('./components/WeatherView'));
const AccommodationView = lazy(() => import('./components/AccommodationView'));
const TransportView = lazy(() => import('./components/TransportView'));
const SettingsView = lazy(() => import('./components/SettingsView'));
const AuthModal = lazy(() => import('./components/AuthModal'));
const SavedTripsModal = lazy(() => import('./components/SavedTripsModal'));

function ViewLoadingFallback({ label = 'Loading...' }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1.5rem',
        color: 'var(--royal-plum, #54152D)',
        minHeight: '220px',
      }}
    >
      <div
        style={{
          width: '28px',
          height: '28px',
          border: '3px solid var(--border-default, #E9DED6)',
          borderTopColor: 'var(--royal-plum, #54152D)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          marginBottom: '10px',
        }}
      />
      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary, #796D69)' }}>
        {label}
      </span>
    </div>
  );
}
import {
  getAuthMe,
  logout,
  setAuthToken,
  isApiConfigured,
  setRuntimeApiUrl,
  getApiBaseUrl,
  getPendingProposedUrl,
  dismissPendingProposedUrl,
  confirmProposedUrl,
  resolveApiConfig,
  isDevelopment,
  isProduction,
  saveConversation,
  getLocalGuestConversations,
  clearLocalGuestConversations,
} from './services/api';
import './App.css';

export default function App() {
  // Conversational Assistant is the primary default experience
  const [activeTab, setActiveTab] = useState('assistant'); // 'assistant' | 'booking' | 'sightseeing'
  const [bookingParams, setBookingParams] = useState(null);
  const [assistantInitialQuery, setAssistantInitialQuery] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [hasMountedBooking, setHasMountedBooking] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Active chat session key to allow pristine reset on "New Chat" while preserving streams across navigation
  const [activeChatSessionId, setActiveChatSessionId] = useState(() => {
    try {
      return sessionStorage.getItem('yatra_session_id') || `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    } catch {
      return `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    }
  });

  // Landing Screen Gate: First-time devotees see the simplified landing screen until they begin
  const [hasStartedJourney, setHasStartedJourney] = useState(() => {
    try {
      if (typeof window !== 'undefined') {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('skipLanding') === 'true' || urlParams.get('chat') === 'true') {
          return true;
        }
        if (sessionStorage.getItem('yatra_has_started') === 'true') {
          return true;
        }
        const saved = sessionStorage.getItem('yatra_chat_messages');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 1) {
            return true;
          }
        }
      }
    } catch {
      // ignore
    }
    return false;
  });

  // Security Gate: Proposed backend URL from query parameter requires explicit user confirmation
  const [pendingProposal, setPendingProposal] = useState(() => getPendingProposedUrl());

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
    if (convData?.conversation_id) {
      setActiveChatSessionId(convData.conversation_id);
    }
    setShowSavedTripsModal(false);
    setIsHistoryOpen(false);
    setActiveTab('assistant');
  };

  const handleStartFreshChat = () => {
    setActiveConversation(null);
    setAssistantInitialQuery(null);
    setActiveTab('assistant');
    const newSid = `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setActiveChatSessionId(newSid);
    try {
      sessionStorage.setItem('yatra_session_id', newSid);
      sessionStorage.removeItem('yatra_chat_messages');
      sessionStorage.removeItem('yatra_chat_messages_session_id');
      sessionStorage.removeItem('yatra_chat_state');
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
        activeTab={!hasStartedJourney ? 'landing' : (activeTab === 'home' ? 'assistant' : activeTab)}
        setActiveTab={(tab) => {
          setHasStartedJourney(true);
          sessionStorage.setItem('yatra_has_started', 'true');
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
        onStartNewChat={() => {
          setHasStartedJourney(true);
          sessionStorage.setItem('yatra_has_started', 'true');
          handleStartFreshChat();
        }}
        onReturnToLanding={() => {
          setHasStartedJourney(false);
          sessionStorage.removeItem('yatra_has_started');
        }}
        isHistoryOpen={isHistoryOpen}
      />

      {/* Security Confirmation Banner when Link Proposes an External Backend */}
      {pendingProposal && (
        <div
          role="alert"
          style={{
            background: '#FEF3C7',
            borderBottom: '2px solid #D97706',
            color: '#92400E',
            padding: '0.65rem 1.25rem',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem',
            fontWeight: 500,
            zIndex: 50,
            textAlign: 'center',
          }}
        >
          <AlertTriangle size={16} strokeWidth={2.2} />
          <span>
            <strong>External Backend Connection Request:</strong> This link requests connecting to backend tunnel <code>{pendingProposal}</code>.
            <em> Note: A *.trycloudflare.com address does NOT verify ownership. Connecting allows this external endpoint to receive your consultation queries, travel data, and any subsequent login requests. Existing session credentials will be cleared.</em> Do you trust and want to connect to this endpoint?
          </span>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => {
                confirmProposedUrl(pendingProposal);
                setPendingProposal(null);
              }}
              style={{
                background: '#B45309',
                color: '#FFF',
                border: 'none',
                borderRadius: '4px',
                padding: '0.3rem 0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.78rem',
              }}
            >
              Trust & Connect
            </button>
            <button
              type="button"
              onClick={() => {
                dismissPendingProposedUrl();
                setPendingProposal(null);
              }}
              style={{
                background: 'transparent',
                color: '#92400E',
                border: '1px solid #D97706',
                borderRadius: '4px',
                padding: '0.3rem 0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.78rem',
              }}
            >
              Decline & Ignore
            </button>
          </div>
        </div>
      )}

      {/* Informative Status Banner when Backend is Disconnected in Public Preview */}
      {!isApiConfigured() ? (
        <div
          role="status"
          style={{
            background: '#FEF3C7',
            borderBottom: '1px solid #F59E0B',
            color: '#92400E',
            padding: '0.45rem 1rem',
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '0.5rem',
            fontWeight: 500,
            textAlign: 'center',
            zIndex: 40,
          }}
        >
          <Info size={16} strokeWidth={2.2} />
          <span>
            <strong>Public Frontend Preview:</strong> Backend API is currently disconnected (Phase 12.1 preview deployment). Live AI planning and simulated booking services connect via secure Cloudflare Quick Tunnel in Phase 12.2.
          </span>
          <button
            type="button"
            onClick={() => {
              const url = window.prompt('Enter active Cloudflare Quick Tunnel URL (e.g. https://xyz.trycloudflare.com):');
              if (url && url.trim()) {
                const config = resolveApiConfig(url.trim(), { isDev: isDevelopment, isProd: isProduction });
                if (config.isMisconfigured) {
                  window.alert(`Security Policy Violation: ${config.errorMessage}`);
                } else {
                  const confirmed = window.confirm(
                    `Trust Notice: Connecting to ${config.baseUrl} allows this endpoint to receive your consultation queries and future authentication requests. Existing credentials will be cleared.\n\nDo you trust and wish to connect to this backend?`
                  );
                  if (confirmed) {
                    setRuntimeApiUrl(config.baseUrl);
                  }
                }
              }
            }}
            style={{
              background: '#B45309',
              color: '#FFF',
              border: 'none',
              borderRadius: '4px',
              padding: '0.2rem 0.6rem',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
          >
            Connect Tunnel URL
          </button>
        </div>
      ) : (
        /* Optional Connected Badge if using runtime tunnel URL */
        sessionStorage.getItem('yatra_runtime_api_url') && (
          <div
            role="status"
            style={{
              background: '#ECFDF5',
              borderBottom: '1px solid #10B981',
              color: '#065F46',
              padding: '0.35rem 1rem',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
              fontWeight: 500,
              zIndex: 40,
            }}
          >
            <CheckCircle2 size={16} strokeWidth={2.2} />
            <span>
              <strong>Connected to Local Backend Tunnel:</strong> <code>{getApiBaseUrl()}</code>
            </span>
            <button
              type="button"
              onClick={() => setRuntimeApiUrl(null)}
              style={{
                background: 'transparent',
                color: '#065F46',
                border: '1px solid #10B981',
                borderRadius: '4px',
                padding: '0.15rem 0.45rem',
                cursor: 'pointer',
                fontSize: '0.7rem',
                fontWeight: 600,
              }}
            >
              Disconnect
            </button>
          </div>
        )
      )}

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
        {/* 0. Clean Simplified Landing Screen */}
        {!hasStartedJourney && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <LandingScreen
              onStartJourney={() => {
                setHasStartedJourney(true);
                sessionStorage.setItem('yatra_has_started', 'true');
                setActiveTab('assistant');
              }}
              onSignIn={() => {
                setHasStartedJourney(true);
                sessionStorage.setItem('yatra_has_started', 'true');
                setActiveTab('assistant');
                setShowAuthModal(true);
              }}
            />
          </div>
        )}

        {/* 1. Primary AI Assistant View (Persistently mounted so active requests & streaming survive navigation) */}
        {hasStartedJourney && (
          <div
            style={{
              display: (activeTab === 'assistant' || activeTab === 'home') ? 'flex' : 'none',
              flexDirection: 'column',
              flex: 1,
              minHeight: 0,
              height: '100%',
              width: '100%',
            }}
          >
            <AIChat
              key={activeConversation?.conversation_id || activeChatSessionId}
              user={currentUser}
              initialMessage={assistantInitialQuery}
              loadedConversation={activeConversation}
              onClearLoadedConversation={() => setActiveConversation(null)}
              sharedSessionId={activeConversation?.conversation_id || activeChatSessionId}
              onNavigateToBooking={(payload) => handleStartBooking(payload)}
              onExplorePlace={(placeName) => handleExplorePlaceQuery(`Tell me about ${placeName}`)}
            />
          </div>
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
            <Suspense fallback={<ViewLoadingFallback label="Loading Booking Experience..." />}>
              <YatraBooking
                initialSearchParams={bookingParams}
                currentUser={currentUser}
                onRequireAuth={() => setShowAuthModal(true)}
                onReturnHome={() => {
                  setActiveTab('assistant');
                }}
              />
            </Suspense>
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
            <Suspense fallback={<ViewLoadingFallback label="Loading Sightseeing Catalog..." />}>
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
            </Suspense>
          </div>
        )}

        {/* 3b. Dedicated Weather View */}
        {activeTab === 'weather' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <Suspense fallback={<ViewLoadingFallback label="Loading Elevation Forecasts..." />}>
              <WeatherView
                onReturnToAssistant={() => setActiveTab('assistant')}
              />
            </Suspense>
          </div>
        )}

        {/* 3c. Dedicated Accommodation & Bhawans View */}
        {activeTab === 'accommodation' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <Suspense fallback={<ViewLoadingFallback label="Loading Shrine Accommodations..." />}>
              <AccommodationView
                onReturnToAssistant={() => setActiveTab('assistant')}
                onBookAccommodation={(hotel) => {
                  handleStartBooking({
                    accommodation_choice: 'custom',
                    selected_hotel: hotel,
                  });
                }}
              />
            </Suspense>
          </div>
        )}

        {/* 3d. Dedicated Transport & Schedules View */}
        {activeTab === 'transport' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <Suspense fallback={<ViewLoadingFallback label="Loading Transport Schedules..." />}>
              <TransportView
                onReturnToAssistant={() => setActiveTab('assistant')}
                onBookTransport={(tr) => {
                  handleStartBooking({
                    transport_choice: 'custom',
                    selected_transport: tr,
                  });
                }}
              />
            </Suspense>
          </div>
        )}

        {/* 4. Dedicated Settings & Account Management View */}
        {activeTab === 'settings' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <Suspense fallback={<ViewLoadingFallback label="Loading Settings..." />}>
              <SettingsView
                user={currentUser}
                onOpenAuthModal={() => setShowAuthModal(true)}
                onLogout={handleLogout}
                onReturnToAssistant={() => setActiveTab('assistant')}
              />
            </Suspense>
          </div>
        )}
      </main>

      {/* Collapsible History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectConversation={handleOpenConversation}
        onStartNewChat={handleStartFreshChat}
        onNavigate={(tab) => {
          setHasStartedJourney(true);
          sessionStorage.setItem('yatra_has_started', 'true');
          if (tab === 'booking') {
            setHasMountedBooking(true);
            setActiveTab('booking');
          } else {
            setActiveTab(tab);
          }
          setIsHistoryOpen(false);
        }}
        activeTab={activeTab}
        user={currentUser}
        onOpenAuthModal={() => setShowAuthModal(true)}
        onOpenSettings={() => {
          setHasStartedJourney(true);
          setActiveTab('settings');
          setIsHistoryOpen(false);
        }}
        onLogout={handleLogout}
        activeSessionId={activeConversation?.conversation_id || null}
      />

      {/* Passwordless Email Auth Modal */}
      {showAuthModal && (
        <Suspense fallback={null}>
          <AuthModal
            isOpen={showAuthModal}
            onClose={() => setShowAuthModal(false)}
            onAuthSuccess={async (user, token) => {
              setCurrentUser(user);
              if (token) setAuthToken(token);
              try {
                const guestConvs = getLocalGuestConversations();
                if (guestConvs && guestConvs.length > 0) {
                  for (const gc of guestConvs) {
                    if (gc.messages && gc.messages.length > 0) {
                      await saveConversation(
                        gc.title || 'Saved Journey',
                        gc.messages,
                        gc.conversation_id,
                        gc.trip_request,
                        gc.itinerary
                      );
                    }
                  }
                  clearLocalGuestConversations();
                }
              } catch (err) {
                console.debug('Silent error migrating guest conversations on login:', err);
              }
            }}
          />
        </Suspense>
      )}

      {/* Authenticated User Saved Trips Modal (Account, Bookings, Itineraries, Conversations) */}
      {showSavedTripsModal && (
        <Suspense fallback={null}>
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
        </Suspense>
      )}
    </div>
  );
}
