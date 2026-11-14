import React from 'react';
import { Compass, Building2, Sparkles, CloudSun, Train, Luggage } from 'lucide-react';
import YatraLogo from '../common/YatraLogo';

/**
 * Modern, elegant Welcome Screen displayed when devotee begins a new conversation.
 * Clean, uncluttered, professional line icons, Cinzel serif typography,
 * deep burgundy & warm gold aesthetic. Zero emojis.
 */
export default function WelcomeScreen({ onSelectPrompt }) {
  const suggestedPrompts = [
    {
      icon: Compass,
      title: 'Plan my Vaishno Devi trip',
      desc: 'Create a tailored multi-day pilgrimage with transport & itinerary',
      query: 'Plan a comfortable two-day Vaishno Devi trip from Jammu with my family',
    },
    {
      icon: Building2,
      title: 'Find accommodation in Katra',
      desc: 'Explore verified dharamshalas, hotels, and Shrine Board complexes',
      query: 'Find accommodation options in Katra',
    },
    {
      icon: Sparkles,
      title: 'Darshan and Yatra Registration',
      desc: 'RFID Yatra Access Card, Bhawan trek routes, and Aarti rituals',
      query: 'What is the procedure for Vaishno Devi darshan and RFID registration?',
    },
    {
      icon: CloudSun,
      title: 'Check mountain weather',
      desc: 'Live mountain temperature, forecast, and base vs Bhawan conditions',
      query: 'Check current weather and temperature at Katra and Bhawan',
    },
    {
      icon: Train,
      title: 'Transport from Jammu & Delhi',
      desc: 'Compare Indian Railways, JKSRTC buses, and flight transfers',
      query: 'What are the transport options from Jammu to Katra?',
    },
    {
      icon: Luggage,
      title: 'Yatra packing essentials',
      desc: 'Trek footwear, winter layers, document requirements, and advisories',
      query: 'What should we pack and carry for the Vaishno Devi pilgrimage?',
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
        maxWidth: '740px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* Brand Vector Logo with subtle spiritual elevation */}
      <YatraLogo
        size={64}
        style={{
          marginBottom: '1.25rem',
          filter: 'drop-shadow(0 6px 18px rgba(88, 17, 26, 0.22))',
        }}
      />

      {/* Suggested Heading */}
      <h1
        style={{
          fontFamily: 'var(--font-serif, Cinzel, serif)',
          fontSize: 'clamp(1.5rem, 3.2vw, 2.15rem)',
          fontWeight: 800,
          color: 'var(--burgundy, #58111A)',
          lineHeight: 1.25,
          marginBottom: '0.65rem',
          letterSpacing: '0.02em',
        }}
      >
        Where would you like your pilgrimage to begin?
      </h1>

      {/* Supporting Description */}
      <p
        style={{
          fontSize: 'clamp(0.88rem, 1.8vw, 0.98rem)',
          color: 'var(--text-muted, #6B5C5C)',
          maxWidth: '580px',
          lineHeight: 1.55,
          marginBottom: '2rem',
        }}
      >
        Your unified AI-powered pilgrimage and tourism assistant. Ask about sacred Maa Vaishno Devi darshan guidance, Katra stays, multimodal travel routes, mountain elevation weather, and itemized budgets.
      </p>

      {/* Prompt Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '12px',
          width: '100%',
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
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                textAlign: 'left',
                background: '#FFFFFF',
                border: '1.5px solid var(--gold-border, #E5D2AD)',
                borderRadius: '14px',
                padding: '14px 16px',
                cursor: 'pointer',
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                boxShadow: '0 2px 8px rgba(88, 17, 26, 0.03)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--gold-primary, #B8860B)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 16px rgba(88, 17, 26, 0.08)';
                e.currentTarget.style.background = '#FFFCF7';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--gold-border, #E5D2AD)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(88, 17, 26, 0.03)';
                e.currentTarget.style.background = '#FFFFFF';
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'var(--gold-subtle, #F5ECDA)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--burgundy, #58111A)',
                  marginBottom: '10px',
                }}
              >
                <Icon size={18} strokeWidth={2} />
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-serif, Cinzel, serif)',
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  color: 'var(--burgundy, #58111A)',
                  marginBottom: '4px',
                  lineHeight: 1.3,
                }}
              >
                {p.title}
              </div>
              <div
                style={{
                  fontSize: '0.76rem',
                  color: 'var(--text-muted, #6B5C5C)',
                  lineHeight: 1.4,
                }}
              >
                {p.desc}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
