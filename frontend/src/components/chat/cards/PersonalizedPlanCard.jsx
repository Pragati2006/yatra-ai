import React from 'react';
import { Sparkles, Users, Calendar, Briefcase, Footprints, CalendarDays, Train, Search, Landmark, ArrowRight, Coins, Info } from 'lucide-react';

/**
 * Reusable Personalized Plan Card for AI Chat stream.
 * Displays trip overview badges, cost estimation, action triggers,
 * and collapsible detailed strategy.
 */
export default function PersonalizedPlanCard({
  recommendation,
  message,
  chatState,
  onSend,
  onNavigateToBooking,
  onSwitchToForm,
  onExplorePlace,
}) {
  if (!recommendation) return null;

  const prof = recommendation.profile || {};
  const pax = prof.pax || message?.request?.pax || 1;
  const groupType = (prof.group_type || message?.request?.group_type || 'Family').toUpperCase();
  const duration = prof.duration_days || message?.request?.duration_days || 4;
  const pace = (prof.travel_style || message?.request?.travel_style || 'Comfortable').toUpperCase();
  const budgetPref = (prof.budget_preference || message?.request?.budget_preference || 'Comfortable').toUpperCase();

  const grandTotal = message?.plan?.budget_evaluation?.grand_total || message?.budget_evaluation?.grand_total || null;
  const estTotalStr = grandTotal ? `₹${Math.round(grandTotal).toLocaleString('en-IN')}` : null;

  const oneLineDesc = recommendation.tagline || recommendation.summary || (
    `A ${budgetPref.toLowerCase()} devotional trip with dedicated time for Darshan and sightseeing.`
  );

  const bullets = recommendation.approach_bullets || [
    'Dedicated time for trek, darshan, and Bhairavnath Temple.',
    'Explore scenic places around Katra and foothills.',
    'Flexible rest buffers with hill-station excursions.',
  ];
  const places = recommendation.suggested_places || [];

  const handleProceedWithBooking = () => {
    const planOpts = chatState?.pending_options || message?.plan?.options || null;
    const selOpt = chatState?.selected_option || message?.plan?.selected_option || (planOpts && planOpts.length > 0 ? planOpts[0] : null);
    const req = chatState?.current_request || message?.request || null;
    const itin = chatState?.current_itinerary || message?.itinerary || message?.plan?.itinerary || null;
    const htl = chatState?.hotel || message?.plan?.hotel || null;
    const bgt = chatState?.budget_evaluation || message?.plan?.budget_evaluation || null;

    const navPayload = {
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
      step: (planOpts && planOpts.length > 0) ? 2 : 1,
    };

    if (onSwitchToForm) {
      onSwitchToForm(navPayload);
    } else if (onNavigateToBooking) {
      onNavigateToBooking(navPayload);
    } else {
      onSend('Find travel options to Katra');
    }
  };

  return (
    <div
      data-testid="compact-personalized-plan-card"
      className="compact-plan-card"
      style={{
        marginTop: '0.75rem',
        width: '100%',
        boxSizing: 'border-box',
        background: '#FFFFFF',
        border: '1.5px solid var(--gold-border, #E5D2AD)',
        borderRadius: '14px',
        padding: '14px 16px',
        boxShadow: '0 3px 12px rgba(88, 17, 26, 0.05)',
        overflow: 'hidden',
      }}
    >
      {/* Header & Title */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '10px',
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-serif, Cinzel, serif)',
            fontWeight: 800,
            fontSize: '0.9rem',
            letterSpacing: '0.03em',
            color: 'var(--burgundy, #58111A)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Sparkles size={14} color="var(--burgundy)" /> YOUR PERSONALIZED YATRA PLAN
        </div>
        {estTotalStr && (
          <div
            style={{
              fontSize: '0.8rem',
              fontWeight: 700,
              color: '#8A5D00',
              background: '#FFF8E7',
              padding: '3px 10px',
              borderRadius: '6px',
              border: '1px solid #E5D2AD',
            }}
          >
            Est. Total: {estTotalStr}
          </div>
        )}
      </div>

      {/* Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        <span className="pill pill-gold" style={{ fontSize: '0.74rem', padding: '3px 9px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <Users size={12} /> {pax} {pax === 1 ? 'Pilgrim' : 'Pilgrims'}
        </span>
        <span className="pill pill-gold" style={{ fontSize: '0.74rem', padding: '3px 9px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <Calendar size={12} /> {duration} Days
        </span>
        <span className="pill pill-gold" style={{ fontSize: '0.74rem', padding: '3px 9px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <Briefcase size={12} /> {groupType}
        </span>
        <span className="pill pill-gold" style={{ fontSize: '0.74rem', padding: '3px 9px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
          <Footprints size={12} /> {pace}
        </span>
      </div>

      {/* One-line trip description */}
      <div
        style={{
          fontSize: '0.85rem',
          color: 'var(--text-dark, #2A2020)',
          lineHeight: 1.5,
          marginBottom: '12px',
        }}
      >
        {oneLineDesc}
      </div>

      {/* Two Primary Action Buttons */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
        <button
          type="button"
          onClick={() => onSend('Show full itinerary')}
          className="btn btn-primary"
          style={{
            flex: '1 1 150px',
            minHeight: '38px',
            padding: '0.5rem 0.9rem',
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}
        >
          <CalendarDays size={14} />
          <span>Explore Itinerary</span>
        </button>
        <button
          type="button"
          data-testid="proceed-with-booking-btn"
          onClick={handleProceedWithBooking}
          className="btn btn-gold"
          style={{
            flex: '1 1 150px',
            minHeight: '38px',
            padding: '0.5rem 0.9rem',
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
          }}
        >
          <Train size={14} />
          <span>Proceed with Booking</span>
        </button>
      </div>

      {/* Progressive Disclosure Details */}
      <details
        data-testid="plan-card-progressive-details"
        style={{
          marginTop: '12px',
          background: 'var(--bg-subtle, #F8F4EC)',
          border: '1px solid #EAE0D0',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.78rem',
        }}
      >
        <summary
          style={{
            cursor: 'pointer',
            fontWeight: 700,
            color: 'var(--burgundy, #58111A)',
            fontFamily: 'var(--font-serif, Cinzel, serif)',
            userSelect: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Search size={13} />
            <span>View Detailed Strategy & Recommendations</span>
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted, #6B5C5C)' }}>Details ▼</span>
        </summary>

        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--burgundy, #58111A)', marginBottom: '4px' }}>
              Recommended Strategy:
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-dark, #2A2020)', lineHeight: 1.45 }}>
              <li><b>Darshan:</b> {bullets[0] || 'Dedicated darshan and Bhairavnath trek.'}</li>
              <li><b>Sightseeing:</b> {bullets[1] || 'Explore scenic places around Katra and foothills.'}</li>
              <li><b>Pace:</b> {bullets[2] || 'Flexible rest buffers with hill-station excursions.'}</li>
            </ul>
          </div>

          {recommendation.reasoning && (
            <div
              style={{
                background: '#FFF9F0',
                borderLeft: '3px solid #B8860B',
                padding: '6px 10px',
                borderRadius: '4px',
                lineHeight: 1.45,
              }}
            >
              <b>Why this plan:</b> {recommendation.reasoning}
            </div>
          )}

          {places.length > 0 && (
            <div>
              <div style={{ fontWeight: 700, color: 'var(--burgundy, #58111A)', marginBottom: '6px' }}>
                Suggested Places ({places.length}):
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {places.slice(0, 4).map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onExplorePlace ? onExplorePlace(p.name) : onSend(`Tell me about ${p.name}`)}
                    className="btn btn-secondary"
                    style={{ padding: '3px 9px', fontSize: '0.74rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Landmark size={12} />
                    <span>{p.name}</span>
                    <ArrowRight size={11} />
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
            <button
              type="button"
              onClick={() => onSend('Show detailed cost breakdown')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--burgundy, #58111A)',
                fontWeight: 700,
                fontSize: '0.76rem',
                cursor: 'pointer',
                textDecoration: 'underline',
                padding: '2px 4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Coins size={12} />
              <span>View Itemized Cost Breakdown</span>
              <ArrowRight size={11} />
            </button>
          </div>
        </div>
      </details>

      {/* No-availability Message / Warning Card */}
      {message?.plan && (message.plan.status === 'NO_AVAILABILITY' || message.plan.status === 'NO_COMBINATION') && (
        <div
          style={{
            background: '#FFF9F2',
            border: '1.5px solid #DFD2BC',
            borderRadius: '10px',
            padding: '10px 14px',
            marginTop: '12px',
          }}
        >
          <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '0.84rem', color: 'var(--burgundy)', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={14} />
            <span>TRAVEL OPTIONS NOT FOUND</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dark)', marginBottom: '4px' }}>
            No verified transport combinations were found for the selected date and route.
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.35 }}>
            <b>Try:</b> Another travel date (e.g. next week), another transport mode, or a supported departure hub.
          </div>
        </div>
      )}
    </div>
  );
}
