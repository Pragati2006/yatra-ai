import React, { useState, useEffect } from 'react';
import {
  Clock,
  X,
  Plus,
  ScrollText,
  MessageSquare,
  Trash2,
  Search,
  Ticket,
  Building2,
  Train,
  MapPin,
  CloudSun,
  Settings,
  User,
  LogOut,
} from 'lucide-react';
import YatraLogo from '../common/YatraLogo';
import {
  getSavedConversations,
  deleteSavedConversation,
  getSavedConversation,
  getLocalGuestConversations,
  deleteLocalGuestConversation,
} from '../../services/api';

/**
 * Unified Navigation & History Sidebar Drawer for Yatra AI Web.
 * Fully aligned with Android SidebarDrawer (Phase 8.6 & 8.8.33 design system).
 * Contains:
 * 1. Brand Header (YatraLogo + Yatra AI title/subtitle + close)
 * 2. CHAT: New Chat, Search conversations, Recent Conversations list
 * 3. YATRA SERVICES: Assistant, Booking/Parchi, Accommodation/Bhawans, Transport/Schedules, Sightseeing/Destinations, Weather Guidance
 * 4. FOOTER: Settings, Devotee Profile / Sign In, Sign Out
 */
export default function HistoryDrawer({
  isOpen,
  onClose,
  onSelectConversation,
  onStartNewChat,
  onNavigate = null,
  activeTab = 'assistant',
  user = null,
  onOpenAuthModal = null,
  onOpenSettings = null,
  onLogout = null,
  activeSessionId = null,
}) {
  const [conversations, setConversations] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const loadConversations = async () => {
    if (!isOpen) return;
    setLoading(true);
    setErrorMsg('');
    try {
      if (user) {
        const res = await getSavedConversations();
        setConversations(res?.conversations || []);
      } else {
        const local = getLocalGuestConversations();
        setConversations(local || []);
      }
    } catch {
      if (!user) {
        setConversations(getLocalGuestConversations() || []);
      } else {
        setErrorMsg('Could not load history. Check network or sign in again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen, user]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleResume = async (conv) => {
    try {
      let fullConv = conv;
      if (user && conv.conversation_id) {
        try {
          const detail = await getSavedConversation(conv.conversation_id);
          if (detail?.conversation) {
            fullConv = detail.conversation;
          }
        } catch {
          // fallback to cached record
        }
      }
      onSelectConversation(fullConv);
      onClose();
    } catch (err) {
      console.warn('Failed to resume conversation:', err);
    }
  };

  const handleDelete = async (e, convId, title) => {
    e.stopPropagation();
    if (!window.confirm(`Delete conversation "${title || 'Saved Journey'}"?`)) return;
    try {
      if (user) {
        await deleteSavedConversation(convId);
      } else {
        deleteLocalGuestConversation(convId);
      }
      setConversations((prev) => prev.filter((c) => c.conversation_id !== convId));
    } catch {
      alert('Could not delete conversation.');
    }
  };

  const handleNavClick = (tabKey) => {
    if (onNavigate) {
      onNavigate(tabKey);
    }
    onClose();
  };

  const services = [
    { key: 'assistant', label: 'Assistant', icon: MessageSquare, description: 'AI Pilgrimage Companion' },
    { key: 'booking', label: 'Booking / Parchi', icon: Ticket, description: 'Yatra Pass & Guided Wizard' },
    { key: 'accommodation', label: 'Accommodation / Bhawans', icon: Building2, description: 'Shrine Board Bhawans & Stays' },
    { key: 'transport', label: 'Transport / Schedules', icon: Train, description: 'Trains, Buses, Flights & Helicopters' },
    { key: 'sightseeing', label: 'Sightseeing / Destinations', icon: MapPin, description: 'Holy Sites & Regional Shrines' },
    { key: 'weather', label: 'Weather Guidance', icon: CloudSun, description: 'Multi-Elevation Trek Advisories' },
  ];

  return (
    <div
      data-testid="chat-history-drawer-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        display: 'flex',
        background: 'rgba(61, 16, 34, 0.45)',
        backdropFilter: 'blur(3px)',
        transition: 'opacity 0.25s ease',
      }}
      onClick={onClose}
    >
      <div
        data-testid="chat-history-drawer-panel"
        style={{
          width: 'min(340px, 86vw)',
          height: '100%',
          background: 'var(--surface-white, #FFFCF9)',
          borderRight: '1px solid var(--border-default, #E9DED6)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '4px 0 24px rgba(84, 21, 45, 0.12)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 1. Drawer Header */}
        <div
          style={{
            padding: '1rem 1.15rem',
            borderBottom: '1px solid var(--border-default, #E9DED6)',
            background: 'var(--surface-white, #FFFCF9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <YatraLogo size={28} />
            <div>
              <div
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 800,
                  fontSize: '0.98rem',
                  color: 'var(--royal-plum, #54152D)',
                  letterSpacing: '0.04em',
                  lineHeight: 1.1,
                }}
              >
                YATRA AI
              </div>
              <div
                style={{
                  fontSize: '0.62rem',
                  fontWeight: 700,
                  color: 'var(--champagne-taupe, #A3826C)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                Pilgrimage &amp; Tourism
              </div>
            </div>
          </div>
          <button
            type="button"
            data-testid="history-drawer-close-btn"
            onClick={onClose}
            aria-label="Close drawer"
            style={{
              background: 'var(--secondary-bg, #F2EAE4)',
              border: '1px solid var(--border-default, #E9DED6)',
              borderRadius: '8px',
              width: '30px',
              height: '30px',
              color: 'var(--royal-plum, #54152D)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease',
            }}
          >
            <X size={16} strokeWidth={2.2} />
          </button>
        </div>

        {/* Scrollable Drawer Body */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {/* 2. CHAT Section Header & Actions */}
          <div style={{ padding: '0.85rem 1.15rem 0.5rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div
              style={{
                fontSize: '0.68rem',
                fontWeight: 800,
                color: 'var(--champagne-taupe, #A3826C)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              CHAT
            </div>

            {/* New Chat Button */}
            <button
              type="button"
              data-testid="history-new-chat-btn"
              onClick={() => {
                onStartNewChat();
                onClose();
              }}
              style={{
                width: '100%',
                padding: '0.55rem 0.85rem',
                fontSize: '0.82rem',
                fontWeight: 700,
                gap: '8px',
                background: 'var(--royal-plum, #54152D)',
                border: 'none',
                borderRadius: '10px',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(84, 21, 45, 0.15)',
              }}
            >
              <Plus size={16} strokeWidth={2.5} />
              <span>New Chat</span>
            </button>

            {/* Search Conversations Input */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--secondary-bg, #F2EAE4)',
                border: '1px solid var(--border-default, #E9DED6)',
                borderRadius: '8px',
                padding: '6px 10px',
              }}
            >
              <Search size={14} color="var(--text-secondary, #796D69)" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  outline: 'none',
                  width: '100%',
                  fontSize: '0.8rem',
                  color: 'var(--text-primary, #30272A)',
                }}
              />
            </div>
          </div>

          {/* Recent Conversations List */}
          <div
            data-testid="history-conversations-list"
            style={{
              padding: '0 0.85rem 0.85rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              maxHeight: '220px',
              overflowY: 'auto',
              borderBottom: '1px solid var(--border-subtle, #F0E8E2)',
            }}
          >
            {loading && (
              <div style={{ padding: '0.85rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                Loading saved conversations...
              </div>
            )}

            {!loading && errorMsg && (
              <div style={{ padding: '0.65rem', textAlign: 'center', color: 'var(--status-error, #C75A60)', fontSize: '0.75rem' }}>
                {errorMsg}
              </div>
            )}

            {!loading && !errorMsg && conversations.length === 0 && (
              <div style={{ padding: '1rem 0.5rem', textAlign: 'center', color: 'var(--text-secondary, #796D69)', fontSize: '0.76rem' }}>
                {searchQuery ? 'No matching conversations' : 'No previous consultations yet'}
              </div>
            )}

            {!loading &&
              conversations
                .filter((c) => {
                  if (!searchQuery.trim()) return true;
                  const q = searchQuery.toLowerCase();
                  const title = (c.title || '').toLowerCase();
                  const preview = (c.preview || '').toLowerCase();
                  return title.includes(q) || preview.includes(q);
                })
                .slice(0, 15)
                .map((c) => {
                  const isActive = activeSessionId && c.conversation_id === activeSessionId;
                  const dateVal = c.updated_at || c.created_at;
                  const dateStr = dateVal ? new Date(dateVal).toLocaleDateString([], { month: 'short', day: 'numeric' }) : '';
                  const title = c.title || 'Pilgrimage Consultation';

                  return (
                    <div
                      key={c.conversation_id}
                      data-testid={`history-item-${c.conversation_id}`}
                      onClick={() => handleResume(c)}
                      style={{
                        padding: '7px 10px',
                        borderRadius: '8px',
                        border: `1px solid ${isActive ? 'var(--royal-plum, #54152D)' : 'transparent'}`,
                        background: isActive ? 'var(--soft-plum-surface, #F0E3E7)' : 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '6px',
                        transition: 'all 0.12s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) e.currentTarget.style.background = 'var(--secondary-bg, #F2EAE4)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                        <MessageSquare size={13} color={isActive ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)'} style={{ flexShrink: 0 }} />
                        <span
                          style={{
                            fontWeight: isActive ? 700 : 500,
                            fontSize: '0.78rem',
                            color: isActive ? 'var(--royal-plum, #54152D)' : 'var(--text-primary, #30272A)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {title}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                        {dateStr && <span style={{ fontSize: '0.68rem', color: 'var(--text-muted, #A39994)' }}>{dateStr}</span>}
                        <button
                          type="button"
                          data-testid={`delete-history-${c.conversation_id}`}
                          onClick={(e) => handleDelete(e, c.conversation_id, title)}
                          title="Delete conversation"
                          aria-label="Delete saved conversation"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-muted, #A39994)',
                            cursor: 'pointer',
                            padding: '2px',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.color = '#C75A60')}
                          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted, #A39994)')}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  );
                })}
          </div>

          {/* 3. Yatra Services Section */}
          <div style={{ padding: '0.85rem 1.15rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div
              style={{
                fontSize: '0.68rem',
                fontWeight: 800,
                color: 'var(--champagne-taupe, #A3826C)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}
            >
              YATRA SERVICES &amp; EXPLORE
            </div>

            {services.map((svc) => {
              const IconComp = svc.icon;
              const isActive = activeTab === svc.key;
              return (
                <button
                  key={svc.key}
                  type="button"
                  data-testid={`sidebar-nav-${svc.key}`}
                  onClick={() => handleNavClick(svc.key)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    border: `1px solid ${isActive ? 'var(--border-default, #E9DED6)' : 'transparent'}`,
                    background: isActive ? 'var(--soft-plum-surface, #F0E3E7)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.12s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'var(--secondary-bg, #F2EAE4)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <IconComp
                    size={16}
                    color={isActive ? 'var(--royal-plum, #54152D)' : 'var(--royal-plum, #54152D)'}
                    strokeWidth={isActive ? 2.4 : 1.9}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.82rem',
                        fontWeight: isActive ? 800 : 600,
                        color: isActive ? 'var(--royal-plum, #54152D)' : 'var(--text-primary, #30272A)',
                      }}
                    >
                      {svc.label}
                    </div>
                  </div>
                  {isActive && (
                    <div
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'var(--royal-plum, #54152D)',
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* 4. FOOTER Section */}
        <div
          style={{
            padding: '0.85rem 1.15rem',
            borderTop: '1px solid var(--border-default, #E9DED6)',
            background: 'var(--surface-white, #FFFCF9)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {/* Settings / Server Connection */}
          <button
            type="button"
            data-testid="sidebar-footer-settings"
            onClick={() => {
              if (onOpenSettings) onOpenSettings();
              else handleNavClick('settings');
            }}
            style={{
              padding: '6px 8px',
              borderRadius: '8px',
              border: 'none',
              background: 'transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: 'var(--text-primary, #30272A)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--secondary-bg, #F2EAE4)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <Settings size={15} color="var(--royal-plum, #54152D)" strokeWidth={2} />
            <span>Settings / Server</span>
          </button>

          {/* Profile / Sign In */}
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <User size={15} color="var(--royal-plum, #54152D)" strokeWidth={2} />
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--royal-plum, #54152D)' }}>
                  {user.name || user.email || 'Devotee'}
                </span>
              </div>
              {onLogout && (
                <button
                  type="button"
                  data-testid="sidebar-footer-logout"
                  onClick={onLogout}
                  title="Sign Out"
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted, #A39994)',
                    padding: '2px',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = '#C75A60')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted, #A39994)')}
                >
                  <LogOut size={14} />
                </button>
              )}
            </div>
          ) : (
            <button
              type="button"
              data-testid="sidebar-footer-signin"
              onClick={() => {
                if (onOpenAuthModal) onOpenAuthModal();
                onClose();
              }}
              style={{
                padding: '6px 8px',
                borderRadius: '8px',
                border: 'none',
                background: 'transparent',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: 'var(--royal-plum, #54152D)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--secondary-bg, #F2EAE4)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <User size={15} color="var(--royal-plum, #54152D)" strokeWidth={2} />
              <span>Devotee Sign In (Guest Mode)</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
