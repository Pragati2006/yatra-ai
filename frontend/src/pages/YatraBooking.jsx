import React, { useState, useEffect } from 'react';
import { Compass, AlertCircle, X, ClipboardList, MessageSquare, Check, ArrowRight, MapPin, CheckCircle2, Info, Mountain, RotateCcw } from 'lucide-react';
import TravelSearch from '../components/TravelSearch';
import RecommendedYatra from '../components/RecommendedYatra';
import TransportCard from '../components/TransportCard';
import HotelCard from '../components/HotelCard';
import SightseeingBrowser from '../components/SightseeingBrowser';
import Authorization from '../components/Authorization';
import BookingConfirmation from '../components/BookingConfirmation';
import AIChat from '../components/AIChat';
import AuthModal from '../components/AuthModal';
import {
  searchYatra,
  getAccommodation,
  getSightseeing,
  generateItinerary,
  authorizePlan,
  confirmBooking,
  getAuthMe,
  saveBooking,
  setAuthToken,
} from '../services/api';

const STEPS = [
  { id: 1, label: '1. Preferences' },
  { id: 2, label: '2. Recommended Yatra' },
  { id: 3, label: '3. Booking Review & RPA' },
  { id: 4, label: '4. Confirmation' },
];

const isOptionEqual = (a, b) => {
  if (a === b) return true;
  if (!a || !b) return false;
  const trA = a.transport || a.flight || {};
  const trB = b.transport || b.flight || {};
  if (trA.id && trB.id) return trA.id === trB.id;
  if (trA.transport_no && trB.transport_no) return trA.transport_no === trB.transport_no;
  return trA.operator === trB.operator && trA.departure_time === trB.departure_time && trA.mode === trB.mode;
};

export default function YatraBooking({ 
  initialSearchParams = null, 
  onReturnHome,
  currentUser: propUser = null,
  onRequireAuth: propOnRequireAuth = null,
}) {
  const [currentUser, setCurrentUser] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  const activeUser = propUser || currentUser;

  useEffect(() => {
    if (propUser) return;
    let isMounted = true;
    getAuthMe()
      .then((res) => {
        if (isMounted && res.authenticated && res.user) {
          setCurrentUser(res.user);
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, [propUser]);

  // Planning Mode: null (Choice Screen) | 'form' (Guided Intake) | 'chat' (AI Companion)
  const [planningMode, setPlanningMode] = useState(() => {
    if (initialSearchParams?.planningMode) return initialSearchParams.planningMode;
    if (initialSearchParams?.queryText) return 'form';
    if (initialSearchParams?.sessionId || initialSearchParams?.request || initialSearchParams?.itinerary || initialSearchParams?.options) return 'form';
    return null;
  });
  const [currentStep, setCurrentStep] = useState(() => {
    if (initialSearchParams?.step) return initialSearchParams.step;
    if (initialSearchParams?.options && initialSearchParams.options.length > 0) return 2;
    return 1;
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Session & Version Tracking
  const [sessionId, setSessionId] = useState(() => {
    return initialSearchParams?.sessionId || sessionStorage.getItem('yatra_session_id') || null;
  });
  const [planVersion, setPlanVersion] = useState(() => {
    return initialSearchParams?.planVersion || parseInt(sessionStorage.getItem('yatra_plan_version') || '1', 10);
  });

  useEffect(() => {
    if (sessionId) {
      sessionStorage.setItem('yatra_session_id', sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    if (planVersion) {
      sessionStorage.setItem('yatra_plan_version', String(planVersion));
    }
  }, [planVersion]);

  // Booking Flow State
  const [tripRequest, setTripRequest] = useState(() => initialSearchParams?.request || null);
  const [availableOptions, setAvailableOptions] = useState(() => initialSearchParams?.options || []);
  const [selectedOption, setSelectedOption] = useState(() => initialSearchParams?.selected_option || (initialSearchParams?.options && initialSearchParams.options.length > 0 ? initialSearchParams.options[0] : null));
  const [budgetEvaluation, setBudgetEvaluation] = useState(() => initialSearchParams?.budget_evaluation || null);

  // Flexible Service Preferences & Pilgrims State (Phase 8.8.54A)
  const [includeHotel, setIncludeHotel] = useState(() => {
    if (initialSearchParams?.hotelSelected !== undefined) return initialSearchParams.hotelSelected;
    if (initialSearchParams?.hotel_selected !== undefined) return initialSearchParams.hotel_selected;
    if (initialSearchParams?.booking_handoff?.hotel_selected !== undefined) return initialSearchParams.booking_handoff.hotel_selected;
    return true;
  });
  const [includeTransport, setIncludeTransport] = useState(() => {
    if (initialSearchParams?.transportSelected !== undefined) return initialSearchParams.transportSelected;
    if (initialSearchParams?.transport_selected !== undefined) return initialSearchParams.transport_selected;
    if (initialSearchParams?.booking_handoff?.transport_selected !== undefined) return initialSearchParams.booking_handoff.transport_selected;
    return true;
  });
  const [ownVehicle, setOwnVehicle] = useState(() => {
    if (initialSearchParams?.ownVehicle !== undefined) return initialSearchParams.ownVehicle;
    if (initialSearchParams?.own_vehicle !== undefined) return initialSearchParams.own_vehicle;
    if (initialSearchParams?.booking_handoff?.own_vehicle !== undefined) return initialSearchParams.booking_handoff.own_vehicle;
    return false;
  });

  const initialPaxCount = Math.max(1, parseInt(initialSearchParams?.request?.pax || initialSearchParams?.pax || 2, 10));
  const [pilgrims, setPilgrims] = useState(() => {
    if (Array.isArray(initialSearchParams?.pilgrims) && initialSearchParams.pilgrims.length > 0) {
      return initialSearchParams.pilgrims;
    }
    if (Array.isArray(initialSearchParams?.booking_handoff?.pilgrims) && initialSearchParams.booking_handoff.pilgrims.length > 0) {
      return initialSearchParams.booking_handoff.pilgrims;
    }
    const primaryName = initialSearchParams?.booking_handoff?.primary_contact?.name || activeUser?.name || '';
    const primaryAge = initialSearchParams?.booking_handoff?.primary_contact?.age || '';
    const list = [{ full_name: primaryName, age: primaryAge ? String(primaryAge) : '', gender: 'Male' }];
    while (list.length < initialPaxCount) {
      list.push({ full_name: '', age: '', gender: 'Male' });
    }
    return list;
  });

  const [primaryContact, setPrimaryContact] = useState(() => {
    return initialSearchParams?.primary_contact || initialSearchParams?.booking_handoff?.primary_contact || {
      name: activeUser?.name || '',
      email: activeUser?.email || '',
      phone: activeUser?.phone || '',
    };
  });

  const [prefilledFields, setPrefilledFields] = useState(() => {
    const raw = initialSearchParams?.prefilled_fields || initialSearchParams?.booking_handoff?.prefilled_fields || [];
    return new Set(Array.isArray(raw) ? raw : []);
  });

  // Accommodation State
  const [hotels, setHotels] = useState([]);
  const [selectedHotel, setSelectedHotel] = useState(() => initialSearchParams?.hotel || null);
  const [hotelCategoryFilter, setHotelCategoryFilter] = useState('All');

  // Sightseeing State (All 29 destinations)
  const [allPlaces, setAllPlaces] = useState([]);
  const [selectedPlaces, setSelectedPlaces] = useState([]);
  const [sightseeingChoice, setSightseeingChoice] = useState(() => initialSearchParams?.sightseeing_choice || null);

  // Itinerary State & Feasibility Tracking
  const [itineraryDays, setItineraryDays] = useState(() => initialSearchParams?.itinerary || []);
  const [feasiblePlaces, setFeasiblePlaces] = useState(() => initialSearchParams?.feasible_places || []);
  const [infeasiblePlaces, setInfeasiblePlaces] = useState(() => initialSearchParams?.infeasible_places || []);

  // Confirmation State
  const [confirmationData, setConfirmationData] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [planRevisionNotice, setPlanRevisionNotice] = useState('');

  const loadSightseeing = async () => {
    try {
      const data = await getSightseeing();
      if (data && data.places) {
        setAllPlaces(data.places);
      }
    } catch (err) {
      console.error('Failed to fetch sightseeing destinations:', err);
    }
  };

  const handleSearch = async (params) => {
    setLoading(true);
    setErrorMsg('');
    setPlanRevisionNotice('');
    if (params.hotelSelected !== undefined) setIncludeHotel(params.hotelSelected);
    if (params.transportSelected !== undefined) setIncludeTransport(params.transportSelected);
    if (params.ownVehicle !== undefined) setOwnVehicle(params.ownVehicle);
    if (Array.isArray(params.pilgrims) && params.pilgrims.length > 0) setPilgrims(params.pilgrims);
    if (params.primaryContact) setPrimaryContact(params.primaryContact);
    try {
      const result = await searchYatra(params.queryText);
      const req = {
        origin: params.origin || (result.request?.origin || ''),
        pax: params.pax || 2,
        start_date: params.startDate || '2026-10-20',
        mode: params.mode || 'any',
        category: params.category || 'Normal Darshan',
        duration_days: params.duration || 4,
        total_budget: params.total_budget || null,
        budget_type: params.budget_type || 'total',
        budget_per_person: params.budget_per_person || null,
        travel_style: params.travel_style || 'balanced',
        accommodation_preference: params.accommodation_preference || 'Standard',
        sightseeing_choice: params.sightseeing_choice || 'recommend',
        hotel_selected: params.hotelSelected !== undefined ? params.hotelSelected : includeHotel,
        transport_selected: params.transportSelected !== undefined ? params.transportSelected : includeTransport,
        own_vehicle: params.ownVehicle !== undefined ? params.ownVehicle : ownVehicle,
        pilgrims: params.pilgrims || pilgrims,
        primary_contact: params.primaryContact || primaryContact,
        ...result.request,
      };
      setTripRequest(req);

      if (result.status === 'NO_AVAILABILITY' || result.plan?.status === 'NO_AVAILABILITY') {
        const msg = result.reply || result.plan?.message || `Direct transport availability from ${req.origin} is not present in the current prototype dataset.`;
        setErrorMsg(msg);
        setAvailableOptions([]);
        setSelectedOption(null);
        setSelectedHotel(null);
        return;
      }

      if (result.status === 'NO_COMBINATION' || result.plan?.status === 'NO_COMBINATION') {
        const msg = result.reply || result.plan?.message || 'Found travel options and darshan slots separately, but no timing-safe combination exists.';
        setErrorMsg(msg);
        setAvailableOptions([]);
        setSelectedOption(null);
        setSelectedHotel(null);
        return;
      }

      const plan = result.plan || {};
      const options = plan.options || [];

      if (result.session_id) {
        setSessionId(result.session_id);
      }
      if (result.plan_version) {
        setPlanVersion(result.plan_version);
      }

      if (plan.itinerary) {
        setItineraryDays(plan.itinerary);
      }

      // Refresh feasibility state to prevent stale advisories across search/replanning
      const feasible = result.feasible_places || plan.feasible_places || [];
      const infeasible = result.infeasible_places || plan.infeasible_places || [];
      setFeasiblePlaces(feasible);
      setInfeasiblePlaces(infeasible);
      if (req.sightseeing_choice) {
        setSightseeingChoice(req.sightseeing_choice);
      }

      const budgetEval = result.budget_evaluation || plan.budget_evaluation || null;
      setBudgetEvaluation(budgetEval);

      if (options.length > 0) {
        setAvailableOptions(options);
        const topOption = plan.selected_option || options[0];
        setSelectedOption(topOption);
        setSelectedHotel(plan.hotel || null);
        setCurrentStep(2); // Consolidated "Your Recommended Yatra" Page
      } else {
        setErrorMsg(plan.message || 'No direct options found for this date. Try another date or departure hub.');
      }
    } catch (err) {
      console.error('Yatra Search Error:', err);
      const isMisconfigured = err?.message && (
        err.message.includes('Production API URL') ||
        err.message.includes('Insecure backend URL') ||
        err.message.includes('Malformed API URL')
      );
      setErrorMsg(isMisconfigured
        ? `Backend Disconnected: ${err.message}`
        : 'Search failed. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const applyNavPayload = (payload) => {
    if (!payload) return;
    if (payload.planningMode) {
      setPlanningMode(payload.planningMode);
    } else if (payload.sessionId || payload.request || payload.itinerary || payload.options || payload.queryText) {
      setPlanningMode('form');
    }
    if (payload.sessionId) {
      setSessionId(payload.sessionId);
    }
    if (payload.planVersion) {
      setPlanVersion(payload.planVersion);
    }
    if (payload.itinerary) {
      setItineraryDays(payload.itinerary);
    }
    if (payload.feasible_places) {
      setFeasiblePlaces(payload.feasible_places);
    }
    if (payload.infeasible_places) {
      setInfeasiblePlaces(payload.infeasible_places);
    }
    if (payload.sightseeing_choice) {
      setSightseeingChoice(payload.sightseeing_choice);
    }
    if (payload.request) {
      setTripRequest(payload.request);
    }
    if (payload.options && Array.isArray(payload.options) && payload.options.length > 0) {
      setAvailableOptions(payload.options);
      if (payload.selected_option) {
        const matched = payload.options.find((o) => isOptionEqual(o, payload.selected_option));
        setSelectedOption(matched || payload.selected_option);
      } else {
        setSelectedOption(payload.options[0]);
      }
    } else if (payload.selected_option) {
      setSelectedOption(payload.selected_option);
    }
    if (payload.hotel) {
      setSelectedHotel(payload.hotel);
    }
    if (payload.budget_evaluation) {
      setBudgetEvaluation(payload.budget_evaluation);
    }
    if (payload.hotelSelected !== undefined) {
      setIncludeHotel(payload.hotelSelected);
    } else if (payload.hotel_selected !== undefined) {
      setIncludeHotel(payload.hotel_selected);
    } else if (payload.booking_handoff?.hotel_selected !== undefined) {
      setIncludeHotel(payload.booking_handoff.hotel_selected);
    }

    if (payload.transportSelected !== undefined) {
      setIncludeTransport(payload.transportSelected);
    } else if (payload.transport_selected !== undefined) {
      setIncludeTransport(payload.transport_selected);
    } else if (payload.booking_handoff?.transport_selected !== undefined) {
      setIncludeTransport(payload.booking_handoff.transport_selected);
    }

    if (payload.ownVehicle !== undefined) {
      setOwnVehicle(payload.ownVehicle);
    } else if (payload.own_vehicle !== undefined) {
      setOwnVehicle(payload.own_vehicle);
    } else if (payload.booking_handoff?.own_vehicle !== undefined) {
      setOwnVehicle(payload.booking_handoff.own_vehicle);
    }

    if (Array.isArray(payload.pilgrims) && payload.pilgrims.length > 0) {
      setPilgrims(payload.pilgrims);
    } else if (Array.isArray(payload.booking_handoff?.pilgrims) && payload.booking_handoff.pilgrims.length > 0) {
      setPilgrims(payload.booking_handoff.pilgrims);
    }

    if (payload.primaryContact) {
      setPrimaryContact(payload.primaryContact);
    } else if (payload.primary_contact) {
      setPrimaryContact(payload.primary_contact);
    } else if (payload.booking_handoff?.primary_contact) {
      setPrimaryContact(payload.booking_handoff.primary_contact);
    }

    if (payload.prefilledFields || payload.prefilled_fields || payload.booking_handoff?.prefilled_fields) {
      const raw = payload.prefilledFields || payload.prefilled_fields || payload.booking_handoff?.prefilled_fields;
      setPrefilledFields(new Set(Array.isArray(raw) ? raw : []));
    }

    if (payload.step) {
      setCurrentStep(payload.step);
    } else if ((payload.options && payload.options.length > 0) || (payload.itinerary && payload.itinerary.length > 0)) {
      setCurrentStep(2);
    }
  };

  const [prevSearchParams, setPrevSearchParams] = useState(initialSearchParams);

  if (initialSearchParams !== prevSearchParams) {
    setPrevSearchParams(initialSearchParams);
    if (initialSearchParams) {
      applyNavPayload(initialSearchParams);
    }
  }

  // Auto-search or initialize if parameters provided
  useEffect(() => {
    let isCancelled = false;
    if (initialSearchParams?.queryText) {
      const timer = setTimeout(() => {
        handleSearch(initialSearchParams);
      }, 0);
      return () => clearTimeout(timer);
    } else {
      getSightseeing()
        .then((data) => {
          if (!isCancelled && data && data.places) {
            setAllPlaces(data.places);
          }
        })
        .catch((err) => {
          if (!isCancelled) {
            console.error('Failed to fetch sightseeing destinations:', err);
          }
        });
      return () => {
        isCancelled = true;
      };
    }
  }, [initialSearchParams]);

  const handleChatTripUpdated = (data) => {
    if (!data) return;
    if (data.session_id) setSessionId(data.session_id);
    if (data.plan_version) setPlanVersion(data.plan_version);

    if (data.request) {
      setTripRequest((prev) => ({ ...prev, ...data.request }));
      if (data.request.sightseeing_places && Array.isArray(data.request.sightseeing_places)) {
        const placeObjs = data.request.sightseeing_places.map((p) => {
          if (typeof p === 'object' && p.name) return p;
          const matched = allPlaces.find((ap) => ap.name.toLowerCase() === String(p).toLowerCase());
          return matched || { name: String(p) };
        });
        setSelectedPlaces(placeObjs);
      }
      if (data.request.sightseeing_choice) {
        setSightseeingChoice(data.request.sightseeing_choice);
      }
    }

    if (data.itinerary) {
      setItineraryDays(data.itinerary);
    }
    if (data.feasible_places) {
      setFeasiblePlaces(data.feasible_places);
    }
    if (data.infeasible_places) {
      setInfeasiblePlaces(data.infeasible_places);
    }

    const opts = data.plan?.options || data.pending_options || [];
    if (opts.length > 0) {
      setAvailableOptions(opts);
      if (!selectedOption) setSelectedOption(opts[0]);
    }
  };

  const handleSwitchMode = (targetMode) => {
    setErrorMsg('');
    if (targetMode === 'chat') {
      setPlanningMode('chat');
    } else if (targetMode === 'form') {
      setPlanningMode('form');
      if (!currentStep || currentStep === 1) {
        if ((availableOptions && availableOptions.length > 0) || (itineraryDays && itineraryDays.length > 0)) {
          setCurrentStep(2);
        } else {
          setCurrentStep(1);
        }
      }
    } else {
      setPlanningMode(null);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Step 2 -> Step 3: Load Hotels
  const handleProceedToHotels = async () => {
    if (!selectedOption) {
      setErrorMsg('Please select a travel & darshan option to proceed.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      const checkIn = tripRequest?.start_date || '2026-10-20';
      const data = await getAccommodation({
        check_in_date: checkIn,
        category: hotelCategoryFilter !== 'All' ? hotelCategoryFilter : null,
      });

      if (data && data.hotels) {
        setHotels(data.hotels);
        if (data.hotels.length > 0 && !selectedHotel) {
          setSelectedHotel(data.hotels[0]); // default select first only if none selected
        }
      }
      setCurrentStep('edit-accommodation'); // Move to Accommodation
    } catch (err) {
      console.error('Hotel fetch error:', err);
      setErrorMsg('Unable to fetch hotels. You may proceed without a hotel reservation.');
      setCurrentStep('edit-accommodation');
    } finally {
      setLoading(false);
    }
  };


  // Step 4 -> Step 5: Build Itinerary
  const handleGenerateItinerary = async () => {
    const placeNames = selectedPlaces.map((p) => (typeof p === 'object' && p.name ? p.name : String(p)));
    const choice = placeNames.length > 0 ? 'selected' : (sightseeingChoice || 'later');

    if (!selectedOption) {
      if (availableOptions && availableOptions.length > 0) {
        setSelectedOption(availableOptions[0]);
      } else {
        setCurrentStep(1);
        setErrorMsg('Destinations selected! Please confirm your travel dates and departure city to generate your full itinerary.');
        return;
      }
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const data = await generateItinerary({
        option: selectedOption || availableOptions[0],
        hotel: selectedHotel,
        hotel_nights: 2,
        sightseeing_places: placeNames,
        request: {
          ...tripRequest,
          sightseeing_places: placeNames,
          sightseeing_choice: choice,
        },
      });

      if (data && data.itinerary) {
        setItineraryDays(data.itinerary);
        // Refresh feasibility metadata to ensure no stale data from prior plans
        setFeasiblePlaces(Array.isArray(data.feasible_places) ? data.feasible_places : []);
        setInfeasiblePlaces(Array.isArray(data.infeasible_places) ? data.infeasible_places : []);
        setSightseeingChoice(choice);
        triggerPlanRevision('sightseeing destinations');
        setCurrentStep(2);
      } else {
        setErrorMsg('Itinerary generation returned empty plan.');
      }
    } catch (err) {
      console.error('Itinerary error:', err);
      setErrorMsg('Failed to generate customized itinerary.');
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Handle "Choose Later" for Sightseeing
  const handleChooseLater = async () => {
    setSelectedPlaces([]);
    setSightseeingChoice('later');
    setFeasiblePlaces([]);
    setInfeasiblePlaces([]);
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await generateItinerary({
        option: selectedOption,
        hotel: selectedHotel,
        hotel_nights: 2,
        sightseeing_places: [],
        request: {
          ...tripRequest,
          sightseeing_choice: 'later',
        },
      });

      if (data && data.itinerary) {
        setItineraryDays(data.itinerary);
        setFeasiblePlaces(Array.isArray(data.feasible_places) ? data.feasible_places : []);
        setInfeasiblePlaces(Array.isArray(data.infeasible_places) ? data.infeasible_places : []);
        triggerPlanRevision('sightseeing set to later');
        setCurrentStep(2);
      } else {
        setErrorMsg('Itinerary generation returned empty plan.');
      }
    } catch (err) {
      console.error('Itinerary error:', err);
      setErrorMsg('Failed to generate customized itinerary.');
    } finally {
      setLoading(false);
    }
  };

  // Step 6: Confirm Booking
  const handleConfirmBooking = async (authorized) => {
    if (!authorized) {
      setErrorMsg('Human authorization is required to proceed with booking.');
      return;
    }

    // Compulsory Authentication Gate (Requirement 6)
    if (!activeUser) {
      if (propOnRequireAuth) {
        propOnRequireAuth();
      } else {
        setShowAuthModal(true);
      }
      return;
    }

    setConfirming(true);
    setErrorMsg('');
    try {
      if (sessionId) {
        await authorizePlan({
          session_id: sessionId,
          plan_version: planVersion || 1,
        });
      }

      const userName = activeUser.name || activeUser.email || activeUser.phone || 'Devotee';
      const formattedPilgrims = pilgrims && pilgrims.length > 0 ? pilgrims.map(p => ({
        full_name: (p.full_name || '').trim() || 'Devotee',
        age: parseInt(p.age, 10) || 30,
        gender: p.gender || 'Male',
      })) : [{ full_name: userName, age: 35, gender: 'Male' }];

      const data = await confirmBooking({
        option: selectedOption,
        pax: tripRequest?.pax || formattedPilgrims.length || 1,
        user_name: userName,
        hotel: selectedHotel,
        hotel_nights: Math.max(1, (tripRequest?.duration_days || 4) - 1),
        sightseeing_places: selectedPlaces.map((p) => p.name),
        human_authorized: true,
        session_id: sessionId,
        plan_version: planVersion || 1,
        pilgrims: formattedPilgrims,
        primary_contact: primaryContact,
        hotel_selected: includeHotel,
        transport_selected: includeTransport,
        own_vehicle: ownVehicle,
        start_date: selectedOption?.slot?.slot_date || tripRequest?.start_date,
        return_date: tripRequest?.return_date,
        duration: tripRequest?.duration_days,
        budget: tripRequest?.total_budget,
      });

      if (data && data.status === 'success') {
        setConfirmationData(data);
        setCurrentStep(7);
        // Persist booking to authenticated user account (Requirement 7)
        if (data.booking_id) {
          try {
            await saveBooking({
              booking_id: data.booking_id,
              pax_count: tripRequest?.pax || formattedPilgrims.length || 1,
              slot_date: selectedOption?.slot?.slot_date || tripRequest?.start_date || '2026-10-20',
              category: selectedOption?.slot?.category || 'Normal Darshan',
              slot_time: selectedOption?.slot?.slot_time || 'Morning (06:00)',
              transport_mode: ownVehicle ? 'Own Vehicle' : (!includeTransport ? 'Self-arranged' : (selectedOption?.transport?.mode || 'Train')),
              transport_info: ownVehicle ? 'Personal Vehicle / Car' : (!includeTransport ? 'Self-arranged Transport' : (selectedOption?.transport?.name || 'Express Service')),
              hotel_name: includeHotel && selectedHotel?.name ? selectedHotel.name : 'Accommodation not selected',
              total_price: data.total_price || selectedOption?.total_price || 0,
              session_id: sessionId,
              plan_version: planVersion || 1,
              pilgrims: formattedPilgrims,
              primary_contact: primaryContact,
              hotel_selected: includeHotel,
              transport_selected: includeTransport,
              own_vehicle: ownVehicle,
              start_date: selectedOption?.slot?.slot_date || tripRequest?.start_date,
              return_date: tripRequest?.return_date,
              duration: tripRequest?.duration_days,
              receipt: data.receipt || {},
            });
          } catch (e) {
            console.warn('Booking persistence warning:', e);
          }
        }
      } else {
        setErrorMsg(data.message || 'Booking confirmation returned error.');
      }
    } catch (err) {
      console.error('Confirmation error:', err);
      setErrorMsg('Booking confirmation failed. Please check backend connection.');
    } finally {
      setConfirming(false);
    }
  };


  const triggerPlanRevision = (reason) => {
    setPlanVersion((prev) => {
      const nextVer = prev + 1;
      setPlanRevisionNotice(`Trip ${reason} updated (Plan Revision #${nextVer}). Prior authorization has been reset. Please review your updated plan.`);
      return nextVer;
    });
  };

  const handleSelectOption = (opt) => {
    if (!isOptionEqual(selectedOption, opt)) {
      setSelectedOption(opt);
      triggerPlanRevision('transport option');
    }
  };

  const handleSelectHotel = (h) => {
    if (selectedHotel?.name !== h.name) {
      setSelectedHotel(h);
      triggerPlanRevision('accommodation');
    }
  };


  const handleSkipSightseeing = async () => {
    setSelectedPlaces([]);
    setSightseeingChoice('skipped');
    setFeasiblePlaces([]);
    setInfeasiblePlaces([]);
    triggerPlanRevision('sightseeing skipped');
    setLoading(true);
    setErrorMsg('');
    try {
      const activeOpt = selectedOption || availableOptions[0];
      const data = await generateItinerary({
        option: activeOpt,
        hotel: selectedHotel,
        hotel_nights: 2,
        sightseeing_places: [],
        request: {
          ...tripRequest,
          sightseeing_places: [],
          sightseeing_choice: 'skipped',
        },
      });
      if (data && data.itinerary) {
        setItineraryDays(data.itinerary);
        setFeasiblePlaces([]);
        setInfeasiblePlaces([]);
      }
      setCurrentStep(6);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      console.error('Skip sightseeing error:', err);
      setCurrentStep(6);
    } finally {
      setLoading(false);
    }
  };

  const togglePlaceSelection = (place) => {
    const targetName = typeof place === 'object' && place.name ? place.name : String(place);
    const exists = selectedPlaces.some((p) => {
      const pName = typeof p === 'object' && p.name ? p.name : String(p);
      return pName.toLowerCase() === targetName.toLowerCase();
    });
    if (exists) {
      setSelectedPlaces(selectedPlaces.filter((p) => {
        const pName = typeof p === 'object' && p.name ? p.name : String(p);
        return pName.toLowerCase() !== targetName.toLowerCase();
      }));
    } else {
      setSelectedPlaces([...selectedPlaces, place]);
    }
    triggerPlanRevision('sightseeing destination');
  };

  return (
    <div className="page-container">
      {/* Global Error Notice */}
      {errorMsg && (
        <div style={{
          background: '#FFF4F4',
          border: '1.5px solid #F5C6CB',
          color: '#721C24',
          borderRadius: '12px',
          padding: '12px 18px',
          marginBottom: '1.5rem',
          fontSize: '0.86rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertCircle size={16} /> <b>Alert:</b> {errorMsg}
          </div>
          <button
            onClick={() => setErrorMsg('')}
            style={{ background: 'none', border: 'none', fontSize: '1rem', cursor: 'pointer', color: '#721C24', display: 'flex', alignItems: 'center' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ========================================================= */}
      {/* CHOICE SCREEN: PLAN WITH FORM vs CHAT WITH AI */}
      {/* ========================================================= */}
      {planningMode === null && (
        <div data-testid="choice-screen" style={{ maxWidth: '960px', margin: '1rem auto 3.5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: '#FAF5EE',
              border: '1px solid var(--gold-border)',
              borderRadius: '20px',
              padding: '6px 16px',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: 'var(--burgundy)',
              marginBottom: '1rem',
            }}>
              <Compass size={16} /> Shri Mata Vaishno Devi Yatra Planning
            </div>
            <h1 style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '2.3rem',
              fontWeight: 800,
              color: 'var(--burgundy)',
              marginBottom: '0.75rem',
              lineHeight: 1.25,
            }}>
              Choose How You Wish to Plan Your Yatra
            </h1>
            <p style={{
              fontSize: '1rem',
              color: 'var(--text-muted)',
              maxWidth: '650px',
              margin: '0 auto',
              lineHeight: 1.6,
            }}>
              Personalize your sacred pilgrimage with our intelligent planning system. Choose between a structured, guided form or an interactive conversational AI companion. Both methods synchronize with the same verified transport, darshan slots, Katra stays, and realistic itinerary engine.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '24px',
            alignItems: 'stretch',
          }}>
            {/* Option 1: Plan with a Form */}
            <div
              data-testid="choice-form-card"
              style={{
                background: 'var(--card-bg, #FFFFFF)',
                border: '1.5px solid var(--gold-border, #E4D5B7)',
                borderRadius: '16px',
                padding: '2.25rem 2rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 8px 24px rgba(61, 8, 16, 0.06)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                  <ClipboardList size={36} color="var(--burgundy)" />
                  <span style={{
                    background: '#FAF5EE',
                    border: '1px solid var(--gold-border)',
                    color: 'var(--burgundy)',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    padding: '4px 10px',
                    borderRadius: '12px',
                  }}>
                    Structured & Direct
                  </span>
                </div>
                <h2 style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: '1.55rem',
                  fontWeight: 800,
                  color: 'var(--burgundy)',
                  marginBottom: '0.75rem',
                }}>
                  Plan with a Form
                </h2>
                <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
                  A guided, step-by-step intake form to configure your departure city, travel dates, pilgrim count, transport preference, darshan slot, hotel tier, budget, and travel pace.
                </p>

                <ul style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: '0 0 1.75rem 0',
                  fontSize: '0.88rem',
                  color: 'var(--text-dark, #2D3748)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Guided step-by-step preference intake
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Compare direct train & flight options
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Select Katra hotels and sightseeing spots
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Clear timeline with feasibility advisories
                  </li>
                </ul>
              </div>

              <button
                data-testid="select-form-btn"
                onClick={() => handleSwitchMode('form')}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '12px 20px',
                  fontSize: '1rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                <span>Plan with Form</span>
                <ArrowRight size={16} />
              </button>
            </div>

            {/* Option 2: Chat with AI */}
            <div
              data-testid="choice-chat-card"
              style={{
                background: 'var(--card-bg, #FFFFFF)',
                border: '1.5px solid var(--gold-border, #E4D5B7)',
                borderRadius: '16px',
                padding: '2.25rem 2rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 8px 24px rgba(61, 8, 16, 0.06)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                  <MessageSquare size={36} color="#166534" />
                  <span style={{
                    background: '#F0FDF4',
                    border: '1px solid #BBF7D0',
                    color: '#166534',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    padding: '4px 10px',
                    borderRadius: '12px',
                  }}>
                    Conversational & Flexible
                  </span>
                </div>
                <h2 style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: '1.55rem',
                  fontWeight: 800,
                  color: 'var(--burgundy)',
                  marginBottom: '0.75rem',
                }}>
                  Chat with AI
                </h2>
                <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
                  A conversational AI interface. Describe your pilgrimage vision naturally, ask questions regarding Katra weather, darshan slots, or local sights, and let AI build your plan.
                </p>

                <ul style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: '0 0 1.75rem 0',
                  fontSize: '0.88rem',
                  color: 'var(--text-dark, #2D3748)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Natural speech and text conversation
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Answers tourism, weather & yatra queries
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> AI gathers missing details conversationally
                  </li>
                  <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Check size={14} color="#2E7D32" strokeWidth={3} /> Switch back to form with preserved state
                  </li>
                </ul>
              </div>

              <button
                data-testid="select-chat-btn"
                onClick={() => handleSwitchMode('chat')}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '12px 20px',
                  fontSize: '1rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                <span>Chat with AI</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* CHAT-BASED PLANNING WORKSPACE */}
      {/* ========================================================= */}
      {planningMode === 'chat' && (
        <div data-testid="chat-planning-workspace" style={{ maxWidth: '980px', margin: '0 auto 3rem' }}>
          {/* Top Mode Switcher Bar */}
          <div
            data-testid="mode-switcher-bar"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#FAF5EE',
              border: '1px solid var(--gold-border)',
              borderRadius: '12px',
              padding: '10px 18px',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <MessageSquare size={18} color="var(--burgundy)" />
              <div>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Planning Mode: </span>
                <b style={{ color: 'var(--burgundy)', fontSize: '0.9rem' }}>Conversational AI Assistant</b>
                {tripRequest?.origin && (
                  <span style={{ marginLeft: '10px', fontSize: '0.8rem', background: '#FFFFFF', padding: '2px 8px', borderRadius: '8px', border: '1px solid var(--gold-border)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <MapPin size={11} /> {tripRequest.origin} • {tripRequest.pax || 2} Pilgrims • {tripRequest.duration_days || 4} Days
                  </span>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => handleSwitchMode(null)}
                className="btn btn-outline"
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                title="Change planning method"
              >
                Change Method
              </button>
              <button
                data-testid="switch-to-form-btn"
                onClick={() => handleSwitchMode('form')}
                className="btn btn-primary"
                style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <ClipboardList size={14} /> Switch to Form
              </button>
            </div>
          </div>

          {/* Shared Trip Context Notice if plan or itinerary active */}
          {itineraryDays && itineraryDays.length > 0 && (
            <div
              data-testid="chat-shared-trip-badge"
              style={{
                background: '#F0FDF4',
                border: '1px solid #BBF7D0',
                borderRadius: '10px',
                padding: '10px 16px',
                marginBottom: '1.25rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
                fontSize: '0.85rem',
                color: '#166534',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <CheckCircle2 size={16} color="#166534" />
                <span>
                  <b>Active Itinerary Synced:</b> {itineraryDays.length}-Day Plan
                  {tripRequest?.origin ? ` from ${tripRequest.origin}` : ''}
                  {feasiblePlaces.length > 0 ? ` • Feasible: ${feasiblePlaces.join(', ')}` : ''}
                  {infeasiblePlaces.length > 0 ? ` • Infeasible: ${infeasiblePlaces.map(p => (typeof p === 'object' ? p.destination || p.name : p)).join(', ')}` : ''}
                </span>
              </div>
              <button
                onClick={() => {
                  setCurrentStep(2);
                  setPlanningMode('form');
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#166534',
                  textDecoration: 'underline',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                View Full Timeline in Form <ArrowRight size={14} />
              </button>
            </div>
          )}

          <AIChat
            sharedTripRequest={tripRequest}
            sharedSessionId={sessionId}
            sharedPlanVersion={planVersion}
            onTripUpdated={handleChatTripUpdated}
            onSwitchToForm={(payload) => {
              if (payload) {
                applyNavPayload(payload);
              } else {
                handleSwitchMode('form');
              }
            }}
            onNavigateToBooking={(payload) => {
              if (payload) {
                applyNavPayload(payload);
              } else {
                handleSwitchMode('form');
              }
            }}
          />
        </div>
      )}

      {/* ========================================================= */}
      {/* FORM-BASED PLANNING WORKSPACE */}
      {/* ========================================================= */}
      {planningMode === 'form' && (
        <div>
          {/* Top Mode Switcher Bar */}
          <div
            data-testid="mode-switcher-bar"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#FAF5EE',
              border: '1px solid var(--gold-border)',
              borderRadius: '12px',
              padding: '10px 18px',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <ClipboardList size={18} color="var(--burgundy)" />
              <div>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Planning Mode: </span>
                <b style={{ color: 'var(--burgundy)', fontSize: '0.9rem' }}>Guided Structured Form</b>
                {tripRequest?.origin && (
                  <span style={{ marginLeft: '10px', fontSize: '0.8rem', background: '#FFFFFF', padding: '2px 8px', borderRadius: '8px', border: '1px solid var(--gold-border)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <MapPin size={11} /> {tripRequest.origin} • {tripRequest.pax || 2} Pilgrims • {tripRequest.duration_days || 4} Days
                  </span>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => handleSwitchMode(null)}
                className="btn btn-outline"
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                title="Change planning method"
              >
                Change Method
              </button>
              <button
                data-testid="switch-to-chat-btn"
                onClick={() => handleSwitchMode('chat')}
                className="btn btn-primary"
                style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <MessageSquare size={14} /> Switch to Chat
              </button>
            </div>
          </div>

          {/* Stepper Breadcrumb */}
          {(() => {
            const getNormalizedStep = (step) => {
              if (step === 1) return 1;
              if (step === 2 || String(step).startsWith('edit-') || step === 'transport' || step === 'accommodation' || step === 'sightseeing') return 2;
              if (step === 3 || step === 6) return 3;
              if (step === 4 || step === 7 || step === 'confirmation') return 4;
              return 1;
            };
            const normStep = getNormalizedStep(currentStep);

            return (
              <div className="stepper-container" data-testid="main-4-step-stepper">
                {STEPS.map((step) => {
                  let isCompleted = false;
                  if (step.id === 1) {
                    isCompleted = (availableOptions.length > 0 && normStep > 1) || normStep > 1;
                  } else if (step.id === 2) {
                    isCompleted = normStep > 2;
                  } else if (step.id === 3) {
                    isCompleted = normStep > 3 || Boolean(confirmationData?.booking_id);
                  } else if (step.id === 4) {
                    isCompleted = Boolean(confirmationData?.booking_id) && normStep === 4;
                  }

                  const isActive = normStep === step.id;
                  const isClickable = (
                    (step.id === 1) ||
                    (step.id === 2 && availableOptions.length > 0) ||
                    (step.id === 3 && availableOptions.length > 0) ||
                    (step.id === 4 && Boolean(confirmationData?.booking_id))
                  );

                  return (
                    <React.Fragment key={step.id}>
                      <div
                        className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                        data-testid={`step-pill-${step.id}`}
                        data-step-item={`main-step-${step.id}-item`}
                        onClick={() => {
                          if (isClickable) {
                            if (step.id === 1) setCurrentStep(1);
                            else if (step.id === 2) setCurrentStep(2);
                            else if (step.id === 3) setCurrentStep(3);
                            else if (step.id === 4 && confirmationData?.booking_id) setCurrentStep(4);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }
                        }}
                        style={{ cursor: isClickable ? 'pointer' : 'not-allowed', opacity: !isClickable && step.id === 4 ? 0.6 : 1 }}
                        title={isClickable ? `Navigate to ${step.label}` : (step.id === 4 ? 'Complete booking verification to unlock confirmation' : 'Complete search to unlock')}
                      >
                        <div className="step-circle">
                          {isCompleted ? <Check size={12} strokeWidth={3} /> : step.id}
                        </div>
                        <span>{step.label}</span>
                      </div>
                      {step.id < STEPS.length && <div className="step-divider" />}
                    </React.Fragment>
                  );
                })}
              </div>
            );
          })()}

          {/* Plan Revision & Invalidation Notice */}
          {planRevisionNotice && (
            <div style={{
              background: '#FFF9E6',
              border: '1.5px solid var(--gold-border)',
              color: '#8A5800',
              borderRadius: '10px',
              padding: '10px 14px',
              marginBottom: '1.25rem',
              fontSize: '0.84rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={15} /> <b>Plan Preference Updated:</b> {planRevisionNotice}
              </div>
              <button
                type="button"
                onClick={() => setPlanRevisionNotice('')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem', color: '#8A5800', display: 'flex', alignItems: 'center' }}
              >
                <X size={15} />
              </button>
            </div>
          )}

          {/* STEP 1: TRAVEL & DARSHAN SEARCH */}
          {currentStep === 1 && (
            <div>
              <TravelSearch
                onSearch={handleSearch}
                loading={loading}
                initialValues={{
                  origin: tripRequest?.origin || '',
                  pax: tripRequest?.pax || pilgrims.length || 2,
                  startDate: tripRequest?.start_date || '2026-10-20',
                  returnDate: tripRequest?.return_date || '',
                  mode: tripRequest?.mode || 'any',
                  category: tripRequest?.category || 'Normal Darshan',
                  duration: tripRequest?.duration_days || 4,
                  budgetType: tripRequest?.budget_type || 'total',
                  budgetAmount: tripRequest?.total_budget || 15000,
                  travelStyle: tripRequest?.travel_style || 'balanced',
                  accommodationPreference: tripRequest?.accommodation_preference || 'Standard',
                  sightseeingChoice: sightseeingChoice || tripRequest?.sightseeing_choice || 'recommend',
                  hotelSelected: includeHotel,
                  transportSelected: includeTransport,
                  ownVehicle: ownVehicle,
                  pilgrims: pilgrims,
                  primaryContact: primaryContact,
                  prefilledFields: prefilledFields,
                }}
              />
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 2: CONSOLIDATED "YOUR RECOMMENDED YATRA" PAGE        */}
          {/* ========================================================= */}
          {currentStep === 2 && (
            <RecommendedYatra
              planData={{
                selected_option: selectedOption,
                options: availableOptions,
                hotel: selectedHotel,
                itinerary: itineraryDays,
                feasible_places: feasiblePlaces,
                infeasible_places: infeasiblePlaces,
                budget_evaluation: budgetEvaluation,
                hotel_selected: includeHotel,
                transport_selected: includeTransport,
                own_vehicle: ownVehicle,
                pilgrims: pilgrims,
              }}
              tripRequest={{
                ...tripRequest,
                hotel_selected: includeHotel,
                transport_selected: includeTransport,
                own_vehicle: ownVehicle,
                pilgrims: pilgrims,
              }}
              sessionId={sessionId}
              planVersion={planVersion}
              planRevisionNotice={planRevisionNotice}
              onConfirmSelections={() => {
                setCurrentStep(3);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              onEditCategory={(category) => {
                if (category === 'transport' || category === 'darshan') {
                  setCurrentStep('edit-transport');
                } else if (category === 'accommodation') {
                  if (hotels.length === 0) {
                    handleProceedToHotels();
                  } else {
                    setCurrentStep('edit-accommodation');
                  }
                } else if (category === 'sightseeing') {
                  if (allPlaces.length === 0) {
                    loadSightseeing();
                  }
                  setCurrentStep('edit-sightseeing');
                } else if (category === 'dates' || category === 'budget' || category === 'style') {
                  setCurrentStep(1);
                  setPlanRevisionNotice(`Editing ${category}: Adjust your preference fields below and click "Search Yatra Options" to refresh recommendations.`);
                }
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          )}

          {/* ========================================================= */}
          {/* EDIT VIEW: TRANSPORT & DARSHAN SLOT SELECTION             */}
          {/* ========================================================= */}
          {(currentStep === 'edit-transport' || currentStep === 'transport') && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.3rem', color: 'var(--burgundy)' }}>
                    Customize Travel & Darshan Option
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Found <b>{availableOptions.length} verified distinct option{availableOptions.length !== 1 ? 's' : ''}</b> for {tripRequest?.origin || 'your origin'} to Katra. Your accommodation and itinerary will be preserved.
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    data-testid="return-to-recommended-yatra-btn"
                    onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    className="btn btn-primary"
                    style={{ fontSize: '0.85rem', padding: '6px 16px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    <RotateCcw size={14} /> Return to Recommended Yatra
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '2rem' }}>
                {availableOptions.map((opt, i) => (
                  <TransportCard
                    key={i}
                    option={opt}
                    pax={tripRequest?.pax || 1}
                    isSelected={isOptionEqual(selectedOption, opt)}
                    onSelect={() => handleSelectOption(opt)}
                  />
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <button
                  type="button"
                  data-testid="transport-back-to-review-btn"
                  onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  className="btn btn-outline"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <RotateCcw size={14} /> Return to Recommended Yatra
                </button>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    data-testid="transport-review-direct-btn"
                    onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    disabled={!selectedOption || loading}
                    className="btn btn-outline"
                    style={{ borderColor: 'var(--gold-primary)', color: 'var(--burgundy)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <ClipboardList size={14} /> Save Selection & Return <ArrowRight size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={handleProceedToHotels}
                    disabled={!selectedOption || loading}
                    className="btn btn-primary"
                    style={{ padding: '0.75rem 2rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    {loading ? (
                      'Finding Hotels...'
                    ) : (
                      <>
                        Proceed to Accommodation <ArrowRight size={14} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* EDIT VIEW: ACCOMMODATION SELECTION                        */}
          {/* ========================================================= */}
          {(currentStep === 'edit-accommodation' || currentStep === 'accommodation') && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 800, fontSize: '1.3rem', color: 'var(--burgundy)' }}>
                    Customize Katra Accommodation
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Select certified pilgrim guest houses, shrine bhawan lodges, or deluxe hotels
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {['All', 'Standard', 'Deluxe', 'Heritage'].map((cat) => (
                    <button
                      key={cat}
                      onClick={async () => {
                        setHotelCategoryFilter(cat);
                        setLoading(true);
                        try {
                          const checkIn = tripRequest?.start_date || '2026-10-20';
                          const data = await getAccommodation({
                            check_in_date: checkIn,
                            category: cat !== 'All' ? cat : null,
                          });
                          if (data && data.hotels) setHotels(data.hotels);
                        } finally {
                          setLoading(false);
                        }
                      }}
                      className={`btn ${hotelCategoryFilter === cat ? 'btn-primary' : 'btn-outline'}`}
                      style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                    >
                      {cat}
                    </button>
                  ))}
                  <button
                    type="button"
                    data-testid="return-to-recommended-yatra-btn"
                    onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    className="btn btn-primary"
                    style={{ fontSize: '0.85rem', padding: '6px 14px', marginLeft: '6px' }}
                  >
                    ↩ Return to Recommended Yatra
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '2rem' }}>
                {hotels
                  .filter((h) => hotelCategoryFilter === 'All' || h.category === hotelCategoryFilter)
                  .map((hotel, i) => (
                    <HotelCard
                      key={i}
                      hotel={hotel}
                      isSelected={selectedHotel?.name === hotel.name}
                      onSelect={() => handleSelectHotel(hotel)}
                    />
                  ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <button
                  type="button"
                  data-testid="hotel-back-to-review-btn"
                  onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  className="btn btn-outline"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <RotateCcw size={14} /> Return to Recommended Yatra
                </button>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    data-testid="hotel-review-direct-btn"
                    onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    disabled={loading}
                    className="btn btn-outline"
                    style={{ borderColor: 'var(--gold-primary)', color: 'var(--burgundy)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <ClipboardList size={14} /> Save Selection & Return <ArrowRight size={14} />
                  </button>
                  <button
                    onClick={() => { setSelectedHotel(null); triggerPlanRevision('hotel removed'); setCurrentStep(2); }}
                    className="btn btn-outline"
                  >
                    Remove Hotel
                  </button>
                  <button
                    onClick={() => {
                      if (allPlaces.length === 0) loadSightseeing();
                      setCurrentStep('edit-sightseeing');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    className="btn btn-primary"
                    style={{ padding: '0.75rem 2rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    Proceed to Sightseeing ({selectedPlaces.length} selected) <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* EDIT VIEW: SIGHTSEEING SELECTION (All 29 Destinations)     */}
          {/* ========================================================= */}
          {(currentStep === 'edit-sightseeing' || currentStep === 'sightseeing') && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ fontSize: '0.9rem', color: 'var(--burgundy)', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Mountain size={16} /> Customizing Jammu & Kashmir Sightseeing
                </div>
                <button
                  type="button"
                  data-testid="return-to-recommended-yatra-btn"
                  onClick={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  className="btn btn-outline"
                  style={{ fontSize: '0.82rem', padding: '5px 14px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <RotateCcw size={14} /> Return to Recommended Yatra
                </button>
              </div>

              <SightseeingBrowser
                places={allPlaces}
                selectedPlaces={selectedPlaces}
                onToggleSelect={togglePlaceSelection}
                onGenerateItinerary={handleGenerateItinerary}
                onChooseLater={handleChooseLater}
                onSkipSightseeing={handleSkipSightseeing}
                onReviewTripDirectly={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                returnedFromReview={true}
                onBack={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                loading={loading}
                tripRequest={tripRequest}
              />
            </div>
          )}

          {/* ========================================================= */}
          {/* STEP 3: HUMAN AUTHORIZATION & PLAYWRIGHT RPA (FINAL REVIEW)*/}
          {/* ========================================================= */}
          {(currentStep === 3 || currentStep === 6) && (
            <Authorization
              bookingSummary={{
                option: selectedOption,
                pax: tripRequest?.pax || pilgrims.length || 1,
                hotel: selectedHotel,
                hotelNights: Math.max(1, (tripRequest?.duration_days || 4) - 1),
                sightseeingPlaces: selectedPlaces,
                feasiblePlaces: feasiblePlaces,
                infeasiblePlaces: infeasiblePlaces,
                origin: tripRequest?.origin || '',
                sessionId: sessionId,
                planVersion: planVersion,
                tripRequest: tripRequest,
                itineraryDays: itineraryDays,
                pilgrims: pilgrims,
                primaryContact: primaryContact,
                hotelSelected: includeHotel,
                transportSelected: includeTransport,
                ownVehicle: ownVehicle,
              }}
              currentUser={activeUser}
              onRequireAuth={() => {
                if (propOnRequireAuth) {
                  propOnRequireAuth();
                } else {
                  setShowAuthModal(true);
                }
              }}
              onNavigateToConfirmation={(confirmedResult) => {
                setConfirmationData(confirmedResult);
                setCurrentStep(4);
                window.scrollTo({ top: 0, behavior: 'smooth' });
                if (activeUser && confirmedResult?.booking_id) {
                  const bPrice = confirmedResult.total_price || selectedOption?.total_price || 0;
                  const formattedPilgrims = pilgrims && pilgrims.length > 0 ? pilgrims.map(p => ({
                    full_name: (p.full_name || '').trim() || 'Devotee',
                    age: parseInt(p.age, 10) || 30,
                    gender: p.gender || 'Male',
                  })) : [{ full_name: activeUser?.name || 'Devotee', age: 35, gender: 'Male' }];
                  saveBooking({
                    booking_id: confirmedResult.booking_id,
                    pax_count: tripRequest?.pax || formattedPilgrims.length || 1,
                    slot_date: selectedOption?.slot?.slot_date || tripRequest?.start_date || '2026-10-20',
                    category: selectedOption?.slot?.category || 'Normal Darshan',
                    slot_time: selectedOption?.slot?.slot_time || 'Morning (06:00)',
                    transport_mode: ownVehicle ? 'Own Vehicle' : (!includeTransport ? 'Self-arranged' : (selectedOption?.transport?.mode || 'Train')),
                    transport_info: ownVehicle ? 'Personal Vehicle / Car' : (!includeTransport ? 'Self-arranged Transport' : (selectedOption?.transport?.name || (tripRequest?.origin ? `${selectedOption?.transport?.mode || 'Train'} from ${tripRequest.origin}` : `${selectedOption?.transport?.mode || 'Train'} to Katra`))),
                    hotel_name: includeHotel && selectedHotel?.name ? selectedHotel.name : 'Accommodation not selected',
                    total_price: bPrice,
                    session_id: sessionId,
                    plan_version: planVersion || 1,
                    pilgrims: formattedPilgrims,
                    primary_contact: primaryContact,
                    hotel_selected: includeHotel,
                    transport_selected: includeTransport,
                    own_vehicle: ownVehicle,
                    start_date: selectedOption?.slot?.slot_date || tripRequest?.start_date,
                    return_date: tripRequest?.return_date,
                    duration: tripRequest?.duration_days,
                    receipt: {
                      booking_id: confirmedResult.booking_id,
                      user_name: activeUser?.name || activeUser?.email || 'Pilgrim Devotee',
                      email: activeUser?.email,
                      pax_count: tripRequest?.pax || formattedPilgrims.length || 1,
                      origin: tripRequest?.origin || '',
                      destination: 'Katra (Shri Mata Vaishno Devi)',
                      slot_date: selectedOption?.slot?.slot_date || tripRequest?.start_date || '2026-10-20',
                      category: selectedOption?.slot?.category || 'Normal Darshan',
                      slot_time: selectedOption?.slot?.slot_time || 'Morning (06:00)',
                      transport_info: ownVehicle ? 'Personal Vehicle / Car' : (!includeTransport ? 'Self-arranged Transport' : (selectedOption?.transport?.name || (tripRequest?.origin ? `${selectedOption?.transport?.mode || 'Train'} from ${tripRequest.origin}` : `${selectedOption?.transport?.mode || 'Train'} to Katra`))),
                      hotel_name: includeHotel && selectedHotel?.name ? selectedHotel.name : 'Accommodation not selected',
                      total_price: bPrice,
                      confirmed_at: new Date().toISOString(),
                      portal_label: 'LOCAL MOCK PORTAL / DEMO',
                      disclaimer: 'NOT AN OFFICIAL SHRINE BOARD BOOKING',
                      pilgrims: formattedPilgrims,
                      primary_contact: primaryContact,
                      hotel_selected: includeHotel,
                      transport_selected: includeTransport,
                      own_vehicle: ownVehicle,
                    },
                  }).catch((err) => console.warn('Account sync notice:', err));
                }
              }}
              onConfirmBooking={handleConfirmBooking}
              onBack={() => { setCurrentStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              onNavigateToStep={(stepId) => {
                if (stepId === 1) setCurrentStep(1);
                else if (stepId === 2) setCurrentStep('edit-transport');
                else if (stepId === 3) {
                  if (hotels.length === 0) handleProceedToHotels();
                  else setCurrentStep('edit-accommodation');
                } else if (stepId === 4) {
                  if (allPlaces.length === 0) loadSightseeing();
                  setCurrentStep('edit-sightseeing');
                } else {
                  setCurrentStep(2);
                }
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              confirming={confirming}
            />
          )}

          {/* ========================================================= */}
          {/* STEP 4: BOOKING CONFIRMATION & DOWNLOAD PASS              */}
          {/* ========================================================= */}
          {(currentStep === 4 || currentStep === 7 || currentStep === 'confirmation') && (
            <BookingConfirmation
              confirmationData={confirmationData}
              bookingSummary={{
                option: selectedOption,
                pax: tripRequest?.pax || pilgrims.length || 1,
                hotel: selectedHotel,
                hotelNights: Math.max(1, (tripRequest?.duration_days || 4) - 1),
                origin: tripRequest?.origin || '',
                tripRequest: tripRequest,
                pilgrims: pilgrims,
                primaryContact: primaryContact,
                hotelSelected: includeHotel,
                transportSelected: includeTransport,
                ownVehicle: ownVehicle,
              }}
              onReturnHome={onReturnHome}
              onStartNewBooking={() => {
                setConfirmationData(null);
                setCurrentStep(1);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          )}
        </div>
      )}

      {/* Embedded AuthModal for YatraBooking */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onAuthSuccess={(user, token) => {
          setCurrentUser(user);
          if (token) setAuthToken(token);
          setShowAuthModal(false);
        }}
      />
    </div>
  );
}
