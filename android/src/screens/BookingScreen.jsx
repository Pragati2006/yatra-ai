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
  requestOtp,
  verifyOtp,
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

  // Form State (Intake)
  const [origin, setOrigin] = useState(route?.params?.origin || 'Delhi');
  const [destination] = useState('Katra (Shri Mata Vaishno Devi)');
  const [startDate, setStartDate] = useState(route?.params?.startDate || route?.params?.travelDate || '2026-11-10');
  const [duration, setDuration] = useState(parseInt(route?.params?.duration || '4', 10));
  const [pax, setPax] = useState(parseInt(route?.params?.pax || '2', 10));
  const [budgetAmount, setBudgetAmount] = useState(route?.params?.budget ? String(route?.params?.budget) : '15000');
  const [darshanCategory, setDarshanCategory] = useState('Normal Darshan');
  const [mobilityPref, setMobilityPref] = useState('Standard Walking Trek');

  // Primary Devotee
  const [fullName, setFullName] = useState(route?.params?.fullName || 'Ramesh Sharma');
  const [age, setAge] = useState('38');
  const [gender, setGender] = useState('Male');
  const [phone, setPhone] = useState('9876543210');

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
      setPax(parseInt(route.params.pax, 10));
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
  }, [route?.params]);

  // Step 3 Guardrails & Auth
  const [authorized, setAuthorized] = useState(false);
  const [activeDraftPassId, setActiveDraftPassId] = useState(null);
  const [generatedPass, setGeneratedPass] = useState(null);

  // Inline Auth Gate State
  const [authMode, setAuthMode] = useState(false);
  const [authIdentifier, setAuthIdentifier] = useState('9876543210');
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // My Bookings State
  const [savedBookings, setSavedBookings] = useState([]);
  const [loadingBookings, setLoadingBookings] = useState(false);
  const [expandedBookingId, setExpandedBookingId] = useState(null);

  // Check auth on mount
  useEffect(() => {
    checkUserAuth();
    loadDraftIfAvailable();
  }, []);

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

  const loadDraftIfAvailable = async () => {
    try {
      const draft = await getBookingDraft();
      if (draft && !route?.params?.overrideDraft) {
        if (draft.origin) setOrigin(draft.origin);
        if (draft.startDate) setStartDate(draft.startDate);
        if (draft.duration) setDuration(draft.duration);
        if (draft.pax) setPax(draft.pax);
        if (draft.fullName) setFullName(draft.fullName);
        if (draft.phone) setPhone(draft.phone);
      }
    } catch {
      // ignore
    }
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

  // Dynamic Financial Breakdown
  const transportCost = (selectedTransport?.pricePerPerson || 0) * paxCount;
  const ascentCost = (selectedAscent?.pricePerPerson || 0) * paxCount;
  const hotelCost = (selectedHotel?.pricePerNight || 0) * roomsCount * nightsCount;
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
      selectedTransportId: selectedTransport?.id,
      selectedHotelId: selectedHotel?.id,
    });
  }, [origin, startDate, duration, pax, fullName, phone, selectedTransport, selectedHotel]);

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

  // Handle Inline OTP Request
  const handleRequestOtp = async () => {
    if (!authIdentifier.trim()) {
      Alert.alert('Required', 'Please enter your mobile number or email.');
      return;
    }
    setAuthLoading(true);
    try {
      const res = await requestOtp({ identifier: authIdentifier.trim() });
      setOtpSent(true);
      Alert.alert(
        'OTP Sent',
        res?.demo_otp
          ? `Devotee Demo OTP is: ${res.demo_otp}`
          : 'Verification code sent to your mobile.'
      );
      if (res?.demo_otp) {
        setOtpCode(res.demo_otp);
      }
    } catch (err) {
      Alert.alert('Auth Error', err.message || 'Could not send verification code.');
    } finally {
      setAuthLoading(false);
    }
  };

  // Handle Inline OTP Verification
  const handleVerifyOtp = async () => {
    if (!otpCode.trim()) {
      Alert.alert('Required', 'Please enter the 6-digit verification code.');
      return;
    }
    setAuthLoading(true);
    try {
      const res = await verifyOtp({
        identifier: authIdentifier.trim(),
        otp: otpCode.trim(),
      });
      if (res?.token) {
        await saveAuthToken(res.token);
      }
      if (res?.user) {
        setCurrentUser(res.user);
        await setStoredUser(res.user);
      }
      setAuthMode(false);
      Alert.alert('Verified', 'Authentication successful! You can now complete your booking.');
    } catch (err) {
      Alert.alert('Verification Failed', err.message || 'Invalid verification code.');
    } finally {
      setAuthLoading(false);
    }
  };

  // Step 1 -> Step 2 validation
  const handleProceedToItinerary = () => {
    if (!origin.trim()) {
      Alert.alert('Missing Field', 'Please enter your departure city / origin.');
      return;
    }
    if (!fullName.trim() || !phone.trim()) {
      Alert.alert('Pilgrim Details', 'Please provide primary devotee name and mobile number.');
      return;
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

    // Compulsory Authentication Gate (Requirement 6)
    if (!currentUser) {
      setAuthMode(true);
      Alert.alert(
        'Authentication Required',
        'To issue your verified demonstration pilgrimage pass and save it to your account, please verify your mobile number.'
      );
      return;
    }

    setLoading(true);
    try {
      const passId = activeDraftPassId || `VD-RPA-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
      if (!activeDraftPassId) {
        setActiveDraftPassId(passId);
      }

      const bookingRecord = {
        booking_id: passId,
        pax_count: paxCount,
        slot_date: startDate,
        category: darshanCategory,
        slot_time: 'Morning (06:00 - 12:00)',
        transport_mode: selectedTransport?.mode || 'Train',
        transport_info: `${selectedTransport?.name} (${selectedTransport?.route})`,
        hotel_name: selectedHotel?.name,
        total_price: grandTotal,
        receipt: {
          reference: passId,
          primaryDevotee: fullName,
          phone,
          origin,
          destination,
          startDate,
          returnDate,
          durationDays: duration,
          pax: paxCount,
          rooms: roomsCount,
          nights: nightsCount,
          transport: {
            ...selectedTransport,
            dataTier: selectedTransport?.dataTier || 'Indicative Estimate',
            dataFreshness: selectedTransport?.dataFreshness || 'Published Timetable (IRCTC/NTES 139)',
            restrictions: selectedTransport?.restrictions || 'Advance reservation required',
          },
          ascentMode: {
            ...selectedAscent,
            dataTier: selectedAscent?.dataTier || 'Demonstration Data',
            dataFreshness: selectedAscent?.dataFreshness || 'Simulated Pilgrimage Model',
            restrictions: selectedAscent?.restrictions || 'Official booking via maavaishnodevi.org',
          },
          hotel: selectedHotel,
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
            transport: selectedTransport,
            slot: { category: darshanCategory, slot_date: startDate, slot_time: 'Morning' },
            total_price: grandTotal,
          },
          pax: paxCount,
          user_name: fullName,
          hotel: selectedHotel,
          hotel_nights: nightsCount,
          human_authorized: true,
        });
      } catch {
        // Continue with local demonstration record
      }

      // Persist in User Account
      try {
        await saveBooking(bookingRecord);
      } catch {
        // Fallback for offline mode
      }

      setGeneratedPass({
        ...bookingRecord,
        status: 'CONFIRMED (SIMULATED RPA PASS)',
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
                  Please sign in with your mobile number to view and manage your pilgrimage passes across devices.
                </Text>
                <TouchableOpacity
                  style={styles.primaryActionButton}
                  onPress={() => {
                    setActiveView('wizard');
                    setStep(3);
                    setAuthMode(true);
                  }}
                >
                  <Text style={styles.primaryActionText}>Sign In / Verify OTP</Text>
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
                    <Text style={styles.inputLabel}>Start Date (YYYY-MM-DD) *</Text>
                    <TextInput
                      style={styles.input}
                      value={startDate}
                      onChangeText={setStartDate}
                      placeholder="2026-11-10"
                      placeholderTextColor={colors.textLight}
                    />
                  </View>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Duration (Days) *</Text>
                    <View style={styles.stepperRow}>
                      {[2, 3, 4, 5, 6].map((d) => (
                        <TouchableOpacity
                          key={d}
                          style={[styles.stepperBtn, duration === d && styles.stepperBtnActive]}
                          onPress={() => setDuration(d)}
                        >
                          <Text style={[styles.stepperText, duration === d && styles.stepperTextActive]}>
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
                    <View style={styles.stepperRow}>
                      {[1, 2, 3, 4, 5, 6].map((num) => (
                        <TouchableOpacity
                          key={num}
                          style={[styles.stepperBtn, pax === num && styles.stepperBtnActive]}
                          onPress={() => setPax(num)}
                        >
                          <Text style={[styles.stepperText, pax === num && styles.stepperTextActive]}>
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

                {/* Primary Pilgrim Information */}
                <View style={styles.sectionDivider} />
                <Text style={styles.sectionHeader}>Primary Pilgrim Registration</Text>

                <Text style={styles.inputLabel}>Full Name *</Text>
                <TextInput
                  style={styles.input}
                  value={fullName}
                  onChangeText={setFullName}
                  placeholder="e.g. Ramesh Sharma"
                  placeholderTextColor={colors.textLight}
                />

                <View style={styles.row}>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Age *</Text>
                    <TextInput
                      style={styles.input}
                      value={age}
                      onChangeText={setAge}
                      placeholder="38"
                      keyboardType="number-pad"
                      placeholderTextColor={colors.textLight}
                    />
                  </View>
                  <View style={styles.halfCol}>
                    <Text style={styles.inputLabel}>Mobile (+91) *</Text>
                    <TextInput
                      style={styles.input}
                      value={phone}
                      onChangeText={setPhone}
                      placeholder="9876543210"
                      keyboardType="phone-pad"
                      placeholderTextColor={colors.textLight}
                    />
                  </View>
                </View>

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

                  {/* Day 4 (if duration >= 4) */}
                  {duration >= 4 && (
                    <View style={styles.itineraryCard}>
                      <View style={styles.dayBadge}>
                        <Text style={styles.dayBadgeText}>DAY 4</Text>
                      </View>
                      <Text style={styles.itineraryDayHeading}>
                        Local Sacred Excursion & Return Journey
                      </Text>
                      <Text style={styles.itineraryTiming}>⏰ Morning & Afternoon</Text>
                      <Text style={styles.itineraryActivityText}>
                        Excursion to Baba Dhansar sacred holy spring / Nau Devi Temple. Return to hotel for check-out. Board your return transit back to {origin}.
                      </Text>
                      <Text style={styles.itineraryStayNote}>🚆 Departure: {selectedTransport.name} back to {origin}</Text>
                    </View>
                  )}
                </View>

                {/* ------------------------------------------------- */}
                {/* TRANSPORT SELECTION (Requirement 4) */}
                {/* ------------------------------------------------- */}
                <View style={styles.sectionDivider} />
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionHeader}>🚆 Select Intercity Transport Option</Text>
                  <View style={styles.demoBadge}>
                    <Text style={styles.demoBadgeText}>Demonstration Data</Text>
                  </View>
                </View>

                {REALISTIC_TRANSPORTS.map((t) => {
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
                })}

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
                    <Text style={styles.demoBadgeText}>Honest Rates</Text>
                  </View>
                </View>

                {ACCOMMODATION_CATALOGUE.map((h) => {
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
                })}

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
                    • Intercity Transport ({selectedTransport.name}): ₹{transportCost} (₹{selectedTransport.pricePerPerson} × {paxCount})
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Holy Ascent ({selectedAscent.name}): ₹{ascentCost} (₹{selectedAscent.pricePerPerson} × {paxCount})
                  </Text>
                  <Text style={styles.budgetBreakdownText}>
                    • Accommodation ({selectedHotel.name}): ₹{hotelCost} (₹{selectedHotel.pricePerNight} × {roomsCount} room × {nightsCount} nights)
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
                  <Text style={styles.summaryLine}>• Primary Devotee: <Text style={styles.bold}>{fullName}</Text> ({age} yrs, {gender}, +91-{phone})</Text>
                  <Text style={styles.summaryLine}>• Route: <Text style={styles.bold}>{origin} → Katra</Text></Text>
                  <Text style={styles.summaryLine}>• Yatra Dates: <Text style={styles.bold}>{startDate}</Text> to <Text style={styles.bold}>{returnDate}</Text> ({duration} Days)</Text>
                  <Text style={styles.summaryLine}>• Pilgrims: <Text style={styles.bold}>{paxCount} Person(s)</Text></Text>
                  <Text style={styles.summaryLine}>• Darshan Category: <Text style={styles.bold}>{darshanCategory}</Text></Text>
                  <Text style={styles.summaryLine}>• Selected Transport: <Text style={styles.bold}>{selectedTransport.name}</Text> (₹{transportCost}) <Text style={{ fontSize: 11, color: '#856404', fontWeight: '700' }}>[{selectedTransport.dataTier || 'Indicative Estimate'}]</Text></Text>
                  <Text style={styles.summaryLine}>• Ascent Mode: <Text style={styles.bold}>{selectedAscent.name}</Text> (₹{ascentCost}) <Text style={{ fontSize: 11, color: '#721C24', fontWeight: '700' }}>[{selectedAscent.dataTier || 'Demonstration Data'}]</Text></Text>
                  <Text style={styles.summaryLine}>• Selected Stay: <Text style={styles.bold}>{selectedHotel.name}</Text> ({roomsCount} room(s), {nightsCount} night(s) — ₹{hotelCost})</Text>
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
                          Linked to: {currentUser.name || currentUser.phone || currentUser.email || 'Verified Devotee'}
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
                        Please verify your mobile number. Your draft booking is preserved and will be linked to your account.
                      </Text>

                      {!otpSent ? (
                        <View style={{ marginTop: 8 }}>
                          <TextInput
                            style={styles.input}
                            value={authIdentifier}
                            onChangeText={setAuthIdentifier}
                            placeholder="Mobile (+91) or Email"
                            placeholderTextColor={colors.textLight}
                          />
                          <TouchableOpacity
                            style={[styles.primaryActionButton, { marginTop: 6 }]}
                            onPress={handleRequestOtp}
                            disabled={authLoading}
                          >
                            {authLoading ? (
                              <ActivityIndicator size="small" color="#FFFFFF" />
                            ) : (
                              <Text style={styles.primaryActionText}>Send Verification Code (OTP)</Text>
                            )}
                          </TouchableOpacity>
                        </View>
                      ) : (
                        <View style={{ marginTop: 8 }}>
                          <TextInput
                            style={styles.input}
                            value={otpCode}
                            onChangeText={setOtpCode}
                            placeholder="Enter 6-digit OTP"
                            keyboardType="number-pad"
                            maxLength={6}
                            placeholderTextColor={colors.textLight}
                          />
                          <TouchableOpacity
                            style={[styles.primaryActionButton, { marginTop: 6 }]}
                            onPress={handleVerifyOtp}
                            disabled={authLoading}
                          >
                            {authLoading ? (
                              <ActivityIndicator size="small" color="#FFFFFF" />
                            ) : (
                              <Text style={styles.primaryActionText}>Verify & Continue Booking</Text>
                            )}
                          </TouchableOpacity>
                        </View>
                      )}
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
                      <Text style={styles.passValue}>{selectedTransport.name}</Text>
                      <Text style={{ fontSize: 10, color: '#856404', fontWeight: '700', marginTop: 2 }}>
                        ● {selectedTransport.dataTier || 'Indicative Estimate'}
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
                      <Text style={styles.passValue}>{selectedHotel.name}</Text>
                    </View>
                    <View style={styles.gridCol}>
                      <Text style={styles.passLabel}>TOTAL FARE</Text>
                      <Text style={[styles.passValue, { color: colors.primary, fontWeight: '800' }]}>
                        ₹{grandTotal}
                      </Text>
                    </View>
                  </View>

                  <View style={styles.passFooter}>
                    <Text style={styles.passFooterText}>
                      STATUS: {generatedPass.status || 'VERIFIED (SIMULATION)'}
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
});
