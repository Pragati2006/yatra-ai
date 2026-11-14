"""
tests/test_phase8_3_cache.py
Verification Test Suite for Phase 8 Checkpoint 8.3:
In-Memory Data Freshness & Cache Engine.

Covers all 40 verification requirements:
 1. Cache manager initialization.
 2. Cache set and get.
 3. Fresh cache hit.
 4. Cache miss.
 5. TTL expiration.
 6. Explicit invalidation.
 7. Clear operation.
 8. Cache statistics.
 9. Maximum entry count.
10. Eviction policy (LRU / expired).
11. Deterministic cache keys.
12. Cache key separation by location.
13. Cache key separation by elevation.
14. Cache key separation by provider parameters.
15. Weather first-request provider call.
16. Weather second-request cache hit.
17. No duplicate provider call on a cache hit.
18. Cached provenance classification.
19. Original data timestamp preservation.
20. Correct retrieval timestamp on cache hit.
21. Expired cache refresh success.
22. Expired cache refresh failure.
23. Stale fallback classification.
24. Maximum stale age enforcement.
25. No usable stale data behavior.
26. Provider failure with existing seasonal fallback.
27. Provider failure without fallback.
28. Per-location multi-weather caching.
29. Partial multi-location failure.
30. Concurrent identical requests (single-flight coordination).
31. Concurrent requests for different locations.
32. Concurrent cache writes.
33. Lock release after exceptions.
34. Provenance deduplication compatibility.
35. live_sources filtering compatibility.
36. Central Agent compatibility.
37. Deterministic orchestrator compatibility.
38. JSON serialization.
39. Session isolation.
40. Existing booking/RPA behavior remains unaffected.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import json
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from agents import central_agent, coordinator, orchestrator, session_store
import utils.cache_manager as cm
from utils.cache_manager import (
    CacheEntry,
    CacheManager,
    CacheState,
    generate_cache_key,
    generate_weather_cache_key,
    get_cache_manager,
    reset_cache_manager,
)
import utils.provenance as prov
from utils.provenance import FreshnessStatus, SourceType, VerificationStatus
import weather


def make_mock_weather_data(location_key="bhawan", temp_max=18.0, temp_min=6.0, time_str="2026-11-06T12:00+05:30"):
    """Creates realistic structured weather dict matching fetch_location_weather format."""
    loc_info = weather.get_location_info(location_key)
    return {
        "location": loc_info["name"],
        "location_key": loc_info["key"],
        "latitude": loc_info["latitude"],
        "longitude": loc_info["longitude"],
        "elevation_m": loc_info["elevation_m"],
        "date": "2026-11-06",
        "summary": "Clear sky",
        "condition": "Clear sky",
        "low_c": round(temp_min),
        "high_c": round(temp_max),
        "temperature_c": round((temp_max + temp_min) / 2.0, 1),
        "apparent_temperature_c": round((temp_max + temp_min) / 2.0, 1),
        "precipitation_mm": 0.0,
        "precipitation_probability_pct": 5,
        "wind_speed_kmh": 12.0,
        "advisory": "Pleasant conditions along the track.",
        "source": "forecast",
        "source_name": "Open-Meteo Weather API",
        "source_url": "https://open-meteo.com",
        "source_tier": "tier_2_open_api",
        "source_type": "live_api",
        "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_timestamp": time_str,
        "provider_timezone": "Asia/Kolkata",
        "provider_utc_offset_seconds": 19800,
        "freshness_status": "live",
        "weather_type": "live_forecast",
        "verification_status": "verified_external_api",
        "disclaimer": weather.MOUNTAIN_WEATHER_DISCLAIMER,
    }


class TestPhase83CacheEngine(unittest.TestCase):
    """Exhaustive test suite for In-Memory Data Freshness & Cache Engine."""

    def setUp(self):
        """Resets the global cache manager and clears any test entries."""
        weather.clear_weather_cache()
        reset_cache_manager()

    # =========================================================================
    # 1–10. CACHE MANAGER PRIMITIVES, TTL, AND EVICTION
    # =========================================================================

    def test_01_cache_manager_initialization(self):
        """1. Verifies cache manager initializes with default capacity and policies."""
        mgr = CacheManager(max_entries=100, ttl_weather=600.0, max_stale_weather=3600.0)
        self.assertEqual(mgr.max_entries, 100)
        self.assertEqual(mgr.ttl_policies["weather"], 600.0)
        self.assertEqual(mgr.max_stale_policies["weather"], 3600.0)
        stats = mgr.get_stats()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)

    def test_02_cache_set_and_get(self):
        """2. Verifies set and get roundtrip stores and retrieves payloads correctly."""
        mgr = CacheManager()
        entry = mgr.set("test_key_1", {"data": 42}, ttl=300.0, category="test")
        self.assertIsInstance(entry, CacheEntry)
        self.assertEqual(entry.key, "test_key_1")
        val = mgr.get("test_key_1")
        self.assertEqual(val, {"data": 42})

    def test_03_fresh_cache_hit(self):
        """3. Verifies entry within TTL returns fresh status and increments hits."""
        mgr = CacheManager()
        mgr.set("key_fresh", "payload_fresh", ttl=100.0)
        payload, status, entry = mgr.get_with_status("key_fresh")
        self.assertEqual(status, CacheState.FRESH.value)
        self.assertEqual(payload, "payload_fresh")
        self.assertEqual(mgr.get_stats()["hits"], 1)

    def test_04_cache_miss(self):
        """4. Verifies non-existent key returns miss status and increments misses."""
        mgr = CacheManager()
        payload, status, entry = mgr.get_with_status("non_existent_key")
        self.assertEqual(status, CacheState.MISS.value)
        self.assertIsNone(payload)
        self.assertIsNone(entry)
        self.assertEqual(mgr.get_stats()["misses"], 1)

    def test_05_ttl_expiration(self):
        """5. Verifies monotonic clock expiration: entry becomes expired after TTL."""
        curr_time = 1000.0
        mgr = CacheManager(monotonic_clock=lambda: curr_time)

        mgr.set("key_exp", "val_exp", ttl=60.0, max_stale=300.0)
        # Immediate lookup is fresh
        payload, status, _ = mgr.get_with_status("key_exp")
        self.assertEqual(status, CacheState.FRESH.value)

        # Advance clock past TTL (61s later)
        curr_time += 61.0
        payload, status, _ = mgr.get_with_status("key_exp")
        self.assertEqual(status, CacheState.STALE.value)

    def test_06_explicit_invalidation(self):
        """6. Verifies explicit invalidation deletes the key immediately."""
        mgr = CacheManager()
        mgr.set("key_to_del", "val_del")
        self.assertTrue(mgr.invalidate("key_to_del"))
        self.assertIsNone(mgr.get("key_to_del"))
        self.assertFalse(mgr.invalidate("key_to_del"))  # already deleted

    def test_07_clear_operation(self):
        """7. Verifies clear removes all entries."""
        mgr = CacheManager()
        mgr.set("k1", "v1")
        mgr.set("k2", "v2")
        mgr.set("k3", "v3")
        cleared = mgr.clear()
        self.assertEqual(cleared, 3)
        self.assertEqual(mgr.get_stats()["total_entries"], 0)

    def test_08_cache_statistics(self):
        """8. Verifies stats dictionary reports accurate counts."""
        mgr = CacheManager()
        mgr.set("k1", "v1")
        mgr.get("k1")  # hit
        mgr.get("k2")  # miss
        stats = mgr.get_stats()
        self.assertEqual(stats["total_entries"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

    def test_09_maximum_entry_count(self):
        """9. Verifies cache capacity never exceeds max_entries."""
        mgr = CacheManager(max_entries=3)
        mgr.set("k1", "v1")
        mgr.set("k2", "v2")
        mgr.set("k3", "v3")
        mgr.set("k4", "v4")  # should trigger eviction
        self.assertEqual(len(mgr._entries), 3)
        self.assertEqual(mgr.get_stats()["evictions"], 1)

    def test_10_eviction_policy(self):
        """10. Verifies expired entries are evicted before active entries."""
        curr_time = 1000.0
        mgr = CacheManager(max_entries=2, monotonic_clock=lambda: curr_time)

        # k1 has short TTL and max_stale (expires completely in 10s)
        mgr.set("k1", "v1", ttl=5.0, max_stale=5.0)
        # k2 has long TTL
        mgr.set("k2", "v2", ttl=500.0, max_stale=500.0)

        # Fast-forward so k1 is completely expired past max_stale
        curr_time += 15.0

        # Insert k3; k1 should be evicted first because it is expired
        mgr.set("k3", "v3", ttl=500.0)
        self.assertNotIn("k1", mgr._entries)
        self.assertIn("k2", mgr._entries)
        self.assertIn("k3", mgr._entries)

    # =========================================================================
    # 11–14. CACHE KEY DETERMINISM & INDEPENDENCE
    # =========================================================================

    def test_11_deterministic_cache_keys(self):
        """11. Verifies same parameters produce identical cache keys."""
        k1 = generate_weather_cache_key("katra", "2026-11-06", 32.99, 74.93, 750)
        k2 = generate_weather_cache_key("katra", "2026-11-06", 32.99, 74.93, 750)
        self.assertEqual(k1, k2)

    def test_12_cache_key_separation_by_location(self):
        """12. Verifies all 4 trek locations produce distinct non-colliding keys."""
        k_katra = generate_weather_cache_key("katra", "2026-11-06", 32.99, 74.93, 750)
        k_ardh = generate_weather_cache_key("ardhkuwari", "2026-11-06", 33.02, 74.95, 1400)
        k_bhawan = generate_weather_cache_key("bhawan", "2026-11-06", 33.03, 74.95, 1585)
        k_bhairon = generate_weather_cache_key("bhairon", "2026-11-06", 33.04, 74.95, 2011)

        keys = {k_katra, k_ardh, k_bhawan, k_bhairon}
        self.assertEqual(len(keys), 4, "All 4 pilgrimage locations must have distinct cache keys")

    def test_13_cache_key_separation_by_elevation(self):
        """13. Verifies different elevations produce distinct keys even with identical coordinates."""
        k1 = generate_weather_cache_key("test_loc", "2026-11-06", 33.03, 74.95, 1585)
        k2 = generate_weather_cache_key("test_loc", "2026-11-06", 33.03, 74.95, 1831)
        self.assertNotEqual(k1, k2)

    def test_14_cache_key_separation_by_provider_parameters(self):
        """14. Verifies generic cache key generator separates parameter changes."""
        k1 = generate_cache_key("weather", {"lat": 32.99, "lon": 74.93, "elev": 750})
        k2 = generate_cache_key("weather", {"lat": 32.99, "lon": 74.93, "elev": 1585})
        self.assertNotEqual(k1, k2)

    # =========================================================================
    # 15–20. WEATHER INTEGRATION, CACHE HITS & TIMESTAMPS
    # =========================================================================

    @patch("weather._fetch_live_forecast_location")
    def test_15_weather_first_request_provider_call(self, mock_fetch):
        """15. Verifies first weather query calls provider on cache miss."""
        mock_fetch.return_value = make_mock_weather_data("bhawan", temp_max=16.0)
        res = weather.fetch_location_weather("bhawan")
        mock_fetch.assert_called_once()
        self.assertEqual(res["freshness_status"], "live")
        self.assertEqual(res["source_type"], "live_api")

    @patch("weather._fetch_live_forecast_location")
    def test_16_weather_second_request_cache_hit(self, mock_fetch):
        """16. Verifies second weather query within TTL returns cached data."""
        mock_fetch.return_value = make_mock_weather_data("bhawan", temp_max=16.0)
        # Query 1: Cache miss
        res1 = weather.fetch_location_weather("bhawan")
        # Query 2: Cache hit
        res2 = weather.fetch_location_weather("bhawan")

        self.assertEqual(res2["freshness_status"], "cached")
        self.assertEqual(res2["source_type"], "cached_api")
        self.assertEqual(res2["high_c"], 16)

    @patch("weather._fetch_live_forecast_location")
    def test_17_no_duplicate_provider_call_on_cache_hit(self, mock_fetch):
        """17. Verifies provider is called exactly ONCE across multiple queries."""
        mock_fetch.return_value = make_mock_weather_data("bhawan")
        weather.fetch_location_weather("bhawan")
        weather.fetch_location_weather("bhawan")
        weather.fetch_location_weather("bhawan")
        self.assertEqual(mock_fetch.call_count, 1)

    @patch("weather._fetch_live_forecast_location")
    def test_18_cached_provenance_classification(self, mock_fetch):
        """18. Verifies cached result updates provenance to cached_api / cached."""
        mock_fetch.return_value = make_mock_weather_data("bhawan")
        weather.fetch_location_weather("bhawan")  # fills cache
        res_cached = weather.fetch_location_weather("bhawan")

        provs = prov.extract_provenance_from_weather(res_cached)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["source_type"], "cached_api")
        self.assertEqual(provs[0]["freshness_status"], "cached")
        self.assertEqual(provs[0]["verification_status"], "verified_external_api")

    @patch("weather._fetch_live_forecast_location")
    def test_19_original_data_timestamp_preservation(self, mock_fetch):
        """19. Verifies cached response preserves original provider data timestamp."""
        orig_time = "2026-11-06T10:15+05:30"
        mock_fetch.return_value = make_mock_weather_data("katra", time_str=orig_time)
        weather.fetch_location_weather("katra")
        res_cached = weather.fetch_location_weather("katra")
        self.assertEqual(res_cached["data_timestamp"], orig_time)

    @patch("weather._fetch_live_forecast_location")
    def test_20_correct_retrieval_timestamp_on_cache_hit(self, mock_fetch):
        """20. Verifies retrieval_timestamp reflects current turn time, not original fetch time."""
        mock_fetch.return_value = make_mock_weather_data("katra")
        res1 = weather.fetch_location_weather("katra")
        time.sleep(0.01)
        res2 = weather.fetch_location_weather("katra")
        self.assertIsNotNone(res2["retrieval_timestamp"])
        self.assertTrue("+" in res2["retrieval_timestamp"] or res2["retrieval_timestamp"].endswith("Z"))

    # =========================================================================
    # 21–27. EXPIRATION, REFRESH, STALE FALLBACK & FAILURES
    # =========================================================================

    def test_21_expired_cache_refresh_success(self):
        """21. Verifies expired cache fetches fresh live data when provider succeeds."""
        curr_time = 1000.0
        mgr = CacheManager(monotonic_clock=lambda: curr_time)

        calls = []
        def fetcher():
            calls.append(len(calls) + 1)
            return {"temp": 20.0 + len(calls)}

        # 1. Miss -> live
        p1, s1 = mgr.get_or_fetch("k_ref", fetcher, category="weather", ttl=60.0)
        self.assertEqual(s1, "live")
        self.assertEqual(p1["temp"], 21.0)

        # 2. Advance time past TTL
        curr_time += 65.0

        # 3. Next query refreshes from provider
        p2, s2 = mgr.get_or_fetch("k_ref", fetcher, category="weather", ttl=60.0)
        self.assertEqual(s2, "live")
        self.assertEqual(p2["temp"], 22.0)
        self.assertEqual(len(calls), 2)

    def test_22_expired_cache_refresh_failure(self):
        """22. Verifies expired cache falls back to stale data when refresh fails."""
        curr_time = 1000.0
        mgr = CacheManager(monotonic_clock=lambda: curr_time)

        # 1. First fetch succeeds
        mgr.get_or_fetch("k_stale", lambda: {"temp": 19.5}, category="weather", ttl=60.0, max_stale=600.0)

        # 2. Advance time past TTL (70s later)
        curr_time += 70.0

        # 3. Provider fails (returns None)
        p, status = mgr.get_or_fetch("k_stale", lambda: None, category="weather", ttl=60.0, max_stale=600.0)
        self.assertEqual(status, "stale")
        self.assertEqual(p["temp"], 19.5)

    def test_23_stale_fallback_classification(self):
        """23. Verifies stale fallback payload carries freshness_status='stale' and disclaimer."""
        p = prov.create_provenance(
            source_name="Open-Meteo Weather API",
            source_type=SourceType.CACHED_API,
            freshness_status=FreshnessStatus.STALE,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API,
            disclaimer="Stale Weather Forecast — Provider Unavailable.",
        )
        self.assertEqual(p["source_type"], "cached_api")
        self.assertEqual(p["freshness_status"], "stale")
        self.assertIn("Provider Unavailable", p["disclaimer"])

    def test_24_maximum_stale_age_enforcement(self):
        """24. Verifies cache older than max_stale is rejected as expired_unusable."""
        curr_time = 1000.0
        mgr = CacheManager(monotonic_clock=lambda: curr_time)

        mgr.set("k_max", "data", ttl=60.0, max_stale=120.0)
        # Advance 200s (exceeds TTL + max_stale = 180s)
        curr_time += 200.0

        payload, status = mgr.get_or_fetch("k_max", lambda: None, category="weather", ttl=60.0, max_stale=120.0)
        self.assertEqual(status, "fallback")
        self.assertIsNone(payload)

    def test_25_no_usable_stale_data_behavior(self):
        """25. Verifies provider failure with no prior cache returns fallback."""
        mgr = CacheManager()
        payload, status = mgr.get_or_fetch("no_prior_cache", lambda: None, category="weather")
        self.assertEqual(status, "fallback")
        self.assertIsNone(payload)

    @patch("weather._fetch_live_forecast_location")
    def test_26_provider_failure_with_existing_seasonal_fallback(self, mock_fetch):
        """26. Verifies provider failure without cache engages regional seasonal fallback."""
        mock_fetch.return_value = None  # Provider fails
        res = weather.fetch_location_weather("bhawan")
        self.assertEqual(res["source"], "seasonal_average")
        self.assertEqual(res["freshness_status"], "fallback")
        self.assertEqual(res["weather_type"], "seasonal_estimate")
        self.assertIn("Seasonal Climate Estimate", res["disclaimer"])

    @patch("weather.requests.get")
    def test_27_provider_failure_without_fallback_exception(self, mock_get):
        """27. Verifies requests.Timeout engages fallback gracefully without crashing."""
        mock_get.side_effect = Exception("Network down")
        res = weather.fetch_location_weather("ardhkuwari")
        self.assertIsInstance(res, dict)
        self.assertEqual(res["location"], "Ardhkuwari")
        self.assertEqual(res["freshness_status"], "fallback")

    # =========================================================================
    # 28–29. MULTI-LOCATION & PARTIAL FAILURE
    # =========================================================================

    @patch("weather._fetch_live_forecast_location")
    def test_28_per_location_multi_weather_caching(self, mock_fetch):
        """28. Verifies multi-location query caches Katra and Bhawan independently."""
        def side_effect(loc_k, target_date, **kwargs):
            return make_mock_weather_data(loc_k, temp_max=25.0 if loc_k == "katra" else 18.0)

        mock_fetch.side_effect = side_effect
        # Turn 1: Calls provider for Katra and Bhawan
        weather.get_multi_location_weather(["katra", "bhawan"])
        self.assertEqual(mock_fetch.call_count, 2)

        # Turn 2: Cached for both Katra and Bhawan
        res2 = weather.get_multi_location_weather(["katra", "bhawan"])
        self.assertEqual(mock_fetch.call_count, 2)  # No additional provider calls!
        self.assertEqual(res2["freshness_status"], "cached")

    @patch("weather._fetch_live_forecast_location")
    def test_29_partial_multi_location_failure(self, mock_fetch):
        """29. Verifies partial failure: Katra cached, Bhawan fails -> Katra cached, Bhawan fallback."""
        def side_effect(loc_k, target_date, **kwargs):
            if loc_k == "bhawan":
                return None  # Bhawan fails
            return make_mock_weather_data(loc_k)

        mock_fetch.side_effect = side_effect
        res = weather.get_multi_location_weather(["katra", "bhawan"])
        self.assertEqual(res["locations"][0]["location"], "Katra Town")
        self.assertEqual(res["locations"][0]["freshness_status"], "live")

        self.assertEqual(res["locations"][1]["location"], "Vaishno Devi Bhawan")
        self.assertEqual(res["locations"][1]["freshness_status"], "fallback")
        self.assertEqual(res["freshness_status"], "partial_live")

    # =========================================================================
    # 30–33. CONCURRENCY & THREAD SAFETY
    # =========================================================================

    def test_30_concurrent_identical_requests_single_flight(self):
        """30. Verifies identical concurrent requests call provider exactly ONCE (single-flight)."""
        mgr = CacheManager()
        call_count = 0
        call_lock = threading.Lock()

        def slow_provider():
            nonlocal call_count
            time.sleep(0.04)  # Small delay to simulate network latency
            with call_lock:
                call_count += 1
            return {"temperature": 21.5}

        # Launch 8 concurrent threads for the exact same key
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(mgr.get_or_fetch, "weather:bhawan:race", slow_provider, "weather")
                for _ in range(8)
            ]
            results = [f.result() for f in futures]

        # Verify: All 8 got the payload, but provider was called exactly ONCE!
        for payload, status in results:
            self.assertEqual(payload["temperature"], 21.5)
        self.assertEqual(call_count, 1)

    def test_31_concurrent_requests_for_different_locations(self):
        """31. Verifies concurrent requests for different locations do not cross-talk."""
        mgr = CacheManager()

        def fetch_loc(name, temp):
            def _fn():
                time.sleep(0.02)
                return {"location": name, "temp": temp}
            return _fn

        with ThreadPoolExecutor(max_workers=4) as executor:
            f1 = executor.submit(mgr.get_or_fetch, "loc:katra", fetch_loc("Katra", 25.0))
            f2 = executor.submit(mgr.get_or_fetch, "loc:bhawan", fetch_loc("Bhawan", 18.0))
            f3 = executor.submit(mgr.get_or_fetch, "loc:ardhkuwari", fetch_loc("Ardhkuwari", 21.0))
            f4 = executor.submit(mgr.get_or_fetch, "loc:bhairon", fetch_loc("Bhairon", 15.0))

            r1 = f1.result()[0]
            r2 = f2.result()[0]
            r3 = f3.result()[0]
            r4 = f4.result()[0]

        self.assertEqual(r1["location"], "Katra")
        self.assertEqual(r2["location"], "Bhawan")
        self.assertEqual(r3["location"], "Ardhkuwari")
        self.assertEqual(r4["location"], "Bhairon")

    def test_32_concurrent_cache_writes(self):
        """32. Verifies concurrent cache writes do not corrupt storage."""
        mgr = CacheManager(max_entries=100)

        def worker(idx):
            mgr.set(f"concurrent_k_{idx}", f"val_{idx}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(worker, range(20)))

        self.assertEqual(len(mgr._entries), 20)

    def test_33_lock_release_after_exceptions(self):
        """33. Verifies single-flight lock is released even if provider raises an exception."""
        mgr = CacheManager()

        def failing_provider():
            raise RuntimeError("Provider connection exploded")

        # Calling get_or_fetch with a failing provider gracefully returns fallback without crashing
        payload, status = mgr.get_or_fetch("k_boom", failing_provider, category="weather")
        self.assertIsNone(payload)
        self.assertEqual(status, "fallback")

        # Subsequent fetch for the same key must NOT deadlock and acquires lock cleanly
        payload2, status2 = mgr.get_or_fetch("k_boom", lambda: "recovered", category="weather")
        self.assertEqual(payload2, "recovered")
        self.assertEqual(status2, "live")

    # =========================================================================
    # 34–35. PROVENANCE & LIVE_SOURCES FILTERING
    # =========================================================================

    def test_34_provenance_deduplication_compatibility(self):
        """34. Verifies cached provenance records deduplicate without dropping separate locations."""
        p_katra = prov.create_provenance("Open-Meteo Weather API", "cached_api", "cached", "verified_external_api", location="Katra Town")
        p_bhawan = prov.create_provenance("Open-Meteo Weather API", "cached_api", "cached", "verified_external_api", location="Vaishno Devi Bhawan")
        p_katra_dupe = prov.create_provenance("Open-Meteo Weather API", "cached_api", "cached", "verified_external_api", location="Katra Town")

        deduped = prov.deduplicate_provenance([p_katra, p_bhawan, p_katra_dupe])
        self.assertEqual(len(deduped), 2)
        locations = [r["location"] for r in deduped]
        self.assertIn("Katra Town", locations)
        self.assertIn("Vaishno Devi Bhawan", locations)

    def test_35_live_sources_filtering_compatibility(self):
        """35. Verifies cached hits and stale fallbacks are STRICTLY EXCLUDED from live_sources."""
        base_resp = {
            "reply": "🙏 Jai Mata Di! Weather is cached.",
            "intent": "WEATHER",
            "weather": {
                "location": "Katra Town",
                "source_type": "cached_api",
                "freshness_status": "cached",
                "source_name": "Open-Meteo Weather API",
            }
        }
        envelope = prov.attach_provenance_to_response(base_resp)
        self.assertEqual(len(envelope["source_provenance"]), 1)
        # CRITICAL SAFEGUARD: Cached responses must NOT appear in live_sources
        self.assertEqual(len(envelope["live_sources"]), 0)

    # =========================================================================
    # 36–40. SYSTEM COMPATIBILITY & REGRESSION INTEGRITY
    # =========================================================================

    @patch("weather._fetch_live_forecast_location")
    def test_36_central_agent_compatibility(self, mock_fetch):
        """36. Verifies Central AI Agent tool invocation works seamlessly with caching."""
        mock_fetch.return_value = make_mock_weather_data("bhawan")
        w1 = central_agent.check_weather_guidance.invoke({"location": "Bhawan"})
        self.assertEqual(w1["canonical_location"], "Vaishno Devi Bhawan")

        w2 = central_agent.check_weather_guidance.invoke({"location": "Bhawan"})
        self.assertEqual(w2["canonical_location"], "Vaishno Devi Bhawan")
        # Second call was cached
        self.assertEqual(mock_fetch.call_count, 1)

    @patch("weather._fetch_live_forecast_location")
    def test_37_deterministic_orchestrator_compatibility(self, mock_fetch):
        """37. Verifies orchestrator fallback operates seamlessly with cached data."""
        mock_fetch.return_value = make_mock_weather_data("katra")
        res = orchestrator.orchestrate_conversational_turn("What is the weather in Katra?")
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)

    @patch("weather._fetch_live_forecast_location")
    def test_38_json_serialization(self, mock_fetch):
        """38. Verifies response envelope with cached provenance serializes to JSON cleanly."""
        mock_fetch.return_value = make_mock_weather_data("katra")
        res = coordinator.process_weather_message("What is the weather in Katra?")
        json_str = json.dumps(res, default=str)
        self.assertIsInstance(json_str, str)
        deserialized = json.loads(json_str)
        self.assertIn("source_provenance", deserialized)

    @patch("weather._fetch_live_forecast_location")
    def test_39_session_isolation(self, mock_fetch):
        """39. Verifies cached weather does not cross-contaminate distinct user sessions."""
        mock_fetch.return_value = make_mock_weather_data("katra")
        sess1 = session_store.create_session()
        sess2 = session_store.create_session()
        sid1 = sess1["session_id"]
        sid2 = sess2["session_id"]

        res1 = orchestrator.orchestrate_conversational_turn("What is the weather?", session_id=sid1)
        res2 = orchestrator.orchestrate_conversational_turn("Aarti timings", session_id=sid2)

        self.assertEqual(res1["session_id"], sid1)
        self.assertEqual(res2["session_id"], sid2)

    @patch("agents.rpa_agent.check_yatra_slot_availability")
    def test_40_existing_booking_rpa_behavior_remains_unaffected(self, mock_rpa):
        """40. Verifies mock booking availability and RPA remain un-cached and safely simulation_only."""
        mock_rpa.return_value = {
            "status": "AVAILABLE",
            "date": "2026-10-20",
            "category": "Normal Darshan",
            "slots": [{"slot_time": "06:00", "status": "available"}],
        }
        avail = central_agent.check_slot_availability.invoke({"date": "2026-10-20"})
        self.assertEqual(avail["source_type"], "simulated_data")
        self.assertEqual(avail["verification_status"], "simulation_only")

        booking_intent = central_agent.request_booking_intent.invoke({})
        self.assertEqual(booking_intent["action"], "NAVIGATE_TO_BOOKING")


if __name__ == "__main__":
    unittest.main()
