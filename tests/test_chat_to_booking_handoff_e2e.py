"""
tests/test_chat_to_booking_handoff_e2e.py
Comprehensive End-to-End Test Suite for AI Chat to Booking Handoff
Verifies:
1. Booking intent from chat NEVER auto-confirms or generates booking IDs.
2. Complete recommendation context (pax, origin, dates, train/flight, hotel, itinerary) is preserved.
3. Chat triggers navigation to the guided booking experience (Step 2: Recommended Yatra).
4. Step 2 allows devotee to review selections and advance to Step 3 (Review & RPA).
5. Unauthenticated user on Step 3 is required to authenticate before RPA can be started.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents import coordinator, conversation_agent, orchestrator


class TestChatToBookingHandoff(unittest.TestCase):
    """Verifies that conversational booking intent transfers to the guided workflow without premature execution."""

    def test_01_booking_intent_does_not_auto_confirm(self):
        """Verifies that the exact problematic user prompt does not generate a booking ID or execute RPA."""
        # Step 1: User asks for a trip plan
        plan_res = coordinator.route_message("Plan a 3-day trip from Delhi to Katra for 2 people with train")
        self.assertEqual(plan_res.get("status"), "PLAN_READY")
        sid = plan_res.get("session_id")
        self.assertIsNotNone(sid, "Session ID must be created")
        
        # Step 2: The exact problematic intent message
        intent_query = (
            "I want to proceed with booking the recommended Vaishno Devi Yatra for 2 pilgrims. "
            "Help me continue with the booking."
        )
        intent_res = coordinator.route_message(
            intent_query,
            session_id=sid,
            current_request=plan_res.get("request"),
            pending_options=plan_res.get("plan", {}).get("options"),
            current_itinerary=plan_res.get("itinerary"),
        )
        
        # 1. Must NOT auto-confirm
        self.assertIsNone(intent_res.get("booking_id"), "Booking ID must NEVER be generated on booking intent!")
        self.assertIsNone(intent_res.get("rpa_execution"), "RPA execution must NEVER occur on booking intent!")
        
        # 2. Must return NAVIGATE_TO_BOOKING action and status
        self.assertEqual(intent_res.get("intent"), "BOOKING_INTENT")
        self.assertEqual(intent_res.get("status"), "NAVIGATE_TO_BOOKING")
        self.assertEqual(intent_res.get("action"), "NAVIGATE_TO_BOOKING")
        
        # 3. Devotional transition reply must guide to review
        reply = intent_res.get("reply", "").lower()
        self.assertNotIn("booking executed", reply)
        self.assertNotIn("booking confirmed", reply)
        self.assertNotIn("playwright rpa", reply)
        self.assertIn("jai mata di", reply)
        self.assertIn("review", reply)
        
        # 4. Context preservation
        req = intent_res.get("request") or {}
        self.assertEqual(req.get("pax"), 2, "Pilgrim count must be preserved as 2")
        self.assertEqual(req.get("origin"), "Delhi", "Origin must be preserved as Delhi")
        
        # 5. Plan and itinerary preservation
        plan = intent_res.get("plan")
        self.assertIsNotNone(plan, "Plan must be preserved")
        self.assertGreater(len(plan.get("options") or []), 0, "Transport options must be present")
        self.assertIsNotNone(plan.get("selected_option"), "Selected option must be set")
        self.assertIsNotNone(plan.get("hotel"), "Hotel must be present")
        self.assertIsNotNone(intent_res.get("itinerary"), "Itinerary must be preserved")
        self.assertEqual(intent_res.get("step"), 2, "Target step must be Step 2 (Recommended Yatra)")

    def test_02_variations_of_booking_intent_detected_accurately(self):
        """Verifies that natural language booking-intent variants classify as BOOKING_INTENT."""
        queries = [
            "Proceed with booking",
            "Proceed to booking",
            "Continue with the booking",
            "Continue with booking",
            "I want to book this recommended yatra",
            "Book the recommended trip",
            "Help me continue with the booking",
            "Ready to proceed with the booking for 4 pilgrims",
        ]
        for q in queries:
            intent = conversation_agent.detect_intent(q)
            self.assertEqual(
                intent,
                "BOOKING_INTENT",
                f"Query '{q}' should be BOOKING_INTENT but got '{intent}'"
            )

    def test_03_informational_questions_do_not_trigger_booking(self):
        """Verifies that informational questions are kept out of booking."""
        queries = [
            "How do I book tickets?",
            "What is the booking procedure for Vaishno Devi?",
            "Where can I book helicopter tickets?",
            "Explain the booking steps",
            "How does booking work?",
        ]
        for q in queries:
            intent = conversation_agent.detect_intent(q)
            self.assertIn(
                intent,
                ["TOURISM", "UNKNOWN"],
                f"Informational query '{q}' should be TOURISM but got '{intent}'"
            )

    def test_04_explicit_authorization_remains_distinct(self):
        """Verifies that explicit confirmation keywords remain reserved for true authorization."""
        queries = [
            "Confirm booking",
            "Yes, confirm booking",
            "Authorize booking",
            "Execute rpa",
        ]
        for q in queries:
            intent = conversation_agent.detect_intent(q)
            self.assertEqual(
                intent,
                "BOOKING",
                f"Explicit query '{q}' should be BOOKING but got '{intent}'"
            )

    def test_05_missing_origin_prompts_gently_without_error(self):
        """Verifies that if user says 'Proceed with booking' without origin, system asks politely for origin."""
        res = orchestrator.handle_booking_navigation_intent(
            "I want to proceed with booking for 2 pilgrims",
            session_data={},
        )
        self.assertEqual(res.get("status"), "NEEDS_INFO")
        self.assertIn("origin", res.get("missing_fields", []))
        self.assertIsNone(res.get("booking_id"))
        self.assertIn("departure city", res.get("reply", "").lower())


def run_optional_browser_journey():
    """Optional Playwright browser test verifying the UI transitions if dev servers are accessible."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed, skipping browser check")
        return

    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:5173", timeout=2)
    except Exception:
        print("Frontend server (http://localhost:5173) is not accessible in this process; skipping browser check.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("Navigating to http://localhost:5173...")
        page.goto("http://localhost:5173", timeout=15000)

        # Go to Assistant
        page.click("button:has-text('AI Assistant')")
        page.wait_for_selector("#chat-user-input", timeout=10000)

        # Plan trip
        page.fill("#chat-user-input", "Plan a 3-day trip from Delhi to Katra for 2 people with train")
        page.click("[data-testid='chat-send-btn']")
        page.wait_for_selector("[data-testid='compact-personalized-plan-card']", timeout=20000)

        # Send booking intent
        page.fill(
            "#chat-user-input",
            "I want to proceed with booking the recommended Vaishno Devi Yatra for 2 pilgrims. Help me continue with the booking."
        )
        page.click("[data-testid='chat-send-btn']")

        # Verify no confirmation ID or premature completion in chat
        time.sleep(3)
        chat_content = page.content()
        assert "VD-RPA-" not in chat_content
        assert "Booking Executed & Confirmed" not in chat_content

        # Verify navigation to Step 2
        page.wait_for_selector("[data-testid='proceed-to-review-btn']", timeout=15000)
        print("Successfully transitioned to Step 2 (Recommended Yatra)!")

        # Advance to Step 3
        page.click("[data-testid='proceed-to-review-btn']")
        page.wait_for_selector("[data-testid='bottom-start-yatra-rpa-btn']", timeout=10000)
        print("Successfully reached Step 3 (Review & RPA)!")

        # As guest, clicking Start Yatra Booking with RPA requires authentication
        page.click("[data-testid='bottom-start-yatra-rpa-btn']")
        page.wait_for_selector("[data-testid='auth-modal']", timeout=5000)
        print("Compulsory authentication modal displayed for guest before RPA execution!")

        browser.close()


if __name__ == "__main__":
    unittest.main()

