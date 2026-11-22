"""
services/destination_ingestion/__init__.py
J&K Destination Data Ingestion & Enrichment Module for Yatra AI.
"""

from .models import DestinationRecord, ProvenanceInfo
from .scraper import DestinationScraper, OFFICIAL_SOURCES
from .deduplicator import resolve_deduplication, find_curated_match
from .storage import DestinationStorage, COLLECTION_NAME
from .manager import DestinationManager, get_destination_manager
from .mongo_migration import DestinationMongoMigrator, adapt_record_to_collection_schema

__all__ = [
    "DestinationRecord",
    "ProvenanceInfo",
    "DestinationScraper",
    "OFFICIAL_SOURCES",
    "resolve_deduplication",
    "find_curated_match",
    "DestinationStorage",
    "COLLECTION_NAME",
    "DestinationManager",
    "get_destination_manager",
    "DestinationMongoMigrator",
    "adapt_record_to_collection_schema",
]
