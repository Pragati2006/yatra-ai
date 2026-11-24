import React, { useState, useEffect, useRef } from 'react';
import {
  Compass,
  MapPin,
  Calendar,
  Users,
  Train,
  CheckCircle2,
  Clock,
  Coins,
  Footprints,
  Building2,
  Mountain,
  ArrowRight,
  Car,
  Plus,
  Trash2,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import InteractiveDatePicker from './common/InteractiveDatePicker';

const POPULAR_HUBS = [
  'Delhi', 'Jammu', 'Mumbai', 'Ahmedabad', 'Amritsar', 
  'Srinagar', 'Surat', 'Bhopal', 'Haridwar', 'Kolkata',
  'Chandigarh', 'Jaipur', 'Lucknow', 'Patna', 'Pune',
  'Palampur', 'Mandi', 'Dharamshala', 'Una', 'Reasi', 'Udhampur', 'Bangalore'
];

export default function TravelSearch({ onSearch, loading = false, initialValues = {} }) {
  const todayISO = (() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  })();

  const [origin, setOrigin] = useState(initialValues.origin || '');
  const [startDate, setStartDate] = useState(initialValues.startDate || initialValues.start_date || todayISO);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [pax, setPax] = useState(initialValues.pax || 2);
  const [mode, setMode] = useState(initialValues.mode || 'any');
  const [category, setCategory] = useState(initialValues.category || 'Normal Darshan');
  const [duration, setDuration] = useState(initialValues.duration || initialValues.duration_days || 4);
  const [budgetType, setBudgetType] = useState(initialValues.budget_type || 'total');
  const [budgetAmount, setBudgetAmount] = useState(() => {
    if (initialValues.total_budget) return String(initialValues.total_budget);
    if (initialValues.budget_per_person) return String(initialValues.budget_per_person);
    return '';
  });
  const [travelStyle, setTravelStyle] = useState(initialValues.travel_style || 'balanced');
  const [accommodationPreference, setAccommodationPreference] = useState(initialValues.accommodation_preference || 'Standard');
  const [sightseeingChoice, setSightseeingChoice] = useState(initialValues.sightseeing_choice || 'recommend');
  const [mobilityPreference, setMobilityPreference] = useState(initialValues.mobility_preference || 'Standard Walking Trek');

  // Flexible Service Preferences (Part 1)
  const [includeHotel, setIncludeHotel] = useState(
    initialValues.hotelSelected !== undefined ? initialValues.hotelSelected : (initialValues.hotel_selected !== undefined ? initialValues.hotel_selected : true)
  );
  const [includeTransport, setIncludeTransport] = useState(
    initialValues.transportSelected !== undefined ? initialValues.transportSelected : (initialValues.transport_selected !== undefined ? initialValues.transport_selected : true)
  );
  const [ownVehicle, setOwnVehicle] = useState(
    initialValues.ownVehicle !== undefined ? initialValues.ownVehicle : (initialValues.own_vehicle !== undefined ? initialValues.own_vehicle : false)
  );

  // Group & Dynamic Pilgrim Records (Part 3)
  const initialPaxCount = Math.max(1, parseInt(initialValues.pax, 10) || 2);
  const [pilgrims, setPilgrims] = useState(() => {
    if (Array.isArray(initialValues.pilgrims) && initialValues.pilgrims.length > 0) {
      return initialValues.pilgrims.map(p => ({
        full_name: p.full_name || p.name || '',
        age: p.age ? String(p.age) : '',
        gender: p.gender || 'Male',
      }));
    }
    const initialList = [{
      full_name: initialValues.primaryContact?.name || initialValues.fullName || '',
      age: initialValues.primaryContact?.age ? String(initialValues.primaryContact.age) : '',
      gender: 'Male',
    }];
    while (initialList.length < initialPaxCount) {
      initialList.push({ full_name: '', age: '', gender: 'Male' });
    }
    return initialList;
  });

  const [primaryContact, setPrimaryContact] = useState(() => {
    return initialValues.primaryContact || initialValues.primary_contact || {
      name: initialValues.fullName || '',
      email: '',
      phone: initialValues.phone || '',
    };
  });

  const [prefilledFields, setPrefilledFields] = useState(() => {
    const raw = initialValues.prefilledFields || initialValues.prefilled_fields || [];
    return new Set(Array.isArray(raw) ? raw : []);
  });

  const [validationError, setValidationError] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState('');

  const calculateReturnDate = (start, dur) => {
    try {
      const parts = String(start).split('-');
      if (parts.length === 3) {
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        d.setDate(d.getDate() + Math.max(1, parseInt(dur, 10) - 1));
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
      }
    } catch {
      // fallback
    }
    return '';
  };

  const returnDate = calculateReturnDate(startDate, duration);

  const prevValuesRef = useRef(initialValues);

  useEffect(() => {
    const prev = prevValuesRef.current;
    if (initialValues.origin && initialValues.origin !== prev?.origin) {
      setOrigin(initialValues.origin);
    }
    const newStart = initialValues.startDate || initialValues.start_date;
    const prevStart = prev?.startDate || prev?.start_date;
    if (newStart && newStart !== prevStart) {
      setStartDate(newStart);
    }
    if (initialValues.pax && initialValues.pax !== prev?.pax) {
      const newPaxVal = parseInt(initialValues.pax, 10) || 1;
      setPax(newPaxVal);
      setPilgrims((curr) => {
        const copy = [...curr];
        if (copy.length < newPaxVal) {
          while (copy.length < newPaxVal) {
            copy.push({ full_name: '', age: '', gender: 'Male' });
          }
        } else if (copy.length > newPaxVal) {
          return copy.slice(0, newPaxVal);
        }
        return copy;
      });
    }
    if (initialValues.mode && initialValues.mode !== prev?.mode) {
      setMode(initialValues.mode);
    }
    if (initialValues.category && initialValues.category !== prev?.category) {
      setCategory(initialValues.category);
    }
    const newDur = initialValues.duration || initialValues.duration_days;
    const prevDur = prev?.duration || prev?.duration_days;
    if (newDur && newDur !== prevDur) {
      setDuration(newDur);
    }
    if (initialValues.budget_type && initialValues.budget_type !== prev?.budget_type) {
      setBudgetType(initialValues.budget_type);
    }
    const newBudget = initialValues.total_budget || initialValues.budget_per_person;
    const prevBudget = prev?.total_budget || prev?.budget_per_person;
    if (newBudget && newBudget !== prevBudget) {
      setBudgetAmount(String(newBudget));
    }
    if (initialValues.travel_style && initialValues.travel_style !== prev?.travel_style) {
      setTravelStyle(initialValues.travel_style);
    }
    if (initialValues.accommodation_preference && initialValues.accommodation_preference !== prev?.accommodation_preference) {
      setAccommodationPreference(initialValues.accommodation_preference);
    }
    if (initialValues.sightseeing_choice && initialValues.sightseeing_choice !== prev?.sightseeing_choice) {
      setSightseeingChoice(initialValues.sightseeing_choice);
    }
    if (initialValues.hotelSelected !== undefined && initialValues.hotelSelected !== prev?.hotelSelected) {
      setIncludeHotel(initialValues.hotelSelected);
    }
    if (initialValues.transportSelected !== undefined && initialValues.transportSelected !== prev?.transportSelected) {
      setIncludeTransport(initialValues.transportSelected);
    }
    if (initialValues.ownVehicle !== undefined && initialValues.ownVehicle !== prev?.ownVehicle) {
      setOwnVehicle(initialValues.ownVehicle);
    }
    if (Array.isArray(initialValues.pilgrims) && initialValues.pilgrims.length > 0) {
      setPilgrims(initialValues.pilgrims.map(p => ({
        full_name: p.full_name || p.name || '',
        age: p.age ? String(p.age) : '',
        gender: p.gender || 'Male',
      })));
      setPax(initialValues.pilgrims.length);
    }
    if (initialValues.prefilledFields || initialValues.prefilled_fields) {
      const raw = initialValues.prefilledFields || initialValues.prefilled_fields;
      setPrefilledFields(new Set(Array.isArray(raw) ? raw : []));
    }
    prevValuesRef.current = initialValues;
  }, [initialValues]);

  // Synchronize dynamic pilgrims array with count
  const handlePaxChange = (newCount) => {
    const count = Math.max(1, Math.min(200, parseInt(newCount, 10) || 1));
    setPax(count);
    setPilgrims((prev) => {
      const copy = [...prev];
      if (copy.length < count) {
        while (copy.length < count) {
          copy.push({ full_name: '', age: '', gender: 'Male' });
        }
      } else if (copy.length > count) {
        return copy.slice(0, count);
      }
      return copy;
    });
  };

  const handleAddPilgrim = () => {
    if (pilgrims.length >= 200) {
      setValidationError('Group size is capped at 200 pilgrims for online booking.');
      return;
    }
    const nextCount = pilgrims.length + 1;
    setPax(nextCount);
    setPilgrims([...pilgrims, { full_name: '', age: '', gender: 'Male' }]);
    setValidationError('');
  };

  const handleRemovePilgrim = (index) => {
    if (pilgrims.length <= 1) return;
    const updated = pilgrims.filter((_, i) => i !== index);
    setPax(updated.length);
    setPilgrims(updated);
    setValidationError('');
  };

  const handleUpdatePilgrim = (index, field, value) => {
    setPilgrims((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
    // Check for duplicate names warning
    if (field === 'full_name' && value.trim()) {
      const valLower = value.trim().toLowerCase();
      const isDup = pilgrims.some((p, i) => i !== index && p.full_name?.trim().toLowerCase() === valLower);
      if (isDup) {
        setDuplicateWarning(`"${value.trim()}" appears multiple times in this booking. Ensure distinct names or append initials.`);
      } else {
        setDuplicateWarning('');
      }
    }
    setValidationError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError('');

    // Date validation
    if (startDate && startDate < todayISO) {
      setValidationError('Yatra start date cannot be in the past.');
      return;
    }

    const durNum = parseInt(duration, 10);
    if (isNaN(durNum) || durNum < 1 || durNum > 90) {
      setValidationError('Trip duration must be between 1 and 90 days.');
      return;
    }

    // Pilgrims validation (Part 3 & 4)
    if (!pilgrims || pilgrims.length === 0) {
      setValidationError('At least 1 pilgrim is required.');
      return;
    }

    for (let i = 0; i < pilgrims.length; i++) {
      const p = pilgrims[i];
      if (!p.full_name || !p.full_name.trim()) {
        setValidationError(`Please enter the full name for Pilgrim ${i + 1}.`);
        return;
      }
      const ageNum = parseInt(p.age, 10);
      if (!p.age || isNaN(ageNum) || ageNum < 1 || ageNum > 125) {
        setValidationError(`Please enter a valid age (1-125) for Pilgrim ${i + 1} (${p.full_name || 'Pilgrim'}).`);
        return;
      }
    }

    const effectiveTransportSelected = Boolean(includeTransport && !ownVehicle);
    const effectiveHotelSelected = Boolean(includeHotel);

    const bAmt = budgetAmount ? parseFloat(budgetAmount) : null;
    const bType = budgetType || 'total';
    const totalB = bAmt ? (bType === 'per_person' ? bAmt * parseInt(pax, 10) : bAmt) : null;
    const perPersonB = bAmt ? (bType === 'per_person' ? bAmt : bAmt / parseInt(pax, 10)) : null;

    let budgetStr = '';
    if (bAmt) {
      budgetStr = bType === 'per_person' ? ` with budget of ₹${bAmt} per person` : ` with total budget of ₹${bAmt}`;
    }

    let transportStr = '';
    if (ownVehicle) {
      transportStr = ' by own vehicle';
    } else if (includeTransport && mode !== 'any') {
      transportStr = ` by ${mode}`;
    } else if (!includeTransport) {
      transportStr = ' with self-arranged transport';
    }

    let hotelStr = includeHotel ? `, ${accommodationPreference} stay` : ', without hotel (self-arranged accommodation)';

    const queryText = `Plan a trip for ${pax} people from ${origin || 'Delhi'} travelling to Katra on ${startDate} for ${duration} days with ${category}${transportStr}${budgetStr}, ${travelStyle} pace${hotelStr}, mobility: ${mobilityPreference}`;
    
    onSearch({
      queryText,
      origin: origin || 'Delhi',
      startDate,
      returnDate,
      return_date: returnDate,
      pax: parseInt(pax, 10),
      mode: ownVehicle ? 'own_vehicle' : mode,
      category,
      duration: parseInt(duration, 10),
      total_budget: totalB,
      budget_type: bType,
      budget_per_person: perPersonB,
      travel_style: travelStyle,
      accommodation_preference: accommodationPreference,
      sightseeing_choice: sightseeingChoice,
      mobility_preference: mobilityPreference,
      hotelSelected: effectiveHotelSelected,
      transportSelected: effectiveTransportSelected,
      ownVehicle: ownVehicle,
      pilgrims: pilgrims.map(p => ({
        full_name: p.full_name.trim(),
        age: parseInt(p.age, 10),
        gender: p.gender || 'Male',
      })),
      primaryContact: {
        name: pilgrims[0]?.full_name?.trim() || primaryContact.name || '',
        email: primaryContact.email || '',
        phone: primaryContact.phone || '',
      },
    });
  };

  return (
    <div style={{
      background: '#FFFFFF',
      border: '1.5px solid var(--gold-border)',
      borderRadius: '20px',
      padding: '1.5rem',
      boxShadow: 'var(--shadow-md)',
      width: '100%',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.15rem', color: 'var(--burgundy)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Compass size={20} color="var(--burgundy)" />
            Plan Your Sacred Yatra
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Search verified trains, flights, buses, and shrine darshan slots to Katra
          </div>
        </div>
        <span className="pill pill-gold">
          Live Shrine Connectivity
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px',
          marginBottom: '1.25rem',
        }}>
          {/* Origin */}
          <div>
            <label htmlFor="travel-origin" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <MapPin size={14} /> Departure City
              {prefilledFields.has('origin') && (
                <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                  ✨ From Chat
                </span>
              )}
            </label>
            <input
              id="travel-origin"
              type="text"
              list="popular-hubs-list"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              placeholder="e.g. Delhi, Mandi, Palampur, Reasi, Pune..."
              style={{ padding: '0.55rem 0.75rem', width: '100%', boxSizing: 'border-box' }}
            />
            <datalist id="popular-hubs-list">
              {POPULAR_HUBS.map((h) => (
                <option key={h} value={h} />
              ))}
            </datalist>
          </div>

          {/* Travel Date */}
          <div style={{ position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label htmlFor="travel-start-date" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', margin: 0 }}>
                <Calendar size={14} /> Yatra Start Date
                {prefilledFields.has('startDate') || prefilledFields.has('travel_dates') ? (
                  <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                    ✨ From Chat
                  </span>
                ) : null}
              </label>
              <button
                type="button"
                data-testid="toggle-date-picker-btn"
                onClick={() => setShowDatePicker((prev) => !prev)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--burgundy)',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0,
                }}
              >
                {showDatePicker ? 'Close Calendar' : 'Open Calendar'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                id="travel-start-date"
                type="date"
                value={startDate}
                min={todayISO}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!val || val >= todayISO) {
                    setStartDate(val);
                  }
                }}
                style={{ flex: 1, padding: '0.55rem 0.75rem' }}
              />
            </div>
            {showDatePicker && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 40,
                  marginTop: '8px',
                  boxShadow: '0 8px 30px rgba(0,0,0,0.18)',
                  borderRadius: '14px',
                }}
              >
                <InteractiveDatePicker
                  initialDeparture={startDate || todayISO}
                  initialReturn={returnDate}
                  onSelectDates={(dates) => {
                    if (dates.startDate) setStartDate(dates.startDate);
                    if (dates.durationDays) setDuration(dates.durationDays);
                    setShowDatePicker(false);
                  }}
                  onClose={() => setShowDatePicker(false)}
                />
              </div>
            )}
          </div>

          {/* Pilgrims */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label htmlFor="travel-pax" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', margin: 0 }}>
                <Users size={14} /> Pilgrims (Pax)
                {prefilledFields.has('pax') && (
                  <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                    ✨ From Chat
                  </span>
                )}
              </label>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <select
                id="travel-pax"
                value={pax}
                onChange={(e) => handlePaxChange(parseInt(e.target.value, 10) || 1)}
                style={{ flex: 1, padding: '0.55rem 0.75rem' }}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 25, 30, 40, 50].map((num) => (
                  <option key={num} value={num}>{num} {num === 1 ? 'Pilgrim' : 'Pilgrims'}</option>
                ))}
                {!([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 25, 30, 40, 50].includes(Number(pax))) && (
                  <option value={pax}>{pax} Pilgrims</option>
                )}
              </select>
              <input
                id="travel-pax-input"
                type="number"
                min="1"
                max="200"
                step="1"
                value={pax}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (!isNaN(val) && val >= 1) {
                    handlePaxChange(val);
                  } else if (e.target.value === '') {
                    setPax('');
                  }
                }}
                onBlur={() => {
                  if (!pax || pax < 1) handlePaxChange(1);
                }}
                aria-label="Custom Pilgrim Count"
                title="Enter custom pilgrim count"
                placeholder="Qty"
                style={{ width: '65px', padding: '0.55rem 0.5rem', textAlign: 'center' }}
              />
            </div>
          </div>

          {/* Transport Mode */}
          <div>
            <label htmlFor="travel-mode" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Train size={14} /> Travel Mode
              {ownVehicle ? (
                <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>Own Car</span>
              ) : (!includeTransport ? (
                <span className="pill" style={{ fontSize: '0.62rem', padding: '1px 5px', background: '#F1F5F9' }}>Excluded</span>
              ) : null)}
            </label>
            <select
              id="travel-mode"
              value={ownVehicle ? 'own_vehicle' : (!includeTransport ? 'none' : mode)}
              disabled={ownVehicle || !includeTransport}
              onChange={(e) => setMode(e.target.value)}
              style={{ padding: '0.55rem 0.75rem', opacity: (ownVehicle || !includeTransport) ? 0.7 : 1 }}
            >
              {ownVehicle ? (
                <option value="own_vehicle">Own Vehicle / Private Car</option>
              ) : !includeTransport ? (
                <option value="none">Self-Arranged (No Booking)</option>
              ) : (
                <>
                  <option value="any">Any Available Mode</option>
                  <option value="train">Train</option>
                  <option value="flight">Flight</option>
                  <option value="bus">Bus</option>
                </>
              )}
            </select>
          </div>

          {/* Darshan Slot */}
          <div>
            <label htmlFor="travel-category" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <CheckCircle2 size={14} /> Darshan Category
            </label>
            <select
              id="travel-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="Normal Darshan">Normal Darshan</option>
              <option value="VIP Darshan">VIP Darshan</option>
              <option value="Helicopter Darshan">Helicopter Darshan</option>
            </select>
          </div>

          {/* Duration */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label htmlFor="travel-duration" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', margin: 0 }}>
                <Clock size={14} /> Trip Duration
                {prefilledFields.has('duration') && (
                  <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                    ✨ From Chat
                  </span>
                )}
              </label>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <select
                id="travel-duration"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value, 10) || 1)}
                style={{ flex: 1, padding: '0.55rem 0.75rem' }}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 20, 30].map((days) => (
                  <option key={days} value={days}>
                    {days} {days === 1 ? 'Day (Express Same-Day)' : `${days} Days (${days - 1} Nights)`}
                  </option>
                ))}
                {!([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 20, 30].includes(Number(duration))) && (
                  <option value={duration}>{duration} Days ({duration - 1} Nights)</option>
                )}
              </select>
              <input
                id="travel-duration-input"
                type="number"
                min="1"
                max="90"
                step="1"
                value={duration}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (!isNaN(val) && val >= 1) {
                    setDuration(val);
                  } else if (e.target.value === '') {
                    setDuration('');
                  }
                }}
                onBlur={() => {
                  if (!duration || duration < 1) setDuration(1);
                }}
                aria-label="Custom Trip Duration Days"
                title="Enter custom duration in days"
                placeholder="Days"
                style={{ width: '65px', padding: '0.55rem 0.5rem', textAlign: 'center' }}
              />
            </div>
          </div>

          {/* Budget Scope */}
          <div>
            <label htmlFor="travel-budget-type" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Coins size={14} /> Budget Scope
            </label>
            <select
              id="travel-budget-type"
              value={budgetType}
              onChange={(e) => setBudgetType(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="total">Total Group Budget</option>
              <option value="per_person">Per-Person Budget</option>
            </select>
          </div>

          {/* Budget Amount */}
          <div>
            <label htmlFor="travel-budget-amount" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Coins size={14} /> Budget Amount (₹)
              {prefilledFields.has('budget') && (
                <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                  ✨ From Chat
                </span>
              )}
            </label>
            <input
              id="travel-budget-amount"
              type="number"
              placeholder={budgetType === 'total' ? 'e.g. 15000' : 'e.g. 7500'}
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              min="0"
              step="500"
              style={{ padding: '0.55rem 0.75rem' }}
            />
          </div>

          {/* Travel Pace */}
          <div>
            <label htmlFor="travel-pace" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Footprints size={14} /> Travel Pace / Style
            </label>
            <select
              id="travel-pace"
              value={travelStyle}
              onChange={(e) => setTravelStyle(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="balanced">Balanced & Moderate</option>
              <option value="relaxed">Relaxed & Leisurely</option>
              <option value="packed">Packed & Full Exploration</option>
            </select>
          </div>

          {/* Accommodation Preference */}
          <div>
            <label htmlFor="travel-accommodation" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Building2 size={14} /> Stay Preference
              {!includeHotel && <span className="pill" style={{ fontSize: '0.62rem', padding: '1px 5px', background: '#F1F5F9' }}>Excluded</span>}
            </label>
            <select
              id="travel-accommodation"
              value={includeHotel ? accommodationPreference : 'None'}
              disabled={!includeHotel}
              onChange={(e) => setAccommodationPreference(e.target.value)}
              style={{ padding: '0.55rem 0.75rem', opacity: includeHotel ? 1 : 0.7 }}
            >
              {!includeHotel ? (
                <option value="None">No Hotel (Self-Arranged)</option>
              ) : (
                <>
                  <option value="Standard">Standard (Comfort Guest House)</option>
                  <option value="Deluxe">Deluxe (Premium Rooms)</option>
                  <option value="Heritage">Heritage (Luxury Resort)</option>
                </>
              )}
            </select>
          </div>

          {/* Sightseeing Approach */}
          <div>
            <label htmlFor="travel-sightseeing" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Mountain size={14} /> Sightseeing Plan
            </label>
            <select
              id="travel-sightseeing"
              value={sightseeingChoice}
              onChange={(e) => setSightseeingChoice(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="recommend">AI Recommended Highlights</option>
              <option value="later">Decide Later in Katra</option>
            </select>
          </div>

          {/* Mobility & Accessibility Preference */}
          <div>
            <label htmlFor="travel-mobility" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Footprints size={14} /> Mobility Support
            </label>
            <select
              id="travel-mobility"
              value={mobilityPreference}
              onChange={(e) => setMobilityPreference(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="Standard Walking Trek">Standard Walking Trek</option>
              <option value="Senior Citizen (Battery Car)">Senior Citizen (Battery Car)</option>
              <option value="Palki / Pony Support">Palki / Pony Support</option>
              <option value="Helicopter Priority">Helicopter Priority</option>
            </select>
          </div>
        </div>

        {/* ========================================================= */}
        {/* PART 1: INDEPENDENTLY OPTIONAL HOTEL & TRANSPORT         */}
        {/* ========================================================= */}
        <div style={{
          background: '#FAF8F5',
          border: '1px solid var(--gold-border)',
          borderRadius: '14px',
          padding: '14px 16px',
          marginBottom: '1.25rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--burgundy)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Car size={16} /> Flexible Yatra Components
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Customize your journey components. Hotel and transport can be booked or omitted independently.
              </div>
            </div>
            {prefilledFields.has('hotel_selected') || prefilledFields.has('transport_selected') || prefilledFields.has('own_vehicle') ? (
              <span className="pill pill-gold" style={{ fontSize: '0.68rem' }}>✨ Preferences from Chat</span>
            ) : null}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
            {/* Include Hotel Toggle */}
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              background: includeHotel ? '#FFFFFF' : '#F1F5F9',
              border: `1.5px solid ${includeHotel ? 'var(--gold-border)' : '#CBD5E1'}`,
              borderRadius: '10px',
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={includeHotel}
                onChange={(e) => setIncludeHotel(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--gold-primary)' }}
              />
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: includeHotel ? 'var(--text-dark)' : 'var(--text-muted)' }}>
                  Include Katra Hotel / Stay
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {includeHotel ? 'Verified Katra hotel or Dharamshala' : 'Self-arranged / day-trip (₹0 hotel cost)'}
                </div>
              </div>
            </label>

            {/* Include Transport Toggle */}
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              background: (includeTransport && !ownVehicle) ? '#FFFFFF' : '#F1F5F9',
              border: `1.5px solid ${(includeTransport && !ownVehicle) ? 'var(--gold-border)' : '#CBD5E1'}`,
              borderRadius: '10px',
              cursor: ownVehicle ? 'not-allowed' : 'pointer',
              opacity: ownVehicle ? 0.6 : 1,
            }}>
              <input
                type="checkbox"
                checked={includeTransport && !ownVehicle}
                disabled={ownVehicle}
                onChange={(e) => setIncludeTransport(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--gold-primary)' }}
              />
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: (includeTransport && !ownVehicle) ? 'var(--text-dark)' : 'var(--text-muted)' }}>
                  Include Public Transport
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {ownVehicle ? 'Bypassed (Traveling by own car)' : (includeTransport ? 'Verified Train, Flight, or Bus booking' : 'Self-arranged transport (₹0 fare)')}
                </div>
              </div>
            </label>

            {/* Own Vehicle Option */}
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              background: ownVehicle ? '#FEF3C7' : '#FFFFFF',
              border: `1.5px solid ${ownVehicle ? '#F59E0B' : '#E2E8F0'}`,
              borderRadius: '10px',
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={ownVehicle}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setOwnVehicle(checked);
                  if (checked) {
                    setIncludeTransport(false);
                    setMode('own_vehicle');
                  } else {
                    setIncludeTransport(true);
                    setMode('any');
                  }
                }}
                style={{ width: '16px', height: '16px', accentColor: '#D97706' }}
              />
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: ownVehicle ? '#92400E' : 'var(--text-dark)' }}>
                  Traveling by Own Car / Vehicle
                </div>
                <div style={{ fontSize: '0.7rem', color: ownVehicle ? '#B45309' : 'var(--text-muted)' }}>
                  Bypasses ticket carrier fees; provides Katra parking advice
                </div>
              </div>
            </label>
          </div>

          {/* Service Notices */}
          {ownVehicle && (
            <div style={{ marginTop: '10px', fontSize: '0.74rem', color: '#92400E', background: '#FEF3C7', padding: '6px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Car size={13} />
              <span><b>Own Vehicle Mode Active:</b> Public carrier searches are bypassed. Total fare is ₹0. Route guidance and Katra Shrine parking pointers will be provided.</span>
            </div>
          )}
          {!includeHotel && (
            <div style={{ marginTop: ownVehicle ? '6px' : '10px', fontSize: '0.74rem', color: '#1E40AF', background: '#EFF6FF', padding: '6px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Building2 size={13} />
              <span><b>Accommodation Excluded:</b> No Katra hotel will be reserved or billed. Day-excursion or self-arranged stay at family/dharamshala.</span>
            </div>
          )}
          {!includeTransport && !ownVehicle && (
            <div style={{ marginTop: '6px', fontSize: '0.74rem', color: '#475569', background: '#F8FAFC', padding: '6px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Train size={13} />
              <span><b>Public Transport Excluded:</b> You will arrive at Katra independently. Only shrine darshan queue guidance and selected hotels are coordinated.</span>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* PART 3: INDIVIDUAL PILGRIM DETAILS & GROUP MANAGEMENT     */}
        {/* ========================================================= */}
        <div style={{
          background: '#FFFFFF',
          border: '1.5px solid var(--gold-border)',
          borderRadius: '14px',
          padding: '16px',
          marginBottom: '1.25rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.94rem', color: 'var(--burgundy)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Users size={16} /> Individual Pilgrim Records ({pilgrims.length} Devotees)
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Shrine Board registration requires the individual full name and age of every pilgrim in your party.
              </div>
            </div>
            <button
              type="button"
              onClick={handleAddPilgrim}
              className="btn btn-outline"
              style={{ fontSize: '0.76rem', padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Plus size={13} /> Add Pilgrim
            </button>
          </div>

          {/* Pilgrim Cards List */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {pilgrims.map((p, idx) => (
              <div
                key={idx}
                style={{
                  background: '#FAF8F5',
                  border: '1px solid #E5D2AD',
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      width: '22px',
                      height: '22px',
                      borderRadius: '50%',
                      background: 'var(--burgundy)',
                      color: '#FFF',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      {idx + 1}
                    </span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--burgundy)' }}>
                      Pilgrim {idx + 1} {idx === 0 ? '(Primary Booker)' : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {(idx === 0 && prefilledFields.has('fullName')) || prefilledFields.has('pilgrims') ? (
                      <span className="pill pill-gold" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                        ✨ From Chat
                      </span>
                    ) : null}
                    {idx > 0 && (
                      <button
                        type="button"
                        onClick={() => handleRemovePilgrim(idx)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#DC2626',
                          cursor: 'pointer',
                          padding: '2px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                        title={`Remove Pilgrim ${idx + 1}`}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dark)', display: 'block', marginBottom: '2px' }}>
                      Full Name *
                    </label>
                    <input
                      type="text"
                      placeholder={`Full Name ${idx + 1}`}
                      value={p.full_name}
                      onChange={(e) => handleUpdatePilgrim(idx, 'full_name', e.target.value)}
                      style={{ width: '100%', padding: '0.45rem 0.6rem', fontSize: '0.82rem', boxSizing: 'border-box' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dark)', display: 'block', marginBottom: '2px' }}>
                      Age (1–125) *
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="125"
                      placeholder="Age"
                      value={p.age}
                      onChange={(e) => handleUpdatePilgrim(idx, 'age', e.target.value)}
                      style={{ width: '100%', padding: '0.45rem 0.6rem', fontSize: '0.82rem', boxSizing: 'border-box' }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-dark)', display: 'block', marginBottom: '2px' }}>
                    Gender
                  </label>
                  <select
                    value={p.gender || 'Male'}
                    onChange={(e) => handleUpdatePilgrim(idx, 'gender', e.target.value)}
                    style={{ width: '100%', padding: '0.45rem 0.6rem', fontSize: '0.82rem', boxSizing: 'border-box' }}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>
            ))}
          </div>

          {/* Duplicate Name Warning */}
          {duplicateWarning && (
            <div style={{ marginTop: '10px', fontSize: '0.76rem', color: '#92400E', background: '#FEF3C7', padding: '6px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={14} />
              <span>{duplicateWarning}</span>
            </div>
          )}
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div style={{
            background: '#FEE2E2',
            border: '1.5px solid #FCA5A5',
            borderRadius: '10px',
            padding: '10px 14px',
            marginBottom: '1rem',
            color: '#991B1B',
            fontSize: '0.82rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <AlertCircle size={16} />
            <span>{validationError}</span>
          </div>
        )}

        {/* Calculated Return Date Banner */}
        {returnDate && (
          <div style={{
            background: '#FAF5EE',
            border: '1px solid var(--gold-border)',
            borderRadius: '10px',
            padding: '8px 14px',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.82rem',
            color: 'var(--burgundy)',
            fontWeight: 600,
          }}>
            <Clock size={15} color="var(--burgundy)" />
            <span>
              Calculated Return: <b>{returnDate}</b> ({duration} Days / {Math.max(1, duration - 1)} Nights) • Destination: <b>Katra (Shri Mata Vaishno Devi)</b>
            </span>
          </div>
        )}

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ padding: '0.75rem 2rem', fontSize: '0.92rem', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            {loading ? 'Searching Verified Options...' : (
              <>
                Search Yatra Options <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
