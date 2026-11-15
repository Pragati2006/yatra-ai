"""
agents/mongo_store.py
Persistent storage adapter for MongoDB Atlas in Yatra AI.

Provides full remote persistence for all user-specific categories:
1. User accounts (auth_users)
2. Authentication sessions & OTP challenges (auth_sessions, auth_otp_challenges)
3. Conversation history & saved conversations (chat_sessions, chat_messages, auth_saved_conversations)
4. Saved itineraries (auth_saved_itineraries)
5. Simulated booking records & receipts (auth_user_bookings)
6. User workflows & RPA checkpoints (user_workflows)

Invariants:
- Activated strictly when PERSISTENCE_BACKEND=mongodb.
- Refuses silent fallback to ephemeral SQLite when in cloud mode.
- Sanitizes and prevents logging of any credentials or secrets.
- Enforces strict user-id and session-id isolation across all operations.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def is_mongodb_mode() -> bool:
    """Returns True if MongoDB persistence is explicitly configured."""
    return os.getenv("PERSISTENCE_BACKEND", "sqlite").lower() == "mongodb"


def _get_coll(name: str):
    """
    Retrieves collection from mongo_db module.
    Raises RuntimeError if MongoDB is unavailable in cloud persistence mode.
    """
    try:
        import mongo_db
        if not mongo_db.is_available():
            raise RuntimeError(
                f"CRITICAL PERSISTENCE FAILURE: Persistence backend 'mongodb' requested, "
                f"but MongoDB Atlas is unreachable. Refusing silent fallback to ephemeral storage."
            )
        coll = mongo_db.get_collection(name)
        if coll is None:
            raise RuntimeError(
                f"CRITICAL PERSISTENCE FAILURE: Collection '{name}' unavailable in MongoDB Atlas."
            )
        return coll
    except Exception as exc:
        if "CRITICAL PERSISTENCE FAILURE" in str(exc):
            raise
        raise RuntimeError(
            f"CRITICAL PERSISTENCE FAILURE: MongoDB Atlas connection error: {exc}. "
            f"Refusing silent fallback to ephemeral storage."
        ) from exc


def ensure_indexes():
    """Idempotently ensures all required indexes and unique constraints exist."""
    if not is_mongodb_mode():
        return
    try:
        # 1. User accounts: unique email
        users_coll = _get_coll("auth_users")
        users_coll.create_index("email", unique=True)
        users_coll.create_index("user_id", unique=True)

        # 2. Auth sessions: index on user_id and expires_at
        sessions_coll = _get_coll("auth_sessions")
        sessions_coll.create_index("user_id")
        sessions_coll.create_index("expires_at")

        # 3. OTP challenges: index on email
        otp_coll = _get_coll("auth_otp_challenges")
        otp_coll.create_index("email", unique=True)

        # 4. Saved itineraries: compound user_id + created_at
        itin_coll = _get_coll("auth_saved_itineraries")
        itin_coll.create_index([("user_id", 1), ("created_at", -1)])

        # 5. Saved conversations: compound user_id + created_at
        conv_coll = _get_coll("auth_saved_conversations")
        conv_coll.create_index([("user_id", 1), ("created_at", -1)])

        # 6. User bookings: unique booking_id, compound user_id + created_at
        bookings_coll = _get_coll("auth_user_bookings")
        bookings_coll.create_index("booking_id", unique=True)
        bookings_coll.create_index([("user_id", 1), ("created_at", -1)])

        # 7. Chat sessions & messages
        chat_sess = _get_coll("chat_sessions")
        chat_sess.create_index("session_id", unique=True)
        chat_sess.create_index("user_id")

        chat_msg = _get_coll("chat_messages")
        chat_msg.create_index([("session_id", 1), ("created_at", 1)])

        # 8. Workflows
        wf_coll = _get_coll("user_workflows")
        wf_coll.create_index("workflow_id", unique=True)
        wf_coll.create_index("session_id")
    except Exception as exc:
        logger.warning("MongoDB index initialization notice: %s", exc)


# =============================================================================
# 1. User Accounts (auth_users)
# =============================================================================

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_users")
    doc = coll.find_one({"email": email})
    if not doc:
        return None
    return {
        "user_id": doc.get("user_id") or str(doc.get("_id")),
        "email": doc.get("email"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "preferences": doc.get("preferences") or {},
    }


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_users")
    doc = coll.find_one({"$or": [{"user_id": user_id}, {"_id": user_id}]})
    if not doc:
        return None
    return {
        "user_id": doc.get("user_id") or str(doc.get("_id")),
        "email": doc.get("email"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "preferences": doc.get("preferences") or {},
    }


def create_user(user_id: str, email: str, preferences: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    coll = _get_coll("auth_users")
    doc = {
        "_id": user_id,
        "user_id": user_id,
        "email": email,
        "created_at": now_iso,
        "updated_at": now_iso,
        "preferences": preferences,
    }
    coll.insert_one(doc)
    return {
        "user_id": user_id,
        "email": email,
        "created_at": now_iso,
        "updated_at": now_iso,
        "preferences": preferences,
    }


def get_user_profile_summary(user_id: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_id(user_id)
    if not user:
        return None
    itin_coll = _get_coll("auth_saved_itineraries")
    conv_coll = _get_coll("auth_saved_conversations")
    book_coll = _get_coll("auth_user_bookings")

    itin_count = itin_coll.count_documents({"user_id": user_id})
    conv_count = conv_coll.count_documents({"user_id": user_id})
    book_count = book_coll.count_documents({"user_id": user_id})

    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
        "preferences": user.get("preferences") or {},
        "stats": {
            "saved_itineraries_count": itin_count,
            "saved_conversations_count": conv_count,
            "confirmed_bookings_count": book_count,
        },
    }


# =============================================================================
# 2. OTP Challenges & Auth Sessions
# =============================================================================

def save_otp_challenge(email: str, otp_hash: str, now_iso: str, expires_at: str) -> bool:
    coll = _get_coll("auth_otp_challenges")
    coll.update_one(
        {"email": email},
        {
            "$set": {
                "_id": email,
                "email": email,
                "otp_hash": otp_hash,
                "attempts": 0,
                "created_at": now_iso,
                "expires_at": expires_at,
                "last_requested_at": now_iso,
            }
        },
        upsert=True,
    )
    return True


def get_otp_challenge(email: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_otp_challenges")
    doc = coll.find_one({"email": email})
    if not doc:
        return None
    return {
        "email": doc.get("email"),
        "otp_hash": doc.get("otp_hash"),
        "attempts": doc.get("attempts", 0),
        "created_at": doc.get("created_at"),
        "expires_at": doc.get("expires_at"),
        "last_requested_at": doc.get("last_requested_at"),
    }


def update_otp_attempts(email: str, attempts: int) -> bool:
    coll = _get_coll("auth_otp_challenges")
    res = coll.update_one({"email": email}, {"$set": {"attempts": attempts}})
    return res.modified_count > 0


def delete_otp_challenge(email: str) -> bool:
    coll = _get_coll("auth_otp_challenges")
    res = coll.delete_one({"email": email})
    return res.deleted_count > 0


def create_auth_session(session_token: str, user_id: str, email: str, now_iso: str, expires_at: str) -> bool:
    coll = _get_coll("auth_sessions")
    doc = {
        "_id": session_token,
        "session_token": session_token,
        "user_id": user_id,
        "email": email,
        "created_at": now_iso,
        "expires_at": expires_at,
    }
    coll.insert_one(doc)
    return True


def get_auth_session(session_token: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_sessions")
    doc = coll.find_one({"session_token": session_token})
    if not doc:
        return None
    return {
        "session_token": doc.get("session_token"),
        "user_id": doc.get("user_id"),
        "email": doc.get("email"),
        "created_at": doc.get("created_at"),
        "expires_at": doc.get("expires_at"),
    }


def delete_auth_session(session_token: str) -> bool:
    coll = _get_coll("auth_sessions")
    res = coll.delete_one({"session_token": session_token})
    return res.deleted_count > 0


# =============================================================================
# 3. User Saved Itineraries
# =============================================================================

def save_itinerary(itinerary_id: str, user_id: str, title: str, now_iso: str, data: Any) -> Dict[str, Any]:
    coll = _get_coll("auth_saved_itineraries")
    doc = {
        "_id": itinerary_id,
        "itinerary_id": itinerary_id,
        "user_id": user_id,
        "title": title,
        "created_at": now_iso,
        "data": data,
    }
    coll.insert_one(doc)
    return {
        "itinerary_id": itinerary_id,
        "user_id": user_id,
        "title": title,
        "created_at": now_iso,
        "data": data,
    }


def get_saved_itineraries(user_id: str) -> List[Dict[str, Any]]:
    coll = _get_coll("auth_saved_itineraries")
    docs = coll.find({"user_id": user_id}).sort("created_at", -1)
    results = []
    for d in docs:
        results.append({
            "itinerary_id": d.get("itinerary_id") or str(d.get("_id")),
            "title": d.get("title"),
            "created_at": d.get("created_at"),
            "data": d.get("data"),
        })
    return results


def delete_saved_itinerary(user_id: str, itinerary_id: str) -> bool:
    coll = _get_coll("auth_saved_itineraries")
    res = coll.delete_one({"user_id": user_id, "$or": [{"itinerary_id": itinerary_id}, {"_id": itinerary_id}]})
    return res.deleted_count > 0


# =============================================================================
# 4. User Saved Conversations
# =============================================================================

def save_conversation(
    conversation_id: str,
    user_id: str,
    title: str,
    now_iso: str,
    messages: List[Dict[str, Any]],
    trip_request: Optional[Dict[str, Any]] = None,
    itinerary: Optional[Any] = None,
) -> Dict[str, Any]:
    coll = _get_coll("auth_saved_conversations")
    existing = coll.find_one({"conversation_id": conversation_id, "user_id": user_id})
    created_at = existing.get("created_at") if existing else now_iso

    set_doc = {
        "_id": conversation_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": title,
        "created_at": created_at,
        "updated_at": now_iso,
        "messages": messages,
    }
    if trip_request is not None:
        set_doc["trip_request"] = trip_request
    elif existing and existing.get("trip_request"):
        set_doc["trip_request"] = existing.get("trip_request")

    if itinerary is not None:
        set_doc["itinerary"] = itinerary
    elif existing and existing.get("itinerary"):
        set_doc["itinerary"] = existing.get("itinerary")

    coll.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": set_doc},
        upsert=True,
    )
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": title,
        "created_at": created_at,
        "updated_at": now_iso,
        "messages": messages,
        "trip_request": set_doc.get("trip_request"),
        "itinerary": set_doc.get("itinerary"),
    }


def get_saved_conversations(user_id: str) -> List[Dict[str, Any]]:
    coll = _get_coll("auth_saved_conversations")
    docs = coll.find({"user_id": user_id}).sort([("updated_at", -1), ("created_at", -1)])
    results = []
    for d in docs:
        results.append({
            "conversation_id": d.get("conversation_id") or str(d.get("_id")),
            "title": d.get("title"),
            "created_at": d.get("created_at"),
            "updated_at": d.get("updated_at") or d.get("created_at"),
            "messages": d.get("messages") or [],
            "trip_request": d.get("trip_request"),
            "itinerary": d.get("itinerary"),
        })
    return results


def get_saved_conversation(user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_saved_conversations")
    doc = coll.find_one({"user_id": user_id, "$or": [{"conversation_id": conversation_id}, {"_id": conversation_id}]})
    if not doc:
        return None
    return {
        "conversation_id": doc.get("conversation_id") or str(doc.get("_id")),
        "title": doc.get("title"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at") or doc.get("created_at"),
        "messages": doc.get("messages") or [],
        "trip_request": doc.get("trip_request"),
        "itinerary": doc.get("itinerary"),
    }


def sync_saved_conversation_messages(user_id: str, conversation_id: str, messages: List[Dict[str, Any]]) -> bool:
    coll = _get_coll("auth_saved_conversations")
    now_iso = datetime.now(timezone.utc).isoformat()
    res = coll.update_one(
        {"user_id": user_id, "$or": [{"conversation_id": conversation_id}, {"_id": conversation_id}]},
        {"$set": {"messages": messages, "updated_at": now_iso}},
    )
    return res.matched_count > 0


def delete_saved_conversation(user_id: str, conversation_id: str) -> bool:
    coll = _get_coll("auth_saved_conversations")
    res = coll.delete_one({"user_id": user_id, "$or": [{"conversation_id": conversation_id}, {"_id": conversation_id}]})
    return res.deleted_count > 0


# =============================================================================
# 5. User Bookings (auth_user_bookings)
# =============================================================================

def save_booking(user_id: str, booking_data: Dict[str, Any]) -> Dict[str, Any]:
    coll = _get_coll("auth_user_bookings")
    bid = str(booking_data.get("booking_id")).strip()

    # Ownership check if booking already exists
    existing = coll.find_one({"booking_id": bid})
    if existing and existing.get("user_id") != user_id:
        raise PermissionError(f"Booking {bid} does not belong to user {user_id}")

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": bid,
        "booking_id": bid,
        "user_id": user_id,
        "session_id": booking_data.get("session_id"),
        "plan_version": int(booking_data.get("plan_version") or 1),
        "user_name": booking_data.get("user_name") or "Pilgrim",
        "pax_count": int(booking_data.get("pax_count") or 1),
        "slot_date": str(booking_data.get("slot_date") or ""),
        "category": str(booking_data.get("category") or "Normal Darshan"),
        "slot_time": str(booking_data.get("slot_time") or ""),
        "transport_mode": str(booking_data.get("transport_mode") or "Train"),
        "transport_info": str(booking_data.get("transport_info") or ""),
        "hotel_name": booking_data.get("hotel_name"),
        "total_price": float(booking_data.get("total_price") or 0.0),
        "payment_status": str(booking_data.get("payment_status") or "COMPLETED_SANDBOX"),
        "status": "SIMULATED_CONFIRMED",
        "created_at": booking_data.get("created_at") or now_iso,
        "receipt": booking_data.get("receipt") or {},
    }

    coll.update_one({"booking_id": bid}, {"$set": doc}, upsert=True)
    return doc


def get_user_bookings(user_id: str) -> List[Dict[str, Any]]:
    coll = _get_coll("auth_user_bookings")
    docs = coll.find({"user_id": user_id}).sort("created_at", -1)
    results = []
    for d in docs:
        results.append({
            "booking_id": d.get("booking_id") or str(d.get("_id")),
            "user_id": d.get("user_id"),
            "session_id": d.get("session_id"),
            "plan_version": d.get("plan_version", 1),
            "user_name": d.get("user_name"),
            "pax_count": d.get("pax_count"),
            "slot_date": d.get("slot_date"),
            "category": d.get("category"),
            "slot_time": d.get("slot_time"),
            "transport_mode": d.get("transport_mode"),
            "transport_info": d.get("transport_info"),
            "hotel_name": d.get("hotel_name"),
            "total_price": d.get("total_price"),
            "payment_status": d.get("payment_status"),
            "status": d.get("status"),
            "created_at": d.get("created_at"),
            "receipt": d.get("receipt") or {},
        })
    return results


def get_user_booking(user_id: str, booking_id: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("auth_user_bookings")
    d = coll.find_one({"user_id": user_id, "$or": [{"booking_id": booking_id}, {"_id": booking_id}]})
    if not d:
        return None
    return {
        "booking_id": d.get("booking_id") or str(d.get("_id")),
        "user_id": d.get("user_id"),
        "session_id": d.get("session_id"),
        "plan_version": d.get("plan_version", 1),
        "user_name": d.get("user_name"),
        "pax_count": d.get("pax_count"),
        "slot_date": d.get("slot_date"),
        "category": d.get("category"),
        "slot_time": d.get("slot_time"),
        "transport_mode": d.get("transport_mode"),
        "transport_info": d.get("transport_info"),
        "hotel_name": d.get("hotel_name"),
        "total_price": d.get("total_price"),
        "payment_status": d.get("payment_status"),
        "status": d.get("status"),
        "created_at": d.get("created_at"),
        "receipt": d.get("receipt") or {},
    }


# =============================================================================
# 6. Multi-Turn Sessions & Messages (chat_sessions, chat_messages)
# =============================================================================

def create_chat_session(session_id: str, user_id: Optional[str], initial_state: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    coll = _get_coll("chat_sessions")
    doc = {
        "_id": session_id,
        "session_id": session_id,
        "status": "INITIALIZED",
        "created_at": now_iso,
        "updated_at": now_iso,
        "state": initial_state,
        "user_id": user_id,
    }
    coll.insert_one(doc)
    return doc


def get_chat_session(session_id: str) -> Optional[Dict[str, Any]]:
    coll = _get_coll("chat_sessions")
    doc = coll.find_one({"$or": [{"session_id": session_id}, {"_id": session_id}]})
    if not doc:
        return None
    return {
        "session_id": doc.get("session_id") or str(doc.get("_id")),
        "status": doc.get("status"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "state": doc.get("state") or {},
        "user_id": doc.get("user_id"),
    }


def update_chat_session(
    session_id: str,
    updates: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    now_iso: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    coll = _get_coll("chat_sessions")
    existing = get_chat_session(session_id)
    if not existing:
        return None

    state = existing.get("state", {})
    now = now_iso or datetime.now(timezone.utc).isoformat()
    new_status = status if status is not None else existing.get("status", "ACTIVE")
    new_user_id = user_id if user_id is not None else existing.get("user_id")

    if updates:
        for k, v in updates.items():
            if k == "user_id" and v is not None:
                new_user_id = str(v).strip()
            elif isinstance(v, dict) and isinstance(state.get(k), dict):
                state[k].update(v)
            else:
                state[k] = v

    coll.update_one(
        {"$or": [{"session_id": session_id}, {"_id": session_id}]},
        {
            "$set": {
                "state": state,
                "status": new_status,
                "user_id": new_user_id,
                "updated_at": now,
            }
        },
    )
    return {
        "session_id": session_id,
        "status": new_status,
        "created_at": existing.get("created_at"),
        "updated_at": now,
        "user_id": new_user_id,
        "state": state,
    }


def update_session_user(session_id: str, user_id: str) -> bool:
    coll = _get_coll("chat_sessions")
    now_iso = datetime.now(timezone.utc).isoformat()
    res = coll.update_one(
        {"$or": [{"session_id": session_id}, {"_id": session_id}]},
        {"$set": {"user_id": user_id, "updated_at": now_iso}},
    )
    return res.matched_count > 0


def get_sessions_by_user(user_id: str) -> List[Dict[str, Any]]:
    coll = _get_coll("chat_sessions")
    docs = coll.find({"user_id": user_id}).sort("updated_at", -1)
    results = []
    for doc in docs:
        results.append({
            "session_id": doc.get("session_id") or str(doc.get("_id")),
            "status": doc.get("status"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "state": doc.get("state") or {},
            "user_id": doc.get("user_id"),
        })
    return results


def delete_chat_session(session_id: str) -> bool:
    chat_coll = _get_coll("chat_sessions")
    msg_coll = _get_coll("chat_messages")
    chat_res = chat_coll.delete_one({"$or": [{"session_id": session_id}, {"_id": session_id}]})
    msg_coll.delete_many({"session_id": session_id})
    return chat_res.deleted_count > 0


def list_chat_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    coll = _get_coll("chat_sessions")
    docs = coll.find().sort("updated_at", -1).limit(limit)
    results = []
    for doc in docs:
        results.append({
            "session_id": doc.get("session_id") or str(doc.get("_id")),
            "status": doc.get("status"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "user_id": doc.get("user_id"),
        })
    return results


def add_chat_message(session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]], now_iso: str) -> Dict[str, Any]:
    coll = _get_coll("chat_messages")
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    doc = {
        "_id": msg_id,
        "message_id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": now_iso,
    }
    coll.insert_one(doc)
    doc["id"] = msg_id
    return doc


def get_chat_messages(session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    coll = _get_coll("chat_messages")
    cursor = coll.find({"session_id": session_id}).sort("created_at", 1)
    if limit:
        cursor = cursor.limit(limit)
    messages = []
    for d in cursor:
        messages.append({
            "id": d.get("message_id") or str(d.get("_id")),
            "role": d.get("role"),
            "content": d.get("content"),
            "metadata": d.get("metadata") or {},
            "created_at": d.get("created_at"),
        })
    return messages


def clear_chat_messages(session_id: str) -> int:
    coll = _get_coll("chat_messages")
    res = coll.delete_many({"session_id": session_id})
    return res.deleted_count


def delete_chat_message(session_id: str, message_id: str) -> bool:
    coll = _get_coll("chat_messages")
    res = coll.delete_one({"session_id": session_id, "$or": [{"message_id": message_id}, {"_id": message_id}]})
    return res.deleted_count > 0


# =============================================================================
# 7. Workflows (user_workflows)
# =============================================================================

def create_workflow(
    workflow_id: str,
    session_id: str,
    state: str,
    step: str,
    operation: str,
    pending_action: str,
    checkpoint_data: Dict[str, Any],
    resume_token: Optional[str],
    created_at: str,
    expires_at: str,
) -> bool:
    coll = _get_coll("user_workflows")
    doc = {
        "_id": workflow_id,
        "workflow_id": workflow_id,
        "session_id": session_id,
        "state": state,
        "step": step,
        "operation": operation,
        "pending_action": pending_action,
        "created_at": created_at,
        "updated_at": created_at,
        "expires_at": expires_at,
        "checkpoint_data": checkpoint_data,
        "resume_token": resume_token,
    }
    coll.insert_one(doc)
    return True


def get_workflow(workflow_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    coll = _get_coll("user_workflows")
    doc = coll.find_one({"$or": [{"workflow_id": workflow_id}, {"_id": workflow_id}]})
    if not doc:
        return None
    if session_id and doc.get("session_id") != session_id:
        return None
    return {
        "workflow_id": doc.get("workflow_id") or str(doc.get("_id")),
        "session_id": doc.get("session_id"),
        "state": doc.get("state"),
        "step": doc.get("step"),
        "operation": doc.get("operation"),
        "pending_action": doc.get("pending_action"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "expires_at": doc.get("expires_at"),
        "checkpoint_data": doc.get("checkpoint_data") or {},
        "resume_token": doc.get("resume_token"),
    }


def update_workflow(workflow_id: str, updates: Dict[str, Any]) -> bool:
    coll = _get_coll("user_workflows")
    now_iso = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now_iso
    res = coll.update_one({"$or": [{"workflow_id": workflow_id}, {"_id": workflow_id}]}, {"$set": updates})
    return res.matched_count > 0


def cancel_workflow(workflow_id: str, reason: str = "User cancelled") -> bool:
    coll = _get_coll("user_workflows")
    now_iso = datetime.now(timezone.utc).isoformat()
    wf = get_workflow(workflow_id)
    if not wf or wf.get("state") in ("COMPLETED", "CANCELLED", "FAILED"):
        return False
    chk = wf.get("checkpoint_data") or {}
    chk["cancelled_reason"] = reason
    res = coll.update_one(
        {"$or": [{"workflow_id": workflow_id}, {"_id": workflow_id}]},
        {
            "$set": {
                "state": "CANCELLED",
                "pending_action": "NONE",
                "updated_at": now_iso,
                "checkpoint_data": chk,
            }
        },
    )
    return res.matched_count > 0


def list_workflows(
    session_id: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    coll = _get_coll("user_workflows")
    query: Dict[str, Any] = {}
    if session_id:
        query["session_id"] = session_id
    if state:
        query["state"] = state
    docs = coll.find(query).sort("created_at", -1).limit(limit)
    results = []
    for doc in docs:
        results.append({
            "workflow_id": doc.get("workflow_id") or str(doc.get("_id")),
            "session_id": doc.get("session_id"),
            "state": doc.get("state"),
            "step": doc.get("step"),
            "operation": doc.get("operation"),
            "pending_action": doc.get("pending_action"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "expires_at": doc.get("expires_at"),
            "checkpoint_data": doc.get("checkpoint_data") or {},
            "resume_token": doc.get("resume_token"),
        })
    return results
