import React, { useState, useEffect } from 'react';
import { Building2, MapPin, Phone, Globe, Check, ArrowLeft, Search, RefreshCw, Star, ShieldCheck } from 'lucide-react';
import { getAccommodation } from '../services/api';

const CURATED_ACCOMMODATIONS = [
  {
    id: 'smvdsb-niharika',
    name: 'Niharika Complex (SMVDSB)',
    type: 'Shrine Board',
    location: 'Near Bus Stand, Katra (Base)',
    tariff: '₹800 - ₹2,100 / night',
    distance: '0.2 km from Katra Bus Stand | 1.8 km to Banganga',
    rating: 4.5,
    amenities: ['Pure Veg Bhojanalaya', 'Locker Facility', 'Yatra Registration Counter', '24h Hot Water'],
    inventoryNote: 'Reserved directly via Shrine Board portal. High demand.',
    officialLink: 'https://www.maavaishnodevi.org',
  },
  {
    id: 'smvdsb-shakti',
    name: 'Shakti Bhawan (SMVDSB)',
    type: 'Shrine Board',
    location: 'Holy Cave Bhawan Complex (Sanctum)',
    tariff: '₹1,100 - ₹2,800 / night',
    distance: '0.1 km from Holy Cave Sanctum',
    rating: 4.6,
    amenities: ['Warm Bedding', 'Electric Blankets', 'Hot Water', 'Direct Sanctum Access'],
    inventoryNote: 'Strictly allocated for senior citizens and pre-booked yatris.',
    officialLink: 'https://www.maavaishnodevi.org',
  },
  {
    id: 'smvdsb-ardhkuwari',
    name: 'Ardhkuwari Rest House (SMVDSB)',
    type: 'Shrine Board',
    location: 'Garbhjoon Temple Compound (Mid-Trek)',
    tariff: '₹600 - ₹1,400 / night',
    distance: '6 km from Katra | 6.5 km to Bhawan',
    rating: 4.2,
    amenities: ['Dormitory Beds', 'Blanket Service', 'Free Luggage Room', 'Bhojanalaya'],
    inventoryNote: 'Ideal for resting during long Garbhjoon darshan token waits.',
    officialLink: 'https://www.maavaishnodevi.org',
  },
  {
    id: 'hotel-the-white',
    name: 'The White Hotel Katra',
    type: 'Luxury / Star',
    location: 'Railway Road, Katra',
    tariff: '₹4,500 - ₹8,500 / night',
    distance: '1 km from Railway Station | 2.5 km to Banganga',
    rating: 4.7,
    amenities: ['5-Star Luxury', 'Pure Vegetarian Restaurant', 'Helipad Shuttle', 'Spa & Wellness'],
    inventoryNote: 'Premium stay with private panoramic Trikuta mountain view.',
    officialLink: null,
  },
  {
    id: 'hotel-hari-niwas',
    name: 'Hotel Shree Hari Niwas',
    type: 'Budget',
    location: 'Jammu Road, Katra',
    tariff: '₹1,200 - ₹2,200 / night',
    distance: '0.5 km from Bus Stand | 2 km to Banganga',
    rating: 4.1,
    amenities: ['Free WiFi', 'AC Rooms', 'Room Service', 'Banganga Drop Assistance'],
    inventoryNote: 'Devotee-friendly family budget accommodation.',
    officialLink: null,
  },
];

const CATEGORIES = ['All', 'Shrine Board', 'Budget', 'Luxury / Star'];

/**
 * AccommodationView for Yatra AI Web.
 * Visual parity with Android AccommodationScreen.
 */
export default function AccommodationView({ onReturnToAssistant, onBookAccommodation }) {
  const [accommodations, setAccommodations] = useState(CURATED_ACCOMMODATIONS);
  const [selectedCat, setSelectedCat] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAccommodations();
  }, []);

  const loadAccommodations = async () => {
    setLoading(true);
    try {
      const data = await getAccommodation({});
      if (data && data.hotels && Array.isArray(data.hotels) && data.hotels.length > 0) {
        // Merge or augment
        const mapped = data.hotels.map((h, i) => ({
          id: h.id || `api-hotel-${i}`,
          name: h.name,
          type: h.category || 'Standard',
          location: h.location || h.address || 'Katra',
          tariff: h.price_per_night ? `₹${h.price_per_night} / night` : 'Check Tariff',
          distance: h.distance || 'Katra area',
          rating: h.rating || 4.2,
          amenities: Array.isArray(h.amenities) ? h.amenities : ['Verified Stay', 'Hot Water'],
          inventoryNote: h.inventoryNote || 'Verified Katra accommodation.',
          officialLink: h.official_website || null,
        }));
        setAccommodations([...CURATED_ACCOMMODATIONS, ...mapped.slice(0, 10)]);
      }
    } catch {
      // Keep curated list
    } finally {
      setLoading(false);
    }
  };

  const filtered = accommodations.filter((item) => {
    const matchesCat = selectedCat === 'All' || item.type === selectedCat;
    const matchesSearch =
      (item.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.location || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div
      data-testid="accommodation-view"
      style={{
        maxWidth: '1000px',
        margin: '0 auto',
        width: '100%',
        padding: '1.25rem 1rem 3rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}
    >
      {/* Top Return Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          type="button"
          onClick={onReturnToAssistant}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'var(--surface-white, #FFFCF9)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '999px',
            padding: '6px 14px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: 'var(--royal-plum, #54152D)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <ArrowLeft size={14} />
          <span>Return to Yatra AI Companion</span>
        </button>
        <button
          type="button"
          onClick={loadAccommodations}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'transparent',
            border: 'none',
            fontSize: '0.78rem',
            color: 'var(--champagne-taupe, #A3826C)',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Screen Title Banner */}
      <div>
        <h1
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 'clamp(1.35rem, 2.5vw, 1.75rem)',
            fontWeight: 800,
            color: 'var(--royal-plum, #54152D)',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Building2 size={24} color="var(--royal-plum, #54152D)" />
          <span>Shrine Board Bhawans &amp; Accommodation</span>
        </h1>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary, #796D69)' }}>
          Verified shrine complexes at Katra, Ardhkuwari, and Holy Bhawan, alongside trusted devotee hotels.
        </p>
      </div>

      {/* Search & Category Filter Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--surface-white, #FFFCF9)',
            border: '1px solid var(--border-default, #E9DED6)',
            borderRadius: '12px',
            padding: '8px 14px',
          }}
        >
          <Search size={16} color="var(--text-secondary, #796D69)" />
          <input
            type="text"
            placeholder="Search bhawans, rest houses, hotels by name or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              border: 'none',
              background: 'transparent',
              outline: 'none',
              width: '100%',
              fontSize: '0.85rem',
              color: 'var(--text-primary, #30272A)',
            }}
          />
        </div>

        {/* Category Filter Pills */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          {CATEGORIES.map((cat) => {
            const isActive = selectedCat === cat;
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCat(cat)}
                style={{
                  background: isActive ? 'var(--royal-plum, #54152D)' : 'var(--surface-white, #FFFCF9)',
                  border: `1px solid ${isActive ? 'var(--royal-plum, #54152D)' : 'var(--border-default, #E9DED6)'}`,
                  color: isActive ? '#FFFFFF' : 'var(--text-primary, #30272A)',
                  padding: '5px 14px',
                  borderRadius: '999px',
                  fontSize: '0.78rem',
                  fontWeight: isActive ? 700 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease',
                }}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Accommodation Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
          gap: '14px',
        }}
      >
        {filtered.map((item) => (
          <div
            key={item.id}
            style={{
              background: 'var(--surface-white, #FFFCF9)',
              border: '1px solid var(--border-default, #E9DED6)',
              borderRadius: '14px',
              padding: '1.15rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '10px',
              boxShadow: '0 2px 8px rgba(84, 21, 45, 0.03)',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span
                  style={{
                    background: item.type === 'Shrine Board' ? 'var(--soft-plum-surface, #F0E3E7)' : 'var(--secondary-bg, #F2EAE4)',
                    color: item.type === 'Shrine Board' ? 'var(--royal-plum, #54152D)' : 'var(--text-secondary, #796D69)',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '6px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <ShieldCheck size={11} />
                  <span>{item.type}</span>
                </span>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--royal-plum, #54152D)' }}>
                  {item.tariff}
                </span>
              </div>

              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--royal-plum, #54152D)', marginBottom: '4px' }}>
                {item.name}
              </h3>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.76rem', color: 'var(--text-secondary, #796D69)', marginBottom: '8px' }}>
                <MapPin size={12} style={{ flexShrink: 0 }} />
                <span>{item.location}</span>
              </div>

              <p style={{ fontSize: '0.76rem', color: 'var(--champagne-taupe, #A3826C)', fontWeight: 600, marginBottom: '8px' }}>
                📍 {item.distance}
              </p>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '10px' }}>
                {item.amenities.map((am, i) => (
                  <span
                    key={i}
                    style={{
                      background: 'var(--secondary-bg, #F2EAE4)',
                      padding: '2px 7px',
                      borderRadius: '5px',
                      fontSize: '0.7rem',
                      color: 'var(--text-primary, #30272A)',
                    }}
                  >
                    {am}
                  </span>
                ))}
              </div>

              {item.inventoryNote && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary, #796D69)', fontStyle: 'italic', background: 'var(--warm-ivory, #F7F1EB)', padding: '6px 8px', borderRadius: '6px' }}>
                  ℹ️ {item.inventoryNote}
                </div>
              )}
            </div>

            <div style={{ borderTop: '1px solid var(--border-subtle, #F0E8E2)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              {item.officialLink ? (
                <a
                  href={item.officialLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    color: 'var(--royal-plum, #54152D)',
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Globe size={13} />
                  <span>Shrine Portal</span>
                </a>
              ) : (
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #796D69)' }}>Direct Booking</span>
              )}
              {onBookAccommodation && (
                <button
                  type="button"
                  onClick={() => onBookAccommodation(item)}
                  style={{
                    background: 'var(--royal-plum, #54152D)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '5px 12px',
                    fontSize: '0.76rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Plan in Yatra
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

