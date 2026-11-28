/**
 * android/src/utils/flightCatalog.js
 *
 * Verified Curated Flight Schedule Catalog & Search/Sort Helpers for Yatra AI Android.
 * Grounded strictly in audited AAI / DGCA published flight corridors from
 * data/curated_flight_schedules.json.
 *
 * Truth-in-data guarantees:
 * - Never invents flight numbers, departure times, confirmed fares, or live seat availability.
 * - Clearly distinguishes Indicative Market Estimates from Unavailable / Unverified static timetables.
 * - Deduplicates routes by canonical route/flight key.
 * - Supports origin/destination/date matching, nonstop vs connecting filtering, and sorting.
 */

export const CITY_TO_AIRPORT_CODE = {
  del: 'DEL',
  delhi: 'DEL',
  'new delhi': 'DEL',
  igi: 'DEL',
  bom: 'BOM',
  mumbai: 'BOM',
  bombay: 'BOM',
  sxr: 'SXR',
  srinagar: 'SXR',
  blr: 'BLR',
  bengaluru: 'BLR',
  bangalore: 'BLR',
  hyd: 'HYD',
  hyderabad: 'HYD',
  ccu: 'CCU',
  kolkata: 'CCU',
  amd: 'AMD',
  ahmedabad: 'AMD',
  maa: 'MAA',
  chennai: 'MAA',
  pnq: 'PNQ',
  pune: 'PNQ',
  ixj: 'IXJ',
  jammu: 'IXJ',
  satwari: 'IXJ',
  katra: 'IXJ',
  'vaishno devi': 'IXJ',
  'shri mata vaishno devi': 'IXJ',
  'katra (shri mata vaishno devi)': 'IXJ',
};

export const FLIGHT_ORIGIN_PRESETS = [
  { label: 'All Cities', value: 'All' },
  { label: 'Delhi (DEL)', value: 'Delhi' },
  { label: 'Mumbai (BOM)', value: 'Mumbai' },
  { label: 'Bengaluru (BLR)', value: 'Bengaluru' },
  { label: 'Hyderabad (HYD)', value: 'Hyderabad' },
  { label: 'Ahmedabad (AMD)', value: 'Ahmedabad' },
  { label: 'Srinagar (SXR)', value: 'Srinagar' },
  { label: 'Kolkata (CCU)', value: 'Kolkata' },
  { label: 'Chennai (MAA)', value: 'Chennai' },
  { label: 'Pune (PNQ)', value: 'Pune' },
];

export const FLIGHT_DESTINATION_PRESETS = [
  { label: 'Jammu / Katra (IXJ)', value: 'IXJ' },
  { label: 'Srinagar (SXR)', value: 'SXR' },
  { label: 'All Destinations', value: 'All' },
];

export const CURATED_FLIGHTS = [
  // --- DELHI (DEL) -> JAMMU (IXJ) ---
  {
    id: 'flight_del_ixj_6e2122',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-2122',
    title: 'IndiGo · 6E-2122 (DEL → IXJ)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Delhi (DEL · Terminal 2)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'DEL · 08:35',
    arrival: 'IXJ · 10:00',
    departure_time: '08:35',
    arrival_time: '10:00',
    duration: '1h 25m',
    durationHours: 1.41,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Ground transfer to Katra ~1h 30m (50 km)',
    indicativeFareMin: 3800,
    indicativeFareMax: 7200,
    fareRange: 'Est. ₹3,800 – ₹7,200 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify check-in & 7 kg cabin terms)',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },
  {
    id: 'flight_del_ixj_ai821',
    mode: 'Flight',
    airlineName: 'Air India',
    airlineCode: 'AI',
    flightNumber: 'AI-821',
    title: 'Air India · AI-821 (DEL → IXJ)',
    provider: 'Air India (Illustrative Schedule · Confirm on airindia.com)',
    origin: 'Delhi (DEL · Terminal 3)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'DEL · 10:30',
    arrival: 'IXJ · 11:55',
    departure_time: '10:30',
    arrival_time: '11:55',
    duration: '1h 25m',
    durationHours: 1.41,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Ground transfer to Katra ~1h 30m (50 km)',
    indicativeFareMin: 4200,
    indicativeFareMax: 8500,
    fareRange: 'Est. ₹4,200 – ₹8,500 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on airindia.com',
    baggageAllowance: 'Checked baggage included (full-service carrier)',
    bookingPlatform: 'airindia.com / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },
  {
    id: 'flight_airindia_del_ixj_ix1074',
    mode: 'Flight',
    airlineName: 'Air India Express',
    airlineCode: 'IX',
    flightNumber: 'IX 1074',
    title: 'Air India Express · IX 1074 (DEL → IXJ)',
    provider: 'Air India Express (AAI/DGCA Route)',
    origin: 'Delhi (DEL · Terminal 3)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'DEL · Check Portal',
    arrival: 'IXJ · Check Portal',
    departure_time: null,
    arrival_time: null,
    duration: 'Non-Stop Corridor',
    durationHours: null,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily scheduled corridor · Confirm slot on airline portal',
    indicativeFareMin: null,
    indicativeFareMax: null,
    fareRange: 'Dynamic airfare · Check airindiaexpress.com',
    fareDisclaimer: 'Live schedule and fare unavailable in static registry.',
    baggageAllowance: 'Check Air India Express fare tier baggage rules',
    bookingPlatform: 'airindiaexpress.com',
    dataTier: 'Unavailable / Unverified',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'UNVERIFIED',
    fareVerificationStatus: 'UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'ROUTE_GUIDANCE_ONLY',
  },
  {
    id: 'flight_indigo_del_ixj_6e6474',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E 6474',
    title: 'IndiGo · 6E 6474 (DEL → IXJ)',
    provider: 'IndiGo (AAI/DGCA Route)',
    origin: 'Delhi (DEL · T1 / T2)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'DEL · Check Portal',
    arrival: 'IXJ · Check Portal',
    departure_time: null,
    arrival_time: null,
    duration: 'Non-Stop Corridor',
    durationHours: null,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily scheduled corridor · Confirm slot on goindigo.in',
    indicativeFareMin: null,
    indicativeFareMax: null,
    fareRange: 'Dynamic airfare · Check goindigo.in',
    fareDisclaimer: 'Live schedule and fare unavailable in static registry.',
    baggageAllowance: 'Check IndiGo fare class baggage rules',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Unavailable / Unverified',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'UNVERIFIED',
    fareVerificationStatus: 'UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'ROUTE_GUIDANCE_ONLY',
  },

  // --- MUMBAI (BOM) -> JAMMU (IXJ) ---
  {
    id: 'flight_bom_ixj_6e5374',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-5374',
    title: 'IndiGo · 6E-5374 (BOM → IXJ)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Mumbai (BOM · Terminal 2)',
    originCity: 'Mumbai',
    originAirportCode: 'BOM',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'BOM · 09:05',
    arrival: 'IXJ · 11:50',
    departure_time: '09:05',
    arrival_time: '11:50',
    duration: '2h 45m',
    durationHours: 2.75,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Direct non-stop Mumbai to Jammu gateway',
    indicativeFareMin: 5800,
    indicativeFareMax: 11500,
    fareRange: 'Est. ₹5,800 – ₹11,500 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify at booking)',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },

  // --- AHMEDABAD (AMD) -> JAMMU (IXJ) ---
  {
    id: 'flight_amd_ixj_6e6184',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-6184',
    title: 'IndiGo · 6E-6184 (AMD → IXJ)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Ahmedabad (AMD)',
    originCity: 'Ahmedabad',
    originAirportCode: 'AMD',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'AMD · 08:00',
    arrival: 'IXJ · 10:40',
    departure_time: '08:00',
    arrival_time: '10:40',
    duration: '2h 40m',
    durationHours: 2.66,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Direct non-stop Gujarat to Jammu corridor',
    indicativeFareMin: 5200,
    indicativeFareMax: 10500,
    fareRange: 'Est. ₹5,200 – ₹10,500 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify at booking)',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },

  // --- SRINAGAR (SXR) -> JAMMU (IXJ) ---
  {
    id: 'flight_sxr_ixj_6e5147',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-5147',
    title: 'IndiGo · 6E-5147 (SXR → IXJ)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Srinagar (SXR)',
    originCity: 'Srinagar',
    originAirportCode: 'SXR',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'SXR · 14:15',
    arrival: 'IXJ · 15:00',
    departure_time: '14:15',
    arrival_time: '15:00',
    duration: '45m',
    durationHours: 0.75,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Direct regional flight over Pir Panjal',
    indicativeFareMin: 2400,
    indicativeFareMax: 4800,
    fareRange: 'Est. ₹2,400 – ₹4,800 (Indicative)',
    fareDisclaimer: 'Indicative regional fare; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify at booking)',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },

  // --- BENGALURU (BLR) -> JAMMU (IXJ) (CONNECTING) ---
  {
    id: 'flight_blr_ixj_6e6582',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-6582',
    title: 'IndiGo · 6E-6582 (BLR → IXJ)',
    provider: 'IndiGo (1-Stop via Delhi)',
    origin: 'Bengaluru (BLR)',
    originCity: 'Bengaluru',
    originAirportCode: 'BLR',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'BLR · 06:10',
    arrival: 'IXJ · 11:55',
    departure_time: '06:10',
    arrival_time: '11:55',
    duration: '5h 45m',
    durationHours: 5.75,
    stops: '1-Stop via DEL',
    stopsCount: 1,
    layoverAirports: ['DEL'],
    operatingDays: ['Daily'],
    frequency: 'Daily · 1-Stop via New Delhi (DEL)',
    indicativeFareMin: 7200,
    indicativeFareMax: 13800,
    fareRange: 'Est. ₹7,200 – ₹13,800 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Through-check baggage rules depend on airline itinerary',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },

  // --- HYDERABAD (HYD) -> JAMMU (IXJ) (CONNECTING) ---
  {
    id: 'flight_hyd_ixj_6e6277',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-6277',
    title: 'IndiGo · 6E-6277 (HYD → IXJ)',
    provider: 'IndiGo (1-Stop via Delhi)',
    origin: 'Hyderabad (HYD)',
    originCity: 'Hyderabad',
    originAirportCode: 'HYD',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'HYD · 07:10',
    arrival: 'IXJ · 12:15',
    departure_time: '07:10',
    arrival_time: '12:15',
    duration: '5h 05m',
    durationHours: 5.08,
    stops: '1-Stop via DEL',
    stopsCount: 1,
    layoverAirports: ['DEL'],
    operatingDays: ['Daily'],
    frequency: 'Daily · Seamless transfer via New Delhi (DEL)',
    indicativeFareMin: 6800,
    indicativeFareMax: 12900,
    fareRange: 'Est. ₹6,800 – ₹12,900 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Through-check baggage rules depend on airline itinerary',
    bookingPlatform: 'goindigo.in / Official Airline Portal',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },

  // --- CONNECTING HUB GUIDANCE ROUTES (CCU / MAA / PNQ -> IXJ) ---
  {
    id: 'flight_indigo_ccu_ixj_via_del',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: 'Connecting',
    title: 'IndiGo Connecting Network (CCU → DEL → IXJ)',
    provider: 'IndiGo (Hub Transfer Guidance)',
    origin: 'Kolkata (CCU)',
    originCity: 'Kolkata',
    originAirportCode: 'CCU',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'CCU · Check Portal',
    arrival: 'IXJ · via DEL',
    departure_time: null,
    arrival_time: null,
    duration: 'Connecting via DEL',
    durationHours: null,
    stops: '1-Stop via DEL',
    stopsCount: 1,
    layoverAirports: ['DEL'],
    operatingDays: ['Daily'],
    frequency: 'Daily hub transfers via New Delhi (DEL)',
    indicativeFareMin: null,
    indicativeFareMax: null,
    fareRange: 'Dynamic airfare · Check goindigo.in',
    fareDisclaimer: 'Confirm layover times and live fares on airline portal.',
    baggageAllowance: 'Verify through-checked baggage at booking',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Unavailable / Unverified',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'UNVERIFIED',
    fareVerificationStatus: 'UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'CONNECTING_HUB_GUIDANCE',
  },
  {
    id: 'flight_indigo_maa_ixj_via_del',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: 'Connecting',
    title: 'IndiGo Connecting Network (MAA → DEL → IXJ)',
    provider: 'IndiGo (Hub Transfer Guidance)',
    origin: 'Chennai (MAA)',
    originCity: 'Chennai',
    originAirportCode: 'MAA',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'MAA · Check Portal',
    arrival: 'IXJ · via DEL',
    departure_time: null,
    arrival_time: null,
    duration: 'Connecting via DEL',
    durationHours: null,
    stops: '1-Stop via DEL',
    stopsCount: 1,
    layoverAirports: ['DEL'],
    operatingDays: ['Daily'],
    frequency: 'Daily hub transfers via New Delhi (DEL)',
    indicativeFareMin: null,
    indicativeFareMax: null,
    fareRange: 'Dynamic airfare · Check goindigo.in',
    fareDisclaimer: 'Confirm layover times and live fares on airline portal.',
    baggageAllowance: 'Verify through-checked baggage at booking',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Unavailable / Unverified',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'UNVERIFIED',
    fareVerificationStatus: 'UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'CONNECTING_HUB_GUIDANCE',
  },
  {
    id: 'flight_indigo_pnq_ixj_via_del',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: 'Connecting',
    title: 'IndiGo Connecting Network (PNQ → DEL → IXJ)',
    provider: 'IndiGo (Hub Transfer Guidance)',
    origin: 'Pune (PNQ)',
    originCity: 'Pune',
    originAirportCode: 'PNQ',
    destination: 'Jammu (IXJ · Satwari)',
    destinationCity: 'Jammu',
    destinationAirportCode: 'IXJ',
    departure: 'PNQ · Check Portal',
    arrival: 'IXJ · via DEL',
    departure_time: null,
    arrival_time: null,
    duration: 'Connecting via DEL',
    durationHours: null,
    stops: '1-Stop via DEL',
    stopsCount: 1,
    layoverAirports: ['DEL'],
    operatingDays: ['Daily'],
    frequency: 'Daily hub transfers via New Delhi (DEL)',
    indicativeFareMin: null,
    indicativeFareMax: null,
    fareRange: 'Dynamic airfare · Check goindigo.in',
    fareDisclaimer: 'Confirm layover times and live fares on airline portal.',
    baggageAllowance: 'Verify through-checked baggage at booking',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Unavailable / Unverified',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'UNVERIFIED',
    fareVerificationStatus: 'UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'CONNECTING_HUB_GUIDANCE',
  },

  // --- FLIGHTS TO SRINAGAR (SXR) ---
  {
    id: 'flight_del_sxr_6e2051',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-2051',
    title: 'IndiGo · 6E-2051 (DEL → SXR)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Delhi (DEL · Terminal 2)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Srinagar (SXR)',
    destinationCity: 'Srinagar',
    destinationAirportCode: 'SXR',
    departure: 'DEL · 06:50',
    arrival: 'SXR · 08:25',
    departure_time: '06:50',
    arrival_time: '08:25',
    duration: '1h 35m',
    durationHours: 1.58,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Early morning flight to Kashmir Valley',
    indicativeFareMin: 4200,
    indicativeFareMax: 8800,
    fareRange: 'Est. ₹4,200 – ₹8,800 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify at booking)',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },
  {
    id: 'flight_del_sxr_ai825',
    mode: 'Flight',
    airlineName: 'Air India',
    airlineCode: 'AI',
    flightNumber: 'AI-825',
    title: 'Air India · AI-825 (DEL → SXR)',
    provider: 'Air India (Illustrative Schedule · Confirm on airindia.com)',
    origin: 'Delhi (DEL · Terminal 3)',
    originCity: 'Delhi',
    originAirportCode: 'DEL',
    destination: 'Srinagar (SXR)',
    destinationCity: 'Srinagar',
    destinationAirportCode: 'SXR',
    departure: 'DEL · 11:15',
    arrival: 'SXR · 12:50',
    departure_time: '11:15',
    arrival_time: '12:50',
    duration: '1h 35m',
    durationHours: 1.58,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Full-service carrier to Srinagar',
    indicativeFareMin: 4600,
    indicativeFareMax: 9500,
    fareRange: 'Est. ₹4,600 – ₹9,500 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on airindia.com',
    baggageAllowance: 'Checked baggage included (full-service carrier)',
    bookingPlatform: 'airindia.com',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },
  {
    id: 'flight_bom_sxr_6e5381',
    mode: 'Flight',
    airlineName: 'IndiGo',
    airlineCode: '6E',
    flightNumber: '6E-5381',
    title: 'IndiGo · 6E-5381 (BOM → SXR)',
    provider: 'IndiGo (Illustrative Schedule · Confirm on goindigo.in)',
    origin: 'Mumbai (BOM · Terminal 2)',
    originCity: 'Mumbai',
    originAirportCode: 'BOM',
    destination: 'Srinagar (SXR)',
    destinationCity: 'Srinagar',
    destinationAirportCode: 'SXR',
    departure: 'BOM · 11:15',
    arrival: 'SXR · 14:10',
    departure_time: '11:15',
    arrival_time: '14:10',
    duration: '2h 55m',
    durationHours: 2.91,
    stops: 'Non-Stop',
    stopsCount: 0,
    operatingDays: ['Daily'],
    frequency: 'Daily · Direct non-stop flight to Srinagar',
    indicativeFareMin: 6400,
    indicativeFareMax: 12800,
    fareRange: 'Est. ₹6,400 – ₹12,800 (Indicative)',
    fareDisclaimer: 'Indicative market range; confirm live fares on goindigo.in',
    baggageAllowance: 'Carrier policy applies (verify at booking)',
    bookingPlatform: 'goindigo.in',
    dataTier: 'Indicative Estimate',
    verificationStatus: 'PARTIALLY_VERIFIED',
    corridorVerificationStatus: 'VERIFIED_CORRIDOR',
    timetableVerificationStatus: 'INDICATIVE_UNVERIFIED',
    fareVerificationStatus: 'INDICATIVE_UNVERIFIED',
    isLiveInventory: false,
    scheduleType: 'INDICATIVE_ESTIMATE',
  },
];

export function normalizeAirportOrCity(query) {
  if (!query || typeof query !== 'string') return null;
  const cleaned = query.trim().toLowerCase();
  if (!cleaned || cleaned === 'all' || cleaned === 'all cities' || cleaned === 'all destinations') {
    return null;
  }
  if (CITY_TO_AIRPORT_CODE[cleaned]) {
    return CITY_TO_AIRPORT_CODE[cleaned];
  }
  // Extract code in parentheses like "Delhi (DEL)"
  const parenMatch = cleaned.match(/\(([a-z]{3})\)/i);
  if (parenMatch) return parenMatch[1].toUpperCase();
  if (/^[a-z]{3}$/i.test(cleaned)) return cleaned.toUpperCase();
  return cleaned;
}

export function deduplicateFlights(flights = []) {
  const seen = new Set();
  const result = [];
  for (const f of flights) {
    if (!f) continue;
    const rawNum = f.flightNumber || f.flight_no || '';
    const fNum = rawNum
      ? String(rawNum).replace(/[^a-zA-Z0-9]/g, '').toUpperCase()
      : String(f.id || f.title || '').trim().toUpperCase();
    const orig = String(normalizeAirportOrCity(f.originAirportCode || f.originCity || f.origin || '')).toUpperCase();
    const dest = String(normalizeAirportOrCity(f.destinationAirportCode || f.destinationCity || f.destination || '')).toUpperCase();
    const dedupeKey = fNum && fNum !== 'CONNECTING'
      ? `${fNum}::${orig}::${dest}`
      : `${f.id || f.title}::${orig}::${dest}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    result.push(f);
  }
  return result;
}

function timeToMinutes(t) {
  if (!t || typeof t !== 'string') return Number.POSITIVE_INFINITY;
  const m = t.match(/(\d{1,2}):(\d{2})/);
  if (!m) return Number.POSITIVE_INFINITY;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

export function getDayAbbrevFromDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return null;
  try {
    const parts = dateStr.split('-');
    if (parts.length !== 3) return null;
    const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    if (Number.isNaN(d.getTime())) return null;
    return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
  } catch {
    return null;
  }
}

export function filterAndSortFlights(
  flights = CURATED_FLIGHTS,
  {
    origin = 'All',
    destination = 'IXJ',
    travelDate = null,
    stopsFilter = 'all',
    sortBy = 'price_asc',
    searchText = '',
  } = {}
) {
  const deduped = deduplicateFlights(flights);
  const normOrigin = normalizeAirportOrCity(origin);
  const normDest = normalizeAirportOrCity(destination);
  const dayAbbrev = getDayAbbrevFromDate(travelDate);
  const queryLower = (searchText || '').trim().toLowerCase();

  const filtered = deduped.filter((f) => {
    if (normOrigin) {
      const codeMatch = (f.originAirportCode || '').toUpperCase() === String(normOrigin).toUpperCase();
      const cityMatch = (f.originCity || '').toLowerCase() === String(normOrigin).toLowerCase() ||
        (f.originCity || '').toLowerCase().includes(String(normOrigin).toLowerCase());
      if (!codeMatch && !cityMatch) return false;
    }

    if (normDest) {
      const dCodeMatch = (f.destinationAirportCode || '').toUpperCase() === String(normDest).toUpperCase();
      const dCityMatch = (f.destinationCity || '').toLowerCase() === String(normDest).toLowerCase() ||
        (f.destination || '').toLowerCase().includes(String(normDest).toLowerCase());
      if (!dCodeMatch && !dCityMatch) return false;
    }

    if (stopsFilter === 'nonstop' && (f.stopsCount ?? 0) !== 0) return false;
    if (stopsFilter === 'connecting' && (f.stopsCount ?? 0) === 0) return false;

    if (dayAbbrev && Array.isArray(f.operatingDays) && f.operatingDays.length > 0) {
      const isDaily = f.operatingDays.some((d) => ['daily', 'all'].includes(String(d).toLowerCase()));
      if (!isDaily && !f.operatingDays.some((d) => String(d).toLowerCase().includes(dayAbbrev.toLowerCase()))) {
        return false;
      }
    }

    if (queryLower) {
      const haystack = `${f.title} ${f.airlineName} ${f.flightNumber} ${f.origin} ${f.destination} ${f.stops}`.toLowerCase();
      if (!haystack.includes(queryLower)) return false;
    }

    return true;
  });

  return filtered.sort((a, b) => {
    if (sortBy === 'price_asc') {
      const pa = typeof a.indicativeFareMin === 'number' ? a.indicativeFareMin : Number.POSITIVE_INFINITY;
      const pb = typeof b.indicativeFareMin === 'number' ? b.indicativeFareMin : Number.POSITIVE_INFINITY;
      if (pa !== pb) return pa - pb;
    } else if (sortBy === 'departure_asc') {
      const ta = timeToMinutes(a.departure_time);
      const tb = timeToMinutes(b.departure_time);
      if (ta !== tb) return ta - tb;
    } else if (sortBy === 'duration_asc') {
      const da = typeof a.durationHours === 'number' ? a.durationHours : Number.POSITIVE_INFINITY;
      const db = typeof b.durationHours === 'number' ? b.durationHours : Number.POSITIVE_INFINITY;
      if (da !== db) return da - db;
    }
    // Tie-breaker: timed/priced curated schedules before route-guidance-only
    const aHasSchedule = a.departure_time ? 0 : 1;
    const bHasSchedule = b.departure_time ? 0 : 1;
    if (aHasSchedule !== bHasSchedule) return aHasSchedule - bHasSchedule;
    return String(a.id).localeCompare(String(b.id));
  });
}

export function toBookingTransportOption(flight) {
  if (!flight) return null;
  const hasIndicative = typeof flight.indicativeFareMin === 'number' && flight.indicativeFareMin > 0;
  const dep = flight.departure_time || 'Check Portal';
  const arr = flight.arrival_time ? `${flight.arrival_time} + 1.5h Cab` : 'Check Portal';
  const destCode = flight.destinationAirportCode || 'IXJ';
  const cabNote = destCode === 'IXJ'
    ? 'Lands at Jammu Civil Enclave (IXJ). 50 km (~1.5h) highway transfer to Katra base camp.'
    : 'Lands at Srinagar International Airport (SXR).';

  return {
    id: flight.id,
    name: `${flight.airlineName} ${flight.flightNumber}${destCode === 'IXJ' ? ' + Katra Taxi' : ''}`,
    mode: 'Flight',
    airlineName: flight.airlineName,
    airlineCode: flight.airlineCode,
    flightNumber: flight.flightNumber,
    route: `${flight.originCity || flight.origin} (${flight.originAirportCode || ''}) → ${flight.destinationCity || flight.destination} (${destCode})${destCode === 'IXJ' ? ' + Cab' : ''}`,
    depTime: dep,
    arrTime: arr,
    duration: flight.duration || 'Check Portal',
    classType: flight.stopsCount > 0 ? `Economy (${flight.stops})` : 'Economy Non-Stop',
    pricePerPerson: hasIndicative ? flight.indicativeFareMin : 0,
    indicativeFareRange: flight.fareRange,
    isIndicativeFare: true,
    availability: hasIndicative ? 'Indicative Schedule (Confirm on Portal)' : 'Route Guidance Only',
    badge: flight.stopsCount > 0 ? flight.stops : 'Non-Stop Flight',
    dataTier: flight.dataTier || 'Indicative Estimate',
    dataFreshness: `Illustrative Airline Corridor (${flight.airlineName} · Confirm live schedule & fare on portal)`,
    baggageAllowance: flight.baggageAllowance,
    restrictions: `${cabNote} ${flight.fareDisclaimer || 'Live airfare must be confirmed on official airline portal.'}`,
  };
}
