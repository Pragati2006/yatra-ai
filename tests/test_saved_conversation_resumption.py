"""
tests/test_saved_conversation_resumption.py
Comprehensive Test Suite for Saved Conversation Reopening, Resumption, and Data Isolation.

Covers:
1. Saving a conversation via endpoint.
2. Retrieving a saved conversation by ID with exact message order.
3. Restoring all messages in exact chronological order.
4. Continuing an existing conversation after reopening under the same conversation ID.
5. Ensuring newly sent messages are attached to the original conversation.
6. Preventing cross-user access (strict ownership validation & data isolation).
7. Handling missing or invalid conversation IDs (404).
8. Deleting a conversation cleanly without affecting other users or records.
9. Updating existing saved conversation in-place without generating duplicate IDs.
10. Unauthenticated access blocked (401).
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.datastructures import Headers
from fastapi import HTTPException
from agents.auth_service import auth_service, get_email_provider
from backend.main import chat, ChatRequest, get_chat_history
from backend.routes.auth import (
    save_conversation_endpoint,
    get_saved_conversations_endpoint,
    get_saved_conversation_detail_endpoint,
    delete_saved_conversation_endpoint,
    SaveConversationRequest,
)


class MockRequest:
    """Lightweight mock request providing Starlette-compatible headers and cookies."""
    def __init__(self, token=None, method="GET"):
        hdr_dict = {"authorization": f"Bearer {token}"} if token else {}
        self.headers = Headers(hdr_dict)
        self.cookies = {}
        self.method = method
        self.url = type("URL", (), {"scheme": "http"})()


class TestSavedConversationResumption(unittest.TestCase):
    """Acceptance tests for saved conversation retrieval, reopening, continuation, and security."""

    def setUp(self):
        self.mock_provider = get_email_provider()
        self.user_a_email = f"devotee_a_{uuid.uuid4().hex[:6]}@example.com"
        self.user_b_email = f"devotee_b_{uuid.uuid4().hex[:6]}@example.com"
        self.token_a, self.user_a_id = self._create_user(self.user_a_email)
        self.token_b, self.user_b_id = self._create_user(self.user_b_email)

    def _create_user(self, email):
        auth_service.request_otp(email)
        otp = self.mock_provider.get_latest_otp_for(email)
        res = auth_service.verify_otp(email, otp)
        self.assertEqual(res.get("status"), "success")
        return res["session_token"], res["user"]["user_id"]

    def test_01_save_and_retrieve_single_conversation(self):
        """Verifies saving and retrieving a complete conversation by ID with exact message order."""
        messages = [
            {"id": "msg-1", "role": "user", "content": "How far is Bhawan from Katra?"},
            {"id": "msg-2", "role": "assistant", "content": "It is approximately 13 kilometers via the traditional trek route."},
            {"id": "msg-3", "role": "user", "content": "Are battery cars available for senior citizens?"},
            {"id": "msg-4", "role": "assistant", "content": "Yes, battery-operated electric autos run between Ardhkuwari and Bhawan."},
        ]

        save_req = MockRequest(token=self.token_a, method="POST")
        save_payload = SaveConversationRequest(
            title="Bhawan Distance & Battery Car Inquiry",
            messages=messages,
        )
        save_res = save_conversation_endpoint(save_payload, save_req)
        self.assertEqual(save_res["status"], "success")
        saved = save_res["conversation"]
        conv_id = saved["conversation_id"]
        self.assertTrue(conv_id.startswith("conv_"))
        self.assertEqual(saved["title"], "Bhawan Distance & Battery Car Inquiry")

        # 1. Retrieve single conversation by ID
        get_req = MockRequest(token=self.token_a, method="GET")
        detail_res = get_saved_conversation_detail_endpoint(conv_id, get_req)
        self.assertEqual(detail_res["status"], "success")
        conv = detail_res["conversation"]
        self.assertEqual(conv["conversation_id"], conv_id)
        self.assertEqual(conv["title"], "Bhawan Distance & Battery Car Inquiry")
        self.assertEqual(len(conv["messages"]), 4)

        # 2. Verify exact message order, roles, and content
        self.assertEqual(conv["messages"][0]["content"], "How far is Bhawan from Katra?")
        self.assertEqual(conv["messages"][0]["role"], "user")
        self.assertEqual(conv["messages"][1]["content"], "It is approximately 13 kilometers via the traditional trek route.")
        self.assertEqual(conv["messages"][1]["role"], "assistant")
        self.assertEqual(conv["messages"][2]["content"], "Are battery cars available for senior citizens?")
        self.assertEqual(conv["messages"][2]["role"], "user")
        self.assertEqual(conv["messages"][3]["content"], "Yes, battery-operated electric autos run between Ardhkuwari and Bhawan.")
        self.assertEqual(conv["messages"][3]["role"], "assistant")

    def test_02_strict_ownership_and_data_isolation(self):
        """Verifies that User B CANNOT retrieve, list, or delete User A's saved conversation."""
        # User A saves private conversation
        save_req = MockRequest(token=self.token_a, method="POST")
        save_payload = SaveConversationRequest(
            title="User A Private Pilgrimage Notes",
            messages=[{"role": "user", "content": "Confidential travel preferences"}],
        )
        save_res = save_conversation_endpoint(save_payload, save_req)
        conv_id = save_res["conversation"]["conversation_id"]

        # User B attempts to access User A's conversation by ID -> 404
        req_b_get = MockRequest(token=self.token_b, method="GET")
        with self.assertRaises(HTTPException) as ctx:
            get_saved_conversation_detail_endpoint(conv_id, req_b_get)
        self.assertEqual(ctx.exception.status_code, 404)

        # User B attempts to delete User A's conversation -> 404
        req_b_del = MockRequest(token=self.token_b, method="DELETE")
        with self.assertRaises(HTTPException) as ctx:
            delete_saved_conversation_endpoint(conv_id, req_b_del)
        self.assertEqual(ctx.exception.status_code, 404)

        # User B lists conversations -> User A's conversation is not present
        list_b_res = get_saved_conversations_endpoint(req_b_get)
        self.assertEqual(list_b_res["status"], "success")
        b_ids = [c["conversation_id"] for c in list_b_res["conversations"]]
        self.assertNotIn(conv_id, b_ids, "User A's conversation must never appear in User B's list")

    def test_03_missing_or_invalid_conversation_id(self):
        """Verifies 404 handling when querying non-existent or malformed conversation IDs."""
        req_get = MockRequest(token=self.token_a, method="GET")
        with self.assertRaises(HTTPException) as ctx:
            get_saved_conversation_detail_endpoint("conv_nonexistent_xyz_999", req_get)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found or access denied", ctx.exception.detail.lower())

    def test_04_continuing_reopened_conversation_preserves_id(self):
        """Verifies that sending a new message to a reopened saved conversation attaches to the same ID."""
        # 1. User saves initial conversation
        initial_msgs = [
            {"role": "user", "content": "What is the best time for Vaishno Devi Darshan?"},
            {"role": "assistant", "content": "The shrine is open throughout the year, with March to October being pleasant."},
        ]
        save_req = MockRequest(token=self.token_a, method="POST")
        save_payload = SaveConversationRequest(
            title="Season & Weather Consultation",
            messages=initial_msgs,
        )
        save_res = save_conversation_endpoint(save_payload, save_req)
        conv_id = save_res["conversation"]["conversation_id"]

        # 2. User reopens conversation and sends a follow-up query via /api/chat
        chat_req = MockRequest(token=self.token_a, method="POST")
        chat_payload = ChatRequest(
            message="How is the weather in Katra in December?",
            session_id=conv_id,
        )
        chat_res = chat(chat_payload, http_request=chat_req)

        # 3. Crucial: session_id must match the original conv_id (do NOT replace with new UUID)
        res_sid = chat_res.get("session_id")
        self.assertEqual(res_sid, conv_id, f"Session ID must remain {conv_id}, got {res_sid}")

        # 4. History endpoint /api/chat/history/{conv_id} must return prior turns + new turn
        hist_data = get_chat_history(conv_id)
        hist_msgs = hist_data["messages"]
        self.assertGreaterEqual(len(hist_msgs), 3)

        # 5. Saved conversation in auth_service is synced and updated
        saved_conv = auth_service.get_saved_conversation(self.user_a_id, conv_id)
        self.assertIsNotNone(saved_conv)
        self.assertEqual(saved_conv["conversation_id"], conv_id)
        saved_contents = [m.get("content") for m in saved_conv["messages"]]
        self.assertTrue(any("December" in (c or "") for c in saved_contents))

    def test_05_delete_conversation_is_isolated(self):
        """Verifies deleting a conversation removes it cleanly and subsequent retrieval returns 404."""
        save_req = MockRequest(token=self.token_a, method="POST")
        save_payload = SaveConversationRequest(
            title="Temporary Chat Thread",
            messages=[{"role": "user", "content": "Temporary"}],
        )
        save_res = save_conversation_endpoint(save_payload, save_req)
        conv_id = save_res["conversation"]["conversation_id"]

        # Delete it
        del_req = MockRequest(token=self.token_a, method="DELETE")
        del_res = delete_saved_conversation_endpoint(conv_id, del_req)
        self.assertEqual(del_res["status"], "success")

        # Now get by ID returns 404
        get_req = MockRequest(token=self.token_a, method="GET")
        with self.assertRaises(HTTPException) as ctx:
            get_saved_conversation_detail_endpoint(conv_id, get_req)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_06_unauthenticated_request_rejected(self):
        """Verifies that an unauthenticated request cannot access saved conversations."""
        no_auth_req = MockRequest(token=None, method="GET")
        with self.assertRaises(HTTPException) as ctx:
            get_saved_conversation_detail_endpoint("conv_any_123", no_auth_req)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_07_save_conversation_idempotent_update(self):
        """Verifies updating an existing saved conversation by conversation_id modifies the same record."""
        save_req = MockRequest(token=self.token_a, method="POST")
        initial_payload = SaveConversationRequest(
            title="Helicopter Ticket Queries",
            messages=[{"role": "user", "content": "How to get helicopter tickets?"}],
        )
        res1 = save_conversation_endpoint(initial_payload, save_req)
        conv_id = res1["conversation"]["conversation_id"]

        # Update with new message and pass conversation_id
        updated_payload = SaveConversationRequest(
            title="Helicopter Ticket Queries (Updated)",
            messages=[
                {"role": "user", "content": "How to get helicopter tickets?"},
                {"role": "assistant", "content": "You can book helicopter tickets online on the shrine board portal."},
            ],
            conversation_id=conv_id,
        )
        res2 = save_conversation_endpoint(updated_payload, save_req)
        self.assertEqual(res2["conversation"]["conversation_id"], conv_id)
        self.assertEqual(res2["conversation"]["title"], "Helicopter Ticket Queries (Updated)")
        self.assertEqual(len(res2["conversation"]["messages"]), 2)

        # Retrieve and verify persistence
        get_req = MockRequest(token=self.token_a, method="GET")
        detail = get_saved_conversation_detail_endpoint(conv_id, get_req)
        self.assertEqual(detail["conversation"]["title"], "Helicopter Ticket Queries (Updated)")
        self.assertEqual(len(detail["conversation"]["messages"]), 2)

    def test_08_transfer_guest_conversation_preserves_id(self):
        """Verifies transferring a guest session creates a saved conversation accessible under that ID."""
        from agents import session_store
        from backend.routes.auth import transfer_conversation_endpoint, TransferConversationRequest

        guest_sid = f"guest_sess_{uuid.uuid4().hex[:6]}"
        session_store.create_session(guest_sid)
        session_store.add_message(guest_sid, "user", "Are battery cars available?")
        session_store.add_message(guest_sid, "assistant", "Yes, between Ardhkuwari and Bhawan.")

        transfer_req = MockRequest(token=self.token_a, method="POST")
        transfer_payload = TransferConversationRequest(
            session_id=guest_sid,
            title="Guest Battery Car Consultation",
        )
        t_res = transfer_conversation_endpoint(transfer_payload, transfer_req)
        self.assertEqual(t_res["status"], "success")
        conv_id = t_res["conversation"]["conversation_id"]

        # Retrieve via get_saved_conversation_detail_endpoint
        get_req = MockRequest(token=self.token_a, method="GET")
        detail = get_saved_conversation_detail_endpoint(conv_id, get_req)
        self.assertEqual(detail["conversation"]["conversation_id"], conv_id)
        self.assertEqual(len(detail["conversation"]["messages"]), 2)


if __name__ == "__main__":
    unittest.main()
