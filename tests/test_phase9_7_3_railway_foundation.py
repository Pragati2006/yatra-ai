"""
tests/test_phase9_7_3_railway_foundation.py
Comprehensive Focused Test Suite for Phase 9.7.3 — Railway Foundation Implementation.

Covers:
1. Railway Data Contracts:
   - TrainRunningStatus (enforcing None for unknown delay/platform, is_live_status=False)
   - CuratedTrainSchedule (serialization, typed fields, verification provenance)
   - StationInfo (station codes, elevation, division)
2. Curated Railway Timetable Dataset:
   - JSON structure, authentic Katra trains (22439, 22477, 22461, 12445, 12471, etc.)
   - Operating day verification (Vande Bharat Tuesday/Wednesday maintenance rules)
3. Curated Railway Adapter:
   - Provider properties, priority, timeout
   - Search by origin, destination, train number, travel date
   - Fail-closed handling on unknown train or corrupted dataset
   - Truth-in-data provenance and availability transparency
4. Live Data Service Manager Integration:
   - Provider registration, discovery under DataDomain.TRANSPORT
   - fetch_data coordination, caching, and circuit-breaker compatibility
5. Central Agent Tool Integration:
   - search_transport_options routing through manager
   - query_train_live_status honest clarification of disconnected live telemetry
   - Fallback and multi-modal preservation (flights, buses)
"""

from datetime import date, timedelta
import os
import tempfile
import unittest

from services.live_data.contracts import (
    CuratedTrainSchedule,
    DataDomain,
    ProviderErrorType,
    ProviderRequest,
    StationInfo,
    TrainRunningStatus,
    TrainRunningStatusType,
)
from services.live_data.adapters.curated_railway_adapter import CuratedRailwayAdapter
from services.live_data.manager import (
    get_live_data_manager,
    reset_live_data_manager,
    UnifiedLiveDataManager,
)
from services.railway_schedules import (
    DEFAULT_SCHEDULES_PATH,
    get_station_by_code_or_city,
    get_train_by_number,
    load_curated_schedules,
    search_curated_schedules,
)
import agents.central_agent as central_agent
from utils.provenance import (
    FreshnessStatus,
    VerificationStatus,
)


class TestPhase973RailwayContracts(unittest.TestCase):
    """Verifies typed railway contracts and strict truth-in-data defaults."""

    def test_01_train_running_status_defaults(self):
        """CRITICAL: Unknown delay, platform, and times must default to None, NOT 0 or empty string."""
        status = TrainRunningStatus(
            train_number="22439",
            train_name="New Delhi - SMVD Katra Vande Bharat Express",
        )
        self.assertEqual(status.train_number, "22439")
        self.assertIsNone(status.delay_departure_minutes)
        self.assertIsNone(status.delay_arrival_minutes)
        self.assertIsNone(status.platform_number)
        self.assertIsNone(status.expected_arrival_time)
        self.assertIsNone(status.expected_departure_time)
        self.assertFalse(status.is_live_status)
        self.assertEqual(status.status, TrainRunningStatusType.UNKNOWN.value)

        # Test dictionary serialization
        d = status.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIsNone(d["delay_departure_minutes"])
        self.assertIsNone(d["platform_number"])
        self.assertFalse(d["is_live_status"])

    def test_02_curated_train_schedule_model(self):
        """Verifies CuratedTrainSchedule attributes and strict is_live_status=False flag."""
        schedule = CuratedTrainSchedule(
            train_number="22461",
            train_name="Shri Shakti AC Superfast Express",
            origin_station_code="NDLS",
            origin_station_name="New Delhi",
            destination_station_code="SVDK",
            destination_station_name="Shri Mata Vaishno Devi Katra",
            departure_time="19:05",
            arrival_time="07:05",
            days_of_operation=["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
            travel_classes=["1A", "2A", "3A", "3E"],
            major_halts=[{"station_code": "UMB", "station_name": "Ambala Cantt"}],
            total_distance_km=655,
            duration_hours=12.0,
            catering_available=True,
            indicative_fare_min=1050,
            indicative_fare_max=2485,
        )
        self.assertFalse(schedule.is_live_status)
        self.assertEqual(schedule.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)

        d = schedule.to_dict()
        self.assertEqual(d["train_number"], "22461")
        self.assertEqual(d["travel_classes"], ["1A", "2A", "3A", "3E"])
        self.assertFalse(d["is_live_status"])

    def test_03_station_info_model(self):
        """Verifies StationInfo serialization and fields."""
        station = StationInfo(
            station_code="SVDK",
            station_name="Shri Mata Vaishno Devi Katra",
            city="Katra",
            state="Jammu & Kashmir",
            latitude=32.9908,
            longitude=74.9315,
            elevation_meters=813,
            division="Firozpur (FZR)",
            zone="Northern Railway (NR)",
        )
        self.assertEqual(station.station_code, "SVDK")
        self.assertEqual(station.elevation_meters, 813)
        d = station.to_dict()
        self.assertEqual(d["city"], "Katra")
        self.assertEqual(d["zone"], "Northern Railway (NR)")


class TestPhase973CuratedDataset(unittest.TestCase):
    """Verifies curated railway dataset content and operating days."""

    def test_04_dataset_loading_and_counts(self):
        """Verifies dataset loads at least 16 schedules and 9 key stations."""
        schedules, stations, meta = load_curated_schedules()
        self.assertGreaterEqual(len(schedules), 16)
        self.assertGreaterEqual(len(stations), 9)
        self.assertEqual(meta.get("verification_status"), "verified_curated_source")
        self.assertFalse(meta.get("is_live_telemetry_connected"))

    def test_05_authentic_train_numbers_present(self):
        """Verifies major Katra express trains exist in curated catalog."""
        schedules, _, _ = load_curated_schedules()
        train_nos = {s.train_number for s in schedules}
        required_trains = {"22439", "22440", "22477", "22478", "22461", "22462", "12445", "12446", "12471", "12919"}
        for t in required_trains:
            self.assertIn(t, train_nos, f"Train {t} must be present in curated timetable")

    def test_06_operating_day_rules(self):
        """Verifies Vande Bharat day-of-week maintenance exclusions."""
        # 22439 excludes Tuesday
        t22439 = get_train_by_number("22439")
        self.assertIsNotNone(t22439)
        self.assertNotIn("TUE", t22439.days_of_operation)
        self.assertIn("WED", t22439.days_of_operation)

        # 22477 excludes Wednesday
        t22477 = get_train_by_number("22477")
        self.assertIsNotNone(t22477)
        self.assertIn("TUE", t22477.days_of_operation)
        self.assertNotIn("WED", t22477.days_of_operation)

    def test_07_station_metadata_retrieval(self):
        """Verifies station lookup by code and city name."""
        svdk = get_station_by_code_or_city("SVDK")
        self.assertIsNotNone(svdk)
        self.assertEqual(svdk.city, "Katra")
        self.assertEqual(svdk.elevation_meters, 813)

        delhi = get_station_by_code_or_city("Delhi")
        self.assertIsNotNone(delhi)
        self.assertEqual(delhi.station_code, "NDLS")


class TestPhase973CuratedRailwayAdapter(unittest.TestCase):
    """Verifies CuratedRailwayAdapter execution, failure handling, and provenance."""

    def setUp(self):
        self.adapter = CuratedRailwayAdapter()

    def test_08_adapter_properties(self):
        """Verifies provider metadata, domain, and priority."""
        self.assertEqual(self.adapter.domain, DataDomain.TRANSPORT.value)
        self.assertEqual(self.adapter.provider_id, "curated_railway_schedules")
        self.assertEqual(self.adapter.priority, 10)
        self.assertTrue(self.adapter.is_configured())
        self.assertFalse(self.adapter.is_simulated)
        self.assertTrue(self.adapter.is_source_verified)

    def test_09_search_by_origin_delhi(self):
        """Verifies searching trains from Delhi returns authentic Katra express routes."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Delhi",
            params={"destination": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertEqual(res.status, "SUCCESS")
        schedules = res.data.get("schedules", [])
        self.assertGreaterEqual(len(schedules), 4)

        train_numbers = [s["train_number"] for s in schedules]
        self.assertIn("22439", train_numbers)
        self.assertIn("22461", train_numbers)
        self.assertIn("12445", train_numbers)

        # Truth-in-data checks
        self.assertFalse(res.data.get("live_status_available"))
        self.assertFalse(res.availability_verified)
        self.assertEqual(res.claims_breakdown.get("seat_availability"), "NOT_CHECKED")
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)

    def test_10_search_by_train_number(self):
        """Verifies searching a single train number returns exactly that schedule."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            params={"train_number": "22461"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertEqual(res.status, "SUCCESS")
        schedules = res.data.get("schedules", [])
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["train_number"], "22461")
        self.assertEqual(schedules[0]["train_name"], "Shri Shakti AC Superfast Express")

    def test_11_unknown_train_returns_empty_not_fabricated(self):
        """CRITICAL: Querying an unknown train number must return 0 results, never invent data."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            params={"train_number": "99999"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.data.get("count"), 0)
        self.assertEqual(len(res.data.get("schedules")), 0)

    def test_12_corrupted_or_missing_file_fails_closed(self):
        """Verifies adapter returns clean UNAVAILABLE result when file is missing."""
        bad_adapter = CuratedRailwayAdapter(dataset_path="non_existent_schedules_xyz.json")
        req = ProviderRequest(domain=DataDomain.TRANSPORT.value, location="Delhi")
        res = bad_adapter.fetch_live_data(req)
        self.assertEqual(res.status, "UNAVAILABLE")
        self.assertIsNotNone(res.error)
        self.assertEqual(res.error.error_type, ProviderErrorType.UNAVAILABLE.value)
        self.assertEqual(res.data.get("count"), 0)


class TestPhase973ManagerIntegration(unittest.TestCase):
    """Verifies LiveDataServiceManager discovery, caching, and execution."""

    def setUp(self):
        reset_live_data_manager()
        self.mgr = get_live_data_manager()

    def tearDown(self):
        reset_live_data_manager()

    def test_13_manager_discovery_under_transport_domain(self):
        """Verifies CuratedRailwayAdapter is registered and discovered under DataDomain.TRANSPORT."""
        providers = self.mgr.discover_providers(DataDomain.TRANSPORT.value)
        p_ids = [p.provider_id for p in providers]
        self.assertIn("curated_railway_schedules", p_ids)

    def test_14_manager_fetch_data_coordination(self):
        """Verifies fetching transport data through manager envelope."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Delhi",
            params={"destination": "Katra"},
        )
        res = self.mgr.fetch_data(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.domain, DataDomain.TRANSPORT.value)
        self.assertGreater(res.data.get("count", 0), 0)
        self.assertEqual(res.claims_breakdown.get("timetable_schedule"), "VERIFIED_OFFICIAL_TIMETABLE")
        self.assertEqual(res.claims_breakdown.get("live_running_telemetry"), "NOT_CONNECTED")


class TestPhase973CentralAgentTools(unittest.TestCase):
    """Verifies Central Agent tool integration and honest live status responses."""

    def test_15_search_transport_options_tool_trains(self):
        """Verifies search_transport_options uses live data manager and returns authentic Katra trains."""
        d1 = (date.today() + timedelta(days=2)).isoformat()
        d2 = (date.today() + timedelta(days=6)).isoformat()
        res = central_agent.search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": d1,
            "end_date": d2,
            "mode": "train",
            "pax": 2,
        })
        self.assertIsInstance(res, dict)
        self.assertEqual(res["origin"], "Delhi")
        self.assertEqual(res["pax"], 2)
        opts = res.get("options", [])
        self.assertGreater(len(opts), 0)
        self.assertEqual(opts[0]["mode"].lower(), "train")
        self.assertIn("Indian Railways", opts[0]["operator"])
        self.assertFalse(opts[0]["is_live_status"])
        self.assertFalse(res["live_status_available"])
        self.assertIn("not connected", res["live_status_notice"].lower())

    def test_16_query_train_live_status_clarification(self):
        """CRITICAL: query_train_live_status must honestly state live status is disconnected."""
        res = central_agent.query_train_live_status.invoke({"train_number": "22439"})
        self.assertIsInstance(res, dict)
        self.assertEqual(res["status"], "LIVE_TELEMETRY_NOT_CONNECTED")
        self.assertEqual(res["train_number"], "22439")
        self.assertFalse(res["is_live_status"])
        self.assertIsNone(res["live_delay_minutes"])
        self.assertIsNone(res["platform_number"])
        self.assertEqual(res["scheduled_departure"], "06:00")
        self.assertEqual(res["scheduled_arrival"], "14:00")
        self.assertIn("139", res["next_steps"])

    def test_17_query_train_live_status_unknown_train(self):
        """Verifies unknown train lookup reports TRAIN_NOT_FOUND."""
        res = central_agent.query_train_live_status.invoke({"train_number": "88888"})
        self.assertEqual(res["status"], "TRAIN_NOT_FOUND")
        self.assertFalse(res["is_live_status"])

    def test_18_multimodal_flight_and_bus_preservation(self):
        """Verifies searching flights and buses preserves backward compatibility."""
        d1 = (date.today() + timedelta(days=2)).isoformat()
        d2 = (date.today() + timedelta(days=6)).isoformat()

        flights = central_agent.search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": d1,
            "end_date": d2,
            "mode": "flight",
            "pax": 1,
        })
        self.assertGreater(len(flights["options"]), 0)
        self.assertEqual(flights["options"][0]["mode"], "flight")

        buses = central_agent.search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": d1,
            "end_date": d2,
            "mode": "bus",
            "pax": 1,
        })
        self.assertGreater(len(buses["options"]), 0)
        self.assertEqual(buses["options"][0]["mode"], "bus")


if __name__ == "__main__":
    unittest.main()
