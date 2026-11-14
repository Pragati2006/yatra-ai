/**
 * frontend/src/components/chat/provenance/SourceDetailsPopover.jsx
 * Accessible details dialog presenting comprehensive, verifiable source metadata.
 * Complies with strict truth-in-data rules, URL sanitization, and timestamp safeguards.
 */

import React, { useEffect, useRef } from 'react';
import { ScrollText, X, AlertTriangle, ExternalLink, XCircle } from 'lucide-react';
import {
  SOURCE_TYPE_LABELS,
  FRESHNESS_LABELS,
  VERIFICATION_LABELS,
  getEffectiveSourceLabel,
  formatTimestamp,
  sanitizeUrl,
} from './provenanceUtils';
import FreshnessIndicator from './FreshnessIndicator';

export default function SourceDetailsPopover({
  isOpen,
  onClose,
  sources = [],
  toolExecutions = [],
  partialFailure = false,
  isCached = false,
}) {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);

  // Close on Escape key and manage focus
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    const prevActiveElement = document.activeElement;
    closeButtonRef.current?.focus();

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (prevActiveElement && typeof prevActiveElement.focus === 'function') {
        prevActiveElement.focus();
      }
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Extract any failed tools for honest disclosure
  const failedTools = Array.isArray(toolExecutions)
    ? toolExecutions.filter((t) => t && t.status && t.status !== 'success' && t.status !== 'skipped')
    : [];

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(20, 10, 10, 0.45)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-details-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border, #E5D2AD)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.18)',
          animation: 'fadeIn 0.15s ease-out',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 18px',
            borderBottom: '1px solid var(--gold-border, #E5D2AD)',
            background: 'linear-gradient(135deg, #FFFDF9 0%, #FAF6F0 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ScrollText size={20} color="var(--burgundy, #58111A)" />
            <div>
              <h3
                id="source-details-title"
                style={{
                  margin: 0,
                  fontSize: '0.95rem',
                  fontFamily: 'var(--font-serif, Cinzel, serif)',
                  fontWeight: 800,
                  color: 'var(--burgundy, #58111A)',
                }}
              >
                Information Provenance & Verification
              </h3>
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted, #6B5C5C)' }}>
                Verifiable metadata for information presented in this turn.
              </p>
            </div>
          </div>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close source details dialog"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted, #6B5C5C)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body content */}
        <div
          style={{
            padding: '14px 18px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {/* Cache or Partial Failure Notice */}
          {isCached && (
            <div
              style={{
                background: '#F0F5FF',
                border: '1px solid #BAD3F7',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '0.75rem',
                color: '#1B4D8A',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span>○</span>
              <span>
                <b>Cached Response:</b> Parts of this answer were served from in-memory cache to ensure rapid response times.
              </span>
            </div>
          )}

          {partialFailure && (
            <div
              style={{
                background: '#FFF8E6',
                border: '1px solid #FAD980',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '0.75rem',
                color: '#8A5D00',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <AlertTriangle size={15} color="#8A5D00" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <b>Partial Service Degradation:</b> One or more external specialist tools could not complete within the timeout window. Successful sibling data is displayed below; unavailable data was strictly omitted rather than estimated.
              </div>
            </div>
          )}

          {/* Validated Sources List */}
          {sources.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
              No external sources or tools were required for this conversational turn.
            </div>
          ) : (
            sources.map((src, idx) => {
              const effectiveLabel = getEffectiveSourceLabel(src);
              const safeUrl = sanitizeUrl(src.source_url);
              const retrievedTime = formatTimestamp(src.retrieval_timestamp);
              const dataTime = formatTimestamp(src.data_timestamp);

              return (
                <div
                  key={idx}
                  data-testid={`provenance-source-item-${idx}`}
                  style={{
                    background: '#FFFFFF',
                    border: '1px solid var(--gold-border, #E5D2AD)',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--burgundy, #58111A)' }}>
                      {src.source_name || effectiveLabel}
                    </div>
                    <FreshnessIndicator
                      freshnessStatus={src.freshness_status}
                      sourceType={src.source_type}
                      customText={effectiveLabel}
                    />
                  </div>

                  {/* Metadata Table Grid */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                      gap: '6px 12px',
                      fontSize: '0.73rem',
                      background: 'var(--cream-bg, #FAF6F0)',
                      borderRadius: '8px',
                      padding: '8px 10px',
                      marginTop: '4px',
                    }}
                  >
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Source Type: </span>
                      <b>{SOURCE_TYPE_LABELS[src.source_type] || src.source_type || 'Unknown'}</b>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Freshness: </span>
                      <b>{FRESHNESS_LABELS[src.freshness_status] || src.freshness_status || 'N/A'}</b>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Verification: </span>
                      <b>{VERIFICATION_LABELS[src.verification_status] || src.verification_status || 'Unverified'}</b>
                    </div>
                    {src.location && (
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Location: </span>
                        <b>{src.location}</b>
                      </div>
                    )}
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Retrieved: </span>
                      <b>{retrievedTime || 'Unavailable'}</b>
                    </div>
                    {dataTime && (
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Observation Time: </span>
                        <b>{dataTime}</b>
                      </div>
                    )}
                  </div>

                  {/* Disclaimers & Notes */}
                  {src.disclaimer && (
                    <div
                      style={{
                        fontSize: '0.72rem',
                        color: '#7D4E00',
                        background: '#FFFBF2',
                        borderLeft: '3px solid #E5A823',
                        padding: '4px 8px',
                        borderRadius: '0 4px 4px 0',
                        marginTop: '2px',
                      }}
                    >
                      <b>Note:</b> {src.disclaimer}
                    </div>
                  )}

                  {src.notes && !src.disclaimer && (
                    <div style={{ fontSize: '0.71rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      {src.notes}
                    </div>
                  )}

                  {/* Verified External Link */}
                  {safeUrl && (
                    <div style={{ marginTop: '2px' }}>
                      <a
                        href={safeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: '0.72rem',
                          color: 'var(--burgundy, #58111A)',
                          textDecoration: 'underline',
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <ExternalLink size={12} />
                        <span>View Official Source Provider</span>
                      </a>
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Failed Capabilities List (Truth in Data) */}
          {failedTools.length > 0 && (
            <div
              style={{
                marginTop: '6px',
                borderTop: '1px dashed #E5D2AD',
                paddingTop: '10px',
              }}
            >
              <div
                style={{
                  fontSize: '0.76rem',
                  fontWeight: 700,
                  color: '#A91B1B',
                  marginBottom: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <XCircle size={14} color="#A91B1B" />
                <span>Unavailable Capabilities During This Turn</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {failedTools.map((ft, fIdx) => (
                  <li key={fIdx}>
                    <b>{ft.tool || 'Specialist service'}</b>: {ft.error || ft.error_message || 'Service timed out or unavailable'}.
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '10px 18px',
            borderTop: '1px solid var(--gold-border, #E5D2AD)',
            background: 'var(--cream-bg, #FAF6F0)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            className="btn btn-secondary"
            style={{
              padding: '6px 14px',
              fontSize: '0.76rem',
              fontWeight: 700,
              borderRadius: '6px',
              cursor: 'pointer',
              border: '1px solid var(--gold-border, #E5D2AD)',
              background: '#FFFFFF',
              color: 'var(--burgundy, #58111A)',
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
