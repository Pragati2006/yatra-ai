import React from 'react';

/**
 * Itemized Budget Breakdown Card for AI Chat stream.
 */
export default function BudgetCard({ budgetEvaluation }) {
  if (!budgetEvaluation) return null;

  const b = budgetEvaluation;
  const transport = b.transport_cost || b.transport || 0;
  const lodging = b.lodging_cost || b.hotel_cost || b.lodging || 0;
  const darshan = b.darshan_cost || b.darshan || 0;
  const buffer = b.buffer_amount || b.buffer || 0;
  const total = b.grand_total || (transport + lodging + darshan + buffer);

  return (
    <div
      style={{
        marginTop: '0.65rem',
        background: '#FFFFFF',
        border: '1px solid var(--gold-border, #E5D2AD)',
        borderRadius: '12px',
        padding: '12px 14px',
        boxShadow: '0 2px 8px rgba(88, 17, 26, 0.04)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '1.1rem' }}>💰</span>
          <span style={{ fontFamily: 'var(--font-serif)', fontWeight: 700, fontSize: '0.84rem', color: 'var(--burgundy)' }}>
            Itemized Pilgrimage Budget
          </span>
        </div>
        <div style={{ fontWeight: 800, fontSize: '0.92rem', color: '#8A5D00' }}>
          Total: ₹{Math.round(total).toLocaleString('en-IN')}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '6px', fontSize: '0.78rem' }}>
        <div style={{ background: 'var(--bg-subtle)', padding: '6px 8px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Transport</div>
          <div style={{ fontWeight: 700 }}>₹{Math.round(transport).toLocaleString('en-IN')}</div>
        </div>
        <div style={{ background: 'var(--bg-subtle)', padding: '6px 8px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Lodging</div>
          <div style={{ fontWeight: 700 }}>₹{Math.round(lodging).toLocaleString('en-IN')}</div>
        </div>
        <div style={{ background: 'var(--bg-subtle)', padding: '6px 8px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Darshan / Activity</div>
          <div style={{ fontWeight: 700 }}>₹{Math.round(darshan).toLocaleString('en-IN')}</div>
        </div>
        <div style={{ background: 'var(--bg-subtle)', padding: '6px 8px', borderRadius: '6px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Contingency Buffer</div>
          <div style={{ fontWeight: 700 }}>₹{Math.round(buffer).toLocaleString('en-IN')}</div>
        </div>
      </div>
    </div>
  );
}
