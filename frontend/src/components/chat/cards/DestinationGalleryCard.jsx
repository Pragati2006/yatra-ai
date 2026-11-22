import React, { useState } from 'react';
import { Landmark, ExternalLink, Maximize2, X, Camera, Info } from 'lucide-react';

/**
 * DestinationGalleryCard
 * Renders verified photographs of tourist destinations in conversational chat turns.
 * Includes responsive gallery layout, lightbox magnification, author attribution, and license links.
 */
export default function DestinationGalleryCard({ destination, images = [], onExplorePlace = null }) {
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [failedImages, setFailedImages] = useState({});

  const gallery = images && images.length > 0 ? images : destination?.image_gallery || [];
  const destName = destination?.name || destination?.destination_name || 'Destinations & Sightseeing';

  if (!gallery || gallery.length === 0) {
    return null;
  }

  const handleImageError = (index) => {
    setFailedImages((prev) => ({ ...prev, [index]: true }));
  };

  return (
    <div
      data-testid="destination-gallery-card"
      style={{
        margin: '0.85rem 0 0.5rem 0',
        borderRadius: '14px',
        overflow: 'hidden',
        border: '1px solid var(--border-default, #E9DED6)',
        background: 'var(--surface-white, #FFFCF9)',
        boxShadow: '0 2px 10px rgba(84, 21, 45, 0.04)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          background: 'linear-gradient(135deg, var(--royal-plum, #54152D), var(--deep-plum, #3D1022))',
          color: '#FAF6EE',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Camera size={15} color="var(--soft-champagne, #D7C2B2)" />
          <span style={{ fontSize: '0.82rem', fontWeight: 700, letterSpacing: '0.02em', color: '#FAF6EE' }}>
            Verified Photographs: {destName}
          </span>
        </div>
        <span
          style={{
            fontSize: '0.72rem',
            background: 'rgba(215, 194, 178, 0.25)',
            color: '#FAF6EE',
            padding: '2px 8px',
            borderRadius: '12px',
            border: '1px solid rgba(215, 194, 178, 0.45)',
            fontWeight: 600,
          }}
        >
          {gallery.length} {gallery.length === 1 ? 'Photo' : 'Photos'}
        </span>
      </div>

      {/* Gallery Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: gallery.length === 1 ? '1fr' : gallery.length === 2 ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '8px',
          padding: '10px',
        }}
      >
        {gallery.slice(0, 3).map((item, idx) => {
          const isFailed = failedImages[idx];
          const imgUrl = item.thumbnail_url || item.image_url;

          return (
            <div
              key={idx}
              data-testid={`gallery-item-${idx}`}
              style={{
                position: 'relative',
                borderRadius: '10px',
                overflow: 'hidden',
                background: '#FFFFFF',
                border: '1px solid #EBE1CF',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
              }}
            >
              {/* Image Container */}
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: gallery.length === 1 ? '240px' : '160px',
                  background: '#3D0810',
                  cursor: isFailed ? 'default' : 'pointer',
                  overflow: 'hidden',
                }}
                onClick={() => !isFailed && setSelectedPhoto(item)}
              >
                {!isFailed ? (
                  <img
                    src={imgUrl}
                    alt={item.title || destName}
                    loading="lazy"
                    onError={() => handleImageError(idx)}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      transition: 'transform 0.3s ease',
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
                    onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                  />
                ) : (
                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'linear-gradient(135deg, #58111A, #3D0810)',
                      color: '#E5D2AD',
                      padding: '12px',
                      textAlign: 'center',
                    }}
                  >
                    <Landmark size={28} color="#E5D2AD" style={{ marginBottom: '6px' }} />
                    <span style={{ fontSize: '0.74rem', opacity: 0.85 }}>{destName}</span>
                  </div>
                )}

                {/* Magnify Icon Overlay */}
                {!isFailed && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '6px',
                      right: '6px',
                      background: 'rgba(0, 0, 0, 0.55)',
                      borderRadius: '50%',
                      width: '26px',
                      height: '26px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#FFFFFF',
                      backdropFilter: 'blur(4px)',
                    }}
                  >
                    <Maximize2 size={13} />
                  </div>
                )}
              </div>

              {/* Attribution and Caption Bar */}
              <div
                style={{
                  padding: '6px 10px',
                  fontSize: '0.72rem',
                  color: '#4A3E3E',
                  background: '#FAF6EE',
                  borderTop: '1px solid #EBE1CF',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '3px',
                }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    color: 'var(--burgundy, #58111A)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={item.title || destName}
                >
                  {item.title || destName}
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.67rem',
                    color: '#7A6B6B',
                  }}
                >
                  <span title={item.attribution}>
                    {item.photographer ? `By ${item.photographer}` : 'Wikimedia Commons'}
                  </span>

                  {item.license_url ? (
                    <a
                      href={item.license_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: '#8A5D00',
                        textDecoration: 'none',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '2px',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {item.license || 'CC License'}
                      <ExternalLink size={9} />
                    </a>
                  ) : (
                    <span>{item.license || 'Verified License'}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Lightbox Modal */}
      {selectedPhoto && (
        <div
          data-testid="gallery-lightbox"
          onClick={() => setSelectedPhoto(null)}
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
              maxWidth: '900px',
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
            {/* Close Button */}
            <button
              type="button"
              data-testid="lightbox-close-btn"
              onClick={() => setSelectedPhoto(null)}
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

            {/* Modal Image */}
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
                src={selectedPhoto.image_url || selectedPhoto.thumbnail_url}
                alt={selectedPhoto.title || destName}
                style={{
                  maxWidth: '100%',
                  maxHeight: '68vh',
                  objectFit: 'contain',
                }}
              />
            </div>

            {/* Modal Footer / Legal Attribution */}
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
                <h4 style={{ margin: '0 0 4px 0', fontSize: '0.92rem', color: 'var(--burgundy, #58111A)', fontWeight: 700 }}>
                  {selectedPhoto.title || destName}
                </h4>
                <div style={{ fontSize: '0.76rem', color: '#6A5C5C' }}>
                  {selectedPhoto.attribution || `Photo by ${selectedPhoto.photographer} · ${selectedPhoto.license}`}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {selectedPhoto.source_page_url && (
                  <a
                    href={selectedPhoto.source_page_url}
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
                    <span>View on Wikimedia Commons</span>
                    <ExternalLink size={12} />
                  </a>
                )}
                {onExplorePlace && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPhoto(null);
                      onExplorePlace(destName);
                    }}
                    className="btn btn-primary"
                    style={{ padding: '6px 14px', fontSize: '0.76rem' }}
                  >
                    Explore Details
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

