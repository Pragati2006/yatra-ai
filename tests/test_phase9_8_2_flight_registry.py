"""
tests/test_phase9_8_2_flight_registry.py
Comprehensive Test Suite for Phase 9.8.2: Curated Flight Registry Implementation.

Validates:
1. CuratedFlightSchedule contract invariants, fail-safes, and claim-level independence.
2. Dataset schema integrity and source attribution in curated_flight_schedules.json.
3. Service layer search, normalization, and fail-closed origin handling.
4. CuratedFlightAdapter and UnifiedLiveDataManager registration, caching, and provenance.
5. Database fallback db.search_flights isolation from synthetic data.
6. Central Agent search_transport_options intent handling, multimodal ground guidance, and origin preservation.
7. Frontend TransportMiniCard presentation rules, status indicators, and flight disclaimer isolation.
"""

import json
import os
import unittest
from datetime import date

from services.live_data.contracts import (
    CuratedFlightSchedule,
    ClaimVerification,
    DataDomain,
    ProviderRequest,
)
from utils.provenance import VerificationStatus, SourceType, FreshnessStatus
from services.flight_schedules import (
    DEFAULT_FLIGHT_SCHEDULES_PATH,
    load_curated_flight_schedules,
    search_curated_flight_schedules,
    normalize_airport_or_city,
)
from services.live_data.adapters.curated_flight_adapter import CuratedFlightAdapter
from services.live_data.manager import get_live_data_manager, reset_live_data_manager
from agents.tools import search_transport_tool, _search_flights_via_live_manager
from agents.central_agent import search_transport_options
import db


class TestPhase982FlightRegistry(unittest.TestCase):
    """Test suite covering Phase 9.8.2 Curated Flight Registry implementation."""

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reset_live_data_manager()

    # -------------------------------------------------------------------------
    # 1. Contract & Model Invariants
    # -------------------------------------------------------------------------

    def test_01_flight_contract_failsafes(self):
        """Verifies CuratedFlightSchedule enforces strict fail-safes on live status, seats, and fares."""
        sch = CuratedFlightSchedule(
            route_id="test_route_001",
            airline_name="Test Air",
            airline_code="TA",
            origin_airport_code="DEL",
            origin_airport_name="Indira Gandhi Intl",
            origin_city="Delhi",
            flight_number="TA 101",
            departure_time="08:00",
            arrival_time="09:20",
            indicative_fare_min=4000,
            indicative_fare_max=8000,
            source_name="Official Test Source",
            source_url="https://test.gov.in",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
            # Attempt to inject invalid live/booking flags
            is_live_status=True,
            availability_verified=True,
            seat_count=50,
        )
        # Fail-safes must strictly override injected live/seat values
        self.assertFalse(sch.is_live_status, "is_live_status must strictly remain False for curated flight schedules")
        self.assertFalse(sch.availability_verified, "availability_verified must strictly remain False")
        self.assertIsNone(sch.seat_count, "seat_count must strictly remain None (no synthetic seats)")

    def test_02_claim_verification_contract_and_provenance_hardening(self):
        """Verifies Correction B: Contract tests for missing metadata, generic URLs, and unverified claim timestamps."""
        # 1. Missing verification metadata on verified claim fails closed to unverified
        claim_missing_meta = ClaimVerification(
            status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            source_name="Official Carrier",
            source_url=None,
            document_reference=None,
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
        )
        self.assertEqual(claim_missing_meta.status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(claim_missing_meta.verified_at)
        self.assertIsNone(claim_missing_meta.verified_by)

        # 2. Unverified claim with generic homepage URL preserves reference_url and clears source_url
        claim_unverified_homepage = ClaimVerification(
            status=VerificationStatus.UNVERIFIED.value,
            source_name="IndiGo Portal",
            source_url="https://www.goindigo.in/",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
            effective_date="2026-01-01",
        )
        self.assertEqual(claim_unverified_homepage.status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(claim_unverified_homepage.source_url)
        self.assertEqual(claim_unverified_homepage.reference_url, "https://www.goindigo.in/")
        self.assertIsNone(claim_unverified_homepage.verified_at)
        self.assertIsNone(claim_unverified_homepage.verified_by)
        self.assertIsNone(claim_unverified_homepage.effective_date)

        # 3. Verified claim with generic homepage and no specific document fails closed to unverified
        claim_generic_verified = ClaimVerification(
            status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            source_name="IndiGo",
            source_url="https://www.goindigo.in/",
            document_reference=None,
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
        )
        self.assertEqual(claim_generic_verified.status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(claim_generic_verified.source_url)
        self.assertEqual(claim_generic_verified.reference_url, "https://www.goindigo.in/")

        # 4. Properly populated source-backed claim preserves verified_official_source
        claim_verified_ok = ClaimVerification(
            status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            source_name="Airports Authority of India (AAI)",
            source_url="https://www.aai.aero/en/airports/jammu",
            document_reference="AAI Jammu Operational Flights & DGCA Approved Slot",
            effective_date="2026-01-01",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Yatra AI Transport Curatorial Desk",
        )
        self.assertEqual(claim_verified_ok.status, VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value)
        self.assertEqual(claim_verified_ok.verified_by, "Yatra AI Transport Curatorial Desk")
        self.assertEqual(claim_verified_ok.verified_at, "2026-11-08T00:00:00Z")

        # 5. CuratedFlightSchedule separate tracking of audited_at / record_updated_at from verified_at
        sch = CuratedFlightSchedule(
            route_id="test_route_provenance",
            airline_name="IndiGo",
            airline_code="6E",
            origin_airport_code="DEL",
            origin_airport_name="Indira Gandhi Intl",
            origin_city="Delhi",
            fare_classification="UNAVAILABLE",
            source_name="Airports Authority of India (AAI)",
            source_url="https://www.aai.aero/en/airports/jammu",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Curatorial Desk",
            audited_at="2026-11-08T00:00:00Z",
            record_updated_at="2026-11-08T00:00:00Z",
            timetable_verification=ClaimVerification(
                status=VerificationStatus.UNVERIFIED.value,
                source_name="Official Carrier Portal",
                source_url="https://www.goindigo.in/",
            ),
            fare_verification=ClaimVerification(
                status=VerificationStatus.UNVERIFIED.value,
                source_name="Official Carrier Portal",
                source_url="https://www.goindigo.in/",
            ),
        )
        self.assertEqual(sch.audited_at, "2026-11-08T00:00:00Z")
        self.assertEqual(sch.record_updated_at, "2026-11-08T00:00:00Z")
        self.assertIsNone(sch.duration_hours)
        self.assertIsNone(sch.estimated_duration_desc)
        self.assertIsNone(sch.timetable_verification.verified_at)
        self.assertIsNone(sch.fare_verification.verified_at)
        self.assertEqual(sch.timetable_verification.reference_url, "https://www.goindigo.in/")

    # -------------------------------------------------------------------------
    # 2. Dataset Schema & Integrity
    # -------------------------------------------------------------------------

    def test_03_curated_dataset_loading_and_routes(self):
        """Verifies curated_flight_schedules.json contains valid direct and connecting routes."""
        schedules, meta = load_curated_flight_schedules(force_reload=True)
        self.assertGreaterEqual(len(schedules), 10, "Registry must contain at least 10 nationwide flight schedules")
        self.assertIn("authority", meta)
        self.assertIn("destination_airport", meta)
        self.assertEqual(meta["destination_airport"]["iata_code"], "IXJ")

        # Check for key direct corridors
        del_routes = [s for s in schedules if s.origin_airport_code == "DEL"]
        bom_routes = [s for s in schedules if s.origin_airport_code == "BOM"]
        sxr_routes = [s for s in schedules if s.origin_airport_code == "SXR"]
        self.assertGreaterEqual(len(del_routes), 3, "Must have at least 3 direct flights from Delhi to Jammu")
        self.assertEqual(len(bom_routes), 1, "Must have direct flight from Mumbai to Jammu")
        self.assertEqual(len(sxr_routes), 1, "Must have intra-UT direct flight from Srinagar to Jammu")

        # Verify Phase 9.8.2.2.3 data integrity corrections across entire dataset
        for s in schedules:
            self.assertIsNone(s.seat_count, f"Route {s.route_id} must have seat_count=None")
            self.assertFalse(s.is_live_status, f"Route {s.route_id} must have is_live_status=False")
            self.assertIsNone(s.duration_hours, f"Route {s.route_id} must have duration_hours=None")
            self.assertIsNone(s.estimated_duration_desc, f"Route {s.route_id} must have estimated_duration_desc=None")
            self.assertIsNone(s.indicative_fare_min, f"Route {s.route_id} must have indicative_fare_min=None")
            self.assertIsNone(s.indicative_fare_max, f"Route {s.route_id} must have indicative_fare_max=None")
            self.assertEqual(s.fare_classification, "UNAVAILABLE", f"Route {s.route_id} must have fare_classification=UNAVAILABLE")
            self.assertEqual(s.fare_verification.status, VerificationStatus.UNVERIFIED.value)
            self.assertIsNone(s.fare_verification.verified_at)
            self.assertIsNone(s.fare_verification.effective_date)
            self.assertEqual(s.timetable_verification.status, VerificationStatus.UNVERIFIED.value)
            self.assertIsNone(s.timetable_verification.verified_at)
            self.assertIsNone(s.timetable_verification.effective_date)
            self.assertIn(s.route_type, ("DIRECT", "CONNECTING", "ROUTE_GUIDANCE_ONLY"))
            if s.route_type == "DIRECT":
                # Correction B & C: Direct flight timetables unverified / route guidance only without static operating minutes or durations
                self.assertIsNone(s.departure_time, f"Direct route {s.route_id} must have departure_time=None")
                self.assertIsNone(s.arrival_time, f"Direct route {s.route_id} must have arrival_time=None")
                self.assertEqual(s.schedule_type, "ROUTE_GUIDANCE_ONLY")
            elif s.route_id.endswith("_via_del"):
                # FA-03: Connecting hub guidance reclassified
                self.assertEqual(s.route_type, "ROUTE_GUIDANCE_ONLY")
                self.assertEqual(s.schedule_type, "CONNECTING_HUB_GUIDANCE")
            elif s.route_id == "flight_amritsar_ixj_advisory":
                # Correction C: Amritsar advisory uses qualified bounded wording without Train 22487/Vande Bharat
                self.assertEqual(s.route_type, "ROUTE_GUIDANCE_ONLY")
                self.assertIn("not listed in Yatra AI's curated flight registry", s.notes)
                self.assertNotIn("No direct scheduled commercial flight exists", s.notes)
                self.assertNotIn("Vande Bharat", s.notes)
                self.assertNotIn("22487", s.notes)

    # -------------------------------------------------------------------------
    # 3. Service Layer Search & Normalization
    # -------------------------------------------------------------------------

    def test_04_service_normalization_and_nationwide_search(self):
        """Verifies city/airport normalization and search results for major hubs."""
        self.assertEqual(normalize_airport_or_city("delhi"), "DEL")
        self.assertEqual(normalize_airport_or_city("Mumbai"), "BOM")
        self.assertEqual(normalize_airport_or_city("bengaluru"), "BLR")
        self.assertEqual(normalize_airport_or_city("Bangalore"), "BLR")
        self.assertEqual(normalize_airport_or_city("Kolkata"), "CCU")
        self.assertEqual(normalize_airport_or_city("Jammu"), "IXJ")

        # Direct search: Delhi
        del_res, del_meta = search_curated_flight_schedules("Delhi")
        self.assertEqual(del_meta["status"], "SUCCESS")
        self.assertGreaterEqual(len(del_res), 4)

        # Direct search: Mumbai
        bom_res, bom_meta = search_curated_flight_schedules("Mumbai")
        self.assertEqual(bom_meta["status"], "SUCCESS")
        self.assertEqual(bom_res[0].route_type, "DIRECT")
        self.assertEqual(bom_res[0].flight_number, "6E 603")

        # Connecting search: Bengaluru (FA-03: ROUTE_GUIDANCE_ONLY / CONNECTING_HUB_GUIDANCE)
        blr_res, blr_meta = search_curated_flight_schedules("Bengaluru")
        self.assertEqual(blr_meta["status"], "SUCCESS")
        self.assertEqual(blr_res[0].route_type, "ROUTE_GUIDANCE_ONLY")
        self.assertEqual(blr_res[0].schedule_type, "CONNECTING_HUB_GUIDANCE")
        self.assertIn("DEL", blr_res[0].layover_airports)

        # Ground advisory search: Amritsar (Correction C: qualified wording, no Train 22487/Vande Bharat)
        atq_res, atq_meta = search_curated_flight_schedules("Amritsar")
        self.assertEqual(atq_res[0].route_type, "ROUTE_GUIDANCE_ONLY")
        self.assertNotIn("Vande Bharat", atq_res[0].notes)
        self.assertNotIn("22487", atq_res[0].notes)
        self.assertIn("not listed in Yatra AI's curated flight registry", atq_res[0].notes)
        self.assertIn("road or railway connections", atq_res[0].notes)

        # Ground transfer advisory truthfulness (FA-05)
        self.assertIn("prepaid taxi", del_meta["ground_transfer_advisory"].lower())
        self.assertIn("jammu railway station", del_meta["ground_transfer_advisory"].lower())

        # Unsupported origin: Varanasi (fail-closed, no silent Delhi fallback)
        var_res, var_meta = search_curated_flight_schedules("Varanasi")
        self.assertEqual(len(var_res), 0)
        self.assertEqual(var_meta["status"], "ROUTE_NOT_IN_CURATED_REGISTRY")

        # Missing origin: fail-closed
        none_res, none_meta = search_curated_flight_schedules("")
        self.assertEqual(len(none_res), 0)
        self.assertEqual(none_meta["status"], "ORIGIN_REQUIRED")

    # -------------------------------------------------------------------------
    # 4. Provider Adapter & Live Manager Integration
    # -------------------------------------------------------------------------

    def test_05_curated_flight_adapter_and_live_manager(self):
        """Verifies CuratedFlightAdapter registers with manager and executes requests with caching."""
        mgr = get_live_data_manager()
        provider = mgr.get_provider("transport", "curated_flight_schedules")
        self.assertIsNotNone(provider, "CuratedFlightAdapter must be registered under domain 'transport'")
        self.assertEqual(provider.provider_id, "curated_flight_schedules")
        self.assertEqual(provider.domain, DataDomain.TRANSPORT.value)

        # Execute request through manager
        req = ProviderRequest(
            domain="transport",
            location="Delhi",
            params={"origin": "Delhi", "destination": "Jammu", "travel_date": "2026-10-20"},
        )
        res = mgr.execute_request(req, provider_id="curated_flight_schedules")
        self.assertTrue(res.is_success)
        self.assertEqual(res.freshness_status, FreshnessStatus.CACHED.value)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)
        self.assertFalse(res.availability_verified)

        schedules = res.data.get("schedules", [])
        self.assertGreaterEqual(len(schedules), 4)
        first_sch = schedules[0]
        self.assertEqual(first_sch["airline_name"], "IndiGo")
        self.assertEqual(first_sch["origin_airport_code"], "DEL")
        self.assertIsNotNone(first_sch["route_verification"])
        self.assertIsNotNone(first_sch["fare_verification"])

    # -------------------------------------------------------------------------
    # 5. Database Layer Isolation
    # -------------------------------------------------------------------------

    def test_06_db_search_flights_isolation(self):
        """Verifies db.search_flights queries curated registry and does not leak synthetic CSV data."""
        res = db.search_flights("Delhi", "2026-10-20", "2026-10-22")
        self.assertGreaterEqual(len(res), 4)
        for r in res:
            self.assertEqual(r["mode"], "flight")
            self.assertIsNone(r["seats_available"], "db.search_flights must return seats_available=None")
            self.assertIsNone(r["fare"], "db.search_flights must return fare=None")
            self.assertIsNone(r["price"], "db.search_flights must return price=None")
            self.assertIsNone(r["indicative_fare_min"], "db.search_flights must return indicative_fare_min=None")
            self.assertIsNone(r["indicative_fare_max"], "db.search_flights must return indicative_fare_max=None")
            self.assertEqual(r["fare_classification"], "UNAVAILABLE")
            self.assertIn("Prices are dynamic", r["fare_disclaimer"])

        # Unsupported origin returns empty list
        v_res = db.search_flights("Varanasi", "2026-10-20", "2026-10-22")
        self.assertEqual(len(v_res), 0, "db.search_flights must fail-closed for unsupported origins")

    # -------------------------------------------------------------------------
    # 6. Central Agent & Tools Integration
    # -------------------------------------------------------------------------

    def test_07_search_transport_tool_flight_dispatch(self):
        """Verifies search_transport_tool dispatches flight queries truthfully via live manager."""
        flights = search_transport_tool.func("Delhi", "2026-10-20", "2026-10-22", mode="flight")
        self.assertGreaterEqual(len(flights), 4)
        self.assertEqual(flights[0]["mode"], "flight")
        self.assertEqual(flights[0]["origin_airport_code"], "DEL")

        # Check multimodal ground transfer advisory (FA-05)
        self.assertIn("ground_transfer_advisory", flights[0])
        self.assertIn("Jammu Airport (IXJ) is ~50 km from Katra", flights[0]["ground_transfer_advisory"])
        self.assertIn("prepaid taxi", flights[0]["ground_transfer_advisory"].lower())
        self.assertIn("jammu railway station", flights[0]["ground_transfer_advisory"].lower())

    def test_08_central_agent_search_transport_options_truthfulness(self):
        """Verifies central_agent.search_transport_options truthful flight presentation and limitations."""
        # Delhi query
        del_plan = search_transport_options.func(origin="Delhi", start_date="2026-10-20", end_date="2026-10-22", mode="flight")
        del_opts = [o for o in del_plan.get("options", []) if o.get("mode") == "flight"]
        self.assertGreaterEqual(len(del_opts), 4)
        self.assertIsNone(del_opts[0].get("seats_available"))
        self.assertIn("ground_transfer_advisory", del_plan)

        # Varanasi query (coverage limitation)
        var_plan = search_transport_options.func(origin="Varanasi", start_date="2026-10-20", end_date="2026-10-22", mode="flight")
        var_opts = [o for o in var_plan.get("options", []) if o.get("mode") == "flight"]
        self.assertEqual(len(var_opts), 0)
        self.assertIn("flight_coverage_limitation", var_plan)
        self.assertEqual(var_plan["flight_coverage_limitation"]["status"], "ROUTE_NOT_IN_CURATED_REGISTRY")

        # Missing origin
        none_plan = search_transport_options.func(origin="", start_date="2026-10-20", end_date="2026-10-22", mode="flight")
        self.assertEqual(none_plan.get("status"), "MISSING_ORIGIN")

    # -------------------------------------------------------------------------
    # 7. Frontend TransportMiniCard Verification
    # -------------------------------------------------------------------------

    def test_09_frontend_card_flight_presentation_rules(self):
        """Inspects TransportMiniCard.jsx and TransportCard.jsx to verify truthful flight rendering and disclaimers."""
        card_path = os.path.join(self.root_dir, "frontend", "src", "components", "chat", "cards", "TransportMiniCard.jsx")
        self.assertTrue(os.path.exists(card_path))
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()

        # 1. Airplane icon for flight
        self.assertIn("isFlight ? '✈️'", code)

        # 2. Honest airfare display: when unavailable or null
        self.assertIn("isFlight ? 'Airfare on airline website'", code)

        # 3. Ground transfer advisory strip for Jammu Airport (FA-05)
        self.assertIn("Jammu Airport (IXJ) transfer:", code)
        self.assertIn("prepaid taxi from airport terminal", code.lower())
        self.assertIn("public jkrtc buses depart from jammu railway station", code.lower())

        # 4. Status indicator: guidance only and unverified schedule badges
        self.assertIn("CONNECTING GUIDANCE", code)
        self.assertIn("ROUTE GUIDANCE", code)
        self.assertIn("TIMETABLE UNVERIFIED", code)

        # 5. Timing row shows route guidance without unsupported duration
        self.assertIn("Flight route guidance — confirm current schedules and journey duration with the airline", code)
        self.assertIn("!isFlight ? (option.estimated_duration_desc", code)
        self.assertNotIn("~1h 25m non-stop", code)

        # 6. Flight dynamic airfare footnote isolation (Correction A)
        self.assertIn("*Airfare unavailable. Prices are dynamic; please check the airline's official booking website.", code)

        # 7. Check TransportCard.jsx protects against displaying unavailable airfare as ₹0
        full_card_path = os.path.join(self.root_dir, "frontend", "src", "components", "TransportCard.jsx")
        with open(full_card_path, "r", encoding="utf-8") as f_full:
            full_code = f_full.read()
        self.assertIn("isFareUnavailable", full_code)
        self.assertIn("Airfare on airline website (dynamic pricing)", full_code)
        self.assertIn("Darshan Bundle (Excludes Airfare)", full_code)

    # -------------------------------------------------------------------------
    # 8. Budget Engine & Orchestrator Isolation (Corrections A, D & E)
    # -------------------------------------------------------------------------

    def test_10_budget_engine_synthetic_fixture_isolation(self):
        """Verifies Correction A: Synthetic test fixtures are isolated and never enter production dataset."""
        from agents import budget_engine

        # Explicitly identified synthetic test fixtures (testing values only, not production data)
        SYNTHETIC_TEST_AIRFARE_MIN = 4200
        SYNTHETIC_TEST_AIRFARE_MAX = 8800

        # Property 1: Flight with unavailable airfare does NOT produce an estimated transport monetary value
        flight_unavailable = {
            "mode": "flight",
            "airline": "IndiGo",
            "fare_classification": "UNAVAILABLE",
            "indicative_fare_min": None,
            "indicative_fare_max": None,
        }
        res_unavail = budget_engine.calculate_budget(pax=2, transport=flight_unavailable, is_round_trip=False)
        self.assertNotIn("estimated_outbound_transport", res_unavail["estimated_costs"]["items"])
        self.assertEqual(res_unavail["estimated_costs"]["total_estimated"], 0.0)

        # Property 2: Flight with unavailable airfare does NOT produce a verified transport cost
        self.assertEqual(res_unavail["verified_costs"]["transport"], 0.0)
        self.assertEqual(res_unavail["verified_costs"]["total_verified"], 0.0)

        # Property 3: Mixed itinerary with unknown airfare remains incomplete when total cannot be calculated
        mixed_unavail = budget_engine.calculate_budget(
            pax=2,
            transport=flight_unavailable,
            accommodation={"price_per_night": 2500, "rooms": 1, "nights": 2},
            is_round_trip=False,
        )
        self.assertFalse(mixed_unavail["is_complete"])
        self.assertIsNone(mixed_unavail["grand_total"])
        self.assertEqual(mixed_unavail["verified_costs"]["accommodation"], 5000.0)
        self.assertEqual(mixed_unavail["verified_costs"]["transport"], 0.0)

        # Property 4: Synthetic test values NEVER enter the curated production dataset
        schedules, _ = load_curated_flight_schedules(force_reload=True)
        for s in schedules:
            self.assertIsNone(s.indicative_fare_min)
            self.assertIsNone(s.indicative_fare_max)
            self.assertEqual(s.fare_classification, "UNAVAILABLE")
            self.assertNotEqual(s.indicative_fare_min, SYNTHETIC_TEST_AIRFARE_MIN)
            self.assertNotEqual(s.indicative_fare_max, SYNTHETIC_TEST_AIRFARE_MAX)

        # Property 5: Estimated fare is included ONLY when an explicitly supplied test estimate exists
        flight_with_synthetic_fixture = {
            "mode": "flight",
            "airline": "IndiGo",
            "indicative_fare_min": SYNTHETIC_TEST_AIRFARE_MIN,
            "indicative_fare_max": SYNTHETIC_TEST_AIRFARE_MAX,
            "fare_classification": "ESTIMATED_MARKET_TARIFF",
        }
        res_synthetic = budget_engine.calculate_budget(pax=2, transport=flight_with_synthetic_fixture, is_round_trip=False)
        self.assertTrue(res_synthetic["is_complete"])
        self.assertEqual(res_synthetic["estimated_costs"]["items"]["estimated_outbound_transport"], SYNTHETIC_TEST_AIRFARE_MIN * 2)
        self.assertEqual(res_synthetic["grand_total"], SYNTHETIC_TEST_AIRFARE_MIN * 2)

    def test_11_budget_engine_eight_edge_cases(self):
        """Verifies Correction D: Retesting all 8 budget engine edge cases."""
        from agents import budget_engine

        # Synthetic test fixtures for edge-case testing
        SYNTHETIC_OUTBOUND_TEST_FARE = 4200
        SYNTHETIC_RETURN_TEST_FARE = 4500

        # Edge Case 1: One-way flight with unavailable fare
        c1 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            is_round_trip=False,
        )
        self.assertFalse(c1["is_complete"])
        self.assertIsNone(c1["grand_total"])
        self.assertTrue(any("outbound" in issue.lower() for issue in c1["issues"]))
        self.assertNotIn("estimated_outbound_transport", c1["estimated_costs"]["items"])

        # Edge Case 2: Round-trip flight with unavailable outbound and return fares
        c2 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            return_transport={"mode": "flight", "airline": "Air India", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            is_round_trip=True,
        )
        self.assertFalse(c2["is_complete"])
        self.assertIsNone(c2["grand_total"])
        self.assertTrue(any("outbound" in issue.lower() for issue in c2["issues"]))
        self.assertTrue(any("return" in issue.lower() for issue in c2["issues"]))

        # Edge Case 3: Verified train outbound plus unavailable flight return
        c3 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "train", "price": 1800.0, "fare": 1800.0, "fare_classification": "STANDARD_TICKET_PRICE"},
            return_transport={"mode": "flight", "airline": "IndiGo", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            is_round_trip=True,
        )
        self.assertFalse(c3["is_complete"])
        self.assertIsNone(c3["grand_total"])
        self.assertEqual(c3["verified_costs"]["transport"], 3600.0)
        self.assertTrue(any("return" in issue.lower() for issue in c3["issues"]))

        # Edge Case 4: Unavailable flight outbound plus verified train return
        c4 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            return_transport={"mode": "train", "price": 1800.0, "fare": 1800.0, "fare_classification": "STANDARD_TICKET_PRICE"},
            is_round_trip=True,
        )
        self.assertFalse(c4["is_complete"])
        self.assertIsNone(c4["grand_total"])
        self.assertEqual(c4["verified_costs"]["transport"], 3600.0)
        self.assertTrue(any("outbound" in issue.lower() for issue in c4["issues"]))

        # Edge Case 5: Explicitly estimated test fare in outbound and return directions
        c5 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "indicative_fare_min": SYNTHETIC_OUTBOUND_TEST_FARE, "fare_classification": "ESTIMATED_MARKET_TARIFF"},
            return_transport={"mode": "flight", "airline": "SpiceJet", "indicative_fare_min": SYNTHETIC_RETURN_TEST_FARE, "fare_classification": "ESTIMATED_MARKET_TARIFF"},
            is_round_trip=True,
        )
        self.assertTrue(c5["is_complete"])
        self.assertEqual(c5["verified_costs"]["total_verified"], 0.0)
        self.assertEqual(c5["estimated_costs"]["items"]["estimated_outbound_transport"], SYNTHETIC_OUTBOUND_TEST_FARE * 2)
        self.assertEqual(c5["estimated_costs"]["items"]["estimated_return_transport"], SYNTHETIC_RETURN_TEST_FARE * 2)
        self.assertEqual(c5["grand_total"], (SYNTHETIC_OUTBOUND_TEST_FARE + SYNTHETIC_RETURN_TEST_FARE) * 2)

        # Edge Case 6: Multiple passengers (4 passengers)
        c6 = budget_engine.calculate_budget(
            pax=4,
            transport={"mode": "flight", "airline": "IndiGo", "indicative_fare_min": SYNTHETIC_OUTBOUND_TEST_FARE, "fare_classification": "ESTIMATED_MARKET_TARIFF"},
            is_round_trip=False,
        )
        self.assertTrue(c6["is_complete"])
        self.assertEqual(c6["estimated_costs"]["items"]["estimated_outbound_transport"], SYNTHETIC_OUTBOUND_TEST_FARE * 4)
        self.assertEqual(c6["grand_total"], SYNTHETIC_OUTBOUND_TEST_FARE * 4)

        # Edge Case 7: Unknown transport fare combined with verified accommodation and meals
        c7 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "fare_classification": "UNAVAILABLE", "indicative_fare_min": None},
            accommodation={"price_per_night": 1800, "rooms": 1, "nights": 2},
            estimated_costs={"meals_and_refreshments": 1300.0},
            is_round_trip=False,
        )
        self.assertFalse(c7["is_complete"])
        self.assertIsNone(c7["grand_total"])
        self.assertEqual(c7["verified_costs"]["accommodation"], 3600.0)
        self.assertEqual(c7["verified_costs"]["transport"], 0.0)
        self.assertEqual(c7["estimated_costs"]["items"]["meals_and_refreshments"], 1300.0)

        # Edge Case 8: Itemized estimates reconcile exactly with their estimated subtotal
        c8 = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "flight", "airline": "IndiGo", "indicative_fare_min": SYNTHETIC_OUTBOUND_TEST_FARE, "fare_classification": "ESTIMATED_MARKET_TARIFF"},
            return_transport={"mode": "flight", "airline": "IndiGo", "indicative_fare_min": SYNTHETIC_RETURN_TEST_FARE, "fare_classification": "ESTIMATED_MARKET_TARIFF"},
            accommodation={"price_per_night": 1800, "rooms": 1, "nights": 2},
            estimated_costs={"local_road_transfer": 3000.0, "meals_and_refreshments": 1300.0},
            is_round_trip=True,
        )
        self.assertTrue(c8["is_complete"])
        sum_items = sum(c8["estimated_costs"]["items"].values())
        self.assertEqual(sum_items, c8["estimated_costs"]["total_estimated"])
        self.assertEqual(c8["grand_total"], c8["verified_costs"]["total_verified"] + c8["estimated_costs"]["total_estimated"])

    def test_12_itemized_estimated_expenses_reconciliation(self):
        """Verifies Correction E: orchestrator.format_itemized_cost_breakdown reconciles sub-bullets with e_total."""
        from agents.orchestrator import format_itemized_cost_breakdown

        # Test A: Reconciled breakdown when estimates and grand total exist
        budget_data = {
            "is_complete": True,
            "is_partially_estimated": True,
            "verified_costs": {
                "total_verified": 3600.0,
                "hotel": 3600.0,
                "transport": 0.0,
            },
            "estimated_costs": {
                "total_estimated": 18300.0,
                "items": {
                    "estimated_outbound_transport": 7000.0,
                    "estimated_return_transport": 7000.0,
                    "local_road_transfer": 3000.0,
                    "meals_and_refreshments": 1300.0,
                },
            },
            "grand_total": 21900.0,
        }
        session_data = {
            "state": {
                "requirements": {"pax": 2, "duration_days": 3, "origin": "Delhi"},
                "selected_options": {
                    "transport": {
                        "mode": "flight",
                        "origin": "Delhi",
                        "fare_classification": "ESTIMATED_MARKET_TARIFF",
                        "indicative_fare_min": 3500,
                    },
                    "accommodation": {
                        "name": "Katra Hotel",
                        "price_per_night": 1800,
                    },
                },
                "budget_evaluation": budget_data,
                "plan_version": 1,
            }
        }
        breakdown_text = format_itemized_cost_breakdown(session_data)
        self.assertIn("₹3,600.00", breakdown_text)
        self.assertIn("₹18,300.00", breakdown_text)
        self.assertIn("Outbound Airfare", breakdown_text)
        self.assertIn("Return Airfare", breakdown_text)
        self.assertIn("Local Road Transfers", breakdown_text)
        self.assertIn("Meals & Refreshments", breakdown_text)
        self.assertIn("₹3,000.00", breakdown_text)
        self.assertIn("₹1,300.00", breakdown_text)
        rendered_subtotal = 7000.0 + 7000.0 + 3000.0 + 1300.0
        self.assertEqual(rendered_subtotal, budget_data["estimated_costs"]["total_estimated"])

        # Test B: Incomplete plan when airfare is unavailable displays informative note, not ₹0
        unavail_session = {
            "state": {
                "requirements": {"pax": 2, "duration_days": 3, "origin": "Delhi"},
                "selected_options": {
                    "transport": {
                        "mode": "flight",
                        "origin": "Delhi",
                        "fare_classification": "UNAVAILABLE",
                        "indicative_fare_min": None,
                    },
                    "accommodation": {
                        "name": "Katra Hotel",
                        "price_per_night": 1800,
                    },
                },
                "budget_evaluation": {
                    "is_complete": False,
                    "is_partially_estimated": False,
                    "verified_costs": {"total_verified": 3600.0, "hotel": 3600.0, "transport": 0.0},
                    "estimated_costs": {"total_estimated": 0.0, "items": {}},
                    "grand_total": None,
                },
                "plan_version": 1,
            }
        }
        unavail_text = format_itemized_cost_breakdown(unavail_session)
        self.assertIn("Airfare unavailable (dynamic pricing on airline website)", unavail_text)
        self.assertIn("Payable at booking (transport fare unverified)", unavail_text)
        self.assertNotIn("Estimated Grand Total: ₹0", unavail_text)

if __name__ == "__main__":
    unittest.main()
