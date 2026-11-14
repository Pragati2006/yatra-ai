"""
tests/test_phase9_5_2_2_consistency.py
Dedicated Unit & Integration Test Suite for Yatra AI Phase 9.5.2.2:
Final Provider Consistency Fixes (H2-Obs & L2-Obs).

Covers:
1. H2-Obs — Eager Provider Lock Initialization:
   - Lock exists immediately after provider construction (no lazy evaluation).
   - Concurrent first access across threads returns identical lock object instance.
   - Counter updates remain atomic and consistent under multi-threaded load.
   - Operational state transitions remain fully synchronized.
   - Zero deadlock risk under concurrent execution.

2. L2-Obs — Claims & Availability Preservation Through Cache Reconstruction:
   - Fresh curated accommodation responses carry availability_verified=False and claims_breakdown.
   - Cached responses reconstituted from cache preserve availability_verified=False.
   - Cached responses preserve claims_breakdown in both LiveDataResult and source_provenance.
   - Cached accommodation items preserve rooms_available=None without fabricating counts.
   - Cached accommodation items preserve availability_status="NOT_CHECKED".
   - Multi-room cached requests preserve room_requirement_status="UNVERIFIED".
   - Legacy cache entries without availability/claims fields safely default to availability_verified=False.
   - Standard weather and other provider cache entries remain unaffected.
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
)
from services.live_data.manager import (
    UnifiedLiveDataManager,
    reset_live_data_manager,
)
from services.live_data.registry import ProviderRegistry
from utils.cache_manager import (
    CacheManager,
    generate_cache_key,
    get_cache_manager,
)


class TestEagerLockInitialization(unittest.TestCase):
    """Verifies eager lock initialization and thread safety in BaseLiveDataProvider (H2-Obs)."""

    def setUp(self):
        reset_live_data_manager()
        get_cache_manager().clear()

    def test_01_lock_exists_immediately_upon_construction(self):
        """Lock attribute exists immediately upon instantiation without requiring property access."""
        # Test mock provider
        prov1 = MockTestLiveDataProvider(provider_id="eager_test_prov")
        self.assertTrue(hasattr(prov1, "_state_lock"))
        self.assertIsInstance(prov1._state_lock, type(threading.RLock()))

        # Test curated accommodation adapter
        prov2 = CuratedAccommodationAdapter()
        self.assertTrue(hasattr(prov2, "_state_lock"))
        self.assertIsInstance(prov2._state_lock, type(threading.RLock()))

        # Direct property returns the pre-existing lock
        self.assertIs(prov1._lock, prov1._state_lock)
        self.assertIs(prov2._lock, prov2._state_lock)

    def test_02_lock_instance_identical_across_first_accesses(self):
        """Concurrent first access across 30 threads returns the exact same RLock object ID."""
        prov = MockTestLiveDataProvider(provider_id="concurrent_first_access_prov")
        num_threads = 30
        barrier = threading.Barrier(num_threads)
        seen_locks = set()
        seen_ids = set()
        lock_collector = threading.Lock()

        def worker():
            barrier.wait()
            # First concurrent access to prov._lock
            l = prov._lock
            with lock_collector:
                seen_locks.add(l)
                seen_ids.add(id(l))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 1 distinct lock instance must be seen across all threads
        self.assertEqual(len(seen_locks), 1)
        self.assertEqual(len(seen_ids), 1)
        self.assertIs(list(seen_locks)[0], prov._state_lock)

    def test_03_concurrent_atomic_increments(self):
        """Atomic request and failure counters maintain integrity under mixed concurrent load."""
        prov = MockTestLiveDataProvider(provider_id="atomic_load_prov")
        prov.failure_threshold = 1000  # High threshold to prevent tripping during test
        success_count = 25
        failure_count = 15
        total_workers = success_count + failure_count
        barrier = threading.Barrier(total_workers)

        def worker_success():
            barrier.wait()
            prov.record_execution_success()

        def worker_failure():
            barrier.wait()
            prov.record_execution_failure()

        threads = []
        for _ in range(success_count):
            threads.append(threading.Thread(target=worker_success))
        for _ in range(failure_count):
            threads.append(threading.Thread(target=worker_failure))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(prov.total_requests, total_workers)
        # Final success call leaves consecutive_failures at 0 or >0 depending on thread interleaving,
        # but total_requests must equal exact sum of all calls
        self.assertGreater(prov.successful_requests, 0)
        self.assertLessEqual(prov.successful_requests, success_count)

    def test_04_state_transitions_remain_consistent(self):
        """Lifecycle transitions remain properly synchronized under lock."""
        prov = MockTestLiveDataProvider(provider_id="state_trans_prov")
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value)

        # Success -> OPERATIONAL
        prov.record_execution_success()
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.OPERATIONAL.value)

        # Failure 1 -> DEGRADED
        prov.record_execution_failure()
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.DEGRADED.value)

        # Failures up to threshold -> UNAVAILABLE
        prov.failure_threshold = 2
        prov.record_execution_failure()
        self.assertEqual(prov.operational_status, ProviderOperationalStatus.UNAVAILABLE.value)
        self.assertIsNotNone(prov.unavailable_since)

    def test_05_no_deadlocks_under_load(self):
        """Concurrent requests through manager execute smoothly without lock inversions or deadlocks."""
        reg = ProviderRegistry()
        mock = MockTestLiveDataProvider(
            provider_id="deadlock_test_prov",
            custom_payload={"status": "ok", "latency": 12},
        )
        reg.register(mock)
        manager = UnifiedLiveDataManager(registry=reg)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
        )

        num_threads = 20
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


class TestClaimsPreservationThroughCacheReconstitution(unittest.TestCase):
    """Verifies that availability claims and breakdowns are preserved through cache (L2-Obs)."""

    def setUp(self):
        reset_live_data_manager()
        get_cache_manager().clear()
        self.adapter = CuratedAccommodationAdapter()
        self.registry = ProviderRegistry()
        self.registry.register(self.adapter)
        self.manager = UnifiedLiveDataManager(registry=self.registry)

    def test_06_fresh_curated_accommodation_response_includes_claims(self):
        """Fresh query directly via adapter returns explicit unverified availability and claims breakdown."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertFalse(res.availability_verified)
        self.assertIsNotNone(res.claims_breakdown)
        self.assertEqual(res.claims_breakdown.get("property_identity"), "VERIFIED_CURATED_SOURCE")
        self.assertEqual(res.claims_breakdown.get("live_room_availability"), "UNVERIFIED (NOT_CHECKED)")

    def test_07_cached_response_preserves_both_fields(self):
        """Cached response reconstituted from cache faithfully preserves availability_verified and claims_breakdown."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        # Fetch fresh and verify
        res_fresh = self.manager.execute_request(req)
        self.assertFalse(res_fresh.is_cached)
        self.assertFalse(res_fresh.availability_verified)
        self.assertIsNotNone(res_fresh.claims_breakdown)

        # Fetch cached hit (second call)
        res_cached = self.manager.execute_request(req)
        self.assertTrue(res_cached.is_cached)
        self.assertEqual(res_cached.cached_state, "fresh")

        # Invariant 1: availability_verified remains strictly False
        self.assertFalse(res_cached.availability_verified)

        # Invariant 2: claims_breakdown preserved on top-level result
        self.assertIsNotNone(res_cached.claims_breakdown)
        self.assertEqual(res_cached.claims_breakdown.get("property_identity"), "VERIFIED_CURATED_SOURCE")
        self.assertEqual(res_cached.claims_breakdown.get("live_room_availability"), "UNVERIFIED (NOT_CHECKED)")
        self.assertEqual(res_cached.claims_breakdown.get("room_inventory"), "UNKNOWN (rooms_available=None)")

        # Invariant 3: claims_breakdown also preserved in source_provenance
        self.assertIn("claims_breakdown", res_cached.source_provenance)
        self.assertEqual(
            res_cached.source_provenance["claims_breakdown"].get("live_room_availability"),
            "UNVERIFIED (NOT_CHECKED)",
        )

    def test_08_cached_response_retains_rooms_available_none(self):
        """Reconstituted cached response preserves rooms_available=None without converting to 0 or int."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        # Populate cache
        self.manager.execute_request(req)

        # Retrieve from cache
        res = self.manager.execute_request(req)
        self.assertTrue(res.is_cached)
        hotels = res.data if isinstance(res.data, list) else res.data.get("hotels", [])
        self.assertGreater(len(hotels), 0)
        for h in hotels:
            self.assertIsNone(h.get("rooms_available"))

    def test_09_cached_response_retains_availability_status_not_checked(self):
        """Reconstituted cached response preserves availability_status=NOT_CHECKED."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra"},
        )
        # Populate and retrieve cached
        self.manager.execute_request(req)
        res = self.manager.execute_request(req)
        self.assertTrue(res.is_cached)
        hotels = res.data if isinstance(res.data, list) else res.data.get("hotels", [])
        for h in hotels:
            self.assertEqual(h.get("availability_status"), "NOT_CHECKED")

    def test_10_cached_response_retains_room_requirement_status_unverified(self):
        """Multi-room request preserved through cache maintains room_requirement_status=UNVERIFIED."""
        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "Katra", "min_rooms": 3},
            min_rooms=3,
        )
        # Execute and cache
        self.manager.execute_request(req)
        res = self.manager.execute_request(req)
        self.assertTrue(res.is_cached)
        hotels = res.data if isinstance(res.data, list) else res.data.get("hotels", [])
        self.assertGreater(len(hotels), 0)
        for h in hotels:
            self.assertEqual(h.get("room_requirement_status"), "UNVERIFIED")

    def test_11_legacy_cache_entries_without_fields_readable(self):
        """Legacy cache dictionary lacking new fields reconstitutes safely with availability_verified=False."""
        legacy_payload = {
            "status": "SUCCESS",
            "domain": "accommodation",
            "data": [{"hotel_id": "katra_001", "name": "Hotel Vaishno Devi", "rooms_available": None}],
            "provider_id": "curated_katra_catalog",
            "retrieval_timestamp": "2026-11-07T12:00:00+00:00",
            "freshness_status": "cached",
            "verification_status": "verified_curated_source",
            # Note: "availability_verified" and "claims_breakdown" deliberately omitted to simulate legacy cache
        }
        cache_key = generate_cache_key(category="live_accommodation", params={"location": "legacy_test"})
        cm = get_cache_manager()
        cm.set(
            key=cache_key,
            payload=legacy_payload,
            ttl=3600.0,
            max_stale=7200.0,
            category="live_accommodation",
            request_params={"location": "legacy_test"},
            source_identifier="curated_katra_catalog",
        )

        req = ProviderRequest(
            domain=DataDomain.ACCOMMODATION.value,
            params={"location": "legacy_test"},
        )
        res = self.manager.execute_request(req)
        self.assertTrue(res.is_cached)
        # Safe defaults must apply:
        self.assertFalse(res.availability_verified)
        self.assertIsNone(res.claims_breakdown)
        self.assertEqual(len(res.data), 1)
        self.assertIsNone(res.data[0]["rooms_available"])

    def test_12_normal_weather_cache_behavior_unchanged(self):
        """Standard weather provider cache flow operates normally without interference."""
        mock_weather = MockTestLiveDataProvider(
            provider_id="weather_consistency_mock",
            domain=DataDomain.WEATHER.value,
            custom_payload={"temp_c": 19.5, "condition": "Partly Cloudy"},
        )
        self.registry.register(mock_weather)

        req = ProviderRequest(
            domain=DataDomain.WEATHER.value,
            params={"location": "Katra"},
        )

        res1 = self.manager.execute_request(req)
        self.assertFalse(res1.is_cached)
        self.assertEqual(res1.data["temp_c"], 19.5)
        self.assertFalse(res1.availability_verified)
        self.assertIsNone(res1.claims_breakdown)

        res2 = self.manager.execute_request(req)
        self.assertTrue(res2.is_cached)
        self.assertEqual(res2.data["temp_c"], 19.5)
        self.assertFalse(res2.availability_verified)
        self.assertIsNone(res2.claims_breakdown)


if __name__ == "__main__":
    unittest.main()
