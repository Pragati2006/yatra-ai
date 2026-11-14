# PHASE 9.0 — LIVE DATA SOURCE DISCOVERY & FEASIBILITY AUDIT
## Yatra AI — Unified Pilgrimage & Tourism Assistant

**Audit Date:** November 7, 2026
**Auditor Roles:** Senior Data Systems Architect, Legal & Integration Auditor, API Specialist & Release Engineer
**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Workspace Python Environment:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly Untouched at HEAD `8996d6a`)
**Audit Status:** Strictly Read-Only (Zero Code/Test Modifications)

---

## 1. EXECUTIVE SUMMARY

Phase 9 of Yatra AI investigates methods for augmenting the assistant with reliable, real-world, dynamic information across six operational domains:
1. Hotel room pricing, real-time availability, and direct booking links.
2. Shri Mata Vaishno Devi Shrine Board (SMVDSB) RFID registrations, card issuance, and daily pilgrim carrying capacity.
3. Transport schedules, fares, and availability (Indian Railways, state buses, SMVDSB helicopters, battery cars, and cable cars).
4. Mountain weather, elevation-aware lapse rates, and operational weather alerts.
5. Official Shrine Board notices, track route closures, landslide advisories, and yatra suspensions.
6. Regional tourism attractions, local emergency/medical facilities, and travel guidelines across Jammu, Katra, and Kashmir.

### Core Discoveries & Truth-in-Data Grounding
- **The "Live RFID Counter" Reality:** SMVDSB utilizes RFID-enabled Yatra Access Cards strictly for **internal crowd control, security tracking, and choke-point regulation** across Banganga, Tarakote Marg, and Bhawan. **No public REST API, JSON feed, or real-time remaining capacity counter is published by SMVDSB.** Any claim of a live remaining-card counter is factually false. Yatra AI must honestly report the regulatory carrying capacity (50,000 pilgrims/day per NGT mandate), physical counter operating hours, and official registration status (Open vs. Suspended) derived from official announcements.
- **Indian Railways / IRCTC Reality:** CRIS and IRCTC do not offer a free, open, public REST API for real-time seat availability or PNR tracking. Access is restricted under the commercial **Train Information Enquiry Scheme (TIES)** requiring high registration fees, annual commitment charges, and formal enterprise contracts. Unofficial scraping wrappers (e.g. RapidAPI) violate IRCTC Terms of Service and break frequently. The honest, legally sound approach is to ingest published timetables and station lists from Open Government Data (`data.gov.in`) as indicative data with clear confirmation caveats.
- **Commercial Hotels vs. Shrine Board Dharamshalas:** Global GDS APIs (Amadeus Hotel Offers API v3) provide legitimate, structured room pricing and availability for commercial hotels in Katra, but do not index SMVDSB guest houses or small local lodges. SMVDSB dharamshala tariffs are officially standardized by the Shrine Board (₹120–₹2,500/night) and must be presented as curated baseline schedules, since live room availability is locked behind authenticated login and graphical CAPTCHA on `online.maavaishnodevi.org`.
- **Weather & Operational Alerts:** Open-Meteo continues to provide an outstanding, open, elevation-aware forecast API (Class A). Official SMVDSB route advisories and J&K Traffic Police NH-44 alerts are extractable from public announcement marquees (Class C) to power automated background alerts.

---

## 2. EXISTING ARCHITECTURE ASSESSMENT

The robust infrastructure established in Phase 8 provides the complete foundation required to ingest, cache, attribute, and display live dynamic data without architectural rework:

1. **Unified Response Envelope & Provenance Schema (`utils/provenance.py`):**
   - Directly supports `SourceType.LIVE_API`, `SourceType.CACHED_API`, `SourceType.CURATED_DATA`, and `SourceType.INDICATIVE_DATA`.
   - Distinctly tracks `retrieval_timestamp` (when Yatra AI queried the source) vs `data_timestamp` (when the source recorded the observation).
   - Validates external provider URLs and sanitizes them (`http:`/`https:` only) to prevent XSS before rendering in client cards.
2. **In-Memory Freshness & Cache Engine (`utils/cache_manager.py`):**
   - Thread-safe single-flight coordination (`_single_flight_mutex`) prevents stampedes during concurrent queries.
   - Built-in `stale_if_error` recovery gracefully preserves expired entries during provider network timeouts.
   - Distinct TTL policies can be assigned per category (e.g., 30 minutes for weather, 15 minutes for operational notices, 24 hours for static timetables).
3. **Central AI Agent Hybrid Orchestrator (`agents/central_agent.py`):**
   - LangChain tool execution pipeline with in-batch canonical deduplication (`registered_sigs`).
   - Seamless deterministic fallbacks ensure provider outages never crash the conversation.
4. **Frontend Provenance Presentation (`frontend/src/components/chat/provenance/`):**
   - Micro-pills (`SourceBadge.jsx`), multi-source badges (`ProvenanceList.jsx`), and accessible modal inspection (`SourceDetailsPopover.jsx`) already render live, cached, stale, fallback, and curated metadata cleanly.

---

## 3. HOTEL SOURCE FEASIBILITY

### 3.1 Commercial Hotels in Katra & Jammu
Pilgrims require hotel recommendations ranging from budget dharamshalas to luxury resorts (e.g. Vivanta Katra, Welcomhotel Katra, Lemon Tree, Hotel Rama Trident).

| Provider / Channel | Data Fields Available | Access Method & Auth | Feasibility & Restrictions | Classification |
|---|---|---|---|:---:|
| **Amadeus for Developers** (Hotel Search & Shopping API v3) | Room rates, room types, taxes/fees, cancellation policies, booking offer IDs | REST API, OAuth2 Client Credentials (Free Self-Service tier: 2,000 monthly test calls) | **Feasible for branded/chain hotels.** Katra geocode (`32.99° N, 74.93° E`, radius 5–10km). Does not index small independent lodges or dharamshalas. | **A (Official API)** |
| **Google Places / Hotels** (Place Details API) | Hotel name, user rating, address, photos, phone, indicative price level, website link | Google Maps Platform REST API (API key with billing enabled) | **Feasible for directory and location enrichment.** High reliability. Does not return live room availability for specific check-in dates. | **A (Official API)** |
| **Domestic OTAs** (MakeMyTrip, Goibibo, Yatra, OYO) | Real-time Katra budget room availability, instant booking links | No public developer API. Restricted B2B affiliate program | **Not feasible for direct integration.** Automated scraping strictly prohibited by ToS and blocked by Akamai/Cloudflare bot protection. | **E (Restricted)** |

### 3.2 SMVDSB Dharamshalas & Guest Houses
The Shrine Board operates non-profit pilgrim accommodations at Katra base (Niharika Bhawan, Shakti Bhawan, Ashirwad Bhawan, Trikuta Bhawan) and along the route / Bhawan (Kalika Bhawan, Saraswati Dham, Manokamana Bhawan, Bhawan Main complex).

- **Available Information:**
  - Standardized tariff schedule: Officially published and fixed annually (e.g. Dormitory bed: ₹120–₹150; Standard room: ₹750–₹1,200; AC Suite: ₹1,500–₹2,500).
  - Room categories, amenities, check-in rules (24-hour cycle, valid Yatra Registration slip mandatory).
- **Live Inventory Feasibility:**
  - Real-time room vacancy is locked behind authenticated pilgrim accounts with graphical CAPTCHA on `online.maavaishnodevi.org`.
  - Automated extraction is prohibited and would compromise security controls.
- **Feasibility Classification:** **Class D (Curated Official Schedule)**.
- **Recommended Integration:** Ingest official SMVDSB published tariffs and booking windows into the curated knowledge catalog. When pilgrims inquire about availability, provide the exact indicative tariff, location, amenities, and direct them to the official `online.maavaishnodevi.org` portal for reservation.

---

## 4. RFID AND DAILY CAPACITY FEASIBILITY

### 4.1 SMVDSB Yatra Access Card (RFID) Infrastructure
In 2022, SMVDSB replaced traditional paper Yatra Parchi with RFID-enabled Yatra Access Cards.

| Metric / Parameter | Public Availability | Official Source | Investigation Finding | Classification |
|---|:---:|---|---|:---:|
| **Daily Carrying Capacity** | Semi-Static / Public | National Green Tribunal (NGT) & SMVDSB Guidelines | Capped at **50,000 pilgrims per day** at Bhawan. Regulated dynamically during adverse weather. | **Class D (Curated Standard)** |
| **Live RFID Issue Counter** | **NOT AVAILABLE** | SMVDSB Internal Control Room | **No public API, webhook, or live counter exists.** Data is restricted to disaster management and police control rooms. | **Class E (No Public Source)** |
| **Instantaneous Bhawan Headcount** | **NOT AVAILABLE** | SMVDSB Choke-Point Scanners | Restricted internal telemetry (Banganga, Tarakote, Sanjichhat, Bhawan entry gates). | **Class E (No Public Source)** |
| **Registration Status (Open/Suspended)** | **Available** (Public Web) | `maavaishnodevi.org` flash ticker & press releases | Text announcements published when yatra registration is temporarily suspended due to heavy rain, landslides, or crowd saturation. | **Class C (Public Text Notice)** |
| **Registration Counter Details** | **Available** (Static/Curated) | Official SMVDSB Handbook | 100% free physical registration counters at Katra Railway Station, Bus Stand, Counter No. 2, and Tarakote Marg (Operating hours: 5:00 AM – 10:00 PM). | **Class D (Curated Official)** |

### 4.2 The Honest Alternative
Yatra AI must **never simulate or fabricate a dynamic "Remaining RFID Cards: 14,230" counter**. The honest system architecture must:
1. Clearly display the official **50,000 pilgrims/day ceiling** established by the NGT and Shrine Board.
2. Ingest the official **Registration Status** (Operational / Paused / Weather Suspended) from the Shrine Board's public bulletin board.
3. Provide pilgrims with physical counter locations, operating timings, required government photo IDs, and rules (RFID card is mandatory, non-transferable, and must be returned at exit points).

---

## 5. TRANSPORT SOURCE FEASIBILITY

### 5.1 Indian Railways (IRCTC / Northern Railway)
Katra is served by Shri Mata Vaishno Devi Katra Railway Station (SVDK), connected via major trains including Vande Bharat Express (22439/22440, 22477/22478), Uttar Sampark Kranti (12445/12446), and Shri Shakti Express (22461/22462).

- **Official API Status:**
  - CRIS / Indian Railways enterprise API gateway ("Project Pravah") is strictly B2B and requires accredited institutional credentials.
  - IRCTC Train Information Enquiry Scheme (TIES) requires heavy commercial fees, recurring annual commitment charges, and formal agreements.
  - Open Government Data Platform India (`data.gov.in`) provides static/curated train route lists, station codes, and master timetables.
- **Feasibility Classification:** **Class D (Curated Official Timetable)**.
- **Recommended Integration:** Ingest published SVDK train timetables, arrival/departure schedules, and operating frequencies. Tag all responses with `source_type = "indicative_data"` and disclaimer: *"Schedules based on published Northern Railway timetables. Real-time platform and seat availability must be verified on IRCTC."*

### 5.2 Bus Services (JKSRTC & Private Operators)
- **JKSRTC (Jammu & Kashmir State Road Transport Corporation):**
  - Connects Jammu Tawi Railway Station and Jammu Airport to Katra Bus Stand.
  - Fleet: Deluxe, AC Volvo, and Super Fast buses.
  - Timetables & Fares: Publicly published by JKSRTC (`jksrtc.jk.gov.in`). Flat fares (approx. ₹150–₹250 for Deluxe, ₹350–₹450 for AC Volvo).
  - Feasibility: **Class D (Curated Official Schedule)** with periodic seasonal updates.
- **Private Tourist & Inter-State Buses:**
  - Services from Delhi, Chandigarh, Amritsar, and Jaipur.
  - Aggregators (RedBus, AbhiBus) do not offer open public developer APIs.
  - Feasibility: **Class D (Curated indicative routes and average fare bands)**.

### 5.3 SMVDSB Helicopter Services (Katra ⇋ Sanjichhat)
- **Operators:** Global Vectra Helicorp and Himalayan Heli Services (contracted by SMVDSB).
- **Helipad Locations:** Serli Helipad (Katra) and Sanjichhat Helipad (~2.5 km from Bhawan).
- **Official Tariff:** Fixed by SMVDSB (₹2,100 per passenger one-way / ₹4,200 return; infants under 2 fly free).
- **Booking Rules:** 100% exclusively online via `online.maavaishnodevi.org` (opens 60 days in advance) or emergency current counter at Serli Helipad with mandatory biometric verification.
- **Flight Operations Status:** Extremely weather-dependent (suspended during poor visibility, strong mountain winds, or heavy rains).
- **Feasibility Classification:** **Class D (Curated Official Tariff)** + **Class C (Weather-linked operational status)**.

### 5.4 Battery Car & Cable Car Services
- **Battery Car (Ardhkuwari ⇋ Bhawan via Himkoti Marg):**
  - Official Tariff: ₹354 uphill, ₹236 downhill per passenger.
  - Priority: Senior citizens (>60 years) and specially-abled pilgrims.
  - Booking: On-spot counters at Ardhkuwari and Bhawan; limited online quota on `online.maavaishnodevi.org`.
  - Feasibility: **Class D (Curated Official Rules & Fares)**.
- **Bhairon Ropeway / Cable Car (Bhawan ⇋ Bhairon Temple):**
  - Capacity: 800 persons/hour (Swiss cabin system).
  - Tariff: ₹100 round trip per passenger.
  - Ticketing: On-spot scanning using RFID card at Bhawan ropeway station.
  - Operating Hours: 7:00 AM to 5:00 PM (suspended during high winds).
  - Feasibility: **Class D (Curated Rules & Tariff)**.

---

## 6. WEATHER & OPERATIONAL NOTICE FEASIBILITY

### 6.1 Weather Integrations
- **Open-Meteo API:**
  - **Status:** Integrated, verified, and operational in Phase 8 (Checkpoint 8.1).
  - **Capabilities:** Elevation-aware mountain forecasting (750m to 2,011m) with temperature lapse-rate calculations (-6.5°C/km), precipitation probability, and wind speeds.
  - **Terms:** Open access, free up to 10,000 calls/day, attribution required.
  - **Feasibility:** **Class A (Official Structured API)** — **GO**.
- **India Meteorological Department (IMD) Bulletins:**
  - Katra Base Station (Index 42050) provides daily regional forecasts and severe weather warnings (`mausam.imd.gov.in`).
  - Feasibility: **Class C (Public Bulletins)** / **Class D (Climatological Normals)** used as offline seasonal fallback.

### 6.2 Official Shrine Board Notices & Track Advisories
- **SMVDSB Flash Notices:**
  - Published on `maavaishnodevi.org` homepage announcements and `/news.aspx`.
  - Alerts cover track closures (e.g. shooting stones on Himkoti Marg), helicopter suspensions, and Aarti timings.
  - Extraction Method: Lightweight, periodic HTTP parsing of the public announcement banner (every 15–30 minutes) stored in `CacheManager`.
  - Feasibility: **Class C (Public Web Extraction)** — **GO**.
- **J&K Traffic Police Highway Bulletins:**
  - Daily status of NH-44 (Jammu-Srinagar Highway) and Jammu-Katra link road.
  - Published via J&K Traffic Police press bulletins and official Twitter/X handle (`@Traffic_hqrs`).
  - Feasibility: **Class C (Public Text Bulletins)**.

---

## 7. TOURISM & EMERGENCY SOURCE FEASIBILITY

### 7.1 Tourism Attractions & Regional Circuits
- **Sources:** Directorate of Tourism, Jammu (`jammutourism.gov.in`), JKTDC (`jktdc.co.in`), and District Administration Reasi (`reasi.nic.in`).
- **Covered Destinations (29 destinations cataloged):**
  - Katra circuit: Bhawan, Bhairon Temple, Ardhkuwari, Charan Paduka, Ban Ganga, Baba Dhansar, Siar Baba, Shiv Khori.
  - Jammu circuit: Bahu Fort & Bagh-e-Bahu, Raghunath Temple, Amar Mahal Museum, Kol Kandoli Temple.
  - Patnitop & Hill Stations: Sanasar, Nathatop, Kud, Mansar Lake, Surinsar Lake.
- **Data Attributes:** Operating hours, historical significance, dress code/etiquette, distance from Katra base, local taxi union tariffs.
- **Feasibility Classification:** **Class D (Curated Regional Catalog)**. Verified, grounded, and complete.

### 7.2 Medical and Emergency Facilities
Pilgrims, especially elderly travellers or families, frequently require urgent medical information:

| Facility Name | Location | Capability & Services | Contact / Access | Classification |
|---|---|---|---|:---:|
| **SMVD Narayana Super Speciality Hospital** | Kakryal (~12 km from Katra) | 230-bed tertiary hospital, 24/7 Trauma, Cardiology, ICU, Emergency | Dedicated emergency trauma hotline; SMVDSB partner facility | **Class D (Curated Verified)** |
| **Sub-District Hospital (SDH) Katra** | Katra Town | Base emergency care, ambulance services, general medicine | Directorate of Health Services Jammu | **Class D (Curated Verified)** |
| **SMVDSB Track Dispensaries** | Banganga, Ardhkuwari, Himkoti, Sanjichhat, Bhawan | Free first-aid, oxygen cylinders, emergency cardiac care, specialized stretcher evacuation | Operated 24/7 by Shrine Board Medical Staff | **Class D (Curated Verified)** |
| **Disaster Management Task Force** | Trikuta Hills | Quick response team, landslide clearance, emergency search and rescue | Joint SMVDSB & J&K Police Emergency Cell | **Class D (Curated Verified)** |

---

## 8. AUTOMATIC REFRESH FEASIBILITY

Automatic background polling reduces user query latency and ensures up-to-date information without overloading providers.

```
+------------------------------------------------------------------------------------+
|                        AUTOMATIC BACKGROUND REFRESH SCHEDULE                       |
+------------------------------------------------------------------------------------+
| Source / Endpoint          | Poll Frequency | Target Cache TTL | Error Handling    |
+----------------------------+----------------+------------------+-------------------+
| Open-Meteo Weather         | Every 30 mins  | 60 mins          | Stale-if-error    |
| SMVDSB Advisory Ticker     | Every 15 mins  | 30 mins          | Retain prior news |
| J&K Traffic Road Status    | Every 30 mins  | 60 mins          | Fallback notice   |
| Amadeus Hotel Search       | Disabled       | On-demand only   | Prevent quota burn|
| Train Timetables (Static)  | Weekly         | 7 days           | Static catalog    |
| Curated Regional Tourism   | Bi-weekly      | 14 days          | Static catalog    |
+------------------------------------------------------------------------------------+
```

### Technical Implementation Mechanism
- Implemented as a lightweight asynchronous worker task using `asyncio` or FastAPI background tasks.
- Calls `CacheManager.set()` with designated `ttl` and `max_stale`.
- Strict circuit breaker prevents repeated rapid polling if a government website returns HTTP 500 or times out.

---

## 9. ON-DEMAND RETRIEVAL FEASIBILITY

On-demand retrieval is triggered when a user explicitly requests real-time data that cannot be predicted in advance:
1. **Dynamic Hotel Shopping (Amadeus Hotel Offers API v3):**
   - Trigger: User specifies check-in/out dates, guest count, and hotel budget.
   - Execution: Query Amadeus with Katra geocode (`32.99° N, 74.93° E`).
   - Latency: ~1.2s to 2.5s.
   - Cache Strategy: Keyed by `f"amadeus:hotel:{check_in}:{check_out}:{pax}"` with 15-minute TTL.
2. **Specific Date Weather Lookup:**
   - Trigger: User asks for weather on a specific date (e.g. 10 days ahead).
   - Execution: Query Open-Meteo daily forecast range.
   - Latency: ~0.3s to 0.6s.
   - Cache Strategy: Keyed by `f"weather:{location}:{target_date}"` with 60-minute TTL.

---

## 10. LEGAL, TERMS OF SERVICE & ACCESS RESTRICTIONS

| Provider / Target | Permitted Use | Strict Prohibitions & Legal Boundaries |
|---|---|---|
| **Open-Meteo API** | Permitted for non-commercial and application use under fair use limits (<10,000 calls/day). Requires attribution. | Commercial resale without license; extreme high-frequency hammering. |
| **Amadeus for Developers** | Permitted for registered developers; rate limits enforced via OAuth2 tokens. | Caching pricing data beyond 24 hours; scraping GDS content without API. |
| **SMVDSB (`maavaishnodevi.org`)** | Public reading of published notices, tariff charts, guidelines, and circulars. | **STRICT PROHIBITION:** Automated scraping of authenticated sections, CAPTCHA bypass, unauthorized ticket booking bots, credential harvesting. |
| **Indian Railways / IRCTC** | Reading public schedules from Open Government Data (`data.gov.in`). | **STRICT PROHIBITION:** Unauthorized automated PNR/availability scraping. Violates IRCTC IT policies and Section 43/66 of Indian Information Technology Act. |
| **Domestic OTAs (MakeMyTrip, OYO)** | Manual web browsing by consumers. | Automated scraping prohibited under Computer Fraud and Abuse / ToS terms; aggressively blocked by Cloudflare bot management. |

---

## 11. SOURCE INVENTORY & CLASSIFICATIONS

Classification Scheme:
- **A** — Official structured API or public data feed.
- **B** — Authorized automated extraction with formal permissions.
- **C** — Public but limited or unstructured web information.
- **D** — Curated, verified static or indicative knowledge base.
- **E** — No suitable verified public source found.

| # | Data Domain | Provider & Source URL | Update Frequency | Available Fields | Feasibility Class | Recommended Integration Strategy |
|---|---|---|---|---|:---:|---|
| **1** | Elevation Mountain Weather | Open-Meteo API (`api.open-meteo.com`) | Hourly / Daily | Temp, low/high, rain probability, wind, elevation | **A** | Active Phase 8 integration; automated 30-min cache refresh. |
| **2** | Historical Climatology | IMD Normals (`mausam.imd.gov.in`) | Seasonal | Monthly averages, standard lapse rates | **D** | Offline seasonal fallback engine in `weather.py`. |
| **3** | Commercial Hotels (Katra) | Amadeus Developer API (`api.amadeus.com`) | Real-time | Room rates, room types, taxes, cancellation | **A** | On-demand tool call via `central_agent` with 15-min cache. |
| **4** | SMVDSB Dharamshalas | SMVDSB Official Portal (`maavaishnodevi.org`) | Annual tariff revision | Room names, standard tariffs, amenities, booking rules | **D** | Curated catalog in knowledge base with official portal link. |
| **5** | Domestic OTA Hotel Vacancy | MakeMyTrip / OYO / Goibibo | Real-time | Live room vacancy | **E** | **No public API.** Do not scrape. Provide indicative rates. |
| **6** | RFID Live Counter | SMVDSB Operations Control Room | Real-time (Internal) | Instantaneous cards issued, remaining capacity | **E** | **No public API.** Disclose NGT 50,000 cap; do not fake counter. |
| **7** | Yatra Registration Status | SMVDSB Home Marquee (`maavaishnodevi.org`) | Ad-hoc / Flash | Yatra open/suspended status, track closures | **C** | Public announcement banner parser with 15-min background poll. |
| **8** | Railway Timetables (SVDK) | Northern Railway / `data.gov.in` | Bi-annual | Train name, number, arrival/departure, origin | **D** | Curated indicative timetable dataset; refer user to IRCTC. |
| **9** | Real-time Train Availability| CRIS / IRCTC TIES | Real-time (Commercial) | Live seat vacancy, PNR tracking | **E** | **No open public API.** Commercial TIES only. Provide indicative info. |
| **10**| JKSRTC State Buses | JKSRTC (`jksrtc.jk.gov.in`) | Seasonal | Routes (Jammu-Katra), bus types, flat fares | **D** | Curated transport catalog with booking counter locations. |
| **11**| Helicopter Service | SMVDSB / Global Vectra / Himalayan Heli | Fixed Tariff / Seasonal | Fixed rates (₹2,100), helipad locations, luggage limits | **D** | Curated official guidelines; link to `online.maavaishnodevi.org`. |
| **12**| Battery Car & Cable Car | SMVDSB Transport Division | Fixed Tariff | Fares (₹354/₹236, ₹100 ropeway), operating hours | **D** | Curated official guidelines with concession rules for elderly. |
| **13**| Highway Traffic (NH-44) | J&K Traffic Police (`@Traffic_hqrs`) | Daily / Twice Daily | Road open/closed, convoy timings, landslide alerts | **C** | Public bulletin parser with 30-min cache TTL. |
| **14**| Regional Tourism Sights | J&K Tourism (`jammutourism.gov.in`) | Static / Curated | 29 sights, visiting hours, history, distance | **D** | Curated Vector Store RAG knowledge base. |
| **15**| Emergency & Hospital Care | SMVD Narayana Hospital & SDH Katra | 24/7 Verified | Emergency hotlines, trauma facilities, dispensaries | **D** | Curated critical emergency directory in knowledge base. |

---

## 12. RECOMMENDED ARCHITECTURE FOR PHASE 9

```
[ External World ]
   ├── Open-Meteo REST API (Class A) ──────┐
   ├── Amadeus Hotel API v3 (Class A) ─────┤
   ├── SMVDSB News Ticker (Class C) ───────┤
   └── J&K Highway Bulletins (Class C) ────┤
                                           │
                                           ▼
[ Ingestion & Background Polling Engine ]
   ├── Background Scheduler (30-min weather, 15-min flash notices)
   ├── Rate Limiter & Circuit Breaker (exponential backoff)
   ├── Normalizer & Sanitizer (converts raw payloads into typed schemas)
   │
   ▼
[ CacheManager (utils/cache_manager.py) ]
   ├── Keyed by category & parameters
   ├── Single-flight concurrency deduplication
   ├── TTL expiry & Stale-if-error fallback
   │
   ▼
[ CentralAgent & Coordinator (agents/) ]
   ├── Tool Selector: invokes live tool vs cached entry vs curated catalog
   ├── Attaches DataProvenance (SourceType, FreshnessStatus, Timestamps)
   ├── Enforces Truth-in-Data Disclaimers (Indicative vs Live vs Simulated)
   │
   ▼
[ FastAPI Response Envelope & Session Store ]
   ├── JSON serialized into SQLite metadata_json
   │
   ▼
[ React 19 Frontend ]
   ├── SourceBadge: Live (Emerald), Cached (Sky), Stale (Amber), Fallback (Rose)
   ├── SourceDetailsPopover: Viewport-clamped interactive modal
   └── Truth-in-Data Cards: WeatherCard, HotelMiniCard, TransportMiniCard
```

---

## 13. PROPOSED PHASE 9.1 IMPLEMENTATION ORDER

When Phase 9.1 is authorized, implementation should proceed in four disciplined, incremental checkpoints:

1. **Checkpoint 9.1: Live Operational Advisory & Route Notice Parser:**
   - Ingest SMVDSB public announcements and J&K Traffic Police road advisories (Class C).
   - Add automated 15-minute background refresh to `CacheManager`.
   - Propagate real-time track advisories (e.g., *"Himkoti battery car track temporarily suspended due to heavy rain; traditional track via Ardhkuwari operational"*) to the Central Agent and frontend alert cards.
2. **Checkpoint 9.2: Amadeus Hotel Search Integration:**
   - Integrate Amadeus for Developers Hotel Search & Shopping API v3 (Class A) as a callable LangChain tool.
   - Filter Katra properties with fallback to curated indicative tariffs when API quota is exhausted or property is not GDS-indexed.
   - Enforce explicit `SourceType.LIVE_API` provenance with live offer expiration timestamps.
3. **Checkpoint 9.3: Honest RFID & Daily Capacity Guidance Engine:**
   - Formalize the official NGT 50,000 pilgrims/day regulatory ceiling and counter operating directory.
   - Link real-time registration status directly to SMVDSB operational advisory feed.
   - Display prominent truth-in-data guidance disclaiming instantaneous RFID queue counts.
4. **Checkpoint 9.4: Emergency & Medical Facility Quick-Action Service:**
   - Integrate structured lookup for SMVD Narayana Super Speciality Hospital, trackside medical aid centres, oxygen posts, and emergency ambulance contacts.
   - Tag with `VerificationStatus.VERIFIED_OFFICIAL_SOURCE` and instant dial/location actions.

---

## 14. RISKS AND UNRESOLVED QUESTIONS

1. **Risk of Public Web Ticker Markup Changes (Class C):**
   - *Risk:* If SMVDSB redesigns `maavaishnodevi.org`, HTML scraping selectors may fail.
   - *Mitigation:* Defensive regex parsing, schema validation, and immediate fallback to `CacheManager` stale cache or curated baseline with clear degraded status.
2. **Amadeus GDS Inventory Depth in Katra:**
   - *Risk:* Amadeus may only return 5–15 major commercial hotels in Katra, omitting small lodges.
   - *Mitigation:* Hybrid response combining live GDS offers for available branded hotels with curated indicative schedules for local dharamshalas and lodges.
3. **Absence of Real-Time Train Vacancy:**
   - *Risk:* Users may expect live IRCTC PNR or seat availability status inside the chat.
   - *Mitigation:* Transparent conversational handling: explicitly inform the user that live IRCTC seat reservations require official IRCTC login, and provide one-click direct links to the official IRCTC portal.

---

## 15. GO / NO-GO RECOMMENDATION BY CATEGORY

| Domain / Category | Evaluated Sources | Feasibility Class | Final Determination | Strategic Rationale |
|---|---|:---:|:---:|---|
| **1. Elevation Weather** | Open-Meteo REST API | **A** | **GO** | Fully functional, zero cost, reliable, elevation-aware. |
| **2. Commercial Hotels** | Amadeus Hotel Offers API v3 | **A** | **GO (Cautious)** | Implement for branded hotels; hybrid fallback to curated baseline for local lodges. |
| **3. SMVDSB Dharamshalas** | Official Tariff Charts | **D** | **GO** | Curated official schedule; no live scraping permitted. |
| **4. Live RFID Counter** | SMVDSB Internal Scanners | **E** | **NO-GO (Reject)** | **No public API exists.** Present NGT cap and counter hours honestly. |
| **5. Yatra Route Advisories** | SMVDSB / Traffic Bulletins | **C** | **GO** | High pilgrim value; parse public notice banner with background cache. |
| **6. Railway Schedules** | Northern Railway / data.gov.in | **D** | **GO** | Ingest published timetables as indicative data; no live IRCTC scraping. |
| **7. Bus & Helicopter** | JKSRTC / SMVDSB Official Schedules | **D** | **GO** | Reliable published fixed fares and booking rules. |
| **8. Emergency / Hospitals** | SMVD Narayana & Track Dispensaries | **D** | **GO** | High safety value; 100% verified official emergency directory. |

---

*(Phase 9.0 Live Data Source Discovery & Feasibility Audit is complete. Implementation of Phase 9.1 has NOT begun and awaits explicit user authorization.)*
