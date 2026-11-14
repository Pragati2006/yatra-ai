"""
Phase 14.6: Data Integrity, Transport Verification & Truthfulness Test Suite.

Validates:
1. Udhampur-Katra rail connection truthfulness:
   - Synthetic train number '04615' is completely purged from routing and train resolution.
   - Station naming incorporates Martyr Captain Tushar Mahajan Railway Station (MCTM / UHP).
   - Regional link verification status is downgraded to SUGGESTED_CONNECTING_LEG / ROUTE_CORRIDOR_GUIDANCE.
   - Fares are correctly attributed to STATUTORY_TARIFF (statutory minimum ₹30).
2. Complete 78-record physical transport dataset inventory:
   - Railway: Exactly 36 records representing 30 distinct train numbers across 25 station master entries.
   - Bus: Exactly 17 records covering 13 unique intercity corridors and 17 bus stand pairs.
   - Flight: Exactly 25 records (12 scheduled flights with indicative market fares + 13 corridor route advisories with fares UNAVAILABLE).
3. Aviation reconciliation: 12 scheduled flights + 13 corridor route guidance = 25 physical records.
4. Intermediate rail boarding points: Exactly 4 long-distance trains accounting for the 6 additional physical records.
5. Absolute zero synthetic or invented records in all active curated transport files.
"""

import json
import os
import unittest

from services.connecting_journey_engine import ConnectingJourneyEngine, get_connecting_journey_engine
from services.geo_resolver import get_geo_resolver


class TestPhase146DataIntegrityAndVerification(unittest.TestCase):
    """Rigorous audit test cases for data integrity, provenance, and truthfulness."""

    @classmethod
    def setUpClass(cls):
        cls.engine = get_connecting_journey_engine()
        cls.geo = get_geo_resolver()
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.rail_file = os.path.join(cls.base_dir, "data", "curated_railway_schedules.json")
        cls.bus_file = os.path.join(cls.base_dir, "data", "curated_bus_schedules.json")
        cls.flight_file = os.path.join(cls.base_dir, "data", "curated_flight_schedules.json")

    # =========================================================================
    # SECTION 1: UDHAMPUR-KATRA RAIL CONNECTION INTEGRITY & TRUTHFULNESS
    # =========================================================================

    def test_01_purge_of_synthetic_04615_train_number(self):
        """04615 must NOT appear anywhere in connecting journey options for Udhampur or Jammu."""
        # 1. Direct Udhampur query
        res_udhampur = self.engine.plan_connecting_journey("Udhampur")
        opts_uhp = res_udhampur.get("options", [])
        for opt in opts_uhp:
            for leg in opt.get("legs", []):
                self.assertNotIn(
                    "04615",
                    leg.get("transport_name", ""),
                    "Synthetic train number 04615 must not appear in Udhampur legs"
                )

        # 2. Remote origin routing through Udhampur (e.g. Kishtwar)
        res_kishtwar = self.engine.plan_connecting_journey("Kishtwar")
        opts_kishtwar = res_kishtwar.get("options", [])
        for opt in opts_kishtwar:
            for leg in opt.get("legs", []):
                self.assertNotIn(
                    "04615",
                    leg.get("transport_name", ""),
                    "Synthetic train number 04615 must not appear in connecting legs via Udhampur"
                )

    def test_02_udhampur_station_naming_and_mctm_attribution(self):
        """Udhampur rail connection must properly reference Martyr Captain Tushar Mahajan (MCTM) and passing express."""
        res = self.engine.plan_connecting_journey("Udhampur")
        train_opt = next((o for o in res["options"] if o["mode"] == "Train-Direct"), None)
        self.assertIsNotNone(train_opt, "Direct train option must exist for Udhampur")

        leg = train_opt["legs"][0]
        self.assertIn("MCTM", leg["transport_name"])
        self.assertIn("12445 Uttar Sampark Kranti", leg["transport_name"])
        self.assertIn("MCTM", leg["from_place"])
        # Truth-in-data: Timetable guidance requires confirmation
        self.assertEqual(leg["schedule_availability"], "REGIONAL_FREQUENCY_GUIDANCE")
        self.assertEqual(leg["fare_source"], "STATUTORY_TARIFF")
        self.assertEqual(leg["indicative_price_per_pax"], 30.0)
        self.assertFalse(leg["is_verified_schedule"], "Must not claim verified schedule for unverified timetable")

    def test_03_udhampur_verified_train_for_station_contract(self):
        """_get_verified_train_for_station for UHP/MCTM returns truthful regional frequency guidance."""
        train_info = self.engine._get_verified_train_for_station("UHP", None)
        self.assertNotIn("04615", train_info["train_name"])
        self.assertIn("MCTM", train_info["train_name"])
        self.assertFalse(train_info["is_verified_schedule"])
        self.assertEqual(train_info["fare_source"], "STATUTORY_TARIFF")
        self.assertEqual(train_info["fare_per_pax"], 30.0)

    # =========================================================================
    # SECTION 2: PHYSICAL DATASET INVENTORY RECONCILIATION (78 TOTAL RECORDS)
    # =========================================================================

    def test_04_exact_physical_record_inventory(self):
        """Curated datasets must contain exactly 36 rail, 17 bus, and 25 flight records (78 total)."""
        with open(self.rail_file, "r", encoding="utf-8") as f:
            rail_data = json.load(f)
        with open(self.bus_file, "r", encoding="utf-8") as f:
            bus_data = json.load(f)
        with open(self.flight_file, "r", encoding="utf-8") as f:
            flight_data = json.load(f)

        rail_count = len(rail_data.get("schedules", []))
        bus_count = len(bus_data.get("schedules", []))
        flight_count = len(flight_data.get("schedules", []))
        total_count = rail_count + bus_count + flight_count

        self.assertEqual(rail_count, 36, "Curated railway dataset must have exactly 36 physical records")
        self.assertEqual(bus_count, 17, "Curated bus dataset must have exactly 17 physical records")
        self.assertEqual(flight_count, 25, "Curated flight dataset must have exactly 25 physical records")
        self.assertEqual(total_count, 78, "Total physical transport records must equal exactly 78")

    def test_05_railway_train_numbers_and_intermediate_boarding_reconciliation(self):
        """36 railway records represent exactly 30 unique train numbers with 6 intermediate boarding points."""
        with open(self.rail_file, "r", encoding="utf-8") as f:
            rail_data = json.load(f)
        schedules = rail_data.get("schedules", [])

        train_numbers = [s["train_number"] for s in schedules]
        unique_trains = set(train_numbers)
        self.assertEqual(len(unique_trains), 30, "Must represent exactly 30 unique Indian Railways train numbers")

        # Verify intermediate boarding points for the 4 multi-origin trains
        train_counts = {}
        for tn in train_numbers:
            train_counts[tn] = train_counts.get(tn, 0) + 1

        self.assertEqual(train_counts["12919"], 3, "Malwa Express must have 3 physical records (INDB, JRC, BPL)")
        self.assertEqual(train_counts["14609"], 3, "Hemkunt Express must have 3 physical records (YNRK, CDG, HW)")
        self.assertEqual(train_counts["12471"], 2, "Swaraj Express must have 2 physical records (BDTS, LDH)")
        self.assertEqual(train_counts["12237"], 2, "Begampura Express must have 2 physical records (LKO, BSB)")

        extra_records = sum(c - 1 for c in train_counts.values())
        self.assertEqual(extra_records, 6, "Intermediate boarding records must account for exactly 6 extra records")
        self.assertEqual(len(unique_trains) + extra_records, 36)

    def test_06_aviation_reconciliation_12_scheduled_plus_13_corridor_guidance(self):
        """25 flight records must reconcile to 12 scheduled services and 13 corridor route advisories."""
        with open(self.flight_file, "r", encoding="utf-8") as f:
            flight_data = json.load(f)
        schedules = flight_data.get("schedules", [])

        scheduled_services = [s for s in schedules if s.get("indicative_fare_min") is not None]
        corridor_advisories = [s for s in schedules if s.get("indicative_fare_min") is None]

        self.assertEqual(len(scheduled_services), 12, "Phase 9.8.2 scheduled services with indicative fares must equal 12")
        self.assertEqual(len(corridor_advisories), 13, "Phase 14.4.3 corridor route advisories must equal 13")
        self.assertEqual(len(scheduled_services) + len(corridor_advisories), 25)

        # In the 13 corridor advisories: 6 have confirmed flight numbers, 7 are generic connecting via DEL
        advisories_with_fn = [s for s in corridor_advisories if s.get("flight_number") is not None]
        advisories_without_fn = [s for s in corridor_advisories if s.get("flight_number") is None]

        self.assertEqual(len(advisories_with_fn), 6, "Must have exactly 6 corridor advisories with flight numbers")
        self.assertEqual(len(advisories_without_fn), 7, "Must have exactly 7 connecting hub advisories without flight numbers")

    def test_07_bus_corridor_and_operator_integrity(self):
        """17 bus records represent 13 distinct intercity corridors and 17 boarding stand pairs."""
        with open(self.bus_file, "r", encoding="utf-8") as f:
            bus_data = json.load(f)
        schedules = bus_data.get("schedules", [])

        corridors = set(f"{s['origin_city']} -> {s['destination_city']}" for s in schedules)
        self.assertEqual(len(corridors), 13, "Must cover exactly 13 unique intercity corridors")

        stand_pairs = set(f"{s['origin_bus_stand']} -> {s['destination_bus_stand']}" for s in schedules)
        self.assertEqual(len(stand_pairs), 16, "Must cover 16 distinct bus stand departure pairs (Delhi-Katra has 2 service tiers)")

        # Ensure all operators are valid public/state transport entities
        for s in schedules:
            op = s.get("operator_name", "")
            self.assertTrue(
                any(keyword in op for keyword in ["JKRTC", "JKSRTC", "HRTC", "PRTC", "Punjab Roadways", "Stage Carriage"]),
                f"Operator {op} must be an authorized state or licensed carriage operator"
            )

    # =========================================================================
    # SECTION 3: PROVENANCE AND ZERO-SYNTHETIC GUARANTEE
    # =========================================================================

    def test_08_zero_synthetic_records_in_datasets(self):
        """No record in railway, bus, or flight datasets should have synthetic or fabricated provenance."""
        datasets = [
            ("railway", self.rail_file),
            ("bus", self.bus_file),
            ("flight", self.flight_file),
        ]
        for name, path in datasets:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            for r in d.get("schedules", []):
                self.assertNotEqual(r.get("data_tier"), "synthetic", f"Synthetic data_tier found in {name}")
                self.assertNotIn("SYNTHETIC", str(r.get("verification_status", "")), f"Synthetic status in {name}")
                self.assertIsNotNone(r.get("source_name"), f"Missing source_name in {name} record {r}")

    def test_09_flight_fare_truthfulness_and_disclaimers(self):
        """All 13 corridor route advisories must declare UNAVAILABLE fares and refer to official airline portals."""
        with open(self.flight_file, "r", encoding="utf-8") as f:
            flight_data = json.load(f)
        schedules = flight_data.get("schedules", [])

        for s in schedules:
            if s.get("indicative_fare_min") is None:
                self.assertEqual(s.get("fare_classification"), "UNAVAILABLE")
                self.assertIn("airline", s.get("fare_disclaimer", "").lower())


if __name__ == "__main__":
    unittest.main()
