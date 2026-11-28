import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  VERIFIED_DESTINATION_GALLERIES,
  resolveDestinationImages,
  PUBLIC_ASSETS_BASE_URL,
  resolveImageUri,
  getImageRequestHeaders,
  buildAndroidImageSource,
  getCandidateImageUrls,
  markImageUriFailed,
  isImageUriFailed,
} from '../utils/destinationImages.js';

import {
  CURATED_FLIGHTS,
  normalizeAirportOrCity,
  deduplicateFlights,
  getDayAbbrevFromDate,
  filterAndSortFlights,
  toBookingTransportOption,
  FLIGHT_ORIGIN_PRESETS,
  FLIGHT_DESTINATION_PRESETS,
} from '../utils/flightCatalog.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');

// ==============================================================================
// PHASE 1: SIDEBAR PERFORMANCE, CACHING & NON-BLOCKING DATA LOADING
// ==============================================================================

test('Phase 1.1: api.js implements TTL cache, in-flight dedup, session isolation, and avoids 45s LLM transport call', () => {
  const apiCode = fs.readFileSync(path.join(SRC_DIR, 'services/api.js'), 'utf8');

  assert.ok(apiCode.includes('STATIC_CATALOG_TTL_MS'), 'Must define static catalog cache TTL');
  assert.ok(apiCode.includes('WEATHER_CACHE_TTL_MS'), 'Must define weather cache TTL');
  assert.ok(apiCode.includes('HISTORY_CACHE_TTL_MS'), 'Must define short user-scoped chat history cache TTL');
  assert.ok(apiCode.includes('inFlightRequests'), 'Must deduplicate concurrent identical requests');
  assert.ok(apiCode.includes('dedupedFetch'), 'Must wrap network calls with dedupedFetch');
  assert.ok(apiCode.includes('clearUserSessionCaches'), 'Must expose session cache invalidation');
  assert.ok(apiCode.includes('clearCatalogCaches'), 'Must clear catalog caches when switching backend URL');
  assert.ok(
    !apiCode.includes("searchYatra('transport options')"),
    'fetchTransportOptions must NOT trigger slow conversational LLM loop'
  );
  assert.ok(apiCode.includes('getCachedAccommodations'), 'Must expose cached accommodations reader');
  assert.ok(apiCode.includes('getCachedTourismSpots'), 'Must expose cached tourism spots reader');
  assert.ok(apiCode.includes('getCachedWeather'), 'Must expose cached weather reader');
  assert.ok(apiCode.includes('getCachedTransportOptions'), 'Must expose cached transport reader');
});

test('Phase 1.2: Sidebar screens render cached/curated data immediately without blocking full-screen spinner', () => {
  const screens = [
    { file: 'screens/AccommodationScreen.jsx', cacheFn: 'getCachedAccommodations' },
    { file: 'screens/TourismScreen.jsx', cacheFn: 'getCachedTourismSpots' },
    { file: 'screens/TransportScreen.jsx', cacheFn: 'getCachedTransportOptions' },
    { file: 'screens/WeatherScreen.jsx', cacheFn: 'getCachedWeather' },
  ];

  for (const { file, cacheFn } of screens) {
    const code = fs.readFileSync(path.join(SRC_DIR, file), 'utf8');
    assert.ok(code.includes(cacheFn), `${file} must read initial cached data synchronously via ${cacheFn}`);
    assert.ok(!code.includes('loading && !refreshing'), `${file} must NOT block visible list with loading spinner`);
  }

  const drawerCode = fs.readFileSync(path.join(SRC_DIR, 'components/SidebarDrawer.jsx'), 'utf8');
  assert.ok(drawerCode.includes('getCachedChatHistory'), 'SidebarDrawer must reuse cached history immediately on reopen');
  assert.ok(drawerCode.includes('clearUserSessionCaches'), 'SidebarDrawer must isolate history across user switches');

  const tourismCode = fs.readFileSync(path.join(SRC_DIR, 'screens/TourismScreen.jsx'), 'utf8');
  assert.ok(tourismCode.includes('mergeTourismSpots'), 'TourismScreen must merge backend records with verified ALL_43_DESTINATIONS');
});

// ==============================================================================
// PHASES 2-5: ANDROID PHOTOGRAPHS, HOLY SHRINES, WIKIMEDIA HEADERS & REMOVAL
// ==============================================================================

test('Phase 2.1: Relative local asset paths resolve cleanly to HTTPS Cloudflare CDN URLs', () => {
  const relUri = resolveImageUri('/assets/images/places/Jhajjar Kotli.jpg');
  assert.equal(relUri, `${PUBLIC_ASSETS_BASE_URL}/assets/images/places/Jhajjar%20Kotli.jpg`);

  const himkotiUri = resolveImageUri('/assets/images/places/Himkoti.jpg');
  assert.equal(himkotiUri, `${PUBLIC_ASSETS_BASE_URL}/assets/images/places/Himkoti.jpg`);

  const peerKhoUri = resolveImageUri('/assets/images/places/Peer Kho Cave Temple.jpg');
  assert.equal(peerKhoUri, `${PUBLIC_ASSETS_BASE_URL}/assets/images/places/Peer%20Kho%20Cave%20Temple.jpg`);
});

test('Phase 2.2: Wikimedia URLs attach compliant User-Agent headers; CDN assets avoid custom Wikimedia UA', () => {
  const wikiSrc = buildAndroidImageSource(
    'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Patni_top_%2838%29.JPG/960px-Patni_top_%2838%29.JPG'
  );
  assert.ok(wikiSrc?.headers?.['User-Agent']?.includes('YatraAI'), 'Wikimedia URL must receive YatraAI User-Agent header');

  const cdnSrc = buildAndroidImageSource('https://yatra-ai.pages.dev/assets/images/places/Bhairavnath%20Temple.png');
  assert.equal(cdnSrc?.headers, undefined, 'Cloudflare CDN URL does not need Wikimedia headers');
});

test('Phase 2.3: Holy Pilgrimage Sites resolve valid verified candidates and municipal Katra never maps to Bhawan photo', () => {
  for (const name of ['Bhairavnath Temple', 'Ardhkuwari Cave', 'Charan Paduka', 'Ban Ganga', 'Holy Cave Bhawan (Mata Vaishno Devi)']) {
    const urls = getCandidateImageUrls({ name }, VERIFIED_DESTINATION_GALLERIES[name]?.images || []);
    assert.ok(urls.length >= 1, `${name} must have at least one verified candidate URL`);
    assert.ok(urls.every((u) => u.startsWith('https://')), `${name} candidate URLs must be HTTPS`);
  }

  const katraCandidates = getCandidateImageUrls({ name: 'Katra' }, []);
  assert.equal(katraCandidates.length, 0, 'Municipal Katra town must not borrow Bhawan shrine photograph');
  assert.equal(resolveDestinationImages('Hotels in Katra main bazaar'), null);
});

test('Phase 2.4: Failed URI session cache excludes broken candidate on subsequent retries', () => {
  const brokenUri = 'https://example.invalid/broken-yatra-test-photo.jpg';
  markImageUriFailed(brokenUri);
  assert.equal(isImageUriFailed(brokenUri), true);

  const candidates = getCandidateImageUrls(
    { name: 'Test Spot', image_url: brokenUri },
    [{ thumbnail_url: 'https://yatra-ai.pages.dev/assets/images/places/Patnitop.jpg' }]
  );
  assert.ok(!candidates.includes(brokenUri), 'Session-failed URI must be skipped');
  assert.equal(candidates[0], 'https://yatra-ai.pages.dev/assets/images/places/Patnitop.jpg');
});

test('Phase 3: UI components never show Photo unavailable, archival curation, or empty placeholder boxes', () => {
  const forbiddenPhrases = [
    'Photo unavailable',
    'Verified photograph in archival curation',
    'fallbackNoticeBox',
    'imageFallbackBox',
  ];
  for (const relPath of ['components/TourismCard.jsx', 'components/ChatBubble.jsx']) {
    const code = fs.readFileSync(path.join(SRC_DIR, relPath), 'utf8');
    for (const phrase of forbiddenPhrases) {
      assert.ok(!code.includes(phrase), `${relPath} must not contain "${phrase}"`);
    }
  }
});

// ==============================================================================
// PHASE 9: EXPANDED FLIGHT OPTIONS & BOOKING INTEGRATION
// ==============================================================================

test('Phase 9.1: Curated flight catalog delivers multiple flights per major corridor with required metadata', () => {
  assert.ok(Array.isArray(CURATED_FLIGHTS) && CURATED_FLIGHTS.length >= 10, 'Must provide rich curated flight schedule catalog');

  const delIxj = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'DEL', destination: 'IXJ', sortBy: 'price_asc' });
  assert.ok(delIxj.length >= 3, `Expected >= 3 flights for DEL->IXJ, found ${delIxj.length}`);

  const airlines = new Set(delIxj.map((f) => f.airlineName));
  assert.ok(airlines.size >= 2, 'DEL->IXJ must cover multiple airlines');

  for (const f of delIxj) {
    assert.ok(f.airlineName && f.airlineCode && f.flightNumber, 'Each flight must identify airline and flight number');
    assert.ok(f.originAirportCode === 'DEL' && f.destinationAirportCode === 'IXJ', 'Airport codes must match query');
    assert.ok(f.fareRange && f.fareDisclaimer, 'Must include honest indicative fare labeling');
    assert.ok(f.baggageAllowance, 'Must include baggage allowance info');
    assert.equal(f.isLiveInventory, false, 'Static curated catalog must never falsely claim live inventory');
    assert.notEqual(f.verificationStatus, 'OFFICIALLY_VERIFIED', 'Static flights must not claim OFFICIALLY_VERIFIED');
    assert.equal(f.verificationStatus, 'PARTIALLY_VERIFIED');
  }
});

test('Phase 8.8.57B: Flight provenance integrity across curated JSON, REALISTIC_TRANSPORTS, and BookingScreen totals', () => {
  const curatedJson = JSON.parse(
    fs.readFileSync(path.resolve(SRC_DIR, '../../data/curated_flight_schedules.json'), 'utf8')
  );
  for (const s of curatedJson.schedules || []) {
    assert.notEqual(s.verification_status, 'OFFICIALLY_VERIFIED', `${s.route_id} must not claim OFFICIALLY_VERIFIED`);
    if (s.schedule_type === 'INDICATIVE_ESTIMATE') {
      assert.equal(s.verification_status, 'partially_verified');
      assert.equal(s.timetable_verification?.status, 'unverified');
      assert.equal(s.fare_verification?.status, 'unverified');
    }
  }

  const bookingCode = fs.readFileSync(path.join(SRC_DIR, 'screens/BookingScreen.jsx'), 'utf8');
  assert.ok(!bookingCode.includes("availability: 'Available',\n    badge: 'Fastest Transit'"), 'Legacy flight-indigo must not display generic Available');
  assert.ok(bookingCode.includes('Indicative Schedule (Confirm on goindigo.in)'), 'Legacy flight-indigo must show indicative availability disclosure');
  assert.ok(bookingCode.includes("t.dataTier === 'Live Availability' ? '#2E7D32' : '#856404'"), 'Static options must never render green live-availability color');
  assert.ok(bookingCode.includes('ESTIMATED TOTAL'), 'Step 4 pass must label unconfirmed package totals as ESTIMATED TOTAL');
  assert.ok(bookingCode.includes('Indicative / Not a Confirmed Quote'), 'Step 4 pass must disclose non-confirmed quote status');
});

test('Phase 9.2: Sorting by price, earliest departure, and shortest duration orders flights accurately', () => {
  const byPrice = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'Delhi', destination: 'Jammu', stopsFilter: 'nonstop', sortBy: 'price_asc' });
  const timedPriced = byPrice.filter((f) => typeof f.indicativeFareMin === 'number');
  for (let i = 1; i < timedPriced.length; i++) {
    assert.ok(timedPriced[i - 1].indicativeFareMin <= timedPriced[i].indicativeFareMin, 'price_asc must sort ascending');
  }

  const byDep = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'DEL', destination: 'IXJ', sortBy: 'departure_asc' });
  const timedDep = byDep.filter((f) => f.departure_time);
  for (let i = 1; i < timedDep.length; i++) {
    assert.ok(timedDep[i - 1].departure_time <= timedDep[i].departure_time, 'departure_asc must sort earliest first');
  }

  const byDur = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'DEL', destination: 'IXJ', sortBy: 'duration_asc' });
  const timedDur = byDur.filter((f) => typeof f.durationHours === 'number');
  for (let i = 1; i < timedDur.length; i++) {
    assert.ok(timedDur[i - 1].durationHours <= timedDur[i].durationHours, 'duration_asc must sort shortest first');
  }
});

test('Phase 9.3: Stops filter separates Non-Stop from Connecting flights and unsupported routes return empty honestly', () => {
  const blrNonStop = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'Bengaluru', destination: 'IXJ', stopsFilter: 'nonstop' });
  const blrConnecting = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'Bengaluru', destination: 'IXJ', stopsFilter: 'connecting' });
  assert.equal(blrNonStop.length, 0, 'BLR->IXJ has no direct non-stop flight in curated DGCA set');
  assert.ok(blrConnecting.length >= 1, 'BLR->IXJ must surface 1-stop connecting flight via DEL');

  const unsupported = filterAndSortFlights(CURATED_FLIGHTS, { origin: 'Goa', destination: 'IXJ' });
  assert.equal(unsupported.length, 0, 'Unsupported city must return empty rather than inventing fake flights');

  assert.equal(normalizeAirportOrCity('New Delhi'), 'DEL');
  assert.equal(getDayAbbrevFromDate('2026-11-10'), 'Tue');
});

test('Phase 9.4: Deduplication collapses duplicate airline/flight numbers and toBookingTransportOption builds booking payload', () => {
  const dupList = deduplicateFlights([
    { id: 'a', mode: 'Flight', airlineName: 'IndiGo', flightNumber: '6E-2144', originAirportCode: 'DEL', destinationAirportCode: 'IXJ', departure_time: '07:15' },
    { id: 'b', mode: 'Flight', airlineName: 'IndiGo', flightNumber: '6E 2144', originAirportCode: 'DEL', destinationAirportCode: 'IXJ', departure_time: '07:15' },
  ]);
  assert.equal(dupList.length, 1, 'Must deduplicate identical normalized flight number & schedule');

  const option = toBookingTransportOption(CURATED_FLIGHTS[0]);
  assert.ok(option.mode === 'Flight' && option.isIndicativeFare === true, 'Booking handoff option must preserve indicative fare disclosure');
  assert.ok(FLIGHT_ORIGIN_PRESETS.length >= 5 && FLIGHT_DESTINATION_PRESETS.length >= 2, 'Presets must be exported');
});

test('Phase 9.5: TransportScreen, TransportCard, and BookingScreen integrate multi-flight controls, stale invalidation, and handoff', () => {
  const screenCode = fs.readFileSync(path.join(SRC_DIR, 'screens/TransportScreen.jsx'), 'utf8');
  assert.ok(screenCode.includes('CURATED_FLIGHTS'), 'TransportScreen must use CURATED_FLIGHTS instead of single flight-1');
  assert.ok(!screenCode.includes("id: 'flight-1'"), 'Single generic flight-1 placeholder must be replaced');
  assert.ok(screenCode.includes('filterAndSortFlights'), 'TransportScreen must filter and sort flights dynamically');
  assert.ok(screenCode.includes('toBookingTransportOption'), 'TransportScreen must transform selected flight for BookingScreen');
  assert.ok(screenCode.includes('ListEmptyComponent'), 'TransportScreen must render honest empty state for zero matches');
  assert.ok(screenCode.includes('setSelectedFlightId(null)'), 'TransportScreen must invalidate stale selection when route/date changes');

  const cardCode = fs.readFileSync(path.join(SRC_DIR, 'components/TransportCard.jsx'), 'utf8');
  assert.ok(cardCode.includes('airlineBadge'), 'TransportCard must show airline code badge');
  assert.ok(cardCode.includes('baggageAllowance'), 'TransportCard must show baggage info when present');
  assert.ok(cardCode.includes('fareDisclaimer'), 'TransportCard must show honest indicative fare disclaimer');

  const bookingCode = fs.readFileSync(path.join(SRC_DIR, 'screens/BookingScreen.jsx'), 'utf8');
  assert.ok(bookingCode.includes('routeMatchingFlights'), 'BookingScreen Step 2 must derive multiple matching flights for origin/date');
  assert.ok(bookingCode.includes('staleFlightNotice'), 'BookingScreen must invalidate stale flight selections when origin/date changes');
  assert.ok(bookingCode.includes('transportSortBy'), 'BookingScreen must allow sorting flight options');
  assert.ok(bookingCode.includes('isIndicativeFare'), 'BookingScreen must label indicative flight fares honestly');
});

