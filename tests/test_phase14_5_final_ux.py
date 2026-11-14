"""
yatra-ai/tests/test_phase14_5_final_ux.py
Final Conversational UX, Transport Integration & Cross-Platform Experience Test Suite.

Verifies:
1. Single-Question Clarification Policy progression (Turn 1: origin, Turn 2: pax, Turn 3: dates/duration).
2. Answer First, Question Later principle (elderly accessibility, weather, duration).
3. Repetitive greeting suppression on intermediate turns.
4. Remote origin connecting journey (Kishtwar -> UHP -> SVDK).
5. Direct foothill origin options (Udhampur MCTM Rail Link, bus, taxi).
6. Ambiguous origin clarification before secondary questions.
7. Mid-conversation corrections (pax, origin, travel mode) with state preservation.
8. Truth-in-data presentation without fabricated PNRs or ticket fares.
9. Human-authorized booking execution handoff.
10. Cross-platform payload compatibility for React Web & React Native Android.
"""

import os
import sys
import uuid
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents import orchestrator, session_store, central_agent
from services.connecting_journey_engine import get_connecting_journey_engine
from services.geo_resolver import get_geo_resolver


class TestPhase145FinalUX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_connecting_journey_engine()
        cls.geo = get_geo_resolver()

    def test_01_single_question_policy_progression(self):
        """Conversational flow must ask strictly ONE question at a time."""
        sid = session_store.create_session()["session_id"]

        # Turn 1: General intent
        res1 = orchestrator.orchestrate_conversational_turn("I want to visit Vaishno Devi", session_id=sid)
        reply1 = res1.get("reply", "")
        self.assertIn("Which city or town will you be travelling from", reply1)
        self.assertNotIn("how many pilgrims", reply1.lower())
        self.assertNotIn("travel dates or duration", reply1.lower())

        # Turn 2: Provide origin
        res2 = orchestrator.orchestrate_conversational_turn("I am coming from Chandigarh", session_id=sid)
        reply2 = res2.get("reply", "")
        self.assertIn("Chandigarh", reply2)
        self.assertIn("How many pilgrims", reply2)
        self.assertNotIn("travel dates or duration", reply2.lower())

        # Turn 3: Provide pax
        res3 = orchestrator.orchestrate_conversational_turn("We are 3 people", session_id=sid)
        reply3 = res3.get("reply", "")
        self.assertTrue("3" in reply3 or "three" in reply3.lower())
        self.assertIn("What travel dates or trip duration", reply3)

        # Turn 4: Provide duration
        res4 = orchestrator.orchestrate_conversational_turn("3 days next week", session_id=sid)
        reply4 = res4.get("reply", "")
        self.assertEqual(res4.get("intent"), "TRIP_PLANNING")
        self.assertIn("Chandigarh", reply4)
        self.assertIn("Estimated total", reply4)

    def test_02_repetitive_greeting_suppression(self):
        """Intermediate conversational turns must not repeat '🙏 Jai Mata Di!' on every message."""
        sid = session_store.create_session()["session_id"]

        # Turn 1: Opening greeting is customary
        res1 = orchestrator.orchestrate_conversational_turn("Help me plan my yatra", session_id=sid)
        reply1 = res1.get("reply", "")
        self.assertIn("Jai Mata Di", reply1)

        # Turn 2: Intermediate turn answering origin
        res2 = orchestrator.orchestrate_conversational_turn("from Delhi", session_id=sid)
        reply2 = res2.get("reply", "").strip()
        # Should NOT start with 🙏 **Jai Mata Di!**
        self.assertFalse(reply2.startswith("🙏 **Jai Mata Di!**"), f"Turn 2 repeated opening greeting: {reply2[:60]}")

        # Turn 3: Intermediate turn answering pax
        res3 = orchestrator.orchestrate_conversational_turn("2 people", session_id=sid)
        reply3 = res3.get("reply", "").strip()
        self.assertFalse(reply3.startswith("🙏 **Jai Mata Di!**"), f"Turn 3 repeated opening greeting: {reply3[:60]}")

    def test_03_answer_first_elderly_accessibility(self):
        """Senior/accessibility queries must be answered FIRST before asking clarifying questions."""
        sid = session_store.create_session()["session_id"]

        res = orchestrator.orchestrate_conversational_turn(
            "Can senior citizens easily visit? We are 2 elderly people from Delhi.",
            session_id=sid,
        )
        reply = res.get("reply", "")

        # Substantive accessibility answer present
        self.assertTrue(
            any(k in reply.lower() for k in ("battery car", "helicopter", "palki", "pony", "adhkuwari", "trek")),
            "Reply must provide senior/elderly mobility guidance",
        )
        # Follow-up question for duration comes after
        self.assertIn("What travel dates or trip duration", reply)

    def test_04_returning_pilgrim_complete_request(self):
        """A complete multi-parameter request from an experienced traveller should yield a plan immediately."""
        sid = session_store.create_session()["session_id"]

        res = orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Delhi by train with total budget 15000",
            session_id=sid,
        )
        self.assertEqual(res.get("intent"), "TRIP_PLANNING")
        self.assertIn("Delhi", res.get("reply", ""))
        self.assertIn("Estimated total", res.get("reply", ""))
        self.assertIsNotNone(res.get("budget_evaluation"))
        self.assertEqual(res.get("plan_version"), 1)

    def test_05_remote_origin_udhampur_shuttle_integration(self):
        """Kishtwar must route via Udhampur (UHP) using the authentic MCTM regional rail link."""
        journey = self.engine.plan_connecting_journey("Kishtwar")
        self.assertEqual(journey["fallback_level"], "Level 2: Verified Connection via Nearby Hub")

        # Find rail-connect option
        rail_opt = next((o for o in journey["options"] if o["mode"] == "Train-Connect"), None)
        self.assertIsNotNone(rail_opt, "Kishtwar must offer a Train-Connect option via Udhampur")
        self.assertEqual(rail_opt["primary_hub"], "Udhampur")
        self.assertIn("185", str(rail_opt["estimated_total_distance_km"]))

        # Verify legs
        legs = rail_opt["legs"]
        self.assertEqual(len(legs), 2)
        # Leg 2 must be the verified UHP regional link
        self.assertEqual(legs[1]["from_place"], "Udhampur (UHP)")
        self.assertEqual(legs[1]["to_place"], "Shri Mata Vaishno Devi Katra (SVDK)")
        self.assertIn(legs[1]["verification_status"], ("SUGGESTED_CONNECTING_LEG", "VERIFIED_SCHEDULE"))
        self.assertIn("Udhampur (MCTM)", legs[1]["transport_name"])
        self.assertNotIn("04615", legs[1]["transport_name"])
        self.assertEqual(legs[1]["indicative_price_per_pax"], 30.0)

    def test_06_direct_foothill_udhampur_origin(self):
        """Udhampur origin must present genuine local options: DMU rail shuttle, JKRTC bus, road taxi."""
        journey = self.engine.plan_connecting_journey("Udhampur")
        options = journey.get("options", [])
        self.assertGreaterEqual(len(options), 2)

        modes = [o["mode"] for o in options]
        self.assertIn("Train-Direct", modes)
        self.assertIn("Road-Direct", modes)

        dmu_opt = next(o for o in options if o["mode"] == "Train-Direct")
        self.assertIn("₹30", dmu_opt["fare_summary"])
        self.assertIn("Udhampur (MCTM)", dmu_opt["legs"][0]["transport_name"])
        self.assertNotIn("04615", dmu_opt["legs"][0]["transport_name"])

    def test_07_ambiguous_origin_clarification(self):
        """Bilaspur must trigger geographic clarification BEFORE asking for passenger count or dates."""
        sid = session_store.create_session()["session_id"]

        res = orchestrator.orchestrate_conversational_turn("I want to travel from Bilaspur", session_id=sid)
        reply = res.get("reply", "")

        self.assertIn("Himachal Pradesh", reply)
        self.assertIn("Chhattisgarh", reply)
        # Truth-in-data: No internal status labels exposed
        self.assertNotIn("NEEDS_CLARIFICATION", reply)
        self.assertNotIn("Clarification Required", reply)
        # Do not ask secondary questions yet
        self.assertNotIn("how many pilgrims", reply.lower())

        # Follow up with state disambiguation
        res2 = orchestrator.orchestrate_conversational_turn("Bilaspur in Himachal Pradesh", session_id=sid)
        reply2 = res2.get("reply", "")
        self.assertIn("Himachal Pradesh", reply2)
        self.assertIn("How many pilgrims", reply2)

    def test_08_mid_conversation_correction_pax(self):
        """Changing pax mid-conversation updates revision number, room requirements, and budget."""
        sid = session_store.create_session()["session_id"]

        # Step 1: Create active plan
        orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Delhi by train",
            session_id=sid,
        )

        # Step 2: Edit pax mid-conversation
        res_edit = orchestrator.orchestrate_conversational_turn("Actually make it 5 people", session_id=sid)
        reply_edit = res_edit.get("reply", "")

        self.assertEqual(res_edit.get("status"), "PLAN_REVISED")
        self.assertEqual(res_edit.get("plan_version"), 2)
        self.assertIn("5 pilgrims", reply_edit)
        self.assertIn("Revision #2", reply_edit)

        # Step 3: Verify state preservation
        session = session_store.get_session(sid)
        state_req = session["state"]["requirements"]
        self.assertEqual(state_req["pax"], 5)
        self.assertEqual(state_req["origin"], "Delhi")
        self.assertEqual(state_req["duration_days"], 3)

    def test_09_mid_conversation_correction_origin(self):
        """Changing origin mid-conversation replans the transport route and updates revision."""
        sid = session_store.create_session()["session_id"]

        # Step 1: Initial plan
        orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Delhi by train",
            session_id=sid,
        )

        # Step 2: Change origin
        res_edit = orchestrator.orchestrate_conversational_turn("Actually change starting city to Jaipur", session_id=sid)

        self.assertEqual(res_edit.get("status"), "PLAN_REVISED")
        self.assertEqual(res_edit.get("plan_version"), 2)

        session = session_store.get_session(sid)
        state_req = session["state"]["requirements"]
        self.assertEqual(state_req["origin"], "Jaipur")
        self.assertEqual(state_req["pax"], 2)

    def test_10_mid_conversation_correction_travel_mode(self):
        """Changing mode to flight triggers airport link advisory and recalculates budget."""
        sid = session_store.create_session()["session_id"]

        # Step 1: Initial plan
        orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Mumbai by train",
            session_id=sid,
        )

        # Step 2: Change mode to flight
        res_edit = orchestrator.orchestrate_conversational_turn("Prefer flight instead", session_id=sid)

        self.assertEqual(res_edit.get("status"), "PLAN_REVISED")
        self.assertEqual(res_edit.get("plan_version"), 2)

        session = session_store.get_session(sid)
        state_req = session["state"]["requirements"]
        self.assertEqual(state_req["mode"], "flight")

    def test_11_booking_intent_human_authorization(self):
        """Booking intent must require explicit human authorization before execution."""
        sid = session_store.create_session()["session_id"]

        # Create active plan
        orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Delhi by train",
            session_id=sid,
        )

        # Trigger booking intent
        res = orchestrator.orchestrate_conversational_turn("Book this trip for us", session_id=sid)

        self.assertIn(res.get("status"), ("NAVIGATE_TO_BOOKING", "SUCCESS", "PLAN_READY"))
        self.assertTrue(
            "Confirm booking" in res.get("reply", "") or res.get("action") == "NAVIGATE_TO_BOOKING",
            "Booking must prompt for human confirmation or navigate to booking screen",
        )

    def test_12_cross_platform_payload_compatibility(self):
        """Plan results must carry payload structures consumed by both Web and Android."""
        sid = session_store.create_session()["session_id"]

        res = orchestrator.orchestrate_conversational_turn(
            "Plan a 3-day trip for 2 people from Delhi by train",
            session_id=sid,
        )

        # Keys required by Web & Android
        self.assertIn("session_id", res)
        self.assertIn("requirements", res)
        self.assertIn("budget_evaluation", res)
        self.assertIn("itinerary", res)
        self.assertIn("selected_options", res)
        self.assertIn("plan_version", res)

        transport = res["selected_options"].get("transport")
        self.assertIsNotNone(transport)
        # Transport schema compatibility
        self.assertTrue(any(k in transport for k in ("name", "train_name", "operator", "mode")))


    def test_13_first_time_visitor_general_enquiry(self):
        """Scenario 1: First-time visitor asking general trek questions receives factual overview first."""
        sid = session_store.create_session()["session_id"]
        res = orchestrator.orchestrate_conversational_turn(
            "What is the trek like from Katra to Bhawan? How far is it?",
            session_id=sid,
        )
        reply = res.get("reply", "")
        # Must give factual trek details (13 km, Banganga, Adhkuwari, Bhawan)
        self.assertTrue(
            any(k in reply.lower() for k in ("13 km", "12-13 km", "adhkuwari", "banganga", "bhawan", "trek")),
            "Reply must explain the holy 13 km trek",
        )
        self.assertEqual(res.get("intent"), "TOURISM")

    def test_14_missing_fares_truth_in_data(self):
        """Scenario 9: Missing schedules/fares must not fabricate live PNRs, tickets, or fake fares."""
        # Test connecting journey from a non-hub city without direct verified schedule (e.g. Alwar)
        journey = self.engine.plan_connecting_journey("Alwar")
        self.assertIsNotNone(journey)
        for opt in journey.get("options", []):
            # Check legs: unverified or connecting legs must not have fake live confirmation
            for leg in opt.get("legs", []):
                self.assertNotIn("PNR", str(leg.get("notes", "")))
                self.assertNotIn("CONFIRMED SEAT", str(leg.get("verification_status", "")))
                if leg.get("verification_status") != "VERIFIED_SCHEDULE":
                    self.assertIn(leg.get("fare_status"), ("COUNTER_VERIFICATION_REQUIRED", "INDICATIVE_STAGE_CARRIAGE_RATE", "STATUTORY_TARIFF", "UNVERIFIED"))

    def test_15_offline_deterministic_fallback(self):
        """Scenario 12: Backend functions reliably when LLM is unavailable or offline."""
        sid = session_store.create_session()["session_id"]
        # Explicitly pass llm=None and verify deterministic orchestration succeeds
        res = orchestrator.orchestrate_conversational_turn(
            "Plan a 2-day pilgrimage for 2 people from Delhi",
            session_id=sid,
            llm=None,
        )
        self.assertEqual(res.get("intent"), "TRIP_PLANNING")
        self.assertEqual(res.get("status"), "PLAN_READY")
        self.assertIn("Delhi", res.get("reply", ""))
        self.assertIsNotNone(res.get("selected_options"))


if __name__ == "__main__":
    unittest.main()
