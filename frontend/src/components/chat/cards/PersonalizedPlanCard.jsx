import React, { useState } from 'react';
import {
  Sparkles,
  Users,
  Calendar,
  Briefcase,
  Footprints,
  CalendarDays,
  Train,
  Search,
  Landmark,
  ArrowRight,
  Coins,
  MapPin,
  Clock,
  CheckCircle2,
  Info,
  BookmarkCheck,
} from 'lucide-react';
import { InlineMarkdown } from '../MarkdownContent';
import { upsertItinerary, getAuthToken } from '../../../services/api';

/**
 * Minimal, high-impact Personalized Plan Card for AI Chat stream.
 * Displays:
 * 1. Destination & trip duration
 * 2. Number of travellers
 * 3. Origin & travel dates (when available)
 * 4. Concise day-wise overview
 * 5. Estimated total budget
 * 6. Primary Action: "View Full Itinerary" (opens dedicated full view with all details preserved)
 * 7. Secondary Action: "Proceed with Booking"
 */
export default function PersonalizedPlanCard({
  recommendation,
  message,
  chatState,
  onSend,
  onNavigateToBooking,
  onSwitchToForm,
  onExplorePlace,
  onRequestSaveAuth = null,
}) {
  const [saveState, setSaveState] = useState('idle');
  if (!recommendation) return null;

  const prof = recommendation.profile || {};
  const destination = recommendation.destination || prof.destination || message?.request?.destination || chatState?.current_request?.destination || 'Shri Mata Vaishno Devi Shrine';
  const pax = prof.pax || message?.request?.pax || chatState?.current_request?.pax || 1;
  const groupType = (prof.group_type || message?.request?.group_type || 'Family');
  const duration = prof.duration_days || message?.request?.duration_days || chatState?.current_request?.duration_days || 4;
  const nights = Math.max(1, duration - 1);
  const pace = prof.travel_style || message?.request?.travel_style || 'Comfortable';
  const origin = prof.origin || message?.request?.origin || chatState?.current_request?.origin || null;
  const startDate = prof.start_date || message?.request?.start_date || chatState?.current_request?.start_date || null;
  const endDate = prof.end_date || message?.request?.end_date || chatState?.current_request?.end_date || null;

  const grandTotal = message?.plan?.budget_evaluation?.grand_total || message?.budget_evaluation?.grand_total || recommendation?.estimated_total_budget || null;
  const estTotalStr = grandTotal ? `₹${Math.round(grandTotal).toLocaleString('en-IN')}` : null;

  const oneLineDesc = recommendation.tagline || recommendation.summary || (
    `A balanced devotional yatra with dedicated darshan windows, scenic regional excursions, and comfortable Katra stays.`
  );

  // Extract day-wise overview
  const rawItin = message?.itinerary || chatState?.current_itinerary || message?.plan?.itinerary || recommendation?.itinerary || null;
  const itinDays = rawItin?.days || (Array.isArray(rawItin) ? rawItin : []);

  // Generate concise day-wise highlights
  const dayHighlights = [];
  if (itinDays && itinDays.length > 0) {
    itinDays.forEach((d, idx) => {
      const dayNum = d.day_number || d.day || idx + 1;
      const title = d.title || d.theme || (d.activities?.[0]?.activity || d.activities?.[0] || `Day ${dayNum} Program`);
      dayHighlights.push({ dayNum, title: typeof title === 'string' ? title : `Day ${dayNum} Yatra activities` });
    });
  } else {
    // Elegant fallback day highlights based on duration
    const defaultThemes = [
      'Arrival at Katra, Hotel Check-in & RFID Yatra Registration',
      'Sacred Trek to Bhawan, Mata Vaishno Devi Darshan & Bhairavnath Temple',
      'Scenic Excursion to Patnitop / Shiv Khori & Rest Period',
      'Morning Aarti, Local Katra Souvenir Shopping & Onward Journey',
      'Kashmir Foothills or Mansar Lake Excursion',
      'Extended Regional Pilgrimage & Leisure',
      'Final Blessings & Departure',
    ];
    for (let i = 0; i < Math.min(duration, 7); i++) {
      dayHighlights.push({ dayNum: i + 1, title: defaultThemes[i] || `Day ${i + 1} Itinerary Schedule` });
    }
  }

  const places = recommendation.suggested_places || [];

  const buildNavPayload = () => {
    const planOpts = chatState?.pending_options || message?.plan?.options || null;
    const selOpt = chatState?.selected_option || message?.plan?.selected_option || (planOpts && planOpts.length > 0 ? planOpts[0] : null);
    const req = chatState?.current_request || message?.request || {
      destination,
      origin: origin || 'New Delhi',
      pax,
      duration_days: duration,
      start_date: startDate || '2026-11-25',
    };
    const itin = chatState?.current_itinerary || message?.itinerary || message?.plan?.itinerary || null;
    const htl = chatState?.hotel || message?.plan?.hotel || null;
    const bgt = chatState?.budget_evaluation || message?.plan?.budget_evaluation || null;

    return {
      sessionId: chatState?.session_id || message?.session_id,
      planVersion: chatState?.plan_version || message?.plan_version || 1,
      feasible_places: chatState?.feasible_places?.length > 0 ? chatState.feasible_places : (message?.feasible_places || []),
      infeasible_places: chatState?.infeasible_places?.length > 0 ? chatState.infeasible_places : (message?.infeasible_places || []),
      itinerary: itin,
      request: req,
      sightseeing_choice: req?.sightseeing_choice || null,
      options: planOpts,
      selected_option: selOpt,
      hotel: htl,
      budget_evaluation: bgt,
      planningMode: 'form',
      step: 2, // Opens dedicated full itinerary view (RecommendedYatra)
    };
  };

  const handleViewFullItinerary = () => {
    const navPayload = buildNavPayload();
    if (onNavigateToBooking) {
      onNavigateToBooking(navPayload);
    } else if (onSwitchToForm) {
      onSwitchToForm(navPayload);
    } else if (onSend) {
      onSend('Show full itinerary');
    }
  };

  const handleProceedWithBooking = () => {
    const navPayload = buildNavPayload();
    if (onNavigateToBooking) {
      onNavigateToBooking(navPayload);
    } else if (onSwitchToForm) {
      onSwitchToForm(navPayload);
    } else if (onSend) {
      onSend('Find travel options to Katra');
    }
  };

  return (
    <div
      data-testid="compact-personalized-plan-card"
      className="compact-plan-card"
      style={{
        marginTop: '0.85rem',
        width: '100%',
        boxSizing: 'border-box',
        background: 'var(--surface-white, #FFFCF9)',
        border: '1.5px solid var(--border-default, #E9DED6)',
        borderRadius: '16px',
        padding: '16px 18px',
        boxShadow: '0 3px 12px rgba(84, 21, 45, 0.05)',
        overflow: 'hidden',
      }}
    >
      {/* 1. Header: Title, Destination & Trip Duration */}
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
              fontFamily: 'var(--font-sans)',
              fontWeight: 800,
              fontSize: '0.74rem',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--champagne-taupe, #A3826C)',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              marginBottom: '3px',
            }}
          >
            <Sparkles size={13} color="var(--royal-plum, #54152D)" />
            <span>PERSONALIZED YATRA ITINERARY</span>
          </div>
          <div
            style={{
              fontFamily: 'var(--font-serif, Cinzel, serif)',
              fontWeight: 800,
              fontSize: '1.05rem',
              color: 'var(--royal-plum, #54152D)',
              letterSpacing: '0.01em',
            }}
          >
            {destination} · {duration} Days / {nights} Nights
          </div>
        </div>

        {/* Estimated Total Budget */}
        {estTotalStr && (
          <div
            style={{
              fontSize: '0.84rem',
              fontWeight: 800,
              color: 'var(--royal-plum, #54152D)',
              background: 'var(--soft-plum-surface, #F0E3E7)',
              padding: '4px 11px',
              borderRadius: '8px',
              border: '1px solid var(--border-default, #E9DED6)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Coins size={14} color="var(--royal-plum, #54152D)" />
            <span>Est. Total: {estTotalStr}</span>
          </div>
        )}
      </div>

      {/* 2. Metadata Badges: Pax, Origin, Dates, Style */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
        <span
          className="pill pill-gold"
          style={{
            fontSize: '0.74rem',
            padding: '3px 10px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--secondary-bg, #F2EAE4)',
            color: 'var(--royal-plum, #54152D)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '999px',
            fontWeight: 700,
          }}
        >
          <Users size={12} />
          <span>{pax} {pax === 1 ? 'Traveler' : 'Travelers'} ({groupType})</span>
        </span>

        {origin && (
          <span
            style={{
              fontSize: '0.74rem',
              padding: '3px 10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--secondary-bg, #F2EAE4)',
              color: 'var(--royal-plum, #54152D)',
              border: '1px solid var(--border-default, #E9DED6)',
              borderRadius: '999px',
              fontWeight: 600,
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
              padding: '3px 10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--secondary-bg, #F2EAE4)',
              color: 'var(--royal-plum, #54152D)',
              border: '1px solid var(--border-default, #E9DED6)',
              borderRadius: '999px',
              fontWeight: 600,
            }}
          >
            <Calendar size={12} />
            <span>{startDate}{endDate ? ` to ${endDate}` : ''}</span>
          </span>
        )}

        <span
          style={{
            fontSize: '0.74rem',
            padding: '3px 10px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--secondary-bg, #F2EAE4)',
            color: 'var(--text-secondary, #796D69)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '999px',
            fontWeight: 600,
          }}
        >
          <Footprints size={12} />
          <span>{pace} Pace</span>
        </span>
      </div>

      {/* 3. Narrative Summary */}
      <div
        style={{
          fontSize: '0.86rem',
          color: 'var(--text-primary, #30272A)',
          lineHeight: 1.55,
          marginBottom: '12px',
        }}
      >
        <InlineMarkdown text={oneLineDesc} />
      </div>

      {/* 4. Concise Day-Wise Overview */}
      <div
        style={{
          background: 'var(--secondary-bg, #F2EAE4)',
          border: '1px solid var(--border-default, #E9DED6)',
          borderRadius: '10px',
          padding: '10px 14px',
          marginBottom: '14px',
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-sans)',
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
          {dayHighlights.map((dh) => (
            <li
              key={dh.dayNum}
              style={{
                fontSize: '0.8rem',
                lineHeight: 1.45,
                color: 'var(--text-primary, #30272A)',
              }}
            >
              <strong style={{ color: 'var(--royal-plum, #54152D)' }}>Day {dh.dayNum}: </strong>
              <span>{dh.title}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* 5. Primary Actions: View Full Itinerary & Proceed with Booking */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
        <button
          type="button"
          data-testid="view-full-itinerary-btn"
          onClick={handleViewFullItinerary}
          className="btn btn-primary"
          style={{
            flex: '1 1 180px',
            minHeight: '40px',
            padding: '0.55rem 1rem',
            fontSize: '0.84rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            background: 'var(--royal-plum, #54152D)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '10px',
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(84, 21, 45, 0.15)',
            transition: 'all 0.15s ease',
          }}
        >
          <CalendarDays size={15} />
          <span>View Full Itinerary</span>
          <ArrowRight size={14} />
        </button>

        <button
          type="button"
          data-testid="proceed-with-booking-btn"
          onClick={handleProceedWithBooking}
          className="btn btn-secondary"
          style={{
            flex: '1 1 160px',
            minHeight: '40px',
            padding: '0.55rem 1rem',
            fontSize: '0.84rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            background: 'var(--surface-white, #FFFCF9)',
            color: 'var(--royal-plum, #54152D)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '10px',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <Train size={14} />
          <span>Proceed with Booking</span>
        </button>

        <button
          type="button"
          data-testid="save-personalized-plan-btn"
          disabled={saveState === 'saving'}
          onClick={async () => {
            const sid = chatState?.session_id || message?.session_id || 'plan';
            const rawDays = message?.itinerary?.days || message?.itinerary || recommendation?.itinerary?.days || [];
            const savePayload = {
              title: `${destination} (${duration} Days)`,
              sourceKey: `plan-${sid}-${duration}-${startDate || 'flex'}`,
              itinerary: {
                title: `${destination} (${duration} Days)`,
                destination,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
                duration_days: duration,
                travellers_count: pax,
                request: chatState?.current_request || message?.request || undefined,
                days: Array.isArray(rawDays) && rawDays.length > 0 ? rawDays : dayHighlights.map((dh) => ({ day_number: dh.dayNum, title: dh.title, activities: [dh.title] })),
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
          className="btn btn-secondary"
          style={{
            flex: '0 1 auto',
            minHeight: '40px',
            padding: '0.55rem 0.9rem',
            fontSize: '0.82rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            background: saveState === 'saved' ? '#D1FAE5' : 'var(--surface-white, #FFFCF9)',
            color: saveState === 'saved' ? '#065F46' : 'var(--royal-plum, #54152D)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '10px',
            cursor: 'pointer',
          }}
        >
          <BookmarkCheck size={14} />
          <span>{saveState === 'saved' ? 'Saved' : saveState === 'saving' ? 'Saving...' : 'Save Itinerary'}</span>
        </button>
      </div>

      {/* 6. Progressive Disclosure Details: Strategy & Places */}
      <details
        data-testid="plan-card-progressive-details"
        style={{
          marginTop: '12px',
          background: 'var(--surface-white, #FFFCF9)',
          border: '1px solid var(--border-default, #E9DED6)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.78rem',
        }}
      >
        <summary
          style={{
            cursor: 'pointer',
            fontWeight: 700,
            color: 'var(--royal-plum, #54152D)',
            userSelect: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Search size={13} />
            <span>Strategy Details &amp; Suggested Sites ({places.length})</span>
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary, #796D69)' }}>Details ▼</span>
        </summary>

        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {recommendation.reasoning && (
            <div
              style={{
                background: 'var(--secondary-bg, #F2EAE4)',
                borderLeft: '3px solid var(--champagne-taupe, #A3826C)',
                padding: '6px 10px',
                borderRadius: '4px',
                lineHeight: 1.45,
                color: 'var(--text-primary, #30272A)',
              }}
            >
              <b>Why this plan: </b>
              <InlineMarkdown text={recommendation.reasoning} />
            </div>
          )}

          {places.length > 0 && (
            <div>
              <div style={{ fontWeight: 700, color: 'var(--royal-plum, #54152D)', marginBottom: '5px' }}>
                Suggested Destinations:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {places.slice(0, 5).map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onExplorePlace ? onExplorePlace(p.name) : onSend(`Tell me about ${p.name}`)}
                    className="btn btn-secondary"
                    style={{
                      padding: '3px 8px',
                      fontSize: '0.73rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'var(--secondary-bg, #F2EAE4)',
                      border: '1px solid var(--border-default, #E9DED6)',
                      borderRadius: '6px',
                      color: 'var(--royal-plum, #54152D)',
                      cursor: 'pointer',
                    }}
                  >
                    <Landmark size={11} />
                    <span>{p.name}</span>
                    <ArrowRight size={10} />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
