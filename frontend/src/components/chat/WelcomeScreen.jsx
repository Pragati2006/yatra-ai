import React from 'react';

/**
 * Modern, elegant Welcome Screen displayed when user begins a new conversation.
 * Inspired by ChatGPT / Gemini interaction design.
 */
export default function WelcomeScreen({ onSelectPrompt }) {
  const suggestedPrompts = [
    {
      icon: '🗺️',
      title: 'Plan my Vaishno Devi trip',
      desc: 'Create a tailored multi-day pilgrimage with transport & itinerary',
      query: 'Plan my Vaishno Devi trip',
    },
    {
      icon: '🏨',
      title: 'Find accommodation in Katra',
      desc: 'Explore verified hotels, guest houses, and shrine board dorms',
      query: 'Find accommodation in Katra',
    },
    {
      icon: '🕉️',
      title: 'Tell me about Mata Vaishno Devi',
      desc: 'Holy Cave history, Bhairavnath story, and sacred rituals',
      query: 'Tell me about Mata Vaishno Devi',
    },
    {
      icon: '⛅',
      title: 'Check the weather in Katra',
      desc: 'Live mountain temperature, forecast, and trekking conditions',
      query: 'Check the weather in Katra',
    },
    {
      icon: '🎫',
      title: 'Help me with booking',
      desc: 'Assistance with yatra slots, transport tickets, and guided booking',
      query: 'Help me with booking',
    },
    {
      icon: '🚆',
      title: 'Trains from Delhi to Katra',
      desc: 'Compare Vande Bharat, Shri Shakti, and Jammu mail schedules',
      query: 'Trains from Delhi to Katra',
    },
  ];

  return (
    <div
      data-testid="chat-welcome-screen"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '2.5rem 1rem 1.5rem',
        maxWidth: '720px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* Brand Icon with subtle spiritual glow */}
      <div
        style={{
          width: '58px',
          height: '58px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--burgundy, #58111A) 0%, var(--burgundy-dark, #3D0810) 100%)',
          border: '2px solid var(--gold-primary, #B8860B)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.75rem',
          color: '#E5D2AD',
          boxShadow: '0 8px 24px rgba(88, 17, 26, 0.18)',
          marginBottom: '1.25rem',
        }}
      >
        🔱
      </div>

      {/* Suggested Heading */}
      <h1
        style={{
          fontFamily: 'var(--font-serif, Cinzel, serif)',
          fontSize: 'clamp(1.5rem, 3.2vw, 2.1rem)',
          fontWeight: 800,
          color: 'var(--burgundy, #58111A)',
          lineHeight: 1.25,
          marginBottom: '0.65rem',
          letterSpacing: '0.02em',
        }}
      >
        Where would you like your journey to begin?
      </h1>

      {/* Supporting Text */}
      <p
        style={{
          fontSize: 'clamp(0.88rem, 1.8vw, 0.98rem)',
          color: 'var(--text-muted, #6B5C5C)',
          maxWidth: '560px',
          lineHeight: 1.55,
          marginBottom: '2rem',
        }}
      >
        Ask me about Vaishno Devi, pilgrimage planning, accommodation, transport, weather, itineraries and booking assistance.
      </p>

      {/* Prompt Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '10px',
          width: '100%',
        }}
      >
        {suggestedPrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            data-testid={`suggested-prompt-${idx}`}
            onClick={() => onSelectPrompt(p.query)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              textAlign: 'left',
              background: '#FFFFFF',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              borderRadius: '14px',
              padding: '12px 14px',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow: '0 2px 8px rgba(88, 17, 26, 0.03)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--gold-primary, #B8860B)';
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 16px rgba(88, 17, 26, 0.08)';
              e.currentTarget.style.background = 'var(--bg-subtle, #F8F4EC)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--gold-border, #E5D2AD)';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(88, 17, 26, 0.03)';
              e.currentTarget.style.background = '#FFFFFF';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '1.15rem' }}>{p.icon}</span>
              <span
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 700,
                  fontSize: '0.86rem',
                  color: 'var(--burgundy, #58111A)',
                }}
              >
                {p.title}
              </span>
            </div>
            <div
              style={{
                fontSize: '0.74rem',
                color: 'var(--text-muted, #6B5C5C)',
                lineHeight: 1.35,
              }}
            >
              {p.desc}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
