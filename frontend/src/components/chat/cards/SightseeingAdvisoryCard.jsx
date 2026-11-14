import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Sightseeing Advisory warning card for time/distance/feasibility constraints.
 */
export default function SightseeingAdvisoryCard({ infeasiblePlaces }) {
  if (!infeasiblePlaces || infeasiblePlaces.length === 0) return null;

  return (
    <div
      data-testid="chat-infeasible-advisory"
      style={{
        marginTop: '0.65rem',
        background: '#FFF8F6',
        border: '1px solid #F5C6CB',
        borderLeft: '4px solid #C0392B',
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '0.8rem',
        color: '#721C24',
        lineHeight: 1.45,
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <AlertCircle size={14} color="#C0392B" /> Sightseeing Advisory & Route Feasibility:
      </div>
      <div>
        {infeasiblePlaces.map((inf, idx) => {
          const name = typeof inf === 'string' ? inf : (inf.place || inf.name);
          const reason = typeof inf === 'object' ? inf.reason : null;
          return (
            <span key={idx}>
              <b>{name}</b>
              {reason ? ` (${reason})` : ''}
              {idx < infeasiblePlaces.length - 1 ? '; ' : ''}
            </span>
          );
        })}
      </div>
    </div>
  );
}
