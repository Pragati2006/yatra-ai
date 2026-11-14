import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Send, Globe, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

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

      {/* Main Composer Box */}
      <div
        style={{
          background: '#FFFFFF',
          border: `1.5px solid ${
            micState === 'listening'
              ? '#C0392B'
              : isFocused
              ? 'var(--gold-primary, #B8860B)'
              : 'var(--gold-border, #E5D2AD)'
          }`,
          borderRadius: '20px',
          padding: '10px 14px',
          boxShadow:
            micState === 'listening'
              ? '0 0 16px rgba(192, 57, 43, 0.25)'
              : isFocused
              ? '0 0 0 3px rgba(184, 134, 11, 0.16), 0 4px 20px rgba(88, 17, 26, 0.08)'
              : '0 4px 20px rgba(88, 17, 26, 0.06)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
          colorScheme: 'light',
        }}
      >
        {/* High-Contrast Multiline Textarea */}
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
            width: '100%',
            border: 'none',
            outline: 'none',
            resize: 'none',
            minHeight: '44px',
            maxHeight: '130px',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.96rem',
            lineHeight: 1.5,
            color: '#1A0407',
            background: '#FFFFFF',
            padding: '6px 8px',
            caretColor: 'var(--burgundy, #58111A)',
            boxSizing: 'border-box',
          }}
          aria-label="Ask Yatra AI"
        />

        {/* Primary Controls Row: Language Pill + Mic Button + Send Button */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid var(--border-subtle, #EBE1D0)',
            paddingTop: '8px',
            marginTop: '2px',
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          {/* Left: Language Selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: '0.76rem',
                fontWeight: 700,
                color: 'var(--burgundy, #58111A)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Globe size={14} strokeWidth={2} />
              <span className="hide-on-mobile">Voice:</span>
            </span>
            <select
              id="composer-lang-select"
              data-testid="composer-lang-select"
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              disabled={micState === 'listening'}
              style={{
                fontSize: '0.76rem',
                padding: '4px 8px',
                borderRadius: '8px',
                border: '1px solid var(--gold-border, #E5D2AD)',
                background: 'var(--bg-subtle, #F8F4EC)',
                color: 'var(--burgundy, #58111A)',
                fontWeight: 700,
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

          {/* Right: Direct Microphone & Send Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Desktop keyboard hint */}
            <span
              className="hide-on-mobile"
              style={{ fontSize: '0.72rem', color: 'var(--text-muted, #6B5C5C)', marginRight: '4px' }}
            >
              Press Enter to send
            </span>

            {/* Recognizable Voice Input Button */}
            <button
              type="button"
              id="composer-mic-btn"
              data-testid="composer-mic-btn"
              onClick={toggleListening}
              style={{
                background: micState === 'listening' ? '#C0392B' : 'var(--gold-subtle, #F5ECDA)',
                border: `1.5px solid ${micState === 'listening' ? '#962D22' : 'var(--gold-border, #E5D2AD)'}`,
                color: micState === 'listening' ? '#FFFFFF' : 'var(--burgundy, #58111A)',
                borderRadius: '999px',
                padding: '6px 14px',
                fontSize: '0.82rem',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                minHeight: '36px',
                transition: 'all 0.2s ease',
                boxShadow: micState === 'listening' ? '0 0 10px rgba(192, 57, 43, 0.4)' : 'none',
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
              {micState === 'listening' ? (
                <>
                  <Square size={14} fill="#FFFFFF" />
                  <span>Listening...</span>
                </>
              ) : (
                <>
                  <Mic size={15} strokeWidth={2.2} />
                  <span>Voice Input</span>
                </>
              )}
            </button>

            {/* Send Button */}
            <button
              type="button"
              id="chat-send-btn"
              data-testid="chat-send-btn"
              onClick={() => handleSubmit()}
              disabled={loading || !inputValue.trim()}
              className="btn btn-primary"
              style={{
                padding: '6px 18px',
                fontSize: '0.84rem',
                fontWeight: 800,
                borderRadius: '999px',
                minHeight: '36px',
                gap: '6px',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label="Send message"
            >
              {loading ? (
                <>
                  <span
                    className="spinner"
                    style={{ width: '13px', height: '13px', borderWidth: '2px', display: 'inline-block' }}
                  />
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <Send size={14} strokeWidth={2.2} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
