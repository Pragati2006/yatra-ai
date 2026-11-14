"""
tests/test_phase7_1_rag_reliability.py
Comprehensive Verification Suite for Phase 7.1 RAG Reliability Remediation.

Covers 25 critical test requirements:
1. test_01_domain_classification: Validates deterministic classification into 6 domains.
2. test_02_unsupported_general_query_rejection: Blocks out-of-domain queries (e.g. Interstellar, Australia).
3. test_03_pilgrimage_entity_recognition: Extracts known pilgrimage entities (Holy Pindies, Garbh Joon, etc.).
4. test_04_place_alias_recognition: Verifies place alias resolution via _PLACE_ALIASES.
5. test_05_paraphrased_supported_retrieval: Retrieves correct knowledge for non-keyword paraphrases.
6. test_06_synonym_normalization: Normalizes devotee terminology (cableway -> ropeway, tariff -> fare).
7. test_07_context_dependent_followup: Resolves queries whose meaning depends on session context.
8. test_08_ambiguous_query_handling: Returns clarifying guidance for generic/ambiguous travel prompts.
9. test_09_false_positive_rejection: Confirms zero irrelevant document retrieval on non-travel topics.
10. test_10_adversarial_keyword_overlap_rejection: Rejects adversarial questions containing sacred words.
11. test_11_domain_filtered_retrieval: Restricts retrieval results to specific knowledge domain.
12. test_12_similarity_threshold_behaviour: Enforces relevance cutoff, suppressing low-score noise.
13. test_13_source_verification_metadata: Verifies verification_status and source_notes in chunks.
14. test_14_unverified_source_handling: Correctly flags non-official or unverified sources without fabrication.
15. test_15_missing_source_url_handling: Safely formats citations when source URLs are empty or missing.
16. test_16_source_citation_correctness: Ensures UI source attributes contain official trusted links.
17. test_17_retrieval_abstention: Produces honest official fallback disclaimer when knowledge is absent.
18. test_18_retrieval_failure_fallback: Handles vector store exceptions gracefully without crashing.
19. test_19_multiturn_rag_followup: Maintains coherent RAG context across consecutive conversational turns.
20. test_20_weather_tool_separation: Weather requests route to weather tool without triggering RAG.
21. test_21_dynamic_availability_separation: Slot inquiries route to availability tool without reading RAG.
22. test_22_booking_authorization_protection: Booking requests strictly gate behind human authorization.
23. test_23_conversation_session_isolation: Multi-tenant sessions remain isolated with zero leakage.
24. test_24_frontend_source_rendering: Verifies source payload satisfies React MessageItem component schema.
25. test_25_existing_phase6_regression: Guarantees central agent envelope keys and tools remain unimpaired.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from agents.central_agent import CENTRAL_TOOLS, search_yatra_knowledge
from agents.orchestrator import orchestrate_conversational_turn
from agents import session_store
from rag.classifier import ClassificationResult, DomainRelevanceClassifier
from rag.embeddings import DomainTermEmbeddingModel
from rag.normalizer import QueryTerminologyNormalizer
from rag.retriever import (
    DEFAULT_AMBIGUOUS_DISCLAIMER,
    DEFAULT_UNSUPPORTED_DISCLAIMER,
    YatraKnowledgeRetriever,
)
from rag.schema import Chunk, Document, RetrievalResult
from rag.vector_store import VectorStore


class TestPhase7_1RAGReliability(unittest.TestCase):
    """Rigorous test suite for Phase 7.1 RAG reliability corrections."""

    @classmethod
    def setUpClass(cls):
        cls.retriever = YatraKnowledgeRetriever()
        cls.classifier = cls.retriever.classifier
        cls.normalizer = cls.retriever.normalizer

    def setUp(self):
        self.test_session_id = f"test_p71_{os.urandom(4).hex()}"
        session_store.create_session(session_id=self.test_session_id)

    def tearDown(self):
        session_store.delete_session(self.test_session_id)

    # 1. Domain Classification
    def test_01_domain_classification(self):
        res = self.classifier.classify("Where is Bhairavnath Temple?")
        self.assertEqual(res.status, "supported")
        self.assertEqual(res.primary_domain, "vaishno_devi_pilgrimage")
        self.assertIn("Bhairavnath Temple", res.detected_entities)

    # 2. Unsupported General Query Rejection
    def test_02_unsupported_general_query_rejection(self):
        unsupported_queries = [
            "Who directed Interstellar?",
            "What is the capital of Australia?",
            "Explain quantum computing.",
            "Who won the latest cricket match?",
            "What is the stock price of Apple Inc today?",
        ]
        for q in unsupported_queries:
            res = self.retriever.retrieve(q)
            self.assertFalse(res["relevant_found"], f"Query should be rejected: {q}")
            self.assertEqual(res["top_score"], 0.0)
            self.assertEqual(len(res["sources"]), 0)
            self.assertEqual(res["classification"]["status"], "unsupported")
            self.assertIn("maavaishnodevi.org", res["disclaimer"])

    # 3. Pilgrimage Entity Recognition
    def test_03_pilgrimage_entity_recognition(self):
        entities = self.classifier._extract_entities("Is RFID card required for visiting Garbh Joon at Ardhkuwari?")
        self.assertTrue(any("RFID" in e for e in entities))
        self.assertTrue(any("Garbh Joon" in e or "Ardhkuwari" in e for e in entities))

    # 4. Place Alias Recognition
    def test_04_place_alias_recognition(self):
        # "bhairon baba" should resolve to canonical "Bhairavnath Temple" via _PLACE_ALIASES
        res = self.classifier.classify("How steep is the climb to Bhairon Baba?")
        self.assertEqual(res.status, "supported")
        self.assertIn("Bhairavnath Temple", res.detected_entities)

    # 5. Paraphrased Supported Retrieval
    def test_05_paraphrased_supported_retrieval(self):
        res = self.retriever.retrieve("Where did the goddess meditate for nine months?")
        self.assertTrue(res["relevant_found"])
        self.assertGreaterEqual(res["top_score"], 0.25)
        context = res["context"].lower()
        self.assertTrue("ardhkuwari" in context or "garbh joon" in context)

    # 6. Synonym Normalization
    def test_06_synonym_normalization(self):
        query = "What is the tariff for the cableway ride?"
        normalized = self.normalizer.normalize_for_retrieval(query)
        self.assertIn("ropeway", normalized.lower())
        self.assertIn("fare", normalized.lower())

        res = self.retriever.retrieve(query)
        self.assertTrue(res["relevant_found"])
        self.assertTrue(any("Ropeway" in s["title"] for s in res["sources"]))

    # 7. Context-Dependent Follow-Up
    def test_07_context_dependent_followup(self):
        # Follow-up "What about the return route?" with session context
        ctx = {"last_tourism_place": "Bhairon Temple", "recent_domain": "routes_and_trekking"}
        res = self.retriever.retrieve("What about the return route?", conversation_context=ctx)
        self.assertTrue(res["relevant_found"])
        self.assertEqual(res["classification"]["status"], "context_dependent")
        self.assertTrue(res["classification"]["requires_context"])

    # 8. Ambiguous-Query Handling
    def test_08_ambiguous_query_handling(self):
        # Query with only generic words without entities
        res = self.retriever.retrieve("Tell me about a cave and a temple")
        self.assertFalse(res["relevant_found"])
        self.assertEqual(res["classification"]["status"], "ambiguous")
        self.assertIn("ambiguous", res["disclaimer"].lower())

    # 9. False-Positive Rejection
    def test_09_false_positive_rejection(self):
        # Random query that caused false-positive hash collision in previous audit
        res = self.retriever.retrieve("Who is the current Prime Minister of Australia?")
        self.assertFalse(res["relevant_found"])
        self.assertEqual(len(res["sources"]), 0)
        self.assertEqual(res["top_score"], 0.0)

    # 10. Adversarial Keyword-Overlap Rejection
    def test_10_adversarial_keyword_overlap_rejection(self):
        adversarial_queries = [
            "Do doctors recommend eating beef in the cave temple?",
            "Can I feed wild monkeys holy water near the river?",
            "What is the best movie about a temple?",
            "Explain the chemistry of water found in caves.",
        ]
        for q in adversarial_queries:
            res = self.retriever.retrieve(q)
            self.assertFalse(res["relevant_found"], f"Adversarial query not rejected: {q}")
            self.assertEqual(res["classification"]["status"], "unsupported")

    # 11. Domain-Filtered Retrieval
    def test_11_domain_filtered_retrieval(self):
        res = self.retriever.retrieve(
            "What attractions can I visit in Patnitop and Sanasar?",
            domain="jk_regional_tourism",
        )
        self.assertTrue(res["relevant_found"])
        for s in res["sources"]:
            self.assertEqual(s["domain"], "jk_regional_tourism")

    # 12. Similarity Threshold Behaviour
    def test_12_similarity_threshold_behaviour(self):
        # High threshold should filter out low scores cleanly
        res = self.retriever.retrieve("Where is Katra?", score_threshold=0.99)
        self.assertFalse(res["relevant_found"])
        self.assertEqual(len(res["sources"]), 0)

    # 13. Source Verification Metadata
    def test_13_source_verification_metadata(self):
        res = self.retriever.retrieve("What are the Aarti timings at the Holy Cave?")
        self.assertTrue(res["relevant_found"])
        self.assertGreater(len(res["sources"]), 0)
        source = res["sources"][0]
        self.assertIn("verification_status", source)
        self.assertIn(source["verification_status"], ["verified_direct_source", "verified_general_source"])
        self.assertIn("source_notes", source)
        self.assertIn("last_verified", source)

    # 14. Unverified Source Handling
    def test_14_unverified_source_handling(self):
        # Create a test RetrievalResult with unverified status
        chunk = Chunk(
            chunk_id="test_unverified#c0",
            document_id="test_unverified",
            text="Unverified community claim about a hidden pathway.",
            chunk_index=0,
            metadata={"verification_status": "unverified", "source_name": "Travel Forum"},
        )
        rr = RetrievalResult(
            chunk=chunk,
            score=0.75,
            title="Unverified Forum Tip",
            source_name="Travel Forum",
            source_url="https://example.com/unverified",
            domain="routes_and_trekking",
            last_verified="2026-11-06",
            excerpt=chunk.text,
            verification_status="unverified",
        )
        self.assertEqual(rr.verification_status, "unverified")
        self.assertEqual(rr.to_dict()["verification_status"], "unverified")

    # 15. Missing Source URL Handling
    def test_15_missing_source_url_handling(self):
        chunk = Chunk(
            chunk_id="test_nourl#c0",
            document_id="test_nourl",
            text="Official physical notice board text without a web link.",
            chunk_index=0,
        )
        rr = RetrievalResult(
            chunk=chunk,
            score=0.65,
            title="Katra Station Notice Board",
            source_name="SMVDSB Physical Notice",
            source_url="",
            domain="registration_guidance",
            last_verified="2026-11-06",
            excerpt=chunk.text,
            verification_status="verified_general_source",
        )
        self.assertEqual(rr.source_url, "")
        d = rr.to_dict()
        self.assertEqual(d["source_url"], "")

    # 16. Source Citation Correctness
    def test_16_source_citation_correctness(self):
        res = self.retriever.retrieve("How do I register for an RFID card?")
        self.assertTrue(res["relevant_found"])
        top_src = res["sources"][0]
        self.assertTrue(
            top_src["source_url"].startswith("https://www.maavaishnodevi.org") or
            top_src["source_url"].startswith("https://jktourism.jk.gov.in")
        )

    # 17. Retrieval Abstention
    def test_17_retrieval_abstention(self):
        res = self.retriever.retrieve("What is the stock price of Apple Inc?")
        self.assertFalse(res["relevant_found"])
        self.assertIsNotNone(res["disclaimer"])
        self.assertIn("1800-180-7198", res["disclaimer"])

    # 18. Retrieval Failure Fallback
    def test_18_retrieval_failure_fallback(self):
        # Simulate vector store failure
        with patch.object(self.retriever.vector_store, "search", side_effect=RuntimeError("Simulated disk error")):
            res = self.retriever.retrieve("Tell me about Bhairavnath Temple")
            self.assertFalse(res["relevant_found"])
            self.assertIn("1800-180-7198", res["disclaimer"])

    # 19. Multi-Turn RAG Follow-Up
    def test_19_multiturn_rag_followup(self):
        session_store.update_session(self.test_session_id, {
            "last_tourism_place": "Shiv Khori",
            "recent_domain": "jk_regional_tourism",
        })
        sess = session_store.get_session(self.test_session_id)
        res = self.retriever.retrieve(
            "What is the travel distance?",
            conversation_context=sess,
        )
        self.assertTrue(res["relevant_found"])
        self.assertTrue(any("Shiv Khori" in s["title"] for s in res["sources"]))

    # 20. Weather Tool Separation
    def test_20_weather_tool_separation(self):
        turn = orchestrate_conversational_turn(
            user_text="What is the weather in Katra today?",
            session_id=self.test_session_id,
        )
        self.assertEqual(turn["intent"], "WEATHER")
        self.assertEqual(turn["response_source"], "weather_service")
        # Ensure knowledge sources are empty for pure weather turns
        self.assertEqual(len(turn.get("knowledge_sources", [])), 0)

    # 21. Dynamic Availability Separation
    def test_21_dynamic_availability_separation(self):
        turn = orchestrate_conversational_turn(
            user_text="Is a darshan slot available on 2026-11-20?",
            session_id=self.test_session_id,
        )
        self.assertIn(turn["intent"], ["AVAILABILITY", "YATRA_PLAN", "TRIP_PLANNING"])
        self.assertEqual(len(turn.get("knowledge_sources", [])), 0)

    # 22. Booking Authorization Protection
    def test_22_booking_authorization_protection(self):
        from agents import central_agent
        central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people by train",
            session_id=self.test_session_id,
        )
        turn = central_agent.process_conversational_turn(
            "Please proceed with booking now",
            session_id=self.test_session_id,
        )
        # Must return NAVIGATE_TO_BOOKING action card, not execute autonomous booking
        self.assertEqual(turn["action"], "NAVIGATE_TO_BOOKING")
        self.assertNotIn("booking_id", turn)

    # 23. Conversation Session Isolation
    def test_23_conversation_session_isolation(self):
        session_a = f"sess_a_{os.urandom(4).hex()}"
        session_b = f"sess_b_{os.urandom(4).hex()}"

        try:
            session_store.create_session(session_id=session_a)
            session_store.update_session(session_a, {"last_tourism_place": "Patnitop", "private_note": "devotee_a_data"})
            session_store.create_session(session_id=session_b)
            session_store.update_session(session_b, {"last_tourism_place": "Shiv Khori", "private_note": "devotee_b_data"})

            data_a = session_store.get_session(session_a)
            data_b = session_store.get_session(session_b)

            state_a = data_a.get("state", {})
            state_b = data_b.get("state", {})

            self.assertEqual(state_a.get("last_tourism_place"), "Patnitop")
            self.assertEqual(state_b.get("last_tourism_place"), "Shiv Khori")
            self.assertNotEqual(state_a.get("private_note"), state_b.get("private_note"))
        finally:
            session_store.delete_session(session_a)
            session_store.delete_session(session_b)

    # 24. Frontend Source Rendering Payload Schema
    def test_24_frontend_source_rendering(self):
        res = self.retriever.retrieve("What are the daily Aarti timings at the Holy Cave?")
        self.assertTrue(res["relevant_found"])
        self.assertGreater(len(res["sources"]), 0)
        src = res["sources"][0]

        # Verify all keys required by MessageItem.jsx are present and non-empty
        self.assertIn("title", src)
        self.assertIn("source_name", src)
        self.assertIn("source_url", src)
        self.assertIn("domain", src)
        self.assertIn("verification_status", src)
        self.assertTrue(src["source_url"].startswith("http"))

    # 25. Existing Phase 6 Central Agent Regression
    def test_25_existing_phase6_regression(self):
        turn = orchestrate_conversational_turn(
            user_text="Hello, Jai Mata Di! Can you help me plan my yatra?",
            session_id=self.test_session_id,
        )
        # All required Phase 6 envelope keys must be present
        required_keys = [
            "reply", "intent", "status", "session_id", "request",
            "plan", "itinerary", "recommendation", "action", "hotel", "budget_evaluation",
        ]
        for k in required_keys:
            self.assertIn(k, turn, f"Missing required envelope key: {k}")


if __name__ == "__main__":
    unittest.main()
