import React, { useState, useEffect } from 'react';
import { getSavedConversations, deleteSavedConversation, getSavedConversation } from '../../services/api';

/**
 * Collapsible History Drawer / Slide-Over Panel for Yatra AI.
 * Opened on-demand via the History button; not permanently visible by default.
 */
export default function HistoryDrawer({
  isOpen,
  onClose,
  onSelectConversation,
  onStartNewChat,
  user = null,
  onOpenAuthModal,
  activeSessionId = null,
}) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const loadConversations = async () => {
    if (!isOpen) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await getSavedConversations();
      setConversations(res?.conversations || []);
    } catch {
      setErrorMsg('Could not load history. Sign in or check network.');
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
      if (conv.conversation_id) {
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
      await deleteSavedConversation(convId);
      setConversations((prev) => prev.filter((c) => c.conversation_id !== convId));
    } catch {
      alert('Could not delete conversation.');
    }
  };

  return (
    <div
      data-testid="chat-history-drawer-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        display: 'flex',
        background: 'rgba(45, 5, 11, 0.45)',
        backdropFilter: 'blur(3px)',
        transition: 'opacity 0.25s ease',
      }}
      onClick={onClose}
    >
      <div
        data-testid="chat-history-drawer-panel"
        style={{
          width: 'min(360px, 85vw)',
          height: '100%',
          background: '#FFFFFF',
          borderRight: '1.5px solid var(--gold-border, #E5D2AD)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '4px 0 24px rgba(88, 17, 26, 0.15)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div
          style={{
            padding: '1.1rem 1.25rem',
            borderBottom: '1px solid var(--gold-border, #E5D2AD)',
            background: 'linear-gradient(135deg, var(--burgundy, #58111A) 0%, var(--burgundy-dark, #3D0810) 100%)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.15rem' }}>⏱️</span>
            <div>
              <div style={{ fontFamily: 'var(--font-serif, Cinzel, serif)', fontWeight: 800, fontSize: '0.96rem' }}>
                Saved Journeys
              </div>
              <div style={{ fontSize: '0.7rem', color: '#E5D2AD' }}>
                Conversation History & Trips
              </div>
            </div>
          </div>
          <button
            type="button"
            data-testid="history-drawer-close-btn"
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.15)',
              border: 'none',
              borderRadius: '50%',
              width: '28px',
              height: '28px',
              color: '#FFFFFF',
              cursor: 'pointer',
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ✕
          </button>
        </div>

        {/* Start New Chat Action */}
        <div style={{ padding: '0.9rem 1.25rem', borderBottom: '1px solid var(--border-subtle, #EBE1D0)' }}>
          <button
            type="button"
            data-testid="history-new-chat-btn"
            onClick={() => {
              onStartNewChat();
              onClose();
            }}
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '0.6rem 1rem',
              fontSize: '0.84rem',
              gap: '6px',
            }}
          >
            <span>➕</span>
            <span>Start Fresh Conversation</span>
          </button>
        </div>

        {/* Conversation List */}
        <div
          data-testid="history-conversations-list"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {loading && (
            <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
              Loading saved conversations...
            </div>
          )}

          {!loading && errorMsg && (
            <div style={{ padding: '1rem', textAlign: 'center', color: '#C0392B', fontSize: '0.8rem' }}>
              {errorMsg}
            </div>
          )}

          {!loading && !errorMsg && conversations.length === 0 && (
            <div
              style={{
                padding: '2.5rem 1rem',
                textAlign: 'center',
                color: 'var(--text-muted, #6B5C5C)',
                fontSize: '0.84rem',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📜</div>
              <div style={{ fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
                No Saved Conversations Yet
              </div>
              <p style={{ fontSize: '0.76rem', lineHeight: 1.45, maxWidth: '240px', margin: '0 auto' }}>
                Your pilgrimage planning conversations and itineraries will appear here when saved.
              </p>
              {!user && onOpenAuthModal && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenAuthModal();
                  }}
                  className="btn btn-secondary"
                  style={{ marginTop: '1rem', padding: '0.4rem 0.9rem', fontSize: '0.78rem' }}
                >
                  Sign In to Sync History
                </button>
              )}
            </div>
          )}

          {!loading &&
            conversations.map((c) => {
              const isActive = activeSessionId && c.conversation_id === activeSessionId;
              const dateStr = c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recent';
              const title = c.title || 'Pilgrimage Planning Session';
              const msgCount = c.message_count || (Array.isArray(c.messages) ? c.messages.length : 0);

              return (
                <div
                  key={c.conversation_id}
                  data-testid={`history-item-${c.conversation_id}`}
                  onClick={() => handleResume(c)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: `1.5px solid ${isActive ? 'var(--gold-primary, #B8860B)' : 'var(--gold-border, #E5D2AD)'}`,
                    background: isActive ? 'var(--gold-subtle, #F5ECDA)' : '#FFFFFF',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'var(--bg-subtle, #F8F4EC)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = '#FFFFFF';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '0.84rem',
                        color: 'var(--burgundy, #58111A)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '220px',
                      }}
                    >
                      💬 {title}
                    </span>
                    <button
                      type="button"
                      data-testid={`delete-history-${c.conversation_id}`}
                      onClick={(e) => handleDelete(e, c.conversation_id, title)}
                      title="Delete saved conversation"
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        padding: '2px 4px',
                        borderRadius: '4px',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = '#C0392B';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = 'var(--text-muted)';
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    <span>{dateStr}</span>
                    <span>{msgCount} messages</span>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Bottom Note */}
        {!user && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderTop: '1px solid var(--border-subtle, #EBE1D0)',
              background: 'var(--bg-subtle, #F8F4EC)',
              fontSize: '0.74rem',
              color: 'var(--text-muted)',
              textAlign: 'center',
            }}
          >
            Signed out (Guest Mode). Conversations are saved in your current browser session.
          </div>
        )}
      </div>
    </div>
  );
}
