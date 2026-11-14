"""
rag/ingestion.py
Document ingestion, preprocessing, deduplication, and indexing pipeline for Yatra AI.
Loads verified domain documents, normalizes content, generates semantic chunks,
embeds them, and persists the vector store to disk.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from rag.chunker import SemanticSectionChunker
from rag.embeddings import BaseEmbeddingModel, get_embedding_model
from rag.schema import Document
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

DEFAULT_KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
DEFAULT_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "vector_store.json")


class IngestionPipeline:
    """Manages verified document loading, deduplication, chunking, and index building."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[BaseEmbeddingModel] = None,
        chunker: Optional[SemanticSectionChunker] = None,
        index_path: str = DEFAULT_INDEX_PATH,
    ):
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or get_embedding_model("domain_term")
        self.chunker = chunker or SemanticSectionChunker()
        self.index_path = index_path

    def load_document_from_file(self, file_path: str) -> List[Document]:
        """Loads and parses documents from a JSON file."""
        if not os.path.exists(file_path):
            logger.error("Knowledge file not found: %s", file_path)
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = [data]

            documents: List[Document] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                # Validate required fields
                if not item.get("document_id") or not item.get("content"):
                    logger.warning("Skipping document missing ID or content in %s", file_path)
                    continue

                doc = Document.from_dict(item)
                documents.append(doc)

            return documents
        except Exception as exc:
            logger.error("Failed to parse knowledge file %s: %s", file_path, exc)
            return []

    def ingest_directory(self, dir_path: str = DEFAULT_KB_DIR) -> Dict[str, Any]:
        """Scans directory for knowledge JSON files and ingests all verified documents."""
        if not os.path.exists(dir_path):
            logger.warning("Knowledge base directory does not exist: %s", dir_path)
            return {"status": "error", "message": f"Directory not found: {dir_path}"}

        files_processed = 0
        docs_loaded = 0
        docs_indexed = 0
        duplicates_skipped = 0

        for root, _, files in os.walk(dir_path):
            for file in sorted(files):
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    docs = self.load_document_from_file(file_path)
                    files_processed += 1
                    docs_loaded += len(docs)

                    for doc in docs:
                        added = self.vector_store.add_document(
                            document=doc,
                            embedder=self.embedder,
                            chunker=self.chunker,
                        )
                        if added:
                            docs_indexed += 1
                        else:
                            duplicates_skipped += 1

        # Save to disk
        self.vector_store.save(self.index_path)

        stats = self.vector_store.get_stats()
        return {
            "status": "success",
            "files_processed": files_processed,
            "documents_loaded": docs_loaded,
            "documents_indexed": docs_indexed,
            "duplicates_skipped": duplicates_skipped,
            "total_chunks_indexed": stats["chunks_count"],
            "domains_covered": stats["domains"],
            "index_path": self.index_path,
        }

    def ingest_single_document(self, doc_data: Dict[str, Any]) -> bool:
        """Dynamically ingests or updates a single document."""
        doc = Document.from_dict(doc_data)
        success = self.vector_store.add_document(
            document=doc,
            embedder=self.embedder,
            chunker=self.chunker,
        )
        if success:
            self.vector_store.save(self.index_path)
        return success

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document from the index and persists changes."""
        success = self.vector_store.delete_document(document_id)
        if success:
            self.vector_store.save(self.index_path)
        return success

    def reindex_all(self, dir_path: str = DEFAULT_KB_DIR) -> Dict[str, Any]:
        """Clears existing index and re-ingests entire knowledge base from scratch."""
        self.vector_store = VectorStore(dimension=self.embedder.dimension)
        return self.ingest_directory(dir_path)


_DEFAULT_VECTOR_STORE_CACHE = None

def initialize_default_vector_store(force_reload: bool = False) -> VectorStore:
    """Convenience helper ensuring the vector store is loaded from disk or built if missing.
    Uses in-memory singleton cache to prevent repeated disk I/O on every turn."""
    global _DEFAULT_VECTOR_STORE_CACHE
    if not force_reload and _DEFAULT_VECTOR_STORE_CACHE is not None:
        return _DEFAULT_VECTOR_STORE_CACHE

    vs = VectorStore()
    if os.path.exists(DEFAULT_INDEX_PATH):
        vs.load(DEFAULT_INDEX_PATH)
    else:
        pipeline = IngestionPipeline(vector_store=vs)
        pipeline.ingest_directory()
    _DEFAULT_VECTOR_STORE_CACHE = vs
    return vs
