import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import Header from '../components/Header';
import BookingDatePicker from '../components/BookingDatePicker';
import {
  CheckIcon,
  TicketIcon,
  TrainIcon,
  BusIcon,
  PlaneIcon,
  HelicopterIcon,
  BuildingIcon,
  ClockIcon,
  ShieldIcon,
  AlertCircleIcon,
  InfoIcon,
  CopyIcon,
  RefreshIcon,
  ArrowRightIcon,
  UserIcon,
} from '../components/Icons';
import {
  authorizeBooking,
  confirmBooking,
  saveBooking,
  getSavedBookings,
  getAuthMe,
} from '../services/api';
import {
  getStoredUser,
  setStoredUser,
  saveAuthToken,
  saveBookingDraft,
  getBookingDraft,
} from '../utils/storage';

export const DATA_TIERS = {
  LIVE: 'Live Availability',
  INDICATIVE: 'Indicative Estimate',
  DEMO: 'Demonstration Data',
  UNVERIFIED: 'Unavailable / Unverified',
};

export const getDataTierBadgeStyle = (tier) => {
  switch (tier) {
    case 'Live Availability':
      return { backgroundColor: '#D4EDDA', borderColor: '#C3E6CB', textColor: '#155724' };
    case 'Indicative Estimate':
      return { backgroundColor: '#FFF3CD', borderColor: '#FFEEBA', textColor: '#856404' };
    case 'Demonstration Data':
      return { backgroundColor: '#F8D7DA', borderColor: '#F5C6CB', textColor: '#721C24' };
    case 'Unavailable / Unverified':
    default:
      return { backgroundColor: '#E2E3E5', borderColor: '#D6D8DB', textColor: '#383D41' };
  }
};

export const REALISTIC_TRANSPORTS = [
  {
    id: 'tr-vande-bharat',
    name: 'Vande Bharat Express (22439)',
    mode: 'Train',
    route: 'New Delhi (NDLS) → SVDK Katra',
    depTime: '06:00',
    arrTime: '14:00',
    duration: '8h 00m',
    classType: 'AC Chair Car (CC)',
    pricePerPerson: 1665,
    availability: 'Available (Curated)',
    badge: 'Fastest Train',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Published Timetable (IRCTC/NTES 139)',
    restrictions: 'Advance reservation via irctc.co.in or PRS counter. Dynamic catering optional.',
  },
  {
    id: 'tr-uttar-sampark',
    name: 'Uttar Sampark Kranti (12445)',
    mode: 'Train',
    route: 'New Delhi (NDLS) → SVDK Katra',
    depTime: '20:50',
    arrTime: '08:05',
    duration: '11h 15m',
    classType: '3A / 2A / SL',
    pricePerPerson: 380,
    availability: 'RAC / Available',
    badge: 'Overnight Express',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Published Timetable (IRCTC/NTES 139)',
    restrictions: 'Overnight service. RAC/Waitlist rules apply under Northern Railway regulations.',
  },
  {
    id: 'tr-shri-shakti',
    name: 'Shri Shakti Express (22461)',
    mode: 'Train',
    route: 'New Delhi (NDLS) → SVDK Katra',
    depTime: '19:05',
    arrTime: '06:10',
    duration: '11h 05m',
    classType: '3rd AC (3A)',
    pricePerPerson: 1045,
    availability: 'Available',
    badge: 'Popular Choice',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Published Timetable (IRCTC/NTES 139)',
    restrictions: 'All-AC superfast express. Linen included for 3A/2A/1A passengers.',
  },
  {
    id: 'bus-zingbus',
    name: 'Zingbus BharatBenz AC Sleeper',
    mode: 'Bus',
    route: 'Kashmiri Gate, Delhi → Katra Stand',
    depTime: '20:00',
    arrTime: '07:30',
    duration: '11h 30m',
    classType: 'AC Sleeper 2+1',
    pricePerPerson: 649,
    availability: '18 Seats Left',
    badge: 'Budget Sleeper',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Operator Tariff Schedule (Zingbus 2026)',
    restrictions: 'Online reservation via zingbus.com or app. Boarding 15 mins prior at lounge.',
  },
  {
    id: 'bus-laxmi',
    name: 'Laxmi Holidays Volvo 9600 Multi-Axle',
    mode: 'Bus',
    route: 'Majnu Ka Tilla, Delhi → Katra',
    depTime: '19:30',
    arrTime: '07:00',
    duration: '11h 30m',
    classType: 'Premium Volvo 9600',
    pricePerPerson: 899,
    availability: '12 Seats Left',
    badge: 'Comfort Volvo',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Operator Tariff Schedule (Laxmi Holidays)',
    restrictions: 'Luggage allowance 15 kg per seat. Direct drop at Subhash Parking Katra.',
  },
  {
    id: 'flight-indigo',
    name: 'IndiGo 6E-2144 + Katra Taxi',
    mode: 'Flight',
    route: 'Delhi (DEL) → Jammu (IXJ) + Cab',
    depTime: '08:30',
    arrTime: '10:00 + 1.5h Cab',
    duration: '3h 00m Total',
    classType: 'Economy Air + Cab',
    pricePerPerson: 3850,
    availability: 'Available',
    badge: 'Fastest Transit',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Scheduled Airline Corridor (IndiGo/DGCA)',
    restrictions: 'Lands at Jammu Civil Enclave (IXJ). 50 km (~1.5h) highway transfer to Katra base camp.',
  },
  {
    id: 'flight-air-india',
    name: 'Air India AI-821 + Katra Taxi',
    mode: 'Flight',
    route: 'Delhi (DEL) → Jammu (IXJ) + Cab',
    depTime: '11:15',
    arrTime: '12:45 + 1.5h Cab',
    duration: '3h 00m Total',
    classType: 'Full Service Economy',
    pricePerPerson: 4200,
    availability: 'Available',
    badge: 'Full Service Flight',
    dataTier: 'Indicative Estimate',
    dataFreshness: 'Scheduled Airline Corridor (Air India/DGCA)',
    restrictions: 'Lands at Jammu Civil Enclave (IXJ). 20 kg check-in baggage. Highway cab to Katra.',
  },
];

export const ASCENT_MODES = [
  {
    id: 'ascent-traditional',
    name: 'Traditional Walking Trek (Banganga)',
    description: '13 km holy trail via Charan Paduka & Ardhkuwari',
    pricePerPerson: 0,
    duration: '5 - 6 Hours',
    badge: 'Devotional Walk',
    dataTier: 'Demonstration Data',
    dataFreshness: 'Simulated Pilgrimage Model (Academic Prototype)',
    restrictions: 'Free walking trek. Mandatory RFID card required before Banganga checkpoint.',
  },
  {
    id: 'ascent-tarakote',
    name: 'Tarakote Marg Paved Track',
    description: 'Gentler gradient paved track free of horses/ponies',
    pricePerPerson: 0,
    duration: '5 - 6 Hours',
    badge: 'Gentle Paved Slope',
    dataTier: 'Demonstration Data',
    dataFreshness: 'Simulated Pilgrimage Model (Academic Prototype)',
    restrictions: 'Clean eco track; no ponies/mules allowed. 12 km paved path with resting sheds.',
  },
  {
    id: 'ascent-battery-car',
    name: 'Eco Battery Car (Ardhkuwari ↔ Bhawan)',
    description: 'Electric eco-vehicle for seniors & families',
    pricePerPerson: 354,
    duration: '25 Minutes',
    badge: 'Senior Citizen Friendly',
    dataTier: 'Demonstration Data',
    dataFreshness: 'Official Tariff Sched (SMVDSB ₹354)',
    restrictions: 'Priority to senior citizens, differently-abled devotees, and pregnant women.',
  },
  {
    id: 'ascent-helicopter',
    name: 'Helicopter (Katra Helipad ↔ Sanjichhat)',
    description: '8-minute aerial flight to Sanjichhat + 2.5 km trek to Bhawan',
    pricePerPerson: 2100,
    duration: '8 Minutes flight',
    badge: 'Direct Aerial Ascent',
    dataTier: 'Demonstration Data',
    dataFreshness: 'Official Tariff Sched (SMVDSB ₹2,100)',
    restrictions: 'Official booking exclusively via maavaishnodevi.org. Subject to weather at Sanjichhat.',
  },
  {
    id: 'ascent-palki',
    name: 'Palki / Palanquin Service',
    description: 'Carried by 4 registered shrine porters to Bhawan',
    pricePerPerson: 1250,
    duration: '4 Hours',
    badge: 'Full Mobility Support',
    dataTier: 'Demonstration Data',
    dataFreshness: 'Shrine Board Notified Porter Tariff',
    restrictions: 'Available at Banganga, Katra and Ardhkuwari counters with registered rate cards.',
  },
];

export const ACCOMMODATION_CATALOGUE = [
  {
    id: 'htl-niharika',
    name: 'Niharika Complex (SMVDSB)',
    location: 'Near Central Bus Stand, Katra',
    roomType: 'Standard AC Double Room',
    occupancy: '2 Adults per room',
    pricePerNight: 800,
    facilities: ['Shrine Board Operated', 'Pure Veg Bhojanalaya', '24h Hot Water', 'Lift Access'],
    restrictions: 'Strictly Pure Vegetarian, No Alcohol, Devotee ID mandatory',
    availability: 'Available (Curated)',
    badge: 'Shrine Board Official',
  },
  {
    id: 'htl-trikuta',
    name: 'Trikuta Bhawan (SMVDSB)',
    location: 'Near Katra Railway Station',
    roomType: 'Dormitory Hall Bed',
    occupancy: '1 Pilgrim per bed',
    pricePerNight: 150,
    facilities: ['Locker Facility', 'Hot Water Bathrooms', 'Near Station'],
    restrictions: 'Devotees only, Strict vegetarianism',
    availability: 'Available',
    badge: 'Budget Dormitory',
  },
  {
    id: 'htl-asia',
    name: 'Hotel Asia Vaishno Devi',
    location: 'Jammu Road, Katra',
    roomType: 'Deluxe AC Double Room',
    occupancy: '2 Adults + 1 Child per room',
    pricePerNight: 2200,
    facilities: ['Free Wi-Fi', 'Running Hot Water', 'Pure Veg Restaurant', 'Free Helipad Pickup'],
    restrictions: '100% Vegetarian Premises, Alcohol strictly prohibited',
    availability: 'Available (Curated)',
    badge: 'Most Popular',
  },
  {
    id: 'htl-vaishnavi',
    name: 'Hotel The Vaishnavi',
    location: 'Railway Road, Katra',
    roomType: 'Standard Double Room',
    occupancy: '2 Adults per room',
    pricePerNight: 1000,
    facilities: ['Hot Water', 'Room Service', 'Near Railway Station'],
    restrictions: 'Pure Vegetarian Only',
    availability: 'Available',
    badge: 'Economic Value',
  },
  {
    id: 'htl-white',
    name: 'The White Hotel, Katra',
    location: 'Reasi Road, Katra',
    roomType: 'Superior Mountain View Room',
    occupancy: '2 Adults per room',
    pricePerNight: 4200,
    facilities: ['Panoramic Mountain View', 'Multi-Cuisine Veg', 'Spa & Wellness', 'Free Shuttle'],
    restrictions: 'Pure Vegetarian, Govt ID Mandatory',
    availability: 'Available (Curated)',
    badge: 'Premium Comfort',
  },
  {
    id: 'htl-vivanta',
    name: 'Vivanta Katra (Taj Group)',
    location: 'Jammu Road, Katra',
    roomType: 'Deluxe Valley View Suite',
    occupancy: '2 Adults per room',
    pricePerNight: 6000,
    facilities: ['5-Star Luxury Hospitality', 'Heated Pool', 'Fine Dining Pure Veg', 'Helipad Service'],
    restrictions: 'Strictly Vegetarian Menu, Standard Luxury Policies',
    availability: 'Available',
    badge: '5-Star Luxury',
  },
];

export const POPULAR_ORIGINS = ['Delhi', 'Jammu', 'Amritsar', 'Srinagar', 'Mumbai', 'Ahmedabad', 'Pune', 'Chandigarh'];

export default function BookingScreen({ route, navigation }) {
  // Navigation tabs: 'wizard' (Plan & Book) | 'my-bookings' (Saved Bookings)
  const [activeView, setActiveView] = useState('wizard');

  // Step state: 1: Intake & Details, 2: Itinerary & Selections, 3: Review & Auth Gate, 4: Pass Generated
  const [step, setStep] = useState(route?.params?.step ? Number(route.params.step) : (route?.params?.initialStep ? Number(route.params.initialStep) : 1));
  const [loading, setLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Flexible Service Toggles
  const [includeHotel, setIncludeHotel] = useState(
    route?.params?.includeHotel !== undefined ? Boolean(route.params.includeHotel) : true
  );
  const [includeTransport, setIncludeTransport] = useState(
    route?.params?.includeTransport !== undefined ? Boolean(route.params.includeTransport) : true
  );
  const [ownVehicle, setOwnVehicle] = useState(
    route?.params?.ownVehicle !== undefined ? Boolean(route.params.ownVehicle) : false
  );
  const [prefilledFields, setPrefilledFields] = useState(
    Array.isArray(route?.params?.prefilledFields) ? route.params.prefilledFields : []
  );

  // Form State (Intake)
  const [origin, setOrigin] = useState(route?.params?.origin || 'Delhi');
  const [destination] = useState('Katra (Shri Mata Vaishno Devi)');
  const [startDate, setStartDate] = useState(route?.params?.startDate || route?.params?.travelDate || '2026-11-10');
  const [duration, setDuration] = useState(parseInt(route?.params?.duration || '4', 10));
  const [pax, setPax] = useState(parseInt(route?.params?.pax || '2', 10));
  const [budgetAmount, setBudgetAmount] = useState(route?.params?.budget ? String(route?.params?.budget) : '15000');
  const [darshanCategory, setDarshanCategory] = useState('Normal Darshan');
  const [mobilityPref, setMobilityPref] = useState('Standard Walking Trek');

  // Primary Devotee & Contact
  const [fullName, setFullName] = useState(route?.params?.fullName || 'Ramesh Sharma');
  const [age, setAge] = useState('38');
  const [gender, setGender] = useState('Male');
  const [phone, setPhone] = useState(route?.params?.phone || '');

  // Dynamic Pilgrims Roster with Unique Record Identifiers
  const generatePilgrimId = (idx = 0) => `p_${Date.now()}_${idx}_${Math.random().toString(36).substring(2, 6)}`;
  const initialPaxCount = parseInt(route?.params?.pax || '2', 10) || 2;
  const initialPilgrimsList = Array.isArray(route?.params?.pilgrims) && route.params.pilgrims.length > 0
    ? route.params.pilgrims.map((p, idx) => ({
        id: p.id || generatePilgrimId(idx),
        full_name: p.full_name || p.name || '',
        age: p.age ? String(p.age) : '',
        gender: p.gender || 'Male',
      }))
    : [
        { id: generatePilgrimId(0), full_name: route?.params?.fullName || 'Ramesh Sharma', age: '38', gender: 'Male' },
        ...(initialPaxCount > 1 ? Array.from({ length: initialPaxCount - 1 }, (_, i) => ({ id: generatePilgrimId(i + 1), full_name: '', age: '', gender: 'Male' })) : []),
      ];
  const [pilgrims, setPilgrims] = useState(initialPilgrimsList);
  const [duplicateNameAdvisory, setDuplicateNameAdvisory] = useState('');

  // Selection State
  const [selectedTransport, setSelectedTransport] = useState(route?.params?.selectedTransport || REALISTIC_TRANSPORTS[0]);
  const [selectedAscent, setSelectedAscent] = useState(route?.params?.selectedAscent || ASCENT_MODES[0]);
  const [selectedHotel, setSelectedHotel] = useState(route?.params?.selectedHotel || ACCOMMODATION_CATALOGUE[2]); // Hotel Asia

  // Update form and selections if route params change during navigation
  useEffect(() => {
    if (route?.params?.step) {
      setStep(Number(route.params.step));
    }
    if (route?.params?.selectedTransport) {
      setSelectedTransport(route.params.selectedTransport);
    }
    if (route?.params?.selectedHotel) {
      setSelectedHotel(route.params.selectedHotel);
    }
    if (route?.params?.selectedAscent) {
      setSelectedAscent(route.params.selectedAscent);
    }
    if (route?.params?.budget) {
      setBudgetAmount(String(route.params.budget));
    }
    if (route?.params?.pax) {
      const pCount = parseInt(route.params.pax, 10);
      setPax(pCount);
    }
    if (route?.params?.duration) {
      setDuration(parseInt(route.params.duration, 10));
    }
    if (route?.params?.startDate || route?.params?.travelDate) {
      setStartDate(route.params.startDate || route.params.travelDate);
    }
    if (route?.params?.origin) {
      setOrigin(route.params.origin);
    }
    if (route?.params?.includeHotel !== undefined) {
      setIncludeHotel(Boolean(route.params.includeHotel));
    }
    if (route?.params?.includeTransport !== undefined) {
      setIncludeTransport(Boolean(route.params.includeTransport));
    }
    if (route?.params?.ownVehicle !== undefined) {
      setOwnVehicle(Boolean(route.params.ownVehicle));
    }
    if (Array.isArray(route?.params?.prefilledFields)) {
      setPrefilledFields(route.params.prefilledFields);
    }
    if (Array.isArray(route?.params?.pilgrims) && route.params.pilgrims.length > 0) {
      setPilgrims(route.params.pilgrims.map(p => ({
        full_name: p.full_name || p.name || '',
        age: p.age ? String(p.age) : '',
        gender: p.gender || 'Male',
      })));
    }
  }, [route?.params]);

  // Step 3 Guardrails & Auth
  const [authorized, setAuthorized] = useState(false);
  const [activeDraftPassId, setActiveDraftPassId] = useState(null);
  const [generatedPass, setGeneratedPass] = useState(null);

  // My Bookings State
  const [savedBookings, setSavedBookings] = useState([]);
  const [loadingBookings, setLoadingBookings] = useState(false);
  const [expandedBookingId, setExpandedBookingId] = useState(null);

  // Check auth and restore draft on mount and focus
  useEffect(() => {
    checkUserAuth();
    loadDraftIfAvailable();
  }, []);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      checkUserAuth();
      loadDraftIfAvailable();
    });
    return unsubscribe;
  }, [navigation]);

  useEffect(() => {
    if (route?.params?.returnStep) {
      setStep(Number(route.params.returnStep));
    }
  }, [route?.params?.returnStep]);

  const checkUserAuth = async () => {
    try {
      const stored = await getStoredUser();
      if (stored) {
        setCurrentUser(stored);
      }
      const meRes = await getAuthMe();
      if (meRes?.authenticated && meRes.user) {
        setCurrentUser(meRes.user);
        await setStoredUser(meRes.user);
      }
    } catch {
      // offline or guest
    }
  };

  const saveCurrentBookingDraft = async (targetStep = step) => {
    try {
      await saveBookingDraft({
        step: targetStep,
        origin,
        destination,
        startDate,
        duration,
        pax,
        fullName,
        age,
        gender,
        phone,
        includeHotel,
        includeTransport,
        ownVehicle,
        pilgrims,
        prefilledFields,
        darshanCategory,
        mobilityPref,
        selectedTransport,
        selectedHotel,
        selectedAscent,
        budgetAmount,
      });
    } catch {
      // ignore
    }
  };

  const loadDraftIfAvailable = async () => {
    try {
      const draft = await getBookingDraft();
      if (draft && !route?.params?.overrideDraft) {
        if (draft.origin) setOrigin(draft.origin);
        if (draft.startDate) setStartDate(draft.startDate);
        if (draft.duration) setDuration(draft.duration);
        if (draft.pax) setPax(draft.pax);
        if (draft.fullName) setFullName(draft.fullName);
        if (draft.age) setAge(draft.age);
        if (draft.gender) setGender(draft.gender);
        if (draft.phone) setPhone(draft.phone);
        if (draft.includeHotel !== undefined) setIncludeHotel(Boolean(draft.includeHotel));
        if (draft.includeTransport !== undefined) setIncludeTransport(Boolean(draft.includeTransport));
        if (draft.ownVehicle !== undefined) setOwnVehicle(Boolean(draft.ownVehicle));
        if (Array.isArray(draft.pilgrims) && draft.pilgrims.length > 0) setPilgrims(draft.pilgrims);
        if (Array.isArray(draft.prefilledFields)) setPrefilledFields(draft.prefilledFields);
        if (draft.darshanCategory) setDarshanCategory(draft.darshanCategory);
        if (draft.mobilityPref) setMobilityPref(draft.mobilityPref);
        if (draft.selectedTransport) setSelectedTransport(draft.selectedTransport);
        if (draft.selectedHotel) setSelectedHotel(draft.selectedHotel);
        if (draft.selectedAscent) setSelectedAscent(draft.selectedAscent);
        if (draft.budgetAmount) setBudgetAmount(draft.budgetAmount);
        if (draft.step && draft.step > 1 && !route?.params?.step && !route?.params?.returnStep) {
          setStep(draft.step);
        }
      }
    } catch {
      // ignore
    }
  };

  const handleUpdatePax = (newPax) => {
    const n = Math.max(1, Math.min(200, parseInt(newPax, 10) || 1));
    setPax(n);
    setPilgrims((prev) => {
      if (prev.length === n) return prev;
      if (prev.length < n) {
        const added = Array.from({ length: n - prev.length }, (_, i) => ({
          id: generatePilgrimId(prev.length + i),
          full_name: '',
          age: '',
          gender: 'Male',
        }));
        return [...prev, ...added];
      }
      return prev.slice(0, n);
    });
  };

  const handleAddPilgrim = () => {
    if (pilgrims.length >= 200) {
      Alert.alert('Group Limit', 'Maximum 200 pilgrims allowed per reservation request.');
      return;
    }
    const nextCount = pilgrims.length + 1;
    setPax(nextCount);
    setPilgrims((prev) => [...prev, { id: generatePilgrimId(prev.length), full_name: '', age: '', gender: 'Male' }]);
  };

  const handleRemovePilgrim = (indexToRemove) => {
    if (pilgrims.length <= 1) {
      Alert.alert('Minimum Devotee', 'At least 1 pilgrim must be registered.');
      return;
    }
    const updated = pilgrims.filter((_, idx) => idx !== indexToRemove);
    setPax(updated.length);
    setPilgrims(updated);
    if (indexToRemove === 0 && updated.length > 0) {
      setFullName(updated[0].full_name || '');
      setAge(updated[0].age ? String(updated[0].age) : '');
      setGender(updated[0].gender || 'Male');
    }
  };

  const handleUpdatePilgrim = (index, field, value) => {
    setPilgrims((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
    if (index === 0) {
      if (field === 'full_name') setFullName(value);
      if (field === 'age') setAge(value);
      if (field === 'gender') setGender(value);
    }
    if (field === 'full_name') {
      const trimmed = value.trim().toLowerCase();
      if (trimmed) {
        const hasDup = pilgrims.some((p, idx) => idx !== index && p.full_name?.trim().toLowerCase() === trimmed);
        if (hasDup) {
          setDuplicateNameAdvisory(
            `Advisory: Devotee name "${value.trim()}" appears multiple times in this booking. Each pilgrim will receive a distinct pass with a unique token.`
          );
        } else {
          setDuplicateNameAdvisory('');
        }
      }
    }
  };

  const handleOpenEmailAuth = async () => {
    await saveCurrentBookingDraft(3);
    navigation.navigate('Auth', {
      returnScreen: 'Booking',
      returnStep: 3,
    });
  };

  // Auto-calculated Return Date & validation
  const calculateReturnDate = (start, durDays) => {
    try {
      const parts = start.split('-');
      if (parts.length === 3) {
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        d.setDate(d.getDate() + Math.max(1, durDays - 1));
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
      }
    } catch {
      // fallback
    }
    return '2026-11-13';
  };

  const returnDate = calculateReturnDate(startDate, duration);
  const nightsCount = Math.max(1, duration - 1);
  const paxCount = Math.max(1, parseInt(pax, 10) || 1);
  const roomsCount = Math.ceil(paxCount / 2);

  // Dynamic Financial Breakdown with flexible service toggles
  const isTransportActive = includeTransport && !ownVehicle;
  const transportCost = isTransportActive ? ((selectedTransport?.pricePerPerson || 0) * paxCount) : 0;
  const ascentCost = (selectedAscent?.pricePerPerson || 0) * paxCount;
  const hotelCost = includeHotel ? ((selectedHotel?.pricePerNight || 0) * roomsCount * nightsCount) : 0;
  const darshanCost = darshanCategory === 'VIP Aarti Darshan' ? 2000 * paxCount : 0;
  const mealsEstCost = 350 * paxCount * duration;
  const grandTotal = transportCost + ascentCost + hotelCost + darshanCost + mealsEstCost;
  const perPersonCost = Math.round(grandTotal / paxCount);
  const userBudgetNum = parseFloat(budgetAmount) || 0;
  const budgetDifference = userBudgetNum > 0 ? userBudgetNum - grandTotal : null;

  // Save draft whenever key inputs change
  useEffect(() => {
    saveBookingDraft({
      origin,
      startDate,
      duration,
      pax,
      fullName,
      phone,
      includeHotel,
      includeTransport,
      ownVehicle,
      pilgrims,
      prefilledFields,
      selectedTransportId: selectedTransport?.id,
      selectedHotelId: selectedHotel?.id,
    });
  }, [origin, startDate, duration, pax, fullName, phone, includeHotel, includeTransport, ownVehicle, pilgrims, prefilledFields, selectedTransport, selectedHotel]);

  // Load My Bookings
  const loadUserBookings = async () => {
    setLoadingBookings(true);
    try {
      const res = await getSavedBookings();
      if (res?.bookings && Array.isArray(res.bookings)) {
        setSavedBookings(res.bookings);
      } else if (Array.isArray(res)) {
        setSavedBookings(res);
      } else {
        setSavedBookings([]);
      }
    } catch {
      setSavedBookings([]);
    } finally {
      setLoadingBookings(false);
    }
  };

  useEffect(() => {
    if (activeView === 'my-bookings' && currentUser) {
      loadUserBookings();
    }
  }, [activeView, currentUser]);

  // Step 1 -> Step 2 validation
  const handleProceedToItinerary = () => {
    if (!origin.trim()) {
      Alert.alert('Missing Field', 'Please enter your departure city / origin.');
      return;
    }
    const paxNum = parseInt(pax, 10);
    if (!pax || isNaN(paxNum) || paxNum < 1) {
      Alert.alert('Pilgrims Required', 'Please specify at least 1 pilgrim.');
      return;
    }
    if (paxNum > 200) {
      Alert.alert(
        'Pilgrim Group Limit',
        'Online itinerary booking supports groups up to 200 pilgrims per request to ensure accurate accommodation allocation. For larger congregations, please contact group reservation support directly.'
      );
      return;
    }
    const durationNum = parseInt(duration, 10);
    if (!duration || isNaN(durationNum) || durationNum < 1) {
      Alert.alert('Duration Required', 'Please specify a positive itinerary duration in days.');
      return;
    }
    if (durationNum > 90) {
      Alert.alert(
        'Itinerary Duration Limit',
        'The interactive itinerary generator supports trips up to 90 days (3 months) to ensure optimal device performance and stay within local storage safety limits. For longer journeys, please plan separate regional segments.'
      );
      return;
    }
    if (phone.trim() && !/^\d{10}$/.test(phone.trim().replace(/[\s+-]/g, ''))) {
      Alert.alert('Contact Phone', 'Please enter a valid 10-digit mobile number for transit alerts, or leave blank.');
      return;
    }

    // Comprehensive Individual Pilgrim Validation (Phase 8.8.54A)
    if (!pilgrims || pilgrims.length === 0) {
      Alert.alert('Pilgrim Required', 'Please add at least 1 pilgrim to proceed.');
      return;
    }
    if (pilgrims.length !== paxNum) {
      Alert.alert(
        'Devotee Count Mismatch',
        `You requested ${paxNum} pilgrim(s) but currently have ${pilgrims.length} devotee record(s). Please adjust your roster.`
      );
      return;
    }
    for (let i = 0; i < pilgrims.length; i++) {
      const p = pilgrims[i];
      if (!p.full_name || !p.full_name.trim()) {
        Alert.alert('Incomplete Devotee Details', `Please enter the full name for Devotee #${i + 1}.`);
        return;
      }
      const a = parseInt(p.age, 10);
      if (!p.age || isNaN(a) || a < 1 || a > 125) {
        Alert.alert('Invalid Age', `Please enter a valid integer age (1-125) for Devotee #${i + 1} (${p.full_name.trim()}).`);
        return;
      }
    }
    // Check duplicate devotee names (Non-blocking advisory warning - legitimate family members may share names)
    const names = pilgrims.map(p => p.full_name.trim().toLowerCase());
    const dups = names.filter((item, index) => names.indexOf(item) !== index);
    if (dups.length > 0) {
      setDuplicateNameAdvisory(
        `Advisory: Devotee name "${dups[0]}" is repeated. Separate passes with unique identification tokens will be issued for each devotee.`
      );
    } else {
      setDuplicateNameAdvisory('');
    }

    setStep(2);
  };

  // Step 2 -> Step 3
  const handleProceedToReview = () => {
    setStep(3);
  };

  // Step 3 -> Final Confirmation
  const handleConfirmBookingExecution = async () => {
    if (!authorized) {
      Alert.alert(
        'Human Verification Required',
        'Please check the mandatory human authorization box confirming you understand this is an educational simulation.'
      );
      return;
    }

    // Compulsory Email Authentication Gate (Requirement 6)
    if (!currentUser) {
      Alert.alert(
        'Authentication Required',
        'To issue your verified demonstration pilgrimage pass and link it to your account, please sign in with your email address.',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Sign In with Email OTP',
            onPress: handleOpenEmailAuth,
          },
        ]
      );
      return;
    }

    setLoading(true);
    try {
      const passId = activeDraftPassId || `VD-RPA-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
      if (!activeDraftPassId) {
        setActiveDraftPassId(passId);
      }

      const primaryContactObj = {
        name: (pilgrims[0]?.full_name || fullName).trim(),
        phone: phone.trim(),
        email: currentUser?.email || '',
      };

      const sanitizedPilgrims = pilgrims.map((p, idx) => ({
        id: p.id || generatePilgrimId(idx),
        full_name: p.full_name.trim(),
        age: parseInt(p.age, 10),
        gender: p.gender || 'Male',
      }));

      const transportDisplayMode = ownVehicle
        ? 'Own Vehicle / Private Conveyance'
        : (!includeTransport ? 'Self-Arranged Transport' : (selectedTransport?.mode || 'Train'));

      const transportDisplayInfo = ownVehicle
        ? 'Self-Driving to Katra (Carrier booking excluded)'
        : (!includeTransport ? 'Devotee-arranged travel (Carrier booking excluded)' : `${selectedTransport?.name} (${selectedTransport?.route})`);

      const hotelDisplayName = !includeHotel ? 'Self-Arranged Lodging (No Hotel Booked)' : selectedHotel?.name;

      const bookingRecord = {
        booking_id: passId,
        pax_count: paxCount,
        slot_date: startDate,
        category: darshanCategory,
        slot_time: 'Morning (06:00 - 12:00)',
        transport_mode: transportDisplayMode,
        transport_info: transportDisplayInfo,
        hotel_name: hotelDisplayName,
        total_price: grandTotal,
        status: 'SIMULATED_ISSUED',
        receipt: {
          reference: passId,
          primaryDevotee: primaryContactObj.name,
          phone,
          origin,
          destination,
          startDate,
          returnDate,
          durationDays: duration,
          pax: paxCount,
          rooms: includeHotel ? roomsCount : 0,
          nights: includeHotel ? nightsCount : 0,
          hotel_selected: includeHotel,
          transport_selected: includeTransport,
          own_vehicle: ownVehicle,
          pilgrims: sanitizedPilgrims,
          primary_contact: primaryContactObj,
          transport: {
            ...selectedTransport,
            dataTier: selectedTransport?.dataTier || 'Indicative Estimate',
            dataFreshness: selectedTransport?.dataFreshness || 'Published Timetable (IRCTC/NTES 139)',
            restrictions: ownVehicle ? 'Self-arranged driving' : (selectedTransport?.restrictions || 'Advance reservation required'),
          },
          ascentMode: {
            ...selectedAscent,
            dataTier: selectedAscent?.dataTier || 'Demonstration Data',
            dataFreshness: selectedAscent?.dataFreshness || 'Simulated Pilgrimage Model',
            restrictions: selectedAscent?.restrictions || 'Official booking via maavaishnodevi.org',
          },
          hotel: includeHotel ? selectedHotel : null,
          darshanCategory,
          mobilityPreference: mobilityPref,
          itemized: {
            transportTotal: transportCost,
            ascentTotal: ascentCost,
            hotelTotal: hotelCost,
            darshanTotal: darshanCost,
            mealsEstimate: mealsEstCost,
            grandTotal,
            perPerson: perPersonCost,
          },
        },
      };

      // Call API confirmation & save to account
      try {
        await confirmBooking({
          option: {
            transport: isTransportActive ? selectedTransport : null,
            slot: { category: darshanCategory, slot_date: startDate, slot_time: 'Morning' },
            total_price: grandTotal,
          },
          pax: paxCount,
          user_name: primaryContactObj.name,
          hotel: includeHotel ? selectedHotel : null,
          hotel_nights: includeHotel ? nightsCount : 0,
          human_authorized: true,
          hotel_selected: includeHotel,
          transport_selected: includeTransport,
          own_vehicle: ownVehicle,
          pilgrims: sanitizedPilgrims,
          primary_contact: primaryContactObj,
          start_date: startDate,
          return_date: returnDate,
          duration: duration,
          budget: userBudgetNum,
        });
      } catch {
        // Continue with local demonstration record
      }

      // Persist in User Account
      try {
        await saveBooking({
          ...bookingRecord,
          pilgrims: sanitizedPilgrims,
          primary_contact: primaryContactObj,
          hotel_selected: includeHotel,
          transport_selected: includeTransport,
          own_vehicle: ownVehicle,
          start_date: startDate,
          return_date: returnDate,
          duration: duration,
        });
      } catch {
        // Fallback for offline mode
      }

      setGeneratedPass({
        ...bookingRecord,
        status: 'SIMULATED_ISSUED',
        generatedAt: new Date().toLocaleString(),
      });

      setStep(4);
    } catch (err) {
      Alert.alert('Booking Error', err.message || 'Simulation execution encountered an issue.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPass = async () => {
    if (generatedPass?.booking_id) {
      await Clipboard.setStringAsync(generatedPass.booking_id);
      Alert.alert('Copied', `Pass Reference ${generatedPass.booking_id} copied to clipboard.`);
    }
  };

  const handleReset = () => {
    setStep(1);
    setAuthorized(false);
    setActiveDraftPassId(null);
    setGeneratedPass(null);
  };

  return (
    <View style={styles.container}>
      <Header
        title="Guided Yatra Booking"
        subtitle="Pilgrimage Intake & Reservation Pass"
        showBack={true}
        onBackPress={() => navigation.navigate('Assistant')}
        user={currentUser}
      />

      {/* Primary View Toggle: Plan Yatra vs My Bookings */}
      <View style={styles.viewToggleBar}>
        <TouchableOpacity
          style={[styles.viewToggleBtn, activeView === 'wizard' && styles.viewToggleBtnActive]}
          onPress={() => setActiveView('wizard')}
          activeOpacity={0.8}
        >
          <TicketIcon size={16} color={activeView === 'wizard' ? '#FFFFFF' : colors.primary} />
          <Text style={[styles.viewToggleText, activeView === 'wizard' && styles.viewToggleTextActive]}>
            Plan & Book Yatra
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.viewToggleBtn, activeView === 'my-bookings' && styles.viewToggleBtnActive]}
          onPress={() => {
            setActiveView('my-bookings');
            if (currentUser) loadUserBookings();
          }}
          activeOpacity={0.8}
        >
          <BuildingIcon size={16} color={activeView === 'my-bookings' ? '#FFFFFF' : colors.primary} />
          <Text style={[styles.viewToggleText, activeView === 'my-bookings' && styles.viewToggleTextActive]}>
            My Bookings {savedBookings.length > 0 ? `(${savedBookings.length})` : ''}
          </Text>
        </TouchableOpacity>
      </View>

      {/* ========================================================= */}
      {/* VIEW A: MY BOOKINGS (SAVED USER BOOKINGS) */}
      {/* ========================================================= */}
      {activeView === 'my-bookings' && (
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <View style={styles.card}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <Text style={styles.stepTitle}>Your Verified Yatra Bookings</Text>
              <TouchableOpacity onPress={loadUserBookings} style={{ padding: 4 }}>
                <RefreshIcon size={16} color={colors.primary} />
              </TouchableOpacity>
            </View>

            {!currentUser ? (
              <View style={styles.emptyStateBox}>
                <UserIcon size={36} color={colors.gold} />
                <Text style={styles.emptyStateTitle}>Sign In to View Saved Bookings</Text>
                <Text style={styles.emptyStateSubtitle}>
                  Please sign in with your email address to view and manage your verified pilgrimage passes across devices.
                </Text>
                <TouchableOpacity
                  style={styles.primaryActionButton}
                  onPress={handleOpenEmailAuth}
                  activeOpacity={0.8}
                  accessibilityLabel="Sign In with Email OTP"
                >
                  <Text style={styles.primaryActionText}>Sign In with Email OTP</Text>
                </TouchableOpacity>
              </View>
            ) : loadingBookings ? (
              <View style={{ padding: 24, alignItems: 'center' }}>
                <ActivityIndicator size="small" color={colors.primary} />
                <Text style={{ marginTop: 8, fontSize: 13, color: colors.textSecondary }}>
                  Loading your yatra bookings...
                </Text>
              </View>
            ) : savedBookings.length === 0 ? (
              <View style={styles.emptyStateBox}>
                <TicketIcon size={36} color={colors.gold} />
                <Text style={styles.emptyStateTitle}>No Bookings Found</Text>
                <Text style={styles.emptyStateSubtitle}>
                  You do not have any saved pilgrimage bookings yet. Plan your sacred journey to Mata Vaishno Devi today.
                </Text>
                <TouchableOpacity
                  style={styles.primaryActionButton}
                  onPress={() => {
                    setActiveView('wizard');
                    setStep(1);
                  }}
                >
                  <Text style={styles.primaryActionText}>Start Yatra Intake →</Text>
                </TouchableOpacity>
              </View>
            ) : (
              savedBookings.map((b, idx) => {
                const isExpanded = expandedBookingId === (b.booking_id || String(idx));
                const bId = b.booking_id || `VD-${idx + 1}`;
                return (
                  <View key={bId} style={styles.bookingHistoryCard}>
                    <View style={styles.bookingHeaderRow}>
                      <View>
                        <Text style={styles.bookingRefText}>{bId}</Text>
                        <Text style={styles.bookingDateSub}>
                          {b.slot_date || '2026-11-10'} • {b.pax_count || 1} Pilgrim(s)
                        </Text>
                      </View>
                      <View style={styles.bookingBadgeConfirmed}>
                        <CheckIcon size={12} color="#155724" />
                        <Text style={styles.bookingBadgeText}>CONFIRMED</Text>
                      </View>
                    </View>

                    <View style={styles.bookingDetailsRow}>
                      <Text style={styles.bookingDetailItem}>
                        🚆 <Text style={{ fontWeight: '700' }}>Transport:</Text> {b.transport_mode || 'Train'} ({b.transport_info || 'Direct Express'})
                      </Text>
                      {b.receipt?.transport?.dataTier && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 2, marginBottom: 4 }}>
                          <View style={[styles.dataTierPill, getDataTierBadgeStyle(b.receipt.transport.dataTier)]}>
                            <Text style={[styles.dataTierPillText, { color: getDataTierBadgeStyle(b.receipt.transport.dataTier).textColor }]}>
                              ● {b.receipt.transport.dataTier}
                            </Text>
                          </View>
                        </View>
                      )}
                      <Text style={styles.bookingDetailItem}>
                        🏨 <Text style={{ fontWeight: '700' }}>Stay:</Text> {b.hotel_name || 'Katra Stay'}
                      </Text>
                      <Text style={styles.bookingDetailItem}>
                        💰 <Text style={{ fontWeight: '700' }}>Total Cost:</Text> ₹{b.total_price || 0}
                      </Text>
                    </View>

                    <TouchableOpacity
                      style={styles.expandItineraryBtn}
                      onPress={() => setExpandedBookingId(isExpanded ? null : bId)}
                    >
                      <Text style={styles.expandItineraryText}>
                        {isExpanded ? 'Hide Day-Wise Itinerary ▲' : 'View Full Day-Wise Itinerary ▼'}
                      </Text>
                    </TouchableOpacity>

                    {isExpanded && (
                      <View style={styles.expandedItineraryBox}>
                        <Text style={styles.itineraryDayHeading}>Day 1: Arrival & Katra Base</Text>
                        <Text style={styles.itineraryActivityText}>
                          Arrival in Katra via {b.transport_mode || 'Train'}. Check into {b.hotel_name || 'Hotel'}. Collect RFID Yatra Parchi at Katra counter.
                        </Text>

                        <Text style={styles.itineraryDayHeading}>Day 2: Holy Darshan at Bhawan</Text>
                        <Text style={styles.itineraryActivityText}>
                          Morning trek to Bhawan. Attend darshan of the Holy Natural Pindies. Divine Attka Aarti & prasad collection.
                        </Text>

                        <Text style={styles.itineraryDayHeading}>Day 3: Bhairon Nath & Descent</Text>
                        <Text style={styles.itineraryActivityText}>
                          Cable car to Bhairon Temple. Complete mandatory darshan. Return descent to Katra base for rest and local market visit.
                        </Text>
                      </View>
                    )}
                  </View>
                );
              })
            )}
          </View>
        </ScrollView>
      )}

      {/* ========================================================= */}
      {/* VIEW B: WIZARD (INTAKE, ITINERARY, REVIEW, PASS) */}
      {/* ========================================================= */}
      {activeView === 'wizard' && (
        <>
          {/* 4-Step Wizard Progress Bar */}
          <View style={styles.progressContainer}>
            {[
              { id: 1, label: 'Intake' },
              { id: 2, label: 'Itinerary' },
              { id: 3, label: 'Review & Gate' },
              { id: 4, label: 'Pass' },
            ].map((s) => (
              <View key={s.id} style={styles.progressStep}>
                <View
                  style={[
                    styles.stepCircle,
                    step >= s.id ? styles.stepCircleActive : styles.stepCircleInactive,
                  ]}
                >
                  {s.id === 4 && step === 4 ? (
                    <CheckIcon size={12} color={colors.surface} />
                  ) : (
                    <Text
                      style={[
                        styles.stepNumber,
                        step >= s.id ? styles.stepNumberActive : styles.stepNumberInactive,
                      ]}
                    >
                      {s.id}
                    </Text>
                  )}
                </View>
                <Text style={styles.stepLabel}>{s.label}</Text>
              </View>
            ))}
          </View>

          <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
            {/* ----------------------------------------------------- */}
            {/* STEP 1: PILGRIMAGE INTAKE & PREFERENCES */}
            {/* ----------------------------------------------------- */}
            {step === 1 && (
              <View style={styles.card}>
                <Text style={styles.stepTitle}>Step 1: Pilgrimage Intake & Preferences</Text>
                <Text style={styles.stepSubtitle}>
                  Provide journey particulars, duration, dates, and devotee details.
                </Text>

                {/* Departure Hub / Origin */}
                <Text style={styles.inputLabel}>Departure City / Origin *</Text>
                <View style={styles.originChipsRow}>
                  {POPULAR_ORIGINS.map((hub) => (
                    <TouchableOpacity
                      key={hub}
                      style={[styles.hubChip, origin === hub && styles.hubChipActive]}
                      onPress={() => setOrigin(hub)}
                    >
                      <Text style={[styles.hubChipText, origin === hub && styles.hubChipTextActive]}>
                        {hub}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <TextInput
                  style={styles.input}
                  value={origin}
                  onChangeText={setOrigin}
                  placeholder="e.g. Delhi, Mandi, Palampur, Reasi, Pune..."
                  placeholderTextColor={colors.textLight}
                />

                {/* Destination Badge */}
                <Text style={styles.inputLabel}>Sacred Destination</Text>
                <View style={styles.destinationBadge}>
                  <Text style={styles.destinationBadgeText}>🔱 {destination}</Text>
                </View>

                {/* Dates & Duration with Auto Return Date */}
                <View style={styles.row}>
                  <View style={styles.halfCol}>
                    <BookingDatePicker
                      value={startDate}
                      onChange={setStartDate}
                      label="Start Date *"
                    />
                  </View>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Duration (Days) *</Text>
                    <View style={styles.numericInputRow}>
                      <TouchableOpacity
                        style={styles.stepperCtrlBtn}
                        onPress={() => setDuration((prev) => Math.max(1, (parseInt(prev, 10) || 1) - 1))}
                        accessibilityLabel="Decrease duration"
                      >
                        <Text style={styles.stepperCtrlText}>−</Text>
                      </TouchableOpacity>
                      <TextInput
                        style={styles.numericTextInput}
                        value={String(duration)}
                        onChangeText={(txt) => {
                          const clean = txt.replace(/[^0-9]/g, '');
                          if (clean === '') {
                            setDuration('');
                          } else {
                            setDuration(Math.max(1, parseInt(clean, 10)));
                          }
                        }}
                        onBlur={() => {
                          if (!duration || parseInt(duration, 10) < 1) {
                            setDuration(1);
                          }
                        }}
                        keyboardType="number-pad"
                        placeholder="Days"
                        placeholderTextColor={colors.textLight}
                        accessibilityLabel="Itinerary duration in days"
                        testID="duration-input"
                      />
                      <TouchableOpacity
                        style={styles.stepperCtrlBtn}
                        onPress={() => setDuration((prev) => Math.min(90, (parseInt(prev, 10) || 0) + 1))}
                        accessibilityLabel="Increase duration"
                      >
                        <Text style={styles.stepperCtrlText}>+</Text>
                      </TouchableOpacity>
                    </View>
                    <View style={styles.quickChipsRow}>
                      {[2, 3, 4, 7, 10].map((d) => (
                        <TouchableOpacity
                          key={d}
                          style={[styles.quickChip, duration === d && styles.quickChipActive]}
                          onPress={() => setDuration(d)}
                        >
                          <Text style={[styles.quickChipText, duration === d && styles.quickChipTextActive]}>
                            {d}d
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                </View>

                {/* Auto-Calculated Return Date Display */}
                <View style={styles.returnDateNotice}>
                  <ClockIcon size={14} color={colors.primary} />
                  <Text style={styles.returnDateNoticeText}>
                    Calculated Return: <Text style={{ fontWeight: '800' }}>{returnDate}</Text> ({duration} Days / {nightsCount} Nights)
                  </Text>
                </View>

                {/* Travellers & Budget */}
                <View style={styles.row}>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Pilgrims (Pax Count) *</Text>
                    <View style={styles.numericInputRow}>
                      <TouchableOpacity
                        style={styles.stepperCtrlBtn}
                        onPress={() => handleUpdatePax(Math.max(1, (parseInt(pax, 10) || 1) - 1))}
                        accessibilityLabel="Decrease pilgrims"
                      >
                        <Text style={styles.stepperCtrlText}>−</Text>
                      </TouchableOpacity>
                      <TextInput
                        style={styles.numericTextInput}
                        value={String(pax)}
                        onChangeText={(txt) => {
                          const clean = txt.replace(/[^0-9]/g, '');
                          if (clean === '') {
                            setPax('');
                          } else {
                            handleUpdatePax(Math.max(1, parseInt(clean, 10)));
                          }
                        }}
                        onBlur={() => {
                          if (!pax || parseInt(pax, 10) < 1) {
                            handleUpdatePax(1);
                          }
                        }}
                        keyboardType="number-pad"
                        placeholder="Pilgrims"
                        placeholderTextColor={colors.textLight}
                        accessibilityLabel="Number of pilgrims"
                        testID="pax-input"
                      />
                      <TouchableOpacity
                        style={styles.stepperCtrlBtn}
                        onPress={() => handleUpdatePax(Math.min(200, (parseInt(pax, 10) || 0) + 1))}
                        accessibilityLabel="Increase pilgrims"
                      >
                        <Text style={styles.stepperCtrlText}>+</Text>
                      </TouchableOpacity>
                    </View>
                    <View style={styles.quickChipsRow}>
                      {[1, 2, 4, 6, 10].map((num) => (
                        <TouchableOpacity
                          key={num}
                          style={[styles.quickChip, pax === num && styles.quickChipActive]}
                          onPress={() => handleUpdatePax(num)}
                        >
                          <Text style={[styles.quickChipText, pax === num && styles.quickChipTextActive]}>
                            {num}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Target Budget (₹)</Text>
                    <TextInput
                      style={styles.input}
                      value={budgetAmount}
                      onChangeText={setBudgetAmount}
                      placeholder="15000"
                      keyboardType="number-pad"
                      placeholderTextColor={colors.textLight}
                    />
                  </View>
                </View>

                {/* ------------------------------------------------- */}
                {/* FLEXIBLE SERVICE CUSTOMIZATION (Part 1) */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>Included Yatra Services</Text>
                  {prefilledFields.includes('hotel_selected') || prefilledFields.includes('transport_selected') ? (
                    <View style={styles.prefilledBadge}>
                      <Text style={styles.prefilledBadgeText}>Filled from your conversation</Text>
                    </View>
                  ) : null}
                </View>
                <Text style={styles.stepSubtitle}>
                  Choose which services to include in your package. All four combinations are supported.
                </Text>

                {/* Service 1: Intercity Transport */}
                <View style={styles.serviceCard}>
                  <View style={styles.serviceCardHeader}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      <TrainIcon size={16} color={colors.primary} />
                      <Text style={styles.serviceCardTitle}>Intercity Transport</Text>
                    </View>
                    <View style={{ flexDirection: 'row', gap: 6 }}>
                      <TouchableOpacity
                        style={[styles.serviceToggleBtn, includeTransport && !ownVehicle && styles.serviceToggleBtnActive]}
                        onPress={() => {
                          setIncludeTransport(true);
                          if (ownVehicle) setOwnVehicle(false);
                        }}
                      >
                        <Text style={[styles.serviceToggleText, includeTransport && !ownVehicle && styles.serviceToggleTextActive]}>
                          Include
                        </Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.serviceToggleBtn, (!includeTransport || ownVehicle) && styles.serviceToggleBtnActive]}
                        onPress={() => setIncludeTransport(false)}
                      >
                        <Text style={[styles.serviceToggleText, (!includeTransport || ownVehicle) && styles.serviceToggleTextActive]}>
                          Exclude
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  {/* Own Vehicle Checkbox */}
                  <TouchableOpacity
                    style={styles.ownVehicleCheckRow}
                    onPress={() => {
                      const next = !ownVehicle;
                      setOwnVehicle(next);
                      if (next) setIncludeTransport(false);
                      else setIncludeTransport(true);
                    }}
                    activeOpacity={0.7}
                  >
                    <View style={[styles.checkbox, ownVehicle && styles.checkboxChecked]}>
                      {ownVehicle && <CheckIcon size={14} color="#FFFFFF" strokeWidth={3} />}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 12, fontWeight: '700', color: colors.text }}>
                        🚗 Travelling by Own Vehicle / Self-Drive
                      </Text>
                      <Text style={{ fontSize: 10.5, color: colors.textSecondary }}>
                        Carrier transit is disabled (₹0 fare). Hotel booking remains available.
                      </Text>
                    </View>
                  </TouchableOpacity>
                </View>

                {/* Service 2: Katra Accommodation */}
                <View style={styles.serviceCard}>
                  <View style={styles.serviceCardHeader}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                      <BuildingIcon size={16} color={colors.primary} />
                      <Text style={styles.serviceCardTitle}>Katra Accommodation</Text>
                    </View>
                    <View style={{ flexDirection: 'row', gap: 6 }}>
                      <TouchableOpacity
                        style={[styles.serviceToggleBtn, includeHotel && styles.serviceToggleBtnActive]}
                        onPress={() => setIncludeHotel(true)}
                      >
                        <Text style={[styles.serviceToggleText, includeHotel && styles.serviceToggleTextActive]}>
                          Include
                        </Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.serviceToggleBtn, !includeHotel && styles.serviceToggleBtnActive]}
                        onPress={() => setIncludeHotel(false)}
                      >
                        <Text style={[styles.serviceToggleText, !includeHotel && styles.serviceToggleTextActive]}>
                          Exclude
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                  <Text style={{ fontSize: 10.5, color: colors.textSecondary }}>
                    {includeHotel ? 'Verified Katra hotel room reserved for night halts.' : 'Self-arranged lodging / day-excursion (₹0 hotel rate).'}
                  </Text>
                </View>

                {/* Accessibility & Mobility Preferences */}
                <Text style={styles.inputLabel}>Mobility & Accessibility Preference</Text>
                <View style={styles.mobilityOptionsRow}>
                  {[
                    'Standard Walking Trek',
                    'Senior Citizen (Battery Car)',
                    'Palki / Pony Assistance',
                    'Helicopter Preferred',
                  ].map((m) => (
                    <TouchableOpacity
                      key={m}
                      style={[styles.mobilityChip, mobilityPref === m && styles.mobilityChipActive]}
                      onPress={() => setMobilityPref(m)}
                    >
                      <Text style={[styles.mobilityChipText, mobilityPref === m && styles.mobilityChipTextActive]}>
                        {m}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {/* Darshan Category */}
                <Text style={styles.inputLabel}>Darshan Category</Text>
                <View style={styles.optionsContainer}>
                  {[
                    'Normal Darshan',
                    'VIP Aarti Darshan',
                    'Helicopter Priority Darshan',
                  ].map((c) => (
                    <TouchableOpacity
                      key={c}
                      style={[styles.optionChip, darshanCategory === c && styles.optionChipActive]}
                      onPress={() => setDarshanCategory(c)}
                    >
                      <Text style={[styles.optionText, darshanCategory === c && styles.optionTextActive]}>
                        {c}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {/* ------------------------------------------------- */}
                {/* DYNAMIC INDIVIDUAL PILGRIMS ROSTER (Part 3) */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>Registered Devotees ({pilgrims.length}) *</Text>
                  {prefilledFields.includes('pilgrims') && (
                    <View style={styles.prefilledBadge}>
                      <Text style={styles.prefilledBadgeText}>Filled from your conversation</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.stepSubtitle}>
                  Every pilgrim must have individual details recorded for Shrine Board RFID registration.
                </Text>

                {pilgrims.map((p, idx) => (
                  <View key={idx} style={styles.devoteeCard}>
                    <View style={styles.devoteeHeaderRow}>
                      <Text style={styles.devoteeTitle}>
                        Devotee #{idx + 1} {idx === 0 ? '(Primary Pilgrim)' : ''}
                      </Text>
                      {pilgrims.length > 1 && (
                        <TouchableOpacity onPress={() => handleRemovePilgrim(idx)}>
                          <Text style={styles.removeDevoteeText}>✕ Remove</Text>
                        </TouchableOpacity>
                      )}
                    </View>

                    <Text style={styles.inputLabel}>Full Legal Name *</Text>
                    <TextInput
                      style={styles.input}
                      value={p.full_name}
                      onChangeText={(val) => handleUpdatePilgrim(idx, 'full_name', val)}
                      placeholder={`e.g. ${idx === 0 ? 'Ramesh Sharma' : 'Devotee Full Name'}`}
                      placeholderTextColor={colors.textLight}
                    />

                    <View style={styles.row}>
                      <View style={styles.halfCol}>
                        <Text style={styles.inputLabel}>Age *</Text>
                        <TextInput
                          style={styles.input}
                          value={String(p.age || '')}
                          onChangeText={(val) => handleUpdatePilgrim(idx, 'age', val.replace(/[^0-9]/g, ''))}
                          placeholder="e.g. 38"
                          keyboardType="number-pad"
                          placeholderTextColor={colors.textLight}
                        />
                      </View>
                      <View style={styles.halfCol}>
                        <Text style={styles.inputLabel}>Gender</Text>
                        <View style={styles.genderChipsRow}>
                          {['Male', 'Female', 'Other'].map((g) => (
                            <TouchableOpacity
                              key={g}
                              style={[styles.genderChip, (p.gender || 'Male') === g && styles.genderChipActive]}
                              onPress={() => handleUpdatePilgrim(idx, 'gender', g)}
                            >
                              <Text style={[styles.genderChipText, (p.gender || 'Male') === g && styles.genderChipTextActive]}>
                                {g}
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>
                    </View>
                  </View>
                ))}

                {/* Add Devotee Button */}
                {pilgrims.length < 200 && (
                  <TouchableOpacity style={styles.addDevoteeBtn} onPress={handleAddPilgrim} activeOpacity={0.8}>
                    <Text style={styles.addDevoteeBtnText}>+ Add Another Devotee</Text>
                  </TouchableOpacity>
                )}

                {Boolean(duplicateNameAdvisory) && (
                  <View style={{ backgroundColor: '#FFF3CD', borderColor: '#FFEEBA', borderWidth: 1, padding: 8, borderRadius: 6, marginTop: 8 }}>
                    <Text style={{ fontSize: 11, color: '#856404', fontWeight: '500' }}>
                      {duplicateNameAdvisory}
                    </Text>
                  </View>
                )}

                {/* Primary Contact Details */}
                <View style={styles.sectionDivider} />
                <Text style={styles.sectionHeader}>Primary Contact Details</Text>
                <Text style={styles.stepSubtitle}>
                  For booking SMS notifications, schedule coordination, and emergency contact.
                </Text>

                <View style={styles.row}>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Contact Person</Text>
                    <TextInput
                      style={styles.input}
                      value={fullName}
                      onChangeText={setFullName}
                      placeholder="Primary contact name"
                      placeholderTextColor={colors.textLight}
                    />
                  </View>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Contact Phone (Optional)</Text>
                    <TextInput
                      style={styles.input}
                      value={phone}
                      onChangeText={setPhone}
                      placeholder="10-digit mobile"
                      keyboardType="phone-pad"
                      placeholderTextColor={colors.textLight}
                      accessibilityLabel="Contact Phone Number"
                    />
                  </View>
                </View>

                <Text style={styles.contactHelperText}>
                  * Contact phone is optional and used solely for transit SMS updates. Account authentication is strictly via passwordless Email OTP.
                </Text>

                <TouchableOpacity style={styles.primaryActionButton} onPress={handleProceedToItinerary}>
                  <Text style={styles.primaryActionText}>Continue to Recommended Itinerary →</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* ----------------------------------------------------- */}
            {/* STEP 2: PRE-CONFIRMATION EDITABLE DAY-WISE ITINERARY */}
            {/* ----------------------------------------------------- */}
            {step === 2 && (
              <View style={styles.card}>
                <Text style={styles.stepTitle}>Step 2: Recommended Itinerary & Choices</Text>
                <Text style={styles.stepSubtitle}>
                  Review your complete day-wise plan and customize transport or stay.
                </Text>

                {/* Day-Wise Dynamic Itinerary Presentation */}
                <View style={styles.itineraryContainer}>
                  <Text style={styles.itineraryMainTitle}>📅 Day-Wise Pilgrimage Schedule</Text>

                  {/* Day 1 */}
                  <View style={styles.itineraryCard}>
                    <View style={styles.dayBadge}>
                      <Text style={styles.dayBadgeText}>DAY 1</Text>
                    </View>
                    <Text style={styles.itineraryDayHeading}>
                      Transit from {origin} & Katra Base Arrival
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Morning (06:00 - 14:00)</Text>
                    <Text style={styles.itineraryActivityText}>
                      Board {selectedTransport.name} from {origin}. Relax during scenic transit through Punjab & Jammu foothills.
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Afternoon & Evening</Text>
                    <Text style={styles.itineraryActivityText}>
                      Arrive at Katra. Check into {selectedHotel.name}. Verify your Shrine Board Yatra Parchi registration at Katra counter. Base acclimatization and restful evening.
                    </Text>
                    <Text style={styles.itineraryStayNote}>🏨 Stay: {selectedHotel.name} (Room 1/{roomsCount})</Text>
                  </View>

                  {/* Day 2 */}
                  <View style={styles.itineraryCard}>
                    <View style={styles.dayBadge}>
                      <Text style={styles.dayBadgeText}>DAY 2</Text>
                    </View>
                    <Text style={styles.itineraryDayHeading}>
                      Ascent to Holy Bhawan & Sacred Pindi Darshan
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Morning (06:00 - 12:00)</Text>
                    <Text style={styles.itineraryActivityText}>
                      Begin holy ascent via {selectedAscent.name}. Pass scenic Banganga, Charan Paduka, and Ardhkuwari midway temple.
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Afternoon & Evening</Text>
                    <Text style={styles.itineraryActivityText}>
                      Reach Holy Bhawan. Proceed to the Holy Cave for divine darshan of the Natural Pindies of Maha Kali, Maha Lakshmi, and Maha Saraswati. Collect prasad and experience evening Attka Aarti.
                    </Text>
                    <Text style={styles.itineraryStayNote}>🏨 Night Stay: {selectedHotel.name} / Bhawan Rest Hall</Text>
                  </View>

                  {/* Day 3 */}
                  <View style={styles.itineraryCard}>
                    <View style={styles.dayBadge}>
                      <Text style={styles.dayBadgeText}>DAY 3</Text>
                    </View>
                    <Text style={styles.itineraryDayHeading}>
                      Bhairon Nath Temple & Return Descent
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Morning</Text>
                    <Text style={styles.itineraryActivityText}>
                      Board the Bhawan-Bhairon Passenger Ropeway to Bhairon Ghati (2,017 m). Complete mandatory Bhairon Baba darshan to complete yatra.
                    </Text>
                    <Text style={styles.itineraryTiming}>⏰ Afternoon & Evening</Text>
                    <Text style={styles.itineraryActivityText}>
                      Descent to Katra base along gentle Tarakote track. Foot relaxation, Katra bazaar shopping for dry fruits and devotional souvenirs.
                    </Text>
                    <Text style={styles.itineraryStayNote}>🏨 Stay: {selectedHotel.name}</Text>
                  </View>

                  {/* Day 4 onward dynamically rendered up to duration */}
                  {duration >= 4 &&
                    (duration <= 10 ? (
                      Array.from({ length: duration - 3 }, (_, idx) => {
                        const dayNum = idx + 4;
                        const isLastDay = dayNum === duration;
                        return (
                          <View key={dayNum} style={styles.itineraryCard}>
                            <View style={styles.dayBadge}>
                              <Text style={styles.dayBadgeText}>DAY {dayNum}</Text>
                            </View>
                            <Text style={styles.itineraryDayHeading}>
                              {isLastDay
                                ? `Local Sacred Excursion & Return Journey`
                                : `Day ${dayNum}: Regional Pilgrimage & Valley Excursion`}
                            </Text>
                            <Text style={styles.itineraryTiming}>
                              {isLastDay ? `⏰ Morning & Afternoon` : `⏰ Full Day Exploration`}
                            </Text>
                            <Text style={styles.itineraryActivityText}>
                              {isLastDay
                                ? `Excursion to Baba Dhansar sacred holy spring / Nau Devi Temple. Check-out from ${selectedHotel.name}. Board your return transit back to ${origin}.`
                                : `Spiritual exploration of holy spots around Katra and Jammu hills (Shiv Khori, Patnitop, or Sanasar). Evening Aarti & devotional satsang.`}
                            </Text>
                            <Text style={styles.itineraryStayNote}>
                              {isLastDay
                                ? `🚆 Departure: ${selectedTransport.name} back to ${origin}`
                                : `🏨 Stay: ${selectedHotel.name}`}
                            </Text>
                          </View>
                        );
                      })
                    ) : (
                      <>
                        {[4, 5].map((dayNum) => (
                          <View key={dayNum} style={styles.itineraryCard}>
                            <View style={styles.dayBadge}>
                              <Text style={styles.dayBadgeText}>DAY {dayNum}</Text>
                            </View>
                            <Text style={styles.itineraryDayHeading}>
                              Day {dayNum}: Regional Pilgrimage & Valley Excursion
                            </Text>
                            <Text style={styles.itineraryTiming}>⏰ Full Day Exploration</Text>
                            <Text style={styles.itineraryActivityText}>
                              Spiritual exploration of holy spots around Katra and Jammu hills (Shiv Khori, Patnitop, or Sanasar). Evening Aarti & devotional satsang.
                            </Text>
                            <Text style={styles.itineraryStayNote}>🏨 Stay: {selectedHotel.name}</Text>
                          </View>
                        ))}
                        <View key="intermediate-summary" style={styles.itineraryCard}>
                          <View style={styles.dayBadge}>
                            <Text style={styles.dayBadgeText}>DAYS 6–{duration - 1}</Text>
                          </View>
                          <Text style={styles.itineraryDayHeading}>
                            Regional Pilgrimage & Sacred Excursions ({duration - 6} Days)
                          </Text>
                          <Text style={styles.itineraryTiming}>⏰ Extended Spiritual Immersion</Text>
                          <Text style={styles.itineraryActivityText}>
                            Self-paced spiritual exploration across Jammu & Kashmir sacred sites (Patnitop, Sanasar, Shiv Khori, and local Katra shrines). Sacred rest buffers, satsang, and devotional relaxation.
                          </Text>
                          <Text style={styles.itineraryStayNote}>🏨 Stay: {selectedHotel.name}</Text>
                        </View>
                        <View key={duration} style={styles.itineraryCard}>
                          <View style={styles.dayBadge}>
                            <Text style={styles.dayBadgeText}>DAY {duration}</Text>
                          </View>
                          <Text style={styles.itineraryDayHeading}>
                            Local Sacred Excursion & Return Journey
                          </Text>
                          <Text style={styles.itineraryTiming}>⏰ Morning & Afternoon</Text>
                          <Text style={styles.itineraryActivityText}>
                            Excursion to Baba Dhansar sacred holy spring / Nau Devi Temple. Check-out from {selectedHotel.name}. Board your return transit back to {origin}.
                          </Text>
                          <Text style={styles.itineraryStayNote}>
                            🚆 Departure: {selectedTransport.name} back to {origin}
                          </Text>
                        </View>
                      </>
                    ))}
                </View>

                {/* ------------------------------------------------- */}
                {/* TRANSPORT SELECTION (Requirement 4) */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>🚆 Select Intercity Transport Option</Text>
                  <View style={styles.demoBadge}>
                    <Text style={styles.demoBadgeText}>
                      {ownVehicle ? 'Own Vehicle Active' : (!includeTransport ? 'Transport Excluded' : 'Demonstration Data')}
                    </Text>
                  </View>
                </View>

                {ownVehicle ? (
                  <View style={styles.excludedNoticeBanner}>
                    <Text style={styles.excludedNoticeTitle}>🚗 Own Vehicle / Self-Drive Active</Text>
                    <Text style={styles.excludedNoticeSubtitle}>
                      You are driving in your own vehicle to Katra. Intercity carrier transport booking is excluded (₹0 Fare).
                    </Text>
                  </View>
                ) : !includeTransport ? (
                  <View style={styles.excludedNoticeBanner}>
                    <Text style={styles.excludedNoticeTitle}>🚶 Self-Arranged Transport Active</Text>
                    <Text style={styles.excludedNoticeSubtitle}>
                      Devotees will arrange their own flights, trains, or buses. Carrier transport booking is excluded (₹0 Fare).
                    </Text>
                  </View>
                ) : (
                  REALISTIC_TRANSPORTS.map((t) => {
                    const isSelected = selectedTransport.id === t.id;
                    const tierStyle = getDataTierBadgeStyle(t.dataTier || 'Indicative Estimate');
                    return (
                      <TouchableOpacity
                        key={t.id}
                        style={[styles.selectionCard, isSelected && styles.selectionCardActive]}
                        onPress={() => setSelectedTransport(t)}
                        activeOpacity={0.7}
                      >
                        <View style={styles.cardHeaderRow}>
                          <View style={{ flex: 1 }}>
                            <Text style={styles.cardTitle}>{t.name}</Text>
                            <Text style={styles.cardRoute}>{t.route}</Text>
                          </View>
                          <View style={styles.priceTag}>
                            <Text style={styles.priceTagText}>₹{t.pricePerPerson}</Text>
                            <Text style={styles.perPersonSub}>/ pilgrim</Text>
                          </View>
                        </View>

                        <View style={styles.cardMetaRow}>
                          <Text style={styles.metaItem}>⏰ {t.depTime} - {t.arrTime} ({t.duration})</Text>
                          <Text style={styles.metaItem}>🎟️ {t.classType}</Text>
                          <Text style={[styles.metaItem, { color: '#2E7D32', fontWeight: '700' }]}>
                            ✓ {t.availability}
                          </Text>
                        </View>

                        {/* Truth-in-Data Classification & Provenance */}
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                          <View style={[styles.dataTierPill, { backgroundColor: tierStyle.backgroundColor, borderColor: tierStyle.borderColor }]}>
                            <Text style={[styles.dataTierPillText, { color: tierStyle.textColor }]}>
                              ● {t.dataTier || 'Indicative Estimate'}
                            </Text>
                          </View>
                          {t.dataFreshness && (
                            <Text style={{ fontSize: 10.5, color: colors.textSecondary }}>
                              Source: {t.dataFreshness}
                            </Text>
                          )}
                        </View>
                        {t.restrictions && (
                          <Text style={{ fontSize: 10.5, color: '#C0392B', marginTop: 2 }}>
                            ⚠️ {t.restrictions}
                          </Text>
                        )}

                        <View style={styles.cardFooterRow}>
                          <View style={styles.badgeSmall}>
                            <Text style={styles.badgeSmallText}>{t.badge}</Text>
                          </View>
                          <Text style={[styles.selectActionText, isSelected && styles.selectActionActive]}>
                            {isSelected ? '✓ Selected' : 'Tap to Select'}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    );
                  })
                )}

                {/* ------------------------------------------------- */}
                {/* ASCENT / LOCAL MODES */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>🚡 Select Pilgrimage Ascent Mode</Text>
                </View>

                {ASCENT_MODES.map((a) => {
                  const isSelected = selectedAscent.id === a.id;
                  const ascentTierStyle = getDataTierBadgeStyle(a.dataTier || 'Demonstration Data');
                  return (
                    <TouchableOpacity
                      key={a.id}
                      style={[styles.selectionCard, isSelected && styles.selectionCardActive]}
                      onPress={() => setSelectedAscent(a)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.cardHeaderRow}>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.cardTitle}>{a.name}</Text>
                          <Text style={styles.cardRoute}>{a.description}</Text>
                        </View>
                        <View style={styles.priceTag}>
                          <Text style={styles.priceTagText}>
                            {a.pricePerPerson === 0 ? 'FREE' : `₹${a.pricePerPerson}`}
                          </Text>
                          <Text style={styles.perPersonSub}>/ pilgrim</Text>
                        </View>
                      </View>

                      {/* Truth-in-Data Classification & Provenance */}
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                        <View style={[styles.dataTierPill, { backgroundColor: ascentTierStyle.backgroundColor, borderColor: ascentTierStyle.borderColor }]}>
                          <Text style={[styles.dataTierPillText, { color: ascentTierStyle.textColor }]}>
                            ● {a.dataTier || 'Demonstration Data'}
                          </Text>
                        </View>
                        {a.dataFreshness && (
                          <Text style={{ fontSize: 10.5, color: colors.textSecondary }}>
                            Source: {a.dataFreshness}
                          </Text>
                        )}
                      </View>
                      {a.restrictions && (
                        <Text style={{ fontSize: 10.5, color: '#C0392B', marginTop: 2 }}>
                          ⚠️ {a.restrictions}
                        </Text>
                      )}

                      <View style={styles.cardFooterRow}>
                        <View style={styles.badgeSmall}>
                          <Text style={styles.badgeSmallText}>{a.duration}</Text>
                        </View>
                        <Text style={[styles.selectActionText, isSelected && styles.selectActionActive]}>
                          {isSelected ? '✓ Selected' : 'Tap to Select'}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}

                {/* ------------------------------------------------- */}
                {/* ACCOMMODATION SELECTION (Requirement 5) */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>🏨 Select Accommodation (Katra / Bhawan)</Text>
                  <View style={styles.demoBadge}>
                    <Text style={styles.demoBadgeText}>{!includeHotel ? 'Hotel Excluded' : 'Honest Rates'}</Text>
                  </View>
                </View>

                {!includeHotel ? (
                  <View style={styles.excludedNoticeBanner}>
                    <Text style={styles.excludedNoticeTitle}>🏨 Self-Arranged Accommodation Active</Text>
                    <Text style={styles.excludedNoticeSubtitle}>
                      No Katra hotel is reserved through the portal. Devotees arrange their own lodging or day-excursion (₹0 accommodation rate).
                    </Text>
                  </View>
                ) : (
                  ACCOMMODATION_CATALOGUE.map((h) => {
                    const isSelected = selectedHotel.id === h.id;
                    const totalHotelCost = h.pricePerNight * roomsCount * nightsCount;
                    return (
                      <TouchableOpacity
                        key={h.id}
                        style={[styles.selectionCard, isSelected && styles.selectionCardActive]}
                        onPress={() => setSelectedHotel(h)}
                        activeOpacity={0.7}
                      >
                        <View style={styles.cardHeaderRow}>
                          <View style={{ flex: 1 }}>
                            <Text style={styles.cardTitle}>{h.name}</Text>
                            <Text style={styles.cardRoute}>📍 {h.location} • {h.roomType}</Text>
                          </View>
                          <View style={styles.priceTag}>
                            <Text style={styles.priceTagText}>₹{h.pricePerNight}</Text>
                            <Text style={styles.perPersonSub}>/ night</Text>
                          </View>
                        </View>

                        <View style={styles.cardMetaRow}>
                          <Text style={styles.metaItem}>🛏️ Requires {roomsCount} room(s) for {paxCount} pilgrim(s)</Text>
                          <Text style={styles.metaItem}>🌙 {nightsCount} Nights Stay: ₹{totalHotelCost}</Text>
                        </View>

                        <View style={{ marginTop: 4 }}>
                          <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                            ✨ {h.facilities.join(' • ')}
                          </Text>
                          <Text style={{ fontSize: 10.5, color: '#C0392B', marginTop: 2 }}>
                            ⚠️ {h.restrictions}
                          </Text>
                        </View>

                        <View style={styles.cardFooterRow}>
                          <View style={styles.badgeSmall}>
                            <Text style={styles.badgeSmallText}>{h.badge}</Text>
                          </View>
                          <Text style={[styles.selectActionText, isSelected && styles.selectActionActive]}>
                            {isSelected ? '✓ Selected' : 'Tap to Select'}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    );
                  })
                )}

                {/* ------------------------------------------------- */}
                {/* LIVE DYNAMIC BUDGET RECALCULATION */}
                {/* ------------------------------------------------- */}
                <View style={styles.budgetBox}>
                  <View style={styles.budgetHeaderRow}>
                    <Text style={styles.budgetTitle}>Dynamic Live Budget Breakdown</Text>
                    <Text style={styles.budgetGrandTotal}>₹{grandTotal}</Text>
                  </View>
                  <Text style={styles.perPersonGrandText}>
                    ≈ ₹{perPersonCost} per pilgrim (for {paxCount} pilgrim{paxCount > 1 ? 's' : ''})
                  </Text>

                  <View style={styles.budgetDivider} />
                  <Text style={styles.budgetBreakdownText}>
                    • Intercity Transport: {ownVehicle ? 'Own Vehicle / Private Conveyance (₹0 Fare)' : (!includeTransport ? 'Self-Arranged (₹0 Fare)' : `${selectedTransport.name}: ₹${transportCost} (₹${selectedTransport.pricePerPerson} × ${paxCount})`)}
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Holy Ascent ({selectedAscent.name}): ₹{ascentCost} (₹{selectedAscent.pricePerPerson} × {paxCount})
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Accommodation: {!includeHotel ? 'Self-Arranged Lodging (₹0 Rate)' : `${selectedHotel.name}: ₹${hotelCost} (₹${selectedHotel.pricePerNight} × ${roomsCount} rm × ${nightsCount} n)`}
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Shrine Darshan / RFID Parchi: {darshanCost === 0 ? 'FREE' : `₹${darshanCost}`}
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Meals & Local Transfers (Estimate): ₹{mealsEstCost} (₹350/day per pilgrim)
                  </Text>

                  {userBudgetNum > 0 && (
                    <View style={styles.budgetComparisonBox}>
                      <Text style={{ fontSize: 12, fontWeight: '700', color: budgetDifference >= 0 ? '#155724' : '#721C24' }}>
                        {budgetDifference >= 0
                          ? `✓ Within Target Budget: ₹${budgetDifference} surplus remaining.`
                          : `⚠️ Exceeds Target Budget by ₹${Math.abs(budgetDifference)}.`}
                      </Text>
                    </View>
                  )}
                </View>

                {/* Action Buttons */}
                <View style={styles.buttonRow}>
                  <TouchableOpacity style={styles.backBtn} onPress={() => setStep(1)}>
                    <Text style={styles.backBtnText}>← Back</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.nextBtnFlex} onPress={handleProceedToReview}>
                    <Text style={styles.nextBtnText}>Review & Authorize →</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* ----------------------------------------------------- */}
            {/* STEP 3: MANDATORY HUMAN REVIEW & AUTHENTICATION GATE */}
            {/* ----------------------------------------------------- */}
            {step === 3 && (
              <View style={styles.card}>
                <Text style={styles.stepTitle}>Step 3: Verification & Human Guardrail</Text>
                <Text style={styles.stepSubtitle}>
                  Mandatory human authorization and authentication before pass issuance.
                </Text>

                {/* Pre-Booking Comprehensive Summary */}
                <View style={styles.summaryBox}>
                  <Text style={styles.summaryTitle}>Pilgrimage Reservation Summary</Text>
                  <Text style={styles.summaryLine}>• Route: <Text style={styles.bold}>{origin} → Katra Base & Holy Bhawan</Text></Text>
                  <Text style={styles.summaryLine}>• Yatra Dates: <Text style={styles.bold}>{startDate}</Text> to <Text style={styles.bold}>{returnDate}</Text> ({duration} Days / {nightsCount} Nights)</Text>
                  <Text style={styles.summaryLine}>• Pilgrims: <Text style={styles.bold}>{paxCount} Devotee(s)</Text></Text>

                  {/* Registered Devotees Roster */}
                  {pilgrims && pilgrims.length > 0 && (
                    <View style={{ marginVertical: 6, paddingLeft: 8, borderLeftWidth: 2, borderLeftColor: colors.gold }}>
                      <Text style={{ fontSize: 11, fontWeight: '700', color: colors.primary, marginBottom: 2 }}>
                        Registered Devotees ({pilgrims.length}):
                      </Text>
                      {pilgrims.map((p, idx) => (
                        <Text key={idx} style={{ fontSize: 11, color: colors.text, marginBottom: 1 }}>
                          {idx + 1}. <Text style={styles.bold}>{p.full_name || `Devotee ${idx + 1}`}</Text> ({p.age || '—'} yrs, {p.gender || 'Not specified'})
                        </Text>
                      ))}
                    </View>
                  )}

                  <Text style={styles.summaryLine}>• Primary Contact: <Text style={styles.bold}>{(pilgrims[0]?.full_name || fullName)}</Text>{phone ? ` (Contact: +91-${phone})` : ''}</Text>
                  <Text style={styles.summaryLine}>• Darshan Category: <Text style={styles.bold}>{darshanCategory}</Text></Text>
                  <Text style={styles.summaryLine}>
                    • Intercity Transport: <Text style={styles.bold}>
                      {ownVehicle
                        ? 'Own Vehicle / Private Conveyance (₹0 Fare)'
                        : (!includeTransport ? 'Self-Arranged Transport (₹0 Fare)' : `${selectedTransport.name} (₹${transportCost})`)}
                    </Text>
                  </Text>
                  <Text style={styles.summaryLine}>• Ascent Mode: <Text style={styles.bold}>{selectedAscent.name}</Text> (₹{ascentCost}) <Text style={{ fontSize: 11, color: '#721C24', fontWeight: '700' }}>[{selectedAscent.dataTier || 'Demonstration Data'}]</Text></Text>
                  <Text style={styles.summaryLine}>
                    • Accommodation: <Text style={styles.bold}>
                      {!includeHotel
                        ? 'Self-Arranged Lodging (₹0 Rate)'
                        : `${selectedHotel.name} (${roomsCount} room(s), ${nightsCount} night(s) — ₹${hotelCost})`}
                    </Text>
                  </Text>
                  <Text style={styles.summaryLine}>• Estimated Total Package: <Text style={styles.boldPrice}>₹{grandTotal}</Text> (₹{perPersonCost} / pilgrim)</Text>
                </View>

                {/* Mandatory Academic Guardrail Notice */}
                <View style={styles.safetyCard}>
                  <Text style={styles.safetyHeader}>SANDBOXED SIMULATION GUARDRAIL</Text>
                  <Text style={styles.safetyBody}>
                    This system generates a verified proof-of-concept RPA reservation pass. Real darshan parchi and helicopter tickets MUST be purchased through Shri Mata Vaishno Devi Shrine Board at <Text style={styles.bold}>maavaishnodevi.org</Text>.
                  </Text>
                </View>

                <TouchableOpacity
                  style={styles.checkboxContainer}
                  onPress={() => setAuthorized(!authorized)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.checkbox, authorized && styles.checkboxChecked]}>
                    {authorized && <CheckIcon size={14} color="#FFFFFF" strokeWidth={3} />}
                  </View>
                  <Text style={styles.checkboxLabel}>
                    I confirm that I have reviewed the yatra schedule, selected transport, accommodation, and understand this is an educational mock reservation pass.
                  </Text>
                </TouchableOpacity>

                {/* ------------------------------------------------- */}
                {/* AUTHENTICATION GATE (Requirement 6) */}
                {/* ------------------------------------------------- */}
                <View style={styles.authGateBox}>
                  {currentUser ? (
                    <View style={styles.authSuccessRow}>
                      <View style={styles.authIconCircle}>
                        <CheckIcon size={14} color="#155724" />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.authSuccessTitle}>Authenticated User Account</Text>
                        <Text style={styles.authSuccessSub}>
                          Linked to: {currentUser.email || currentUser.name || 'Verified Devotee'}
                        </Text>
                      </View>
                    </View>
                  ) : (
                    <View>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                        <UserIcon size={16} color={colors.primary} />
                        <Text style={styles.authGateTitle}>Sign In Required for Confirmation</Text>
                      </View>
                      <Text style={styles.authGateSub}>
                        Please sign in with your email address using passwordless 6-digit email OTP. Your draft booking, selected itinerary, and travel choices are preserved.
                      </Text>
                      <TouchableOpacity
                        style={[styles.primaryActionButton, { marginTop: 10 }]}
                        onPress={handleOpenEmailAuth}
                        activeOpacity={0.8}
                        accessibilityLabel="Sign In with Email OTP"
                      >
                        <Text style={styles.primaryActionText}>Sign In with Email OTP →</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </View>

                {/* Action Buttons */}
                <View style={styles.buttonRow}>
                  <TouchableOpacity style={styles.backBtn} onPress={() => setStep(2)}>
                    <Text style={styles.backBtnText}>← Back</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[
                      styles.confirmBtn,
                      (!authorized || loading) && styles.confirmBtnDisabled,
                    ]}
                    onPress={handleConfirmBookingExecution}
                    disabled={!authorized || loading}
                  >
                    {loading ? (
                      <ActivityIndicator size="small" color="#FFFFFF" />
                    ) : (
                      <Text style={styles.confirmBtnText}>
                        {currentUser ? 'Confirm & Issue Pass 🔱' : 'Sign In & Confirm 🔱'}
                      </Text>
                    )}
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* ----------------------------------------------------- */}
            {/* STEP 4: FINAL DEMONSTRATION CONFIRMATION SCREEN */}
            {/* ----------------------------------------------------- */}
            {step === 4 && generatedPass && (
              <View style={styles.card}>
                <View style={styles.passHeader}>
                  <View style={styles.passIconCircle}>
                    <CheckIcon size={28} color="#FFFFFF" strokeWidth={2.5} />
                  </View>
                  <Text style={styles.passTitle}>Pilgrimage Pass Generated</Text>
                  <Text style={styles.passSubtitle}>Shri Mata Vaishno Devi Shrine Board (Prototype)</Text>
                </View>

                <View style={styles.passCard}>
                  <View style={styles.passTopRow}>
                    <View>
                      <Text style={styles.passLabel}>PASS REFERENCE ID</Text>
                      <Text style={styles.passRefText}>{generatedPass.booking_id}</Text>
                    </View>
                    <TouchableOpacity style={styles.copyBtn} onPress={handleCopyPass}>
                      <CopyIcon size={14} color={colors.primary} />
                      <Text style={styles.copyBtnText}>Copy</Text>
                    </TouchableOpacity>
                  </View>

                  <View style={styles.passDivider} />

                  <View style={styles.passGrid}>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>PRIMARY DEVOTEE</Text>
                      <Text style={styles.passValue}>{generatedPass.receipt?.primaryDevotee || fullName}</Text>
                    </View>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>PILGRIMS (PAX)</Text>
                      <Text style={styles.passValue}>{paxCount} Person(s)</Text>
                    </View>
                  </View>

                  <View style={styles.passGrid}>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>YATRA START</Text>
                      <Text style={styles.passValue}>{startDate}</Text>
                    </View>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>RETURN DATE</Text>
                      <Text style={styles.passValue}>{returnDate}</Text>
                    </View>
                  </View>

                  <View style={styles.passGrid}>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>INTERCITY TRANSPORT</Text>
                      <Text style={styles.passValue}>
                        {ownVehicle
                          ? 'Own Vehicle / Private Conveyance'
                          : (!includeTransport ? 'Self-Arranged Transport' : selectedTransport.name)}
                      </Text>
                      <Text style={{ fontSize: 10, color: '#856404', fontWeight: '700', marginTop: 2 }}>
                        ● {ownVehicle ? 'Self-Drive' : (!includeTransport ? 'Self-Arranged' : (selectedTransport.dataTier || 'Indicative Estimate'))}
                      </Text>
                    </View>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>ASCENT MODE</Text>
                      <Text style={styles.passValue}>{selectedAscent.name}</Text>
                      <Text style={{ fontSize: 10, color: '#721C24', fontWeight: '700', marginTop: 2 }}>
                        ● {selectedAscent.dataTier || 'Demonstration Data'}
                      </Text>
                    </View>
                  </View>

                  <View style={styles.passGrid}>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>ACCOMMODATION</Text>
                      <Text style={styles.passValue}>
                        {!includeHotel ? 'Self-Arranged Lodging (₹0)' : selectedHotel.name}
                      </Text>
                    </View>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>TOTAL FARE</Text>
                      <Text style={[styles.passValue, { color: colors.primary, fontWeight: '800' }]}>
                        ₹{grandTotal}
                      </Text>
                    </View>
                  </View>

                  {/* Registered Devotees Pass Tokens */}
                  {pilgrims && pilgrims.length > 0 && (
                    <View style={{ marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.goldBorder }}>
                      <Text style={[styles.passLabel, { marginBottom: 6 }]}>REGISTERED DEVOTEES & ACCESS PASSES</Text>
                      {pilgrims.map((p, idx) => (
                        <View key={idx} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4, backgroundColor: '#FAF5EB', padding: 6, borderRadius: 6 }}>
                          <Text style={{ fontSize: 11.5, fontWeight: '700', color: colors.text }}>
                            {idx + 1}. {p.full_name || `Devotee #${idx + 1}`} ({p.age || '—'} yrs, {p.gender || 'Devotee'})
                          </Text>
                          <View style={{ backgroundColor: '#D4EDDA', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 }}>
                            <Text style={{ fontSize: 9.5, fontWeight: '800', color: '#155724' }}>
                              PASS #{generatedPass.booking_id ? generatedPass.booking_id.slice(-4) : 'RPA'}-{idx + 1}
                            </Text>
                          </View>
                        </View>
                      ))}
                    </View>
                  )}

                  <View style={styles.passFooter}>
                    <Text style={styles.passFooterText}>
                      STATUS: {generatedPass.status || 'SIMULATED_ISSUED'}
                    </Text>
                    <Text style={styles.passTimestamp}>Issued: {generatedPass.generatedAt}</Text>
                  </View>
                </View>

                {/* Notice */}
                <View style={[styles.safetyCard, { marginTop: 16 }]}>
                  <Text style={styles.safetyHeader}>ACADEMIC DEMONSTRATION NOTICE</Text>
                  <Text style={styles.safetyBody}>
                    This reservation pass is a proof-of-concept simulation generated for academic evaluation. To enter the Katra track and board real helicopters, original official parchi must be obtained at <Text style={styles.bold}>maavaishnodevi.org</Text> or the Katra registration counters.
                  </Text>
                </View>

                {/* Final Actions */}
                <View style={styles.finalActionsRow}>
                  <TouchableOpacity
                    style={styles.primaryActionButton}
                    onPress={() => {
                      setActiveView('my-bookings');
                      if (currentUser) loadUserBookings();
                    }}
                  >
                    <Text style={styles.primaryActionText}>View in My Bookings →</Text>
                  </TouchableOpacity>

                  <TouchableOpacity style={styles.secondaryActionButton} onPress={handleReset}>
                    <Text style={styles.secondaryActionText}>+ Plan Another Yatra</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}
          </ScrollView>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  viewToggleBar: {
    flexDirection: 'row',
    backgroundColor: '#FAF5EB',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.goldBorder,
    gap: 8,
  },
  viewToggleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 9,
    borderRadius: 8,
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  viewToggleBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  viewToggleText: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.primary,
  },
  viewToggleTextActive: {
    color: '#FFFFFF',
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: colors.surfaceWhite,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  progressStep: {
    alignItems: 'center',
    flex: 1,
  },
  stepCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  stepCircleActive: {
    backgroundColor: colors.primary,
  },
  stepCircleInactive: {
    backgroundColor: colors.border,
  },
  stepNumber: {
    fontSize: 12,
    fontWeight: '700',
  },
  stepNumberActive: {
    color: '#FFFFFF',
  },
  stepNumberInactive: {
    color: colors.textSecondary,
  },
  stepLabel: {
    fontSize: 10.5,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: colors.surfaceWhite,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  stepTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.primary,
    marginBottom: 4,
  },
  stepSubtitle: {
    fontSize: 12.5,
    color: colors.textSecondary,
    marginBottom: 16,
    lineHeight: 18,
  },
  inputLabel: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 6,
    marginTop: 10,
  },
  input: {
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.text,
  },
  originChipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8,
  },
  hubChip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  hubChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  hubChipText: {
    fontSize: 12,
    color: colors.primary,
    fontWeight: '600',
  },
  hubChipTextActive: {
    color: '#FFFFFF',
  },
  destinationBadge: {
    backgroundColor: '#FAF5EB',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    marginBottom: 6,
  },
  destinationBadgeText: {
    fontSize: 13.5,
    fontWeight: '700',
    color: colors.primary,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  halfCol: {
    flex: 1,
  },
  numericInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 6,
  },
  stepperCtrlBtn: {
    width: 36,
    height: 38,
    borderRadius: 8,
    backgroundColor: colors.goldSubtle,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperCtrlText: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.burgundy,
    marginTop: -2,
  },
  numericTextInput: {
    flex: 1,
    height: 38,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
    borderRadius: 8,
    textAlign: 'center',
    fontSize: 14,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  quickChipsRow: {
    flexDirection: 'row',
    gap: 4,
    flexWrap: 'wrap',
  },
  quickChip: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  quickChipActive: {
    backgroundColor: colors.burgundy,
    borderColor: colors.burgundy,
  },
  quickChipText: {
    fontSize: 10.5,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  quickChipTextActive: {
    color: colors.textWhite,
  },
  stepperRow: {
    flexDirection: 'row',
    gap: 4,
  },
  stepperBtn: {
    flex: 1,
    paddingVertical: 9,
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceWhite,
  },
  stepperBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  stepperText: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.text,
  },
  stepperTextActive: {
    color: '#FFFFFF',
  },
  returnDateNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 8,
    padding: 9,
    marginTop: 8,
    marginBottom: 4,
  },
  returnDateNoticeText: {
    fontSize: 12,
    color: colors.primary,
  },
  mobilityOptionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  mobilityChip: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  mobilityChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  mobilityChipText: {
    fontSize: 11.5,
    color: colors.primary,
    fontWeight: '600',
  },
  mobilityChipTextActive: {
    color: '#FFFFFF',
  },
  optionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  optionChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  optionChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  optionText: {
    fontSize: 12,
    color: colors.primary,
    fontWeight: '600',
  },
  optionTextActive: {
    color: '#FFFFFF',
  },
  sectionDivider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 16,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  sectionHeader: {
    fontSize: 14.5,
    fontWeight: '800',
    color: colors.primary,
  },
  demoBadge: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 0.5,
    borderColor: '#F59E0B',
  },
  demoBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#92400E',
  },
  primaryActionButton: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
  },
  primaryActionText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  secondaryActionButton: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  secondaryActionText: {
    color: colors.primary,
    fontSize: 13.5,
    fontWeight: '700',
  },
  itineraryContainer: {
    marginBottom: 16,
  },
  itineraryMainTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: colors.primary,
    marginBottom: 10,
  },
  itineraryCard: {
    backgroundColor: '#FAF5EB',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  dayBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginBottom: 4,
  },
  dayBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '800',
  },
  itineraryDayHeading: {
    fontSize: 13.5,
    fontWeight: '800',
    color: colors.primary,
    marginBottom: 4,
  },
  itineraryTiming: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.gold,
    marginTop: 4,
  },
  itineraryActivityText: {
    fontSize: 12,
    color: colors.text,
    lineHeight: 17,
  },
  itineraryStayNote: {
    fontSize: 11.5,
    fontWeight: '600',
    color: colors.primary,
    marginTop: 6,
  },
  selectionCard: {
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  selectionCardActive: {
    borderColor: colors.primary,
    borderWidth: 1.5,
    backgroundColor: '#FAF5EB',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  cardTitle: {
    fontSize: 13.5,
    fontWeight: '800',
    color: colors.primary,
  },
  cardRoute: {
    fontSize: 11.5,
    color: colors.textSecondary,
    marginTop: 2,
  },
  priceTag: {
    alignItems: 'flex-end',
  },
  priceTagText: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.primary,
  },
  perPersonSub: {
    fontSize: 9.5,
    color: colors.textSecondary,
  },
  cardMetaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 6,
    paddingTop: 6,
    borderTopWidth: 0.5,
    borderTopColor: colors.border,
  },
  metaItem: {
    fontSize: 11,
    color: colors.text,
  },
  cardFooterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  badgeSmall: {
    backgroundColor: '#FAF5EB',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 0.5,
    borderColor: colors.goldBorder,
  },
  badgeSmallText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.primary,
  },
  dataTierPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 0.8,
  },
  dataTierPillText: {
    fontSize: 10,
    fontWeight: '800',
  },
  selectActionText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  selectActionActive: {
    color: colors.primary,
    fontWeight: '800',
  },
  budgetBox: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1.5,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
  },
  budgetHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  budgetTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.primary,
  },
  budgetGrandTotal: {
    fontSize: 18,
    fontWeight: '900',
    color: colors.primary,
  },
  perPersonGrandText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: colors.textSecondary,
    marginTop: 2,
  },
  budgetDivider: {
    height: 1,
    backgroundColor: colors.goldBorder,
    marginVertical: 8,
  },
  budgetBreakdownText: {
    fontSize: 11.5,
    color: colors.text,
    marginBottom: 3,
  },
  budgetComparisonBox: {
    marginTop: 8,
    padding: 8,
    borderRadius: 6,
    backgroundColor: colors.surfaceWhite,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 16,
  },
  backBtn: {
    flex: 1,
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  backBtnText: {
    color: colors.primary,
    fontSize: 13.5,
    fontWeight: '700',
  },
  nextBtnFlex: {
    flex: 2,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  nextBtnText: {
    color: '#FFFFFF',
    fontSize: 13.5,
    fontWeight: '800',
  },
  summaryBox: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  summaryTitle: {
    fontSize: 13.5,
    fontWeight: '800',
    color: colors.primary,
    marginBottom: 6,
  },
  summaryLine: {
    fontSize: 12,
    color: colors.text,
    marginBottom: 3,
  },
  bold: {
    fontWeight: '700',
  },
  boldPrice: {
    fontWeight: '900',
    color: colors.primary,
  },
  safetyCard: {
    backgroundColor: '#FFF4F4',
    borderWidth: 1,
    borderColor: '#F5C6CB',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  safetyHeader: {
    fontSize: 11,
    fontWeight: '800',
    color: '#721C24',
    marginBottom: 2,
    letterSpacing: 0.5,
  },
  safetyBody: {
    fontSize: 11,
    color: '#721C24',
    lineHeight: 15,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 12,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 4,
    borderWidth: 1.5,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  checkboxChecked: {
    backgroundColor: colors.primary,
  },
  checkboxLabel: {
    flex: 1,
    fontSize: 11.5,
    color: colors.text,
    lineHeight: 16,
  },
  contactHelperText: {
    fontSize: 11,
    color: colors.textSecondary,
    fontStyle: 'italic',
    marginTop: -4,
    marginBottom: 12,
    lineHeight: 15,
  },
  authGateBox: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  authGateTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.primary,
  },
  authGateSub: {
    fontSize: 11.5,
    color: colors.textSecondary,
    lineHeight: 15,
  },
  authSuccessRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  authIconCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#D4EDDA',
    alignItems: 'center',
    justifyContent: 'center',
  },
  authSuccessTitle: {
    fontSize: 12.5,
    fontWeight: '800',
    color: '#155724',
  },
  authSuccessSub: {
    fontSize: 11,
    color: '#155724',
  },
  confirmBtn: {
    flex: 2,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  confirmBtnDisabled: {
    opacity: 0.5,
  },
  confirmBtnText: {
    color: '#FFFFFF',
    fontSize: 13.5,
    fontWeight: '800',
  },
  passHeader: {
    alignItems: 'center',
    marginBottom: 16,
  },
  passIconCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  passTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: colors.primary,
  },
  passSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  passCard: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1.5,
    borderColor: colors.goldBorder,
    borderRadius: 12,
    padding: 16,
  },
  passTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  passLabel: {
    fontSize: 9.5,
    fontWeight: '800',
    color: colors.gold,
    letterSpacing: 0.5,
  },
  passRefText: {
    fontSize: 15,
    fontWeight: '900',
    color: colors.primary,
  },
  copyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  copyBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
  },
  passDivider: {
    height: 1,
    backgroundColor: colors.goldBorder,
    marginVertical: 10,
  },
  passGrid: {
    flexDirection: 'row',
    marginBottom: 10,
    gap: 8,
  },
  gridCol: {
    flex: 1,
  },
  passValue: {
    fontSize: 12.5,
    fontWeight: '700',
    color: colors.text,
    marginTop: 1,
  },
  passFooter: {
    borderTopWidth: 1,
    borderTopColor: colors.goldBorder,
    paddingTop: 8,
    marginTop: 4,
  },
  passFooterText: {
    fontSize: 10.5,
    fontWeight: '800',
    color: '#155724',
  },
  passTimestamp: {
    fontSize: 9.5,
    color: colors.textSecondary,
    marginTop: 1,
  },
  finalActionsRow: {
    marginTop: 16,
  },
  emptyStateBox: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 16,
  },
  emptyStateTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.primary,
    marginTop: 12,
    marginBottom: 4,
  },
  emptyStateSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 16,
  },
  bookingHistoryCard: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  bookingHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  bookingRefText: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.primary,
  },
  bookingDateSub: {
    fontSize: 11.5,
    color: colors.textSecondary,
  },
  bookingBadgeConfirmed: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#D4EDDA',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  bookingBadgeText: {
    fontSize: 9.5,
    fontWeight: '800',
    color: '#155724',
  },
  bookingDetailsRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 0.5,
    borderTopColor: colors.goldBorder,
    gap: 3,
  },
  bookingDetailItem: {
    fontSize: 11.5,
    color: colors.text,
  },
  expandItineraryBtn: {
    marginTop: 8,
    paddingVertical: 6,
    alignItems: 'center',
    backgroundColor: colors.surfaceWhite,
    borderRadius: 6,
    borderWidth: 0.5,
    borderColor: colors.goldBorder,
  },
  expandItineraryText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
  },
  expandedItineraryBox: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 0.5,
    borderTopColor: colors.goldBorder,
  },
  // Flexible services & dynamic pilgrim management (Phase 8.8.54A)
  serviceCard: {
    backgroundColor: '#FAF5EB',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  serviceCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  serviceCardTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.primary,
  },
  serviceToggleBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.surfaceWhite,
  },
  serviceToggleBtnActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  serviceToggleText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  serviceToggleTextActive: {
    color: '#FFFFFF',
  },
  ownVehicleCheckRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 0.5,
    borderTopColor: colors.goldBorder,
  },
  devoteeCard: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  devoteeHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  devoteeTitle: {
    fontSize: 12.5,
    fontWeight: '800',
    color: colors.primary,
  },
  removeDevoteeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#C0392B',
  },
  genderChipsRow: {
    flexDirection: 'row',
    gap: 6,
    marginTop: 4,
  },
  genderChip: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: '#FAF5EB',
  },
  genderChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  genderChipText: {
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  genderChipTextActive: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  addDevoteeBtn: {
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FAF5EB',
    marginTop: 6,
    marginBottom: 12,
  },
  addDevoteeBtnText: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.primary,
  },
  prefilledBadge: {
    backgroundColor: '#DCFCE7',
    borderWidth: 1,
    borderColor: '#86EFAC',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  prefilledBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#166534',
  },
  excludedNoticeBanner: {
    backgroundColor: '#F3F4F6',
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 8,
    padding: 12,
    marginVertical: 10,
  },
  excludedNoticeTitle: {
    fontSize: 12.5,
    fontWeight: '800',
    color: '#374151',
  },
  excludedNoticeSubtitle: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 2,
  },
});
