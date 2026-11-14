"""
tests/test_phase9_8_1_bus_provider.py

Phase 9.8.1: Curated Bus Registry & JKRTC Provider Implementation Test Suite.

Verifies:
1. Data Contract Integrity: CuratedBusSchedule fail-closed validation and immutable static flag.
2. Curated Dataset Audit: 4 authentic corridors without synthetic departure minutes or unevidenced fares.
3. Bus Schedules Service: Thread-safe caching, location matching, and coverage limitations for unsupported routes.
4. Curated Bus Adapter: Unified Live Data Architecture integration, provenance attribution, claims breakdown.
5. Live Data Manager Registration: Retrieval via UnifiedLiveDataManager with domain and provider_id routing.
6. Central Agent Tool Integration: search_transport_options bus routing and coverage limitation propagation.
7. Database Isolation: db.search_buses returns curated records or empty list, completely eliminating synthetic CSV data.
8. End-to-End Booking Lifecycle: Successful booking creation using authentic curated bus options.
"""

from datetime import date, timedelta
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.central_agent import search_transport_options
import db
from services.bus_schedules import (
    DEFAULT_BUS_SCHEDULES_PATH,
    get_bus_service_by_id,
    get_bus_service_summary,
    load_curated_bus_schedules,
    search_curated_bus_schedules,
)
from services.live_data.adapters.curated_bus_adapter import CuratedBusAdapter
from services.live_data.contracts import (
    CuratedBusSchedule,
    DataDomain,
    ProviderRequest,
)
from services.live_data.manager import get_live_data_manager, reset_live_data_manager
from utils.provenance import VerificationStatus


class TestPhase981CuratedBusRegistry(unittest.TestCase):
    """Verifies contracts, datasets, and service logic for Curated Bus Registry."""

    def setUp(self):
        self.dataset_path = DEFAULT_BUS_SCHEDULES_PATH
        self.assertTrue(os.path.exists(self.dataset_path), "Curated bus dataset must exist.")

    # -------------------------------------------------------------------------
    # 1. Data Contract Integrity
    # -------------------------------------------------------------------------

    def test_01_curated_bus_schedule_contract_defaults(self):
        """Verifies CuratedBusSchedule enforces static schedule flag and full provenance."""
        sched = CuratedBusSchedule(
            service_id="bus_test_1",
            operator_name="JKRTC",
            service_type="STAGE_CARRIAGE_FREQUENCY",
            origin_bus_stand="Jammu GBS",
            destination_bus_stand="Katra Bus Stand",
            origin_city="Jammu",
            destination_city="Katra",
            source_name="J&K Transport Dept",
            source_url="https://jaktrans.jk.gov.in/",
            source_circular_reference="STA Notification 01-P-MVD of 2026",
            verified_at="2026-11-07T12:00:00Z",
            verified_by="Transport Auditor",
        )
        self.assertFalse(sched.is_live_status, "is_live_status must always be False for static schedule")
        self.assertEqual(sched.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)
        self.assertIsInstance(sched.to_dict(), dict)

    def test_02_curated_bus_schedule_downgrades_when_source_missing(self):
        """CuratedBusSchedule must downgrade verification_status to UNVERIFIED if source evidence is missing."""
        sched = CuratedBusSchedule(
            service_id="bus_test_unverified",
            operator_name="JKRTC",
            service_type="STAGE_CARRIAGE_FREQUENCY",
            origin_bus_stand="Jammu GBS",
            destination_bus_stand="Katra Bus Stand",
            origin_city="Jammu",
            destination_city="Katra",
            source_name="J&K Transport Dept",
            source_url="",  # Missing URL
            source_circular_reference="STA Notification 01-P-MVD of 2026",
            verified_at="2026-11-07T12:00:00Z",
            verified_by="Transport Auditor",
        )
        self.assertEqual(sched.verification_status, VerificationStatus.UNVERIFIED.value)

    # -------------------------------------------------------------------------
    # 2. Curated Dataset Audit
    # -------------------------------------------------------------------------

    def test_03_curated_dataset_audit_metadata(self):
        """Verifies metadata in curated_bus_schedules.json contains official circular references."""
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        self.assertEqual(meta.get("audit_status"), "AUDITED_PHASE_9_8_1")
        self.assertEqual(meta.get("version"), "1.0.0")
        self.assertIn("STA Notification No. 01-P-MVD of 2026", meta.get("source_circular_reference", ""))
        self.assertIn("S.O. Notification No. 126", meta.get("source_circular_reference", ""))

    def test_04_curated_dataset_corridors_and_no_fake_departure_times(self):
        """Verifies 4 authentic corridors exist and do NOT invent minute-level departure times."""
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        schedules = data.get("schedules", [])
        self.assertEqual(len(schedules), 4, "Must contain exactly 4 verified corridors")

        service_ids = {s["service_id"] for s in schedules}
        self.assertIn("bus_jksrtc_jammu_katra_exp", service_ids)
        self.assertIn("bus_jksrtc_railhead_katra_shuttle", service_ids)
        self.assertIn("bus_udhampur_katra_feeder", service_ids)
        self.assertIn("bus_jksrtc_delhi_katra_interstate", service_ids)

        for s in schedules:
            self.assertFalse(s.get("is_live_status"), "is_live_status must be false")
            # Strict truth-in-data: no synthetic minute-level departure times
            self.assertIsNone(s.get("departure_time"), f"Corridor {s['service_id']} must not claim specific departure time")
            self.assertIsNone(s.get("arrival_time"), f"Corridor {s['service_id']} must not claim specific arrival time")
            self.assertTrue(s.get("source_url"), f"Corridor {s['service_id']} must have valid source_url")
            self.assertTrue(s.get("source_circular_reference"), f"Corridor {s['service_id']} must have source_circular_reference")

    # -------------------------------------------------------------------------
    # 3. Bus Schedules Service Layer
    # -------------------------------------------------------------------------

    def test_05_search_curated_bus_schedules_corridors(self):
        """Verifies searching by origin returns appropriate curated corridors."""
        # Jammu origin
        jammu_buses, meta_j = search_curated_bus_schedules(origin="Jammu")
        self.assertEqual(len(jammu_buses), 2)
        j_ids = {b.service_id for b in jammu_buses}
        self.assertIn("bus_jksrtc_jammu_katra_exp", j_ids)
        self.assertIn("bus_jksrtc_railhead_katra_shuttle", j_ids)

        # Delhi origin
        delhi_buses, meta_d = search_curated_bus_schedules(origin="Delhi")
        self.assertEqual(len(delhi_buses), 1)
        self.assertEqual(delhi_buses[0].service_id, "bus_jksrtc_delhi_katra_interstate")

        # Udhampur origin
        udhampur_buses, meta_u = search_curated_bus_schedules(origin="Udhampur")
        self.assertEqual(len(udhampur_buses), 1)
        self.assertEqual(udhampur_buses[0].service_id, "bus_udhampur_katra_feeder")

    def test_06_search_unsupported_route_returns_coverage_limitation(self):
        """Unsupported origin in bus registry returns coverage_limitation without synthetic records."""
        buses, meta = search_curated_bus_schedules(origin="Varanasi")
        self.assertEqual(len(buses), 0)
        self.assertIn("coverage_limitation", meta)
        cov = meta["coverage_limitation"]
        self.assertEqual(cov["status"], "ROUTE_NOT_IN_CURATED_BUS_REGISTRY")
        self.assertEqual(cov["origin"], "Varanasi")
        self.assertIn("supported_origins", cov)
        self.assertTrue(any("Jammu" in o for o in cov["supported_origins"]))

    def test_07_get_bus_service_by_id_and_summary(self):
        """Verifies lookup by ID and summary reporting."""
        svc = get_bus_service_by_id("bus_jksrtc_jammu_katra_exp")
        self.assertIsNotNone(svc)
        self.assertEqual(svc.origin_city, "Jammu")

        summary = get_bus_service_summary()
        self.assertEqual(summary["total_corridors"], 4)
        self.assertIn("Jammu", summary["supported_origins"])
        self.assertIn("Delhi", summary["supported_origins"])
        self.assertIn("Udhampur", summary["supported_origins"])


class TestPhase981BusAdapterAndManager(unittest.TestCase):
    """Verifies CuratedBusAdapter and UnifiedLiveDataManager registration."""

    def setUp(self):
        reset_live_data_manager()
        self.mgr = get_live_data_manager()
        self.adapter = CuratedBusAdapter()

    def tearDown(self):
        reset_live_data_manager()

    def test_08_bus_adapter_properties(self):
        """Verifies CuratedBusAdapter metadata properties."""
        self.assertEqual(self.adapter.provider_id, "curated_bus_schedules")
        self.assertEqual(self.adapter.domain, DataDomain.TRANSPORT.value)
        self.assertEqual(self.adapter.priority, 12)
        self.assertTrue(self.adapter.is_configured())
        self.assertFalse(self.adapter.is_simulated)
        self.assertTrue(self.adapter.is_source_verified)

    def test_09_bus_adapter_fetch_live_data_success(self):
        """Verifies fetch_live_data returns standardized LiveDataResult."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Jammu",
            params={"origin": "Jammu", "destination": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.domain, DataDomain.TRANSPORT.value)
        self.assertFalse(res.availability_verified)
        self.assertEqual(res.claims_breakdown.get("statutory_fare_slabs"), "VERIFIED_STA_NOTIFICATION")
        self.assertEqual(res.claims_breakdown.get("live_tracking"), "NOT_CONNECTED")
        self.assertFalse(res.data.get("live_status_available"))
        self.assertEqual(res.data.get("count"), 2)

    def test_10_bus_adapter_propagates_coverage_limitation(self):
        """Verifies unsupported origin propagates coverage_limitation in result payload."""
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Mumbai",
            params={"origin": "Mumbai", "destination": "Katra"},
        )
        res = self.adapter.fetch_live_data(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.data.get("count"), 0)
        self.assertIn("coverage_limitation", res.data)
        self.assertEqual(res.data["coverage_limitation"]["status"], "ROUTE_NOT_IN_CURATED_BUS_REGISTRY")

    def test_11_manager_registration_and_routing(self):
        """Verifies CuratedBusAdapter is registered in UnifiedLiveDataManager and accessible via provider_id."""
        prov = self.mgr.get_provider(DataDomain.TRANSPORT.value, "curated_bus_schedules")
        self.assertIsNotNone(prov, "CuratedBusAdapter must be registered in UnifiedLiveDataManager")
        self.assertEqual(prov.provider_id, "curated_bus_schedules")

        # Explicit provider query through manager
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Delhi",
            params={"origin": "Delhi", "destination": "Katra"},
        )
        res = self.mgr.fetch_data(req, provider_id="curated_bus_schedules")
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.provider_id, "curated_bus_schedules")
        self.assertEqual(res.data.get("count"), 1)


class TestPhase981CentralAgentAndDatabase(unittest.TestCase):
    """Verifies Central Agent tool integration, database isolation, and booking flow."""

    def test_12_central_agent_search_transport_options_bus_mode(self):
        """Verifies search_transport_options returns authentic curated buses for Jammu."""
        d1 = (date.today() + timedelta(days=3)).isoformat()
        d2 = (date.today() + timedelta(days=5)).isoformat()
        res = search_transport_options.invoke({
            "origin": "Jammu",
            "start_date": d1,
            "end_date": d2,
            "mode": "bus",
            "pax": 2,
        })
        self.assertIsInstance(res, dict)
        options = res.get("options", [])
        bus_opts = [o for o in options if o.get("mode") == "bus"]
        self.assertGreaterEqual(len(bus_opts), 2, "Must return authentic curated buses for Jammu")

        sample = bus_opts[0]
        self.assertFalse(sample["is_live_status"])
        self.assertEqual(sample["fare_classification"], "STATUTORY_NOTIFIED_PER_KM_SLAB")
        self.assertTrue(sample["fare_disclaimer"])
        self.assertTrue(sample["source_circular_reference"])

    def test_13_central_agent_search_transport_options_unsupported_bus_route(self):
        """Verifies search_transport_options returns coverage_limitation for unsupported bus origin."""
        d1 = (date.today() + timedelta(days=3)).isoformat()
        d2 = (date.today() + timedelta(days=5)).isoformat()
        res = search_transport_options.invoke({
            "origin": "Varanasi",
            "start_date": d1,
            "end_date": d2,
            "mode": "bus",
            "pax": 2,
        })
        options = res.get("options", [])
        bus_opts = [o for o in options if o.get("mode") == "bus"]
        self.assertEqual(len(bus_opts), 0, "Must NEVER return synthetic bus options for unsupported origin")

        cov = res.get("coverage_limitation")
        self.assertIsNotNone(cov, "Must return coverage_limitation for unsupported origin")
        self.assertEqual(cov.get("status"), "ROUTE_NOT_IN_CURATED_BUS_REGISTRY")
        self.assertEqual(cov.get("origin"), "Varanasi")

    def test_14_db_search_buses_isolation(self):
        """Verifies db.search_buses returns curated records or empty list, NEVER synthetic CSV."""
        # Supported route: Jammu
        jammu_records = db.search_buses("Jammu", "2026-11-20", "2026-11-20")
        self.assertGreaterEqual(len(jammu_records), 2)
        sample = jammu_records[0]
        self.assertEqual(sample["mode"], "bus")
        self.assertFalse(sample["is_live_status"])
        self.assertEqual(sample["verification_status"], VerificationStatus.VERIFIED_CURATED_SOURCE.value)

        # Unsupported route: Varanasi -> strictly empty list
        varanasi_records = db.search_buses("Varanasi", "2026-11-20", "2026-11-20")
        self.assertEqual(varanasi_records, [], "Must return empty list for unsupported origin")

        # Unsupported route: Chennai -> strictly empty list
        chennai_records = db.search_buses("Chennai", "2026-11-20", "2026-11-20")
        self.assertEqual(chennai_records, [], "Must return empty list for unsupported origin")

    def test_15_db_create_booking_curated_bus_option(self):
        """Verifies create_booking completes successfully with authentic curated bus transport."""
        bus_options = db.search_buses("Jammu", "2026-11-20", "2026-11-20")
        self.assertGreater(len(bus_options), 0)
        selected_bus = bus_options[0]

        booking_id = db.create_booking(
            user_name="Pilgrim Tester",
            pax_count=2,
            yatra_slot=None,
            transport=selected_bus,
            total_price=(selected_bus.get("price") or selected_bus.get("indicative_fare_min") or 0) * 2,
        )
        self.assertTrue(booking_id.startswith("VD"), f"Booking ID must start with VD, got {booking_id}")


if __name__ == "__main__":
    unittest.main()
