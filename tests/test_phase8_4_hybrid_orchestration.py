"""
tests/test_phase8_4_hybrid_orchestration.py
Phase 8 Checkpoint 8.4 Dedicated Verification Suite:
Central Agent Hybrid Orchestration & Partial Fallback

Covers all 30 Checkpoint 8.4 verification requirements:
 1. Simple conversational request (no tools, greeting fast-path, execution_mode='deterministic_greeting').
 2. Deterministic booking intent routing (safeguard gate, execution_mode='deterministic_booking').
 3. Booking authorization bypass prevention (execute_authorized_booking blocked without human auth).
 4. Single tool request (weather) with successful execution and provenance.
 5. Multi-tool request with all tools succeeding (weather + transport, partial_failure=False).
 6. Multi-tool request with one failed tool (failure handled, sibling survives, partial_failure=True).
 7. Multi-tool request with one timed-out tool (per-tool timeout 5.0s, partial_failure=True).
 8. Multi-tool request with multiple failures (degraded response, partial_failure=True).
 9. All tools unavailable (transparent honest degradation, status='UNAVAILABLE').
10. Malformed tool response (non-serializable object caught as 'invalid_tool_response').
11. Malformed LLM tool call response (invalid JSON arguments safely caught).
12. LLM provider unavailable (Groq 503/connection error falls back to deterministic orchestrator).
13. LLM timeout (Groq timeout falls back cleanly to deterministic orchestrator).
14. LLM iteration limit reached (bounded at max_iterations=3, triggers partial synthesis).
15. Duplicate tool call prevention (identical call signature in turn skipped with 'skipped').
16. Tool execution timeout handling (verifying timeout enforcement under slow execution).
17. Independent tool calls parallel execution (concurrent ThreadPoolExecutor timing).
18. Dependent tool calls preserve order (sequential iterations preserve tool outputs).
19. Successful results survive sibling failure (sibling tool data preserved in envelope).
20. Provenance survives partial failure (source_provenance accurately records success/failure).
21. Cached weather remains cached (freshness_status='cached', strictly excluded from live_sources).
22. Stale weather remains stale (freshness_status='stale', strictly excluded from live_sources).
23. Static RAG sources retain classification (source_type='static_rag', verification_status='verified_curated_source').
24. Simulated booking data retains classification (source_type='indicative_data' or 'simulated_booking').
25. Deterministic fallback response envelope contract compliance.
26. LLM response envelope contract compliance.
27. Session isolation across distinct session IDs.
28. No private data leaks across session contexts.
29. Existing booking handoff behavior unchanged (action='NAVIGATE_TO_BOOKING').
30. Existing RPA authorization protections intact end-to-end.
"""

import os
import sys
import uuid
import json
import time
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agents import central_agent, coordinator, itinerary_agent, orchestrator, session_store, tools
from agents.central_agent import ToolExecutionStatus, ToolExecutionRecord
from utils.provenance import attach_provenance_to_response, extract_provenance_from_tool_result


class TestPhase84HybridOrchestration(unittest.TestCase):
    """30-scenario verification suite for Central Agent Hybrid Orchestration & Partial Fallback."""

    def setUp(self):
        self.session_id = f"test-p84-{uuid.uuid4().hex[:10]}"
        session_store.create_session(session_id=self.session_id)

    def tearDown(self):
        try:
            session_store.delete_session(self.session_id)
        except Exception:
            pass

    # =========================================================================
    # 1. SIMPLE CONVERSATIONAL REQUEST (NO TOOLS, GREETING FAST-PATH)
    # =========================================================================
    def test_01_simple_conversational_request_no_tools(self):
        """Verifies pure greetings route deterministically with execution_mode='deterministic_greeting'."""
        greetings = ["Namaste", "Hello", "Jai Mata Di"]
        for g in greetings:
            res = central_agent.process_conversational_turn(g, session_id=self.session_id)
            self.assertEqual(res.get("execution_mode"), "deterministic_greeting")
            self.assertEqual(res.get("tool_executions"), [])
            self.assertFalse(res.get("partial_failure"))
            self.assertEqual(res.get("status"), "SUCCESS")
            self.assertEqual(res.get("intent"), "GENERAL")
            self.assertIn("Jai Mata Di", res.get("reply", ""))
            self.assertIn("source_provenance", res)
            self.assertIn("live_sources", res)

    # =========================================================================
    # 2. DETERMINISTIC BOOKING INTENT ROUTING
    # =========================================================================
    def test_02_deterministic_booking_intent_routing(self):
        """Verifies explicit booking requests route immediately to deterministic booking workflow."""
        central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people by train",
            session_id=self.session_id,
        )
        res = central_agent.process_conversational_turn(
            "I want to proceed with booking",
            session_id=self.session_id,
        )
        self.assertEqual(res.get("execution_mode"), "deterministic_booking")
        self.assertFalse(res.get("partial_failure"))
        self.assertEqual(res.get("action"), "NAVIGATE_TO_BOOKING")
        self.assertIn("booking", res.get("reply", "").lower())

    # =========================================================================
    # 3. BOOKING AUTHORIZATION BYPASS PREVENTION
    # =========================================================================
    def test_03_booking_authorization_bypass_prevention(self):
        """Verifies execute_authorized_booking is strictly blocked if human authorization is not granted."""
        # Case A: direct tool execution without authorization
        rec = central_agent._execute_single_tool_safe(
            "execute_authorized_booking",
            {"pax": 2, "dates": "2026-10-20", "human_authorized": False},
            session_id=self.session_id,
        )
        self.assertEqual(rec.status, "failure")
        self.assertEqual(rec.result.get("status"), "BLOCKED")
        self.assertTrue(rec.result.get("human_confirmation_required"))
        self.assertIn("Human authorization required", rec.error)

        # Case B: via mock LLM tool calling turn
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [{
            "name": "execute_authorized_booking",
            "args": {"pax": 2, "dates": "2026-10-20", "human_authorized": True},  # Attempted bypass in args
            "id": "call_booking_bypass",
        }]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Booking could not proceed without human authorization."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        # Session state has NO granted authorization
        res = central_agent.process_conversational_turn(
            "Execute booking now",
            session_id=self.session_id,
            llm=mock_llm,
        )
        tool_records = res.get("tool_executions", [])
        self.assertEqual(len(tool_records), 1)
        self.assertEqual(tool_records[0].get("status"), "failure")
        self.assertEqual(tool_records[0].get("result", {}).get("status"), "BLOCKED")

    # =========================================================================
    # 4. SINGLE TOOL REQUEST (WEATHER)
    # =========================================================================
    def test_04_single_tool_weather_request(self):
        """Verifies single tool execution returns clean execution record and provenance."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [{
            "name": "check_weather_guidance",
            "args": {"location": "Katra"},
            "id": "call_weather_1",
        }]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "🙏 **Jai Mata Di!** Katra weather is pleasant."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            "What is the weather in Katra?",
            session_id=self.session_id,
            llm=mock_llm,
        )
        self.assertEqual(res.get("execution_mode"), "hybrid_llm")
        self.assertEqual(len(res.get("tool_executions", [])), 1)
        self.assertEqual(res["tool_executions"][0]["status"], "success")
        self.assertFalse(res.get("partial_failure"))
        self.assertIn("source_provenance", res)
        self.assertTrue(len(res["source_provenance"]) >= 1)

    # =========================================================================
    # 5. MULTI-TOOL REQUEST (ALL SUCCESSFUL)
    # =========================================================================
    def test_05_multi_tool_request_all_successful(self):
        """Verifies multi-tool execution with weather and transport both succeeding."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {
                "name": "check_weather_guidance",
                "args": {"location": "Katra"},
                "id": "call_w_1",
            },
            {
                "name": "search_transport_options",
                "args": {"origin": "Delhi", "start_date": "2026-10-20", "end_date": "2026-10-24", "pax": 2},
                "id": "call_t_1",
            },
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "🙏 **Jai Mata Di!** Weather is pleasant and trains are available from Delhi."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            "Give me weather in Katra and transport from Delhi",
            session_id=self.session_id,
            llm=mock_llm,
        )
        self.assertFalse(res.get("partial_failure"))
        self.assertEqual(len(res.get("tool_executions", [])), 2)
        statuses = [t["status"] for t in res["tool_executions"]]
        self.assertEqual(statuses, ["success", "success"])
        self.assertEqual(res.get("status"), "SUCCESS")

    # =========================================================================
    # 6. MULTI-TOOL REQUEST (ONE FAILED TOOL, SIBLING SURVIVES)
    # =========================================================================
    def test_06_multi_tool_request_one_failed_tool(self):
        """Verifies that when one tool fails, the sibling tool result survives and partial_failure=True."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {
                "name": "check_weather_guidance",
                "args": {"location": "Katra"},
                "id": "call_w_ok",
            },
            {
                "name": "search_transport_options",
                "args": {"origin": "Delhi", "start_date": "2026-10-20", "end_date": "2026-10-24", "pax": 2},
                "id": "call_t_fail",
            },
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Weather in Katra is clear. Notice: Transport timetables are currently unavailable."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        mock_t = MagicMock()
        mock_t.invoke.side_effect = RuntimeError("Railway DB timeout")
        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {"search_transport_options": mock_t}):
            res = central_agent.process_conversational_turn(
                "Check Katra weather and trains from Delhi",
                session_id=self.session_id,
                llm=mock_llm,
            )

        self.assertTrue(res.get("partial_failure"))
        self.assertEqual(len(res.get("tool_executions", [])), 2)
        rec_map = {t["tool"]: t for t in res["tool_executions"]}
        self.assertEqual(rec_map["check_weather_guidance"]["status"], "success")
        self.assertEqual(rec_map["search_transport_options"]["status"], "failure")
        self.assertEqual(res.get("status"), "PARTIAL_SUCCESS")

    # =========================================================================
    # 7. MULTI-TOOL REQUEST (ONE TIMED-OUT TOOL)
    # =========================================================================
    def test_07_multi_tool_request_one_timed_out_tool(self):
        """Verifies that a tool exceeding timeout is recorded as status='timeout' while sibling succeeds."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {
                "name": "check_weather_guidance",
                "args": {"location": "Katra"},
                "id": "call_w_ok",
            },
            {
                "name": "evaluate_yatra_plan",
                "args": {"origin": "Delhi", "duration_days": 4, "pax": 2},
                "id": "call_plan_timeout",
            },
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Weather guidance retrieved. Yatra plan evaluation timed out."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        def slow_plan(*args, **kwargs):
            time.sleep(0.3)
            return {"status": "PLAN_READY"}

        mock_plan = MagicMock()
        mock_plan.invoke.side_effect = slow_plan
        orig_exec = central_agent._execute_single_tool_safe
        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {"evaluate_yatra_plan": mock_plan}):
            with patch("agents.central_agent._execute_single_tool_safe", side_effect=lambda name, args, session_id=None, timeout_seconds=5.0: (
                orig_exec(name, args, session_id=session_id, timeout_seconds=0.05)
            )):
                res = central_agent.process_conversational_turn(
                    "Check Katra weather and evaluate plan",
                    session_id=self.session_id,
                    llm=mock_llm,
                )

        self.assertTrue(res.get("partial_failure"))
        rec_map = {t["tool"]: t for t in res.get("tool_executions", [])}
        self.assertEqual(rec_map["evaluate_yatra_plan"]["status"], "timeout")
        self.assertEqual(rec_map["check_weather_guidance"]["status"], "success")

    # =========================================================================
    # 8. MULTI-TOOL REQUEST (MULTIPLE FAILURES)
    # =========================================================================
    def test_08_multi_tool_request_multiple_failures(self):
        """Verifies handling when 2 out of 3 tools fail, preserving the 1 successful result."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {"name": "get_tourism_knowledge", "args": {"query": "Bhairavnath"}, "id": "c1"},
            {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "c2"},
            {"name": "search_transport_options", "args": {"origin": "Delhi"}, "id": "c3"},
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Bhairavnath details retrieved. Weather and transport services unavailable."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        mock_w = MagicMock()
        mock_w.invoke.side_effect = RuntimeError("Weather API error")
        mock_t = MagicMock()
        mock_t.invoke.side_effect = RuntimeError("Transport DB down")

        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {
            "check_weather_guidance": mock_w,
            "search_transport_options": mock_t,
        }):
            res = central_agent.process_conversational_turn(
                "Tell me about Bhairavnath, Katra weather, and trains from Delhi",
                session_id=self.session_id,
                llm=mock_llm,
            )

        self.assertTrue(res.get("partial_failure"))
        self.assertEqual(res.get("status"), "PARTIAL_SUCCESS")
        self.assertEqual(res.get("last_tourism_place"), "Bhairavnath Temple")

    # =========================================================================
    # 9. ALL TOOLS UNAVAILABLE
    # =========================================================================
    def test_09_all_tools_unavailable(self):
        """Verifies that when all tools fail, system returns transparent degraded response with status='UNAVAILABLE'."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "c1"},
            {"name": "search_transport_options", "args": {"origin": "Delhi"}, "id": "c2"},
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "All services are currently unavailable."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        mock_w = MagicMock()
        mock_w.invoke.side_effect = RuntimeError("Weather 500")
        mock_t = MagicMock()
        mock_t.invoke.side_effect = RuntimeError("Transport 500")

        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {
            "check_weather_guidance": mock_w,
            "search_transport_options": mock_t,
        }):
            res = central_agent.process_conversational_turn(
                "Katra weather and Delhi transport",
                session_id=self.session_id,
                llm=mock_llm,
            )

        self.assertTrue(res.get("partial_failure"))
        self.assertEqual(res.get("status"), "UNAVAILABLE")

    # =========================================================================
    # 10. MALFORMED TOOL RESPONSE
    # =========================================================================
    def test_10_malformed_tool_response(self):
        """Verifies that non-serializable tool output is safely caught as 'invalid_tool_response'."""
        class NonSerializableObj:
            pass

        mock_bad = MagicMock()
        mock_bad.invoke.return_value = NonSerializableObj()
        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {"check_weather_guidance": mock_bad}):
            rec = central_agent._execute_single_tool_safe("check_weather_guidance", {"location": "Katra"})
            self.assertEqual(rec.status, "invalid_tool_response")
            self.assertEqual(rec.result.get("status"), "invalid_tool_response")

    # =========================================================================
    # 11. MALFORMED LLM TOOL CALL RESPONSE
    # =========================================================================
    def test_11_malformed_llm_tool_call_response(self):
        """Verifies that unparseable or malformed JSON in tool call arguments is safely caught."""
        seen_calls = {}
        batch = [{
            "name": "check_weather_guidance",
            "args": "{invalid_json_missing_quotes: true",
            "id": "c_bad_json",
        }]
        results = central_agent._execute_tool_batch(batch, seen_calls=seen_calls)
        self.assertEqual(len(results), 1)
        call, rec = results[0]
        self.assertEqual(rec.status, "invalid_tool_response")
        self.assertEqual(rec.error, "Malformed JSON arguments")

    # =========================================================================
    # 12. LLM PROVIDER UNAVAILABLE (GROQ 503 / CONNECTION ERROR)
    # =========================================================================
    def test_12_llm_provider_unavailable(self):
        """Verifies graceful fallback to deterministic pipeline when Groq API throws 503 / connection error."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound
        mock_bound.invoke.side_effect = RuntimeError("503 Service Unavailable: Groq API gateway timeout")

        res = central_agent.process_conversational_turn(
            "What is the weather in Katra?",
            session_id=self.session_id,
            llm=mock_llm,
        )
        self.assertEqual(res.get("execution_mode"), "deterministic_fallback")
        self.assertIn("Jai Mata Di", res.get("reply", ""))
        self.assertIn("source_provenance", res)

    # =========================================================================
    # 13. LLM TIMEOUT
    # =========================================================================
    def test_13_llm_timeout(self):
        """Verifies that an LLM timeout triggers fallback to the deterministic pipeline without dropping query."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound
        mock_bound.invoke.side_effect = TimeoutError("Groq inference timeout after 30.0s")

        res = central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people",
            session_id=self.session_id,
            llm=mock_llm,
        )
        self.assertEqual(res.get("execution_mode"), "deterministic_fallback")
        self.assertIn("reply", res)
        self.assertFalse(res.get("partial_failure"))

    # =========================================================================
    # 14. LLM ITERATION LIMIT REACHED
    # =========================================================================
    def test_14_llm_iteration_limit_reached(self):
        """Verifies loop bound enforcement (max_iterations=3) when LLM loops endlessly requesting tools."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        loop_msg = MagicMock()
        loop_msg.tool_calls = [{
            "name": "check_weather_guidance",
            "args": {"location": "Katra"},
            "id": "loop_call",
        }]
        loop_msg.content = ""

        # Model keeps requesting tools forever
        mock_bound.invoke.return_value = loop_msg

        res = central_agent.process_conversational_turn(
            "Check weather in Katra",
            session_id=self.session_id,
            llm=mock_llm,
        )
        self.assertEqual(res.get("execution_mode"), "hybrid_partial_fallback")
        self.assertIn("reply", res)
        self.assertIn("Katra", res.get("reply", ""))

    # =========================================================================
    # 15. DUPLICATE TOOL CALL PREVENTION
    # =========================================================================
    def test_15_duplicate_tool_call_prevention(self):
        """Verifies duplicate tool calls with identical arguments in a batch are marked as 'skipped'."""
        seen_calls = {}
        tool_calls = [
            {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "call_1"},
            {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "call_2"},
        ]
        results = central_agent._execute_tool_batch(tool_calls, seen_calls=seen_calls)
        self.assertEqual(len(results), 2)
        rec1 = results[0][1]
        rec2 = results[1][1]
        self.assertEqual(rec1.status, "success")
        self.assertEqual(rec2.status, "skipped")
        self.assertIn("Duplicate", rec2.error)

    # =========================================================================
    # 16. TOOL EXECUTION TIMEOUT HANDLING
    # =========================================================================
    def test_16_tool_execution_timeout_handling(self):
        """Dedicated test verifying timeout enforcement via _execute_single_tool_safe."""
        def slow_invoke(*args, **kwargs):
            time.sleep(0.2)
            return {"status": "ok"}

        mock_slow = MagicMock()
        mock_slow.invoke.side_effect = slow_invoke
        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {"check_weather_guidance": mock_slow}):
            rec = central_agent._execute_single_tool_safe(
                "check_weather_guidance",
                {"location": "Katra"},
                timeout_seconds=0.05,
            )
            self.assertEqual(rec.status, "timeout")
            self.assertEqual(rec.result.get("status"), "timeout")
            self.assertIn("Timeout after 0.05s", rec.error)

    # =========================================================================
    # 17. INDEPENDENT TOOL CALLS PARALLEL EXECUTION
    # =========================================================================
    def test_17_independent_tool_calls_parallel_execution(self):
        """Verifies independent tool calls in a batch run concurrently via ThreadPoolExecutor."""
        def slow_w(*args, **kwargs):
            time.sleep(0.15)
            return {"status": "SUCCESS", "weather": "pleasant"}

        def slow_t(*args, **kwargs):
            time.sleep(0.15)
            return {"status": "SUCCESS", "trains": []}

        mock_w = MagicMock()
        mock_w.invoke.side_effect = slow_w
        mock_t = MagicMock()
        mock_t.invoke.side_effect = slow_t

        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {
            "check_weather_guidance": mock_w,
            "search_transport_options": mock_t,
        }):
            seen = {}
            calls = [
                {"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "c1"},
                {"name": "search_transport_options", "args": {"origin": "Delhi"}, "id": "c2"},
            ]
            t0 = time.perf_counter()
            results = central_agent._execute_tool_batch(calls, seen_calls=seen)
            elapsed = time.perf_counter() - t0

            self.assertEqual(len(results), 2)
            # Parallel execution should finish well under sequential 0.30s (typically ~0.16s - 0.25s)
            self.assertLess(elapsed, 0.28)

    # =========================================================================
    # 18. DEPENDENT TOOL CALLS PRESERVE ORDER
    # =========================================================================
    def test_18_dependent_tool_calls_preserve_order(self):
        """Verifies multi-iteration sequential tool calls preserve ordering and history."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg_1 = MagicMock()
        call_msg_1.tool_calls = [{"name": "get_tourism_knowledge", "args": {"query": "Bhairavnath"}, "id": "call_1"}]
        call_msg_1.content = ""

        call_msg_2 = MagicMock()
        call_msg_2.tool_calls = [{"name": "check_weather_guidance", "args": {"location": "Bhawan"}, "id": "call_2"}]
        call_msg_2.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Bhairavnath details and Bhawan weather synthesized."

        mock_bound.invoke.side_effect = [call_msg_1, call_msg_2, final_msg]

        res = central_agent.process_conversational_turn(
            "Tell me about Bhairavnath and its weather",
            session_id=self.session_id,
            llm=mock_llm,
        )
        tool_names = [t["tool"] for t in res.get("tool_executions", [])]
        self.assertEqual(tool_names, ["get_tourism_knowledge", "check_weather_guidance"])

    # =========================================================================
    # 19. SUCCESSFUL RESULTS SURVIVE SIBLING FAILURE
    # =========================================================================
    def test_19_successful_results_survive_sibling_failure(self):
        """Verifies structured assets from successful tools are retained even if a sibling tool fails."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {"name": "evaluate_yatra_plan", "args": {"origin": "Delhi", "duration_days": 4, "pax": 2}, "id": "c1"},
            {"name": "check_weather_guidance", "args": {"location": "InvalidLocationXYZ"}, "id": "c2"},
        ]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Plan evaluated. Weather for requested location was unavailable."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        mock_w = MagicMock()
        mock_w.invoke.side_effect = RuntimeError("Location not found")
        with patch.dict(central_agent.CENTRAL_TOOL_MAP, {"check_weather_guidance": mock_w}):
            res = central_agent.process_conversational_turn(
                "Evaluate plan and check weather",
                session_id=self.session_id,
                llm=mock_llm,
            )

        self.assertIsNotNone(res.get("plan"))
        self.assertIsNotNone(res.get("itinerary"))
        self.assertTrue(res.get("partial_failure"))

    # =========================================================================
    # 20. PROVENANCE SURVIVES PARTIAL FAILURE
    # =========================================================================
    def test_20_provenance_survives_partial_failure(self):
        """Verifies source_provenance includes both successful and failed tool executions with correct metadata."""
        executed_tools = [
            {
                "tool": "check_weather_guidance",
                "args": {"location": "Katra"},
                "status": "success",
                "result": {
                    "location": "Katra",
                    "source_name": "Open-Meteo Weather API",
                    "source_type": "live_api",
                    "freshness_status": "live",
                    "verification_status": "verified_external_api",
                    "url": "https://api.open-meteo.com/v1/forecast",
                    "retrieved_at": datetime.now().isoformat(),
                },
                "duration_ms": 120.0,
            },
            {
                "tool": "search_transport_options",
                "args": {"origin": "Delhi"},
                "status": "failure",
                "result": {"status": "failed", "error": "Connection refused"},
                "duration_ms": 80.0,
                "error": "Connection refused",
            },
        ]
        base_resp = {"reply": "Partial synthesis", "tool_executions": executed_tools}
        enriched = attach_provenance_to_response(base_resp, tool_executions=executed_tools)

        self.assertIn("source_provenance", enriched)
        self.assertIn("live_sources", enriched)
        self.assertEqual(len(enriched["live_sources"]), 1)
        self.assertEqual(enriched["live_sources"][0]["source_name"], "Open-Meteo Weather API")
        prov_statuses = [p["freshness_status"] for p in enriched["source_provenance"]]
        self.assertIn("live", prov_statuses)
        self.assertIn("unavailable", prov_statuses)

    # =========================================================================
    # 21. CACHED WEATHER REMAINS CACHED
    # =========================================================================
    def test_21_cached_weather_remains_cached(self):
        """Verifies cached weather is classified as freshness_status='cached' and strictly excluded from live_sources."""
        cached_weather_record = {
            "tool": "check_weather_guidance",
            "args": {"location": "Katra"},
            "status": "success",
            "result": {
                "location": "Katra",
                "source_name": "Open-Meteo Weather API",
                "source_type": "live_api",
                "freshness_status": "cached",
                "verification_status": "verified_external_api",
                "retrieved_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            },
        }
        resp = {"reply": "Weather cached", "tool_executions": [cached_weather_record]}
        enriched = attach_provenance_to_response(resp, tool_executions=[cached_weather_record])

        self.assertEqual(len(enriched["source_provenance"]), 1)
        self.assertEqual(enriched["source_provenance"][0]["freshness_status"], "cached")
        self.assertEqual(len(enriched["live_sources"]), 0, "Cached weather must NOT appear in live_sources")

    # =========================================================================
    # 22. STALE WEATHER REMAINS STALE
    # =========================================================================
    def test_22_stale_weather_remains_stale(self):
        """Verifies stale weather is classified as freshness_status='stale' and strictly excluded from live_sources."""
        stale_weather_record = {
            "tool": "check_weather_guidance",
            "args": {"location": "Katra"},
            "status": "success",
            "result": {
                "location": "Katra",
                "source_name": "Open-Meteo Weather API",
                "source_type": "live_api",
                "freshness_status": "stale",
                "verification_status": "unverified",
                "retrieved_at": (datetime.now() - timedelta(hours=3)).isoformat(),
            },
        }
        resp = {"reply": "Weather stale", "tool_executions": [stale_weather_record]}
        enriched = attach_provenance_to_response(resp, tool_executions=[stale_weather_record])

        self.assertEqual(len(enriched["source_provenance"]), 1)
        self.assertEqual(enriched["source_provenance"][0]["freshness_status"], "stale")
        self.assertEqual(len(enriched["live_sources"]), 0, "Stale weather must NOT appear in live_sources")

    # =========================================================================
    # 23. STATIC RAG SOURCES RETAIN CLASSIFICATION
    # =========================================================================
    def test_23_static_rag_sources_retain_classification(self):
        """Verifies static RAG search retains source_type='static_rag' and verification_status='verified_curated_source'."""
        rag_record = {
            "tool": "search_yatra_knowledge",
            "args": {"query": "Ardhkuwari holy cave significance"},
            "status": "success",
            "result": {
                "query": "Ardhkuwari holy cave significance",
                "sources": [{"title": "Ardhkuwari Guide", "source_file": "ardhkuwari.md"}],
                "source_name": "Yatra Pilgrimage Knowledge Base",
                "source_type": "static_rag",
                "freshness_status": "static",
                "verification_status": "verified_curated_source",
            },
        }
        resp = {"reply": "Ardhkuwari significance", "tool_executions": [rag_record]}
        enriched = attach_provenance_to_response(resp, tool_executions=[rag_record])

        prov = enriched["source_provenance"][0]
        self.assertEqual(prov["source_type"], "static_rag")
        self.assertIn(prov["verification_status"], ("verified_official_source", "verified_curated_source"))
        self.assertEqual(len(enriched["live_sources"]), 0)

    # =========================================================================
    # 24. SIMULATED BOOKING DATA RETAINS CLASSIFICATION
    # =========================================================================
    def test_24_simulated_booking_data_retains_classification(self):
        """Verifies simulated booking / indicative schedule sources retain their indicative classification."""
        indicative_record = {
            "tool": "search_transport_options",
            "args": {"origin": "Delhi"},
            "status": "success",
            "result": {
                "origin": "Delhi",
                "options": [],
                "source_name": "Regional Transport Timetable Dataset",
                "source_type": "indicative_data",
                "freshness_status": "cached",
                "verification_status": "verified_curated_source",
            },
        }
        resp = {"reply": "Indicative timetables", "tool_executions": [indicative_record]}
        enriched = attach_provenance_to_response(resp, tool_executions=[indicative_record])

        prov = enriched["source_provenance"][0]
        self.assertEqual(prov["source_type"], "indicative_data")
        self.assertEqual(len(enriched["live_sources"]), 0)

    # =========================================================================
    # 25. DETERMINISTIC FALLBACK RESPONSE ENVELOPE
    # =========================================================================
    def test_25_deterministic_fallback_response_envelope(self):
        """Verifies deterministic fallback envelope includes all standard keys required by the frontend."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound
        mock_bound.invoke.side_effect = RuntimeError("Offline")

        res = central_agent.process_conversational_turn(
            "What is the weather in Katra?",
            session_id=self.session_id,
            llm=mock_llm,
        )
        required_keys = [
            "reply", "intent", "status", "session_id", "request", "plan",
            "itinerary", "recommendation", "action", "hotel", "budget_evaluation",
            "knowledge_sources", "tool_executions", "source_provenance", "live_sources",
            "partial_failure", "execution_mode",
        ]
        for k in required_keys:
            self.assertIn(k, res, f"Missing required envelope key: {k}")
        self.assertEqual(res["execution_mode"], "deterministic_fallback")

    # =========================================================================
    # 26. LLM RESPONSE ENVELOPE COMPATIBILITY
    # =========================================================================
    def test_26_llm_response_envelope_compatibility(self):
        """Verifies LLM orchestrated response envelope matches full schema contract."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        call_msg = MagicMock()
        call_msg.tool_calls = [{"name": "check_weather_guidance", "args": {"location": "Katra"}, "id": "c1"}]
        call_msg.content = ""

        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "Weather is pleasant."

        mock_bound.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            "Katra weather",
            session_id=self.session_id,
            llm=mock_llm,
        )
        required_keys = [
            "reply", "intent", "status", "session_id", "request", "plan",
            "itinerary", "recommendation", "action", "hotel", "budget_evaluation",
            "knowledge_sources", "tool_executions", "source_provenance", "live_sources",
            "partial_failure", "execution_mode",
        ]
        for k in required_keys:
            self.assertIn(k, res, f"Missing required envelope key in LLM turn: {k}")
        self.assertEqual(res["execution_mode"], "hybrid_llm")

    # =========================================================================
    # 27. SESSION ISOLATION
    # =========================================================================
    def test_27_session_isolation(self):
        """Verifies two separate session IDs maintain independent conversation histories."""
        sid1 = f"session-a-{uuid.uuid4().hex[:8]}"
        sid2 = f"session-b-{uuid.uuid4().hex[:8]}"
        session_store.create_session(sid1)
        session_store.create_session(sid2)

        central_agent.process_conversational_turn("Jai Mata Di from pilgrim 1", session_id=sid1)
        central_agent.process_conversational_turn("Namaste from pilgrim 2", session_id=sid2)

        msgs1 = session_store.get_messages(sid1)
        msgs2 = session_store.get_messages(sid2)

        texts1 = [m["content"] for m in msgs1]
        texts2 = [m["content"] for m in msgs2]

        self.assertTrue(any("pilgrim 1" in t for t in texts1))
        self.assertFalse(any("pilgrim 2" in t for t in texts1))
        self.assertTrue(any("pilgrim 2" in t for t in texts2))
        self.assertFalse(any("pilgrim 1" in t for t in texts2))

    # =========================================================================
    # 28. NO PRIVATE DATA LEAKS ACROSS SESSIONS
    # =========================================================================
    def test_28_no_private_data_leaks_across_sessions(self):
        """Verifies requirements and sensitive state in Session 1 do not leak to Session 2."""
        sid1 = f"leak-test-1-{uuid.uuid4().hex[:8]}"
        sid2 = f"leak-test-2-{uuid.uuid4().hex[:8]}"
        session_store.create_session(sid1, initial_state={"requirements": {"origin": "Bengaluru", "pax": 5, "budget": 50000}})
        session_store.create_session(sid2, initial_state={"requirements": {"origin": "Lucknow", "pax": 1}})

        sess1 = session_store.get_session(sid1)
        sess2 = session_store.get_session(sid2)

        self.assertEqual(sess1["state"]["requirements"]["origin"], "Bengaluru")
        self.assertEqual(sess2["state"]["requirements"]["origin"], "Lucknow")
        self.assertNotIn("budget", sess2["state"]["requirements"])

    # =========================================================================
    # 29. EXISTING BOOKING HANDOFF BEHAVIOR UNCHANGED
    # =========================================================================
    def test_29_existing_booking_handoff_behavior_unchanged(self):
        """Verifies booking intent with active requirements produces expected booking handoff card."""
        central_agent.process_conversational_turn(
            "Plan a 3 day trip from Chandigarh for 4 people",
            session_id=self.session_id,
        )
        res = central_agent.process_conversational_turn(
            "I want to proceed with booking",
            session_id=self.session_id,
        )
        self.assertEqual(res.get("action"), "NAVIGATE_TO_BOOKING")
        self.assertEqual(res.get("execution_mode"), "deterministic_booking")
        self.assertIn("Jai Mata Di", res.get("reply", ""))

    # =========================================================================
    # 30. EXISTING RPA AUTHORIZATION PROTECTIONS INTACT
    # =========================================================================
    def test_30_existing_rpa_authorization_protections_intact(self):
        """Verifies legacy and Central Agent RPA execution safeguards remain enforced end-to-end."""
        # Invoking execute_authorized_booking without explicit human grant must fail
        rec = central_agent._execute_single_tool_safe(
            "execute_authorized_booking",
            {"pax": 1, "dates": "2026-10-20"},
            session_id=self.session_id,
        )
        self.assertEqual(rec.status, "failure")
        self.assertTrue(rec.result.get("human_confirmation_required"))
        self.assertEqual(rec.result.get("status"), "BLOCKED")


if __name__ == "__main__":
    unittest.main()
