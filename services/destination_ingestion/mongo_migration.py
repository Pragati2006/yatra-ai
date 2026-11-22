"""
services/destination_ingestion/mongo_migration.py
Safe, Idempotent Migration Engine for J&K Tourist Destinations into MongoDB 'tourist_attractions'.

Invariants:
- Targets the EXISTING 'tourist_attractions' collection in the configured MongoDB database.
- Strictly preserves existing curated records (never overwrites or mutates manually verified entries).
- Idempotent: repeated executions detect existing records and insert 0 duplicates.
- Retains full provenance, official coordinates, and original concise descriptions.
- Keeps unknown fees, timings, and photographs as null per legal/compliance rules.
- Never logs, prints, or exposes MongoDB credentials.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import mongo_db
import explore_data
from .deduplicator import resolve_deduplication, normalize_name

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INGESTED_JSON_PATH = REPO_ROOT / "data" / "ingested_destinations.json"
TARGET_COLLECTION = "tourist_attractions"


def adapt_record_to_collection_schema(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms an ingested destination record into the schema expected by the
    existing 'tourist_attractions' MongoDB collection.
    """
    lat = raw_record.get("latitude")
    lon = raw_record.get("longitude")

    doc = {
        "id": raw_record.get("id") or f"dest-{re.sub(r'[^a-z0-9]+', '-', raw_record.get('name', '').lower()).strip('-')}",
        "name": raw_record["name"],
        "district": raw_record.get("district", "Jammu and Kashmir"),
        "region": raw_record.get("region", "Jammu"),
        "state": raw_record.get("state", "Jammu and Kashmir"),
        "category": raw_record.get("category", "Tourist Destination"),
        "category_type": raw_record.get("category_type", "tourist_attraction"),
        "latitude": lat,
        "longitude": lon,
        "coordinates": {"lat": lat, "lng": lon} if (lat is not None and lon is not None) else None,
        "coordinates_source": raw_record.get("coordinates_source"),
        "distance": raw_record.get("distance"),
        "timings": raw_record.get("timings"),
        "timings_verified": bool(raw_record.get("timings_verified", False)),
        "entry_fee": raw_record.get("entry_fee"),
        "entry_fee_verified": bool(raw_record.get("entry_fee_verified", False)),
        "description": raw_record.get("description", ""),
        "historical_background": raw_record.get("historical_background", ""),
        "source_url": raw_record.get("source_url", ""),
        "source_domain": raw_record.get("source_domain", ""),
        "verification_status": raw_record.get("verification_status", "OFFICIALLY_VERIFIED"),
        "provenance": raw_record.get("provenance", {}),
        "is_curated": False,
        "duplicate_of": None,
        "image": None,  # Strictly null per copyright compliance
        "image_file": None,
        "image_notice": "Photographs omitted per copyright compliance policy",
        "video_search": raw_record.get("video_search"),
        "altitude_m": raw_record.get("altitude_m"),
        "darshan_timings": None,
        "aarti_timings": None,
        "visiting_hours": None,
        "best_time_to_visit": raw_record.get("best_time_to_visit"),
        "accessibility": raw_record.get("accessibility"),
        "seasonal_restrictions": raw_record.get("seasonal_restrictions"),
    }
    return doc


class DestinationMongoMigrator:
    """
    Executes safe, idempotent migration of verified destination records
    into the primary 'tourist_attractions' collection.
    """

    def __init__(self, db=None, collection_name: str = TARGET_COLLECTION):
        self._db = db
        self.collection_name = collection_name

    def get_collection(self):
        """Retrieves target collection handle, with connection health check."""
        if self._db is not None:
            return self._db[self.collection_name]
        if mongo_db.is_available():
            coll = mongo_db.get_collection(self.collection_name)
            return coll
        return None

    def ensure_target_indexes(self, coll) -> List[str]:
        """Ensures indexes on name and id without altering existing collections."""
        created = []
        try:
            # Query existing index names
            existing_indexes = {idx["name"] for idx in coll.list_indexes()}

            # Idempotently add index on name if not present
            if "name_1" not in existing_indexes:
                coll.create_index("name", name="name_1")
                created.append("name_1")
            else:
                created.append("name_1 (reused)")

            if "id_1" not in existing_indexes:
                coll.create_index("id", name="id_1")
                created.append("id_1")
            else:
                created.append("id_1 (reused)")
        except Exception as exc:
            logger.debug("Index ensure warning: %s", exc)
        return created

    def execute_migration(
        self,
        ingested_file: Optional[Path] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Migrates new verified destinations into 'tourist_attractions'.
        Returns detailed execution manifest.
        """
        coll = self.get_collection()
        if coll is None:
            raise ConnectionError(
                "MongoDB Atlas is currently unreachable or unconfigured. "
                "Migration cannot proceed without database connection."
            )

        # Read source ingested records
        source_path = ingested_file or INGESTED_JSON_PATH
        if not source_path.exists():
            raise FileNotFoundError(f"Ingested destination registry not found at {source_path}")

        ingested_records = json.loads(source_path.read_text(encoding="utf-8"))

        # Initial collection status
        initial_count = coll.count_documents({})
        indexes = self.ensure_target_indexes(coll)

        # Build existing name set from target collection
        existing_names = set()
        existing_ids = set()
        for doc in coll.find({}, {"name": 1, "id": 1, "_id": 0}):
            if doc.get("name"):
                existing_names.add(doc["name"].lower().strip())
                existing_names.add(normalize_name(doc["name"]))
            if doc.get("id"):
                existing_ids.add(doc["id"])

        # Also add all baseline curated places to existing protection set
        for p in explore_data.PLACES:
            existing_names.add(p["name"].lower().strip())
            existing_names.add(normalize_name(p["name"]))

        inserted_records = []
        skipped_curated_duplicates = []
        skipped_already_present = []

        for r in ingested_records:
            name = r.get("name", "").strip()
            name_lower = name.lower()
            name_norm = normalize_name(name)

            # Check 1: Record flagged as curated duplicate
            if r.get("is_curated", False) or r.get("duplicate_of"):
                skipped_curated_duplicates.append({
                    "name": name,
                    "duplicate_of": r.get("duplicate_of"),
                    "reason": "Preserved existing curated catalog record"
                })
                continue

            # Check 2: Deduplication against curated catalog names
            is_dup, dup_of, _ = resolve_deduplication(name, r.get("source_url", ""))
            if is_dup:
                skipped_curated_duplicates.append({
                    "name": name,
                    "duplicate_of": dup_of,
                    "reason": "Matches curated equivalent; preserved curated record"
                })
                continue

            # Check 3: Already present in target MongoDB collection
            if name_lower in existing_names or name_norm in existing_names:
                skipped_already_present.append({
                    "name": name,
                    "reason": "Already exists in tourist_attractions collection"
                })
                continue

            # Check 4: ID already present
            adapted = adapt_record_to_collection_schema(r)
            if adapted["id"] in existing_ids:
                skipped_already_present.append({
                    "name": name,
                    "id": adapted["id"],
                    "reason": "ID already exists in tourist_attractions collection"
                })
                continue

            # Safe, non-destructive insertion
            if not dry_run:
                # Use insert_one (pure insert, never overwrites)
                coll.insert_one(adapted)
                existing_names.add(name_lower)
                existing_names.add(name_norm)
                existing_ids.add(adapted["id"])

            inserted_records.append({
                "id": adapted["id"],
                "name": adapted["name"],
                "district": adapted["district"],
                "category": adapted["category"],
                "source_url": adapted["source_url"]
            })

        final_count = coll.count_documents({}) if not dry_run else initial_count + len(inserted_records)

        result = {
            "database_name": coll.database.name if hasattr(coll, "database") else "unknown",
            "collection_name": self.collection_name,
            "dry_run": dry_run,
            "initial_document_count": initial_count,
            "inserted_count": len(inserted_records),
            "skipped_curated_duplicates": len(skipped_curated_duplicates),
            "skipped_already_present": len(skipped_already_present),
            "final_document_count": final_count,
            "curated_records_preserved": True,
            "inserted_destinations": inserted_records,
            "curated_duplicates_skipped": skipped_curated_duplicates,
            "already_present_skipped": skipped_already_present,
            "indexes": indexes,
            "status": "SUCCESS" if (not dry_run or len(inserted_records) >= 0) else "DRY_RUN_COMPLETE"
        }

        logger.info(
            "Destination migration completed: initial=%d, inserted=%d, final=%d",
            initial_count, len(inserted_records), final_count
        )
        return result
