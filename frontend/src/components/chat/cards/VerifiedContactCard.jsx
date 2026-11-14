import React from 'react';
import { AlertCircle, Building2, Navigation, Shield, HeartPulse, Phone, MapPin, Clock, Info } from 'lucide-react';
import FreshnessIndicator from '../provenance/FreshnessIndicator';

/**
 * VerifiedContactCard: Renders verified emergency and official authority helplines.
 *
 * Governance & Safety Invariants:
 * - 112 is always displayed as the primary statutory emergency contact at the top.
 * - Distinguishes 24x7 emergency response from office-hours administrative desks.
 * - Provides direct tel: links for mobile devotees.
 */
export default function VerifiedContactCard({ contactsData }) {
  if (!contactsData) return null;

  let contacts = [];
  let _primaryDirective = null;
  let disclaimer = null;

  if (Array.isArray(contactsData)) {
    contacts = contactsData;
  } else if (typeof contactsData === 'object') {
    contacts = contactsData.contacts || (contactsData.contact_id ? [contactsData] : []);
    _primaryDirective = contactsData.primary_emergency_directive || null;
    disclaimer = contactsData.disclaimer || null;
  }

  const getCategoryMeta = (cat) => {
    switch (cat) {
      case 'NATIONAL_EMERGENCY':
        return { label: 'National Emergency', icon: <AlertCircle size={12} color="#B91C1C" style={{ marginRight: 3 }} />, color: '#B91C1C', bg: '#FEF2F2' };
      case 'SHRINE_BOARD_ASSISTANCE':
        return { label: 'Shrine Board (SMVDSB)', icon: <Building2 size={12} color="#92400E" style={{ marginRight: 3 }} />, color: '#92400E', bg: '#FEF3C7' };
      case 'TRAFFIC_CONTROL':
        return { label: 'Traffic Control Unit', icon: <Navigation size={12} color="#0369A1" style={{ marginRight: 3 }} />, color: '#0369A1', bg: '#E0F2FE' };
      case 'LOCAL_POLICE':
        return { label: 'Local Police', icon: <Shield size={12} color="#4338CA" style={{ marginRight: 3 }} />, color: '#4338CA', bg: '#EEF2FF' };
      case 'MEDICAL_ASSISTANCE':
        return { label: 'Medical Ambulance', icon: <HeartPulse size={12} color="#15803D" style={{ marginRight: 3 }} />, color: '#15803D', bg: '#DCFCE7' };
      default:
        return { label: 'Helpline', icon: <Phone size={12} color="#4B5563" style={{ marginRight: 3 }} />, color: '#4B5563', bg: '#F3F4F6' };
    }
  };

  return (
    <div
      data-testid="chat-verified-contacts-card"
      style={{
        marginTop: '0.65rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '12px 14px',
        boxShadow: '0 2px 6px rgba(88, 17, 26, 0.04)',
      }}
    >
      {/* 1. Primary Statutory Emergency Directive (112 Banner) */}
      <div
        data-testid="emergency-112-banner"
        style={{
          background: 'linear-gradient(135deg, #7F1D1D 0%, #991B1B 100%)',
          color: '#FFFFFF',
          borderRadius: '8px',
          padding: '10px 14px',
          marginBottom: '10px',
          boxShadow: '0 2px 6px rgba(127, 29, 29, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.88rem', letterSpacing: '0.2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={16} />
              <span>PRIMARY EMERGENCY DIRECTIVE: DIAL 112</span>
            </div>
            <div style={{ fontSize: '0.74rem', opacity: 0.92, marginTop: '2px', lineHeight: 1.35 }}>
              For immediate life-safety emergencies (Police, Fire, Ambulance, Disaster), call 112 directly. Operational 24x7 across Pan-India and J&K.
            </div>
          </div>
          <a
            href="tel:112"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: '#FFFFFF',
              color: '#991B1B',
              padding: '5px 12px',
              borderRadius: '6px',
              fontWeight: 800,
              fontSize: '0.82rem',
              textDecoration: 'none',
              boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
              flexShrink: 0,
            }}
          >
            <Phone size={12} /> Call 112
          </a>
        </div>
      </div>

      {/* Directory Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Phone size={16} color="var(--burgundy, #58111A)" />
          <span style={{ fontWeight: 700, fontSize: '0.84rem', color: 'var(--burgundy, #58111A)' }}>
            Verified Helplines & Authority Directory
          </span>
        </div>
        <span style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 500 }}>
          {contacts.length} Verified Contact{contacts.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Contact Entries List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {contacts.map((c) => {
          const meta = getCategoryMeta(c.category);
          const isOfficeHoursOnly = (c.operating_hours || '').toLowerCase().includes('office hours') || (c.operating_hours || '').toLowerCase().includes('working days');

          return (
            <div
              key={c.contact_id}
              data-testid={`contact-entry-${c.contact_id}`}
              style={{
                background: '#F9FAFB',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                padding: '8px 12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '2px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.8rem', color: '#111827' }}>
                      {c.organization}
                    </span>
                    <span
                      style={{
                        fontSize: '0.62rem',
                        fontWeight: 600,
                        padding: '1px 5px',
                        borderRadius: '4px',
                        background: meta.bg,
                        color: meta.color,
                      }}
                    >
                      {meta.label}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.73rem', color: '#4B5563', lineHeight: 1.35, marginBottom: '4px' }}>
                    {c.service_description}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', fontSize: '0.68rem', color: '#6B7280' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <MapPin size={11} /> {c.geographic_jurisdiction}
                    </span>
                    <span style={{ color: isOfficeHoursOnly ? '#B45309' : '#047857', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Clock size={11} /> {c.operating_hours}
                    </span>
                  </div>
                </div>

                {/* Telephone dial button */}
                <div style={{ flexShrink: 0, textAlign: 'right' }}>
                  <a
                    href={`tel:${c.telephone_number.replace(/\s+/g, '')}`}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'var(--burgundy, #58111A)',
                      color: '#FFFFFF',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.76rem',
                      fontWeight: 700,
                      textDecoration: 'none',
                    }}
                  >
                    <Phone size={12} /> {c.telephone_number}
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      {disclaimer && (
        <div style={{ marginTop: '8px', fontSize: '0.71rem', color: '#6B7280', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Info size={11} />
          <span>{disclaimer}</span>
        </div>
      )}

      {/* Provenance Footer */}
      <div
        style={{
          marginTop: '8px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(229, 210, 173, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.68rem',
          color: 'var(--text-muted, #6B5C5C)',
        }}
      >
        <FreshnessIndicator freshness="not_applicable" sourceType="curated_data" />
        <span>Verified Primary Registry</span>
      </div>
    </div>
  );
}
