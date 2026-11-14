# PHASE 9.7.1 — LIVE DATA SOURCE DISCOVERY & FEASIBILITY AUDIT REPORT

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `yatra-ai`
**Active Branch:** `main`
**Current Baseline Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Audit Date:** November 7, 2026
**Auditor:** Independent Antigravity Architecture & Feasibility Agent
**Audit Scope:** Strictly READ-ONLY Research, Source-Discovery, and Architecture Feasibility Audit
**Report Destination:** `project_reports/Phase_09/Phase_9.7/PHASE_9_7_1_LIVE_DATA_SOURCE_FEASIBILITY_AUDIT.md`

---

## 1. Executive Summary

This report documents the strictly **read-only** research, source-discovery, and architecture-feasibility audit for **Phase 9.7** of the Yatra AI platform.

The objective of this checkpoint is to rigorously evaluate which additional live-data capabilities can realistically, legally, and safely be integrated into the Phase 9.5 provider framework. This audit investigates five core operational workstreams:
1. **Railway Intelligence:** Train schedules, live running status, delays, and arrivals/departures for Shri Mata Vaishno Devi Katra (`SVDK`), Jammu Tawi (`JAT`), and Martyr Captain Tushar Mahajan (`MCTM`/Udhampur).
2. **Road & Traffic Intelligence:** J&K Traffic Police, Traffic Control Units (TCUs Jammu, Udhampur, Ramban), and NH-44 highway advisories.
3. **Accommodation Intelligence:** Shri Mata Vaishno Devi Shrine Board (SMVDSB) rooms, Katra budget dharamsalas, and commercial hotel APIs (Amadeus, MakeMyTrip, Agoda).
4. **Tourism & Pilgrimage Intelligence:** SMVDSB pilgrimage facilities (battery car, ropeway, helicopter, RFID registration) and J&K Tourism Development Corporation (JKTDC) regional circuits.
5. **Weather & Environmental Intelligence:** Open-Meteo elevation-aware forecasts across four sacred milestones (Katra, Ardhkuwari, Bhawan, Bhairon) and potential India Meteorological Department (IMD) integration.

### High-Level Findings & Core Realities
- **The "No Public API" Reality for Indian Public Transit & Government Portals:** Neither Indian Railways (CRIS/NTES), J&K Traffic Police, NHAI, nor SMVDSB provides an open, self-service developer REST API. Official access to CRIS/NTES is restricted to enterprise B2B partners under the Train Information Enquiry Scheme (TIES), while government traffic portals publish static HTML/PDF updates or social media announcements.
- **The Third-Party API Landscape:** Independent third-party providers (such as RailRadar) offer structured REST APIs for live train coordinates, delays, and station boards via hybrid telemetry (NTES web data + crowdsourced GPS). These providers operate with disclosed terms and commercial tiers, but are explicitly **not** official Indian Railways partners.
- **Accommodation Separation:** Commercial OTAs (MakeMyTrip, Goibibo) do not provide open developer APIs for hotel search. Global GDS providers (Amadeus) have self-service APIs but lack inventory for 90%+ of Katra's non-chain budget hotels and dharamsalas. SMVDSB official accommodations are locked behind user authentication with CAPTCHA/OTP. The curated catalog architecture established in Phase 9.3b remains the most truthful and legally compliant accommodation model.
- **Static RAG vs. Dynamic Provider Separation:** Stable pilgrimage facts (rituals, legend, temple history, routes, statutory pony rates) belong exclusively in the static RAG vector store. Only volatile operational information (track closures, severe weather, train delays, emergency helplines) belongs in the live data provider framework.

---

## 2. Existing Architecture Inventory

An exhaustive inspection of the active `yatra-ai` repository reveals the following baseline components:

### 2.1. Active Live Data Providers & Adapters (`services/live_data/adapters/`)
1. **`CuratedAccommodationAdapter`:**
   - **Domain:** `DataDomain.ACCOMMODATION` (`"accommodation"`)
   - **Backing Store:** `data/katra_accommodation_catalog.json` (22 verified Katra properties across 4 tariff tiers)
   - **Truth-in-Data:** Curated property details, tariff bands, and amenities are verified (`verified_curated_source`); live room availability is explicitly disclaimed as unverified (`availability_verified = False`).
2. **`CuratedOperationalNoticesAdapter`:**
   - **Domain:** `DataDomain.OPERATIONAL_NOTICE` (`"operational_notice"`)
   - **Backing Store:** `data/curated_operational_notices.json`
   - **Truth-in-Data:** Human-verified statutory notices (Mandatory RFID, private agent warning). Supports lifecycle states (`ACTIVE`, `PUBLISHED`, `REQUIRES_REVERIFICATION`, `SUPERSEDED`, `WITHDRAWN`). Enforces non-override rule and explicit supersession.
3. **`VerifiedContactAdapter`:**
   - **Domain:** `DataDomain.EMERGENCY` (`"emergency"`)
   - **Backing Store:** `data/verified_contacts.json`
   - **Truth-in-Data:** Emergency hierarchy sorting: 112 (National Emergency), 108 (Ambulance), Katra Police, Traffic Control Units, Shrine Board administrative desks. Suppresses unverified contacts by default.
4. **`OpenMeteoWeatherAdapter`:**
   - **Domain:** `DataDomain.WEATHER` (`"weather"`)
   - **Backing Service:** Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`)
   - **Truth-in-Data:** Live numerical forecasts across 4 elevation-aware milestones: Katra (750m), Ardhkuwari (1400m), Bhawan (1585m), Bhairon (2011m). Fallback to elevation-adjusted IMD seasonal climate averages.

### 2.2. Core Provider Framework (`services/live_data/`)
- **`BaseLiveDataProvider` (`base.py`):** Abstract provider contract with thread-safe eager RLock synchronization in `__new__`, state transition tracking, circuit breaker (CLOSED, OPEN, HALF-OPEN recovery), and standardized provenance generation.
- **`UnifiedLiveDataManager` (`manager.py`):** Central orchestrator managing single-flight request deduping, domain-specific LRU caching with stale-if-error fallback, circuit breaker evaluation, provider failover, and statutory emergency fallbacks.
- **Cache Policies (`DEFAULT_DOMAIN_CACHE_POLICIES`):**
  - `WEATHER`: TTL 30m, Max Stale 6h
  - `ACCOMMODATION`: TTL 15m, Max Stale 1h
  - `OPERATIONAL_NOTICE`: TTL 15m, Max Stale 2h
  - `CAPACITY`: TTL 15m, Max Stale 4h
  - `EMERGENCY`: TTL 7d, Max Stale 30d
  - `TRANSPORT`: TTL 24h, Max Stale 7d

### 2.3. Central Agent Tool Integration (`agents/central_agent.py`)
Exposes 12 specialized tools in `CENTRAL_TOOLS`:
- `search_yatra_knowledge` (RAG domain search)
- `get_tourism_knowledge` (RAG regional tourism)
- `check_weather_guidance` (Live Open-Meteo adapter)
- `search_transport_options` (Mock CSV dataset queries in `db.py`)
- `search_accommodation_options` (Curated Katra catalog)
- `query_operational_notices` (Curated operational notices)
- `lookup_verified_contacts` (Verified contact registry)
- `evaluate_yatra_plan` (Rule-based pilgrimage itinerary evaluator)
- `modify_itinerary` (Interactive plan updater)
- `check_slot_availability` (Simulated helicopter/battery car slots)
- `request_booking_intent` (Booking handoff trigger)
- `execute_authorized_booking` (Human-gated mock booking execution)

### 2.4. Identified Architecture & Data Gaps
1. **Transport Domain Gap:** `search_transport_options` is backed entirely by synthetic CSV files (`trains_dataset.csv`, `flights_dataset.csv`, `buses_dataset.csv`) queried via `db.py`. **There is currently zero live or verified transit provider integration.**
2. **Capacity Domain Gap:** `DataDomain.CAPACITY` is configured in `UnifiedLiveDataManager`, but has no provider adapter because SMVDSB does not publish real-time RFID track counts.
3. **Accommodation Availability Gap:** While curated hotel records exist, live room inventory is not integrated due to the absence of open APIs for Katra budget properties.

---

## 3. Workstream A — Railway Intelligence Feasibility

### 3.1. Official Railway Infrastructure (CRIS & NTES)
- **Authority:** Centre for Railway Information Systems (CRIS), IT wing of Ministry of Railways, Government of India.
- **Portals:** `https://enquiry.indianrail.gov.in/` (NTES web), `https://www.irctc.co.in/` (Ticketing).
- **API Availability:** **No open public REST API.**
- **Enterprise Access:** Project *Pravah* serves as CRIS's internal enterprise API gateway, but is restricted to authorized government bodies and logistics partners.
- **IRCTC TIES (Train Information Enquiry Scheme):** Programmatic access to PNR status, seat availability, and train inquiry requires a commercial license agreement with IRCTC, security compliance audits, substantial financial deposits, and per-query transaction fees.
- **Access Permission:** Automated polling or scraping of `enquiry.indianrail.gov.in` is strictly prohibited under Indian IT Act regulations and railway terms of use.
- **Classification:** **Class D** (Public web portal without automated access permission); **Class A** (Enterprise B2B API available only via commercial agreement).

### 3.2. Third-Party Provider: RailRadar
- **Provider:** RailRadar (`https://railradar.in/`), operated as an independent private transit technology service in India.
- **API Model:** REST over HTTPS, returning structured JSON.
- **Authentication:** API Key passed via header (`x-api-key`).
- **Endpoints Available:**
  - `GET /train/running-status/{train_number}`: Real-time GPS coordinates, delay in minutes, current speed, bearing, current station, upcoming halting stations, estimated arrival time (ETA), and diversion/cancellation flags.
  - `GET /station/live/{station_code}`: Live station arrival/departure board (trains arriving/departing within next 2–4 hours with platform assignments).
  - `GET /train/schedule/{train_number}`: Static timetable and route segments.
- **Upstream Data Provenance:** Disclosed hybrid model combining public railway data (NTES) and crowdsourced passenger GPS tracking from the RailRadar consumer app.
- **Terms & Legal Disclaimers:** Explicitly disclaims affiliation with Indian Railways, IRCTC, CRIS, or NTES. Provided strictly "as-is" for guidance; disclaims liability for missed connections.
- **Pricing & Limits:** Free developer tier (100 requests/month); scalable paid developer tiers for commercial integration.
- **Classification:** **Class C** (Third-party API with disclosed upstream provenance and documented terms).

### 3.3. Key Katra Pilgrim Railway Corridors
The following key trains connect pilgrims to the Katra base camp (`SVDK`) and Jammu Tawi (`JAT`):
- **22439 / 22440:** New Delhi – SVDK Vande Bharat Express (Fastest connectivity: ~8 hours)
- **22477 / 22478:** New Delhi – SVDK Vande Bharat Express (Second Vande Bharat rake)
- **12445 / 12446:** Uttar Sampark Kranti Express (New Delhi – SVDK)
- **12425 / 12426:** New Delhi – Jammu Tawi Rajdhani Express
- **12471 / 12472:** Swaraj Express (Bandra Terminus Mumbai – SVDK)
- **12919 / 12920:** Malwa Express (Dr. Ambedkar Nagar Indore – SVDK)
- **14609 / 14610:** Hemkunt Express (Rishikesh/Haridwar – SVDK)
- **14033 / 14034:** Jammu Mail (Old Delhi – SVDK)

### 3.4. Feasibility Verdict for Railway Intelligence
- **Verdict:** **APPROVED FOR FUTURE IMPLEMENTATION (CONDITIONAL)**
- **Architecture Strategy:**
  1. Implement a **`RailRadarTrainAdapter`** under `DataDomain.TRANSPORT`.
  2. Implement a secondary **`CuratedRailwayScheduleAdapter`** containing verified static timetables, station codes, and running days for the primary Katra express trains.
  3. Enforce strict truth-in-data: RailRadar data must be tagged `source_type = "third_party_api"`, `verification_status = "unverified"`, with a visible disclaimer (*"Crowdsourced and third-party transit estimates. Confirm platform and delay at station or 139 helpline"*).
  4. Single-flight caching with 15-minute TTL to prevent API quota depletion.

---

## 4. Workstream B — Road & Traffic Intelligence Feasibility

### 4.1. J&K Traffic Police
- **Authority:** Jammu & Kashmir Police, Traffic Wing.
- **Portals:** `https://trafficpolice.jk.gov.in/`
- **API / Feed Status:** **Zero public REST APIs, zero RSS feeds, zero GeoJSON feeds.**
- **Publication Mechanism:** Daily Traffic Movement Plan is published as unstructured HTML text, scanned PDF circulars, and announcements on social media handles (X / Facebook).
- **Access Permission:** Automated scraping or polling of `trafficpolice.jk.gov.in` is unstated/prohibited.
- **Operational Reality:** The Jammu–Srinagar National Highway (NH-44), specifically the Nashri–Ramban–Banihal stretch, is prone to landslides, shooting stones, and heavy vehicle breakdowns. Cut-off timings are enforced daily at Nagrota (Jammu) and Qazigund (Kashmir).
- **Official Point of Contact:** 24x7 Traffic Control Units (TCUs):
  - TCU Jammu: `0191-2459048`, `0191-2740550`, `103`
  - TCU Ramban: `9419993745`
  - TCU Udhampur: `8491928625`
- **Classification:** **Class D** (Public website without automated access permission).

### 4.2. National Highways Authority of India (NHAI)
- **Authority:** NHAI / Indian Highway Management Company Limited (IHMCL), Ministry of Road Transport and Highways (MoRTH).
- **Portals:** `https://rajmargyatra.ihmcl.co.in/`, Rajmargyatra mobile app.
- **API Availability:** **No open developer API.**
- **Data Model:** Advanced Traffic Management Systems (ATMS) camera and IoT sensor feeds route directly into internal Command and Control Centers and the NHAI Data Lake. Public interaction is consumer-only via the Rajmargyatra app or the **1033 National Highway Helpline**.
- **Classification:** **Class D/E** (Proprietary internal systems; no developer API).

### 4.3. Feasibility Verdict for Road & Traffic Intelligence
- **Verdict:** **BLOCKED FOR AUTOMATED POLLING; MAINTAIN CURATED REGISTRY & TELEPHONE BRIDGE**
- **Architecture Strategy:**
  1. Continue maintaining the human-verified **`CuratedOperationalNoticesAdapter`** established in Phase 9.6.2.
  2. Maintain the verified contact registry (`VerifiedContactAdapter`) providing instant one-click calling to TCU Jammu, TCU Ramban, TCU Udhampur, and NH Helpline 1033.
  3. Strictly prohibit web scraping or automated polling of police websites.

---

## 5. Workstream C — Accommodation Intelligence Feasibility

### 5.1. Shri Mata Vaishno Devi Shrine Board (SMVDSB) Accommodation
- **Authority:** Shri Mata Vaishno Devi Shrine Board.
- **Facilities:** Niharika Yatri Niwas, Shakti Bhawan, Ashirwad Complex (Katra); Ardhkuwari Bhawan; Sanjichhat Bhawan; Main Bhawan Complex (Kalika, Saraswati, Durga, Vaishnavi Bhawans).
- **Portal:** `https://online.maavaishnodevi.org/`
- **Access Model:** Gated behind mandatory user authentication with username, password, graphical CAPTCHA, and SMS OTP.
- **API Availability:** **No public API.**
- **Security Constraint:** Defeating or scripting CAPTCHA/OTP bypasses violates shrine governance and legal access controls.
- **Classification:** **Class D/E** (Protected transaction portal; automated integration strictly prohibited).

### 5.2. Commercial Hotel APIs (Amadeus vs. Indian OTAs)
- **Amadeus Self-Service Hotel API (`v3/shopping/hotel-offers`):**
  - **Status:** Documented, open self-service REST API with free test tier.
  - **Limitation:** Global GDS inventory. In Katra, coverage is restricted to chain properties (Fortune, Radisson, Lemon Tree). It has zero inventory for Katra's 200+ budget hotels, dharamsalas, or Yatri Niwas.
  - **Classification:** **Class A/C** (Official developer API, but limited domain coverage).
- **Indian OTAs (MakeMyTrip, Goibibo, EaseMyTrip):**
  - **Status:** No open public developer APIs. API access is restricted to closed corporate travel platforms (`myBiz`, `myPartner`) requiring registered travel agency licensing and commercial contracts.
  - **Classification:** **Class D/E** (Closed commercial ecosystems).

### 5.3. Truth-in-Data Categorization of Accommodation Information
To prevent misinforming pilgrims, the platform must formally separate five distinct states:
1. **Published Tariff:** Base rack rate registered with District Administration Reasi or SMVDSB published tariff schedule (Static / Curated).
2. **Indicative Market Price:** Typical seasonal price range observed for the property tier (e.g. ₹800 – ₹2,500/night).
3. **Actual Current Price:** Dynamic live quote generated by a provider for specific dates with active yield management.
4. **Actual Room Availability:** Real-time system verification that unreserved inventory exists for specific check-in/out dates.
5. **Confirmed Booking:** Cryptographically or system-verified reservation with a confirmed booking reference, guest name, and settlement.

### 5.4. Feasibility Verdict for Accommodation Intelligence
- **Verdict:** **MAINTAIN CURATED CATALOG ARCHITECTURE; CONDITIONAL GDS EXTENSION**
- **Architecture Strategy:**
  1. Continue utilizing the **`CuratedAccommodationAdapter`** (`data/katra_accommodation_catalog.json`) as the primary accommodation knowledge base for Katra.
  2. Tag all accommodation results with explicit provenance: `source_type = "curated_data"`, `availability_verified = False`, and clear tariff disclaimers (*"Indicative tariff band; live availability must be confirmed directly with property or official Shrine Board portal"*).
  3. Keep the Amadeus provider adapter (`AmadeusHotelAdapter`) as an optional secondary provider for luxury/chain properties, strictly isolated from local budget properties.

---

## 6. Workstream D — Tourism & Pilgrimage Intelligence Feasibility

### 6.1. SMVDSB Pilgrimage Facilities
- **Facilities:** Battery car (Ardhkuwari–Bhawan), passenger cable car (Bhawan–Bhairon), helicopter shuttle (Katra–Sanjichhat), free Langar (Tarakote, Sanjichhat, Bhawan), cloakrooms, medical dispensaries.
- **Operating Norms:**
  - Battery cars run 24x7 subject to track clearance and weather, prioritized for senior citizens and differently-abled pilgrims.
  - Passenger cable car operates daylight hours (approx. 7:00 AM – 5:00 PM), subject to high-wind safety cutoffs.
  - Helicopter shuttle operates daylight hours only, highly sensitive to cloud cover and valley fog.
  - Pithoo, Palki, and Pony rates are strictly fixed by District Administration Reasi and SMVDSB.
- **Data Stability:** These policies and operating rules are stable throughout the year and are appropriately captured in static documentation.
- **Classification:** **Class B/D** (Official published policies; best served via Static RAG).

### 6.2. Jammu & Kashmir Tourism Development Corporation (JKTDC)
- **Portals:** `https://www.jktdc.co.in/`, `https://jandktourism.jk.gov.in/`
- **API Availability:** **No open developer API.**
- **Content:** Tourist circuits, heritage sites (Krimchi Temples, Baba Banda Bahadur), hill resorts (Patnitop, Sanasar), and water bodies (Mansar, Surinsar).
- **Classification:** **Class D/E** (No public API; static tourism descriptions).

### 6.3. Separation of Static RAG vs. Dynamic Live Data
| Domain | Information Type | Optimal Architecture Layer | Rationale |
| :--- | :--- | :--- | :--- |
| **Temple Legend & History** | Static Knowledge | **RAG Vector Store** (`knowledge_base/`) | Immutable religious history and traditions. |
| **Trek Routes & Elevation** | Static Knowledge | **RAG Vector Store** (`routes_and_trekking.json`) | Physical track profiles do not change dynamically. |
| **Ritual Timings & Etiquette** | Static Knowledge | **RAG Vector Store** (`vaishno_devi_pilgrimage.json`) | Aarti timings and darshan norms are statutory. |
| **Statutory Pony/Palki Rates**| Curated Table | **RAG / Catalog** | Rates are revised annually by district notification. |
| **Track Closures & Landslides**| Volatile Notice | **Live Provider** (`CuratedOperationalNoticesAdapter`) | Changes hourly based on weather and rockfall. |
| **Severe Weather & Wind** | Volatile Telemetry | **Live Provider** (`OpenMeteoWeatherAdapter`) | Direct safety impact on cable car and trekking. |
| **Emergency Helplines** | Curated Helpline | **Live Provider** (`VerifiedContactAdapter`) | Critical life-safety contact routing. |

---

## 7. Workstream E — Weather & Environmental Intelligence Feasibility

### 7.1. Existing Open-Meteo Integration Assessment
- **Provider:** Open-Meteo REST API (`weather_adapter.py`, `weather.py`).
- **Resolution:** High-resolution numerical weather prediction (NWP) model incorporating exact coordinates and barometric elevation.
- **Coverage:** Four discrete pilgrimage milestones:
  - Katra Base: 750 m
  - Ardhkuwari Mid-point: 1,400 m
  - Bhawan Sanctum Sanctorum: 1,585 m (~5,200 ft)
  - Bhairon Peak: 2,011 m (~6,600 ft)
- **Licensing & Usage Limits:** Free tier allows up to 10,000 API calls per day for non-commercial use with CC BY 4.0 attribution (`"Weather data by Open-Meteo.com"`). Commercial licenses are available for enterprise scaling.
- **Reliability:** Proven 100% reliable across 28 dedicated automated tests in `test_phase8_1_weather.py`. Provides elevation-adjusted seasonal fallback when offline.
- **Classification:** **Class A** (Official documented API with authorized access).

### 7.2. India Meteorological Department (IMD) API Platform
- **Authority:** India Meteorological Department (IMD), Ministry of Earth Sciences.
- **Portal:** `https://api.imd.gov.in/public/index.php`
- **Capabilities:** District-level severe weather warnings (Color-coded: Red, Orange, Yellow, Green), Nowcasts (3-hour station warnings), and Quantitative Precipitation Forecasts (QPF).
- **Access Architecture:** Requires registration on the IMD API platform, static public IP whitelisting by IMD administrators, and token authentication (API Key + JWT Bearer token).
- **Value Proposition for Yatra AI:** Official statutory severe weather warnings for Reasi and Jammu districts could directly feed `OperationalNoticeCategory.WEATHER_WARNING`.
- **Classification:** **Class A** (Official documented API with authorized access, subject to IP whitelisting approval).

### 7.3. Feasibility Verdict for Weather Intelligence
- **Verdict:** **APPROVED (MAINTAIN OPEN-METEO; CONDITIONAL IMD EXTENSION)**
- **Architecture Strategy:**
  1. Maintain **`OpenMeteoWeatherAdapter`** as the primary live weather engine.
  2. Open-Meteo fully satisfies all forecast requirements without requiring static IP binding or organizational approvals.
  3. Keep IMD API integration on the long-term roadmap as an official secondary source for statutory weather warning circulars once organizational IP whitelisting is secured.

---

## 8. Source Evidence Matrix

| Candidate Source | Domain | Authority / Org | Classification | Official URL | Documented API? | Auth Model | Rate Limits / Cost | Feasibility Finding |
| :--- | :--- | :--- | :---: | :--- | :---: | :--- | :--- | :---: |
| **Indian Railways NTES** | Railway | CRIS / MoR | **Class D** | `enquiry.indianrail.gov.in` | No public API | None (Web only) | Scraping prohibited | **BLOCKED** |
| **IRCTC TIES** | Railway | IRCTC | **Class A (B2B)**| `irctc.co.in` | Yes (Enterprise) | Formal Contract, IP, Cert | Commercial license fees | **CONDITIONAL (B2B)** |
| **RailRadar API** | Railway | RailRadar | **Class C** | `railradar.in` | Yes (REST/JSON) | API Key (`x-api-key`) | 100 req/mo free; paid tiers | **APPROVED (CONDITIONAL)** |
| **J&K Traffic Police** | Traffic | J&K Police | **Class D** | `trafficpolice.jk.gov.in`| No public API | None (Web notices) | Scraping prohibited | **BLOCKED** |
| **Traffic Control Units**| Traffic | J&K Police | **Class B** | Official Helplines | Voice Telephone | 24x7 Telephone lines | Standard call rates | **APPROVED (CURATED)** |
| **NHAI Rajmargyatra** | Traffic | NHAI / MoRTH | **Class D/E** | `rajmargyatra.ihmcl.co.in`| No public API | Consumer App only | N/A | **BLOCKED** |
| **SMVDSB Rooms Portal** | Accom. | SMVDSB | **Class D/E** | `online.maavaishnodevi.org`| No public API | Login + CAPTCHA + OTP | Auth-gated | **BLOCKED** |
| **Amadeus Hotel API** | Accom. | Amadeus IT | **Class A** | `developers.amadeus.com` | Yes (REST/JSON) | OAuth2 Client Credentials | Free test tier; per-call prod | **APPROVED (CHAIN ONLY)**|
| **MakeMyTrip / Goibibo**| Accom. | MakeMyTrip Ltd| **Class D/E** | `makemytrip.com` | No public API | Closed B2B Partner Portal| Commercial contract | **BLOCKED** |
| **Curated Katra Catalog**| Accom. | Yatra AI Audit| **Class B** | Local Data Catalog | JSON Catalog | Internal Verification | Zero external API cost | **APPROVED (ACTIVE)** |
| **SMVDSB Facilities** | Pilgrimage | SMVDSB | **Class B** | `maavaishnodevi.org` | Static Policies | Public Information | Zero cost | **APPROVED (RAG)** |
| **JKTDC Tourism Portal**| Tourism | JKTDC | **Class D** | `jktdc.co.in` | No public API | Consumer Web only | Scraping prohibited | **APPROVED (RAG ONLY)**|
| **Open-Meteo REST API** | Weather | Open-Meteo | **Class A** | `open-meteo.com` | Yes (REST/JSON) | None (Public endpoint) | 10,000 req/day free | **APPROVED (ACTIVE)** |
| **IMD API Platform** | Weather | IMD / MoES | **Class A** | `api.imd.gov.in` | Yes (REST/JSON) | API Key + JWT + Static IP| Free (Govt registration) | **CONDITIONAL (IP)** |

---

## 9. Provider Architecture Compatibility

### 9.1. Proposed `RailRadarTrainAdapter` Design
To safely introduce railway intelligence without breaking existing contracts:
- **Adapter Location:** `services/live_data/adapters/railradar_train_adapter.py`
- **Base Class:** `BaseLiveDataProvider`
- **Domain:** `DataDomain.TRANSPORT.value` (`"transport"`)
- **Configured Capability:** `["train_running_status", "station_live_board", "train_schedule"]`
- **Input Parameters (`ProviderRequest`):**
  - `location`: Station code (e.g., `'SVDK'`, `'JAT'`, `'UHP'`, `'NDLS'`)
  - `params`: `{"train_number": "22439", "date": "2026-11-08"}`
- **Output Data Structure (`LiveDataResult`):**
  ```python
  {
      "train_number": "22439",
      "train_name": "NDLS-SVDK Vande Bharat Express",
      "origin": "NDLS",
      "destination": "SVDK",
      "current_station": "Udhampur (MCTM)",
      "delay_minutes": 12,
      "status": "RUNNING",
      "eta_destination": "2026-11-08T14:12:00Z",
      "last_updated": "2026-11-08T13:45:00Z",
      "is_delayed": True,
      "halts": [...]
  }
  ```
- **Provenance Attributes:**
  - `source_name`: `"RailRadar Developer Telemetry"`
  - `source_type`: `SourceType.THIRD_PARTY_API.value`
  - `verification_status`: `VerificationStatus.VERIFIED_EXTERNAL_API.value` (or `UNVERIFIED`)
  - `disclaimer`: `"Third-party transit telemetry. Delay estimates may fluctuate based on signal clearance. Verify at station or call 139."`

### 9.2. Proposed Contract Additions (`services/live_data/contracts.py`)
To ensure strong typing, add two standardized dataclasses:
```python
@dataclass
class TrainRunningStatus:
    train_number: str
    train_name: str
    current_station: str
    delay_minutes: int
    is_delayed: bool
    status_summary: str
    eta_destination: Optional[str] = None
    last_reported_timestamp: Optional[str] = None
    source_attribution: str = "RailRadar Telemetry"

@dataclass
class StationLiveBoard:
    station_code: str
    station_name: str
    query_timestamp: str
    arrivals: List[Dict[str, Any]]
    departures: List[Dict[str, Any]]
```

### 9.3. Frontend Presentation Requirements
- **Component:** Extend `TransportMiniCard.jsx` or introduce `TrainRunningStatusCard.jsx`.
- **Visual Indicators:**
  - On-time trains: Green badge (`"On Time"`).
  - Delayed trains: Amber/Red badge (`"Delayed by X mins"`).
  - Cancelled/Diverted: Critical alert badge (`"Cancelled / Diverted"`).
  - Upstream source badge: `"Third-party GPS telemetry"` with clickable popover.

---

## 10. Security and Data-Integrity Assessment

All proposed live data integrations must strictly comply with the twelve core project safety mandates:
1. **Never Invent Live Data:** If an external railway or hotel API fails or returns no data, return an explicit `UNAVAILABLE` or `NO_RESULTS` status. Never synthesize dummy train delays, prices, or room vacancies.
2. **Strict Provenance Labeling:** Clearly distinguish live API, cached API, stale fallback, static RAG, and estimated values in all responses.
3. **Fail-Closed Verification:** A successful API call or JSON load indicates only that *retrieval* succeeded. It does not automatically elevate an unverified third-party report to official statutory verification.
4. **Outage Honesty:** An API outage or empty response must never be rendered as "All Clear" or "No Delays".
5. **No CAPTCHA / Auth Bypassing:** Under no circumstances should scripts attempt to bypass SMVDSB or IRCTC authentication, CAPTCHAs, or OTP prompts.
6. **No Automated Booking Execution:** Preserve the mandatory human confirmation gate (`request_booking_intent` -> user confirmation -> `execute_authorized_booking`).
7. **Rate Limiting & Secret Isolation:** API keys (such as `RAILRADAR_API_KEY` or `AMADEUS_CLIENT_SECRET`) must be managed strictly via environment variables (`.env`) and never exposed in client bundles or public commits.

---

## 11. Prioritized Integration Recommendations

| Priority | Proposed Capability | Recommended Source | Target Checkpoint | Feasibility Finding |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **Live Train Telemetry & Status** | RailRadar REST API | **Phase 9.7.2** | **APPROVED FOR FUTURE IMPLEMENTATION** |
| **2** | **Curated Katra Express Timetable** | Official IR Timetable (Static) | **Phase 9.7.2** | **APPROVED FOR FUTURE IMPLEMENTATION** |
| **3** | **Official Severe Weather Warnings**| IMD API Platform (`api.imd.gov.in`)| **Phase 9.8** | **CONDITIONAL — MORE EVIDENCE REQUIRED** |
| **4** | **Commercial Chain Hotel Search** | Amadeus Hotel Offers API v3 | **Phase 9.8** | **CONDITIONAL — MORE EVIDENCE REQUIRED** |
| **5** | **Live SMVDSB Room Availability** | `online.maavaishnodevi.org` | N/A | **BLOCKED — NO AUTHORIZED PUBLIC API** |
| **6** | **Live NH-44 Video / Traffic Sensor**| J&K Police / NHAI ATMS | N/A | **BLOCKED — NO AUTHORIZED PUBLIC API** |
| **7** | **Automated Ticket Booking Engine** | IRCTC / Shrine Board Portals | N/A | **NOT RECOMMENDED (LEGAL/SAFETY RISK)**|

---

## 12. Blocked or Unsupported Capabilities

1. **Live SMVDSB Bhawan Room Availability:** Blocked. The Shrine Board does not publish live room availability feeds and gates access behind user credentials with CAPTCHA/OTP. Attempting automated scraping is strictly prohibited.
2. **Live RFID Pilgrim Track Counts:** Blocked. Live count of pilgrims crossing Banganga, Ardhkuwari, or Bhawan is held in internal Shrine Board RFID control rooms and is not broadcast publicly.
3. **Automated Government Traffic Polling:** Blocked. J&K Traffic Police has no API or RSS feed. Scraping web press releases violates government IT guidelines. Official telephone helplines (TCUs) remain the designated channel.
4. **Direct CRIS/NTES Internal Feeds:** Blocked without formal IRCTC TIES commercial partnership agreements.

---

## 13. Proposed Phase 9.7 Implementation Sequence

Following this feasibility audit, the recommended implementation sequence is:
- **Phase 9.7.1 (Current):** Live Data Source Discovery & Feasibility Audit (Completed).
- **Phase 9.7.2:** Railway Intelligence Architecture & Data Contracts:
  - Define `TrainRunningStatus` and `StationLiveBoard` dataclasses in `services/live_data/contracts.py`.
  - Create curated Katra Express static dataset (`data/curated_railway_schedules.json`) for key SVDK/JAT trains.
  - Implement `RailRadarTrainAdapter` with mock/sandbox support for testing without depleting API quotas.
- **Phase 9.7.3:** Central Agent & Live Data Manager Transport Integration:
  - Register transport provider in `UnifiedLiveDataManager`.
  - Wire `search_transport_options` tool to prioritize live railway adapter with fallback to curated timetables.
  - Implement `TrainRunningStatusCard.jsx` in frontend with live delay badges and provenance tooltips.
- **Phase 9.7.4:** Comprehensive Verification & Safety Audit:
  - Dedicated unit tests for train running status, station boards, delay calculations, and offline fallback.
  - End-to-end regression testing.

---

## 14. Outstanding Questions Requiring Human Decisions

1. **Third-Party Railway API Subscription:** Does the project sponsor approve using RailRadar (`railradar.in`) as a third-party telemetry source (utilizing the free 100 req/month tier for development), or should the transport domain rely strictly on offline human-curated static timetables?
2. **Amadeus Hotel API Scope:** Should the project pursue Amadeus Hotel integration for luxury Katra hotels (Radisson, Fortune), or is the curated 22-property Katra accommodation catalog sufficient for pilgrimage use?
3. **IMD Static IP Whitelisting:** Is a dedicated static public server IP available for registering on the IMD API platform (`api.imd.gov.in`), or should Open-Meteo remain the sole weather provider?

---

**FEASIBILITY AUDIT COMPLETE. STOPPING EXECUTION IN ACCORDANCE WITH AUDIT MANDATE.**
