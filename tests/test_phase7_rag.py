"""
tests/test_phase7_rag.py
Phase 7 Dedicated Verification Suite: Retrieval-Augmented Generation (RAG) Knowledge Foundation.

Covers all 25 Phase 7 verification requirements:
 1. Document ingestion
 2. Text extraction
 3. Metadata preservation
 4. Chunk creation
 5. Duplicate detection
 6. Embedding generation
 7. Vector indexing
 8. Semantic retrieval
 9. Metadata-filtered retrieval
10. Relevance thresholding
11. Empty-result handling
12. Source attribution
13. Source freshness metadata
14. Unsupported-question handling
15. Central-agent RAG tool invocation
16. Combined RAG and itinerary request
17. RAG and weather tool separation
18. Multi-turn knowledge follow-up
19. Document update and re-indexing
20. Document deletion
21. Malformed document handling
22. Retrieval failure handling
23. Session isolation
24. Existing booking handoff regression
25. Existing Phase 5 and Phase 6 regression
"""

import json
import math
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rag.chunker import SemanticSectionChunker
from rag.embeddings import DomainTermEmbeddingModel, MockEmbeddingModel, get_embedding_model
from rag.ingestion import IngestionPipeline, initialize_default_vector_store
from rag.retriever import YatraKnowledgeRetriever, DEFAULT_UNSUPPORTED_DISCLAIMER
from rag.schema import Chunk, Document, RetrievalResult
from rag.vector_store import VectorStore

from agents import central_agent, coordinator, session_store


class TestPhase7RAG(unittest.TestCase):
    """Comprehensive test suite for Phase 7 RAG Knowledge Foundation."""

    @classmethod
    def setUpClass(cls):
        # Build or load default vector store
        cls.retriever = YatraKnowledgeRetriever()

    def setUp(self):
        self.session_id = f"test-p7-{uuid.uuid4().hex[:10]}"
        session_store.create_session(session_id=self.session_id)

    def tearDown(self):
        try:
            session_store.delete_session(self.session_id)
        except Exception:
            pass

    # =========================================================================
    # 1. DOCUMENT INGESTION
    # =========================================================================
    def test_01_document_ingestion(self):
        """Verifies ingestion of a valid document increases document and chunk count."""
        store = VectorStore(dimension=256)
        embedder = MockEmbeddingModel(dim=256)
        chunker = SemanticSectionChunker(target_chunk_size=200, chunk_overlap=30)

        doc = Document(
            document_id="doc_test_ingest_01",
            title="Test Shrine History",
            content="### History\nThis is a sacred shrine in the hills.\n\n### Significance\nDevotees visit for inner peace.",
            domain="vaishno_devi_pilgrimage",
            category="history",
            source_name="SMVDSB Test",
            source_url="https://maavaishnodevi.org/test",
        )
        added = store.add_document(doc, embedder=embedder, chunker=chunker)
        self.assertTrue(added)
        self.assertEqual(len(store.list_documents()), 1)
        self.assertGreater(store.get_stats()["chunks_count"], 0)

    # =========================================================================
    # 2. TEXT EXTRACTION
    # =========================================================================
    def test_02_text_extraction(self):
        """Verifies document extraction correctly extracts text and headings."""
        chunker = SemanticSectionChunker(target_chunk_size=250)
        doc = Document(
            document_id="doc_extract_02",
            title="Ardhkuwari Story",
            content="### Garbh Joon\nMata Vaishno Devi meditated inside Garbh Joon cave for nine continuous months.",
            domain="vaishno_devi_pilgrimage",
            category="sacred_landmarks",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        chunks = chunker.chunk_document(doc)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Garbh Joon", chunks[0].text)
        self.assertIn("meditated inside Garbh Joon", chunks[0].text)

    # =========================================================================
    # 3. METADATA PRESERVATION
    # =========================================================================
    def test_03_metadata_preservation(self):
        """Verifies all required metadata fields are preserved in both document and chunks."""
        chunker = SemanticSectionChunker()
        doc = Document(
            document_id="doc_meta_03",
            title="Tarakote Marg Track",
            content="Tarakote Marg is a 14 km pedestrian alternative track to Bhawan.",
            domain="routes_and_trekking",
            category="trek_routes",
            source_name="SMVDSB Official",
            source_url="https://maavaishnodevi.org/tarakote",
            source_type="tier_1_official",
            publication_date="2024-03-01",
            last_verified="2026-11-06",
            content_version="1.0.0",
        )
        chunks = chunker.chunk_document(doc)
        self.assertEqual(len(chunks), 1)
        c_meta = chunks[0].metadata
        self.assertEqual(c_meta["domain"], "routes_and_trekking")
        self.assertEqual(c_meta["source_name"], "SMVDSB Official")
        self.assertEqual(c_meta["source_url"], "https://maavaishnodevi.org/tarakote")
        self.assertEqual(c_meta["source_type"], "tier_1_official")
        self.assertEqual(c_meta["last_verified"], "2026-11-06")

    # =========================================================================
    # 4. CHUNK CREATION
    # =========================================================================
    def test_04_chunk_creation(self):
        """Verifies structure-aware chunking preserves heading context and sentence boundaries."""
        chunker = SemanticSectionChunker(target_chunk_size=150, chunk_overlap=30, min_chunk_size=40)
        doc = Document(
            document_id="doc_chunk_04",
            title="Multi Section Guide",
            content="### Section A\nThis is paragraph one explaining Banganga holy bath details.\n\n### Section B\nThis is paragraph two explaining Charan Paduka footprints.",
            domain="vaishno_devi_pilgrimage",
            category="landmarks",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        chunks = chunker.chunk_document(doc)
        self.assertGreaterEqual(len(chunks), 2)
        headings = [c.heading for c in chunks]
        self.assertIn("Section A", headings)
        self.assertIn("Section B", headings)

    # =========================================================================
    # 5. DUPLICATE DETECTION
    # =========================================================================
    def test_05_duplicate_detection(self):
        """Verifies duplicate documents with identical content hash are skipped."""
        store = VectorStore(dimension=256)
        embedder = MockEmbeddingModel(dim=256)

        doc1 = Document(
            document_id="doc_dup_01",
            title="Aarti Timing Guide",
            content="Morning Aarti occurs from 6:20 AM to 8:00 AM every single day.",
            domain="vaishno_devi_pilgrimage",
            category="aarti",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        doc2 = Document(
            document_id="doc_dup_02",  # Different ID, but identical content
            title="Aarti Timing Duplicate",
            content="Morning Aarti occurs from 6:20 AM to 8:00 AM every single day.",
            domain="vaishno_devi_pilgrimage",
            category="aarti",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        added1 = store.add_document(doc1, embedder=embedder)
        added2 = store.add_document(doc2, embedder=embedder)

        self.assertTrue(added1)
        self.assertFalse(added2)  # Should reject duplicate
        self.assertEqual(len(store.list_documents()), 1)

    # =========================================================================
    # 6. EMBEDDING GENERATION
    # =========================================================================
    def test_06_embedding_generation(self):
        """Verifies DomainTermEmbeddingModel produces valid 256-dim L2-normalized float vectors."""
        embedder = DomainTermEmbeddingModel(dim=256)
        vec = embedder.embed_text("Mata Vaishno Devi Bhawan Aarti and Darshan")

        self.assertEqual(len(vec), 256)
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)
        # Empty string should yield zero vector without error
        zero_vec = embedder.embed_text("")
        self.assertEqual(len(zero_vec), 256)

    # =========================================================================
    # 7. VECTOR INDEXING
    # =========================================================================
    def test_07_vector_indexing(self):
        """Verifies vector store rebuilds index matrix, supports save and load from disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "test_vstore.json")
            store = VectorStore(dimension=256)
            embedder = DomainTermEmbeddingModel(dim=256)

            doc = Document(
                document_id="doc_index_07",
                title="Bhairavnath Story",
                content="Bhairavnath was granted a divine boon by Mata Vaishno Devi.",
                domain="vaishno_devi_pilgrimage",
                category="landmarks",
                source_name="SMVDSB",
                source_url="https://maavaishnodevi.org",
            )
            store.add_document(doc, embedder=embedder)
            store.save(file_path)

            loaded_store = VectorStore()
            success = loaded_store.load(file_path)
            self.assertTrue(success)
            self.assertEqual(len(loaded_store.list_documents()), 1)
            self.assertIn("doc_index_07", loaded_store._documents)

    # =========================================================================
    # 8. SEMANTIC RETRIEVAL
    # =========================================================================
    def test_08_semantic_retrieval(self):
        """Verifies natural language conceptual query matches relevant semantic document."""
        res = self.retriever.retrieve("Where did the goddess meditate for nine months?")
        self.assertTrue(res["relevant_found"])
        self.assertGreater(res["top_score"], 0.25)
        # Should retrieve Ardhkuwari / Garbh Joon documentation
        context_lower = res["context"].lower()
        self.assertTrue("ardhkuwari" in context_lower or "garbh joon" in context_lower or "vaishno" in context_lower)

    # =========================================================================
    # 9. METADATA-FILTERED RETRIEVAL
    # =========================================================================
    def test_09_metadata_filtered_retrieval(self):
        """Verifies metadata filtering restricts results to the requested domain."""
        res = self.retriever.retrieve("Tell me about Patnitop altitude and snow", domain="jk_regional_tourism")
        self.assertTrue(res["relevant_found"])
        for src in res["sources"]:
            self.assertEqual(src["domain"], "jk_regional_tourism")

    # =========================================================================
    # 10. RELEVANCE THRESHOLDING
    # =========================================================================
    def test_10_relevance_thresholding(self):
        """Verifies results scoring below relevance threshold are discarded."""
        # Unrelated query with high threshold should reject
        res = self.retriever.retrieve("Quantum computing entanglement algorithms", score_threshold=0.75)
        self.assertFalse(res["relevant_found"])
        self.assertEqual(res["results_count"], 0)

    # =========================================================================
    # 11. EMPTY-RESULT HANDLING
    # =========================================================================
    def test_11_empty_result_handling(self):
        """Verifies empty or whitespace query returns structured fallback with disclaimer."""
        res = self.retriever.retrieve("   ")
        self.assertFalse(res["relevant_found"])
        self.assertEqual(res["results_count"], 0)
        self.assertIn("1800-180-7198", res["disclaimer"])

    # =========================================================================
    # 12. SOURCE ATTRIBUTION
    # =========================================================================
    def test_12_source_attribution(self):
        """Verifies retrieved results contain verified source title, authority, and official URL."""
        res = self.retriever.retrieve("What are the Aarti timings?")
        self.assertTrue(res["relevant_found"])
        self.assertGreater(len(res["sources"]), 0)
        top_src = res["sources"][0]
        self.assertIn("title", top_src)
        self.assertIn("source_name", top_src)
        self.assertIn("source_url", top_src)
        self.assertTrue(top_src["source_url"].startswith("http"))

    # =========================================================================
    # 13. SOURCE FRESHNESS METADATA
    # =========================================================================
    def test_13_source_freshness_metadata(self):
        """Verifies retrieved sources contain last_verified date."""
        res = self.retriever.retrieve("How to register for yatra RFID pass?")
        self.assertTrue(res["relevant_found"])
        top_src = res["sources"][0]
        self.assertIn("last_verified", top_src)
        self.assertTrue(len(top_src["last_verified"]) >= 8)

    # =========================================================================
    # 14. UNSUPPORTED-QUESTION HANDLING
    # =========================================================================
    def test_14_unsupported_question_handling(self):
        """Verifies out-of-domain questions return relevant_found = False with official helpline."""
        res = self.retriever.retrieve("Who won the FIFA football world cup in 2022?")
        self.assertFalse(res["relevant_found"])
        self.assertIsNotNone(res["disclaimer"])
        self.assertIn("1800-180-7198", res["disclaimer"])

    # =========================================================================
    # 15. CENTRAL AGENT RAG TOOL INVOCATION
    # =========================================================================
    def test_15_central_agent_rag_tool_invocation(self):
        """Verifies search_yatra_knowledge tool returns structured RAG response."""
        tool_res = central_agent.search_yatra_knowledge.invoke({
            "query": "Is RFID card mandatory for Vaishno Devi?",
            "domain": "registration_guidance",
        })
        self.assertIsInstance(tool_res, dict)
        self.assertTrue(tool_res["relevant_found"])
        self.assertGreater(len(tool_res["sources"]), 0)
        self.assertIn("answer_context", tool_res)
        self.assertIn("confidence_assessment", tool_res)

    # =========================================================================
    # 16. COMBINED RAG AND ITINERARY REQUEST
    # =========================================================================
    def test_16_combined_rag_and_itinerary_request(self):
        """Verifies tool execution when user requests Patnitop knowledge and itinerary modification."""
        # 1. RAG query about Patnitop
        rag_res = central_agent.search_yatra_knowledge.invoke({"query": "Tell me about Patnitop altitude and attractions"})
        self.assertTrue(rag_res["relevant_found"])
        self.assertIn("Patnitop", rag_res["answer_context"])

        # 2. Itinerary modification tool
        itin_res = central_agent.modify_itinerary.invoke({"command": "Add Patnitop to Day 3"})
        self.assertEqual(itin_res["status"], "EDIT_APPLIED")
        day_3 = [d for d in itin_res["updated_itinerary"] if d.get("day_number") == 3 or d.get("day") == 3]
        self.assertTrue(len(day_3) > 0)
        day_3_text = json.dumps(day_3).lower()
        self.assertIn("patnitop", day_3_text)

    # =========================================================================
    # 17. RAG AND WEATHER TOOL SEPARATION
    # =========================================================================
    def test_17_rag_and_weather_tool_separation(self):
        """Verifies weather questions use check_weather_guidance while knowledge uses RAG."""
        # Weather tool
        w_res = central_agent.check_weather_guidance.invoke({"location": "Katra"})
        self.assertEqual(w_res["location"], "Katra")
        self.assertIn("low_c", w_res)

        # RAG tool
        rag_res = central_agent.search_yatra_knowledge.invoke({"query": "History of Banganga river"})
        self.assertTrue(rag_res["relevant_found"])
        self.assertNotIn("low_c", rag_res)

    # =========================================================================
    # 18. MULTI-TURN KNOWLEDGE FOLLOW-UP
    # =========================================================================
    def test_18_multi_turn_knowledge_follow_up(self):
        """Verifies multi-turn knowledge state persistence in session store."""
        # Turn 1: Discuss Ardhkuwari
        r1 = central_agent.process_conversational_turn(
            user_text="Tell me about Ardhkuwari Cave",
            session_id=self.session_id,
        )
        self.assertIn("session_id", r1)
        self.assertEqual(r1["session_id"], self.session_id)

        # Turn 2: Follow-up question referencing session context
        r2 = central_agent.process_conversational_turn(
            user_text="How long did Mata Rani stay there?",
            session_id=self.session_id,
        )
        self.assertIn("session_id", r2)
        messages = session_store.get_messages(self.session_id)
        self.assertGreaterEqual(len(messages), 4)

    # =========================================================================
    # 19. DOCUMENT UPDATE AND RE-INDEXING
    # =========================================================================
    def test_19_document_update_and_reindexing(self):
        """Verifies updating an existing document modifies its index and retrieved text."""
        store = VectorStore(dimension=256)
        embedder = DomainTermEmbeddingModel(dim=256)

        doc_v1 = Document(
            document_id="doc_update_19",
            title="Helpline Notice",
            content="Old emergency contact number: 01991-000000",
            domain="registration_guidance",
            category="helpline",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        store.add_document(doc_v1, embedder=embedder)

        doc_v2 = Document(
            document_id="doc_update_19",
            title="Helpline Notice Updated",
            content="New official emergency toll-free contact: 1800-180-7198 24x7",
            domain="registration_guidance",
            category="helpline",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
            content_version="2.0.0",
        )
        updated = store.update_document(doc_v2, embedder=embedder)
        self.assertTrue(updated)
        self.assertEqual(len(store.list_documents()), 1)

        # Search should find new content
        q_vec = embedder.embed_text("official emergency toll-free contact")
        results = store.search(q_vec, top_k=1, score_threshold=0.30)
        self.assertGreater(len(results), 0)
        self.assertIn("1800-180-7198", results[0].chunk.text)

    # =========================================================================
    # 20. DOCUMENT DELETION
    # =========================================================================
    def test_20_document_deletion(self):
        """Verifies deleting a document removes all its chunks from the vector store."""
        store = VectorStore(dimension=256)
        embedder = MockEmbeddingModel(dim=256)

        doc = Document(
            document_id="doc_del_20",
            title="Temporary Facility Notice",
            content="Temporary tent city established at Katra stadium.",
            domain="registration_guidance",
            category="facilities",
            source_name="SMVDSB",
            source_url="https://maavaishnodevi.org",
        )
        store.add_document(doc, embedder=embedder)
        self.assertEqual(len(store.list_documents()), 1)

        deleted = store.delete_document("doc_del_20")
        self.assertTrue(deleted)
        self.assertEqual(len(store.list_documents()), 0)
        self.assertEqual(store.get_stats()["chunks_count"], 0)

    # =========================================================================
    # 21. MALFORMED DOCUMENT HANDLING
    # =========================================================================
    def test_21_malformed_document_handling(self):
        """Verifies pipeline rejects documents missing required document_id or content."""
        pipeline = IngestionPipeline()
        malformed_doc = {"title": "Missing ID and content"}
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump([malformed_doc], f)
            tmp_path = f.name

        try:
            docs = pipeline.load_document_from_file(tmp_path)
            self.assertEqual(len(docs), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================================
    # 22. RETRIEVAL FAILURE HANDLING
    # =========================================================================
    def test_22_retrieval_failure_handling(self):
        """Verifies retriever gracefully recovers and returns structured disclaimer on internal exception."""
        faulty_store = MagicMock()
        faulty_store.search.side_effect = RuntimeError("Simulated vector index IO failure")
        retriever = YatraKnowledgeRetriever(vector_store=faulty_store)

        try:
            res = retriever.retrieve("Any query")
            # Should not raise exception
            self.assertFalse(res.get("relevant_found", True))
        except Exception as exc:
            self.fail(f"Retriever should have caught exception gracefully, but raised: {exc}")

    # =========================================================================
    # 23. SESSION ISOLATION
    # =========================================================================
    def test_23_session_isolation(self):
        """Verifies separate sessions maintain isolated message histories."""
        sid1 = f"iso-1-{uuid.uuid4().hex[:6]}"
        sid2 = f"iso-2-{uuid.uuid4().hex[:6]}"

        session_store.create_session(sid1)
        session_store.create_session(sid2)

        session_store.add_message(sid1, "user", "Message from user 1")
        session_store.add_message(sid2, "user", "Message from user 2")

        msgs1 = session_store.get_messages(sid1)
        msgs2 = session_store.get_messages(sid2)

        self.assertEqual(len(msgs1), 1)
        self.assertEqual(len(msgs2), 1)
        self.assertEqual(msgs1[0]["content"], "Message from user 1")
        self.assertEqual(msgs2[0]["content"], "Message from user 2")

        session_store.delete_session(sid1)
        session_store.delete_session(sid2)

    # =========================================================================
    # 24. EXISTING BOOKING HANDOFF REGRESSION
    # =========================================================================
    def test_24_existing_booking_handoff_regression(self):
        """Verifies booking intent triggers NAVIGATE_TO_BOOKING without executing RAG or RPA."""
        central_agent.process_conversational_turn(
            "Plan a 4 day trip from Delhi for 2 people by train",
            session_id=self.session_id,
        )
        res = central_agent.process_conversational_turn(
            "I want to proceed with booking",
            session_id=self.session_id,
        )
        self.assertEqual(res["action"], "NAVIGATE_TO_BOOKING")
        self.assertIn(res["status"], ("NAVIGATE_TO_BOOKING", "BOOKING_INTENT_TRIGGERED"))
        # Ensure no synthetic booking ID or unauthorized execution occurred
        self.assertNotIn("booking_id", res)

    # =========================================================================
    # 25. EXISTING PHASE 5 AND PHASE 6 REGRESSION
    # =========================================================================
    def test_25_existing_phase5_and_phase6_regression(self):
        """Verifies all required response envelope keys are present and correctly typed."""
        res = central_agent.process_conversational_turn(
            user_text="What are the free community facilities and medical centers at Vaishno Devi?",
            session_id=self.session_id,
        )
        required_keys = [
            "reply", "intent", "status", "session_id", "request",
            "plan", "itinerary", "recommendation", "action", "hotel",
            "budget_evaluation", "knowledge_sources",
        ]
        for key in required_keys:
            self.assertIn(key, res, f"Envelope missing critical key: {key}")

        self.assertIsInstance(res["reply"], str)
        self.assertIsInstance(res["knowledge_sources"], list)
        self.assertTrue(len(res["reply"]) > 20)
        self.assertIn("Jai Mata Di", res["reply"])


if __name__ == "__main__":
    unittest.main()
