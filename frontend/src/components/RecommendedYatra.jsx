import React, { useState } from 'react';
import { Edit3, Info, X, Train, Plane, Bus, CheckCircle2, Building2, Mountain, Coins, Calendar, Compass, MapPin, Clock, ArrowRight, Check, ChevronDown, ChevronUp } from 'lucide-react';
import ItineraryTimeline from './ItineraryTimeline';
import InteractiveDatePicker from './common/InteractiveDatePicker';

/**
 * RecommendedYatra.jsx
 * Consolidated "Your Recommended Yatra" presentation page.
 * Displays automatically generated recommendations across:
 * - Trip Overview
 * - Selected Transport
 * - Selected Accommodation
 * - Selected Darshan Slot
 * - Sightseeing Feasibility & Day-Wise Itinerary (with travel & recovery considerations)
 * - Itemised Budget (distinguishing verified direct costs, discretionary estimates, and excluded expenses)
 * - Confirmation prompt: "Are you happy with these selections, or would you like to change anything before proceeding?"
 *   - Path A: "Confirm Selections & Continue"
 *   - Path B: "Change My Selections" (with direct jump to editable categories)
 */
export default function RecommendedYatra({
  planData,
  tripRequest,
  sessionId,
  planVersion = 1,
  onConfirmSelections,
  onEditCategory,
  planRevisionNotice = '',
}) {
  const [showCategorySelector, setShowCategorySelector] = useState(false);
  const [showHotelSelector, setShowHotelSelector] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);

  // Extract components from planData
  const option = planData?.selected_option || planData?.option || {};
  const tr = option.transport || option.flight || {};
  const slot = option.slot || {};
  const hotel = planData?.hotel || planData?.selected_hotel || null;
  const itinerary = planData?.itinerary || [];
  const feasiblePlaces = planData?.feasible_places || [];
  const infeasiblePlaces = planData?.infeasible_places || [];
  const budgetEval = planData?.budget_evaluation || {};

  const req = tripRequest || planData?.request || {};
  const origin = req.origin || tr.origin || '';
  const pax = req.pax || req.pilgrims || 1;
  const initialDuration = req.duration_days || req.duration || req.days || (itinerary.length > 0 ? itinerary.length : 4);
  const initialTravelDate = req.start_date || tr.travel_date || '2026-11-25';

  const [currentHotel, setCurrentHotel] = useState(hotel);
  const [currentTravelDate, setCurrentTravelDate] = useState(initialTravelDate);
  const [currentDurationDays, setCurrentDurationDays] = useState(initialDuration);

  const durationDays = currentDurationDays;
  const travelDate = currentTravelDate;
  const activeHotel = currentHotel || hotel;
  const hotelNights = Math.max(1, durationDays - 1);
  const roomsCount = Math.ceil(pax / 2);

  const verifiedHotelsCatalog = [
    { name: 'Niharika Complex (SMVDSB)', category: 'Dharamshala', price_per_night: 150, location: 'Near Main Bus Stand, Katra', phone: '01991-234053', operator_type: 'SMVDSB' },
    { name: 'Trikuta Bhawan (SMVDSB)', category: 'Dharamshala', price_per_night: 150, location: 'Near YRC-II, Katra', phone: '01991-234053', operator_type: 'SMVDSB' },
    { name: 'Ardhkuwari Complex (SMVDSB)', category: 'Dharamshala', price_per_night: 150, location: 'Ardhkuwari Temple Complex (6 km mark)', phone: '01991-234053', operator_type: 'SMVDSB' },
    { name: 'Main Bhawan Complex (SMVDSB)', category: 'Dharamshala', price_per_night: 150, location: 'Holy Bhawan Shrine Area (13 km peak)', phone: '01991-234053', operator_type: 'SMVDSB' },
    { name: 'Vivanta Katra, Vaishno Devi', category: 'Premium', price_per_night: 6000, location: 'Jammu-Katra Highway', phone: '+91 1991 350200', operator_type: 'IHCL_TAJ' },
    { name: 'Welcomhotel by ITC Hotels, Katra', category: 'Premium', price_per_night: 6500, location: 'SMVD Chowk, Katra', phone: '+91 1991 351 000', operator_type: 'ITC_HOTELS' },
    { name: 'Lemon Tree Hotel, Katra', category: 'Mid-Range', price_per_night: 3200, location: 'Railway Station Road', phone: '+91 7298524450', operator_type: 'LEMON_TREE_HOTELS' },
    { name: 'Ramada by Wyndham Katra Station Road', category: 'Premium', price_per_night: 3500, location: 'Station Road, Katra', phone: '+91 1991 350 300', operator_type: 'WYNDHAM_HOTELS' },
    { name: 'The Vaishnodevi Sarovar Portico, Katra', category: 'Mid-Range', price_per_night: 3500, location: 'Jammu Road, Katra', phone: '+91 1991-233301', operator_type: 'SAROVAR_HOTELS' },
    { name: 'The White Hotel, Katra', category: 'Mid-Range', price_per_night: 4200, location: 'Reasi Road, Katra', phone: '+91 1991 350100', operator_type: 'INDEPENDENT' },
    { name: 'Hotel Asia Vaishno Devi', category: 'Mid-Range', price_per_night: 2200, location: 'Near Katra Bus Stand', phone: '+91 9070433364', operator_type: 'INDEPENDENT' },
    { name: 'Hotel Subash International', category: 'Budget', price_per_night: 1200, location: 'Main Bazaar, Katra', phone: '01991-232100', operator_type: 'INDEPENDENT' },
    { name: 'Hotel Shree Hari Niwas', category: 'Budget', price_per_night: 1200, location: 'Jammu Road, Katra', phone: '+91 1991-233601', operator_type: 'INDEPENDENT' },
    { name: 'Zone Connect by The Park, Katra', category: 'Mid-Range', price_per_night: 2800, location: 'Railway Road, Katra', phone: '01991-233001', operator_type: 'THE_PARK_HOTELS' },
    { name: 'Hotel The Vaishnavi', category: 'Budget', price_per_night: 1000, location: 'Jammu Road, Katra', phone: '+91 1991-233499', operator_type: 'INDEPENDENT' },
  ];
  const hotelList = (planData?.available_hotels && planData.available_hotels.length > 0)
    ? planData.available_hotels
    : verifiedHotelsCatalog;

  const handleSelectHotel = (htl) => {
    setCurrentHotel(htl);
    if (planData) {
      planData.hotel = htl;
      planData.selected_hotel = htl;
    }
    setShowHotelSelector(false);
  };

  const handleApplyDates = (dates) => {
    setCurrentTravelDate(dates.startDate);
    setCurrentDurationDays(dates.durationDays);
    if (tripRequest) {
      tripRequest.start_date = dates.startDate;
      tripRequest.end_date = dates.endDate;
      tripRequest.duration_days = dates.durationDays;
    }
    setShowDatePicker(false);
  };

  // Transport details
  const mode = (tr.mode || 'train').toUpperCase();
  const operator = tr.operator || (mode === 'TRAIN' ? 'Indian Railways' : 'Express Service');
  const serviceNo = tr.transport_no || (tr.id ? `ID #${tr.id}` : 'Direct Service');

  const isTrain = mode === 'TRAIN';
  const isBus = mode === 'BUS';
  const isFlight = mode === 'FLIGHT';

  // Timetable truthfulness: If point timings are unverified (e.g. curated railway), suppress fabricated clock times
  const isTrainTimetableUnverified = isTrain && (tr.timetable_verification?.status === 'unverified' || !tr.timetable_verification);
  const depTime = isTrainTimetableUnverified ? 'Check NTES (139)' : (tr.departure_time || (isBus ? '05:00 - 22:00 Window' : (isFlight ? 'Check flight' : 'Check schedule')));
  const arrTime = isTrainTimetableUnverified ? 'Check NTES (139)' : (tr.arrival_time || (isBus ? 'Regular departures' : (isFlight ? 'Confirm with airline' : 'Enquire at counter')));
  const durationStr = !isFlight && !isTrainTimetableUnverified ? (tr.duration_str || (tr.duration_mins ? `${Math.floor(tr.duration_mins / 60)}h ${tr.duration_mins % 60}m` : null)) : null;

  // Fares segregation: never display unavailable airfare, train fare, or counter slab as confirmed ₹0
  const isFareUnavailable = tr.fare_classification === 'UNAVAILABLE' ||
    tr.fare_classification === 'STATUTORY_NOTIFIED_PER_KM_SLAB' ||
    (isFlight && tr.fare == null && tr.price == null && tr.indicative_fare_min == null) ||
    (isTrain && tr.fare == null && tr.price == null && tr.indicative_fare_min == null) ||
    (tr.fare == null && tr.price == null && tr.fare_per_person == null);

  const farePerPerson = isFareUnavailable ? null : (tr.fare_per_person || tr.price || null);
  const transportFareTotal = farePerPerson !== null ? (tr.total_fare || (farePerPerson * pax)) : null;

  // Darshan details
  const slotCategory = slot.category || req.category || 'Normal Darshan';
  const slotPricePerPerson = slot.price || 0;
  const darshanTotal = slotPricePerPerson * pax;

  // Accommodation details
  const hotelPricePerNight = activeHotel?.price_per_night || 0;
  const hotelTotal = hotelPricePerNight * roomsCount * hotelNights;

  // Financial Summary from budgetEval or deterministic formula
  const verifiedDirectTotal = (transportFareTotal || 0) + darshanTotal + hotelTotal;
  const roadTransferEst = budgetEval?.estimated_costs?.items?.local_road_transfer || (mode === 'FLIGHT' ? 1500 * pax : 350 * pax);
  const mealsEst = budgetEval?.estimated_costs?.items?.meals_and_refreshments || (350 * pax * durationDays);
  const totalEstimated = roadTransferEst + mealsEst;

  const isBudgetIncomplete = isFareUnavailable || budgetEval.grand_total == null || budgetEval.is_complete === false;
  const grandTotal = isBudgetIncomplete ? null : (budgetEval.grand_total || (verifiedDirectTotal + totalEstimated));
  const costPerPerson = grandTotal !== null && pax > 0 ? Math.round(grandTotal / pax) : null;
  const targetBudget = req.total_budget ? Number(req.total_budget) : (budgetEval.total_budget ? Number(budgetEval.total_budget) : null);
  const remainingBudget = (targetBudget !== null && grandTotal !== null) ? targetBudget - grandTotal : null;
  const isWithinBudget = grandTotal !== null && targetBudget !== null ? grandTotal <= targetBudget : null;

  return (
    <div data-testid="recommended-yatra-page" style={{ width: '100%' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span className="pill pill-gold" style={{ fontSize: '0.8rem', fontWeight: 800 }}>
              AI Recommended Package
            </span>
            <span className="pill" style={{ background: '#F0EAE1', color: 'var(--burgundy)', fontSize: '0.78rem', fontWeight: 700 }}>
              Plan Revision #{planVersion} {sessionId ? `• Session ${sessionId.slice(0, 8)}` : ''}
            </span>
          </div>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.85rem', fontWeight: 800, color: 'var(--burgundy)', margin: '6px 0 2px 0' }}>
            Your Recommended Yatra Package
          </h1>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', margin: 0 }}>
            Curated specifically for your travel dates, budget scope, and Maa Vaishno Devi darshan timing feasibility.
          </p>
        </div>

        <button
          type="button"
          data-testid="toggle-change-selections-btn"
          onClick={() => setShowCategorySelector(!showCategorySelector)}
          className="btn btn-outline"
          style={{ fontSize: '0.84rem', padding: '7px 16px', borderColor: 'var(--gold-primary)', color: 'var(--burgundy)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <Edit3 size={14} /> Change My Selections
        </button>
      </div>

      {/* Plan Revision Banner if updated */}
      {planRevisionNotice && (
        <div style={{
          background: '#FFFBEB',
          border: '1.5px solid #FCD34D',
          borderRadius: '12px',
          padding: '12px 16px',
          marginBottom: '1.5rem',
          fontSize: '0.85rem',
          color: '#92400E',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Info size={16} /> {planRevisionNotice}
        </div>
      )}

      {/* Editable Category Quick-Links Drawer */}
      {showCategorySelector && (
        <div className="card" style={{ background: '#FFFDF7', border: '1.5px solid var(--gold-border)', marginBottom: '1.75rem', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ fontWeight: 800, color: 'var(--burgundy)', fontSize: '0.92rem' }}>
              Select a category to customize:
            </div>
            <button
              onClick={() => setShowCategorySelector(false)}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <X size={14} /> Close
            </button>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              data-testid="edit-cat-transport"
              onClick={() => onEditCategory('transport')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Train size={14} /> Transport
            </button>
            <button
              type="button"
              data-testid="edit-cat-darshan"
              onClick={() => onEditCategory('darshan')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <CheckCircle2 size={14} /> Darshan Slot
            </button>
            <button
              type="button"
              data-testid="edit-cat-accommodation"
              onClick={() => onEditCategory('accommodation')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Building2 size={14} /> Accommodation
            </button>
            <button
              type="button"
              data-testid="edit-cat-sightseeing"
              onClick={() => onEditCategory('sightseeing')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Mountain size={14} /> Sightseeing
            </button>
            <button
              type="button"
              data-testid="edit-cat-budget"
              onClick={() => onEditCategory('budget')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Coins size={14} /> Budget
            </button>
            <button
              type="button"
              data-testid="edit-cat-dates"
              onClick={() => setShowDatePicker(!showDatePicker)}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Calendar size={14} /> Dates & Duration
            </button>
            <button
              type="button"
              data-testid="edit-cat-style"
              onClick={() => onEditCategory('style')}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Compass size={14} /> Style & Pacing
            </button>
          </div>
        </div>
      )}

      {/* Main Consolidated Grids */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        {/* Left Column: Trip Overview, Transport, Hotel, Darshan */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* 1. Trip Overview Card */}
          <div className="card" style={{ background: '#FFFFFF' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.05rem', color: 'var(--burgundy)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={16} /> Pilgrimage Overview
              </div>
              <span className="pill pill-gold" style={{ fontSize: '0.72rem' }}>
                {durationDays} Days / {hotelNights} Nights
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.84rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Starting Location</span>
                <b>{origin}</b>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Sacred Destination</span>
                <b>Katra & Bhawan</b>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Pilgrims Count</span>
                <b>{pax} {pax === 1 ? 'Pilgrim' : 'Pilgrims'}</b>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Yatra Start Date</span>
                <b>{travelDate}</b>
                <button
                  type="button"
                  data-testid="change-dates-btn"
                  onClick={() => setShowDatePicker(!showDatePicker)}
                  style={{
                    display: 'block',
                    marginTop: '3px',
                    fontSize: '0.72rem',
                    color: 'var(--burgundy)',
                    background: 'none',
                    border: 'none',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    padding: 0,
                    fontWeight: 600,
                  }}
                >
                  Change Dates
                </button>
              </div>
            </div>
            {showDatePicker && (
              <div style={{ marginTop: '12px', borderTop: '1px solid var(--gold-border)', paddingTop: '10px' }}>
                <InteractiveDatePicker
                  initialDeparture={travelDate}
                  onSelectDates={handleApplyDates}
                  onClose={() => setShowDatePicker(false)}
                />
              </div>
            )}
          </div>

          {/* 2. Selected Transport Service Card */}
          <div className="card" style={{ background: '#FFFFFF', border: '1.5px solid var(--gold-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="pill pill-gold" style={{ fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    {mode === 'FLIGHT' ? <><Plane size={12} /> FLIGHT</> : (mode === 'BUS' ? <><Bus size={12} /> BUS</> : <><Train size={12} /> TRAIN</>)}
                  </span>
                  <span style={{ fontWeight: 800, fontSize: '0.98rem', color: 'var(--burgundy)' }}>
                    {operator} {serviceNo && `· ${serviceNo}`}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Departure: <b>{origin}</b> <ArrowRight size={12} /> Arrival: <b>{tr.destination || 'Katra'}</b>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onEditCategory('transport')}
                className="btn btn-outline"
                style={{ fontSize: '0.74rem', padding: '4px 10px' }}
              >
                Change
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', padding: '8px 0', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)', marginBottom: '8px' }}>
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-dark)' }}>{depTime}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{origin}</div>
              </div>
              <div style={{ textAlign: 'center', padding: '0 8px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '3px' }}>
                  {durationStr ? <><Clock size={11} /> {durationStr}</> : 'Scheduled'}
                </div>
                <div style={{ color: 'var(--gold-primary)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ArrowRight size={14} />
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-dark)' }}>{arrTime}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tr.destination || 'Katra'}</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.82rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>
                {isFareUnavailable ? 'Transport Tariff:' : `Transport Fare (${pax}x ₹${farePerPerson}):`}
              </span>
              <b style={{ color: 'var(--burgundy)', fontSize: '0.92rem' }}>
                {isFareUnavailable
                  ? (isFlight
                      ? 'Airfare on airline portal (dynamic pricing)'
                      : (isTrain
                          ? 'Fare on IRCTC portal (dynamic pricing)'
                          : (tr.indicative_fare_min
                              ? `Statutory slab approx ₹${tr.indicative_fare_min}–₹${tr.indicative_fare_max || 110} (Counter)`
                              : 'Tariff payable at counter')))
                  : `₹${transportFareTotal.toLocaleString('en-IN')}`}
              </b>
            </div>
          </div>

          {/* 3. Selected Darshan Slot Guidance Card */}
          <div className="card" style={{ background: '#FFFFFF', border: '1.5px solid var(--gold-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="pill pill-gold" style={{ fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={12} /> DARSHAN GUIDANCE
                  </span>
                  <span style={{ fontWeight: 800, fontSize: '0.98rem', color: 'var(--burgundy)' }}>
                    {slotCategory}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Shri Mata Vaishno Devi Shrine Board · Free Public Yatra
                </div>
              </div>
              <span className="pill" style={{ background: '#F0EAE1', color: 'var(--burgundy)', fontSize: '0.68rem', fontWeight: 700 }}>
                RFID Registration at Katra
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.84rem', marginTop: '6px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Targeted Darshan Date</span>
                <b>{slot.slot_date || travelDate}</b>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.74rem' }}>Shrine Fee</span>
                <b style={{ color: '#155724' }}>
                  {darshanTotal === 0 ? '₹0 (Free Entry · RFID Card Required)' : `₹${darshanTotal.toLocaleString('en-IN')}`}
                </b>
              </div>
            </div>

            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px dashed #DDD', paddingTop: '6px', marginTop: '6px' }}>
              <strong>Shrine Board Procedure:</strong> Normal Darshan has no pre-booked Shrine Board time slots. Pilgrims collect a free RFID Yatra Access Card at Katra counters on arrival before beginning the trek.
            </div>
          </div>

          {/* 4. Selected Accommodation Card */}
          <div className="card" style={{ background: '#FFFFFF', border: '1.5px solid var(--gold-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="pill pill-gold" style={{ fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Building2 size={12} /> HOTEL
                  </span>
                  <span style={{ fontWeight: 800, fontSize: '0.98rem', color: 'var(--burgundy)' }}>
                    {activeHotel?.name || 'Katra Stay Reserved'}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {activeHotel?.location || 'Central Katra Base'} · {activeHotel?.category || 'Standard'} Category
                </div>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  type="button"
                  data-testid="change-hotel-btn"
                  onClick={() => setShowHotelSelector(!showHotelSelector)}
                  className="btn btn-outline"
                  style={{ fontSize: '0.74rem', padding: '4px 10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  Select Another Hotel {showHotelSelector ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
              </div>
            </div>

            {activeHotel ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.82rem', marginTop: '6px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.72rem' }}>Room Configuration</span>
                  <b>{roomsCount} room(s) for {pax} guest(s)</b>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.72rem' }}>Stay Duration</span>
                  <b>{hotelNights} Night(s)</b>
                </div>
                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Hotel Total ({roomsCount} rm x {hotelNights} n):</span>
                  <b style={{ color: 'var(--burgundy)' }}>₹{hotelTotal.toLocaleString('en-IN')}</b>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '4px' }}>
                No Katra hotel reserved (day-excursion or self-arranged stay).
              </div>
            )}

            {showHotelSelector && (
              <div
                data-testid="inline-hotel-selector"
                style={{
                  marginTop: '10px',
                  borderTop: '1px solid var(--gold-border)',
                  paddingTop: '10px',
                }}
              >
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--burgundy)', marginBottom: '8px' }}>
                  Select Katra Accommodation:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                  {hotelList.map((h, i) => {
                    const isSelected = activeHotel?.name === h.name;
                    return (
                      <div
                        key={i}
                        data-testid={`hotel-option-${i}`}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '8px 10px',
                          borderRadius: '8px',
                          border: isSelected ? '1.5px solid var(--burgundy)' : '1px solid #E0E0E0',
                          background: isSelected ? 'rgba(88, 17, 26, 0.04)' : '#FFFFFF',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '0.84rem', color: isSelected ? 'var(--burgundy)' : '#222' }}>
                            {h.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {h.category} · ₹{(h.price_per_night || 1200).toLocaleString('en-IN')}/night · {h.location || 'Katra'}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleSelectHotel(h)}
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.72rem',
                            borderRadius: '6px',
                            background: isSelected ? 'var(--burgundy)' : 'rgba(88, 17, 26, 0.08)',
                            color: isSelected ? '#FFFFFF' : 'var(--burgundy)',
                            border: '1px solid var(--gold-border)',
                            cursor: 'pointer',
                            fontWeight: 700,
                          }}
                        >
                          {isSelected ? 'Selected' : 'Select'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Sightseeing & Itinerary + Itemised Budget */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* 5. Sightseeing & Day-Wise Itinerary */}
          <div className="card" style={{ background: '#FFFFFF', padding: '1.25rem' }}>
            <ItineraryTimeline
              itinerary={itinerary}
              daysCount={durationDays}
              feasiblePlaces={feasiblePlaces}
              infeasiblePlaces={infeasiblePlaces}
              onEditCategory={onEditCategory}
            />
          </div>

          {/* 6. Itemised Budget Summary */}
          <div className="card" style={{ background: 'var(--gold-subtle)', border: '1.5px solid var(--gold-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.05rem', color: 'var(--burgundy)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Coins size={16} /> Itemised Budget Breakdown
              </div>
              <button
                type="button"
                onClick={() => onEditCategory('budget')}
                className="btn btn-outline"
                style={{ fontSize: '0.74rem', padding: '4px 10px', background: '#FFFFFF' }}
              >
                Adjust Budget
              </button>
            </div>

            {/* Verified Direct Costs */}
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dark)', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{isFareUnavailable ? 'Transport Tariff:' : `Verified Transport (${pax}x fare):`}</span>
                <b style={{ color: isFareUnavailable ? '#856404' : 'inherit' }}>
                  {isFareUnavailable ? 'Payable to carrier (excluded from total)' : `₹${transportFareTotal.toLocaleString('en-IN')}`}
                </b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Darshan Entry ({pax}x pilgrim):</span>
                <b style={{ color: '#155724' }}>
                  {darshanTotal === 0 ? '₹0 (Free Normal Darshan)' : `₹${darshanTotal.toLocaleString('en-IN')}`}
                </b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Verified Hotel ({roomsCount} rm, {hotelNights} n):</span>
                <b>₹{hotelTotal.toLocaleString('en-IN')}</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #E5D2AD', paddingTop: '4px', marginTop: '2px', fontWeight: 700 }}>
                <span>Total Verified Direct Charges:</span>
                <span style={{ color: '#155724' }}>₹{verifiedDirectTotal.toLocaleString('en-IN')}</span>
              </div>
            </div>

            {/* Discretionary Estimates */}
            <div style={{ background: '#FFFDF9', borderRadius: '8px', padding: '8px 10px', fontSize: '0.74rem', color: '#856404', border: '1px solid #FFEBAA', marginBottom: '8px' }}>
              <div style={{ fontWeight: 700, marginBottom: '2px' }}>Estimated Discretionary Expenses (Pay on-site):</div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>• Road Transfers (Katra taxi/shuttle):</span>
                <span>₹{roadTransferEst.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>• Meals & Refreshments ({pax} pax, {durationDays} d):</span>
                <span>₹{mealsEst.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, marginTop: '2px', borderTop: '1px dashed #FFEBAA', paddingTop: '2px' }}>
                <span>Total Estimates:</span>
                <span>₹{totalEstimated.toLocaleString('en-IN')}</span>
              </div>
            </div>

            {/* Grand Total & Per Person */}
            <div style={{ background: '#FFFFFF', borderRadius: '10px', padding: '10px 14px', border: '1.5px solid var(--gold-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {isBudgetIncomplete ? 'Group Total (Excl. Dynamic Fare)' : 'Grand Group Total'}
                  </div>
                  <div style={{ fontSize: isBudgetIncomplete ? '1.18rem' : '1.45rem', fontWeight: 800, color: isBudgetIncomplete ? '#856404' : 'var(--burgundy)' }}>
                    {isBudgetIncomplete
                      ? `₹${(verifiedDirectTotal + totalEstimated).toLocaleString('en-IN')} + Transport`
                      : `₹${grandTotal.toLocaleString('en-IN')}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Cost Per Pilgrim</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--burgundy-dark)' }}>
                    {costPerPerson !== null ? `₹${costPerPerson.toLocaleString('en-IN')}` : 'Pending Fare'}
                  </div>
                </div>
              </div>

              {/* Target Budget Comparison if provided */}
              {targetBudget !== null && (
                <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.78rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Target Budget: <b>₹{targetBudget.toLocaleString('en-IN')}</b></span>
                  {isWithinBudget ? (
                    <span className="pill pill-success" style={{ fontSize: '0.7rem' }}>
                      Within Budget (Surplus ₹{remainingBudget?.toLocaleString('en-IN')})
                    </span>
                  ) : (
                    <span className="pill" style={{ background: '#FEE2E2', color: '#991B1B', fontSize: '0.7rem' }}>
                      Exceeded by ₹{Math.abs(remainingBudget || 0).toLocaleString('en-IN')}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Excluded Expenses Notice */}
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '6px' }}>
              Excludes voluntary trek pony/palki charges, personal pooja offerings, and Katra market shopping.
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* REQUIREMENT 3: ASK FOR CONFIRMATION BEFORE PROCEEDING     */}
      {/* ========================================================= */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, #FFFCF7 0%, #FFF9F0 100%)',
          border: '2px solid var(--gold-primary)',
          borderRadius: '16px',
          padding: '1.5rem',
          boxShadow: 'var(--shadow-md)',
          marginBottom: '2rem',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: '680px', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', fontWeight: 800, color: 'var(--burgundy)', marginBottom: '8px' }}>
            Are you happy with these selections, or would you like to change anything before proceeding?
          </div>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            You can confirm this recommended plan to proceed directly to the final booking review and human authorization gate, or customize individual transport, hotel, darshan, or sightseeing choices.
          </p>

          <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {/* Path A */}
            <button
              type="button"
              data-testid="confirm-selections-continue-btn"
              onClick={onConfirmSelections}
              className="btn btn-primary"
              style={{
                padding: '0.8rem 2.2rem',
                fontSize: '0.96rem',
                fontWeight: 800,
                boxShadow: '0 4px 14px rgba(88, 17, 26, 0.25)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Check size={16} /> Confirm Selections & Continue <ArrowRight size={16} />
            </button>

            <button
              type="button"
              data-testid="proceed-to-review-btn"
              onClick={onConfirmSelections}
              className="btn btn-outline"
              style={{
                padding: '0.8rem 1.6rem',
                fontSize: '0.96rem',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              Proceed to Review <ArrowRight size={16} />
            </button>

            {/* Path B */}
            <button
              type="button"
              data-testid="change-my-selections-btn"
              onClick={() => setShowCategorySelector(!showCategorySelector)}
              className="btn btn-outline"
              style={{
                padding: '0.8rem 1.8rem',
                fontSize: '0.94rem',
                fontWeight: 700,
                borderColor: 'var(--gold-primary)',
                color: 'var(--burgundy)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Edit3 size={16} /> Change My Selections
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
