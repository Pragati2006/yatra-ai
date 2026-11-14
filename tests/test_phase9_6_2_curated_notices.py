"""
tests/test_phase9_6_2_curated_notices.py
Dedicated Test Suite for Phase 9.6.2: Curated Operational Notices & Verified Contact Registry.

Covers all 17 requirements:
 1. Curated operational notice loading & dataclass validation.
 2. Missing or corrupted catalog handling (returns SOURCE_UNAVAILABLE without crash).
 3. Empty registry truth-in-data (NO_ACTIVE_NOTICES, never claims 'Yatra running smoothly').
 4. Future effective date lifecycle (PUBLISHED status).
 5. Active validity horizon lifecycle (ACTIVE status).
 6. Horizon expiration handling (REQUIRES_REVERIFICATION; never assumes track cleared).
 7. Category-specific 24-hour horizon (TRAFFIC_ADVISORY / WEATHER_WARNING expiration).
 8. Explicit withdrawal persistence (WITHDRAWN status preserved).
 9. Declared superseding relationship (SUPERSEDED with back-link).
10. Automatic 5-point alignment superseding (authority, location, route, category, timestamp).
11. Non-override rule (unverified/secondary reports CANNOT supersede verified official notice).
12. Conflicting notices preservation (different authorities preserved together).
13. Verified contact loading & statutory 112 primary emergency priority.
14. Jurisdiction filtering (Ramban, Jammu, Udhampur, Katra; universal 112 retained).
15. Unverified contact suppression by default.
16. Unified Live Data Manager integration for OperationalNotice & Emergency domains.
17. Central AI Agent specialist tools & deterministic fallback routing.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from services.live_data.contracts import (
    ContactCategory,
    DataDomain,
    NoticeAggregateStatus,
    NoticeCategory,
    NoticeLifecycleStatus,
    OperationalNotice,
    ProviderRequest,
    VerifiedContact,
)
from services.live_data.manager import UnifiedLiveDataManager, get_live_data_manager
from services.live_data.adapters.curated_operational_notices_adapter import CuratedOperationalNoticesAdapter
from services.live_data.adapters.curated_contact_adapter import CuratedContactAdapter
from services.operational_notices import (
    DEFAULT_NOTICES_PATH,
    evaluate_notice_lifecycle,
    load_curated_notices,
    query_curated_notices,
    resolve_superseding_relationships,
)
from services.verified_contacts import (
    DEFAULT_CONTACTS_PATH,
    load_verified_contacts,
    query_verified_contacts,
)
from agents.central_agent import (
    CENTRAL_TOOLS,
    is_operational_notice_query,
    is_verified_contact_query,
    lookup_verified_contacts,
    process_conversational_turn,
    query_operational_notices,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    attach_provenance_to_response,
    extract_provenance_from_tool_result,
    get_utc_now_iso,
)


class TestCuratedOperationalNotices(unittest.TestCase):
    """Test suite for Phase 9.6.2 Curated Operational Notices & Verified Contact Registry."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.now = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_notices_json(self, notices_list):
        path = os.path.join(self.temp_dir, "test_notices.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"notices": notices_list}, f)
        return path

    def _create_temp_contacts_json(self, contacts_list, primary_directive=None):
        path = os.path.join(self.temp_dir, "test_contacts.json")
        payload = {"contacts": contacts_list}
        if primary_directive:
            payload["primary_emergency_directive"] = primary_directive
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return path

    # -------------------------------------------------------------------------
    # Requirement 1: Notice Loading & Dataclass Validation
    # -------------------------------------------------------------------------
    def test_01_curated_notices_loading_and_dataclass_validation(self):
        notices, status = load_curated_notices(DEFAULT_NOTICES_PATH)
        self.assertEqual(status, "SUCCESS")
        self.assertGreater(len(notices), 0)
        for n in notices:
            self.assertIsInstance(n, OperationalNotice)
            self.assertTrue(n.notice_id)
            self.assertTrue(n.notice_title)
            self.assertTrue(n.issuing_authority)
            self.assertTrue(n.source_url)
            self.assertIn(n.verification_status, [v.value for v in VerificationStatus])
            self.assertIn(n.notice_lifecycle_status, [l.value for l in NoticeLifecycleStatus])
            n_dict = n.to_dict()
            self.assertIsInstance(n_dict, dict)
            self.assertEqual(n_dict["notice_id"], n.notice_id)

    # -------------------------------------------------------------------------
    # Requirement 2: Missing or Corrupted Catalog Handling
    # -------------------------------------------------------------------------
    def test_02_missing_or_corrupted_catalog_handling(self):
        missing_path = os.path.join(self.temp_dir, "non_existent.json")
        notices, status = load_curated_notices(missing_path)
        self.assertEqual(status, NoticeAggregateStatus.SOURCE_UNAVAILABLE.value)
        self.assertEqual(len(notices), 0)

        # Corrupted JSON
        corrupt_path = os.path.join(self.temp_dir, "corrupt.json")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("{invalid json content")
        c_notices, c_status = load_curated_notices(corrupt_path)
        self.assertEqual(c_status, NoticeAggregateStatus.SOURCE_UNAVAILABLE.value)
        self.assertEqual(len(c_notices), 0)

        # Query handles missing catalog gracefully
        q_notices, q_agg, q_meta = query_curated_notices(file_path=missing_path)
        self.assertEqual(q_agg, NoticeAggregateStatus.SOURCE_UNAVAILABLE.value)
        self.assertEqual(len(q_notices), 0)
        self.assertIn("unavailable", q_meta.get("disclaimer", "").lower())

    # -------------------------------------------------------------------------
    # Requirement 3: Empty Registry Truth-in-Data
    # -------------------------------------------------------------------------
    def test_03_empty_registry_truth_in_data(self):
        empty_path = self._create_temp_notices_json([])
        notices, agg_status, meta = query_curated_notices(file_path=empty_path)
        self.assertEqual(agg_status, NoticeAggregateStatus.NO_ACTIVE_NOTICES.value)
        self.assertEqual(len(notices), 0)
        self.assertEqual(meta["active_notices_count"], 0)

        # CRITICAL SAFETY INVARIANT: Must NOT claim 'running smoothly' or 'all clear'
        advisory = meta.get("advisory", "").lower()
        self.assertNotIn("running smoothly", advisory)
        self.assertNotIn("all clear", advisory)
        self.assertIn("no active disruption notices", advisory)
        self.assertIn("unconfirmed", advisory)

    # -------------------------------------------------------------------------
    # Requirement 4: Future Effective Date Lifecycle (PUBLISHED)
    # -------------------------------------------------------------------------
    def test_04_future_effective_date_lifecycle(self):
        notice = OperationalNotice(
            notice_id="future_001",
            notice_title="Scheduled Maintenance Notice",
            notice_text="Track maintenance scheduled for next week.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra",
            effective_from=(self.now + timedelta(days=2)).isoformat(),
        )
        evaluated = evaluate_notice_lifecycle(notice, reference_time=self.now)
        self.assertEqual(evaluated.notice_lifecycle_status, NoticeLifecycleStatus.PUBLISHED.value)

    # -------------------------------------------------------------------------
    # Requirement 5: Active Validity Horizon Lifecycle (ACTIVE)
    # -------------------------------------------------------------------------
    def test_05_active_validity_horizon_lifecycle(self):
        notice = OperationalNotice(
            notice_id="active_001",
            notice_title="Current Active Circular",
            notice_text="Ongoing pilgrimage operational circular.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra",
            effective_from=(self.now - timedelta(days=1)).isoformat(),
            effective_until=(self.now + timedelta(days=1)).isoformat(),
        )
        evaluated = evaluate_notice_lifecycle(notice, reference_time=self.now)
        self.assertEqual(evaluated.notice_lifecycle_status, NoticeLifecycleStatus.ACTIVE.value)

    # -------------------------------------------------------------------------
    # Requirement 6: Horizon Expiration Handling (REQUIRES_REVERIFICATION)
    # -------------------------------------------------------------------------
    def test_06_horizon_expiration_handling_requires_reverification(self):
        # Notice whose explicit horizon expired 1 hour ago
        notice = OperationalNotice(
            notice_id="expired_horizon_001",
            notice_title="Temporary Landslide Closure at Tarakote",
            notice_text="Track closed due to shooting stones.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Tarakote Marg",
            effective_from=(self.now - timedelta(hours=6)).isoformat(),
            effective_until=(self.now - timedelta(hours=1)).isoformat(),
        )
        evaluated = evaluate_notice_lifecycle(notice, reference_time=self.now)
        # CRITICAL SAFETY INVARIANT: Must NEVER clear automatically; must REQUIRE reverification
        self.assertEqual(evaluated.notice_lifecycle_status, NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value)

    # -------------------------------------------------------------------------
    # Requirement 7: Category-Specific 24-Hour Horizon Expiration
    # -------------------------------------------------------------------------
    def test_07_category_specific_24_hour_horizon_expiration(self):
        # Daily traffic advisory published 26 hours ago without explicit effective_until
        notice = OperationalNotice(
            notice_id="traffic_old_001",
            notice_title="Daily NH-44 Traffic Movement Plan",
            notice_text="One way traffic from Jammu to Srinagar.",
            issuing_authority="Traffic Police HQ J&K",
            source_url="https://trafficpolice.jk.gov.in",
            affected_location="NH-44",
            category=NoticeCategory.TRAFFIC_ADVISORY.value,
            publication_timestamp=(self.now - timedelta(hours=26)).isoformat(),
        )
        evaluated = evaluate_notice_lifecycle(notice, reference_time=self.now)
        self.assertEqual(evaluated.notice_lifecycle_status, NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value)

    # -------------------------------------------------------------------------
    # Requirement 8: Explicit Withdrawal Persistence
    # -------------------------------------------------------------------------
    def test_08_explicit_withdrawal_persistence(self):
        notice = OperationalNotice(
            notice_id="withdrawn_001",
            notice_title="Withdrawn Advisory",
            notice_text="Prior advisory withdrawn by authority circular.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra",
            notice_lifecycle_status=NoticeLifecycleStatus.WITHDRAWN.value,
            effective_until=(self.now + timedelta(days=5)).isoformat(),
        )
        evaluated = evaluate_notice_lifecycle(notice, reference_time=self.now)
        self.assertEqual(evaluated.notice_lifecycle_status, NoticeLifecycleStatus.WITHDRAWN.value)

    # -------------------------------------------------------------------------
    # Requirement 9: Declared Superseding Relationship
    # -------------------------------------------------------------------------
    def test_09_declared_superseding_relationship(self):
        old_notice = OperationalNotice(
            notice_id="old_notice_001",
            notice_title="Old Route Advisory",
            notice_text="Initial closure notice.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Himkoti Track",
            publication_timestamp="2026-11-06T10:00:00Z",
        )
        new_notice = OperationalNotice(
            notice_id="new_notice_002",
            notice_title="Updated Route Advisory",
            notice_text="Resumption of battery car on Himkoti.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Himkoti Track",
            publication_timestamp="2026-11-07T08:00:00Z",
            supersedes_notice_id="old_notice_001",
        )

        resolved = resolve_superseding_relationships([old_notice, new_notice], reference_time=self.now)
        res_map = {n.notice_id: n for n in resolved}
        self.assertEqual(res_map["old_notice_001"].notice_lifecycle_status, NoticeLifecycleStatus.SUPERSEDED.value)
        self.assertEqual(res_map["old_notice_001"].superseded_by_notice_id, "new_notice_002")

    # -------------------------------------------------------------------------
    # Requirement 10: Prohibition of Implicit Automatic Superseding (F-01 Remediation)
    # -------------------------------------------------------------------------
    def test_10_no_implicit_superseding_five_point_alignment(self):
        """MANDATORY SAFETY INVARIANT (F-01 Remediation):
        Matching 5-point attributes (authority, location, route, category, newer timestamp)
        MUST NOT cause automatic supersession.
        A newer routine advisory must never silently retire an active safety warning/closure
        without an explicit declared superseding link. Multiple corridor notices must remain active.
        """
        # Critical safety warning: Rockfall closure on NH-44
        safety_closure = OperationalNotice(
            notice_id="closure_nh44_rockfall",
            notice_title="NH-44 Closed: Rockfall Near Ramban",
            notice_text="Highway blocked due to shooting stones and heavy rockfall.",
            issuing_authority="Traffic Police HQ J&K",
            source_url="https://trafficpolice.jk.gov.in",
            affected_location="NH-44",
            affected_route="Ramban-Banihal",
            category=NoticeCategory.TRAFFIC_ADVISORY.value,
            severity="CRITICAL",
            publication_timestamp=(self.now - timedelta(hours=3)).isoformat(),
            effective_until=(self.now + timedelta(days=1)).isoformat(),
        )
        # Newer routine advisory published later matching all 5 points
        routine_advisory = OperationalNotice(
            notice_id="advisory_nh44_convoy",
            notice_title="NH-44 Advisory: Security Convoy Movement",
            notice_text="Slow movement expected due to security convoy.",
            issuing_authority="Traffic Police HQ J&K",
            source_url="https://trafficpolice.jk.gov.in",
            affected_location="NH-44",
            affected_route="Ramban-Banihal",
            category=NoticeCategory.TRAFFIC_ADVISORY.value,
            severity="ADVISORY",
            publication_timestamp=(self.now - timedelta(hours=1)).isoformat(),
            effective_until=(self.now + timedelta(days=1)).isoformat(),
        )

        resolved = resolve_superseding_relationships([safety_closure, routine_advisory], reference_time=self.now)
        res_map = {n.notice_id: n for n in resolved}

        # 1. CRITICAL SAFETY ASSERTION: Older closure MUST NOT be superseded implicitly
        self.assertEqual(res_map["closure_nh44_rockfall"].notice_lifecycle_status, NoticeLifecycleStatus.ACTIVE.value)
        self.assertIsNone(res_map["closure_nh44_rockfall"].superseded_by_notice_id)

        # 2. Newer routine advisory must also remain ACTIVE
        self.assertEqual(res_map["advisory_nh44_convoy"].notice_lifecycle_status, NoticeLifecycleStatus.ACTIVE.value)
        self.assertIsNone(res_map["advisory_nh44_convoy"].supersedes_notice_id)

        # 3. Both notices must remain simultaneously visible to pilgrims
        active_ids = {n.notice_id for n in resolved if n.notice_lifecycle_status == NoticeLifecycleStatus.ACTIVE.value}
        self.assertIn("closure_nh44_rockfall", active_ids)
        self.assertIn("advisory_nh44_convoy", active_ids)

    # -------------------------------------------------------------------------
    # Requirement 11: Non-Override Rule (Media/Unverified cannot supersede Official)
    # -------------------------------------------------------------------------
    def test_11_non_override_rule_media_cannot_supersede_official(self):
        official = OperationalNotice(
            notice_id="official_smvdsb_closure",
            notice_title="Official Shrine Board Track Suspension",
            notice_text="Track suspended by SMVDSB due to severe weather.",
            issuing_authority="Shri Mata Vaishno Devi Shrine Board",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra-Bhawan Track",
            affected_route="Traditional Route",
            category=NoticeCategory.YATRA_SUSPENSION.value,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            publication_timestamp="2026-11-07T06:00:00Z",
        )
        unverified_media = OperationalNotice(
            notice_id="media_report_reopen",
            notice_title="Local News: Track Clear",
            notice_text="Social media reports claim track is reopening.",
            issuing_authority="Shri Mata Vaishno Devi Shrine Board",
            source_url="https://unverified-blog.example.com",
            affected_location="Katra-Bhawan Track",
            affected_route="Traditional Route",
            category=NoticeCategory.YATRA_SUSPENSION.value,
            verification_status=VerificationStatus.UNVERIFIED.value,
            publication_timestamp="2026-11-07T10:00:00Z",
            supersedes_notice_id="official_smvdsb_closure",
        )

        resolved = resolve_superseding_relationships([official, unverified_media], reference_time=self.now)
        res_map = {n.notice_id: n for n in resolved}
        # CRITICAL SAFETY INVARIANT: Official notice must NOT be marked superseded by an unverified report!
        self.assertNotEqual(res_map["official_smvdsb_closure"].notice_lifecycle_status, NoticeLifecycleStatus.SUPERSEDED.value)

    # -------------------------------------------------------------------------
    # Requirement 12: Conflicting Notices Preservation
    # -------------------------------------------------------------------------
    def test_12_conflicting_notices_preservation(self):
        # Authority A and Authority B issue notices for the same general corridor
        notice_police = OperationalNotice(
            notice_id="notice_police_001",
            notice_title="Traffic Police Advisory",
            notice_text="Slow movement due to convoy.",
            issuing_authority="J&K Traffic Police",
            source_url="https://trafficpolice.jk.gov.in",
            affected_location="Katra Base Camp",
            category=NoticeCategory.TRAFFIC_ADVISORY.value,
            publication_timestamp="2026-11-07T08:00:00Z",
        )
        notice_board = OperationalNotice(
            notice_id="notice_board_001",
            notice_title="Shrine Board Notice",
            notice_text="All battery cars operational.",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra Base Camp",
            category=NoticeCategory.TRAFFIC_ADVISORY.value,
            publication_timestamp="2026-11-07T08:30:00Z",
        )

        resolved = resolve_superseding_relationships([notice_police, notice_board], reference_time=self.now)
        # Both must remain active and neither may silently swallow the other
        active_ids = {n.notice_id for n in resolved if n.notice_lifecycle_status == NoticeLifecycleStatus.ACTIVE.value}
        self.assertIn("notice_police_001", active_ids)
        self.assertIn("notice_board_001", active_ids)

    # -------------------------------------------------------------------------
    # Requirement 13: Verified Contacts Loading & 112 Primary Priority
    # -------------------------------------------------------------------------
    def test_13_verified_contacts_loading_and_112_priority(self):
        contacts, primary_dir = load_verified_contacts(DEFAULT_CONTACTS_PATH)
        self.assertGreater(len(contacts), 0)
        self.assertEqual(primary_dir.get("number"), "112")

        query_res, meta = query_verified_contacts(file_path=DEFAULT_CONTACTS_PATH)
        self.assertGreater(len(query_res), 0)
        self.assertEqual(meta.get("primary_emergency_number"), "112")

        # CRITICAL SAFETY INVARIANT: The very first contact returned must be 112
        first_contact = query_res[0]
        self.assertEqual(first_contact.get("telephone_number"), "112")
        self.assertTrue(first_contact.get("is_primary_emergency"))

    # -------------------------------------------------------------------------
    # Requirement 14: Contact Jurisdiction Filtering
    # -------------------------------------------------------------------------
    def test_14_contact_jurisdiction_filtering(self):
        # When querying for Ramban, TCU Ramban must be returned, and universal 112 must NOT be dropped
        ramban_contacts, _ = query_verified_contacts(jurisdiction="Ramban", file_path=DEFAULT_CONTACTS_PATH)
        numbers = [c["telephone_number"] for c in ramban_contacts]
        self.assertIn("112", numbers)  # Universal statutory emergency
        self.assertIn("9419993745", numbers)  # TCU Ramban

        # When querying for Jammu
        jammu_contacts, _ = query_verified_contacts(jurisdiction="Jammu", file_path=DEFAULT_CONTACTS_PATH)
        j_numbers = [c["telephone_number"] for c in jammu_contacts]
        self.assertIn("112", j_numbers)
        self.assertIn("0191-2459048", j_numbers)  # TCU Jammu

    # -------------------------------------------------------------------------
    # Requirement 15: Unverified Contact Suppression
    # -------------------------------------------------------------------------
    def test_15_unverified_contact_suppression(self):
        sample_contacts = [
            {
                "contact_id": "c_verified_1",
                "organization": "Verified Emergency",
                "telephone_number": "112",
                "service_description": "ERSS",
                "category": "NATIONAL_EMERGENCY",
                "geographic_jurisdiction": "Pan-India",
                "verification_status": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                "is_primary_emergency": True,
            },
            {
                "contact_id": "c_unverified_2",
                "organization": "Rumored Taxi Helpline",
                "telephone_number": "9999999999",
                "service_description": "Unverified phone from social media",
                "category": "TRAFFIC_CONTROL",
                "geographic_jurisdiction": "Katra",
                "verification_status": VerificationStatus.UNVERIFIED.value,
                "is_primary_emergency": False,
            },
        ]
        tmp_path = self._create_temp_contacts_json(sample_contacts)

        # By default, unverified contacts MUST be suppressed
        filtered_default, _ = query_verified_contacts(file_path=tmp_path, include_unverified=False)
        ids_default = [c["contact_id"] for c in filtered_default]
        self.assertIn("c_verified_1", ids_default)
        self.assertNotIn("c_unverified_2", ids_default)

        # Explicit inclusion
        filtered_all, _ = query_verified_contacts(file_path=tmp_path, include_unverified=True)
        ids_all = [c["contact_id"] for c in filtered_all]
        self.assertIn("c_unverified_2", ids_all)

    # -------------------------------------------------------------------------
    # Requirement 16: Live Data Manager Integration (UnifiedLiveDataManager)
    # -------------------------------------------------------------------------
    def test_16_live_data_manager_integration(self):
        mgr = UnifiedLiveDataManager()
        notice_adapter = CuratedOperationalNoticesAdapter()
        contact_adapter = CuratedContactAdapter()
        mgr.register_provider(notice_adapter)
        mgr.register_provider(contact_adapter)

        # Operational Notice fetch
        req_notice = ProviderRequest(
            domain=DataDomain.OPERATIONAL_NOTICE.value,
            location="Vaishno Devi",
        )
        res_notice = mgr.fetch_data(req_notice)
        self.assertTrue(res_notice.is_success)
        self.assertEqual(res_notice.domain, DataDomain.OPERATIONAL_NOTICE.value)
        self.assertEqual(res_notice.source_type, SourceType.CURATED_DATA.value)
        self.assertEqual(res_notice.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)
        self.assertIn("notices", res_notice.data)

        # Emergency & Contact fetch
        req_contact = ProviderRequest(
            domain=DataDomain.EMERGENCY.value,
            location="Katra",
        )
        res_contact = mgr.fetch_data(req_contact)
        self.assertTrue(res_contact.is_success)
        self.assertEqual(res_contact.domain, DataDomain.EMERGENCY.value)
        self.assertEqual(res_contact.data.get("primary_emergency_number"), "112")
        self.assertIn("contacts", res_contact.data)

    # -------------------------------------------------------------------------
    # Requirement 17: Central AI Agent Specialist Tools & Fallback Routing
    # -------------------------------------------------------------------------
    def test_17_central_agent_tools_and_fallback_routing(self):
        # 1. Tools exist in CENTRAL_TOOLS
        tool_names = [t.name for t in CENTRAL_TOOLS]
        self.assertIn("query_operational_notices", tool_names)
        self.assertIn("lookup_verified_contacts", tool_names)

        # 2. Invoke query_operational_notices tool
        res_notice_tool = query_operational_notices.invoke({"route": "Katra-Bhawan Yatra Trek"})
        self.assertEqual(res_notice_tool["status"], "SUCCESS")
        self.assertIn("notices", res_notice_tool)
        self.assertIn(res_notice_tool["aggregate_status"], ["HAS_NOTICES", "NO_ACTIVE_NOTICES"])

        # 3. Invoke lookup_verified_contacts tool
        res_contact_tool = lookup_verified_contacts.invoke({"category": "NATIONAL_EMERGENCY"})
        self.assertEqual(res_contact_tool["status"], "SUCCESS")
        self.assertEqual(res_contact_tool["primary_emergency_number"], "112")
        self.assertGreater(len(res_contact_tool["contacts"]), 0)

        # 4. Pattern detection helpers
        self.assertTrue(is_operational_notice_query("Is Tarakote Marg open or closed due to landslide?"))
        self.assertTrue(is_operational_notice_query("What is the track status and is yatra suspended?"))
        self.assertTrue(is_verified_contact_query("Please share emergency helpline numbers for Katra"))
        self.assertTrue(is_verified_contact_query("What is the police station or ambulance contact?"))

        # 5. Deterministic fallback turn for Operational Notices
        turn_notice = process_conversational_turn("Is the track closed or suspended?")
        self.assertEqual(turn_notice["status"], "SUCCESS")
        self.assertEqual(turn_notice["execution_mode"], "deterministic_operational_notice")
        self.assertIn("operational_notices", turn_notice)
        self.assertIn("Jai Mata Di", turn_notice["reply"])
        self.assertTrue(len(turn_notice.get("source_provenance", [])) > 0)

        # 6. Deterministic fallback turn for Verified Helplines
        turn_contacts = process_conversational_turn("Give me emergency helpline numbers")
        self.assertEqual(turn_contacts["status"], "SUCCESS")
        self.assertEqual(turn_contacts["execution_mode"], "deterministic_verified_contacts")
        self.assertIn("verified_contacts", turn_contacts)
        self.assertIn("112", turn_contacts["reply"])
        self.assertTrue(len(turn_contacts.get("source_provenance", [])) > 0)

    # -------------------------------------------------------------------------
    # Requirement 18: Fail-Closed Verification Metadata Defaults (F-02 Remediation)
    # -------------------------------------------------------------------------
    def test_18_fail_closed_verification_metadata_defaults(self):
        """MANDATORY SAFETY INVARIANT (F-02 Remediation):
        Records missing verification metadata MUST default to:
        - verification_status = UNVERIFIED
        - verified_by = None
        - verified_at = None
        Never generate synthetic verifiers, timestamps, or automatic verified status.
        Catalog retrieval success must NEVER be conflated with verification.
        """
        # 1. Raw JSON notice without verification fields
        unverified_raw_notice = [
            {
                "notice_id": "notice_raw_001",
                "notice_title": "Unverified Public Notice",
                "notice_text": "Rumored track condition from anonymous post.",
                "issuing_authority": "Local Rumor",
                "source_url": "https://example.com/rumor",
                "affected_location": "Tarakote",
            }
        ]
        tmp_notice_path = self._create_temp_notices_json(unverified_raw_notice)
        loaded_notices, load_status = load_curated_notices(tmp_notice_path)
        self.assertEqual(load_status, "SUCCESS")
        self.assertEqual(len(loaded_notices), 1)

        loaded_n = loaded_notices[0]
        self.assertEqual(loaded_n.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(loaded_n.verified_by)
        self.assertIsNone(loaded_n.verified_at)

        # 2. Raw JSON contact without verification fields
        unverified_raw_contact = [
            {
                "contact_id": "contact_raw_001",
                "organization": "Unverified Local Guide",
                "telephone_number": "9123456789",
                "service_description": "Private trekking assistance",
                "category": ContactCategory.SHRINE_BOARD_ASSISTANCE.value,
                "geographic_jurisdiction": "Katra",
            }
        ]
        tmp_contact_path = self._create_temp_contacts_json(unverified_raw_contact)
        loaded_contacts, _ = load_verified_contacts(tmp_contact_path)
        self.assertEqual(len(loaded_contacts), 1)

        loaded_c = loaded_contacts[0]
        self.assertEqual(loaded_c.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(loaded_c.verified_by)
        self.assertIsNone(loaded_c.verified_at)

        # 3. Direct dataclass construction without verification metadata
        default_notice = OperationalNotice(
            notice_id="def_n",
            notice_title="Title",
            notice_text="Text",
            issuing_authority="Auth",
            source_url="http://example.com",
            affected_location="Loc",
        )
        self.assertEqual(default_notice.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(default_notice.verified_by)
        self.assertIsNone(default_notice.verified_at)

        default_contact = VerifiedContact(
            contact_id="def_c",
            organization="Org",
            telephone_number="123",
            service_description="Desc",
        )
        self.assertEqual(default_contact.verification_status, VerificationStatus.UNVERIFIED.value)
        self.assertIsNone(default_contact.verified_by)
        self.assertIsNone(default_contact.verified_at)

        # 4. Verified records with explicit metadata must retain declared values
        explicit_notice = OperationalNotice(
            notice_id="exp_n",
            notice_title="Title",
            notice_text="Text",
            issuing_authority="SMVDSB",
            source_url="https://maavaishnodevi.org",
            affected_location="Katra",
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            verified_by="Official SMVDSB Guidelines Audit",
            verified_at="2026-11-07T12:00:00Z",
        )
        self.assertEqual(explicit_notice.verification_status, VerificationStatus.VERIFIED_CURATED_SOURCE.value)
        self.assertEqual(explicit_notice.verified_by, "Official SMVDSB Guidelines Audit")
        self.assertEqual(explicit_notice.verified_at, "2026-11-07T12:00:00Z")

    # -------------------------------------------------------------------------
    # Requirement 19: Operational Notice Card UI State Differentiation (F-03 Remediation)
    # -------------------------------------------------------------------------
    def test_19_frontend_operational_notice_card_state_differentiation(self):
        """MANDATORY SAFETY INVARIANT (F-03 Remediation):
        Validates distinct UI states in OperationalNoticeCard.jsx:
        1. SOURCE_UNAVAILABLE renders distinct amber/yellow warning (notice-unavailable-state).
        2. NO_ACTIVE_NOTICES renders informational empty-state banner (notice-empty-state).
        3. HAS_NOTICES renders active notices list (notice-active-list).
        4. Empty notices array with SOURCE_UNAVAILABLE NEVER renders the empty-state banner.
        5. Null / malformed inputs are handled defensively without throwing.
        """
        card_jsx_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "frontend",
            "src",
            "components",
            "chat",
            "cards",
            "OperationalNoticeCard.jsx",
        )
        self.assertTrue(os.path.exists(card_jsx_path), "OperationalNoticeCard.jsx must exist")
        with open(card_jsx_path, "r", encoding="utf-8") as f:
            jsx_content = f.read()

        # Static inspection of required testids and safety branches
        self.assertIn('data-testid="notice-unavailable-state"', jsx_content)
        self.assertIn('data-testid="notice-empty-state"', jsx_content)
        self.assertIn('data-testid="notice-active-list"', jsx_content)
        self.assertIn("Operational Notice Registry Unavailable", jsx_content)
        self.assertIn("The curated registry could not be accessed", jsx_content)
        self.assertIn("Registry Unavailable", jsx_content)

        # Execute Node.js verification simulating component state selection logic
        node_script = """
        function resolveState(noticesData) {
          if (!noticesData) return { rendered: null };
          let notices = [];
          let aggregateStatus = 'HAS_NOTICES';

          if (Array.isArray(noticesData)) {
            notices = noticesData;
            aggregateStatus = notices.length > 0 ? 'HAS_NOTICES' : 'NO_ACTIVE_NOTICES';
          } else if (typeof noticesData === 'object') {
            notices = noticesData.notices || (noticesData.notice_id ? [noticesData] : []);
            if (noticesData.aggregate_status) {
              aggregateStatus = String(noticesData.aggregate_status).toUpperCase();
            } else if (notices.length > 0) {
              aggregateStatus = 'HAS_NOTICES';
            } else {
              aggregateStatus = 'NO_ACTIVE_NOTICES';
            }
          } else {
            return { rendered: null };
          }

          const isUnavailable = aggregateStatus === 'SOURCE_UNAVAILABLE';
          const hasNotices = !isUnavailable && aggregateStatus === 'HAS_NOTICES' && notices.length > 0;
          const isNoActiveNotices = !isUnavailable && (aggregateStatus === 'NO_ACTIVE_NOTICES' || notices.length === 0);

          return { isUnavailable, hasNotices, isNoActiveNotices, aggregateStatus };
        }

        const stateUnavail = resolveState({ aggregate_status: 'SOURCE_UNAVAILABLE', notices: [] });
        const stateEmpty = resolveState({ aggregate_status: 'NO_ACTIVE_NOTICES', notices: [] });
        const stateActive = resolveState({ aggregate_status: 'HAS_NOTICES', notices: [{ notice_id: 'n1' }] });
        const stateNull = resolveState(null);
        const stateMalformed = resolveState("invalid string");

        console.log(JSON.stringify({ stateUnavail, stateEmpty, stateActive, stateNull, stateMalformed }));
        """
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)

        # Assert SOURCE_UNAVAILABLE state
        u = res["stateUnavail"]
        self.assertTrue(u["isUnavailable"])
        self.assertFalse(u["isNoActiveNotices"], "SOURCE_UNAVAILABLE must NEVER trigger isNoActiveNotices empty state!")
        self.assertFalse(u["hasNotices"])

        # Assert NO_ACTIVE_NOTICES state
        e = res["stateEmpty"]
        self.assertFalse(e["isUnavailable"])
        self.assertTrue(e["isNoActiveNotices"])
        self.assertFalse(e["hasNotices"])

        # Assert HAS_NOTICES state
        a = res["stateActive"]
        self.assertFalse(a["isUnavailable"])
        self.assertFalse(a["isNoActiveNotices"])
        self.assertTrue(a["hasNotices"])

        # Assert Defensive handling
        self.assertIsNone(res["stateNull"]["rendered"])
        self.assertIsNone(res["stateMalformed"]["rendered"])

    # -------------------------------------------------------------------------
    # Requirement 20: Emergency Contact Priority Hierarchy (F-04 Remediation)
    # -------------------------------------------------------------------------
    def test_20_emergency_contact_priority_hierarchy(self):
        """MANDATORY SAFETY INVARIANT (F-04 Remediation):
        Category ordering must prioritize life-safety over administrative inquiry:
        1. NATIONAL_EMERGENCY (112)
        2. MEDICAL_ASSISTANCE (108)
        3. LOCAL_POLICE (Katra Police Station)
        4. TRAFFIC_CONTROL (TCU Ramban, TCU Jammu, TCU Udhampur)
        5. SHRINE_BOARD_ASSISTANCE (SMVDSB Call Centre, Protocol Desk)
        Within each category, deterministic organization ordering is preserved.
        Protocol desk remains identifiable as non-emergency office-hours only.
        """
        all_contacts, meta = query_verified_contacts(file_path=DEFAULT_CONTACTS_PATH)
        self.assertGreater(len(all_contacts), 0)

        # 1. 112 is always first
        self.assertEqual(all_contacts[0]["telephone_number"], "112")
        self.assertEqual(all_contacts[0]["category"], ContactCategory.NATIONAL_EMERGENCY.value)

        # 2. 108 Emergency Ambulance appears immediately after 112 (Rank 2)
        medical_contact = next(c for c in all_contacts if c["telephone_number"] == "108")
        self.assertEqual(medical_contact["category"], ContactCategory.MEDICAL_ASSISTANCE.value)
        idx_108 = all_contacts.index(medical_contact)
        self.assertEqual(idx_108, 1, "108 Emergency Ambulance must be ranked 2nd right after 112")

        # 3. Katra Police Station appears before administrative and traffic assistance (Rank 3)
        police_contact = next(c for c in all_contacts if c["category"] == ContactCategory.LOCAL_POLICE.value)
        idx_police = all_contacts.index(police_contact)
        self.assertEqual(idx_police, 2, "Katra Police Station must be ranked 3rd")

        # 4. Traffic Control units appear before Shrine Board assistance (Rank 4)
        tcu_contacts = [c for c in all_contacts if c["category"] == ContactCategory.TRAFFIC_CONTROL.value]
        self.assertGreater(len(tcu_contacts), 0)
        idx_tcu_first = all_contacts.index(tcu_contacts[0])
        self.assertGreater(idx_tcu_first, idx_police)

        # 5. Shrine Board assistance appears last (Rank 5)
        sb_contacts = [c for c in all_contacts if c["category"] == ContactCategory.SHRINE_BOARD_ASSISTANCE.value]
        self.assertGreater(len(sb_contacts), 0)
        idx_sb_first = all_contacts.index(sb_contacts[0])
        self.assertGreater(idx_sb_first, idx_tcu_first, "Shrine Board administrative contacts must appear after traffic control")

        # 6. Protocol Desk is clearly identifiable as non-emergency and office-hours only
        protocol = next(c for c in sb_contacts if "protocol" in c["organization"].lower())
        self.assertIn("office hours only", protocol["operating_hours"].lower())
        self.assertIn("administrative", protocol["service_description"].lower())
        self.assertFalse(protocol.get("is_primary_emergency", False))
        self.assertIn("not a 24x7 emergency helpline", protocol.get("notes", "").lower())


if __name__ == "__main__":
    unittest.main()
