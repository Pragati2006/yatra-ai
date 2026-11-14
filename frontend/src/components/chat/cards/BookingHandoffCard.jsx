import React from 'react';
import { Ticket, ArrowRight } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';

/**
 * Booking Handoff Action Card for AI Chat stream.
 * Renders when the user indicates intent to book or when NAVIGATE_TO_BOOKING is returned.
 * Prepopulates trip context and transitions smoothly to the guided booking review flow.
 * Explicitly communicates simulated sandboxed demonstration status.
 */
export default function BookingHandoffCard({
  message,
  chatState,
  onNavigateToBooking,
  onSwitchToForm,
}) {
  const planOpts = message.options || message.plan?.options || chatState?.pending_options || null;
  const selOpt = message.selected_option || message.plan?.selected_option || chatState?.selected_option || (planOpts && planOpts.length > 0 ? planOpts[0] : null);
  const req = message.request || chatState?.current_request || null;
  const itin = message.itinerary || message.plan?.itinerary || chatState?.current_itinerary || null;
  const htl = message.hotel || message.plan?.hotel || chatState?.hotel || null;
  const bgt = message.budget_evaluation || message.plan?.budget_evaluation || chatState?.budget_evaluation || null;

  const pax = req?.pax || selOpt?.pax || 2;
  const origin = req?.origin || selOpt?.origin || 'Delhi';
  const mode = (req?.travel_mode || selOpt?.mode || 'Train').toUpperCase();
  const hotelName = htl?.name || 'Hotel in Katra';
  const totalAmount = bgt?.grand_total ? `₹${Math.round(bgt.grand_total).toLocaleString('en-IN')}` : null;

  const handleProceed = () => {
    const navPayload = {
      sessionId: message.session_id || chatState?.session_id,
      planVersion: message.plan_version || chatState?.plan_version || 1,
      feasible_places: message.feasible_places || chatState?.feasible_places || [],
      infeasible_places: message.infeasible_places || chatState?.infeasible_places || [],
      itinerary: itin,
      request: req,
      sightseeing_choice: req?.sightseeing_choice || null,
      options: planOpts,
      selected_option: selOpt,
      hotel: htl,
      budget_evaluation: bgt,
      planningMode: 'form',
      step: 2, // Step 2: Recommended Yatra Review
    };

    if (onNavigateToBooking) {
      onNavigateToBooking(navPayload);
    } else if (onSwitchToForm) {
      onSwitchToForm(navPayload);
    }
  };

  return (
    <div
      data-testid="booking-handoff-action-card"
      style={{
        marginTop: '0.85rem',
        background: 'linear-gradient(135deg, #FFFDF9 0%, #FAF4E8 100%)',
        border: '1.5px solid var(--gold-primary, #B8860B)',
        borderRadius: '14px',
        padding: '14px 16px',
        boxShadow: '0 4px 16px rgba(184, 134, 11, 0.12)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Ticket size={20} color="var(--burgundy)" />
          <div>
            <div
              style={{
                fontFamily: 'var(--font-serif, Cinzel, serif)',
                fontWeight: 800,
                fontSize: '0.92rem',
                color: 'var(--burgundy, #58111A)',
              }}
            >
              Sacred Yatra Booking Handoff
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted, #6B5C5C)' }}>
              Your trip details have been organized. Review options before human authorization.
            </div>
          </div>
        </div>

        <FreshnessIndicator
          freshnessStatus="simulated"
          sourceType="simulated_data"
          customText="Simulated Booking Portal"
        />
      </div>

      {/* Summary grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          margin: '10px 0 12px',
          background: '#FFFFFF',
          borderRadius: '10px',
          padding: '10px 12px',
          border: '1px solid var(--gold-border, #E5D2AD)',
        }}
      >
        <div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Route</div>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--burgundy)' }}>{origin} to Katra</div>
        </div>
        <div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Pilgrims & Mode</div>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-dark)' }}>{pax} Pax • {mode}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Accommodation</div>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-dark)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{hotelName}</div>
        </div>
        {totalAmount && (
          <div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Est. Total</div>
            <div style={{ fontSize: '0.84rem', fontWeight: 800, color: '#8A5D00' }}>{totalAmount}</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <button
          type="button"
          data-testid="continue-to-booking-btn"
          onClick={handleProceed}
          className="btn btn-gold"
          style={{
            padding: '9px 18px',
            fontSize: '0.86rem',
            fontWeight: 800,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            borderRadius: '999px',
            cursor: 'pointer',
            boxShadow: '0 3px 10px rgba(184, 134, 11, 0.25)',
          }}
        >
          <ArrowRight size={14} /> Review & Proceed with Booking
        </button>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          *Simulated demonstration environment. Human authorization strictly required before any automated actions.
        </span>
      </div>
    </div>
  );
}
