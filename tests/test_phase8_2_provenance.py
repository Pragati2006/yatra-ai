"""
tests/test_phase8_2_provenance.py
Exhaustive Verification Test Suite for Phase 8 Checkpoint 8.2:
Live Data Provenance Schema & Unified Response Envelope.

Covers all 33 verification requirements:
 1. Provenance creation.
 2. ISO 8601 timezone-aware timestamps.
 3. Missing optional metadata.
 4. Live API source classification.
 5. Cached source classification.
 6. Stale source classification.
 7. Static RAG classification.
 8. Curated data classification.
 9. Indicative hotel tariff classification.
10. Simulated booking classification.
11. Unavailable source handling.
12. Failed provider request handling.
13. Weather provenance integration.
14. Multi-location weather provenance.
15. Partial weather failure provenance.
16. RAG provenance integration.
17. Transport provenance integration.
18. Hotel provenance integration.
19. Mock availability provenance.
20. Mock booking provenance.
21. Duplicate source handling.
22. Unified response envelope compatibility.
23. Preservation of existing response fields.
24. Central AI Agent provenance propagation.
25. ToolMessage metadata propagation.
26. Deterministic fallback compatibility.
27. JSON serialization.
28. Session isolation.
29. Existing Phase 6 regression tests verification.
30. Existing Phase 7 regression tests verification.
31. Existing Phase 7.1 regression tests verification.
32. Existing Phase 8.1 regression tests verification.
33. Frontend payload contract compatibility.
"""

from datetime import datetime, timezone
import json
import unittest
from unittest.mock import MagicMock, patch

from agents import central_agent, coordinator, orchestrator, session_store
import utils.provenance as prov
from utils.provenance import (
    FreshnessStatus,
    ProvenanceRecord,
    SourceType,
    VerificationStatus,
    attach_provenance_to_response,
    create_provenance,
    deduplicate_provenance,
    extract_provenance_from_tool_result,
    extract_provenance_from_weather,
    get_utc_now_iso,
    normalize_freshness_status,
    normalize_source_type,
    normalize_verification_status,
    validate_provenance,
)
import weather


class TestPhase82Provenance(unittest.TestCase):
    """Exhaustive test suite for Live Data Provenance Schema & Unified Response Envelope."""

    # =========================================================================
    # 1–3. PROVENANCE CREATION & TIMESTAMP SCHEMA
    # =========================================================================

    def test_01_provenance_creation(self):
        """1. Verifies create_provenance builds a valid record with all required fields."""
        p = create_provenance(
            source_name="Open-Meteo Weather API",
            source_type=SourceType.LIVE_API,
            freshness_status=FreshnessStatus.LIVE,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API,
            source_url="https://open-meteo.com",
            source_tier="tier_2_open_api",
            location="Vaishno Devi Bhawan",
            disclaimer="Model-based mountain forecast.",
        )
        self.assertIsInstance(p, dict)
        self.assertEqual(p["source_name"], "Open-Meteo Weather API")
        self.assertEqual(p["source_type"], "live_api")
        self.assertEqual(p["freshness_status"], "live")
        self.assertEqual(p["verification_status"], "verified_external_api")
        self.assertEqual(p["source_url"], "https://open-meteo.com")
        self.assertEqual(p["location"], "Vaishno Devi Bhawan")

        valid, errors = validate_provenance(p)
        self.assertTrue(valid, f"Validation failed with errors: {errors}")

    def test_02_iso_8601_timezone_aware_timestamps(self):
        """2. Verifies retrieval_timestamp is ISO 8601 with explicit timezone offset."""
        ts = get_utc_now_iso()
        self.assertIn("T", ts)
        self.assertTrue("+" in ts or ts.endswith("Z"))
        parsed_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        self.assertIsNotNone(parsed_dt.tzinfo)

        # Naive timestamp passed to create_provenance is automatically offset
        p = create_provenance(
            source_name="Test Source",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
            retrieval_timestamp="2026-11-06T12:00:00",
        )
        self.assertTrue("+" in p["retrieval_timestamp"])

    def test_03_missing_optional_metadata(self):
        """3. Verifies missing optional fields remain None without inventing synthetic data."""
        p = create_provenance(
            source_name="Minimal Source",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_INTERNAL_KNOWLEDGE,
        )
        # Optional fields omitted from dictionary
        self.assertNotIn("data_timestamp", p)
        self.assertNotIn("source_url", p)
        self.assertNotIn("location", p)
        self.assertNotIn("disclaimer", p)
        valid, errors = validate_provenance(p)
        self.assertTrue(valid, f"Minimal record must be valid: {errors}")

    # =========================================================================
    # 4–12. CLASSIFICATION AND SAFETY INTEGRITY RULES
    # =========================================================================

    def test_04_live_api_source_classification(self):
        """4. Verifies live API source classification and normalization."""
        norm_type = normalize_source_type("live_api")
        self.assertEqual(norm_type, SourceType.LIVE_API.value)

        p = create_provenance(
            source_name="Live API Provider",
            source_type="live",
            freshness_status="live_forecast",
            verification_status="verified_external_api",
        )
        self.assertEqual(p["source_type"], "live_api")
        self.assertEqual(p["freshness_status"], "live")

    def test_05_cached_source_classification(self):
        """5. Verifies cached source classification is distinct from live."""
        p = create_provenance(
            source_name="Cached Endpoint",
            source_type=SourceType.CACHED_API,
            freshness_status=FreshnessStatus.CACHED,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
        )
        self.assertEqual(p["source_type"], "cached_api")
        self.assertEqual(p["freshness_status"], "cached")
        self.assertNotEqual(p["freshness_status"], "live")

    def test_06_stale_source_classification(self):
        """6. Verifies stale source classification."""
        p = create_provenance(
            source_name="Stale Dataset",
            source_type=SourceType.CACHED_API,
            freshness_status=FreshnessStatus.STALE,
            verification_status=VerificationStatus.UNVERIFIED,
        )
        self.assertEqual(p["freshness_status"], "stale")

    def test_07_static_rag_classification(self):
        """7. Verifies static RAG cannot be marked as live (anti-hallucination safeguard)."""
        p = create_provenance(
            source_name="SMVDSB History Document",
            source_type=SourceType.STATIC_RAG,
            freshness_status=FreshnessStatus.LIVE,  # Attempting to mark RAG as live
            verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE,
        )
        # Invariant enforced: static RAG cannot be live
        self.assertEqual(p["freshness_status"], "cached")

    def test_08_curated_data_classification(self):
        """8. Verifies curated catalog classification."""
        p = create_provenance(
            source_name="Regional Tourism Catalog",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
        )
        self.assertEqual(p["source_type"], "curated_data")
        self.assertEqual(p["verification_status"], "verified_curated_source")

    def test_09_indicative_hotel_tariff_classification(self):
        """9. Verifies indicative hotel tariff classification."""
        p = create_provenance(
            source_name="Katra Hotel Directory",
            source_type=SourceType.INDICATIVE_DATA,
            freshness_status=FreshnessStatus.CACHED,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
            disclaimer="Indicative base tariffs; subject to seasonal hotel confirmation.",
        )
        self.assertEqual(p["source_type"], "indicative_data")
        self.assertIn("Indicative base tariffs", p["disclaimer"])

    def test_10_simulated_booking_classification(self):
        """10. Verifies simulated booking responses must have verification_status='simulation_only'."""
        p = create_provenance(
            source_name="Local Mock Booking Portal",
            source_type=SourceType.SIMULATED_DATA,
            freshness_status=FreshnessStatus.SIMULATED,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API,  # Attempting to mark mock as verified external
        )
        # Invariant enforced: mock data must always be simulation_only
        self.assertEqual(p["verification_status"], "simulation_only")

    def test_11_unavailable_source_handling(self):
        """11. Verifies unavailable data cannot claim external verification."""
        p = {
            "source_name": "Dead API",
            "source_type": "live_api",
            "freshness_status": "unavailable",
            "verification_status": "verified_external_api",
            "retrieval_timestamp": get_utc_now_iso(),
        }
        valid, errors = validate_provenance(p)
        self.assertFalse(valid)
        self.assertTrue(any("cannot be marked as verified_external_api" in e for e in errors))

    def test_12_failed_provider_request_handling(self):
        """12. Verifies failed provider request yields unavailable status without false success."""
        failed_tool_res = {"status": "failed", "error": "Connection refused to upstream weather endpoint"}
        provs = extract_provenance_from_tool_result("check_weather_guidance", failed_tool_res)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["freshness_status"], "unavailable")
        self.assertEqual(provs[0]["verification_status"], "unverified")
        self.assertIn("Connection refused", provs[0]["disclaimer"])

    # =========================================================================
    # 13–20. DATA SOURCE PROVENANCE INTEGRATION
    # =========================================================================

    def test_13_weather_provenance_integration(self):
        """13. Verifies weather single-location output carries valid provenance."""
        live_mock_weather = {
            "location": "Vaishno Devi Bhawan",
            "elevation_m": 1585,
            "source": "forecast",
            "source_name": "Open-Meteo Weather API",
            "source_url": "https://open-meteo.com",
            "freshness_status": "live",
            "weather_type": "live_forecast",
            "verification_status": "verified_external_api",
            "retrieval_timestamp": get_utc_now_iso(),
            "data_timestamp": "2026-11-06T11:45+05:30",
            "disclaimer": "Mountain conditions can change rapidly.",
        }
        provs = extract_provenance_from_weather(live_mock_weather)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["source_name"], "Open-Meteo Weather API")
        self.assertEqual(provs[0]["source_type"], "live_api")
        self.assertEqual(provs[0]["freshness_status"], "live")
        self.assertEqual(provs[0]["location"], "Vaishno Devi Bhawan")

    def test_14_multi_location_weather_provenance(self):
        """14. Verifies multi-location weather preserves separate provenance for all locations."""
        mock_multi_weather = {
            "is_multi_location": True,
            "locations": [
                {"location": "Katra Town", "elevation_m": 750, "freshness_status": "live", "source_name": "Open-Meteo Weather API", "source_url": "https://open-meteo.com"},
                {"location": "Ardhkuwari", "elevation_m": 1400, "freshness_status": "live", "source_name": "Open-Meteo Weather API", "source_url": "https://open-meteo.com"},
                {"location": "Vaishno Devi Bhawan", "elevation_m": 1585, "freshness_status": "live", "source_name": "Open-Meteo Weather API", "source_url": "https://open-meteo.com"},
                {"location": "Bhairon Temple", "elevation_m": 2011, "freshness_status": "live", "source_name": "Open-Meteo Weather API", "source_url": "https://open-meteo.com"},
            ],
            "retrieval_timestamp": get_utc_now_iso(),
        }
        provs = extract_provenance_from_weather(mock_multi_weather)
        self.assertEqual(len(provs), 4)
        locations = [p["location"] for p in provs]
        self.assertIn("Katra Town", locations)
        self.assertIn("Ardhkuwari", locations)
        self.assertIn("Vaishno Devi Bhawan", locations)
        self.assertIn("Bhairon Temple", locations)

    def test_15_partial_weather_failure_provenance(self):
        """15. Verifies partial failure distinguishes live location from fallback location."""
        mock_partial = {
            "is_multi_location": True,
            "locations": [
                {"location": "Katra Town", "elevation_m": 750, "freshness_status": "live", "source_name": "Open-Meteo Weather API"},
                {"location": "Vaishno Devi Bhawan", "elevation_m": 1585, "freshness_status": "fallback", "source_name": "IMD Katra Climatological Normals"},
            ],
            "retrieval_timestamp": get_utc_now_iso(),
        }
        provs = extract_provenance_from_weather(mock_partial)
        self.assertEqual(len(provs), 2)
        katra_prov = next(p for p in provs if p["location"] == "Katra Town")
        bhawan_prov = next(p for p in provs if p["location"] == "Vaishno Devi Bhawan")

        self.assertEqual(katra_prov["freshness_status"], "live")
        self.assertEqual(katra_prov["source_type"], "live_api")

        self.assertEqual(bhawan_prov["freshness_status"], "fallback")
        self.assertEqual(bhawan_prov["source_type"], "curated_data")

    def test_16_rag_provenance_integration(self):
        """16. Verifies search_yatra_knowledge RAG provenance extraction."""
        rag_mock_result = {
            "relevant_found": True,
            "retrieved_at": get_utc_now_iso(),
            "sources": [
                {
                    "title": "RFID Registration Guidelines",
                    "source_name": "SMVDSB Official Portal",
                    "source_url": "https://www.maavaishnodevi.org/rfid",
                    "verification_status": "verified_official_source",
                    "source_notes": "Official Shrine Board mandatory rule.",
                    "domain": "registration_guidance",
                },
                {
                    "title": "Dogra Cultural Heritage",
                    "source_name": "Jammu Heritage Society",
                    "source_url": "https://jammuheritage.org",
                    "verification_status": "verified_general_source",
                    "domain": "cultural_heritage",
                }
            ]
        }
        provs = prov.extract_provenance_from_rag(rag_mock_result)
        self.assertEqual(len(provs), 2)
        self.assertEqual(provs[0]["source_type"], "static_rag")
        self.assertEqual(provs[0]["verification_status"], "verified_official_source")
        self.assertEqual(provs[0]["source_tier"], "tier_1_official")

        self.assertEqual(provs[1]["source_type"], "static_rag")
        self.assertEqual(provs[1]["verification_status"], "verified_curated_source")
        self.assertEqual(provs[1]["source_tier"], "tier_3_curated_catalog")

    def test_17_transport_provenance_integration(self):
        """17. Verifies search_transport_options returns indicative/curated provenance."""
        t_res = central_agent.search_transport_options.invoke({
            "origin": "Delhi",
            "start_date": "2026-11-15",
            "end_date": "2026-11-18",
            "pax": 2,
        })
        provs = extract_provenance_from_tool_result("search_transport_options", t_res)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["source_type"], "indicative_data")
        self.assertEqual(provs[0]["freshness_status"], "cached")
        self.assertIn("IRCTC", provs[0]["disclaimer"])

    def test_18_hotel_provenance_integration(self):
        """18. Verifies evaluate_yatra_plan returns hotel and transport provenance."""
        plan_mock_result = {
            "status": "PLAN_READY",
            "hotel": {"name": "Hotel Vaishno Devi Heights", "category": "Mid-Range", "price": 2400},
            "selected_options": {"transport": {"mode": "Train"}},
        }
        provs = extract_provenance_from_tool_result("evaluate_yatra_plan", plan_mock_result)
        self.assertGreaterEqual(len(provs), 2)
        domains = [p.get("domain") for p in provs]
        self.assertIn("transport", domains)
        self.assertIn("accommodation", domains)

    def test_19_mock_availability_provenance(self):
        """19. Verifies check_slot_availability identifies as simulated portal data."""
        avail_res = {
            "status": "AVAILABLE",
            "requested_date": "2026-10-20",
            "slots": [{"category": "Normal Darshan", "seats_available": 100}],
        }
        provs = extract_provenance_from_tool_result("check_slot_availability", avail_res)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["source_type"], "simulated_data")
        self.assertEqual(provs[0]["freshness_status"], "simulated")
        self.assertEqual(provs[0]["verification_status"], "simulation_only")
        self.assertIn("not an official Shri Mata Vaishno Devi Shrine Board reservation", provs[0]["disclaimer"])

    def test_20_mock_booking_provenance(self):
        """20. Verifies execute_authorized_booking identifies as mock RPA simulation."""
        booking_res = {
            "status": "CONFIRMED",
            "booking_id": "MOCK-YATRA-84729",
            "user_name": "Rohan Sharma",
            "total_price": 4640.0,
        }
        provs = extract_provenance_from_tool_result("execute_authorized_booking", booking_res)
        self.assertEqual(len(provs), 1)
        self.assertEqual(provs[0]["source_type"], "simulated_data")
        self.assertEqual(provs[0]["verification_status"], "simulation_only")
        self.assertIn("Simulated demonstration booking", provs[0]["disclaimer"])

    # =========================================================================
    # 21–23. DEDUPLICATION & ENVELOPE PRESERVATION
    # =========================================================================

    def test_21_duplicate_source_handling(self):
        """21. Verifies duplicate provenance records are removed without dropping distinct locations."""
        dupes = [
            {"source_name": "Open-Meteo Weather API", "source_type": "live_api", "location": "Katra Town"},
            {"source_name": "Open-Meteo Weather API", "source_type": "live_api", "location": "Katra Town"},  # exact duplicate
            {"source_name": "Open-Meteo Weather API", "source_type": "live_api", "location": "Vaishno Devi Bhawan"},  # distinct location
            {"source_name": "SMVDSB Official Portal", "source_type": "static_rag", "location": None},
            {"source_name": "SMVDSB Official Portal", "source_type": "static_rag", "location": None},  # duplicate
        ]
        cleaned = deduplicate_provenance(dupes)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned[0]["location"], "Katra Town")
        self.assertEqual(cleaned[1]["location"], "Vaishno Devi Bhawan")
        self.assertEqual(cleaned[2]["source_name"], "SMVDSB Official Portal")

    def test_22_unified_response_envelope_compatibility(self):
        """22. Verifies attach_provenance_to_response adds source_provenance and live_sources."""
        base_resp = {
            "reply": "🙏 Jai Mata Di! Weather is pleasant.",
            "intent": "WEATHER",
            "status": "SUCCESS",
            "session_id": "test_session_123",
            "weather": {
                "location": "Katra Town",
                "freshness_status": "live",
                "source": "forecast",
                "source_name": "Open-Meteo Weather API",
                "source_url": "https://open-meteo.com",
            }
        }
        res = attach_provenance_to_response(base_resp)
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)
        self.assertEqual(len(res["source_provenance"]), 1)
        self.assertEqual(len(res["live_sources"]), 1)
        self.assertEqual(res["live_sources"][0]["source_name"], "Open-Meteo Weather API")

    def test_23_preservation_of_existing_response_fields(self):
        """23. Verifies every existing top-level field is preserved intact."""
        rich_envelope = {
            "reply": "Complete plan ready.",
            "intent": "TRIP_PLANNING",
            "status": "PLAN_READY",
            "session_id": "sess_491",
            "request": {"origin": "Delhi", "pax": 2},
            "plan": {"status": "PLAN_READY"},
            "itinerary": [{"day": 1, "title": "Arrival in Katra"}],
            "recommendation": {"title": "Devotional Yatra"},
            "action": "NAVIGATE_TO_BOOKING",
            "hotel": {"name": "Hotel Katra Continental"},
            "budget_evaluation": {"total_cost": 8500, "is_feasible": True},
            "knowledge_sources": [{"title": "Yatra Rule 1", "source_url": "https://maavaishnodevi.org"}],
            "last_tourism_place": "Katra",
            "last_itinerary_context": {"day": 1},
        }
        res = attach_provenance_to_response(rich_envelope)
        for key in rich_envelope:
            self.assertIn(key, res)
            self.assertEqual(res[key], rich_envelope[key])
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)

    # =========================================================================
    # 24–28. AGENT PROPAGATION, FALLBACK, SERIALIZATION, SESSION ISOLATION
    # =========================================================================

    def test_24_central_ai_agent_provenance_propagation(self):
        """24. Verifies Central AI Agent tool-calling propagation of provenance."""
        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound_llm

        call_msg = MagicMock()
        call_msg.tool_calls = [
            {"name": "check_weather_guidance", "args": {"location": "Bhawan"}, "id": "call_w1"},
        ]
        final_msg = MagicMock()
        final_msg.tool_calls = []
        final_msg.content = "🙏 Bhawan weather is crisp and clear."
        mock_bound_llm.invoke.side_effect = [call_msg, final_msg]

        res = central_agent.process_conversational_turn(
            user_text="What is the weather at Bhawan?",
            llm=mock_llm,
        )
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)
        prov_sources = [p["source_name"] for p in res["source_provenance"]]
        self.assertTrue(any("Open-Meteo" in s or "IMD" in s for s in prov_sources))

    def test_25_tool_message_metadata_propagation(self):
        """25. Verifies ToolMessage content preserves structured provenance JSON."""
        t_res = central_agent.get_tourism_knowledge.invoke({"place": "Bhairavnath Temple"})
        self.assertIn("source_name", t_res)
        self.assertEqual(t_res["source_type"], "curated_data")
        # Ensure json.dumps passes cleanly for ToolMessage
        serialized = json.dumps(t_res)
        self.assertIn("Yatra AI Regional Tourism Catalog", serialized)

    def test_26_deterministic_fallback_compatibility(self):
        """26. Verifies deterministic fallback attaches valid provenance when LLM is unavailable."""
        res = orchestrator.orchestrate_conversational_turn(
            user_text="What is the weather in Katra?",
            llm=None,  # Forces deterministic fallback
        )
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)
        self.assertIsInstance(res["source_provenance"], list)
        self.assertGreater(len(res["source_provenance"]), 0)

    def test_27_json_serialization(self):
        """27. Verifies full response envelope serializes cleanly to JSON for FastAPI."""
        res = coordinator.process_weather_message("What is the weather at Bhawan?")
        json_str = json.dumps(res, default=str)
        self.assertIsInstance(json_str, str)
        deserialized = json.loads(json_str)
        self.assertIn("source_provenance", deserialized)
        self.assertIn("live_sources", deserialized)

    def test_28_session_isolation(self):
        """28. Verifies session isolation: independent sessions do not cross-contaminate provenance."""
        sess1 = session_store.create_session()
        sess2 = session_store.create_session()
        sid1 = sess1["session_id"]
        sid2 = sess2["session_id"]

        res1 = orchestrator.orchestrate_conversational_turn(
            user_text="What is the weather in Katra?",
            session_id=sid1,
            llm=None,
        )
        res2 = orchestrator.orchestrate_conversational_turn(
            user_text="What are the aarti timings?",
            session_id=sid2,
            llm=None,
        )

        self.assertEqual(res1["session_id"], sid1)
        self.assertEqual(res2["session_id"], sid2)
        self.assertNotEqual(res1["session_id"], res2["session_id"])
        # Ensure distinct provenance records per session
        p1_domains = [p.get("domain") for p in res1["source_provenance"]]
        p2_domains = [p.get("domain") for p in res2["source_provenance"]]
        self.assertIn("weather", p1_domains)
        self.assertNotIn("weather", p2_domains)

    # =========================================================================
    # 29–33. REGRESSION SUITES & FRONTEND COMPATIBILITY
    # =========================================================================

    def test_29_phase6_regression_verification(self):
        """29. Verifies Phase 6 check_weather_guidance and central agent tools pass."""
        w = central_agent.check_weather_guidance.invoke({"location": "Katra"})
        self.assertEqual(w["location"], "Katra")
        self.assertIn("source_name", w)

    def test_30_phase7_regression_verification(self):
        """30. Verifies Phase 7 search_yatra_knowledge RAG retrieval tool passes."""
        k = central_agent.search_yatra_knowledge.invoke({"query": "What are the rules for RFID card?"})
        self.assertIn("snippets", k)
        self.assertIn("sources", k)

    def test_31_phase7_1_regression_verification(self):
        """31. Verifies Phase 7.1 domain gate and false-positive prevention pass."""
        k_reject = central_agent.search_yatra_knowledge.invoke({"query": "How to visit Eiffel tower in Paris?"})
        self.assertFalse(k_reject.get("relevant_found", True))
        self.assertIn("disclaimer", k_reject)

    def test_32_phase8_1_regression_verification(self):
        """32. Verifies Phase 8.1 multi-location weather tool passes."""
        w_multi = weather.get_multi_location_weather("Compare Katra and Bhawan weather")
        self.assertTrue(w_multi.get("is_multi_location"))
        self.assertIsNotNone(w_multi.get("comparison"))

    def test_33_frontend_payload_contract_compatibility(self):
        """33. Verifies response envelope adheres strictly to React AIChat.jsx & MessageItem.jsx expectations."""
        res = central_agent.process_conversational_turn(
            user_text="Jai Mata Di",
            llm=None,
        )
        # React AIChat requires these core keys
        self.assertIn("reply", res)
        self.assertIn("intent", res)
        self.assertIn("status", res)
        self.assertIn("session_id", res)
        self.assertIn("knowledge_sources", res)
        # Checkpoint 8.2 adds source_provenance and live_sources
        self.assertIn("source_provenance", res)
        self.assertIn("live_sources", res)
        self.assertIsInstance(res["source_provenance"], list)
        self.assertIsInstance(res["live_sources"], list)


if __name__ == "__main__":
    unittest.main()
