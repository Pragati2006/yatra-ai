"""
rag/vector_store.py
Persistent, metadata-filtered in-memory vector store powered by NumPy.
Provides exact cosine similarity search, relevance thresholding,
document deduplication, document updates, deletions, and disk persistence.
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional
import numpy as np

from rag.chunker import SemanticSectionChunker
from rag.embeddings import BaseEmbeddingModel, DomainTermEmbeddingModel
from rag.schema import Chunk, Document, RetrievalResult

logger = logging.getLogger(__name__)


class VectorStore:
    """
    High-performance, persistent vector store for Yatra AI knowledge base.
    Features:
    - Normalized cosine dot-product indexing using NumPy
    - Document deduplication via SHA-256 content hashes
    - Metadata filtering by domain, category, source_type, and place
    - Score thresholding to discard irrelevant chunks
    - Document CRUD and atomic re-indexing
    - Disk persistence to JSON/JSONL format
    """

    def __init__(self, dimension: int = 256):
        self.dimension = dimension
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, Chunk] = {}
        self._doc_to_chunks: Dict[str, List[str]] = {}
        self._content_hashes: Dict[str, str] = {}  # hash -> doc_id

        # Cached NumPy matrix for vectorized similarity search
        self._chunk_ids_ordered: List[str] = []
        self._matrix: Optional[np.ndarray] = None
        self._dirty = False

    def _rebuild_matrix(self):
        """Reconstructs the internal NumPy embedding matrix."""
        valid_chunks = [c for c in self._chunks.values() if c.embedding and len(c.embedding) == self.dimension]
        if not valid_chunks:
            self._chunk_ids_ordered = []
            self._matrix = None
            self._dirty = False
            return

        self._chunk_ids_ordered = [c.chunk_id for c in valid_chunks]
        matrix_data = [c.embedding for c in valid_chunks]
        self._matrix = np.array(matrix_data, dtype=np.float32)

        # Ensure L2 normalized rows
        norms = np.linalg.norm(self._matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._matrix = self._matrix / norms
        self._dirty = False

    def add_document(
        self,
        document: Document,
        embedder: BaseEmbeddingModel,
        chunker: Optional[SemanticSectionChunker] = None,
    ) -> bool:
        """
        Ingests a Document, checks for duplicates, chunks, embeds, and indexes it.
        Returns True if newly added, False if duplicate skipped.
        """
        # Duplicate detection by content hash
        if document.content_hash in self._content_hashes:
            existing_id = self._content_hashes[document.content_hash]
            logger.info("Duplicate document detected (matches %s); skipping ingestion of %s.", existing_id, document.document_id)
            return False

        if chunker is None:
            chunker = SemanticSectionChunker()

        chunks = chunker.chunk_document(document)
        if not chunks:
            logger.warning("Document %s yielded 0 chunks; not indexed.", document.document_id)
            return False

        # Embed all chunk texts
        texts = [c.text for c in chunks]
        embeddings = embedder.embed_documents(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        # Store document and its chunks
        self._documents[document.document_id] = document
        self._content_hashes[document.content_hash] = document.document_id
        chunk_ids = []

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            chunk_ids.append(chunk.chunk_id)

        self._doc_to_chunks[document.document_id] = chunk_ids
        self._dirty = True
        return True

    def add_documents(
        self,
        documents: List[Document],
        embedder: BaseEmbeddingModel,
        chunker: Optional[SemanticSectionChunker] = None,
    ) -> int:
        """Ingests a collection of documents. Returns count of successfully indexed documents."""
        added = 0
        for doc in documents:
            if self.add_document(doc, embedder=embedder, chunker=chunker):
                added += 1
        if self._dirty:
            self._rebuild_matrix()
        return added

    def update_document(
        self,
        document: Document,
        embedder: BaseEmbeddingModel,
        chunker: Optional[SemanticSectionChunker] = None,
    ) -> bool:
        """Updates an existing document by re-chunking and re-embedding."""
        if document.document_id in self._documents:
            self.delete_document(document.document_id)
        return self.add_document(document, embedder=embedder, chunker=chunker)

    def delete_document(self, document_id: str) -> bool:
        """Removes a document and all its associated chunks from the index."""
        if document_id not in self._documents:
            return False

        doc = self._documents.pop(document_id)
        if doc.content_hash in self._content_hashes:
            del self._content_hashes[doc.content_hash]

        chunk_ids = self._doc_to_chunks.pop(document_id, [])
        for cid in chunk_ids:
            self._chunks.pop(cid, None)

        self._dirty = True
        self._rebuild_matrix()
        return True

    def get_document(self, document_id: str) -> Optional[Document]:
        return self._documents.get(document_id)

    def list_documents(self) -> List[Document]:
        return list(self._documents.values())

    def search(
        self,
        query_vec: List[float],
        top_k: int = 4,
        score_threshold: float = 0.40,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[RetrievalResult]:
        """
        Executes semantic search over indexed chunks using cosine similarity.
        Applies metadata filtering and relevance thresholding.
        """
        if self._dirty or self._matrix is None:
            self._rebuild_matrix()

        if self._matrix is None or len(self._chunk_ids_ordered) == 0:
            return []

        q_arr = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm == 0:
            return []
        q_normed = q_arr / q_norm

        # Vectorized cosine similarities
        scores = np.dot(self._matrix, q_normed)

        # Rank indices descending
        ranked_indices = np.argsort(-scores)

        results: List[RetrievalResult] = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score < score_threshold:
                break

            cid = self._chunk_ids_ordered[idx]
            chunk = self._chunks.get(cid)
            if not chunk:
                continue

            # Check metadata filter if supplied
            if filter_fn and not filter_fn(chunk.metadata):
                continue

            meta = chunk.metadata
            res = RetrievalResult(
                chunk=chunk,
                score=score,
                title=meta.get("title", ""),
                source_name=meta.get("source_name", ""),
                source_url=meta.get("source_url", ""),
                domain=meta.get("domain", ""),
                last_verified=meta.get("last_verified", ""),
                excerpt=chunk.text[:280] + ("..." if len(chunk.text) > 280 else ""),
                verification_status=meta.get("verification_status", "verified_general_source"),
                source_notes=meta.get("source_notes", ""),
            )
            results.append(res)
            if len(results) >= top_k:
                break

        return results

    def save(self, filepath: str):
        """Serializes the entire store and all metadata to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        data = {
            "dimension": self.dimension,
            "documents": [d.to_dict() for d in self._documents.values()],
            "chunks": [c.to_dict() for c in self._chunks.values()],
            "doc_to_chunks": self._doc_to_chunks,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("VectorStore saved %d docs, %d chunks to %s", len(self._documents), len(self._chunks), filepath)

    def load(self, filepath: str) -> bool:
        """Loads vector store and chunks from disk."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.dimension = data.get("dimension", 256)
            self._documents = {d["document_id"]: Document.from_dict(d) for d in data.get("documents", [])}
            self._content_hashes = {d.content_hash: d.document_id for d in self._documents.values()}
            self._chunks = {c["chunk_id"]: Chunk.from_dict(c) for c in data.get("chunks", [])}
            self._doc_to_chunks = data.get("doc_to_chunks", {})
            self._rebuild_matrix()
            logger.info("VectorStore loaded %d docs, %d chunks from %s", len(self._documents), len(self._chunks), filepath)
            return True
        except Exception as exc:
            logger.error("Failed to load VectorStore from %s: %s", filepath, exc)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Returns diagnostic metrics and domain coverage."""
        domains = set(d.domain for d in self._documents.values())
        return {
            "documents_count": len(self._documents),
            "chunks_count": len(self._chunks),
            "dimension": self.dimension,
            "domains_count": len(domains),
            "domains": sorted(list(domains)),
            "sources": sorted(list(set(d.source_name for d in self._documents.values()))),
        }
