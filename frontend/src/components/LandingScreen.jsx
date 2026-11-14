import React from 'react';
import YatraLogo from './common/YatraLogo';

/**
 * Clean, simplified Landing Screen for Web matching the Android SplashScreen.
 * Minimal, uncluttered, balanced alignment, Cinzel serif typography,
 * burgundy & warm ivory brand palette.
 */
export default function LandingScreen({ onStartJourney, onSignIn }) {
  return (
    <div
      data-testid="landing-screen"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 80px)',
        padding: '2rem 1.5rem',
        textAlign: 'center',
        maxWidth: '680px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* Brand Logo */}
      <YatraLogo
        size={88}
        style={{
          marginBottom: '1.5rem',
          filter: 'drop-shadow(0 8px 24px rgba(88, 17, 26, 0.2))',
        }}
      />

      {/* Yatra AI Title */}
      <h1
        style={{
          fontFamily: 'var(--font-serif, Cinzel, serif)',
          fontSize: 'clamp(2.2rem, 5vw, 3rem)',
          fontWeight: 800,
          color: 'var(--burgundy, #58111A)',
          letterSpacing: '0.04em',
          lineHeight: 1.15,
          marginBottom: '0.4rem',
        }}
      >
        Yatra AI
      </h1>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 'clamp(1rem, 2.2vw, 1.25rem)',
          fontWeight: 600,
          color: 'var(--text-dark, #2A2020)',
          marginBottom: '1rem',
          letterSpacing: '0.02em',
        }}
      >
        Unified Pilgrimage &amp; Tourism Assistant
      </div>

      {/* Edition Badge */}
      <div
        style={{
          display: 'inline-block',
          background: 'var(--gold-subtle, #F5ECDA)',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '999px',
          padding: '6px 18px',
          fontSize: '0.76rem',
          fontWeight: 800,
          letterSpacing: '0.12em',
          color: 'var(--burgundy, #58111A)',
          textTransform: 'uppercase',
          marginBottom: '1.5rem',
        }}
      >
        MAA VAISHNO DEVI YATRA EDITION
      </div>

      {/* Introductory Text */}
      <p
        style={{
          fontSize: 'clamp(0.95rem, 2vw, 1.05rem)',
          color: 'var(--text-muted, #6B5C5C)',
          lineHeight: 1.6,
          maxWidth: '480px',
          marginBottom: '2.5rem',
        }}
      >
        Your intelligent companion for a smoother pilgrimage journey.
      </p>

      {/* Action Buttons */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          width: '100%',
          maxWidth: '320px',
          marginBottom: '2.5rem',
        }}
      >
        <button
          type="button"
          data-testid="landing-begin-journey-btn"
          onClick={onStartJourney}
          className="btn btn-primary"
          style={{
            padding: '0.85rem 2rem',
            fontSize: '0.96rem',
            fontWeight: 800,
            borderRadius: '999px',
            boxShadow: '0 4px 16px rgba(88, 17, 26, 0.22)',
            cursor: 'pointer',
          }}
        >
          Begin Your Journey
        </button>

        <button
          type="button"
          data-testid="landing-signin-btn"
          onClick={onSignIn}
          className="btn btn-secondary"
          style={{
            padding: '0.78rem 1.8rem',
            fontSize: '0.92rem',
            fontWeight: 700,
            borderRadius: '999px',
            background: '#FFFFFF',
            border: '1.5px solid var(--gold-border, #E5D2AD)',
            color: 'var(--burgundy, #58111A)',
            cursor: 'pointer',
          }}
        >
          Sign In / Devotee Login
        </button>
      </div>

      {/* Official Booking Disclaimer */}
      <p
        style={{
          fontSize: '0.75rem',
          color: 'var(--text-muted, #8C7A7A)',
          lineHeight: 1.5,
          maxWidth: '440px',
          borderTop: '1px solid var(--border-subtle, #EBE1D0)',
          paddingTop: '1.25rem',
        }}
      >
        Dedicated to devotees of Shri Mata Vaishno Devi. Official parchi bookings must be confirmed via maavaishnodevi.org.
      </p>
    </div>
  );
}
