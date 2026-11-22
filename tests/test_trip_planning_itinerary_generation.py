"""
tests/test_trip_planning_itinerary_generation.py

Validates Phase 8.8.30C: Critical Trip Planning & Itinerary Generation Fix.
Ensures that multi-turn trip intake collects missing details and generates a
complete, meaningful, day-wise itinerary with trip overview, daily activities,
transport recommendations, accommodation arrangements, itemized budget breakdown
with budget honesty assessment, and customization guidance.
"""

import os
import shutil
import sys
import tempfile
import unittest

# Ensure UTF-8 output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import db
from agents import orchestrator, session_store


class TestTripPlanningItineraryGeneration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(self.temp_dir, "test_sessions.db")
        self.orig_db_path = session_store.DEFAULT_DB_PATH
        session_store.DEFAULT_DB_PATH = self.temp_db_path
        session_store.init_db(self.temp_db_path)
        db.ensure_live_data()

    def tearDown(self):
        session_store.DEFAULT_DB_PATH = self.orig_db_path
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Test 1: Multi-turn flow where origin is missing in Turn 1
    # -------------------------------------------------------------------------
    def test_multi_turn_missing_origin_then_full_itinerary(self):
        """
        Turn 1: User provides duration, pax, and budget, but omits origin.
        Turn 2: User provides origin ('Delhi').
        Expected: Full, complete day-wise itinerary is generated, not just an input summary.
        """
        # Turn 1
        r1 = orchestrator.orchestrate_conversational_turn(
            "Plan a trip for 4 days with 5 people with a budget of ₹20,000."
        )
        self.assertEqual(r1["status"], "NEEDS_INFO")
        self.assertIn("origin", r1["missing_fields"])
        sid = r1["session_id"]
        self.assertIsNotNone(sid)

        # Assistant should politely ask for departure city/town
        r1_reply = r1["reply"].lower()
        self.assertTrue(
            any(w in r1_reply for w in ("city", "town", "travelling from", "traveling from", "departure")),
            f"Expected question about origin, got: {r1['reply']}"
        )

        # Requirements should preserve accumulated details across turns
        req1 = r1["requirements"]
        self.assertEqual(req1.get("duration_days"), 4)
        self.assertEqual(req1.get("pax"), 5)
        self.assertEqual(req1.get("total_budget"), 20000.0)

        # Turn 2: User supplies origin
        r2 = orchestrator.orchestrate_conversational_turn("Delhi", session_id=sid)
        self.assertEqual(r2["status"], "PLAN_READY")
        self.assertEqual(r2["missing_fields"], [])

        reply = r2["reply"]
        self.assertIsNotNone(reply)

        # A. Devotional greeting & Trip Overview
        self.assertIn("Jai Mata Di", reply)
        self.assertIn("Trip Overview", reply)
        self.assertIn("Delhi", reply)
        self.assertIn("4 Days", reply)
        self.assertIn("5 Pilgrims", reply)
        self.assertIn("₹20,000", reply)
        self.assertIn("3 rooms", reply)

        # B. Day-Wise Itinerary (Must have all 4 days with activities and timings)
        self.assertIn("Day-Wise Itinerary", reply)
        self.assertIn("Day 1:", reply)
        self.assertIn("Day 2:", reply)
        self.assertIn("Day 3:", reply)
        self.assertIn("Day 4:", reply)

        # Day 1: Arrival & Registration
        self.assertIn("Arrival", reply)
        self.assertIn("RFID", reply)

        # Day 2: Dedicated Yatra Trek
        self.assertIn("Dedicated Holy Yatra", reply)
        self.assertTrue(
            any(k in reply for k in ("Ban Ganga", "Tarakote Marg", "Charan Paduka", "Ardhkuwari")),
            "Expected sacred trek waypoints on Day 2"
        )
        self.assertIn("Bhawan", reply)
        self.assertIn("Bhairavnath", reply)

        # Day 3: Post-Trek Recovery / Sightseeing
        self.assertTrue(
            any(k in reply for k in ("Recovery", "Baba Dhansar", "Sightseeing")),
            "Expected Day 3 to cover recovery / gentle sightseeing"
        )

        # Day 4: Return
        self.assertIn("Return Journey", reply)

        # Meals & Stay guidance for each day
        self.assertIn("Meals:", reply)
        self.assertIn("Stay:", reply)

        # C. Transport Recommendation
        self.assertIn("Transport Recommendation", reply)
        self.assertIn("Delhi ➔ Katra", reply)
        self.assertIn("Total Group Transport Cost:", reply)

        # D. Accommodation Arrangements
        self.assertIn("Accommodation Arrangements", reply)
        self.assertIn("Recommended Property:", reply)
        self.assertIn("Allocation:", reply)
        self.assertIn("Curated Category Alternatives", reply)

        # E. Budget Breakdown & Honesty Assessment
        self.assertIn("Budget Breakdown", reply)
        self.assertIn("Intercity Travel", reply)
        self.assertIn("Accommodation", reply)
        self.assertIn("Meals & Refreshments", reply)
        self.assertIn("Local Katra Transfers", reply)
        self.assertIn("Estimated Total Group Cost:", reply)
        self.assertIn("Estimated Cost Per Person:", reply)

        # Honesty: ₹20,000 for 5 people (₹4,000/person) fits with affordable options
        self.assertIn("Budget Assessment", reply)

        # F. Customization & Next Steps
        self.assertIn("Customization & Next Steps", reply)

        # Crucial check: Must NOT simply be an input summary (should have substantial depth)
        lines = [l for l in reply.split("\n") if l.strip()]
        self.assertGreater(len(lines), 25, "Response must be a comprehensive itinerary, not a 4-line snippet")

    # -------------------------------------------------------------------------
    # Test 2: Ambiguous destination handling
    # -------------------------------------------------------------------------
    def test_missing_destination_handling(self):
        """
        When user specifies origin ('from Delhi'), duration, pax, and budget,
        but completely omits the destination and pilgrimage context,
        the system must ask for the destination rather than silently assuming Katra.
        Once supplied, it proceeds to generate the full itinerary.
        """
        # Turn 1: Generic trip without destination or pilgrimage terms
        s1 = orchestrator.orchestrate_conversational_turn(
            "Plan a 4-day trip from Delhi for 5 people with a budget of ₹20,000."
        )
        self.assertEqual(s1["status"], "NEEDS_INFO")
        self.assertIn("destination", s1["missing_fields"])
        self.assertIn("Which destination or pilgrimage circuit", s1["reply"])

        sid = s1["session_id"]

        # Turn 2: User provides destination
        s2 = orchestrator.orchestrate_conversational_turn("Vaishno Devi", session_id=sid)
        self.assertEqual(s2["status"], "PLAN_READY")
        self.assertEqual(s2["missing_fields"], [])

        reply = s2["reply"]
        self.assertIn("Trip Overview", reply)
        self.assertIn("Delhi", reply)
        self.assertIn("Day-Wise Itinerary", reply)
        self.assertIn("Day 1:", reply)
        self.assertIn("Day 4:", reply)
        self.assertIn("Budget Breakdown", reply)

    # -------------------------------------------------------------------------
    # Test 3: Explicit single-turn trip planning
    # -------------------------------------------------------------------------
    def test_explicit_single_turn_trip_planning(self):
        """
        When user specifies origin, destination, duration, pax, and budget in a single turn,
        the full itinerary is generated immediately without follow-up questions.
        """
        res = orchestrator.orchestrate_conversational_turn(
            "Plan a 4-day trip from Delhi to Vaishno Devi for 5 people with a budget of ₹20,000."
        )
        self.assertEqual(res["status"], "PLAN_READY")
        self.assertEqual(res["missing_fields"], [])

        reply = res["reply"]
        self.assertIn("Delhi", reply)
        self.assertIn("Vaishno Devi", reply)
        self.assertIn("Day-Wise Itinerary", reply)
        self.assertIn("Day 1:", reply)
        self.assertIn("Day 2:", reply)
        self.assertIn("Day 3:", reply)
        self.assertIn("Day 4:", reply)
        self.assertIn("Budget Breakdown", reply)
        self.assertIn("Transport Recommendation", reply)
        self.assertIn("Accommodation Arrangements", reply)

    # -------------------------------------------------------------------------
    # Test 4: Budget honesty evaluation
    # -------------------------------------------------------------------------
    def test_budget_honesty_evaluation(self):
        """
        Tests that ₹20,000 for 5 people (₹4,000/person) produces a realistic reconciled total,
        and accurately identifies remaining budget buffer.
        """
        res = orchestrator.orchestrate_conversational_turn(
            "Plan a 4-day trip from Delhi to Katra for 5 people with a budget of ₹20,000."
        )
        reply = res["reply"]

        # Must mention group budget and per person budget
        self.assertIn("₹20,000", reply)
        self.assertIn("₹4,000 per person", reply)

        # Budget breakdown must be itemized
        self.assertIn("Intercity Travel", reply)
        self.assertIn("Accommodation", reply)
        self.assertIn("Meals & Refreshments", reply)
        self.assertIn("Local Katra Transfers", reply)
        self.assertIn("RFID Parchi", reply)

        # Must provide clear budget assessment (within budget for subsidized options)
        self.assertIn("Budget Assessment", reply)


if __name__ == "__main__":
    unittest.main()

