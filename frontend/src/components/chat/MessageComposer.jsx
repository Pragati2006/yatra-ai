import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Send, Globe, AlertCircle, CheckCircle2, Loader2, Calendar, Plus, ArrowUp } from 'lucide-react';

const SUPPORTED_LANGUAGES = [
  { code: 'en-IN', label: 'English (India)', native: 'English' },
  { code: 'hi-IN', label: 'Hindi (हिंदी)', native: 'हिंदी' },
  { code: 'pa-IN', label: 'Punjabi (ਪੰਜਾਬੀ)', native: 'ਪੰਜਾਬੀ' },
  { code: 'ur-IN', label: 'Urdu (اردو)', native: 'اردو' },
];

/**
 * Enhanced Message Composer:
 * - High-contrast, crystal-clear input visibility across light and dark modes
 * - Professional Lucide icon system (Zero emojis)
 * - Distinct visual voice states: IDLE, LISTENING, PROCESSING, COMPLETED, ERROR
 * - User review and inline editing before sending (no auto-submission)
 * - Multi-language voice support (English, Hindi, Punjabi, Urdu)
 */
export default function MessageComposer({
  onSend,
  loading = false,
  placeholder = "Ask Yatra AI (e.g. 'How to reach Bhawan from Katra?')...",
}) {
  const [inputValue, setInputValue] = useState('');
  const [micState, setMicState] = useState('idle'); // 'idle' | 'listening' | 'processing' | 'completed' | 'error'
  const [micStatus, setMicStatus] = useState('');
  const [selectedLang, setSelectedLang] = useState('en-IN');
  const [isSupported, setIsSupported] = useState(true);
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check Web Speech API availability on mount
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setIsSupported(false);
    }
  }, []);

  // Cleanup speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  // Auto-resize textarea dynamically
  const adjustHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 130)}px`;
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    adjustHeight();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = (customText) => {
    const text = (customText !== undefined ? customText : inputValue).trim();
    if (!text || loading) return;

    // If currently listening, stop recognition before sending
    if (micState === 'listening' && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      setMicState('idle');
      setMicStatus('');
    }

    onSend(text);
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '42px';
    }
  };

  // Web Speech API Voice Recognition Toggle
  const toggleListening = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setMicState('error');
      setMicStatus('Voice input is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.');
      setTimeout(() => {
        setMicState('idle');
        setMicStatus('');
      }, 5000);
      return;
    }

    // If already listening, stop it cleanly
    if (micState === 'listening') {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
      setMicState('idle');
      setMicStatus('');
      return;
    }

    try {
      const recognition = new SR();
      recognition.lang = selectedLang;
      recognition.interimResults = true; // Stream interim results into input
      recognition.continuous = false;
      recognition.maxAlternatives = 1;
      recognitionRef.current = recognition;

      const activeLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLang) || SUPPORTED_LANGUAGES[0];

      recognition.onstart = () => {
        setMicState('listening');
        setMicStatus(`Listening in ${activeLangObj.label}... Speak clearly into your microphone.`);
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += trans;
          } else {
            interimTranscript += trans;
          }
        }

        const currentSpeech = finalTranscript || interimTranscript;
        if (currentSpeech) {
          setInputValue((prev) => {
            if (!prev.trim()) return currentSpeech;
            return `${prev.trim()} ${currentSpeech}`;
          });
          adjustHeight();
        }

        if (finalTranscript) {
          setMicState('completed');
          setMicStatus(`Transcribed: "${finalTranscript.trim()}" — Review or press Send.`);
          setTimeout(() => {
            setMicState('idle');
            setMicStatus('');
          }, 4000);
        }
      };

      recognition.onerror = (event) => {
        setMicState('error');
        if (event.error === 'no-speech') {
          setMicStatus("Didn't detect speech. Please click Voice Input and speak again.");
        } else if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setMicStatus('Microphone permission was denied. Please allow microphone access in your browser settings.');
        } else if (event.error === 'network') {
          setMicStatus('Speech recognition network error. Please verify your internet connection.');
        } else {
          setMicStatus(`Voice recognition notice: ${event.error}. Please try again.`);
        }
        setTimeout(() => {
          setMicState('idle');
          setMicStatus('');
        }, 5000);
      };

      recognition.onend = () => {
        if (micState === 'listening') {
          setMicState('idle');
        }
      };

      recognition.start();
    } catch (err) {
      console.error('Speech recognition initiation error:', err);
      setMicState('error');
      setMicStatus('Could not access microphone. Please check system audio permissions.');
      setTimeout(() => {
        setMicState('idle');
        setMicStatus('');
      }, 4000);
    }
  };

  const activeLang = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLang) || SUPPORTED_LANGUAGES[0];

  return (
    <div
      data-testid="chat-composer-wrapper"
      style={{
        width: '100%',
        maxWidth: '820px',
        margin: '0 auto',
        padding: '0.75rem 1rem 1rem',
      }}
    >
      {/* Live Voice Listening & Status Banner */}
      {micStatus && (
        <div
          data-testid="composer-mic-status"
          style={{
            background:
              micState === 'listening'
                ? '#FFF5F5'
                : micState === 'error'
                ? '#FFF0F0'
                : micState === 'completed'
                ? '#F0FDF4'
                : '#FFF9F0',
            border: `1.5px solid ${
              micState === 'listening'
                ? '#C0392B'
                : micState === 'error'
                ? '#E74C3C'
                : micState === 'completed'
                ? '#16A34A'
                : 'var(--gold-border, #E5D2AD)'
            }`,
            borderRadius: '12px',
            padding: '8px 14px',
            fontSize: '0.82rem',
            color:
              micState === 'error'
                ? '#900C3F'
                : micState === 'completed'
                ? '#15803D'
                : 'var(--burgundy, #58111A)',
            fontWeight: 700,
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: micState === 'listening' ? '0 0 12px rgba(192, 57, 43, 0.2)' : 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {micState === 'listening' ? (
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: '#C0392B',
                  display: 'inline-block',
                  boxShadow: '0 0 0 3px rgba(192, 57, 43, 0.3)',
                }}
              />
            ) : micState === 'error' ? (
              <AlertCircle size={16} color="#E74C3C" />
            ) : micState === 'completed' ? (
              <CheckCircle2 size={16} color="#16A34A" />
            ) : (
              <Loader2 size={16} className="spin" />
            )}
            <span>{micStatus}</span>
          </div>
          {micState === 'listening' && (
            <button
              type="button"
              onClick={toggleListening}
              style={{
                background: '#C0392B',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '999px',
                padding: '3px 10px',
                fontSize: '0.74rem',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
              title="Stop listening"
            >
              <Square size={12} fill="#FFFFFF" />
              <span>Stop</span>
            </button>
          )}
        </div>
      )}

      {/* Floating Modern AI Composer Container */}
      <div
        style={{
          background: 'var(--surface-white, #FFFCF9)',
          border: `1.5px solid ${
            micState === 'listening'
              ? 'var(--status-error, #C75A60)'
              : isFocused
              ? 'var(--royal-plum, #54152D)'
              : 'var(--border-default, #E9DED6)'
          }`,
          borderRadius: '24px',
          padding: '8px 14px 10px 14px',
          boxShadow: isFocused
            ? '0 0 0 3px rgba(84, 21, 45, 0.08), 0 6px 20px rgba(84, 21, 45, 0.06)'
            : '0 4px 16px rgba(84, 21, 45, 0.04)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          transition: 'all 0.2s ease',
          colorScheme: 'light',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Quick Action (+) button (Preserves data-testid="composer-calendar-btn") */}
          <button
            type="button"
            data-testid="composer-calendar-btn"
            onClick={() => {
              if (onSend) {
                onSend("Change my travel date to 27 November");
              }
            }}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'var(--secondary-bg, #F2EAE4)',
              border: '1px solid var(--border-default, #E9DED6)',
              color: 'var(--royal-plum, #54152D)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              flexShrink: 0,
              transition: 'all 0.15s ease',
            }}
            title="Travel Options & Dates"
            aria-label="Options"
          >
            <Plus size={16} strokeWidth={2.4} />
          </button>

          {/* Multiline Textarea */}
          <textarea
            ref={textareaRef}
            id="chat-user-input"
            data-testid="chat-user-input"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={micState === 'listening' ? `Listening in ${activeLang.label}... speak now` : placeholder}
            disabled={loading}
            rows={1}
            style={{
              flex: 1,
              width: '100%',
              border: 'none',
              outline: 'none',
              resize: 'none',
              minHeight: '38px',
              maxHeight: '130px',
              fontFamily: 'var(--font-sans)',
              fontSize: '0.96rem',
              lineHeight: 1.5,
              color: 'var(--text-primary, #30272A)',
              background: 'transparent',
              padding: '6px 4px',
              caretColor: 'var(--royal-plum, #54152D)',
              boxSizing: 'border-box',
            }}
            aria-label="Ask Yatra AI"
          />

          {/* Voice Input Button */}
          <button
            type="button"
            id="composer-mic-btn"
            data-testid="composer-mic-btn"
            onClick={toggleListening}
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              background: micState === 'listening' ? 'var(--status-error, #C75A60)' : 'var(--secondary-bg, #F2EAE4)',
              border: `1px solid ${micState === 'listening' ? 'transparent' : 'var(--border-default, #E9DED6)'}`,
              color: micState === 'listening' ? '#FFFFFF' : 'var(--royal-plum, #54152D)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.15s ease',
            }}
            title={
              !isSupported
                ? 'Voice recognition not supported in this browser'
                : micState === 'listening'
                ? 'Listening... Click to stop voice input'
                : `Voice Input: Click to speak in ${activeLang.label}`
            }
            aria-label={micState === 'listening' ? 'Stop voice listening' : 'Voice Input: Click to speak'}
          >
            {micState === 'listening' ? <Square size={13} fill="#FFFFFF" /> : <Mic size={16} strokeWidth={2.2} />}
          </button>

          {/* Royal Plum Circular Send Button with Clean Arrow-Up */}
          <button
            type="button"
            id="chat-send-btn"
            data-testid="chat-send-btn"
            onClick={() => handleSubmit()}
            disabled={loading || !inputValue.trim()}
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: loading || !inputValue.trim() ? 'var(--secondary-bg, #F2EAE4)' : 'var(--royal-plum, #54152D)',
              border: 'none',
              color: loading || !inputValue.trim() ? 'var(--text-muted, #A39994)' : '#FFFFFF',
              cursor: loading || !inputValue.trim() ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.18s ease',
              boxShadow: !inputValue.trim() ? 'none' : '0 2px 8px rgba(84, 21, 45, 0.25)',
            }}
            aria-label="Send message"
          >
            {loading ? (
              <span className="spinner" style={{ width: '13px', height: '13px', borderWidth: '2px', display: 'inline-block' }} />
            ) : (
              <ArrowUp size={18} strokeWidth={2.4} />
            )}
          </button>
        </div>

        {/* Subtle Bottom Metadata Row: Language Selector */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px', fontSize: '0.74rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-secondary, #796D69)' }}>
            <Globe size={13} strokeWidth={2} />
            <select
              id="composer-lang-select"
              data-testid="composer-lang-select"
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              disabled={micState === 'listening'}
              style={{
                fontSize: '0.74rem',
                border: 'none',
                background: 'transparent',
                color: 'var(--royal-plum, #54152D)',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
              title="Select voice recognition language"
              aria-label="Voice recognition language"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>
          <span className="hide-on-mobile" style={{ color: 'var(--text-muted, #A39994)', fontSize: '0.72rem' }}>
            Yatra AI provides pilgrimage guidance · Verify train &amp; darshan bookings
          </span>
        </div>
      </div>
    </div>
  );
}
