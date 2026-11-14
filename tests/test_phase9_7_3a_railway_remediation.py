"""
tests/test_phase9_7_3a_railway_remediation.py

Phase 9.7.3A: Railway Data Integrity Remediation Verification Suite.
Verifies:
1. Unsupported route returns explicit coverage limitation without synthetic train records.
2. Synthetic fallback rejection: search_transport_options and db.search_trains never fabricate synthetic trains.
3. Strict verification metadata: missing/invalid source evidence is downgraded to UNVERIFIED.
4. Indicative published base tariff classification and explicit fare disclaimers.
5. Static timetable vs live running status strict distinction (is_live_status=False, delays=None).
6. Multimodal flight/bus preservation without claiming live external integrations.
7. End-to-end booking integrity with authentic Katra train options.
"""

import unittest
import json
import os
import tempfile

from services.live_data.contracts import (
    CuratedTrainSchedule,
    TrainRunningStatus,
    VerificationStatus,
    DataDomain,
    ProviderRequest,
)
from services.railway_schedules import (
    load_curated_schedules,
    search_curated_schedules,
    get_train_by_number,
)
from services.live_data.adapters.curated_railway_adapter import CuratedRailwayAdapter
from agents.central_agent import search_transport_options
import db


class TestPhase973ARailwayRemediation(unittest.TestCase):

    def setUp(self):
        self.curated_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "curated_railway_schedules.json"
        )
        self.assertTrue(os.path.exists(self.curated_file), "curated_railway_schedules.json must exist")

    # -------------------------------------------------------------------------
    # 1. Dataset Evidence & Verification Integrity
    # -------------------------------------------------------------------------

    def test_curated_dataset_audit_metadata(self):
        """Verify the curated dataset version and audit status."""
        with open(self.curated_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        self.assertEqual(meta.get("version"), "1.1.0")
        self.assertEqual(meta.get("audit_status"), "AUDITED_PHASE_9_7_3A")
        self.assertIn("irctc", meta.get("audit_note", "").lower())
        self.assertIn("working timetable", meta.get("audit_note", "").lower())

    def test_all_16_schedules_have_traceable_evidence_and_fare_classification(self):
        """Verify all 16 curated schedules have circular reference, official URL, and tariff classification."""
        schedules, stations, meta = load_curated_schedules()
        self.assertEqual(len(schedules), 16, "Must contain exactly 16 curated schedules for 8 Katra corridors")

        for s in schedules:
            # Source evidence
            self.assertTrue(s.train_number, "Train number must not be empty")
            self.assertTrue(s.train_name, f"Train name must not be empty for {s.train_number}")
            self.assertTrue(s.source_url.startswith("https://enquiry.indianrail.gov.in"),
                            f"Train {s.train_number} must trace to NTES official portal")
            self.assertTrue(s.source_circular_reference,
                            f"Train {s.train_number} must have a circular/WTT reference")
            self.assertIn("WTT", s.source_circular_reference)
            self.assertEqual(s.verified_by, "Yatra AI Curatorial & Verification Desk")
            self.assertTrue(s.verified_at, f"Train {s.train_number} must have a verified_at timestamp")
            self.assertEqual(s.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)

            # Fare classification: Phase 9.8.3.1.4 establishes UNAVAILABLE with numerical fares suppressed
            self.assertIn(s.fare_classification, ("UNAVAILABLE", "ESTIMATED_PUBLISHED_BASE_TARIFF"),
                             f"Train {s.train_number} must have UNAVAILABLE or legacy classification")
            self.assertTrue(s.fare_disclaimer, f"Train {s.train_number} must have explicit fare disclaimer")
            self.assertIn("dynamic surge", s.fare_disclaimer.lower())
            if s.fare_classification == "UNAVAILABLE":
                self.assertIsNone(s.indicative_fare_min)
            else:
                self.assertGreater(s.indicative_fare_min, 0)

            # Static timetable distinction
            self.assertFalse(s.is_live_status)

    def test_unverified_record_downgrades_to_unverified(self):
        """Verify records missing official source evidence downgrade to UNVERIFIED during parsing."""
        raw_payload = {
            "metadata": {
                "version": "1.1.0",
                "verification_status": "verified_curated_source"
            },
            "stations": [],
            "schedules": [
                {
                    "train_number": "99999",
                    "train_name": "Test Express",
                    "origin_station_code": "NDLS",
                    "origin_station_name": "New Delhi",
                    "destination_station_code": "SVDK",
                    "destination_station_name": "SMVD Katra",
                    "departure_time": "06:00",
                    "arrival_time": "14:00",
                    "duration_hours": 8.0,
                    "days_of_operation": ["SUN"],
                    "travel_classes": ["CC"],
                    "major_halts": [],
                    "verification_status": "verified_curated_source",
                    # Missing source_name and source_url!
                    "source_name": "",
                    "source_url": "",
                }
            ]
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(raw_payload, tf)
            temp_path = tf.name

        try:
            schedules, _, _ = load_curated_schedules(temp_path)
            self.assertEqual(len(schedules), 1)
            self.assertEqual(schedules[0].verification_status, VerificationStatus.UNVERIFIED.value)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------------------
    # 2. Coverage Limitation vs Synthetic Fallback Rejection
    # -------------------------------------------------------------------------

    def test_search_curated_schedules_returns_coverage_limitation_on_unsupported_route(self):
        """Unsupported origin in search_curated_schedules returns coverage_limitation metadata."""
        schedules, meta = search_curated_schedules(origin="Varanasi")
        self.assertEqual(len(schedules), 0)
        self.assertIn("coverage_limitation", meta)
        cov = meta["coverage_limitation"]
        self.assertEqual(cov["status"], "ROUTE_NOT_IN_CURATED_REGISTRY")
        self.assertEqual(cov["origin"], "Varanasi")
        self.assertIn("supported_origins", cov)
        self.assertTrue(any("Delhi" in o for o in cov["supported_origins"]))

    def test_central_agent_search_transport_options_never_returns_synthetic_trains(self):
        """search_transport_options must NOT fall back to db.search_trains to fabricate synthetic trains."""
        res = search_transport_options.invoke({
            "origin": "Varanasi",
            "start_date": "2026-11-20",
            "end_date": "2026-11-20",
            "mode": "train",
        })
        options = res.get("options", [])
        train_options = [o for o in options if o.get("mode") == "train"]
        self.assertEqual(len(train_options), 0, "Must NEVER return synthetic trains for unsupported origin")

        cov = res.get("coverage_limitation")
        self.assertIsNotNone(cov, "Must return coverage_limitation when train route is not supported")
        self.assertEqual(cov.get("status"), "ROUTE_NOT_IN_CURATED_REGISTRY")
        self.assertEqual(cov.get("origin"), "Varanasi")
        self.assertIn("IRCTC", cov.get("message"))

    def test_db_search_trains_returns_empty_list_for_unsupported_route(self):
        """db.search_trains must return empty list for unsupported origin, never synthetic CSV data."""
        results = db.search_trains("Varanasi", "2026-11-20", "2026-11-20")
        self.assertEqual(results, [])

        results_chennai = db.search_trains("Chennai", "2026-11-20", "2026-11-20")
        self.assertEqual(results_chennai, [])

    def test_db_search_trains_returns_authentic_curated_records_for_supported_route(self):
        """db.search_trains returns authentic verified trains for New Delhi with full provenance."""
        results = db.search_trains("New Delhi", "2026-11-20", "2026-11-20")
        self.assertGreater(len(results), 0)

        train_nos = [t["train_no"] for t in results]
        self.assertIn("22439", train_nos, "Vande Bharat Express must be present")

        sample = next(t for t in results if t["train_no"] == "22439")
        self.assertEqual(sample["verification_status"], VerificationStatus.VERIFIED_CURATED_SOURCE.value)
        self.assertIn(sample["fare_classification"], ("UNAVAILABLE", "ESTIMATED_PUBLISHED_BASE_TARIFF"))
        self.assertFalse(sample["is_live_status"])
        self.assertTrue(sample["fare_disclaimer"])
        self.assertTrue(sample["source_circular_reference"])

    # -------------------------------------------------------------------------
    # 3. Static Timetable vs Live Running Status Distinction
    # -------------------------------------------------------------------------

    def test_static_timetable_contracts_cannot_simulate_live_status(self):
        """Ensure CuratedTrainSchedule and TrainRunningStatus have fail-closed live defaults."""
        sched = CuratedTrainSchedule(
            train_number="22439",
            train_name="Vande Bharat",
            origin_station_code="NDLS",
            origin_station_name="New Delhi",
            destination_station_code="SVDK",
            destination_station_name="SMVD Katra",
            departure_time="06:00",
            arrival_time="14:00",
            duration_hours=8.0,
            days_of_operation=["SUN"],
            travel_classes=["CC"],
            major_halts=[],
        )
        self.assertFalse(sched.is_live_status)

        status = TrainRunningStatus(
            train_number="22439",
            train_name="Vande Bharat",
        )
        self.assertFalse(status.is_live_status)
        self.assertIsNone(status.delay_departure_minutes)
        self.assertIsNone(status.delay_arrival_minutes)
        self.assertIsNone(status.platform_number)

    def test_curated_railway_adapter_propagates_coverage_limitation(self):
        """CuratedRailwayAdapter propagates coverage_limitation in payload when route is uncurated."""
        adapter = CuratedRailwayAdapter()
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location="Patna",
            params={"origin": "Patna", "destination": "Katra"},
        )
        response = adapter.fetch_live_data(req)
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(len(response.data.get("schedules", [])), 0)
        self.assertIn("coverage_limitation", response.data)
        self.assertEqual(response.data["coverage_limitation"]["status"], "ROUTE_NOT_IN_CURATED_REGISTRY")

    # -------------------------------------------------------------------------
    # 4. Multimodal Transport & Demonstration Labeling Preservation
    # -------------------------------------------------------------------------

    def test_multimodal_flights_and_buses_labeled_demonstration(self):
        """Flight and bus demonstration options must be explicitly labeled without claiming live APIs."""
        res_flight = search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": "2026-11-20",
            "end_date": "2026-11-20",
            "mode": "flight",
        })
        flight_opts = res_flight.get("options", [])
        self.assertGreater(len(flight_opts), 0)
        for opt in flight_opts:
            self.assertEqual(opt.get("mode"), "flight")
            self.assertEqual(opt.get("source_type"), "indicative_data")
            self.assertIn("demonstration", opt.get("route_note", "").lower())
            self.assertFalse(opt.get("is_live_status"))

        res_bus = search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": "2026-11-20",
            "end_date": "2026-11-20",
            "mode": "bus",
        })
        bus_opts = res_bus.get("options", [])
        self.assertGreater(len(bus_opts), 0)
        for opt in bus_opts:
            self.assertEqual(opt.get("mode"), "bus")
            self.assertEqual(opt.get("source_type"), "indicative_data")
            self.assertIn("demonstration", opt.get("route_note", "").lower())
            self.assertFalse(opt.get("is_live_status"))

    # -------------------------------------------------------------------------
    # 5. Booking and RPA End-to-End Regression Protection
    # -------------------------------------------------------------------------

    def test_booking_creation_with_curated_train_record(self):
        """db.create_booking creates and stores a booking with authentic curated train options."""
        trains = db.search_trains("New Delhi", "2026-11-20", "2026-11-20")
        self.assertGreater(len(trains), 0)
        chosen_train = trains[0]

        booking_id = db.create_booking(
            user_name="SafetyAuditUser",
            pax_count=1,
            yatra_slot={"id": "mock_slot", "category": "Normal Darshan", "slot_date": "2026-11-21", "slot_time": "09:00", "price": 0},
            transport=chosen_train,
            total_price=chosen_train["price"]
        )
        self.assertTrue(booking_id.startswith("VD"))

        fetched = db.get_booking(booking_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["booking_id"], booking_id)
        self.assertEqual(fetched["transport_mode"], "train")
        self.assertEqual(fetched["origin"], chosen_train["origin"])
        self.assertEqual(fetched["transport_price"], chosen_train["price"])

        # Clean up test row
        import pandas as pd
        df = pd.read_csv(db.BOOKINGS_FILE)
        df = df[df["booking_id"] != booking_id]
        df.to_csv(db.BOOKINGS_FILE, index=False)


if __name__ == "__main__":
    unittest.main()
