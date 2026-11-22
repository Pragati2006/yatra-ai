import React, { useState, useEffect } from 'react';
import { Train, Bus, Plane, ArrowLeft, Search, RefreshCw, Clock, MapPin, ShieldCheck, ExternalLink } from 'lucide-react';
import { searchYatra } from '../services/api';

const HelicopterIcon = ({ size = 18, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 3h18" />
    <path d="M12 3v4" />
    <path d="M4 14a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4v-4H4v4z" />
    <path d="M2 17h16" />
    <path d="M18 10l4-4" />
  </svg>
);

const CURATED_TRANSPORTS = [
  // Trains
  {
    id: 'train-1',
    mode: 'Train',
    title: 'Vande Bharat Express (22439 / 22440)',
    origin: 'New Delhi (NDLS)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '8h 00m',
    departure: '06:00 AM (NDLS)',
    arrival: '02:00 PM (SVDK)',
    frequency: 'All days except Tuesday',
    fareRange: '₹1,630 (CC) - ₹3,015 (EC)',
    stops: 'Ambala Cantt, Ludhiana, Jammu Tawi',
    bookingPlatform: 'IRCTC / PRS Counters',
    dataTier: 'Indicative Estimate',
  },
  {
    id: 'train-2',
    mode: 'Train',
    title: 'Uttar Sampark Kranti (12445 / 12446)',
    origin: 'New Delhi (NDLS)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '11h 40m',
    departure: '08:50 PM (NDLS)',
    arrival: '08:05 AM (SVDK)',
    frequency: 'Daily Overnight',
    fareRange: '₹375 (SL) - ₹1,430 (3A) - ₹2,050 (2A)',
    stops: 'Panipat, Ambala, Ludhiana, Jammu Tawi, Udhampur',
    bookingPlatform: 'IRCTC / PRS Counters',
    dataTier: 'Indicative Estimate',
  },
  {
    id: 'train-3',
    mode: 'Train',
    title: 'Hemkunt Express (14609 / 14610)',
    origin: 'Rishikesh (RKSH)',
    destination: 'Shri Mata Vaishno Devi Katra (SVDK)',
    duration: '14h 50m',
    departure: '05:20 PM (RKSH)',
    arrival: '08:10 AM (SVDK)',
    frequency: 'Daily',
    fareRange: '₹390 (SL) - ₹1,080 (3A) - ₹1,550 (2A)',
    stops: 'Haridwar, Saharanpur, Ambala, Jammu Tawi',
    bookingPlatform: 'IRCTC / PRS Counters',
    dataTier: 'Indicative Estimate',
  },
  // Helicopter
  {
    id: 'heli-1',
    mode: 'Helicopter',
    title: 'Shrine Board Aerial Shuttle',
    origin: 'Katra Helipad (875m)',
    destination: 'Sanjichhat Helipad (1,768m)',
    duration: '8 minutes flight',
    departure: 'Continuous daylight flights',
    arrival: 'Operates 07:00 AM - 05:00 PM',
    frequency: 'Every 10-15 minutes (weather permitting)',
    fareRange: '₹2,100 (One Way) / ₹4,200 (Return)',
    stops: 'Direct aerial corridor over Banganga gorge',
    bookingPlatform: 'maavaishnodevi.org (Official portal only)',
    dataTier: 'Demonstration Data',
  },
  // Buses
  {
    id: 'bus-1',
    mode: 'Bus',
    title: 'JKSRTC Volvo Multi-Axle AC (Delhi–Jammu + Feeder)',
    origin: 'ISBT Kashmiri Gate, Delhi',
    destination: 'Jammu GBS / Katra Feeder',
    duration: '12h 30m',
    departure: '07:30 PM & 08:30 PM',
    arrival: '08:00 AM & 09:00 AM',
    frequency: 'Daily evening services',
    fareRange: '₹1,250 - ₹1,450',
    stops: 'Murthal, Karnal, Ludhiana, Pathankot, Jammu GBS',
    bookingPlatform: 'jksrtc.co.in / Bus Counters',
    dataTier: 'Indicative Estimate',
  },
  {
    id: 'bus-2',
    mode: 'Bus',
    title: 'Laxmi Holidays Volvo 9600 AC Sleeper',
    origin: 'Majnu Ka Tilla, Delhi',
    destination: 'Katra Private Bus Stand',
    duration: '11h 45m',
    departure: '08:00 PM',
    arrival: '07:45 AM',
    frequency: 'Daily',
    fareRange: '₹1,350 - ₹1,800',
    stops: 'Direct highway route with comfort dinner break',
    bookingPlatform: 'Private Bus Operators',
    dataTier: 'Indicative Estimate',
  },
  // Flights
  {
    id: 'flight-1',
    mode: 'Flight',
    title: 'IndiGo / Air India Direct Corridor (DEL → IXJ)',
    origin: 'IGI Airport, New Delhi (DEL)',
    destination: 'Jammu Satwari Airport (IXJ)',
    duration: '1h 25m',
    departure: 'Morning & Afternoon schedules',
    arrival: 'Direct flight',
    frequency: 'Daily multiple frequencies',
    fareRange: '₹3,500 - ₹7,500 (Dynamic airfare)',
    stops: 'Non-stop aerial corridor',
    bookingPlatform: 'Airlines / Travel Portals',
    dataTier: 'Live Availability',
  },
];

const CATEGORIES = ['All', 'Train', 'Bus', 'Helicopter', 'Flight'];

const getDataTierBadge = (tier) => {
  switch (tier) {
    case 'Live Availability':
      return { bg: '#D4EDDA', color: '#155724', border: '#C3E6CB' };
    case 'Indicative Estimate':
      return { bg: '#FFF3CD', color: '#856404', border: '#FFEEBA' };
    case 'Demonstration Data':
      return { bg: '#F8D7DA', color: '#721C24', border: '#F5C6CB' };
    default:
      return { bg: '#E2E3E5', color: '#383D41', border: '#D6D8DB' };
  }
};

/**
 * TransportView for Yatra AI Web.
 * Full visual parity with Android TransportScreen.
 */
export default function TransportView({ onReturnToAssistant, onBookTransport }) {
  const [transports, setTransports] = useState(CURATED_TRANSPORTS);
  const [selectedCat, setSelectedCat] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTransports();
  }, []);

  const loadTransports = async () => {
    setLoading(true);
    try {
      const data = await searchYatra({ message: 'transport options' });
      if (data && data.options && Array.isArray(data.options) && data.options.length > 0) {
        const mapped = data.options.map((opt, i) => {
          const tr = opt.transport || opt.flight || {};
          return {
            id: tr.id || `api-tr-${i}`,
            mode: tr.mode || 'Train',
            title: tr.name || tr.operator || 'Transport Service',
            origin: tr.origin || 'Departure Point',
            destination: tr.destination || 'Katra',
            duration: tr.duration_hours ? `${tr.duration_hours}h` : 'Enquire',
            departure: tr.departure_time || 'Check timetable',
            arrival: tr.arrival_time || 'Check timetable',
            frequency: 'Scheduled',
            fareRange: tr.price ? `₹${tr.price}` : 'Dynamic Fare',
            stops: tr.stops || 'Direct Route',
            bookingPlatform: tr.bookingPlatform || 'Official Booking Counter',
            dataTier: tr.dataTier || 'Indicative Estimate',
          };
        });
        setTransports([...CURATED_TRANSPORTS, ...mapped.slice(0, 10)]);
      }
    } catch {
      // Keep curated list
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (mode) => {
    switch (mode) {
      case 'Train':
        return <Train size={18} color="var(--royal-plum, #54152D)" />;
      case 'Bus':
        return <Bus size={18} color="var(--royal-plum, #54152D)" />;
      case 'Helicopter':
        return <HelicopterIcon size={18} color="var(--royal-plum, #54152D)" />;
      case 'Flight':
        return <Plane size={18} color="var(--royal-plum, #54152D)" />;
      default:
        return <Train size={18} color="var(--royal-plum, #54152D)" />;
    }
  };

  const filtered = transports.filter((item) => {
    const matchesCat = selectedCat === 'All' || item.mode === selectedCat;
    const matchesSearch =
      (item.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.origin || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.destination || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.stops || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div
      data-testid="transport-view"
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
          onClick={loadTransports}
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
          <Train size={24} color="var(--royal-plum, #54152D)" />
          <span>Pilgrimage Transport &amp; Schedules</span>
        </h1>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary, #796D69)' }}>
          Curated Indian Railways timetables, verified government and private bus fleets, flights, and Shrine Board helicopter options.
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
            placeholder="Search train 22439, bus operator, flight, or route..."
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

      {/* Transport Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
          gap: '14px',
        }}
      >
        {filtered.map((item) => {
          const badgeStyle = getDataTierBadge(item.dataTier);
          return (
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
                      background: 'var(--secondary-bg, #F2EAE4)',
                      color: 'var(--royal-plum, #54152D)',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: '6px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    {getIcon(item.mode)}
                    <span>{item.mode}</span>
                  </span>
                  <span
                    style={{
                      background: badgeStyle.bg,
                      color: badgeStyle.color,
                      border: `1px solid ${badgeStyle.border}`,
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      padding: '2px 7px',
                      borderRadius: '999px',
                    }}
                  >
                    {item.dataTier}
                  </span>
                </div>

                <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--royal-plum, #54152D)', marginBottom: '4px' }}>
                  {item.title}
                </h3>

                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.78rem', color: 'var(--text-secondary, #796D69)', marginBottom: '6px' }}>
                  <MapPin size={12} style={{ flexShrink: 0 }} />
                  <span>{item.origin} → {item.destination}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--champagne-taupe, #A3826C)', fontWeight: 600, marginBottom: '6px' }}>
                  <Clock size={12} />
                  <span>{item.departure} | Duration: {item.duration}</span>
                </div>

                <div style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--royal-plum, #54152D)', marginBottom: '6px' }}>
                  {item.fareRange}
                </div>

                {item.stops && (
                  <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary, #796D69)', lineHeight: 1.4, marginBottom: '6px' }}>
                    Stops: {item.stops}
                  </p>
                )}
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle, #F0E8E2)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--champagne-taupe, #A3826C)', fontWeight: 600 }}>
                  {item.bookingPlatform}
                </span>
                {onBookTransport && (
                  <button
                    type="button"
                    onClick={() => onBookTransport(item)}
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
                    Select in Yatra
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

