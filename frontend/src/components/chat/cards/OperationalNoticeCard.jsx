import React from 'react';
import { Bell, AlertTriangle, AlertCircle, Phone, MapPin, Landmark, Lightbulb } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';

/**
 * OperationalNoticeCard: Renders curated, human-verified operational notices,
 * route restrictions, and traffic advisories for Vaishno Devi tracks & NH-44.
 *
 * Enforces truth-in-data:
 * - Visually distinguishes CRITICAL / HIGH / WARNING / ADVISORY severities.
 * - Explicitly highlights REQUIRES_REVERIFICATION when validity horizons lapse.
 * - Honestly states upstream unconfirmed status when NO_ACTIVE_NOTICES are present.
 * - Clearly displays a distinct amber/yellow warning when SOURCE_UNAVAILABLE occurs.
 */
export default function OperationalNoticeCard({ noticesData }) {
  if (!noticesData) return null;

  // Handle array of notices, full envelope dictionary, or defensive fallback
  let notices = [];
  let aggregateStatus = 'HAS_NOTICES';
  let advisoryText = null;

  if (Array.isArray(noticesData)) {
    notices = noticesData;
    aggregateStatus = notices.length > 0 ? 'HAS_NOTICES' : 'NO_ACTIVE_NOTICES';
  } else if (typeof noticesData === 'object') {
    if (Array.isArray(noticesData.notices)) {
      notices = noticesData.notices;
    } else if (noticesData.notice_id) {
      notices = [noticesData];
    } else {
      notices = [];
    }

    if (noticesData.aggregate_status) {
      aggregateStatus = String(noticesData.aggregate_status).toUpperCase();
    } else if (notices.length > 0) {
      aggregateStatus = 'HAS_NOTICES';
    } else {
      aggregateStatus = 'NO_ACTIVE_NOTICES';
    }

    advisoryText = noticesData.advisory || null;
  } else {
    return null;
  }

  const isUnavailable = aggregateStatus === 'SOURCE_UNAVAILABLE';
  const hasNotices = !isUnavailable && aggregateStatus === 'HAS_NOTICES' && notices.length > 0;
  const isNoActiveNotices = !isUnavailable && (aggregateStatus === 'NO_ACTIVE_NOTICES' || notices.length === 0);

  const getSeverityStyle = (severity) => {
    const sev = (severity || 'ADVISORY').toUpperCase();
    if (sev === 'CRITICAL' || sev === 'HIGH') {
      return {
        bg: '#FFF5F5',
        border: '#FEB2B2',
        accent: '#E53E3E',
        badgeBg: '#FED7D7',
        badgeText: '#9B2C2C',
        icon: <AlertCircle size={14} color="#E53E3E" style={{ display: 'inline', verticalAlign: '-2px', marginRight: '5px' }} />,
      };
    }
    if (sev === 'WARNING') {
      return {
        bg: '#FFFBEB',
        border: '#FDE68A',
        accent: '#D97706',
        badgeBg: '#FEF3C7',
        badgeText: '#92400E',
        icon: <AlertTriangle size={14} color="#D97706" style={{ display: 'inline', verticalAlign: '-2px', marginRight: '5px' }} />,
      };
    }
    return {
      bg: '#F0F7FF',
      border: '#BAE6FD',
      accent: '#0284C7',
      badgeBg: '#E0F2FE',
      badgeText: '#0369A1',
      icon: <Bell size={14} color="#0284C7" style={{ display: 'inline', verticalAlign: '-2px', marginRight: '5px' }} />,
    };
  };

  const getPillConfig = () => {
    if (isUnavailable) {
      return {
        text: 'Registry Unavailable',
        bg: '#FEF3C7',
        color: '#92400E',
      };
    }
    if (hasNotices) {
      return {
        text: `${notices.length} Active Notice${notices.length > 1 ? 's' : ''}`,
        bg: '#FEF3C7',
        color: '#92400E',
      };
    }
    return {
      text: 'No Active Restrictions',
      bg: '#F3F4F6',
      color: '#4B5563',
    };
  };

  const pill = getPillConfig();

  return (
    <div
      data-testid="chat-operational-notices-card"
      style={{
        marginTop: '0.65rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '12px 14px',
        boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
      }}
    >
      {/* Header Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Bell size={16} color="var(--burgundy, #58111A)" />
          <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--burgundy, #58111A)' }}>
            Official Operational Notices & Advisories
          </span>
        </div>
        <span
          className="pill"
          style={{
            fontSize: '0.68rem',
            padding: '2px 7px',
            background: pill.bg,
            color: pill.color,
            fontWeight: 600,
            borderRadius: '999px',
          }}
        >
          {pill.text}
        </span>
      </div>

      {/* State 1: SOURCE_UNAVAILABLE Warning Banner (F-03 Remediation) */}
      {isUnavailable && (
        <div
          data-testid="notice-unavailable-state"
          style={{
            background: '#FFFBEB',
            border: '1px solid #FDE68A',
            borderRadius: '8px',
            padding: '10px 12px',
            fontSize: '0.78rem',
            color: '#92400E',
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 700, color: '#B45309', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={15} color="#B45309" /> Operational Notice Registry Unavailable
          </div>
          <div>
            Operational notice information is currently unavailable. The curated registry could not be accessed. This does not mean that routes are clear or that no disruptions exist. Please verify current conditions directly with the relevant authorities before travelling.
          </div>
          <div style={{ marginTop: '6px', fontSize: '0.72rem', color: '#78350F', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Phone size={12} color="#78350F" />
            <span>For immediate assistance, contact <b>SMVDSB Call Centre (1800-180-7212)</b> or <b>National Emergency (112)</b>.</span>
          </div>
        </div>
      )}

      {/* State 2: NO_ACTIVE_NOTICES Informational State */}
      {isNoActiveNotices && (
        <div
          data-testid="notice-empty-state"
          style={{
            background: '#F9FAFB',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
            padding: '10px 12px',
            fontSize: '0.78rem',
            color: '#4B5563',
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 600, color: '#1F2937', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={14} color="#1F2937" />
            <span>No Active Track Closures or Disruption Circulars Recorded</span>
          </div>
          <div>
            The curated registry currently contains no active matching suspension or closure notices for Vaishno Devi tracks or connecting corridors as of today.
          </div>
          <div style={{ marginTop: '5px', fontSize: '0.72rem', color: '#6B7280', fontStyle: 'italic' }}>
            Explicit Note: This informational status does not confirm live route clearance or uninterrupted Yatra operations. Ground conditions may change rapidly. Confirm passage directly with Shrine Board or Traffic Police authorities.
          </div>
        </div>
      )}

      {/* State 3: HAS_NOTICES Active Notice List */}
      {hasNotices && (
        <div data-testid="notice-active-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {notices.map((n) => {
            const style = getSeverityStyle(n.severity);
            const isReverification = n.notice_lifecycle_status === 'REQUIRES_REVERIFICATION';
            const isWithdrawn = n.notice_lifecycle_status === 'WITHDRAWN';
            const isSuperseded = n.notice_lifecycle_status === 'SUPERSEDED';

            return (
              <div
                key={n.notice_id}
                data-testid={`notice-item-${n.notice_id}`}
                style={{
                  background: style.bg,
                  border: `1px solid ${style.border}`,
                  borderRadius: '8px',
                  padding: '10px 12px',
                  opacity: (isWithdrawn || isSuperseded) ? 0.65 : 1,
                }}
              >
                {/* Title & Severity Badge */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#1F2937', lineHeight: 1.3, display: 'flex', alignItems: 'center' }}>
                    {style.icon}
                    <span>{n.notice_title}</span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.64rem',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: style.badgeBg,
                      color: style.badgeText,
                      flexShrink: 0,
                    }}
                  >
                    {n.severity || 'ADVISORY'}
                  </span>
                </div>

                {/* Reverification Alert Banner */}
                {isReverification && (
                  <div
                    data-testid={`reverification-banner-${n.notice_id}`}
                    style={{
                      marginTop: '4px',
                      marginBottom: '6px',
                      background: '#FEF2F2',
                      border: '1px solid #FCA5A5',
                      borderRadius: '6px',
                      padding: '4px 8px',
                      fontSize: '0.72rem',
                      color: '#991B1B',
                      fontWeight: 600,
                      lineHeight: 1.35,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <AlertTriangle size={12} color="#991B1B" style={{ flexShrink: 0 }} />
                    <span>Validity horizon lapsed without official renewal. Ground passage unconfirmed; verify directly before travel.</span>
                  </div>
                )}

                {/* Affected Location & Route Corridor */}
                <div style={{ fontSize: '0.74rem', color: '#4B5563', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <MapPin size={12} style={{ flexShrink: 0 }} />
                  <span><b>Affected:</b> {n.affected_location}{n.affected_route ? ` (${n.affected_route})` : ''}</span>
                </div>

                {/* Notice text or summary */}
                <div style={{ fontSize: '0.76rem', color: '#374151', lineHeight: 1.4, marginBottom: '6px' }}>
                  {n.translated_summary || n.notice_text}
                </div>

                {/* Metadata & Authority attribution */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    fontSize: '0.68rem',
                    color: '#6B7280',
                    borderTop: '1px solid rgba(0,0,0,0.06)',
                    paddingTop: '5px',
                    gap: '4px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Landmark size={12} style={{ flexShrink: 0 }} />
                    <span><b>Issued by:</b> {n.issuing_authority}</span>
                  </div>
                  {n.source_url && (
                    <a
                      href={n.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: style.accent, textDecoration: 'none', fontWeight: 600 }}
                    >
                      Official Source ↗
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Advisory footnote */}
      {advisoryText && hasNotices && (
        <div style={{ marginTop: '8px', fontSize: '0.72rem', color: '#6B7280', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Lightbulb size={12} style={{ flexShrink: 0 }} />
          <span>{advisoryText}</span>
        </div>
      )}

      {/* Provenance footer */}
      <div
        style={{
          marginTop: '8px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(229, 210, 173, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.68rem',
          color: 'var(--text-muted, #6B5C5C)',
        }}
      >
        <FreshnessIndicator freshness={isUnavailable ? 'unavailable' : 'not_applicable'} sourceType="curated_data" />
        <span>{isUnavailable ? 'Registry Offline' : 'Curated Official Registry'}</span>
      </div>
    </div>
  );
}
