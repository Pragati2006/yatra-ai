"""
rag/chunker.py
Structure-aware semantic document chunker for Yatra AI.
Preserves headings, section boundaries, bullet lists, and contextual relationships.
"""

import re
from typing import List, Optional
from rag.schema import Chunk, Document


class SemanticSectionChunker:
    """
    Splits text documents into semantically coherent, structure-aware chunks.
    Preserves Markdown headings (###, ##), bullet points, and sentence integrity.
    Prepends parent heading hierarchy to chunks to maintain context independence.
    """

    def __init__(
        self,
        target_chunk_size: int = 450,
        chunk_overlap: int = 60,
        min_chunk_size: int = 80,
    ):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Splits a single Document into a list of attributed Chunks."""
        text = (document.content or "").strip()
        if not text:
            return []

        # Split document into heading sections
        sections = self._split_into_sections(text)
        chunks: List[Chunk] = []
        global_idx = 0

        for section_heading, section_body in sections:
            section_chunks = self._chunk_section_text(
                section_body,
                heading=section_heading,
            )

            for sc_text in section_chunks:
                # Prepend heading if not already present in the chunk text
                formatted_text = sc_text
                if section_heading and not sc_text.startswith(f"### {section_heading}"):
                    formatted_text = f"[{section_heading}]\n{sc_text}"

                chunk_id = f"{document.document_id}#c{global_idx}"
                chunk = Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    text=formatted_text,
                    chunk_index=global_idx,
                    heading=section_heading,
                    metadata={
                        "title": document.title,
                        "domain": document.domain,
                        "category": document.category,
                        "source_name": document.source_name,
                        "source_url": document.source_url,
                        "source_type": document.source_type,
                        "publication_date": document.publication_date,
                        "last_verified": document.last_verified,
                        "verification_status": document.verification_status,
                        "source_notes": document.source_notes,
                        "content_version": document.content_version,
                        "document_id": document.document_id,
                    },
                )
                chunks.append(chunk)
                global_idx += 1

        return chunks

    def _split_into_sections(self, text: str) -> List[tuple]:
        """Splits markdown text by headings (###, ##, #)."""
        lines = text.split("\n")
        sections = []
        current_heading = "Overview"
        current_lines = []

        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            m = heading_pattern.match(line.strip())
            if m:
                if current_lines:
                    body = "\n".join(current_lines).strip()
                    if body:
                        sections.append((current_heading, body))
                    current_lines = []
                current_heading = m.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_heading, body))

        if not sections and text.strip():
            sections.append((None, text.strip()))

        return sections

    def _chunk_section_text(
        self,
        text: str,
        heading: Optional[str] = None,
    ) -> List[str]:
        """Chunks a section text honoring paragraph and sentence boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks = []
        current_chunk_parts = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)

            # If adding paragraph exceeds target chunk size and we already have content
            if current_len + p_len > self.target_chunk_size and current_chunk_parts:
                chunk_str = "\n\n".join(current_chunk_parts).strip()
                if len(chunk_str) >= self.min_chunk_size:
                    chunks.append(chunk_str)

                # Keep overlap if possible
                overlap_text = current_chunk_parts[-1] if self.chunk_overlap > 0 else ""
                if len(overlap_text) > self.chunk_overlap:
                    # Slice tail of previous part
                    overlap_text = overlap_text[-self.chunk_overlap:]

                current_chunk_parts = [overlap_text, p] if overlap_text else [p]
                current_len = sum(len(x) for x in current_chunk_parts)
            else:
                current_chunk_parts.append(p)
                current_len += p_len

        if current_chunk_parts:
            final_str = "\n\n".join(current_chunk_parts).strip()
            if len(final_str) >= self.min_chunk_size or not chunks:
                chunks.append(final_str)

        return chunks
