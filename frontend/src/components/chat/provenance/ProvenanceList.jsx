/**
 * frontend/src/components/chat/provenance/ProvenanceList.jsx
 * Unified message-level source attribution and freshness component for Yatra AI.
 * Self-contained, responsive, keyboard-accessible, and truth-grounded.
 */

import React, { useState } from 'react';
import { ScrollText, AlertTriangle, Info } from 'lucide-react';
import { extractValidProvenance } from './provenanceUtils';
import SourceBadge from './SourceBadge';
import FreshnessIndicator from './FreshnessIndicator';
import SourceDetailsPopover from './SourceDetailsPopover';

export default function ProvenanceList({ message }) {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  if (!message || message.role === 'user') {
    return null;
  }

  const sources = extractValidProvenance(message);
  const isCached = Boolean(message.is_cached);
  const partialFailure = Boolean(message.partial_failure);
  const toolExecutions = message.tool_executions || [];

  // If there are no sources, no cache flag, and no partial failure, omit
  if (sources.length === 0 && !isCached && !partialFailure) {
    return null;
  }

  const handleOpen = () => setIsPopoverOpen(true);
  const handleClose = () => setIsPopoverOpen(false);

  return (
    <div
      data-testid="message-provenance-container"
      style={{
        marginTop: '10px',
        paddingTop: '8px',
        borderTop: '1px solid var(--gold-border, #E5D2AD)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '6px',
        }}
      >
        {/* Source summary & badges */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '6px',
          }}
        >
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--burgundy, #58111A)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <ScrollText size={12} color="var(--burgundy, #58111A)" /> Sources ({sources.length}):
          </span>

          {sources.slice(0, 3).map((src, sIdx) => (
            <SourceBadge
              key={sIdx}
              source={src}
              compact={sources.length > 1}
              isInteractive={true}
              onClick={handleOpen}
            />
          ))}

          {sources.length > 3 && (
            <button
              type="button"
              onClick={handleOpen}
              aria-haspopup="dialog"
              aria-expanded={isPopoverOpen}
              style={{
                background: '#FAF6F0',
                border: '1px dashed #D5C29D',
                borderRadius: '6px',
                padding: '2px 6px',
                fontSize: '0.68rem',
                color: 'var(--burgundy, #58111A)',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              +{sources.length - 3} more
            </button>
          )}

          {isCached && (
            <FreshnessIndicator
              freshnessStatus="cached"
              customText="Cached"
              showLabel={true}
            />
          )}

          {partialFailure && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
                background: '#FFF3E8',
                color: '#A04A00',
                border: '1px solid #F5C69C',
                borderRadius: '999px',
                padding: '2px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
              }}
            >
              <AlertTriangle size={11} color="#A04A00" />
              <span>Partial</span>
            </span>
          )}
        </div>

        {/* Expand / Details button */}
        <button
          type="button"
          onClick={handleOpen}
          data-testid="inspect-provenance-btn"
          aria-haspopup="dialog"
          aria-expanded={isPopoverOpen}
          aria-label="View source verification and freshness details"
          style={{
            background: 'none',
            border: 'none',
            fontSize: '0.70rem',
            color: 'var(--burgundy, #58111A)',
            fontWeight: 700,
            cursor: 'pointer',
            textDecoration: 'underline',
            padding: '2px 4px',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            <span>View Details</span>
            <Info size={11} />
          </span>
        </button>
      </div>

      {/* Accessible popover dialog */}
      <SourceDetailsPopover
        isOpen={isPopoverOpen}
        onClose={handleClose}
        sources={sources}
        toolExecutions={toolExecutions}
        partialFailure={partialFailure}
        isCached={isCached}
      />
    </div>
  );
}
