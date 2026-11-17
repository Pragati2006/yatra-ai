import os
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from backend.routes.weather import router as weather_router
import agents.coordinator as coordinator
import agents.session_store as session_store
from backend.routes.tourism import router as tourism_router
from backend.routes.yatra import router as yatra_router
from backend.routes.auth import router as auth_router
from utils.logger import SanitizingFormatter, set_correlation_id, get_correlation_id, log_event

# Configure root logger with SanitizingFormatter
root_logger = logging.getLogger()
if not root_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(SanitizingFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    root_logger.addHandler(_handler)
else:
    for _handler in root_logger.handlers:
        _handler.setFormatter(SanitizingFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))

logger = logging.getLogger(__name__)


def is_production_mode() -> bool:
    env = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()
    return env in ("production", "prod", "live")


def is_local_or_lan_origin(origin: str) -> bool:
    """Checks if an origin points to localhost, loopback, or private RFC 1918 LAN."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(origin)
        host = (parsed.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return True
        if host.startswith("192.168.") or host.startswith("10."):
            return True
        if host.startswith("172."):
            parts = host.split(".")
            if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
                return True
        return False
    except Exception:
        return False


def resolve_cors_origins() -> list[str]:
    """
    Dynamically resolves allowed CORS origins based on environment configuration.
    - Reads CORS_ALLOWED_ORIGINS from environment (comma-separated list).
    - Trims whitespace and excludes empty/malformed values.
    - Rejects wildcard '*' because allow_credentials=True requires explicit origins.
    - In development mode: includes standard localhost development origins and allows private LAN.
    - In production mode: strictly allows ONLY approved public HTTPS frontend origins.
      Localhost and private LAN origins are strictly forbidden in production.
    """
    is_prod = is_production_mode()
    raw_env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    parsed_origins = [o.strip() for o in raw_env_origins.split(",") if o.strip()]

    dev_localhost_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    allowed: list[str] = []
    if not is_prod:
        allowed.extend(dev_localhost_origins)

    for origin in parsed_origins:
        if origin == "*" or "*" in origin:
            logger.warning("Wildcard CORS origin '%s' is rejected because allow_credentials=True requires explicit origins.", origin)
            continue
        if origin.startswith("http://") or origin.startswith("https://"):
            clean_origin = origin.rstrip("/")
            if is_prod:
                if not clean_origin.startswith("https://"):
                    logger.warning("CORS security violation: Insecure HTTP origin '%s' rejected in production mode.", clean_origin)
                    continue
                if is_local_or_lan_origin(clean_origin):
                    logger.warning("CORS security violation: Localhost/private LAN origin '%s' rejected in production mode.", clean_origin)
                    continue
            if clean_origin not in allowed:
                allowed.append(clean_origin)
        else:
            logger.warning("Ignoring malformed CORS origin: '%s'", origin)

    # Always ensure the official Cloudflare Pages web frontend is permitted
    official_prod_frontend = "https://yatra-ai.pages.dev"
    if official_prod_frontend not in allowed:
        allowed.append(official_prod_frontend)

    return allowed


is_prod = is_production_mode()

app = FastAPI(
    title="Yatra AI — Unified Pilgrimage & Tourism Assistant API",
    description="AI-powered Vaishno Devi Yatra Planning and Booking API",
    version="1.0.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        correlation_id = set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


app.add_middleware(CorrelationIdMiddleware)

# Dynamic CORS middleware
cors_allowed = resolve_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tourism_router)
app.include_router(weather_router)
app.include_router(yatra_router)
app.include_router(auth_router)

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    current_request: dict | None = None
    current_itinerary: list | None = None
    last_tourism_place: str | None = None
    last_itinerary_context: dict | None = None
    pending_options: list | None = None


@app.get("/")
def root():
    return {
        "message": "Yatra Booking Agent API is running",
        "status": "success"
    }


@app.get("/api/health")
def health():
    """Liveness probe: reports basic service process availability."""
    return {
        "status": "healthy",
        "service": "Yatra Booking Agent"
    }


@app.get("/api/health/ready")
def health_ready():
    """
    Readiness probe: reports whether mandatory local application dependencies are operational.
    Distinguishes liveness from readiness; discloses zero secrets, paths, or exception traces.
    """
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    is_ready = True
    deps: dict[str, str] = {}

    # 1. Mandatory database connectivity based on PERSISTENCE_BACKEND
    from agents.mongo_store import is_mongodb_mode
    if is_mongodb_mode():
        try:
            import mongo_db
            if mongo_db.is_available():
                deps["database"] = "ready_mongodb"
                deps["mongodb"] = "connected"
            else:
                logger.error("Readiness check: PERSISTENCE_BACKEND=mongodb requested, but MongoDB Atlas is unreachable.")
                deps["database"] = "unavailable_mongodb"
                deps["mongodb"] = "offline"
                is_ready = False
        except Exception as exc:
            logger.error("Readiness check: MongoDB check failed: %s", type(exc).__name__)
            deps["database"] = "unavailable_mongodb"
            deps["mongodb"] = "error"
            is_ready = False
    else:
        try:
            from config import SESSIONS_DB_PATH, AUTH_DB_PATH
            import sqlite3
            with sqlite3.connect(str(SESSIONS_DB_PATH), timeout=2.0) as conn:
                conn.execute("SELECT 1")
            with sqlite3.connect(str(AUTH_DB_PATH), timeout=2.0) as conn:
                conn.execute("SELECT 1")
            deps["database"] = "ready"
        except Exception as exc:
            logger.error("Readiness check: SQLite database check failed: %s", type(exc).__name__)
            deps["database"] = "unavailable"
            is_ready = False

        # Optional: MongoDB status in SQLite mode
        try:
            import mongo_db
            if mongo_db.is_available():
                deps["mongodb"] = "connected"
            elif not os.getenv("MONGO_URI"):
                deps["mongodb"] = "unconfigured_fallback_active"
            else:
                deps["mongodb"] = "offline_fallback_active"
        except Exception:
            deps["mongodb"] = "fallback_active"

    # 2. Mandatory: Production Auth Secret Check
    try:
        from agents.auth_service import validate_and_get_auth_secret
        validate_and_get_auth_secret()
        deps["auth_config"] = "ready"
    except Exception as exc:
        logger.error("Readiness check: Auth secret validation failed: %s", type(exc).__name__)
        deps["auth_config"] = "missing_or_invalid"
        is_ready = False

    # 4. Optional: LLM Inference API Configuration
    if os.environ.get("GROQ_API_KEY"):
        deps["llm_provider"] = "configured"
    else:
        deps["llm_provider"] = "unconfigured_rule_based_fallback"

    response_payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": "Yatra AI",
        "timestamp": now_iso,
        "dependencies": deps,
    }

    if not is_ready:
        return JSONResponse(status_code=503, content=response_payload)
    return response_payload


def get_session_owner_id(session_id: str) -> Optional[str]:
    """Retrieves owner user_id for a session from in-memory RAM or persistent store."""
    if not session_id:
        return None
    session_obj = session_store.get_session(session_id)
    if session_obj and session_obj.get("user_id"):
        return session_obj.get("user_id")
    try:
        from agents.auth_service import auth_service
        if auth_service.is_mongodb():
            from agents import mongo_store
            conv_coll = mongo_store._get_coll("auth_saved_conversations")
            d = conv_coll.find_one(
                {"$or": [{"conversation_id": session_id.strip()}, {"_id": session_id.strip()}]},
                projection={"user_id": 1}
            )
            if d:
                return d.get("user_id")
        else:
            import sqlite3
            with sqlite3.connect(auth_service.db_path, timeout=5.0) as conn:
                row = conn.cursor().execute(
                    "SELECT user_id FROM saved_conversations WHERE conversation_id = ?",
                    (session_id.strip(),)
                ).fetchone()
                if row:
                    return row[0]
    except Exception:
        pass
    return None


def verify_chat_session_access(session_id: Optional[str], http_request: Optional[Request]) -> Optional[Dict[str, Any]]:
    """Enforces strict conversation ownership for chat and streaming endpoints.
    - If session_id is owned by an authenticated user, caller must present a valid token for that user.
    - If caller is a different user or unauthenticated guest, raises HTTPException(403).
    - Returns current authenticated user dict or None.
    """
    current_user = None
    if http_request is not None:
        try:
            from backend.routes.auth import extract_session_token
            from agents.auth_service import auth_service
            token = extract_session_token(http_request)
            if token:
                current_user = auth_service.get_user_by_session_token(token)
        except Exception:
            pass

    if not session_id:
        return current_user

    current_uid = current_user.get("user_id") if current_user else None
    owner_uid = get_session_owner_id(session_id)

    if owner_uid:
        if not current_uid or current_uid != owner_uid:
            logger.warning(
                "Access denied: caller %s attempted to access conversation %s owned by %s",
                current_uid or "anonymous_guest",
                session_id,
                owner_uid,
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied to private conversation session.",
            )

    return current_user


@app.post("/api/chat")
def chat(request: ChatRequest, response: Response = None, http_request: Request = None):
    # Enforce session ownership
    current_user = verify_chat_session_access(request.session_id, http_request)
    calling_user_id = current_user.get("user_id") if current_user else None

    try:
        result = coordinator.route_message(
            user_text=request.message,
            session_id=request.session_id,
            current_request=request.current_request,
            current_itinerary=request.current_itinerary,
            last_tourism_place=request.last_tourism_place,
            last_itinerary_context=request.last_itinerary_context,
            pending_options=request.pending_options,
            user_id=calling_user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unhandled exception in chat processing for session '%s': %s",
            request.session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the chat message.",
        )

    # Link session to authenticated user if signed in
    if current_user is not None:
        try:
            from agents.auth_service import auth_service
            sid = (result or {}).get("session_id") or request.session_id
            if sid:
                sess = session_store.get_session(sid)
                if not sess or not sess.get("user_id") or sess.get("user_id") == current_user["user_id"]:
                    session_store.update_session_user(sid, current_user["user_id"])
                    auth_service.sync_saved_conversation_messages(current_user["user_id"], sid)
        except Exception as exc:
            logger.debug("Silently ignored session user update error: %s", exc)

    if response is not None:
        timing = (result or {}).get("timing") or {}
        total_ms = timing.get("total_ms", 0.0)
        intent_ms = timing.get("intent_ms", 0.0)
        response.headers["Server-Timing"] = f"total;dur={total_ms}, intent;dur={intent_ms}"

    return result


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest, http_request: Request = None):
    from fastapi.responses import StreamingResponse
    import json

    # Enforce session ownership
    stream_user = verify_chat_session_access(request.session_id, http_request)
    calling_user_id = stream_user.get("user_id") if stream_user else None

    # Link session to authenticated user if signed in before stream begins
    if stream_user and request.session_id:
        try:
            from agents.auth_service import auth_service
            sid = request.session_id
            sess = session_store.get_session(sid)
            if not sess or not sess.get("user_id") or sess.get("user_id") == stream_user["user_id"]:
                session_store.update_session_user(sid, stream_user["user_id"])
                auth_service.sync_saved_conversation_messages(stream_user["user_id"], sid)
        except Exception as exc:
            logger.debug("Silently ignored stream session user update error: %s", exc)

    def event_stream():
        stream_has_error = False
        try:
            stream_gen = coordinator.route_message_stream(
                user_text=request.message,
                session_id=request.session_id,
                current_request=request.current_request,
                current_itinerary=request.current_itinerary,
                last_tourism_place=request.last_tourism_place,
                last_itinerary_context=request.last_itinerary_context,
                pending_options=request.pending_options,
                user_id=calling_user_id,
            )
            for event in stream_gen:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            stream_has_error = True
            logger.error(
                "Unhandled exception in chat stream for session '%s': %s",
                request.session_id,
                exc,
                exc_info=True,
            )
            error_payload = {
                "type": "error",
                "error": "An error occurred while streaming the response.",
                "status": "ERROR",
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        # Sync messages after stream finishes ONLY if no error occurred
        if not stream_has_error and stream_user and request.session_id:
            try:
                from agents.auth_service import auth_service
                sess = session_store.get_session(request.session_id)
                if not sess or not sess.get("user_id") or sess.get("user_id") == stream_user["user_id"]:
                    auth_service.sync_saved_conversation_messages(stream_user["user_id"], request.session_id)
            except Exception as exc:
                logger.debug("Silently ignored post-stream message sync error: %s", exc)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/chat/history/{session_id}")
def get_chat_history(session_id: str, http_request: Request = None):
    """
    Returns persistent chat history for a session in chronological order.
    Returns an empty message list for unknown or new sessions without creating a session record.
    Enforces per-user data isolation: rejects unauthorized access if session is owned by a user.
    Raises HTTPException 500 on database retrieval errors.
    """
    try:
        from agents.auth_service import auth_service
        # Verify ownership if session is bound to an authenticated user
        session_obj = session_store.get_session(session_id)
        owner_user_id = session_obj.get("user_id") if session_obj else None

        doc_owner_id = None
        if not owner_user_id:
            if auth_service.is_mongodb():
                try:
                    from agents import mongo_store
                    conv_coll = mongo_store._get_coll("auth_saved_conversations")
                    d = conv_coll.find_one({"$or": [{"conversation_id": session_id}, {"_id": session_id}]})
                    if d:
                        doc_owner_id = d.get("user_id")
                except Exception:
                    pass
            else:
                import sqlite3
                try:
                    with sqlite3.connect(auth_service.db_path, timeout=5.0) as conn:
                        row = conn.cursor().execute("SELECT user_id FROM saved_conversations WHERE conversation_id = ?", (session_id,)).fetchone()
                        if row:
                            doc_owner_id = row[0]
                except Exception:
                    pass

        target_owner_id = owner_user_id or doc_owner_id
        if target_owner_id and http_request is not None:
            from backend.routes.auth import extract_session_token
            token = extract_session_token(http_request)
            current_user = auth_service.get_user_by_session_token(token) if token else None
            if not current_user or current_user.get("user_id") != target_owner_id:
                raise HTTPException(status_code=403, detail="Access denied to private conversation history.")

        messages = session_store.get_messages(session_id)
        if not messages:
            if auth_service.is_mongodb():
                try:
                    from agents import mongo_store
                    conv_coll = mongo_store._get_coll("auth_saved_conversations")
                    doc = conv_coll.find_one({"$or": [{"conversation_id": session_id}, {"_id": session_id}]})
                    if doc and doc.get("messages"):
                        messages = doc["messages"]
                except Exception as e:
                    logger.debug("MongoDB fallback check in get_chat_history error: %s", e)
            else:
                import sqlite3
                try:
                    with sqlite3.connect(auth_service.db_path, timeout=5.0) as conn:
                        row = conn.cursor().execute(
                            "SELECT messages_json FROM saved_conversations WHERE conversation_id = ?",
                            (session_id,),
                        ).fetchone()
                        if row and row[0]:
                            messages = json.loads(row[0])
                except Exception as e:
                    logger.debug("Fallback check in get_chat_history error: %s", e)
        return {
            "session_id": session_id,
            "messages": messages,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve chat history for session %s: %s", session_id, type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history",
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
