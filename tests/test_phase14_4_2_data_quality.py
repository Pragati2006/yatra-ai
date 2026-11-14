"""
yatra-ai/tests/test_phase14_4_2_data_quality.py
Regression test suite for Phase 14.4.2:
- Geographic data quality and reconciliation
- Disambiguation and conversational clarification propagation
- Suppression of internal labels ('NEEDS_CLARIFICATION', 'Clarification Required')
- Multi-turn origin state persistence and correction
- Foreign/invalid origin handling without arbitrary gateways
- Provenance tagging across connecting journey legs
- Sightseeing dataset 100% coordinates and administrative fields
"""

import sys
import os

# Add repo root to sys.path before local imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import unittest

from agents import conversation_state, orchestrator, session_store
from services.geo_resolver import get_geo_resolver
from services.connecting_journey_engine import get_connecting_journey_engine
import explore_data


class TestPhase1442DataQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = get_geo_resolver()
        cls.engine = get_connecting_journey_engine()

    def test_01_sightseeing_completeness(self):
        """All 29 sightseeing attractions must have validated coordinates, district, region, flags."""
        places = explore_data.PLACES
        self.assertEqual(len(places), 29, "Sightseeing catalog must contain exactly 29 unique destinations")
        for p in places:
            self.assertIn("coordinates", p, f"Missing coordinates in {p['name']}")
            self.assertIsNotNone(p["coordinates"], f"Coordinates is None in {p['name']}")
            self.assertIn("lat", p["coordinates"])
            self.assertIn("lng", p["coordinates"])
            self.assertGreater(p["coordinates"]["lat"], 32.0, f"Latitude out of bounds in {p['name']}")
            self.assertIn("district", p, f"Missing district in {p['name']}")
            self.assertTrue(len(p["district"]) > 0, f"Empty district in {p['name']}")
            self.assertIn("region", p, f"Missing region in {p['name']}")
            self.assertTrue(len(p["region"]) > 0, f"Empty region in {p['name']}")
            self.assertIn("coordinates_source", p, f"Missing coordinates_source in {p['name']}")
            self.assertIn("timings_verified", p, f"Missing timings_verified flag in {p['name']}")
            self.assertIn("entry_fee_verified", p, f"Missing entry_fee_verified flag in {p['name']}")

    def test_02_ambiguous_origin_detection(self):
        """Ambiguous places must trigger is_ambiguous=True with valid candidates."""
        # Bilaspur
        res_bil = self.geo.resolve_origin("Bilaspur")
        self.assertTrue(res_bil.is_ambiguous)
        self.assertEqual(len(res_bil.ambiguity_candidates), 2)
        cand_states = [c["state"] for c in res_bil.ambiguity_candidates]
        self.assertIn("Himachal Pradesh", cand_states)
        self.assertIn("Chhattisgarh", cand_states)

        # Anandpur
        res_anand = self.geo.resolve_origin("Anandpur")
        self.assertTrue(res_anand.is_ambiguous)
        cand_states = [c["state"] for c in res_anand.ambiguity_candidates]
        self.assertIn("Punjab", cand_states)
        self.assertIn("Odisha", cand_states)

        # Aurangabad
        res_aur = self.geo.resolve_origin("Aurangabad")
        self.assertTrue(res_aur.is_ambiguous)
        cand_states = [c["state"] for c in res_aur.ambiguity_candidates]
        self.assertIn("Maharashtra", cand_states)
        self.assertIn("Bihar", cand_states)

        # Rampur
        res_ramp = self.geo.resolve_origin("Rampur")
        self.assertTrue(res_ramp.is_ambiguous)

        # Pratapgarh
        res_prat = self.geo.resolve_origin("Pratapgarh")
        self.assertTrue(res_prat.is_ambiguous)

    def test_03_disambiguated_origin_resolution(self):
        """Qualified origins must resolve cleanly without ambiguity."""
        res_hp = self.geo.resolve_origin("Bilaspur in Himachal Pradesh")
        self.assertFalse(res_hp.is_ambiguous)
        self.assertEqual(res_hp.state, "Himachal Pradesh")
        self.assertIn("Kiratpur", res_hp.primary_gateway_hub)

        res_cg = self.geo.resolve_origin("Bilaspur CG")
        self.assertFalse(res_cg.is_ambiguous)
        self.assertEqual(res_cg.state, "Chhattisgarh")
        self.assertIn("New Delhi", res_cg.primary_gateway_hub)

        res_pb = self.geo.resolve_origin("Anandpur Sahib")
        self.assertFalse(res_pb.is_ambiguous)
        self.assertEqual(res_pb.state, "Punjab")

    def test_04_invalid_and_foreign_origin_safeguards(self):
        """Foreign cities, digits, and keyboard mash must be detected as invalid."""
        for foreign in ("London", "New York", "Dubai", "Singapore"):
            res = self.geo.resolve_origin(foreign)
            self.assertTrue(res.is_invalid, f"Foreign city {foreign} should be marked invalid")

        for gibberish in ("12345", "asdfghjk", "qwertyuiop"):
            res = self.geo.resolve_origin(gibberish)
            self.assertTrue(res.is_invalid, f"Gibberish {gibberish} should be marked invalid")

    def test_05_bilaspur_conversational_clarification_flow(self):
        """Bilaspur must prompt for state clarification first, then resolve on follow-up."""
        # Turn 1
        t1 = orchestrator.orchestrate_conversational_turn(
            "I want to plan a pilgrimage to Vaishno Devi from Bilaspur"
        )
        self.assertEqual(t1.get("status"), "NEEDS_CLARIFICATION")
        self.assertNotIn("Clarification Required", t1.get("reply", ""))
        self.assertIn("Himachal Pradesh", t1.get("reply", ""))
        self.assertIn("Chhattisgarh", t1.get("reply", ""))
        # Crucial: Must NOT ask for passenger count or travel dates before resolving origin
        self.assertNotIn("How many pilgrims", t1.get("reply", ""))
        self.assertNotIn("What travel dates", t1.get("reply", ""))

        sid = t1["session_id"]

        # Turn 2: User provides state
        t2 = orchestrator.orchestrate_conversational_turn(
            "Himachal Pradesh, we are 2 people for 3 days",
            session_id=sid,
        )
        self.assertIn(t2.get("status"), ("PLAN_READY", "PLAN_REVISED"))
        self.assertIn("Bilaspur, Himachal Pradesh", t2.get("request", {}).get("origin", ""))
        self.assertEqual(t2.get("request", {}).get("pax"), 2)
        self.assertEqual(t2.get("request", {}).get("duration_days"), 3)

    def test_06_origin_correction_mid_clarification(self):
        """User can change their starting city during an ambiguity clarification prompt."""
        t1 = orchestrator.orchestrate_conversational_turn("Plan a trip from Anandpur")
        self.assertEqual(t1.get("status"), "NEEDS_CLARIFICATION")
        sid = t1["session_id"]

        t2 = orchestrator.orchestrate_conversational_turn(
            "Actually change my starting city to Delhi for 2 adults",
            session_id=sid,
        )
        self.assertEqual(t2.get("request", {}).get("origin"), "Delhi")
        self.assertNotIn("Punjab", str(t2.get("request", {}).get("origin")))

    def test_07_route_provenance_metadata(self):
        """Connecting journey legs must have explicit data provenance metadata."""
        conn = self.engine.plan_connecting_journey("Mandi, Himachal Pradesh")
        self.assertEqual(conn.get("status"), "CONNECTING_ROUTES_AVAILABLE")
        options = conn.get("options", [])
        self.assertGreaterEqual(len(options), 2)
        for opt in options:
            for leg in opt.get("legs", []):
                self.assertIsNotNone(leg.get("data_source"))
                self.assertIn(leg.get("data_tier"), ("curated", "estimated", "live", "synthetic", "unknown"))
                self.assertIsNotNone(leg.get("schedule_availability"))
                self.assertIsNotNone(leg.get("fare_source"))
                self.assertIsNotNone(leg.get("duration_source"))


if __name__ == "__main__":
    unittest.main()
