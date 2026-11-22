"""
services/destination_ingestion/storage.py
Persistent storage engine for enriched J&K destination records.

Maintains:
- Dedicated separate MongoDB collection: 'enriched_destinations' (preserving curated 'tourist_attractions')
- Deterministic offline file fallback: 'data/ingested_destinations.json'
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import mongo_db
from .models import DestinationRecord

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = REPO_ROOT / "data" / "ingested_destinations.json"
COLLECTION_NAME = "enriched_destinations"
PRIMARY_COLLECTION = "tourist_attractions"


class DestinationStorage:
    """Manages MongoDB Atlas retrieval and local JSON fallback for enriched destinations."""

    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or DATA_FILE
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_mongo_collection(self):
        """Retrieves the separate MongoDB collection if Atlas is available."""
        if mongo_db.is_available():
            try:
                coll = mongo_db.get_collection(COLLECTION_NAME)
                return coll
            except Exception as e:
                logger.warning("MongoDB collection access failed: %s", e)
        return None

    def save_destinations(self, records: List[DestinationRecord]) -> int:
        """
        Saves destination records to the separate MongoDB collection and offline JSON file.
        Preserves curated records; updates metadata and provenance cleanly.
        """
        dict_records = [r.to_dict() for r in records]

        # 1. Save to local JSON fallback
        try:
            self.data_file.write_text(
                json.dumps(dict_records, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info("Saved %d destination records to %s", len(records), self.data_file)
        except Exception as exc:
            logger.error("Failed saving local JSON backup: %s", exc)

        # 2. Save to separate MongoDB collection if connected
        coll = self._get_mongo_collection()
        if coll is not None:
            try:
                from pymongo import ReplaceOne
                operations = [
                    ReplaceOne({"id": r["id"]}, r, upsert=True)
                    for r in dict_records
                ]
                if operations:
                    result = coll.bulk_write(operations)
                    logger.info("MongoDB bulk write: %d matched, %d upserted", result.matched_count, len(result.upserted_ids))
                    return len(dict_records)
            except Exception as exc:
                logger.error("MongoDB bulk save error: %s", exc)

        return len(dict_records)

    def load_destinations(self) -> List[Dict[str, Any]]:
        """
        Loads destinations from MongoDB if available, otherwise falls back to local JSON file.
        Queries the primary 'tourist_attractions' collection first to ensure 43 unified destinations,
        falling back to 'enriched_destinations' and local file.
        """
        if self.data_file == DATA_FILE and mongo_db.is_available():
            try:
                coll = mongo_db.get_collection(PRIMARY_COLLECTION)
                if coll is not None:
                    records = list(coll.find({"is_curated": False}, {"_id": 0}))
                    if records:
                        return records
            except Exception:
                pass

        coll = self._get_mongo_collection()
        if coll is not None:
            try:
                records = list(coll.find({}, {"_id": 0}))
                if records:
                    return records
            except Exception:
                pass

        # Local JSON fallback
        if self.data_file.exists():
            try:
                data = json.loads(self.data_file.read_text(encoding="utf-8"))
                return data
            except Exception as exc:
                logger.error("Failed loading local destination JSON: %s", exc)

        return []

    def get_destination_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single destination record by name."""
        if not name:
            return None
        target = name.strip().lower()
        all_recs = self.load_destinations()
        for r in all_recs:
            if r.get("name", "").lower() == target:
                return r
        for r in all_recs:
            if target in r.get("name", "").lower():
                return r
        return None


_VERIFIED_IMAGES_CACHE: Optional[Dict[str, Any]] = None


def get_verified_images_map() -> Dict[str, Any]:
    """Retrieves verified destination image metadata indexed by name and ID."""
    global _VERIFIED_IMAGES_CACHE
    if _VERIFIED_IMAGES_CACHE is not None:
        return _VERIFIED_IMAGES_CACHE

    img_file = REPO_ROOT / "data" / "verified_destination_images.json"
    result = {}
    if img_file.exists():
        try:
            raw = json.loads(img_file.read_text(encoding="utf-8"))
            for dest_id, d in raw.items():
                result[dest_id] = d
                d_name = d.get("destination_name")
                if d_name:
                    result[d_name] = d
                    result[d_name.lower().strip()] = d

            # Also index aliases from knowledge_agent to guarantee instant O(1) resolution
            try:
                from agents.knowledge_agent import _PLACE_ALIASES
                for alias_k, canon_n in _PLACE_ALIASES.items():
                    target_rec = result.get(canon_n) or result.get(canon_n.lower().strip())
                    if target_rec:
                        if alias_k not in result:
                            result[alias_k] = target_rec
                        clean_k = alias_k.lower().strip()
                        if clean_k not in result:
                            result[clean_k] = target_rec
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Error reading verified destination images: %s", exc)

    _VERIFIED_IMAGES_CACHE = result
    return result
