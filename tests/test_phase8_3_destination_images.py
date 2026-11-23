"""
tests/test_phase8_3_destination_images.py
Comprehensive test suite for Phase 8.3:
Destination Image Enrichment & Conversational Image Display.
"""

import os
import sys
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import mongo_db
from services.destination_ingestion.storage import get_verified_images_map
from services.destination_ingestion.manager import DestinationManager
from agents.coordinator import answer_tourism_query, _resolve_destination_images
from agents.orchestrator import _finalize_turn_response


class TestPhase83DestinationImages(unittest.TestCase):
    """Test suite for destination image metadata, validation, retrieval, and chat display."""

    @classmethod
    def setUpClass(cls):
        cls.data_file = REPO_ROOT / "data" / "verified_destination_images.json"
        with open(cls.data_file, encoding="utf-8") as f:
            cls.verified_images = json.load(f)

    def test_01_all_43_destinations_catalogued(self):
        """All 43 destinations are catalogued in verified_destination_images.json."""
        self.assertEqual(len(self.verified_images), 43)

    def test_02_verified_photos_and_fallback_counts(self):
        """All 43 destinations have verified photos catalogued in Phase 8.8.52."""
        with_photos = [d for d in self.verified_images.values() if d.get("photo_count", 0) > 0]
        fallback_only = [d for d in self.verified_images.values() if d.get("photo_count", 0) == 0]
        self.assertEqual(len(self.verified_images), 43)
        self.assertEqual(len(with_photos), 43)
        self.assertEqual(len(fallback_only), 0)

    def test_03_image_metadata_structure_and_https(self):
        """All verified photographs contain valid HTTPS or curated asset URLs, author, license, and attribution."""
        for dest_id, d in self.verified_images.items():
            if d["photo_count"] > 0:
                self.assertTrue(d["image_url"].startswith("https://") or d["image_url"].startswith("/assets/"))
                self.assertGreater(len(d["image_gallery"]), 0)
                for img in d["image_gallery"]:
                    self.assertTrue(img["image_url"].startswith("https://") or img["image_url"].startswith("/assets/"))
                    self.assertTrue(img["thumbnail_url"].startswith("https://") or img["thumbnail_url"].startswith("/assets/"))
                    self.assertTrue(img["source_page_url"].startswith("https://") or img["source_page_url"].startswith("/assets/"))
                    self.assertTrue(len(img["photographer"].strip()) > 0)
                    self.assertTrue(len(img["license"].strip()) > 0)
                    self.assertTrue(len(img["attribution"].strip()) > 0)
                    self.assertTrue("Wikimedia Commons" in img["attribution"] or "Jammu & Kashmir Tourism" in img["attribution"] or "Official Archive" in img["attribution"])
                    self.assertTrue(img["verified"])
                    self.assertGreaterEqual(img["width"], 400)
                    self.assertGreaterEqual(img["height"], 300)

    def test_04_conversational_resolution_single_destinations(self):
        """Conversational queries for specific destinations resolve genuine photos."""
        # Pari Mahal
        pari_imgs, pari_dest = _resolve_destination_images("Tell me about Pari Mahal.")
        self.assertGreaterEqual(len(pari_imgs), 2)
        self.assertIn("Pari Mahal", pari_dest["name"])
        self.assertTrue(any("Pari Mahal" in img["title"] for img in pari_imgs))

        # Akhnoor Fort
        akh_imgs, akh_dest = _resolve_destination_images("Tell me about Akhnoor Fort.")
        self.assertGreaterEqual(len(akh_imgs), 2)
        self.assertIn("Akhnoor Fort", akh_dest["name"])
        self.assertTrue(any("Akhnoor" in img["title"] for img in akh_imgs))

        # Machail Mata
        mach_imgs, mach_dest = _resolve_destination_images("Show me pictures of Machail Mata.")
        self.assertGreaterEqual(len(mach_imgs), 2)
        self.assertIn("Machail Mata", mach_dest["name"])
        self.assertTrue(any("Machail" in img["title"] for img in mach_imgs))

        # Dachigam
        dachi_imgs, dachi_dest = _resolve_destination_images("Is Dachigam National Park suitable for nature lovers?")
        self.assertGreaterEqual(len(dachi_imgs), 2)
        self.assertIn("Dachigam", dachi_dest["name"])
        self.assertTrue(any("Dachigam" in img["title"] or "hangul" in img["title"].lower() for img in dachi_imgs))

        # Aru Valley: resolves to actual Aru Valley photographs, never Pahalgam Golf Course
        aru_imgs, aru_dest = _resolve_destination_images("Show me pictures of Aru Valley.")
        self.assertGreaterEqual(len(aru_imgs), 1)
        self.assertTrue(all("Aru" in img["title"] for img in aru_imgs))
        self.assertFalse(any("Golf" in img["title"] for img in aru_imgs))

        # Chandanwari: resolves to actual Chandanwari photo
        chan_imgs, chan_dest = _resolve_destination_images("Tell me about Chandanwari and show photos.")
        self.assertGreaterEqual(len(chan_imgs), 1)
        self.assertTrue(all("Chandanwari" in img["title"] for img in chan_imgs))

        # Vaishno Devi Bhawan: strictly resolves to Holy Cave Bhawan, returning ONLY genuine Bhawan photo
        bhawan_imgs, bhawan_dest = _resolve_destination_images("Show pictures of Vaishno Devi Bhawan.")
        self.assertEqual(len(bhawan_imgs), 1)
        self.assertEqual(bhawan_imgs[0]["title"], "Holy Cave Bhawan, Shri Mata Vaishno Devi")
        self.assertIn("Mata_Vaishno_Devi_Bhawan.jpg", bhawan_imgs[0]["image_url"])
        self.assertIn("Holy Cave Bhawan", bhawan_dest["name"])
        # Never returns the 2 Katra municipal overview photos
        self.assertFalse(any("Houses and Shops" in img["title"] or "KATRA TOWN" in img["title"] for img in bhawan_imgs))

        # Ordinary Katra query with photo intent: returns Katra municipal overview photos, NEVER Bhawan-only photo
        katra_imgs, katra_dest = _resolve_destination_images("Show me pictures of Katra.")
        self.assertEqual(len(katra_imgs), 2)
        self.assertEqual(katra_dest["name"], "Katra")
        self.assertTrue(all("Bhawan" not in img["title"] for img in katra_imgs))
        self.assertTrue(any("Houses and Shops" in img["title"] for img in katra_imgs))
        self.assertTrue(any("KATRA TOWN" in img["title"] for img in katra_imgs))

        # Generic Katra query without photo intent: suppressed
        gen_katra_imgs, _ = _resolve_destination_images("Tell me about Katra.")
        self.assertEqual(len(gen_katra_imgs), 0)

        # Doodhpathri & Baisaran Valley: photos suppressed until verified images exist
        doodh_imgs, _ = _resolve_destination_images("Tell me about Doodhpathri and show photos.")
        self.assertEqual(len(doodh_imgs), 0)

        bais_imgs, _ = _resolve_destination_images("Tell me about Baisaran Valley and show photographs.")
        self.assertEqual(len(bais_imgs), 0)

    def test_05_conversational_resolution_regional_queries(self):
        """Regional queries return multi-destination image galleries."""
        # Kishtwar
        k_imgs, k_dest = _resolve_destination_images("What can I visit in Kishtwar?")
        self.assertGreaterEqual(len(k_imgs), 2)

        # Srinagar
        s_imgs, s_dest = _resolve_destination_images("Suggest places to visit in Srinagar.")
        self.assertGreaterEqual(len(s_imgs), 2)

        # Jammu Heritage
        j_imgs, j_dest = _resolve_destination_images("Suggest historical places near Jammu.")
        self.assertGreaterEqual(len(j_imgs), 2)

    def test_06_non_tourism_queries_do_not_return_images(self):
        """Ordinary non-tourism queries do not attach destination images."""
        res = answer_tourism_query("How do I register for RFID parchi at Katra?")
        # When asking for registration facilities, it should not attach random tourist spot galleries
        imgs, dest = _resolve_destination_images(
            user_text="How do I book a train ticket from Delhi to Katra?",
            detected_place=None,
            specific_places=[]
        )
        self.assertEqual(len(imgs), 0)

    def test_07_atlas_tourist_attractions_intact(self):
        """Atlas tourist_attractions collection retains 43 documents with intact core fields."""
        if not mongo_db.is_available():
            self.skipTest("Atlas not connected")

        coll = mongo_db.tourist_attractions
        count = coll.count_documents({})
        self.assertEqual(count, 43)

        # Ingested doc check
        pari = coll.find_one({"name": "Pari Mahal"})
        self.assertIsNotNone(pari)
        self.assertEqual(pari.get("district"), "Srinagar")
        self.assertEqual(pari.get("category"), "Heritage Garden")
        self.assertTrue(pari.get("image_verified"))
        self.assertEqual(len(pari.get("image_gallery", [])), 3)

        # Curated doc check
        patnitop = coll.find_one({"name": "Patnitop"})
        self.assertIsNotNone(patnitop)
        self.assertTrue(patnitop.get("image_verified"))
        self.assertEqual(len(patnitop.get("image_gallery", [])), 3)

    def test_08_local_fallback_unified_catalog_has_images(self):
        """Unified catalog in local mode attaches verified images to destinations."""
        mgr = DestinationManager()
        places = mgr.get_unified_places_catalog()
        self.assertEqual(len(places), 43)

        # Check that Pari Mahal has image_url and image_gallery
        pari = next((p for p in places if p["name"] == "Pari Mahal"), None)
        self.assertIsNotNone(pari)
        self.assertTrue(pari.get("image_url", "").startswith("https://"))
        self.assertGreaterEqual(len(pari.get("image_gallery", [])), 1)

    def test_09_orchestrator_finalization_preserves_images(self):
        """Orchestrator _finalize_turn_response preserves destination_images and metadata."""
        sample_turn = {
            "intent": "TOURISM",
            "reply": "Pari Mahal is a stunning seven-terraced Mughal garden.",
            "destination_images": [{"title": "Pari Mahal Arch", "thumbnail_url": "https://thumb..."}],
            "matched_destination": {"name": "Pari Mahal", "district": "Srinagar"},
        }
        finalized = _finalize_turn_response(sample_turn, sid="test-img-session", default_intent="TOURISM")
        self.assertEqual(len(finalized["destination_images"]), 1)
        self.assertEqual(finalized["matched_destination"]["name"], "Pari Mahal")

    def test_10_backend_duration_and_pax_validation(self):
        """Backend validates duration and pax bounds explicitly without silent truncation."""
        from agents.itinerary_agent import build_itinerary

        # 1. Omitted duration uses existing default
        itin_omitted = build_itinerary({}, request={})
        self.assertGreaterEqual(len(itin_omitted), 3)

        itin_none = build_itinerary({}, request={"duration_days": None})
        self.assertGreaterEqual(len(itin_none), 3)

        # 2. Valid durations (10, 14, 21, 90) retain exact values
        for d in [10, 14, 21, 90]:
            itin = build_itinerary({}, request={"duration_days": d})
            self.assertEqual(len(itin), d, f"Itinerary for {d} days must have exactly {d} days")

        # 3. Invalid durations: "abc", 10.5, 0, -1, 120
        for inv_d in ["abc", 10.5, 0, -1, 120, ""]:
            with self.assertRaises(ValueError, msg=f"Duration {inv_d} must raise ValueError"):
                build_itinerary({}, request={"duration_days": inv_d})

        # 4. Valid pilgrim counts: 1, 10, 50, 200
        for p in [1, 10, 50, 200]:
            itin = build_itinerary({}, request={"duration_days": 3, "pax": p})
            self.assertEqual(len(itin), 3)

        # 5. Invalid pilgrim counts: "abc", 10.5, 0, -1, 201
        for inv_p in ["abc", 10.5, 0, -1, 201, ""]:
            with self.assertRaises(ValueError, msg=f"Pax {inv_p} must raise ValueError"):
                build_itinerary({}, request={"duration_days": 3, "pax": inv_p})

    def test_11_api_request_validation_http_400(self):
        """API endpoints reject invalid duration and pilgrim requests with HTTP 400."""
        from fastapi import HTTPException
        from backend.routes.yatra import itinerary, confirm_booking, ItineraryRequest, ConfirmBookingRequest

        # Invalid durations to /api/yatra/itinerary must return HTTP 400
        for inv_d in ["abc", 10.5, 0, -1, 120, ""]:
            with self.assertRaises(HTTPException, msg=f"Duration {inv_d} must return HTTP 400") as ctx:
                itinerary(ItineraryRequest(request={"duration_days": inv_d}))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertTrue(len(ctx.exception.detail) > 0)

        # Invalid pilgrim counts to /api/yatra/itinerary must return HTTP 400
        for inv_p in ["abc", 10.5, 0, -1, 201, ""]:
            with self.assertRaises(HTTPException, msg=f"Pax {inv_p} must return HTTP 400") as ctx:
                itinerary(ItineraryRequest(request={"duration_days": 3, "pax": inv_p}))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertTrue(len(ctx.exception.detail) > 0)

        # Invalid pilgrim counts to /api/yatra/confirm must return HTTP 400
        for inv_p in ["abc", 10.5, 0, -1, 201, ""]:
            with self.assertRaises(HTTPException, msg=f"Confirm pax {inv_p} must return HTTP 400") as ctx:
                confirm_booking(ConfirmBookingRequest(option={}, user_name="Test", pax=inv_p))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertTrue(len(ctx.exception.detail) > 0)

    def test_12_bhawan_and_katra_photo_precision(self):
        """Bhawan queries exclude Katra municipal photos; generic Katra queries do not receive Bhawan photos."""
        # Bhawan-specific photos exclude Katra municipal photos
        bhawan_imgs, bhawan_dest = _resolve_destination_images("Show pictures of Vaishno Devi Bhawan.")
        self.assertEqual(len(bhawan_imgs), 1)
        self.assertEqual(bhawan_imgs[0]["title"], "Holy Cave Bhawan, Shri Mata Vaishno Devi")
        self.assertIn("Mata_Vaishno_Devi_Bhawan.jpg", bhawan_imgs[0]["image_url"])
        self.assertFalse(any("Houses and Shops" in img["title"] or "KATRA TOWN" in img["title"] for img in bhawan_imgs))

        # Katra town with photo intent receives municipal photos, never Bhawan-only photos
        katra_imgs, katra_dest = _resolve_destination_images("Show me pictures of Katra.")
        self.assertEqual(len(katra_imgs), 2)
        self.assertTrue(all("Bhawan" not in img["title"] for img in katra_imgs))
        self.assertTrue(any("Houses and Shops" in img["title"] for img in katra_imgs))
        self.assertTrue(any("KATRA TOWN" in img["title"] for img in katra_imgs))

        # Generic Katra queries without photo intent return no attached photos
        gen_katra_imgs, _ = _resolve_destination_images("Tell me about Katra.")
        self.assertEqual(len(gen_katra_imgs), 0)


if __name__ == "__main__":
    unittest.main()
