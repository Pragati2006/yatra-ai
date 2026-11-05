import React from 'react';

/**
 * Structured Weather Summary Card for AI Chat stream.
 */
export default function WeatherCard({ weatherData }) {
  if (!weatherData) return null;

  const loc = weatherData.location || 'Katra (Mata Vaishno Devi Base)';
  const temp = weatherData.temperature || weatherData.temp || '18°C';
  const condition = weatherData.condition || weatherData.weather || 'Pleasant';
  const forecast = weatherData.forecast || weatherData.summary || 'Comfortable conditions for trekking to Bhawan.';
  const advisory = weatherData.advisory || null;

  return (
    <div
      style={{
        marginTop: '0.65rem',
        background: 'linear-gradient(135deg, #F0F7FF 0%, #E8F1FC 100%)',
        border: '1px solid #B8D5E5',
        borderRadius: '12px',
        padding: '10px 14px',
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.04)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '1.2rem' }}>⛅</span>
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: '#1B4965' }}>
            Live Weather: {loc}
          </span>
        </div>
        <span style={{ fontWeight: 800, fontSize: '1.05rem', color: '#0F3057' }}>
          {temp}
        </span>
      </div>

      <div style={{ fontSize: '0.8rem', color: '#2B4162', lineHeight: 1.4 }}>
        <b>Condition:</b> {condition} — {forecast}
      </div>

      {advisory && (
        <div style={{ marginTop: '4px', fontSize: '0.74rem', color: '#C0392B', fontWeight: 600 }}>
          ⚠️ Trek Advisory: {advisory}
        </div>
      )}
    </div>
  );
}
