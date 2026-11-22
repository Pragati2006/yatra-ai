"""
services/destination_ingestion/models.py
Pydantic schemas for J&K destination data ingestion and enrichment.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProvenanceInfo(BaseModel):
    source_type: str = "official_government_portal"
    authority: str
    source_url: str
    source_domain: str
    retrieval_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    copyright_assessment: str = (
        "Factual attributes (name, coordinates, category, district) extracted. "
        "Original concise descriptions composed. Third-party paragraphs and "
        "photographs strictly omitted per copyright compliance policy."
    )
    permission_notes: str = (
        "Complies with NIC Web Guidelines and Section 52(1) Indian Copyright Act "
        "(fair dealing / public factual information)."
    )


class DestinationRecord(BaseModel):
    id: str
    name: str
    district: str
    region: str  # 'Jammu' or 'Kashmir'
    state: str = "Jammu and Kashmir"
    category: str
    category_type: str  # 'historical_site', 'nature_destination', 'religious_site', etc.
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinates_source: Optional[str] = None
    distance: Optional[str] = None
    timings: Optional[str] = None
    timings_verified: bool = False
    entry_fee: Optional[str] = None
    entry_fee_verified: bool = False
    description: str
    historical_background: Optional[str] = None
    source_url: str
    source_domain: str
    verification_status: str = "OFFICIALLY_VERIFIED"  # OFFICIALLY_VERIFIED, CURATED_PRESERVED, PARTIALLY_VERIFIED
    provenance: ProvenanceInfo
    is_curated: bool = False
    duplicate_of: Optional[str] = None
    image: Optional[str] = None
    image_notice: Optional[str] = "Photographs omitted per copyright compliance"
    video_search: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
