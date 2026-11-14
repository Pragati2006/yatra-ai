"""
tests/test_phase13_3_conversational_intelligence.py
===================================================
Phase 13.3 Test Suite: Conversational Intelligence, Context Retention & Travel Coverage.

Verifies:
1. Origin and pilgrim count extracted from one message ("...from Delhi for two adults").
2. Destination retained across multiple messages.
3. Pilgrim count retained across multiple messages.
4. Origin correction ("Change departure city to Chandigarh").
5. Destination correction ("Actually let's visit Patnitop").
6. Follow-up questions using previous context.
7. Different conversation IDs maintain isolated state.
8. Different users maintain isolated state.
9. Missing information is requested only when necessary (stops repeated questions).
10. Arbitrary Indian city accepted as origin (e.g. Pune, Jaipur, Lucknow, Guwahati).
11. Unsupported transport route reported honestly without fabricated schedules.
12. Unknown fare never presented as verified.
13. Transport preference changed in a follow-up message ("What if we travel by train instead?").
14. Booking authorization still strictly enforced (no automated confirmation).
15. Android and web clients use the same backend conversation behaviour.
"""

import os
import sys
import unittest
import uuid
from typing import Dict, Any

# Ensure project root is on sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from agents import coordinator, session_store, conversation_state, conversation_agent, central_agent
from backend.main import app
from fastapi.testclient import TestClient


class TestPhase13ConversationalIntelligence(unittest.TestCase):
    def setUp(self):
        """Prepare fresh session IDs for test isolation."""
        self.session_a = f"test_conv_a_{uuid.uuid4().hex[:8]}"
        self.session_b = f"test_conv_b_{uuid.uuid4().hex[:8]}"

    def test_01_origin_and_pilgrim_count_extracted_from_single_message(self):
        """1. User: 'I want to plan a Vaishno Devi pilgrimage from Delhi for two adults.'
        Should extract Origin=Delhi, Destination=Katra, Pax=2 without asking for them again."""
        msg = "I want to plan a Vaishno Devi pilgrimage from Delhi for two adults."
        res = coordinator.route_message(msg, session_id=self.session_a)

        self.assertIsNotNone(res)
        req = res.get("request") or res.get("requirements") or {}
        self.assertEqual(req.get("origin"), "Delhi", "Expected origin to be Delhi")
        self.assertEqual(req.get("pax"), 2, "Expected pax to be 2 for 'two adults'")
        self.assertEqual(req.get("destination"), "Katra", "Expected default destination to be Katra")

        # Crucial check: reply must NOT ask for origin or pilgrim count
        reply_lower = res.get("reply", "").lower()
        self.assertNotIn("which city", reply_lower, "Assistant must not ask for departure city again")
        self.assertNotIn("where are you travelling from", reply_lower, "Assistant must not ask origin again")
        self.assertNotIn("how many pilgrims", reply_lower, "Assistant must not ask for pilgrim count again")
        # Should either confirm plan ready or prompt for dates/duration
        self.assertTrue(
            "date" in reply_lower or "duration" in reply_lower or "trip" in reply_lower or "plan" in reply_lower or res.get("status") in ("PLAN_READY", "NEEDS_INFO"),
            f"Expected prompt for dates/duration or plan, got: {res.get('reply')}"
        )

    def test_02_destination_retained_across_multiple_messages(self):
        """2. Destination retained across multiple turns even when subsequent messages don't mention it."""
        # Turn 1:
        res1 = coordinator.route_message("I am planning a trip to Patnitop.", session_id=self.session_a)
        req1 = res1.get("request") or {}
        self.assertEqual(req1.get("destination"), "Patnitop")

        # Turn 2: User provides origin only
        res2 = coordinator.route_message("We will travel from Delhi.", session_id=self.session_a)
        req2 = res2.get("request") or {}
        self.assertEqual(req2.get("destination"), "Patnitop", "Destination Patnitop must be retained in Turn 2")
        self.assertEqual(req2.get("origin"), "Delhi", "Origin Delhi must be recorded")

        # Turn 3: User provides pax only
        res3 = coordinator.route_message("Three pilgrims.", session_id=self.session_a)
        req3 = res3.get("request") or {}
        self.assertEqual(req3.get("destination"), "Patnitop", "Destination Patnitop must be retained in Turn 3")
        self.assertEqual(req3.get("pax"), 3, "Pax 3 must be recorded")

    def test_03_pilgrim_count_retained_across_multiple_messages(self):
        """3. Pilgrim count retained across multiple turns."""
        # Turn 1:
        res1 = coordinator.route_message("Travelling with 4 pilgrims from Delhi.", session_id=self.session_a)
        req1 = res1.get("request") or {}
        self.assertEqual(req1.get("pax"), 4)

        # Turn 2: Contextual query
        res2 = coordinator.route_message("What is the weather like at Katra?", session_id=self.session_a)
        req2 = res2.get("request") or {}
        self.assertEqual(req2.get("pax"), 4, "Pax 4 must be retained after weather question")
        self.assertEqual(req2.get("origin"), "Delhi", "Origin Delhi must be retained")

    def test_04_origin_correction(self):
        """4. User corrects origin in a follow-up message."""
        # Turn 1:
        coordinator.route_message("Plan a trip from Delhi for 2 people.", session_id=self.session_a)

        # Turn 2: User explicitly corrects origin
        res2 = coordinator.route_message("Change my departure city to Chandigarh.", session_id=self.session_a)
        req2 = res2.get("request") or {}
        self.assertEqual(req2.get("origin"), "Chandigarh", "Origin should be updated to Chandigarh")
        self.assertEqual(req2.get("pax"), 2, "Pax count 2 should be preserved during origin correction")

    def test_05_destination_correction(self):
        """5. User corrects destination in a follow-up message."""
        # Turn 1: Default Katra
        coordinator.route_message("We are travelling from Delhi for 3 people.", session_id=self.session_a)

        # Turn 2: User changes destination
        res2 = coordinator.route_message("Actually change destination to Shiv Khori.", session_id=self.session_a)
        req2 = res2.get("request") or {}
        self.assertEqual(req2.get("destination"), "Shiv Khori")
        self.assertEqual(req2.get("origin"), "Delhi", "Origin Delhi must be preserved during destination change")
        self.assertEqual(req2.get("pax"), 3, "Pax 3 must be preserved during destination change")

    def test_06_followup_questions_using_previous_context(self):
        """6. Follow-up query uses accumulated context without re-prompting."""
        # Turn 1:
        coordinator.route_message("Travelling from Mumbai for two adults for 4 days.", session_id=self.session_a)

        # Turn 2: Follow-up question about accommodation
        res2 = coordinator.route_message("Find accommodation near Katra.", session_id=self.session_a)
        self.assertIsNotNone(res2.get("reply"))
        reply_lower = res2.get("reply", "").lower()
        self.assertNotIn("which city will you be travelling from", reply_lower)
        self.assertNotIn("how many pilgrims", reply_lower)

    def test_07_different_conversation_ids_maintain_isolated_state(self):
        """7. Sessions A and B remain strictly isolated."""
        coordinator.route_message("We are 2 pilgrims from Delhi.", session_id=self.session_a)
        coordinator.route_message("We are 5 pilgrims from Mumbai.", session_id=self.session_b)

        sess_a = session_store.get_session(self.session_a)
        sess_b = session_store.get_session(self.session_b)

        self.assertEqual(sess_a["state"]["requirements"]["origin"], "Delhi")
        self.assertEqual(sess_a["state"]["requirements"]["pax"], 2)

        self.assertEqual(sess_b["state"]["requirements"]["origin"], "Mumbai")
        self.assertEqual(sess_b["state"]["requirements"]["pax"], 5)

    def test_08_different_users_maintain_isolated_state(self):
        """8. Authenticated user sessions remain isolated in session store."""
        sess_u1 = session_store.create_session(user_id="user_alpha_123", initial_state={"requirements": {"origin": "Ahmedabad", "pax": 3}})
        sess_u2 = session_store.create_session(user_id="user_beta_456", initial_state={"requirements": {"origin": "Kolkata", "pax": 6}})

        retrieved_1 = session_store.get_session(sess_u1["session_id"])
        retrieved_2 = session_store.get_session(sess_u2["session_id"])

        self.assertEqual(retrieved_1["user_id"], "user_alpha_123")
        self.assertEqual(retrieved_1["state"]["requirements"]["origin"], "Ahmedabad")
        self.assertEqual(retrieved_2["user_id"], "user_beta_456")
        self.assertEqual(retrieved_2["state"]["requirements"]["origin"], "Kolkata")

    def test_09_missing_information_requested_only_when_necessary(self):
        """9. Missing slot logic: Gradual input asks ONLY for what is genuinely missing."""
        # Step 1: User gives only destination intent
        res1 = coordinator.route_message("I want to visit Vaishno Devi.", session_id=self.session_a)
        rep1 = res1.get("reply", "").lower()
        self.assertTrue("which city" in rep1 or "travelling from" in rep1, "Should ask for origin when origin is missing")

        # Step 2: User provides origin
        res2 = coordinator.route_message("Delhi.", session_id=self.session_a)
        rep2 = res2.get("reply", "").lower()
        self.assertNotIn("which city", rep2, "Should NOT ask for city again")
        self.assertTrue("how many pilgrims" in rep2 or "pilgrim" in rep2, "Should ask for pax count next")

        # Step 3: User provides pax
        res3 = coordinator.route_message("Two adults.", session_id=self.session_a)
        rep3 = res3.get("reply", "").lower()
        self.assertNotIn("which city", rep3, "Should NOT ask for city")
        self.assertNotIn("how many pilgrims", rep3, "Should NOT ask for pax")
        self.assertTrue("date" in rep3 or "duration" in rep3, "Should ask for travel date or duration")

    def test_10_arbitrary_indian_city_accepted_as_origin(self):
        """10. User specifies an origin outside the 8 static CSV hubs (e.g. Pune, Jaipur, Lucknow, Patna)."""
        res = coordinator.route_message("I am travelling from Pune with 3 pilgrims.", session_id=self.session_a)
        req = res.get("request") or {}
        self.assertEqual(req.get("origin"), "Pune", "Should accept Pune as valid geographical origin")
        self.assertEqual(req.get("pax"), 3)

        # System should not crash or produce an empty unhandled response
        self.assertIsNotNone(res.get("reply"))
        self.assertTrue(len(res["reply"]) > 20)

    def test_11_unsupported_transport_route_reported_honestly(self):
        """11. When an origin lacks direct static schedules, connecting guidance is provided without fake flights."""
        guidance = conversation_state.get_transit_guidance_for_origin("Nagpur")
        self.assertFalse(guidance["has_verified_direct"])
        self.assertIn("New Delhi", guidance["guidance_text"])

    def test_12_unknown_fare_never_presented_as_verified(self):
        """12. Verified hub schedules have prices; unverified transit legs report unknown/self-arranged."""
        guidance = conversation_state.get_transit_guidance_for_origin("Guwahati")
        self.assertFalse(guidance["has_verified_direct"])
        # Guidance must not contain fabricated fares or flight ticket prices
        self.assertNotIn("₹1650", guidance["guidance_text"])
        self.assertNotIn("₹1200", guidance["guidance_text"])

    def test_13_transport_preference_changed_in_followup(self):
        """13. 'What if we travel by train instead?' updates mode and retains other details."""
        # Turn 1:
        coordinator.route_message("Travelling from Delhi for 2 adults for 4 days by flight.", session_id=self.session_a)

        # Turn 2: Switch to train
        res2 = coordinator.route_message("What if we travel by train instead?", session_id=self.session_a)
        req2 = res2.get("request") or {}
        self.assertEqual(req2.get("mode"), "train", "Mode should be updated to train")
        self.assertEqual(req2.get("origin"), "Delhi", "Origin Delhi should remain intact")
        self.assertEqual(req2.get("pax"), 2, "Pax count 2 should remain intact")

    def test_14_booking_authorization_still_enforced(self):
        """14. Booking confirmation requires explicit human authorization, never executed automatically."""
        # User says book option 1 without prior human authorization checkbox
        res = coordinator.route_message("Book option 1", session_id=self.session_a)
        self.assertEqual(res.get("intent"), "BOOKING")
        # Ensure status is not CONFIRMED without human authorization
        self.assertNotEqual(res.get("status"), "CONFIRMED", "Must not autonomously confirm booking")
        self.assertTrue(
            "authoriz" in res.get("reply", "").lower() or "confirm" in res.get("reply", "").lower() or res.get("status") == "AWAITING_AUTHORIZATION",
            f"Expected authorization prompt, got: {res.get('reply')}"
        )

        # User expresses navigation intent
        res_intent = coordinator.route_message("Continue with the booking process", session_id=self.session_a)
        self.assertEqual(res_intent.get("intent"), "BOOKING_INTENT")
        self.assertNotEqual(res_intent.get("status"), "CONFIRMED")

    def test_15_android_and_web_clients_use_same_backend_endpoint(self):
        """15. Both Android and Web clients hit /api/chat with session_id and receive identical structure."""
        from backend.main import chat, ChatRequest

        req_web = ChatRequest(
            message="Travelling from Delhi for 2 adults for 4 days.",
            session_id=self.session_a,
        )
        data_web = chat(req_web)
        self.assertIn("reply", data_web)
        self.assertIn("session_id", data_web)
        self.assertEqual(data_web["session_id"], self.session_a)

        # Android client payload with session_id
        req_android = ChatRequest(
            message="What is the weather at Bhawan?",
            session_id=self.session_a,
        )
        data_android = chat(req_android)
        self.assertIn("reply", data_android)
        self.assertEqual(data_android["session_id"], self.session_a)
        # Context was preserved
        self.assertEqual(data_android.get("request", {}).get("origin"), "Delhi")
        self.assertEqual(data_android.get("request", {}).get("pax"), 2)


if __name__ == "__main__":
    unittest.main()
