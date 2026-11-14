import React from 'react';

/**
 * Official Yatra AI Vector Brand Logo
 * Features:
 * - Deep Burgundy circular shield (#58111A)
 * - Muted gold perimeter trim (#D4AF37)
 * - Sacred Trikuta Mountain Peaks (symbolizing Maa Vaishno Devi's abode)
 * - Ascending golden pilgrimage trail (Yatra)
 * - Guiding AI summit star (symbolizing AI assistance & illumination)
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
      {/* Deep Burgundy Circular Shield with Gold Trim */}
      <circle cx="50" cy="50" r="47" fill="#58111A" stroke="#D4AF37" strokeWidth="2.5" />
      <circle cx="50" cy="50" r="43" fill="none" stroke="#E5D2AD" strokeWidth="0.75" strokeOpacity="0.6" strokeDasharray="2 2" />

      {/* Trikuta Mountain Peaks in Sacred Gold */}
      <polygon points="18,68 35,42 48,68" fill="#B8860B" opacity="0.55" />
      <polygon points="52,68 65,42 82,68" fill="#B8860B" opacity="0.55" />
      <polygon points="26,70 50,26 74,70" fill="url(#yatraLogoGrad)" opacity="0.95" />
      <polygon points="50,26 50,70 74,70" fill="#7A4B08" opacity="0.25" />

      {/* Ascending Pilgrimage Path (Yatra) */}
      <path d="M44,78 Q50,64 47,54 T50,38" stroke="#FFFDF9" strokeWidth="2.2" strokeLinecap="round" fill="none" />

      {/* Guiding AI Star / Divine Jyoti at Summit */}
      <circle cx="50" cy="22" r="3" fill="#FFFDF9" />
      <path d="M50,15 L50,29 M43,22 L57,22" stroke="#E5D2AD" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M45,17 L55,27 M45,27 L55,17" stroke="#D4AF37" strokeWidth="0.9" strokeLinecap="round" />

      {/* Base Foundation Arc */}
      <path d="M22,76 C36,83 64,83 78,76" stroke="#D4AF37" strokeWidth="1.5" strokeLinecap="round" fill="none" />

      <defs>
        <linearGradient id="yatraLogoGrad" x1="26" y1="26" x2="74" y2="70" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FAF5EB" />
          <stop offset="35%" stopColor="#E5D2AD" />
          <stop offset="70%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#996515" />
        </linearGradient>
      </defs>
    </svg>
  );
}
