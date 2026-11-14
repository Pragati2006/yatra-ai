# PHASE 9.6.1 — OFFICIAL OPERATIONAL NOTICES & TRAFFIC SOURCE FEASIBILITY AUDIT

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `yatra-ai`
**Branch:** `main`
**Current Baseline Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Backup Repository:** `yatra-booking-agent` (Strictly untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`)
**Python Runtime:** Python 3.12.4 (`venv`)
**Audit Date:** November 7, 2026
**Audit Mode:** Strictly READ-ONLY Feasibility Audit
**Phase Status:** Architecture & Source Feasibility Complete (Phase 9.6.1)

---

## 1. Executive Summary & Audit Mandate

This report documents the **Phase 9.6.1 Official Operational Notices & Traffic Source Feasibility Audit** for the Yatra AI system.

### Objective
To conduct a strictly read-only technical and source-feasibility investigation to identify reliable, authorized, and sustainable sources for retrieving:
1. **Vaishno Devi Yatra Operational Notices:** Track closures, yatra suspensions/resumptions, RFID registration pauses, battery car/ropeway/helicopter status, and official Shrine Board directives.
2. **Jammu & Kashmir Highway & Traffic Advisories:** NH-44 highway status, traffic plans, cut-off timings (Nagrota, Jakheni/Udhampur, Ramban, Qazigund), vehicle movement restrictions, convoy movements, and landslide disruptions.

### Critical Truth-in-Data Baseline Finding
The audit reveals that **no official, public, machine-readable REST API or structured RSS feed currently exists** from either the Shri Mata Vaishno Devi Shrine Board (SMVDSB) or the Jammu & Kashmir Traffic Police. All official government operational communications are disseminated through public server-rendered HTML pages (`.aspx` / `.html`), static PDF circulars, official press releases, and social media channels.

Consequently, any future implementation (Phase 9.6.2) must be designed as an **authorized, conservative, fault-tolerant public document poller** with strict deduplication, content hashing, and unambiguous lifecycle status tracking.

---

## 2. Official Source Discovery & Technical Investigation

### 2.1 Candidate A: Shri Mata Vaishno Devi Shrine Board (SMVDSB) Main Portal
- **Organization:** Shri Mata Vaishno Devi Shrine Board (Statutory Autonomous Body established under J&K SMVDSB Act 1988).
- **Official URL:** `https://www.maavaishnodevi.org/`
- **Key Sub-pages:**
  - Public Notices & Circulars: `https://www.maavaishnodevi.org/public-notices.aspx`
  - Homepage Marquee / Ticker: `https://www.maavaishnodevi.org/index.aspx`
  - General Yatra Guidelines: `https://www.maavaishnodevi.org/yatra-guidelines.aspx`
- **Information Published:**
  - Yatra operational status ("Running smoothly", suspended, or resumed).
  - Track closures (Traditional Banganga-Adhkuwari-Bhawan route vs. Tarakote Marg).
  - Facility operational status (Battery car service, Bhawan-Bhairon ropeway, Sanjichhat helipad operations).
  - RFID Yatra Access Card registration counters and daily capacity announcements.
  - Advisory warnings against fraudulent third-party booking agents.
- **Technical Architecture & Format:**
  - **Platform:** Microsoft ASP.NET WebForms (`.aspx`), running on IIS with NIC / State Data Centre infrastructure.
  - **Delivery Format:** Server-rendered HTML with embedded table lists linking to static downloadable `.pdf` documents.
  - **Homepage Marquee:** A client-rendered HTML `<marquee>` / JavaScript ticker displaying brief one-line status updates.
- **Technical Limitations & Risks:**
  - *No Structured API:* There is no JSON/XML/REST endpoint or RSS feed.
  - *Marquee Instability:* The homepage ticker is a presentation artifact prone to unannounced DOM changes, styling refactors, and lacks publication timestamps or machine-readable notice IDs.
  - *Security & Infrastructure:* Protected by state government Web Application Firewalls (WAF) and NIC security policies. High-frequency automated polling risks IP rate-limiting or CAPTCHA challenges.
- **Access Controls & Authentication:**
  - Public informational pages require no authentication or credentials.
  - `robots.txt` permits general web crawling of public informational sections while excluding administrative directories.

---

### 2.2 Candidate B: SMVDSB Online Services Portal
- **Organization:** Shri Mata Vaishno Devi Shrine Board (Online IT Wing).
- **Official URL:** `https://online.maavaishnodevi.org/`
- **Purpose:** Transactional portal for pilgrim account creation, RFID registration slots, helicopter ticket booking, room accommodation, and online pooja bookings.
- **Technical Architecture & Access Controls:**
  - Highly secure, session-state-dependent transactional web application.
  - Enforces mandatory user login, Mobile OTP verification, and image-based CAPTCHA verification.
  - Employs strict CSRF tokens and rate-limiting to prevent ticket scalping and automated bot reservations.
- **Audit Finding & Policy Decision:**
  - **STRICTLY UNSUITABLE & PROHIBITED FOR AUTOMATED POLLING.**
  - Attempting to scrape or automate `online.maavaishnodevi.org` would violate the Shrine Board's terms of service, trigger automated IP blocks, and breach security and privacy boundaries.
  - Public operational notices are already duplicated on the public informational portal (`www.maavaishnodevi.org`). The transactional portal must not be touched by any poller.

---

### 2.3 Candidate C: Jammu & Kashmir Traffic Police Headquarters
- **Organization:** Traffic Police Headquarters, Jammu & Kashmir (J&K Police Department, UT of J&K).
- **Official URL:** `https://trafficpolice.jk.gov.in/`
- **Key Information Published:**
  - **Daily Traffic Plans:** Published daily in the evening (typically 18:00–21:00 IST) detailing vehicular movement permissions on NH-44 for the following calendar day.
  - **NH-44 Sector Details:** Specifies whether Light Motor Vehicles (LMVs) and Heavy Motor Vehicles (HMVs) can move from Jammu &rarr; Srinagar or Srinagar &rarr; Jammu (one-way convoy regulations).
  - **Cut-off Timings:** Strict passage deadlines at Nagrota (Jammu), Jakheni (Udhampur), Qazigund, and Navyug Tunnel.
  - **Disruption Bulletins:** Real-time road closures caused by landslides, shooting stones, mudslides (especially in the Ramban–Banihal sector: Mehar, Cafeteria Morh, Panthyal, Dalwas), or snow accumulation.
  - **Traffic Control Unit (TCU) Contact Helplines:** TCU Jammu (`0191-2459048`), TCU Ramban (`9419993745`), TCU Srinagar (`0194-2450022`), Helpline `103`.
- **Technical Architecture & Format:**
  - Government web portal hosted on National Informatics Centre (NIC) J&K state servers.
  - Format: Unstructured HTML news items, scanned JPEG circulars, or PDF press releases.
  - Social Dissemination: The department also broadcasts real-time updates via official social media (`@Traffic_hqrsJK` on X).
- **Technical Limitations & Risks:**
  - *No Structured API:* No public REST API or RSS feed.
  - *Social Platform Constraints:* Accessing X (Twitter) programmatically is heavily constrained by enterprise API paywalls ($100/mo minimum tier) and terms forbidding unauthenticated scraping.
  - *Server Availability:* State NIC servers occasionally experience transient connection drops or slow response times during severe weather events.

---

### 2.4 Candidate D: Jammu & Kashmir DIPR (Directorate of Information & Public Relations)
- **Organization:** Department of Information & Public Relations, Government of Jammu & Kashmir.
- **Official URL:** `https://dipr.jk.gov.in/`
- **Key Information Published:**
  - Official government press bulletins, cabinet decisions, and emergency announcements from District Magistrates (e.g., DM Reasi, DM Jammu).
- **Audit Finding & Policy Decision:**
  - **SECONDARY DISSEMINATION CHANNEL (NOT ORIGINAL AUTHORITY):**
  - DIPR does not operate the Yatra or manage highway traffic. When DIPR posts *"Yatra suspended due to inclement weather"*, it is republishing a directive issued by the SMVDSB CEO or District Administration.
  - *Latency:* DIPR press bulletins often lag primary issuing channels by 1 to 4 hours.
  - *Conclusion:* DIPR must be classified as a secondary validation source (Class D). It must never override official Shrine Board or Traffic Police directives.

---

### 2.5 Candidate E: India Meteorological Department (IMD) — Vaishno Devi Service
- **Organization:** India Meteorological Department (Ministry of Earth Sciences, Government of India).
- **Official URL:** `https://mausam.imd.gov.in/maa_vaishno_devi_yatra/`
- **Key Information Published:**
  - Route-specific weather forecasts (Jammu &rarr; Katra, Katra &rarr; Bhawan).
  - Trek-level nowcasts (thunderstorm, precipitation intensity, wind speeds).
  - Temperature, humidity, and rainfall totals for Katra.
- **Audit Finding & Deduplication Analysis:**
  - **DUPLICATIVE WITH PHASE 8 INTEGRATION:**
  - The Yatra AI architecture already possesses a production-grade, multi-point weather provider (`OpenMeteoProvider`, audited in Phase 8) delivering localized, hourly, and daily forecasts for Katra, Bhawan, Sanjichhat, and Adhkuwari with cache-backed performance (0.29ms latency) and offline deterministic fallback.
  - IMD's dedicated Yatra portal is rendered as static HTML tables and embedded image maps without a documented open REST API.
  - *Recommendation:* Phase 9.6 must **NOT duplicate** weather forecast retrieval. IMD meteorological bulletins should only be referenced if an active `WEATHER_WARNING` is formally declared that directly impacts pilgrimage trek status.

---

## 3. Source Access & Permission Classification Matrix

Every candidate source is classified under the established governance tier:
- **Class A:** Official structured API/feed with documented permitted access.
- **Class B:** Official public page with stable, permitted automated retrieval.
- **Class C:** Official public publication, but automated retrieval permission or stability is unclear.
- **Class D:** Secondary reporting or republication; not an authoritative operational source.
- **Class E:** Inaccessible, authenticated, prohibited, or otherwise unsuitable.

### Comprehensive Source Classification Matrix

| Source Candidate | Authority & Scope | Exact URL | Format | Auth / Controls | Robots / Terms | Class | Justification & Reliability Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **SMVDSB Public Notices** | SMVDSB (Pilgrimage Authority) | `https://www.maavaishnodevi.org/public-notices.aspx` | HTML / PDF table | None (Public) | Standard NIC crawling rules | **Class C** | Primary operational authority for shrine & trek. Stable URL, but lacks structured API. Requires conservative HTML table parser. |
| **SMVDSB Homepage Marquee** | SMVDSB (Pilgrimage Authority) | `https://www.maavaishnodevi.org/index.aspx` | HTML `<marquee>` | None (Public) | Standard NIC crawling rules | **Class C** | Primary operational status line, but fragile DOM structure, lacks timestamps, and is prone to unannounced styling shifts. |
| **SMVDSB Online Services** | SMVDSB (Booking Portal) | `https://online.maavaishnodevi.org/` | ASP.NET Dynamic | Session, OTP, CAPTCHA | Anti-bot policies enforced | **Class E** | Strictly prohibited. Transactional booking system; polling breaches security boundaries and privacy rules. |
| **J&K Traffic Police Portal** | Traffic Police HQ J&K | `https://trafficpolice.jk.gov.in/` | HTML / PDF bulletins | None (Public) | Public government domain | **Class C** | Primary statutory authority for NH-44 and Katra road links. Stable authority, but publishes unstructured text/scanned circulars. |
| **J&K Traffic Police X Channel** | Traffic Police HQ J&K | `https://x.com/Traffic_hqrsJK` | Social Feed (Microblog) | X API Key / Paywall | Scraping prohibited by X ToS | **Class E** | Primary real-time alert feed, but inaccessible via permitted free API. Scraping violates platform terms. |
| **J&K DIPR Portal** | J&K Govt PR Dept | `https://dipr.jk.gov.in/` | HTML / Press Releases | None (Public) | Public government domain | **Class D** | Secondary republication channel. Does not originate operational decisions; exhibits 1–4 hour publication latency. |
| **Commercial News Media** | Daily Excelsior, JK Alerts | Various commercial domains | Commercial HTML | Ad-supported, paywalls | Commercial copyright terms | **Class D** | Secondary reporting. High risk of sensationalism, editorial distortion, or outdated reports. Cannot override official sources. |
| **IMD Vaishno Devi Page** | IMD (Meteorological Authority) | `https://mausam.imd.gov.in/maa_vaishno_devi_yatra/` | HTML / Image Maps | None (Public) | Public government domain | **Class C** | Authoritative for weather alerts, but routine weather forecasting is already completely solved by Phase 8 Open-Meteo adapter. |

---

## 4. Proposed Normalized Notice Data Model (Phase 9.6 Architecture)

The following strongly-typed schema is designed for implementation in Phase 9.6.2, extending the Phase 9.5 contracts (`LiveDataResult`, `ProviderRequest`, `SourceProvenance`):

```python
@dataclass
class OperationalNotice:
    """Normalized, strongly-typed operational advisory container."""
    notice_id: str                      # Unique content-derived hash, e.g. "smvdsb_20261107_a1b2c3d4"
    source_name: str                    # e.g., "Shri Mata Vaishno Devi Shrine Board"
    source_url: str                     # Exact URL from which notice was extracted
    issuing_authority: str              # e.g., "SMVDSB Administration", "Traffic Police HQ J&K"
    notice_title: str                   # Clean, human-readable headline
    notice_text: str                    # Verbatim official body text (unmodified)
    notice_category: str                # One of OperationalNoticeCategory enum
    affected_location: str              # e.g., "Bhawan Trek", "Tarakote Marg", "NH-44 Ramban"
    affected_route: Optional[str]       # Specific corridor affected (e.g., "Jammu-Udhampur-Katra")
    severity: str                       # 'INFO', 'ADVISORY', 'WARNING', 'CRITICAL'
    effective_from: Optional[str]       # ISO 8601 UTC timestamp
    effective_until: Optional[str]      # ISO 8601 UTC timestamp (or None if indefinite)
    publication_timestamp: Optional[str]# Extracted official publication timestamp
    retrieval_timestamp: str            # ISO 8601 UTC timestamp when system fetched the notice
    source_updated_timestamp: Optional[str]
    verification_status: str            # VerifiedExternalAPI, VerifiedCuratedSource, Unverified
    freshness_status: str               # Live, Cached, Stale, Unavailable
    notice_status: str                  # PUBLISHED, EFFECTIVE, EXPIRED, SUPERSEDED, UNAVAILABLE
    original_language: str              # Default: 'en'
    translated_summary: Optional[str]   # Optional plain-language summary for pilgrims
    supersedes_notice_id: Optional[str] # Pointer to previous notice superseded by this update
    expiry_policy: str                  # 'EXPLICIT_UNTIL', '24H_DEFAULT', 'UNTIL_SUPERSEDED'
```

### Standard Operational Categories
1. `YATRA_SUSPENSION`: Complete or partial halt of pilgrimage operations due to weather, disaster, or capacity.
2. `YATRA_RESUMPTION`: Official reopening and resumption of pilgrimage after a suspension.
3. `REGISTRATION_RESTRICTION`: Daily RFID pilgrim token quotas exhausted or counter issuance temporarily paused.
4. `ROUTE_CLOSURE`: Physical closure of a specific track (e.g., Himkoti route closed due to shooting stones; Tarakote open).
5. `ROUTE_RESTRICTION`: Movement restrictions (e.g., one-way pedestrian flow, no ponies permitted on new track).
6. `TRAFFIC_ADVISORY`: NH-44 highway status, convoy cut-off timings, landslide delays, or heavy vehicle diversions.
7. `WEATHER_WARNING`: Heavy rainfall, thunderstorm, or snow alerts officially affecting pilgrim movement.
8. `FACILITY_DISRUPTION`: Helicopter, battery car, passenger ropeway, or power/water infrastructure interruptions.
9. `GENERAL_OPERATIONAL_NOTICE`: Administrative announcements, lost-and-found protocols, or security screening advisories.

### Truth-in-Data Operational States
To maintain absolute compliance with Yatra AI truth-in-data principles, downstream consumers must recognize six distinct operational states:
- **`PUBLISHED`**: Notice issued by authority; start time is in the future.
- **`EFFECTIVE`**: Notice is currently active and enforceable.
- **`EXPIRED`**: Notice end time has passed; restrictions are no longer officially active.
- **`SUPERSEDED`**: A newer official bulletin from the same issuing authority has replaced this notice.
- **`SOURCE_UNAVAILABLE`**: The upstream portal could not be reached; active status cannot be confirmed.
- **`NO_ACTIVE_NOTICES`**: The portal was successfully checked, and no disruption notices are currently posted.
  > [!IMPORTANT]
  > **Mandatory Rule:** The system must **never** equate `NO_ACTIVE_NOTICES` with a fabricated statement that *"Yatra is running smoothly"*. The system must state: *"No active disruption notices posted by the Shrine Board as of [Timestamp]."*

---

## 5. Source Conflict & Hierarchy of Trust Policy

When disparate sources publish contradictory or ambiguous announcements, the Yatra AI central orchestration engine must resolve them using the following deterministic policy:

```mermaid
flowchart TD
    A["Incoming Notice / Advisory"] --> B{"Issuing Authority?"}
    B -->|"SMVDSB"| C["Primary Authority for Pilgrimage, Trek & RFID"]
    B -->|"Traffic Police HQ"| D["Primary Authority for NH-44 & Road Movement"]
    B -->|"IMD"| E["Primary Authority for Meteorological Warnings"]
    B -->|"DIPR / Media"| F["Secondary Source — Cannot Override Primary"]

    C --> G{"Conflicts with Older Notice?"}
    G -->|"Later Timestamp"| H["Supersedes Older Notice"]
    G -->|"No Timestamp"| I["Apply Most Restrictive Safety Directive"]
```

### Conflict Resolution Principles
1. **Jurisdictional Precedence:**
   - **Trek & Shrine Affairs:** The Shri Mata Vaishno Devi Shrine Board (SMVDSB) possesses exclusive jurisdiction. No announcement by traffic police or news outlets can override an SMVDSB declaration regarding trek closures, ropeway status, or RFID availability.
   - **Highway & Road Transit:** The Traffic Police Headquarters, J&K, possesses exclusive jurisdiction over NH-44 and regional vehicular corridors.
2. **News Media Subordination:** Commercial news reports (Daily Excelsior, Greater Kashmir, etc.) must **never** override official government publications. If a news outlet reports a track closure but `maavaishnodevi.org` shows no such notice, the system must display: *"Media reports suggest possible disruption; awaiting official confirmation from the Shrine Board."*
3. **Temporal Superseding:** A notice from the primary authority bearing a later `publication_timestamp` automatically marks prior conflicting notices as `SUPERSEDED`.
4. **Indefinite Notices & Default Expiry:**
   - Daily Traffic Plans: Automatically expire after **24 hours** from issuance unless renewed.
   - Route Closure Notices without an `effective_until` date: Remain `EFFECTIVE` until explicitly superseded or marked `REQUIRES_REVERIFICATION` after 12 hours.
5. **Fail-Safe Safety Default:** In the event of an irreconcilable conflict between two official statements where timestamps are identical or missing, the system must present the **more restrictive safety advisory** to protect pilgrims from physical peril.

---

## 6. Freshness, Polling Feasibility & Resource Governance

### 6.1 Polling Intervals & Publication Cadence
Unlike financial tickers, operational notices on government portals do not update continuously. Unnecessary rapid polling wastes bandwidth and risks IP bans by government Web Application Firewalls (NIC WAF).

| Operation Domain | Source Update Frequency | Recommended Polling Cadence | Cache TTL | Max Stale Window |
| :--- | :---: | :---: | :---: | :---: |
| **SMVDSB Public Notices** | Ad-hoc (0–2 times / day) | Every **60 minutes** (Daytime: 06:00–22:00) | 30 minutes | 180 minutes |
| **SMVDSB Emergency Notices** | Inclement weather events | Every **30 minutes** (During active alerts) | 15 minutes | 60 minutes |
| **NH-44 Traffic Plan** | Daily evening (18:00–21:00) | Every **120 minutes** (Off-peak)<br>Every **30 minutes** (18:00–21:30 IST) | 60 minutes | 360 minutes |
| **Night-Time Window** | Near zero publication (22:00–05:00) | Every **180 minutes** | 120 minutes | 360 minutes |

### 6.2 Polling Optimization & Resilience Architecture
To ensure zero service degradation, the future poller must implement:
1. **HTTP Conditional Requests:** Utilize `If-Modified-Since` and `If-None-Match` (ETag) headers. When upstream servers respond with `304 Not Modified`, bypass parsing entirely.
2. **Cryptographic Content Hashing (SHA-256):** Calculate the SHA-256 hash of the normalized notice title, body text, and publication date. If the hash matches the active stored notice, update `retrieval_timestamp` without triggering duplicate downstream user alerts.
3. **Single-Flight Concurrency Mutex:** Conceptual reuse of the existing Phase 9.5 `UnifiedLiveDataManager` concurrency lock. Only one worker thread may query an upstream government portal at a time, completely preventing "thundering herd" conditions during cache expiration.
4. **Exponential Backoff on Failure:** If a government server returns `500 Internal Server Error`, `503 Service Unavailable`, or connection timeouts, back off exponentially: 1 min &rarr; 2 min &rarr; 5 min &rarr; 15 min, while serving cached data marked with `FreshnessStatus.STALE`.

---

## 7. Security, Privacy & Architectural Integrity

The proposed operational notices architecture strictly enforces all project security standards:
1. **Zero Pilgrim Data Exposure:** Operational notices deal exclusively with public civic infrastructure, road corridors, and shrine tracks. No passenger names, booking PNRs, telephone numbers, or private user credentials will ever be processed by or stored in the notices poller.
2. **Strict Public Isolation:** Public notices will reside exclusively in the public cache category `live_operational_notices`, maintaining total separation from conversational state or private session contexts.
3. **No Access-Control Circumvention:** The poller will strictly query public, unauthenticated `.aspx` and `.html` endpoints. It will not attempt to bypass login screens, solve CAPTCHAs, or spoof authentication cookies.
4. **Source Provenance Retention:** Every rendered notice will carry full provenance metadata (`source_name`, `source_url`, `retrieval_timestamp`, `verification_status`) conforming to the project's standard response envelopes.

---

## 8. Implementation Readiness & Phased Recommendations

### Recommended Scope for Phase 9.6.2 (Controlled Implementation)

```text
Approved Candidate 1:
├── SMVDSB Operational Notices Adapter
│   ├── Target: https://www.maavaishnodevi.org/public-notices.aspx
│   ├── Fallback: Curated Hand-Verified Operational Baseline
│   └── Polling: 60-min interval, SHA-256 deduplication, ASP.NET table parser

Approved Candidate 2:
├── J&K Traffic Police NH-44 Advisory Adapter
│   ├── Target: https://trafficpolice.jk.gov.in/ (or direct TCU telephone directory)
│   ├── Fallback: Statutory TCU Helplines & Verified Route Advisories
│   └── Polling: 60-min interval, daily evening refresh window
```

### Excluded / Deferred Candidates
- ❌ **`online.maavaishnodevi.org`:** **REJECTED.** Transactional booking portal with CAPTCHA and anti-bot protections; violates security boundaries.
- ❌ **X (Twitter) Scraping (`@Traffic_hqrsJK`):** **REJECTED.** Paywalled API ($100/mo minimum), high risk of account suspension for scraping.
- ❌ **DIPR Republication Scraper:** **DEFERRED.** Secondary republisher with noticeable latency; redundant if primary SMVDSB and Traffic Police sources are monitored.
- ❌ **IMD Web Scraper:** **REJECTED AS NEW INTEGRATION.** Weather data is already fully handled by Phase 8 (`OpenMeteoProvider`). Meteorological alerts will be referenced conceptually without redundant scraping.

---

## 9. Baseline Repository & Git State Record

Before concluding this feasibility audit, the Git state was verified:
- **Active Repository:** `yatra-ai` on branch `main` at commit `db54ba33f6049caec6894bb8e943be20656fa02c`.
- **Working Tree Status:** Preserved with 18 tracked modified files and 23 untracked directories/files intact (Phase 9.5 framework, reports, and tests). No commits, pushes, cleans, or stashes were performed.
- **Backup Repository:** `yatra-booking-agent` verified completely untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`.

---

## 10. Audit Verdict & Stop Condition

### Audit Verdict: **FEASIBILITY AUDIT COMPLETE (APPROVED FOR PHASE 9.6.2 DESIGN)**

The technical and regulatory feasibility of official operational notices has been established. The absence of public REST APIs necessitates a disciplined, conservative HTML table poller for SMVDSB and Traffic Police public notices, backed by SHA-256 deduplication and statutory fallback helplines.

Per the instructions for Phase 9.6.1, **no implementation code, pollers, schedulers, or database changes have been created.** Execution has halted in a strictly read-only state, awaiting user review and explicit authorization before commencing **Phase 9.6.2 (Operational Notices Adapter & Poller Implementation)**.
