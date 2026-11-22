import React from 'react';

/**
 * Official Yatra AI Master Vector Brand Logo
 * Master Visual Identity:
 * - Deep Burgundy circular shield (#58111A)
 * - Muted gold perimeter trim (#D4AF37 / #B8860B gradient)
 * - Sacred Trishul / Trident emblem & lotus base
 * - Sacred Tilak / Bindi (#C0392B)
 */
export default function YatraLogo({ size = 32, className = '', style = {} }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
      aria-label="Yatra AI Logo"
      role="img"
    >
      <defs>
        <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#B8860B" />
        </linearGradient>
      </defs>

      {/* Sacred Deep Burgundy Shield & Golden Perimeter */}
      <circle cx="50" cy="50" r="46" fill="#58111A" stroke="url(#goldGradient)" strokeWidth="3" />
      <circle cx="50" cy="50" r="41" stroke="#D4AF37" strokeWidth="1.2" strokeDasharray="3 3" opacity="0.65" />

      {/* Central Trishul / Lotus Sacred Emblem */}
      {/* Central Trident Blade */}
      <path
        d="M50 16 L53 38 L50 42 L47 38 Z"
        fill="url(#goldGradient)"
      />
      {/* Left Crescent Flame */}
      <path
        d="M50 42 C38 42 32 30 32 24 C36 28 42 32 48 35 Z"
        fill="url(#goldGradient)"
      />
      {/* Right Crescent Flame */}
      <path
        d="M50 42 C62 42 68 30 68 24 C64 28 58 32 52 35 Z"
        fill="url(#goldGradient)"
      />
      {/* Trident Shaft */}
      <path
        d="M48.5 42 L51.5 42 L51 76 L49 76 Z"
        fill="url(#goldGradient)"
      />
      {/* Lotus Petal Base */}
      <path
        d="M36 72 C42 66 50 68 50 68 C50 68 58 66 64 72 C58 78 42 78 36 72 Z"
        fill="#58111A"
        stroke="url(#goldGradient)"
        strokeWidth="1.5"
      />
      {/* Sacred Bindi / Tilak */}
      <circle cx="50" cy="22" r="2.5" fill="#C0392B" />
    </svg>
  );
}
