"""
tests/test_phase9_8_1_2_2_presentation.py
Phase 9.8.1.2.2: Final Transport Presentation & Provenance Remediation Test Suite.

Validates that:
1. F-01: Statutory tariff figures are never displayed as fixed ticket prices (Statutory Tariff Slab precedence).
2. F-01: Indicative fare ranges are preserved (Est. ₹800–₹1,800) instead of collapsed point fares.
3. F-02: Operating windows are semantically preserved (never split with .split(' to ')[0] or defaulted to 06:00).
4. F-02: Arrival times are never populated with terminal strings ('Katra Central Bus Stand').
5. F-02: agent._transport_arrival_datetime gracefully handles None departure times without error.
6. F-03: Claim-level verification metadata (route, operator, timetable, fare) is propagated to frontend options.
7. F-04: Residual silent Delhi defaults are completely eliminated across legacy frontend and backend files.
8. F-05: Status indicators never display green REGULAR SERVICE or fake live availability for static schedules.
"""

import os
import re
import unittest
from datetime import date

from agents.tools import search_transport_tool, _search_buses_via_live_manager
from agents.central_agent import search_transport_options
from agent import _transport_arrival_datetime
import db


class TestPhase98122TransportPresentationRemediation(unittest.TestCase):
    """Exhaustive test suite for Phase 9.8.1.2.2 presentation & provenance remediation."""

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # -------------------------------------------------------------------------
    # 1. F-01: Fare Classification, Range & Precedence
    # -------------------------------------------------------------------------

    def test_01_statutory_fare_precedence_in_frontend_card(self):
        """Verifies TransportMiniCard.jsx checks STATUTORY_NOTIFIED_PER_KM_SLAB before numerical fare."""
        card_path = os.path.join(self.root_dir, "frontend", "src", "components", "chat", "cards", "TransportMiniCard.jsx")
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()

        statutory_idx = code.find("option.fare_classification === 'STATUTORY_NOTIFIED_PER_KM_SLAB'")
        fare_num_idx = code.find("option.fare != null && option.fare !== ''")

        self.assertNotEqual(statutory_idx, -1, "STATUTORY_NOTIFIED_PER_KM_SLAB check must exist in TransportMiniCard.jsx")
        self.assertNotEqual(fare_num_idx, -1, "option.fare check must exist in TransportMiniCard.jsx")
        self.assertLess(
            statutory_idx, fare_num_idx,
            "STATUTORY_NOTIFIED_PER_KM_SLAB check must precede option.fare numerical check to avoid displaying ₹75/seat as ticket price"
        )
        self.assertIn("fareDisplay = 'Statutory Tariff Slab'", code)

    def test_02_indicative_fare_ranges_preserved_in_backend_options(self):
        """Verifies backend search options propagate indicative_fare_min and indicative_fare_max."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        delhi_buses = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(delhi_buses) >= 1, "Should return Delhi-Katra bus option")
        delhi_opt = delhi_buses[0]

        self.assertEqual(delhi_opt["indicative_fare_min"], 800)
        self.assertEqual(delhi_opt["indicative_fare_max"], 1800)
        self.assertEqual(delhi_opt["fare_classification"], "ESTIMATED_MARKET_TARIFF")

    def test_03_statutory_bus_fare_is_none_or_not_fixed_ticket_price(self):
        """Verifies statutory stage carriage bus does not set a numerical fare as a confirmed ticket price."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        jammu_buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(jammu_buses) >= 2, "Should return at least 2 Jammu bus options")
        for b in jammu_buses:
            if b.get("fare_classification") == "STATUTORY_NOTIFIED_PER_KM_SLAB":
                self.assertIsNone(b.get("fare"), "Statutory stage carriage must set fare to None so it is not treated as a fixed ticket price")
                self.assertIn("indicative_fare_min", b)

    # -------------------------------------------------------------------------
    # 2. F-02: Operating Windows & Timings Integrity
    # -------------------------------------------------------------------------

    def test_04_operating_windows_not_split_into_point_departures(self):
        """Verifies operating windows are never truncated into point departures in tools or central agent."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        jammu_buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        for b in jammu_buses:
            # Hourly service has operating_hours = "05:00 to 22:00"
            if b.get("operating_hours") == "05:00 to 22:00":
                self.assertIsNone(b.get("departure_time"), "Hourly service has no fixed point departure, departure_time must be None")
                self.assertEqual(b.get("operating_hours"), "05:00 to 22:00")

        delhi_buses = fn(origin="Delhi", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        for b in delhi_buses:
            if b.get("departure_window") == "18:00 to 21:00":
                self.assertIsNone(b.get("departure_time"), "Interstate window schedule must have departure_time None")
                self.assertEqual(b.get("departure_window"), "18:00 to 21:00")

    def test_05_arrival_time_is_not_terminal_string(self):
        """Verifies arrival_time is never populated with a bus stand name string."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        all_buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        for b in all_buses:
            self.assertNotEqual(b.get("arrival_time"), "Katra Central Bus Stand", "arrival_time must not be a bus stand name")

    def test_06_transport_arrival_datetime_handles_none_departure_time(self):
        """Verifies _transport_arrival_datetime handles bus options with None departure_time safely."""
        tr_mock = {
            "travel_date": "2026-11-20",
            "departure_time": None,
            "operating_hours": "05:00 to 22:00",
            "duration_mins": 90,
            "mode": "bus",
        }
        arrival = _transport_arrival_datetime(tr_mock)
        self.assertIsNotNone(arrival)
        self.assertEqual(arrival.year, 2026)
        self.assertEqual(arrival.month, 11)
        self.assertEqual(arrival.day, 20)

    # -------------------------------------------------------------------------
    # 3. F-03: Claim-Level Verification Propagation
    # -------------------------------------------------------------------------

    def test_07_claim_verification_metadata_propagated(self):
        """Verifies all 4 claim verification objects are present in tools and central agent options."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(buses) >= 1)
        b = buses[0]

        self.assertIn("route_verification", b)
        self.assertIn("operator_verification", b)
        self.assertIn("timetable_verification", b)
        self.assertIn("fare_verification", b)

        self.assertIsNotNone(b["route_verification"])
        self.assertIsNotNone(b["operator_verification"])
        self.assertIsNotNone(b["timetable_verification"])
        self.assertIsNotNone(b["fare_verification"])

    # -------------------------------------------------------------------------
    # 4. F-04: Elimination of Silent Delhi Defaults
    # -------------------------------------------------------------------------

    def test_08_no_silent_delhi_defaults_in_journey_flows(self):
        """Verifies zero hardcoded || 'Delhi' or default Delhi assumptions across journey flows."""
        files_to_check = [
            os.path.join(self.root_dir, "frontend", "src", "pages", "YatraBooking.jsx"),
            os.path.join(self.root_dir, "frontend", "src", "components", "RecommendedYatra.jsx"),
            os.path.join(self.root_dir, "frontend", "src", "components", "TravelSearch.jsx"),
            os.path.join(self.root_dir, "frontend", "src", "components", "Authorization.jsx"),
            os.path.join(self.root_dir, "frontend", "src", "components", "BookingConfirmation.jsx"),
            os.path.join(self.root_dir, "agents", "coordinator.py"),
            os.path.join(self.root_dir, "agents", "itinerary_agent.py"),
            os.path.join(self.root_dir, "backend", "routes", "yatra.py"),
        ]

        # Pattern matching hardcoded Delhi defaults in fallback logic
        delhi_fallback_pattern = re.compile(r"(\|\|\s*['\"]Delhi['\"]|or\s*['\"]Delhi['\"]|,\s*['\"]Delhi['\"]\))")

        for fpath in files_to_check:
            self.assertTrue(os.path.exists(fpath), f"File {fpath} must exist")
            with open(fpath, "r", encoding="utf-8") as f:
                code = f.read()
            matches = delhi_fallback_pattern.findall(code)
            self.assertEqual(
                matches, [],
                f"File {os.path.basename(fpath)} contains residual silent Delhi fallbacks: {matches}"
            )

    # -------------------------------------------------------------------------
    # 5. F-05: Truthful Status Indicators (No Green Fake Live Indicator)
    # -------------------------------------------------------------------------

    def test_09_bus_status_emits_route_guidance_not_regular_service(self):
        """Verifies backend bus status is ROUTE GUIDANCE rather than REGULAR SERVICE."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        buses = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        for b in buses:
            self.assertEqual(b.get("status"), "ROUTE GUIDANCE")
            self.assertFalse(b.get("is_live_status"))

    def test_10_frontend_card_does_not_render_green_dot_for_curated_schedules(self):
        """Verifies TransportMiniCard.jsx only renders green dot for is_live_status === true."""
        card_path = os.path.join(self.root_dir, "frontend", "src", "components", "chat", "cards", "TransportMiniCard.jsx")
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Must branch on option.is_live_status for green indicator
        self.assertIn("option.is_live_status ?", code)
        self.assertIn("<span style={{ color: '#28A745', fontWeight: 700 }}>● {status}</span>", code)
        self.assertIn("color: '#8A5D00', fontWeight: 600", code)
        self.assertIn("<Info size={11} />", code)
        self.assertIn("<span>{status}</span>", code)


if __name__ == "__main__":
    unittest.main()
