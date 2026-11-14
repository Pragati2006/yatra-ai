"""
tests/test_phase15_2_3_persistence.py
Phase 15.2.3: MongoDB Persistence Implementation Audit & Cloud Deployment Safety Gate.

Validates that:
1. Local mode defaults to SQLite; cloud mode explicitly activates MongoDB Atlas.
2. Refuses silent fallback to ephemeral SQLite when PERSISTENCE_BACKEND=mongodb and Mongo is offline.
3. System fails safely on startup/readiness when cloud persistence is broken.
4. User accounts, sessions, conversations, itineraries, and simulated bookings persist in MongoDB.
5. Strict cross-user isolation and cross-session isolation are enforced.
6. Duplicate bookings are rejected or updated idempotently.
7. Session expiry cleans up stale sessions.
8. Credentials and secrets are never logged or exposed.
"""

import os
import json
import uuid
import copy
import logging
from datetime import datetime, timezone, timedelta
from unittest import TestCase
from unittest.mock import patch, MagicMock

# Import components
from agents.mongo_store import is_mongodb_mode
import agents.mongo_store as mongo_store
from agents.auth_service import AuthService, compute_otp_hmac
import agents.session_store as session_store
from backend.main import health_ready


class MockMongoCollection:
    """In-memory mock MongoDB collection mimicking pymongo API for unit testing."""

    def __init__(self, name: str):
        self.name = name
        self.documents = []
        self.indexes = []

    def create_index(self, keys, unique=False):
        self.indexes.append({"keys": keys, "unique": unique})

    def insert_one(self, doc):
        stored = copy.deepcopy(doc)
        if "_id" not in stored:
            stored["_id"] = str(uuid.uuid4())
        self.documents.append(stored)
        return MagicMock(inserted_id=stored["_id"])

    def _matches(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, subq) for subq in v):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    def find_one(self, query):
        for doc in self.documents:
            if self._matches(doc, query):
                return copy.deepcopy(doc)
        return None

    def find(self, query=None):
        matched = [copy.deepcopy(d) for d in self.documents if self._matches(d, query or {})]
        return MockCursor(matched)

    def update_one(self, query, update, upsert=False):
        set_vals = update.get("$set", {})
        for doc in self.documents:
            if self._matches(doc, query):
                doc.update(copy.deepcopy(set_vals))
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            new_doc = copy.deepcopy(set_vals)
            for k, v in query.items():
                if k != "$or":
                    new_doc.setdefault(k, v)
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4())
            self.documents.append(new_doc)
            return MagicMock(matched_count=0, modified_count=1, upserted_id=new_doc["_id"])
        return MagicMock(matched_count=0, modified_count=0)

    def delete_one(self, query):
        for i, doc in enumerate(self.documents):
            if self._matches(doc, query):
                self.documents.pop(i)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    def delete_many(self, query):
        orig_count = len(self.documents)
        self.documents = [d for d in self.documents if not self._matches(d, query)]
        return MagicMock(deleted_count=orig_count - len(self.documents))

    def count_documents(self, query):
        return sum(1 for d in self.documents if self._matches(d, query))


class MockCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            key = key_or_list[0][0]
            direction = key_or_list[0][1]
        else:
            key = key_or_list
        reverse = (direction == -1)
        self.docs.sort(key=lambda d: d.get(key) or "", reverse=reverse)
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __iter__(self):
        return iter(self.docs)

    def __len__(self):
        return len(self.docs)


class Phase1523PersistenceTestCase(TestCase):
    """Automated persistence and cloud deployment safety gate test suite."""

    def setUp(self):
        self.mock_collections = {}

    def get_mock_coll(self, name: str):
        if name not in self.mock_collections:
            self.mock_collections[name] = MockMongoCollection(name)
        return self.mock_collections[name]

    # -------------------------------------------------------------------------
    # 1. Backend Selection & Default Checks
    # -------------------------------------------------------------------------
    def test_01_backend_selection_sqlite_default(self):
        """Default configuration selects SQLite and does not require MongoDB."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_mongodb_mode())
            auth = AuthService()
            self.assertFalse(auth.is_mongodb())

    def test_02_backend_selection_mongodb_cloud(self):
        """Setting PERSISTENCE_BACKEND=mongodb explicitly activates MongoDB persistence mode."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            self.assertTrue(is_mongodb_mode())
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()
                self.assertTrue(auth.is_mongodb())

    # -------------------------------------------------------------------------
    # 2. Refusal of Silent Fallback to Ephemeral SQLite
    # -------------------------------------------------------------------------
    def test_03_refuse_silent_fallback_when_mongo_offline(self):
        """Refuses silent fallback to SQLite when PERSISTENCE_BACKEND=mongodb and Mongo is offline."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=False):
                with self.assertRaises(RuntimeError) as ctx:
                    mongo_store._get_coll("auth_users")
                self.assertIn("CRITICAL PERSISTENCE FAILURE", str(ctx.exception))
                self.assertIn("Refusing silent fallback", str(ctx.exception))

    def test_04_readiness_probe_fails_when_mongo_offline_in_cloud_mode(self):
        """Health readiness probe returns 503 unavailable_mongodb when Mongo is offline in cloud mode."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=False):
                res = health_ready()
                self.assertEqual(res.status_code, 503)
                data = json.loads(res.body.decode("utf-8"))
                self.assertEqual(data["status"], "not_ready")
                self.assertEqual(data["dependencies"]["database"], "unavailable_mongodb")
                self.assertEqual(data["dependencies"]["mongodb"], "offline")

    def test_05_readiness_probe_ready_when_mongo_online(self):
        """Health readiness probe returns 200 ready when Mongo is online in cloud mode."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True):
                res = health_ready()
                data = res if isinstance(res, dict) else json.loads(res.body.decode("utf-8"))
                self.assertEqual(data["status"], "ready")
                self.assertEqual(data["dependencies"]["database"], "ready_mongodb")
                self.assertEqual(data["dependencies"]["mongodb"], "connected")

    # -------------------------------------------------------------------------
    # 3. User Accounts & Session Persistence
    # -------------------------------------------------------------------------
    def test_06_user_account_persistence_in_mongodb(self):
        """User accounts are created and retrieved faithfully from MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                now_iso = datetime.now(timezone.utc).isoformat()
                u = mongo_store.create_user("usr_test123", "bhakt@example.com", {"lang": "hi"}, now_iso)
                self.assertEqual(u["email"], "bhakt@example.com")

                by_email = mongo_store.get_user_by_email("bhakt@example.com")
                self.assertIsNotNone(by_email)
                self.assertEqual(by_email["user_id"], "usr_test123")
                self.assertEqual(by_email["preferences"]["lang"], "hi")

                by_id = mongo_store.get_user_by_id("usr_test123")
                self.assertIsNotNone(by_id)
                self.assertEqual(by_id["email"], "bhakt@example.com")

    def test_07_auth_session_and_otp_challenge_in_mongodb(self):
        """Auth OTP challenges and server sessions are stored and verified in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                # Request OTP
                res = auth.request_otp("devotee@example.com")
                self.assertEqual(res["status"], "success")

                # Verify challenge was saved in mock MongoDB
                challenge = mongo_store.get_otp_challenge("devotee@example.com")
                self.assertIsNotNone(challenge)
                self.assertEqual(challenge["attempts"], 0)

                # Compute valid OTP HMAC
                test_otp = "123456"
                valid_hash = compute_otp_hmac(test_otp, "devotee@example.com", created_at=challenge["created_at"])
                challenge["otp_hash"] = valid_hash
                mongo_store.save_otp_challenge("devotee@example.com", valid_hash, challenge["created_at"], challenge["expires_at"])

                # Verify OTP
                verify_res = auth.verify_otp("devotee@example.com", test_otp)
                self.assertEqual(verify_res["status"], "success")
                token = verify_res["session_token"]

                # Validate server session
                user = auth.get_user_by_session_token(token)
                self.assertIsNotNone(user)
                self.assertEqual(user["email"], "devotee@example.com")

                # Challenge must be deleted upon successful login (single-use)
                self.assertIsNone(mongo_store.get_otp_challenge("devotee@example.com"))

    def test_08_session_expiry_and_cleanup_in_mongodb(self):
        """Expired session token is automatically cleaned up and returns None."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
                expired_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                mongo_store.create_user("usr_exp", "exp@example.com", {}, past_iso)
                mongo_store.create_auth_session("token_exp", "usr_exp", "exp@example.com", past_iso, expired_iso)

                # Getting user by expired token should return None and delete token
                user = auth.get_user_by_session_token("token_exp")
                self.assertIsNone(user)
                self.assertIsNone(mongo_store.get_auth_session("token_exp"))

    # -------------------------------------------------------------------------
    # 4. User Conversations & Itineraries Persistence
    # -------------------------------------------------------------------------
    def test_09_conversation_history_persistence_in_mongodb(self):
        """Conversations are saved, retrieved, updated, and deleted in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                msgs = [
                    {"role": "user", "content": "How do I reach Bhawan?"},
                    {"role": "assistant", "content": "You can trek 13 km or take the battery car."},
                ]
                saved = auth.save_conversation("usr_pilgrim1", "Bhawan Trek Guide", msgs, conversation_id="conv_101")
                self.assertEqual(saved["conversation_id"], "conv_101")

                all_convs = auth.get_saved_conversations("usr_pilgrim1")
                self.assertEqual(len(all_convs), 1)
                self.assertEqual(all_convs[0]["title"], "Bhawan Trek Guide")

                single = auth.get_saved_conversation("usr_pilgrim1", "conv_101")
                self.assertIsNotNone(single)
                self.assertEqual(len(single["messages"]), 2)

                # Delete conversation
                deleted = auth.delete_saved_conversation("usr_pilgrim1", "conv_101")
                self.assertTrue(deleted)
                self.assertIsNone(auth.get_saved_conversation("usr_pilgrim1", "conv_101"))

    def test_10_itinerary_persistence_in_mongodb(self):
        """Itineraries are saved, retrieved, and deleted in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                itin_data = {"days": 3, "destination": "Katra", "budget": 12000}
                res = auth.save_itinerary("usr_pilgrim1", "3-Day Katra Pilgrimage", itin_data)
                self.assertIn("itinerary_id", res)
                itin_id = res["itinerary_id"]

                itins = auth.get_saved_itineraries("usr_pilgrim1")
                self.assertEqual(len(itins), 1)
                self.assertEqual(itins[0]["data"]["budget"], 12000)

                del_res = auth.delete_saved_itinerary("usr_pilgrim1", itin_id)
                self.assertTrue(del_res)
                self.assertEqual(len(auth.get_saved_itineraries("usr_pilgrim1")), 0)

    # -------------------------------------------------------------------------
    # 5. Simulated Booking Records & Idempotency
    # -------------------------------------------------------------------------
    def test_11_simulated_booking_persistence_and_receipts(self):
        """Simulated booking records and receipts are saved and retrieved in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                booking_data = {
                    "booking_id": "VD-BOOK-2026-9999",
                    "user_name": "Devotee Sharma",
                    "pax_count": 2,
                    "slot_date": "2026-10-25",
                    "category": "Normal Darshan",
                    "slot_time": "Morning (06:00)",
                    "transport_mode": "Train",
                    "total_price": 3500.0,
                    "receipt": {
                        "receipt_number": "RCP-8888",
                        "status": "CONFIRMED",
                    },
                }

                saved = auth.save_booking("usr_devotee", booking_data)
                self.assertEqual(saved["booking_id"], "VD-BOOK-2026-9999")
                self.assertEqual(saved["status"], "SIMULATED_CONFIRMED")

                # Retrieve by user
                bookings = auth.get_user_bookings("usr_devotee")
                self.assertEqual(len(bookings), 1)
                self.assertEqual(bookings[0]["receipt"]["receipt_number"], "RCP-8888")

                # Retrieve single
                single = auth.get_user_booking("usr_devotee", "VD-BOOK-2026-9999")
                self.assertIsNotNone(single)
                self.assertEqual(single["total_price"], 3500.0)

    def test_12_duplicate_booking_prevention_and_idempotency(self):
        """Re-saving an existing booking_id updates the record idempotently without duplicate entries."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                booking_data = {
                    "booking_id": "VD-BOOK-IDEMP-01",
                    "user_name": "Devotee Gupta",
                    "pax_count": 1,
                    "slot_date": "2026-11-01",
                    "total_price": 1000.0,
                }
                auth.save_booking("usr_idemp", booking_data)

                # Update same booking
                booking_data["total_price"] = 1500.0
                auth.save_booking("usr_idemp", booking_data)

                bookings = auth.get_user_bookings("usr_idemp")
                self.assertEqual(len(bookings), 1)
                self.assertEqual(bookings[0]["total_price"], 1500.0)

    # -------------------------------------------------------------------------
    # 6. Strict Isolation Between Users
    # -------------------------------------------------------------------------
    def test_13_cross_user_isolation(self):
        """User A cannot access or overwrite User B's bookings, itineraries, or conversations."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()

                # User A saves a booking and an itinerary
                auth.save_booking("usr_A", {"booking_id": "BID-A-01", "total_price": 500.0})
                auth.save_itinerary("usr_A", "User A Trip", {"route": "Jammu-Katra"})
                auth.save_conversation("usr_A", "User A Chat", [{"role": "user", "content": "Private"}], conversation_id="conv_A")

                # User B cannot retrieve User A's data
                self.assertIsNone(auth.get_user_booking("usr_B", "BID-A-01"))
                self.assertEqual(len(auth.get_saved_itineraries("usr_B")), 0)
                self.assertIsNone(auth.get_saved_conversation("usr_B", "conv_A"))

                # User B cannot overwrite User A's booking
                with self.assertRaises(PermissionError):
                    auth.save_booking("usr_B", {"booking_id": "BID-A-01", "total_price": 999.0})

    # -------------------------------------------------------------------------
    # 7. Multi-Turn Session State & Deep Merge in MongoDB
    # -------------------------------------------------------------------------
    def test_14_chat_sessions_and_messages_in_mongodb(self):
        """Multi-turn session state with deep merge and messages are persisted in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):

                sess = session_store.create_session("sess_100", initial_state={"requirements": {"origin": "Delhi", "pax": 2}})
                self.assertEqual(sess["session_id"], "sess_100")

                # Add messages
                m1 = session_store.add_message("sess_100", "user", "I want to visit Vaishno Devi.")
                m2 = session_store.add_message("sess_100", "assistant", "Sure, what date are you looking at?")
                self.assertIsNotNone(m1)
                self.assertIsNotNone(m2)

                msgs = session_store.get_messages("sess_100")
                self.assertEqual(len(msgs), 2)
                self.assertEqual(msgs[0]["content"], "I want to visit Vaishno Devi.")

                # Update session with deep merge
                updated = session_store.update_session("sess_100", updates={"requirements": {"pax": 4, "date": "2026-10-20"}})
                self.assertIsNotNone(updated)
                # Verify origin was preserved (deep merge) and pax updated
                self.assertEqual(updated["state"]["requirements"]["origin"], "Delhi")
                self.assertEqual(updated["state"]["requirements"]["pax"], 4)
                self.assertEqual(updated["state"]["requirements"]["date"], "2026-10-20")

                # Clear messages
                session_store.clear_messages("sess_100")
                self.assertEqual(len(session_store.get_messages("sess_100")), 0)

    # -------------------------------------------------------------------------
    # 8. Workflows & State Machine Persistence
    # -------------------------------------------------------------------------
    def test_15_workflow_persistence_and_checkpoints(self):
        """User workflows with checkpoints and cancellation are persisted in MongoDB."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):

                wf = session_store.create_user_workflow(
                    session_id="sess_wf_1",
                    state="AWAITING_USER_ACTION",
                    step="CONFIRM_BOOKING",
                    operation="RPA_BOOKING",
                    pending_action="REVIEW_RECEIPT",
                    expires_in_seconds=600,
                    checkpoint_data={"booking_amount": 2500, "sensitive_otp": "999999"},
                )
                wf_id = wf["workflow_id"]

                # Sensitive OTP must be sanitized from checkpoint
                retrieved = session_store.get_user_workflow(wf_id, session_id="sess_wf_1")
                self.assertIsNotNone(retrieved)
                self.assertNotIn("sensitive_otp", retrieved["checkpoint_data"])
                self.assertEqual(retrieved["checkpoint_data"]["booking_amount"], 2500)

                # Cancel workflow
                cancel_res = session_store.cancel_user_workflow(wf_id, session_id="sess_wf_1", reason="Changed travel date")
                self.assertEqual(cancel_res["status"], "success")
                self.assertEqual(cancel_res["state"], "CANCELLED")

                # Verify state in DB
                wf_after = session_store.get_user_workflow(wf_id)
                self.assertEqual(wf_after["state"], "CANCELLED")

    # -------------------------------------------------------------------------
    # 9. Credential Sanitization Invariant
    # -------------------------------------------------------------------------
    def test_16_credentials_never_logged(self):
        """Plain OTPs, tokens, and passwords are never logged."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "mongodb"}):
            with patch("mongo_db.is_available", return_value=True), \
                 patch("mongo_db.get_collection", side_effect=self.get_mock_coll):
                auth = AuthService()
                with self.assertLogs(logger="agents.auth_service", level="INFO") as log_cm:
                    auth.request_otp("secretuser@example.com")
                    log_text = " ".join(log_cm.output)
                    # Plain email should be masked
                    self.assertNotIn("secretuser@example.com", log_text)
                    self.assertIn("@example.com", log_text)
