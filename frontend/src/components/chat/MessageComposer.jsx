import React, { useState, useRef } from 'react';

/**
 * Modern, anchored Message Composer with Multiline Textarea,
 * Web Speech Voice Input, Language Selector, and Keyboard Handling.
 */
export default function MessageComposer({
  onSend,
  loading = false,
  placeholder = "Ask Yatra AI (e.g. 'What places can I visit around Katra?')...",
}) {
  const [inputValue, setInputValue] = useState('');
  const [micState, setMicState] = useState('idle'); // 'idle' | 'listening' | 'processing'
  const [micStatus, setMicStatus] = useState('');
  const [selectedLang, setSelectedLang] = useState('en-IN');
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);

  // Auto-resize textarea up to 120px
  const adjustHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
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

    onSend(text);
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '42px';
    }
  };

  // Web Speech API Voice Interaction
  const toggleListening = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setMicStatus('Voice input is not supported in this browser. Try Chrome, Edge, or Safari.');
      setTimeout(() => setMicStatus(''), 4500);
      return;
    }

    if (micState === 'listening' && recognitionRef.current) {
      recognitionRef.current.stop();
      setMicState('idle');
      setMicStatus('');
      return;
    }

    try {
      const recognition = new SR();
      recognition.lang = selectedLang;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognitionRef.current = recognition;

      recognition.onstart = () => {
        setMicState('listening');
        setMicStatus('🎧 Listening... Speak your pilgrimage question.');
      };

      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        setMicState('processing');
        setMicStatus(`Recognized: "${transcript}"`);

        // Display recognized speech in the composer for review and editing
        setInputValue(transcript);
        adjustHeight();

        setTimeout(() => {
          setMicState('idle');
          setMicStatus('');
        }, 2000);
      };

      recognition.onerror = (event) => {
        setMicState('idle');
        if (event.error === 'no-speech') {
          setMicStatus("Didn't catch that. Please speak again.");
        } else if (event.error === 'not-allowed') {
          setMicStatus('Microphone access was denied. Please allow microphone permission in your browser.');
        } else {
          setMicStatus(`Voice recognition error: ${event.error}`);
        }
        setTimeout(() => setMicStatus(''), 4500);
      };

      recognition.onend = () => {
        if (micState === 'listening') {
          setMicState('idle');
        }
      };

      recognition.start();
    } catch (err) {
      console.error('Mic initialization error:', err);
      setMicState('idle');
      setMicStatus('Could not access microphone.');
      setTimeout(() => setMicStatus(''), 4000);
    }
  };

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
      {/* Mic Status Banner */}
      {micStatus && (
        <div
          data-testid="composer-mic-status"
          style={{
            background: micState === 'listening' ? '#FFF9F0' : '#FFF5F5',
            border: `1px solid ${micState === 'listening' ? 'var(--gold-border, #E5D2AD)' : '#F5C6CB'}`,
            borderRadius: '8px',
            padding: '6px 12px',
            fontSize: '0.76rem',
            color: 'var(--burgundy, #58111A)',
            fontWeight: 600,
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{micStatus}</span>
          {micState === 'listening' && (
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#C0392B',
                display: 'inline-block',
                boxShadow: '0 0 0 3px rgba(192, 57, 43, 0.25)',
              }}
            />
          )}
        </div>
      )}

      {/* Main Composer Box */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '24px',
          padding: '8px 12px',
          boxShadow: '0 4px 20px rgba(88, 17, 26, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
        }}
      >
        {/* Multiline Textarea */}
        <textarea
          ref={textareaRef}
          id="chat-user-input"
          data-testid="chat-user-input"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={loading}
          rows={1}
          style={{
            width: '100%',
            border: 'none',
            outline: 'none',
            resize: 'none',
            minHeight: '42px',
            maxHeight: '120px',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.92rem',
            lineHeight: 1.5,
            color: 'var(--text-dark, #2A2020)',
            background: 'transparent',
            padding: '4px 6px',
          }}
          aria-label="Ask Yatra AI"
        />

        {/* Action Row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid var(--border-subtle, #EBE1D0)',
            paddingTop: '6px',
            marginTop: '2px',
          }}
        >
          {/* Voice Input Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <select
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              style={{
                fontSize: '0.72rem',
                padding: '4px 8px',
                borderRadius: '8px',
                border: '1px solid var(--gold-border, #E5D2AD)',
                background: 'var(--bg-subtle, #F8F4EC)',
                color: 'var(--burgundy, #58111A)',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
              title="Select speech recognition language"
              aria-label="Speech recognition language"
            >
              <option value="en-IN">English (India)</option>
              <option value="hi-IN">Hindi (हिंदी)</option>
              <option value="pa-IN">Punjabi (ਪੰਜਾਬੀ)</option>
              <option value="ur-IN">Urdu (اردو)</option>
            </select>

            <button
              type="button"
              data-testid="composer-mic-btn"
              onClick={toggleListening}
              style={{
                background: micState === 'listening' ? '#C0392B' : 'var(--bg-subtle, #F8F4EC)',
                border: `1px solid ${micState === 'listening' ? '#C0392B' : 'var(--gold-border, #E5D2AD)'}`,
                color: micState === 'listening' ? '#FFFFFF' : 'var(--burgundy, #58111A)',
                borderRadius: '999px',
                padding: '4px 10px',
                fontSize: '0.74rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                transition: 'all 0.15s ease',
              }}
              title={micState === 'listening' ? 'Click to stop listening' : 'Speak your query via microphone'}
              aria-label="Microphone speech input"
            >
              <span>{micState === 'listening' ? '🔴' : '🎙️'}</span>
              <span>{micState === 'listening' ? 'Listening...' : 'Speak'}</span>
            </button>
          </div>

          {/* Right: Hint + Send Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              className="hide-on-mobile"
              style={{ fontSize: '0.7rem', color: 'var(--text-muted, #6B5C5C)' }}
            >
              Press Enter ↵ to send
            </span>

            <button
              type="button"
              data-testid="chat-send-btn"
              onClick={() => handleSubmit()}
              disabled={loading || !inputValue.trim()}
              className="btn btn-primary"
              style={{
                padding: '6px 14px',
                fontSize: '0.8rem',
                fontWeight: 800,
                borderRadius: '999px',
                minHeight: '34px',
                gap: '6px',
              }}
              aria-label="Send message"
            >
              {loading ? (
                <>
                  <span
                    className="spinner"
                    style={{ width: '12px', height: '12px', borderWidth: '2px', display: 'inline-block' }}
                  />
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <span>➔</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
