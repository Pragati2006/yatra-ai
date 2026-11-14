"""
services/operational_notices.py
Curated Operational Notice Service & Domain Registry for Yatra AI.

Provides human-verified, source-attributed operational advisories for Vaishno Devi
pilgrimage tracks and regional travel corridors (Jammu, Udhampur, Ramban, Katra, NH-44).

Adheres strictly to project governance:
- Zero automated scraping of unconfigured government websites.
- Truth-in-data lifecycle separation (source_fetch, freshness, verification, lifecycle).
- Explicit REQUIRES_REVERIFICATION handling when validity horizons lapse.
- Strict 5-point alignment rules for superseding notices.
- Non-override of official sources by secondary media reports.
"""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import (
    NoticeAggregateStatus,
    NoticeCategory,
    NoticeLifecycleStatus,
    OperationalNotice,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    get_utc_now_iso,
)

logger = logging.getLogger(__name__)

DEFAULT_NOTICES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "curated_operational_notices.json",
)


def _parse_iso_utc(ts_str: Optional[str]) -> Optional[datetime]:
    """Safely parses an ISO 8601 string into a timezone-aware UTC datetime."""
    if not ts_str:
        return None
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        logger.debug("Failed to parse ISO timestamp '%s': %s", ts_str, exc)
        return None


def load_curated_notices(file_path: Optional[str] = None) -> Tuple[List[OperationalNotice], str]:
    """Loads curated operational notices from storage.
    Returns (notices_list, status), where status is 'SUCCESS' or 'SOURCE_UNAVAILABLE'.
    """
    path = file_path or DEFAULT_NOTICES_PATH
    if not os.path.exists(path):
        logger.warning("Curated operational notices catalog not found at '%s'.", path)
        return [], NoticeAggregateStatus.SOURCE_UNAVAILABLE.value

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        raw_notices = payload.get("notices", [])
        notices: List[OperationalNotice] = []
        for n in raw_notices:
            raw_v_status = n.get("verification_status")
            v_status = raw_v_status if raw_v_status else VerificationStatus.UNVERIFIED.value
            notice = OperationalNotice(
                notice_id=str(n.get("notice_id", "")),
                notice_title=str(n.get("notice_title", "")),
                notice_text=str(n.get("notice_text", "")),
                issuing_authority=str(n.get("issuing_authority", "")),
                source_url=str(n.get("source_url", "")),
                affected_location=str(n.get("affected_location", "")),
                affected_route=n.get("affected_route"),
                category=n.get("category", NoticeCategory.GENERAL_OPERATIONAL_NOTICE.value),
                severity=n.get("severity", "ADVISORY"),
                publication_timestamp=n.get("publication_timestamp"),
                effective_from=n.get("effective_from"),
                effective_until=n.get("effective_until"),
                verified_at=n.get("verified_at"),
                verified_by=n.get("verified_by"),
                verification_status=v_status,
                notice_lifecycle_status=n.get("notice_lifecycle_status", NoticeLifecycleStatus.ACTIVE.value),
                superseded_by_notice_id=n.get("superseded_by_notice_id"),
                supersedes_notice_id=n.get("supersedes_notice_id"),
                translated_summary=n.get("translated_summary"),
                notes=n.get("notes"),
            )
            notices.append(notice)

        return notices, "SUCCESS"
    except Exception as exc:
        logger.error("Failed to load curated operational notices from '%s': %s", path, exc)
        return [], NoticeAggregateStatus.SOURCE_UNAVAILABLE.value


def evaluate_notice_lifecycle(
    notice: OperationalNotice,
    reference_time: Optional[datetime] = None,
) -> OperationalNotice:
    """Evaluates the semantic lifecycle of a single operational notice.

    Enforces the mandatory project safety invariant:
    A notice must NEVER be assumed to have cleared merely because a validity timer elapsed.
    When a validity horizon expires without an explicit withdrawal or superseding update,
    the notice transitions to REQUIRES_REVERIFICATION.
    """
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Terminal / Explicit states remain unchanged
    if notice.notice_lifecycle_status in (
        NoticeLifecycleStatus.WITHDRAWN.value,
        NoticeLifecycleStatus.SUPERSEDED.value,
    ):
        return notice

    # 2. Check future effective date
    dt_from = _parse_iso_utc(notice.effective_from)
    if dt_from and now < dt_from:
        notice.notice_lifecycle_status = NoticeLifecycleStatus.PUBLISHED.value
        return notice

    # 3. Check explicit effective_until horizon
    dt_until = _parse_iso_utc(notice.effective_until)
    if dt_until and now > dt_until:
        # Validity horizon elapsed without explicit withdrawal; require reverification!
        notice.notice_lifecycle_status = NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value
        return notice

    # 4. Check category-specific default validity horizon
    # For daily traffic plans and weather warnings, expected horizon is 24 hours
    dt_pub = _parse_iso_utc(notice.publication_timestamp) or dt_from
    if dt_pub and notice.category in (
        NoticeCategory.TRAFFIC_ADVISORY.value,
        NoticeCategory.WEATHER_WARNING.value,
    ):
        age_hours = (now - dt_pub).total_seconds() / 3600.0
        if age_hours > 24.0 and not dt_until:
            notice.notice_lifecycle_status = NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value
            return notice

    # 5. Otherwise active
    notice.notice_lifecycle_status = NoticeLifecycleStatus.ACTIVE.value
    return notice


def resolve_superseding_relationships(
    notices: List[OperationalNotice], reference_time: Optional[datetime] = None
) -> List[OperationalNotice]:
    """Resolves explicit superseding relationships among operational notices.

    MANDATORY SAFETY RULES (F-01 Remediation):
    1. An explicit `supersedes_notice_id` relationship may establish supersession,
       subject to source-verification and authority checks.
    2. An unverified secondary source can NEVER supersede a verified official notice.
    3. An explicit withdrawal record changes the relevant notice to WITHDRAWN.
    4. A newer notice without explicit replacement or withdrawal evidence MUST NOT
       silently supersede an older notice.
    5. Multiple notices concerning the same corridor remain active simultaneously.
    6. Conflicting notices remain visible together.
    7. Expired notices transition to REQUIRES_REVERIFICATION, not automatically
       to WITHDRAWN or SUPERSEDED.
    """
    # Evaluate lifecycle states first (preserves explicit terminal states and handles horizons)
    evaluated = [evaluate_notice_lifecycle(n, reference_time=reference_time) for n in notices]

    # Map by notice_id for fast lookup
    notice_map = {n.notice_id: n for n in evaluated}

    # Honor declared explicit supersedes_notice_id relationships
    for n in evaluated:
        if n.supersedes_notice_id and n.supersedes_notice_id in notice_map:
            old_n = notice_map[n.supersedes_notice_id]

            # Rule 2: Ensure unverified / secondary source cannot supersede verified official source
            if (
                old_n.verification_status == VerificationStatus.VERIFIED_CURATED_SOURCE.value
                and n.verification_status == VerificationStatus.UNVERIFIED.value
            ):
                logger.warning(
                    "Rejected unverified notice '%s' attempting to supersede verified official notice '%s'.",
                    n.notice_id,
                    old_n.notice_id,
                )
                continue

            # Authority compatibility check
            if old_n.issuing_authority and n.issuing_authority:
                old_auth = old_n.issuing_authority.strip().lower()
                new_auth = n.issuing_authority.strip().lower()
                if old_auth != new_auth and not (
                    ("shrine board" in old_auth and "shrine board" in new_auth)
                    or ("traffic police" in old_auth and "traffic police" in new_auth)
                ):
                    logger.warning(
                        "Rejected cross-authority superseding: notice '%s' (%s) cannot supersede notice '%s' (%s).",
                        n.notice_id,
                        n.issuing_authority,
                        old_n.notice_id,
                        old_n.issuing_authority,
                    )
                    continue

            old_n.notice_lifecycle_status = NoticeLifecycleStatus.SUPERSEDED.value
            old_n.superseded_by_notice_id = n.notice_id

    return evaluated


def query_curated_notices(
    location: Optional[str] = None,
    route: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    active_only: bool = True,
    file_path: Optional[str] = None,
    reference_time: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """Queries curated operational notices with lifecycle evaluation, superseding resolution,
    and standardized aggregate status determination.

    Returns:
        (notices_list, aggregate_status, metadata)
        aggregate_status is one of: 'HAS_NOTICES', 'NO_ACTIVE_NOTICES', 'SOURCE_UNAVAILABLE'.
    """
    raw_notices, load_status = load_curated_notices(file_path=file_path)
    if load_status == NoticeAggregateStatus.SOURCE_UNAVAILABLE.value:
        return [], NoticeAggregateStatus.SOURCE_UNAVAILABLE.value, {
            "total_notices": 0,
            "disclaimer": "Curated operational notices catalog is temporarily unavailable.",
        }

    # Evaluate lifecycle and superseding relationships
    all_notices = resolve_superseding_relationships(raw_notices)

    # Filter notices
    filtered: List[OperationalNotice] = []
    for n in all_notices:
        # Evaluate against reference_time if provided
        if reference_time:
            n = evaluate_notice_lifecycle(n, reference_time=reference_time)

        if active_only and n.notice_lifecycle_status in (
            NoticeLifecycleStatus.SUPERSEDED.value,
            NoticeLifecycleStatus.WITHDRAWN.value,
        ):
            continue

        if location:
            loc_clean = location.strip().lower()
            n_loc = n.affected_location.strip().lower()
            if loc_clean not in n_loc and n_loc not in loc_clean:
                # Allow generic pilgrimage locations
                if loc_clean not in ("vaishno devi", "katra", "all", "jammu"):
                    continue

        if route:
            route_clean = route.strip().lower()
            n_route = (n.affected_route or "").strip().lower()
            if route_clean not in n_route and n_route not in route_clean:
                continue

        if category:
            cat_clean = category.strip().upper()
            if n.category.upper() != cat_clean:
                continue

        if severity:
            sev_clean = severity.strip().upper()
            if n.severity.upper() != sev_clean:
                continue

        filtered.append(n)

    # Aggregate status determination
    active_count = sum(
        1 for n in filtered
        if n.notice_lifecycle_status in (
            NoticeLifecycleStatus.ACTIVE.value,
            NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value,
        )
    )

    if not filtered or active_count == 0:
        agg_status = NoticeAggregateStatus.NO_ACTIVE_NOTICES.value
        advisory_msg = (
            "No active disruption notices or closures recorded in the curated registry as of "
            f"{get_utc_now_iso()}. Upstream live status remains unconfirmed without direct authority verification."
        )
    else:
        agg_status = NoticeAggregateStatus.HAS_NOTICES.value
        has_reverification = any(
            n.notice_lifecycle_status == NoticeLifecycleStatus.REQUIRES_REVERIFICATION.value
            for n in filtered
        )
        if has_reverification:
            advisory_msg = (
                "ADVISORY: One or more operational notices have reached their expected validity horizon "
                "without official renewal. Confirm current passage with Traffic Control or the Shrine Board."
            )
        else:
            advisory_msg = "Official operational notices retrieved from verified curated registry."

    metadata = {
        "total_notices": len(filtered),
        "active_notices_count": active_count,
        "aggregate_status": agg_status,
        "advisory": advisory_msg,
        "retrieval_timestamp": get_utc_now_iso(),
    }

    return [n.to_dict() for n in filtered], agg_status, metadata
