"""
agents/itinerary_collab_service.py

Phase 8.8.58 — Itinerary Persistence, Optimistic Concurrency, Undo History,
& Role-Based Group Collaboration Service (SQLite + MongoDB Dual-Store Parity).

Roles:
- OWNER  : Full read, edit, undo, delete, and share/invite management rights.
- EDITOR : Read, partial-edit preview/apply, undo; CANNOT delete or manage shares.
- VIEWER : Read-only sanitized access; CANNOT edit, undo, delete, or manage shares.
"""

import copy
import hashlib
import json
import logging
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.auth_service import auth_service
from agents.itinerary_editor import (
    ItineraryEditValidationError,
    extract_itinerary_summary_fields,
    normalize_itinerary_data,
    preview_itinerary_edit,
    sanitize_itinerary_data_for_member,
)
from utils.masking import mask_email

logger = logging.getLogger(__name__)

VALID_SHARE_ROLES = {"VIEWER", "EDITOR"}
VALID_MEMBER_ROLES = {"OWNER", "EDITOR", "VIEWER"}
MAX_EDIT_HISTORY = 25


class CollabServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class ItineraryNotFoundError(CollabServiceError):
    def __init__(self, message: str = "Itinerary not found."):
        super().__init__(message, status_code=404)


class ItineraryPermissionError(CollabServiceError):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(message, status_code=403)


class ItineraryConflictError(CollabServiceError):
    def __init__(
        self,
        message: str = "This itinerary was updated concurrently. Refresh and review latest changes before applying.",
        current_revision: Optional[int] = None,
    ):
        super().__init__(message, status_code=409)
        self.current_revision = current_revision


class ItineraryInviteError(CollabServiceError):
    def __init__(self, message: str = "Invalid or expired invitation token.", status_code: int = 403):
        super().__init__(message, status_code=status_code)


def hash_invite_token(raw_token: str) -> str:
    """Computes SHA-256 hex digest of a cryptographically random invite token."""
    return hashlib.sha256(str(raw_token or "").strip().encode("utf-8")).hexdigest()


def ensure_collab_sqlite_schema(db_path: str) -> None:
    """Idempotently upgrades SQLite schema with versioning and group collaboration tables."""
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        cursor = conn.cursor()
        # Ensure saved_itineraries has extended columns
        alter_stmts = [
            "ALTER TABLE saved_itineraries ADD COLUMN updated_at TEXT",
            "ALTER TABLE saved_itineraries ADD COLUMN revision INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE saved_itineraries ADD COLUMN source_key TEXT",
            "ALTER TABLE saved_itineraries ADD COLUMN edit_history_json TEXT",
        ]
        for stmt in alter_stmts:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itinerary_members (
                itinerary_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                added_by TEXT,
                created_at TEXT NOT NULL,
                revoked_at TEXT,
                PRIMARY KEY (itinerary_id, user_id)
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_itin_members_user ON itinerary_members (user_id, revoked_at);"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS itinerary_invites (
                invite_id TEXT PRIMARY KEY,
                itinerary_id TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                use_count INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_itin_invites_itin ON itinerary_invites (itinerary_id, revoked_at);"
        )
        conn.commit()


class ItineraryCollabService:
    """Service coordinating itinerary CRUD, partial edits, undo history, and sharing."""

    def _db_path(self) -> str:
        return auth_service.db_path

    def _is_mongo(self) -> bool:
        return auth_service.is_mongodb()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_schema(self) -> None:
        if not self._is_mongo():
            ensure_collab_sqlite_schema(self._db_path())

    def _lookup_masked_email(self, conn: Optional[sqlite3.Connection], user_id: str) -> str:
        email = ""
        if self._is_mongo():
            from agents import mongo_store
            doc = mongo_store.get_user_by_id(user_id)
            email = (doc or {}).get("email") or ""
        elif conn is not None:
            cur = conn.cursor()
            cur.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row and row[0]:
                email = row[0]
        return mask_email(email) if email else f"devotee-{str(user_id)[-6:]}"

    def _decorate_record(
        self,
        raw_record: Dict[str, Any],
        caller_user_id: str,
        my_role: str,
        member_count: int = 1,
        conn: Optional[sqlite3.Connection] = None,
        members_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        is_owner = my_role == "OWNER"
        raw_data = raw_record.get("data")
        title = (raw_record.get("title") or "Vaishno Devi Yatra Itinerary").strip()
        if is_owner:
            safe_data = normalize_itinerary_data(raw_data, title_fallback=title)
        else:
            safe_data = sanitize_itinerary_data_for_member(raw_data, is_owner=False)

        summary = extract_itinerary_summary_fields(safe_data, title=title)
        history = raw_record.get("edit_history") or []
        rev = int(raw_record.get("revision") or 1)
        created_at = raw_record.get("created_at") or self._now_iso()
        updated_at = raw_record.get("updated_at") or created_at

        sharing_status = "Private" if member_count <= 1 else f"Shared ({member_count})"
        out: Dict[str, Any] = {
            "itinerary_id": raw_record["itinerary_id"],
            "owner_user_id": raw_record.get("owner_user_id") if is_owner else None,
            "is_owner": is_owner,
            "my_role": my_role,
            "title": summary["title"],
            "destination": summary["destination"],
            "destinations": summary["destinations"],
            "start_date": summary["start_date"],
            "end_date": summary["end_date"],
            "duration_days": summary["duration_days"],
            "travellers_count": summary["travellers_count"],
            "created_at": created_at,
            "updated_at": updated_at,
            "revision": rev,
            "sharing_status": sharing_status,
            "member_count": member_count,
            "can_edit": my_role in ("OWNER", "EDITOR"),
            "can_delete": is_owner,
            "can_manage_shares": is_owner,
            "can_undo": bool(history) and (my_role in ("OWNER", "EDITOR")),
            "edit_history_count": len(history),
            "last_edit_summary": history[-1].get("summary") if history else None,
            "data": safe_data,
        }
        if members_list is not None:
            out["members"] = members_list
        return out

    # ------------------------------------------------------------------
    # CRUD & Deduplicated Upsert
    # ------------------------------------------------------------------

    def upsert_itinerary(
        self,
        user_id: str,
        title: str,
        itinerary_data: Any,
        itinerary_id: Optional[str] = None,
        source_key: Optional[str] = None,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Creates or updates an itinerary cleanly without duplicate records."""
        self._ensure_schema()
        now_iso = self._now_iso()
        norm_data = normalize_itinerary_data(itinerary_data, title_fallback=title)
        t_clean = (title or norm_data.get("title") or "Vaishno Devi Yatra Itinerary").strip()
        norm_data["title"] = t_clean
        s_key = (source_key or norm_data.get("source_session_id") or "").strip() or None

        if self._is_mongo():
            from agents import mongo_store
            rec, created = mongo_store.upsert_itinerary_collab(
                user_id=user_id,
                title=t_clean,
                now_iso=now_iso,
                data=norm_data,
                itinerary_id=itinerary_id,
                source_key=s_key,
                expected_revision=expected_revision,
            )
            role = rec.get("_caller_role", "OWNER")
            mcount = rec.get("_member_count", 1)
            members_safe = self._get_safe_members_mongo(rec["itinerary_id"], rec.get("owner_user_id"))
            return self._decorate_record(rec, user_id, role, member_count=mcount, members_list=members_safe)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            cursor = conn.cursor()
            existing = None

            # Check explicit itinerary_id first
            if itinerary_id and str(itinerary_id).strip():
                iid = str(itinerary_id).strip()
                cursor.execute(
                    "SELECT itinerary_id, user_id, title, created_at, updated_at, revision, data_json, edit_history_json "
                    "FROM saved_itineraries WHERE itinerary_id = ?",
                    (iid,),
                )
                row = cursor.fetchone()
                if row:
                    role = self._get_sqlite_role(cursor, iid, user_id, row[1])
                    if role not in ("OWNER", "EDITOR"):
                        raise ItineraryPermissionError("You do not have edit permission for this itinerary.")
                    existing = (row, role)

            # Fallback deduplication via source_key for same user
            if existing is None and s_key:
                cursor.execute(
                    "SELECT itinerary_id, user_id, title, created_at, updated_at, revision, data_json, edit_history_json "
                    "FROM saved_itineraries WHERE user_id = ? AND source_key = ? ORDER BY updated_at DESC LIMIT 1",
                    (user_id, s_key),
                )
                row = cursor.fetchone()
                if row:
                    existing = (row, "OWNER")

            if existing is not None:
                row, role = existing
                iid = row[0]
                old_title = row[2]
                created_at = row[3]
                cur_rev = int(row[5] or 1)
                old_data = json.loads(row[6]) if row[6] else {}
                history = json.loads(row[7]) if row[7] else []

                if role != "OWNER":
                    if expected_revision is None:
                        raise ItineraryEditValidationError(
                            "expected_revision is required when updating a shared itinerary.",
                            status_code=400,
                        )
                    if int(expected_revision) != cur_rev:
                        raise ItineraryConflictError(current_revision=cur_rev)
                    # Preserve owner's private booking_refs untouched on non-owner edits
                    old_bookings = old_data.get("booking_refs") if isinstance(old_data, dict) else []
                    norm_data["booking_refs"] = copy.deepcopy(old_bookings if isinstance(old_bookings, list) else [])
                elif expected_revision is not None and int(expected_revision) != cur_rev:
                    raise ItineraryConflictError(current_revision=cur_rev)

                history.append({
                    "revision": cur_rev,
                    "timestamp": now_iso,
                    "edited_by": user_id,
                    "summary": "Saved updated itinerary snapshot",
                    "title": old_title,
                    "data": old_data,
                })
                history = history[-MAX_EDIT_HISTORY:]
                new_rev = cur_rev + 1
                cursor.execute(
                    """
                    UPDATE saved_itineraries
                    SET title = ?, updated_at = ?, revision = ?, source_key = COALESCE(?, source_key),
                        data_json = ?, edit_history_json = ?
                    WHERE itinerary_id = ? AND (revision = ? OR revision IS NULL)
                    """,
                    (t_clean, now_iso, new_rev, s_key, json.dumps(norm_data), json.dumps(history), iid, cur_rev),
                )
                if cursor.rowcount == 0:
                    raise ItineraryConflictError(current_revision=cur_rev)
                conn.commit()
                mcount = self._get_sqlite_member_count(cursor, iid)
                members_safe = self._get_safe_members_sqlite(conn, iid, row[1])
                return self._decorate_record(
                    {
                        "itinerary_id": iid,
                        "owner_user_id": row[1],
                        "title": t_clean,
                        "created_at": created_at,
                        "updated_at": now_iso,
                        "revision": new_rev,
                        "edit_history": history,
                        "data": norm_data,
                    },
                    user_id,
                    role,
                    member_count=mcount,
                    conn=conn,
                    members_list=members_safe,
                )

            # Create new record + OWNER membership
            iid = (str(itinerary_id).strip() if itinerary_id and str(itinerary_id).strip() else f"itin_{uuid.uuid4().hex[:12]}")
            cursor.execute(
                """
                INSERT INTO saved_itineraries
                    (itinerary_id, user_id, title, created_at, updated_at, revision, source_key, data_json, edit_history_json)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, '[]')
                """,
                (iid, user_id, t_clean, now_iso, now_iso, s_key, json.dumps(norm_data)),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO itinerary_members (itinerary_id, user_id, role, added_by, created_at, revoked_at)
                VALUES (?, ?, 'OWNER', ?, ?, NULL)
                """,
                (iid, user_id, user_id, now_iso),
            )
            conn.commit()
            return self._decorate_record(
                {
                    "itinerary_id": iid,
                    "owner_user_id": user_id,
                    "title": t_clean,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "revision": 1,
                    "edit_history": [],
                    "data": norm_data,
                },
                user_id,
                "OWNER",
                member_count=1,
                conn=conn,
            )

    def _get_sqlite_role(
        self,
        cursor: sqlite3.Cursor,
        itinerary_id: str,
        user_id: str,
        owner_user_id: str,
    ) -> Optional[str]:
        if owner_user_id == user_id:
            return "OWNER"
        cursor.execute(
            "SELECT role, revoked_at FROM itinerary_members WHERE itinerary_id = ? AND user_id = ?",
            (itinerary_id, user_id),
        )
        m_row = cursor.fetchone()
        if not m_row or m_row[1] is not None:
            return None
        return m_row[0]

    def _get_sqlite_member_count(self, cursor: sqlite3.Cursor, itinerary_id: str) -> int:
        cursor.execute(
            "SELECT COUNT(*) FROM itinerary_members WHERE itinerary_id = ? AND revoked_at IS NULL",
            (itinerary_id,),
        )
        c = cursor.fetchone()
        return max(1, int(c[0]) if c and c[0] else 1)

    def list_itineraries_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists all owned + actively shared itineraries for `user_id`."""
        self._ensure_schema()

        if self._is_mongo():
            from agents import mongo_store
            rows = mongo_store.list_itineraries_for_user(user_id)
            return [
                self._decorate_record(r, user_id, r.get("_caller_role", "VIEWER"), member_count=r.get("_member_count", 1))
                for r in rows
            ]

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT s.itinerary_id, s.user_id, s.title, s.created_at,
                       COALESCE(s.updated_at, s.created_at) AS upd,
                       COALESCE(s.revision, 1) AS rev,
                       s.data_json, s.edit_history_json,
                       CASE WHEN s.user_id = ? THEN 'OWNER' ELSE m.role END AS caller_role
                FROM saved_itineraries s
                LEFT JOIN itinerary_members m
                  ON s.itinerary_id = m.itinerary_id
                 AND m.user_id = ?
                 AND m.revoked_at IS NULL
                WHERE s.user_id = ? OR m.user_id IS NOT NULL
                ORDER BY upd DESC, s.created_at DESC
                """,
                (user_id, user_id, user_id),
            )
            rows = cursor.fetchall()
            out: List[Dict[str, Any]] = []
            for r in rows:
                iid = r[0]
                mcount = self._get_sqlite_member_count(cursor, iid)
                rec = {
                    "itinerary_id": iid,
                    "owner_user_id": r[1],
                    "title": r[2],
                    "created_at": r[3],
                    "updated_at": r[4],
                    "revision": r[5],
                    "data": json.loads(r[6]) if r[6] else {},
                    "edit_history": json.loads(r[7]) if r[7] else [],
                }
                out.append(self._decorate_record(rec, user_id, r[8], member_count=mcount, conn=conn))
            return out

    def _load_authorized_sqlite_raw(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        itinerary_id: str,
        required_roles: Tuple[str, ...] = ("OWNER", "EDITOR", "VIEWER"),
    ) -> Tuple[Dict[str, Any], str, int]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT itinerary_id, user_id, title, created_at,
                   COALESCE(updated_at, created_at), COALESCE(revision, 1),
                   data_json, edit_history_json
            FROM saved_itineraries
            WHERE itinerary_id = ?
            """,
            (itinerary_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ItineraryNotFoundError()

        role = self._get_sqlite_role(cursor, itinerary_id, user_id, row[1])
        if role is None:
            raise ItineraryPermissionError("Access denied: you are not a member of this itinerary.")
        if role not in required_roles:
            raise ItineraryPermissionError(f"Role '{role}' cannot perform this action.")

        mcount = self._get_sqlite_member_count(cursor, itinerary_id)
        rec = {
            "itinerary_id": row[0],
            "owner_user_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "revision": int(row[5] or 1),
            "data": json.loads(row[6]) if row[6] else {},
            "edit_history": json.loads(row[7]) if row[7] else [],
        }
        return rec, role, mcount

    def _get_safe_members_mongo(self, itinerary_id: str, owner_user_id: Optional[str]) -> List[Dict[str, Any]]:
        from agents import mongo_store
        shares = mongo_store.list_itinerary_shares(itinerary_id, owner_user_id or "")
        members = shares.get("members") or []
        for m in members:
            m["masked_email"] = self._lookup_masked_email(None, m["user_id"])
        return members

    def get_itinerary_for_user(self, user_id: str, itinerary_id: str) -> Dict[str, Any]:
        """Retrieves single itinerary for an authorized member (privacy-sanitized if non-owner)."""
        self._ensure_schema()

        if self._is_mongo():
            from agents import mongo_store
            rec, role, mcount = mongo_store.get_itinerary_collab(user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if role is None:
                raise ItineraryPermissionError("Access denied: you are not a member of this itinerary.")
            members_safe = self._get_safe_members_mongo(itinerary_id, rec.get("owner_user_id"))
            return self._decorate_record(rec, user_id, role, member_count=mcount, members_list=members_safe)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, role, mcount = self._load_authorized_sqlite_raw(conn, user_id, itinerary_id)
            members_safe = self._get_safe_members_sqlite(conn, itinerary_id, rec["owner_user_id"])
            return self._decorate_record(rec, user_id, role, member_count=mcount, conn=conn, members_list=members_safe)

    def delete_itinerary(self, user_id: str, itinerary_id: str) -> bool:
        """Deletes itinerary strictly if caller is OWNER."""
        self._ensure_schema()

        if self._is_mongo():
            from agents import mongo_store
            rec, role, _ = mongo_store.get_itinerary_collab(user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if role != "OWNER":
                raise ItineraryPermissionError("Only the itinerary owner can delete this itinerary.")
            return mongo_store.delete_itinerary_collab(user_id, itinerary_id)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            self._load_authorized_sqlite_raw(conn, user_id, itinerary_id, required_roles=("OWNER",))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM itinerary_invites WHERE itinerary_id = ?", (itinerary_id,))
            cursor.execute("DELETE FROM itinerary_members WHERE itinerary_id = ?", (itinerary_id,))
            cursor.execute("DELETE FROM saved_itineraries WHERE itinerary_id = ? AND user_id = ?", (itinerary_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Partial Edit Preview, Apply, & Undo
    # ------------------------------------------------------------------

    def preview_edit(
        self,
        user_id: str,
        itinerary_id: str,
        edit_payload: Dict[str, Any],
        llm_caller: Optional[Callable[[Dict[str, Any], Dict[str, Any], str], Any]] = None,
    ) -> Dict[str, Any]:
        """Computes before/after diff preview without saving (OWNER or EDITOR only)."""
        self._ensure_schema()

        if self._is_mongo():
            from agents import mongo_store
            rec, role, _ = mongo_store.get_itinerary_collab(user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if role not in ("OWNER", "EDITOR"):
                raise ItineraryPermissionError("Viewers cannot edit this itinerary.")
        else:
            with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
                rec, role, _ = self._load_authorized_sqlite_raw(conn, user_id, itinerary_id, required_roles=("OWNER", "EDITOR"))

        is_owner = role == "OWNER"
        base_data = rec["data"] if is_owner else sanitize_itinerary_data_for_member(rec["data"], is_owner=False)
        preview = preview_itinerary_edit(base_data, edit_payload, llm_caller=llm_caller)
        if not is_owner:
            preview["before"] = sanitize_itinerary_data_for_member(preview["before"], is_owner=False)
            preview["after"] = sanitize_itinerary_data_for_member(preview["after"], is_owner=False)

        preview["itinerary_id"] = itinerary_id
        preview["expected_revision"] = int(rec.get("revision") or 1)
        preview["my_role"] = role
        return preview

    def apply_edit(
        self,
        user_id: str,
        itinerary_id: str,
        edit_payload: Dict[str, Any],
        expected_revision: Optional[int] = None,
        llm_caller: Optional[Callable[[Dict[str, Any], Dict[str, Any], str], Any]] = None,
    ) -> Dict[str, Any]:
        """Validates, checks optimistic concurrency revision, saves new version, pushes Undo history."""
        self._ensure_schema()
        now_iso = self._now_iso()

        if self._is_mongo():
            from agents import mongo_store
            rec, role, mcount = mongo_store.get_itinerary_collab(user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if role not in ("OWNER", "EDITOR"):
                raise ItineraryPermissionError("Viewers cannot edit this itinerary.")
            cur_rev = int(rec.get("revision") or 1)
            if expected_revision is not None and int(expected_revision) != cur_rev:
                raise ItineraryConflictError(current_revision=cur_rev)

            preview = preview_itinerary_edit(rec["data"], edit_payload, llm_caller=llm_caller)
            if preview["requires_confirmation"] and not edit_payload.get("confirm_impact"):
                raise ItineraryEditValidationError(
                    preview.get("impact_warning") or "Please confirm the impact before applying this edit.",
                    status_code=422,
                    details={"requires_confirmation": True, "affected_days": preview["affected_days"]},
                )

            new_data = preview["after"]
            # Preserve owner's private booking_refs untouched if edited by non-owner!
            if role != "OWNER" and isinstance(rec["data"], dict) and "booking_refs" in rec["data"]:
                new_data["booking_refs"] = copy.deepcopy(rec["data"].get("booking_refs") or [])

            updated = mongo_store.commit_itinerary_edit_collab(
                itinerary_id=itinerary_id,
                expected_revision=cur_rev,
                new_title=new_data.get("title") or rec["title"],
                new_data=new_data,
                edited_by=user_id,
                now_iso=now_iso,
                diff_summary="; ".join(preview["diff_summary"]),
                old_snapshot={"revision": cur_rev, "timestamp": now_iso, "edited_by": user_id, "summary": "; ".join(preview["diff_summary"]), "title": rec["title"], "data": rec["data"]},
            )
            if updated is None:
                raise ItineraryConflictError()
            members_safe = self._get_safe_members_mongo(itinerary_id, rec.get("owner_user_id"))
            decorated = self._decorate_record(updated, user_id, role, member_count=mcount, members_list=members_safe)
            decorated["diff_summary"] = preview["diff_summary"]
            return decorated

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, role, mcount = self._load_authorized_sqlite_raw(conn, user_id, itinerary_id, required_roles=("OWNER", "EDITOR"))
            cur_rev = int(rec["revision"] or 1)
            if expected_revision is not None and int(expected_revision) != cur_rev:
                raise ItineraryConflictError(current_revision=cur_rev)

            preview = preview_itinerary_edit(rec["data"], edit_payload, llm_caller=llm_caller)
            if preview["requires_confirmation"] and not edit_payload.get("confirm_impact"):
                raise ItineraryEditValidationError(
                    preview.get("impact_warning") or "Please confirm the impact before applying this edit.",
                    status_code=422,
                    details={"requires_confirmation": True, "affected_days": preview["affected_days"]},
                )

            new_data = preview["after"]
            if role != "OWNER" and isinstance(rec["data"], dict) and "booking_refs" in rec["data"]:
                new_data["booking_refs"] = copy.deepcopy(rec["data"].get("booking_refs") or [])

            history = list(rec.get("edit_history") or [])
            summary_line = "; ".join(preview["diff_summary"]) or f"Edited revision {cur_rev}"
            history.append({
                "revision": cur_rev,
                "timestamp": now_iso,
                "edited_by": user_id,
                "summary": summary_line,
                "title": rec["title"],
                "data": rec["data"],
            })
            history = history[-MAX_EDIT_HISTORY:]
            new_rev = cur_rev + 1
            new_title = new_data.get("title") or rec["title"]

            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE saved_itineraries
                SET title = ?, updated_at = ?, revision = ?, data_json = ?, edit_history_json = ?
                WHERE itinerary_id = ? AND revision = ?
                """,
                (new_title, now_iso, new_rev, json.dumps(new_data), json.dumps(history), itinerary_id, cur_rev),
            )
            if cursor.rowcount == 0:
                raise ItineraryConflictError(current_revision=cur_rev)
            conn.commit()

            updated_rec = {
                "itinerary_id": itinerary_id,
                "owner_user_id": rec["owner_user_id"],
                "title": new_title,
                "created_at": rec["created_at"],
                "updated_at": now_iso,
                "revision": new_rev,
                "edit_history": history,
                "data": new_data,
            }
            members_safe = self._get_safe_members_sqlite(conn, itinerary_id, rec["owner_user_id"])
            decorated = self._decorate_record(updated_rec, user_id, role, member_count=mcount, conn=conn, members_list=members_safe)
            decorated["diff_summary"] = preview["diff_summary"]
            return decorated

    def undo_last_edit(
        self,
        user_id: str,
        itinerary_id: str,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Reverts itinerary to the most recent snapshot stored in edit_history."""
        self._ensure_schema()
        now_iso = self._now_iso()

        if self._is_mongo():
            from agents import mongo_store
            rec, role, mcount = mongo_store.get_itinerary_collab(user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if role not in ("OWNER", "EDITOR"):
                raise ItineraryPermissionError("Viewers cannot revert edits.")
            cur_rev = int(rec.get("revision") or 1)
            if expected_revision is not None and int(expected_revision) != cur_rev:
                raise ItineraryConflictError(current_revision=cur_rev)
            history = list(rec.get("edit_history") or [])
            if not history:
                raise ItineraryEditValidationError("No previous edits available to undo.", status_code=400)
            prev_snap = history.pop()
            updated = mongo_store.commit_undo_itinerary_collab(
                itinerary_id=itinerary_id,
                expected_revision=cur_rev,
                restored_title=prev_snap.get("title") or rec["title"],
                restored_data=prev_snap.get("data"),
                remaining_history=history,
                now_iso=now_iso,
            )
            if updated is None:
                raise ItineraryConflictError()
            members_safe = self._get_safe_members_mongo(itinerary_id, rec.get("owner_user_id"))
            decorated = self._decorate_record(updated, user_id, role, member_count=mcount, members_list=members_safe)
            decorated["reverted_from_revision"] = cur_rev
            decorated["restored_revision_snapshot"] = prev_snap.get("revision")
            return decorated

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, role, mcount = self._load_authorized_sqlite_raw(conn, user_id, itinerary_id, required_roles=("OWNER", "EDITOR"))
            cur_rev = int(rec["revision"] or 1)
            if expected_revision is not None and int(expected_revision) != cur_rev:
                raise ItineraryConflictError(current_revision=cur_rev)
            history = list(rec.get("edit_history") or [])
            if not history:
                raise ItineraryEditValidationError("No previous edits available to undo.", status_code=400)

            prev_snap = history.pop()
            restored_data = prev_snap.get("data") or rec["data"]
            restored_title = prev_snap.get("title") or rec["title"]
            new_rev = cur_rev + 1

            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE saved_itineraries
                SET title = ?, updated_at = ?, revision = ?, data_json = ?, edit_history_json = ?
                WHERE itinerary_id = ? AND revision = ?
                """,
                (restored_title, now_iso, new_rev, json.dumps(restored_data), json.dumps(history), itinerary_id, cur_rev),
            )
            if cursor.rowcount == 0:
                raise ItineraryConflictError(current_revision=cur_rev)
            conn.commit()

            updated_rec = {
                "itinerary_id": itinerary_id,
                "owner_user_id": rec["owner_user_id"],
                "title": restored_title,
                "created_at": rec["created_at"],
                "updated_at": now_iso,
                "revision": new_rev,
                "edit_history": history,
                "data": restored_data,
            }
            members_safe = self._get_safe_members_sqlite(conn, itinerary_id, rec["owner_user_id"])
            decorated = self._decorate_record(updated_rec, user_id, role, member_count=mcount, conn=conn, members_list=members_safe)
            decorated["reverted_from_revision"] = cur_rev
            decorated["restored_revision_snapshot"] = prev_snap.get("revision")
            return decorated

    # ------------------------------------------------------------------
    # Group Trip Sharing, Invitations, Roles & Immediate Revocation
    # ------------------------------------------------------------------

    def _get_safe_members_sqlite(
        self, conn: sqlite3.Connection, itinerary_id: str, owner_user_id: str
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, role, created_at
            FROM itinerary_members
            WHERE itinerary_id = ? AND revoked_at IS NULL
            ORDER BY CASE WHEN role = 'OWNER' THEN 0 WHEN role = 'EDITOR' THEN 1 ELSE 2 END, created_at ASC
            """,
            (itinerary_id,),
        )
        rows = cursor.fetchall()
        members: List[Dict[str, Any]] = []
        seen = set()
        for uid, role, created_at in rows:
            seen.add(uid)
            members.append({
                "user_id": uid,
                "role": role,
                "masked_email": self._lookup_masked_email(conn, uid),
                "added_at": created_at,
            })
        if owner_user_id and owner_user_id not in seen:
            members.insert(0, {
                "user_id": owner_user_id,
                "role": "OWNER",
                "masked_email": self._lookup_masked_email(conn, owner_user_id),
                "added_at": None,
            })
        return members

    def create_invite(
        self,
        owner_user_id: str,
        itinerary_id: str,
        role: str = "VIEWER",
        expires_in_hours: int = 72,
    ) -> Dict[str, Any]:
        """Generates a cryptographically random invite token and stores only its SHA-256 hash."""
        self._ensure_schema()
        role_upper = str(role or "VIEWER").strip().upper()
        if role_upper not in VALID_SHARE_ROLES:
            raise CollabServiceError("Invite role must be VIEWER or EDITOR.", status_code=400)

        try:
            hours = int(expires_in_hours)
        except Exception:
            hours = 72
        if hours < 1 or hours > 720:
            raise CollabServiceError("expires_in_hours must be between 1 and 720.", status_code=400)

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(hours=hours)).isoformat()
        invite_id = f"inv_{uuid.uuid4().hex[:12]}"
        raw_token = secrets.token_urlsafe(32)
        t_hash = hash_invite_token(raw_token)

        if self._is_mongo():
            from agents import mongo_store
            rec, caller_role, _ = mongo_store.get_itinerary_collab(owner_user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if caller_role != "OWNER":
                raise ItineraryPermissionError("Only the owner can create share invitations.")
            mongo_store.create_itinerary_invite(
                invite_id=invite_id,
                itinerary_id=itinerary_id,
                token_hash=t_hash,
                role=role_upper,
                created_by=owner_user_id,
                created_at=now_iso,
                expires_at=expires_iso,
            )
            return {
                "invite_id": invite_id,
                "itinerary_id": itinerary_id,
                "role": role_upper,
                "invite_token": raw_token,
                "expires_at": expires_iso,
                "created_at": now_iso,
            }

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            self._load_authorized_sqlite_raw(conn, owner_user_id, itinerary_id, required_roles=("OWNER",))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO itinerary_invites
                    (invite_id, itinerary_id, token_hash, role, created_by, created_at, expires_at, revoked_at, use_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0)
                """,
                (invite_id, itinerary_id, t_hash, role_upper, owner_user_id, now_iso, expires_iso),
            )
            conn.commit()

        return {
            "invite_id": invite_id,
            "itinerary_id": itinerary_id,
            "role": role_upper,
            "invite_token": raw_token,
            "expires_at": expires_iso,
            "created_at": now_iso,
        }

    def list_shares(self, owner_user_id: str, itinerary_id: str) -> Dict[str, Any]:
        """Lists active collaborators and active invites (OWNER ONLY; never leaks raw/hashed tokens)."""
        self._ensure_schema()

        if self._is_mongo():
            from agents import mongo_store
            rec, caller_role, _ = mongo_store.get_itinerary_collab(owner_user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if caller_role != "OWNER":
                raise ItineraryPermissionError("Only the owner can manage sharing and permissions.")
            shares = mongo_store.list_itinerary_shares(itinerary_id, rec["owner_user_id"])
            for m in shares["members"]:
                m["masked_email"] = self._lookup_masked_email(None, m["user_id"])
            return shares

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, _, _ = self._load_authorized_sqlite_raw(conn, owner_user_id, itinerary_id, required_roles=("OWNER",))
            members = self._get_safe_members_sqlite(conn, itinerary_id, rec["owner_user_id"])
            cursor = conn.cursor()
            now_iso = self._now_iso()
            cursor.execute(
                """
                SELECT invite_id, role, created_at, expires_at, revoked_at, use_count
                FROM itinerary_invites
                WHERE itinerary_id = ?
                ORDER BY created_at DESC
                """,
                (itinerary_id,),
            )
            invites = []
            for iid, role, created_at, expires_at, revoked_at, use_count in cursor.fetchall():
                status = "REVOKED" if revoked_at else ("EXPIRED" if expires_at <= now_iso else "ACTIVE")
                invites.append({
                    "invite_id": iid,
                    "role": role,
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "revoked_at": revoked_at,
                    "use_count": int(use_count or 0),
                    "status": status,
                })
            return {"itinerary_id": itinerary_id, "members": members, "invites": invites}

    def update_member_role(
        self,
        owner_user_id: str,
        itinerary_id: str,
        target_user_id: str,
        new_role: str,
    ) -> Dict[str, Any]:
        """Updates an existing collaborator's role between VIEWER and EDITOR (OWNER ONLY)."""
        self._ensure_schema()
        role_upper = str(new_role or "").strip().upper()
        if role_upper not in VALID_SHARE_ROLES:
            raise CollabServiceError("Target role must be VIEWER or EDITOR.", status_code=400)
        if target_user_id == owner_user_id:
            raise CollabServiceError("Owner role cannot be downgraded.", status_code=400)

        if self._is_mongo():
            from agents import mongo_store
            rec, caller_role, _ = mongo_store.get_itinerary_collab(owner_user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if caller_role != "OWNER":
                raise ItineraryPermissionError("Only the owner can update collaborator roles.")
            ok = mongo_store.update_itinerary_member_role(itinerary_id, target_user_id, role_upper)
            if not ok:
                raise ItineraryNotFoundError("Collaborator not found.")
            return {"itinerary_id": itinerary_id, "user_id": target_user_id, "role": role_upper}

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, _, _ = self._load_authorized_sqlite_raw(conn, owner_user_id, itinerary_id, required_roles=("OWNER",))
            if target_user_id == rec["owner_user_id"]:
                raise CollabServiceError("Owner role cannot be modified.", status_code=400)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE itinerary_members SET role = ?
                WHERE itinerary_id = ? AND user_id = ? AND revoked_at IS NULL
                """,
                (role_upper, itinerary_id, target_user_id),
            )
            if cursor.rowcount == 0:
                raise ItineraryNotFoundError("Active collaborator not found.")
            conn.commit()
            return {"itinerary_id": itinerary_id, "user_id": target_user_id, "role": role_upper}

    def revoke_member(self, owner_user_id: str, itinerary_id: str, target_user_id: str) -> bool:
        """Immediately revokes a collaborator's access (OWNER ONLY)."""
        self._ensure_schema()
        if target_user_id == owner_user_id:
            raise CollabServiceError("Owner cannot revoke their own ownership.", status_code=400)
        now_iso = self._now_iso()

        if self._is_mongo():
            from agents import mongo_store
            rec, caller_role, _ = mongo_store.get_itinerary_collab(owner_user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if caller_role != "OWNER":
                raise ItineraryPermissionError("Only the owner can revoke collaborators.")
            return mongo_store.revoke_itinerary_member(itinerary_id, target_user_id, now_iso)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            rec, _, _ = self._load_authorized_sqlite_raw(conn, owner_user_id, itinerary_id, required_roles=("OWNER",))
            if target_user_id == rec["owner_user_id"]:
                raise CollabServiceError("Owner cannot revoke ownership.", status_code=400)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE itinerary_members SET revoked_at = ? WHERE itinerary_id = ? AND user_id = ?",
                (now_iso, itinerary_id, target_user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def revoke_invite(self, owner_user_id: str, itinerary_id: str, invite_id: str) -> bool:
        """Immediately revokes an outstanding invitation link (OWNER ONLY)."""
        self._ensure_schema()
        now_iso = self._now_iso()

        if self._is_mongo():
            from agents import mongo_store
            rec, caller_role, _ = mongo_store.get_itinerary_collab(owner_user_id, itinerary_id)
            if rec is None:
                raise ItineraryNotFoundError()
            if caller_role != "OWNER":
                raise ItineraryPermissionError("Only the owner can revoke invitations.")
            return mongo_store.revoke_itinerary_invite(itinerary_id, invite_id, now_iso)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            self._load_authorized_sqlite_raw(conn, owner_user_id, itinerary_id, required_roles=("OWNER",))
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE itinerary_invites SET revoked_at = ? WHERE itinerary_id = ? AND invite_id = ?",
                (now_iso, itinerary_id, invite_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def accept_invite(self, user_id: str, raw_token: str) -> Dict[str, Any]:
        """
        Accepts a cryptographic invitation token on behalf of an authenticated user.
        Rejects missing, revoked, or expired tokens without exposing itinerary metadata.
        """
        self._ensure_schema()
        token_clean = str(raw_token or "").strip()
        if not token_clean:
            raise ItineraryInviteError("Invalid invitation token.", status_code=403)
        t_hash = hash_invite_token(token_clean)
        now_iso = self._now_iso()

        if self._is_mongo():
            from agents import mongo_store
            itinerary_id = mongo_store.accept_itinerary_invite(user_id, t_hash, now_iso)
            return self.get_itinerary_for_user(user_id, itinerary_id)

        with sqlite3.connect(self._db_path(), timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT invite_id, itinerary_id, role, created_by, expires_at, revoked_at
                FROM itinerary_invites
                WHERE token_hash = ?
                """,
                (t_hash,),
            )
            row = cursor.fetchone()
            if not row:
                raise ItineraryInviteError("Invitation token is invalid or unrecognized.", status_code=403)

            invite_id, itinerary_id, role, created_by, expires_at, revoked_at = row
            if revoked_at is not None:
                raise ItineraryInviteError("This invitation link has been revoked.", status_code=410)
            if str(expires_at) <= now_iso:
                raise ItineraryInviteError("This invitation link has expired.", status_code=410)

            cursor.execute("SELECT user_id FROM saved_itineraries WHERE itinerary_id = ?", (itinerary_id,))
            itin_row = cursor.fetchone()
            if not itin_row:
                raise ItineraryInviteError("Invitation target no longer exists.", status_code=404)

            owner_uid = itin_row[0]
            if user_id != owner_uid:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO itinerary_members
                        (itinerary_id, user_id, role, added_by, created_at, revoked_at)
                    VALUES (?, ?, ?, ?, ?, NULL)
                    """,
                    (itinerary_id, user_id, role, created_by, now_iso),
                )
            cursor.execute(
                "UPDATE itinerary_invites SET use_count = use_count + 1 WHERE invite_id = ?",
                (invite_id,),
            )
            conn.commit()

        return self.get_itinerary_for_user(user_id, itinerary_id)


itinerary_collab_service = ItineraryCollabService()
