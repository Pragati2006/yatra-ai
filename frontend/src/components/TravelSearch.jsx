import React, { useState, useEffect, useRef } from 'react';
import { Compass, MapPin, Calendar, Users, Train, CheckCircle2, Clock, Coins, Footprints, Building2, Mountain, ArrowRight } from 'lucide-react';

const POPULAR_HUBS = [
  'Delhi', 'Jammu', 'Mumbai', 'Ahmedabad', 'Amritsar', 
  'Srinagar', 'Surat', 'Bhopal', 'Haridwar', 'Kolkata',
  'Chandigarh', 'Jaipur', 'Lucknow', 'Patna', 'Pune',
  'Palampur', 'Mandi', 'Dharamshala', 'Una', 'Reasi', 'Udhampur', 'Bangalore'
];

export default function TravelSearch({ onSearch, loading = false, initialValues = {} }) {
  const [origin, setOrigin] = useState(initialValues.origin || '');
  const [startDate, setStartDate] = useState(initialValues.startDate || initialValues.start_date || '2026-11-10');
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
      setPax(initialValues.pax);
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
    prevValuesRef.current = initialValues;
  }, [initialValues]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const bAmt = budgetAmount ? parseFloat(budgetAmount) : null;
    const bType = budgetType || 'total';
    const totalB = bAmt ? (bType === 'per_person' ? bAmt * parseInt(pax, 10) : bAmt) : null;
    const perPersonB = bAmt ? (bType === 'per_person' ? bAmt : bAmt / parseInt(pax, 10)) : null;

    let budgetStr = '';
    if (bAmt) {
      budgetStr = bType === 'per_person' ? ` with budget of ₹${bAmt} per person` : ` with total budget of ₹${bAmt}`;
    }

    const queryText = `Plan a trip for ${pax} people from ${origin} travelling to Katra on ${startDate} for ${duration} days with ${category}${mode !== 'any' ? ' by ' + mode : ''}${budgetStr}, ${travelStyle} pace, ${accommodationPreference} stay, mobility: ${mobilityPreference}`;
    
    onSearch({
      queryText,
      origin,
      startDate,
      returnDate,
      return_date: returnDate,
      pax: parseInt(pax, 10),
      mode,
      category,
      duration: parseInt(duration, 10),
      total_budget: totalB,
      budget_type: bType,
      budget_per_person: perPersonB,
      travel_style: travelStyle,
      accommodation_preference: accommodationPreference,
      sightseeing_choice: sightseeingChoice,
      mobility_preference: mobilityPreference,
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
          <div>
            <label htmlFor="travel-start-date" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Calendar size={14} /> Yatra Start Date
            </label>
            <input
              id="travel-start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            />
          </div>

          {/* Pilgrims */}
          <div>
            <label htmlFor="travel-pax" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Users size={14} /> Pilgrims (Pax)
            </label>
            <select
              id="travel-pax"
              value={pax}
              onChange={(e) => setPax(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              {[1, 2, 3, 4, 5, 6, 8, 10].map((num) => (
                <option key={num} value={num}>{num} {num === 1 ? 'Pilgrim' : 'Pilgrims'}</option>
              ))}
            </select>
          </div>

          {/* Transport Mode */}
          <div>
            <label htmlFor="travel-mode" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Train size={14} /> Travel Mode
            </label>
            <select
              id="travel-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="any">Any Available Mode</option>
              <option value="train">Train</option>
              <option value="flight">Flight</option>
              <option value="bus">Bus</option>
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
            <label htmlFor="travel-duration" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '4px' }}>
              <Clock size={14} /> Trip Duration
            </label>
            <select
              id="travel-duration"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              {[2, 3, 4, 5, 6, 7].map((days) => (
                <option key={days} value={days}>{days} Days ({days - 1} Nights)</option>
              ))}
            </select>
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
            </label>
            <select
              id="travel-accommodation"
              value={accommodationPreference}
              onChange={(e) => setAccommodationPreference(e.target.value)}
              style={{ padding: '0.55rem 0.75rem' }}
            >
              <option value="Standard">Standard (Comfort Guest House)</option>
              <option value="Deluxe">Deluxe (Premium Rooms)</option>
              <option value="Heritage">Heritage (Luxury Resort)</option>
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
