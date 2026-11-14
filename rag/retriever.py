"""
rag/retriever.py
Staged Knowledge Retrieval Engine for Yatra AI.

Implements a staged retrieval process:
User Query
    ↓
Context Resolution
    ↓
Domain Relevance Gate (DomainRelevanceClassifier)
    ↓
Synonym & Terminology Normalization (QueryTerminologyNormalizer)
    ↓
Domain/Entity Filtering
    ↓
Vector Similarity Retrieval (NumPy Cosine Dot-Product)
    ↓
Relevance Assessment & Thresholding
    ↓
Duplicate Suppression
    ↓
Source Validation & Context Assembly
    ↓
Central Agent Response
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from rag.classifier import ClassificationResult, DomainRelevanceClassifier
from rag.embeddings import BaseEmbeddingModel, get_embedding_model
from rag.ingestion import initialize_default_vector_store
from rag.normalizer import QueryTerminologyNormalizer
from rag.schema import RetrievalResult
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Official Shrine Board fallback disclaimer when knowledge is unavailable or unsupported
DEFAULT_UNSUPPORTED_DISCLAIMER = (
    "🙏 **Jai Mata Di!** The Yatra AI verified knowledge base does not contain sufficient reliable "
    "information to answer this specific query. To ensure your pilgrimage is safe and based on current rules, "
    "please consult the official Shri Mata Vaishno Devi Shrine Board portal at [maavaishnodevi.org](https://www.maavaishnodevi.org) "
    "or call the 24x7 toll-free helpline at **1800-180-7198**."
)

DEFAULT_AMBIGUOUS_DISCLAIMER = (
    "🙏 **Jai Mata Di!** Your query appears ambiguous or mentions general travel/religious words without a "
    "specific pilgrimage landmark. Please specify the destination or aspect you would like information on "
    "(e.g., *Bhairavnath Temple*, *Ardhkuwari Garbh Joon*, *RFID Registration*, *Patnitop*, *Shiv Khori*, or *Aarti Timings*)."
)


class YatraKnowledgeRetriever:
    """
    High-level staged knowledge retrieval engine for Yatra AI.
    Combines domain classification, terminology normalization, exact cosine vector search,
    relevance assessment, deduplication, and verified source provenance.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[BaseEmbeddingModel] = None,
        classifier: Optional[DomainRelevanceClassifier] = None,
        normalizer: Optional[QueryTerminologyNormalizer] = None,
        default_top_k: int = 3,
        relevance_threshold: float = 0.25,
        max_context_chars: int = 1500,
    ):
        self.vector_store = vector_store or initialize_default_vector_store()
        self.embedder = embedder or get_embedding_model("domain_term")
        self.classifier = classifier or DomainRelevanceClassifier()
        self.normalizer = normalizer or QueryTerminologyNormalizer()
        self.default_top_k = default_top_k
        self.relevance_threshold = relevance_threshold
        self.max_context_chars = max_context_chars

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full staged retrieval pipeline for a user query.

        Args:
            query: User's raw natural-language question.
            top_k: Maximum number of chunks to return (defaults to self.default_top_k).
            score_threshold: Minimum cosine similarity threshold (defaults to self.relevance_threshold).
            domain: Optional domain filter override.
            category: Optional category filter override.
            source_type: Optional source tier filter ('tier_1_official', etc.).
            conversation_context: Optional session context (e.g. last_tourism_place, recent_domain).

        Returns:
            Dict containing:
            - 'relevant_found': bool
            - 'context': str formatted evidence blocks
            - 'sources': list of source attribution dictionaries
            - 'top_score': float
            - 'results_count': int
            - 'classification': Dict of domain classification outcome
            - 'normalized_query': str
            - 'disclaimer': Optional[str]
            - 'retrieved_at': str (ISO 8601)
        """
        cleaned_query = (query or "").strip()
        k = top_k if top_k is not None else self.default_top_k
        threshold = score_threshold if score_threshold is not None else self.relevance_threshold
        now_iso = datetime.now(timezone.utc).isoformat()

        cache_key = f"{cleaned_query.lower()}|{domain or ''}|{category or ''}|{k}|{threshold}"
        if not conversation_context and cache_key in _RAG_QUERY_CACHE:
            cached = dict(_RAG_QUERY_CACHE[cache_key])
            cached["retrieved_at"] = now_iso
            return cached

        if not cleaned_query:
            return {
                "relevant_found": False,
                "context": "",
                "sources": [],
                "top_score": 0.0,
                "results_count": 0,
                "classification": {
                    "status": "unsupported",
                    "rationale": "Empty query",
                },
                "normalized_query": "",
                "disclaimer": DEFAULT_UNSUPPORTED_DISCLAIMER,
                "retrieved_at": now_iso,
            }

        # Step 1: Domain Relevance Gate
        classification: ClassificationResult = self.classifier.classify(
            cleaned_query,
            conversation_context=conversation_context,
        )

        # If an explicit domain filter was requested by caller, honor it over default classifier rejection
        if domain and classification.status == "unsupported":
            classification.status = "supported"
            classification.primary_domain = domain
            classification.rationale = f"Explicit domain override provided by caller: {domain}"

        # Reject unsupported questions immediately (anti-collision guard)
        if classification.status == "unsupported":
            logger.info(
                "RAG Gate REJECTED query '%s' as unsupported: %s",
                cleaned_query,
                classification.rationale,
            )
            unsupported_res = {
                "relevant_found": False,
                "context": "",
                "sources": [],
                "top_score": 0.0,
                "results_count": 0,
                "classification": classification.to_dict(),
                "normalized_query": cleaned_query,
                "disclaimer": DEFAULT_UNSUPPORTED_DISCLAIMER,
                "retrieved_at": now_iso,
            }
            try:
                from utils.provenance import extract_provenance_from_rag
                unsupported_res["source_provenance"] = extract_provenance_from_rag(unsupported_res)
            except Exception:
                unsupported_res["source_provenance"] = []
            return unsupported_res

        # Handle purely ambiguous questions
        if classification.status == "ambiguous":
            logger.info("RAG Gate classified query '%s' as ambiguous", cleaned_query)
            ambiguous_res = {
                "relevant_found": False,
                "context": "",
                "sources": [],
                "top_score": 0.0,
                "results_count": 0,
                "classification": classification.to_dict(),
                "normalized_query": cleaned_query,
                "disclaimer": DEFAULT_AMBIGUOUS_DISCLAIMER,
                "retrieved_at": now_iso,
            }
            try:
                from utils.provenance import extract_provenance_from_rag
                ambiguous_res["source_provenance"] = extract_provenance_from_rag(ambiguous_res)
            except Exception:
                ambiguous_res["source_provenance"] = []
            return ambiguous_res

        # Step 2: Query Normalization for Retrieval
        normalized_query = self.normalizer.normalize_for_retrieval(cleaned_query)

        # Context-dependent query expansion if entity is available from session context
        search_query_text = normalized_query
        ctx_entity = None
        if classification.requires_context and classification.detected_entities:
            ctx_entity = classification.detected_entities[0]
        elif conversation_context:
            st = conversation_context.get("state") or {} if isinstance(conversation_context, dict) else {}
            ctx_entity = (
                conversation_context.get("last_tourism_place")
                or st.get("last_tourism_place")
                or conversation_context.get("destination")
                or (st.get("requirements") or {}).get("destination")
            )

        if ctx_entity and str(ctx_entity).lower() not in normalized_query.lower():
            search_query_text = f"{ctx_entity} {normalized_query}"
        else:
            # Default regional grounding: only if query is bare/vague without specific facility or topic terms
            known_entities = ["vaishno", "devi", "katra", "jammu", "patnitop", "shiv khori", "bhairav", "kashmir", "srinagar"]
            facility_keywords = [
                "wheelchair", "langar", "bhojanalaya", "locker", "cloakroom", "prohibit", "banned",
                "battery", "palki", "palanquin", "rfid", "parchi", "helicopter", "ropeway", "medical",
                "emergency", "food", "trek", "trekking", "night", "clothes", "clothing", "dress code",
                "photo id", "aadhaar", "passport", "registration"
            ]
            has_topical_signal = any(t in normalized_query.lower() for t in facility_keywords)
            if not any(k in normalized_query.lower() for k in known_entities) and not has_topical_signal:
                search_query_text = f"Vaishno Devi Katra {normalized_query}"

        # Step 3: Embed Normalized Query
        query_vec = self.embedder.embed_text(search_query_text)

        # Step 4: Metadata Filtering
        target_domain = domain

        def metadata_filter(meta: Dict[str, Any]) -> bool:
            if target_domain and meta.get("domain") != target_domain:
                return False
            if category and meta.get("category") != category:
                return False
            if source_type and meta.get("source_type") != source_type:
                return False
            return True

        filter_fn = metadata_filter if (target_domain or category or source_type) else None

        # Step 5: Vector Similarity Retrieval
        try:
            raw_results = self.vector_store.search(
                query_vec=query_vec,
                top_k=k * 2,
                score_threshold=threshold,
                filter_fn=filter_fn,
            )
            # If high-confidence domain filter yielded 0 results, retry without domain restriction
            if not raw_results and filter_fn and target_domain and not domain:
                raw_results = self.vector_store.search(
                    query_vec=query_vec,
                    top_k=k * 2,
                    score_threshold=threshold,
                    filter_fn=None,
                )
        except Exception as exc:
            logger.error("VectorStore search failed: %s", exc)
            return {
                "relevant_found": False,
                "context": "",
                "sources": [],
                "top_score": 0.0,
                "results_count": 0,
                "classification": classification.to_dict(),
                "normalized_query": normalized_query,
                "disclaimer": DEFAULT_UNSUPPORTED_DISCLAIMER,
                "retrieved_at": now_iso,
            }

        if not raw_results:
            logger.info("RAG query '%s' yielded 0 chunks above threshold %.2f", cleaned_query, threshold)
            return {
                "relevant_found": False,
                "context": "",
                "sources": [],
                "top_score": 0.0,
                "results_count": 0,
                "classification": classification.to_dict(),
                "normalized_query": normalized_query,
                "disclaimer": DEFAULT_UNSUPPORTED_DISCLAIMER,
                "retrieved_at": now_iso,
            }

        # Step 6: Relevance Assessment & Duplicate Suppression
        deduped_results: List[RetrievalResult] = []
        seen_keys = set()

        for res in raw_results:
            key = f"{res.chunk.document_id}::{res.chunk.heading}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped_results.append(res)
            if len(deduped_results) >= k:
                break

        top_score = deduped_results[0].score if deduped_results else 0.0

        # Step 7: Source Validation & Grounded Context Construction
        context_parts = []
        total_chars = 0
        sources_list = []
        seen_urls = set()

        for res in deduped_results:
            chunk_text = res.chunk.text.strip()
            if total_chars + len(chunk_text) > self.max_context_chars:
                remaining = self.max_context_chars - total_chars
                if remaining > 100:
                    chunk_text = chunk_text[:remaining] + "..."
                else:
                    break

            verification_label = getattr(res, "verification_status", "verified_general_source")
            part_header = f"--- Source: {res.title} ({res.source_name}) [{verification_label}] ---"
            context_parts.append(f"{part_header}\n{chunk_text}")
            total_chars += len(chunk_text) + len(part_header) + 2

            # Collect source attribution record
            url_key = res.source_url or res.title
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                sources_list.append({
                    "title": res.title,
                    "source_name": res.source_name,
                    "source_url": res.source_url,
                    "verification_status": getattr(res, "verification_status", "verified_general_source"),
                    "source_notes": getattr(res, "source_notes", ""),
                    "last_verified": res.last_verified,
                    "domain": res.domain,
                    "relevance_score": round(res.score, 4),
                    "excerpt": res.excerpt,
                })

        assembled_context = "\n\n".join(context_parts)

        logger.info(
            "RAG query '%s' retrieved %d chunks (top_score: %.3f, domain: %s)",
            cleaned_query,
            len(deduped_results),
            top_score,
            classification.primary_domain,
        )

        success_res = {
            "relevant_found": True,
            "context": assembled_context,
            "sources": sources_list,
            "top_score": round(top_score, 4),
            "results_count": len(deduped_results),
            "classification": classification.to_dict(),
            "normalized_query": normalized_query,
            "disclaimer": None,
            "retrieved_at": now_iso,
        }
        try:
            from utils.provenance import extract_provenance_from_rag
            success_res["source_provenance"] = extract_provenance_from_rag(success_res)
        except Exception:
            success_res["source_provenance"] = []
        if not conversation_context:
            if len(_RAG_QUERY_CACHE) >= _MAX_RAG_CACHE_SIZE:
                first_k = next(iter(_RAG_QUERY_CACHE))
                _RAG_QUERY_CACHE.pop(first_k, None)
            _RAG_QUERY_CACHE[cache_key] = success_res
        return success_res

_RAG_QUERY_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_RAG_CACHE_SIZE = 256
_RETRIEVER_INSTANCE: Optional[YatraKnowledgeRetriever] = None


def get_retriever() -> YatraKnowledgeRetriever:
    """Module-level singleton retriever avoiding re-instantiation overhead."""
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is None:
        _RETRIEVER_INSTANCE = YatraKnowledgeRetriever()
    return _RETRIEVER_INSTANCE


def clear_rag_cache() -> None:
    """Clears the in-memory RAG query cache."""
    global _RAG_QUERY_CACHE
    _RAG_QUERY_CACHE.clear()
