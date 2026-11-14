# PHASE 9.8.1.2 — TRANSPORT TRUTHFULNESS & DATA INTEGRITY REMEDIATION REPORT
## Yatra AI — Unified Pilgrimage & Tourism Assistant

**Author:** Senior Software Architect, AI Agent Systems Engineer & Data Verification Auditor
**Date:** 2026-11-08
**Repository:** `yatra-ai`
**Active Branch:** `main`
**Baseline Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Phase Status:** Fully Completed & Verified

---

## 1. Executive Summary

Phase 9.8.1.2 was executed following the accepted findings of **Phase 9.8.1.1 (Nationwide Bus Transport Coverage & Data Integrity Audit)**. The audit identified four critical defects where default fallbacks and synthetic data conflated unevidenced estimates with authentic schedules:

1. **D-01 (Silent Delhi Defaulting):** The orchestrator, central agent, and legacy planners silently defaulted missing origins to "Delhi", inventing journeys from Delhi when pilgrims never specified an origin. Furthermore, `REGION_TO_HUB` routed Northern pilgrims (Punjab, Himachal Pradesh, Kashmir) South to Delhi before routing North to Katra, fabricating a 1,000 km unnecessary detour.
2. **D-02 (Fabricated Frontend Fallbacks):** `TransportMiniCard.jsx` hardcoded `fare || 1650`, `depTime || '06:00 AM'`, `arrTime || '02:00 PM'`, and `status || 'AVAILABLE'`, presenting fictitious fares and times whenever transport options lacked explicit pricing or timings.
3. **D-03 (Record-Level Verification Conflation):** `CuratedBusSchedule` used a monolithic `verification_status` flag that conflated route existence with timetable frequency and ticket counter tariffs.
4. **D-04 (Unevidenced Claims in Registry):** The curated bus dataset claimed an unevidenced fixed 60-minute frequency for Jammu GBS, an unevidenced continuous shuttle SLA for Jammu Railhead, and an unevidenced 75-minute frequency for Udhampur feeder.

Through targeted, fail-closed remediation across contracts, data registries, routing managers, and UI components, all four defects have been remediated with zero regressions. The test suite expanded to **410 passing automated tests across 19 modules** (0 failures, 0 errors), with full frontend production build validation (`npm run build` in 1.49s).

---

## 2. Mandatory Repository Safety & Non-Negotiable Rules Audit

| Requirement | Audit Finding | Status |
| :--- | :--- | :--- |
| **Workspace Isolation** | All work performed strictly within `yatra-ai`. | **COMPLIANT** |
| **Backup Repository** | `yatra-booking-agent` inspected and strictly untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`. | **COMPLIANT** |
| **Git Safety** | Zero commits, zero pushes, zero resets, zero stashes, zero cleans performed. | **COMPLIANT** |
| **Dependency Safety** | Zero packages installed; purely local Python standard library and existing dependencies used. | **COMPLIANT** |
| **API Cost & Subscriptions** | Zero paid APIs, zero subscriptions, zero credit card requirements. | **COMPLIANT** |
| **Scope Enforcement** | Flight provider (Phase 9.8.2) and nationwide registry expansion strictly excluded. | **COMPLIANT** |

---

## 3. Detailed Remediation Actions

### 3.1 D-01: Silent Delhi Default Removal & Regional Corridor Coherence

1. **Orchestrator Pipeline (`agents/orchestrator.py`):**
   - **`coordinate_plan` (Line 431):** Removed `origin = req.get("origin", "Delhi")`. When `origin` is missing or blank, `coordinate_plan` immediately returns `status="NEEDS_INFO"` with `missing_fields=["origin"]` and a polite clarification prompt asking the pilgrim for their departure location without assuming Delhi.
   - **`_format_consolidated_reply` (Line 759):** Replaced silent `"Delhi"` fallback with `origin = req.get("origin") or tr.get("origin") or "your departure city"`.
   - **`format_concise_edit_reply` (Line 804):** Replaced `origin = req.get("origin", "Delhi")` with `origin = req.get("origin") or "your departure city"`.
   - **`_format_cost_breakdown` (Line 908):** Sourced route label from `display_route` or `f"{origin} → Katra"` if origin exists, avoiding fabricated Delhi journey headers.
   - **`confirm_and_book_plan` (Line 1488):** Replaced `origin = req.get("origin", "Delhi")` with `origin = req.get("origin") or tr.get("origin") or "your departure city"`.

2. **Central Agent Tool (`agents/central_agent.py`):**
   - In `search_transport_options`: When `origin` is empty or None, returns an explicit clarification schema (`{"status": "MISSING_ORIGIN", "requires_clarification": True, "message": "Please specify your departure city or town to check suitable travel options to Katra."}`).

3. **Regional Transit Alignment (`agent.py`):**
   - In `REGION_TO_HUB`: Replaced incorrect mappings that routed Northern regions (Punjab, Himachal Pradesh, Kashmir) to Delhi. Mapped `chandigarh`, `amritsar`, `ludhiana`, `jalandhar`, `punjab`, `shimla`, `dharamshala`, `manali`, `himachal`, `himachal pradesh`, and `srinagar` to `Jammu` (the natural gateway corridor to Katra). This completely eliminates counter-directional 1,000 km Southward detours.

### 3.2 D-02: Elimination of Fabricated Frontend Fallbacks

1. **`TransportMiniCard.jsx` (`frontend/src/components/chat/cards/TransportMiniCard.jsx`):**
   - **Tariff Display:** Removed `fare || 1650`. Implemented honest multi-tier tariff formatting:
     - Numeric fare > 0: `₹{fare}/seat`
     - Indicative range: `₹{min}–₹{max}`
     - Statutory tariff slab: `Statutory Tariff Slab`
     - Missing / unverified: `Tariff at counter` (NEVER `₹1650/seat`).
   - **Departure Time:** Removed `'06:00 AM'` fallback. Uses `departure_time` or `departure_window` or `operating_hours` or `'Schedule at counter'` (NEVER `'06:00 AM'`).
   - **Arrival Time:** Removed `'02:00 PM'` fallback. Uses `arrival_time` or `~{duration_hours}h journey` or `'Enquire at counter'`.
   - **Status Pill:** Removed `'AVAILABLE'` fallback. Uses `status || availability || (mode === 'BUS' ? 'REGULAR SERVICE' : 'ROUTE GUIDANCE')`.
   - **Attribution & Provenance:** Preserved `Indicative Timetable` and `confirmation` disclaimer strings, ensuring 100% backward compatibility with Checkpoint 8.5 tests.

2. **`TransportCard.jsx` (`frontend/src/components/TransportCard.jsx`):**
   - Removed `'06:00'`, `'14:00'`, and `'Delhi'` fallbacks. Sourced departures from timetable windows or `'Schedule at counter'`, origin from `'Departure Point'`, and arrival from duration or counter inquiries.

### 3.3 D-03: Claim-Level Transport Verification Architecture

1. **Contract Definition (`services/live_data/contracts.py`):**
   - Added `ClaimVerification` dataclass:
     ```python
     @dataclass
     class ClaimVerification:
         status: str = VerificationStatus.UNVERIFIED.value
         source_name: Optional[str] = None
         source_url: Optional[str] = None
         document_reference: Optional[str] = None
         effective_date: Optional[str] = None
         verified_at: Optional[str] = None
         verified_by: Optional[str] = None
         notes: Optional[str] = None
     ```
   - Extended `CuratedBusSchedule` with four distinct claim verifications:
     - `route_verification: Optional[ClaimVerification]`
     - `operator_verification: Optional[ClaimVerification]`
     - `timetable_verification: Optional[ClaimVerification]`
     - `fare_verification: Optional[ClaimVerification]`
   - Implemented strict fail-closed downgrade rules in `CuratedBusSchedule.__post_init__`:
     - If `timetable_verification` references a generic root URL or has an unpublished / guidance document reference, status is automatically downgraded to `INDICATIVE_INFORMATION`.
     - If `fare_classification == "ESTIMATED_MARKET_TARIFF"`, fare claim status cannot be `VERIFIED_OFFICIAL_SOURCE` and is downgraded to `INDICATIVE_INFORMATION`.

2. **Provenance Enum Extension (`utils/provenance.py` & `provenanceUtils.js`):**
   - Added `PARTIALLY_VERIFIED = "partially_verified"` and `INDICATIVE_INFORMATION = "indicative_information"` to `VerificationStatus` and frontend `VERIFICATION_LABELS`.

### 3.4 D-04: Curated Bus Dataset Corrections (`data/curated_bus_schedules.json`)

All four existing corridors were audited and updated to reflect verified public evidence:

| Corridor ID | Origin Bus Stand | Operating Hours / Window | Frequency Minutes | Fare Classification | Route Claim | Operator Claim | Timetable Claim | Fare Claim |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `bus_jksrtc_jammu_katra_exp` | Jammu General Bus Stand (GBS) | 05:00 to 22:00 (Regular stage carriage departures based on passenger flow) | `null` (stripped unevidenced 60m guarantee) | `STATUTORY_NOTIFIED_PER_KM_SLAB` (₹75–₹110) | `verified_official_source` | `verified_official_source` | `indicative_information` | `partially_verified` |
| `bus_jksrtc_railhead_katra_shuttle` | Jammu Tawi Station (Rail Head Complex) | 05:30 to 21:00 (Train connection window) | `null` (stripped continuous shuttle claim) | `STATUTORY_NOTIFIED_PER_KM_SLAB` (₹80–₹120) | `verified_official_source` | `verified_official_source` | `unverified` | `partially_verified` |
| `bus_udhampur_katra_feeder` | Udhampur Bus Stand | 06:00 to 18:30 (Daylight Hours) | `null` (stripped fabricated 75m frequency) | `STATUTORY_NOTIFIED_PER_KM_SLAB` (₹50–₹90) | `verified_official_source` | `verified_curated_source` | `unverified` | `partially_verified` |
| `bus_jksrtc_delhi_katra_interstate` | Delhi ISBT Kashmiri Gate | 18:00 to 21:00 (Evening Departure Window) | `null` | `ESTIMATED_MARKET_TARIFF` (₹800–₹1,800) | `verified_official_source` | `verified_official_source` | `indicative_information` | `indicative_information` |

### 3.5 Unified Bus Tool Routing & Elimination of CSV Leakage

1. **Tools Unified Routing (`agents/tools.py`):**
   - Refactored `search_transport_tool` bus mode to query `UnifiedLiveDataManager.get_live_data_manager().execute_request(...)` with `provider_id="curated_bus_schedules"`.
   - Sourced bus options with verified provenance and `is_live_status=False`.
   - Unsupported origins return empty lists `[]` rather than falling back to synthetic bus rows.

2. **Elimination of Synthetic CSV Leakage (`db.py`):**
   - Refactored `get_distinct_origins()` to load authentic origins from `services.bus_schedules.load_curated_bus_schedules()` and `services.railway_schedules.load_curated_schedules()`.
   - Completely stopped reading `BUSES_LIVE` and `TRAINS_LIVE` CSVs for origin resolution.

---

## 4. Verification & Test Execution Matrix

### 4.1 Dedicated Phase 9.8.1.2 Remediation Test Suite (`tests/test_phase9_8_1_2_remediation.py`)

| Test Method | Description | Result |
| :--- | :--- | :--- |
| `test_01_coordinate_plan_missing_origin_requires_clarification` | Missing origin in `coordinate_plan` returns `NEEDS_INFO` and asks for departure location; never assumes Delhi. | **PASS** |
| `test_02_central_agent_missing_origin_requires_clarification` | Empty/None origin in `search_transport_options` returns `MISSING_ORIGIN` schema. | **PASS** |
| `test_03_regional_corridor_coherence_punjab_himachal_kashmir` | Amritsar, Chandigarh, Shimla, Srinagar map to Jammu; zero Southward detours via Delhi. | **PASS** |
| `test_04_get_distinct_origins_eliminates_synthetic_csv_leakage` | `db.get_distinct_origins()` returns authentic curated hubs; synthetic CSV cities (Patna, Bhopal) do not leak. | **PASS** |
| `test_05_claim_verification_contract_and_serialization` | `ClaimVerification` dataclass instantiates, validates, and serializes to dictionary. | **PASS** |
| `test_06_fail_closed_timetable_downgrade_on_generic_root_url` | Inconclusive timetable claims automatically downgrade to `indicative_information`. | **PASS** |
| `test_07_fail_closed_fare_downgrade_on_market_tariff` | Estimated market tariffs automatically downgrade to `indicative_information`. | **PASS** |
| `test_08_curated_bus_dataset_remediated_claims` | Audits all 4 corridors in `curated_bus_schedules.json`; confirms stripped frequencies and honest claim statuses. | **PASS** |
| `test_09_tools_routes_buses_via_unified_live_data_manager` | `search_transport_tool` bus mode routes via `UnifiedLiveDataManager`; unsupported origin returns `[]`. | **PASS** |
| `test_10_frontend_card_no_fabricated_fallbacks` | Confirms `TransportMiniCard.jsx` has zero `|| 1650`, zero `|| '06:00 AM'`, zero `|| '02:00 PM'`, zero `|| 'AVAILABLE'`. | **PASS** |

### 4.2 Full System Regression Matrix (19 Test Modules)

```
Ran 410 tests in 21.472s
OK (410/410 tests passing, 0 failures, 0 errors)
```

1. `tests.test_phase6_central_agent` (20 tests) — **PASS**
2. `tests.test_phase7_1_rag_reliability` (21 tests) — **PASS**
3. `tests.test_phase7_rag` (28 tests) — **PASS**
4. `tests.test_phase8_1_weather` (11 tests) — **PASS**
5. `tests.test_phase8_2_provenance` (22 tests) — **PASS**
6. `tests.test_phase8_3_cache` (14 tests) — **PASS**
7. `tests.test_phase8_4_hybrid_orchestration` (32 tests) — **PASS**
8. `tests.test_phase8_5_frontend_provenance` (22 tests) — **PASS**
9. `tests.test_phase9_3b_2_isolation` (12 tests) — **PASS**
10. `tests.test_phase9_3b_catalog` (26 tests) — **PASS**
11. `tests.test_phase9_5_1_hardening` (28 tests) — **PASS**
12. `tests.test_phase9_5_2_2_consistency` (18 tests) — **PASS**
13. `tests.test_phase9_5_2_remediation` (24 tests) — **PASS**
14. `tests.test_phase9_5_provider_framework` (23 tests) — **PASS**
15. `tests.test_phase9_6_2_curated_notices` (18 tests) — **PASS**
16. `tests.test_phase9_7_3_railway_foundation` (30 tests) — **PASS**
17. `tests.test_phase9_7_3a_railway_remediation` (20 tests) — **PASS**
18. `tests.test_phase9_8_1_bus_provider` (31 tests) — **PASS**
19. `tests.test_phase9_8_1_2_remediation` (10 tests) — **PASS**

### 4.3 Frontend Production Build Validation

```bash
$ npm run build
vite v8.3.4 building client environment for production...
✓ 109 modules transformed.
rendering chunks...
dist/index.html                   0.65 kB │ gzip:   0.39 kB
dist/assets/index-jngrsc2L.css   13.14 kB │ gzip:   3.34 kB
dist/assets/index-UrDtXZUr.js   573.86 kB │ gzip: 155.60 kB
✓ built in 1.49s
```

---

## 5. Artifacts and Deliverables

- **Implementation Report:** `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_2_TRANSPORT_TRUTHFULNESS_REMEDIATION_REPORT.md`
- **Updated Project Index:** `project_reports/README.md`
- **Brain Artifact:** `phase_9_8_1_2_transport_truthfulness_remediation_report.md`
- **Active Code Modifications:**
  - `yatra-ai/services/live_data/contracts.py`
  - `yatra-ai/services/bus_schedules.py`
  - `yatra-ai/services/live_data/manager.py`
  - `yatra-ai/data/curated_bus_schedules.json`
  - `yatra-ai/agents/orchestrator.py`
  - `yatra-ai/agents/central_agent.py`
  - `yatra-ai/agents/tools.py`
  - `yatra-ai/agent.py`
  - `yatra-ai/db.py`
  - `yatra-ai/utils/provenance.py`
  - `yatra-ai/frontend/src/components/chat/cards/TransportMiniCard.jsx`
  - `yatra-ai/frontend/src/components/TransportCard.jsx`
  - `yatra-ai/frontend/src/components/chat/provenance/provenanceUtils.js`
  - `yatra-ai/tests/test_phase9_8_1_2_remediation.py`

---

## 6. Conclusion & Next Steps

Phase 9.8.1.2 has definitively solved the transport truthfulness and origin-handling issues in Yatra AI. The system never invents Delhi as a default origin, never fabricates fares or departure times in frontend cards, properly segments claims into fine-grained provenance records, and accurately routes regional transport through authentic corridors.

**Recommended Next Step:**
Wait for the project owner's explicit prompt before proceeding to **Phase 9.8.2 (Curated Flight Registry & Passenger Airline Adapter)** or any future milestone.
