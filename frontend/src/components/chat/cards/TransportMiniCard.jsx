import React from 'react';

/**
 * Clean Transport options summary card for AI Chat stream.
 */
export default function TransportMiniCard({ option }) {
  if (!option) return null;

  const mode = (option.mode || 'Train').toUpperCase();
  const name = option.train_name || option.flight_no || option.vehicle_name || 'Vande Bharat Express';
  const depTime = option.departure_time || '06:00 AM';
  const arrTime = option.arrival_time || '02:00 PM';
  const origin = option.origin || 'Delhi';
  const fare = option.fare || option.price || 1650;
  const status = option.status || option.availability || 'AVAILABLE';

  return (
    <div
      style={{
        marginTop: '0.65rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '10px 14px',
        boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>{mode === 'FLIGHT' ? '✈️' : (mode === 'BUS' ? '🚌' : '🚆')}</span>
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--burgundy)' }}>{name}</span>
          <span className="pill pill-gold" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>{mode}</span>
        </div>
        <span style={{ fontWeight: 800, fontSize: '0.86rem', color: '#8A5D00' }}>
          ₹{fare}/seat
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
        <span>{origin} ({depTime}) ➔ Katra ({arrTime})</span>
        <span style={{ color: '#28A745', fontWeight: 700 }}>● {status}</span>
      </div>
    </div>
  );
}
