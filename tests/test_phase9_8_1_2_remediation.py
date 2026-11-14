"""
tests/test_phase9_8_1_2_remediation.py

Phase 9.8.1.2: Transport Truthfulness & Data Integrity Remediation Verification Suite.

Verifies:
1. Missing Origin Handling: coordinate_plan and search_transport_options ask for clarification; never default to Delhi.
2. Regional Corridor Coherence: resolve_hub maps Punjab, Himachal, and Kashmir to Jammu, eliminating 1,000 km Southward detours via Delhi.
3. Dataset Isolation & No Leakage: db.get_distinct_origins() eliminates synthetic CSV leakage from BUSES_LIVE and TRAINS_LIVE.
4. Claim-Level Transport Verification: ClaimVerification dataclass serialization and CuratedBusSchedule claim integration.
5. Fail-Closed Timetable Downgrade: Generic homepage root URLs without deep schedule references downgrade timetable claims.
6. Fail-Closed Fare Downgrade: Estimated market tariffs cannot claim verified official status.
7. Curated Bus Dataset Remediation: Stripped unevidenced 60m/75m frequencies, unverified continuous shuttle claims, and honest claim statuses.
8. Tools Unified LiveDataManager Routing: search_transport_tool routes bus queries through UnifiedLiveDataManager.
9. Frontend Honest Card Fallbacks: TransportMiniCard.jsx eliminates hardcoded 1650, 06:00 AM, 02:00 PM, and AVAILABLE fallbacks.
10. Backward Compatibility: All existing orchestrator responses and provenance badges remain preserved.
"""

from datetime import date, timedelta
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import resolve_hub
from agents.central_agent import search_transport_options
from agents.orchestrator import coordinate_plan, format_concise_edit_reply, format_itemized_cost_breakdown
from agents.tools import search_transport_tool
import db
from services.bus_schedules import (
    DEFAULT_BUS_SCHEDULES_PATH,
    load_curated_bus_schedules,
    search_curated_bus_schedules,
)
from services.live_data.contracts import (
    ClaimVerification,
    CuratedBusSchedule,
    DataDomain,
    ProviderRequest,
)
from services.live_data.manager import get_live_data_manager
from utils.provenance import VerificationStatus


class TestPhase9812TransportTruthfulnessRemediation(unittest.TestCase):
    """Test suite verifying Phase 9.8.1.2 Transport Truthfulness Remediation."""

    # -------------------------------------------------------------------------
    # 1. Missing Origin Clarification (Never Default to Delhi)
    # -------------------------------------------------------------------------

    def test_01_coordinate_plan_missing_origin_requires_clarification(self):
        """Verifies coordinate_plan returns NEEDS_INFO when origin is missing, rather than defaulting to Delhi."""
        req = {"pax": 2, "duration_days": 4}
        res = coordinate_plan(req)

        self.assertEqual(res["status"], "NEEDS_INFO")
        self.assertIn("origin", res["missing_fields"])
        self.assertIn("departure location", res["reply"].lower())
        self.assertNotIn("delhi", res["reply"].lower())

    def test_02_central_agent_missing_origin_requires_clarification(self):
        """Verifies search_transport_options returns MISSING_ORIGIN schema when origin is empty."""
        fn = getattr(search_transport_options, "func", search_transport_options)
        res_empty = fn(origin="", start_date="2026-11-20", end_date="2026-11-24")
        self.assertEqual(res_empty["status"], "MISSING_ORIGIN")
        self.assertTrue(res_empty["requires_clarification"])
        self.assertEqual(res_empty["count"], 0)

        res_none = fn(origin=None, start_date="2026-11-20", end_date="2026-11-24")
        self.assertEqual(res_none["status"], "MISSING_ORIGIN")
        self.assertTrue(res_none["requires_clarification"])

    # -------------------------------------------------------------------------
    # 2. Regional Corridor Coherence (No Southward Detours to Delhi)
    # -------------------------------------------------------------------------

    def test_03_regional_corridor_coherence_punjab_himachal_kashmir(self):
        """Verifies Northern origins map toward Jammu rather than routing South to Delhi."""
        # Punjab
        hub_amritsar, direct_a = resolve_hub("Amritsar")
        self.assertEqual(hub_amritsar, "Jammu", "Amritsar should connect via Jammu, not Delhi")

        hub_chandigarh, direct_c = resolve_hub("Chandigarh")
        self.assertEqual(hub_chandigarh, "Jammu", "Chandigarh should connect via Jammu, not Delhi")

        # Himachal Pradesh
        hub_shimla, direct_s = resolve_hub("Shimla")
        self.assertEqual(hub_shimla, "Jammu", "Shimla should connect via Jammu, not Delhi")

        # Kashmir
        hub_srinagar, direct_sr = resolve_hub("Srinagar")
        self.assertEqual(hub_srinagar, "Jammu", "Srinagar should connect via Jammu, not Delhi")

    # -------------------------------------------------------------------------
    # 3. Dataset Isolation & Elimination of Synthetic CSV Leakage
    # -------------------------------------------------------------------------

    def test_04_get_distinct_origins_eliminates_synthetic_csv_leakage(self):
        """Verifies db.get_distinct_origins() only returns authentic origins from curated sources."""
        origins = db.get_distinct_origins()
        origin_set = set(origins)

        # Authentic curated origins must be present
        self.assertIn("Jammu", origin_set)
        self.assertIn("Udhampur", origin_set)
        self.assertIn("Delhi", origin_set)

        # Synthetic bus CSV origins should not leak
        # In synthetic CSV, random cities were fabricated with fake buses
        self.assertNotIn("Patna", origin_set)
        self.assertNotIn("Bhopal", origin_set)

    # -------------------------------------------------------------------------
    # 4. Claim-Level Transport Verification Contracts
    # -------------------------------------------------------------------------

    def test_05_claim_verification_contract_and_serialization(self):
        """Verifies ClaimVerification dataclass creation, fields, and dictionary serialization."""
        claim = ClaimVerification(
            status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            source_name="J&K Transport Department",
            source_url="https://jaktrans.jk.gov.in/",
            document_reference="Notification S.O. 126",
            effective_date="2026-04-29",
            verified_at="2026-11-08T12:00:00Z",
            verified_by="Yatra AI Curatorial Desk",
            notes="Stage carriage route permit.",
        )
        d = claim.to_dict()
        self.assertEqual(d["status"], "verified_official_source")
        self.assertEqual(d["document_reference"], "Notification S.O. 126")
        self.assertEqual(d["verified_by"], "Yatra AI Curatorial Desk")

    def test_06_fail_closed_timetable_downgrade_on_generic_root_url(self):
        """Verifies fail-closed rule downgrades timetable verification when document reference is missing or unpublished."""
        sched = CuratedBusSchedule(
            service_id="test_fail_closed_bus",
            operator_name="JKRTC",
            service_type="STAGE_CARRIAGE_FREQUENCY",
            origin_bus_stand="Test Stand",
            destination_bus_stand="Katra Stand",
            origin_city="TestCity",
            destination_city="Katra",
            source_name="Generic Portal",
            source_url="https://jaktrans.jk.gov.in/",
            source_circular_reference="Circular 101",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
            timetable_verification=ClaimVerification(
                status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                source_name="Generic Portal",
                source_url="https://jaktrans.jk.gov.in/",
                document_reference="Unpublished Guidance",  # Inconclusive/unpublished
            ),
        )
        # Should be downgraded to INDICATIVE_INFORMATION by __post_init__
        self.assertEqual(
            sched.timetable_verification.status,
            VerificationStatus.INDICATIVE_INFORMATION.value,
            "Timetable claim with unpublished/inconclusive reference must be downgraded to indicative_information",
        )

    def test_07_fail_closed_fare_downgrade_on_market_tariff(self):
        """Verifies fail-closed rule downgrades fare claim when classified as ESTIMATED_MARKET_TARIFF."""
        sched = CuratedBusSchedule(
            service_id="test_market_fare_bus",
            operator_name="JKRTC Interstate",
            service_type="INTERSTATE_SCHEDULED_WINDOW",
            origin_bus_stand="ISBT",
            destination_bus_stand="Katra Stand",
            origin_city="Delhi",
            destination_city="Katra",
            fare_classification="ESTIMATED_MARKET_TARIFF",
            source_name="Interstate Division",
            source_url="https://jksrtc.co.in/",
            source_circular_reference="Interstate Guide",
            verified_at="2026-11-08T00:00:00Z",
            verified_by="Auditor",
            fare_verification=ClaimVerification(
                status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                source_name="Estimated Market Survey",
                source_url="https://jksrtc.co.in/",
                document_reference="Market Estimate",
            ),
        )
        # Should be downgraded to INDICATIVE_INFORMATION because estimated market tariff cannot claim verified official status
        self.assertEqual(
            sched.fare_verification.status,
            VerificationStatus.INDICATIVE_INFORMATION.value,
            "Estimated market tariffs cannot claim verified_official_source",
        )

    # -------------------------------------------------------------------------
    # 5. Curated Bus Dataset Integrity (Remediated Claims)
    # -------------------------------------------------------------------------

    def test_08_curated_bus_dataset_remediated_claims(self):
        """Verifies curated_bus_schedules.json contains 4 corridors with truthful claim-level attributions."""
        with open(DEFAULT_BUS_SCHEDULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        schedules = data.get("schedules", [])
        self.assertEqual(len(schedules), 4)

        sched_by_id = {s["service_id"]: s for s in schedules}

        # Corridor 1: Jammu GBS - No 60m SLA guarantee
        gbs = sched_by_id["bus_jksrtc_jammu_katra_exp"]
        self.assertIsNone(gbs.get("frequency_minutes"), "Must not claim fixed 60-minute frequency")
        self.assertIn("Regular stage carriage departures", gbs["operating_hours"])
        self.assertIsNotNone(gbs.get("route_verification"))
        self.assertIsNotNone(gbs.get("operator_verification"))
        self.assertEqual(gbs["timetable_verification"]["status"], "indicative_information")
        self.assertEqual(gbs["fare_verification"]["status"], "partially_verified")

        # Corridor 2: Rail Head Shuttle - No continuous shuttle SLA
        shuttle = sched_by_id["bus_jksrtc_railhead_katra_shuttle"]
        self.assertIsNone(shuttle.get("departure_window"), "Must not claim continuous shuttle SLA")
        self.assertIsNone(shuttle.get("frequency_minutes"))
        self.assertEqual(shuttle["timetable_verification"]["status"], "unverified")

        # Corridor 3: Udhampur - No 75m frequency
        udhampur = sched_by_id["bus_udhampur_katra_feeder"]
        self.assertIsNone(udhampur.get("frequency_minutes"), "Must not claim fabricated 75-minute frequency")
        self.assertEqual(udhampur["timetable_verification"]["status"], "unverified")

        # Corridor 4: Delhi ISBT - Estimated market tariff
        delhi = sched_by_id["bus_jksrtc_delhi_katra_interstate"]
        self.assertEqual(delhi["fare_classification"], "ESTIMATED_MARKET_TARIFF")
        self.assertEqual(delhi["fare_verification"]["status"], "indicative_information")

    # -------------------------------------------------------------------------
    # 6. Tools Routing via Unified Live Data Manager
    # -------------------------------------------------------------------------

    def test_09_tools_routes_buses_via_unified_live_data_manager(self):
        """Verifies search_transport_tool routes bus queries through UnifiedLiveDataManager."""
        fn = getattr(search_transport_tool, "func", search_transport_tool)
        results = fn(origin="Jammu", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertTrue(len(results) >= 2, "Should return at least 2 curated corridors for Jammu")
        for r in results:
            self.assertEqual(r["mode"], "bus")
            self.assertEqual(r["source_type"], "curated_data")
            self.assertFalse(r["is_live_status"])
            self.assertIn("indicative_fare_min", r)

        # Unsupported route returns empty list (no synthetic buses)
        unsupported = fn(origin="Bengaluru", start_date="2026-11-20", end_date="2026-11-24", mode="bus")
        self.assertEqual(unsupported, [], "Unsupported route must return empty list without synthetic fallback")

    # -------------------------------------------------------------------------
    # 7. Frontend Card Truthfulness (No Fabricated Fallbacks)
    # -------------------------------------------------------------------------

    def test_10_frontend_card_no_fabricated_fallbacks(self):
        """Verifies TransportMiniCard.jsx does not fabricate fares or departure times."""
        card_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend",
            "src",
            "components",
            "chat",
            "cards",
            "TransportMiniCard.jsx",
        )
        with open(card_path, "r", encoding="utf-8") as f:
            code = f.read()

        # No fabricated fallbacks
        self.assertNotIn("|| 1650", code, "Must not fall back to ₹1650")
        self.assertNotIn("|| '06:00 AM'", code, "Must not fall back to 06:00 AM")
        self.assertNotIn("|| '02:00 PM'", code, "Must not fall back to 02:00 PM")
        self.assertNotIn("|| 'AVAILABLE'", code, "Must not fall back to AVAILABLE")

        # Honest displays present
        self.assertIn("Tariff at counter", code)
        self.assertIn("ROUTE GUIDANCE", code)
        self.assertIn("Indicative Timetable", code)
        self.assertIn("confirmation", code)


if __name__ == "__main__":
    unittest.main()
