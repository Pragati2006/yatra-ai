"""
backend/routes/itineraries.py

Phase 8.8.58 — Smart Itinerary Management, Partial Editing & Group Collaboration API.

Endpoints:
- GET    /api/itineraries
- POST   /api/itineraries
- GET    /api/itineraries/{itinerary_id}
- DELETE /api/itineraries/{itinerary_id}
- POST   /api/itineraries/{itinerary_id}/edit/preview
- POST   /api/itineraries/{itinerary_id}/edit/apply
- POST   /api/itineraries/{itinerary_id}/edit/undo
- POST   /api/itineraries/{itinerary_id}/shares
- GET    /api/itineraries/{itinerary_id}/shares
- PATCH  /api/itineraries/{itinerary_id}/shares/members/{member_user_id}
- DELETE /api/itineraries/{itinerary_id}/shares/members/{member_user_id}
- DELETE /api/itineraries/{itinerary_id}/shares/invites/{invite_id}
- POST   /api/itineraries/invites/{token}/accept
- POST   /api/itineraries/invites/accept
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agents.itinerary_collab_service import (
    CollabServiceError,
    ItineraryConflictError,
    itinerary_collab_service,
)
from agents.itinerary_editor import ItineraryEditValidationError
from backend.routes.auth import require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/itineraries",
    tags=["Itineraries & Collaboration"],
)


class UpsertItineraryPayload(BaseModel):
    itinerary_id: Optional[str] = Field(default=None, description="Optional existing itinerary ID to update")
    title: str = Field(default="Vaishno Devi Yatra Itinerary", description="Display title")
    source_key: Optional[str] = Field(default=None, description="Optional deduplication key")
    expected_revision: Optional[int] = Field(default=None, description="Expected revision for optimistic concurrency on updates")
    itinerary: Any = Field(..., description="Structured itinerary payload")


class ItineraryEditRequest(BaseModel):
    operation: str = Field(..., description="Partial edit operation identifier")
    day_number: Optional[int] = Field(default=None)
    activity_index: Optional[int] = Field(default=None)
    place: Optional[str] = Field(default=None)
    old_place: Optional[str] = Field(default=None)
    new_place: Optional[str] = Field(default=None)
    activity: Optional[str] = Field(default=None)
    time: Optional[str] = Field(default=None)
    duration: Optional[str] = Field(default=None)
    start_time: Optional[str] = Field(default=None)
    end_time: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    preferences: Optional[Dict[str, Any]] = Field(default=None)
    duration_days: Optional[int] = Field(default=None)
    instruction: Optional[str] = Field(default=None)
    use_ai: bool = Field(default=True)
    require_ai: bool = Field(default=False)
    ai_response: Optional[Any] = Field(default=None)
    title: Optional[str] = Field(default=None)
    start_date: Optional[str] = Field(default=None)
    end_date: Optional[str] = Field(default=None)
    travellers_count: Optional[int] = Field(default=None)
    confirm_impact: bool = Field(default=False)
    expected_revision: Optional[int] = Field(default=None)


class UndoEditRequest(BaseModel):
    expected_revision: Optional[int] = Field(default=None)


class CreateInviteRequest(BaseModel):
    role: str = Field(default="VIEWER", description="Collaborator role: VIEWER or EDITOR")
    expires_in_hours: int = Field(default=72, description="Invite validity window in hours (1-720)")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., description="Updated collaborator role: VIEWER or EDITOR")


class AcceptInviteBody(BaseModel):
    token: str = Field(..., description="Invitation token")


def _raise_collab_http_error(exc: Exception):
    if isinstance(exc, ItineraryConflictError):
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "current_revision": exc.current_revision},
        )
    if isinstance(exc, CollabServiceError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    if isinstance(exc, ItineraryEditValidationError):
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), **exc.details})
    raise exc


@router.get("")
def list_itineraries(request: Request):
    user = require_authenticated_user(request)
    items = itinerary_collab_service.list_itineraries_for_user(user["user_id"])
    return {
        "status": "success",
        "count": len(items),
        "itineraries": items,
    }


@router.post("")
def create_or_upsert_itinerary(payload: UpsertItineraryPayload, request: Request):
    user = require_authenticated_user(request)
    try:
        saved = itinerary_collab_service.upsert_itinerary(
            user_id=user["user_id"],
            title=payload.title,
            itinerary_data=payload.itinerary,
            itinerary_id=payload.itinerary_id,
            source_key=payload.source_key,
            expected_revision=payload.expected_revision,
        )
        return {
            "status": "success",
            "message": "Itinerary saved.",
            "itinerary": saved,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.get("/{itinerary_id}")
def get_itinerary_detail(itinerary_id: str, request: Request):
    user = require_authenticated_user(request)
    try:
        item = itinerary_collab_service.get_itinerary_for_user(user["user_id"], itinerary_id)
        return {
            "status": "success",
            "itinerary": item,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.delete("/{itinerary_id}")
def delete_itinerary(itinerary_id: str, request: Request):
    user = require_authenticated_user(request)
    try:
        deleted = itinerary_collab_service.delete_itinerary(user["user_id"], itinerary_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Itinerary not found.")
        return {
            "status": "success",
            "message": "Itinerary deleted.",
            "itinerary_id": itinerary_id,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/{itinerary_id}/edit/preview")
def preview_itinerary_change(itinerary_id: str, payload: ItineraryEditRequest, request: Request):
    user = require_authenticated_user(request)
    try:
        preview = itinerary_collab_service.preview_edit(
            user_id=user["user_id"],
            itinerary_id=itinerary_id,
            edit_payload=payload.model_dump(exclude_none=True),
        )
        return {
            "status": "success",
            "preview": preview,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/{itinerary_id}/edit/apply")
def apply_itinerary_change(itinerary_id: str, payload: ItineraryEditRequest, request: Request):
    user = require_authenticated_user(request)
    try:
        updated = itinerary_collab_service.apply_edit(
            user_id=user["user_id"],
            itinerary_id=itinerary_id,
            edit_payload=payload.model_dump(exclude_none=True),
            expected_revision=payload.expected_revision,
        )
        return {
            "status": "success",
            "message": "Itinerary updated cleanly.",
            "itinerary": updated,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/{itinerary_id}/edit/undo")
def undo_itinerary_change(itinerary_id: str, request: Request, payload: Optional[UndoEditRequest] = None):
    user = require_authenticated_user(request)
    try:
        reverted = itinerary_collab_service.undo_last_edit(
            user_id=user["user_id"],
            itinerary_id=itinerary_id,
            expected_revision=payload.expected_revision if payload else None,
        )
        return {
            "status": "success",
            "message": "Reverted to previous revision.",
            "itinerary": reverted,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/{itinerary_id}/shares")
def create_share_invite(itinerary_id: str, payload: CreateInviteRequest, request: Request):
    user = require_authenticated_user(request)
    try:
        invite = itinerary_collab_service.create_invite(
            owner_user_id=user["user_id"],
            itinerary_id=itinerary_id,
            role=payload.role,
            expires_in_hours=payload.expires_in_hours,
        )
        origin = str(request.headers.get("Origin") or "").strip()
        if not origin:
            origin = str(os.getenv("PUBLIC_FRONTEND_URL") or "").strip()
        if not origin:
            origin = str(request.base_url)
        origin = origin.rstrip("/")
        invite["invite_url"] = f"{origin}/?invite={invite['invite_token']}"
        return {
            "status": "success",
            "share": invite,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.get("/{itinerary_id}/shares")
def list_share_access(itinerary_id: str, request: Request):
    user = require_authenticated_user(request)
    try:
        shares = itinerary_collab_service.list_shares(user["user_id"], itinerary_id)
        return {
            "status": "success",
            **shares,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.patch("/{itinerary_id}/shares/members/{member_user_id}")
def update_share_member_role(
    itinerary_id: str,
    member_user_id: str,
    payload: UpdateMemberRoleRequest,
    request: Request,
):
    user = require_authenticated_user(request)
    try:
        updated = itinerary_collab_service.update_member_role(
            owner_user_id=user["user_id"],
            itinerary_id=itinerary_id,
            target_user_id=member_user_id,
            new_role=payload.role,
        )
        return {
            "status": "success",
            "member": updated,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.delete("/{itinerary_id}/shares/members/{member_user_id}")
def revoke_share_member(itinerary_id: str, member_user_id: str, request: Request):
    user = require_authenticated_user(request)
    try:
        ok = itinerary_collab_service.revoke_member(
            owner_user_id=user["user_id"],
            itinerary_id=itinerary_id,
            target_user_id=member_user_id,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Collaborator membership not found.")
        return {
            "status": "success",
            "message": "Collaborator access revoked.",
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.delete("/{itinerary_id}/shares/invites/{invite_id}")
def revoke_share_invite(itinerary_id: str, invite_id: str, request: Request):
    user = require_authenticated_user(request)
    try:
        ok = itinerary_collab_service.revoke_invite(
            owner_user_id=user["user_id"],
            itinerary_id=itinerary_id,
            invite_id=invite_id,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Invitation not found.")
        return {
            "status": "success",
            "message": "Invitation link revoked.",
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/invites/{token}/accept")
def accept_share_invite_path(token: str, request: Request):
    user = require_authenticated_user(request)
    try:
        item = itinerary_collab_service.accept_invite(user["user_id"], token)
        return {
            "status": "success",
            "message": "Shared itinerary access granted.",
            "itinerary": item,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)


@router.post("/invites/accept")
def accept_share_invite_body(payload: AcceptInviteBody, request: Request):
    user = require_authenticated_user(request)
    try:
        item = itinerary_collab_service.accept_invite(user["user_id"], payload.token)
        return {
            "status": "success",
            "message": "Shared itinerary access granted.",
            "itinerary": item,
        }
    except (CollabServiceError, ItineraryEditValidationError) as exc:
        _raise_collab_http_error(exc)

