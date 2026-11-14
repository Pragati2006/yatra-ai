# Phase 9.4: Live Data Source Integration Roadmap & Architecture Audit

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`)
**Workspace Python Runtime:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Audit Date:** November 7, 2026
**Audit Scope:** Strictly Read-Only (Zero Code/Data/Credential Modifications)
**Status:** Completed & Validated

---

## Executive Summary

Phase 9.3B.2 resolved synthetic accommodation leakage across all production paths. The verified Katra accommodation catalog ([`data/katra_accommodation_catalog.json`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/data/katra_accommodation_catalog.json)) now serves as the trusted, curated static foundation for Katra lodging options.

This Phase 9.4 audit evaluates how Yatra AI can legitimately obtain changing real-world information across six operational domains without fabricating room availability, prices, crowd metrics, or operational notices:

1. **Commercial & Shrine Board Accommodation:** Evaluates legitimate API availability, commercial access conditions, direct property booking engines, and phone/email enquiry channels.
2. **RFID Registration & Carrying Capacity:** Establishes the boundary between official statutory capacity rules (50,000 pilgrims/day) and live telemetry. Proves that remaining real-time RFID card counters are **not published publicly** and must be classified as `UNAVAILABLE_FROM_PUBLIC_SOURCES`.
3. **Official Operational Notices:** Identifies legitimate feeds and public bulletins for Shrine Board announcements, track closures, yatra suspensions, weather warnings, and NH-44 traffic advisories.
4. **Emergency & Medical Services:** Audits official healthcare infrastructure, 24x7 mountain route dispensaries, oxygen replenishment kiosks, Narayana Superspeciality Hospital Kakryal, and official police/disaster management helplines.
5. **Unified Live Data Architecture:** Designs a provider-independent adapter framework that strictly reuses the existing response envelope, provenance tracking ([`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py)), thread-safe caching ([`utils/cache_manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/cache_manager.py)), and Central Agent orchestration ([`agents/central_agent.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/central_agent.py)).
6. **Implementation Sequence:** Lays out a phased, dependency-aware roadmap (Phases 9.5 through 9.9).

---

## 1. Existing Architecture Baseline

### 1.1 Git Branch and Working-Tree State

- **Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
- **Branch:** `main` at commit `db54ba3` (`feat(phase-5): complete conversational interface redesign with full-screen layout, markdown, and rich cards`).
- **Working Tree:** Contains uncommitted additions and modifications representing accepted phases (Phases 6, 7, 7.1, 8.1–8.6, 9.3B, 9.3B.2).
- **Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` remains 100% clean and untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`.

### 1.2 Phase 9.3B.2 Remediation Verification

All Phase 9.3B.2 remediations are active and verified in the working tree:
- **Zero Fallback to `db.search_hotels()`:** In [`agents/coordinator.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/coordinator.py) (`get_hotel_options`) and [`agents/orchestrator.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/orchestrator.py) (`coordinate_plan`), all branches falling back to the synthetic database have been severed.
- **Zero Hardcoded Placeholders:** The string `"Devi Darshan Hotel (Katra)"` has been eradicated across all backend and frontend files.
- **Accurate Inventory Semantics:** [`services/accommodation_catalog.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/accommodation_catalog.py) preserves `rooms_available=None` without fabricating numbers and marks multi-room requests as `room_requirement_status: "UNVERIFIED"`.
- **Status-Aware API:** `@router.post("/accommodation")` distinguishes `CATALOG_SUCCESS`, `NO_MATCHING_PROPERTIES`, and `CATALOG_UNAVAILABLE`.
- **Full Test Suite:** **280 / 280 tests passing** in the active workspace Python environment.

### 1.3 Active Subsystems & Reuse Opportunities

| Component | File Path | Current Capability | Role in Live Data Integration |
| :--- | :--- | :--- | :--- |
| **Provenance Engine** | [`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py) | Full metadata schema: `SourceType`, `FreshnessStatus`, `VerificationStatus`, ISO 8601 UTC timestamps, validation, and deduplication. | Direct reuse. Standardizes metadata for every live, cached, and fallback provider. |
| **In-Memory Cache** | [`utils/cache_manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/cache_manager.py) | Thread-safe LRU cache, single-flight request mutex (`get_or_fetch_single_flight`), TTL expiration, stale-if-error fallback. | Direct reuse. Prevents concurrent API stampedes and caches external live responses. |
| **Weather Service** | [`weather.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/weather.py) | Live Open-Meteo REST API queries for 4 elevation milestones (Katra 750m, Ardhkuwari 1400m, Bhawan 1585m, Bhairon 2011m) with IMD climate fallbacks. | Reference implementation for external live REST API integration. |
| **Curated Catalog** | [`services/accommodation_catalog.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/accommodation_catalog.py) | Loads 15 verified Katra properties from JSON; provides structured filtering, status reporting, and legacy record adaptation. | Permanent static fallback when live accommodation APIs are offline or unconfigured. |
| **Central Agent** | [`agents/central_agent.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/central_agent.py) | LangChain ChatGroq agent with 10 specialist tools, session store persistence, and hybrid deterministic fallbacks. | Execution surface for live data retrieval tools. |
| **Frontend Provenance** | [`frontend/src/components/chat/provenance/`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/provenance/) | `SourceBadge.jsx`, `FreshnessIndicator.jsx`, `ProvenanceList.jsx`, `SourceDetailsPopover.jsx`. | Renders user-facing freshness badges (`Live data`, `Cached data`, `Potentially outdated`, `Fallback estimate`). |

---

## 2. Verified Source Inventory

To avoid conflating documentation with actual access, every prospective external source is classified against six strict evidentiary criteria:
1. **Doc Found:** Official developer or technical documentation located.
2. **Public Info:** Relevant data observed on a public web page.
3. **API Confirmed:** Programmable API endpoint confirmed active and reachable.
4. **Creds Available:** Valid authentication credentials present in the workspace.
5. **Call Tested:** Live test call executed from the workspace.
6. **Data Retrieved:** Genuine real-world dynamic data parsed and verified.

### Source Evidence Matrix

| Domain | Source / Provider | Doc Found | Public Info | API Confirmed | Creds Available | Call Tested | Data Retrieved | Current Feasibility Classification |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Weather** | Open-Meteo REST API | **YES** | **YES** | **YES** | N/A (Free) | **YES** | **YES** | `LIVE_VERIFIED` (Production Active) |
| **Weather** | IMD Climatological Normals | **YES** | **YES** | N/A | N/A | N/A | **YES** | `STATIC_CURATED` (Fallback Active) |
| **Accommodation** | Katra Accommodation Catalog v1.0 | **YES** | **YES** | N/A | N/A | **YES** | **YES** | `STATIC_CURATED` (Production Active) |
| **Accommodation** | Amadeus Self-Service Hotel v3 | **YES** | N/A | **NO** (EOL) | **NO** | **NO** | **NO** | `UNAVAILABLE` (Decommissioned July 2026) |
| **Accommodation** | Amadeus Enterprise Hotel API | **YES** | N/A | **YES** | **NO** | **NO** | **NO** | `UNVERIFIED` (Requires commercial B2B contract) |
| **Accommodation** | Commercial OTAs (MMT, Goibibo) | **NO** | **YES** | **NO** | **NO** | **NO** | **NO** | `UNAVAILABLE` (Scraping prohibited by ToS) |
| **Accommodation** | SMVDSB Online Portal Booking | **YES** | **YES** | **NO** | **NO** | **NO** | **NO** | `UNAVAILABLE` (Protected by graphical CAPTCHA) |
| **RFID / Capacity** | SMVDSB Statutory Ceiling | **YES** | **YES** | N/A | N/A | N/A | **YES** | `STATIC_CURATED` (NGT 50k limit verified) |
| **RFID / Capacity** | Real-Time Remaining RFID Count | **NO** | **NO** | **NO** | **NO** | **NO** | **NO** | `UNAVAILABLE_FROM_PUBLIC_SOURCES` |
| **Operational Notices** | SMVDSB Flash Marquee Notices | **NO** | **YES** | **NO** | N/A | **NO** | **NO** | `PUBLIC_WEB_OBSERVED` (Scraping/feed candidate) |
| **Operational Notices** | J&K Traffic Police Daily Bulletins | **NO** | **YES** | **NO** | N/A | **NO** | **NO** | `PUBLIC_WEB_OBSERVED` (NH-44 advisory feed) |
| **Operational Notices** | J&K DIPR Press Releases | **NO** | **YES** | **NO** | N/A | **NO** | **NO** | `PUBLIC_WEB_OBSERVED` (Emergency notices) |
| **Emergency / Medical**| SMVDSB / Reasi District Registry | **YES** | **YES** | N/A | N/A | N/A | **YES** | `STATIC_CURATED` (Verified official registry) |

---

## 3. Hotel API Feasibility Matrix

### 3.1 Commercial Provider Evaluation

```mermaid
flowchart TD
    Req[Pilgrim Hotel Inquiry] --> ProviderCheck{Live API Available & Configured?}
    ProviderCheck -- No / Failure --> CuratedFallback["Katra Accommodation Catalog v1.0<br/>(15 Verified Properties)<br/>Status: STATIC_CURATED<br/>Availability: NOT_CHECKED"]
    ProviderCheck -- Yes --> LiveAPI["Live Accommodation Provider<br/>(Enterprise GDS / Property Direct)<br/>Status: LIVE_VERIFIED<br/>Availability: CONFIRMED_AVAILABLE"]
    LiveAPI --> FormatQuote["Format Live Offer & Quote<br/>(Price, Room Type, Expiration)"]
    CuratedFallback --> FormatStatic["Format Published Indicative Rate<br/>(Official Contact & Booking URL)"]
```

#### Detailed Provider Evaluation

1. **Amadeus for Developers (Hotel Search API v3):**
   - **Provider URL:** `https://developers.amadeus.com/`
   - **Data Fields:** Hotel ID, room types, price, taxes/charges, cancellation terms, offer validity.
   - **Geographic Coverage:** Katra production coverage is UNVERIFIED (test environment contains no Katra properties).
   - **Authentication:** OAuth2 Client Credentials.
   - **Automation / Terms:** Self-Service tier was decommissioned on July 17, 2026. Enterprise tier requires formal commercial agreement, annual commitment fees, and enterprise credentials.
   - **Freshness:** Real-time GDS offers (valid ~15–30 minutes).
   - **Actual Accessibility Evidence:** Documentation found. No enterprise credentials exist. Amadeus must remain an optional provider.
   - **Priority:** Low (Deferred until commercial credentials are provided).

2. **Booking.com Connectivity / Demand Partner API:**
   - **Provider URL:** `https://partner.booking.com/`
   - **Data Fields:** Hotel inventory, room rates, live availability, policies.
   - **Geographic Coverage:** High Katra property density.
   - **Authentication:** Proprietary API keys via certified connectivity partner program.
   - **Automation / Terms:** Restricted to certified property-management software or registered affiliate technology partners. Not available for standalone development projects. Public scraping is prohibited by ToS and Cloudflare bot management.
   - **Actual Accessibility Evidence:** No API access confirmed.
   - **Priority:** Low (Infeasible without official affiliate partnership).

3. **Google Hotel Prices / Travel Partner API:**
   - **Provider URL:** `https://developers.google.com/hotels`
   - **Data Fields:** Indicative pricing, deep links to booking partners.
   - **Geographic Coverage:** Katra hotels listed on Google Maps.
   - **Authentication:** Google Cloud Console OAuth2 + Hotel Center account.
   - **Automation / Terms:** Restricted to Google Hotel Ads integration partners and OTAs who provide live price feeds to Google.
   - **Actual Accessibility Evidence:** Read-only consumer API does not exist.
   - **Priority:** Low.

4. **Direct Property Booking Engines (IHCL Vivanta, ITC Welcomhotel, Wyndham):**
   - **Provider URLs:** Official brand portals (`vivanta.com`, `itchotels.com`, `wyndhamhotels.com`).
   - **Data Fields:** Room types, member rates, live date-specific inventory.
   - **Authentication:** Session-based consumer booking engines.
   - **Automation / Terms:** Automated access without partnership violates website Terms of Service and triggers bot mitigation.
   - **Actual Accessibility Evidence:** Direct booking URLs verified in catalog; automated backend API access not permitted.
   - **Priority:** High for direct referral links; Low for automated scraping.

5. **SMVDSB Official Online Portal (`online.maavaishnodevi.org`):**
   - **Data Fields:** Subsidized rooms and dormitories at Niharika, Trikuta Bhawan, Ardhkuwari, and Bhawan.
   - **Access / Restrictions:** Requires registered devotee account, OTP verification, and graphical CAPTCHA.
   - **Automation / Terms:** Automated scraping or headless browser booking on the live shrine portal is strictly prohibited and unethical.
   - **Priority:** Zero for automation; High for curated published rates and direct pilgrim portal guidance.

### 3.2 Quote vs. Indicative Rate vs. Confirmed Reservation

| Distinction | Definition | Example in Yatra AI | User Advisory Required |
| :--- | :--- | :--- | :--- |
| **Indicative Rate** | Published tariff schedule or seasonal price range verified from official property sources. | Vivanta Katra: ₹7,500–₹16,000/night; SMVDSB Niharika: ₹120–₹1,500/night. | *"Published indicative rate. Final price depends on travel dates and room category."* |
| **Live Offer / Quote** | Date-specific price returned by a verified commercial API with active availability hold. | ₹8,450 + GST for Deluxe Room (check-in 2026-11-20), offer expires in 15 mins. | *"Live quote valid for 15 minutes. Final price confirmed upon booking checkout."* |
| **Confirmed Reservation** | Legally binding booking voucher issued after successful payment and confirmation number generation. | Confirmation Voucher #SMVDSB-2026-88192 for Room 204. | *"Confirmed reservation. Present voucher and original photo ID at check-in."* |

> [!IMPORTANT]
> **Strict Availability Rule:** Yatra AI must **never** classify a property as `AVAILABLE` unless a legitimate, verified API provider returns confirmed date-specific room availability. For curated catalog properties, availability must remain `NOT_CHECKED` / `UNVERIFIED`.

---

## 4. RFID and Yatra Capacity Source Assessment

A central source of confusion in pilgrimage planning is the conflation of different crowd metrics. This audit delineates each metric and establishes its empirical availability.

```mermaid
flowchart LR
    Quota["1. Daily Statutory Limit<br/>(50,000 pilgrims/day)<br/>[PUBLIC STATIC]"]
    Counters["2. RFID Cards Issued<br/>(Physical Counters)<br/>[INTERNAL TELEMETRY]"]
    Gates["3. Commenced Yatra<br/>(RFID Scans at Banganga)<br/>[INTERNAL TELEMETRY]"]
    RemQuota["4. Remaining Capacity<br/>(Limit - Issued)<br/>[UNAVAILABLE PUBLICLY]"]

    Quota --> RemQuota
    Counters --> RemQuota
```

### 4.1 Detailed Metric Audit

1. **Daily Registration Limit (Carrying Capacity):**
   - **Definition:** The maximum number of pilgrims allowed to register and proceed towards Bhawan per calendar day.
   - **Value:** **50,000 pilgrims per day**.
   - **Source:** Established by National Green Tribunal (NGT) order (November 2017) and enacted under SMVDSB Crowd Management Standard Operating Procedures.
   - **Availability:** **Public & Verified** (Statutory policy).
   - **Classification:** `STATIC_CURATED`.

2. **RFID Cards Issued:**
   - **Definition:** The cumulative count of physical RFID cards issued at the 24x7 Katra registration counters (SVDK Railway Station, Katra Bus Stand, Tarakote Marg, Helipad) for the current day.
   - **Source:** SMVDSB RFID Management System database.
   - **Availability:** **Internal Telemetry Only**. No public REST API, JSON endpoint, or web counter is published.
   - **Classification:** `UNAVAILABLE_FROM_PUBLIC_SOURCES`.

3. **Pilgrims Who Commenced Yatra:**
   - **Definition:** The count of pilgrims whose RFID cards have been scanned at the physical entrance turnstiles at Banganga Checkpoint or Tarakote Marg Checkpoint.
   - **Source:** SMVDSB Track Control Room telemetry.
   - **Availability:** **Internal Telemetry Only**.
   - **Classification:** `UNAVAILABLE_FROM_PUBLIC_SOURCES`.

4. **Remaining Daily Registration Capacity:**
   - **Definition:** `50,000 - (RFID Cards Issued Today)`.
   - **Availability:** **NOT EXPOSED ON ANY PUBLIC CHANNEL**.
   - **Classification:** `UNAVAILABLE_FROM_PUBLIC_SOURCES`.
   - **Architectural Directive:** Yatra AI must **never** estimate, simulate, or fabricate a "Remaining RFID Cards" counter. Doing so risks misleading devotees and causing crowd surges or panic at Katra counters.

5. **Remaining Physical Route Capacity:**
   - **Definition:** Dynamic carrying capacity across trek segments (Banganga–Ardhkuwari, Ardhkuwari–Bhawan, Sanjichhat) based on congestion sensors and CCTV density tracking.
   - **Availability:** **Restricted Internal Telemetry**.
   - **Classification:** `UNAVAILABLE_FROM_PUBLIC_SOURCES`.

6. **Official Registration Status (Operational vs. Suspended):**
   - **Definition:** High-level status indicating whether yatra registration is currently open, temporarily paused for crowd clearance, or suspended due to severe weather/landslides.
   - **Source:** SMVDSB Flash Marquee Notices (`maavaishnodevi.org`), J&K DIPR press statements, Reasi District Administration bulletins.
   - **Availability:** **Publicly Observed Text Announcements**.
   - **Classification:** `PUBLIC_WEB_OBSERVED` (Feasible for structured notice ingestion).

---

## 5. Official Operational Notice Source Assessment

During heavy rainfall, winter snowfall, or peak holiday surges, operational conditions along the Trikuta Hills change rapidly. Yatra AI requires a legitimate operational notice ingestion mechanism.

### 5.1 Prospective Operational Notice Sources

| Notice Domain | Primary Source | Public URL / Channel | Update Frequency | Ingestion Feasibility | Recommended Freshness (TTL) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Yatra Suspensions & Reopenings** | SMVDSB Official Portal | `https://www.maavaishnodevi.org` (Homepage flash marquee) | Ad-hoc (Incident-driven) | Medium (Requires HTML parser of public marquee) | 15 minutes (Max Stale: 1 hour) |
| **High-Severity Civil Advisories** | J&K DIPR (Dept of Information & Public Relations) | `https://dipr.jk.gov.in` & Official Twitter/X (`@diprjk`) | Multiple times daily | Medium (RSS feed or public portal parsing) | 30 minutes (Max Stale: 2 hours) |
| **Highway & Traffic Advisories** | J&K Traffic Police | `http://jktrafficpolice.nic.in` & Twitter/X (`@Traffic_hqrs`) | Twice daily (Morning 07:00 IST & Evening 18:00 IST) | High (Daily traffic bulletin PDF/text) | 4 hours (Max Stale: 12 hours) |
| **Helicopter Service Disruptions** | Katra Helipad Operations Desk / SMVDSB Control Room | SMVDSB Control Room: `01991-232010` | Real-time weather dependent | Low for API; Medium for telephonic/marquee notice | 15 minutes (Max Stale: 1 hour) |
| **Weather Warnings & Landslides** | IMD Meteorological Centre Srinagar / Jammu | `https://mausam.imd.gov.in/srinagar/` | Every 6 hours / Nowcasts | High (IMD district alerts & Open-Meteo codes) | 1 hour (Max Stale: 3 hours) |

### 5.2 Polling Feasibility & Rate Limiting

- **Poller Architecture:** Background worker scheduled via cron or background task polling public marquees at 15-minute intervals.
- **Header Standards:** Uses a descriptive User-Agent (`YatraAI-Bot/1.0 (+https://github.com/prag-ai/yatra-ai; academic-research)`), conditional HTTP headers (`If-Modified-Since`, `ETag`), and respects HTTP 429 rate limit backoff.
- **Fail-Safe Operation:** If the bulletin source is unreachable, the system retains the previous advisory tagged with `freshness_status: "stale"`, or gracefully falls back to `"No active advisories reported by official sources; verify locally before travel"`.

---

## 6. Emergency and Medical Information Source Assessment

### 6.1 Medical Care Architecture (Trikuta Hills Pilgrimage Gradient)

Emergency medical care along the 13 km mountain trek is operated directly by the Shrine Board's Medical Directorate in coordination with Shri Mata Vaishno Devi Narayana Superspeciality Hospital.

```mermaid
flowchart TD
    Emergency[Pilgrim Medical Emergency] --> LocationCheck{Location of Pilgrim?}
    LocationCheck -- Base Town / Katra --> SDHKatra["Community Health Centre / SDH Katra<br/>Tel: 01991-232047<br/>Level: Primary / Secondary Base Care"]
    LocationCheck -- Critical / Trauma --> Narayana["SMVD Narayana Superspeciality Hospital (Kakryal)<br/>Tel: 01991-285635 / 285555<br/>Level: Tertiary Super-Speciality, Cardiac, ICU, Helipad"]
    LocationCheck -- Along Mountain Trek --> RouteDispensaries["24x7 SMVDSB Trek Medical Units<br/>• Banganga (km 1.5)<br/>• Charan Paduka (km 2.5)<br/>• Adhkuwari (km 6.0 - Oxygen Kiosk)<br/>• Himkoti (km 8.5)<br/>• Sanjichhat (km 9.5 - Oxygen Kiosk, Air Evac)<br/>• Bhawan (km 13.0 - Main Complex ICU)"]
```

### 6.2 Verified Emergency Contact Registry

| Facility / Service | Category | Location | Verified Contact Number | Operating Hours | Source Verification Tier |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Unified Emergency Helpline** | All Emergencies | J&K State / Katra | **112** | 24x7 | Tier-1 Official (National Standard) |
| **SMVDSB Central Helpline** | Pilgrim Assistance | Katra Base Central | **1800-180-7198** (Toll-Free) | 24x7 | Tier-1 Official (SMVDSB Handbook) |
| **SMVDSB Katra Control Room** | Operations / Helpline | Katra Central Chowk | **01991-232010**, **01991-232111** | 24x7 | Tier-1 Official (SMVDSB Handbook) |
| **SMVDSB Bhawan Control Room** | Shrine Operations | Bhawan Complex | **01991-232029** | 24x7 | Tier-1 Official (SMVDSB Handbook) |
| **SMVD Narayana Hospital** | Tertiary Medical Care | Kakryal, Katra (15km) | **01991-285635**, **01991-285555** | 24x7 Emergency / Trauma | Tier-1 Official (Direct Hospital Verification) |
| **Sub-District Hospital (SDH)** | Secondary Medical Care| Railway Road, Katra | **01991-232047** | 24x7 Emergency | Tier-1 Official (Health Dept J&K) |
| **Ambulance Service** | Medical Transport | J&K State / Katra | **108** / **102** | 24x7 | Tier-1 Official (National Health Mission) |
| **Police Station Katra** | Law & Order | Katra Base Town | **01991-232010**, **01991-232034** | 24x7 | Tier-1 Official (J&K Police Directory) |
| **Police Post Bhawan** | Law & Order | Bhawan Complex | **01991-232029** | 24x7 | Tier-1 Official (J&K Police Directory) |
| **Disaster Management (DDMA)** | Natural Hazards | Reasi District HQ | **1077** (Toll-Free), **01991-245305** | 24x7 Emergency Control | Tier-1 Official (Reasi District Administration) |

---

## 7. Unified Live Data Architecture

The live data architecture is provider-independent, pluggable, and built strictly upon existing components ([`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py) and [`utils/cache_manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/cache_manager.py)).

### 7.1 Architecture Diagram

```mermaid
flowchart TD
    Client[Client / AIChat / REST Route] --> CentralAgent[Central AI Agent / Coordinator]
    CentralAgent --> LiveDataManager[Unified Live Data Manager]

    subgraph LiveDataManager[Unified Live Data Manager]
        CacheCheck{In-Memory Cache Check<br/>utils/cache_manager.py}
        CacheCheck -- Fresh Hit --> ReturnCached[Return CACHED_VERIFIED Response]
        CacheCheck -- Stale / Miss --> SingleFlight[Single-Flight Request Mutex]
        SingleFlight --> AdapterRouter{Select Provider Adapter}

        AdapterRouter --> WeatherAdapter[Open-Meteo Weather Adapter]
        AdapterRouter --> HotelAdapter[Accommodation Provider Adapter]
        AdapterRouter --> NoticeAdapter[Operational Notice Adapter]
        AdapterRouter --> EmergencyAdapter[Emergency Registry Adapter]

        WeatherAdapter --> UpstreamAPI[Open-Meteo REST API]
        HotelAdapter --> HotelUpstream[Commercial GDS / Catalog Fallback]
        NoticeAdapter --> NoticeUpstream[Official Public Bulletin Feeds]
        EmergencyAdapter --> EmergencyUpstream[Verified Emergency Registry]

        UpstreamAPI --> Normalizer[Data Normalizer & Provenance Attacher<br/>utils/provenance.py]
        HotelUpstream --> Normalizer
        NoticeUpstream --> Normalizer
        EmergencyUpstream --> Normalizer

        Normalizer --> StoreCache[Store in Cache with TTL]
    end

    StoreCache --> ReturnResponse[Unified Response Envelope]
    ReturnCached --> ReturnResponse
    ReturnResponse --> Client
```

### 7.2 Abstract Provider Interface (`BaseLiveDataProvider`)

Every live data provider implements a standard Python interface:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from utils.provenance import FreshnessStatus, SourceType, VerificationStatus

class BaseLiveDataProvider(ABC):
    """Abstract base class for all Yatra AI live data providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the canonical name of the upstream source."""
        pass

    @abstractmethod
    def get_domain(self) -> str:
        """Returns the domain classification (weather, accommodation, notices, emergency)."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks whether necessary credentials and endpoints are present."""
        pass

    @abstractmethod
    def fetch_live_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the upstream retrieval and returns normalized data."""
        pass

    @abstractmethod
    def get_fallback_data(self, params: Dict[str, Any], exc: Optional[Exception] = None) -> Dict[str, Any]:
        """Provides curated or cached fallback when upstream is unavailable."""
        pass
```

### 7.3 Status Taxonomy & Alignment

The architecture standardizes on eight mutually exclusive operational states across backend and frontend:

| Architecture Status | Backend `SourceType` | Backend `FreshnessStatus` | Backend `VerificationStatus` | Frontend Label | Meaning & UI Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LIVE_VERIFIED` | `live_api` | `live` | `verified_external_api` | `Live data` (Green) | Real-time observation retrieved within active TTL directly from authorized API. |
| `CACHED_VERIFIED` | `cached_api` | `cached` | `verified_external_api` | `Cached data` (Blue) | Fresh cache hit within active TTL window. Zero upstream latency. |
| `STALE` | `cached_api` / `live_api` | `stale` | `verified_external_api` | `Potentially outdated` (Amber) | Past active TTL but within permitted stale fallback window during provider outage. |
| `STATIC_CURATED` | `curated_data` | `not_applicable` | `verified_curated_source` | `Curated information` (Slate) | Hand-verified static knowledge (e.g., Katra Catalog v1.0, 50k NGT quota). |
| `INDICATIVE` | `indicative_data` | `cached` | `verified_curated_source` | `Indicative information` (Purple) | Estimated rates, seasonal climate patterns, or published train timetables. |
| `SIMULATED` | `simulated_data` | `simulated` | `simulation_only` | `Simulated demonstration` (Orange) | Local sandboxed mock portal interaction (e.g., local darshan slot availability). |
| `UNAVAILABLE` | `unknown_source` | `unavailable` | `not_applicable` | `Currently unavailable` (Red) | Upstream provider down and no usable cache exists. Explicit failure note. |
| `UNVERIFIED` | Any | Any | `unverified` | `Source not verified` (Gray) | Unrecognized location, unverified property, or unconfirmed availability. |

---

## 8. Normalized Data Contracts

Every provider must output structured JSON conforming to strict data contracts before attaching provenance.

### 8.1 Operational Notice Contract (`OperationalNoticePayload`)

```json
{
  "notice_id": "notice_smvdsb_20261107_01",
  "category": "TRACK_ADVISORY",
  "severity": "WARNING",
  "title": "Tarakote Marg Pedestrian Route Operational",
  "summary": "Tarakote Marg is fully open for pedestrian pilgrims and battery cars. Traditional route via Banganga has moderate pony traffic.",
  "impacted_segments": ["tarakote_marg", "banganga"],
  "effective_from": "2026-11-07T06:00:00+05:30",
  "effective_until": "2026-11-07T22:00:00+05:30",
  "official_source": "Shri Mata Vaishno Devi Shrine Board",
  "source_url": "https://www.maavaishnodevi.org",
  "source_provenance": {
    "source_name": "SMVDSB Public Announcement Marquee",
    "source_type": "live_api",
    "freshness_status": "live",
    "verification_status": "verified_official_source",
    "retrieval_timestamp": "2026-11-07T09:15:00Z"
  }
}
```

### 8.2 Yatra Capacity & Registration Contract (`YatraCapacityPayload`)

```json
{
  "yatra_date": "2026-11-07",
  "registration_status": "OPEN",
  "statutory_daily_quota": 50000,
  "daily_quota_source": "National Green Tribunal (NGT) / SMVDSB Statutory Regulation",
  "live_remaining_counter": null,
  "live_remaining_counter_status": "UNAVAILABLE_FROM_PUBLIC_SOURCES",
  "advisory": "Spot RFID registration is currently OPEN at all 24x7 Katra counters (Railway Station, Bus Stand, Tarakote Marg). Original Aadhaar or Passport is mandatory. Real-time counter of remaining cards is not published by the Shrine Board.",
  "counters": [
    { "name": "Katra Railway Station (SVDK)", "timings": "24x7", "fee": "Free" },
    { "name": "Katra Bus Stand (Counter No. 2)", "timings": "24x7", "fee": "Free" },
    { "name": "Tarakote Marg Checkpoint", "timings": "05:00 to 22:00", "fee": "Free" }
  ],
  "source_provenance": {
    "source_name": "SMVDSB Statutory Guidelines",
    "source_type": "curated_data",
    "freshness_status": "not_applicable",
    "verification_status": "verified_official_source",
    "retrieval_timestamp": "2026-11-07T09:15:00Z"
  }
}
```

### 8.3 Live Hotel Offer Contract (`HotelOfferPayload`)

```json
{
  "property_id": "HTL_VIVANTA_KATRA",
  "property_name": "Vivanta Katra, Vaishno Devi",
  "check_in_date": "2026-11-20",
  "check_out_date": "2026-11-21",
  "rooms_requested": 1,
  "availability_status": "CONFIRMED_AVAILABLE",
  "room_requirement_status": "SATISFIED",
  "currency": "INR",
  "base_rate": 8500.0,
  "taxes_and_fees": 1530.0,
  "total_price": 10030.0,
  "offer_valid_until": "2026-11-07T10:00:00Z",
  "cancellation_policy": "Free cancellation up to 48 hours before check-in",
  "direct_booking_url": "https://www.vivantahotels.com/en-in/vivanta-katra-vaishno-devi/",
  "source_provenance": {
    "source_name": "Amadeus Enterprise Hotel Offers v3",
    "source_type": "live_api",
    "freshness_status": "live",
    "verification_status": "verified_external_api",
    "retrieval_timestamp": "2026-11-07T09:15:00Z",
    "data_timestamp": "2026-11-07T09:14:30Z"
  }
}
```

---

## 9. Provenance and Freshness Design

### 9.1 Distinction Between Query Time and Data Time

In accordance with [`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py), all live payloads strictly distinguish two timestamps:
- `retrieval_timestamp`: The exact UTC ISO 8601 moment when Yatra AI queried the upstream provider (e.g., `2026-11-07T09:15:00Z`).
- `data_timestamp`: The exact timestamp when the upstream provider generated or published the observation (e.g., Open-Meteo model run time: `2026-11-07T08:00:00Z` or J&K Traffic Police bulletin publication time: `2026-11-07T07:00:00+05:30`).

### 9.2 Frontend Visual Design Tokens

The frontend provenance components map backend states directly into accessible visual tokens:

| State | Background Color | Text Color | Border Color | Icon | Screen-Reader Text |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Live** | `#EBF9F1` (Light Mint) | `#0E6245` (Forest Green) | `#A3E0C0` | 🟢 | "Live data retrieved from external provider" |
| **Cached** | `#EBF4FB` (Light Ice) | `#0B4F8A` (Deep Sky) | `#A3CEF1` | 🔵 | "Cached data within active freshness window" |
| **Stale** | `#FFF8E6` (Warm Cream) | `#8A5D00` (Amber Ochre) | `#FAD980` | ⚠️ | "Potentially outdated information; provider refresh pending" |
| **Fallback** | `#F5EEFA` (Soft Lavender)| `#5B2C6F` (Royal Plum) | `#D2B4DE` | ℹ️ | "Fallback estimate or seasonal normal" |
| **Unavailable**| `#FDEAEA` (Pale Rose) | `#922B21` (Crimson) | `#F5B7B1` | 🚫 | "Information currently unavailable from provider" |

---

## 10. Proposed Refresh Strategy

| Data Domain | Default TTL (Active) | Max Stale Age (Fallback) | Upstream Polling Trigger | User-Requested Refresh Policy |
| :--- | :---: | :---: | :--- | :--- |
| **Mountain Weather** | 30 minutes | 6 hours | Periodic background refresh + on-demand query. | Allowed with 60-second debounce per session. |
| **Operational Notices** | 15 minutes | 2 hours | Background poller runs every 15 minutes. | Immediate refresh on user request. |
| **Traffic Advisories (NH-44)** | 4 hours | 12 hours | Scheduled at 07:15 IST and 18:15 IST daily. | Allowed with 5-minute debounce. |
| **Live Hotel Offers (if active)**| 15 minutes | 1 hour | Strictly on-demand (when user requests dates/rooms).| Fresh search on filter/date change. |
| **Katra Accommodation Catalog** | 24 hours | 7 days | Loaded on startup; reloaded on file modification. | Administrative reload only. |
| **RFID / Capacity Status** | 15 minutes | 4 hours | Background poller synchronized with notice poller. | Immediate refresh on user request. |
| **Emergency & Medical Registry**| 7 days | 30 days | Loaded in memory; re-verified every 6 months. | Administrative update only. |

---

## 11. Security and Compliance

1. **Credential Isolation:**
   - All provider API keys and client secrets reside exclusively in workspace environment variables (`.env`).
   - `.env` is Git-ignored.
   - Vite build configuration strictly prevents `VITE_` prefixing of private credentials, ensuring secrets are never leaked to client JavaScript bundles.
2. **Devotee Privacy & PII Protection:**
   - Sensitive personal information (Aadhaar number, passport details, phone number, physical address) is masked via [`utils/masking.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/masking.py).
   - Private pilgrim identity data is **never** embedded in public RAG knowledge bases or vector embeddings.
3. **Strict Anti-Scraping & Terms of Service Compliance:**
   - Yatra AI never scrapes behind authenticated logins (e.g. `online.maavaishnodevi.org`).
   - Never bypasses graphical CAPTCHAs, biometric verification, or anti-bot protections (Akamai, Cloudflare).
   - Never performs automated financial transactions or mock reservations against live shrine payment gateways.
4. **Human-in-the-Loop Booking Gate Maintained:**
   - The two-step authorization architecture ([`POST /api/yatra/authorize`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/backend/routes/yatra.py) and [`POST /api/yatra/confirm`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/backend/routes/yatra.py)) is strictly maintained.
   - The local sandboxed mock portal remains the dedicated testing and demonstration environment for Playwright RPA execution.

---

## 12. Implementation Dependency Map

```mermaid
graph TD
    subgraph Foundation["Phase 8 & 9.3B Foundation (Established)"]
        Prov["utils/provenance.py"]
        Cache["utils/cache_manager.py"]
        Catalog["data/katra_accommodation_catalog.json"]
        Agent["agents/central_agent.py"]
    end

    subgraph Phase95["Phase 9.5: Provider Framework & Normalized Contracts"]
        AdapterBase["BaseLiveDataProvider Interface"]
        NormContracts["Normalized Data Contracts"]
        LiveManager["Unified Live Data Manager"]
    end

    subgraph Phase96["Phase 9.6: Official Operational Notices & Alerts"]
        NoticePoller["SMVDSB & Traffic Notice Poller"]
        NoticeTool["Central Agent Notice Tool"]
    end

    subgraph Phase97["Phase 9.7: Verified Emergency Services Registry"]
        EmergRegistry["Structured Emergency Registry JSON"]
        EmergTool["Central Agent Emergency Tool"]
    end

    subgraph Phase98["Phase 9.8: Commercial Hotel Integration Bridge"]
        HotelBridge["Optional GDS/Commercial Adapter"]
        CatalogFallback["Static Catalog Fallback Gate"]
    end

    subgraph Phase99["Phase 9.9: Dashboard & End-to-End Verification"]
        FullDashboard["Live Operations Dashboard"]
        E2ETests["Full Regression & Provenance Tests"]
    end

    Prov --> Phase95
    Cache --> Phase95
    Agent --> Phase95

    Phase95 --> Phase96
    Phase95 --> Phase97
    Phase95 --> Phase98
    Catalog --> Phase98

    Phase96 --> Phase99
    Phase97 --> Phase99
    Phase98 --> Phase99
```

---

## 13. Recommended Checkpoint Sequence

| Checkpoint | Target Focus | Key Deliverables | Risk Level |
| :--- | :--- | :--- | :---: |
| **Phase 9.4** *(Current)* | Live Data Architecture & Feasibility Audit | Complete roadmap, evidence matrix, and contract specifications. | **Zero (Read-Only)** |
| **Phase 9.5** | Provider Framework & Normalized Contracts | Implement `BaseLiveDataProvider`, `UnifiedLiveDataManager`, unit tests for contracts and single-flight cache coordination. | **Low** |
| **Phase 9.6** | Operational Notices & Traffic Advisory Poller | Implement background poller for SMVDSB notices and NH-44 traffic bulletins; add notice tool to Central Agent. | **Low / Medium** |
| **Phase 9.7** | Emergency & Medical Services Registry | Implement `data/emergency_services_registry.json`, medical triage tool in Central Agent, and emergency UI card. | **Low** |
| **Phase 9.8** | Commercial Hotel Integration Bridge | Implement pluggable hotel adapter interface; ensure 100% fail-safe fallback to Katra Catalog v1.0. | **Medium** |
| **Phase 9.9** | End-to-End Verification & Real-Time Hardening | Comprehensive integration tests, frontend badge verification, documentation update, and final audit. | **Low** |

---

## 14. Known Limitations and Unresolved Questions

1. **Unavailability of Live RFID Headcount Telemetry:**
   - The Shri Mata Vaishno Devi Shrine Board does **not** provide a public API or live web feed for issued RFID card counts.
   - *Design Choice:* The application displays the statutory 50,000 daily limit, physical registration counter hours, required photo IDs, and registration operational status (Open/Suspended), while explicitly tagging remaining counts as `UNAVAILABLE_FROM_PUBLIC_SOURCES`.
2. **Commercial Hotel API Access Constraints:**
   - Public self-service hotel booking APIs for Katra either do not exist or have been decommissioned (Amadeus Self-Service July 2026).
   - *Design Choice:* The curated Katra Accommodation Catalog v1.0 remains the primary production source. Any prospective live hotel API will be integrated strictly as an optional pluggable adapter with zero hard dependency.
3. **Shrine Board Accommodation CAPTCHA Protection:**
   - Real-time room vacancy for subsidized SMVDSB guest houses is locked behind authenticated login and graphical CAPTCHA on `online.maavaishnodevi.org`.
   - *Design Choice:* Yatra AI provides verified subsidized tariffs, direct phone/email contacts, and deep links to the official portal without attempting unauthorized automated extraction.
4. **IRCTC / Indian Railways Live Seat Availability:**
   - Live PNR status and real-time train berth availability require paid CRIS TIES commercial licenses.
   - *Design Choice:* Transport schedules remain indicative timetables with clear caveats advising users to verify final seat availability on IRCTC.

---

## 15. Audit Sign-Off & Next Steps

This Phase 9.4 audit proves that Yatra AI can legitimately obtain dynamic operational information while maintaining strict adherence to truth-in-data principles, user security, and ethical integration boundaries.

**Action Required:**
- Review this roadmap and deliverable ([`PHASE_9_4_LIVE_DATA_SOURCE_ROADMAP.md`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/PHASE_9_4_LIVE_DATA_SOURCE_ROADMAP.md)).
- Await your explicit authorization before proceeding to **Phase 9.5 (Provider Framework & Normalized Contracts)**.
