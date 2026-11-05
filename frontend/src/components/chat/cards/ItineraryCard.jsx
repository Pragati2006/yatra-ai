import React, { useState } from 'react';

/**
 * Visual Day-by-Day Itinerary Card inside the AI Chat Stream.
 */
export default function ItineraryCard({ itinerary }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!itinerary) return null;

  const days = itinerary.days || (Array.isArray(itinerary) ? itinerary : []);
  if (!days || days.length === 0) return null;

  const totalDays = days.length;

  return (
    <div
      style={{
        marginTop: '0.75rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '12px 14px',
        boxShadow: '0 2px 8px rgba(88, 17, 26, 0.04)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded((prev) => !prev)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.1rem' }}>🗓️</span>
          <div>
            <div
              style={{
                fontFamily: 'var(--font-serif, Cinzel, serif)',
                fontWeight: 700,
                fontSize: '0.86rem',
                color: 'var(--burgundy, #58111A)',
              }}
            >
              Sacred {totalDays}-Day Pilgrimage Itinerary
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #6B5C5C)' }}>
              {isExpanded ? 'Click to collapse schedule' : 'Click to view day-by-day timeline'}
            </div>
          </div>
        </div>
        <button
          type="button"
          style={{
            background: 'var(--bg-subtle, #F8F4EC)',
            border: '1px solid var(--gold-border, #E5D2AD)',
            borderRadius: '999px',
            padding: '3px 10px',
            fontSize: '0.74rem',
            color: 'var(--burgundy)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {isExpanded ? '▲ Hide' : '▼ View Timeline'}
        </button>
      </div>

      {isExpanded && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {days.map((day, idx) => {
            const dayNum = day.day_number || day.day || idx + 1;
            const title = day.title || day.theme || `Day ${dayNum}`;
            const activities = day.activities || day.schedule || [];

            return (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-subtle, #F8F4EC)',
                  border: '1px solid #EBE1D0',
                  borderRadius: '8px',
                  padding: '10px 12px',
                }}
              >
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    color: 'var(--burgundy, #58111A)',
                    marginBottom: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span style={{ background: 'var(--burgundy)', color: '#FFF', borderRadius: '4px', padding: '1px 6px', fontSize: '0.7rem' }}>
                    Day {dayNum}
                  </span>
                  <span>{title}</span>
                </div>

                {activities.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.78rem', color: 'var(--text-dark)', lineHeight: 1.5 }}>
                    {activities.map((act, aIdx) => {
                      const timeStr = typeof act === 'object' ? (act.time || act.slot || '') : '';
                      const actText = typeof act === 'object' ? (act.activity || act.description || JSON.stringify(act)) : act;
                      return (
                        <li key={aIdx} style={{ marginBottom: '3px' }}>
                          {timeStr && <b style={{ color: 'var(--gold-primary, #B8860B)' }}>{timeStr}: </b>}
                          <span>{actText}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {day.description || 'Devotional trek, darshan, and rest schedule.'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
