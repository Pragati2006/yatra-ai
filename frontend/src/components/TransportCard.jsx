import React from 'react';
import { Plane, Bus, Train, Info, Check, ArrowRight } from 'lucide-react';

export default function TransportCard({ option, isSelected, onSelect, pax = 1 }) {
  if (!option) return null;

  const tr = option.transport || option.flight || {};
  const slot = option.slot || {};
  const mode = (tr.mode || 'Train').toUpperCase();
  const operator = tr.operator || tr.name || (mode === 'TRAIN' ? 'Indian Railways' : 'Express Service');
  const serviceNo = tr.transport_no || (tr.id ? `ID #${tr.id}` : null);

  const origin = tr.origin || tr.origin_bus_stand || 'Departure Point';
  const dest = tr.destination || tr.destination_bus_stand || 'Katra';

  // Timetable truthfulness: If point timings are unverified (e.g. curated railway), suppress fabricated clock times
  const isTrainTimetableUnverified = mode === 'TRAIN' && (tr.timetable_verification?.status === 'unverified' || !tr.timetable_verification);
  const depTime = isTrainTimetableUnverified ? 'Check NTES (139)' : (tr.departure_time || 'Check schedule');

  const resolveDataTier = () => {
    if (tr.data_tier) return tr.data_tier;
    if (tr.dataTier) return tr.dataTier;
    if (tr.is_live_telemetry || tr.live_tracking_status === 'ACTIVE') return 'Live Availability';
    if (tr.is_simulated || tr.is_demonstration || tr.is_synthetic_test_fare || mode === 'HELICOPTER') return 'Demonstration Data';
    if (isTrainTimetableUnverified || tr.timetable_verification?.status === 'unverified' || tr.is_unverified) return 'Unavailable / Unverified';
    return 'Indicative Estimate';
  };

  const getDataTierPillStyle = (tier) => {
    switch (tier) {
      case 'Live Availability':
        return { background: '#D4EDDA', color: '#155724', border: '1px solid #C3E6CB' };
      case 'Indicative Estimate':
        return { background: '#FFF3CD', color: '#856404', border: '1px solid #FFEEBA' };
      case 'Demonstration Data':
        return { background: '#F8D7DA', color: '#721C24', border: '1px solid #F5C6CB' };
      case 'Unavailable / Unverified':
      default:
        return { background: '#E2E3E5', color: '#383D41', border: '1px solid #D6D8DB' };
    }
  };

  // Calculate arrival time or display safe fallback
  let calculatedArrTime = tr.arrival_time;
  if (!calculatedArrTime && tr.departure_time && tr.duration_hours && !isTrainTimetableUnverified) {
    try {
      const [depH, depM] = tr.departure_time.split(':').map(Number);
      const totalMinutes = depH * 60 + depM + Math.round(tr.duration_hours * 60);
      const arrHour = Math.floor(totalMinutes / 60) % 24;
      const arrMin = totalMinutes % 60;
      const daysLater = Math.floor(totalMinutes / (24 * 60));
      calculatedArrTime = `${String(arrHour).padStart(2, '0')}:${String(arrMin).padStart(2, '0')}${daysLater > 0 ? ` (+${daysLater}d)` : ''}`;
    } catch {
      calculatedArrTime = tr.departure_time;
    }
  }
  const isFlight = mode === 'FLIGHT';
  const isBus = mode === 'BUS';
  const isTrain = mode === 'TRAIN';

  const arrTime = isTrainTimetableUnverified
    ? 'Check NTES (139)'
    : (calculatedArrTime || (!isFlight && tr.duration_hours ? `~${tr.duration_hours}h` : (isFlight ? 'Confirm with airline' : 'Enquire at counter')));

  const durationStr = !isFlight && !isTrainTimetableUnverified ? (tr.duration_str || (tr.duration_mins ? `${Math.floor(tr.duration_mins / 60)}h ${tr.duration_mins % 60}m` : null)) : null;

  // Fares segregation: never display unavailable airfare, train fare, or counter slab as confirmed ₹0
  const isFareUnavailable = tr.fare_classification === 'UNAVAILABLE' ||
    tr.fare_classification === 'STATUTORY_NOTIFIED_PER_KM_SLAB' ||
    (isFlight && tr.fare == null && tr.price == null && tr.indicative_fare_min == null) ||
    (isTrain && tr.fare == null && tr.price == null && tr.indicative_fare_min == null) ||
    (tr.fare == null && tr.price == null && tr.fare_per_person == null);

  const farePerPerson = isFareUnavailable ? null : (tr.fare_per_person || tr.price || 0);
  const transportFareTotal = isFareUnavailable ? null : (tr.total_fare || (farePerPerson * pax));
  const slotPricePerPerson = slot.price || 0;
  const slotTotal = slotPricePerPerson * pax;
  const bundleTotal = option.total_price || (isFareUnavailable ? slotTotal : ((transportFareTotal || 0) + slotTotal));

  // Truthful darshan wording: Normal darshan is free of cost via mandatory RFID card at Katra; not a confirmed booking
  const bundleExplanation = option.bundle_explanation || (
    isFareUnavailable
      ? (isFlight
          ? `Includes pilgrimage itinerary planning for ${pax} ${pax === 1 ? 'pilgrim' : 'pilgrims'}. Airfare is dynamic and payable on official airline portal. Normal Darshan is free; collect RFID card at Katra.`
          : (isTrain
              ? `Includes pilgrimage itinerary planning for ${pax} ${pax === 1 ? 'pilgrim' : 'pilgrims'}. Train fare is dynamic and payable on official IRCTC portal (irctc.co.in). Normal Darshan is free; collect RFID card at Katra.`
              : `Includes pilgrimage itinerary planning for ${pax} ${pax === 1 ? 'pilgrim' : 'pilgrims'}. Bus tariff payable at bus stand counter (approx ₹${tr.indicative_fare_min || 75}–₹${tr.indicative_fare_max || 110}). Normal Darshan is free; collect RFID card at Katra.`))
      : `Includes verified ${mode.toLowerCase()} fare for ${pax} ${pax === 1 ? 'pilgrim' : 'pilgrims'} and yatra planning guidance. Normal Darshan is free via Katra RFID registration.`
  );

  return (
    <div
      className="card card-hover transport-card"
      data-testid="transport-card"
      style={{
        border: isSelected ? '2px solid var(--royal-plum, #54152D)' : '1px solid var(--border-default, #E9DED6)',
        background: isSelected ? 'var(--soft-plum-surface, #F0E3E7)' : 'var(--surface-white, #FFFCF9)',
        borderRadius: '14px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '12px',
        position: 'relative',
      }}
    >
      {/* Header Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span className="pill" style={{ background: 'var(--secondary-bg, #F2EAE4)', color: 'var(--royal-plum, #54152D)', border: '1px solid var(--border-default, #E9DED6)', display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px' }}>
              {isFlight ? <Plane size={12} /> : (isBus ? <Bus size={12} /> : <Train size={12} />)}
              <span>{isFlight ? 'FLIGHT' : (isBus ? 'BUS' : 'TRAIN')}</span>
            </span>
            <span style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--royal-plum, #54152D)' }}>
              {operator}
            </span>
            {serviceNo && (
              <span className="pill" style={{ background: 'var(--soft-plum-surface, #F0E3E7)', color: 'var(--royal-plum, #54152D)', fontSize: '0.74rem', fontWeight: 700, padding: '2px 7px', borderRadius: '6px' }}>
                {serviceNo}
              </span>
            )}
          </div>
        </div>
        <span className="pill" style={{ ...getDataTierPillStyle(resolveDataTier()), fontSize: '0.72rem', fontWeight: 700 }}>
          ● {resolveDataTier()}
        </span>
      </div>

      {/* Origin & Destination Schedule Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr',
        alignItems: 'center',
        padding: '6px 0',
        borderTop: '1px solid var(--border-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-dark)' }}>
            {depTime}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
            {origin}
          </div>
        </div>

        <div style={{ textAlign: 'center', padding: '0 8px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isTrainTimetableUnverified ? 'NTES 139' : (durationStr ? durationStr : (isFlight ? 'Direct' : 'Scheduled'))}
          </div>
          <div style={{ color: 'var(--gold-primary)', fontSize: '0.85rem' }}>────── →</div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-dark)' }}>
            {arrTime}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
            {dest}
          </div>
        </div>
      </div>

      {/* Ground Transfer Footnote for Flight Options */}
      {isFlight && (
        <div style={{
          background: '#FFF9ED',
          border: '1px solid #F3E5AB',
          borderRadius: '6px',
          padding: '6px 8px',
          fontSize: '0.72rem',
          color: '#856404',
          lineHeight: 1.35,
        }}>
          <strong>Ground Transfer Note:</strong> Flights land at Jammu Airport (IXJ). Katra base camp is ~50 km away (~1.5h via taxi/JKSRTC bus).
        </div>
      )}

      {/* Train Timetable Footnote for Curated Train Options */}
      {isTrainTimetableUnverified && (
        <div style={{
          background: '#FFF9ED',
          border: '1px solid #F3E5AB',
          borderRadius: '6px',
          padding: '6px 8px',
          fontSize: '0.72rem',
          color: '#856404',
          lineHeight: 1.35,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Info size={12} style={{ flexShrink: 0 }} />
          <span><strong>Timetable via NTES:</strong> Daily departures operate from {origin}. Exact departure minutes and platform details confirmed via National Train Enquiry System (139) or irctc.co.in.</span>
        </div>
      )}

      {/* Bus Stage Carriage Footnote */}
      {isBus && (
        <div style={{
          background: '#FFF9ED',
          border: '1px solid #F3E5AB',
          borderRadius: '6px',
          padding: '6px 8px',
          fontSize: '0.72rem',
          color: '#856404',
          lineHeight: 1.35,
        }}>
          <strong>Public Stage Carriage:</strong> Governed by J&amp;K STA tariff notification. Operates regular daytime departures; tickets purchased at terminal bus stand counter.
        </div>
      )}

      {/* Connecting Journey Multi-Leg Breakdown */}
      {Boolean(tr.is_connecting || (Array.isArray(tr.legs) && tr.legs.length > 0)) && (
        <div style={{
          background: '#FFFDF9',
          border: '1px dashed #E5D2AD',
          borderRadius: '8px',
          padding: '8px 10px',
          fontSize: '0.74rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontWeight: 700, color: 'var(--burgundy)' }}>
              Connecting Itinerary ({tr.legs ? tr.legs.length : 2} Legs via {tr.primary_hub || 'Transfer Hub'})
            </span>
            {tr.fallback_level && (
              <span style={{ fontSize: '0.64rem', color: '#856404', background: '#FFF3CD', padding: '1px 6px', borderRadius: '4px' }}>
                {tr.fallback_level.split(':')[0]}
              </span>
            )}
          </div>
          {Array.isArray(tr.legs) && tr.legs.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {tr.legs.map((leg, idx) => {
                const isVerified = leg.verification_status === 'VERIFIED_SCHEDULE';
                const isRoadTransfer = leg.verification_status === 'ESTIMATED_ROAD_TRANSFER';
                return (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.70rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        background: 'var(--burgundy)',
                        color: '#FFF',
                        borderRadius: '50%',
                        width: '16px',
                        height: '16px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.62rem',
                        fontWeight: 800,
                      }}>{leg.leg_number || idx + 1}</span>
                      <span><strong>{leg.from_place}</strong> → <strong>{leg.to_place}</strong> ({leg.mode}{leg.estimated_duration ? ` · ${leg.estimated_duration}` : ''})</span>
                    </div>
                    <span style={{
                      fontSize: '0.62rem',
                      fontWeight: 600,
                      padding: '1px 5px',
                      borderRadius: '4px',
                      background: isVerified ? '#E8F5E9' : (isRoadTransfer ? '#E3F2FD' : '#FFF9C4'),
                      color: isVerified ? '#2E7D32' : (isRoadTransfer ? '#1565C0' : '#F57F17'),
                    }}>
                      {isVerified ? 'Verified' : (isRoadTransfer ? 'Feeder Link' : 'Connecting Leg')}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
          {tr.booking_advice && (
            <div style={{ marginTop: '5px', fontSize: '0.68rem', color: '#666', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Info size={11} />
              <span>{tr.booking_advice}</span>
            </div>
          )}
          {Boolean(tr.is_connecting || (Array.isArray(tr.legs) && tr.legs.length > 1)) && (
            <div style={{ marginTop: '6px', fontSize: '0.70rem', color: '#92400E', background: '#FEF3C7', padding: '4px 8px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
              <AlertCircle size={12} color="#92400E" style={{ flexShrink: 0 }} />
              <span>Transfer Buffer Notice: Allow 45–60 min at {tr.primary_hub || 'Jammu GBS'} transfer hub. Non-interline self-connection.</span>
            </div>
          )}
        </div>
      )}

      {/* Yatra Darshan Guidance */}
      <div style={{
        background: 'var(--bg-subtle)',
        borderRadius: '8px',
        padding: '8px 10px',
        fontSize: '0.78rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <span style={{ fontWeight: 700, color: 'var(--burgundy)' }}>
            Darshan Guidance:
          </span>{' '}
          {slot.category || 'Normal Darshan'}
          {slot.slot_date && <span style={{ color: 'var(--text-muted)' }}> · {slot.slot_date}</span>}
        </div>
        <span style={{ fontWeight: 700, color: '#155724', fontSize: '0.74rem' }}>
          {slotPricePerPerson > 0 ? `+₹${slotTotal}` : 'Free Entry (RFID at Katra)'}
        </span>
      </div>

      {/* Transparent Price Breakdown */}
      <div style={{
        background: '#FAF8F5',
        borderRadius: '8px',
        padding: '8px 10px',
        fontSize: '0.76rem',
        color: 'var(--text-dark)',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>
            {isFareUnavailable ? 'Transport Tariff:' : `Transport Fare (${pax}x ₹${farePerPerson}):`}
          </span>
          <span style={{ fontWeight: 700 }}>
            {isFareUnavailable
              ? (isFlight
                  ? 'Airfare on airline website (dynamic pricing)'
                  : (isTrain
                      ? 'Fare on IRCTC portal (dynamic pricing)'
                      : (tr.indicative_fare_min
                          ? `Statutory slab approx ₹${tr.indicative_fare_min}–₹${tr.indicative_fare_max || 110} (Counter)`
                          : 'Tariff payable at counter')))
              : `₹${transportFareTotal.toLocaleString('en-IN')}`}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Darshan Entry (Normal):</span>
          <span style={{ fontWeight: 700, color: '#155724' }}>
            {slotTotal === 0 ? 'Free Entry (RFID Card at Katra)' : `₹${slotTotal.toLocaleString('en-IN')}`}
          </span>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px dashed #DDD', paddingTop: '4px', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Info size={11} />
          <span>{bundleExplanation}</span>
        </div>
      </div>

      {/* Total & Action */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            {isFareUnavailable
              ? (isFlight
                  ? 'Darshan Bundle (Excludes Airfare)'
                  : (isTrain ? 'Itinerary Plan (Train Fare Dynamic)' : 'Itinerary Plan (Counter Bus Tariff)'))
              : `Total Package (${pax} ${pax === 1 ? 'pilgrim' : 'pilgrims'})`}
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--burgundy)' }}>
            {isFareUnavailable
              ? (isFlight ? 'Airfare Dynamic' : (isTrain ? 'Fare via IRCTC' : 'Tariff at Counter'))
              : `₹${bundleTotal.toLocaleString('en-IN')}`}
          </div>
        </div>

        <button
          onClick={onSelect}
          className={`btn ${isSelected ? 'btn-gold' : 'btn-primary'}`}
          style={{ padding: '0.5rem 1.4rem', fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          {isSelected ? (
            <>
              <Check size={13} />
              <span>Selected Option</span>
            </>
          ) : (
            <>
              <span>Select Option</span>
              <ArrowRight size={13} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
