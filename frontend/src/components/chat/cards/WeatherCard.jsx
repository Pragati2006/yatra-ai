import React from 'react';
import { CloudSun, Mountain, AlertTriangle } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';
import { formatTimestamp } from '../provenance/provenanceUtils';

/**
 * Structured Weather Summary Card for AI Chat stream.
 * Displays elevation-aware weather conditions alongside honest source and freshness attribution.
 */
export default function WeatherCard({ weatherData }) {
  if (!weatherData) return null;

  const loc = weatherData.location || 'Katra (Mata Vaishno Devi Base)';
  const temp = weatherData.temperature || weatherData.temp || '18°C';
  const condition = weatherData.condition || weatherData.weather || 'Pleasant';
  const forecast = weatherData.forecast || weatherData.summary || 'Comfortable conditions for trekking to Bhawan.';
  const advisory = weatherData.advisory || null;

  // Provenance & Freshness attribution
  const isFallback = weatherData.is_fallback || weatherData.freshness_status === 'fallback' || weatherData.status === 'FALLBACK';
  const isCached = weatherData.is_cached || weatherData.freshness_status === 'cached';
  const freshness = isFallback ? 'fallback' : (isCached ? 'cached' : 'live');
  const sourceType = isFallback ? 'curated_data' : (isCached ? 'cached_api' : 'live_api');
  const provider = weatherData.provider || (isFallback ? 'Climatological Model' : 'Open-Meteo High-Resolution API');
  const formattedTime = formatTimestamp(weatherData.retrieval_timestamp || weatherData.timestamp);
  const elevation = weatherData.elevation_m ? `${weatherData.elevation_m}m` : (weatherData.elevation || null);

  return (
    <div
      data-testid="chat-weather-card"
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
          <CloudSun size={18} color="#1B4965" />
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: '#1B4965' }}>
            Weather: {loc}
          </span>
          {elevation && (
            <span
              style={{
                fontSize: '0.68rem',
                padding: '1px 5px',
                borderRadius: '4px',
                background: '#D9E8F5',
                color: '#1B4965',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              <Mountain size={11} /> {elevation}
            </span>
          )}
        </div>
        <span style={{ fontWeight: 800, fontSize: '1.05rem', color: '#0F3057' }}>
          {temp}
        </span>
      </div>

      <div style={{ fontSize: '0.8rem', color: '#2B4162', lineHeight: 1.4 }}>
        <b>Condition:</b> {condition} — {forecast}
      </div>

      {advisory && (
        <div style={{ marginTop: '4px', fontSize: '0.74rem', color: '#C0392B', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <AlertTriangle size={12} color="#C0392B" />
          <span>Trek Advisory: {advisory}</span>
        </div>
      )}

      {/* Provenance strip */}
      <div
        style={{
          marginTop: '8px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(184, 213, 229, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '4px',
          fontSize: '0.68rem',
          color: '#3A5A78',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FreshnessIndicator
            freshnessStatus={freshness}
            sourceType={sourceType}
            customText={isFallback ? 'Fallback Estimate' : (isCached ? 'Cached API' : 'Live API')}
          />
          <span>• {provider}</span>
        </div>
        {formattedTime && (
          <span>Updated: {formattedTime}</span>
        )}
      </div>
    </div>
  );
}
