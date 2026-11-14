"""
tests/test_phase9_3b_2_isolation.py
Comprehensive verification test suite for Phase 9.3B.2:
Synthetic Accommodation Isolation & Fallback Remediation.

Covers:
1. Empty catalog search returns NO_MATCHING_PROPERTIES and empty list (no synthetic fallback).
2. Missing catalog JSON returns CATALOG_UNAVAILABLE and empty list.
3. Malformed catalog JSON returns CATALOG_UNAVAILABLE and empty list.
4. Catalog service exception returns controlled empty list (no synthetic fallback).
5. coordinator.get_hotel_options strictly never invokes db.search_hotels.
6. orchestrator.coordinate_plan strictly never invokes db.search_hotels.
7. orchestrator.handle_booking_navigation_intent sets hotel to None when unselected (no Devi Darshan placeholder).
8. No Devi Darshan placeholder in saved trip persistence or receipts.
9. rooms_available == None remains strictly None (unknown inventory preserved).
10. Multi-room requests (min_rooms >= 2) marked UNVERIFIED with explanatory note.
11. Valid matching catalog searches return authentic properties and CATALOG_SUCCESS.
12. Central agent search_accommodation_options tool execution remains functional.
13. Budget calculation remains valid when accommodation is unselected.
14. Backend route /api/yatra/accommodation distinguishes SUCCESS, NO_MATCH, and UNAVAILABLE.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure yatra-ai is on PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
YATRA_DIR = os.path.dirname(CURRENT_DIR)
if YATRA_DIR not in sys.path:
    sys.path.insert(0, YATRA_DIR)

from services.accommodation_catalog import (
    get_catalog_load_error,
    get_catalog_status,
    load_catalog,
    search_hotels_for_orchestrator,
    search_hotels_with_status,
    search_properties,
)
import agents.coordinator as coordinator
import agents.orchestrator as orchestrator
from agents import budget_engine
from backend.routes.yatra import accommodation, HotelRequest


class TestPhase93B2Isolation(unittest.TestCase):
    """Test suite for Phase 9.3B.2 synthetic accommodation isolation."""

    @classmethod
    def setUpClass(cls):
        load_catalog(force_reload=True)

    def test_01_empty_catalog_result_no_synthetic_fallback(self):
        """1. Verify valid search with no matches returns NO_MATCHING_PROPERTIES and empty list."""
        hotels, status = search_hotels_with_status(category="NonExistentCategory999")
        self.assertEqual(status, "NO_MATCHING_PROPERTIES")
        self.assertEqual(hotels, [])
        self.assertEqual(len(hotels), 0)

    def test_02_catalog_json_missing(self):
        """2. Verify missing catalog JSON triggers CATALOG_UNAVAILABLE and empty list."""
        non_existent_path = os.path.join(tempfile.gettempdir(), "non_existent_catalog_123.json")
        props = load_catalog(force_reload=True, catalog_path=non_existent_path)
        self.assertEqual(props, {})
        err = get_catalog_load_error()
        self.assertIsNotNone(err)
        self.assertIn("not found", err.lower())
        self.assertEqual(get_catalog_status(), "CATALOG_UNAVAILABLE")

        hotels, status = search_hotels_with_status()
        self.assertEqual(status, "CATALOG_UNAVAILABLE")
        self.assertEqual(hotels, [])

        # Reload authentic catalog for subsequent tests
        load_catalog(force_reload=True)

    def test_03_catalog_json_malformed(self):
        """3. Verify corrupted JSON triggers CATALOG_UNAVAILABLE and empty list."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as tf:
            tf.write("{ this is invalid json ::: 123 }")
            temp_path = tf.name

        try:
            props = load_catalog(force_reload=True, catalog_path=temp_path)
            self.assertEqual(props, {})
            err = get_catalog_load_error()
            self.assertIsNotNone(err)
            self.assertIn("error", err.lower())
            self.assertEqual(get_catalog_status(), "CATALOG_UNAVAILABLE")

            hotels, status = search_hotels_with_status()
            self.assertEqual(status, "CATALOG_UNAVAILABLE")
            self.assertEqual(hotels, [])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            load_catalog(force_reload=True)

    def test_04_catalog_service_exception_returns_controlled_empty_list(self):
        """4. Verify catalog service exception returns empty list without crashing."""
        with patch("services.accommodation_catalog.search_properties", side_effect=RuntimeError("Disk failure")):
            hotels = search_hotels_for_orchestrator(category="Budget")
            self.assertEqual(hotels, [])

    def test_05_coordinator_never_calls_db_search_hotels(self):
        """5. Verify coordinator.get_hotel_options strictly never invokes db.search_hotels."""
        with patch("db.search_hotels") as mock_db_search:
            # Case A: Valid search
            res1 = coordinator.get_hotel_options("2026-11-15", category="Budget")
            self.assertGreater(len(res1), 0)
            mock_db_search.assert_not_called()

            # Case B: Unmatched search
            res2 = coordinator.get_hotel_options("2026-11-15", category="NonExistentCategory")
            self.assertEqual(res2, [])
            mock_db_search.assert_not_called()

            # Case C: Catalog crash
            with patch("services.accommodation_catalog.search_hotels_for_orchestrator", side_effect=Exception("Crash")):
                res3 = coordinator.get_hotel_options("2026-11-15")
                self.assertEqual(res3, [])
                mock_db_search.assert_not_called()

    def test_06_orchestrator_never_calls_db_search_hotels(self):
        """6. Verify orchestrator.coordinate_plan strictly never invokes db.search_hotels."""
        with patch("db.search_hotels") as mock_db_search:
            # Case A: Normal plan
            plan1 = orchestrator.coordinate_plan({
                "origin": "Delhi",
                "start_date": "2026-11-15",
                "duration_days": 4,
                "pax": 2,
                "hotel_category": "Budget",
            })
            self.assertIsNotNone(plan1.get("selected_options", {}).get("accommodation"))
            mock_db_search.assert_not_called()

            # Case B: Simulated catalog crash in orchestrator
            with patch("services.accommodation_catalog.search_hotels_with_status", side_effect=RuntimeError("Catalog Down")):
                plan2 = orchestrator.coordinate_plan({
                    "origin": "Delhi",
                    "start_date": "2026-11-15",
                    "duration_days": 4,
                    "pax": 2,
                    "hotel_category": "Budget",
                })
                # Accommodation must remain unselected (None), not fictional
                sel_hotel = plan2.get("selected_options", {}).get("accommodation")
                self.assertIsNone(sel_hotel)
                mock_db_search.assert_not_called()
                # Must provide clear explanation advisory
                advisory = plan2.get("request", {}).get("accommodation_advisory", "")
                self.assertIn("temporarily unavailable", advisory)

    def test_07_no_devi_darshan_in_booking_handoff(self):
        """7. Verify booking navigation intent does not inject fictional Devi Darshan Hotel."""
        res = orchestrator.handle_booking_navigation_intent(
            user_text="Proceed to booking",
            session_data={"session_id": "test-sid-1", "state": {"requirements": {"origin": "Delhi", "pax": 2}}},
        )
        hotel = res.get("hotel")
        self.assertIsNone(hotel, "Unselected hotel must be None, not a fictional placeholder")
        plan_hotel = res.get("plan", {}).get("hotel")
        self.assertIsNone(plan_hotel)

    def test_08_no_devi_darshan_in_pdf_and_receipts(self):
        """8. Verify PDF generator does not invent Devi Darshan Hotel when hotel is unselected."""
        from utils.pdf_generator import generate_pdf_pass_bytes
        pdf_bytes = generate_pdf_pass_bytes(booking={
            "booking_id": "VD-TEST-99",
            "user_name": "Test Devotee",
            "pax_count": 2,
            "slot_date": "2026-11-15",
            "total_price": 1000,
            # hotel_name omitted intentionally
        })
        self.assertIsInstance(pdf_bytes, bytes)
        pdf_text = pdf_bytes.decode("latin1", errors="ignore")
        self.assertNotIn("Devi Darshan Hotel", pdf_text)
        self.assertIn("Accommodation not selected", pdf_text)

    def test_09_rooms_available_none_remains_unknown(self):
        """9. Verify rooms_available remains strictly None without converting to 0 or positive int."""
        hotels = search_hotels_for_orchestrator(min_rooms=1)
        self.assertGreater(len(hotels), 0)
        for h in hotels:
            self.assertIsNone(h.get("rooms_available"))
            self.assertEqual(h.get("availability_status"), "NOT_CHECKED")

    def test_10_minimum_two_room_request_marked_unverified(self):
        """10. Verify multi-room request is marked UNVERIFIED with explanatory note."""
        hotels = search_hotels_for_orchestrator(min_rooms=2)
        self.assertGreater(len(hotels), 0)
        for h in hotels:
            self.assertEqual(h.get("room_requirement_status"), "UNVERIFIED")
            self.assertIn("2 rooms", h.get("room_requirement_note", ""))
            self.assertIn("UNVERIFIED", h.get("room_requirement_note", ""))

    def test_11_valid_matching_catalog_results_work(self):
        """11. Verify authentic Katra properties return with CATALOG_SUCCESS."""
        hotels, status = search_hotels_with_status(category="Budget")
        self.assertEqual(status, "CATALOG_SUCCESS")
        self.assertGreaterEqual(len(hotels), 4)
        names = [h["name"] for h in hotels]
        self.assertIn("Niharika Complex (Yatri Niwas, Shakti Bhawan & Ashirwad)", names)

    def test_12_central_agent_tool_works(self):
        """12. Verify search_accommodation_options tool in central agent."""
        from agents.central_agent import search_accommodation_options
        res = search_accommodation_options.invoke({"category": "SMVDSB"})
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("count"), 4)
        for acc in res.get("accommodations", []):
            self.assertEqual(acc.get("operator_type"), "SMVDSB")
            self.assertEqual(acc.get("availability_status"), "NOT_CHECKED")

    def test_13_budget_engine_with_unselected_hotel(self):
        """13. Verify budget calculation computes valid verified total when accommodation is None."""
        b = budget_engine.calculate_budget(
            pax=2,
            transport={"mode": "train", "price": 400},
            darshan_slot={"category": "Normal Darshan", "price": 0},
            accommodation=None,
            duration_days=4,
        )
        self.assertTrue(b["is_complete"])
        self.assertEqual(b["verified_costs"]["transport"], 800.0)
        self.assertEqual(b["verified_costs"]["accommodation"], 0.0)
        self.assertEqual(b["verified_costs"]["total_verified"], 800.0)
        self.assertFalse(b["verified_costs"]["details"]["accommodation"]["selected"])

    def test_14_backend_route_status_distinction(self):
        """14. Verify /api/yatra/accommodation distinguishes SUCCESS, NO_MATCH, and UNAVAILABLE."""
        # A: Success
        r1 = accommodation(HotelRequest(check_in_date="2026-11-15", category="Budget", min_rooms=2))
        self.assertEqual(r1["status"], "success")
        self.assertEqual(r1["catalog_status"], "CATALOG_SUCCESS")
        self.assertGreater(r1["count"], 0)
        self.assertEqual(r1["hotels"][0]["room_requirement_status"], "UNVERIFIED")

        # B: No matching properties
        r2 = accommodation(HotelRequest(check_in_date="2026-11-15", category="NonExistentCategory"))
        self.assertEqual(r2["status"], "no_matching_properties")
        self.assertEqual(r2["catalog_status"], "NO_MATCHING_PROPERTIES")
        self.assertEqual(r2["count"], 0)
        self.assertEqual(r2["hotels"], [])

        # C: Catalog unavailable
        with patch("services.accommodation_catalog.get_catalog_load_error", return_value="Disk failure"):
            r3 = accommodation(HotelRequest(check_in_date="2026-11-15", category="Budget"))
            self.assertEqual(r3["status"], "catalog_unavailable")
            self.assertEqual(r3["catalog_status"], "CATALOG_UNAVAILABLE")
            self.assertEqual(r3["count"], 0)
            self.assertEqual(r3["hotels"], [])


if __name__ == "__main__":
    unittest.main()
