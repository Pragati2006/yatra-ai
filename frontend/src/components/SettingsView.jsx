import React, { useState, useEffect } from 'react';
import {
  User,
  Shield,
  Globe,
  Mic,
  Settings,
  Info,
  LogOut,
  LogIn,
  Trash2,
  CheckCircle2,
} from 'lucide-react';
import { getApiBaseUrl, isApiConfigured } from '../services/api';

/**
 * Dedicated, professional Settings View for Yatra AI Web.
 * Organized into clear, purposeful sections:
 * A. Account
 * B. Authentication
 * C. Profile
 * D. Preferences
 * E. Voice Settings
 * F. Privacy & Security
 * G. About Yatra AI
 */
export default function SettingsView({
  user = null,
  onOpenAuthModal,
  onLogout,
  onReturnToAssistant,
}) {
  const [appLanguage, setAppLanguage] = useState(() => localStorage.getItem('yatra_app_lang') || 'en-IN');
  const [voiceLang, setVoiceLang] = useState(() => localStorage.getItem('yatra_voice_lang') || 'en-IN');
  const [isSpeechAvailable, setIsSpeechAvailable] = useState(true);
  const [storageStatusMsg, setStorageStatusMsg] = useState('');

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSpeechAvailable(Boolean(SR));
  }, []);

  const handleLanguageChange = (code) => {
    setAppLanguage(code);
    localStorage.setItem('yatra_app_lang', code);
  };

  const handleVoiceLanguageChange = (code) => {
    setVoiceLang(code);
    localStorage.setItem('yatra_voice_lang', code);
  };

  const handleClearCache = () => {
    if (window.confirm('Clear local consultation cache and saved search preferences? Your active session messages will be reset.')) {
      try {
        sessionStorage.removeItem('yatra_chat_messages');
        sessionStorage.removeItem('yatra_chat_state');
        sessionStorage.removeItem('yatra_chat_messages_session_id');
        localStorage.removeItem('yatra_app_lang');
        localStorage.removeItem('yatra_voice_lang');
        setStorageStatusMsg('Local consultation cache cleared successfully.');
        setTimeout(() => setStorageStatusMsg(''), 4000);
      } catch (e) {
        setStorageStatusMsg('Could not clear storage: ' + e.message);
      }
    }
  };

  return (
    <div
      data-testid="settings-view"
      style={{
        maxWidth: '820px',
        margin: '0 auto',
        width: '100%',
        padding: '1.5rem 1rem 3rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
      }}
    >
      {/* Settings Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1.5px solid var(--gold-border, #E5D2AD)',
          paddingBottom: '1rem',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'var(--gold-subtle, #F5ECDA)',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--burgundy, #58111A)',
            }}
          >
            <Settings size={22} strokeWidth={2} />
          </div>
          <div>
            <h1
              style={{
                fontFamily: 'var(--font-serif, Cinzel, serif)',
                fontSize: '1.45rem',
                fontWeight: 800,
                color: 'var(--burgundy, #58111A)',
                margin: 0,
                lineHeight: 1.2,
              }}
            >
              Settings &amp; Preferences
            </h1>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted, #6B5C5C)' }}>
              Manage your devotee account, voice recognition, preferences, and privacy.
            </p>
          </div>
        </div>

        {onReturnToAssistant && (
          <button
            type="button"
            onClick={onReturnToAssistant}
            className="btn btn-secondary"
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.8rem',
              borderRadius: '999px',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              background: '#FFFFFF',
              color: 'var(--burgundy, #58111A)',
              cursor: 'pointer',
              fontWeight: 700,
            }}
          >
            Return to Assistant
          </button>
        )}
      </div>

      {storageStatusMsg && (
        <div
          role="status"
          style={{
            background: '#F0FDF4',
            border: '1.5px solid #16A34A',
            color: '#15803D',
            padding: '0.65rem 1rem',
            borderRadius: '10px',
            fontSize: '0.82rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{storageStatusMsg}</span>
        </div>
      )}

      {/* SECTION A & B: ACCOUNT & AUTHENTICATION */}
      <section
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          padding: '1.25rem 1.4rem',
          boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
          <User size={18} strokeWidth={2.2} color="var(--burgundy, #58111A)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            Account &amp; Authentication
          </h2>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted, #6B5C5C)', marginBottom: '1.15rem' }}>
          Signed-in devotees benefit from cloud-synced itineraries, saved consultation history, and simulated booking passes across sessions.
        </p>

        {user ? (
          <div
            style={{
              background: 'var(--bg-subtle, #F8F4EC)',
              border: '1px solid var(--gold-border, #E5D2AD)',
              borderRadius: '12px',
              padding: '1rem 1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #6B5C5C)', textTransform: 'uppercase', fontWeight: 800 }}>
                  Account Identifier
                </div>
                <div style={{ fontSize: '0.96rem', fontWeight: 700, color: 'var(--burgundy, #58111A)' }}>
                  {user.email || user.name || 'Authenticated Devotee'}
                </div>
              </div>
              <div
                style={{
                  background: '#ECFDF5',
                  border: '1px solid #10B981',
                  color: '#065F46',
                  borderRadius: '999px',
                  padding: '4px 12px',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <CheckCircle2 size={13} />
                <span>Verified Devotee Session</span>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border-subtle, #EBE1D0)', paddingTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                data-testid="settings-logout-btn"
                onClick={onLogout}
                style={{
                  background: '#FFFFFF',
                  border: '1.5px solid #E74C3C',
                  color: '#C0392B',
                  borderRadius: '999px',
                  padding: '6px 16px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.15s ease',
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              background: 'var(--bg-subtle, #F8F4EC)',
              border: '1px solid var(--gold-border, #E5D2AD)',
              borderRadius: '12px',
              padding: '1rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted, #6B5C5C)', textTransform: 'uppercase', fontWeight: 800 }}>
                Current Status
              </div>
              <div style={{ fontSize: '0.94rem', fontWeight: 700, color: 'var(--text-dark, #2A2020)' }}>
                Guest Mode (No Sign-In Required)
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-muted, #6B5C5C)', marginTop: '2px' }}>
                All AI consultations, weather forecasts, and route queries are freely available.
              </div>
            </div>

            <button
              type="button"
              data-testid="settings-signin-btn"
              onClick={onOpenAuthModal}
              className="btn btn-primary"
              style={{
                padding: '0.5rem 1.4rem',
                fontSize: '0.84rem',
                fontWeight: 700,
                borderRadius: '999px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
              }}
            >
              <LogIn size={15} />
              <span>Sign In / Devotee Login</span>
            </button>
          </div>
        )}
      </section>

      {/* SECTION C & D: PREFERENCES & DISPLAY */}
      <section
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          padding: '1.25rem 1.4rem',
          boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
          <Globe size={18} strokeWidth={2.2} color="var(--burgundy, #58111A)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            Language &amp; Display Preferences
          </h2>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted, #6B5C5C)', marginBottom: '1.15rem' }}>
          Configure your preferred interface language and regional presentation style.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
          <div>
            <label
              htmlFor="app-lang-select"
              style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy, #58111A)', marginBottom: '6px' }}
            >
              Interface Language
            </label>
            <select
              id="app-lang-select"
              value={appLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1.5px solid var(--gold-border, #E5D2AD)',
                background: '#FFFFFF',
                color: '#1A0407',
                fontSize: '0.86rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="en-IN">English (India)</option>
              <option value="hi-IN">Hindi (हिंदी)</option>
              <option value="pa-IN">Punjabi (ਪੰਜਾਬੀ)</option>
              <option value="ur-IN">Urdu (اردو)</option>
            </select>
          </div>

          <div>
            <label
              style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy, #58111A)', marginBottom: '6px' }}
            >
              Visual Theme
            </label>
            <div
              style={{
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1.5px solid var(--gold-border, #E5D2AD)',
                background: 'var(--bg-subtle, #F8F4EC)',
                color: 'var(--burgundy, #58111A)',
                fontSize: '0.86rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--burgundy)' }} />
              <span>Sacred Burgundy &amp; Warm Ivory</span>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION E: VOICE INPUT SETTINGS */}
      <section
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          padding: '1.25rem 1.4rem',
          boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
          <Mic size={18} strokeWidth={2.2} color="var(--burgundy, #58111A)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            Voice Input &amp; Speech Recognition
          </h2>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted, #6B5C5C)', marginBottom: '1.15rem' }}>
          Yatra AI features in-line voice transcription using the browser Web Speech API. Recognized queries can be reviewed and edited before sending.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label
              htmlFor="voice-lang-select"
              style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy, #58111A)', marginBottom: '6px' }}
            >
              Default Speech Recognition Language
            </label>
            <select
              id="voice-lang-select"
              value={voiceLang}
              onChange={(e) => handleVoiceLanguageChange(e.target.value)}
              style={{
                width: '100%',
                maxWidth: '340px',
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1.5px solid var(--gold-border, #E5D2AD)',
                background: '#FFFFFF',
                color: '#1A0407',
                fontSize: '0.86rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="en-IN">English (India) [en-IN]</option>
              <option value="hi-IN">Hindi (हिंदी) [hi-IN]</option>
              <option value="pa-IN">Punjabi (ਪੰਜਾਬੀ) [pa-IN]</option>
              <option value="ur-IN">Urdu (اردو) [ur-IN]</option>
            </select>
          </div>

          <div
            style={{
              background: isSpeechAvailable ? '#F0FDF4' : '#FEF2F2',
              border: `1px solid ${isSpeechAvailable ? '#10B981' : '#EF4444'}`,
              borderRadius: '10px',
              padding: '8px 12px',
              fontSize: '0.8rem',
              color: isSpeechAvailable ? '#15803D' : '#991B1B',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {isSpeechAvailable ? (
              <>
                <CheckCircle2 size={15} />
                <span>Web Speech API is available and active in your current browser.</span>
              </>
            ) : (
              <>
                <AlertCircle size={15} />
                <span>Web Speech API is not supported in this browser. Please use Chrome, Edge, or Safari.</span>
              </>
            )}
          </div>
        </div>
      </section>

      {/* SECTION F: PRIVACY & SECURITY */}
      <section
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          padding: '1.25rem 1.4rem',
          boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
          <Shield size={18} strokeWidth={2.2} color="var(--burgundy, #58111A)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            Privacy, Security &amp; Storage
          </h2>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted, #6B5C5C)', marginBottom: '1.15rem' }}>
          Yatra AI respects your privacy. Consultation sessions are maintained locally during your visit. Simulated booking actions operate in a local sandbox without accessing external financial payment gateways.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderRadius: '8px',
              background: 'var(--bg-subtle, #F8F4EC)',
              border: '1px solid var(--border-subtle, #EBE1D0)',
              fontSize: '0.82rem',
            }}
          >
            <div>
              <span style={{ fontWeight: 700, color: 'var(--burgundy, #58111A)' }}>Active Backend Service:</span>
              <span style={{ marginLeft: '6px', color: 'var(--text-dark, #2A2020)', fontFamily: 'monospace' }}>
                {getApiBaseUrl() || (isApiConfigured() ? 'Cloudflare Pages / FastApi' : 'Disconnected')}
              </span>
            </div>
            <div style={{ fontSize: '0.74rem', color: '#166534', fontWeight: 700 }}>
              HTTPS / TLS 1.3
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: '6px' }}>
            <button
              type="button"
              onClick={handleClearCache}
              style={{
                background: '#FFFFFF',
                border: '1.5px solid var(--gold-border, #E5D2AD)',
                color: '#C0392B',
                borderRadius: '8px',
                padding: '6px 14px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Trash2 size={14} />
              <span>Clear Local Cache &amp; Reset Storage</span>
            </button>
          </div>
        </div>
      </section>

      {/* SECTION G: ABOUT YATRA AI */}
      <section
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          padding: '1.25rem 1.4rem',
          boxShadow: '0 2px 10px rgba(88, 17, 26, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
          <Info size={18} strokeWidth={2.2} color="var(--burgundy, #58111A)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            About Yatra AI
          </h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.84rem', color: 'var(--text-dark, #2A2020)' }}>
          <div>
            <strong>Application:</strong> Yatra AI — Unified Pilgrimage &amp; Tourism Assistant
          </div>
          <div>
            <strong>Version:</strong> 1.0.0 (Phase 16.1 UI/UX Refinement)
          </div>
          <div>
            <strong>Shrine Focus:</strong> Shri Mata Vaishno Devi Ji, Katra, Jammu &amp; Kashmir
          </div>
          <div>
            <strong>Project Nature:</strong> Minor Project • Academic &amp; Research Development
          </div>
          <p style={{ marginTop: '6px', fontSize: '0.78rem', color: 'var(--text-muted, #6B5C5C)', lineHeight: 1.5 }}>
            Dedicated to devotees of Shri Mata Vaishno Devi. Official parchi registrations, helicopter tickets, and room allotments must be confirmed directly through the official Shrine Board website at maavaishnodevi.org.
          </p>
        </div>
      </section>
    </div>
  );
}
