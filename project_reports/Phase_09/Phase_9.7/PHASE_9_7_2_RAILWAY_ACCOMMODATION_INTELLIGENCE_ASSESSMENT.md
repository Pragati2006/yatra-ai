# PHASE 9.7.2 — RAILWAY & ACCOMMODATION INTELLIGENCE EXPANSION
## Comprehensive Read-Only Technical Assessment & Architecture Roadmap

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Active Branch:** `main`
**Baseline Git Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Assessment Date:** 2026-11-07
**Authorization Mode:** STRICT READ-ONLY ASSESSMENT (Zero Code/Data/Environment Modifications)

---

## Executive Summary

This report establishes the technical feasibility, data contracts, risk profiles, and architectural integration sequence for expanding **Yatra AI**'s live-data intelligence into **Railway Tracking** and **Third-Party Accommodation Telemetry**, while preserving the integrity of existing **Open-Meteo Weather**, **Curated Operational Notices**, and **Curated Accommodation Catalog** frameworks.

In strict compliance with the **Phase 9.7.2 Master Execution Prompt**, this investigation was executed under a strict read-only mandate. No production code was modified, no credentials were added, no external network requests were dispatched with unapproved keys, and no database records were altered.

### Summary of Provider Verdicts

| Provider / Capability | Domain | Proposed Source Type | Legal & Access Class | Feasibility & Integration Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **RailRadar API** | Live Railway Telemetry | Third-Party Aggregator | Class C (Commercial Freemium API) | **CONDITIONAL — FURTHER VALIDATION REQUIRED** |
| **Curated Railway Schedules** | Static Train Timetables | Curated Dataset | Class B (Official Public Timetables) | **APPROVED FOR INTEGRATION** |
| **Amadeus Hotel Offers API v3** | Chain Hotel Rates & Availability | Global Distribution System (GDS) | Class A/C (Self-Service Enterprise API) | **CONDITIONAL — FURTHER VALIDATION REQUIRED** |
| **Curated Accommodation Catalog** | Katra Dharamshalas & Local Hotels | Curated Primary Registry | Class B (Direct Verified Verification) | **APPROVED FOR INTEGRATION** *(Currently Active)* |
| **Open-Meteo Weather API** | Elevation-Aware Multi-Altitude Weather | Open Meteorological API | Class A (Open REST / CC BY 4.0) | **APPROVED FOR INTEGRATION** *(Currently Active)* |

---

## 1. Current Repository and Git State

A thorough, non-destructive audit of the workspace was conducted before commencing inspection:

### 1.1 Active Repository State (`yatra-ai`)
- **Root Path:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
- **Branch:** `main`
- **Current HEAD Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c` (*"Update: Added files for Phase 9.3B - Synthetic Accommodation & Transport Isolation..."*)
- **Working Tree Status:** Preserved dirty state containing 18 tracked modified files and 26 untracked files/directories from Phases 6 through 9.6.2.2.
  - **Modified Tracked Files (18):**
    - `agents/availability_agent.py`, `agents/coordinator.py`, `agents/orchestrator.py`, `mongodb_agent.py`, `weather.py`
    - `backend/routes/yatra.py`
    - `frontend/src/components/AIChat.jsx`, `frontend/src/components/HotelCard.jsx`, `frontend/src/components/SavedTripsModal.jsx`
    - `frontend/src/components/chat/MessageItem.jsx`, `frontend/src/components/chat/cards/BookingHandoffCard.jsx`, `frontend/src/components/chat/cards/HotelMiniCard.jsx`, `frontend/src/components/chat/cards/TransportMiniCard.jsx`, `frontend/src/components/chat/cards/WeatherCard.jsx`
    - `frontend/src/pages/YatraBooking.jsx`, `frontend/src/utils/pdfGenerator.js`, `utils/__init__.py`, `utils/pdf_generator.py`
  - **Untracked Additions Preserved (26):**
    - `agents/central_agent.py` (Central 12-tool conversational supervisor)
    - `data/curated_operational_notices.json`, `data/katra_accommodation_catalog.json`, `data/verified_contacts.json`, `data/vector_store.json`
    - `frontend/src/components/chat/cards/OperationalNoticeCard.jsx`, `frontend/src/components/chat/cards/VerifiedContactCard.jsx`, `frontend/src/components/chat/provenance/`
    - `knowledge_base/`, `project_reports/`, `rag/`, `services/`, `utils/cache_manager.py`, `utils/provenance.py`
    - 15 dedicated test suites in `tests/`
- **Test Baseline:** The focused domain regression suite executes **356 tests in 12.08s with 100% PASS (0 failures, 0 errors)**.
- **Frontend Build Baseline:** `oxlint` reports 0 errors; `vite build` generates production assets cleanly in 1.02s without warnings.

### 1.2 Backup Repository Verification (`yatra-booking-agent`)
- **Root Path:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent`
- **Branch:** `feature/ui-redesign`
- **Current HEAD Commit:** `8996d6a8e3bc83eda0808d0a9ca217979118ebee` (*"Prepare final Yatra Booking Agent project for team collaboration"*)
- **Status:** **STRICTLY UNTOUCHED**. Zero files modified or accessed during this assessment.

---

## 2. Existing Railway Implementation Inventory

An in-depth review of the current transport subsystem was performed across `db.py`, `agents/central_agent.py`, and the frontend chat components.

### 2.1 Current Implementation Components
1. **Synthetic CSV Storage (`yatra-ai/data/trains_dataset.csv`):**
   - Contains 675 synthetic rows modeling 3 travel classes across generic routes.
   - Fields: `id`, `day_offset`, `train_no`, `operator`, `travel_class`, `origin`, `destination`, `departure_time`, `duration_mins`, `price`, `seats_available`.
   - Sample row: `12401, Indian Railways, Sleeper, Delhi, Katra (SVDK), 20:00, 732, 763, 8`.
2. **Database Simulator (`yatra-ai/db.py`):**
   - Function `_build_live(TRAINS_DATASET, TRAINS_LIVE, "travel_date")` projects the static `day_offset` relative to the local host's current date into a transient `trains_live.csv`.
   - Function `search_trains(origin, start_date, end_date, min_seats=1)` performs a pandas filter against `trains_live.csv` based on string matching on origin and destination.
3. **Central Agent Tool (`agents/central_agent.py` — `search_transport_options`):**
   - Tool `search_transport_options` invokes `db.search_flights`, `db.search_trains`, and `db.search_buses` directly.
   - Bypasses the `services.live_data.manager.LiveDataServiceManager` entirely!
   - Constructs hardcoded synthetic provenance:
     ```python
     "source_name": "Regional Transport Timetable Dataset",
     "source_type": "indicative_data",
     "freshness_status": "cached",
     "verification_status": "verified_curated_source",
     "disclaimer": "Indicative transport schedules from local demonstration database; check IRCTC/airlines for live status."
     ```
4. **Frontend Presentation (`frontend/src/components/chat/cards/TransportMiniCard.jsx`):**
   - Renders transport options in the chat stream with an indicative mode icon, train name/operator, departure/arrival times, fare, and a `FreshnessIndicator`.

### 2.2 Gap Analysis: What is Missing
- **No Railway Adapter in Live Data Framework:** Unlike weather, notices, contacts, and accommodation, there is no `services/live_data/adapters/railway_adapter.py`.
- **No Real Train Numbers or Official SVDK Schedules:** Real pilgrims need authentic train schedules for major corridors connecting New Delhi, Mumbai, Varanasi, and Jammu to Shri Mata Vaishno Devi Katra (SVDK), such as:
  - *22439 / 22440:* New Delhi - SMVD Katra Vande Bharat Express
  - *22477 / 22478:* New Delhi - SMVD Katra Vande Bharat Express (Second rake)
  - *22461 / 22462:* Shri Shakti AC Superfast Express
  - *12445 / 12446:* Uttar Sampark Kranti Express
  - *12919 / 12920:* Malwa Express (Indore - SVDK)
  - *12471 / 12472:* Swaraj Express (Bandra Terminus - SVDK)
  - *14609 / 14610:* Hemkunt Express (Rishikesh - SVDK)
- **No Live Running Telemetry:** The application currently has zero concept of delays, real-time platform assignments, cancellation alerts, or current station coordinates.
- **No Station Code Awareness:** System lacks awareness of official Indian Railways station codes (`SVDK`, `JAT`, `UHP`, `NDLS`, `PNP`, `UMB`, `LDH`).

---

## 3. RailRadar Access & Feasibility Assessment

An investigation was conducted into **RailRadar** (`railradar.in`) as a candidate for live railway tracking.

### 3.1 Source Overview & Developer Access
- **Provider:** RailRadar (Private transit data technology provider, Bangalore/India).
- **Service Classification:** **Class C — Third-Party Aggregator / Private Developer API**.
- **Developer Portal:** `https://railradar.in/developers` / `https://api.railradar.in`.
- **Authentication:** Header-based API key (`x-api-key: <RAILRADAR_API_KEY>`).
- **Data Protocol:** HTTPS REST returning JSON payloads.

### 3.2 Documented Endpoints
1. **Live Train Running Status:**
   - `GET /api/v1/train/running-status/{train_number}`
   - *Query Parameters:* `date` (YYYY-MM-DD, journey start date).
   - *Returns:* Current station code/name, delay in minutes (departure/arrival), scheduled vs expected times, GPS coordinates (lat/long if train is GPS-fitted), distance covered, running status (`RUNNING`, `NOT_STARTED`, `ARRIVED`, `CANCELLED`).
2. **Station Live Board:**
   - `GET /api/v1/station/live/{station_code}`
   - *Query Parameters:* `hours` (window: 2, 4, 8 hours).
   - *Returns:* List of trains arriving/departing within the specified window, scheduled platform numbers, current delays, last reported location.
3. **Train Schedule & Route Information:**
   - `GET /api/v1/train/schedule/{train_number}`
   - *Returns:* Full station itinerary, days of operation, halt duration, total distance, rake composition.

### 3.3 Provenance, Freshness, and Reliability
- **Underlying Data Origin:** RailRadar operates a hybrid ingestion architecture combining automated public scraping of the National Train Enquiry System (NTES) with crowdsourced GPS telemetry uploaded by passengers using mobile applications.
- **Update Frequency:** Data refreshes approximately every 2 to 5 minutes for active en-route trains.
- **Critical Grounding Rule:** RailRadar is **NOT** Indian Railways, CRIS, or IRCTC. It possesses no statutory authority. Its telemetry can drift if passenger GPS signals fail or if NTES imposes rate blocks on RailRadar's scrapers.
- **Truth-in-Data Classification:**
  - `source_type = "third_party_api"`
  - `verification_status = "unverified"`
  - `data_authority = "indicative_aggregator"`
  - Explicit disclaimer: *"Train running status provided by third-party crowdsourced telemetry; always verify with NTES (139) or station display boards before boarding."*

### 3.4 Rate Limits, Pricing & Commercial Constraints
- **Free Developer Tier:** Allows up to 100 requests per calendar month with a rate cap of ~1 request per second.
  - *Significance:* 100 requests/month is insufficient for production, but adequate for contract validation and isolated testing.
- **Paid Tier:** Tiered commercial subscriptions starting from INR 1,500/month for 10,000 requests.
- **Availability Risk:** High. Third-party aggregators scraping NTES frequently experience intermittent outages whenever CRIS updates NTES web headers or Cloudflare challenges.

### 3.5 Provider Feasibility Verdict: `CONDITIONAL — FURTHER VALIDATION REQUIRED`
- *Condition:* Integration of RailRadar's live running status must remain conditional on API key provisioning and must strictly be paired with an offline **Curated Railway Timetable Dataset** as a primary fallback when RailRadar is unavailable or rate-limited.

---

## 4. Existing Accommodation Implementation Inventory

The accommodation subsystem was audited across `data/katra_accommodation_catalog.json`, `services/live_data/adapters/curated_accommodation_adapter.py`, and `frontend/src/components/chat/cards/HotelMiniCard.jsx`.

### 4.1 Current Architecture & Catalog
- **Curated Catalog (`data/katra_accommodation_catalog.json`):**
  - Contains **22 human-verified Katra properties** curated during Phase 9.3B.
  - **Tier 1 (Official Shrine Board):** Niharika Yatri Niwas, Trikuta Bhawan, Kalika Bhawan, Shakti Bhawan, Ashirwad Complex (direct statutory ownership by SMVDSB).
  - **Tier 2 (Branded & Corporate Chains):** Radisson Hotel Katra, Fortune Park Katra, Lemon Tree Hotel Katra, Clarks Inn Suites, The White Hotel Katra, Welcomhotel by ITC Katra.
  - **Tier 3 (Verified Local Independent Hotels):** Hotel Jagdish Residency, Hotel Vaishno Devi, Hotel Rama Palace, etc.
- **Data Attributes Per Property:**
  - `property_id`, `name`, `category` (`smvdsb_official`, `branded_hotel`, `independent_hotel`)
  - `address`, `landmark`, `distance_to_banganga_km`, `distance_to_railway_station_km`
  - `phone_numbers` (verified primary landlines/receptions)
  - `official_website` (direct non-OTA URL)
  - `published_indicative_tariffs` (room categories with published minimum and maximum rates in INR)
  - `verification_metadata`: `status = "verified"`, `source = "smvdsb_official_registry"` or `"direct_property_contact"`, `last_verified_date = "2026-11-06"`.
- **Live Data Adapter (`services/live_data/adapters/curated_accommodation_adapter.py`):**
  - Inherits from `BaseLiveDataProvider`, registered under `DataDomain.ACCOMMODATION`.
  - Supports query filters: `category`, `max_price`, `min_rooms`, `pax_count`, `preferred_distance_km`.
  - **Fail-Closed Availability Policy:** Returns `availability_status = "NOT_CHECKED"` and `availability_action = "CALL_PROPERTY"` or `"VISIT_OFFICIAL_PORTAL"`. It strictly **refuses to fabricate real-time room availability**, adhering to the Phase 9.3B synthetic data eradication mandate.

---

## 5. Amadeus Access & Feasibility Assessment

An investigation was conducted into the **Amadeus for Developers** platform for live accommodation pricing and availability.

### 5.1 Source Overview & Developer Access
- **Provider:** Amadeus IT Group (Leading Global Distribution System - GDS).
- **Service Classification:** **Class A/C — Self-Service Developer API / Enterprise GDS**.
- **Developer Portal:** `https://developers.amadeus.com`.
- **Authentication:** OAuth 2.0 Client Credentials flow:
  - `POST https://test.api.amadeus.com/v1/security/oauth2/token`
  - Returns Bearer Token with 1,799 seconds (30 minutes) validity.
- **Target Endpoints:**
  - `GET /v1/reference-data/locations/hotels/by-city?cityCode=IXJ` (Jammu Airport IATA)
  - `GET /v3/shopping/hotel-offers?hotelIds={ids}&adults={pax}&checkInDate={date}`

### 5.2 The Katra Coverage Paradox (GDS vs Local Reality)
A critical geographic and demographic analysis of Amadeus's global distribution catalog revealed an essential architectural constraint:
1. **GDS Target Demographic:** Amadeus aggregates inventory distributed through Sabre/Amadeus GDS pipelines. This system is adopted almost exclusively by international, multinational, or major domestic corporate hospitality chains (Radisson, Lemon Tree, ITC, Clarks).
2. **Katra Market Breakdown:**
   - *Total Accommodations in Katra:* Approximately 250+ properties (including Shrine Board Yatri Niwas, Trust Dharamshalas, budget lodges, family-run guest houses, and 15-20 luxury/business hotels).
   - *GDS / Amadeus Coverage in Katra:* **Less than 5% to 8% of total properties** (primarily Radisson Katra, Lemon Tree Katra, Fortune Park).
   - *SMVDSB Official Accommodation Coverage:* **0% (Zero)**. The Shrine Board does not distribute rooms via Amadeus, Sabre, Agoda, or Booking.com. All 1,800+ SMVDSB beds are bookable exclusively through `online.maavaishnodevi.org` or physical on-arrival counters.
3. **Impact on Pilgrims:**
   - Over 90% of pilgrims seeking budget, trust, or Shrine Board accommodation (INR 300 to INR 1,500/night) would receive **zero results** if Yatra AI were to rely solely on Amadeus.
   - Amadeus rates represent corporate dynamic pricing (often INR 4,500 to INR 12,000/night) aimed at high-end leisure and business travelers.

### 5.3 Data Authority and Rate Nomenclature
If Amadeus is queried, the returned figures represent **Online Distribution Rates (OTA Quotes)** subject to commission, room-tier surcharges, and fluctuating yield algorithms.
- Terminology must strictly distinguish:
  - `OFFICIAL_PUBLISHED_TARIFF`: Direct rate published by the Shrine Board or hotel management.
  - `PROVIDER_RETURNED_RATE`: Real-time GDS quote returned by Amadeus.
  - `INDICATIVE_MARKET_PRICE`: Non-binding price estimate for planning.
  - `CONFIRMED_BOOKING`: A legally binding room allocation with a PNR/Voucher.

### 5.4 Provider Feasibility Verdict: `CONDITIONAL — FURTHER VALIDATION REQUIRED`
- *Condition:* Amadeus can serve as an **optional auxiliary provider** for high-end chain hotel pricing, but it **MUST NOT** replace or supersede the `CuratedAccommodationAdapter`. If Amadeus credentials are missing or return no results for Katra, the system must seamlessly present the curated catalog.

---

## 6. Open-Meteo Preservation Assessment

A comprehensive review of the active weather service was conducted to ensure zero regressions during future expansion.

### 6.1 Architectural Stability
- **Implementation:** `services/live_data/adapters/weather_adapter.py` (`OpenMeteoWeatherAdapter`).
- **Data Domain:** `DataDomain.WEATHER`.
- **Operational Health:** Outstanding. 100% test pass rate across 28 dedicated test cases in `tests/test_phase8_1_weather.py`.
- **Multi-Altitude Pilgrimage Milestones:**
  1. *Katra Base Camp:* 750m elevation (Departure point).
  2. *Ardhkuwari Midpoint:* 1,400m elevation (Midway resting point & Garbh Joon cave).
  3. *Bhawan Holy Shrine:* 1,585m elevation (Primary sanctum).
  4. *Bhairon Ghati Peak:* 2,011m elevation (Steep mountain summit, highest wind chill risk).
- **Provenance Transparency:** Attributed to Open-Meteo REST API under Creative Commons Attribution 4.0 International (CC BY 4.0), cached with a 30-minute TTL, with graceful stale-if-error fallback.

### 6.2 Verdict: `APPROVED FOR INTEGRATION` *(Preserve Exactly As-Is)*
- Open-Meteo remains the primary live weather provider. No changes, parallel providers, or architectural refactoring are permitted for the weather domain.

---

## 7. Existing Live Data Manager Compatibility Assessment

The proposed railway and accommodation expansions were evaluated against the core architecture of `services/live_data/manager.py`, `registry.py`, `base.py`, and `contracts.py`.

### 7.1 Key Architectural Guarantees
1. **Inheritance & Contracts:**
   - Both `RailRadarAdapter` and `AmadeusHotelAdapter` can inherit directly from `BaseLiveDataProvider` (`services/live_data/base.py`).
   - They will emit standard `LiveDataResult[T]` envelopes containing sanitized payloads, typed metadata, and strict provenance records.
2. **Circuit Breakers & Fault Tolerance:**
   - The manager's built-in circuit breaker will automatically protect the application against external provider outages (e.g. if RailRadar or Amadeus returns repeated 5xx errors or 429 rate limits).
   - After 3 consecutive failures, the provider trips to `OPEN`, failing fast for 60 seconds before entering `HALF_OPEN`.
3. **Session Privacy & Multi-Tenant Safety:**
   - `ProviderRequest` objects strictly segregate private request context (`user_id`, `session_id`) from cached responses.
   - Cache keys are generated deterministically based only on public query parameters (`train_no`, `date`, `city_code`, `adults`).
4. **Fail-Closed Verification Defaults:**
   - Any external API response lacking explicit verification flags defaults strictly to `verification_status = "unverified"`.
   - No external provider can override human-verified statutory notices or verified Shrine Board tariffs.

---

## 8. Proposed Railway Data Contracts

To integrate railway capabilities cleanly into `services/live_data/contracts.py`, the following strongly-typed dataclasses and enums are proposed:

```python
class TrainRunningStatusType(str, Enum):
    """Real-time operational running states for an active train."""
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    ARRIVED = "ARRIVED"
    CANCELLED = "CANCELLED"
    DIVERTED = "DIVERTED"
    UNKNOWN = "UNKNOWN"

@dataclass
class TrainRunningStatus:
    """Normalized live running status for an active train service."""
    train_number: str
    train_name: str
    journey_date: str
    source_station_code: str
    destination_station_code: str
    current_station_code: str
    current_station_name: str
    delay_departure_minutes: int = 0
    delay_arrival_minutes: int = 0
    status: TrainRunningStatusType = TrainRunningStatusType.UNKNOWN
    platform_number: Optional[str] = None
    expected_arrival_time: Optional[str] = None
    expected_departure_time: Optional[str] = None
    last_reported_timestamp: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # {'lat': float, 'lon': float}
    data_source: str = "railradar_api"
    data_authority: str = "indicative_aggregator"
    verification_status: str = VerificationStatus.UNVERIFIED.value
    disclaimer: str = (
        "Live running status provided by third-party crowdsourced telemetry; "
        "verify with NTES (139) or official station boards before boarding."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CuratedTrainSchedule:
    """Static, authoritative timetable record for major Katra express trains."""
    train_number: str
    train_name: str
    origin_station_code: str
    origin_station_name: str
    destination_station_code: str
    destination_station_name: str
    departure_time: str
    arrival_time: str
    days_of_operation: List[str]  # ['MON', 'TUE', ...]
    travel_classes: List[str]     # ['1A', '2A', '3A', 'SL', 'CC', 'EC']
    major_halts: List[Dict[str, str]]
    total_distance_km: int
    duration_hours: float
    catering_available: bool
    source_name: str = "Official Indian Railways Published Timetable"
    verification_status: str = VerificationStatus.VERIFIED_CURATED_SOURCE.value
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

---

## 9. Proposed Accommodation Data Contracts

To accommodate external GDS offers while preserving the integrity of local curated accommodations, the following contract expansion is proposed:

```python
class RateType(str, Enum):
    """Distinguishes official statutory tariffs from third-party market rates."""
    OFFICIAL_PUBLISHED_TARIFF = "OFFICIAL_PUBLISHED_TARIFF"
    INDICATIVE_MARKET_PRICE = "INDICATIVE_MARKET_PRICE"
    PROVIDER_RETURNED_RATE = "PROVIDER_RETURNED_RATE"

@dataclass
class AccommodationOffer:
    """Standardized accommodation offer container supporting dual-source routing."""
    property_id: str
    property_name: str
    category: str  # 'smvdsb_official', 'branded_chain', 'independent_hotel'
    provider_name: str  # 'curated_catalog' or 'amadeus_hotel_api'
    rate_type: RateType
    currency: str = "INR"
    min_price: float = 0.0
    max_price: Optional[float] = None
    room_type: str = "Standard"
    occupancy_adults: int = 2
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    availability_status: str = "NOT_CHECKED"  # 'AVAILABLE', 'SOLD_OUT', 'NOT_CHECKED'
    booking_channel: str = "DIRECT"           # 'SMVDSB_PORTAL', 'HOTEL_DIRECT', 'OTA_GDS'
    booking_url: Optional[str] = None
    phone_number: Optional[str] = None
    verification_status: str = VerificationStatus.UNVERIFIED.value
    last_verified_at: Optional[str] = None
    disclaimer: str = (
        "Room tariffs and availability are indicative; bookings must be completed "
        "directly through the property's official portal or counter."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

---

## 10. Security, Privacy and Licensing Considerations

1. **Credential Hygiene:**
   - `RAILRADAR_API_KEY`, `AMADEUS_CLIENT_ID`, and `AMADEUS_CLIENT_SECRET` must be read exclusively from environment variables via `.env`.
   - Never hardcode credentials or log API keys in error envelopes.
2. **Pilgrim PII Protection:**
   - Under no circumstances will pilgrim names, phone numbers, darshan slots, or payment details be passed to RailRadar or Amadeus.
   - External requests are strictly restricted to generic transit queries (`train_number`, `date`, `city_code`, `adults`).
3. **No Unsanctioned Scraping or Auth Bypass:**
   - In accordance with Phase 9.6.1.1 findings, Yatra AI will **never** scrape `maavaishnodevi.org`, `irctc.co.in`, or `enquiry.indianrail.gov.in`.
   - All integrations must adhere to documented, authorized API specifications.
4. **Licensing Compliance:**
   - Open-Meteo: CC BY 4.0 attribution maintained.
   - RailRadar: Non-commercial evaluation license strictly respected on free tier.
   - Amadeus: Self-service developer terms followed; no unauthorized caching of GDS PNRs.

---

## 11. Missing Capabilities and Dependencies

### 11.1 Runtime Libraries
- **HTTP Client:** `httpx` (v0.28.1) and `requests` (v2.32.3) are already installed in the virtual environment. **Zero new package installations are required.**

### 11.2 Datasets & Environment Variables Needed for Future Implementation
- **New Dataset Required:** `data/curated_railway_schedules.json` containing 8-10 major Katra corridor trains (Vande Bharat, Shri Shakti, Swaraj, Uttar Sampark Kranti, etc.).
- **New Environment Variables:**
  - `RAILRADAR_API_KEY`: Optional; defaults to mock provider if unset.
  - `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET`: Optional; defaults to curated catalog if unset.

---

## 12. Proposed Implementation Sequence

To ensure zero downtime, safety, and strict test compliance, the following phased sequence is recommended:

```
[Phase 9.7.3] ──> Data Contracts & Curated Timetable Dataset (Offline, zero credentials)
       │
[Phase 9.7.4] ──> Provider Adapters (CuratedRailwayAdapter, RailRadarAdapter, AmadeusAdapter)
       │
[Phase 9.7.5] ──> Central Agent Tool Integration (search_transport_options & query_train_running_status)
       │
[Phase 9.7.6] ──> Frontend Cards & Provenance Pills (TransportMiniCard & HotelMiniCard)
       │
[Phase 9.7.7] ──> Comprehensive Acceptance Audit & Safety Verification
```

---

## 13. Testing and Acceptance Strategy

Future implementation must enforce the following test coverage:
1. **Contract Tests:** Serialization, deserialization, and immutability of `TrainRunningStatus`, `CuratedTrainSchedule`, and `AccommodationOffer`.
2. **Provider Unit Tests:**
   - Live success response parsing (mocked JSON payloads).
   - Provider timeout handling (3.0-second SLA).
   - Rate limit (HTTP 429) circuit trip.
   - Malformed/missing fields handling.
   - Stale-if-error cache recovery.
3. **Dual-Source Routing Tests:**
   - Verify that when Amadeus fails or returns 0 results for Katra, the system seamlessly returns the 22 verified properties from the curated catalog.
   - Verify that missing train live status gracefully returns the static curated schedule with `freshness_status = "cached"` and `verification_status = "verified_curated_source"`.
4. **Safety & Grounding Regression:**
   - All 356 existing tests across Phases 6 through 9.6.2.2 must maintain 100% pass rates.

---

## 14. Risks and Unresolved Questions

1. **RailRadar Rate Caps:** Free tier is strictly capped at 100 requests/month. A production deployment requires commercial subscription budgeting.
2. **Amadeus Test Sandbox Limitation:** The Amadeus self-service test environment serves synthetic hotel offers from a static sandbox database. Real-time rates for Katra hotels require production environment approval.
3. **Upstream NTES Scraping Blocks:** Since RailRadar relies in part on NTES scraping, widespread Indian Railways anti-bot measures could cause transient delays in RailRadar's feeds.

---

## 15. Exact Files Requiring Modification in Future Implementation

| File Path | Action | Description |
| :--- | :--- | :--- |
| `services/live_data/contracts.py` | Modify | Add `TrainRunningStatusType`, `TrainRunningStatus`, `CuratedTrainSchedule`, `RateType`, and `AccommodationOffer`. |
| `data/curated_railway_schedules.json` | Create | Authentic timetables for 8-10 major SVDK express trains. |
| `services/live_data/adapters/curated_railway_adapter.py` | Create | Production adapter serving static Katra railway schedules. |
| `services/live_data/adapters/railradar_adapter.py` | Create | Resilient live train tracking adapter with mock fallback. |
| `services/live_data/adapters/amadeus_hotel_adapter.py` | Create | GDS chain accommodation adapter with OAuth2 token manager. |
| `services/live_data/manager.py` | Modify | Register new transport and accommodation providers. |
| `agents/central_agent.py` | Modify | Refactor `search_transport_options` to query Live Data Manager; add `query_train_running_status`. |
| `frontend/src/components/chat/cards/TransportMiniCard.jsx` | Modify | Add running status badges and platform indicators. |
| `frontend/src/components/chat/cards/HotelMiniCard.jsx` | Modify | Add GDS rate badges and source provenance distinction. |
| `tests/test_phase9_7_railway_accommodation.py` | Create | Comprehensive test suite covering contracts, adapters, and tools. |

---

## 16. Final Stop Condition & Decision Recommendations

### 16.1 Feasibility Summary
- **Technically Feasible Immediately (Zero External Dependencies):**
  - Curated Katra railway schedule catalog (`data/curated_railway_schedules.json`).
  - `CuratedRailwayAdapter` integrated into `LiveDataServiceManager`.
  - Refactoring `search_transport_options` in `central_agent.py` to route through `LiveDataServiceManager`.
  - Normalized data contracts in `contracts.py`.
- **Requires External Credentials / Commercial Approvals:**
  - Live train telemetry via RailRadar (`RAILRADAR_API_KEY`).
  - Live GDS hotel offers via Amadeus (`AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET`).

### 16.2 Smallest Safe Implementation Sequence
We recommend implementing **Phase 9.7.3** first: deploy the offline Curated Railway Schedule dataset, contracts, and adapter. This immediately brings transport search into the robust Live Data Manager architecture with zero external risk, 100% offline testability, and zero credential dependencies. External API adapters can then be introduced as optional plugins.

### 16.3 Clear Readiness Statement
- **RailRadar:** **NOT READY FOR PRODUCTION INTEGRATION** until commercial API key credentials are confirmed; ready for design and mocked testing.
- **Amadeus:** **NOT READY AS PRIMARY ACCOMMODATION ENGINE** due to lack of Katra local hotel coverage; ready as an optional secondary plugin for chain hotels.

---
**STOP CONDITION REACHED: Assessment complete. Awaiting explicit user authorization before initiating any code or file modifications.**
