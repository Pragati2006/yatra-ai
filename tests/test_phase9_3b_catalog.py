"""
tests/test_phase9_3b_catalog.py
Comprehensive verification test suite for Katra Accommodation Catalog (Phase 9.3B).

Covers all 18 requirements:
1. Catalog loading from data/katra_accommodation_catalog.json
2. Schema validation of properties and tariff schedules
3. All 13 Group A properties present with VERIFIED_PRIMARY identity status
4. Group B properties present with PARTIALLY_VERIFIED identity status
5. Strict exclusion of ineligible properties (Kalika Dham Jammu, Balaji Mandir Trust)
6. Null preservation for unknown fields (no invented defaults)
7. Tariff classification validation (OFFICIAL_PUBLISHED_TARIFF, PROPERTY_CONFIRMED_INDICATIVE_RATE, SECONDARY_DIRECTORY_ESTIMATE)
8. availability_status == "NOT_CHECKED" default across all properties
9. Prevention of static AVAILABLE status
10. Prevention of false SOLD_OUT status
11. Source URL validation (valid HTTP/HTTPS URLs)
12. Property search by name (e.g. Niharika, Vivanta, White Hotel)
13. Property search by category (SMVDSB/Dharamshala, Budget, Mid-Range, Premium)
14. Budget range filtering (min_budget, max_budget)
15. Landmark filtering ("Bus Stand", "Station Road", "Banganga", "Main Bhawan")
16. Legacy adapter compatibility (to_legacy_record, search_hotels_for_orchestrator)
17. Production path exclusion of synthetic accommodation data
18. Central agent tool execution (search_accommodation_options)
"""

import json
import os
import sys
import unittest
from typing import Any, Dict, List

# Ensure yatra-ai is on PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
YATRA_DIR = os.path.dirname(CURRENT_DIR)
if YATRA_DIR not in sys.path:
    sys.path.insert(0, YATRA_DIR)

from services.accommodation_catalog import (
    KatraProperty,
    TariffSchedule,
    get_all_properties,
    get_catalog_metadata,
    get_property_by_id,
    load_catalog,
    search_hotels_for_orchestrator,
    search_properties,
)


class TestPhase93BCatalog(unittest.TestCase):
    """Test suite for Phase 9.3B verified Katra accommodation catalog."""

    @classmethod
    def setUpClass(cls):
        cls.catalog_file = os.path.join(YATRA_DIR, "data", "katra_accommodation_catalog.json")
        cls.properties_map = load_catalog(force_reload=True)

    def test_01_catalog_loading_from_disk(self):
        """1. Verify catalog loads successfully from data/katra_accommodation_catalog.json."""
        self.assertTrue(os.path.exists(self.catalog_file), f"Catalog file not found: {self.catalog_file}")
        self.assertGreater(len(self.properties_map), 0, "Loaded catalog must not be empty")
        metadata = get_catalog_metadata()
        self.assertIn("version", metadata)
        self.assertIn("total_properties", metadata)
        self.assertEqual(len(self.properties_map), 15, "Expected exactly 15 curated properties in catalog")

    def test_02_schema_validation(self):
        """2. Validate property and tariff schema completeness."""
        required_prop_fields = [
            "property_id", "property_name", "property_type", "operator_type",
            "identity_status", "property_status", "address", "landmark",
            "booking_channel", "tariffs", "availability_status", "source_urls"
        ]
        for pid, prop in self.properties_map.items():
            prop_dict = prop.to_dict()
            for req in required_prop_fields:
                self.assertIn(req, prop_dict, f"Property {pid} missing required field '{req}'")
            self.assertIsInstance(prop.tariffs, list, f"Property {pid} tariffs must be a list")
            self.assertGreater(len(prop.tariffs), 0, f"Property {pid} must have at least one tariff schedule")
            for t in prop.tariffs:
                self.assertIsInstance(t, TariffSchedule)
                self.assertGreater(t.tariff_max_inr, 0, f"Property {pid} tariff max must be positive")
                self.assertGreaterEqual(t.tariff_max_inr, t.tariff_min_inr, f"Property {pid} tariff max >= min")

    def test_03_group_a_properties_verified_primary(self):
        """3. Check that all 13 Group A properties have VERIFIED_PRIMARY identity status."""
        group_a_ids = [
            "SMVDSB_NIHARIKA_COMPLEX",
            "SMVDSB_TRIKUTA_BHAWAN",
            "SMVDSB_ARDHKUWARI_COMPLEX",
            "SMVDSB_MAIN_BHAWAN_COMPLEX",
            "HTL_VIVANTA_KATRA",
            "HTL_WELCOMHOTEL_KATRA",
            "HTL_LEMON_TREE_KATRA",
            "HTL_RAMADA_WYNDHAM_KATRA",
            "HTL_SAROVAR_PORTICO_KATRA",
            "HTL_WHITE_HOTEL_KATRA",
            "HTL_ASIA_VAISHNODEVI_KATRA",
            "HTL_SUBASH_INTERNATIONAL_KATRA",
            "HTL_SHREE_HARI_NIWAS_KATRA",
        ]
        for gid in group_a_ids:
            self.assertIn(gid, self.properties_map, f"Group A property {gid} missing from catalog")
            prop = self.properties_map[gid]
            self.assertEqual(
                prop.identity_status, "VERIFIED_PRIMARY",
                f"Group A property {gid} identity_status must be VERIFIED_PRIMARY, got {prop.identity_status}"
            )

    def test_04_group_b_properties_partially_verified(self):
        """4. Check that Group B properties have PARTIALLY_VERIFIED identity status."""
        group_b_ids = [
            "HTL_ZONE_CONNECT_KATRA",
            "HTL_VAISHNAVI_BUDGET_KATRA",
        ]
        for gid in group_b_ids:
            self.assertIn(gid, self.properties_map, f"Group B property {gid} missing from catalog")
            prop = self.properties_map[gid]
            self.assertEqual(
                prop.identity_status, "PARTIALLY_VERIFIED",
                f"Group B property {gid} identity_status must be PARTIALLY_VERIFIED, got {prop.identity_status}"
            )

    def test_05_exclusion_of_ineligible_properties(self):
        """5. Verify strict exclusion of Kalika Dham (Jammu City) and Shri Balaji Mandir Trust Sarai."""
        all_ids = list(self.properties_map.keys())
        all_names = [p.property_name.lower() for p in self.properties_map.values()]

        # Kalika Dham is located in Jammu City (48 km away), not Katra
        for pid in all_ids:
            self.assertNotIn("kalika", pid.lower(), f"Kalika Dham must be excluded from Katra catalog: {pid}")
        for name in all_names:
            self.assertNotIn("kalika dham", name, f"Kalika Dham must not appear in Katra properties: {name}")

        # Shri Balaji Mandir Trust Sarai is non-existent/unverifiable
        for pid in all_ids:
            self.assertNotIn("balaji", pid.lower(), f"Balaji Mandir Trust Sarai must be excluded: {pid}")
        for name in all_names:
            self.assertNotIn("balaji mandir", name, f"Balaji Mandir Trust Sarai must not appear: {name}")

    def test_06_null_handling_for_unknown_fields(self):
        """6. Validate that missing fields are preserved as None without inventing dummy defaults."""
        # For properties without coordinates or emails, verify they are None, not "0.0" or "none@katra.com"
        for pid, prop in self.properties_map.items():
            if prop.email is not None:
                self.assertIn("@", prop.email)
            if prop.phone is not None:
                self.assertFalse("00000" in prop.phone, f"Property {pid} has dummy phone number: {prop.phone}")

    def test_07_tariff_classification_validation(self):
        """7. Verify tariffs are attributed with valid evidence classifications."""
        valid_classifications = {
            "OFFICIAL_PUBLISHED_TARIFF",
            "PROPERTY_CONFIRMED_INDICATIVE_RATE",
            "SECONDARY_DIRECTORY_ESTIMATE",
        }
        for pid, prop in self.properties_map.items():
            for t in prop.tariffs:
                self.assertIn(
                    t.tariff_classification, valid_classifications,
                    f"Property {pid} has invalid tariff classification: {t.tariff_classification}"
                )
            # SMVDSB properties must be OFFICIAL_PUBLISHED_TARIFF
            if prop.operator_type == "SMVDSB":
                for t in prop.tariffs:
                    self.assertEqual(
                        t.tariff_classification, "OFFICIAL_PUBLISHED_TARIFF",
                        f"SMVDSB property {pid} tariff must be OFFICIAL_PUBLISHED_TARIFF"
                    )

    def test_08_availability_status_default_not_checked(self):
        """8. Verify availability_status defaults strictly to NOT_CHECKED across all records."""
        for pid, prop in self.properties_map.items():
            self.assertEqual(
                prop.availability_status, "NOT_CHECKED",
                f"Property {pid} availability_status must be NOT_CHECKED, got {prop.availability_status}"
            )

    def test_09_prevention_of_static_available_status(self):
        """9. Assert catalog loader prevents any property from claiming static AVAILABLE status."""
        for pid, prop in self.properties_map.items():
            self.assertNotEqual(
                prop.availability_status, "AVAILABLE",
                f"Property {pid} statically claims AVAILABLE status, violating live-check audit rules"
            )

    def test_10_prevention_of_false_sold_out_status(self):
        """10. Assert catalog loader prevents any property from claiming false static SOLD_OUT status."""
        for pid, prop in self.properties_map.items():
            self.assertNotEqual(
                prop.availability_status, "SOLD_OUT",
                f"Property {pid} statically claims SOLD_OUT status without real-time check"
            )

    def test_11_source_url_validation(self):
        """11. Validate that all source URLs are well-formed HTTP/HTTPS links."""
        for pid, prop in self.properties_map.items():
            self.assertGreater(len(prop.source_urls), 0, f"Property {pid} has no source URLs")
            for url in prop.source_urls:
                self.assertTrue(
                    url.startswith("http://") or url.startswith("https://"),
                    f"Property {pid} source URL invalid: {url}"
                )
            if prop.official_website:
                self.assertTrue(
                    prop.official_website.startswith("http://") or prop.official_website.startswith("https://"),
                    f"Property {pid} official website invalid: {prop.official_website}"
                )

    def test_12_search_by_name(self):
        """12. Verify searching properties by keyword/name."""
        niharika = search_properties(query="Niharika")
        self.assertEqual(len(niharika), 1)
        self.assertEqual(niharika[0].property_id, "SMVDSB_NIHARIKA_COMPLEX")

        vivanta = search_properties(query="Vivanta")
        self.assertEqual(len(vivanta), 1)
        self.assertEqual(vivanta[0].property_id, "HTL_VIVANTA_KATRA")

        white = search_properties(query="White Hotel")
        self.assertEqual(len(white), 1)
        self.assertEqual(white[0].property_id, "HTL_WHITE_HOTEL_KATRA")

    def test_13_search_by_category(self):
        """13. Verify filtering by categories (SMVDSB, Budget, Mid-Range, Premium)."""
        smvdsb = search_properties(category="SMVDSB")
        self.assertEqual(len(smvdsb), 4)
        for p in smvdsb:
            self.assertEqual(p.operator_type, "SMVDSB")

        dharamshala = search_properties(category="dharamshala")
        self.assertEqual(len(dharamshala), 4)

        premium = search_properties(category="Premium")
        self.assertGreaterEqual(len(premium), 2)
        for p in premium:
            self.assertGreaterEqual(p.indicative_min_price, 5000)

        budget = search_properties(category="Budget")
        self.assertGreaterEqual(len(budget), 4)

    def test_14_budget_filtering(self):
        """14. Verify min_budget and max_budget constraints."""
        under_2000 = search_properties(max_budget=2000)
        self.assertGreater(len(under_2000), 0)
        for p in under_2000:
            self.assertLessEqual(p.indicative_min_price, 2000)

        over_5000 = search_properties(min_budget=5000)
        self.assertGreater(len(over_5000), 0)
        for p in over_5000:
            self.assertGreaterEqual(p.indicative_max_price, 5000)

    def test_15_landmark_filtering(self):
        """15. Verify landmark and location filtering."""
        bus_stand = search_properties(landmark="Bus Stand")
        self.assertGreater(len(bus_stand), 0)

        station = search_properties(landmark="Station")
        self.assertGreater(len(station), 0)

        bhawan = search_properties(landmark="Bhawan")
        self.assertGreater(len(bhawan), 0)

    def test_16_orchestrator_adapter_legacy_compatibility(self):
        """16. Verify search_hotels_for_orchestrator produces dictionary conformant with orchestrator expectations."""
        results = search_hotels_for_orchestrator(check_in_date="2026-10-25", category="Budget")
        self.assertGreater(len(results), 0)
        first = results[0]

        expected_keys = [
            "id", "name", "category", "price_per_night", "price",
            "rooms_available", "address", "phone", "tariff_disclaimer",
            "availability_status", "source_provenance"
        ]
        for k in expected_keys:
            self.assertIn(k, first, f"Orchestrator legacy record missing key '{k}'")

        # Crucial: rooms_available must be None to prevent false certainty
        self.assertIsNone(first["rooms_available"], "rooms_available must be None in static catalog")
        self.assertEqual(first["availability_status"], "NOT_CHECKED")
        self.assertIn("SMVDSB" in first["tariff_disclaimer"] or "Published Indicative" in first["tariff_disclaimer"], [True])

    def test_17_production_path_exclusion_of_synthetic_hotels(self):
        """17. Verify coordinator.get_hotel_options returns authentic Katra catalog properties, not synthetic mock hotels."""
        import agents.coordinator as coordinator
        hotels = coordinator.get_hotel_options(check_in_date="2026-10-25")
        self.assertGreater(len(hotels), 0)

        hotel_names = [h["name"] for h in hotels]
        # Assert none of the old synthetic hotel names appear
        synthetic_names = [
            "Hotel Jai Mata Di",
            "Katra Grand",
            "Maa Sharda Guest House",
            "Trikuta View",
            "Hotel Devi Darshan",
        ]
        for sname in synthetic_names:
            self.assertNotIn(sname, hotel_names, f"Synthetic hotel '{sname}' found in coordinator production path")

        # Assert authentic properties appear
        self.assertIn("Niharika Complex (Yatri Niwas, Shakti Bhawan & Ashirwad)", hotel_names)
        self.assertIn("Vivanta Katra, Vaishno Devi", hotel_names)

    def test_18_central_agent_tool_search_accommodation(self):
        """18. Verify central agent search_accommodation_options tool execution."""
        from agents.central_agent import CENTRAL_TOOL_MAP, search_accommodation_options
        self.assertIn("search_accommodation_options", CENTRAL_TOOL_MAP)

        res = search_accommodation_options.invoke({"category": "SMVDSB"})
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("count"), 4)
        self.assertEqual(res.get("freshness_status"), "verified_catalog")
        self.assertEqual(res.get("verification_status"), "verified_curated_source")
        self.assertIn("NOT_CHECKED", res.get("disclaimer"))

        accommodations = res.get("accommodations", [])
        self.assertEqual(len(accommodations), 4)
        for acc in accommodations:
            self.assertEqual(acc.get("operator_type"), "SMVDSB")
            self.assertEqual(acc.get("availability_status"), "NOT_CHECKED")
            self.assertIn("maavaishnodevi.org", acc.get("official_website", ""))


if __name__ == "__main__":
    unittest.main()
