"""
Phase 8.8.58 — Comprehensive Test Suite for Smart Itinerary Management,
Partial Editing, Undo/Versioning, Optimistic Concurrency & Group Collaboration.
"""

import json
import os
import secrets
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from starlette.requests import Request

from backend.main import app
from backend.routes import itineraries as itin_routes
from agents.auth_service import auth_service, init_auth_db
from agents.itinerary_collab_service import hash_invite_token


def _make_request(method="GET", path="/api/itineraries", headers=None):
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("utf-8"), str(v).encode("utf-8")))
    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "scheme": "http",
        "server": ("testserver", 80),
        "headers": raw_headers,
    }
    return Request(scope)


def _sample_itinerary_payload():
    return {
        "title": "Family Vaishno Devi Pilgrimage",
        "destination": "Shri Mata Vaishno Devi Shrine",
        "start_date": "2026-12-10",
        "duration_days": 4,
        "travellers_count": 3,
        "notes": "Senior citizen wheelchair needed at Bhawan",
        "phone_number": "+91-9811100022",
        "aadhaar": "1234-5678-9012",
        "private_notes": "Secret vault pin 9988",
        "preferences": {"pace": "moderate", "mobility": "elder_friendly"},
        "booking_refs": [
            {
                "booking_id": "YATRA-PRIV-8899",
                "type": "Helicopter & Parchi",
                "label": "Katra -> Sanjichhat",
                "date": "2026-12-11",
                "slot_time": "08:00 AM",
                "payment_id": "pay_secret_5544",
                "receipt_json": {"secret": "rzp_live_123"},
            }
        ],
        "days": [
            {
                "day_number": 1,
                "date": "2026-12-10",
                "title": "Arrival at Katra & RFID Check-in",
                "activities": [
                    {"time": "10:00 AM", "duration": "2 hrs", "activity": "Hotel check-in & Yatra Parchi RFID", "notes": ""}
                ],
            },
            {
                "day_number": 2,
                "date": "2026-12-11",
                "title": "Holy Bhawan Darshan",
                "activities": [
                    {"time": "06:30 AM", "duration": "5 hrs", "activity": "Trek via Ardhkuwari Cave to Bhawan", "place": "Ardhkuwari Cave", "notes": ""}
                ],
            },
            {
                "day_number": 3,
                "date": "2026-12-12",
                "title": "Recovery & Local Sightseeing",
                "activities": [
                    {"time": "10:00 AM", "duration": "2 hrs", "activity": "Visit Banganga Temple", "place": "Banganga Temple", "notes": ""}
                ],
            },
            {
                "day_number": 4,
                "date": "2026-12-13",
                "title": "Departure Day",
                "activities": [
                    {"time": "09:00 AM", "duration": "1.5 hrs", "activity": "Prasad shopping & checkout", "notes": ""}
                ],
            },
        ],
    }


class TestPhase8858ItineraryManagementAndCollaboration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.tmpdir, "test_auth_collab.db")
        self.orig_db_path = auth_service.db_path
        self.orig_mongo_backend = os.environ.get("PERSISTENCE_BACKEND")
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        auth_service.db_path = self.test_db
        init_auth_db(self.test_db)

        self.owner_tok, self.owner_id = self._register_user("owner.pilgrim@example.com")
        self.collab_tok, self.collab_id = self._register_user("companion.collab@example.com")
        self.stranger_tok, self.stranger_id = self._register_user("stranger.other@example.com")

    def tearDown(self):
        auth_service.db_path = self.orig_db_path
        if self.orig_mongo_backend is None:
            os.environ.pop("PERSISTENCE_BACKEND", None)
        else:
            os.environ["PERSISTENCE_BACKEND"] = self.orig_mongo_backend
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _register_user(self, email):
        now = datetime.now(timezone.utc)
        session_token = secrets.token_urlsafe(32)
        expires = (now + timedelta(days=7)).isoformat()
        with sqlite3.connect(self.test_db, timeout=10.0) as conn:
            cursor = conn.cursor()
            user, _ = auth_service._get_or_create_user(email, cursor)
            cursor.execute(
                "INSERT INTO auth_sessions (session_token, user_id, email, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (session_token, user["user_id"], email, now.isoformat(), expires),
            )
            conn.commit()
        return session_token, user["user_id"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}

    def _create_base_itinerary(self):
        payload = itin_routes.UpsertItineraryPayload(
            title="Family Vaishno Devi Pilgrimage",
            source_key="sess-dedup-101",
            itinerary=_sample_itinerary_payload(),
        )
        res = itin_routes.create_or_upsert_itinerary(
            payload, _make_request("POST", "/api/itineraries", self._headers(self.owner_tok))
        )
        return res["itinerary"]

    def test_00_routes_mounted_on_fastapi_app(self):
        paths = {getattr(r, "path", "") for r in app.routes}
        for expected in [
            "/api/itineraries",
            "/api/itineraries/{itinerary_id}",
            "/api/itineraries/{itinerary_id}/edit/preview",
            "/api/itineraries/{itinerary_id}/edit/apply",
            "/api/itineraries/{itinerary_id}/edit/undo",
            "/api/itineraries/{itinerary_id}/shares",
            "/api/itineraries/{itinerary_id}/shares/members/{member_user_id}",
            "/api/itineraries/{itinerary_id}/shares/invites/{invite_id}",
            "/api/itineraries/invites/{token}/accept",
            "/api/itineraries/invites/accept",
        ]:
            self.assertIn(expected, paths)

    def test_01_create_dedup_list_open_and_delete(self):
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]
        self.assertEqual(created["my_role"], "OWNER")
        self.assertEqual(created["duration_days"], 4)
        self.assertEqual(created["travellers_count"], 3)
        self.assertEqual(created["sharing_status"], "Private")

        # Duplicate save with same source_key updates cleanly without creating 2nd row
        dup_payload = itin_routes.UpsertItineraryPayload(
            title="Family Vaishno Devi Pilgrimage v2",
            source_key="sess-dedup-101",
            itinerary=_sample_itinerary_payload(),
        )
        res_dup = itin_routes.create_or_upsert_itinerary(
            dup_payload, _make_request("POST", "/api/itineraries", self._headers(self.owner_tok))
        )
        self.assertEqual(res_dup["itinerary"]["itinerary_id"], iid)

        listed = itin_routes.list_itineraries(_make_request("GET", "/api/itineraries", self._headers(self.owner_tok)))
        self.assertEqual(listed["count"], 1)

        det = itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.owner_tok)))
        self.assertEqual(det["itinerary"]["itinerary_id"], iid)

        d_res = itin_routes.delete_itinerary(iid, _make_request("DELETE", f"/api/itineraries/{iid}", self._headers(self.owner_tok)))
        self.assertEqual(d_res["status"], "success")

        listed_after = itin_routes.list_itineraries(_make_request("GET", "/api/itineraries", self._headers(self.owner_tok)))
        self.assertEqual(listed_after["count"], 0)

    def test_02_partial_single_day_edits_preserve_unaffected_days_and_bookings(self):
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]
        orig_days = created["data"]["days"]
        orig_bookings = created["data"]["booking_refs"]

        # Preview regenerate Day 3 only (use_ai=False for offline deterministic test determinism)
        prev = itin_routes.preview_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(
                operation="regenerate_day",
                day_number=3,
                instruction="Make Day 3 a relaxing recovery day",
                use_ai=False,
            ),
            _make_request("POST", f"/api/itineraries/{iid}/edit/preview", self._headers(self.owner_tok)),
        )
        p_body = prev["preview"]
        self.assertEqual(p_body["affected_days"], [3])
        self.assertEqual(p_body["after"]["days"][0], orig_days[0])
        self.assertEqual(p_body["after"]["days"][1], orig_days[1])
        self.assertEqual(p_body["after"]["days"][3], orig_days[3])
        self.assertEqual(p_body["after"]["booking_refs"], orig_bookings)

        # Confirm DB untouched before Apply
        still_orig = itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.owner_tok)))["itinerary"]
        self.assertEqual(still_orig["revision"], created["revision"])
        self.assertEqual(still_orig["data"]["days"][2]["title"], orig_days[2]["title"])

        # Apply Day 3 regeneration
        updated = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(
                operation="regenerate_day",
                day_number=3,
                instruction="Make Day 3 a relaxing recovery day",
                use_ai=False,
                expected_revision=created["revision"],
            ),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]

        self.assertEqual(updated["revision"], created["revision"] + 1)
        self.assertNotEqual(updated["data"]["days"][2]["title"], orig_days[2]["title"])
        self.assertEqual(updated["data"]["days"][0], orig_days[0])
        self.assertEqual(updated["data"]["days"][1], orig_days[1])
        self.assertEqual(updated["data"]["days"][3], orig_days[3])
        self.assertEqual(updated["data"]["booking_refs"], orig_bookings)

    def test_03_structured_operations_undo_and_duration_confirmation(self):
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]
        rev = created["revision"]

        r_add = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="add_destination", day_number=3, place="Baba Dhansar", time="03:00 PM", duration="2 hrs", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_add["revision"]
        self.assertTrue(any("Baba Dhansar" in json.dumps(a) for a in r_add["data"]["days"][2]["activities"]))

        r_rep = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="replace_destination", day_number=3, old_place="Baba Dhansar", new_place="Patnitop", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_rep["revision"]
        self.assertTrue(any("Patnitop" in json.dumps(a) for a in r_rep["data"]["days"][2]["activities"]))

        r_time = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="update_timing", day_number=3, activity_index=0, time="11:00 AM", duration="3 hrs", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_time["revision"]
        self.assertEqual(r_time["data"]["days"][2]["activities"][0]["time"], "11:00 AM")

        r_pref = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="update_preferences", day_number=3, preferences={"pace": "relaxed"}, expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_pref["revision"]
        self.assertEqual(r_pref["data"]["days"][2]["preferences"]["pace"], "relaxed")

        r_note = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="update_notes", day_number=3, notes="Carry warm shawl", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_note["revision"]
        self.assertEqual(r_note["data"]["days"][2]["notes"], "Carry warm shawl")

        r_rem = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="remove_destination", day_number=3, place="Patnitop", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        rev = r_rem["revision"]

        # Duration reduction without confirm_impact MUST raise 422 impact warning
        with self.assertRaises(HTTPException) as ctx_shrink:
            itin_routes.apply_itinerary_change(
                iid,
                itin_routes.ItineraryEditRequest(operation="adjust_duration", duration_days=2, expected_revision=rev, confirm_impact=False),
                _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
            )
        self.assertEqual(ctx_shrink.exception.status_code, 422)

        r_shrink_ok = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="adjust_duration", duration_days=2, expected_revision=rev, confirm_impact=True),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )["itinerary"]
        self.assertEqual(len(r_shrink_ok["data"]["days"]), 2)

        r_undo = itin_routes.undo_itinerary_change(
            iid,
            _make_request("POST", f"/api/itineraries/{iid}/edit/undo", self._headers(self.owner_tok)),
            itin_routes.UndoEditRequest(expected_revision=r_shrink_ok["revision"]),
        )["itinerary"]
        self.assertEqual(len(r_undo["data"]["days"]), 4)

    def test_04_malformed_ai_output_rejected_and_concurrent_revision_conflict(self):
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]
        rev = created["revision"]

        for bad_ai in [
            "not json at all",
            {"day_number": 3, "title": "", "activities": []},
            {"day_number": 1, "title": "Wrong Day", "activities": ["Valid activity"]},
            {"days": [{"day_number": 1, "title": "Overwrite attempt"}]},
        ]:
            with self.assertRaises(HTTPException) as ctx_bad:
                itin_routes.apply_itinerary_change(
                    iid,
                    itin_routes.ItineraryEditRequest(operation="regenerate_day", day_number=3, ai_response=bad_ai, expected_revision=rev),
                    _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
                )
            self.assertEqual(ctx_bad.exception.status_code, 422)

        # Valid update advances revision
        itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="update_notes", day_number=1, notes="Fresh rev note", expected_revision=rev),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
        )

        # Stale expected_revision must raise 409 Conflict
        with self.assertRaises(HTTPException) as ctx_conflict:
            itin_routes.apply_itinerary_change(
                iid,
                itin_routes.ItineraryEditRequest(operation="update_notes", day_number=1, notes="Stale overwrite", expected_revision=rev),
                _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.owner_tok)),
            )
        self.assertEqual(ctx_conflict.exception.status_code, 409)

    def test_05_sharing_roles_invite_hashing_expiry_revocation_and_sanitization(self):
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]

        # 1. Owner generates VIEWER invite; DB stores SHA-256 hash only
        inv_res = itin_routes.create_share_invite(
            iid,
            itin_routes.CreateInviteRequest(role="VIEWER", expires_in_hours=24),
            _make_request("POST", f"/api/itineraries/{iid}/shares", self._headers(self.owner_tok)),
        )
        raw_token = inv_res["share"]["invite_token"]
        invite_id = inv_res["share"]["invite_id"]

        with sqlite3.connect(self.test_db) as conn:
            row = conn.execute("SELECT token_hash FROM itinerary_invites WHERE invite_id = ?", (invite_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], hash_invite_token(raw_token))
            self.assertNotEqual(row[0], raw_token)

        # 2. Unauthenticated invite acceptance blocked (401)
        with self.assertRaises(HTTPException) as ctx_unauth:
            itin_routes.accept_share_invite_body(
                itin_routes.AcceptInviteBody(token=raw_token),
                _make_request("POST", "/api/itineraries/invites/accept"),
            )
        self.assertEqual(ctx_unauth.exception.status_code, 401)

        # 3. Collaborator accepts VIEWER invite -> receives privacy-sanitized payload
        acc = itin_routes.accept_share_invite_body(
            itin_routes.AcceptInviteBody(token=raw_token),
            _make_request("POST", "/api/itineraries/invites/accept", self._headers(self.collab_tok)),
        )
        shared = acc["itinerary"]
        self.assertEqual(shared["my_role"], "VIEWER")
        self.assertFalse(shared["can_edit"])
        self.assertFalse(shared["can_delete"])
        dumped_shared = json.dumps(shared)
        self.assertNotIn("9811100022", dumped_shared)
        self.assertNotIn("1234-5678-9012", dumped_shared)
        self.assertNotIn("pay_secret_5544", dumped_shared)
        self.assertNotIn("rzp_live_123", dumped_shared)
        self.assertNotIn("Secret vault pin 9988", dumped_shared)
        self.assertNotIn("owner.pilgrim@example.com", dumped_shared)

        # 4. VIEWER cannot edit, delete, or manage shares
        with self.assertRaises(HTTPException) as c_ve:
            itin_routes.apply_itinerary_change(
                iid,
                itin_routes.ItineraryEditRequest(operation="update_notes", day_number=1, notes="Hacked"),
                _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.collab_tok)),
            )
        self.assertEqual(c_ve.exception.status_code, 403)

        with self.assertRaises(HTTPException) as c_vd:
            itin_routes.delete_itinerary(iid, _make_request("DELETE", f"/api/itineraries/{iid}", self._headers(self.collab_tok)))
        self.assertEqual(c_vd.exception.status_code, 403)

        with self.assertRaises(HTTPException) as c_vs:
            itin_routes.list_share_access(iid, _make_request("GET", f"/api/itineraries/{iid}/shares", self._headers(self.collab_tok)))
        self.assertEqual(c_vs.exception.status_code, 403)

        # 5. Stranger cannot access guessed itinerary ID
        with self.assertRaises(HTTPException) as c_st:
            itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.stranger_tok)))
        self.assertEqual(c_st.exception.status_code, 403)

        with self.assertRaises(HTTPException) as c_404:
            itin_routes.get_itinerary_detail("itin_nonexistent999", _make_request("GET", "/api/itineraries/itin_nonexistent999", self._headers(self.stranger_tok)))
        self.assertEqual(c_404.exception.status_code, 404)

        # 6. Owner upgrades collaborator to EDITOR -> EDITOR CAN edit & undo, CANNOT delete or manage shares
        itin_routes.update_share_member_role(
            iid,
            self.collab_id,
            itin_routes.UpdateMemberRoleRequest(role="EDITOR"),
            _make_request("PATCH", f"/api/itineraries/{iid}/shares/members/{self.collab_id}", self._headers(self.owner_tok)),
        )
        ed_res = itin_routes.apply_itinerary_change(
            iid,
            itin_routes.ItineraryEditRequest(operation="update_notes", day_number=2, notes="Editor added group reminder", expected_revision=shared["revision"]),
            _make_request("POST", f"/api/itineraries/{iid}/edit/apply", self._headers(self.collab_tok)),
        )
        self.assertEqual(ed_res["status"], "success")

        owner_view = itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.owner_tok)))["itinerary"]
        self.assertEqual(owner_view["data"]["booking_refs"][0]["payment_id"], "pay_secret_5544")

        with self.assertRaises(HTTPException) as c_ed:
            itin_routes.delete_itinerary(iid, _make_request("DELETE", f"/api/itineraries/{iid}", self._headers(self.collab_tok)))
        self.assertEqual(c_ed.exception.status_code, 403)

        with self.assertRaises(HTTPException) as c_es:
            itin_routes.list_share_access(iid, _make_request("GET", f"/api/itineraries/{iid}/shares", self._headers(self.collab_tok)))
        self.assertEqual(c_es.exception.status_code, 403)

        # 7. Owner revokes collaborator -> immediate 403
        itin_routes.revoke_share_member(
            iid,
            self.collab_id,
            _make_request("DELETE", f"/api/itineraries/{iid}/shares/members/{self.collab_id}", self._headers(self.owner_tok)),
        )
        with self.assertRaises(HTTPException) as c_rev:
            itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.collab_tok)))
        self.assertEqual(c_rev.exception.status_code, 403)

        # 8. Owner revokes invite link -> rejected without leaking itinerary data
        itin_routes.revoke_share_invite(
            iid,
            invite_id,
            _make_request("DELETE", f"/api/itineraries/{iid}/shares/invites/{invite_id}", self._headers(self.owner_tok)),
        )
        with self.assertRaises(HTTPException) as c_rinv:
            itin_routes.accept_share_invite_body(
                itin_routes.AcceptInviteBody(token=raw_token),
                _make_request("POST", "/api/itineraries/invites/accept", self._headers(self.stranger_tok)),
            )
        self.assertIn(c_rinv.exception.status_code, (403, 410))
        self.assertNotIn("Family Vaishno Devi", str(c_rinv.exception.detail))

        # 9. Expired invite token rejected without leaking itinerary data
        inv2 = itin_routes.create_share_invite(
            iid,
            itin_routes.CreateInviteRequest(role="VIEWER", expires_in_hours=1),
            _make_request("POST", f"/api/itineraries/{iid}/shares", self._headers(self.owner_tok)),
        )["share"]
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("UPDATE itinerary_invites SET expires_at = ? WHERE invite_id = ?", (past_iso, inv2["invite_id"]))
            conn.commit()
        with self.assertRaises(HTTPException) as c_exp:
            itin_routes.accept_share_invite_body(
                itin_routes.AcceptInviteBody(token=inv2["invite_token"]),
                _make_request("POST", "/api/itineraries/invites/accept", self._headers(self.stranger_tok)),
            )
        self.assertEqual(c_exp.exception.status_code, 410)
        self.assertNotIn("Family Vaishno Devi", str(c_exp.exception.detail))

    def test_06_mongodb_filter_tenant_isolation_and_undo_parity(self):
        """Phase 8.8.58B: Verifies MongoDB $and/$or filter correctness, cross-user isolation & member parity."""
        from unittest.mock import patch
        from agents import mongo_store
        from agents.itinerary_collab_service import itinerary_collab_service

        # Minimal in-memory Mongo collection spy implementing $and/$or/$exists semantics & recording filters
        class _UpdateRes:
            def __init__(self, matched):
                self.matched_count = matched

        class _CursorList(list):
            def sort(self, *args, **kwargs):
                return self

        class _InMemoryColl:
            def __init__(self, docs=None):
                self.docs = list(docs or [])
                self.recorded_filters = []

            def _matches(self, doc, filt):
                if not filt:
                    return True
                if "$and" in filt:
                    return all(self._matches(doc, sub) for sub in filt["$and"])
                if "$or" in filt:
                    return any(self._matches(doc, sub) for sub in filt["$or"])
                for k, v in filt.items():
                    if k.startswith("$"):
                        continue
                    if isinstance(v, dict) and "$exists" in v:
                        exists = k in doc
                        if exists != bool(v["$exists"]):
                            return False
                    elif doc.get(k) != v:
                        return False
                return True

            def find_one(self, filt):
                for d in self.docs:
                    if self._matches(d, filt):
                        return json.loads(json.dumps(d))
                return None

            def find(self, filt):
                return _CursorList([json.loads(json.dumps(d)) for d in self.docs if self._matches(d, filt)])

            def count_documents(self, filt):
                return sum(1 for d in self.docs if self._matches(d, filt))

            def insert_one(self, doc):
                self.docs.append(json.loads(json.dumps(doc)))

            def update_one(self, filt, update, upsert=False):
                self.recorded_filters.append(json.loads(json.dumps(filt)))
                for idx, d in enumerate(self.docs):
                    if self._matches(d, filt):
                        if "$set" in update:
                            d.update(json.loads(json.dumps(update["$set"])))
                        if "$inc" in update:
                            for ik, iv in update["$inc"].items():
                                d[ik] = d.get(ik, 0) + iv
                        self.docs[idx] = d
                        return _UpdateRes(1)
                if upsert:
                    new_d = dict(update.get("$set") or {})
                    self.docs.append(new_d)
                    return _UpdateRes(1)
                return _UpdateRes(0)

        trip_a_data = _sample_itinerary_payload()
        trip_a_data["title"] = "Trip A"
        colls = {
            "auth_saved_itineraries": _InMemoryColl([
                {"_id": "itin_A", "itinerary_id": "itin_A", "user_id": self.owner_id, "title": "Trip A", "created_at": "2026-01-01T00:00:00Z", "revision": 1, "data": trip_a_data, "edit_history": []},
                {"_id": "itin_B", "itinerary_id": "itin_B", "user_id": self.stranger_id, "title": "Trip B Legacy", "created_at": "2026-01-01T00:00:00Z", "data": _sample_itinerary_payload()},  # legacy doc without revision & same rev-1 effective
                {"_id": "itin_C", "itinerary_id": "itin_C", "user_id": self.stranger_id, "title": "Trip C Same Rev", "created_at": "2026-01-01T00:00:00Z", "revision": 1, "data": _sample_itinerary_payload(), "edit_history": []},
            ]),
            "itinerary_members": _InMemoryColl([
                {"itinerary_id": "itin_A", "user_id": self.owner_id, "role": "OWNER", "revoked_at": None},
                {"itinerary_id": "itin_A", "user_id": self.collab_id, "role": "EDITOR", "revoked_at": None},
            ]),
            "itinerary_invites": _InMemoryColl([]),
            "auth_users": _InMemoryColl([
                {"user_id": self.owner_id, "email": "owner.pilgrim@example.com"},
                {"user_id": self.collab_id, "email": "companion.collab@example.com"},
            ]),
        }

        def fake_get_coll(name):
            return colls[name]

        def fake_get_user_by_id(uid):
            return colls["auth_users"].find_one({"user_id": uid})

        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}), \
             patch.object(mongo_store, "_get_coll", side_effect=fake_get_coll), \
             patch.object(mongo_store, "get_user_by_id", side_effect=fake_get_user_by_id):
            # 1. Edit Itinerary A
            new_a = _sample_itinerary_payload()
            new_a["title"] = "Trip A Updated"
            updated_a = mongo_store.commit_itinerary_edit_collab(
                itinerary_id="itin_A",
                expected_revision=1,
                new_title="Trip A Updated",
                new_data=new_a,
                edited_by=self.owner_id,
                now_iso="2026-01-02T00:00:00Z",
                diff_summary="Updated title",
                old_snapshot={"revision": 1, "title": "Trip A", "data": trip_a_data},
            )
            self.assertIsNotNone(updated_a)
            self.assertEqual(updated_a["title"], "Trip A Updated")
            self.assertEqual(updated_a["revision"], 2)

            # Inspect exact filter passed to update_one: must contain $and with identity AND revision
            last_filter = colls["auth_saved_itineraries"].recorded_filters[-1]
            self.assertIn("$and", last_filter)
            self.assertEqual(len(last_filter["$and"]), 2)
            self.assertIn({"$or": [{"itinerary_id": "itin_A"}, {"_id": "itin_A"}]}, last_filter["$and"])

            # Verify Stranger's Trip B (no revision) and Trip C (revision=1) were NEVER touched
            self.assertEqual(colls["auth_saved_itineraries"].find_one({"itinerary_id": "itin_B"})["title"], "Trip B Legacy")
            self.assertEqual(colls["auth_saved_itineraries"].find_one({"itinerary_id": "itin_C"})["title"], "Trip C Same Rev")

            # 2. Stale expected_revision must fail / return None -> 409 Conflict
            stale = mongo_store.commit_itinerary_edit_collab(
                itinerary_id="itin_A",
                expected_revision=1,
                new_title="Stale Write",
                new_data=new_a,
                edited_by=self.owner_id,
                now_iso="2026-01-03T00:00:00Z",
                diff_summary="Stale",
                old_snapshot={},
            )
            self.assertIsNone(stale)

            # 3. Verify get_itinerary_for_user & undo_last_edit under MongoDB include masked members parity
            detail = itinerary_collab_service.get_itinerary_for_user(self.owner_id, "itin_A")
            self.assertIn("members", detail)
            self.assertGreaterEqual(len(detail["members"]), 2)
            self.assertTrue(all("masked_email" in m for m in detail["members"]))

            reverted = itinerary_collab_service.undo_last_edit(self.collab_id, "itin_A", expected_revision=2)
            self.assertEqual(reverted["title"], "Trip A")
            self.assertIn("members", reverted)

            # 4. Legacy document (missing revision) undo still requires itinerary_id match
            reverted_legacy = mongo_store.commit_undo_itinerary_collab(
                itinerary_id="itin_B",
                expected_revision=1,
                restored_title="Trip B Legacy Undone",
                restored_data=_sample_itinerary_payload(),
                remaining_history=[],
                now_iso="2026-01-04T00:00:00Z",
            )
            self.assertIsNotNone(reverted_legacy)
            self.assertEqual(reverted_legacy["title"], "Trip B Legacy Undone")
            self.assertEqual(colls["auth_saved_itineraries"].find_one({"itinerary_id": "itin_C"})["title"], "Trip C Same Rev")

    def test_07_editor_direct_upsert_hardening_and_owner_preserved(self):
        """Phase 8.8.58B: Direct POST /api/itineraries by EDITOR requires expected_revision & protects owner booking_refs."""
        created = self._create_base_itinerary()
        iid = created["itinerary_id"]

        inv = itin_routes.create_share_invite(
            iid,
            itin_routes.CreateInviteRequest(role="EDITOR", expires_in_hours=24),
            _make_request("POST", f"/api/itineraries/{iid}/shares", self._headers(self.owner_tok)),
        )["share"]
        itin_routes.accept_share_invite_body(
            itin_routes.AcceptInviteBody(token=inv["invite_token"]),
            _make_request("POST", "/api/itineraries/invites/accept", self._headers(self.collab_tok)),
        )

        # 1. EDITOR missing expected_revision -> rejected 400
        bad_payload = _sample_itinerary_payload()
        bad_payload["booking_refs"] = [{"booking_id": "ATTACKER-INJECTED", "payment_id": "evil"}]
        with self.assertRaises(HTTPException) as c_missing_rev:
            itin_routes.create_or_upsert_itinerary(
                itin_routes.UpsertItineraryPayload(itinerary_id=iid, title="Editor Overwrite", itinerary=bad_payload),
                _make_request("POST", "/api/itineraries", self._headers(self.collab_tok)),
            )
        self.assertEqual(c_missing_rev.exception.status_code, 400)

        # 2. EDITOR stale expected_revision -> 409 Conflict
        with self.assertRaises(HTTPException) as c_stale:
            itin_routes.create_or_upsert_itinerary(
                itin_routes.UpsertItineraryPayload(itinerary_id=iid, title="Editor Stale", expected_revision=999, itinerary=bad_payload),
                _make_request("POST", "/api/itineraries", self._headers(self.collab_tok)),
            )
        self.assertEqual(c_stale.exception.status_code, 409)

        # 3. EDITOR valid expected_revision -> succeeds AND owner's private booking_refs remain untouched
        ok_upsert = itin_routes.create_or_upsert_itinerary(
            itin_routes.UpsertItineraryPayload(
                itinerary_id=iid,
                title="Editor Updated Title",
                expected_revision=created["revision"],
                itinerary=bad_payload,
            ),
            _make_request("POST", "/api/itineraries", self._headers(self.collab_tok)),
        )["itinerary"]
        self.assertEqual(ok_upsert["title"], "Editor Updated Title")
        owner_view = itin_routes.get_itinerary_detail(iid, _make_request("GET", f"/api/itineraries/{iid}", self._headers(self.owner_tok)))["itinerary"]
        self.assertEqual(owner_view["data"]["booking_refs"][0]["payment_id"], "pay_secret_5544")
        self.assertNotIn("ATTACKER-INJECTED", json.dumps(owner_view["data"]["booking_refs"]))

        # 4. VIEWER & Stranger remain 403
        itin_routes.update_share_member_role(
            iid,
            self.collab_id,
            itin_routes.UpdateMemberRoleRequest(role="VIEWER"),
            _make_request("PATCH", f"/api/itineraries/{iid}/shares/members/{self.collab_id}", self._headers(self.owner_tok)),
        )
        with self.assertRaises(HTTPException) as c_viewer:
            itin_routes.create_or_upsert_itinerary(
                itin_routes.UpsertItineraryPayload(itinerary_id=iid, title="Viewer Hack", expected_revision=owner_view["revision"], itinerary=bad_payload),
                _make_request("POST", "/api/itineraries", self._headers(self.collab_tok)),
            )
        self.assertEqual(c_viewer.exception.status_code, 403)

        # 5. OWNER retains normal update behavior cleanly (with or without explicit expected_revision)
        owner_upd = itin_routes.create_or_upsert_itinerary(
            itin_routes.UpsertItineraryPayload(itinerary_id=iid, title="Owner Direct Update", itinerary=_sample_itinerary_payload()),
            _make_request("POST", "/api/itineraries", self._headers(self.owner_tok)),
        )["itinerary"]
        self.assertEqual(owner_upd["title"], "Owner Direct Update")

    def test_08_invite_url_public_frontend_fallback_without_origin(self):
        """Phase 8.8.58B: Mobile / non-Origin clients use PUBLIC_FRONTEND_URL cleanly."""
        from unittest.mock import patch

        created = self._create_base_itinerary()
        iid = created["itinerary_id"]
        with patch.dict(os.environ, {"PUBLIC_FRONTEND_URL": "https://yatra-ai.pages.dev/"}):
            inv = itin_routes.create_share_invite(
                iid,
                itin_routes.CreateInviteRequest(role="VIEWER", expires_in_hours=24),
                _make_request("POST", f"/api/itineraries/{iid}/shares", self._headers(self.owner_tok)),
            )["share"]
            self.assertTrue(inv["invite_url"].startswith("https://yatra-ai.pages.dev/?invite="))
            self.assertNotIn("//?invite=", inv["invite_url"])

    def test_09_groq_model_selection_structured_parsing_errors_and_require_ai(self):
        """Phase 8.8.60: Verifies active default model, strict JSON output parsing, reasoning isolation & error paths."""
        from unittest.mock import MagicMock, patch
        from agents import itinerary_editor

        # 1. Model selection defaults to openai/gpt-oss-20b cleanly when unset/whitespace
        with patch.dict(os.environ, {"GROQ_MODEL": ""}, clear=False):
            self.assertEqual(itinerary_editor.get_selected_groq_model(), "openai/gpt-oss-20b")
        with patch.dict(os.environ, {"GROQ_MODEL": "openai/gpt-oss-120b"}, clear=False):
            self.assertEqual(itinerary_editor.get_selected_groq_model(), "openai/gpt-oss-120b")

        # 2. Reasoning text in additional_kwargs is NEVER treated as JSON payload
        fake_msg = MagicMock()
        fake_msg.content = ""
        fake_msg.additional_kwargs = {"reasoning_content": '{"day_number": 1, "title": "Should Ignore Reasoning", "activities": ["X"]}'}
        self.assertEqual(itinerary_editor._extract_llm_content(fake_msg), "")

        sample = _sample_itinerary_payload()
        orig_day2 = json.loads(json.dumps(sample["days"][1]))
        orig_brefs = json.loads(json.dumps(sample["booking_refs"]))

        # 3. Valid structured JSON response from ChatGroq succeeds and preserves other days & booking_refs
        valid_msg = MagicMock()
        valid_msg.content = json.dumps({
            "day_number": 1,
            "title": "Katra Calm Arrival & Banganga",
            "activities": [{"time": "10:00 AM", "duration": "2 hrs", "activity": "Banganga Darshan", "place": "Banganga Temple", "notes": ""}],
        })
        mock_llm_inst = MagicMock()
        mock_llm_inst.invoke.return_value = valid_msg

        with patch.dict(os.environ, {"GROQ_API_KEY": "test_key_only", "GROQ_MODEL": ""}), \
             patch("langchain_groq.ChatGroq", return_value=mock_llm_inst) as mock_cls:
            prev = itinerary_editor.preview_itinerary_edit(
                sample,
                {"operation": "regenerate_day", "day_number": 1, "instruction": "Relaxed Day 1", "use_ai": True, "require_ai": True},
            )
            self.assertEqual(prev["validation_source"], "groq_validated")
            self.assertEqual(prev["after"]["days"][0]["title"], "Katra Calm Arrival & Banganga")
            self.assertEqual(prev["after"]["days"][1], orig_day2)
            self.assertEqual(prev["after"]["booking_refs"], orig_brefs)
            # Confirm strict json_schema & >=2048 tokens passed to active default model
            call_kw = mock_cls.call_args.kwargs
            self.assertEqual(call_kw["model"], "openai/gpt-oss-20b")
            self.assertGreaterEqual(call_kw["max_tokens"], 2048)
            self.assertEqual(call_kw["model_kwargs"]["response_format"]["type"], "json_schema")

        # 4. Malformed JSON or missing required fields raises 422
        for bad_content in ("{not json", json.dumps({"day_number": 1, "title": "No Acts", "activities": []}), ""):
            bad_msg = MagicMock()
            bad_msg.content = bad_content
            mock_llm_inst.invoke.return_value = bad_msg
            with patch.dict(os.environ, {"GROQ_API_KEY": "test_key_only"}), \
                 patch("langchain_groq.ChatGroq", return_value=mock_llm_inst):
                with self.assertRaises(itinerary_editor.ItineraryEditValidationError) as ctx:
                    itinerary_editor.preview_itinerary_edit(
                        sample,
                        {"operation": "regenerate_day", "day_number": 1, "use_ai": True, "require_ai": True},
                    )
                self.assertEqual(ctx.exception.status_code, 422)

        # 5. Groq API error: require_ai=True MUST raise 503 (not fabricate AI success); require_ai=False uses deterministic fallback
        mock_err_inst = MagicMock()
        mock_err_inst.invoke.side_effect = RuntimeError("Groq 404/network error")
        with patch.dict(os.environ, {"GROQ_API_KEY": "test_key_only"}), \
             patch("langchain_groq.ChatGroq", return_value=mock_err_inst):
            with self.assertRaises(itinerary_editor.ItineraryEditValidationError) as ctx503:
                itinerary_editor.preview_itinerary_edit(
                    sample,
                    {"operation": "regenerate_day", "day_number": 1, "use_ai": True, "require_ai": True},
                )
            self.assertEqual(ctx503.exception.status_code, 503)

            det = itinerary_editor.preview_itinerary_edit(
                sample,
                {"operation": "regenerate_day", "day_number": 1, "instruction": "Relaxed Day 1", "use_ai": True, "require_ai": False},
            )
            self.assertEqual(det["validation_source"], "deterministic_grounded")
            self.assertEqual(det["after"]["days"][1], orig_day2)
            self.assertEqual(det["after"]["booking_refs"], orig_brefs)


if __name__ == "__main__":
    unittest.main()
