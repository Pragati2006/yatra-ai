import React, { useState } from 'react';
import { Landmark, Check, Plus, MapPin, Clock, Ticket, BookOpen, Car, Navigation, Globe, MessageSquare, Camera, ExternalLink, X, Maximize2 } from 'lucide-react';

const TRAVEL_NOTES = {
  'On the trek route': 'Trek on foot; battery car, pony & ropeway available along the route.',
  'Nearby temple': 'Short local taxi or auto-rickshaw ride from Katra town (10–30 mins).',
  'Nature': 'Half/full-day taxi excursion from Katra with scenic valley views.',
  'Hill station': 'Scenic mountain excursion by taxi from Katra/Jammu (~2.5–3 hrs).',
  'Hill station / adventure': 'Full-day mountain excursion from Katra/Jammu (~2.5–3 hrs).',
  'Nature / heritage': 'Half-day taxi excursion from Jammu or Katra.',
  'Jammu city': 'Direct road route from Katra to Jammu city (~1–1.5 hrs).',
  'Kashmir': 'Northern valley excursion accessible via NH-44 or flight from Jammu.',
  'Pilgrimage Base': 'Centrally located base town with registration counters and bazaars.',
};

export default function SightseeingCard({ place, isSelected, onToggleSelect, onExplorePlace = null }) {
  const [showDetails, setShowDetails] = useState(false);
  const [showLightbox, setShowLightbox] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  if (!place) return null;

  const cardId = place.name ? place.name.toLowerCase().replace(/[^a-z0-9]+/g, '-') : 'destination';
  const travelRequirement = TRAVEL_NOTES[place.category] || null;
  const isReligious = place.category_type === 'religious_site' || (!place.category_type && !['Nature', 'Hill station', 'Hill station / adventure', 'Kashmir', 'nature_destination', 'historical_site', 'tourist_attraction', 'trekking_destination'].includes(place.category));

  // Resolve primary image URL: prefers verified external HTTPS image_url, then local image, then gallery first item
  const gallery = place.image_gallery || [];
  const primaryImage = place.image_url
    ? place.image_url
    : place.image
      ? (place.image.startsWith('http') ? place.image : '/' + place.image)
      : (gallery[0]?.thumbnail_url || gallery[0]?.image_url || null);
  const primaryPhotoMeta = gallery[0] || null;

  return (
    <div
      data-testid={`place-card-${cardId}`}
      className="card card-hover"
      style={{
        border: isSelected ? '2px solid var(--gold-primary)' : '1px solid var(--gold-border)',
        background: isSelected ? '#FFFDF7' : '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '14px',
        position: 'relative',
        borderRadius: '16px',
        boxShadow: isSelected
          ? '0 6px 20px rgba(184, 134, 11, 0.16)'
          : '0 4px 12px rgba(61, 8, 16, 0.04)',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Top Image & Selection Indicator */}
      <div
        style={{
          position: 'relative',
          height: '150px',
          borderRadius: '12px',
          overflow: 'hidden',
          marginBottom: '12px',
          cursor: primaryImage && !imageFailed ? 'pointer' : 'default',
        }}
        onClick={() => primaryImage && !imageFailed && setShowLightbox(true)}
      >
        {primaryImage && !imageFailed ? (
          <img
            src={primaryImage}
            alt={place.name}
            loading="lazy"
            onError={() => setImageFailed(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div
            style={{
              display: 'flex',
              width: '100%',
              height: '100%',
              background: 'linear-gradient(135deg, #58111A, #3D0810)',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#E5D2AD',
            }}
          >
            <Landmark size={36} color="#E5D2AD" />
          </div>
        )}

        {/* Gallery count indicator badge */}
        {gallery.length > 1 && !imageFailed && (
          <div
            style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              background: 'rgba(0, 0, 0, 0.65)',
              color: '#F4E5BE',
              borderRadius: '10px',
              padding: '2px 8px',
              fontSize: '0.68rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              backdropFilter: 'blur(3px)',
            }}
          >
            <Camera size={11} color="#D4AF37" />
            <span>{gallery.length} photos</span>
          </div>
        )}

        {/* Selection Toggle Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect && onToggleSelect();
          }}
          data-testid={`toggle-place-${cardId}`}
          onClick={onToggleSelect}
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            background: isSelected ? 'var(--burgundy)' : 'rgba(255, 255, 255, 0.94)',
            color: isSelected ? '#FFFFFF' : 'var(--burgundy)',
            border: isSelected ? '1.5px solid var(--gold-primary)' : '1.5px solid var(--gold-border)',
            borderRadius: '999px',
            padding: '5px 12px',
            fontSize: '0.76rem',
            fontWeight: 800,
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            transition: 'all 0.15s ease',
          }}
        >
          {isSelected ? (
            <>
              <Check size={12} /> Selected
            </>
          ) : (
            <>
              <Plus size={12} /> Add Place
            </>
          )}
        </button>

        {/* Category Pill */}
        <span
          className="pill"
          style={{
            position: 'absolute',
            bottom: '8px',
            left: '8px',
            background: 'rgba(45, 5, 11, 0.88)',
            color: '#F5ECDA',
            border: '1px solid var(--gold-border)',
            fontSize: '0.7rem',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '8px',
          }}
        >
          {place.category}
        </span>

        {/* Region & District Tag if available */}
        {(place.region || place.district) && (
          <span
            style={{
              position: 'absolute',
              bottom: '8px',
              right: '8px',
              background: 'rgba(255, 255, 255, 0.9)',
              color: 'var(--burgundy)',
              border: '1px solid var(--gold-border)',
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '6px',
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
              <MapPin size={11} /> {place.district && place.region ? `${place.district}, ${place.region}` : (place.district || place.region)}
            </span>
          </span>
        )}
      </div>

      {/* Place Information Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '8px',
          marginBottom: '4px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-serif)',
            fontWeight: 800,
            fontSize: '1.05rem',
            color: 'var(--burgundy)',
            lineHeight: 1.25,
            margin: 0,
          }}>
            {place.name}
          </h3>
          {isSelected && (
            <span style={{
              background: '#F0FDF4',
              color: '#166534',
              border: '1px solid #BBF7D0',
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '6px',
              whiteSpace: 'nowrap',
            }}>
              In Plan
            </span>
          )}
        </div>

        {/* Distance, Altitude & Timings */}
        <div style={{ fontSize: '0.78rem', color: 'var(--gold-primary)', fontWeight: 600, margin: '2px 0 6px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} /> {place.distance || (place.district ? `District ${place.district}` : (place.region ? `${place.region} Region` : 'Jammu & Kashmir'))}
          </span>
          {place.altitude_m && <span>• ~{place.altitude_m} m</span>}
          {isReligious ? (
            (place.darshan_timings || place.timings) && <span>• Darshan: {place.darshan_timings || place.timings}</span>
          ) : (
            (place.visiting_hours || place.timings) && <span>• Hours: {place.visiting_hours || place.timings}</span>
          )}
        </div>

        {/* Entry Fee (if available & not strictly free) */}
        {place.entry_fee && place.entry_fee !== 'Free' && (
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Ticket size={12} /> <b>Fee:</b> {place.entry_fee}
          </div>
        )}

        {/* Description */}
        <div style={{ fontSize: '0.82rem', color: 'var(--text-dark)', lineHeight: 1.45, flex: 1 }}>
          {showDetails ? place.description : (
            place.description && place.description.length > 110
              ? place.description.slice(0, 105) + '...'
              : place.description
          )}
        </div>

        {/* Extended Historical Background & Route Details */}
        {showDetails && (
          <div
            data-testid={`place-details-${cardId}`}
            style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}
          >
            {place.historical_background && (
              <div style={{
                background: '#FAF6EE',
                border: '1px dashed var(--gold-border)',
                borderRadius: '8px',
                padding: '8px 10px',
                fontSize: '0.76rem',
                color: 'var(--text-dark)',
                lineHeight: 1.45,
              }}>
                <b style={{ color: 'var(--burgundy)', display: 'inline-flex', alignItems: 'center', gap: '4px', marginRight: '4px' }}>
                  <BookOpen size={12} /> {isReligious ? 'Sacred Context:' : 'Heritage Context:'}
                </b> {place.historical_background}
              </div>
            )}

            {!isReligious && place.best_time_to_visit && (
              <div style={{
                background: '#F0FDF4',
                border: '1px solid #BBF7D0',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                color: '#166534',
                lineHeight: 1.4,
              }}>
                <b>Best Time to Visit:</b> {place.best_time_to_visit}
              </div>
            )}

            {!isReligious && place.accessibility && (
              <div style={{
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                color: '#334155',
                lineHeight: 1.4,
              }}>
                <b>Accessibility:</b> {place.accessibility}
              </div>
            )}

            {!isReligious && place.seasonal_restrictions && (
              <div style={{
                background: '#FFFBEB',
                border: '1px solid #FDE68A',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                color: '#92400E',
                lineHeight: 1.4,
              }}>
                <b>Seasonal Advisory:</b> {place.seasonal_restrictions}
              </div>
            )}

            {travelRequirement && (
              <div style={{
                background: '#F4F7FB',
                border: '1px solid #D6E4F0',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                color: '#1E3A8A',
                lineHeight: 1.4,
              }}>
                <b style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginRight: '4px' }}>
                  <Car size={12} /> Travel & Access:
                </b> {travelRequirement}
              </div>
            )}

            {place.location_route && (
              <div style={{
                background: '#FDFBF7',
                border: '1px solid var(--gold-border)',
                borderRadius: '8px',
                padding: '6px 10px',
                fontSize: '0.74rem',
                color: 'var(--text-muted)',
                lineHeight: 1.4,
              }}>
                <b style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginRight: '4px' }}>
                  <Navigation size={12} /> Route Guide:
                </b> {place.location_route}
              </div>
            )}

            {place.latitude && place.longitude && (
              <div style={{
                fontSize: '0.71rem',
                color: '#6B7280',
                display: 'flex',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '6px',
                padding: '2px 4px',
              }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <Globe size={11} /> <b>GPS:</b> {place.latitude.toFixed(4)}°N, {place.longitude.toFixed(4)}°E
                </span>
                {place.district && <span>• <b>District:</b> {place.district}</span>}
              </div>
            )}
            {primaryPhotoMeta?.attribution && (
              <div style={{
                fontSize: '0.69rem',
                color: '#786C6C',
                borderTop: '1px dashed #E5D2AD',
                paddingTop: '6px',
                marginTop: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <span title={primaryPhotoMeta.attribution}>
                  📷 {primaryPhotoMeta.attribution}
                </span>
                {primaryPhotoMeta.source_page_url && (
                  <a
                    href={primaryPhotoMeta.source_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#8A5D00', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '2px' }}
                  >
                    Commons <ExternalLink size={9} />
                  </a>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Card Action Footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderTop: '1px solid var(--border-subtle, #E4D5B7)',
        marginTop: '10px',
        paddingTop: '8px',
      }}>
        <button
          type="button"
          data-testid={`toggle-details-${cardId}`}
          onClick={() => setShowDetails(!showDetails)}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '0.76rem',
            color: 'var(--burgundy)',
            fontWeight: 700,
            cursor: 'pointer',
            padding: 0,
          }}
        >
          {showDetails ? 'Hide Details ▲' : 'Read Heritage & Route ▼'}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onExplorePlace && (
            <button
              type="button"
              onClick={() => onExplorePlace(place.name)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '0.74rem',
                color: 'var(--burgundy)',
                fontWeight: 600,
                cursor: 'pointer',
                padding: '2px 4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <MessageSquare size={12} /> Ask AI
            </button>
          )}
          {place.video_search && (
            <a
              href={place.video_search}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: '0.75rem',
                color: 'var(--gold-primary)',
                textDecoration: 'none',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>▶ Watch Guide</span>
            </a>
          )}
        </div>
      </div>

      {/* Lightbox Modal */}
      {showLightbox && primaryImage && (
        <div
          data-testid={`place-lightbox-${cardId}`}
          onClick={(e) => {
            e.stopPropagation();
            setShowLightbox(false);
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(20, 10, 12, 0.88)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'relative',
              maxWidth: '850px',
              width: '100%',
              maxHeight: '90vh',
              background: '#FFFFFF',
              borderRadius: '16px',
              overflow: 'hidden',
              boxShadow: '0 12px 40px rgba(0, 0, 0, 0.5)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <button
              type="button"
              data-testid="lightbox-close-btn"
              onClick={() => setShowLightbox(false)}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'rgba(0, 0, 0, 0.65)',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}
            >
              <X size={18} />
            </button>

            <div
              style={{
                width: '100%',
                maxHeight: '68vh',
                background: '#1A0E10',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
              }}
            >
              <img
                src={primaryImage}
                alt={place.name}
                style={{
                  maxWidth: '100%',
                  maxHeight: '68vh',
                  objectFit: 'contain',
                }}
              />
            </div>

            <div
              style={{
                padding: '14px 18px',
                background: '#FAF6EE',
                borderTop: '1px solid #E5D2AD',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px',
              }}
            >
              <div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '0.94rem', color: 'var(--burgundy, #58111A)', fontWeight: 700 }}>
                  {place.name}
                </h4>
                <div style={{ fontSize: '0.76rem', color: '#6A5C5C' }}>
                  {primaryPhotoMeta?.attribution || 'Verified Tourism Photograph'}
                </div>
              </div>

              {primaryPhotoMeta?.source_page_url && (
                <a
                  href={primaryPhotoMeta.source_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.76rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    textDecoration: 'none',
                  }}
                >
                  <span>Wikimedia Commons</span>
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
