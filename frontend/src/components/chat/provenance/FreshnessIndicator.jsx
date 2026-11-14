/**
 * frontend/src/components/chat/provenance/FreshnessIndicator.jsx
 * Compact, accessible indicator for data freshness.
 * Always renders readable text alongside visual cues to meet WCAG accessibility standards.
 */

import React from 'react';
import { getFreshnessStyle } from './provenanceUtils';

export default function FreshnessIndicator({
  freshnessStatus,
  sourceType,
  showLabel = true,
  customText = null,
  style = {},
}) {
  const meta = getFreshnessStyle(freshnessStatus, sourceType);
  const displayText = customText || meta.label;

  return (
    <span
      role="status"
      aria-label={meta.ariaLabel}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        background: meta.bg,
        color: meta.color,
        border: `1px solid ${meta.border}`,
        borderRadius: '999px',
        padding: '2px 8px',
        fontSize: '0.68rem',
        fontWeight: 700,
        lineHeight: 1.2,
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      <span aria-hidden="true" style={{ fontSize: '0.72rem' }}>
        {meta.icon}
      </span>
      {showLabel && <span>{displayText}</span>}
    </span>
  );
}
