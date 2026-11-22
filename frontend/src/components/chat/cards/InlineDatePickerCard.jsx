import React, { useState } from 'react';
import InteractiveDatePicker from '../../common/InteractiveDatePicker';
import { Calendar, CheckCircle2 } from 'lucide-react';

/**
 * Interactive Date Picker Card for Chat stream.
 * Allows pilgrims to interactively pick departure and return dates
 * directly in chat and apply them to the booking plan.
 */
export default function InlineDatePickerCard({
  initialDeparture = '2026-11-25',
  initialReturn = '2026-11-28',
  onApplyDates,
  onSend,
}) {
  const [applied, setApplied] = useState(false);
  const [appliedInfo, setAppliedInfo] = useState(null);

  const handleSelect = (selected) => {
    setApplied(true);
    setAppliedInfo(selected);
    if (onApplyDates) {
      onApplyDates(selected);
    } else if (onSend) {
      onSend(`We want to travel on ${selected.startDate} and return on ${selected.endDate}`);
    }
  };

  if (applied && appliedInfo) {
    return (
      <div
        data-testid="date-picker-applied-card"
        style={{
          marginTop: '0.65rem',
          background: 'rgba(46, 125, 50, 0.08)',
          border: '1px solid #2E7D32',
          borderRadius: '10px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#2E7D32',
          fontSize: '0.84rem',
        }}
      >
        <CheckCircle2 size={16} />
        <span>
          Dates Applied: <b>{appliedInfo.startDate}</b> to <b>{appliedInfo.endDate}</b> ({appliedInfo.durationDays} Days / {appliedInfo.hotelNights} Nights)
        </span>
      </div>
    );
  }

  return (
    <div data-testid="inline-date-picker" style={{ marginTop: '0.75rem', width: '100%', maxWidth: '380px' }}>
      <InteractiveDatePicker
        inline
        initialDeparture={initialDeparture}
        initialReturn={initialReturn}
        onSelectDates={handleSelect}
      />
    </div>
  );
}

