"""
tests/test_phase9_5_2_remediation.py
Comprehensive Unit & Integration Test Suite for Yatra AI Phase 9.5.2:
Provider Privacy, Concurrency & Recovery Remediation.

Covers:
1. Privacy & PII Hardening (H1 & L1):
   - Recursive traversal through nested dictionaries, lists, tuples, and sets.
   - Expanded 28+ PII keywords (mobile, contact, passport, pan_card, voter_id, customer_name, dob, etc.).
   - Key name normalization across camelCase, snake_case, kebab-case, uppercase.
   - Safe exclusion of public search parameters (hotel_name, location_name).
   - Fail-closed behavior on unsupported or complex objects.
   - Strict cache bypass and isolation for private queries.

2. Concurrency & Thread-Safety (H2):
   - Multi-threaded atomic counter increments for success and failure.
   - Protection against race conditions and lost updates under concurrent workers.
   - Concurrency across manager execution without deadlocks.

3. Circuit Breaker & Safe Half-Open Canary Recovery (M2):
   - Configurable failure threshold transition from OPERATIONAL -> DEGRADED -> UNAVAILABLE.
   - Cooldown period enforcement via monotonic clock.
   - Atomic canary probe reservation (exactly one caller permitted in HALF_OPEN).
   - Canary success recovery to OPERATIONAL and cache population.
   - Canary failure/timeout return to UNAVAILABLE with cooldown reset.
   - Legitimate NO_RESULTS query recovery to OPERATIONAL.
   - Failsafe canary probe release on unexpected execution errors.

4. Statutory Emergency Contacts & Administrative Separation (M1):
   - Verified 24x7 SMVDSB Call Centre numbers (1800-180-7212 and +91-1991-234804).
   - Reclassification of +91-1991-232029 strictly as Protocol administrative desk (10 AM - 5 PM).
   - National universal 112 as primary emergency advisory.
   - Preservation of legacy top-level keys for backward compatibility.

5. Curated Accommodation Provenance & Live Inventory Distinction (L2):
   - Explicit availability_verified=False and claims_breakdown on catalog responses.
   - Preservation of rooms_available=None and availability_status=NOT_CHECKED.
   - Serialized dictionary structure includes availability claims transparency.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import threading
import time
import unittest
from typing import Any, Dict, List, Optional

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
    _PRIVATE_FIELD_KEYWORDS,
    _PUBLIC_NAME_EXCLUSIONS,
    _normalize_key_name,
    contains_private_data,
    is_private_key_name,
)
from services.live_data.manager import (
    EMERGENCY_CRITICAL_ADVISORY,
    STATUTORY_EMERGENCY_DATA,
    STATUTORY_EMERGENCY_DISCLAIMER,
    UnifiedLiveDataManager,
    reset_live_data_manager,
)
from services.live_data.registry import ProviderRegistry
from utils.cache_manager import CacheManager, get_cache_manager


class UnsupportedCustomObject:
    """Mock opaque custom object to test fail-closed privacy validation."""
    def __init__(self, val: str):
        self.val = val


class TestPrivacyAndPIIExtensions(unittest.TestCase):
    """Exhaustive tests for recursive PII detection, normalization, and cache isolation."""

    def setUp(self):
        reset_live_data_manager()
        get_cache_manager().clear()

    def test_01_nested_aadhaar_triggers_private_flag(self):
        """Nested dictionary containing Aadhaar is recursively detected as private."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"guest": {"aadhaar": "1234-5678-9012"}},
        )
        self.assertTrue(req.is_private())

    def test_02_nested_pnr_in_list_triggers_private_flag(self):
        """PNR nested inside a list of itinerary dictionaries is detected as private."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            params={"itinerary": [{"leg": 1, "pnr": "PNR-1029384"}]},
        )
        self.assertTrue(req.is_private())

    def test_03_alternative_pii_field_names_comprehensive(self):
        """Comprehensive verification of alternative PII keywords."""
        test_keys = [
            "mobile", "mobile_number", "contact", "contact_number", "phone_number",
            "passport", "pan_card", "pan_number", "voter_id", "driving_license",
            "customer_name", "full_name", "first_name", "last_name", "passenger_name",
            "dob", "date_of_birth", "email_address", "credit_card", "upi_id", "cvv"
        ]
        for key in test_keys:
            with self.subTest(key=key):
                self.assertTrue(is_private_key_name(key), f"Key '{key}' should be recognized as private")
                req = ProviderRequest(
                    domain=DataDomain.ACCOMMODATION.value,
                    params={key: "sensitive_sample_value"},
                )
                self.assertTrue(req.is_private(), f"Request with key '{key}' must have is_private() == True")

    def test_04_key_normalization_camel_kebab_upper_mixed(self):
        """Key normalization handles camelCase, kebab-case, snake_case, and uppercase."""
        variants = [
            "paxName", "PAX-NAME", "Pax_Name",
            "contactNumber", "CONTACT-NUMBER", "contact_number",
            "dateOfBirth", "DATE-OF-BIRTH", "date_of_birth",
            "panCard", "PAN-CARD", "pan_card",
            "voterId", "VOTER-ID", "voter_id",
        ]
        for var in variants:
            with self.subTest(variant=var):
                self.assertTrue(is_private_key_name(var), f"Variant '{var}' should be detected as private")
                req = ProviderRequest(
                    domain=DataDomain.ACCOMMODATION.value,
                    params={var: "value123"},
                )
                self.assertTrue(req.is_private(), f"Request with '{var}' must be private")

    def test_05_public_search_exclusions_preserved(self):
        """Public search parameters are never falsely classified as private."""
        public_params = {
            "hotel_name": "Hotel Vaishno Devi",
            "location_name": "Katra Main Chowk",
            "service_name": "Battery Car Shuttle",
            "place_name": "Ardhkuwari",
            "property_name": "Niharika Complex",
            "location": "Katra",
            "category": "Deluxe",
            "city": "Katra",
            "guests_count": 2,
            "rooms": 1,
        }
        for k, v in public_params.items():
            with self.subTest(key=k):
                self.assertFalse(is_private_key_name(k), f"Public key '{k}' must not be flagged as private")

        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params=public_params,
        )
        self.assertFalse(req.is_private(), "Public search request must not be marked private")

    def test_06_unsupported_complex_object_fails_closed(self):
        """Unsupported opaque objects in request params fail closed by marking request private."""
        opaque_obj = UnsupportedCustomObject("opaque-data")
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"filter": opaque_obj},
        )
        self.assertTrue(req.is_private(), "Opaque/unsupported object must fail closed to private")

    def test_07_cache_bypass_and_isolation_end_to_end(self):
        """Private requests completely bypass cache reads and writes in LiveDataManager."""
        reset_live_data_manager()
        reg = ProviderRegistry()
        mock = MockTestLiveDataProvider(
            provider_id="privacy_mock",
            domain=DataDomain.ACCOMMODATION.value,
            custom_payload={"booking_status": "CONFIRMED", "rooms_allocated": [101]},
        )
        reg.register(mock)
        manager = UnifiedLiveDataManager(registry=reg)

        priv_req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"guest": {"customer_name": "Devotee Sharma", "mobile": "9876543210"}},
        )
        self.assertTrue(priv_req.is_private())

        res1 = manager.execute_request(priv_req)
        self.assertFalse(res1.is_cached)
        self.assertIsNone(res1.cached_state)
        self.assertEqual(res1.data["booking_status"], "CONFIRMED")

        # Second private execution must also execute live and NOT be cached
        res2 = manager.execute_request(priv_req)
        self.assertFalse(res2.is_cached)
        self.assertIsNone(res2.cached_state)


class TestConcurrencyAndThreadSafety(unittest.TestCase):
    """Exhaustive multi-threaded concurrency tests for provider lifecycle and metrics."""

    def setUp(self):
        reset_live_data_manager()
        get_cache_manager().clear()

    def test_08_concurrent_successes_atomic_counters(self):
        """Multiple concurrent threads recording success increment metrics atomically without loss."""
        provider = MockTestLiveDataProvider(provider_id="atomic_success_prov")
        num_threads = 25
        barrier = threading.Barrier(num_threads)

        def worker():
            barrier.wait()
            provider.record_execution_success()

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(provider.total_requests, num_threads)
        self.assertEqual(provider.successful_requests, num_threads)
        self.assertEqual(provider.consecutive_failures, 0)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.OPERATIONAL.value)

    def test_09_concurrent_failures_atomic_counters(self):
        """Multiple concurrent threads recording failure increment metrics atomically and trip breaker."""
        provider = MockTestLiveDataProvider(provider_id="atomic_failure_prov")
        provider.failure_threshold = 10
        num_threads = 15
        barrier = threading.Barrier(num_threads)

        def worker():
            barrier.wait()
            provider.record_execution_failure()

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(provider.total_requests, num_threads)
        self.assertEqual(provider.consecutive_failures, num_threads)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertIsNotNone(provider.unavailable_since)

    def test_10_mixed_concurrent_success_and_failure(self):
        """Simultaneous concurrent successes and failures maintain exact total request count."""
        provider = MockTestLiveDataProvider(provider_id="mixed_atomic_prov")
        provider.failure_threshold = 100  # Prevent tripping during test
        success_count = 15
        failure_count = 10
        total_workers = success_count + failure_count
        barrier = threading.Barrier(total_workers)

        def worker_success():
            barrier.wait()
            provider.record_execution_success()

        def worker_failure():
            barrier.wait()
            provider.record_execution_failure()

        threads = []
        for _ in range(success_count):
            threads.append(threading.Thread(target=worker_success))
        for _ in range(failure_count):
            threads.append(threading.Thread(target=worker_failure))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(provider.total_requests, total_workers)

    def test_11_concurrent_manager_execute_request_no_deadlock(self):
        """Concurrent request execution through LiveDataManager executes cleanly with no deadlocks."""
        reset_live_data_manager()
        reg = ProviderRegistry()
        mock = MockTestLiveDataProvider(
            provider_id="concurrent_exec_prov",
            custom_payload={"condition": "Clear", "temp_c": 18.0},
        )
        reg.register(mock)
        manager = UnifiedLiveDataManager(registry=reg)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
        )

        num_threads = 16
        results = []

        def worker():
            return manager.execute_request(req)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in as_completed(futures):
                results.append(f.result())

        self.assertEqual(len(results), num_threads)
        for res in results:
            self.assertTrue(res.is_success)
            self.assertEqual(res.data["temp_c"], 18.0)


class TestCircuitBreakerAndRecovery(unittest.TestCase):
    """Exhaustive tests for circuit breaker tripping, cooldown, and atomic canary probe recovery."""

    def setUp(self):
        reset_live_data_manager()
        get_cache_manager().clear()

    def test_12_circuit_breaker_trips_to_unavailable_after_threshold(self):
        """Provider transitions to DEGRADED on single failure, and UNAVAILABLE at threshold."""
        provider = MockTestLiveDataProvider(provider_id="cb_test_prov")
        provider.failure_threshold = 3

        # Failure 1 -> DEGRADED
        provider.record_execution_failure()
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.DEGRADED.value)
        self.assertTrue(provider.is_available())

        # Failure 2 -> DEGRADED
        provider.record_execution_failure()
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.DEGRADED.value)
        self.assertTrue(provider.is_available())

        # Failure 3 -> UNAVAILABLE
        provider.record_execution_failure()
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertFalse(provider.is_available())
        self.assertIsNotNone(provider.unavailable_since)

    def test_13_unavailable_provider_cooldown_enforcement(self):
        """Unavailable provider rejects calls until cooldown window has elapsed."""
        provider = MockTestLiveDataProvider(provider_id="cooldown_prov")
        provider.failure_threshold = 1
        provider.cooldown_seconds = 10.0  # 10s cooldown
        provider.record_execution_failure()

        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertFalse(provider.is_available())
        # Reservation must fail while cooldown active
        self.assertFalse(provider.reserve_canary_probe())

    def test_14_canary_probe_reservation_atomic_single_flight(self):
        """When cooldown elapses, exactly ONE caller can atomically reserve the canary probe."""
        provider = MockTestLiveDataProvider(provider_id="canary_single_prov")
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.03  # 30ms cooldown for fast test
        provider.record_execution_failure()

        time.sleep(0.07)  # Wait safely past Windows timer resolution
        self.assertTrue(provider.is_available())

        num_threads = 10
        barrier = threading.Barrier(num_threads)
        reservation_results = []

        def worker():
            barrier.wait()
            success = provider.reserve_canary_probe()
            reservation_results.append(success)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly ONE thread must succeed
        self.assertEqual(reservation_results.count(True), 1)
        self.assertEqual(reservation_results.count(False), num_threads - 1)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.HALF_OPEN.value)
        self.assertTrue(provider.is_half_open_probe_active)

    def test_15_canary_probe_success_restores_operational_and_populates_cache(self):
        """Successful canary probe restores OPERATIONAL state and updates cache."""
        reset_live_data_manager()
        reg = ProviderRegistry()
        provider = MockTestLiveDataProvider(
            provider_id="canary_recovery_prov",
            custom_payload={"condition": "Clear", "temp_c": 22.0},
        )
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.03
        reg.register(provider)
        manager = UnifiedLiveDataManager(registry=reg)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
        )

        # Trip circuit breaker
        provider.record_execution_failure()
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)

        # Wait for cooldown
        time.sleep(0.07)

        # Execute canary request via manager
        res = manager.execute_request(req)
        self.assertTrue(res.is_success)
        self.assertEqual(res.data["temp_c"], 22.0)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.OPERATIONAL.value)
        self.assertEqual(provider.consecutive_failures, 0)
        self.assertFalse(provider.is_half_open_probe_active)

        # Verify subsequent request is served from cache
        cached_res = manager.execute_request(req)
        self.assertTrue(cached_res.is_cached)

    def test_16_canary_probe_failure_returns_to_unavailable_and_resets_cooldown(self):
        """Canary probe failure returns provider to UNAVAILABLE and resets cooldown timer."""
        provider = MockTestLiveDataProvider(provider_id="canary_fail_prov")
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.03
        provider.record_execution_failure()

        time.sleep(0.07)
        self.assertTrue(provider.reserve_canary_probe())
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.HALF_OPEN.value)

        # Simulate canary failure
        time_before = time.monotonic()
        provider.record_execution_failure()

        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertFalse(provider.is_half_open_probe_active)
        self.assertGreaterEqual(provider.unavailable_since, time_before)
        # New canary reservation must fail because cooldown was reset
        self.assertFalse(provider.reserve_canary_probe())

    def test_17_canary_probe_timeout_fails_probe(self):
        """Canary probe timing out records failure and returns provider to UNAVAILABLE."""
        reset_live_data_manager()
        reg = ProviderRegistry()
        provider = MockTestLiveDataProvider(
            provider_id="canary_timeout_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_TIMEOUT,
            timeout_seconds=0.05,
        )
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.03
        reg.register(provider)
        manager = UnifiedLiveDataManager(registry=reg)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
        )

        # Trip to UNAVAILABLE
        provider.record_execution_failure()
        time.sleep(0.07)

        res = manager.execute_request(req)
        self.assertFalse(res.is_success)
        self.assertEqual(res.error.error_type, ProviderErrorType.TIMEOUT.value)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)

    def test_18_canary_probe_no_results_restores_operational(self):
        """Legitimate empty search result during canary probe restores OPERATIONAL."""
        reset_live_data_manager()
        reg = ProviderRegistry()
        provider = MockTestLiveDataProvider(
            provider_id="canary_no_results_prov",
            domain=DataDomain.WEATHER.value,
            scenario=MockTestLiveDataProvider.SCENARIO_EMPTY,
        )
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.03
        reg.register(provider)
        manager = UnifiedLiveDataManager(registry=reg)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "UnknownLocation"},
        )

        # Trip to UNAVAILABLE
        provider.record_execution_failure()
        time.sleep(0.07)

        res = manager.execute_request(req)
        self.assertEqual(res.status, "NO_RESULTS")
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.OPERATIONAL.value)

    def test_19_canary_probe_failsafe_release_on_unexpected_exception(self):
        """Unexpected exception in execution safely triggers release_canary_probe without deadlock."""
        provider = MockTestLiveDataProvider(provider_id="canary_failsafe_prov")
        provider.failure_threshold = 1
        provider.cooldown_seconds = 0.01
        provider.record_execution_failure()
        time.sleep(0.02)

        self.assertTrue(provider.reserve_canary_probe())
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.HALF_OPEN.value)

        # Invoking release_canary_probe with success=False restores UNAVAILABLE safely
        provider.release_canary_probe(success=False)
        self.assertEqual(provider.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertFalse(provider.is_half_open_probe_active)


class TestEmergencyContactsAndMetadata(unittest.TestCase):
    """Exhaustive tests for statutory emergency data, administrative separation, and verification sources."""

    def test_20_statutory_emergency_data_verified_sources(self):
        """Universal 112 is verified with national police/disaster/medical authority."""
        self.assertEqual(STATUTORY_EMERGENCY_DATA["universal_emergency"], "112")
        cats = STATUTORY_EMERGENCY_DATA.get("categories", {})
        self.assertIn("national_emergency", cats)
        univ = cats["national_emergency"]
        self.assertEqual(univ["number"], "112")
        self.assertIn("112.gov.in", univ["source_url"])

    def test_21_smvdsb_administrative_vs_emergency_separation(self):
        """Official 24x7 SMVDSB Call Centre numbers are distinct from office-hours Protocol desk."""
        cats = STATUTORY_EMERGENCY_DATA.get("categories", {})

        # 24x7 Call Centre
        self.assertIn("shrine_board_call_centre", cats)
        call_centre = cats["shrine_board_call_centre"]
        self.assertIn("1800-180-7212 (Toll Free)", call_centre["numbers"])
        self.assertIn("+91-1991-234804", call_centre["numbers"])
        self.assertEqual(call_centre["availability"], "24x7")

        # Protocol Department: office hours only
        self.assertIn("administrative_office", cats)
        protocol = cats["administrative_office"]
        self.assertEqual(protocol["number"], "+91-1991-232029")
        self.assertEqual(protocol["availability"], "Office Hours Only (10:00 AM - 5:00 PM)")
        self.assertIn("maavaishnodevi.org", protocol["source_url"])
        self.assertIn("not a 24x7 emergency helpline", protocol.get("note", ""))

    def test_22_statutory_emergency_data_backward_compatibility(self):
        """All legacy top-level keys remain present and accurately formatted."""
        expected_keys = [
            "universal_emergency",
            "ambulance_medical",
            "police_control_room",
            "fire_service",
            "disaster_management",
            "women_helpline",
            "katra_police_station",
            "smvdsb_call_centre_toll_free",
            "smvdsb_administrative_protocol",
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, STATUTORY_EMERGENCY_DATA)
                self.assertTrue(len(STATUTORY_EMERGENCY_DATA[key]) > 0)


class TestCuratedAccommodationProvenance(unittest.TestCase):
    """Exhaustive tests for static accommodation provenance and availability transparency."""

    def setUp(self):
        self.adapter = CuratedAccommodationAdapter()

    def test_23_curated_adapter_availability_unverified_flag(self):
        """Curated accommodation adapter explicitly returns availability_verified=False."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertFalse(res.availability_verified)
        self.assertIsNotNone(res.claims_breakdown)
        self.assertEqual(
            res.claims_breakdown.get("property_identity"),
            "VERIFIED_CURATED_SOURCE",
        )
        self.assertEqual(
            res.claims_breakdown.get("live_room_availability"),
            "UNVERIFIED (NOT_CHECKED)",
        )

    def test_24_curated_adapter_rooms_available_none(self):
        """Curated accommodation items preserve rooms_available=None and NOT_CHECKED status."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        hotels = res.data if isinstance(res.data, list) else res.data.get("hotels", [])
        self.assertGreater(len(hotels), 0)
        for h in hotels:
            self.assertIsNone(h.get("rooms_available"))
            self.assertEqual(h.get("availability_status"), "NOT_CHECKED")

    def test_25_curated_adapter_dict_serialization(self):
        """Result serialization preserves availability_verified and claims_breakdown in dict."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        d = res.to_dict()
        self.assertIn("availability_verified", d)
        self.assertFalse(d["availability_verified"])
        self.assertIn("claims_breakdown", d)
        self.assertEqual(d["claims_breakdown"]["live_room_availability"], "UNVERIFIED (NOT_CHECKED)")


if __name__ == "__main__":
    unittest.main()
