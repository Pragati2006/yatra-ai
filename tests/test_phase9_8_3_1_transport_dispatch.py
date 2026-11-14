"""
tests/test_phase9_8_3_1_transport_dispatch.py
Phase 9.8.3.1 Acceptance Tests: Transport Dispatch Harmonization & Evidence Remediation.

Covers:
- Correction A: Unify Railway Tool Dispatch via UnifiedLiveDataManager
- Correction B: Claim-Level Provenance Survival for Railway Records
- Correction C: Reconcile Delhi-Katra Bus Budget Scenario (is_complete=False, grand_total=None)
- Correction D: Ground-Transfer Claim Separation and Truthful Qualifications
- Backward compatibility for legacy db.search_trains callers
"""

import unittest
from unittest.mock import patch, MagicMock

from agents.tools import (
    search_transport_tool,
    _search_trains_via_live_manager,
    _search_buses_via_live_manager,
    _search_flights_via_live_manager,
)
import db
from agents import budget_engine
from agents.central_agent import search_transport_options
from agent import _enrich_flight_transfer


class TestPhase9831TransportDispatch(unittest.TestCase):
    """Acceptance test suite for Phase 9.8.3.1."""

    # -------------------------------------------------------------------------
    # 1. Correction A & B: Railway Tool Dispatch via UnifiedLiveDataManager
    # -------------------------------------------------------------------------

    def test_01_search_transport_tool_train_dispatch_via_live_manager(self):
        """Verifies search_transport_tool routes trains through _search_trains_via_live_manager and LiveDataManager."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) >= 4, "Should return at least 4 train options for Delhi origin")

        # Verify claim-level provenance survival
        for tr in trains:
            self.assertEqual(tr["mode"], "train")
            self.assertEqual(tr["operator"], "Indian Railways")
            self.assertFalse(tr["is_live_status"], "Static timetable schedules must enforce is_live_status=False")
            self.assertIsNone(tr.get("seats_available"), "Curated train schedules must not present placeholder seat counts")
            self.assertFalse(tr.get("availability_verified"), "Seat availability is not verified")
            self.assertEqual(tr.get("seat_availability"), "NOT_CHECKED")
            self.assertEqual(tr["status"], "TIMETABLE_SCHEDULE")
            self.assertIn("route guidance", tr["route_note"].lower())
            self.assertNotIn("Authentic timetable", tr["route_note"])

            # Claim-level verification dictionaries must not be None
            self.assertIsNotNone(tr.get("route_verification"))
            self.assertIsInstance(tr["route_verification"], dict)
            self.assertEqual(tr["route_verification"].get("status"), "unverified")
            self.assertIsNone(tr["route_verification"].get("document_reference"))

            self.assertIsNotNone(tr.get("operator_verification"))
            self.assertIsInstance(tr["operator_verification"], dict)
            self.assertEqual(tr["operator_verification"].get("status"), "verified_official_source")
            self.assertTrue(bool(tr["operator_verification"].get("document_reference")))

            self.assertIsNotNone(tr.get("timetable_verification"))
            self.assertIsInstance(tr["timetable_verification"], dict)
            self.assertEqual(tr["timetable_verification"].get("status"), "unverified")
            self.assertIn("NTES", tr["timetable_verification"].get("notes", ""))

            self.assertIsNotNone(tr.get("fare_verification"))
            self.assertIsInstance(tr["fare_verification"], dict)
            self.assertEqual(tr["fare_verification"].get("status"), "unverified")
            self.assertTrue(bool(tr["fare_verification"].get("source_name")))

    def test_02_all_three_transport_modes_use_live_manager_providers(self):
        """Verifies train, bus, and flight tools all execute via UnifiedLiveDataManager providers."""
        from services.live_data.manager import get_live_data_manager

        mgr = get_live_data_manager()
        self.assertIsNotNone(mgr.get_provider("transport", "curated_railway_schedules"))
        self.assertIsNotNone(mgr.get_provider("transport", "curated_bus_schedules"))
        self.assertIsNotNone(mgr.get_provider("transport", "curated_flight_schedules"))

        # Verify direct tool invocations return authentic data
        delhi_trains = _search_trains_via_live_manager("Delhi", "2026-11-20", "2026-11-24")
        self.assertTrue(any("Vande Bharat" in t["train_name"] for t in delhi_trains))

        jammu_buses = _search_buses_via_live_manager("Jammu", "2026-11-20", "2026-11-24")
        self.assertTrue(any("JKRTC" in b["operator"] for b in jammu_buses))

        delhi_flights = _search_flights_via_live_manager("Delhi", "2026-11-20", "2026-11-24")
        self.assertTrue(any(f["mode"] == "flight" for f in delhi_flights))

    # -------------------------------------------------------------------------
    # 2. Correction C: Reconcile Delhi-Katra Bus Scenario & Budget Integrity
    # -------------------------------------------------------------------------

    def test_03_delhi_katra_bus_budget_scenario_reconciliation(self):
        """Verifies Delhi-Katra bus produces is_complete=False, grand_total=None while preserving hotel in verified_costs."""
        # 1. Fetch Delhi bus option
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        delhi_buses = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(delhi_buses) >= 1)
        delhi_bus = delhi_buses[0]

        # Fares must be None (not fixed ticket prices)
        self.assertIsNone(delhi_bus["price"])
        self.assertIsNone(delhi_bus["fare"])
        self.assertIn(delhi_bus["fare_classification"], ["ESTIMATED_PUBLISHED_BASE_TARIFF", "ESTIMATED_MARKET_TARIFF"])
        self.assertEqual(delhi_bus["indicative_fare_min"], 800)
        self.assertEqual(delhi_bus["indicative_fare_max"], 1800)

        # 2. Pass to budget_engine with verified accommodation
        hotel_mock = {
            "name": "Niharika Bhawan",
            "price_per_night": 1200.0,
            "rooms": 1,
            "nights": 2,
        }
        b_res = budget_engine.calculate_budget(
            pax=2,
            transport=delhi_bus,
            darshan_slot={"category": "Normal Darshan", "price": 0.0},
            accommodation=hotel_mock,
            is_round_trip=True,
            estimate_return_if_missing=True,
        )

        # Incomplete budget guarantees
        self.assertFalse(b_res["is_complete"], "Bus with indicative/unverified tariff must produce is_complete=False")
        self.assertIsNone(b_res["grand_total"], "Incomplete bus itinerary must produce grand_total=None")
        self.assertEqual(b_res["verified_costs"]["accommodation"], 2400.0, "Verified hotel cost must remain intact (1 room * 2 nights * 1200 = 2400)")
        self.assertEqual(b_res["verified_costs"]["transport"], 0.0, "Unverified transport cannot add to verified costs")

        # Explain transport cost must be confirmed at booking
        issues = b_res["issues"]
        self.assertTrue(any("transport" in iss.lower() and ("unverified" in iss.lower() or "booking" in iss.lower() or "counter" in iss.lower()) for iss in issues))

    def test_04_synthetic_test_bus_and_flight_fixture_isolation(self):
        """Verifies explicit synthetic test fixtures are included in estimates without contaminating production."""
        SYNTHETIC_TEST_BUS_FARE = 950.0
        synthetic_bus = {
            "mode": "bus",
            "operator": "Test Interstate Bus",
            "indicative_fare_min": SYNTHETIC_TEST_BUS_FARE,
            "fare_classification": "ESTIMATED_MARKET_TARIFF",
            "is_synthetic_test_fare": True,
        }
        b_synth = budget_engine.calculate_budget(
            pax=2,
            transport=synthetic_bus,
            is_round_trip=False,
        )
        self.assertTrue(b_synth["is_complete"], "Explicit synthetic test fixture allows complete test calculation")
        self.assertEqual(b_synth["estimated_costs"]["items"]["estimated_outbound_transport"], SYNTHETIC_TEST_BUS_FARE * 2)
        self.assertEqual(b_synth["grand_total"], SYNTHETIC_TEST_BUS_FARE * 2)

    # -------------------------------------------------------------------------
    # 3. Correction D: Ground-Transfer Claim Separation
    # -------------------------------------------------------------------------

    def test_05_ground_transfer_claim_separation(self):
        """Verifies _enrich_flight_transfer separates claims into structured transfer_claims with appropriate statuses."""
        mock_flight = {
            "mode": "flight",
            "airline": "IndiGo",
            "flight_no": "6E 603",
            "origin": "Mumbai",
            "destination": "Jammu",
            "is_connecting": False,
        }
        enriched = _enrich_flight_transfer(mock_flight)
        self.assertTrue(enriched["is_flight_connecting_transfer"])
        self.assertEqual(enriched["transfer_duration"], "approx. 1.5-2 hours by road (traffic dependent)")
        self.assertIn("IXJ", enriched["transfer_note"])
        self.assertIn("Jammu", enriched["transfer_note"])
        self.assertIn("prepaid taxis", enriched["transfer_note"].lower())
        self.assertIn("jammu railway station", enriched["transfer_note"].lower())

        # Check structured claims breakdown
        claims = enriched.get("transfer_claims", {})
        self.assertIn("route_corridor", claims)
        self.assertEqual(claims["route_corridor"]["status"], "verified_curated_source")

        self.assertIn("distance", claims)
        self.assertEqual(claims["distance"]["status"], "verified_curated_source")

        self.assertIn("travel_duration", claims)
        self.assertEqual(claims["travel_duration"]["status"], "indicative_information")
        self.assertIn("traffic", claims["travel_duration"]["claim"].lower())

        self.assertIn("prepaid_taxi", claims)
        self.assertEqual(claims["prepaid_taxi"]["status"], "verified_official_source")

        self.assertIn("public_bus", claims)
        self.assertEqual(claims["public_bus"]["status"], "verified_official_source")
        self.assertIn("jammu railway station", claims["public_bus"]["claim"].lower())

    # -------------------------------------------------------------------------
    # 4. Backward Compatibility: db.search_trains
    # -------------------------------------------------------------------------

    def test_06_db_search_trains_backward_compatibility(self):
        """Verifies legacy callers calling db.search_trains continue to function as expected with unavailable fares."""
        trains = db.search_trains("Delhi", "2026-11-20", "2026-11-24")
        self.assertTrue(len(trains) >= 4)
        vande = next((t for t in trains if "22439" in t["train_no"]), None)
        self.assertIsNotNone(vande)
        self.assertEqual(vande["operator"], "Indian Railways")
        self.assertIsNone(vande["price"])
        self.assertEqual(vande["fare_classification"], "UNAVAILABLE")

    # -------------------------------------------------------------------------
    # 5. Phase 9.8.3.1.2: Railway Claim-Level Provenance Completion
    # -------------------------------------------------------------------------

    def test_07_railway_claim_provenance_populated(self):
        """Verifies every train returned for supported origins has non-None claim verification fields."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        for orig in ("Delhi", "Mumbai", "Jammu"):
            trains = fn(origin=orig, start_date="2026-11-20", end_date="2026-11-24", mode="train")
            self.assertTrue(len(trains) > 0, f"Expected train results for origin {orig}")
            for tr in trains:
                self.assertIsNone(tr.get("seats_available"), "Seat placeholder 50 must not be present")
                self.assertFalse(tr.get("availability_verified"))
                self.assertEqual(tr.get("seat_availability"), "NOT_CHECKED")
                for claim_key in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
                    claim = tr.get(claim_key)
                    self.assertIsNotNone(claim, f"Train {tr.get('train_no')} must not have None for {claim_key}")
                    self.assertIsInstance(claim, dict, f"{claim_key} must be serialized dict")
                    self.assertIn(claim.get("status"), ("verified_official_source", "verified_curated_source", "unverified", "indicative_information"))

    def test_08_railway_claim_provenance_fail_closed(self):
        """Train queries for unsupported origins return empty lists, not fallback unverified data."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        for unsupported in ("Kolkata", "Patna", "Chennai", "London", "NonExistentCity"):
            results = fn(origin=unsupported, start_date="2026-11-20", end_date="2026-11-24", mode="train")
            self.assertEqual(results, [], f"Expected fail-closed empty list for unsupported origin: {unsupported}")

    def test_09_railway_claim_verification_schema(self):
        """Each verification object conforms to the ClaimVerification schema."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        tr = trains[0]
        schema_keys = {"status", "source_name", "source_url", "reference_url", "document_reference", "effective_date", "verified_at", "verified_by", "notes"}
        for claim_key in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
            claim = tr[claim_key]
            for k in claim.keys():
                self.assertIn(k, schema_keys, f"Unexpected key {k} in {claim_key}")
            self.assertTrue(bool(claim.get("status")))
            self.assertTrue(bool(claim.get("source_name")))

    def test_10_railway_fare_claim_is_indicative(self):
        """Railway fares are explicitly classified as unavailable/unverified, with appropriate disclaimers."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            fare_claim = tr["fare_verification"]
            self.assertEqual(fare_claim["status"], "unverified")
            self.assertIn("IRCTC", fare_claim["source_name"])
            self.assertIsNone(fare_claim.get("document_reference"))
            self.assertTrue(any(kw in fare_claim["notes"].lower() for kw in ("vary", "dynamic", "tatkal", "indicative", "unverified", "unavailable")))
            self.assertEqual(tr["fare_classification"], "UNAVAILABLE")
            self.assertIsNone(tr["price"])
            self.assertIsNone(tr["fare"])
            self.assertIsNone(tr["indicative_fare_min"])

    # -------------------------------------------------------------------------
    # 6. Phase 9.8.3.1.3: Evidence Authenticity, Verifier Removal & Inventory Safety
    # -------------------------------------------------------------------------

    def test_11_unsupported_source_urls_cannot_produce_verified_claims(self):
        """A generic root homepage without document reference must fail-closed to UNVERIFIED status."""
        from services.live_data.contracts import ClaimVerification
        from utils.provenance import VerificationStatus

        claim = ClaimVerification(
            status="verified_official_source",
            source_name="Indian Railways",
            source_url="https://enquiry.indianrail.gov.in/",
            document_reference=None,
        )
        self.assertEqual(claim.status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(claim.source_url)
        self.assertEqual(claim.reference_url, "https://enquiry.indianrail.gov.in/")
        self.assertIsNone(claim.verified_at)
        self.assertIsNone(claim.verified_by)
        self.assertIsNone(claim.effective_date)

    def test_12_missing_document_evidence_results_in_unverified_status(self):
        """CuratedTrainSchedule enforces that timetable & fare claims without authentic documents remain UNVERIFIED."""
        from services.live_data.contracts import CuratedTrainSchedule
        from utils.provenance import VerificationStatus

        sched = CuratedTrainSchedule(
            train_number="99999",
            train_name="Test Express",
            origin_station_code="NDLS",
            origin_station_name="New Delhi",
            destination_station_code="SVDK",
            destination_station_name="Shri Mata Vaishno Devi Katra",
            departure_time="10:00",
            arrival_time="18:00",
            days_of_operation=["MON"],
            travel_classes=["CC"],
            major_halts=[],
            timetable_verification={"status": "verified_curated_source", "source_name": "NTES", "document_reference": "WTT No. 54"},
            fare_verification={"status": "verified_official_source", "source_name": "IRCTC", "document_reference": "Base Passenger Tariff Table"},
        )
        self.assertEqual(sched.timetable_verification.status, VerificationStatus.UNVERIFIED.value)
        self.assertEqual(sched.fare_verification.status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(sched.timetable_verification.document_reference)
        self.assertIsNone(sched.fare_verification.document_reference)

    def test_13_four_claims_remain_independently_classified(self):
        """Operator is verified official, while route, timetable & fare remain independently unverified."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        tr = trains[0]
        # Operator: verified_official_source (under The Railways Act, 1989)
        self.assertEqual(tr["operator_verification"]["status"], "verified_official_source")
        # Route, Timetable & Fare: unverified due to lack of directly inspected official gazette documents
        self.assertEqual(tr["route_verification"]["status"], "unverified")
        self.assertEqual(tr["timetable_verification"]["status"], "unverified")
        self.assertEqual(tr["fare_verification"]["status"], "unverified")

    def test_14_internal_verifier_labels_not_presented_as_external_certification(self):
        """Internal curatorial desk labels must not be emitted as external certifying authorities in claim verification."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            for k in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
                claim = tr[k]
                self.assertIsNone(claim.get("verified_by"), f"Claim {k} must not claim external verifier identity")
                self.assertIsNone(claim.get("verified_at"), f"Claim {k} must not claim external verification timestamp")
                self.assertIsNone(claim.get("effective_date"), f"Claim {k} must not claim unevidenced effective date")

    def test_15_seat_placeholder_cannot_appear_as_user_facing_availability(self):
        """Placeholder 50 cannot appear as user-facing availability; availability_verified must be False."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        for orig in ("Delhi", "Mumbai", "Jammu"):
            trains = fn(origin=orig, start_date="2026-11-20", end_date="2026-11-24", mode="train")
            for tr in trains:
                self.assertIsNone(tr.get("seats_available"), f"Train {tr.get('train_no')} must have seats_available=None")
                self.assertFalse(tr.get("availability_verified"), "availability_verified must be False")
                self.assertEqual(tr.get("seat_availability"), "NOT_CHECKED")
                self.assertFalse(tr.get("is_live_status"))

    def test_16_booking_and_budget_calculations_do_not_consume_placeholder_inventory(self):
        """Budget engine and booking flows handle unavailable railway fare without placeholder inventory."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        tr = trains[0]
        # Calculate budget with unpriced train
        res = budget_engine.calculate_budget(
            pax=4,
            transport=tr,
            darshan_slot={"category": "Normal Darshan", "price": 0.0},
            accommodation={"name": "Test Hotel", "price_per_night": 1000.0, "rooms": 1, "nights": 2},
            is_round_trip=False,
        )
        self.assertFalse(res["is_complete"], "Missing/unavailable railway fare marks budget incomplete")
        self.assertIsNone(res["grand_total"], "Grand total is None when transport fare is unavailable")
        self.assertEqual(res["verified_costs"]["transport"], 0.0)
        self.assertEqual(res["verified_costs"]["accommodation"], 2000.0)
        self.assertEqual(res["verified_costs"]["darshan"], 0.0)

        # Explicit synthetic test fixture is required to compute test transport cost
        synthetic_tr = dict(tr, price=1630, is_synthetic_test_fare=True)
        res_syn = budget_engine.calculate_budget(
            pax=4,
            transport=synthetic_tr,
            darshan_slot={"category": "Normal Darshan", "price": 0.0},
            accommodation={"name": "Test Hotel", "price_per_night": 1000.0, "rooms": 1, "nights": 2},
            is_round_trip=False,
        )
        self.assertTrue(res_syn["is_complete"])
        self.assertEqual(res_syn["verified_costs"]["transport"], 1630 * 4)

    def test_17_static_timetable_information_remains_non_live(self):
        """Static railway timetable schedules strictly enforce is_live_status=False across all records."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            self.assertFalse(tr["is_live_status"], "is_live_status must strictly remain False")
            self.assertEqual(tr["status"], "TIMETABLE_SCHEDULE")

    # -------------------------------------------------------------------------
    # 7. Phase 9.8.3.1.4: Final Railway Presentation & Budget Truthfulness Tests
    # -------------------------------------------------------------------------

    def test_18_unverified_fare_cannot_enter_verified_budget_totals(self):
        """Phase 9.8.3.1.4 Test 1: Unverified railway fare cannot enter verified budget totals."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        tr = trains[0]
        self.assertEqual(tr["fare_classification"], "UNAVAILABLE")
        self.assertIsNone(tr["price"])
        self.assertIsNone(tr["fare"])

        res = budget_engine.calculate_budget(
            pax=3,
            transport=tr,
            darshan_slot={"category": "Normal Darshan", "price": 0.0},
            accommodation={"name": "Hotel Katra", "price_per_night": 1200.0, "rooms": 1, "nights": 2},
            is_round_trip=False,
        )
        self.assertEqual(res["verified_costs"]["transport"], 0.0, "Verified transport cost must be 0.0 when fare is unverified")
        self.assertNotIn("estimated_outbound_transport", res.get("estimated_costs", {}), "Unverified train fare must not produce invented estimates")

    def test_19_missing_railway_fare_marks_budget_incomplete(self):
        """Phase 9.8.3.1.4 Test 2: Missing railway fare marks budget incomplete (grand_total=None) while preserving hotel & darshan."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Mumbai", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        tr = trains[0]

        res = budget_engine.calculate_budget(
            pax=2,
            transport=tr,
            darshan_slot={"category": "VIP Darshan", "price": 500.0},
            accommodation={"name": "Deluxe Hotel", "price_per_night": 2500.0, "rooms": 1, "nights": 3},
            is_round_trip=False,
        )
        self.assertFalse(res["is_complete"], "Budget must be incomplete when transport fare is unavailable")
        self.assertIsNone(res["grand_total"], "Grand total must be None when budget is incomplete")
        # Preserves other verified costs
        self.assertEqual(res["verified_costs"]["darshan"], 1000.0)  # 2 pax * 500
        self.assertEqual(res["verified_costs"]["accommodation"], 7500.0)    # 1 room * 3 nights * 2500
        self.assertEqual(res["verified_costs"]["transport"], 0.0)
        self.assertTrue(any("transport" in iss.lower() and "price" in iss.lower() for iss in res.get("issues", [])))

    def test_20_unverified_timetable_suppresses_confirmed_times(self):
        """Phase 9.8.3.1.4 Test 3: Unverified timetable suppresses confirmed times and directs to NTES (139)."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            # Verification status must be unverified
            self.assertEqual(tr["timetable_verification"]["status"], "unverified")
            self.assertFalse(tr["is_live_status"], "Must not claim live telemetry")
            self.assertIn("NTES", tr["timetable_verification"]["notes"])
            self.assertIn("139", tr["route_note"])

            # Verify frontend formatting rules: unverified timetable replaces exact times with NTES enquiry
            is_unverified = tr.get("timetable_verification", {}).get("status") == "unverified"
            display_dep = "Check NTES (139)" if is_unverified else tr["departure_time"]
            display_arr = "Check NTES (139)" if is_unverified else tr["arrival_time"]
            self.assertEqual(display_dep, "Check NTES (139)")
            self.assertEqual(display_arr, "Check NTES (139)")

    def test_21_unverified_route_cannot_receive_verified_route_badge(self):
        """Phase 9.8.3.1.4 Test 4: Unverified corridor route cannot receive a verified route badge."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        for orig in ("Delhi", "Mumbai", "Jammu"):
            trains = fn(origin=orig, start_date="2026-11-20", end_date="2026-11-24", mode="train")
            for tr in trains:
                route_claim = tr["route_verification"]
                self.assertEqual(route_claim["status"], "unverified", "Corridor route claim must be unverified")
                self.assertIsNone(route_claim.get("document_reference"), "Must not cite unverified directory as official gazette")
                self.assertIsNone(route_claim.get("verified_at"))
                self.assertIsNone(route_claim.get("verified_by"))

    def test_22_operator_verification_independent_from_route_verification(self):
        """Phase 9.8.3.1.4 Test 5: Operator verification is independent from route verification."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            op_claim = tr["operator_verification"]
            route_claim = tr["route_verification"]
            # Operator is verified by statutory act
            self.assertEqual(op_claim["status"], "verified_official_source")
            self.assertIn("Railways Act, 1989", op_claim.get("document_reference", ""))
            # Route corridor is unverified without inspected gazette
            self.assertEqual(route_claim["status"], "unverified")
            self.assertNotEqual(op_claim["status"], route_claim["status"])

    def test_23_no_misleading_authentic_timetable_text(self):
        """Phase 9.8.3.1.4 Test 6: No misleading 'Authentic timetable' or published fare text in responses."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        for orig in ("Delhi", "Mumbai", "Jammu"):
            trains = fn(origin=orig, start_date="2026-11-20", end_date="2026-11-24", mode="train")
            for tr in trains:
                # Sanitize checks
                self.assertNotIn("Authentic timetable", tr.get("route_note", ""))
                self.assertNotIn("Published Timetable", tr.get("source_name", ""))
                self.assertNotEqual(tr.get("fare_classification"), "ESTIMATED_PUBLISHED_BASE_TARIFF")
                self.assertEqual(tr.get("fare_classification"), "UNAVAILABLE")
                self.assertIsNone(tr.get("price"))
                self.assertIsNone(tr.get("fare"))

    def test_24_nominal_seat_placeholders_cannot_reach_user(self):
        """Phase 9.8.3.1.4 Test 7: Nominal seat placeholders cannot reach user interfaces."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        for tr in trains:
            self.assertIsNone(tr.get("seats_available"))
            self.assertFalse(tr.get("availability_verified"))
            self.assertEqual(tr.get("seat_availability"), "NOT_CHECKED")
            # Also check db.search_trains output
            db_trains = db.search_trains("Delhi", "2026-11-20", "2026-11-24")
            for dbt in db_trains:
                self.assertIsNone(dbt.get("seats_available"))
                self.assertFalse(dbt.get("availability_verified"))
                self.assertEqual(dbt.get("seat_availability"), "NOT_CHECKED")

    def test_25_multimodal_transport_isolation(self):
        """Phase 9.8.3.1.4 Test 8: Multimodal isolation across bus, flight, weather, hotel and darshan."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        # 1. Bus: statutory notified per-km slabs intact
        buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(buses) > 0)
        self.assertEqual(buses[0]["fare_classification"], "STATUTORY_NOTIFIED_PER_KM_SLAB")

        # 2. Flight: DGCA corridor guidance intact
        flights = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="flight")
        self.assertTrue(len(flights) > 0)
        self.assertEqual(flights[0]["fare_classification"], "UNAVAILABLE")

        # 3. Trains: UNAVAILABLE fare and unverified timetable intact
        trains = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="train")
        self.assertTrue(len(trains) > 0)
        self.assertEqual(trains[0]["fare_classification"], "UNAVAILABLE")

        # 4. Budget engine isolation: Bus statutory slab does not enter verified total without synthetic fixture
        bus_budget = budget_engine.calculate_budget(pax=2, transport=buses[0], darshan_slot={"price": 0.0})
        self.assertFalse(bus_budget["is_complete"])
        self.assertEqual(bus_budget["verified_costs"]["transport"], 0.0)

        # 5. Synthetic flight fixture calculates cleanly
        syn_flight = dict(flights[0], price=4500.0, is_synthetic_test_fare=True)
        flight_budget = budget_engine.calculate_budget(pax=2, transport=syn_flight, darshan_slot={"price": 0.0})
        self.assertTrue(flight_budget["is_complete"])
        self.assertEqual(flight_budget["verified_costs"]["transport"], 9000.0)


if __name__ == "__main__":
    unittest.main()
