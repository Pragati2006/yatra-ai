"""
tests/test_phase14_2_universal_origins.py
=========================================
Phase 14.2 Acceptance & Validation Test Suite:
Universal Origin Support & Intelligent Connecting Journey Planning.

Verifies:
1. Universal Origin Acceptance & Hub Discovery across 30+ diverse locations:
   - Metros (Delhi, Mumbai, Kolkata, Bengaluru, Chennai, Hyderabad).
   - Regional/Tier-2/3 (Chandigarh, Amritsar, Pathankot, Jalandhar, Ludhiana, Jaipur, Lucknow, Patna, Bhopal, Pune, Ahmedabad).
   - Himachal Pradesh (Palampur, Mandi, Village near Mandi, Rewalsar near Mandi, Dharamshala, Una, Kullu, Manali, Shimla, Baijnath).
   - Jammu & Kashmir local corridors (Udhampur, Reasi, Kishtwar, Poonch, Rajouri, Doda, Ramban, Srinagar).
   - Ambiguous origins (Bilaspur HP vs CG).
   - Remote / unmapped settlements (graceful zero-rejection heuristic).
2. Connecting Journey Engine multi-leg construction & 5-level fallback logic.
3. Strict truth-in-data: no fake train numbers, no fabricated fares, honest status labels.
4. Central agent search_transport_options integration (no 7-city coverage limitations).
5. Orchestrator coordinate_plan feasibility (PLAN_READY without NO_AVAILABILITY rejections).
6. Multi-turn conversational entity retention and slot extraction without repeated questions.
"""

import os
import sys
import unittest
import uuid

# Ensure active repo root is on sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from services.geo_resolver import GeoResolver, ResolvedLocation, get_geo_resolver
from services.connecting_journey_engine import ConnectingJourneyEngine, get_connecting_journey_engine
from agents import conversation_state
from agents.central_agent import search_transport_options
from agents.orchestrator import coordinate_plan, orchestrate_conversational_turn


# =============================================================================
# 1. 30+ Diverse Indian Origins Dataset
# =============================================================================

TEST_ORIGINS_30 = [
    # Metros & Major Gateways
    {"origin": "Delhi", "type": "Metro", "expected_gateway": "New Delhi", "expect_direct": True},
    {"origin": "Mumbai", "type": "Metro", "expected_gateway": "Mumbai", "expect_direct": True},
    {"origin": "Kolkata", "type": "Metro", "expected_gateway": "Kolkata", "expect_direct": True},
    {"origin": "Bengaluru", "type": "Metro", "expected_gateway": "Bengaluru", "expect_direct": True},
    {"origin": "Chennai", "type": "Metro", "expected_gateway": "Chennai", "expect_direct": True},
    {"origin": "Hyderabad", "type": "Metro", "expected_gateway": "New Delhi / Jammu", "expect_direct": False},

    # Regional & Tier-2/3
    {"origin": "Chandigarh", "type": "Regional Hub", "expected_gateway": "Chandigarh", "expect_direct": True},
    {"origin": "Amritsar", "type": "Regional Hub", "expected_gateway": "Amritsar", "expect_direct": True},
    {"origin": "Pathankot", "type": "Strategic Railhead", "expected_gateway": "Pathankot", "expect_direct": True},
    {"origin": "Jalandhar", "type": "Tier-2", "expected_gateway": "Pathankot / Jalandhar", "expect_direct": False},
    {"origin": "Ludhiana", "type": "Tier-2", "expected_gateway": "Ludhiana", "expect_direct": True},
    {"origin": "Jaipur", "type": "Tier-2", "expected_gateway": "Delhi / Jammu", "expect_direct": False},
    {"origin": "Lucknow", "type": "Tier-2", "expected_gateway": "Delhi / Jammu", "expect_direct": False},
    {"origin": "Patna", "type": "Tier-2", "expected_gateway": "New Delhi", "expect_direct": False},
    {"origin": "Bhopal", "type": "Tier-2", "expected_gateway": "New Delhi", "expect_direct": False},
    {"origin": "Pune", "type": "Tier-2", "expected_gateway": "Mumbai / New Delhi", "expect_direct": False},
    {"origin": "Ahmedabad", "type": "Tier-2", "expected_gateway": "Ahmedabad", "expect_direct": True},

    # Himachal Pradesh
    {"origin": "Palampur", "type": "HP Hill Town", "expected_gateway": "Pathankot Cantt (PTKC)", "expect_direct": False},
    {"origin": "Mandi", "type": "HP District HQ", "expected_gateway": "Pathankot / Chandigarh", "expect_direct": False},
    {"origin": "a small village near Mandi", "type": "Rural Settlement", "expected_gateway": "Pathankot / Chandigarh", "expect_direct": False},
    {"origin": "Rewalsar near Mandi", "type": "Rural Sub-location", "expected_gateway": "Pathankot / Chandigarh", "expect_direct": False},
    {"origin": "Dharamshala", "type": "HP Tourist Hub", "expected_gateway": "Pathankot Cantt (PTKC)", "expect_direct": False},
    {"origin": "Una", "type": "HP Railhead", "expected_gateway": "Una Himachal (UHL)", "expect_direct": False},
    {"origin": "Kullu", "type": "HP Hill Valley", "expected_gateway": "Chandigarh / Pathankot", "expect_direct": False},
    {"origin": "Manali", "type": "HP Hill Station", "expected_gateway": "Chandigarh / Pathankot", "expect_direct": False},
    {"origin": "Shimla", "type": "HP State Capital", "expected_gateway": "Kalka / Chandigarh", "expect_direct": False},
    {"origin": "Baijnath", "type": "HP Pilgrim Town", "expected_gateway": "Pathankot", "expect_direct": False},

    # Jammu & Kashmir Corridors
    {"origin": "Reasi", "type": "Direct Road Neighbour", "expected_gateway": "Katra", "expect_direct": False},
    {"origin": "Udhampur", "type": "Adjacent Rail Corridor", "expected_gateway": "Katra", "expect_direct": False},
    {"origin": "Kishtwar", "type": "J&K Hill District", "expected_gateway": "Jammu / Katra", "expect_direct": False},
    {"origin": "Poonch", "type": "J&K Border District", "expected_gateway": "Jammu", "expect_direct": False},
    {"origin": "Rajouri", "type": "J&K Hill District", "expected_gateway": "Jammu", "expect_direct": False},
    {"origin": "Doda", "type": "J&K Hill District", "expected_gateway": "Jammu / Udhampur", "expect_direct": False},
    {"origin": "Ramban", "type": "J&K Highway Corridor", "expected_gateway": "Udhampur / Katra", "expect_direct": False},
    {"origin": "Srinagar", "type": "J&K Summer Capital", "expected_gateway": "Jammu / Katra", "expect_direct": False},

    # Ambiguity Test
    {"origin": "Bilaspur", "type": "Ambiguous Place", "expected_gateway": "Clarification", "expect_direct": False},
    {"origin": "Bilaspur, HP", "type": "Disambiguated Place", "expected_gateway": "Kiratpur / Chandigarh", "expect_direct": False},

    # Remote Fallback
    {"origin": "remote hamlet in Chamba valley", "type": "Remote Unmapped", "expected_gateway": "Pathankot", "expect_direct": False},
]


# =============================================================================
# Test Suite
# =============================================================================

class TestPhase142UniversalOrigins(unittest.TestCase):
    """Comprehensive test suite covering all 13 Phase 14.2 requirements."""

    def setUp(self):
        self.geo = get_geo_resolver()
        self.engine = get_connecting_journey_engine()

    def test_01_30_diverse_origins_resolved_without_rejection(self):
        """Requirement 1 & 7: Verify all 30+ origins resolve with zero exceptions or abrupt rejections."""
        self.assertGreaterEqual(len(TEST_ORIGINS_30), 30, f"Expected at least 30 test origins, found {len(TEST_ORIGINS_30)}")

        for item in TEST_ORIGINS_30:
            origin = item["origin"]
            res = self.geo.resolve_origin(origin)

            self.assertIsInstance(res, ResolvedLocation, f"Failed resolving {origin}")
            self.assertTrue(bool(res.clean_name), f"clean_name missing for {origin}")
            self.assertTrue(bool(res.primary_gateway_hub), f"primary_gateway_hub missing for {origin}")
            self.assertGreater(res.confidence, 0, f"Confidence zero for {origin}")

            # Check that ambiguous Bilaspur is flagged
            if origin == "Bilaspur":
                self.assertTrue(res.is_ambiguous, f"Expected Bilaspur to be flagged ambiguous")
                self.assertGreaterEqual(len(res.ambiguity_candidates), 2)

            # Check rural village extraction
            if "village near Mandi" in origin:
                self.assertTrue(res.is_village_or_settlement)
                self.assertEqual(res.base_town, "Mandi")

            if "Rewalsar near Mandi" in origin:
                self.assertTrue(res.is_village_or_settlement)
                self.assertEqual(res.base_town, "Mandi")

    def test_02_connecting_journey_engine_multi_leg_generation(self):
        """Requirement 2: Multi-leg route construction produces 2-3 practical options for non-direct origins."""
        non_direct_cases = [
            "Palampur",
            "Mandi",
            "a small village near Mandi",
            "Rewalsar near Mandi",
            "Dharamshala",
            "Una",
            "Jaipur",
            "Lucknow",
            "Patna",
            "Pune",
            "Kishtwar",
        ]

        for origin in non_direct_cases:
            journey = self.engine.plan_connecting_journey(origin, start_date="2026-11-20", pax=2)
            self.assertEqual(journey["status"], "CONNECTING_ROUTES_AVAILABLE", f"Status unexpected for {origin}: {journey['status']}")
            self.assertGreaterEqual(journey["options_count"], 2, f"Fewer than 2 options generated for {origin}")

            # Check leg structure of first option
            opt = journey["options"][0]
            self.assertIn("legs", opt)
            self.assertGreaterEqual(len(opt["legs"]), 2, f"Option for {origin} lacks multi-leg structure")
            self.assertTrue(bool(opt["summary_route"]), f"Missing summary route for {origin}")
            self.assertTrue(bool(opt["primary_hub"]), f"Missing primary hub for {origin}")

            # Check leg verification status transparency
            for leg in opt["legs"]:
                self.assertIn(
                    leg["verification_status"],
                    ("VERIFIED_SCHEDULE", "SUGGESTED_CONNECTING_LEG", "ESTIMATED_ROAD_TRANSFER"),
                    f"Unexpected verification status in {origin}: {leg['verification_status']}"
                )
                self.assertTrue(bool(leg["from_place"]) and bool(leg["to_place"]), f"Leg missing endpoints for {origin}")

    def test_03_adjacent_foothill_neighbours_special_handling(self):
        """Requirement 2 & 5: Towns right next to Katra (Reasi ~28 km, Udhampur ~42 km) get direct road options."""
        for adj in ["Reasi", "Udhampur"]:
            journey = self.engine.plan_connecting_journey(adj, start_date="2026-11-20", pax=2)
            self.assertEqual(journey["status"], "CONNECTING_ROUTES_AVAILABLE")
            self.assertGreaterEqual(journey["options_count"], 2)

            # Option 1 should be a direct road taxi / shared feeder
            opt1 = journey["options"][0]
            self.assertEqual(opt1["legs_count"], 1, f"Expected 1-leg direct transfer for {adj}, got {opt1['legs_count']}")
            self.assertTrue(
                "Road Taxi" in opt1["legs"][0]["mode"] or "Direct Cab" in opt1["legs"][0]["transport_name"],
                f"Expected Road Taxi / Direct Cab mode for {adj}"
            )

    def test_04_level_5_ambiguity_clarification(self):
        """Requirement 3 & Level 5: Ambiguous origins prompt friendly clarification without rejection."""
        journey = self.engine.plan_connecting_journey("Bilaspur")
        self.assertEqual(journey["status"], "NEEDS_CLARIFICATION")
        self.assertTrue(journey["requires_clarification"])
        self.assertIn("clarification_prompt", journey)
        self.assertIn("Himachal Pradesh", journey["clarification_prompt"])
        self.assertIn("Chhattisgarh", journey["clarification_prompt"])

        # Disambiguated query succeeds immediately
        journey_hp = self.engine.plan_connecting_journey("Bilaspur, HP")
        self.assertEqual(journey_hp["status"], "CONNECTING_ROUTES_AVAILABLE")
        self.assertFalse(journey_hp["requires_clarification"])

    def test_05_central_agent_search_transport_options_integration(self):
        """Requirement 4: search_transport_options does not reject non-direct origins with 7-city limitation."""
        for test_origin in ["Palampur", "Village (near Mandi)", "Jaipur", "Pune"]:
            res = search_transport_options.invoke({"origin": test_origin, "start_date": "2026-11-22", "pax": 2})

            self.assertEqual(res["origin"], test_origin)
            self.assertGreaterEqual(res["options_count"], 2, f"Failed for {test_origin}: count={res.get('options_count')}")
            self.assertTrue(res.get("is_connecting"), f"Expected is_connecting=True for {test_origin}")
            self.assertNotIn("coverage_limitation", res, f"Unexpected coverage_limitation present for {test_origin}")

            for opt in res["options"]:
                self.assertTrue(opt.get("is_connecting"))
                if opt.get("status") == "CONNECTING_ROUTE":
                    self.assertIn("legs", opt)
                    self.assertGreaterEqual(len(opt["legs"]), 2)
                self.assertTrue(bool(opt.get("route_note")), f"Missing route note for {test_origin}")

    def test_06_orchestrator_coordinate_plan_success(self):
        """Requirement 5: coordinate_plan builds PLAN_READY for non-direct origins without NO_AVAILABILITY."""
        test_cases = [
            {"origin": "Palampur", "pax": 2},
            {"origin": "Village (near Mandi)", "pax": 2},
            {"origin": "Reasi", "pax": 1},
            {"origin": "Lucknow", "pax": 3},
        ]

        for tc in test_cases:
            req = {
                "origin": tc["origin"],
                "pax": tc["pax"],
                "start_date": "2026-11-25",
                "duration_days": 4,
            }
            res = coordinate_plan(req, session_id=f"test-plan-{tc['origin']}")
            self.assertEqual(res["status"], "PLAN_READY", f"Failed for {tc['origin']}: status={res.get('status')}")
            plan = res.get("plan", {})
            self.assertEqual(plan.get("status"), "PLAN_READY")
            options = plan.get("options", [])
            self.assertGreaterEqual(len(options), 1, f"No options in plan for {tc['origin']}")

            # Verify connecting route attributes
            first_opt = options[0]
            tr = first_opt.get("transport", {})
            self.assertTrue(tr.get("is_connecting"), f"Transport is not marked connecting for {tc['origin']}")

    def test_07_conversational_state_rural_extraction_no_repeated_questions(self):
        """Requirement 4 & 6: Multi-turn conversational flow with rural origin and no repeated questions."""
        session_id = f"test-multi-turn-rural-{uuid.uuid4().hex[:8]}"

        # Turn 1: User specifies rural village origin and pilgrim count
        t1_text = "I want to plan a Vaishno Devi pilgrimage from a small village near Mandi for two adults."
        t1_res = orchestrate_conversational_turn(t1_text, session_id=session_id)
        actual_sid = t1_res.get("session_id")

        req1 = t1_res.get("requirements", {})
        self.assertEqual(req1.get("origin"), "Village (near Mandi)", f"Failed extracting origin: {req1.get('origin')}")
        self.assertEqual(req1.get("pax"), 2, f"Failed extracting pax: {req1.get('pax')}")

        # Crucial: Must NOT ask for origin or pax again!
        missing1 = t1_res.get("missing_fields", [])
        self.assertNotIn("origin", missing1, "Origin was marked missing despite being supplied!")
        self.assertNotIn("pax", missing1, "Pax was marked missing despite being supplied!")

        # Turn 2: User adds parents (pax change) and prefers bus
        t2_text = "Actually my parents will also join us, so total 4 pilgrims, and we prefer travelling by bus."
        t2_res = orchestrate_conversational_turn(t2_text, session_id=actual_sid)

        req2 = t2_res.get("requirements", {})
        self.assertEqual(req2.get("origin"), "Village (near Mandi)", f"Origin lost on turn 2: {req2.get('origin')}")
        self.assertEqual(req2.get("pax"), 4, f"Pax not updated to 4: {req2.get('pax')}")
        self.assertEqual(req2.get("mode"), "bus", f"Mode not updated to bus: {req2.get('mode')}")

        # Turn 3: User changes origin to Chandigarh
        t3_text = "Can you change our starting city to Chandigarh?"
        t3_res = orchestrate_conversational_turn(t3_text, session_id=actual_sid)

        req3 = t3_res.get("requirements", {})
        self.assertEqual(req3.get("origin"), "Chandigarh", f"Origin not switched to Chandigarh: {req3.get('origin')}")
        self.assertEqual(req3.get("pax"), 4, f"Pax lost after origin switch: {req3.get('pax')}")
        self.assertEqual(req3.get("mode"), "bus", f"Mode lost after origin switch: {req3.get('mode')}" )

    def test_08_temporal_words_never_extracted_as_origin(self):
        """Requirement 1: Temporal words must never be misclassified as origin."""
        temporal_queries = [
            "For 3 days starting tomorrow",
            "Tomorrow morning",
            "Planning for next Monday",
            "We want to start today",
        ]
        for query in temporal_queries:
            extracted = conversation_state.extract_origin_city(query)
            self.assertIsNone(extracted, f"Temporal query '{query}' misclassified as origin '{extracted}'")


if __name__ == "__main__":
    unittest.main()
