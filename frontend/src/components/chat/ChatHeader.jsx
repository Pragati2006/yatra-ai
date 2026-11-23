import React from 'react';
import {
  Menu,
  History,
  Plus,
  MessageSquare,
  Compass,
  Ticket,
  MapPin,
  CloudSun,
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
        background: 'var(--surface-white, #FFFCF9)',
        borderBottom: '1px solid var(--border-default, #E9DED6)',
        padding: '0.65rem 1.15rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: '0 1px 4px rgba(84, 21, 45, 0.03)',
        flexShrink: 0,
        gap: '8px',
      }}
    >
      {/* Left: History Button + Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {/* Prominent Sidebar Hamburger Menu Toggle Button */}
        <button
          type="button"
          data-testid="chat-history-toggle-btn"
          id="sidebar-toggle-btn"
          onClick={onToggleHistory}
          aria-label={isHistoryOpen ? 'Close navigation sidebar menu' : 'Open navigation sidebar menu'}
          aria-expanded={isHistoryOpen}
          style={{
            background: isHistoryOpen ? 'var(--soft-plum-surface, #F0E3E7)' : 'var(--surface-white, #FFFCF9)',
            border: `1px solid ${isHistoryOpen ? 'var(--royal-plum, #54152D)' : 'var(--border-default, #E9DED6)'}`,
            borderRadius: '10px',
            padding: '6px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--royal-plum, #54152D)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: '0 1px 3px rgba(84, 21, 45, 0.05)',
          }}
          title="Open navigation menu, services & saved conversations"
        >
          <span
            data-testid="sidebar-toggle-btn"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <Menu size={18} strokeWidth={2.2} />
            <span style={{ fontWeight: 700 }}>Menu</span>
          </span>
        </button>

        {/* New Chat Button */}
        <button
          type="button"
          data-testid="header-new-chat-btn"
          onClick={onStartNewChat}
          style={{
            background: 'var(--surface-white, #FFFCF9)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '10px',
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: 'var(--royal-plum, #54152D)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Start fresh conversation"
        >
          <Plus size={16} strokeWidth={2.2} />
          <span className="hide-on-mobile">New Chat</span>
        </button>

        {/* Divider */}
        <div style={{ width: '1px', height: '22px', background: 'var(--border-subtle, #F0E8E2)' }} />

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
          <YatraLogo size={32} />
          <div>
            <div
              style={{
                fontFamily: 'var(--font-sans)',
                fontWeight: 800,
                fontSize: '1rem',
                color: 'var(--royal-plum, #54152D)',
                letterSpacing: '0.02em',
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
                color: 'var(--champagne-taupe, #A3826C)',
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
          background: 'var(--secondary-bg, #F2EAE4)',
          padding: '3px 4px',
          borderRadius: '999px',
          border: '1px solid var(--border-default, #E9DED6)',
        }}
      >
        <button
          type="button"
          data-testid="nav-assistant"
          aria-current={activeTab === 'assistant' ? 'page' : undefined}
          onClick={() => setActiveTab('assistant')}
          style={{
            background: activeTab === 'assistant' ? 'var(--surface-white, #FFFCF9)' : 'transparent',
            border: activeTab === 'assistant' ? '1px solid var(--border-default, #E9DED6)' : '1px solid transparent',
            color: activeTab === 'assistant' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
            fontWeight: activeTab === 'assistant' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'assistant' ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
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
            color: 'var(--text-secondary, #796D69)',
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
            background: activeTab === 'booking' ? 'var(--surface-white, #FFFCF9)' : 'transparent',
            border: activeTab === 'booking' ? '1px solid var(--border-default, #E9DED6)' : '1px solid transparent',
            color: activeTab === 'booking' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
            fontWeight: activeTab === 'booking' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'booking' ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
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
            background: activeTab === 'sightseeing' ? 'var(--surface-white, #FFFCF9)' : 'transparent',
            border: activeTab === 'sightseeing' ? '1px solid var(--border-default, #E9DED6)' : '1px solid transparent',
            color: activeTab === 'sightseeing' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
            fontWeight: activeTab === 'sightseeing' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'sightseeing' ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <MapPin size={14} strokeWidth={activeTab === 'sightseeing' ? 2.4 : 1.8} />
          <span className="hide-on-mobile">Destinations</span>
        </button>

        {/* Dedicated Weather Tab */}
        <button
          type="button"
          data-testid="nav-weather"
          aria-current={activeTab === 'weather' ? 'page' : undefined}
          onClick={() => setActiveTab('weather')}
          style={{
            background: activeTab === 'weather' ? 'var(--surface-white, #FFFCF9)' : 'transparent',
            border: activeTab === 'weather' ? '1px solid var(--border-default, #E9DED6)' : '1px solid transparent',
            color: activeTab === 'weather' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
            fontWeight: activeTab === 'weather' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'weather' ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
          title="View multi-elevation weather forecasts and trek advisories"
        >
          <CloudSun size={14} strokeWidth={activeTab === 'weather' ? 2.4 : 1.8} />
          <span className="hide-on-mobile">Weather</span>
        </button>

        {/* Dedicated Settings Tab */}
        <button
          type="button"
          data-testid="nav-settings"
          aria-current={activeTab === 'settings' ? 'page' : undefined}
          onClick={() => setActiveTab('settings')}
          style={{
            background: activeTab === 'settings' ? 'var(--surface-white, #FFFCF9)' : 'transparent',
            border: activeTab === 'settings' ? '1px solid var(--border-default, #E9DED6)' : '1px solid transparent',
            color: activeTab === 'settings' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
            fontWeight: activeTab === 'settings' ? 800 : 600,
            fontSize: '0.8rem',
            padding: '5px 12px',
            borderRadius: '999px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            boxShadow: activeTab === 'settings' ? '0 1px 3px rgba(84, 21, 45, 0.04)' : 'none',
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
              background: 'var(--surface-white, #FFFCF9)',
              border: '1px solid var(--border-default, #E9DED6)',
              color: 'var(--royal-plum, #54152D)',
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
              e.currentTarget.style.borderColor = 'var(--champagne-taupe, #A3826C)';
              e.currentTarget.style.background = 'var(--soft-plum-surface, #F0E3E7)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-default, #E9DED6)';
              e.currentTarget.style.background = 'var(--surface-white, #FFFCF9)';
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
                background: 'var(--soft-plum-surface, #F0E3E7)',
                border: '1px solid var(--border-default, #E9DED6)',
                color: 'var(--royal-plum, #54152D)',
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
                border: '1px solid var(--border-default, #E9DED6)',
                color: 'var(--text-secondary, #796D69)',
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
