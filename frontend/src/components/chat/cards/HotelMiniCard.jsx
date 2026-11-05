import React from 'react';

/**
 * Clean Hotel details card for AI Chat stream.
 */
export default function HotelMiniCard({ hotel }) {
  if (!hotel) return null;

  const name = hotel.name || 'Hotel in Katra';
  const category = (hotel.category || 'Deluxe').toUpperCase();
  const price = hotel.price_per_night || hotel.price || 2500;
  const rating = hotel.rating || '4.5';
  const address = hotel.address || hotel.location || 'Near Katra Main Market';

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
          <span>🏨</span>
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--burgundy)' }}>{name}</span>
          <span className="pill pill-gold" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>{category}</span>
        </div>
        <span style={{ fontWeight: 800, fontSize: '0.86rem', color: '#8A5D00' }}>
          ₹{price}/night
        </span>
      </div>
      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
        📍 {address} • ⭐ {rating}/5 Devotee Rating
      </div>
    </div>
  );
}
