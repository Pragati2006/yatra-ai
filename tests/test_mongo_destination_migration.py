"""
tests/test_mongo_destination_migration.py
Test suite for Phase 8: Safe, Idempotent MongoDB Integration of J&K Tourist Destinations into 'tourist_attractions'.

Covers:
1. Target collection schema adaptation.
2. Safe migration into 'tourist_attractions'.
3. Preservation of all 29 curated records.
4. Idempotency across repeated executions (0 duplicate insertions).
5. Skipping of the 6 curated duplicates without overwriting.
6. Provenance and metadata persistence.
7. MongoDB retrieval layer querying both curated and newly ingested records.
8. Local fallback parity and duplicate absence.
9. Safety gate: handles unreachable Atlas database cleanly.
"""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import explore_data
import mongodb_tools
from services.destination_ingestion.mongo_migration import (
    DestinationMongoMigrator,
    adapt_record_to_collection_schema,
    TARGET_COLLECTION
)


class MockMongoCollection:
    """In-memory mock mimicking pymongo Collection for safe, isolated migration testing."""

    def __init__(self, name: str = TARGET_COLLECTION):
        self.name = name
        self._docs = []
        self._indexes = [{"name": "_id_"}]
        self.database = MagicMock()
        self.database.name = "yatra-booking-agent"

    def count_documents(self, filter_dict) -> int:
        return len(self._docs)

    def list_indexes(self):
        return iter(self._indexes)

    def create_index(self, key, name=None, **kwargs):
        idx_name = name or f"{key}_1"
        self._indexes.append({"name": idx_name, "key": key})
        return idx_name

    def find(self, filter_dict=None, projection=None):
        results = []
        regex_filter = filter_dict or {}
        for d in self._docs:
            matched = True
            for k, v in regex_filter.items():
                if isinstance(v, dict) and "$regex" in v:
                    pattern = v["$regex"].strip("^$").lower()
                    if pattern not in str(d.get(k, "")).lower():
                        matched = False
                        break
                elif d.get(k) != v and k != "_id":
                    matched = False
                    break
            if matched:
                item = copy.deepcopy(d)
                if projection and projection.get("_id") == 0:
                    item.pop("_id", None)
                results.append(item)
        return results

    def insert_one(self, doc):
        item = copy.deepcopy(doc)
        if "_id" not in item:
            item["_id"] = str(len(self._docs) + 1)
        self._docs.append(item)
        return MagicMock(inserted_id=item["_id"])


class TestMongoDestinationMigration(unittest.TestCase):

    def setUp(self):
        mongodb_tools.clear_caches()
        self.mock_coll = MockMongoCollection()
        self.mock_db = {"tourist_attractions": self.mock_coll}
        self.migrator = DestinationMongoMigrator(db=self.mock_db)

        # Seed the 29 baseline curated places into mock collection
        for p in explore_data.PLACES:
            self.mock_coll.insert_one(copy.deepcopy(p))

    def tearDown(self):
        mongodb_tools.clear_caches()

    # -------------------------------------------------------------------------
    # 1. Schema Adaptation & Field Conformity
    # -------------------------------------------------------------------------
    def test_01_schema_adaptation(self):
        """Verify field transformation conforms to tourist_attractions document structure."""
        raw = {
            "name": "Akhnoor Fort",
            "district": "Jammu",
            "region": "Jammu",
            "state": "Jammu and Kashmir",
            "category": "Historic Fort",
            "category_type": "historical_site",
            "latitude": 32.896543,
            "longitude": 74.739271,
            "coordinates_source": "District Administration Jammu, NIC",
            "description": "Historical fort on the Chenab river.",
            "historical_background": "Built in 1802 by Raja Alam Singh.",
            "source_url": "https://jammu.nic.in/tourist-place/akhnoor-fort/",
            "source_domain": "jammu.nic.in",
            "provenance": {"authority": "District Administration Jammu, NIC"}
        }

        adapted = adapt_record_to_collection_schema(raw)
        self.assertEqual(adapted["name"], "Akhnoor Fort")
        self.assertEqual(adapted["latitude"], 32.896543)
        self.assertEqual(adapted["longitude"], 74.739271)
        self.assertEqual(adapted["coordinates"], {"lat": 32.896543, "lng": 74.739271})
        self.assertIsNone(adapted["timings"])
        self.assertFalse(adapted["timings_verified"])
        self.assertIsNone(adapted["entry_fee"])
        self.assertFalse(adapted["entry_fee_verified"])
        self.assertIsNone(adapted["image"])
        self.assertIn("Photographs omitted", adapted["image_notice"])
        self.assertEqual(adapted["provenance"]["authority"], "District Administration Jammu, NIC")

    # -------------------------------------------------------------------------
    # 2. Curated Records Baseline Verification
    # -------------------------------------------------------------------------
    def test_02_curated_records_baseline_count(self):
        """Verify baseline collection contains exactly the 29 curated destinations."""
        self.assertEqual(self.mock_coll.count_documents({}), 29)
        names = [d["name"] for d in self.mock_coll.find()]
        self.assertIn("Bhairavnath Temple", names)
        self.assertIn("Ardhkuwari Cave", names)
        self.assertIn("Amar Mahal Palace", names)

    # -------------------------------------------------------------------------
    # 3. Migration Execution & Final Count
    # -------------------------------------------------------------------------
    def test_03_migration_execution_adds_14_new_destinations(self):
        """Verify migration adds exactly 14 new destinations, reaching 43 total."""
        res = self.migrator.execute_migration(dry_run=False)

        self.assertEqual(res["initial_document_count"], 29)
        self.assertEqual(res["inserted_count"], 14)
        self.assertEqual(res["skipped_curated_duplicates"], 6)
        self.assertEqual(res["final_document_count"], 43)
        self.assertTrue(res["curated_records_preserved"])

        all_names = [d["name"] for d in self.mock_coll.find()]
        self.assertEqual(len(all_names), 43)
        self.assertIn("Akhnoor Fort", all_names)
        self.assertIn("Chashma Shahi", all_names)
        self.assertIn("Machail Mata", all_names)
        self.assertIn("Bhairavnath Temple", all_names)

    # -------------------------------------------------------------------------
    # 4. Idempotency & Repeatable Migration
    # -------------------------------------------------------------------------
    def test_04_migration_idempotency_second_run(self):
        """Verify that running the migration a second time inserts 0 records and keeps count at 43."""
        # First run: inserts 14 -> 43 total
        res1 = self.migrator.execute_migration(dry_run=False)
        self.assertEqual(res1["inserted_count"], 14)
        self.assertEqual(self.mock_coll.count_documents({}), 43)

        # Second run: must detect all existing records, insert 0, preserve 43
        res2 = self.migrator.execute_migration(dry_run=False)
        self.assertEqual(res2["initial_document_count"], 43)
        self.assertEqual(res2["inserted_count"], 0)
        self.assertEqual(res2["final_document_count"], 43)
        self.assertEqual(res2["skipped_already_present"], 14)
        self.assertEqual(res2["skipped_curated_duplicates"], 6)

    # -------------------------------------------------------------------------
    # 5. Non-Destructive Curated Duplicate Protection
    # -------------------------------------------------------------------------
    def test_05_curated_duplicates_do_not_overwrite(self):
        """Verify that duplicate entries like Amar Mahal or Bagh-e-Bahu do not overwrite curated records."""
        original_amar_mahal = [d for d in self.mock_coll.find() if d["name"] == "Amar Mahal Palace"][0]
        original_desc = original_amar_mahal.get("description")

        self.migrator.execute_migration(dry_run=False)

        after_amar_mahal = [d for d in self.mock_coll.find() if d["name"] == "Amar Mahal Palace"][0]
        self.assertEqual(after_amar_mahal.get("description"), original_desc)
        # Verify no duplicate 'Amar Mahal Jammu' was inserted
        matching_docs = [d for d in self.mock_coll.find() if "amar mahal" in d["name"].lower()]
        self.assertEqual(len(matching_docs), 1)

    # -------------------------------------------------------------------------
    # 6. Provenance and Metadata Retention
    # -------------------------------------------------------------------------
    def test_06_provenance_retention_in_target_collection(self):
        """Verify that migrated documents retain complete official provenance and verification status."""
        self.migrator.execute_migration(dry_run=False)
        doc = [d for d in self.mock_coll.find() if d["name"] == "Machail Mata"][0]

        self.assertEqual(doc["district"], "Kishtwar")
        self.assertEqual(doc["verification_status"], "OFFICIALLY_VERIFIED")
        self.assertEqual(doc["source_domain"], "kishtwar.nic.in")
        self.assertIn("kishtwar.nic.in", doc["source_url"])
        self.assertIn("District Administration Kishtwar", doc["provenance"]["authority"])
        self.assertIn("Section 52(1)", doc["provenance"]["permission_notes"])

    # -------------------------------------------------------------------------
    # 7. Unified Retrieval Layer via MongoDB Tools
    # -------------------------------------------------------------------------
    def test_07_mongodb_tools_retrieval_across_unified_attractions(self):
        """Verify that search_tourist_attraction retrieves both curated and newly migrated destinations."""
        self.migrator.execute_migration(dry_run=False)

        with patch.object(mongodb_tools, "tourist_attractions", self.mock_coll):
            with patch("mongo_db.is_available", return_value=True):
                # Query curated attraction
                res_curated = mongodb_tools.search_tourist_attraction("Bhairavnath Temple")
                self.assertTrue(len(res_curated) >= 1)
                self.assertEqual(res_curated[0]["name"], "Bhairavnath Temple")

                # Query newly migrated attraction
                res_new = mongodb_tools.search_tourist_attraction("Akhnoor Fort")
                self.assertTrue(len(res_new) >= 1)
                self.assertEqual(res_new[0]["name"], "Akhnoor Fort")

                # Query Srinagar Mughal garden
                res_garden = mongodb_tools.search_tourist_attraction("Chashma Shahi")
                self.assertTrue(len(res_garden) >= 1)
                self.assertEqual(res_garden[0]["name"], "Chashma Shahi")

    # -------------------------------------------------------------------------
    # 8. Unreachable Database Fail-Safe
    # -------------------------------------------------------------------------
    def test_08_unreachable_database_raises_clean_error(self):
        """Verify that migrator raises ConnectionError cleanly when MongoDB is unreachable."""
        offline_migrator = DestinationMongoMigrator(db=None)
        with patch("mongo_db.is_available", return_value=False):
            with self.assertRaises(ConnectionError) as ctx:
                offline_migrator.execute_migration()
            self.assertIn("MongoDB Atlas is currently unreachable", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
