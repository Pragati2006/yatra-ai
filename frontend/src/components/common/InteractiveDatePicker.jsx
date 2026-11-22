import React, { useState } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Check, X, Clock } from 'lucide-react';

/**
 * Interactive calendar date picker supporting departure, return,
 * check-in, and check-out dates. Disables past dates, enforces
 * return >= departure and check-out > check-in.
 */
export default function InteractiveDatePicker({
  initialDeparture = '',
  initialReturn = '',
  onSelectDates,
  onClose,
  inline = false,
}) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const parseISO = (str) => {
    if (!str) return null;
    const parts = str.split('-');
    if (parts.length === 3) {
      return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    }
    return null;
  };

  const formatISO = (d) => {
    if (!d) return '';
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const initialDepDate = parseISO(initialDeparture) || new Date(2026, 10, 25);
  const initialRetDate = parseISO(initialReturn) || new Date(2026, 10, 28);

  const [currentMonth, setCurrentMonth] = useState(
    new Date(initialDepDate.getFullYear(), initialDepDate.getMonth(), 1)
  );
  const [departureDate, setDepartureDate] = useState(initialDepDate);
  const [returnDate, setReturnDate] = useState(initialRetDate);
  const [activePickingMode, setActivePickingMode] = useState('departure'); // 'departure' or 'return'

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const handlePrevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  };

  const daysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

  const totalDays = daysInMonth(currentMonth.getFullYear(), currentMonth.getMonth());
  const startDayOffset = firstDayOfMonth(currentMonth.getFullYear(), currentMonth.getMonth());

  const handleDateClick = (day) => {
    const clicked = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    clicked.setHours(0, 0, 0, 0);

    if (clicked < today) return; // Ignore past dates

    if (activePickingMode === 'departure') {
      setDepartureDate(clicked);
      if (returnDate && clicked > returnDate) {
        // Auto-shift return date to departure + 3 days
        const newRet = new Date(clicked);
        newRet.setDate(newRet.getDate() + 3);
        setReturnDate(newRet);
      }
      setActivePickingMode('return');
    } else {
      if (departureDate && clicked < departureDate) {
        // If clicked return date is earlier than departure, set departure instead
        setDepartureDate(clicked);
        const newRet = new Date(clicked);
        newRet.setDate(newRet.getDate() + 3);
        setReturnDate(newRet);
      } else {
        setReturnDate(clicked);
      }
    }
  };

  const durationDays = departureDate && returnDate
    ? Math.max(1, Math.round((returnDate - departureDate) / (1000 * 60 * 60 * 24)) + 1)
    : 4;
  const hotelNights = Math.max(1, durationDays - 1);

  const applyPreset = (days) => {
    const start = departureDate || new Date(2026, 10, 25);
    const end = new Date(start);
    end.setDate(end.getDate() + (days - 1));
    setReturnDate(end);
  };

  const handleConfirm = () => {
    if (onSelectDates) {
      onSelectDates({
        startDate: formatISO(departureDate),
        endDate: formatISO(returnDate),
        departureDate: formatISO(departureDate),
        returnDate: formatISO(returnDate),
        checkInDate: formatISO(departureDate),
        checkOutDate: formatISO(returnDate),
        durationDays,
        hotelNights,
      });
    }
    if (onClose) onClose();
  };

  return (
    <div
      data-testid="interactive-date-picker-card"
      style={{
        background: '#FFFFFF',
        border: '1.5px solid var(--gold-border, #E5D2AD)',
        borderRadius: '14px',
        padding: '16px',
        boxShadow: inline ? 'none' : '0 6px 24px rgba(88, 17, 26, 0.12)',
        maxWidth: '380px',
        width: '100%',
        margin: inline ? '0 auto' : '0',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--burgundy, #58111A)', fontWeight: 800, fontSize: '0.95rem' }}>
          <CalendarIcon size={16} />
          <span>Select Travel & Hotel Dates</span>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted, #7A7A7A)', padding: '2px' }}
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Date Type Selector: Departure vs Return */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '14px' }}>
        <div
          onClick={() => setActivePickingMode('departure')}
          style={{
            padding: '8px',
            borderRadius: '8px',
            border: activePickingMode === 'departure' ? '2px solid var(--burgundy, #58111A)' : '1px solid #E0E0E0',
            background: activePickingMode === 'departure' ? 'rgba(88, 17, 26, 0.04)' : '#FAFAFA',
            cursor: 'pointer',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #7A7A7A)', textTransform: 'uppercase' }}>
            Departure / Check-in
          </div>
          <div style={{ fontWeight: 800, fontSize: '0.86rem', color: 'var(--burgundy, #58111A)' }}>
            {departureDate ? formatISO(departureDate) : 'Select'}
          </div>
        </div>

        <div
          onClick={() => setActivePickingMode('return')}
          style={{
            padding: '8px',
            borderRadius: '8px',
            border: activePickingMode === 'return' ? '2px solid var(--burgundy, #58111A)' : '1px solid #E0E0E0',
            background: activePickingMode === 'return' ? 'rgba(88, 17, 26, 0.04)' : '#FAFAFA',
            cursor: 'pointer',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted, #7A7A7A)', textTransform: 'uppercase' }}>
            Return / Check-out
          </div>
          <div style={{ fontWeight: 800, fontSize: '0.86rem', color: 'var(--burgundy, #58111A)' }}>
            {returnDate ? formatISO(returnDate) : 'Select'}
          </div>
        </div>
      </div>

      {/* Month Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <button
          type="button"
          onClick={handlePrevMonth}
          style={{ background: 'none', border: '1px solid #E0E0E0', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}
        >
          <ChevronLeft size={14} />
        </button>
        <span style={{ fontWeight: 700, fontSize: '0.88rem', color: '#333' }}>
          {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
        </span>
        <button
          type="button"
          onClick={handleNextMonth}
          style={{ background: 'none', border: '1px solid #E0E0E0', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer' }}
        >
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Weekday Labels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center', marginBottom: '6px' }}>
        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((w, i) => (
          <div key={i} style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted, #7A7A7A)' }}>
            {w}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center', marginBottom: '14px' }}>
        {Array.from({ length: startDayOffset }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}

        {Array.from({ length: totalDays }).map((_, i) => {
          const day = i + 1;
          const thisDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
          thisDate.setHours(0, 0, 0, 0);

          const isPast = thisDate < today;
          const isDep = departureDate && thisDate.getTime() === departureDate.getTime();
          const isRet = returnDate && thisDate.getTime() === returnDate.getTime();
          const inRange = departureDate && returnDate && thisDate > departureDate && thisDate < returnDate;

          let bg = 'transparent';
          let textColor = isPast ? '#CCCCCC' : '#222222';
          let fontWeight = '500';

          if (isDep || isRet) {
            bg = 'var(--burgundy, #58111A)';
            textColor = '#FFFFFF';
            fontWeight = '700';
          } else if (inRange) {
            bg = 'rgba(212, 175, 55, 0.18)';
            textColor = 'var(--burgundy, #58111A)';
          }

          return (
            <button
              key={day}
              type="button"
              disabled={isPast}
              onClick={() => handleDateClick(day)}
              style={{
                width: '100%',
                aspectRatio: '1',
                borderRadius: isDep || isRet ? '8px' : '4px',
                background: bg,
                color: textColor,
                border: 'none',
                fontWeight,
                fontSize: '0.78rem',
                cursor: isPast ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'background 0.15s ease',
              }}
            >
              {day}
            </button>
          );
        })}
      </div>

      {/* Quick Duration Presets */}
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted, #7A7A7A)' }}>Quick duration:</span>
        {[
          { label: '3 Days', days: 3 },
          { label: '4 Days (Standard)', days: 4 },
          { label: '5 Days', days: 5 },
        ].map((p) => (
          <button
            key={p.days}
            type="button"
            onClick={() => applyPreset(p.days)}
            style={{
              padding: '2px 8px',
              fontSize: '0.72rem',
              borderRadius: '12px',
              border: durationDays === p.days ? '1px solid var(--burgundy, #58111A)' : '1px solid #D0D0D0',
              background: durationDays === p.days ? 'rgba(88, 17, 26, 0.08)' : '#FFFFFF',
              color: durationDays === p.days ? 'var(--burgundy, #58111A)' : '#444444',
              cursor: 'pointer',
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Summary Footer */}
      <div style={{ borderTop: '1px solid var(--gold-border, #E5D2AD)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #7A7A7A)' }}>Trip Schedule:</div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--burgundy, #58111A)' }}>
            {durationDays} Days · {hotelNights} Nights
          </div>
        </div>
        <button
          type="button"
          data-testid="apply-calendar-dates-btn"
          onClick={handleConfirm}
          className="btn btn-primary"
          style={{
            fontSize: '0.82rem',
            padding: '6px 14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            borderRadius: '8px',
            backgroundColor: 'var(--burgundy, #58111A)',
            color: '#FFFFFF',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          <Check size={14} /> Apply Dates
        </button>
      </div>
    </div>
  );
}

