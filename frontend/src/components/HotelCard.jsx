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
        border: isSelected ? '2px solid var(--royal-plum, #54152D)' : '1px solid var(--border-default, #E9DED6)',
        background: isSelected ? 'var(--soft-plum-surface, #F0E3E7)' : 'var(--surface-white, #FFFCF9)',
        borderRadius: '14px',
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
          <span className="pill" style={{ background: 'var(--secondary-bg, #F2EAE4)', color: 'var(--royal-plum, #54152D)', border: '1px solid var(--border-default, #E9DED6)', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', borderRadius: '6px', fontWeight: 700 }}>
            <Building2 size={12} />
            <span>{category}</span>
          </span>
          {hasRoomsCount ? (
            <span style={{ fontSize: '0.74rem', color: rooms <= 3 ? '#C75A60' : '#3E876C', fontWeight: 700 }}>
              {rooms} {rooms === 1 ? 'room' : 'rooms'} left
            </span>
          ) : (
            <span style={{ fontSize: '0.70rem', color: 'var(--text-muted, #A39994)', fontWeight: 500, fontStyle: 'italic' }}>
              Live Availability: Not Checked (Unverified)
            </span>
          )}
        </div>

        {/* Hotel Name */}
        <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 800, fontSize: '1.05rem', color: 'var(--royal-plum, #54152D)', lineHeight: 1.25 }}>
          {name}
        </div>

        {/* Location */}
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #796D69)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={12} style={{ flexShrink: 0 }} />
          <span>{location}</span>
        </div>

        {/* Contact Links */}
        {(phone || officialWebsite) && (
          <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem', marginTop: '6px', flexWrap: 'wrap' }}>
            {phone && (
              <span style={{ color: 'var(--royal-plum, #54152D)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Phone size={11} />
                <span>{phone}</span>
              </span>
            )}
            {officialWebsite && (
              <a
                href={officialWebsite}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--royal-plum, #54152D)', textDecoration: 'none', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
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
                background: 'var(--secondary-bg, #F2EAE4)',
                border: '1px solid var(--border-subtle, #F0E8E2)',
                borderRadius: '6px',
                padding: '2px 8px',
                fontSize: '0.72rem',
                color: 'var(--text-primary, #30272A)',
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
