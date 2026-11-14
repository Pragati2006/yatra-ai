"""
Phase 14.4 — Real-World Conversation, End-to-End Performance & Intelligence Acceptance Audit
=============================================================================
Test suite: 30+ realistic traveller scenarios across 15 suites.

Verification classifications used:
  ACTUALLY_EXECUTED   — The code path runs fully in this test
  TESTED_WITH_MOCK    — Sandboxed; LLM calls fail; deterministic fallback active
  STATICALLY_INSPECTED — Verified by reading source, not by running
  REPORTED_BY_EXISTING — Covered by an earlier test suite
  NOT_VERIFIED        — Sandboxed env prevents full verification

NOTE: In the sandbox environment Groq API calls ALWAYS fail with
"Connection error." because the sandbox has no outbound network.
Every test that exercises the LLM path will trigger the circuit breaker.
Tests must therefore verify the DETERMINISTIC FALLBACK path, not live LLM.
"""

import sys
import io
import os
import uuid
import time
import unittest

# Force UTF-8 so emoji replies do not cause UnicodeEncodeError on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ------------------------------------------------------------------
# Ensure repo root is importable
# ------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from agents.central_agent import (
    process_conversational_turn,
    process_conversational_turn_stream,
    llm_circuit_breaker,
    CircuitState,
    select_tools_for_turn,
    is_simple_acknowledgment,
    is_help_query,
    is_accommodation_info_query,
    _handle_deterministic_accommodation_turn,
    execute_authorized_booking,
    CENTRAL_TOOLS,
)
from services.geo_resolver import get_geo_resolver
from services.connecting_journey_engine import get_connecting_journey_engine

GEO = get_geo_resolver()
JE = get_connecting_journey_engine()

REQUIRED_RESPONSE_KEYS = [
    "reply", "session_id", "intent", "status", "timing",
    "execution_mode", "circuit_breaker_state",
]


def _sid():
    """Return a fresh unique session-id."""
    return str(uuid.uuid4())


# ===========================================================================
# Suite 1 — Standard Pilgrimage Planning (Multi-turn, context retention)
# VERIFICATION: ACTUALLY_EXECUTED (deterministic fallback active due to sandbox)
# ===========================================================================
class Suite1_PilgrimagePlanning(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_a1_multiturn_context_origin_pax(self):
        """T1 supplies origin+pax; T2 adds mode; T3 follow-up must retain all."""
        sid = _sid()
        r1 = process_conversational_turn(
            "I want to plan a Vaishno Devi pilgrimage from Delhi for two adults", sid
        )
        req1 = r1.get("request", {})
        self.assertEqual(req1.get("origin", "").lower(), "delhi",
                         "Origin 'Delhi' must be extracted in T1")
        self.assertEqual(req1.get("pax"), 2,
                         "Pilgrim count 2 must be extracted in T1")

    def test_a2_multiturn_mode_retention(self):
        """After T1 provides origin/pax, T2 adds mode; both must survive."""
        sid = _sid()
        process_conversational_turn(
            "I want to plan a Vaishno Devi pilgrimage from Delhi for two adults", sid
        )
        r2 = process_conversational_turn("We prefer to travel by train", sid)
        req2 = r2.get("request", {})
        self.assertEqual(req2.get("origin", "").lower(), "delhi",
                         "Origin must be retained in T2")
        self.assertEqual(req2.get("pax"), 2,
                         "Pax must be retained in T2")
        self.assertIn(req2.get("mode", ""), ["train", "rail", "railway"],
                      "Mode 'train' must be captured in T2")

    def test_a3_no_repeated_origin_question(self):
        """Reply in T2 must not ask for origin again when already supplied."""
        sid = _sid()
        process_conversational_turn(
            "I want to visit Vaishno Devi from Mumbai for three pilgrims", sid
        )
        r2 = process_conversational_turn("What is the best time to go?", sid)
        reply = r2.get("reply", "").lower()
        self.assertNotIn("where are you travelling from", reply,
                         "Should not ask origin again after it was supplied")
        self.assertNotIn("where are you from", reply,
                         "Should not ask origin again")

    def test_a4_no_repeated_pax_question(self):
        """Reply must not ask pax count again after it was given."""
        sid = _sid()
        process_conversational_turn(
            "Planning Amarnath yatra from Chandigarh for four people", sid
        )
        r2 = process_conversational_turn("Please suggest transport options", sid)
        reply = r2.get("reply", "").lower()
        self.assertNotIn("how many pilgrims", reply,
                         "Should not ask pax again after it was supplied")

    def test_a5_pax_text_number_extraction(self):
        """Textual pax counts (two, three, five) must be numeric in request."""
        sid = _sid()
        r = process_conversational_turn(
            "My family of five wants to do Kedarnath from Haridwar", sid
        )
        pax = r.get("request", {}).get("pax")
        self.assertEqual(pax, 5, "Textual 'five' should map to integer 5")

    def test_a6_response_contains_required_keys(self):
        """Every response must carry the standard frontend contract keys."""
        sid = _sid()
        r = process_conversational_turn("Plan Vaishno Devi trip from Jaipur for 2", sid)
        for key in REQUIRED_RESPONSE_KEYS:
            self.assertIn(key, r, f"Response must contain key '{key}'")

    def test_a7_multiturn_four_turns(self):
        """Four consecutive turns on same session must retain state throughout."""
        sid = _sid()
        process_conversational_turn(
            "I want to visit Vaishno Devi from Delhi", sid
        )
        process_conversational_turn("We are four people", sid)
        process_conversational_turn("We prefer train", sid)
        r4 = process_conversational_turn(
            "How far is Katra from Bhawan?", sid
        )
        req4 = r4.get("request", {})
        self.assertEqual(req4.get("origin", "").lower(), "delhi",
                         "Origin must survive four turns")
        self.assertEqual(req4.get("pax"), 4,
                         "Pax must survive four turns")
        self.assertIn(req4.get("mode", ""), ["train", "rail", "railway"],
                      "Mode must survive four turns")


# ===========================================================================
# Suite 2 — Remote J&K Origins
# VERIFICATION: ACTUALLY_EXECUTED (geo-resolver + journey engine run in-process)
# ===========================================================================
class Suite2_RemoteJKOrigins(unittest.TestCase):

    JK_ORIGINS = [
        "Kishtwar", "Poonch", "Rajouri",
        "Doda", "Ramban", "Reasi", "Udhampur",
    ]

    def setUp(self):
        llm_circuit_breaker.reset()

    def _test_origin(self, origin_text):
        loc = GEO.resolve_origin(origin_text)
        self.assertIsNotNone(loc, f"resolve_origin('{origin_text}') must not return None")
        self.assertTrue(len(loc.clean_name) > 0,
                        f"clean_name must be non-empty for '{origin_text}'")
        result = JE.plan_connecting_journey(origin_text, "2025-06-15", 2)
        self.assertIn(result.get("status"), [
            "CONNECTING_ROUTES_AVAILABLE",
            "NEEDS_CLARIFICATION",
            "PARTIAL_ROUTES_FOUND",
        ], f"Connecting journey for '{origin_text}' must not reject with hard failure")
        return loc, result

    def test_b1_kishtwar(self):
        loc, res = self._test_origin("Kishtwar")
        self.assertEqual(loc.state, "Jammu & Kashmir")

    def test_b2_poonch(self):
        loc, res = self._test_origin("Poonch")
        self.assertIn("Jammu", loc.primary_gateway_hub)

    def test_b3_rajouri(self):
        loc, res = self._test_origin("Rajouri")
        self.assertIn("Jammu", loc.primary_gateway_hub)

    def test_b4_doda(self):
        self._test_origin("Doda")

    def test_b5_ramban(self):
        self._test_origin("Ramban")

    def test_b6_reasi(self):
        loc, res = self._test_origin("Reasi")
        self.assertIn("Katra", loc.primary_gateway_hub)

    def test_b7_udhampur(self):
        loc, res = self._test_origin("Udhampur")
        self.assertIn("Udhampur", loc.primary_gateway_hub)

    def test_b8_no_direct_train_no_fabrication(self):
        """Asking about direct train from Kishtwar must not fabricate train routes."""
        sid = _sid()
        llm_circuit_breaker.reset()
        r = process_conversational_turn(
            "Is there a direct train from Kishtwar to Katra?", sid
        )
        reply = r.get("reply", "").lower()
        # Should NOT invent a specific train number for Kishtwar (no railhead)
        import re
        fake_train = re.search(r"\b\d{4,5}\b.*express", reply)
        self.assertIsNone(fake_train,
                          "Must not fabricate specific train numbers for Kishtwar")


# ===========================================================================
# Suite 3 — Small Town / Village Origins
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite3_SmallTownOrigins(unittest.TestCase):

    HIMACHAL_ORIGINS = ["Palampur", "Mandi", "Dharamshala", "Chamba", "Kaza"]

    def setUp(self):
        llm_circuit_breaker.reset()

    def _resolve_ok(self, text):
        loc = GEO.resolve_origin(text)
        self.assertIsNotNone(loc, f"'{text}' must resolve")
        self.assertTrue(loc.clean_name, f"clean_name must not be empty for '{text}'")
        return loc

    def test_c1_palampur(self):
        loc = self._resolve_ok("Palampur")
        self.assertIn("Pathankot", loc.primary_gateway_hub)

    def test_c2_mandi(self):
        self._resolve_ok("Mandi")

    def test_c3_dharamshala(self):
        loc = self._resolve_ok("Dharamshala")
        self.assertIn("Pathankot", loc.primary_gateway_hub)

    def test_c4_chamba(self):
        self._resolve_ok("Chamba")

    def test_c5_kaza_remote(self):
        loc = self._resolve_ok("Kaza")
        # Kaza is remote; corridor type should indicate generic or specific
        self.assertTrue(len(loc.corridor_type) > 0,
                        "corridor_type must not be empty")

    def test_c6_village_near_ambala(self):
        loc = self._resolve_ok("small village near Ambala")
        self.assertIn("Ambala", loc.primary_gateway_hub)

    def test_c7_bilaspur_ambiguous(self):
        loc = GEO.resolve_origin("Bilaspur")
        # Either resolved (with hub) or requires clarification — never hard-rejected
        self.assertIsNotNone(loc, "Bilaspur must resolve (even with AMBIGUOUS_LOCATION)")
        self.assertIn(loc.corridor_type, [
            "AMBIGUOUS_LOCATION", "PRIMARY_GATEWAY", "HIMACHAL_CENTRAL_CORRIDOR",
            "GENERIC_INDIAN_ORIGIN",
        ], f"Bilaspur corridor_type unexpected: {loc.corridor_type}")


# ===========================================================================
# Suite 4 — Accessibility & Family Traveller
# VERIFICATION: ACTUALLY_EXECUTED (deterministic fallback)
# ===========================================================================
class Suite4_AccessibilityFamily(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_d1_elderly_accessibility_mention(self):
        """Query about elderly pilgrim should mention battery car / palki / accessibility."""
        sid = _sid()
        r = process_conversational_turn(
            "Planning with parents, father has difficulty walking. "
            "What accessibility options are available at Vaishno Devi?", sid
        )
        reply = r.get("reply", "").lower()
        accessible_terms = ["battery", "palki", "pony", "helicopter", "wheelchair",
                            "accessible", "mobility", "transport"]
        matches = [t for t in accessible_terms if t in reply]
        self.assertTrue(
            len(matches) >= 1,
            f"Reply must mention at least one accessibility option. Got: {reply[:200]}"
        )

    def test_d2_no_fabricated_accessibility_guarantee(self):
        """Reply must not guarantee specific live accessible transport booking."""
        sid = _sid()
        r = process_conversational_turn(
            "Can you book a wheelchair slot for my elderly mother at Vaishno Devi?", sid
        )
        reply = r.get("reply", "").lower()
        # Must NOT claim 'your wheelchair slot is confirmed' or similar
        self.assertNotIn("confirmed your wheelchair", reply)
        self.assertNotIn("wheelchair slot booked", reply)

    def test_d3_connecting_journey_legs_format(self):
        """ConnectingOption dicts must have a 'legs' list."""
        result = JE.plan_connecting_journey("Kishtwar", "2025-06-15", 2)
        if result.get("options_count", 0) > 0:
            opts = result.get("options", [])
            opt = opts[0]
            # Options are dicts (not dataclass objects)
            self.assertIsInstance(opt, dict,
                                  "ConnectingOption must be a dict")
            self.assertIn("legs", opt,
                          "ConnectingOption dict must have 'legs' key")
            self.assertIsInstance(opt["legs"], list,
                                  "ConnectingOption.legs must be a list")


# ===========================================================================
# Suite 5 — Weather and Tourism Context
# VERIFICATION: ACTUALLY_EXECUTED (deterministic fallback)
# ===========================================================================
class Suite5_WeatherTourism(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_e1_weather_query_response(self):
        """Weather query must produce a reply (not empty)."""
        sid = _sid()
        r = process_conversational_turn(
            "What is the weather like at Vaishno Devi in December?", sid
        )
        self.assertTrue(len(r.get("reply", "")) > 10,
                        "Weather query must produce a substantive reply")

    def test_e2_weather_then_followup_retains_destination(self):
        """After weather query for Vaishno Devi, follow-up must reference same place."""
        sid = _sid()
        process_conversational_turn(
            "What is the weather like at Vaishno Devi in December?", sid
        )
        r2 = process_conversational_turn("What should I pack for the journey?", sid)
        req2 = r2.get("request", {})
        # destination should still reference vaishno devi / katra
        dest = str(req2.get("destination", "")).lower()
        last_ctx = str(r2.get("last_itinerary_context", "")).lower()
        reply = r2.get("reply", "").lower()
        combined = dest + last_ctx + reply
        self.assertTrue(
            "vaishno" in combined or "katra" in combined or "yatra" in combined,
            "Context from first turn should influence follow-up response"
        )

    def test_e3_tourism_query_response(self):
        """Tourism query about sightseeing must produce non-empty reply."""
        sid = _sid()
        r = process_conversational_turn(
            "What are the best places to visit near Katra besides the main temple?", sid
        )
        self.assertTrue(len(r.get("reply", "")) > 20,
                        "Tourism query must produce a substantive reply")


# ===========================================================================
# Suite 6 — Accommodation (Shrine Board Bhawan)
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite6_Accommodation(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_f1_accommodation_query_detected(self):
        """is_accommodation_info_query must fire for bhawan/accommodation queries."""
        self.assertTrue(is_accommodation_info_query(
            "What bhawan accommodation is available at Vaishno Devi?"
        ))
        self.assertTrue(is_accommodation_info_query(
            "Tell me about Shrine Board bhawan options"
        ))
        self.assertTrue(is_accommodation_info_query(
            "Where can I stay near Bhawan during the yatra?"
        ))

    def test_f2_accommodation_handler_returns_reply(self):
        """Direct accommodation handler must return a reply mentioning bhawan/accommodation."""
        sid = _sid()
        r = _handle_deterministic_accommodation_turn(
            sid, "Tell me about Shrine Board bhawan options at Vaishno Devi"
        )
        self.assertEqual(r.get("status"), "SUCCESS")
        reply = r.get("reply", "").lower()
        self.assertTrue(
            "bhawan" in reply or "accommodation" in reply or "stay" in reply,
            f"Accommodation reply must mention lodging. Got: {reply[:200]}"
        )

    def test_f3_accommodation_handler_no_live_availability_promise(self):
        """Accommodation handler must NOT promise real-time availability."""
        sid = _sid()
        r = _handle_deterministic_accommodation_turn(
            sid, "Is Room 204 at Bhawan available tomorrow?"
        )
        reply = r.get("reply", "").lower()
        self.assertNotIn("room 204 is available", reply)
        self.assertNotIn("confirmed availability", reply)

    def test_f4_accommodation_fast_path_latency(self):
        """Accommodation handler must respond in under 500ms."""
        sid = _sid()
        t0 = time.time()
        _handle_deterministic_accommodation_turn(
            sid, "What accommodation options are available?"
        )
        ms = (time.time() - t0) * 1000
        self.assertLess(ms, 500,
                        f"Accommodation fast path took {ms:.0f}ms; must be < 500ms")

    def test_f5_accommodation_execution_mode(self):
        """Accommodation handler must set execution_mode to deterministic_accommodation."""
        sid = _sid()
        r = _handle_deterministic_accommodation_turn(sid, "Bhawan options at Vaishno Devi")
        self.assertEqual(r.get("execution_mode"), "deterministic_accommodation")


# ===========================================================================
# Suite 7 — Budget Transparency
# VERIFICATION: ACTUALLY_EXECUTED (deterministic fallback)
# ===========================================================================
class Suite7_BudgetTransparency(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_g1_budget_reply_not_empty(self):
        """Budget query must produce a reply."""
        sid = _sid()
        r = process_conversational_turn(
            "What is the estimated budget for a 5-day Vaishno Devi trip from Delhi for 2?", sid
        )
        self.assertTrue(len(r.get("reply", "")) > 20,
                        "Budget reply must not be empty")

    def test_g2_budget_uses_estimated_language(self):
        """Budget reply must qualify estimates rather than guaranteeing exact prices."""
        sid = _sid()
        r = process_conversational_turn(
            "Give me the exact total cost breakdown for Vaishno Devi trip", sid
        )
        reply = r.get("reply", "").lower()
        # Deterministic fallback should use estimation language
        caveat_terms = ["estimate", "approximate", "vary", "depend", "around",
                        "budget", "range", "may", "typically", "guideline"]
        matches = [t for t in caveat_terms if t in reply]
        self.assertTrue(
            len(matches) >= 1,
            f"Budget reply should use estimation language. Got: {reply[:300]}"
        )


# ===========================================================================
# Suite 8 — Booking Handoff & Authorization
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite8_BookingAuthorization(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_h1_unauthorized_booking_blocked(self):
        """execute_authorized_booking without human_authorized must return AUTHORIZATION_REQUIRED."""
        result = execute_authorized_booking.func(
            user_name="TestUser",
            pax_count=2,
            transport_text="Train from Delhi to Katra",
            slot_text="2025-06-15 09:00",
            total_price=4500.0,
            human_authorized=False,
        )
        self.assertEqual(result.get("status"), "AUTHORIZATION_REQUIRED",
                         "Booking without auth must be blocked")
        self.assertFalse(result.get("authorized", True),
                         "authorized flag must be False when not authorized")

    def test_h2_authorized_booking_proceeds(self):
        """With human_authorized=True, the gate must pass (not block with AUTHORIZATION_REQUIRED).

        VERIFICATION: STATICALLY_INSPECTED — The authorized path calls
        rpa_agent.execute_playwright_mock_booking() which requires a live browser
        (Playwright) and cannot run in the sandboxed test environment.
        We verify the gate logic, not the RPA execution.
        """
        # The unauthorized path is the security-critical gate; we verified it in h1.
        # For human_authorized=True, the function PASSES the gate and calls RPA.
        # In a sandboxed env this will hang or error — so we just verify the source code
        # contains the authorization check at the right position.
        import inspect
        src = inspect.getsource(execute_authorized_booking.func)
        # Gate must be present and return AUTHORIZATION_REQUIRED when not authorized
        self.assertIn("AUTHORIZATION_REQUIRED", src,
                      "Source must contain AUTHORIZATION_REQUIRED gate")
        self.assertIn("not human_authorized", src,
                      "Source must check human_authorized flag before proceeding")
        # RPA is called only after authorization check
        gate_pos = src.find("not human_authorized")
        rpa_pos = src.find("execute_playwright_mock_booking")
        self.assertGreater(rpa_pos, gate_pos,
                           "RPA call must appear after the authorization gate in source")

    def test_h3_booking_response_has_status_key(self):
        """Booking response must always contain 'status' key."""
        from unittest.mock import patch

        # Test unauthorized (production security gate)
        result_unauth = execute_authorized_booking.func(
            user_name="TestUser",
            pax_count=1,
            transport_text="Bus",
            slot_text="2025-07-01",
            total_price=1200.0,
            human_authorized=False,
        )
        self.assertIn("status", result_unauth, "Unauthorized booking response must have 'status' key")
        self.assertEqual(result_unauth.get("status"), "AUTHORIZATION_REQUIRED")

        # Test authorized (with mock to avoid launching real Playwright browser in sandbox)
        with patch("agents.central_agent.rpa_agent.execute_playwright_mock_booking", return_value={"status": "SUCCESS", "booking_id": "MOCK-123"}):
            result_auth = execute_authorized_booking.func(
                user_name="TestUser",
                pax_count=1,
                transport_text="Bus",
                slot_text="2025-07-01",
                total_price=1200.0,
                human_authorized=True,
            )
            self.assertIn("status", result_auth, "Authorized booking response must have 'status' key")
            self.assertEqual(result_auth.get("status"), "SUCCESS")


# ===========================================================================
# Suite 9 — Mid-Conversation Corrections
# VERIFICATION: ACTUALLY_EXECUTED (deterministic fallback)
# ===========================================================================
class Suite9_Corrections(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_i1_change_origin_mid_conversation(self):
        """Explicitly changing origin mid-conversation must update request.origin."""
        sid = _sid()
        process_conversational_turn(
            "I want to visit Vaishno Devi from Delhi for two adults", sid
        )
        r2 = process_conversational_turn(
            "Actually, change the origin to Chandigarh", sid
        )
        req2 = r2.get("request", {})
        # Origin should now be Chandigarh
        origin = req2.get("origin", "").lower()
        self.assertIn("chandigarh", origin,
                      f"Origin should update to Chandigarh after correction; got: '{origin}'")

    def test_i2_change_pax_mid_conversation(self):
        """Changing pax count mid-conversation must update request.pax."""
        sid = _sid()
        process_conversational_turn(
            "Planning Vaishno Devi trip from Pune for two people", sid
        )
        r2 = process_conversational_turn("Make that five people instead", sid)
        pax = r2.get("request", {}).get("pax")
        self.assertEqual(pax, 5, f"Pax should update to 5; got: {pax}")

    def test_i3_change_mode_mid_conversation(self):
        """Changing travel mode mid-conversation must update request.mode."""
        sid = _sid()
        process_conversational_turn(
            "Plan a train trip to Vaishno Devi from Bangalore for 3", sid
        )
        r2 = process_conversational_turn("Let's travel by flight instead", sid)
        mode = r2.get("request", {}).get("mode", "").lower()
        self.assertTrue(
            "flight" in mode or "air" in mode or "fly" in mode,
            f"Mode should update to flight; got: '{mode}'"
        )


# ===========================================================================
# Suite 10 — Circuit Breaker & Fallback
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite10_CircuitBreaker(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_j1_circuit_breaker_initial_state_closed(self):
        """After reset, circuit breaker must be in CLOSED state."""
        self.assertEqual(llm_circuit_breaker.state, CircuitState.CLOSED)

    def test_j2_circuit_breaker_trips_after_failures(self):
        """After 2+ LLM failures, circuit breaker must be OPEN."""
        sid = _sid()
        # Two LLM-path queries; both will fail in sandbox
        process_conversational_turn("Plan a 3-day trip to Vaishno Devi from Kolkata", sid)
        process_conversational_turn("What transport options are available?", sid)
        # Circuit breaker should be OPEN now
        self.assertEqual(llm_circuit_breaker.state, CircuitState.OPEN,
                         "Circuit breaker must be OPEN after 2 consecutive LLM failures")

    def test_j3_circuit_breaker_open_uses_deterministic(self):
        """When circuit breaker is OPEN, response must be deterministic_fallback."""
        sid = _sid()
        # Trip the breaker
        process_conversational_turn("Plan a complex trip from Kolkata to Amarnath", sid)
        process_conversational_turn("Give detailed itinerary with costs", sid)
        # Now force OPEN state check
        if llm_circuit_breaker.state != CircuitState.OPEN:
            llm_circuit_breaker._fail_count = 10
            llm_circuit_breaker.state = CircuitState.OPEN
        sid2 = _sid()
        r = process_conversational_turn("Plan Kedarnath trip from Hyderabad", sid2)
        self.assertIn(r.get("execution_mode"), [
            "deterministic_fallback", "deterministic_greeting",
            "deterministic_acknowledgment", "deterministic_help",
        ], f"Open circuit breaker must use deterministic path; got: {r.get('execution_mode')}")

    def test_j4_circuit_breaker_response_reports_state(self):
        """Every response must carry circuit_breaker_state field."""
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        self.assertIn("circuit_breaker_state", r,
                      "Response must include circuit_breaker_state")
        self.assertIn(r["circuit_breaker_state"], ["CLOSED", "OPEN", "HALF_OPEN"])

    def test_j5_circuit_breaker_reset_restores_closed(self):
        """After manual reset, circuit breaker must return to CLOSED."""
        llm_circuit_breaker._fail_count = 10
        llm_circuit_breaker.state = CircuitState.OPEN
        llm_circuit_breaker.reset()
        self.assertEqual(llm_circuit_breaker.state, CircuitState.CLOSED)

    def test_j6_deterministic_fallback_still_produces_reply(self):
        """Even with circuit breaker OPEN, every query must produce a non-empty reply."""
        llm_circuit_breaker._fail_count = 10
        llm_circuit_breaker.state = CircuitState.OPEN
        sid = _sid()
        r = process_conversational_turn(
            "What is the route from Doda to Vaishno Devi?", sid
        )
        self.assertTrue(len(r.get("reply", "")) > 10,
                        "Deterministic fallback must still produce a reply")


# ===========================================================================
# Suite 11 — Connecting Journey Acceptance (15+ origins)
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite11_ConnectingJourneyOrigins(unittest.TestCase):

    ALL_ORIGINS = [
        "Kishtwar", "Poonch", "Rajouri", "Doda", "Ramban",
        "Reasi", "Udhampur", "Palampur", "Mandi", "Dharamshala",
        "Chamba", "Kaza", "Delhi", "Mumbai", "Kolkata",
        "small village near Ambala", "Bilaspur",
    ]

    def setUp(self):
        llm_circuit_breaker.reset()

    def _run_journey(self, origin):
        loc = GEO.resolve_origin(origin)
        self.assertIsNotNone(loc, f"'{origin}' must resolve to a location")
        result = JE.plan_connecting_journey(origin, "2025-07-01", 2)
        status = result.get("status")
        self.assertIn(status, [
            "CONNECTING_ROUTES_AVAILABLE",
            "NEEDS_CLARIFICATION",
            "PARTIAL_ROUTES_FOUND",
        ], f"Journey for '{origin}' must not hard-reject; status={status}")
        # Ensure no route leg fabricates a "FAKE" transport
        for opt in result.get("options", []):
            legs = opt.get("legs", []) if isinstance(opt, dict) else getattr(opt, "legs", [])
            for leg in legs:
                tname = leg.get("transport_name", "") if isinstance(leg, dict) else getattr(leg, "transport_name", "")
                self.assertNotIn("FAKE", str(tname).upper(),
                                 f"Route leg must not contain FAKE transport")
        return loc, result

    def test_k01_kishtwar(self):   self._run_journey("Kishtwar")
    def test_k02_poonch(self):     self._run_journey("Poonch")
    def test_k03_rajouri(self):    self._run_journey("Rajouri")
    def test_k04_doda(self):       self._run_journey("Doda")
    def test_k05_ramban(self):     self._run_journey("Ramban")
    def test_k06_reasi(self):      self._run_journey("Reasi")
    def test_k07_udhampur(self):   self._run_journey("Udhampur")
    def test_k08_palampur(self):   self._run_journey("Palampur")
    def test_k09_mandi(self):      self._run_journey("Mandi")
    def test_k10_dharamshala(self):self._run_journey("Dharamshala")
    def test_k11_chamba(self):     self._run_journey("Chamba")
    def test_k12_kaza(self):       self._run_journey("Kaza")
    def test_k13_delhi(self):
        loc, res = self._run_journey("Delhi")
        self.assertEqual(res.get("status"), "CONNECTING_ROUTES_AVAILABLE",
                         "Delhi (major hub) must have available routes")

    def test_k14_mumbai(self):
        _, res = self._run_journey("Mumbai")
        self.assertEqual(res.get("status"), "CONNECTING_ROUTES_AVAILABLE")

    def test_k15_kolkata(self):
        _, res = self._run_journey("Kolkata")
        self.assertEqual(res.get("status"), "CONNECTING_ROUTES_AVAILABLE")

    def test_k16_village_near_ambala(self):
        self._run_journey("small village near Ambala")

    def test_k17_bilaspur_ambiguous(self):
        self._run_journey("Bilaspur")


# ===========================================================================
# Suite 12 — Latency Benchmarks (Deterministic Paths)
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite12_LatencyBenchmarks(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def _measure(self, message, session_id=None, limit_ms=500):
        sid = session_id or _sid()
        t0 = time.time()
        r = process_conversational_turn(message, sid)
        ms = (time.time() - t0) * 1000
        return r, ms

    def test_l1_greeting_latency(self):
        """Simple greeting must respond within 500ms."""
        _, ms = self._measure("Hello")
        self.assertLess(ms, 500, f"Greeting took {ms:.0f}ms; must be < 500ms")

    def test_l2_acknowledgment_latency(self):
        """Acknowledgment must respond within 500ms."""
        _, ms = self._measure("Thank you so much, that was very helpful!")
        self.assertLess(ms, 500, f"Acknowledgment took {ms:.0f}ms; must be < 500ms")

    def test_l3_help_latency(self):
        """Help query must respond within 500ms."""
        _, ms = self._measure("Help me plan a yatra")
        self.assertLess(ms, 500, f"Help query took {ms:.0f}ms; must be < 500ms")

    def test_l4_contacts_latency(self):
        """Contacts query must respond within 500ms."""
        _, ms = self._measure("What is the emergency helpline for Vaishno Devi?")
        self.assertLess(ms, 500, f"Contacts query took {ms:.0f}ms; must be < 500ms")

    def test_l5_accommodation_latency(self):
        """Accommodation fast path must respond within 500ms."""
        t0 = time.time()
        _handle_deterministic_accommodation_turn(_sid(), "Bhawan options at Vaishno Devi?")
        ms = (time.time() - t0) * 1000
        self.assertLess(ms, 500, f"Accommodation took {ms:.0f}ms; must be < 500ms")

    def test_l6_operational_notice_latency(self):
        """Operational notice query must respond within 500ms."""
        # Use the exact phrase that triggers the deterministic_operational_notice fast path
        _, ms = self._measure("What are the current operational notices for Vaishno Devi?")
        self.assertLess(ms, 500, f"Operational notice took {ms:.0f}ms; must be < 500ms")

    def test_l7_connecting_journey_latency(self):
        """Connecting journey computation must complete within 2500ms."""
        t0 = time.time()
        JE.plan_connecting_journey("Kishtwar", "2025-06-15", 2)
        ms = (time.time() - t0) * 1000
        self.assertLess(ms, 2500, f"Connecting journey took {ms:.0f}ms; must be < 2500ms")

    def test_l8_geo_resolution_latency(self):
        """Geo resolution must complete in under 200ms."""
        t0 = time.time()
        GEO.resolve_origin("small village near Mandi")
        ms = (time.time() - t0) * 1000
        self.assertLess(ms, 200, f"Geo resolution took {ms:.0f}ms; must be < 200ms")

    def test_l9_timing_dict_in_response(self):
        """Every response must carry a timing dict with total_ms."""
        _, ms = self._measure("Hello")
        # just verify structure
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        timing = r.get("timing", {})
        self.assertIn("total_ms", timing, "Response timing must have total_ms")


# ===========================================================================
# Suite 13 — SSE Streaming Protocol
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite13_SSEStreaming(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_m1_streaming_yields_start_event(self):
        """process_conversational_turn_stream must yield a 'start' event first."""
        sid = _sid()
        gen = process_conversational_turn_stream("Hello", sid)
        first = next(gen)
        self.assertEqual(first.get("type"), "start",
                         f"First SSE event must be 'start'; got: {first.get('type')}")

    def test_m2_streaming_yields_token_events(self):
        """Stream must produce at least one 'token' event."""
        sid = _sid()
        types = []
        for chunk in process_conversational_turn_stream("Hello, tell me about Vaishno Devi", sid):
            types.append(chunk.get("type"))
            if len(types) > 20:
                break
        self.assertIn("token", types, "Stream must yield at least one 'token' event")

    def test_m3_streaming_yields_done_event(self):
        """Stream must end with a 'done' event containing the full response."""
        sid = _sid()
        final = None
        for chunk in process_conversational_turn_stream("Hello", sid):
            if chunk.get("type") == "done":
                final = chunk
        self.assertIsNotNone(final, "Stream must yield a 'done' event")
        response = final.get("response", {})
        self.assertIn("reply", response, "Done event must contain response.reply")

    def test_m4_streaming_done_has_session_id(self):
        """Done event response must carry session_id."""
        sid = _sid()
        for chunk in process_conversational_turn_stream("Hello", sid):
            if chunk.get("type") == "done":
                resp = chunk.get("response", {})
                self.assertIn("session_id", resp,
                              "Done event response must have session_id")
                break

    def test_m5_streaming_no_empty_reply_in_done(self):
        """Done event reply must not be empty."""
        sid = _sid()
        for chunk in process_conversational_turn_stream("Hello", sid):
            if chunk.get("type") == "done":
                reply = chunk.get("response", {}).get("reply", "")
                self.assertTrue(len(reply) > 5,
                                "Done event reply must not be empty")
                break


# ===========================================================================
# Suite 14 — API Contract & Frontend Keys
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite14_APIContract(unittest.TestCase):

    REQUIRED_KEYS = [
        "reply", "session_id", "intent", "status",
        "timing", "execution_mode", "circuit_breaker_state",
    ]

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_n1_all_required_keys_present(self):
        """All frontend contract keys must be present in every response."""
        sid = _sid()
        r = process_conversational_turn("Plan Vaishno Devi trip from Jaipur", sid)
        for key in self.REQUIRED_KEYS:
            self.assertIn(key, r, f"Response must contain key '{key}'")

    def test_n2_timing_has_total_ms(self):
        """Timing dict must contain total_ms as a number."""
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        timing = r.get("timing", {})
        self.assertIn("total_ms", timing)
        self.assertIsInstance(timing["total_ms"], (int, float))

    def test_n3_status_is_success_or_error(self):
        """status field must be one of SUCCESS, ERROR, PARTIAL."""
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        self.assertIn(r.get("status"), ["SUCCESS", "ERROR", "PARTIAL"],
                      f"status must be SUCCESS/ERROR/PARTIAL; got: {r.get('status')}")

    def test_n4_circuit_breaker_state_valid(self):
        """circuit_breaker_state must be CLOSED, OPEN, or HALF_OPEN."""
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        self.assertIn(r["circuit_breaker_state"], ["CLOSED", "OPEN", "HALF_OPEN"])

    def test_n5_session_id_echoed(self):
        """Response must echo back the same session_id."""
        sid = _sid()
        r = process_conversational_turn("Hello", sid)
        self.assertEqual(r.get("session_id"), sid,
                         "Response must echo the caller's session_id")


# ===========================================================================
# Suite 15 — Ambiguity Handling & Unknown Places
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite15_AmbiguityHandling(unittest.TestCase):

    def setUp(self):
        llm_circuit_breaker.reset()

    def test_p1_bilaspur_resolves_not_rejected(self):
        """Ambiguous Bilaspur must resolve to some location, not be rejected."""
        loc = GEO.resolve_origin("Bilaspur")
        self.assertIsNotNone(loc, "Bilaspur must not return None")
        self.assertTrue(len(loc.clean_name) > 0, "Bilaspur clean_name must not be empty")

    def test_p2_unknown_village_resolves_to_hub(self):
        """An unknown village description must resolve to nearest hub."""
        loc = GEO.resolve_origin("a small village near Mandi in Himachal")
        self.assertIsNotNone(loc, "Village near Mandi must resolve")
        self.assertTrue(len(loc.primary_gateway_hub) > 0,
                        "Village near Mandi must have a gateway hub")

    def test_p3_conversation_handles_unknown_origin_gracefully(self):
        """Giving an obscure origin in chat must produce a helpful reply, not error."""
        sid = _sid()
        r = process_conversational_turn(
            "I want to do Vaishno Devi yatra from Hatta village in Rajasthan", sid
        )
        self.assertNotEqual(r.get("status"), "ERROR",
                            "Unknown origin must not produce an error response")
        self.assertTrue(len(r.get("reply", "")) > 10,
                        "Reply must be substantive even for unknown origin")

    def test_p4_fully_unknown_text_does_not_crash(self):
        """Completely unknown place names must not crash — resolve gracefully."""
        loc = GEO.resolve_origin("XyzNonExistentPlaceABC123")
        # May return None or a fallback — must not raise
        # (asserting no exception is enough; we just call it)

    def test_p5_duplicate_question_detection(self):
        """is_simple_acknowledgment must catch common gratitude phrases."""
        gratitude_phrases = [
            "Thank you!",
            "Thanks so much!",
            "That was very helpful, thank you",
            "Great, appreciated!",
            "Perfect, thank you for the guidance",
        ]
        for phrase in gratitude_phrases:
            self.assertTrue(
                is_simple_acknowledgment(phrase),
                f"'{phrase}' should be detected as acknowledgment"
            )

    def test_p6_help_query_detection(self):
        """is_help_query must catch various help phrasings."""
        help_phrases = [
            "Help me plan a yatra",
            "What can you do?",
            "I need help",
            "How do I use this?",
        ]
        for phrase in help_phrases:
            self.assertTrue(
                is_help_query(phrase),
                f"'{phrase}' should be detected as help query"
            )


# ===========================================================================
# Suite 16 — Tool Selection (Selective Binding)
# VERIFICATION: ACTUALLY_EXECUTED
# ===========================================================================
class Suite16_SelectiveToolBinding(unittest.TestCase):

    def test_q1_select_tools_for_turn_returns_subset(self):
        """select_tools_for_turn must return a non-empty list not exceeding CENTRAL_TOOLS size."""
        tools = select_tools_for_turn("What transport is available from Delhi to Katra?")
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0, "Must return at least 1 tool")
        self.assertLessEqual(len(tools), len(CENTRAL_TOOLS),
                             "Must not exceed total tool count")

    def test_q2_weather_domain_includes_weather_tool(self):
        """Weather query should include weather tool in selection."""
        tools = select_tools_for_turn("What is the weather forecast for December in Katra?")
        tool_names = [getattr(t, "name", str(t)) for t in tools]
        # At least one tool must be weather-related
        weather_match = any("weather" in n.lower() for n in tool_names)
        self.assertTrue(weather_match,
                        f"Weather query must include weather tool; got: {tool_names}")

    def test_q3_transport_domain_includes_transport_tool(self):
        """Transport query should include transport tool in selection."""
        tools = select_tools_for_turn("What trains are available from Delhi to Katra?")
        tool_names = [getattr(t, "name", str(t)) for t in tools]
        transport_match = any("transport" in n.lower() for n in tool_names)
        self.assertTrue(transport_match,
                        f"Transport query must include transport tool; got: {tool_names}")

    def test_q4_simple_greeting_minimal_tools(self):
        """Greeting must bind fewer tools than complex queries."""
        greeting_tools = select_tools_for_turn("Hello, how are you?")
        complex_tools = select_tools_for_turn(
            "Plan a full 7-day itinerary with transport, accommodation and budget from Mumbai"
        )
        # Greeting should bind fewer or equal tools
        self.assertLessEqual(len(greeting_tools), len(complex_tools),
                             "Greeting should not bind more tools than complex query")


if __name__ == "__main__":
    unittest.main(verbosity=2)
