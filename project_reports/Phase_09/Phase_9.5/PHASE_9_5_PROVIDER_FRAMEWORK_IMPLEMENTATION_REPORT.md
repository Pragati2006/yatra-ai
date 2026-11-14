# Phase 9.5: Provider Framework & Normalized Contracts Implementation Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly untouched at HEAD `8996d6a8e3bc83eda0808d0a9ca217979118ebee`)
**Workspace Python Runtime:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Implementation Date:** November 7, 2026
**Status:** Completed & Validated (295/295 tests passing)

---

## Executive Summary

Phase 9.5 establishes the pluggable, provider-independent live data architecture for Yatra AI. It provides an extensible abstraction layer that enables diverse upstream data sources (weather forecasts, curated accommodations, future operational notices, and emergency registries) to supply information to conversational agents and API routes through normalized, typed response contracts.

The architecture directly reuses the existing provenance engine ([`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py)) and in-memory cache manager ([`utils/cache_manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/cache_manager.py)). No external live scraping, CAPTCHA bypass, or unauthorized API calls were made. The implementation is verified through 25 new dedicated unit and integration tests in [`tests/test_phase9_5_provider_framework.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_phase9_5_provider_framework.py), with all 295 regression tests passing without error.

---

## 1. Files Created and Modified

### 1.1 New Files Created

| File Path | Component | Description |
| :--- | :--- | :--- |
| [`services/live_data/__init__.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/__init__.py) | Package Init | Exports public contracts, exceptions, registry, and manager accessors. |
| [`services/live_data/contracts.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/contracts.py) | Normalized Contracts | Defines `LiveDataResult`, `ProviderRequest`, `ProviderError`, `ProviderMetadata`, and enums (`DataDomain`, `ProviderLifecycle`, `ProviderErrorType`). |
| [`services/live_data/exceptions.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/exceptions.py) | Exceptions | Standard exception hierarchy (`LiveDataError`, `ProviderTimeoutError`, `ProviderValidationError`, etc.). |
| [`services/live_data/base.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/base.py) | Abstract Base Class | Enforces provider contracts (`BaseLiveDataProvider`) with input validation, timeout defaults, and provenance generation. |
| [`services/live_data/registry.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/registry.py) | Provider Registry | Thread-safe catalog of registered data providers with domain discovery and priority-ordered selection. |
| [`services/live_data/manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/manager.py) | Unified Manager | Coordinates provider execution, single-flight request deduplication, cache integration, and stale fallback. |
| [`services/live_data/adapters/__init__.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/__init__.py) | Adapters Init | Exports provider adapters. |
| [`services/live_data/adapters/curated_accommodation_adapter.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/curated_accommodation_adapter.py) | Curated Adapter | Bridges [`services/accommodation_catalog.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/accommodation_catalog.py) to the framework, strictly preserving `rooms_available=None` and `NOT_CHECKED`. |
| [`services/live_data/adapters/weather_adapter.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/weather_adapter.py) | Weather Adapter | Bridges [`weather.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/weather.py) elevation-aware multi-location forecasting without rewriting or making premature network calls. |
| [`services/live_data/adapters/mock_provider.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/adapters/mock_provider.py) | Mock Test Provider | Deterministic mock provider supporting success, empty, timeout, error, and malformed scenarios strictly labeled `SIMULATED_DATA`. |
| [`tests/test_phase9_5_provider_framework.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_phase9_5_provider_framework.py) | Test Suite | 25 exhaustive unit and integration tests validating contracts, registration, caching, provenance, and adapters. |

### 1.2 Existing Files Modified

| File Path | Nature of Modification | Purpose |
| :--- | :--- | :--- |
| [`agents/central_agent.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/central_agent.py) | Narrow Bridge Addition | Appended `query_live_data_service()` bridge at end of file, preserving all existing LangChain tools, session stores, and booking logic. |

---

## 2. Provider Abstraction Design

The core interface [`BaseLiveDataProvider`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/base.py) enforces standard behavior for all current and future data providers:

- **Identification:** Each provider declares an immutable `provider_id` (e.g., `"curated_katra_catalog"`) and human-readable `provider_name`.
- **Domain Specialization:** Declares supported domain via `domain` property (`weather`, `accommodation`, `operational_notice`, `capacity`, `emergency`, `transport`).
- **Configuration & Readiness:** `is_configured()` performs local-only checks (verifying environment variables or required disk files) without making outbound network requests during import or registration.
- **Request Invariants:** `validate_request()` asserts domain alignment and parameter sanity before execution.
- **Execution & Timeout:** `fetch_live_data()` defines the execution contract with a configurable `timeout_seconds` limit (default: 5.0 seconds).
- **Provenance Factory:** `build_provenance()` automatically produces validated metadata dictionaries conforming to [`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py).

---

## 3. Normalized Data Contracts

All data structures are strongly typed dataclasses in [`services/live_data/contracts.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/contracts.py):

### 3.1 `LiveDataResult`
Unified container returned to callers:
- `status`: String state (`"SUCCESS"`, `"NO_RESULTS"`, `"ERROR"`, `"UNAVAILABLE"`, `"FALLBACK"`).
- `domain`: Canonical domain identifier.
- `data`: Typed payload or list of records.
- `provider_id`: Unique identifier of the executing provider.
- `source_provenance`: Fully validated provenance record dictionary.
- `retrieval_timestamp`: ISO 8601 UTC timestamp of retrieval.
- `data_timestamp`: Upstream publication/observation timestamp (preserved distinctly).
- `freshness_status`: Provenance freshness (`"live"`, `"cached"`, `"stale"`, `"not_applicable"`, `"simulated"`).
- `verification_status`: Epistemic verification grade (`"verified_external_api"`, `"verified_curated_source"`, `"simulation_only"`, `"unverified"`).
- `error`: Optional `ProviderError` object.
- `advisory`: Human-readable user advisory note.
- `is_cached`: Boolean indicating whether the result was served from cache.
- `cached_state`: Cache state indicator (`"fresh"`, `"stale"`, `"miss"`, or `None`).

### 3.2 `ProviderError`
Sanitized failure container:
- `error_type`: Standardized enum (`UNAVAILABLE`, `MISSING_CREDENTIALS`, `TIMEOUT`, `RATE_LIMIT`, `INVALID_RESPONSE`, `AUTH_FAILURE`, `UNSUPPORTED_OPERATION`, `NO_RESULTS`, `VALIDATION_ERROR`, `UNKNOWN`).
- `message`: Sanitized error description. Automatically redacts API keys, bearer tokens, passwords, and sensitive identifiers.
- `provider_id`: Identifier of failing provider.
- `domain`: Associated domain.

### 3.3 `ProviderRequest`
Validated request container:
- `domain`: Target data domain.
- `params`: Query parameters.
- `location`: Optional location key or name.
- `date_range`: Optional tuple of `(start_date, end_date)` in `YYYY-MM-DD` format.
- `freshness_preference`: Optional preference (`"cached_ok"`, `"live_preferred"`, `"force_refresh"`).
- `session_id`: Optional private session identifier.
- `to_cache_params()`: Method that explicitly filters out `session_id`, user IDs, and auth tokens so private session data is never embedded into public cache keys.

### 3.4 `ProviderMetadata`
Discovery and registry representation:
- `provider_id`, `provider_name`, `domain`, `is_configured`, `priority`, `capabilities`, `is_simulated`.

---

## 4. Provider Lifecycle & Selection Strategy

### 4.1 Lifecycle States
Providers cycle through seven defined states:
1. `CONFIGURED`: Local prerequisites met.
2. `UNAVAILABLE`: Local prerequisites missing or provider disabled.
3. `REQUEST_SUCCESS`: Execution completed and returned usable data.
4. `NO_RESULTS`: Execution completed successfully but returned zero matching records.
5. `TIMED_OUT`: Upstream request exceeded configured timeout.
6. `MALFORMED_DATA`: Upstream returned unparseable or schema-violating payload.
7. `ERROR`: Upstream network failure, HTTP 5xx, or unexpected exception.

### 4.2 Selection Strategy
When a query arrives at [`UnifiedLiveDataManager`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/manager.py):
1. **Explicit Selection:** If `provider_id` is specified, the manager uses only that provider. If unconfigured or missing, returns an explicit error without falling back to unrelated providers.
2. **Domain Discovery:** If no provider is specified, queries [`ProviderRegistry`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/services/live_data/registry.py) for configured providers in the target domain.
3. **Priority Ordering:** Candidates are sorted by `priority` ascending (e.g., priority 10 precedes priority 100). The highest-ranked configured provider is executed.
4. **Fallback Handling:** If no configured provider exists, returns a structured `UNAVAILABLE` result with clear user advisories. Never fabricates data.

---

## 5. Provenance Mapping & Truth-in-Data Grounding

The framework strictly enforces existing provenance enums from [`utils/provenance.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/provenance.py):

| Outcome | `SourceType` | `FreshnessStatus` | `VerificationStatus` |
| :--- | :--- | :--- | :--- |
| **Live API Success** | `live_api` | `live` | `verified_external_api` |
| **Fresh Cache Hit** | `cached_api` | `cached` | `verified_external_api` |
| **Expired Cache Fallback** | `cached_api` | `stale` | `verified_external_api` |
| **Curated Catalog** | `curated_data` | `not_applicable` | `verified_curated_source` |
| **Mock Demonstration** | `simulated_data` | `simulated` | `simulation_only` |
| **Provider Failure / Outage** | `unknown_source` | `unavailable` | `unverified` |

- **Timestamp Integrity:** `retrieval_timestamp` records when Yatra AI executed the request; `data_timestamp` preserves upstream observation times.
- **Non-Masquerading Rule:** Curated static catalog data is never marked as `live`. Mock test data is never marked as `verified_external_api`.

---

## 6. Cache Coordination & Concurrency

The manager directly integrates with [`utils/cache_manager.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/utils/cache_manager.py):

- **Domain-Specific Freshness Policies:**
  - `weather`: 1,800s (30m) TTL, 21,600s (6h) max stale.
  - `accommodation`: 900s (15m) TTL, 3,600s (1h) max stale.
  - `operational_notice`: 900s (15m) TTL, 7,200s (2h) max stale.
  - `capacity`: 900s (15m) TTL, 14,400s (4h) max stale.
  - `emergency`: 604,800s (7d) TTL, 2,592,000s (30d) max stale.
  - `transport`: 86,400s (24h) TTL, 604,800s (7d) max stale.
- **Single-Flight Request Coordination:** Identical concurrent queries wait on an internal lock; only the first thread executes the upstream fetch, and all other threads consume the cached result.
- **Graceful Stale-if-Error:** If an upstream provider times out or fails, the manager returns the expired cache entry tagged with `freshness_status="stale"`, `is_cached=True`, and an explanatory user advisory.

---

## 7. Security and Compliance Boundaries

1. **Zero Secret Exposure:** `ProviderError` sanitizes error messages using regex redaction, stripping tokens, API keys, passwords, and bearer headers before returning results.
2. **Session Isolation:** `ProviderRequest.to_cache_params()` excludes session IDs and user tokens, preventing cache-poisoning or cross-session data leakage.
3. **Local-Only Import & Initialization:** No provider makes network calls during module import, class instantiation, or registry inspection.
4. **Human-in-the-Loop Preserved:** Booking authorization routes and rules remain completely untouched.

---

## 8. Verification & Test Execution

### 8.1 New Test Suite (`tests/test_phase9_5_provider_framework.py`)

All 25 mandatory test cases were executed against Python 3.12.4:

```powershell
& "C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe" -m unittest tests/test_phase9_5_provider_framework.py -v
```

**Results:**
```text
Ran 25 tests in 4.966s
OK
```

**Coverage Breakdown:**
1. `test_01_abstract_provider_contract`: Subclassing without abstract methods raises `TypeError`. [PASSED]
2. `test_02_provider_registration`: Registering, retrieving, and listing metadata works. [PASSED]
3. `test_03_provider_discovery_priority_order`: Priorities 10, 50, 100 sort ascending. [PASSED]
4. `test_04_unsupported_domain_request`: Unregistered domain returns `UNAVAILABLE`. [PASSED]
5. `test_05_missing_provider`: Unknown provider ID returns `UNAVAILABLE` result. [PASSED]
6. `test_06_missing_credentials`: `is_configured()==False` returns `MISSING_CREDENTIALS`. [PASSED]
7. `test_07_successful_normalized_result`: Valid payload returns `SUCCESS` and data. [PASSED]
8. `test_08_empty_result`: Empty provider returns `NO_RESULTS` with empty list. [PASSED]
9. `test_09_provider_timeout_handling`: Timeout is caught and wrapped as `TIMEOUT` error. [PASSED]
10. `test_10_malformed_provider_response`: Corrupt data is caught and returned as `UNKNOWN` error. [PASSED]
11. `test_11_provider_exception_handling`: Unexpected exceptions caught and sanitized. [PASSED]
12. `test_12_provenance_attachment_and_validation`: Provenance passes `validate_provenance()`. [PASSED]
13. `test_13_retrieval_timestamp_validation`: Timestamp is timezone-aware ISO 8601 UTC. [PASSED]
14. `test_14_data_timestamp_preservation`: Distinct observation timestamp preserved. [PASSED]
15. `test_15_cache_hit`: Second query returns cached data without provider re-fetch. [PASSED]
16. `test_16_cache_miss`: Distinct parameters trigger provider fetch. [PASSED]
17. `test_17_single_flight_coordination`: 5 concurrent threads trigger exactly 1 fetch. [PASSED]
18. `test_18_stale_fallback_labeling`: Expired entry returns `stale` when provider fails. [PASSED]
19. `test_19_private_session_cache_isolation`: Sensitive tokens stripped from cache keys. [PASSED]
20. `test_20_mock_provider_simulation_labeling`: Mock strictly tagged `SIMULATED_DATA`. [PASSED]
21. `test_21_curated_accommodation_adapter_loading`: 15 properties loaded via adapter. [PASSED]
22. `test_22_preservation_of_rooms_available_none`: `rooms_available` remains `None`. [PASSED]
23. `test_23_preservation_of_not_checked_and_unverified`: Multi-room marked `UNVERIFIED`. [PASSED]
24. `test_24_central_agent_compatibility`: Central Agent bridge retrieves data. [PASSED]
25. `test_25_no_unintended_network_requests`: Local execution makes 0 HTTP calls. [PASSED]

### 8.2 Full Regression Test Suite

All test suites across the repository were executed together:

| Test Suite | Scope | Tests Run | Passed | Failed | Blocked |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `tests/test_phase9_5_provider_framework.py` | Provider Framework & Contracts | 25 | 25 | 0 | 0 |
| `tests/test_phase9_3b_2_isolation.py` | Synthetic Accommodation Isolation | 14 | 14 | 0 | 0 |
| `tests/test_phase9_3b_catalog.py` | Curated Katra Catalog Verification | 18 | 18 | 0 | 0 |
| `tests/test_phase8_5_frontend_provenance.py`| Frontend Provenance Verification | 22 | 22 | 0 | 0 |
| `tests/test_phase8_4_hybrid_orchestration.py`| Central Agent Orchestration | 30 | 30 | 0 | 0 |
| `tests/test_phase8_3_cache.py` | In-Memory Freshness & Caching | 40 | 40 | 0 | 0 |
| `tests/test_phase8_2_provenance.py` | Provenance Metadata & Tracking | 33 | 33 | 0 | 0 |
| `tests/test_phase8_1_weather.py` | Open-Meteo Weather Service | 27 | 27 | 0 | 0 |
| `tests/test_phase7_rag.py` | Vector Knowledge Retrieval | 25 | 25 | 0 | 0 |
| `tests/test_phase7_1_rag_reliability.py` | RAG Fallback & Reliability | 25 | 25 | 0 | 0 |
| `tests/test_phase6_central_agent.py` | Central Conversational Agent | 20 | 20 | 0 | 0 |
| `tests/test_budget_engine.py` | Trip Budget Engine | 16 | 16 | 0 | 0 |
| **Total** | **All Phase Suites** | **295** | **295** | **0** | **0** |

*(Note: 3 standalone legacy database test files expecting a prepopulated SQLite database during broad test discovery remain excluded, as established in Phase 8.6).*

---

## 9. Known Limitations & Future Integration Requirements

1. **Framework-Level Scope:** Phase 9.5 establishes the provider architecture and adapters for existing services (`weather.py` and `accommodation_catalog.py`). It does not connect commercial hotel APIs or external web scrapers.
2. **Upcoming Operational Notices (Phase 9.6):** The framework is now ready to receive the official notice poller for SMVDSB announcements and J&K Traffic Police NH-44 advisories.
3. **Upcoming Emergency Registry (Phase 9.7):** The emergency registry adapter will be integrated in Phase 9.7 following this standardized provider interface.

---

## 10. Conclusion & Acceptance Recommendation

Phase 9.5 has satisfied all technical objectives and testing mandates:
- Reusable, provider-independent live data architecture established.
- Normalized data contracts and sanitized error handling implemented.
- Provenance engine and thread-safe cache engine fully reused.
- Curated accommodation availability semantics strictly preserved.
- 25 dedicated tests and 295 regression tests passing (100% pass rate).
- Backup repository [`yatra-booking-agent`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-booking-agent) remains untouched.

**Recommendation:** Formally accept Phase 9.5 and authorize progression to Phase 9.6 (Official Operational Notices & Traffic Advisory Poller).
