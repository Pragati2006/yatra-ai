import React from 'react';
import {
  History,
  Plus,
  MessageSquare,
  Compass,
  Ticket,
  MapPin,
  Settings,
  User,
  LogOut,
} from 'lucide-react';
import YatraLogo from '../common/YatraLogo';

/**
 * Polished, professional Header for Yatra AI Web.
 * Clean vector line icons, zero emojis, responsive navigation:
 * 1. AI Assistant (Central conversational intelligence)
 * 2. My Trips (Simulated booking passes & saved itineraries)
 * 3. Booking Wizard (Step-by-step darshan & travel intake)
 * 4. Destinations (Jammu & Kashmir religious and scenic catalogue)
 * 5. Settings (Dedicated settings, preferences, and account management)
 */
export default function ChatHeader({
  activeTab,
  setActiveTab,
  user = null,
  onOpenAuthModal,
  onOpenSavedTrips,
  onLogout,
  onToggleHistory,
  onStartNewChat,
  onReturnToLanding = null,
  isHistoryOpen = false,
}) {
  return (
    <header
      data-testid="yatra-chat-header"
      style={{
        background: '#FFFFFF',
        borderBottom: '1px solid var(--gold-border, #E5D2AD)',
        padding: '0.65rem 1.15rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        flexShrink: 0,
        gap: '8px',
      }}
    >
      {/* Left: History Button + Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {/* Compact History Toggle Button */}
        <button
          type="button"
          data-testid="chat-history-toggle-btn"
          onClick={onToggleHistory}
          aria-label={isHistoryOpen ? 'Close conversation history' : 'Open conversation history'}
          aria-expanded={isHistoryOpen}
          style={{
            background: isHistoryOpen ? 'var(--gold-subtle, #F5ECDA)' : '#FFFFFF',
            border: `1.5px solid ${isHistoryOpen ? 'var(--gold-primary, #B8860B)' : 'var(--gold-border, #E5D2AD)'}`,
            borderRadius: '10px',
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--burgundy, #58111A)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="View saved conversations & trip history"
        >
          <History size={16} strokeWidth={2.2} />
          <span className="hide-on-mobile">History</span>
        </button>

        {/* New Chat Button */}
        <button
          type="button"
          data-testid="header-new-chat-btn"
          onClick={onStartNewChat}
          style={{
            background: '#FFFFFF',
            border: '1.5px solid var(--gold-border, #E5D2AD)',
            borderRadius: '10px',
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: 'var(--burgundy, #58111A)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Start fresh conversation"
        >
          <Plus size={16} strokeWidth={2.2} />
          <span className="hide-on-mobile">New Chat</span>
        </button>

        {/* Divider */}
        <div style={{ width: '1px', height: '22px', background: 'var(--border-subtle, #EBE1D0)' }} />

        {/* Official Brand Identity */}
        <div
          data-testid="nav-brand-logo"
          role="button"
          tabIndex={0}
          onClick={() => (onReturnToLanding ? onReturnToLanding() : setActiveTab('assistant'))}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              if (onReturnToLanding) {
                onReturnToLanding();
              } else {
                setActiveTab('assistant');
              }
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            textDecoration: 'none',
          }}
        >
          <YatraLogo size={34} />
          <div>
            <div
              style={{
                fontFamily: 'var(--font-serif, Cinzel, serif)',
                fontWeight: 800,
                fontSize: '1.02rem',
                color: 'var(--burgundy, #58111A)',
                letterSpacing: '0.04em',
                lineHeight: 1.1,
              }}
            >
              YATRA AI
            </div>
            <div
              className="hide-on-mobile"
              style={{
                fontSize: '0.62rem',
                fontWeight: 700,
                color: 'var(--gold-primary, #B8860B)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                lineHeight: 1,
                marginTop: '1px',
              }}
            >
              Pilgrimage &amp; Tourism Assistant
            </div>
          </div>
        </div>
      </div>

      {/* Center: Core Capability Navigation Pills */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          background: 'var(--bg-subtle, #F8F4EC)',
          padding: '3px 4px',
          borderRadius: '999px',
          border: '1px solid var(--gold-border, #E5D2AD)',
        }}
      >
        <button
          type="button"
          data-testid="nav-assistant"
          aria-current={activeTab === 'assistant' ? 'page' : undefined}
          onClick={() => setActiveTab('assistant')}
          style={{
            background: activeTab === 'assistant' ? '#FFFFFF' : 'transparent',
            border: activeTab === 'assistant' ? '1px solid var(--gold-border, #E5D2AD)' : '1px solid transparent',
            color: activeTab === 'assistant' ? 'var(--burgundy, #58111A)' : 'var(--text-muted, #6B5C5C)',
            fontWeight: activeTab === 'assistant' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'assistant' ? '0 1px 4px rgba(0,0,0,0.05)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <MessageSquare size={14} strokeWidth={activeTab === 'assistant' ? 2.4 : 1.8} />
          <span className="hide-on-small-mobile">Assistant</span>
        </button>

        <button
          type="button"
          data-testid="nav-saved-trips-tab"
          onClick={onOpenSavedTrips}
          style={{
            background: 'transparent',
            border: '1px solid transparent',
            color: 'var(--text-muted, #6B5C5C)',
            fontWeight: 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
          title="Open saved trips, itineraries, and simulated booking passes"
        >
          <Compass size={14} strokeWidth={1.8} />
          <span className="hide-on-mobile">My Trips</span>
        </button>

        <button
          type="button"
          data-testid="nav-booking"
          aria-current={activeTab === 'booking' ? 'page' : undefined}
          onClick={() => setActiveTab('booking')}
          style={{
            background: activeTab === 'booking' ? '#FFFFFF' : 'transparent',
            border: activeTab === 'booking' ? '1px solid var(--gold-border, #E5D2AD)' : '1px solid transparent',
            color: activeTab === 'booking' ? 'var(--burgundy, #58111A)' : 'var(--text-muted, #6B5C5C)',
            fontWeight: activeTab === 'booking' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'booking' ? '0 1px 4px rgba(0,0,0,0.05)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Ticket size={14} strokeWidth={activeTab === 'booking' ? 2.4 : 1.8} />
          <span className="hide-on-mobile">Booking Wizard</span>
        </button>

        <button
          type="button"
          data-testid="nav-sightseeing"
          aria-current={activeTab === 'sightseeing' ? 'page' : undefined}
          onClick={() => setActiveTab('sightseeing')}
          style={{
            background: activeTab === 'sightseeing' ? '#FFFFFF' : 'transparent',
            border: activeTab === 'sightseeing' ? '1px solid var(--gold-border, #E5D2AD)' : '1px solid transparent',
            color: activeTab === 'sightseeing' ? 'var(--burgundy, #58111A)' : 'var(--text-muted, #6B5C5C)',
            fontWeight: activeTab === 'sightseeing' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'sightseeing' ? '0 1px 4px rgba(0,0,0,0.05)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <MapPin size={14} strokeWidth={activeTab === 'sightseeing' ? 2.4 : 1.8} />
          <span className="hide-on-mobile">Destinations</span>
        </button>

        {/* Dedicated Settings Tab */}
        <button
          type="button"
          data-testid="nav-settings"
          aria-current={activeTab === 'settings' ? 'page' : undefined}
          onClick={() => setActiveTab('settings')}
          style={{
            background: activeTab === 'settings' ? '#FFFFFF' : 'transparent',
            border: activeTab === 'settings' ? '1px solid var(--gold-border, #E5D2AD)' : '1px solid transparent',
            color: activeTab === 'settings' ? 'var(--burgundy, #58111A)' : 'var(--text-muted, #6B5C5C)',
            fontWeight: activeTab === 'settings' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'settings' ? '0 1px 4px rgba(0,0,0,0.05)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
          title="Open application settings, preferences, and account controls"
        >
          <Settings size={14} strokeWidth={activeTab === 'settings' ? 2.4 : 1.8} />
          <span className="hide-on-small-mobile">Settings</span>
        </button>
      </nav>

      {/* Right: Account & Authentication Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
        {!user ? (
          <button
            type="button"
            data-testid="nav-signin-btn"
            onClick={onOpenAuthModal}
            style={{
              background: '#FFFDF9',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              color: 'var(--burgundy, #58111A)',
              padding: '0.42rem 0.95rem',
              borderRadius: '999px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--gold-primary, #B8860B)';
              e.currentTarget.style.background = 'var(--gold-subtle, #F5ECDA)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--gold-border, #E5D2AD)';
              e.currentTarget.style.background = '#FFFDF9';
            }}
          >
            <User size={15} strokeWidth={2.2} />
            <span className="hide-on-small-mobile">Sign In</span>
          </button>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              data-testid="nav-saved-trips-btn"
              onClick={onOpenSavedTrips}
              style={{
                background: 'var(--gold-subtle, #F5ECDA)',
                border: '1px solid var(--gold-primary, #B8860B)',
                color: 'var(--burgundy, #58111A)',
                padding: '0.42rem 0.85rem',
                borderRadius: '999px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                maxWidth: '160px',
              }}
              title={`Account: ${user.email}. Click to view saved trips & profile.`}
            >
              <User size={14} strokeWidth={2.2} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.email || 'My Account'}
              </span>
            </button>

            <button
              type="button"
              data-testid="nav-logout-btn"
              onClick={onLogout}
              title={`Signed in as ${user.email}. Click to sign out.`}
              style={{
                background: 'transparent',
                border: '1px solid var(--gold-border, #E5D2AD)',
                color: 'var(--text-muted, #6B5C5C)',
                padding: '0.42rem 0.75rem',
                borderRadius: '999px',
                fontSize: '0.78rem',
                cursor: 'pointer',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <LogOut size={13} strokeWidth={2} />
              <span className="hide-on-small-mobile">Sign Out</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
