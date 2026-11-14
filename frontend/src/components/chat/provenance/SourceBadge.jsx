/**
 * frontend/src/components/chat/provenance/SourceBadge.jsx
 * Compact, interactive badge representing a single data source.
 */

import React from 'react';
import FreshnessIndicator from './FreshnessIndicator';
import { getEffectiveSourceLabel } from './provenanceUtils';

export default function SourceBadge({
  source,
  onClick = null,
  isInteractive = false,
  compact = false,
  style = {},
}) {
  if (!source || typeof source !== 'object') {
    return null;
  }

  const effectiveLabel = getEffectiveSourceLabel(source);
  const name = source.source_name || source.name || effectiveLabel;
  const isClickable = Boolean(isInteractive && onClick);

  const handleKeyDown = (e) => {
    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick(source);
    }
  };

  return (
    <div
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={isClickable ? () => onClick(source) : undefined}
      onKeyDown={handleKeyDown}
      aria-label={`Source: ${name}, ${effectiveLabel}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '6px',
        padding: compact ? '2px 6px' : '3px 8px',
        fontSize: '0.70rem',
        color: 'var(--text-dark, #2A2020)',
        cursor: isClickable ? 'pointer' : 'default',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)',
        transition: 'all 0.15s ease',
        outline: 'none',
        ...style,
      }}
    >
      <span
        style={{
          fontWeight: 600,
          color: 'var(--burgundy, #58111A)',
          maxWidth: compact ? '140px' : '220px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {name}
      </span>

      <FreshnessIndicator
        freshnessStatus={source.freshness_status}
        sourceType={source.source_type}
        customText={effectiveLabel}
        showLabel={true}
      />
    </div>
  );
}
