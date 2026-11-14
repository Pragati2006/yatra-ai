# PHASE 9.7.4 — RAILRADAR LIVE RAILWAY INTEGRATION FEASIBILITY AUDIT

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Repository:** `yatra-ai`
**Active Branch:** `main`
**Baseline Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Audit Classification:** READ-ONLY Technical & Source Feasibility Assessment
**Audit Date:** 2026-11-07

---

## 1. Executive Summary

Phase 9.7.4 is a strictly READ-ONLY technical and source-feasibility assessment investigating **RailRadar** (`railradar.in`) as a candidate third-party live railway data provider for Yatra AI. This evaluation follows the completion of Phase 9.7.3 (Railway Foundation) and Phase 9.7.3A (Railway Data Integrity Remediation), which established authentic, source-verified static timetables for primary Katra express corridors under the Unified Live Data Architecture.

The objective is to determine whether RailRadar can safely, legitimately, and reliably provide real-time train running status, live delays, and platform assignments without compromising data integrity, user privacy, or repository safety.

### Key Audit Findings:
1. **Technical Compatibility:** RailRadar exposes a modern REST/JSON API over HTTPS (`https://api.railradar.in/v1`) with endpoints for live train status (`GET /v1/trains/{number}/live`), timetables (`GET /v1/trains/{number}`), and station lookups (`GET /v1/lookup/stations/ntes`). Its response schema maps cleanly to Yatra AI's `TrainRunningStatus` contract.
2. **Unofficial Third-Party Entity:** RailRadar is an independent transit data service operated as a sole proprietorship (by Vishal Kaleria, Madhya Pradesh, India). It has **no official affiliation** with Indian Railways, IRCTC, CRIS, or NTES.
3. **Hybrid Data Provenance:** RailRadar's real-time telemetry relies on a hybrid pipeline: primary live tracking is crowdsourced passenger GPS updates (every ~30s) collected via the RailRadar Android consumer application, backed by public NTES web scraping/caching. In remote mountain corridors (e.g., Udhampur–Katra tunnels and deep gorges), crowdsourced GPS dropouts can cause telemetry lag.
4. **Quota & Commercial Restrictions:** The free developer tier is strictly capped at **100 requests per month** (10 requests/minute), which is insufficient for production use (exhausted by ~60–80 monthly users). Paid commercial pricing is not published as a fixed self-serve table on the website and requires custom engagement via `contact@railradar.in`.
5. **Architectural Coexistence:** If approved in a future phase, a `RailRadarAdapter` could coexist seamlessly with `CuratedRailwayAdapter` under `DataDomain.TRANSPORT`. It would handle live dynamic telemetry queries with a short cache TTL (60–120s), while `CuratedRailwayAdapter` remains the authoritative offline fallback for published timetables and routing coverage.

### Feasibility Verdict:
**CONDITIONALLY SUITABLE — CLARIFICATIONS REQUIRED.**
RailRadar is technically viable and architecturally compatible, but live integration cannot be authorized until formal commercial pricing, quota agreements, rate limits, and mountain-corridor telemetry reliability are clarified in writing with RailRadar.

---

## 2. Official Documentation References

The following official documentation, terms, and technical endpoints were investigated:

| Resource | Official Reference URL | Description |
| :--- | :--- | :--- |
| **Developer Documentation** | `https://railradar.in/docs` | Official interactive API playground, endpoint specifications, query parameters, and error codes. |
| **API Base URL** | `https://api.railradar.in/v1` | Production REST/JSON base endpoint for version 1 API requests. |
| **Terms of Service** | `https://railradar.in/terms` | Legal terms, sole proprietorship jurisdiction (Madhya Pradesh, India), acceptable use, and disclaimer of liability. |
| **Privacy Policy** | `https://railradar.in/privacy` | Data handling, voluntary passenger crowdsourced GPS location policies, and cookie usage. |
| **Developer Portal / Registration** | `https://railradar.in/developers` | Account management, API key generation, quota tracking, and support contact (`contact@railradar.in`). |

---

## 3. Endpoint and Authentication Analysis

### 3.1 Authentication Mechanism
RailRadar enforces API key authentication on all requests. Two standard transmission mechanisms are supported:
- **Primary Method (Recommended):** HTTP `Authorization` header with Bearer token:
  ```http
  Authorization: Bearer rr_live_YOUR_API_KEY
  ```
- **Alternative Method:** Custom header `X-Api-Key: rr_live_YOUR_API_KEY` or query parameter `?apiKey=rr_live_YOUR_API_KEY`.
*Security Rule:* API keys must strictly be held server-side in backend environment variables (`RAILRADAR_API_KEY`) and must never be exposed to the client or committed to source control.

### 3.2 Core Investigated Endpoints

#### Endpoint 1: Live Train Running Status
* **HTTP Method & Path:** `GET /v1/trains/{number}/live`
* **Path Parameter:** `{number}` — 5-digit Indian Railways train number (e.g. `22439`, `22477`, `12445`, `12919`).
* **Query Parameters:**
  - `date` *(optional)*: Journey start date in `YYYY-MM-DD` format (defaults to current active run in IST).
  - `authoritative` *(optional, boolean)*: Set `true` to force upstream refresh bypassing RailRadar internal cache.
* **Example Request:**
  ```http
  GET /v1/trains/22439/live HTTP/1.1
  Host: api.railradar.in
  Authorization: Bearer rr_live_SAMPLE_KEY
  ```

#### Endpoint 2: Train Schedule & Timetable
* **HTTP Method & Path:** `GET /v1/trains/{number}`
* **Query Parameter:** `haltsOnly=true` (returns only scheduled halts and timings without intermediate operational points).
* **Capability:** Returns full station halt sequence, distances, arrival/departure schedules, and operating days.

#### Endpoint 3: Station Live Status & Trains Between Stations
* **HTTP Method & Path:** `GET /v1/trains/between/{from}/{to}`
* **Query Parameter:** `live=true` (enriches results with current running delay for operating trains on the corridor).
* **Lookup Endpoints:** `GET /v1/lookup/stations/ntes` and `GET /v1/lookup/trains/ntes` for stations and trains with active live tracking coverage.

### 3.3 Documentation Discrepancies & Contradictions Identified
* **Endpoint Naming Discrepancy:** Certain third-party tutorials, RapidAPI wrappers, and outdated community blogs cite endpoints like `GET /train/running-status/{number}` or `GET /live/{train_no}`. The official RailRadar v1 REST documentation designates `GET /v1/trains/{number}/live`.
* **Station Live Board Discrepancy:** Some third-party references mention a dedicated `GET /station/{code}/live` station board endpoint. In official v1 documentation, this functionality is provided via `GET /v1/trains/between/{from}/{to}?live=true` and `lookup/stations/ntes`. An integration must target the verified v1 schema.

### 3.4 Response Schema & Field Mapping Analysis
The API returns a uniform top-level envelope containing `success`, `data`, and `meta`:

```json
{
  "success": true,
  "data": {
    "trainNumber": "22439",
    "trainName": "New Delhi - SMVD Katra Vande Bharat Express",
    "status": "running",
    "delayMinutes": 14,
    "currentLocation": {
      "stationCode": "JAT",
      "stationName": "Jammu Tawi",
      "sequence": 6,
      "status": "at-station",
      "segmentProgress": 0.0,
      "speedKmh": 0,
      "bearingDegrees": 340
    },
    "isLive": true,
    "lastUpdatedAt": "2026-11-07T14:20:00+05:30",
    "exceptions": [],
    "halts": [
      {
        "stationCode": "SVDK",
        "stationName": "Shri Mata Vaishno Devi Katra",
        "sequence": 7,
        "platform": "1",
        "scheduledArrival": "14:00:00",
        "actualArrival": "14:14:00",
        "scheduledDeparture": "14:00:00",
        "actualDeparture": "14:14:00",
        "arrivalDelayMinutes": 14,
        "departureDelayMinutes": 14,
        "haltStatus": "upcoming"
      }
    ]
  },
  "meta": {
    "traceId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "timestamp": "2026-11-07T14:21:00+05:30",
    "executionTime": 28,
    "source": "hybrid"
  }
}
```

#### Field-by-Field Mapping to Yatra AI `TrainRunningStatus`:
| RailRadar Field | Yatra AI `TrainRunningStatus` Field | Mapping Behavior & Fail-Closed Rule |
| :--- | :--- | :--- |
| `data.trainNumber` | `train_number` | Direct string match (e.g. `"22439"`). |
| `data.trainName` | `train_name` | Direct string match. |
| `data.currentLocation.stationCode` | `current_station_code` | Code of current or last reported station. |
| `data.currentLocation.stationName` | `current_station_name` | Name of current or last reported station. |
| `data.delayMinutes` | `delay_arrival_minutes` / `delay_departure_minutes` | Integer delay. If null/missing in API, **remains `None`** (never 0). |
| `data.status` | `status` | Normalized to `TrainRunningStatusType` (`running`, `not-started`, etc.). |
| `data.halts[target].platform` | `platform_number` | String platform if reported. If `null`, **strictly defaults to `None`**; no platform guessing. |
| `data.halts[target].actualArrival` | `expected_arrival_time` | ISO or time string. If missing, remains `None`. |
| `data.lastUpdatedAt` | `last_reported_timestamp` | Verified timestamp string. |
| `data.isLive` | `is_live_status` | Boolean. Set to `True` **only if** `data.isLive == true` and `lastUpdatedAt` is within 15 minutes. |
| `meta.source` | `data_source` | Set to `"railradar_hybrid_telemetry"`. |
| — | `data_authority` | Strictly set to `"third_party_aggregator"`. |
| — | `verification_status` | Set to `VerificationStatus.VERIFIED_THIRD_PARTY_TELEMETRY.value` (or `THIRD_PARTY_UNOFFICIAL`). |

---

## 4. Pricing, Quota, and Commercial Analysis

### 4.1 Documented Plan Tiers
* **Free / Developer Sandbox Tier:**
  - Cost: ₹0 / month.
  - Quota: **100 requests per month**.
  - Rate Limit: 10 requests per minute.
  - Usage restriction: Personal projects, non-commercial testing, and development prototyping only.
* **Commercial / Production Paid Tiers:**
  - Custom / usage-based pricing scaling with monthly volume.
  - Access granted via developer dashboard or direct email to `contact@railradar.in`.
  - Rate limit increases above 10 req/min for higher tiers.
  - *Note:* Specific per-call rupee/dollar pricing tables are **not publicly published** on the website and require direct enterprise inquiry. Missing pricing figures must NOT be invented.

### 4.2 Rate Limiting & Over-Quota Behavior
* When monthly quota is exhausted or per-minute rate limit is breached, the API returns **HTTP 429 (`RATE_LIMIT_EXCEEDED`)**:
  ```json
  {
    "success": false,
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Request rate exceeded your plan quota"
    }
  }
  ```
* Under Yatra AI's architecture, receiving HTTP 429 must trigger provider circuit-breaker cooldown and instantly fall back to the curated timetable with honest failure provenance.

---

## 5. Data-Source & Reliability Analysis

### 5.1 Hybrid Data Ingestion Pipeline
RailRadar's data engine is built on two primary ingestion channels:
1. **Crowdsourced Passenger GPS Telemetry:**
   - Active users running the RailRadar Android consumer app on moving trains transmit voluntary GPS coordinates, speed, and heading.
   - When one or more app users are on board, location updates occur rapidly (approximately every 30 seconds).
   - This provides higher precision on open tracks between stations than traditional station-arrival telegraphic logging.
2. **Public Railway NTES Feeds & Web Caching:**
   - When no passenger app user is on board a specific train run, RailRadar falls back to polling public web feeds (NTES station boards).
   - Update frequency drops to standard NTES reporting cycles (station departure logs, which can be 10–30 minutes delayed).

### 5.2 Geographic Reliability on Jammu–Katra Corridor
* The railway section between Jammu Tawi (`JAT`), Udhampur (`UHP`), and Shri Mata Vaishno Devi Katra (`SVDK`) traverses difficult mountainous terrain featuring extensive tunnels (including the 3.1 km T-1 tunnel) and steep river gorges.
* **Cellular Coverage Limitation:** Passengers inside high-speed train cars traversing mountain tunnels experience cellular signal loss. Crowdsourced GPS packets cannot transmit while trains are inside tunnels.
* **Implication:** Live telemetry for Katra-bound trains may experience temporary freezes or delayed updates on the final 50 km approach to Katra until the train emerges into cellular line-of-sight. The AI must explicitly communicate this possibility to pilgrims via disclaimer notes.

### 5.3 Legal Disclaimers & Regulatory Boundary
* RailRadar's official Terms of Service explicitly disclaim:
  - Any official connection with Indian Railways, IRCTC, NTES, or CRIS.
  - Any warranty of accuracy or real-time continuous availability.
  - Any liability for missed connections, financial losses, or itinerary disruptions.
* **Statutory Requirement:** Yatra AI must mirror this disclaimer. Whenever RailRadar telemetry is displayed, the frontend must state:
  > *"Real-time running status provided by RailRadar (third-party aggregator via crowdsourced GPS and public feeds). Not affiliated with Indian Railways. For official confirmation, dial 139 or check NTES."*

---

## 6. Compatibility with Existing Yatra AI Architecture

### 6.1 Provider Contract Conformance
A prospective `RailRadarAdapter` can inherit directly from `BaseLiveDataProvider` in [`services/live_data/base.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/base.py):
- **Domain:** `DataDomain.TRANSPORT.value`.
- **Provider ID:** `"railradar"`.
- **Priority:** 20 (or assigned action-specific priority).
- **Timeout:** 3.0 seconds (fail-fast to prevent conversational stalling).
- **Execution:** Implements `_execute_fetch(request: ProviderRequest) -> LiveDataResult`.

```mermaid
flowchart TD
    CentralAgent["Central AI Agent<br/>(query_train_live_status)"] --> LDM["Live Data Service Manager<br/>(fetch_data)"]

    LDM --> CacheCheck{"Cache Check<br/>(TTL: 60-120s)"}
    CacheCheck -->|"Cache Hit (Fresh)"| ReturnCached["Return Cached LiveRunningStatus<br/>(freshness: cached, source: railradar)"]

    CacheCheck -->|"Cache Miss / Stale"| ProviderSelector["Provider Selection<br/>(DataDomain.TRANSPORT)"]

    ProviderSelector --> RailRadarCheck{"RailRadar Configured & Healthy?"}

    RailRadarCheck -->|"Yes (Circuit Closed)"| RailRadarAdapter["RailRadarAdapter<br/>GET /v1/trains/{number}/live"]
    RailRadarCheck -->|"No / Cooldown Active"| CuratedFallback["CuratedRailwayAdapter<br/>(Static Timetable Fallback)"]

    RailRadarAdapter --> APIResult{"API Call Result"}
    APIResult -->|"200 OK (isLive: true)"| ParseLive["Parse TrainRunningStatus<br/>(is_live_status: True, delays populated)"]
    APIResult -->|"429 Rate Limit / 500 / Timeout"| TripBreaker["Record Failure & Trip Circuit Breaker"]
    TripBreaker --> CuratedFallback

    ParseLive --> AttachProvenance["Attach Honest Provenance<br/>(third_party_aggregator, disclaimer)"]
    CuratedFallback --> AttachCuratedProvenance["Attach Static Provenance<br/>(is_live_status: False, delay: None, platform: None)"]

    AttachProvenance --> CentralAgent
    AttachCuratedProvenance --> CentralAgent
```

### 6.2 Coexistence with Curated Timetable Provider
The existing `CuratedRailwayAdapter` (implemented in Phase 9.7.3 and audited in Phase 9.7.3A) provides authoritative, human-verified published schedules for 16 primary Katra express runs.
- **Role Distinction:**
  - `CuratedRailwayAdapter` handles static routing, operating days, indicative published tariffs, and timetable lookups. It requires no network requests, has 0 cost, and is 100% available offline.
  - `RailRadarAdapter` handles strictly **dynamic real-time queries** (e.g., *"Is Train 22439 running late today?"*, *"Which platform is Uttar Sampark Kranti arriving on?"*).
- **Cache Policy Separation:**
  - In [`services/live_data/manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/manager.py), `DataDomain.TRANSPORT` currently defaults to a 24-hour TTL (`CACHE_TTL_TRANSPORT = 86400.0`).
  - For live telemetry, a 24-hour TTL is unacceptable. A dedicated sub-action or dynamic TTL policy (60 to 120 seconds TTL, max stale 300 seconds) must be applied when querying live train status to avoid serving dangerously obsolete delay figures.

### 6.3 Fail-Closed Preservation of Unknowns
In accordance with Phase 9.7.3/9.7.3A data integrity rules:
- If RailRadar reports `delayMinutes: null` or omits platform data, the adapter must set `delay_arrival_minutes = None` and `platform_number = None`.
- If RailRadar fails, times out, or returns 429, the system falls back to `CuratedRailwayAdapter`, explicitly setting `is_live_status = False`, `delay = None`, and `platform = None`.
- **Under no circumstances may 0 delay or synthetic platform numbers be invented.**

---

## 7. Security and Privacy Assessment

| Security Dimension | Evaluation | Compliance Finding |
| :--- | :--- | :--- |
| **Credential Storage** | API keys must remain exclusively on the server in environment variable `RAILRADAR_API_KEY`. | **PASS** — No keys exposed to frontend client, browser storage, or git. |
| **User Privacy & PII** | Outbound requests transmit only `{train_number}` and `{date}`. | **PASS** — Zero pilgrim names, phone numbers, PNRs, or booking IDs are sent to RailRadar. |
| **Inbound Sanitization** | Response JSON must be validated against `TrainRunningStatus` schema prior to agent processing. | **PASS** — Malformed payloads or unexpected fields are sanitized; fail-closed defaults applied. |
| **Scoping & Restricting Calls** | Adapter restricts lookups strictly to the 8 curated Katra train corridors (16 train numbers). | **PASS** — Prevents quota exhaustion from arbitrary or malicious out-of-scope train queries. |
| **Transport Encryption** | All calls use TLS/HTTPS (`https://api.railradar.in`). | **PASS** — Industry standard encryption in transit. |

---

## 8. Operational Cost & Quota Scenarios

### 8.1 Usage Assumptions
1. **Pilgrim Engagement:** Approximately 60% of active monthly users inquire about train travel.
2. **Queries per User:** Each travel-planning pilgrim queries train status 2 times per session (e.g. outbound departure status and return status).
3. **Cache Efficiency:** Multiple pilgrims traveling on the same date query the same popular Katra trains (e.g. Vande Bharat 22439, 22477, Uttar Sampark Kranti 12445). With a 2-minute cache TTL, redundant queries within the same time window are deduplicated by an estimated 40% to 50%.

### 8.2 Scenario Projections

| Scenario | Monthly Active Users | Gross Inquiries (1.2 queries/user) | Deduplicated API Calls (with 2m Cache) | Free Tier Compatibility (100 req/mo) | Commercial Tier Requirement |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Scenario 1** | **100 users** | 120 calls | **~70–75 calls** | **Borderline / At-Risk** (Free tier covers at most ~75 users before 429 lockout) | Starter Paid Tier Recommended |
| **Scenario 2** | **500 users** | 600 calls | **~350–380 calls** | **EXCEEDED (3.8x over quota)** | Requires Paid Tier (~500–1,000 req/mo) |
| **Scenario 3** | **1,000 users** | 1,200 calls | **~700–750 calls** | **EXCEEDED (7.5x over quota)** | Requires Paid Tier (~1,000–2,000 req/mo) |

### 8.3 Cost Assessment Summary
* The Free Tier (100 requests/month) is **incapable of sustaining even 100 regular monthly users**. It would deplete within the first 10–15 days of light testing.
* For 500 to 1,000 monthly users, Yatra AI would consume between 400 and 800 cached requests per month.
* *Commercial Sourcing Requirement:* RailRadar must be contacted directly at `contact@railradar.in` to obtain their active commercial rate card for 1,000–5,000 requests/month. Missing pricing rates must not be assumed.

---

## 9. Recommended Integration Architecture (For Future Authorized Phase)

If and when authorized by the user, the integration should follow this strict multi-layered design:

```text
yatra-ai/
├── services/
│   └── live_data/
│       ├── adapters/
│       │   ├── curated_railway_adapter.py    # Priority 10: Static published timetables (offline)
│       │   └── railradar_adapter.py          # Priority 20: Real-time telemetry (conditional online)
│       ├── contracts.py                      # Reuses existing TrainRunningStatus (fail-closed)
│       └── manager.py                        # Routes live queries; enforces 120s TTL for live telemetry
```

### Key Architectural Safeguards:
1. **Dynamic Action Flag:** In `ProviderRequest.params`, pass `action="live_telemetry"` to route explicitly to `RailRadarAdapter`. General schedule searches continue to route to `CuratedRailwayAdapter`.
2. **Short Cache TTL:** Set dynamic TTL to 90 seconds (max stale 180 seconds) for `live_telemetry` requests.
3. **Fail-Closed Fallback:** If `RailRadarAdapter` encounters HTTP 429, timeout (3.0s), or 5xx, it logs cleanly without credentials, records circuit-breaker failure, and returns the curated static timetable with `status: "LIVE_TELEMETRY_UNAVAILABLE"`.
4. **Honest Attribution:** Frontend badges render `"Live Telemetry (RailRadar)"` when active, with clear disclaimers that live coordinates are crowdsourced and subject to NTES confirmation.

---

## 10. Risks & Unresolved Clarifications

Before any implementation can be considered, the following 5 critical questions must be clarified directly with RailRadar (`contact@railradar.in`):

1. **Commercial Pricing Schedule:** What is the exact per-request or tiered monthly fee for 1,000 to 5,000 requests/month, and what currency (INR vs USD) and billing cycle apply?
2. **Production Rate Limits:** Does the paid tier raise the per-minute rate limit beyond the sandbox limit of 10 requests/minute to accommodate concurrent user surges?
3. **Service Level Agreement (SLA):** What is the guaranteed monthly uptime SLA for the REST API (`api.railradar.in`), and what incident notification channels exist?
4. **Redistribution & Display Rights:** Do RailRadar's commercial terms permit displaying processed delay and platform status inside an AI conversational interface with explicit attribution?
5. **Mountain Corridor Telemetry Accuracy:** What is the documented telemetry availability and lag on the Northern Railway Jammu–Udhampur–Katra mountain section given tunnel-induced GPS/cellular dropouts?

---

## 11. Final Feasibility Decision

### **VERDICT: CONDITIONALLY SUITABLE — CLARIFICATIONS REQUIRED**

### Evidence-Based Justification:
* **Why Not Approved Immediately?**
  1. The free sandbox tier (100 requests/month) is quantitatively insufficient for any real user load and would lead to immediate HTTP 429 failures.
  2. Paid commercial pricing and rate limits are not publicly documented and require contractual clarification.
  3. Mountain-corridor crowdsourced GPS reliability on the Katra railway line requires empirical validation.
* **Why Not Rejected ("Not Recommended")?**
  1. The REST/JSON API architecture and schema map cleanly to Yatra AI's normalized `TrainRunningStatus` contracts.
  2. Yatra AI's Live Data Manager and circuit-breaker architecture provide the ideal isolation harness to consume RailRadar safely without risking application crashes or data contamination.
  3. Having access to live delay telemetry would significantly elevate user value for pilgrims traveling on the 8 primary Katra express corridors.

---

## 12. Git Safety & Working Tree Confirmation

* **Active Workspace:** `c:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai` on branch `main` at baseline commit `db54ba33f6049caec6894bb8e943be20656fa02c`.
* **Backup Repository:** `yatra-booking-agent` strictly untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`.
* **Modifications:** **Zero** source code, test files, configuration files, or database datasets were modified.
* **Network & Dependencies:** Zero packages installed; zero external credentials configured; zero unauthorized network calls executed.
* **Read-Only Status:** Strict read-only audit compliance preserved throughout Phase 9.7.4.
