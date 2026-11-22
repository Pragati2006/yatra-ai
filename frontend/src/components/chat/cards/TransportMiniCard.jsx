import React from 'react';
import { Plane, Bus, Train, MapPin, GitFork, Info } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';

/**
 * Clean Transport options summary card for AI Chat stream with honest provenance.
 * Preserves statutory tariff slabs, indicative fare ranges, timetable windows,
 * and multimodal airport-to-Katra guidance for flights.
 */
export default function TransportMiniCard({ option }) {
  if (!option) return null;

  const mode = (option.mode || 'Train').toUpperCase();
  const isFlight = mode === 'FLIGHT' || mode === 'AIR';
  const isBus = mode === 'BUS';
  const isTrain = mode === 'TRAIN';

  // Accurate naming per travel mode
  let name = option.train_name || option.flight_no || option.vehicle_name || option.operator || 'Scheduled Transport';
  if (isFlight) {
    if (option.flight_no && option.operator) {
      name = `${option.operator} ${option.flight_no}`;
    } else if (option.transport_no) {
      name = option.transport_no;
    } else {
      name = option.operator || 'Scheduled Passenger Flight';
    }
  } else if (isBus) {
    name = option.operator || option.vehicle_name || 'Public Bus Service';
  }

  // Truthful timing format: do not collapse windows into point departures
  const depTime = (option.departure_time && option.departure_time !== 'N/A')
    ? option.departure_time
    : (option.departure_window ? `Window: ${option.departure_window}` : (option.operating_hours ? `Hours: ${option.operating_hours}` : null));

  const arrTime = (option.arrival_time && option.arrival_time !== 'N/A')
    ? option.arrival_time
    : (!isFlight ? (option.estimated_duration_desc || (option.duration_hours ? `~${option.duration_hours}h journey` : null)) : null);

  // Airport codes or bus stands
  const origin = option.origin_airport_code
    ? `${option.origin || 'Origin'} (${option.origin_airport_code})`
    : (option.origin_bus_stand || option.origin || 'Departure Point');

  const dest = option.destination_airport_code
    ? `${option.destination || 'Jammu'} (${option.destination_airport_code})`
    : (option.destination_bus_stand || option.destination || 'Katra');

  // Honest tariff display: Statutory slabs and market estimates must never appear as fixed ticket prices
  let fareDisplay = 'Tariff at counter';
  if (option.fare_classification === 'STATUTORY_NOTIFIED_PER_KM_SLAB') {
    if (option.indicative_fare_min != null && option.indicative_fare_max != null) {
      fareDisplay = `Counter Slab: ₹${option.indicative_fare_min}–₹${option.indicative_fare_max}`;
    } else {
      fareDisplay = 'Statutory Tariff Slab';
    }
  } else if (
    option.fare_classification === 'UNAVAILABLE' ||
    (isFlight && option.indicative_fare_min == null && option.fare == null && option.price == null) ||
    (isTrain && option.indicative_fare_min == null && option.fare == null && option.price == null)
  ) {
    fareDisplay = isFlight ? 'Airfare on airline website' : (isTrain ? 'Fare on IRCTC portal' : 'Tariff at counter');
  } else if (
    option.fare_classification === 'ESTIMATED_MARKET_TARIFF' ||
    (option.indicative_fare_min != null && option.indicative_fare_max != null)
  ) {
    if (option.indicative_fare_min != null && option.indicative_fare_max != null) {
      fareDisplay = `Est. ₹${option.indicative_fare_min}–₹${option.indicative_fare_max}`;
    } else {
      fareDisplay = `Est. ₹${option.indicative_fare_min || option.fare || option.price}`;
    }
  } else if (option.fare != null && option.fare !== '' && Number(option.fare) > 0) {
    fareDisplay = `₹${option.fare}/seat`;
  } else if (option.price != null && option.price !== '' && Number(option.price) > 0) {
    fareDisplay = `₹${option.price}/seat`;
  } else if (option.indicative_fare_min != null) {
    fareDisplay = `From ₹${option.indicative_fare_min}`;
  }

  // Honest status: never display green REGULAR SERVICE or fake live availability
  const isGuidanceOnly = option.route_type === 'ROUTE_GUIDANCE_ONLY' || option.schedule_type === 'CONNECTING_HUB_GUIDANCE' || option.timetable_verification?.status === 'unverified';
  const timetableVerified = option.timetable_verification?.status === 'verified_official_source';
  const timetablePartiallyVerified = option.timetable_verification?.status === 'partially_verified';
  const status = option.status || option.availability || (
    isBus
      ? (option.is_connecting
          ? 'CONNECTING (EST. BUFFER)'
          : (option.is_partially_verified || option.verification_status === 'partially_verified'
              ? 'PARTIALLY VERIFIED'
              : 'VERIFIED SCHEDULE'))
      : (
        isFlight
          ? (isGuidanceOnly
              ? (option.schedule_type === 'CONNECTING_HUB_GUIDANCE' ? 'CONNECTING GUIDANCE' : 'ROUTE GUIDANCE')
              : (timetableVerified ? 'TIMETABLE VERIFIED' : (timetablePartiallyVerified ? 'INDICATIVE SCHEDULE' : 'TIMETABLE UNVERIFIED')))
          : (timetableVerified ? 'TIMETABLE VERIFIED' : 'ROUTE GUIDANCE')
      )
  );

  let timeRouteDisplay = `${origin} → ${dest}`;
  if (isFlight && !depTime && !arrTime) {
    timeRouteDisplay = `${origin} → ${dest} (Flight route guidance — confirm current schedules and journey duration with the airline)`;
  } else if (isTrain && option.timetable_verification?.status === 'unverified') {
    timeRouteDisplay = `${origin} → ${dest} (Timetable via NTES 139 / irctc.co.in)`;
  } else if (depTime && arrTime) {
    timeRouteDisplay = `${origin} (${depTime}) → ${dest} (${arrTime})`;
  } else if (depTime) {
    timeRouteDisplay = `${origin} (${depTime}) → ${dest}`;
  } else if (arrTime) {
    timeRouteDisplay = `${origin} → ${dest} (${arrTime})`;
  } else {
    timeRouteDisplay = isFlight
      ? `${origin} → ${dest} (Flight route guidance — confirm current schedules and journey duration with the airline)`
      : `${origin} → ${dest} (Timetable at terminal)`;
  }

  const isConnecting = option.route_type === 'CONNECTING' || option.route_type === 'ROUTE_GUIDANCE_ONLY' || Boolean(option.is_connecting);

  return (
    <div
      data-testid="chat-transport-card"
      style={{
        marginTop: '0.65rem',
        background: 'var(--surface-white, #FFFCF9)',
        border: '1px solid var(--border-default, #E9DED6)',
        borderRadius: '12px',
        padding: '10px 14px',
        boxShadow: '0 1px 4px rgba(84, 21, 45, 0.04)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isFlight ? <Plane size={15} color="var(--royal-plum, #54152D)" /> : (isBus ? <Bus size={15} color="var(--royal-plum, #54152D)" /> : <Train size={15} color="var(--royal-plum, #54152D)" />)}
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--royal-plum, #54152D)' }}>{name}</span>
          <span className="pill pill-gold" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>{mode}</span>
          {isConnecting && (
            <span
              style={{
                fontSize: '0.65rem',
                padding: '1px 5px',
                borderRadius: '4px',
                background: '#FFF3CD',
                color: '#856404',
                fontWeight: 600,
              }}
            >
              {isGuidanceOnly ? 'Route Guidance (Connecting' : 'Connecting'}
              {option.layover_airports?.length ? ` via ${option.layover_airports.join(', ')}` : ''}
              {isGuidanceOnly ? ')' : ''}
            </span>
          )}
        </div>
        <span style={{ fontWeight: 800, fontSize: '0.86rem', color: '#8A5D00' }}>
          {fareDisplay}
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
        <span>{timeRouteDisplay}</span>
        {option.is_live_status ? (
          <span style={{ color: '#28A745', fontWeight: 700 }}>● {status}</span>
        ) : (
          <span style={{ color: '#8A5D00', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            <Info size={11} />
            <span>{status}</span>
          </span>
        )}
      </div>

      {/* Multimodal Flight Ground Link Advisory */}
      {isFlight && (
        <div
          style={{
            marginTop: '4px',
            fontSize: '0.70rem',
            color: '#555',
            background: '#F9F6F0',
            padding: '3px 8px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <MapPin size={13} style={{ flexShrink: 0 }} />
          <span><strong>Jammu Airport (IXJ) transfer:</strong> ~50 km to Katra base camp (~1.5h via prepaid taxi from airport terminal; public JKRTC buses depart from Jammu Railway Station ~8 km away).</span>
        </div>
      )}

      {/* Multi-Leg Connecting Route Breakdown */}
      {Array.isArray(option.legs) && option.legs.length > 0 && (
        <div
          style={{
            marginTop: '8px',
            background: '#FDFBF7',
            border: '1px dashed #E5D2AD',
            borderRadius: '8px',
            padding: '8px 10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.73rem', fontWeight: 700, color: '#58111A', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <GitFork size={13} /> Connecting Itinerary ({option.legs.length} Legs via {option.primary_hub || 'Transfer Hub'})
            </span>
            {option.fallback_level && (
              <span style={{ fontSize: '0.62rem', color: '#856404', background: '#FFF3CD', padding: '1px 5px', borderRadius: '4px' }}>
                {option.fallback_level.split(':')[0]}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {option.legs.map((leg, idx) => {
              const isVerified = leg.verification_status === 'VERIFIED_SCHEDULE';
              const isRoadTransfer = leg.verification_status === 'ESTIMATED_ROAD_TRANSFER';
              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.69rem',
                    padding: '2px 0',
                    borderBottom: idx < option.legs.length - 1 ? '1px dotted #EFE7DB' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      background: '#58111A',
                      color: '#FFF',
                      fontSize: '0.60rem',
                      fontWeight: 800,
                    }}>
                      {leg.leg_number || idx + 1}
                    </span>
                    <span style={{ color: '#222' }}>
                      <strong>{leg.from_place}</strong> → <strong>{leg.to_place}</strong>
                    </span>
                    <span style={{ color: '#666', fontSize: '0.64rem' }}>
                      ({leg.mode}{leg.estimated_duration ? ` · ${leg.estimated_duration}` : ''})
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.62rem',
                      fontWeight: 600,
                      padding: '1px 5px',
                      borderRadius: '4px',
                      background: isVerified ? '#E8F5E9' : (isRoadTransfer ? '#E3F2FD' : '#FFF9C4'),
                      color: isVerified ? '#2E7D32' : (isRoadTransfer ? '#1565C0' : '#F57F17'),
                    }}
                  >
                    {isVerified ? 'Verified' : (isRoadTransfer ? 'Feeder Link' : 'Connecting Leg')}
                  </span>
                </div>
              );
            })}
          </div>
          {option.booking_advice && (
            <div style={{ marginTop: '5px', fontSize: '0.65rem', color: '#666', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Info size={11} />
              <span>{option.booking_advice}</span>
            </div>
          )}
          {Boolean(option.is_connecting || (Array.isArray(option.legs) && option.legs.length > 1)) && (
            <div style={{ marginTop: '6px', fontSize: '0.67rem', color: '#92400E', background: '#FEF3C7', padding: '4px 8px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
              <AlertTriangle size={12} color="#92400E" style={{ flexShrink: 0 }} />
              <span>Transfer Buffer Notice: Allow 45–60 min at {option.primary_hub || 'Jammu GBS'} transfer hub. Self-transfer connection.</span>
            </div>
          )}
        </div>
      )}

      {/* Provenance disclaimer strip */}
      <div
        style={{
          marginTop: '6px',
          paddingTop: '6px',
          borderTop: '1px solid #F5ECDA',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '4px',
          fontSize: '0.67rem',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FreshnessIndicator
            freshnessStatus={option.is_live_status ? 'live' : 'cached'}
            sourceType={option.source_type || 'curated_data'}
            customText={option.is_live_status ? 'Live Status' : (isBus ? 'Stage Carriage' : (isFlight ? 'DGCA Corridor' : 'Indicative Timetable'))}
          />
          <span>
            {option.is_live_status
              ? 'Real-time Telemetry'
              : (isBus
                  ? 'Public Stage Carriage Guide'
                  : (isFlight ? 'Official DGCA Commercial Corridor' : 'Curated Railway Route Guide'))}
          </span>
        </div>
        <span style={{ fontStyle: 'italic' }}>
          {option.is_live_status
            ? '*Live running telemetry'
            : (isBus
                ? (option.fare_classification === 'STATUTORY_NOTIFIED_PER_KM_SLAB'
                    ? '*Statutory notified tariff slab; verify timings and pay at bus stand counter'
                    : '*Indicative market tariff estimate; verify departures and fares with operator')
                : (isFlight
                    ? "*Airfare unavailable. Prices are dynamic; please check the airline's official booking website."
                    : '*Railway fare unavailable in static registry; timetable confirmation via NTES (139)'))}
        </span>
      </div>
    </div>
  );
}
