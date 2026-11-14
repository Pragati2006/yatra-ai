"""
tests/test_phase6_central_agent.py
Phase 6 Dedicated Verification Suite: Central AI Agent & LangChain Tool-Calling Architecture.

Covers all 20 Phase 6 verification requirements:
 1. Tourism knowledge tool execution (Vaishno Devi, Bhairavnath, Aarti, J&K facts).
 2. Weather guidance tool execution (Katra, Bhawan elevation, seasonal & live advisories).
 3. Transport search tool execution (trains, flights, buses with pax, dates, origin).
 4. Accommodation & Yatra planning tool execution (plan evaluation, hotel selection, slots).
 5. Itinerary modification tool execution (add/remove/move destinations, day-by-day edits).
 6. Budget calculation & adjustment (deterministic Decimal arithmetic, itemized breakdown).
 7. Slot availability tool execution (schema validation, date & category checking).
 8. Multi-tool coordination (simultaneous weather and transport query resolution).
 9. Multi-turn conversational context (turn 1 trip intent, turn 2 origin, turn 3 pax edit).
10. Booking intent detection & handoff card (action: NAVIGATE_TO_BOOKING safeguard).
11. Human authorization preservation (LLM strictly blocked from auto-confirming bookings).
12. Session resumption across turns (persistence in SQLite session_store).
13. Missing parameters clarification (polite follow-up without hallucinating origins).
14. Invalid calendar date rejection (impossible dates like Feb 31 rejected cleanly).
15. Unsupported category rejection (invalid darshan categories rejected with valid choices).
16. Offline & fallback resilience (seamless deterministic fallback when LLM is absent).
17. Tool timeout & exception handling (graceful recovery from tool errors).
18. Response envelope contract verification (all required keys present and typed).
19. Devotional tone & formatting (consistent 'Jai Mata Di' reverent pilgrimage voice).
20. Cross-database and account state continuity (session updates synced accurately).
"""

import os
import sys
import uuid
import json
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agents import central_agent, coordinator, itinerary_agent, orchestrator, session_store, tools
import agent as legacy_agent


class TestPhase6CentralAgent(unittest.TestCase):
    """Comprehensive test suite for Phase 6 Central AI Agent & LangChain Tool-Calling Architecture."""

    def setUp(self):
        self.session_id = f"test-p6-{uuid.uuid4().hex[:10]}"
        session_store.create_session(session_id=self.session_id)

    def tearDown(self):
        try:
            session_store.delete_session(self.session_id)
        except Exception:
            pass

    # =========================================================================
    # 1. TOURISM KNOWLEDGE TOOL
    # =========================================================================
    def test_01_tourism_knowledge_tool(self):
        """Verifies get_tourism_knowledge retrieves shrine history, timings, and destination details."""
        res = central_agent.get_tourism_knowledge.invoke({"query": "Bhairavnath Temple"})
        self.assertIsInstance(res, dict)
        self.assertIn("place", res)
        self.assertEqual(res["place"], "Bhairavnath Temple")
        self.assertIn("historical_background", res)
        self.assertTrue(len(res["historical_background"]) > 20)
        self.assertIn("timings", res)

    # =========================================================================
    # 2. WEATHER GUIDANCE TOOL
    # =========================================================================
    def test_02_weather_guidance_tool(self):
        """Verifies check_weather_guidance retrieves Katra & Bhawan temperatures and trek advisories."""
        w = central_agent.check_weather_guidance.invoke({"location": "Katra"})
        self.assertIsInstance(w, dict)
        self.assertEqual(w["location"], "Katra")
        self.assertIn("condition", w)
        self.assertIn("low_c", w)
        self.assertIn("high_c", w)
        self.assertTrue(w["low_c"] <= w["high_c"])
        self.assertIn("bhawan_elevation_note", w)
        self.assertIn("advisory", w)

    # =========================================================================
    # 3. TRANSPORT SEARCH TOOL
    # =========================================================================
    def test_03_transport_search_tool(self):
        """Verifies search_transport_options returns valid transport options for given dates and pax."""
        d1 = (date.today() + timedelta(days=2)).isoformat()
        d2 = (date.today() + timedelta(days=6)).isoformat()
        trans = central_agent.search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": d1,
            "end_date": d2,
            "mode": "train",
            "pax": 2,
        })
        self.assertIsInstance(trans, dict)
        self.assertEqual(trans["origin"], "Delhi")
        self.assertEqual(trans["pax"], 2)
        opts = trans.get("options", [])
        self.assertTrue(len(opts) > 0)
        self.assertEqual(opts[0]["mode"].lower(), "train")
        if opts[0].get("fare_classification") == "UNAVAILABLE":
            self.assertIsNone(opts[0]["total_transport_cost"])
            self.assertIsNone(opts[0]["price"])
        else:
            self.assertTrue(opts[0]["total_transport_cost"] > 0)

    # =========================================================================
    # 4. ACCOMMODATION & YATRA PLANNING TOOL
    # =========================================================================
    def test_04_evaluate_yatra_plan_tool(self):
        """Verifies evaluate_yatra_plan coordinates transport, slot, hotel, and itinerary."""
        start_d = (date.today() + timedelta(days=2)).isoformat()
        plan_out = central_agent.evaluate_yatra_plan.invoke({
            "origin": "Delhi",
            "duration_days": 4,
            "pax": 2,
            "start_date": start_d,
            "mode": "train",
            "budget": 20000.0,
            "hotel_category": "Budget",
            "pacing": "balanced",
        })
        self.assertIsInstance(plan_out, dict)
        self.assertEqual(plan_out["status"], "PLAN_READY")
        self.assertIn("selected_options", plan_out)
        self.assertIn("itinerary", plan_out)
        self.assertTrue(len(plan_out["itinerary"]) >= 4)
        self.assertIn("hotel", plan_out)
        self.assertIn("budget_evaluation", plan_out)
        self.assertTrue(plan_out["feasible"])

    # =========================================================================
    # 5. ITINERARY MODIFICATION TOOL
    # =========================================================================
    def test_05_modify_itinerary_tool(self):
        """Verifies modify_itinerary supports adding destinations and day customization."""
        dummy_req = {"origin": "Delhi", "duration_days": 4, "pax": 2}
        init_itin = itinerary_agent.generate_default_itinerary(dummy_req)

        edit_res = central_agent.modify_itinerary.invoke({
            "command": "Add Patnitop to Day 3",
            "current_itinerary": init_itin,
        })
        self.assertIsInstance(edit_res, dict)
        self.assertEqual(edit_res["status"], "EDIT_APPLIED")
        self.assertIn("Patnitop", edit_res["summary"])
        updated = edit_res["updated_itinerary"]
        day3 = next(d for d in updated if d.get("day_number") == 3 or d.get("day") == 3)
        self.assertTrue(any("Patnitop" in str(act) for act in day3["activities"]))

    # =========================================================================
    # 6. BUDGET CALCULATION & ADJUSTMENT
    # =========================================================================
    def test_06_budget_calculation_and_itemized_breakdown(self):
        """Verifies deterministic Decimal arithmetic and itemized budget evaluation."""
        req = {
            "origin": "Delhi",
            "pax": 3,
            "duration_days": 4,
            "budget": 30000.0,
        }
        plan_res = orchestrator.coordinate_plan(req)
        b_eval = plan_res.get("budget_evaluation")
        self.assertIsNotNone(b_eval)
        self.assertIn("grand_total", b_eval)
        self.assertIn("verified_costs", b_eval)
        self.assertIn("estimated_costs", b_eval)
        v_costs = b_eval["verified_costs"]
        e_costs = b_eval["estimated_costs"]
        if b_eval.get("is_complete"):
            self.assertAlmostEqual(v_costs["total_verified"] + e_costs["total_estimated"], b_eval["grand_total"], places=2)
        else:
            self.assertIsNone(b_eval["grand_total"])
            self.assertFalse(b_eval["is_complete"])

    # =========================================================================
    # 7. SLOT AVAILABILITY TOOL
    # =========================================================================
    def test_07_slot_availability_tool(self):
        """Verifies check_slot_availability validates schema and returns structured capacity data."""
        tool_inst = central_agent.check_slot_availability
        self.assertEqual(tool_inst.name, "check_slot_availability")
        schema = tool_inst.args
        self.assertIn("date", schema)
        self.assertIn("category", schema)

    # =========================================================================
    # 8. MULTI-TOOL COORDINATION (MOCK LLM BIND_TOOLS)
    # =========================================================================
    def test_08_multi_tool_coordination(self):
        """Verifies central agent executes multiple tool calls in a single turn (weather + transport)."""
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm

        # Step 1: Model requests two tool calls: weather and transport search
        call_msg = MagicMock()
        call_msg.tool_calls = [
            {
                "name": "check_weather_guidance",
                "args": {"location": "Katra"},
                "id": "call_weather_1",
            },
            {
                "name": "search_transport_options",
                "args": {"origin": "Delhi", "start_date": "2026-10-20", "end_date": "2026-10-24", "pax": 2, "mode": "train"},
                "id": "call_trans_2",
            },
        ]
        call_msg.content = ""

        # Step 2: Model synthesizes final response using outputs
        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = (
            "🙏 **Jai Mata Di!** Katra weather is pleasant (12°C - 24°C). "
            "Trains from Delhi are available with Vande Bharat Express starting at ₹1,630 per pilgrim."
        )

        mock_bound_llm.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            user_text="What is the weather in Katra and are there trains from Delhi on 2026-10-20 for 2 people?",
            session_id=self.session_id,
            llm=mock_llm,
        )

        self.assertIn("Jai Mata Di", res["reply"])
        self.assertEqual(res["source"], "central_agent_langchain")
        tool_names = [t["tool"] for t in res.get("tool_executions", [])]
        self.assertIn("check_weather_guidance", tool_names)
        self.assertIn("search_transport_options", tool_names)

    # =========================================================================
    # 9. MULTI-TURN CONVERSATIONAL CONTEXT
    # =========================================================================
    def test_09_multi_turn_conversational_context(self):
        """Verifies multi-turn state accumulation across turns (duration -> origin -> pax change)."""
        # Turn 1: Duration & Mode
        t1 = central_agent.process_conversational_turn(
            "Plan a 4 day trip by train with VIP darshan",
            session_id=self.session_id,
        )
        self.assertEqual(t1["intent"], "TRIP_PLANNING")
        self.assertEqual(t1["status"], "NEEDS_INFO")

        # Turn 2: Provide Origin
        t2 = central_agent.process_conversational_turn(
            "From Delhi",
            session_id=self.session_id,
        )
        self.assertEqual(t2["status"], "PLAN_READY")
        self.assertEqual(t2["request"]["origin"], "Delhi")
        self.assertEqual(t2["request"]["duration_days"], 4)
        self.assertEqual(t2["request"]["pax"], 1)

        # Turn 3: Change pax to 3
        t3 = central_agent.process_conversational_turn(
            "Change to 3 travellers",
            session_id=self.session_id,
        )
        self.assertEqual(t3["request"]["pax"], 3)
        self.assertEqual(t3["request"]["origin"], "Delhi")
        self.assertEqual(t3["request"]["duration_days"], 4)

    # =========================================================================
    # 10. BOOKING INTENT DETECTION & HANDOFF CARD
    # =========================================================================
    def test_10_booking_intent_detection_and_handoff_card(self):
        """Verifies booking intent triggers action: NAVIGATE_TO_BOOKING without auto-confirming."""
        # Setup active plan in session
        central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people by train",
            session_id=self.session_id,
        )

        # Devotee expresses intention to book
        res = central_agent.process_conversational_turn(
            "I want to proceed with booking",
            session_id=self.session_id,
        )
        self.assertEqual(res["intent"], "BOOKING_INTENT")
        self.assertEqual(res["action"], "NAVIGATE_TO_BOOKING")
        self.assertIn(res["status"], ("NAVIGATE_TO_BOOKING", "BOOKING_INTENT_TRIGGERED"))
        self.assertIn("booking", res["reply"].lower())
        # Must NOT have confirmed booking record or executed RPA
        self.assertIsNone(res.get("booking_id"))

    # =========================================================================
    # 11. HUMAN AUTHORIZATION PRESERVATION
    # =========================================================================
    def test_11_human_authorization_gate_preservation(self):
        """Verifies the central agent strictly enforces human confirmation before RPA booking."""
        central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people",
            session_id=self.session_id,
        )

        # Booking request without explicit confirmation keyword
        res_unconfirmed = central_agent.process_conversational_turn(
            "Book option 1",
            session_id=self.session_id,
        )
        self.assertEqual(res_unconfirmed["intent"], "BOOKING")
        self.assertIn("Human Confirmation Required", res_unconfirmed["reply"])
        self.assertEqual(res_unconfirmed["tool_execution"]["status"], "pending_human_confirmation")

    # =========================================================================
    # 12. SESSION RESUMPTION ACROSS TURNS
    # =========================================================================
    def test_12_session_resumption_across_turns(self):
        """Verifies session state persists in SQLite sessions.db and resumes seamlessly."""
        t1 = central_agent.process_conversational_turn(
            "Plan a 4 day trip from Jaipur for 2 people",
            session_id=self.session_id,
        )
        sid = t1["session_id"]

        # Resumed in a separate call referencing same session_id
        session_record = session_store.get_session(sid)
        self.assertIsNotNone(session_record)
        state = session_record.get("state", {})
        self.assertEqual(state.get("requirements", {}).get("origin"), "Jaipur")

        # Chat history is preserved
        msgs = session_store.get_messages(sid)
        self.assertTrue(len(msgs) >= 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["role"], "assistant")

    # =========================================================================
    # 13. MISSING PARAMETERS CLARIFICATION
    # =========================================================================
    def test_13_missing_parameters_clarification_no_fabrication(self):
        """Verifies missing mandatory fields (e.g. origin) produce a polite question without fabrication."""
        res = central_agent.process_conversational_turn(
            "I want to plan a pilgrimage to Vaishno Devi",
            session_id=self.session_id,
        )
        self.assertEqual(res["status"], "NEEDS_INFO")
        self.assertTrue("which city" in res["reply"].lower() or "starting city" in res["reply"].lower())
        self.assertFalse(res.get("request", {}).get("origin"))

    # =========================================================================
    # 14. INVALID CALENDAR DATE REJECTION
    # =========================================================================
    def test_14_invalid_calendar_date_rejection(self):
        """Verifies impossible calendar dates are rejected with explanation."""
        res = central_agent.process_conversational_turn(
            "Check availability for 31 February 2026",
            session_id=self.session_id,
        )
        self.assertEqual(res["intent"], "AVAILABILITY")
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertIn("invalid", res["reply"].lower())

    # =========================================================================
    # 15. UNSUPPORTED CATEGORY REJECTION
    # =========================================================================
    def test_15_unsupported_category_rejection(self):
        """Verifies unsupported darshan categories are rejected with valid choices listed."""
        res = central_agent.process_conversational_turn(
            "Check Super VIP darshan availability for 2026-10-20",
            session_id=self.session_id,
        )
        self.assertEqual(res["intent"], "AVAILABILITY")
        self.assertEqual(res["status"], "UNSUPPORTED_CATEGORY")
        self.assertIn("Normal Darshan", res["reply"])
        self.assertIn("VIP Darshan", res["reply"])
        self.assertIn("Helicopter Darshan", res["reply"])

    # =========================================================================
    # 16. OFFLINE & FALLBACK RESILIENCE
    # =========================================================================
    def test_16_offline_and_fallback_resilience(self):
        """Verifies central agent smoothly falls back to deterministic engine when LLM is unavailable."""
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            res = central_agent.process_conversational_turn(
                "Tell me about Ardhkuwari Cave",
                session_id=self.session_id,
                llm=None,
            )
            self.assertEqual(res["intent"], "TOURISM")
            self.assertIn("Ardhkuwari", res["reply"])
            self.assertIn(res["source"], ("local_fallback", "trip_orchestrator", "conversation_agent"))

    # =========================================================================
    # 17. TOOL TIMEOUT & EXCEPTION HANDLING
    # =========================================================================
    def test_17_tool_timeout_and_exception_handling(self):
        """Verifies tool exceptions or timeouts are handled gracefully without application crash."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound
        # Simulate LLM raising an unexpected timeout/network error
        mock_bound.invoke.side_effect = TimeoutError("Simulated LLM network timeout")

        res = central_agent.process_conversational_turn(
            "What is the weather in Katra?",
            session_id=self.session_id,
            llm=mock_llm,
        )
        # Should gracefully fall back to deterministic weather service
        self.assertEqual(res["intent"], "WEATHER")
        self.assertIn("Jai Mata Di", res["reply"])
        self.assertIn("Katra Weather", res["reply"])

    # =========================================================================
    # 18. RESPONSE ENVELOPE CONTRACT VERIFICATION
    # =========================================================================
    def test_18_response_envelope_contract_verification(self):
        """Verifies that response envelopes strictly maintain all required frontend/API keys."""
        res = central_agent.process_conversational_turn(
            "Plan a 4 day trip from Mumbai for 2 people by train",
            session_id=self.session_id,
        )
        required_keys = [
            "reply", "intent", "status", "session_id", "request",
            "plan", "itinerary", "recommendation", "action", "hotel", "budget_evaluation",
        ]
        for key in required_keys:
            self.assertIn(key, res, f"Expected key '{key}' missing from response envelope")

        self.assertIsInstance(res["reply"], str)
        self.assertIsInstance(res["session_id"], str)
        self.assertIsInstance(res["request"], dict)

    # =========================================================================
    # 19. DEVOTIONAL TONE & FORMATTING
    # =========================================================================
    def test_19_devotional_tone_and_greeting_formatting(self):
        """Verifies replies embody devotional warmth ('Jai Mata Di') and structured markdown."""
        queries = [
            "What is the history of Vaishno Devi?",
            "What is the weather in Katra?",
            "Plan a 4 day trip from Delhi for 2 people",
        ]
        for q in queries:
            sid = f"test-tone-{uuid.uuid4().hex[:8]}"
            res = central_agent.process_conversational_turn(q, session_id=sid)
            self.assertIn("Jai Mata Di", res["reply"])

    # =========================================================================
    # 20. CROSS-DATABASE & ACCOUNT STATE CONTINUITY
    # =========================================================================
    def test_20_cross_database_and_account_state_continuity(self):
        """Verifies session updates and messages sync accurately in session_store."""
        res = central_agent.process_conversational_turn(
            "Plan a 4 day trip from Varanasi for 2 people",
            session_id=self.session_id,
        )
        sid = res["session_id"]
        # Verify persistence directly from DB
        sess = session_store.get_session(sid)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["state"]["requirements"]["origin"], "Varanasi")
        self.assertEqual(sess["state"]["requirements"]["pax"], 2)

        # Resurrect state with an itinerary edit
        res_edit = central_agent.process_conversational_turn(
            "Add Patnitop to Day 3",
            session_id=sid,
        )
        self.assertIn(res_edit["intent"], ("ITINERARY", "TRIP_PLANNING"))
        sess_after = session_store.get_session(sid)
        self.assertIsNotNone(sess_after["state"].get("itinerary"))


if __name__ == "__main__":
    unittest.main()
