import React, { useState } from 'react';
import { Calendar, ChevronUp, ChevronDown, CalendarDays, ArrowRight, Sparkles, MapPin, Users, Coins, BookmarkCheck } from 'lucide-react';
import { InlineMarkdown } from '../MarkdownContent';
import { upsertItinerary, getAuthToken } from '../../../services/api';

/**
 * Visual Day-by-Day Itinerary Card inside the AI Chat Stream.
 * Features:
 * 1. Destination & trip duration
 * 2. Number of travellers
 * 3. Concise day-wise overview
 * 4. Estimated total budget (when available)
 * 5. Primary action: "View Full Itinerary" button
 * 6. Interactive timeline disclosure
 */
export default function ItineraryCard({
  itinerary,
  message = null,
  chatState = null,
  onNavigateToBooking = null,
  onSwitchToForm = null,
  onRequestSaveAuth = null,
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [saveState, setSaveState] = useState('idle'); // 'idle' | 'saving' | 'saved'

  if (!itinerary) return null;

  const days = itinerary.days || (Array.isArray(itinerary) ? itinerary : []);
  if (!days || days.length === 0) return null;

  const totalDays = days.length;
  const nights = Math.max(1, totalDays - 1);
  const destination = message?.request?.destination || chatState?.current_request?.destination || 'Shri Mata Vaishno Devi Shrine';
  const pax = message?.request?.pax || chatState?.current_request?.pax || 1;
  const origin = message?.request?.origin || chatState?.current_request?.origin || null;
  const startDate = message?.request?.start_date || chatState?.current_request?.start_date || null;
  const grandTotal = message?.plan?.budget_evaluation?.grand_total || message?.budget_evaluation?.grand_total || chatState?.budget_evaluation?.grand_total || null;
  const estTotalStr = grandTotal ? `₹${Math.round(grandTotal).toLocaleString('en-IN')}` : null;

  const handleViewFullItinerary = () => {
    const planOpts = chatState?.pending_options || message?.plan?.options || null;
    const selOpt = chatState?.selected_option || message?.plan?.selected_option || (planOpts && planOpts.length > 0 ? planOpts[0] : null);
    const req = chatState?.current_request || message?.request || {
      destination,
      origin: origin || 'New Delhi',
      pax,
      duration_days: totalDays,
      start_date: startDate || '2026-11-25',
    };
    const htl = chatState?.hotel || message?.plan?.hotel || null;
    const bgt = chatState?.budget_evaluation || message?.plan?.budget_evaluation || null;

    const navPayload = {
      sessionId: chatState?.session_id || message?.session_id,
      planVersion: chatState?.plan_version || message?.plan_version || 1,
      feasible_places: chatState?.feasible_places || message?.feasible_places || [],
      infeasible_places: chatState?.infeasible_places || message?.infeasible_places || [],
      itinerary: days,
      request: req,
      options: planOpts,
      selected_option: selOpt,
      hotel: htl,
      budget_evaluation: bgt,
      planningMode: 'form',
      step: 2, // Dedicated full itinerary view
    };

    if (onNavigateToBooking) {
      onNavigateToBooking(navPayload);
    } else if (onSwitchToForm) {
      onSwitchToForm(navPayload);
    }
  };

  return (
    <div
      data-testid="chat-itinerary-card"
      style={{
        marginTop: '0.85rem',
        background: 'var(--surface-white, #FFFCF9)',
        border: '1.5px solid var(--border-default, #E9DED6)',
        borderRadius: '16px',
        padding: '14px 16px',
        boxShadow: '0 2px 8px rgba(84, 21, 45, 0.04)',
      }}
    >
      {/* 1. Header with Destination & Duration */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '10px',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '0.72rem',
              fontWeight: 800,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--champagne-taupe, #A3826C)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginBottom: '2px',
            }}
          >
            <Sparkles size={13} color="var(--royal-plum, #54152D)" />
            <span>YATRA ITINERARY OVERVIEW</span>
          </div>
          <div
            style={{
              fontFamily: 'var(--font-serif, Cinzel, serif)',
              fontWeight: 800,
              fontSize: '1rem',
              color: 'var(--royal-plum, #54152D)',
            }}
          >
            {destination} · {totalDays} Days / {nights} Nights
          </div>
        </div>

        {estTotalStr && (
          <div
            style={{
              fontSize: '0.82rem',
              fontWeight: 800,
              color: 'var(--royal-plum, #54152D)',
              background: 'var(--soft-plum-surface, #F0E3E7)',
              padding: '3px 10px',
              borderRadius: '8px',
              border: '1px solid var(--border-default, #E9DED6)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Coins size={13} />
            <span>Est. Total: {estTotalStr}</span>
          </div>
        )}
      </div>

      {/* 2. Metadata Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        <span
          style={{
            fontSize: '0.74rem',
            padding: '2px 9px',
            borderRadius: '999px',
            background: 'var(--secondary-bg, #F2EAE4)',
            color: 'var(--royal-plum, #54152D)',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <Users size={12} />
          <span>{pax} {pax === 1 ? 'Traveler' : 'Travelers'}</span>
        </span>

        {origin && (
          <span
            style={{
              fontSize: '0.74rem',
              padding: '2px 9px',
              borderRadius: '999px',
              background: 'var(--secondary-bg, #F2EAE4)',
              color: 'var(--royal-plum, #54152D)',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <MapPin size={12} />
            <span>From: {origin}</span>
          </span>
        )}

        {startDate && (
          <span
            style={{
              fontSize: '0.74rem',
              padding: '2px 9px',
              borderRadius: '999px',
              background: 'var(--secondary-bg, #F2EAE4)',
              color: 'var(--royal-plum, #54152D)',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Calendar size={12} />
            <span>{startDate}</span>
          </span>
        )}
      </div>

      {/* 3. Concise Day-Wise Overview */}
      <div
        style={{
          background: 'var(--secondary-bg, #F2EAE4)',
          border: '1px solid var(--border-default, #E9DED6)',
          borderRadius: '10px',
          padding: '10px 12px',
          marginBottom: '12px',
        }}
      >
        <div
          style={{
            fontSize: '0.72rem',
            fontWeight: 800,
            color: 'var(--royal-plum, #54152D)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
          }}
        >
          <CalendarDays size={13} color="var(--royal-plum, #54152D)" />
          <span>DAY-WISE OVERVIEW</span>
        </div>

        <ul style={{ margin: 0, paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {days.slice(0, 6).map((day, idx) => {
            const dayNum = day.day_number || day.day || idx + 1;
            const title = day.title || day.theme || (day.activities?.[0]?.activity || day.activities?.[0] || `Day ${dayNum} Program`);
            return (
              <li key={idx} style={{ fontSize: '0.8rem', lineHeight: 1.45, color: 'var(--text-primary, #30272A)' }}>
                <strong style={{ color: 'var(--royal-plum, #54152D)' }}>Day {dayNum}: </strong>
                <span>{typeof title === 'string' ? title : `Day ${dayNum} Yatra activities`}</span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* 4. Primary CTA: View Full Itinerary */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
        <button
          type="button"
          data-testid="view-full-itinerary-btn"
          onClick={handleViewFullItinerary}
          style={{
            flex: '1 1 180px',
            minHeight: '38px',
            padding: '0.5rem 1rem',
            fontSize: '0.82rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            background: 'var(--royal-plum, #54152D)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '10px',
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(84, 21, 45, 0.15)',
          }}
        >
          <CalendarDays size={15} />
          <span>View Full Itinerary</span>
          <ArrowRight size={14} />
        </button>

        <button
          type="button"
          data-testid="save-itinerary-card-btn"
          disabled={saveState === 'saving'}
          onClick={async () => {
            const sid = chatState?.session_id || message?.session_id || 'chat';
            const savePayload = {
              title: `${destination} (${totalDays} Days)`,
              sourceKey: `chat-${sid}-${totalDays}-${startDate || 'flex'}`,
              itinerary: {
                title: `${destination} (${totalDays} Days)`,
                destination,
                start_date: startDate || undefined,
                duration_days: totalDays,
                travellers_count: pax,
                request: chatState?.current_request || message?.request || undefined,
                days,
              },
            };
            if (!getAuthToken()) {
              onRequestSaveAuth?.(savePayload);
              return;
            }
            setSaveState('saving');
            try {
              await upsertItinerary(savePayload);
              setSaveState('saved');
            } catch (err) {
              setSaveState('idle');
              if (err?.response?.status === 401) {
                onRequestSaveAuth?.(savePayload);
              }
            }
          }}
          style={{
            minHeight: '38px',
            padding: '0.5rem 0.85rem',
            fontSize: '0.78rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            background: saveState === 'saved' ? '#D1FAE5' : '#FFFCF9',
            border: '1px solid #E9DED6',
            borderRadius: '10px',
            color: saveState === 'saved' ? '#065F46' : '#54152D',
            cursor: 'pointer',
          }}
        >
          <BookmarkCheck size={14} />
          <span>{saveState === 'saved' ? 'Saved' : saveState === 'saving' ? 'Saving...' : 'Save Itinerary'}</span>
        </button>

        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          style={{
            minHeight: '38px',
            padding: '0.5rem 0.85rem',
            fontSize: '0.78rem',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            background: 'var(--surface-white, #FFFCF9)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '10px',
            color: 'var(--royal-plum, #54152D)',
            cursor: 'pointer',
          }}
        >
          <span>{isExpanded ? 'Collapse Timeline' : 'Preview Schedule'}</span>
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* 5. Expanded Day-by-Day Timeline Schedule */}
      {isExpanded && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {days.map((day, idx) => {
            const dayNum = day.day_number || day.day || idx + 1;
            const title = day.title || day.theme || `Day ${dayNum}`;
            const activities = day.activities || day.schedule || [];

            return (
              <div
                key={idx}
                style={{
                  background: 'var(--surface-white, #FFFCF9)',
                  border: '1px solid var(--border-default, #E9DED6)',
                  borderRadius: '8px',
                  padding: '9px 12px',
                }}
              >
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    color: 'var(--royal-plum, #54152D)',
                    marginBottom: '5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span
                    style={{
                      background: 'var(--royal-plum, #54152D)',
                      color: '#FFF',
                      borderRadius: '4px',
                      padding: '1px 6px',
                      fontSize: '0.68rem',
                    }}
                  >
                    Day {dayNum}
                  </span>
                  <span>{title}</span>
                </div>

                {activities.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.78rem', color: 'var(--text-primary, #30272A)', lineHeight: 1.48 }}>
                    {activities.map((act, aIdx) => {
                      const timeStr = typeof act === 'object' ? (act.time || act.slot || '') : '';
                      const actText = typeof act === 'object' ? (act.activity || act.description || JSON.stringify(act)) : act;
                      return (
                        <li key={aIdx} style={{ marginBottom: '2px' }}>
                          {timeStr && <b style={{ color: 'var(--champagne-taupe, #A3826C)' }}>{timeStr}: </b>}
                          <span>{actText}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary, #796D69)' }}>
                    {day.description || 'Devotional trek, darshan, and rest schedule.'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
