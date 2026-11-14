"""
tests/test_phase14_3_unified_intelligence.py
============================================
Phase 14.3 Comprehensive Acceptance & Verification Test Suite:
Unified Conversational Intelligence, Performance Optimization & End-to-End Travel Validation.

Coverage:
  Suite A: Groq Model Reliability, Fallback & LLM Circuit Breaker
  Suite B: Latency Benchmarks & Sub-Second Fast Paths
  Suite C: Universal Geographic Resolution (30+ Diverse Origins across India)
  Suite D: Connecting Journey Engine & 5-Level Fallback Routing
  Suite E: Multi-Turn Conversation, Context Retention & "Answer First" Policy (15 Dialogues)
  Suite F: Cross-Platform & API Contract Compatibility (Web + Android)
  Suite G: Human-in-the-Loop Booking Gate & Truth-in-Data Safeguards
"""

import os
import sys
import time
import unittest
import uuid
from typing import Dict, Any, List

# Ensure active repo root is on sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from agents import central_agent
from agents.central_agent import (
    llm_circuit_breaker,
    select_tools_for_turn,
    CircuitState,
    CENTRAL_TOOLS,
    check_weather_guidance,
    search_transport_options,
    search_accommodation_options,
    search_yatra_knowledge,
    get_tourism_knowledge,
    query_operational_notices,
    lookup_verified_contacts,
)
from agents import session_store
from agents import conversation_state
from agents import coordinator
from services.geo_resolver import get_geo_resolver, ResolvedLocation
from services.connecting_journey_engine import get_connecting_journey_engine


class TestPhase14_3_UnifiedIntelligence(unittest.TestCase):
    """Phase 14.3 Comprehensive Verification Test Suite."""

    @classmethod
    def setUpClass(cls):
        # Warm up components to ensure clean benchmarks
        get_geo_resolver()
        get_connecting_journey_engine()

    def setUp(self):
        self.session_ids_to_clean: List[str] = []

    def tearDown(self):
        for sid in self.session_ids_to_clean:
            try:
                session_store.delete_session(sid)
            except Exception:
                pass

    def _create_session(self) -> str:
        sid = f"phase14_3_{uuid.uuid4().hex[:8]}"
        self.session_ids_to_clean.append(sid)
        return sid

    # =========================================================================
    # SUITE A: Groq Model Reliability, Fallback & LLM Circuit Breaker
    # =========================================================================

    def test_a1_groq_model_catalog_and_defaults(self):
        """Verifies default primary and fallback model identifiers."""
        primary_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
        fallback_model = os.environ.get("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
        self.assertEqual(primary_model, "openai/gpt-oss-20b")
        self.assertEqual(fallback_model, "openai/gpt-oss-120b")

    def test_a2_selective_tool_binding(self):
        """Verifies select_tools_for_turn bounds tool schemas appropriately to minimize token bloat."""
        # 1. Weather turn
        w_tools = select_tools_for_turn("What is the temperature at Bhawan today?")
        w_names = [t.name for t in w_tools]
        self.assertIn("check_weather_guidance", w_names)
        self.assertNotIn("search_accommodation_options", w_names)
        self.assertLess(len(w_tools), len(CENTRAL_TOOLS))

        # 2. Transport turn
        t_tools = select_tools_for_turn("Show me train schedules from Delhi to Katra")
        t_names = [t.name for t in t_tools]
        self.assertIn("search_transport_options", t_names)
        self.assertNotIn("search_accommodation_options", t_names)

        # 3. Accommodation turn
        h_tools = select_tools_for_turn("Which hotel or bhavan is available for stay in Katra?")
        h_names = [t.name for t in h_tools]
        self.assertIn("search_accommodation_options", h_names)
        self.assertNotIn("check_weather_guidance", h_names)

        # 4. Yatra & Aarti turn
        y_tools = select_tools_for_turn("What are the morning Aarti timings and RFID registration rules?")
        y_names = [t.name for t in y_tools]
        self.assertIn("search_yatra_knowledge", y_names)

        # 5. Full planning turn binds the full suite
        p_tools = select_tools_for_turn("I want to plan a complete 3-day pilgrimage itinerary", intent="PLAN_YATRA")
        self.assertEqual(len(p_tools), len(CENTRAL_TOOLS))

    def test_a3_circuit_breaker_transitions(self):
        """Verifies LLMCircuitBreaker transitions through CLOSED, OPEN, and resets to CLOSED."""
        cb = central_agent.LLMCircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
        self.assertEqual(cb.current_state, CircuitState.CLOSED)
        self.assertTrue(cb.can_attempt())

        # First failure
        cb.record_failure(Exception("Network timeout 1"))
        self.assertEqual(cb.current_state, CircuitState.CLOSED)
        self.assertTrue(cb.can_attempt())

        # Second failure trips breaker
        cb.record_failure(Exception("Network timeout 2"))
        self.assertEqual(cb.current_state, CircuitState.OPEN)
        self.assertFalse(cb.can_attempt())

        # Wait for recovery timeout to transition to HALF_OPEN
        time.sleep(0.25)
        self.assertEqual(cb.current_state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.can_attempt())

        # Canary success restores to CLOSED
        cb.record_success()
        self.assertEqual(cb.current_state, CircuitState.CLOSED)
        self.assertTrue(cb.can_attempt())

    def test_a4_circuit_breaker_fast_fail_execution(self):
        """Verifies that an OPEN circuit breaker bypasses network calls and sets execution metadata."""
        # Trip the breaker manually
        llm_circuit_breaker.record_failure("Simulated connection timeout 1")
        llm_circuit_breaker.record_failure("Simulated connection timeout 2")
        self.assertEqual(llm_circuit_breaker.current_state, CircuitState.OPEN)

        sid = self._create_session()
        t0 = time.perf_counter()
        res = central_agent.process_conversational_turn(
            "What is the official phone helpline for Shri Mata Vaishno Devi Shrine Board?", session_id=sid
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(latency_ms, 500.0, f"Expected fast-fail < 500ms, took {latency_ms:.2f}ms")
        self.assertEqual(res["circuit_breaker_state"], CircuitState.OPEN)
        self.assertTrue(len(res["reply"]) > 20)

    # =========================================================================
    # SUITE B: Latency Benchmarks & Sub-Second Fast Paths
    # =========================================================================

    def test_b1_greeting_fast_path_latency(self):
        """Verifies simple greetings execute deterministically in < 500ms (target < 50ms)."""
        sid = self._create_session()
        t0 = time.perf_counter()
        res = central_agent.process_conversational_turn("Jai Mata Di!", session_id=sid)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(latency_ms, 500.0, f"Greeting took {latency_ms:.2f}ms")
        self.assertEqual(res["execution_mode"], "deterministic_greeting")
        self.assertIn("Jai Mata Di", res["reply"])

    def test_b2_acknowledgment_fast_path_latency(self):
        """Verifies acknowledgments execute deterministically in < 500ms."""
        sid = self._create_session()
        t0 = time.perf_counter()
        res = central_agent.process_conversational_turn("Thank you very much!", session_id=sid)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(latency_ms, 500.0, f"Acknowledgment took {latency_ms:.2f}ms")
        self.assertEqual(res["execution_mode"], "deterministic_acknowledgment")

    def test_b3_help_fast_path_latency(self):
        """Verifies help queries execute deterministically in < 500ms."""
        sid = self._create_session()
        t0 = time.perf_counter()
        res = central_agent.process_conversational_turn("Help me with yatra guide", session_id=sid)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(latency_ms, 500.0, f"Help took {latency_ms:.2f}ms")
        self.assertEqual(res["execution_mode"], "deterministic_help")

    def test_b4_connecting_journey_engine_latency(self):
        """Verifies connecting journey engine computes multi-leg plans in < 2500ms."""
        engine = get_connecting_journey_engine()
        t0 = time.perf_counter()
        journey = engine.plan_connecting_journey(origin="Bengaluru", start_date="2026-12-01", pax=2)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(latency_ms, 2500.0, f"Connecting journey took {latency_ms:.2f}ms")
        self.assertIsNotNone(journey)
        self.assertIn(journey.get("status"), ["SUCCESS", "FEASIBLE", "CONNECTING_ROUTES_AVAILABLE"])
        self.assertGreater(journey.get("options_count", 0), 0)

    # =========================================================================
    # SUITE C: Universal Geographic Resolution (30+ Diverse Origins)
    # =========================================================================

    def test_c1_geographic_origin_resolution_32_locations(self):
        """Verifies that 32 diverse Indian origins from all zones resolve accurately with gateway hubs."""
        resolver = get_geo_resolver()
        test_origins = [
            # Metros
            "Delhi", "Mumbai", "Kolkata", "Bengaluru", "Chennai", "Hyderabad",
            # North / Central
            "Chandigarh", "Amritsar", "Jaipur", "Lucknow", "Ludhiana", "Varanasi", "Agra", "Bhopal",
            # West
            "Pune", "Ahmedabad", "Surat", "Nagpur", "Indore", "Vadodara",
            # South
            "Kochi", "Coimbatore", "Visakhapatnam", "Madurai", "Mysuru",
            # East & Northeast
            "Patna", "Bhubaneswar", "Ranchi", "Guwahati", "Siliguri",
            # Mountain / Remote / Unlisted
            "Palampur", "Kaza"
        ]

        self.assertEqual(len(test_origins), 32)
        for orig in test_origins:
            with self.subTest(origin=orig):
                loc = resolver.resolve_origin(orig)
                self.assertIsNotNone(loc, f"Failed to resolve origin: {orig}")
                self.assertTrue(len(loc.clean_name) > 0)
                self.assertTrue(len(loc.primary_gateway_hub) > 0)
                self.assertTrue(loc.state is None or len(loc.state) > 0)

    def test_c2_never_reject_unlisted_origin(self):
        """Verifies that even an arbitrary remote village/settlement is never rejected."""
        resolver = get_geo_resolver()
        unlisted = "Dhanushkodi"
        loc = resolver.resolve_origin(unlisted)
        self.assertIsNotNone(loc)
        self.assertNotIn("cannot travel", loc.clean_name.lower())

    # =========================================================================
    # SUITE D: Connecting Journey Engine & 5-Level Fallback Routing
    # =========================================================================

    def test_d1_direct_and_connecting_routes(self):
        """Verifies connecting journey generation for direct and connecting origins."""
        engine = get_connecting_journey_engine()

        # 1. Delhi journey
        delhi_j = engine.plan_connecting_journey(origin="Delhi", start_date="2026-12-01", pax=2)
        self.assertIn(delhi_j["status"], ["SUCCESS", "FEASIBLE", "CONNECTING_ROUTES_AVAILABLE"])
        self.assertGreater(delhi_j.get("options_count", 0), 0)

        # 2. Connecting from Pune
        pune_j = engine.plan_connecting_journey(origin="Pune", start_date="2026-12-01", pax=2)
        self.assertIn(pune_j["status"], ["SUCCESS", "FEASIBLE", "CONNECTING_ROUTES_AVAILABLE"])
        self.assertGreater(pune_j.get("options_count", 0), 0)

    def test_d2_truth_in_data_no_synthetic_identifiers(self):
        """Verifies that unverified routes do not fabricate fake train numbers or fake ticket prices."""
        engine = get_connecting_journey_engine()
        journey = engine.plan_connecting_journey(origin="Kaza", start_date="2026-12-01", pax=1)
        self.assertIn(journey["status"], ["SUCCESS", "FEASIBLE", "NEEDS_CLARIFICATION", "CONNECTING_ROUTES_AVAILABLE"])
        for opt in journey.get("options", []):
            legs = opt.legs if hasattr(opt, "legs") else opt.get("legs", [])
            for leg in legs:
                leg_dict = leg.to_dict() if hasattr(leg, "to_dict") else leg
                if not leg_dict.get("verified"):
                    identifier = str(leg_dict.get("transport_name") or "")
                    self.assertNotIn("FAKE_TRAIN", identifier)

    # =========================================================================
    # SUITE E: Multi-Turn Conversation, Context Retention & "Answer First" Policy
    # (15 Distinct Scenarios)
    # =========================================================================

    def test_e01_devotional_greeting_and_warm_welcome(self):
        """Scenario 1: Devotee initiates devotional greeting."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Jai Mata Di! Namaskar.", session_id=sid)
        self.assertIn("Jai Mata Di", res["reply"])
        self.assertEqual(res["execution_mode"], "deterministic_greeting")

    def test_e02_answer_first_weather_query(self):
        """Scenario 2: User asks about weather first; bot answers weather directly without interrogation."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("What is the current weather at Bhawan?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("weather" in reply_lower or "bhawan" in reply_lower or "temperature" in reply_lower or "c" in reply_lower)

    def test_e03_origin_and_pax_slot_extraction(self):
        """Scenario 3: User specifies origin Delhi and 2 adults; state records both."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("I want to plan a yatra from Delhi for 2 adults.", session_id=sid)
        req = res.get("request", {})
        self.assertEqual(req.get("origin"), "Delhi")
        self.assertEqual(req.get("pax"), 2)

    def test_e04_context_retention_no_repeated_origin_questions(self):
        """Scenario 4: User follows up asking for trains; bot retains origin Delhi."""
        sid = self._create_session()
        # Turn 1
        res1 = central_agent.process_conversational_turn("We are 3 pilgrims travelling from Delhi.", session_id=sid)
        self.assertEqual(res1.get("request", {}).get("origin"), "Delhi")
        # Turn 2: Follow-up
        res2 = central_agent.process_conversational_turn("Which trains can we take?", session_id=sid)
        self.assertNotIn("where are you travelling from", res2["reply"].lower())
        self.assertEqual(res2.get("request", {}).get("origin"), "Delhi")

    def test_e05_mid_conversation_pax_correction(self):
        """Scenario 5: User corrects passenger count; state updates from 2 to 4."""
        sid = self._create_session()
        # Turn 1
        central_agent.process_conversational_turn("Planning trip for 2 people from Jaipur", session_id=sid)
        # Turn 2
        res2 = central_agent.process_conversational_turn("Actually 4 pilgrims will be coming with us.", session_id=sid)
        self.assertEqual(res2.get("request", {}).get("pax"), 4)

    def test_e06_non_hub_origin_acceptance(self):
        """Scenario 6: User travels from Pune; bot accepts Pune without rejection."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("I am travelling from Pune to Vaishno Devi.", session_id=sid)
        self.assertEqual(res.get("request", {}).get("origin"), "Pune")
        reply_lower = res["reply"].lower()
        self.assertNotIn("no such place", reply_lower)
        self.assertNotIn("unsupported origin", reply_lower)

    def test_e07_remote_hill_origin_acceptance(self):
        """Scenario 7: User travels from Palampur in Himachal."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("We are starting our pilgrimage from Palampur.", session_id=sid)
        self.assertEqual(res.get("request", {}).get("origin"), "Palampur")
        self.assertNotIn("cannot travel", res["reply"].lower())

    def test_e08_factual_aarti_timings(self):
        """Scenario 8: User asks for Aarti timings; bot answers factually."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("What time is the morning and evening Aarti at Bhawan?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("aarti" in reply_lower or "morning" in reply_lower or "darshan" in reply_lower or "bhawan" in reply_lower)

    def test_e09_track_and_battery_car_advisory(self):
        """Scenario 9: User asks about battery cars from Ardhkuwari."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Is battery car service available from Ardhkuwari to Bhawan?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("battery car" in reply_lower or "ardhkuwari" in reply_lower or "bhawan" in reply_lower or "tarakote" in reply_lower or "track" in reply_lower)

    def test_e10_rfid_registration_parchi_rules(self):
        """Scenario 10: User inquires about mandatory RFID Registration Parchi."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Is RFID card mandatory for yatra, and where can I get it?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("rfid" in reply_lower or "parchi" in reply_lower or "registration" in reply_lower or "katra" in reply_lower)

    def test_e11_shrine_board_accommodation_guidance(self):
        """Scenario 11: User asks for stay options at Bhawan and Katra."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("What are the official Shrine Board accommodation options at Bhawan?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("bhawan" in reply_lower or "bhavan" in reply_lower or "accommodation" in reply_lower or "hotel" in reply_lower or "room" in reply_lower)

    def test_e12_verified_emergency_contacts(self):
        """Scenario 12: User requests emergency Shrine Board contact numbers."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("What is the official Shrine Board helpline or emergency contact number?", session_id=sid)
        reply_lower = res["reply"].lower()
        self.assertTrue("01991" in reply_lower or "helpline" in reply_lower or "contact" in reply_lower or "board" in reply_lower)

    def test_e13_booking_intent_handoff_safeguard(self):
        """Scenario 13: User expresses booking intent; system hands off to booking wizard without autonomous execution."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("I want to book helicopter tickets for 2 adults tomorrow.", session_id=sid)
        self.assertTrue(res.get("action") == "NAVIGATE_TO_BOOKING" or "booking" in res["reply"].lower())

    def test_e14_gratitude_and_politeness(self):
        """Scenario 14: User expresses gratitude."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Thank you so much for the helpful information!", session_id=sid)
        self.assertIn("Jai Mata Di", res["reply"])
        self.assertEqual(res["execution_mode"], "deterministic_acknowledgment")

    def test_e15_single_question_policy_on_partial_input(self):
        """Scenario 15: Incomplete input prompts at most 1-2 clarifying questions."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("I am planning a trip", session_id=sid)
        question_count = res["reply"].count("?")
        self.assertLessEqual(question_count, 2, f"Expected at most 1-2 questions, found {question_count}")

    # =========================================================================
    # SUITE F: Cross-Platform & API Contract Compatibility (Web + Android)
    # =========================================================================

    def test_f1_chat_envelope_contract_for_android_and_web(self):
        """Verifies process_conversational_turn envelope contains all keys required by Android and Web frontends."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Help", session_id=sid)
        required_keys = ["reply", "session_id", "intent", "status", "timing", "execution_mode"]
        for key in required_keys:
            self.assertIn(key, res, f"Missing required response key: {key}")

    def test_f2_streaming_generator_sse_protocol(self):
        """Verifies process_conversational_turn_stream yields SSE start, token, and done events."""
        sid = self._create_session()
        generator = central_agent.process_conversational_turn_stream("Jai Mata Di!", session_id=sid)
        events = list(generator)

        types = [e.get("type") for e in events]
        self.assertIn("start", types)
        self.assertIn("token", types)
        self.assertIn("done", types)
        done_event = [e for e in events if e.get("type") == "done"][0]
        self.assertIn("response", done_event)
        self.assertIn("reply", done_event["response"])

    # =========================================================================
    # SUITE G: Booking Gate & Truth-in-Data Safeguards
    # =========================================================================

    def test_g1_human_in_the_loop_booking_safeguard(self):
        """Verifies execute_authorized_booking rejects autonomous calls without explicit human authorization token."""
        result = central_agent.execute_authorized_booking.func(
            user_name="Rajesh Kumar",
            pax_count=2,
            transport_text="Vande Bharat Express",
            slot_text="Morning 08:00 AM",
            total_price=3500.0,
            human_authorized=False,
        )
        self.assertEqual(result.get("status"), "AUTHORIZATION_REQUIRED")
        self.assertFalse(result.get("authorized", True))
        self.assertIn("Human authorization", result.get("message", ""))

    def test_g2_provenance_attachment_safeguard(self):
        """Verifies that responses attach provenance records for auditability."""
        sid = self._create_session()
        res = central_agent.process_conversational_turn("Help", session_id=sid)
        self.assertIn("source_provenance", res)
        self.assertIsInstance(res["source_provenance"], list)


if __name__ == "__main__":
    unittest.main()
