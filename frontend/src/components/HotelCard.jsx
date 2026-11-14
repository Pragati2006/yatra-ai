import React from 'react';
import { Building2, MapPin, Phone, Globe, Check } from 'lucide-react';

export default function HotelCard({ hotel, isSelected, onSelect }) {
  const name = hotel.name || 'Katra Accommodation';
  const category = hotel.category || 'Standard';
  const price = hotel.price_per_night || hotel.price || 1200;
  const hasRoomsCount = hotel.rooms_available != null;
  const rooms = hotel.rooms_available;
  const location = hotel.address || hotel.landmark || hotel.location || 'Katra Town Centre';
  const phone = hotel.phone;
  const officialWebsite = hotel.official_website;
  const amenities = Array.isArray(hotel.amenities)
    ? hotel.amenities
    : (typeof hotel.amenities === 'string' ? hotel.amenities.split(',') : ['Verified Property', 'Pilgrim Friendly', 'Direct Contact']);

  return (
    <div
      className="card card-hover"
      style={{
        border: isSelected ? '2px solid var(--gold-primary)' : '1px solid var(--gold-border)',
        background: isSelected ? '#FFFCF7' : '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '1.15rem',
        gap: '10px',
      }}
    >
      <div>
        {/* Category Pill & Availability Status */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span className="pill pill-gold" style={{ fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Building2 size={12} />
            <span>{category}</span>
          </span>
          {hasRoomsCount ? (
            <span style={{ fontSize: '0.74rem', color: rooms <= 3 ? '#C0392B' : '#27AE60', fontWeight: 700 }}>
              {rooms} {rooms === 1 ? 'room' : 'rooms'} left
            </span>
          ) : (
            <span style={{ fontSize: '0.70rem', color: '#718096', fontWeight: 500, fontStyle: 'italic' }}>
              Live Availability: Not Checked (Unverified)
            </span>
          )}
        </div>

        {/* Hotel Name */}
        <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.05rem', color: 'var(--burgundy)', lineHeight: 1.25 }}>
          {name}
        </div>

        {/* Location */}
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={12} style={{ flexShrink: 0 }} />
          <span>{location}</span>
        </div>

        {/* Contact Links */}
        {(phone || officialWebsite) && (
          <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem', marginTop: '6px', flexWrap: 'wrap' }}>
            {phone && (
              <span style={{ color: 'var(--burgundy)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Phone size={11} />
                <span>{phone}</span>
              </span>
            )}
            {officialWebsite && (
              <a
                href={officialWebsite}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#0066CC', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              >
                <Globe size={11} />
                <span>Official Link</span>
              </a>
            )}
          </div>
        )}

        {/* Amenities */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' }}>
          {amenities.slice(0, 3).map((am, i) => (
            <span
              key={i}
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '2px 8px',
                fontSize: '0.72rem',
                color: 'var(--text-dark)',
              }}
            >
              {am.trim()}
            </span>
          ))}
        </div>
      </div>

      {/* Pricing & Selection */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: '10px',
        marginTop: '6px',
      }}>
        <div>
          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--burgundy)' }}>
            ₹{price.toLocaleString('en-IN')}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {' '}/ night
          </span>
        </div>

        <button
          onClick={onSelect}
          className={`btn ${isSelected ? 'btn-gold' : 'btn-outline'}`}
          style={{ padding: '0.45rem 1.15rem', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          {isSelected ? (
            <>
              <Check size={12} />
              <span>Selected Stay</span>
            </>
          ) : (
            'Select Stay'
          )}
        </button>
      </div>
    </div>
  );
}
