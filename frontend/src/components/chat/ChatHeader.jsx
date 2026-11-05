import React from 'react';

/**
 * Minimal, modern Header for Yatra AI.
 * Incorporates Yatra AI branding, history drawer toggle, new chat trigger,
 * minimal navigation, and user authentication/profile controls.
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
  isHistoryOpen = false,
}) {
  return (
    <header
      data-testid="yatra-chat-header"
      style={{
        background: '#FFFFFF',
        borderBottom: '1px solid var(--gold-border, #E5D2AD)',
        padding: '0.65rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        flexShrink: 0,
      }}
    >
      {/* Left: History Button + Branding */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Compact History Toggle Button */}
        <button
          type="button"
          data-testid="chat-history-toggle-btn"
          onClick={onToggleHistory}
          aria-label={isHistoryOpen ? 'Close conversation history' : 'Open conversation history'}
          aria-expanded={isHistoryOpen}
          style={{
            background: isHistoryOpen ? 'var(--gold-subtle, #F5ECDA)' : '#FFFFFF',
            border: '1.5px solid var(--gold-border, #E5D2AD)',
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
          <span style={{ fontSize: '0.95rem' }}>⏱️</span>
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
            gap: '5px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: 'var(--burgundy, #58111A)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Start fresh conversation"
        >
          <span>➕</span>
          <span className="hide-on-mobile">New Chat</span>
        </button>

        {/* Divider */}
        <div style={{ width: '1px', height: '22px', background: 'var(--border-subtle, #EBE1D0)' }} />

        {/* Brand */}
        <div
          data-testid="nav-brand-logo"
          role="button"
          tabIndex={0}
          onClick={() => setActiveTab('assistant')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setActiveTab('assistant');
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
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--burgundy, #58111A) 0%, var(--burgundy-dark, #3D0810) 100%)',
              border: '1.5px solid var(--gold-primary, #B8860B)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#E5D2AD',
              fontSize: '1rem',
              boxShadow: '0 2px 6px rgba(88, 17, 26, 0.15)',
              flexShrink: 0,
            }}
          >
            🔱
          </div>
          <div>
            <div
              style={{
                fontFamily: 'var(--font-serif, Cinzel, serif)',
                fontWeight: 800,
                fontSize: '1rem',
                color: 'var(--burgundy, #58111A)',
                letterSpacing: '0.04em',
                lineHeight: 1.1,
              }}
            >
              YATRA AI
            </div>
            <div
              style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: 'var(--gold-primary, #B8860B)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                lineHeight: 1,
              }}
            >
              Pilgrimage Companion
            </div>
          </div>
        </div>
      </div>

      {/* Center: Minimal Navigation Pills */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
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
          }}
        >
          AI Assistant
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
          }}
        >
          Darshan Bookings
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
          }}
        >
          Destinations
        </button>
      </nav>

      {/* Right: Plan Yatra + Auth & Account Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          type="button"
          data-testid="nav-plan-yatra-btn"
          onClick={() => setActiveTab('booking')}
          className="btn btn-primary"
          style={{
            padding: '0.42rem 0.95rem',
            fontSize: '0.8rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
          }}
          title="Open guided yatra booking wizard"
        >
          <span>Plan Your Yatra</span>
          <span>➔</span>
        </button>

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
            <span>👤</span>
            <span>Sign In</span>
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
                gap: '5px',
                maxWidth: '180px',
              }}
              title={`Account: ${user.email}`}
            >
              <span>👤</span>
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
              }}
            >
              Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
