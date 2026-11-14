"""
rag/schema.py
Data models and schemas for Yatra AI Retrieval-Augmented Generation (RAG).
Encapsulates documents, chunks, and retrieval results with complete provenance metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Represents a verified knowledge document with strict source provenance."""
    document_id: str
    title: str
    content: str
    domain: str
    category: str
    source_name: str
    source_url: str
    source_type: str = "tier_1_official"  # 'tier_1_official', 'tier_2_institutional', 'tier_3_secondary'
    publication_date: Optional[str] = None
    last_verified: str = "2026-11-06"
    verification_status: str = "verified_general_source"  # 'verified_direct_source', 'verified_general_source', 'unverified', 'source_unavailable'
    source_notes: str = ""
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    language: str = "en"
    content_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self.compute_hash(self.content)

    @staticmethod
    def compute_hash(text: str) -> str:
        """Returns deterministic SHA-256 hash of normalized text for deduplication."""
        normalized = " ".join((text or "").strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "domain": self.domain,
            "category": self.category,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "publication_date": self.publication_date,
            "last_verified": self.last_verified,
            "verification_status": self.verification_status,
            "source_notes": self.source_notes,
            "retrieved_at": self.retrieved_at,
            "language": self.language,
            "content_version": self.content_version,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        data_copy = dict(data)
        # Gracefully handle optional fields
        data_copy.setdefault("verification_status", "verified_general_source")
        data_copy.setdefault("source_notes", "")
        return cls(**data_copy)


@dataclass
class Chunk:
    """A semantic or section-level slice of a Document with embedded metadata."""
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    heading: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "heading": self.heading,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(**data)


@dataclass
class RetrievalResult:
    """Represents a scored, source-attributed chunk returned by the vector retriever."""
    chunk: Chunk
    score: float
    title: str
    source_name: str
    source_url: str
    domain: str
    last_verified: str
    excerpt: str
    verification_status: str = "verified_general_source"
    source_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "document_id": self.chunk.document_id,
            "title": self.title,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "domain": self.domain,
            "last_verified": self.last_verified,
            "verification_status": self.verification_status,
            "source_notes": self.source_notes,
            "score": round(self.score, 4),
            "excerpt": self.excerpt,
            "heading": self.chunk.heading,
            "category": self.chunk.metadata.get("category", ""),
        }
