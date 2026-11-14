import React from 'react';
import { Building2, MapPin, Phone, Globe } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';

/**
 * Clean Hotel details card for AI Chat stream with verified catalog metadata,
 * authentic contact links, and honest availability disclaimers.
 */
export default function HotelMiniCard({ hotel }) {
  if (!hotel) return null;

  const name = hotel.name || 'Katra Accommodation';
  const category = (hotel.category || 'Standard').toUpperCase();
  const price = hotel.price_per_night || hotel.price || 1200;
  const address = hotel.address || hotel.location || 'Katra, Jammu & Kashmir';
  const phone = hotel.phone;
  const officialWebsite = hotel.official_website;
  const isSmvdsb = hotel.operator_type === 'SMVDSB' || category.includes('DHARAMSHALA');
  const disclaimer = hotel.tariff_disclaimer || (isSmvdsb ? 'Official SMVDSB Subsidized Tariff Schedule' : 'Published Indicative Tariff');

  return (
    <div
      data-testid="chat-hotel-card"
      style={{
        marginTop: '0.65rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '12px 14px',
        boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
      }}
    >
      {/* Header: Name, Category, Price */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <Building2 size={15} color="var(--burgundy)" />
          <span style={{ fontWeight: 700, fontSize: '0.86rem', color: 'var(--burgundy)' }}>{name}</span>
          <span
            className={isSmvdsb ? 'pill pill-gold' : 'pill pill-gray'}
            style={{ fontSize: '0.68rem', padding: '1px 6px' }}
          >
            {category}
          </span>
          {hotel.room_requirement_status === 'UNVERIFIED' && (
            <span
              className="pill pill-gray"
              style={{ fontSize: '0.64rem', padding: '1px 5px', opacity: 0.85 }}
            >
              Inventory Unverified
            </span>
          )}
        </div>
        <span style={{ fontWeight: 800, fontSize: '0.88rem', color: '#8A5D00' }}>
          ₹{price}/night
        </span>
      </div>

      {/* Address & Landmark */}
      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <MapPin size={13} style={{ flexShrink: 0 }} />
        <span>{address}</span>
      </div>

      {/* Contact & Direct Website Links (if available) */}
      {(phone || officialWebsite) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.74rem', marginBottom: '8px', flexWrap: 'wrap' }}>
          {phone && (
            <a
              href={`tel:${phone.replace(/[^0-9+]/g, '')}`}
              style={{ color: 'var(--burgundy)', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              <Phone size={12} />
              <span>{phone}</span>
            </a>
          )}
          {officialWebsite && (
            <a
              href={officialWebsite}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#0066CC', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              <Globe size={12} />
              <span>Official Website</span>
            </a>
          )}
        </div>
      )}

      {/* Honest Availability & Provenance Disclaimer Strip */}
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
            freshnessStatus="not_applicable"
            sourceType="curated_data"
            customText="Curated Catalog"
          />
          <span style={{ fontWeight: 600, color: isSmvdsb ? '#8A5D00' : '#4A5568' }}>
            Indicative Tariff: {disclaimer}
          </span>
        </div>
        <span style={{ fontStyle: 'italic', color: '#718096' }}>
          *Room availability subject to check-in confirmation • Direct property verification recommended
        </span>
      </div>
    </div>
  );
}
