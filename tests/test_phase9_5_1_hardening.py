"""
tests/test_phase9_5_1_hardening.py
Comprehensive Unit & Integration Test Suite for Yatra AI Phase 9.5.1:
Provenance, Cache Safety & Provider State Hardening.

Covers:
1. Provenance Hardening:
   - Known verified provider (is_source_verified=True) -> VERIFIED_EXTERNAL_API.
   - Unverified provider (is_source_verified=False) -> UNVERIFIED despite HTTP 200 / success.
   - Schema validation failure -> downgraded to UNVERIFIED with advisory.
   - Stale observation timestamp (data_timestamp > max_stale) -> marked STALE.
   - Truth-in-data: Curated cannot be live.
   - Truth-in-data: Simulated cannot be verified_external_api.
   - Truth-in-data: Unavailable cannot be verified_external_api.

2. Emergency Data Cache Safety:
   - Stale cache hit in 'emergency' domain attaches mandatory 112 life-safety advisory.
   - Emergency provider failure with no cache returns statutory numbers (112, 108, 100)
     without fabricating private hospital/bed occupancy.
   - Unverified emergency provider cannot masquerade as official Shrine Board / Gov source.

3. Shared Public Cache Privacy Hardening:
   - Explicit private request (is_private_request=True) bypasses shared cache completely.
   - Request with sensitive booking/PII keywords (booking_id, pnr, aadhaar) detected as private.
   - Private requests are never stored in or served from shared public cache.
   - Cross-session isolation: User A's private data cannot be retrieved by User B.

4. Provider Lifecycle & State Consistency:
   - Unconfigured provider -> UNCONFIGURED.
   - Configured provider starts at CONFIGURED_PENDING_VERIFICATION.
   - Successful execution transitions to OPERATIONAL and updates last_verified_timestamp.
   - Failure increments consecutive_failures and sets DEGRADED.
   - 3 consecutive failures transitions to UNAVAILABLE (circuit breaker tripped).
   - Successful execution resets consecutive_failures and restores OPERATIONAL.
   - NO_RESULTS is a valid query outcome, distinct from UNAVAILABLE, and does not degrade provider.
   - TIMEOUT is distinct from NO_RESULTS and records provider failure.
"""

from datetime import datetime, timedelta, timezone
import unittest

from services.live_data.adapters.curated_accommodation_adapter import CuratedAccommodationAdapter
from services.live_data.adapters.mock_provider import MockTestLiveDataProvider
from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderOperationalStatus,
    ProviderRequest,
)
from services.live_data.manager import (
    EMERGENCY_CRITICAL_ADVISORY,
    STATUTORY_EMERGENCY_DATA,
    STATUTORY_EMERGENCY_DISCLAIMER,
    UnifiedLiveDataManager,
    reset_live_data_manager,
)
from services.live_data.registry import ProviderRegistry
from utils.cache_manager import CacheManager, reset_cache_manager
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    create_provenance,
    get_utc_now_iso,
    validate_provenance,
)


class TestPhase951Hardening(unittest.TestCase):
    """Rigorous verification suite for Phase 9.5.1 hardening requirements."""

    def setUp(self):
        """Set up fresh isolated cache manager and live data manager."""
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

    # =========================================================================
    # 1. PROVENANCE VERIFICATION HARDENING
    # =========================================================================

    def test_01_known_verified_provider_provenance(self):
        """Verified provider (is_source_verified=True) returns VERIFIED_EXTERNAL_API."""
        prov = MockTestLiveDataProvider(
            provider_id="verified_met_feed",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            is_simulated=False,
            is_source_verified=True,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        res = self.manager.execute_request(req)

        self.assertTrue(res.is_success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_EXTERNAL_API.value)
        self.assertEqual(res.source_provenance["verification_status"], VerificationStatus.VERIFIED_EXTERNAL_API.value)

    def test_02_unverified_provider_cannot_claim_verified_external_api(self):
        """Unverified provider (is_source_verified=False) returns UNVERIFIED despite 200/success."""
        prov = MockTestLiveDataProvider(
            provider_id="third_party_scraper",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            is_simulated=False,
            is_source_verified=False,  # Unverified!
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        res = self.manager.execute_request(req)

        self.assertTrue(res.is_success)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertEqual(res.source_provenance["verification_status"], VerificationStatus.UNVERIFIED.value)

    def test_03_schema_validation_failure_downgrades_to_unverified(self):
        """Payload failing schema validation cannot claim VERIFIED_EXTERNAL_API."""
        prov = MockTestLiveDataProvider(
            provider_id="faulty_schema_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SCHEMA_INVALID,
            is_simulated=False,
            is_source_verified=True,  # Source is verified, but schema fails!
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        res = self.manager.execute_request(req)

        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertEqual(res.source_provenance["verification_status"], VerificationStatus.UNVERIFIED.value)
        self.assertIn("Payload validation issue", res.source_provenance.get("disclaimer", ""))

    def test_04_stale_observation_timestamp_degradation(self):
        """Result with data_timestamp older than max_stale is marked STALE."""
        old_time = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
        prov = MockTestLiveDataProvider(
            provider_id="stale_timestamp_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"temp": 12.0, "time": old_time},
            is_simulated=False,
            is_source_verified=True,
        )
        self.manager.register_provider(prov)
        # Policy: max_stale = 2 hours (7200s), but data is 8 hours old
        self.manager.set_cache_policy(DataDomain.WEATHER.value, ttl=1800, max_stale=7200)

        # Pre-seed cache with an older data_timestamp
        cached_payload = {
            "status": "SUCCESS",
            "domain": DataDomain.WEATHER.value,
            "data": {"temp": 12.0},
            "data_timestamp": old_time,
            "freshness_status": "live",
        }
        self.cache.set("live_weather_Katra", cached_payload, ttl=1800, max_stale=7200)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        res = self.manager._reconstitute_result(
            payload=cached_payload,
            request=req,
            provider=prov,
            freshness="cached",
            is_cached=True,
        )

        self.assertEqual(res.freshness_status, FreshnessStatus.STALE.value)

    def test_05_truth_in_data_curated_cannot_be_marked_live(self):
        """Curated data cannot be marked as LIVE in LiveDataResult."""
        prov = create_provenance(
            source_name="curated_test",
            source_type=SourceType.CURATED_DATA.value,
            freshness_status=FreshnessStatus.LIVE.value,  # Intentionally conflicting
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            domain="accommodation",
        )
        res = LiveDataResult(
            status="SUCCESS",
            domain="accommodation",
            data=[{"name": "Hotel"}],
            provider_id="curated_test",
            source_provenance=prov,
            freshness_status=FreshnessStatus.LIVE.value,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
        )
        self.assertEqual(res.freshness_status, FreshnessStatus.NOT_APPLICABLE.value)

    def test_06_truth_in_data_simulated_cannot_be_verified_external(self):
        """Simulated data must always reflect simulation verification status."""
        prov = create_provenance(
            source_name="sim_test",
            source_type=SourceType.SIMULATED_DATA.value,
            freshness_status=FreshnessStatus.SIMULATED.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,  # Intentionally conflicting
            domain="weather",
        )
        res = LiveDataResult(
            status="SUCCESS",
            domain="weather",
            data={"test": 1},
            provider_id="sim_test",
            source_provenance=prov,
            freshness_status=FreshnessStatus.SIMULATED.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,
        )
        self.assertEqual(res.verification_status, VerificationStatus.SIMULATION_ONLY.value)

    def test_07_truth_in_data_unavailable_cannot_be_verified(self):
        """Unavailable data cannot be marked as VERIFIED_EXTERNAL_API."""
        res = LiveDataResult(
            status="UNAVAILABLE",
            domain="weather",
            data=None,
            provider_id="offline_prov",
            freshness_status=FreshnessStatus.UNAVAILABLE.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,
        )
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED.value)

    # =========================================================================
    # 2. EMERGENCY DATA CACHE SAFETY
    # =========================================================================

    def test_08_emergency_stale_cache_attaches_mandatory_112_advisory(self):
        """Stale emergency cache hit attaches prominent 112 life-safety advisory."""
        prov = MockTestLiveDataProvider(
            provider_id="emergency_directory",
            domain=DataDomain.EMERGENCY.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"katra_medical_unit": "+91-1991-232000"},
            is_simulated=False,
            is_source_verified=True,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.EMERGENCY.value, params={"sector": "Bhawan"})
        res = self.manager._reconstitute_result(
            payload={"data": {"katra_medical_unit": "+91-1991-232000"}, "status": "SUCCESS"},
            request=req,
            provider=prov,
            freshness=FreshnessStatus.STALE.value,
            is_cached=True,
        )

        self.assertEqual(res.freshness_status, FreshnessStatus.STALE.value)
        self.assertIsNotNone(res.advisory)
        self.assertIn("112 directly", res.advisory)
        self.assertIn("CRITICAL EMERGENCY NOTICE", res.advisory)

    def test_09_emergency_provider_failure_returns_statutory_fallback(self):
        """Emergency provider failure with no cache returns statutory numbers without fabrication."""
        prov = MockTestLiveDataProvider(
            provider_id="failing_emergency_prov",
            domain=DataDomain.EMERGENCY.value,
            scenario=MockTestLiveDataProvider.SCENARIO_ERROR,
            is_simulated=False,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.EMERGENCY.value, params={"sector": "Katra"})
        res = self.manager.execute_request(req)

        self.assertEqual(res.status, "UNAVAILABLE")
        self.assertEqual(res.freshness_status, FreshnessStatus.UNAVAILABLE.value)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED.value)
        # Verify statutory numbers provided
        self.assertEqual(res.data["universal_emergency"], "112")
        self.assertEqual(res.data["ambulance_medical"], "108")
        self.assertEqual(res.data["police"], "100")
        self.assertIn("112 directly", res.advisory)

    def test_10_unverified_emergency_provider_cannot_masquerade_as_verified(self):
        """Third-party emergency provider (is_source_verified=False) remains UNVERIFIED."""
        prov = MockTestLiveDataProvider(
            provider_id="unverified_volunteer_feed",
            domain=DataDomain.EMERGENCY.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"volunteer_phone": "+91-9999999999"},
            is_simulated=False,
            is_source_verified=False,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.EMERGENCY.value, params={"sector": "Ardhkuwari"})
        res = self.manager.execute_request(req)

        self.assertTrue(res.is_success)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertEqual(res.source_provenance["verification_status"], VerificationStatus.UNVERIFIED.value)

    # =========================================================================
    # 3. SHARED PUBLIC CACHE PRIVACY HARDENING
    # =========================================================================

    def test_11_explicit_private_request_bypasses_cache(self):
        """Request marked is_private_request=True bypasses cache completely."""
        prov = MockTestLiveDataProvider(
            provider_id="private_booking_prov",
            domain=DataDomain.ACCOMMODATION.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"booking_status": "CONFIRMED", "passenger": "Devotee Sharma"},
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"room_type": "VIP"},
            is_private_request=True,
        )

        self.assertTrue(req.is_private())

        # Call 1: Executes directly, is_cached=False
        res1 = self.manager.execute_request(req)
        self.assertEqual(prov.call_count, 1)
        self.assertFalse(res1.is_cached)

        # Call 2: Executes directly again (NOT cached)!
        res2 = self.manager.execute_request(req)
        self.assertEqual(prov.call_count, 2)
        self.assertFalse(res2.is_cached)

    def test_12_sensitive_booking_pnr_keywords_detected_as_private(self):
        """Requests containing booking, pnr, or aadhaar are detected as private."""
        req_pnr = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            params={"pnr": "PNR_KATRA_4491"},
            session_id="sess_123",
        )
        self.assertTrue(req_pnr.is_private())

        req_booking = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"booking_id": "BK_SMVDSB_001"},
            session_id="sess_123",
        )
        self.assertTrue(req_booking.is_private())

        req_public = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
            session_id="sess_123",
        )
        self.assertFalse(req_public.is_private())

    def test_13_cross_session_privacy_isolation(self):
        """Devotee A's booking lookup is never cached or served to Devotee B."""
        prov = MockTestLiveDataProvider(
            provider_id="devotee_records_prov",
            domain=DataDomain.ACCOMMODATION.value,
            scenario=MockTestLiveDataProvider.SCENARIO_SUCCESS,
            custom_payload={"devotee_name": "Devotee A", "allocated_room": "Room 101"},
        )
        self.manager.register_provider(prov)

        # Devotee A queries private reservation
        req_user_a = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"booking_reference": "REF_USER_A_77"},
            session_id="session_user_a",
        )
        self.assertTrue(req_user_a.is_private())
        res_a = self.manager.execute_request(req_user_a)
        self.assertEqual(prov.call_count, 1)
        self.assertFalse(res_a.is_cached)

        # Devotee B issues query with their own session
        prov.custom_payload = {"devotee_name": "Devotee B", "allocated_room": "Room 205"}
        req_user_b = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"booking_reference": "REF_USER_B_88"},
            session_id="session_user_b",
        )
        res_b = self.manager.execute_request(req_user_b)
        self.assertEqual(prov.call_count, 2)
        self.assertFalse(res_b.is_cached)
        self.assertEqual(res_b.data["devotee_name"], "Devotee B")

    # =========================================================================
    # 4. PROVIDER LIFECYCLE & STATE CONSISTENCY
    # =========================================================================

    def test_14_provider_initial_lifecycle_state(self):
        """Configured provider starts at CONFIGURED_PENDING_VERIFICATION."""
        prov = MockTestLiveDataProvider(provider_id="lifecycle_prov", domain=DataDomain.WEATHER.value)
        meta = prov.get_metadata()

        self.assertEqual(meta.operational_status, ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value)
        self.assertEqual(prov.consecutive_failures, 0)
        self.assertEqual(prov.total_requests, 0)
        self.assertIsNone(prov.last_verified_timestamp)

    def test_15_provider_lifecycle_transition_to_operational_on_success(self):
        """Successful execution transitions provider to OPERATIONAL."""
        prov = MockTestLiveDataProvider(provider_id="op_prov", domain=DataDomain.WEATHER.value)
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        self.manager.execute_request(req)

        self.assertEqual(prov.operational_status, ProviderOperationalStatus.OPERATIONAL.value)
        self.assertEqual(prov.consecutive_failures, 0)
        self.assertEqual(prov.successful_requests, 1)
        self.assertEqual(prov.total_requests, 1)
        self.assertIsNotNone(prov.last_verified_timestamp)

    def test_16_provider_lifecycle_transition_to_degraded_on_failure(self):
        """Single failure transitions provider to DEGRADED."""
        prov = MockTestLiveDataProvider(
            provider_id="degraded_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_ERROR,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        self.manager.execute_request(req)

        self.assertEqual(prov.operational_status, ProviderOperationalStatus.DEGRADED.value)
        self.assertEqual(prov.consecutive_failures, 1)
        self.assertEqual(prov.total_requests, 1)
        self.assertTrue(prov.is_available())  # Still available to retry

    def test_17_provider_circuit_breaker_trips_to_unavailable_on_3_failures(self):
        """3 consecutive failures trips provider to UNAVAILABLE (circuit breaker)."""
        prov = MockTestLiveDataProvider(
            provider_id="circuit_breaker_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_ERROR,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})

        # Failure 1 -> DEGRADED
        self.manager.execute_request(req, bypass_cache=True)
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.DEGRADED.value)

        # Failure 2 -> DEGRADED
        self.manager.execute_request(req, bypass_cache=True)
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.DEGRADED.value)

        # Failure 3 -> UNAVAILABLE
        self.manager.execute_request(req, bypass_cache=True)
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertFalse(prov.is_available())

        # Attempt 4 should immediately reject without executing provider
        res4 = self.manager.execute_request(req, bypass_cache=True)
        self.assertEqual(res4.status, "UNAVAILABLE")
        self.assertIn("currently unavailable", res4.error.message)

    def test_18_provider_recovery_from_degraded_to_operational(self):
        """Successful request recovers provider from DEGRADED back to OPERATIONAL."""
        prov = MockTestLiveDataProvider(
            provider_id="recovering_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_ERROR,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        self.manager.execute_request(req, bypass_cache=True)
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.DEGRADED.value)

        # Provider recovers
        prov.scenario = MockTestLiveDataProvider.SCENARIO_SUCCESS
        self.manager.execute_request(req, bypass_cache=True)

        self.assertEqual(prov.operational_status, ProviderOperationalStatus.OPERATIONAL.value)
        self.assertEqual(prov.consecutive_failures, 0)

    def test_19_result_state_consistency_no_results_vs_unavailable(self):
        """NO_RESULTS represents empty search results, NOT provider unavailability."""
        prov = MockTestLiveDataProvider(
            provider_id="empty_search_prov",
            domain=DataDomain.ACCOMMODATION.value,
            scenario=MockTestLiveDataProvider.SCENARIO_EMPTY,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.ACCOMMODATION.value, params={"category": "5_Star"})
        res = self.manager.execute_request(req)

        self.assertEqual(res.status, "NO_RESULTS")
        self.assertEqual(res.data, [])
        self.assertIsNone(res.error)
        self.assertTrue(res.is_empty)
        self.assertNotEqual(res.status, "UNAVAILABLE")
        # NO_RESULTS must NOT degrade provider status!
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.OPERATIONAL.value)
        self.assertEqual(prov.consecutive_failures, 0)

    def test_20_result_state_consistency_timeout_vs_no_results(self):
        """TIMEOUT produces ERROR with TIMEOUT error type, never NO_RESULTS."""
        prov = MockTestLiveDataProvider(
            provider_id="timeout_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_TIMEOUT,
            timeout_seconds=0.05,
        )
        self.manager.register_provider(prov)

        req = ProviderRequest(domain=DataDomain.WEATHER.value, params={"city": "Katra"})
        res = self.manager.execute_request(req)

        self.assertEqual(res.status, "ERROR")
        self.assertNotEqual(res.status, "NO_RESULTS")
        self.assertFalse(res.is_empty)
        self.assertEqual(res.error.error_type, ProviderErrorType.TIMEOUT.value)
        self.assertEqual(prov.consecutive_failures, 1)


if __name__ == "__main__":
    unittest.main()
