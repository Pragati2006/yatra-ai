"""
tests/test_destination_ingestion.py
Comprehensive test suite for J&K Tourist Destination Web Scraping & Data Enrichment module.

Covers:
1. Source permission assessment and compliance rules.
2. Factual attribute extraction (names, districts, coordinates, categories).
3. Original description synthesis (no verbatim copyright infringement).
4. Deduplication & non-overwriting of curated catalog records.
5. Error resilience (404, network timeout, malformed HTML, missing fields).
6. Request rate limiting and local caching.
7. MongoDB separate collection and offline JSON persistence.
8. Integration into tourism query answering, sightseeing catalog, and personalized recommendations.
9. Itinerary logistics awareness for new destinations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import explore_data
from services.destination_ingestion.models import DestinationRecord, ProvenanceInfo
from services.destination_ingestion.deduplicator import resolve_deduplication, find_curated_match, normalize_name
from services.destination_ingestion.scraper import DestinationScraper, OFFICIAL_SOURCES, FACTUAL_DESCRIPTIONS
from services.destination_ingestion.storage import DestinationStorage, COLLECTION_NAME
from services.destination_ingestion.manager import DestinationManager, get_destination_manager
import agents.coordinator as coordinator
import agents.knowledge_agent as knowledge_agent
import agents.content_agent as content_agent
import agents.itinerary_agent as itinerary_agent


SAMPLE_AKHNOOR_HTML = """<!DOCTYPE html>
<html>
<head><title>Akhnoor Fort | District Jammu | India</title></head>
<body>
<main>
  <h1>Akhnoor Fort</h1>
  <div class="show-category">
    <strong>Category</strong>
    <span>Historic</span>
  </div>
  <a href="https://www.google.com/maps/dir//32.896543,74.739271">Direction</a>
  <p>The Akhnoor fort which lies towards east of the town, on the bank of the Chenab river holds great significance.</p>
  <p>Work on the fort, actually began in 1762 at the behest of Raja Tegh Singh and was completed in 1802.</p>
</main>
</body>
</html>"""

SAMPLE_MALFORMED_HTML = """<html><body><div><p>Broken page with no headings or coordinates</p></div></body></html>"""


class TestDestinationIngestion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_cache = Path(self.temp_dir) / "cache"
        self.temp_data = Path(self.temp_dir) / "test_destinations.json"
        self.scraper = DestinationScraper(
            cache_dir=self.temp_cache,
            rate_limit_delay=0.01,
            cache_ttl_seconds=3600
        )
        self.storage = DestinationStorage(data_file=self.temp_data)
        self.manager = DestinationManager(storage=self.storage, scraper=self.scraper)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Source Permission Assessment & Compliance Rules
    # -------------------------------------------------------------------------
    def test_01_source_permission_assessment(self):
        """Verify that all configured official sources have valid provenance authorities and domains."""
        self.assertGreaterEqual(len(OFFICIAL_SOURCES), 3)
        domains = [s["domain"] for s in OFFICIAL_SOURCES]
        self.assertIn("jammu.nic.in", domains)
        self.assertIn("srinagar.nic.in", domains)
        self.assertIn("kishtwar.nic.in", domains)

        # Ensure copyright assessment explicitly accounts for Section 52(1) and photograph exclusion
        prov = ProvenanceInfo(
            authority="District Administration Jammu, NIC",
            source_url="https://jammu.nic.in/tourist-place/akhnoor-fort/",
            source_domain="jammu.nic.in"
        )
        self.assertIn("Factual attributes", prov.copyright_assessment)
        self.assertIn("photographs strictly omitted", prov.copyright_assessment)
        self.assertIn("Section 52(1) Indian Copyright Act", prov.permission_notes)

    # -------------------------------------------------------------------------
    # 2. Static HTML Parsing & Attribute Extraction
    # -------------------------------------------------------------------------
    def test_02_parse_destination_page_attributes(self):
        """Verify that destination names, coordinates, and categories are parsed correctly from official HTML."""
        with patch.object(self.scraper, "fetch_url", return_value=SAMPLE_AKHNOOR_HTML):
            src_info = {
                "district": "Jammu",
                "region": "Jammu",
                "authority": "District Administration Jammu, NIC",
                "domain": "jammu.nic.in"
            }
            record = self.scraper.parse_destination_page(
                "https://jammu.nic.in/tourist-place/akhnoor-fort/",
                src_info
            )
            self.assertIsNotNone(record)
            self.assertEqual(record.name, "Akhnoor Fort")
            self.assertEqual(record.district, "Jammu")
            self.assertEqual(record.region, "Jammu")
            self.assertEqual(record.latitude, 32.896543)
            self.assertEqual(record.longitude, 74.739271)
            self.assertIn("District Administration Jammu", record.coordinates_source)
            self.assertEqual(record.source_url, "https://jammu.nic.in/tourist-place/akhnoor-fort/")
            self.assertIsNone(record.image)  # Photo strictly omitted per copyright compliance
            self.assertIn("Photographs omitted", record.image_notice)

    # -------------------------------------------------------------------------
    # 3. Original Concise Description Synthesis (No Verbatim Copying)
    # -------------------------------------------------------------------------
    def test_03_original_concise_descriptions(self):
        """Verify that generated descriptions are original concise overviews and not copied government text."""
        with patch.object(self.scraper, "fetch_url", return_value=SAMPLE_AKHNOOR_HTML):
            src_info = {
                "district": "Jammu",
                "region": "Jammu",
                "authority": "District Administration Jammu, NIC",
                "domain": "jammu.nic.in"
            }
            record = self.scraper.parse_destination_page(
                "https://jammu.nic.in/tourist-place/akhnoor-fort/",
                src_info
            )
            self.assertIsNotNone(record)
            # Must NOT be identical to the raw paragraph in SAMPLE_AKHNOOR_HTML
            raw_p1 = "The Akhnoor fort which lies towards east of the town, on the bank of the Chenab river holds great significance."
            self.assertNotEqual(record.description, raw_p1)
            self.assertTrue(len(record.description) > 30)
            self.assertTrue(len(record.description) < 300)
            self.assertIn("Chenab River", record.description)

    # -------------------------------------------------------------------------
    # 4. Deduplication and Non-Overwriting of Curated Catalog Records
    # -------------------------------------------------------------------------
    def test_04_deduplication_preserves_curated_catalog(self):
        """Verify that records already in explore_data.PLACES are tagged as CURATED_PRESERVED and never overwritten."""
        # Amar Mahal Jammu is already curated in explore_data.PLACES as Amar Mahal Palace
        is_dup, dup_of, curated = resolve_deduplication("Amar Mahal Jammu", "https://jammu.nic.in/tourist-place/amar-mahal-jammu/")
        self.assertTrue(is_dup)
        self.assertEqual(dup_of, "Amar Mahal Palace")
        self.assertIsNotNone(curated)
        self.assertEqual(curated["name"], "Amar Mahal Palace")

        # New destination Akhnoor Fort is NOT in explore_data.PLACES
        is_dup_new, dup_new_of, _ = resolve_deduplication("Akhnoor Fort", "https://jammu.nic.in/tourist-place/akhnoor-fort/")
        self.assertFalse(is_dup_new)
        self.assertIsNone(dup_new_of)

    # -------------------------------------------------------------------------
    # 5. Error Resilience (404, Timeout, Malformed HTML, Missing Fields)
    # -------------------------------------------------------------------------
    def test_05_error_resilience_malformed_and_missing(self):
        """Verify robust handling of 404, malformed HTML, and missing fields without inventing false data."""
        # 404 or network failure returns None cleanly
        with patch.object(self.scraper, "fetch_url", return_value=None):
            record = self.scraper.parse_destination_page("https://jammu.nic.in/tourist-place/nonexistent/", {
                "district": "Jammu", "region": "Jammu", "authority": "NIC", "domain": "jammu.nic.in"
            })
            self.assertIsNone(record)

        # Malformed HTML with missing headings returns None cleanly
        with patch.object(self.scraper, "fetch_url", return_value=SAMPLE_MALFORMED_HTML):
            record_malformed = self.scraper.parse_destination_page("https://jammu.nic.in/tourist-place/broken/", {
                "district": "Jammu", "region": "Jammu", "authority": "NIC", "domain": "jammu.nic.in"
            })
            self.assertIsNone(record_malformed)

        # Missing timings and fees must NOT be hallucinated
        with patch.object(self.scraper, "fetch_url", return_value=SAMPLE_AKHNOOR_HTML):
            rec = self.scraper.parse_destination_page("https://jammu.nic.in/tourist-place/akhnoor-fort/", {
                "district": "Jammu", "region": "Jammu", "authority": "NIC", "domain": "jammu.nic.in"
            })
            self.assertIsNone(rec.timings)
            self.assertFalse(rec.timings_verified)
            self.assertIsNone(rec.entry_fee)
            self.assertFalse(rec.entry_fee_verified)

    # -------------------------------------------------------------------------
    # 6. Rate Limiting and Caching
    # -------------------------------------------------------------------------
    def test_06_rate_limiting_and_caching(self):
        """Verify that repeated requests hit local cache and avoid duplicate network calls."""
        mock_ctx = MagicMock()
        mock_ctx.status = 200
        mock_ctx.read.return_value = SAMPLE_AKHNOOR_HTML.encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_ctx
            url = "https://jammu.nic.in/tourist-place/akhnoor-fort/"
            # First fetch -> calls urlopen and writes cache
            content1 = self.scraper.fetch_url(url)
            self.assertEqual(mock_urlopen.call_count, 1)
            self.assertIsNotNone(content1)

            # Second fetch -> served from local file cache without network call
            content2 = self.scraper.fetch_url(url)
            self.assertEqual(mock_urlopen.call_count, 1)
            self.assertEqual(content1, content2)

    # -------------------------------------------------------------------------
    # 7. Storage Persistence (Separate MongoDB Collection & Local JSON)
    # -------------------------------------------------------------------------
    def test_07_storage_persistence(self):
        """Verify storage in dedicated JSON fallback and collection separation."""
        self.assertEqual(COLLECTION_NAME, "enriched_destinations")

        prov = ProvenanceInfo(
            authority="District Administration Jammu, NIC",
            source_url="https://jammu.nic.in/tourist-place/akhnoor-fort/",
            source_domain="jammu.nic.in"
        )
        rec = DestinationRecord(
            id="dest-akhnoor-fort",
            name="Akhnoor Fort",
            district="Jammu",
            region="Jammu",
            category="Historic Fort",
            category_type="historical_site",
            latitude=32.896543,
            longitude=74.739271,
            description="Historical fort on the Chenab river.",
            source_url="https://jammu.nic.in/tourist-place/akhnoor-fort/",
            source_domain="jammu.nic.in",
            provenance=prov
        )

        saved_count = self.storage.save_destinations([rec])
        self.assertEqual(saved_count, 1)
        self.assertTrue(self.temp_data.exists())

        loaded = self.storage.load_destinations()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["name"], "Akhnoor Fort")
        self.assertEqual(loaded[0]["provenance"]["source_domain"], "jammu.nic.in")

    # -------------------------------------------------------------------------
    # 8. Integration into Tourism Query Answering & Unified Catalog
    # -------------------------------------------------------------------------
    def test_08_coordinator_and_knowledge_agent_integration(self):
        """Verify that newly ingested destinations are discoverable in tourism queries and unified sightseeing."""
        # 1. Unified catalog includes both curated places and new destinations
        unified = content_agent.get_all_places_enriched()
        self.assertGreater(len(unified), len(explore_data.PLACES))
        names = [p["name"] for p in unified]
        self.assertIn("Akhnoor Fort", names)
        self.assertIn("Bhairavnath Temple", names)  # Curated place intact

        # 2. Coordinator can answer questions about newly ingested destinations
        res_akhnoor = coordinator.answer_tourism_query("Tell me about Akhnoor Fort")
        self.assertEqual(res_akhnoor["intent"], "TOURISM")
        self.assertEqual(res_akhnoor["last_tourism_place"], "Akhnoor Fort")
        self.assertIn("Akhnoor Fort", res_akhnoor["reply"])
        self.assertIn("Chenab", res_akhnoor["reply"])

        res_sinthan = coordinator.answer_tourism_query("What is Sinthan Top?")
        self.assertEqual(res_sinthan["intent"], "TOURISM")
        self.assertEqual(res_sinthan["last_tourism_place"], "Sinthan Top")
        self.assertIn("Sinthan Top", res_sinthan["reply"])

    # -------------------------------------------------------------------------
    # 9. Personalized Recommendations Integration
    # -------------------------------------------------------------------------
    def test_09_personalized_recommendations_with_new_destinations(self):
        """Verify that personalized recommendations incorporate enriched destinations matching preferences."""
        nature_recs = knowledge_agent.get_personalized_recommendations({"nature_focused": True})
        rec_names = [p["name"] for p in nature_recs]
        self.assertTrue(any(k in rec_names for k in ["Sinthan Top", "Chashma Shahi", "Pari Mahal", "Dachigam National Park"]))

    # -------------------------------------------------------------------------
    # 10. Itinerary Logistics & Canonical Awareness
    # -------------------------------------------------------------------------
    def test_10_itinerary_logistics_awareness(self):
        """Verify that newly ingested destinations have realistic regional hubs and logistics."""
        self.assertIn("Akhnoor Fort", itinerary_agent.DESTINATION_LOGISTICS)
        logistics = itinerary_agent.DESTINATION_LOGISTICS["Akhnoor Fort"]
        self.assertEqual(logistics["region"], "jammu_city")
        self.assertIn("Jammu", logistics["base_hub"])

        self.assertIn("Chashma Shahi", itinerary_agent.DESTINATION_LOGISTICS)
        cs_logistics = itinerary_agent.DESTINATION_LOGISTICS["Chashma Shahi"]
        self.assertEqual(cs_logistics["region"], "kashmir")
        self.assertIn("Srinagar", cs_logistics["base_hub"])


if __name__ == "__main__":
    unittest.main()
