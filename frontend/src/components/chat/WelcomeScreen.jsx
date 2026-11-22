import React from 'react';
import { Compass, Mountain, Train, MapPin, CloudSun, Calendar } from 'lucide-react';
import YatraLogo from '../common/YatraLogo';

/**
 * Phase 8.6 Modern AI Application Welcome Experience
 * Clean, spacious, conversational layout inspired by modern AI assistants.
 * Palette: Royal Plum (#54152D), Champagne Taupe (#A3826C), Warm Ivory (#F7F1EB), Soft Plum (#F0E3E7).
 */
export default function WelcomeScreen({ onSelectPrompt }) {
  const suggestedPrompts = [
    {
      icon: Compass,
      title: 'Plan my Vaishno Devi trip',
      query: 'Plan a comfortable two-day Vaishno Devi pilgrimage with transport and Bhawan accommodation',
    },
    {
      icon: Mountain,
      title: 'Explore Kashmir',
      query: 'Tell me about visiting Dal Lake, Pari Mahal, and Gulmarg in Kashmir',
    },
    {
      icon: Train,
      title: 'Find trains to Katra',
      query: 'Find trains from Delhi to Katra including Vande Bharat Express',
    },
    {
      icon: MapPin,
      title: 'Show nearby attractions',
      query: 'Show verified sightseeing attractions and tourist spots around Katra and Jammu',
    },
    {
      icon: CloudSun,
      title: 'Check weather in Srinagar',
      query: 'Check current weather, temperature, and seasonal forecast in Srinagar and Katra',
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
        padding: '3rem 1.25rem 2rem',
        maxWidth: '720px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* Brand Vector Logo */}
      <YatraLogo
        size={56}
        style={{
          marginBottom: '1rem',
          filter: 'drop-shadow(0 4px 12px rgba(84, 21, 45, 0.15))',
        }}
      />

      {/* Subtle Devotional Greeting */}
      <div
        style={{
          fontSize: '0.78rem',
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'var(--champagne-taupe, #A3826C)',
          marginBottom: '0.5rem',
        }}
      >
        Jai Mata Di
      </div>

      {/* Primary Heading */}
      <h1
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 'clamp(1.75rem, 3.5vw, 2.35rem)',
          fontWeight: 700,
          color: 'var(--royal-plum, #54152D)',
          lineHeight: 1.2,
          marginBottom: '0.5rem',
          letterSpacing: '-0.01em',
        }}
      >
        Where would you like to go?
      </h1>

      {/* Supporting Text */}
      <p
        style={{
          fontSize: 'clamp(0.92rem, 1.8vw, 1.02rem)',
          color: 'var(--text-secondary, #796D69)',
          maxWidth: '480px',
          lineHeight: 1.5,
          marginBottom: '2.25rem',
        }}
      >
        Your journey, thoughtfully planned.
      </p>

      {/* Modern Suggestion Chips */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '10px',
          width: '100%',
          maxWidth: '640px',
        }}
      >
        {suggestedPrompts.map((p, idx) => {
          const Icon = p.icon;
          return (
            <button
              key={idx}
              type="button"
              data-testid={`suggested-prompt-${idx}`}
              onClick={() => onSelectPrompt(p.query)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--surface-white, #FFFCF9)',
                border: '1px solid var(--border-default, #E9DED6)',
                borderRadius: '999px',
                padding: '9px 16px',
                cursor: 'pointer',
                transition: 'all 0.18s ease',
                boxShadow: '0 1px 3px rgba(84, 21, 45, 0.04)',
                color: 'var(--text-primary, #30272A)',
                fontSize: '0.86rem',
                fontWeight: 600,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--champagne-taupe, #A3826C)';
                e.currentTarget.style.background = 'var(--soft-plum-surface, #F0E3E7)';
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 3px 10px rgba(84, 21, 45, 0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-default, #E9DED6)';
                e.currentTarget.style.background = 'var(--surface-white, #FFFCF9)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(84, 21, 45, 0.04)';
              }}
            >
              <Icon size={15} color="var(--royal-plum, #54152D)" strokeWidth={2} />
              <span>{p.title}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
