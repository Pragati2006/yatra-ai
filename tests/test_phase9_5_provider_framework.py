"""
tests/test_phase9_5_provider_framework.py
Comprehensive Unit & Integration Test Suite for Yatra AI Phase 9.5 Live Data Architecture.

Tests all 25 specific requirements:
1. Abstract provider contract enforcement
2. Provider registration and lifecycle
3. Provider discovery and priority ordering
4. Unsupported domain handling
5. Missing provider handling
6. Missing credentials handling
7. Successful normalized result
8. Empty result handling
9. Provider timeout handling
10. Malformed provider response handling
11. Provider exception handling
12. Provenance attachment and schema validation
13. Timezone-aware retrieval timestamp validation
14. Upstream data timestamp preservation
15. Fast-path cache hit behavior
16. Cache miss behavior
17. Thread-safe single-flight coordination
18. Graceful stale-if-error fallback labeling
19. Private session cache key isolation
20. Mock provider simulation labeling
21. Curated accommodation adapter integration
22. Preservation of rooms_available=None
23. Preservation of availability_status=NOT_CHECKED and room_requirement_status=UNVERIFIED
24. Central Agent compatibility bridge
25. Zero unintended outbound network calls during local operations
"""

from concurrent.futures import ThreadPoolExecutor
import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from services.live_data.adapters.curated_accommodation_adapter import CuratedAccommodationAdapter
from services.live_data.adapters.mock_provider import MockTestLiveDataProvider
from services.live_data.adapters.weather_adapter import OpenMeteoWeatherAdapter
from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderMetadata,
    ProviderRequest,
)
from services.live_data.exceptions import (
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderMalformedResponseError,
    ProviderNotFoundError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from services.live_data.manager import (
    UnifiedLiveDataManager,
    get_live_data_manager,
    reset_live_data_manager,
)
from services.live_data.registry import ProviderRegistry
from utils.cache_manager import CacheManager, reset_cache_manager
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    validate_provenance,
)


class TestPhase95ProviderFramework(unittest.TestCase):
    """Test suite for Phase 9.5 live data provider framework and normalized contracts."""

    def setUp(self):
        """Set up fresh isolated manager and registry for each test."""
        reset_cache_manager()
        reset_live_data_manager()
        self.cache = CacheManager(max_entries=100)
        self.registry = ProviderRegistry()
        self.manager = UnifiedLiveDataManager(
            registry=self.registry,
            cache_manager=self.cache,
        )

    def tearDown(self):
        """Clean up singletons after each test."""
        reset_cache_manager()
        reset_live_data_manager()

    # -------------------------------------------------------------------------
    # Test 1: Abstract provider contract enforcement
    # -------------------------------------------------------------------------
    def test_01_abstract_provider_contract(self):
        """Verifies that subclassing BaseLiveDataProvider without abstract methods raises TypeError."""
        class IncompleteProvider(BaseLiveDataProvider):
            pass

        with self.assertRaises(TypeError):
            IncompleteProvider()

    # -------------------------------------------------------------------------
    # Test 2: Provider registration
    # -------------------------------------------------------------------------
    def test_02_provider_registration(self):
        """Verifies registering, retrieving, and listing providers in the registry."""
        mock_p = MockTestLiveDataProvider(provider_id="mock_test_1", domain=DataDomain.WEATHER.value)
        self.registry.register(mock_p)

        retrieved = self.registry.get_provider(DataDomain.WEATHER.value, "mock_test_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.provider_id, "mock_test_1")

        all_meta = self.registry.list_all_providers()
        self.assertEqual(len(all_meta), 1)
        self.assertEqual(all_meta[0].provider_id, "mock_test_1")
        self.assertTrue(all_meta[0].is_simulated)

    # -------------------------------------------------------------------------
    # Test 3: Provider discovery by priority order
    # -------------------------------------------------------------------------
    def test_03_provider_discovery_priority_order(self):
        """Verifies providers are discovered and sorted by priority ascending (10 > 50 > 100)."""
        p_low = MockTestLiveDataProvider(provider_id="low_prio", domain=DataDomain.WEATHER.value, priority=100)
        p_high = MockTestLiveDataProvider(provider_id="high_prio", domain=DataDomain.WEATHER.value, priority=10)
        p_mid = MockTestLiveDataProvider(provider_id="mid_prio", domain=DataDomain.WEATHER.value, priority=50)

        self.registry.register(p_low)
        self.registry.register(p_high)
        self.registry.register(p_mid)

        discovered = self.registry.get_providers_for_domain(DataDomain.WEATHER.value)
        self.assertEqual(len(discovered), 3)
        self.assertEqual(discovered[0].provider_id, "high_prio")
        self.assertEqual(discovered[1].provider_id, "mid_prio")
        self.assertEqual(discovered[2].provider_id, "low_prio")

    # -------------------------------------------------------------------------
    # Test 4: Unsupported domain
    # -------------------------------------------------------------------------
    def test_04_unsupported_domain_request(self):
        """Verifies requesting an unregistered or unsupported domain returns UNAVAILABLE cleanly."""
        req = ProviderRequest(domain="non_existent_domain", params={"test": 1})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.freshness_status, FreshnessStatus.UNAVAILABLE.value)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, ProviderErrorType.UNAVAILABLE.value)

    # -------------------------------------------------------------------------
    # Test 5: Missing provider
    # -------------------------------------------------------------------------
    def test_05_missing_provider(self):
        """Verifies querying a non-existent provider_id returns UNAVAILABLE result."""
        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"test": 1})
        result = self.manager.execute_request(req, provider_id="unknown_provider")

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, ProviderErrorType.UNAVAILABLE.value)
        self.assertIn("not registered", result.error.message)

    # -------------------------------------------------------------------------
    # Test 6: Missing credentials
    # -------------------------------------------------------------------------
    def test_06_missing_credentials(self):
        """Verifies a provider with is_configured() == False returns MISSING_CREDENTIALS."""
        unconfigured = MockTestLiveDataProvider(
            provider_id="unconfigured_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_MISSING_CREDS,
        )
        self.manager.register_provider(unconfigured)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={})
        result = self.manager.execute_request(req, provider_id="unconfigured_prov")

        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, ProviderErrorType.MISSING_CREDENTIALS.value)

    # -------------------------------------------------------------------------
    # Test 7: Successful normalized result
    # -------------------------------------------------------------------------
    def test_07_successful_normalized_result(self):
        """Verifies successful retrieval returns typed LiveDataResult with valid data."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_success",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"temp_c": 18.5, "condition": "Clear Sky"},
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        result = self.manager.execute_request(req)

        self.assertTrue(result.is_success)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.data["temp_c"], 18.5)
        self.assertEqual(result.provider_id, "mock_success")
        self.assertFalse(result.is_cached)

    # -------------------------------------------------------------------------
    # Test 8: Empty result
    # -------------------------------------------------------------------------
    def test_08_empty_result(self):
        """Verifies a provider returning empty data produces status=NO_RESULTS and empty list."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_empty",
            domain=DataDomain.ACCOMMODATION.value,
            scenario=MockTestLiveDataProvider.SCENARIO_EMPTY,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={"category": "5_Star"})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "NO_RESULTS")
        self.assertEqual(result.data, [])
        self.assertIsNotNone(result.advisory)

    # -------------------------------------------------------------------------
    # Test 9: Provider timeout
    # -------------------------------------------------------------------------
    def test_09_provider_timeout_handling(self):
        """Verifies provider execution timeout raises ProviderTimeoutError and is safely wrapped."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_timeout",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_TIMEOUT,
            timeout_seconds=0.1,  # Short timeout for fast test
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "ERROR")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, ProviderErrorType.TIMEOUT.value)
        self.assertIn("timed out", result.error.message.lower())

    # -------------------------------------------------------------------------
    # Test 10: Malformed provider response
    # -------------------------------------------------------------------------
    def test_10_malformed_provider_response(self):
        """Verifies malformed data exception is caught and wrapped without crashing."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_malformed",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_MALFORMED,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "ERROR")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, ProviderErrorType.UNKNOWN.value)

    # -------------------------------------------------------------------------
    # Test 11: Provider exception handling
    # -------------------------------------------------------------------------
    def test_11_provider_exception_handling(self):
        """Verifies unexpected provider exceptions are caught and sanitized."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_error",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_ERROR,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "ERROR")
        self.assertIsNotNone(result.error)
        self.assertIn("Simulated upstream provider", result.error.message)

    # -------------------------------------------------------------------------
    # Test 12: Provenance attachment and schema validation
    # -------------------------------------------------------------------------
    def test_12_provenance_attachment_and_validation(self):
        """Verifies result carries valid source_provenance conforming to utils/provenance.py."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_prov_test",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"loc": "Bhawan"})
        result = self.manager.execute_request(req)

        self.assertIsNotNone(result.source_provenance)
        is_valid, errors = validate_provenance(result.source_provenance)
        self.assertTrue(is_valid, f"Provenance validation failed: {errors}")
        self.assertEqual(result.source_provenance["source_type"], SourceType.SIMULATED_DATA.value)
        self.assertEqual(result.source_provenance["verification_status"], VerificationStatus.SIMULATION_ONLY.value)

    # -------------------------------------------------------------------------
    # Test 13: Timezone-aware retrieval timestamp validation
    # -------------------------------------------------------------------------
    def test_13_retrieval_timestamp_validation(self):
        """Verifies retrieval_timestamp is ISO 8601 with explicit timezone indicator."""
        prov = MockTestLiveDataProvider(provider_id="mock_ts", domain=DataDomain.WEATHER.value)
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={})
        result = self.manager.execute_request(req)

        ts = result.retrieval_timestamp
        self.assertTrue("+" in ts or ts.endswith("Z"), f"Timestamp not timezone-aware: {ts}")

    # -------------------------------------------------------------------------
    # Test 14: Upstream data timestamp preservation
    # -------------------------------------------------------------------------
    def test_14_data_timestamp_preservation(self):
        """Verifies upstream observation timestamp is preserved distinctly from retrieval timestamp."""
        res = LiveDataResult(
            status="SUCCESS",
            domain=DataDomain.WEATHER.value,
            data={"metric": 10},
            provider_id="test_provider",
            data_timestamp="2026-11-07T08:00:00+00:00",
            retrieval_timestamp="2026-11-07T09:15:00+00:00",
            freshness_status=FreshnessStatus.LIVE.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,
        )
        self.assertEqual(res.data_timestamp, "2026-11-07T08:00:00+00:00")
        self.assertNotEqual(res.data_timestamp, res.retrieval_timestamp)

    # -------------------------------------------------------------------------
    # Test 15: Cache hit behavior
    # -------------------------------------------------------------------------
    def test_15_cache_hit(self):
        """Verifies second query with same params returns fresh cache hit without provider re-fetch."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_cached_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})

        # Call 1: Miss and fetch
        res1 = self.manager.execute_request(req)
        self.assertEqual(prov.call_count, 1)
        self.assertFalse(res1.is_cached)

        # Call 2: Fresh cache hit
        res2 = self.manager.execute_request(req)
        self.assertEqual(prov.call_count, 1)  # Did not increment!
        self.assertTrue(res2.is_cached)
        self.assertEqual(res2.freshness_status, FreshnessStatus.CACHED.value)

    # -------------------------------------------------------------------------
    # Test 16: Cache miss behavior
    # -------------------------------------------------------------------------
    def test_16_cache_miss(self):
        """Verifies different parameters result in cache miss and trigger provider fetch."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_miss_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
        )
        self.manager.register_provider(prov)

        req1 = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        req2 = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Bhawan"})

        self.manager.execute_request(req1)
        self.assertEqual(prov.call_count, 1)

        self.manager.execute_request(req2)
        self.assertEqual(prov.call_count, 2)

    # -------------------------------------------------------------------------
    # Test 17: Thread-safe single-flight coordination
    # -------------------------------------------------------------------------
    def test_17_single_flight_coordination(self):
        """Verifies concurrent identical requests trigger exactly 1 provider fetch."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_single_flight",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})

        def _worker():
            return self.manager.execute_request(req)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_worker) for _ in range(5)]
            results = [f.result() for f in futures]

        # Verify exactly one actual provider execution
        self.assertEqual(prov.call_count, 1)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertTrue(r.is_success)

    # -------------------------------------------------------------------------
    # Test 18: Stale-if-error fallback labeling
    # -------------------------------------------------------------------------
    def test_18_stale_fallback_labeling(self):
        """Verifies that expired cache entries are returned with freshness_status='stale' when provider fails."""
        prov = MockTestLiveDataProvider(
            provider_id="mock_stale_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"temperature": 22.0},
        )
        self.manager.register_provider(prov)
        self.manager.set_cache_policy(DataDomain.WEATHER.value, ttl=0.1, max_stale=5.0)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})

        # Initial fetch to populate cache
        res1 = self.manager.execute_request(req)
        self.assertEqual(res1.status, "SUCCESS")

        # Wait for TTL to expire (0.1s), but within max_stale (5.0s)
        time.sleep(0.15)

        # Now simulate provider failure
        prov.scenario = MockTestLiveDataProvider.SCENARIO_ERROR

        # Retrieve again: should gracefully return stale cache
        res2 = self.manager.execute_request(req)
        self.assertEqual(res2.status, "SUCCESS")
        self.assertTrue(res2.is_cached)
        self.assertEqual(res2.freshness_status, FreshnessStatus.STALE.value)
        self.assertEqual(res2.data["temperature"], 22.0)
        self.assertIsNotNone(res2.advisory)

    # -------------------------------------------------------------------------
    # Test 19: Private session cache isolation
    # -------------------------------------------------------------------------
    def test_19_private_session_cache_isolation(self):
        """Verifies sensitive session IDs or auth tokens are stripped from cache params."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"category": "Deluxe", "auth_token": "secret_abc123", "user_id": 9999},
            session_id="session_devotee_42",
        )
        cache_params = req.to_cache_params()

        self.assertIn("category", cache_params)
        self.assertNotIn("auth_token", cache_params)
        self.assertNotIn("user_id", cache_params)
        self.assertNotIn("session_devotee_42", str(cache_params))

    # -------------------------------------------------------------------------
    # Test 20: Mock provider simulation labeling
    # -------------------------------------------------------------------------
    def test_20_mock_provider_simulation_labeling(self):
        """Verifies mock provider result is strictly labeled SIMULATED_DATA and SIMULATION_ONLY."""
        prov = MockTestLiveDataProvider(provider_id="sim_prov", domain=DataDomain.WEATHER.value)
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={})
        result = self.manager.execute_request(req)

        self.assertEqual(result.source_provenance["source_type"], SourceType.SIMULATED_DATA.value)
        self.assertEqual(result.source_provenance["verification_status"], VerificationStatus.SIMULATION_ONLY.value)

    # -------------------------------------------------------------------------
    # Test 21: Curated accommodation adapter integration
    # -------------------------------------------------------------------------
    def test_21_curated_accommodation_adapter_loading(self):
        """Verifies CuratedAccommodationAdapter loads verified Katra properties via manager."""
        adapter = CuratedAccommodationAdapter()
        self.assertTrue(adapter.is_configured())
        self.manager.register_provider(adapter)

        req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={})
        result = self.manager.execute_request(req)

        self.assertEqual(result.status, "SUCCESS")
        self.assertIsInstance(result.data, list)
        self.assertGreaterEqual(len(result.data), 13)
        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)

    # -------------------------------------------------------------------------
    # Test 22: Preservation of rooms_available=None
    # -------------------------------------------------------------------------
    def test_22_preservation_of_rooms_available_none(self):
        """Verifies curated adapter preserves rooms_available=None without fabricating counts."""
        adapter = CuratedAccommodationAdapter()
        self.manager.register_provider(adapter)

        req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={})
        result = self.manager.execute_request(req)

        self.assertTrue(result.is_success)
        for prop in result.data:
            self.assertIsNone(
                prop.get("rooms_available"),
                f"Property {prop.get('name')} should have rooms_available=None, got {prop.get('rooms_available')}",
            )

    # -------------------------------------------------------------------------
    # Test 23: Preservation of NOT_CHECKED and UNVERIFIED
    # -------------------------------------------------------------------------
    def test_23_preservation_of_not_checked_and_unverified(self):
        """Verifies multi-room requests preserve availability_status=NOT_CHECKED and room_requirement_status=UNVERIFIED."""
        adapter = CuratedAccommodationAdapter()
        self.manager.register_provider(adapter)

        req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={}, min_rooms=3)
        result = self.manager.execute_request(req)

        self.assertTrue(result.is_success)
        for prop in result.data:
            self.assertEqual(prop.get("availability_status"), "NOT_CHECKED")
            self.assertEqual(prop.get("room_requirement_status"), "UNVERIFIED")

    # -------------------------------------------------------------------------
    # Test 24: Central Agent compatibility bridge
    # -------------------------------------------------------------------------
    def test_24_central_agent_compatibility(self):
        """Verifies query_live_data_service in agents.central_agent integrates cleanly."""
        from agents.central_agent import query_live_data_service

        # Register curated accommodation adapter in global manager
        adapter = CuratedAccommodationAdapter()
        get_live_data_manager().register_provider(adapter)

        res = query_live_data_service(
            domain=DataDomain.ACCOMMODATION.value,
            params={"category": "SMVDSB"},
        )

        self.assertIsInstance(res, dict)
        self.assertIn("status", res)
        self.assertIn("domain", res)
        self.assertIn("source_provenance", res)
        self.assertEqual(res["domain"], DataDomain.ACCOMMODATION.value)

    # -------------------------------------------------------------------------
    # Test 25: Zero unintended network calls during local operations
    # -------------------------------------------------------------------------
    def test_25_no_unintended_network_requests(self):
        """Verifies framework initialization, adapter loading, and catalog queries execute 100% locally."""
        with patch("urllib.request.urlopen") as mock_urlopen, patch("requests.Session.send") as mock_send:
            manager = UnifiedLiveDataManager()
            adapter = CuratedAccommodationAdapter()
            manager.register_provider(adapter)

            req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={})
            result = manager.execute_request(req)

            self.assertTrue(result.is_success)
            mock_urlopen.assert_not_called()
            mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
