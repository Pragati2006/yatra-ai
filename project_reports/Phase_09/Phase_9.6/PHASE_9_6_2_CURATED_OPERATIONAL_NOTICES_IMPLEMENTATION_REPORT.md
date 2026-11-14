# PHASE 9.6.2 — CURATED OPERATIONAL NOTICES & VERIFIED CONTACT REGISTRY IMPLEMENTATION REPORT

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Repository:** `yatra-ai`
**Branch:** `main`
**Baseline Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Parent Phases:**
- Phase 9.5: Provider Framework & Normalized Contracts
- Phase 9.6.1: Official Operational Notices & Traffic Source Feasibility Audit
- Phase 9.6.1.1: Official Source Evidence & Automated Retrieval Permission Validation
**Report Destination:** `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_CURATED_OPERATIONAL_NOTICES_IMPLEMENTATION_REPORT.md`
**Execution Timestamp:** 2026-11-07
**Status:** IMPLEMENTED & FULLY VERIFIED (17/17 Dedicated Tests, 353/353 Full Regression Tests Passing)

---

## 1. Executive Summary

Phase 9.6.2 implements a provider-independent, human-verified operational notices and contact registry within the Phase 9.5 live-data provider architecture.

In strict adherence to the safety directives established during the Phase 9.6.1.1 evidence validation audit, this implementation **does not scrape, poll, or automatically query unconfigured government websites** (such as SMVDSB or Traffic Police web portals). Instead, it implements a verifiable, source-attributed, human-curated operational registry that delivers grounded advisories, life-safety helplines, and highway passage guidance directly to pilgrims while enforcing strict truth-in-data boundaries.

### Core Achievements
1. **Separation of Status Concerns:** Disentangled source fetch status (`SUCCESS`, `NO_RESULTS`, `UNAVAILABLE`), data freshness status (`not_applicable` for curated records), epistemic verification status (`verified_curated_source`), and directive lifecycle status (`PUBLISHED`, `ACTIVE`, `REQUIRES_REVERIFICATION`, `SUPERSEDED`, `WITHDRAWN`).
2. **Truth-in-Data Invariants:**
   - **No Presumption of Smooth Operations:** When the registry has no active disruption circulars (`NO_ACTIVE_NOTICES`), the system states honestly that no active closures are recorded in the curated catalog, but notes that upstream live conditions remain unconfirmed without direct authority confirmation.
   - **Expiry Invariant:** Timer expiration never implies that a disrupted corridor or track has reopened. When a notice's expected validity horizon lapses without an explicit withdrawal or superseding circular, it automatically transitions to `REQUIRES_REVERIFICATION`.
   - **Strict 5-Point Alignment Superseding:** An older notice is superseded by a newer notice only if authority, affected location, affected route corridor, and notice category match, and temporal precedence is strictly newer. Secondary media reports are blocked from superseding verified official circulars.
3. **Statutory Emergency Priority (112):** National Emergency Number 112 (ERSS) is established as the primary statutory emergency contact for immediate life safety across Pan-India and J&K. Administrative desks (such as the SMVDSB Protocol Desk) are explicitly demarcated as office-hours only (10:00 AM - 5:00 PM IST).
4. **End-to-End Central Agent & UI Integration:** Added specialist tools `query_operational_notices` and `lookup_verified_contacts` to Central AI Agent tool-calling, wired deterministic fallback handlers for offline/timeout resilience, and built responsive React card components (`OperationalNoticeCard.jsx` and `VerifiedContactCard.jsx`) in the chat interface.
5. **Rigorous Verification:** Built a dedicated 17-point test suite (`tests/test_phase9_6_2_curated_notices.py`) and verified zero regressions across the entire project matrix (353/353 passing tests).

---

## 2. Strict Repository Safety Audit

Before and throughout implementation, repository isolation and working tree status were continuously validated:

| Verification Item | Active Repository (`yatra-ai`) | Backup Repository (`yatra-booking-agent`) | Status |
| :--- | :--- | :--- | :--- |
| **Path** | `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai` | `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` | Verified Clean |
| **Current Branch** | `main` | `feature/ui-redesign` | Verified Match |
| **Baseline Commit** | `db54ba33f6049caec6894bb8e943be20656fa02c` | `8996d6a8e3bc83eda0808d0a9ca217979118ebee` | Verified Invariant |
| **Integrity Rule** | Uncommitted work preserved; zero git reset/stash/commit/push | Strictly untouched at recorded HEAD | Verified Invariant |

---

## 3. Data Contracts & Architecture

### 3.1 Typed Contracts Added to `services/live_data/contracts.py`

```python
class NoticeCategory(str, Enum):
    YATRA_SUSPENSION = "YATRA_SUSPENSION"
    YATRA_RESUMPTION = "YATRA_RESUMPTION"
    REGISTRATION_RESTRICTION = "REGISTRATION_RESTRICTION"
    ROUTE_CLOSURE = "ROUTE_CLOSURE"
    ROUTE_RESTRICTION = "ROUTE_RESTRICTION"
    TRAFFIC_ADVISORY = "TRAFFIC_ADVISORY"
    WEATHER_WARNING = "WEATHER_WARNING"
    FACILITY_DISRUPTION = "FACILITY_DISRUPTION"
    GENERAL_OPERATIONAL_NOTICE = "GENERAL_OPERATIONAL_NOTICE"

class NoticeLifecycleStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    ACTIVE = "ACTIVE"
    REQUIRES_REVERIFICATION = "REQUIRES_REVERIFICATION"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"

class NoticeAggregateStatus(str, Enum):
    HAS_NOTICES = "HAS_NOTICES"
    NO_ACTIVE_NOTICES = "NO_ACTIVE_NOTICES"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"

class ContactCategory(str, Enum):
    NATIONAL_EMERGENCY = "NATIONAL_EMERGENCY"
    SHRINE_BOARD_ASSISTANCE = "SHRINE_BOARD_ASSISTANCE"
    TRAFFIC_CONTROL = "TRAFFIC_CONTROL"
    LOCAL_POLICE = "LOCAL_POLICE"
    MEDICAL_ASSISTANCE = "MEDICAL_ASSISTANCE"
```

### 3.2 Dataclass Definitions

- **`OperationalNotice`**: Represents an official administrative notice, route advisory, or operational restriction. Includes fields for `notice_id`, `notice_title`, `notice_text`, `issuing_authority`, `source_url`, `affected_location`, `affected_route`, `category`, `severity`, `publication_timestamp`, `effective_from`, `effective_until`, `verified_at`, `verified_by`, `verification_status`, `notice_lifecycle_status`, `superseded_by_notice_id`, `supersedes_notice_id`, and `translated_summary`.
- **`VerifiedContact`**: Represents a human-verified helpline or emergency authority. Includes `contact_id`, `organization`, `telephone_number`, `service_description`, `category`, `geographic_jurisdiction`, `operating_hours`, `source_url`, `verified_at`, `verified_by`, `verification_status`, `is_primary_emergency`, and `notes`.
- **`LiveDataResult` Enhancements**: Added property accessors for `source_type`, `source_name`, and `disclaimer` to provide seamless, consistent field access across all provider result consumers.

---

## 4. Curated Registries & Services Implementation

### 4.1 Data Catalogs
- **`data/curated_operational_notices.json`**: Initialized with authentic, verified Shrine Board operational advisories:
  1. `smvdsb_gen_rfid_mandatory`: Mandatory RFID-based Yatra Access Card registration requirement prior to commencing trek from Katra.
  2. `smvdsb_gen_unauthorized_agents`: Advisory warning against unauthorized private agents, tour operators, and fraudulent websites.
- **`data/verified_contacts.json`**: Verified authority directory with statutory emergency primary directive:
  1. Primary Directive: `112` (Unified National Emergency Helpline / ERSS, 24x7 Pan-India & J&K).
  2. Shrine Board 24x7 Call Centre: `1800-180-7212` and `+91-1991-234804`.
  3. Shrine Board Protocol Desk: `+91-1991-232029` (Explicitly classified as office hours only: 10:00 AM - 5:00 PM IST; non-emergency).
  4. TCU Ramban: `9419993745` (NH-44 Ramban–Banihal passage verification).
  5. TCU Jammu: `0191-2459048` (Nagrota checkpoint & Jammu passage).
  6. TCU Udhampur: `8491928625` (Katra turn-off & Jakheni checkpoint).
  7. Katra Police Station: `+91-1991-232010`.
  8. Medical Ambulance (NAS): `108`.

### 4.2 Core Service Logic
- **`services/operational_notices.py`**:
  - `load_curated_notices()`: Safely loads notices JSON; handles missing or corrupt files with `SOURCE_UNAVAILABLE`.
  - `evaluate_notice_lifecycle()`: Implements the non-expiry safety invariant: lapses in `effective_until` or default 24h traffic/weather horizons transition notices to `REQUIRES_REVERIFICATION`.
  - `resolve_superseding_relationships()`: Enforces the 5-point alignment rule (authority, location, route, category, timestamp) and blocks unverified reports from overriding official sources.
  - `query_curated_notices()`: Filters by location, route, category, severity; returns structured notices, aggregate status, and honest advisory messages.
- **`services/verified_contacts.py`**:
  - `load_verified_contacts()`: Safely loads contact records and the primary emergency directive.
  - `query_verified_contacts()`: Performs jurisdiction matching (preserving universal 112 across all queries), category filtering, and automatic suppression of unverified contacts by default.

---

## 5. Live Data Provider Adapters & Manager

### 5.1 Provider Adapters
- **`CuratedOperationalNoticesAdapter`** (`services/live_data/adapters/curated_operational_notices_adapter.py`):
  - Provider ID: `curated_operational_notices`
  - Domain: `DataDomain.OPERATIONAL_NOTICE` (Priority: 10)
  - Source Type: `curated_data`
  - Verification Status: `verified_curated_source`
- **`VerifiedContactAdapter`** (`services/live_data/adapters/curated_contact_adapter.py`):
  - Provider ID: `verified_contact_registry`
  - Domain: `DataDomain.EMERGENCY` (Priority: 10)
  - Source Type: `curated_data`
  - Verification Status: `verified_curated_source`
  - Aliased as `CuratedContactAdapter` for backward compatibility.

### 5.2 Unified Manager Default Registration
Updated `services/live_data/manager.py` to eagerly register:
1. `CuratedOperationalNoticesAdapter` for `operational_notice`
2. `VerifiedContactAdapter` for `emergency`
3. `CuratedAccommodationAdapter` for `accommodation`
4. `OpenMeteoWeatherAdapter` for `weather`

Added `fetch_data()` alias on `UnifiedLiveDataManager` forwarding directly to `execute_request()`.

---

## 6. Central Agent & Provenance Integration

### 6.1 LangChain Tools Added
In `agents/central_agent.py`:
1. `@tool def query_operational_notices(location, route, category) -> dict`: Queries verified notices through `UnifiedLiveDataManager` or service fallback.
2. `@tool def lookup_verified_contacts(category, jurisdiction) -> dict`: Queries verified contacts through `UnifiedLiveDataManager` or service fallback.
3. Registered both tools in `CENTRAL_TOOLS` (12 total tools) and `CENTRAL_TOOL_MAP`.

### 6.2 Turn Execution & Deterministic Fallback
- In `_execute_llm_tool_calling_turn`: Captures `captured_operational_notices` and `captured_verified_contacts`, injecting them into the standardized response envelope and preserving them across partial tool failures.
- In `process_conversational_turn`:
  - Added deterministic routing via `is_operational_notice_query(text)` and `is_verified_contact_query(text)`.
  - Offline or LLM timeout queries regarding track closures, landslides, traffic advisories, or helplines are answered with honest, grounded responses and attached cards.
- In `utils/provenance.py`: Updated `extract_provenance_from_tool_result()` and `attach_provenance_to_response()` to extract standardized provenance records for operational notices and verified helplines.

---

## 7. Frontend User Interface Cards

### 7.1 Reusable Card Components
1. **`OperationalNoticeCard.jsx`** (`frontend/src/components/chat/cards/OperationalNoticeCard.jsx`):
   - Multi-severity styling (Red for `CRITICAL`/`HIGH`, Amber for `WARNING`, Blue for `ADVISORY`).
   - Distinct alert banner for `REQUIRES_REVERIFICATION` warnings.
   - Displays affected location, affected route, issuing authority, and official source link.
   - Clean, honest empty-state view for `NO_ACTIVE_NOTICES`.
2. **`VerifiedContactCard.jsx`** (`frontend/src/components/chat/cards/VerifiedContactCard.jsx`):
   - Prominent 112 Statutory Emergency Banner with direct `tel:112` dialing button.
   - Categorized directory (National Emergency, Shrine Board Assistance, Traffic Control, Local Police, Medical Ambulance).
   - Direct `tel:` links and operating hours indicators.
3. **`MessageItem.jsx`** (`frontend/src/components/chat/MessageItem.jsx`):
   - Imported and wired both cards to render within the chat message container when operational notices or contacts are present.

---

## 8. Verification & Test Matrix

### 8.1 Dedicated Phase 9.6.2 Test Suite
Executed `tests/test_phase9_6_2_curated_notices.py`: **17/17 tests passing (100%)**.

| # | Test Name | Invariant / Requirement Tested | Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_01_curated_notices_loading_and_dataclass_validation` | JSON catalog loading & `OperationalNotice` dataclass typing | **PASS** |
| 2 | `test_02_missing_or_corrupted_catalog_handling` | Missing/corrupt file returns `SOURCE_UNAVAILABLE` safely | **PASS** |
| 3 | `test_03_empty_registry_truth_in_data` | `NO_ACTIVE_NOTICES` honest advisory; no "smooth operations" claim | **PASS** |
| 4 | `test_04_future_effective_date_lifecycle` | Future `effective_from` receives `PUBLISHED` status | **PASS** |
| 5 | `test_05_active_validity_horizon_lifecycle` | Valid timeframe receives `ACTIVE` status | **PASS** |
| 6 | `test_06_horizon_expiration_handling_requires_reverification` | Expired `effective_until` transitions to `REQUIRES_REVERIFICATION` | **PASS** |
| 7 | `test_07_category_specific_24_hour_horizon_expiration` | Traffic advisory older than 24h becomes `REQUIRES_REVERIFICATION` | **PASS** |
| 8 | `test_08_explicit_withdrawal_persistence` | `WITHDRAWN` status remains preserved | **PASS** |
| 9 | `test_09_declared_superseding_relationship` | Explicit `supersedes_notice_id` marks older notice `SUPERSEDED` | **PASS** |
| 10 | `test_10_automatic_five_point_alignment_superseding` | Authority, location, route, category, and timestamp auto-supersede | **PASS** |
| 11 | `test_11_non_override_rule_media_cannot_supersede_official` | Unverified media report blocked from superseding official notice | **PASS** |
| 12 | `test_12_conflicting_notices_preservation` | Different authorities preserved together without silent dropping | **PASS** |
| 13 | `test_13_verified_contacts_loading_and_112_priority` | Directory loading and 112 strictly ordered as primary first | **PASS** |
| 14 | `test_14_contact_jurisdiction_filtering` | Jurisdiction filtering for Ramban/Jammu retains universal 112 | **PASS** |
| 15 | `test_15_unverified_contact_suppression` | Unverified contacts suppressed by default | **PASS** |
| 16 | `test_16_live_data_manager_integration` | `CuratedOperationalNoticesAdapter` & `VerifiedContactAdapter` via manager | **PASS** |
| 17 | `test_17_central_agent_tools_and_fallback_routing` | LangChain tools & deterministic conversational fallback routing | **PASS** |

### 8.2 Full Regression Suite
Executed all active test suites across the project: **353/353 tests passing (0 failures, 0 errors)**.

| Test Suite File | Coverage Scope | Tests | Result |
| :--- | :--- | :---: | :---: |
| `tests/test_phase9_6_2_curated_notices.py` | Curated Notices & Verified Contacts Registry | 17 | **PASS** |
| `tests/test_phase9_5_2_2_consistency.py` | Eager Lock Init & Accommodation Cache Path | 12 | **PASS** |
| `tests/test_phase9_5_2_remediation.py` | Provider Privacy, Concurrency & Half-Open Circuit Breaker | 25 | **PASS** |
| `tests/test_phase9_5_1_hardening.py` | Provenance Hardening, Cache Isolation & State Consistency | 20 | **PASS** |
| `tests/test_phase9_5_provider_framework.py` | Base Provider, Registry & Live Data Manager | 25 | **PASS** |
| `tests/test_phase9_3b_catalog.py` | Katra Accommodation Catalog Validation | 21 | **PASS** |
| `tests/test_phase9_3b_2_isolation.py` | Synthetic Accommodation Fallback Severance | 11 | **PASS** |
| `tests/test_phase8_1_weather.py` | Elevation-Aware Multi-Location Weather Integration | 35 | **PASS** |
| `tests/test_phase8_2_provenance.py` | Standardized Provenance Metadata & Envelope Attacher | 28 | **PASS** |
| `tests/test_phase8_3_cache.py` | Thread-Safe Multi-Tier Cache with Stale-If-Error | 32 | **PASS** |
| `tests/test_phase8_4_hybrid_orchestration.py` | Partial Tool Failure Transparency & Central Agent Routing | 35 | **PASS** |
| `tests/test_phase8_5_frontend_provenance.py` | Frontend Provenance Badges & Freshness Indicators | 22 | **PASS** |
| `tests/test_phase7_rag.py` | Vector Knowledge Retrieval & Ingestion | 24 | **PASS** |
| `tests/test_phase7_1_rag_reliability.py` | Knowledge Domain Scoring & Query Normalization | 26 | **PASS** |
| `tests/test_phase6_central_agent.py` | LangChain ChatGroq Tool-Calling Architecture | 20 | **PASS** |
| **Total** | **Comprehensive Full Project Regression Suite** | **353** | **100% PASS** |

---

## 9. Modified and Created Files Index

### 9.1 Created Files
- [`data/curated_operational_notices.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/data/curated_operational_notices.json): Official Shrine Board circulars (Mandatory RFID pass & advisory on unauthorized private agents).
- [`data/verified_contacts.json`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/data/verified_contacts.json): Official statutory emergency directive (112), Shrine Board Call Centre, Protocol Desk, TCUs, Police, Ambulance.
- [`services/operational_notices.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/operational_notices.py): Core notice service (lifecycle evaluation, 5-point alignment, aggregate status).
- [`services/verified_contacts.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/verified_contacts.py): Verified contact query service (jurisdiction matching, 112 ordering, unverified suppression).
- [`services/live_data/adapters/curated_operational_notices_adapter.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/curated_operational_notices_adapter.py): Provider adapter for `operational_notice`.
- [`services/live_data/adapters/curated_contact_adapter.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/curated_contact_adapter.py): Provider adapter for `emergency`.
- [`frontend/src/components/chat/cards/OperationalNoticeCard.jsx`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/cards/OperationalNoticeCard.jsx): Operational notice UI card component.
- [`frontend/src/components/chat/cards/VerifiedContactCard.jsx`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/cards/VerifiedContactCard.jsx): Verified contacts UI card component with 112 banner.
- [`tests/test_phase9_6_2_curated_notices.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_phase9_6_2_curated_notices.py): Dedicated 17-point test suite.
- [`project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_CURATED_OPERATIONAL_NOTICES_IMPLEMENTATION_REPORT.md`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_CURATED_OPERATIONAL_NOTICES_IMPLEMENTATION_REPORT.md): This technical report.

### 9.2 Modified Files
- [`services/live_data/contracts.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/contracts.py): Added `NoticeCategory`, `NoticeLifecycleStatus`, `NoticeAggregateStatus`, `ContactCategory`, `OperationalNotice`, `VerifiedContact`, and `LiveDataResult` properties.
- [`services/live_data/__init__.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/__init__.py): Exported new data contracts and models in `__all__`.
- [`services/live_data/adapters/__init__.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/__init__.py): Exported `CuratedOperationalNoticesAdapter` and `VerifiedContactAdapter`.
- [`services/live_data/manager.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/manager.py): Default provider registrations and `fetch_data()` alias.
- [`agents/central_agent.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/central_agent.py): Specialist tools `query_operational_notices` and `lookup_verified_contacts`, tool loop capture, and deterministic fallback routing.
- [`utils/provenance.py`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py): Provenance extraction and response envelope attachment for notices and contacts.
- [`frontend/src/components/chat/MessageItem.jsx`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/MessageItem.jsx): Integrated `OperationalNoticeCard` and `VerifiedContactCard`.
- [`project_reports/README.md`](file:///c:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/project_reports/README.md): Master report index updated.

---

## 10. Conclusion & Compliance Certification

Phase 9.6.2 successfully deploys a human-curated operational notice and emergency contact registry that strictly respects government web policies, guarantees epistemic truth-in-data, prevents route clearance hallucinations upon timer expiration, enforces statutory 112 priority, and maintains 100% test passing across the 353-test project matrix.

In accordance with strict checkpoint discipline, execution stops here without initiating Phase 9.6.3 or subsequent phases.
