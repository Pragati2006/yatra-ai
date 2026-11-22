import React, { useState, useEffect } from 'react';
import { CloudSun, Mountain, Wind, Droplets, Compass, RefreshCw, AlertTriangle, ArrowLeft } from 'lucide-react';
import { getWeather } from '../services/api';

const ELEVATION_ZONES = [
  {
    location: 'katra',
    locationName: 'Katra (Base Camp)',
    altitude: '875 m (2,870 ft)',
    condition: 'Partly Cloudy',
    temperature: 21,
    humidity: 55,
    windSpeed: 8,
    precipitationProb: 10,
    advisory: 'Pleasant daytime conditions. Standard walking shoes recommended for start of trek.',
    tempDrop: 'Baseline Temperature',
  },
  {
    location: 'ardhkuwari',
    locationName: 'Ardhkuwari (Mid-Trek)',
    altitude: '1,460 m (4,790 ft)',
    condition: 'Cool Breeze',
    temperature: 17,
    humidity: 62,
    windSpeed: 14,
    precipitationProb: 20,
    advisory: 'Noticeable drop in temperature (~4°C lower than Katra). Light windcheater advised.',
    tempDrop: '-4.0°C vs Katra Base',
  },
  {
    location: 'vaishno_devi_bhawan',
    locationName: 'Holy Cave Bhawan',
    altitude: '1,585 m (5,200 ft)',
    condition: 'Chilly & Overcast',
    temperature: 14,
    humidity: 68,
    windSpeed: 18,
    precipitationProb: 25,
    advisory: 'Brisk mountain winds. Warm jacket or woolen shawl required, especially during evening Aarti.',
    tempDrop: '-7.0°C vs Katra Base',
  },
  {
    location: 'bhairon_temple',
    locationName: 'Bhairon Ghati (Peak)',
    altitude: '2,012 m (6,600 ft)',
    condition: 'Cold & Windy',
    temperature: 10,
    humidity: 75,
    windSpeed: 24,
    precipitationProb: 35,
    advisory: 'High altitude chill. Heavy woollens and gloves recommended. Watch out for sudden fog patches.',
    tempDrop: '-11.0°C vs Katra Base',
  },
];

export default function WeatherView({ onReturnToAssistant }) {
  const [zones, setZones] = useState(ELEVATION_ZONES);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchLiveForecasts = async () => {
    setLoading(true);
    try {
      const updated = await Promise.all(
        ELEVATION_ZONES.map(async (zone) => {
          try {
            const data = await getWeather(zone.location);
            if (data && (data.temperature !== undefined || data.temp !== undefined)) {
              const tempVal = Math.round(data.temperature !== undefined ? data.temperature : parseFloat(data.temp));
              return {
                ...zone,
                temperature: isNaN(tempVal) ? zone.temperature : tempVal,
                condition: data.condition || data.weather || zone.condition,
                humidity: data.humidity || zone.humidity,
                windSpeed: data.wind_speed || data.windSpeed || zone.windSpeed,
                advisory: data.advisory || zone.advisory,
                isLive: !data.is_fallback,
              };
            }
          } catch {
            // Keep fallback
          }
          return zone;
        })
      );
      setZones(updated);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    } catch {
      // Keep existing zones
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveForecasts();
  }, []);

  return (
    <div data-testid="weather-view-screen" style={{ maxWidth: '1100px', margin: '0 auto', padding: '1.25rem 1rem', width: '100%' }}>
      {/* Navigation and Title Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          {onReturnToAssistant && (
            <button
              type="button"
              data-testid="weather-back-btn"
              onClick={onReturnToAssistant}
              className="btn btn-secondary"
              style={{ fontSize: '0.82rem', padding: '0.4rem 0.85rem', marginBottom: '0.5rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={14} /> Return to Yatra AI Companion
            </button>
          )}
          <h1 style={{ fontFamily: 'var(--font-serif, Cinzel, serif)', fontSize: '1.65rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: 0 }}>
            Vaishno Devi Multi-Altitude Weather
          </h1>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted, #6B5C5C)', marginTop: '4px', margin: 0 }}>
            Live meteorological forecasts and altitude advisories along the 13 km sacred yatra track from Katra to Bhairon Ghati.
          </p>
        </div>

        <button
          type="button"
          data-testid="weather-refresh-btn"
          onClick={fetchLiveForecasts}
          disabled={loading}
          style={{
            background: '#FFFFFF',
            border: '1.5px solid var(--gold-border, #E5D2AD)',
            borderRadius: '8px',
            padding: '6px 14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--burgundy, #58111A)',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Weather'}</span>
        </button>
      </div>

      {/* Elevation Zones Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          marginBottom: '1.75rem',
        }}
      >
        {zones.map((zone, idx) => (
          <div
            key={zone.location || idx}
            data-testid={`weather-zone-card-${zone.location}`}
            style={{
              background: '#FFFFFF',
              border: '1.5px solid var(--gold-border, #E5D2AD)',
              borderRadius: '14px',
              padding: '1.15rem',
              boxShadow: '0 2px 10px rgba(88, 17, 26, 0.04)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span
                  style={{
                    background: '#F5ECDA',
                    color: 'var(--burgundy, #58111A)',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Mountain size={11} /> {zone.altitude}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#166534', fontWeight: 600 }}>
                  {zone.tempDrop}
                </span>
              </div>

              <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--burgundy, #58111A)', margin: '0 0 4px 0' }}>
                {zone.locationName}
              </h2>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '8px 0' }}>
                <CloudSun size={28} color="#B8860B" />
                <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#1B4965' }}>
                  {zone.temperature}°C
                </span>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted, #6B5C5C)', fontWeight: 600 }}>
                  {zone.condition}
                </span>
              </div>

              <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: '#4A5568', margin: '6px 0 12px 0' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Droplets size={13} color="#2B6CB0" /> {zone.humidity}% Humidity
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Wind size={13} color="#4A5568" /> {zone.windSpeed} km/h Wind
                </span>
              </div>
            </div>

            <div
              style={{
                background: '#FFFDF9',
                borderTop: '1px solid #EBE1D0',
                paddingTop: '8px',
                marginTop: '4px',
                fontSize: '0.76rem',
                color: '#744210',
                lineHeight: 1.4,
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertTriangle size={12} color="#C05621" /> Trek Advisory:
              </div>
              {zone.advisory}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted, #6B5C5C)' }}>
        Data Source: High-Resolution Open-Meteo Mountain Meteorological API {lastUpdated ? `· Last checked ${lastUpdated}` : ''}
      </div>
    </div>
  );
}

