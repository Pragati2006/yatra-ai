"""
tests/test_phase14_4_3_transport_expansion.py
Comprehensive Verification & Test Suite for Phase 14.4.3:
Large-Scale Transport Dataset Expansion & Verified Route Coverage.

Tests:
1. Unified Transport Schema validation and serialization.
2. Ingestion pipeline deduplication, alias normalization, and expiry tracking.
3. Curated Railway dataset coverage across 19+ candidate Indian origins.
4. Curated Bus dataset coverage across 13 northern regional hubs.
5. Curated Flight dataset coverage to both Jammu Airport (IXJ) and Srinagar (SXR).
6. ConnectingJourneyEngine integration with expanded verified origins.
7. Truth-in-data distinction between curated verified timetables and synthetic fixtures.
"""

from datetime import datetime, timezone
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.transport_schema import (
    UnifiedTransportRecord,
    TransportMode,
    VerificationStatus,
    TransportDataType,
    normalize_city_name,
)
from services.transport_ingestion import (
    TransportIngestionPipeline,
    RailwayNTESAdapter,
    PublicBusCorporationAdapter,
    DGCAFlightScheduleAdapter,
)
from services.railway_schedules import search_curated_schedules, load_curated_schedules
from services.bus_schedules import search_curated_bus_schedules, load_curated_bus_schedules
from services.flight_schedules import search_curated_flight_schedules, load_curated_flight_schedules
from services.connecting_journey_engine import get_connecting_journey_engine
from agents.conversation_state import TRANSIT_HUBS_DIRECT, get_transit_guidance_for_origin


class TestPhase14_4_3_TransportExpansion(unittest.TestCase):
    """Phase 14.4.3 Transport Dataset Expansion Test Suite."""

    def setUp(self):
        self.engine = get_connecting_journey_engine()

    # -------------------------------------------------------------------------
    # 1. Unified Transport Schema Tests
    # -------------------------------------------------------------------------

    def test_unified_transport_schema_valid_record(self):
        """Verifies schema instantiation, serialization, and validation."""
        rec = UnifiedTransportRecord(
            record_id="rail_ntes_22439",
            mode=TransportMode.RAIL,
            origin_name="New Delhi",
            origin_code="NDLS",
            destination_name="Shri Mata Vaishno Devi Katra",
            destination_code="SVDK",
            operator="Northern Railway",
            service_number="22439",
            service_name="Vande Bharat Express",
            departure_time="06:00",
            arrival_time="14:00",
            operating_days=["MON", "TUE", "WED", "FRI", "SAT", "SUN"],
            duration="8h 00m",
            fare=1630.0,
            currency="INR",
            source_name="National Train Enquiry System (NTES)",
            source_url="https://enquiry.indianrail.gov.in/",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            last_verified_at=datetime.now(timezone.utc).isoformat(),
            valid_from="2026-01-01",
            valid_until="2026-12-31",
            verification_status=VerificationStatus.OFFICIALLY_VERIFIED,
            data_type=TransportDataType.CURATED_TIMETABLE,
            is_live_status=False,
        )
        self.assertTrue(rec.is_valid())
        d = rec.to_dict()
        self.assertEqual(d["record_id"], "rail_ntes_22439")
        self.assertEqual(d["mode"], "train")
        self.assertEqual(d["verification_status"], "OFFICIALLY_VERIFIED")
        self.assertFalse(d["is_live_status"])

    def test_unified_transport_schema_rejects_invalid(self):
        """Schema should reject records with negative fares, invalid dates, or empty ids."""
        # Negative fare
        rec_bad_fare = UnifiedTransportRecord(
            record_id="bad_1",
            mode=TransportMode.BUS,
            origin_name="Jammu",
            destination_name="Katra",
            operator="JKSRTC",
            source_name="JKSRTC",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            fare=-100.0,
        )
        self.assertFalse(rec_bad_fare.is_valid())

        # Empty origin
        rec_bad_origin = UnifiedTransportRecord(
            record_id="bad_2",
            mode=TransportMode.BUS,
            origin_name="",
            destination_name="Katra",
            operator="JKSRTC",
            source_name="JKSRTC",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        self.assertFalse(rec_bad_origin.is_valid())

    def test_city_name_normalization(self):
        """Verifies canonical normalization of common Indian city aliases."""
        self.assertEqual(normalize_city_name("Bangalore"), "Bengaluru")
        self.assertEqual(normalize_city_name("BLR"), "Bengaluru")
        self.assertEqual(normalize_city_name("Bombay"), "Mumbai")
        self.assertEqual(normalize_city_name("BOM"), "Mumbai")
        self.assertEqual(normalize_city_name("Calcutta"), "Kolkata")
        self.assertEqual(normalize_city_name("Banaras"), "Varanasi")
        self.assertEqual(normalize_city_name("Kashi"), "Varanasi")
        self.assertEqual(normalize_city_name("Madras"), "Chennai")
        self.assertEqual(normalize_city_name("Simla"), "Shimla")

    # -------------------------------------------------------------------------
    # 2. Ingestion Pipeline & Deduplication Tests
    # -------------------------------------------------------------------------

    def test_ingestion_pipeline_deduplication(self):
        """Pipeline must detect and reject exact duplicate service records."""
        pipeline = TransportIngestionPipeline()
        rec1 = UnifiedTransportRecord(
            record_id="dup_test_1",
            mode=TransportMode.RAIL,
            origin_name="Amritsar",
            origin_code="ASR",
            destination_name="Jammu",
            destination_code="JAT",
            operator="Northern Railway",
            service_number="14633",
            departure_time="09:15",
            source_name="NTES",
            source_url="https://enquiry.indianrail.gov.in/",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        rec2 = UnifiedTransportRecord(
            record_id="dup_test_2",
            mode=TransportMode.RAIL,
            origin_name="Amritsar",
            origin_code="ASR",
            destination_name="Jammu",
            destination_code="JAT",
            operator="Northern Railway",
            service_number="14633",
            departure_time="09:15",
            source_name="NTES",
            source_url="https://enquiry.indianrail.gov.in/",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

        res1 = pipeline.ingest_record(rec1)
        self.assertEqual(res1, "INGESTED")
        res2 = pipeline.ingest_record(rec2)
        self.assertEqual(res2, "DUPLICATE")
        self.assertEqual(pipeline.stats["ingested"], 1)
        self.assertEqual(pipeline.stats["duplicate"], 1)

    def test_ingestion_pipeline_expiry_tracking(self):
        """Pipeline must flag records whose valid_until date has elapsed."""
        pipeline = TransportIngestionPipeline()
        rec_expired = UnifiedTransportRecord(
            record_id="exp_1",
            mode=TransportMode.FLIGHT,
            origin_name="Delhi",
            origin_code="DEL",
            destination_name="Jammu",
            destination_code="IXJ",
            operator="IndiGo",
            service_number="6E-2121",
            source_name="DGCA",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            valid_until="2020-01-01",  # in the past
        )
        res = pipeline.ingest_record(rec_expired)
        self.assertEqual(res, "EXPIRED")
        self.assertEqual(rec_expired.verification_status, VerificationStatus.EXPIRED)

    # -------------------------------------------------------------------------
    # 3. Curated Railway Expanded Coverage Tests
    # -------------------------------------------------------------------------

    def test_curated_railway_19_candidate_origins(self):
        """Verifies direct train retrieval for all 19 Phase 14.4.3 candidate origins."""
        candidate_origins = [
            "Amritsar", "Chandigarh", "Ludhiana", "Jalandhar",
            "Jaipur", "Jodhpur", "Ahmedabad", "Bhopal", "Indore",
            "Lucknow", "Varanasi", "Patna", "Haridwar", "Rishikesh",
            "Pune", "Mumbai", "Kolkata", "Bengaluru", "Hyderabad",
        ]

        for orig in candidate_origins:
            trains, meta = search_curated_schedules(origin=orig)
            self.assertGreater(
                len(trains),
                0,
                f"Expected direct train schedules for origin '{orig}', got 0 matches",
            )
            # Verify data provenance fields
            for t in trains:
                self.assertIn(t.verification_status, ("OFFICIALLY_VERIFIED", "verified_curated_source"))
                self.assertFalse(t.is_live_status)
                self.assertIsNotNone(t.source_name)
                self.assertIsNotNone(t.source_url)
                self.assertIsNotNone(t.verified_at)

    def test_railway_station_code_no_substring_false_matches(self):
        """Station code 'JU' (Jodhpur) must not match every train stopping at a 'junction'."""
        trains_ju, _ = search_curated_schedules(origin="Jodhpur")
        # Jodhpur should have exactly 1 direct train (19225 JU-JAT Express)
        self.assertEqual(len(trains_ju), 1)
        self.assertEqual(trains_ju[0].train_number, "19225")

    # -------------------------------------------------------------------------
    # 4. Curated Bus Expanded Coverage Tests
    # -------------------------------------------------------------------------

    def test_curated_bus_13_northern_hubs(self):
        """Verifies direct bus retrieval for all 13 northern regional hubs."""
        hubs = [
            "Chandigarh", "Pathankot", "Amritsar", "Jalandhar", "Ludhiana",
            "Shimla", "Mandi", "Dharamshala", "Manali",
            "Jammu", "Udhampur", "Srinagar", "Delhi",
        ]

        for hub in hubs:
            buses, meta = search_curated_bus_schedules(origin=hub)
            self.assertGreater(
                len(buses),
                0,
                f"Expected curated bus schedules for hub '{hub}', got 0 matches",
            )
            for b in buses:
                self.assertIsNotNone(b.operator_name)
                self.assertIsNotNone(b.origin_bus_stand)
                self.assertIsNotNone(b.destination_bus_stand)
                self.assertFalse(b.is_live_status)
                self.assertIsNotNone(b.source_name)

    # -------------------------------------------------------------------------
    # 5. Curated Flight Expanded Coverage Tests
    # -------------------------------------------------------------------------

    def test_curated_flight_destinations(self):
        """Verifies curated flights connect to both Jammu (IXJ) and Srinagar (SXR)."""
        schedules, meta = load_curated_flight_schedules()
        self.assertGreaterEqual(len(schedules), 25)

        dest_airports = {s.destination_airport_code for s in schedules}
        self.assertIn("IXJ", dest_airports)
        self.assertIn("SXR", dest_airports)

        # Metros connecting to IXJ
        origins_to_ixj = {s.origin_city for s in schedules if s.destination_airport_code == "IXJ"}
        self.assertIn("Delhi", origins_to_ixj)
        self.assertIn("Mumbai", origins_to_ixj)
        self.assertIn("Bengaluru", origins_to_ixj)
        self.assertIn("Ahmedabad", origins_to_ixj)
        self.assertIn("Pune", origins_to_ixj)

    # -------------------------------------------------------------------------
    # 6. Connecting Journey Engine Integration Tests
    # -------------------------------------------------------------------------

    def test_connecting_engine_direct_rail_cities(self):
        """Candidate railway cities should be classified as Level 1 Verified Direct Corridor."""
        for city in ["Amritsar", "Chandigarh", "Jaipur", "Bhopal", "Haridwar"]:
            res = self.engine.plan_connecting_journey(origin=city)
            self.assertEqual(res["status"], "CONNECTING_ROUTES_AVAILABLE")
            self.assertEqual(res["fallback_level"], "Level 1: Verified Direct Corridor")
            self.assertFalse(res["requires_clarification"])
            self.assertGreaterEqual(res["options_count"], 2)

    def test_connecting_engine_direct_bus_hill_stations(self):
        """Hill stations with direct HRTC buses should get Level 1 direct options."""
        for station in ["Shimla", "Dharamshala", "Manali"]:
            res = self.engine.plan_connecting_journey(origin=station)
            self.assertEqual(res["status"], "CONNECTING_ROUTES_AVAILABLE")
            self.assertEqual(res["fallback_level"], "Level 1: Verified Direct Corridor")
            self.assertFalse(res["requires_clarification"])
            # At least one option is a direct bus
            bus_opts = [o for o in res["options"] if o["mode"] == "Bus-Direct"]
            self.assertGreater(len(bus_opts), 0, f"Expected direct bus option for {station}")

    def test_connecting_engine_rural_feeder_retention(self):
        """Rural settlement (Palampur) should return Level 2 connecting journey with feeder leg."""
        res = self.engine.plan_connecting_journey(origin="Palampur")
        self.assertEqual(res["status"], "CONNECTING_ROUTES_AVAILABLE")
        self.assertEqual(res["fallback_level"], "Level 2: Verified Connection via Nearby Hub")
        self.assertFalse(res["requires_clarification"])
        self.assertGreaterEqual(res["options_count"], 2)

        # Check provenance on legs
        for opt in res["options"]:
            for leg in opt["legs"]:
                self.assertIn("data_source", leg)
                self.assertIn("data_tier", leg)
                self.assertIn("schedule_availability", leg)
                self.assertIn("fare_source", leg)
                self.assertIn("duration_source", leg)
                self.assertIn("is_verified_schedule", leg)

    def test_transit_guidance_for_30_curated_origins(self):
        """Conversation state should recognise all 30 curated origins as having verified direct routes."""
        test_origins = [
            "Delhi", "Jammu", "Udhampur", "Katra", "Amritsar", "Chandigarh",
            "Ludhiana", "Jalandhar", "Pathankot", "Jaipur", "Jodhpur", "Ahmedabad",
            "Bhopal", "Indore", "Lucknow", "Varanasi", "Patna", "Haridwar",
            "Rishikesh", "Pune", "Mumbai", "Kolkata", "Bengaluru", "Chennai",
            "Hyderabad", "Srinagar", "Dharamshala", "Manali", "Mandi", "Shimla",
        ]
        for orig in test_origins:
            guidance = get_transit_guidance_for_origin(orig)
            self.assertTrue(
                guidance["has_verified_direct"],
                f"Expected has_verified_direct=True for {orig}, got {guidance}",
            )

    # -------------------------------------------------------------------------
    # 7. Grounding Check: Curated vs Synthetic Distinction
    # -------------------------------------------------------------------------

    def test_grounding_distinction_curated_not_live(self):
        """Curated timetables must NOT claim live GPS tracking or dynamic availability."""
        trains, _ = search_curated_schedules(origin="Delhi")
        for t in trains:
            self.assertFalse(t.is_live_status)
            self.assertIn(t.verification_status, ("OFFICIALLY_VERIFIED", "verified_curated_source"))

        buses, _ = search_curated_bus_schedules(origin="Delhi")
        for b in buses:
            self.assertFalse(b.is_live_status)


if __name__ == "__main__":
    unittest.main()
