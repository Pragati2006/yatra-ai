import React from 'react';
import Svg, { Path, Circle, Defs, LinearGradient, Stop } from 'react-native-svg';

export default function YatraLogo({ size = 36 }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Defs>
        <LinearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <Stop offset="0%" stopColor="#D4AF37" />
          <Stop offset="100%" stopColor="#B8860B" />
        </LinearGradient>
      </Defs>
      {/* Sacred Outer Ring */}
      <Circle cx="50" cy="50" r="46" stroke="url(#goldGradient)" strokeWidth="3" />
      <Circle cx="50" cy="50" r="41" stroke="#58111A" strokeWidth="1.5" strokeDasharray="3 3" />

      {/* Central Trishul / Lotus Sacred Emblem */}
      {/* Central Trident Blade */}
      <Path
        d="M50 16 L53 38 L50 42 L47 38 Z"
        fill="url(#goldGradient)"
      />
      {/* Left Crescent Flame */}
      <Path
        d="M50 42 C38 42 32 30 32 24 C36 28 42 32 48 35 Z"
        fill="url(#goldGradient)"
      />
      {/* Right Crescent Flame */}
      <Path
        d="M50 42 C62 42 68 30 68 24 C64 28 58 32 52 35 Z"
        fill="url(#goldGradient)"
      />
      {/* Trident Shaft */}
      <Path
        d="M48.5 42 L51.5 42 L51 76 L49 76 Z"
        fill="url(#goldGradient)"
      />
      {/* Lotus Petal Base */}
      <Path
        d="M36 72 C42 66 50 68 50 68 C50 68 58 66 64 72 C58 78 42 78 36 72 Z"
        fill="#58111A"
        stroke="url(#goldGradient)"
        strokeWidth="1.5"
      />
      {/* Sacred Bindi / Tilak */}
      <Circle cx="50" cy="22" r="2.5" fill="#C0392B" />
    </Svg>
  );
}
