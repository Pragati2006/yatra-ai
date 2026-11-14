"""
utils/provenance.py
Standardized Provenance Schema & Unified Metadata Architecture for Yatra AI.

Provides standard metadata classes, source types, freshness statuses, verification statuses,
timestamp generators, validators, and extraction helpers for every information source:
- Live external APIs (Open-Meteo elevation-aware weather)
- Ingested RAG vector store chunks (static_rag)
- Curated regional catalogs (tourism places, Aarti timings, trek landmarks)
- Indicative transport timetables & hotel tariffs
- Simulated local sandboxed mock portal interactions (availability, mock RPA booking)
- Fallback & unavailable data representation
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# -----------------------------------------------------------------------------
# 1. STANDARDIZED ENUMS
# -----------------------------------------------------------------------------

class SourceType(str, Enum):
    """Origin classification for retrieved or generated information."""
    LIVE_API = "live_api"
    CACHED_API = "cached_api"
    STATIC_RAG = "static_rag"
    CURATED_DATA = "curated_data"
    INDICATIVE_DATA = "indicative_data"
    SIMULATED_DATA = "simulated_data"
    UNKNOWN_SOURCE = "unknown_source"


class FreshnessStatus(str, Enum):
    """Temporal state and currency of the information."""
    LIVE = "live"
    CACHED = "cached"
    STALE = "stale"
    FALLBACK = "fallback"
    SIMULATED = "simulated"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class VerificationStatus(str, Enum):
    """Epistemic grounding and verification degree of the source."""
    VERIFIED_EXTERNAL_API = "verified_external_api"
    VERIFIED_OFFICIAL_SOURCE = "verified_official_source"
    VERIFIED_CURATED_SOURCE = "verified_curated_source"
    VERIFIED_INTERNAL_KNOWLEDGE = "verified_internal_knowledge"
    PARTIALLY_VERIFIED = "partially_verified"
    INDICATIVE_INFORMATION = "indicative_information"
    SIMULATION_ONLY = "simulation_only"
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"


# -----------------------------------------------------------------------------
# 2. NORMALIZATION HELPERS
# -----------------------------------------------------------------------------

_VALID_SOURCE_TYPES: Set[str] = {t.value for t in SourceType}
_VALID_FRESHNESS_STATUSES: Set[str] = {f.value for f in FreshnessStatus}
_VALID_VERIFICATION_STATUSES: Set[str] = {v.value for v in VerificationStatus}

_SOURCE_TYPE_ALIASES: Dict[str, str] = {
    "live": SourceType.LIVE_API.value,
    "api": SourceType.LIVE_API.value,
    "external_api": SourceType.LIVE_API.value,
    "open_meteo": SourceType.LIVE_API.value,
    "cached": SourceType.CACHED_API.value,
    "rag": SourceType.STATIC_RAG.value,
    "vector_store": SourceType.STATIC_RAG.value,
    "curated": SourceType.CURATED_DATA.value,
    "catalog": SourceType.CURATED_DATA.value,
    "database": SourceType.CURATED_DATA.value,
    "indicative": SourceType.INDICATIVE_DATA.value,
    "estimate": SourceType.INDICATIVE_DATA.value,
    "seasonal_average": SourceType.CURATED_DATA.value,
    "mock": SourceType.SIMULATED_DATA.value,
    "simulation": SourceType.SIMULATED_DATA.value,
    "synthetic": SourceType.SIMULATED_DATA.value,
    "rpa": SourceType.SIMULATED_DATA.value,
}

_FRESHNESS_ALIASES: Dict[str, str] = {
    "live_forecast": FreshnessStatus.LIVE.value,
    "realtime": FreshnessStatus.LIVE.value,
    "fresh": FreshnessStatus.LIVE.value,
    "cache": FreshnessStatus.CACHED.value,
    "expired": FreshnessStatus.STALE.value,
    "offline": FreshnessStatus.FALLBACK.value,
    "seasonal_estimate": FreshnessStatus.FALLBACK.value,
    "mock": FreshnessStatus.SIMULATED.value,
    "failed": FreshnessStatus.UNAVAILABLE.value,
    "error": FreshnessStatus.UNAVAILABLE.value,
    "static": FreshnessStatus.NOT_APPLICABLE.value,
    "none": FreshnessStatus.NOT_APPLICABLE.value,
}

_VERIFICATION_ALIASES: Dict[str, str] = {
    "verified": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
    "official": VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
    "tier_1_official": VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
    "verified_general_source": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
    "curated_climatological_estimate": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
    "seasonal_estimate": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
    "simulated": VerificationStatus.SIMULATION_ONLY.value,
    "mock_portal": VerificationStatus.SIMULATION_ONLY.value,
    "unrecognized_location": VerificationStatus.UNVERIFIED.value,
}


def normalize_source_type(val: Optional[str]) -> str:
    """Normalizes any string to a standard SourceType value."""
    if not val:
        return SourceType.UNKNOWN_SOURCE.value
    cleaned = str(val).strip().lower()
    if cleaned in _VALID_SOURCE_TYPES:
        return cleaned
    return _SOURCE_TYPE_ALIASES.get(cleaned, SourceType.UNKNOWN_SOURCE.value)


def normalize_freshness_status(val: Optional[str]) -> str:
    """Normalizes any string to a standard FreshnessStatus value."""
    if not val:
        return FreshnessStatus.NOT_APPLICABLE.value
    cleaned = str(val).strip().lower()
    if cleaned in _VALID_FRESHNESS_STATUSES:
        return cleaned
    return _FRESHNESS_ALIASES.get(cleaned, FreshnessStatus.NOT_APPLICABLE.value)


def normalize_verification_status(val: Optional[str]) -> str:
    """Normalizes any string to a standard VerificationStatus value."""
    if not val:
        return VerificationStatus.UNVERIFIED.value
    cleaned = str(val).strip().lower()
    if cleaned in _VALID_VERIFICATION_STATUSES:
        return cleaned
    return _VERIFICATION_ALIASES.get(cleaned, VerificationStatus.UNVERIFIED.value)


def get_utc_now_iso() -> str:
    """Generates a standard timezone-aware ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# 3. PROVENANCE RECORD DATACLASS & CREATOR
# -----------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """Strongly-typed data provenance record."""
    source_name: str
    source_type: str
    freshness_status: str
    verification_status: str
    retrieval_timestamp: str
    source_url: Optional[str] = None
    source_tier: Optional[str] = None
    data_timestamp: Optional[str] = None
    location: Optional[str] = None
    disclaimer: Optional[str] = None
    domain: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes to a clean JSON-serializable dictionary omitting None values."""
        res = asdict(self)
        return {k: v for k, v in res.items() if v is not None}


def create_provenance(
    source_name: str,
    source_type: Union[str, SourceType],
    freshness_status: Union[str, FreshnessStatus],
    verification_status: Union[str, VerificationStatus],
    retrieval_timestamp: Optional[str] = None,
    source_url: Optional[str] = None,
    source_tier: Optional[str] = None,
    data_timestamp: Optional[str] = None,
    location: Optional[str] = None,
    disclaimer: Optional[str] = None,
    domain: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a validated, normalized provenance dictionary."""
    norm_source_type = normalize_source_type(str(source_type.value if isinstance(source_type, Enum) else source_type))
    norm_freshness = normalize_freshness_status(str(freshness_status.value if isinstance(freshness_status, Enum) else freshness_status))
    norm_verification = normalize_verification_status(str(verification_status.value if isinstance(verification_status, Enum) else verification_status))

    # Static RAG content must never be described as live
    if norm_source_type == SourceType.STATIC_RAG.value and norm_freshness == FreshnessStatus.LIVE.value:
        norm_freshness = FreshnessStatus.CACHED.value

    # Simulated/mock data must always have simulation verification status
    if norm_source_type == SourceType.SIMULATED_DATA.value or norm_freshness == FreshnessStatus.SIMULATED.value:
        norm_verification = VerificationStatus.SIMULATION_ONLY.value

    # Ensure timezone-aware ISO 8601 retrieval timestamp
    r_ts = retrieval_timestamp or get_utc_now_iso()
    if r_ts and not ("+" in r_ts or r_ts.endswith("Z")):
        # If naive timestamp was passed, append UTC timezone
        r_ts = f"{r_ts}+00:00"

    record = ProvenanceRecord(
        source_name=source_name.strip() if source_name else "Unknown Source",
        source_type=norm_source_type,
        freshness_status=norm_freshness,
        verification_status=norm_verification,
        retrieval_timestamp=r_ts,
        source_url=source_url.strip() if source_url else None,
        source_tier=source_tier.strip() if source_tier else None,
        data_timestamp=data_timestamp.strip() if data_timestamp else None,
        location=location.strip() if location else None,
        disclaimer=disclaimer.strip() if disclaimer else None,
        domain=domain.strip() if domain else None,
        notes=notes.strip() if notes else None,
    )
    return record.to_dict()


def validate_provenance(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates a provenance record against schema requirements.
    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []
    if not isinstance(record, dict):
        return False, ["Record must be a dictionary"]

    # 1. Required core fields
    for req in ("source_name", "source_type", "freshness_status", "verification_status", "retrieval_timestamp"):
        if not record.get(req):
            errors.append(f"Missing required field: '{req}'")

    # 2. Enum validity
    s_type = record.get("source_type")
    if s_type and s_type not in _VALID_SOURCE_TYPES:
        errors.append(f"Invalid source_type: '{s_type}'")

    fresh = record.get("freshness_status")
    if fresh and fresh not in _VALID_FRESHNESS_STATUSES:
        errors.append(f"Invalid freshness_status: '{fresh}'")

    verif = record.get("verification_status")
    if verif and verif not in _VALID_VERIFICATION_STATUSES:
        errors.append(f"Invalid verification_status: '{verif}'")

    # 3. Timestamp formatting (must have timezone offset)
    r_ts = record.get("retrieval_timestamp")
    if r_ts:
        if not ("+" in r_ts or r_ts.endswith("Z") or "-" in r_ts[10:]):
            errors.append(f"retrieval_timestamp must be timezone-aware ISO 8601: '{r_ts}'")

    # 4. Strict Safety & Integrity Rules
    if s_type == SourceType.STATIC_RAG.value and fresh == FreshnessStatus.LIVE.value:
        errors.append("Static RAG knowledge cannot be labelled as live")

    if s_type == SourceType.SIMULATED_DATA.value and verif != VerificationStatus.SIMULATION_ONLY.value:
        errors.append("Simulated data must have verification_status='simulation_only'")

    if fresh == FreshnessStatus.UNAVAILABLE.value and verif == VerificationStatus.VERIFIED_EXTERNAL_API.value:
        errors.append("Unavailable data cannot be marked as verified_external_api")

    return (len(errors) == 0), errors


def deduplicate_provenance(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicates provenance records while preserving distinct locations and order."""
    deduped: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str, Optional[str]]] = set()

    for r in records:
        if not isinstance(r, dict):
            continue
        key = (
            str(r.get("source_name", "")).strip().lower(),
            str(r.get("source_type", "")).strip().lower(),
            str(r.get("location", "")).strip().lower() if r.get("location") else None,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(r)

    return deduped


# -----------------------------------------------------------------------------
# 4. TOOL PROVENANCE EXTRACTION HELPERS
# -----------------------------------------------------------------------------

def extract_provenance_from_weather(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts provenance from Checkpoint 8.1 weather tool results."""
    records: List[Dict[str, Any]] = []

    # Case 1: Unrecognized location
    if result.get("status") == "UNRECOGNIZED_LOCATION":
        records.append(create_provenance(
            source_name="Yatra AI Location Validator",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.UNVERIFIED,
            location=result.get("unrecognized_location"),
            disclaimer=result.get("clarification_message"),
            domain="weather",
        ))
        return records

    # Case 2: Multi-location result
    locations_list = result.get("locations")
    if locations_list and isinstance(locations_list, list):
        for loc in locations_list:
            if not isinstance(loc, dict):
                continue
            f_stat = loc.get("freshness_status", "fallback")
            s_type = loc.get("source_type") or (
                SourceType.LIVE_API.value if f_stat == "live" else (
                    SourceType.CACHED_API.value if f_stat in ("cached", "stale") else SourceType.CURATED_DATA.value
                )
            )
            v_stat = loc.get("verification_status") or (
                VerificationStatus.VERIFIED_EXTERNAL_API.value if f_stat in ("live", "cached") else (
                    VerificationStatus.UNVERIFIED.value if f_stat == "stale" else VerificationStatus.VERIFIED_CURATED_SOURCE.value
                )
            )
            is_ext = s_type in ("live_api", "cached_api")

            records.append(create_provenance(
                source_name=loc.get("source_name") or ("Open-Meteo Weather API" if is_ext else "IMD Katra Climatological Normals"),
                source_type=s_type,
                freshness_status=f_stat,
                verification_status=v_stat,
                source_url=loc.get("source_url") or ("https://open-meteo.com" if is_ext else "https://mausam.imd.gov.in"),
                source_tier=loc.get("source_tier") or ("tier_2_open_api" if is_ext else "tier_3_curated_catalog"),
                retrieval_timestamp=loc.get("retrieval_timestamp") or result.get("retrieval_timestamp"),
                data_timestamp=loc.get("data_timestamp"),
                location=loc.get("location"),
                disclaimer=loc.get("disclaimer"),
                domain="weather",
            ))
        if records:
            return records

    # Case 3: Single location result
    f_stat = result.get("freshness_status", "fallback")
    s_type = result.get("source_type") or (
        SourceType.LIVE_API.value if f_stat == "live" else (
            SourceType.CACHED_API.value if f_stat in ("cached", "stale") else SourceType.CURATED_DATA.value
        )
    )
    v_stat = result.get("verification_status") or (
        VerificationStatus.VERIFIED_EXTERNAL_API.value if f_stat in ("live", "cached") else (
            VerificationStatus.UNVERIFIED.value if f_stat == "stale" else VerificationStatus.VERIFIED_CURATED_SOURCE.value
        )
    )
    is_ext = s_type in ("live_api", "cached_api")

    records.append(create_provenance(
        source_name=result.get("source_name") or ("Open-Meteo Weather API" if is_ext else "IMD Katra Climatological Normals"),
        source_type=s_type,
        freshness_status=f_stat,
        verification_status=v_stat,
        source_url=result.get("source_url") or ("https://open-meteo.com" if is_ext else "https://mausam.imd.gov.in"),
        source_tier=result.get("source_tier") or ("tier_2_open_api" if is_ext else "tier_3_curated_catalog"),
        retrieval_timestamp=result.get("retrieval_timestamp"),
        data_timestamp=result.get("data_timestamp"),
        location=result.get("location") or result.get("canonical_location"),
        disclaimer=result.get("disclaimer"),
        domain="weather",
    ))
    return records


def extract_provenance_from_rag(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts provenance from search_yatra_knowledge RAG tool results."""
    records: List[Dict[str, Any]] = []
    sources = result.get("sources") or []

    for s in sources:
        if not isinstance(s, dict):
            continue
        s_name = s.get("source_name") or s.get("title") or "Yatra Knowledge Base"
        s_url = s.get("source_url")
        notes = s.get("source_notes", "")
        v_stat = s.get("verification_status", "")

        is_official = "official" in notes.lower() or "maavaishnodevi.org" in (s_url or "").lower() or "official" in v_stat.lower()

        records.append(create_provenance(
            source_name=s_name,
            source_type=SourceType.STATIC_RAG,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE if is_official else VerificationStatus.VERIFIED_CURATED_SOURCE,
            source_url=s_url,
            source_tier="tier_1_official" if is_official else "tier_3_curated_catalog",
            retrieval_timestamp=result.get("retrieved_at"),
            location=result.get("location"),
            domain=s.get("domain") or result.get("knowledge_domain"),
            notes=s.get("title"),
        ))

    if not records and result.get("disclaimer"):
        # Unsupported or ambiguous RAG query
        records.append(create_provenance(
            source_name="SMVDSB Official Portal (Consultation Baseline)",
            source_type=SourceType.STATIC_RAG,
            freshness_status=FreshnessStatus.UNAVAILABLE,
            verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE,
            source_url="https://www.maavaishnodevi.org",
            source_tier="tier_1_official",
            retrieval_timestamp=result.get("retrieved_at"),
            disclaimer=result.get("disclaimer"),
            domain=result.get("knowledge_domain") or "general",
        ))

    return records


def extract_provenance_from_tool_result(tool_name: str, result: Any) -> List[Dict[str, Any]]:
    """Extracts standardized provenance records from any Central AI Agent tool result."""
    if not isinstance(result, dict):
        return []

    # Check for execution failure
    if result.get("status") in ("failed", "timeout", "invalid_tool_response") or result.get("error"):
        return [create_provenance(
            source_name=f"Tool Execution ({tool_name})",
            source_type=SourceType.UNKNOWN_SOURCE,
            freshness_status=FreshnessStatus.UNAVAILABLE,
            verification_status=VerificationStatus.UNVERIFIED,
            disclaimer=str(result.get("error", "Tool execution failed")),
        )]

    if tool_name == "check_weather_guidance":
        return extract_provenance_from_weather(result)

    elif tool_name == "search_yatra_knowledge":
        return extract_provenance_from_rag(result)

    elif tool_name == "get_tourism_knowledge":
        place = result.get("place") or result.get("query")
        return [create_provenance(
            source_name="Yatra AI Regional Tourism Catalog",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
            source_tier="tier_3_curated_catalog",
            location=place,
            domain="tourism",
            notes=f"Category: {result.get('category', 'Pilgrimage')}",
        )]

    elif tool_name == "search_transport_options":
        return [create_provenance(
            source_name="Regional Transport Timetable Dataset",
            source_type=SourceType.INDICATIVE_DATA,
            freshness_status=FreshnessStatus.CACHED,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
            source_tier="tier_3_curated_catalog",
            location=f"{result.get('origin', 'Origin')} to Katra",
            domain="transport",
            disclaimer="Indicative transport schedules from demonstration database; check IRCTC/airlines for live status.",
        )]

    elif tool_name == "evaluate_yatra_plan":
        records = [
            create_provenance(
                source_name="Regional Transport Timetable Dataset",
                source_type=SourceType.INDICATIVE_DATA,
                freshness_status=FreshnessStatus.CACHED,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_tier="tier_3_curated_catalog",
                domain="transport",
                disclaimer="Indicative transport schedules from demonstration database.",
            ),
            create_provenance(
                source_name="Katra Accommodation Directory",
                source_type=SourceType.CURATED_DATA,
                freshness_status=FreshnessStatus.CACHED,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_tier="tier_3_curated_catalog",
                location="Katra",
                domain="accommodation",
                disclaimer="Indicative hotel base tariffs; subject to seasonal demand and direct booking.",
            ),
        ]
        return records

    elif tool_name == "modify_itinerary":
        return [create_provenance(
            source_name="Yatra AI Custom Itinerary Engine",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_INTERNAL_KNOWLEDGE,
            source_tier="tier_3_curated_catalog",
            domain="itinerary",
        )]

    elif tool_name == "check_slot_availability":
        return [create_provenance(
            source_name="Local Sandboxed Mock Yatra Booking Portal",
            source_type=SourceType.SIMULATED_DATA,
            freshness_status=FreshnessStatus.SIMULATED,
            verification_status=VerificationStatus.SIMULATION_ONLY,
            source_tier="tier_4_simulation",
            domain="darshan_availability",
            disclaimer="Simulated demonstration portal data; not an official Shri Mata Vaishno Devi Shrine Board reservation.",
        )]

    elif tool_name == "request_booking_intent":
        return [create_provenance(
            source_name="Yatra AI Booking Handoff Gate",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_INTERNAL_KNOWLEDGE,
            domain="booking_handoff",
            notes="Booking review initiated; human confirmation gate required.",
        )]

    elif tool_name == "execute_authorized_booking":
        return [create_provenance(
            source_name="Local Sandboxed Mock Yatra Booking Portal (Playwright RPA)",
            source_type=SourceType.SIMULATED_DATA,
            freshness_status=FreshnessStatus.SIMULATED,
            verification_status=VerificationStatus.SIMULATION_ONLY,
            source_tier="tier_4_simulation",
            domain="booking_execution",
            disclaimer="Simulated demonstration booking; no financial transaction or real Shrine Board booking occurred.",
        )]

    elif tool_name == "search_accommodation_options":
        return [create_provenance(
            source_name="Verified Katra Accommodation Catalog",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
            source_tier="tier_3_curated_catalog",
            location="Katra",
            domain="accommodation",
            disclaimer="Tariffs are published indicative schedules. Real-time availability is NOT_CHECKED.",
        )]

    elif tool_name == "query_operational_notices":
        records = []
        for n in (result.get("notices") or []):
            auth = n.get("issuing_authority") or "Official Shrine Board / State Authority"
            records.append(create_provenance(
                source_name=auth,
                source_type=SourceType.CURATED_DATA,
                freshness_status=FreshnessStatus.NOT_APPLICABLE,
                verification_status=n.get("verification_status") or VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_url=n.get("source_url") or "https://www.maavaishnodevi.org",
                source_tier="tier_1_official" if "shrine board" in auth.lower() else "tier_2_state_authority",
                location=n.get("affected_location"),
                domain="operational_notice",
                disclaimer="Curated official administrative notice. Ground conditions may change rapidly.",
                notes=f"Lifecycle: {n.get('notice_lifecycle_status')}; Route: {n.get('affected_route')}",
            ))
        if not records:
            records.append(create_provenance(
                source_name=result.get("source_name") or "Curated Vaishno Devi Operational Notices Registry",
                source_type=result.get("source_type") or SourceType.CURATED_DATA,
                freshness_status=result.get("freshness_status") or FreshnessStatus.NOT_APPLICABLE,
                verification_status=result.get("verification_status") or VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_tier="tier_2_state_authority",
                domain="operational_notice",
                disclaimer=result.get("disclaimer") or "No active disruption notices recorded in curated registry.",
            ))
        return records

    elif tool_name == "lookup_verified_contacts":
        records = []
        for c in (result.get("contacts") or []):
            records.append(create_provenance(
                source_name=c.get("organization") or "Verified Contact Registry",
                source_type=SourceType.CURATED_DATA,
                freshness_status=FreshnessStatus.NOT_APPLICABLE,
                verification_status=c.get("verification_status") or VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_url=c.get("source_url") or "https://112.gov.in",
                source_tier="tier_1_official" if c.get("is_primary_emergency") else "tier_2_state_authority",
                location=c.get("geographic_jurisdiction"),
                domain="emergency",
                disclaimer="Direct authority helpline. For urgent emergencies, dial 112 directly.",
            ))
        if not records:
            records.append(create_provenance(
                source_name="Verified Authority Contact Registry",
                source_type=SourceType.CURATED_DATA,
                freshness_status=FreshnessStatus.NOT_APPLICABLE,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE,
                source_url="https://112.gov.in",
                source_tier="tier_1_official",
                domain="emergency",
                disclaimer="Direct authority helpline. For urgent emergencies, dial 112 directly.",
            ))
        return records

    return []


# -----------------------------------------------------------------------------
# 5. UNIFIED RESPONSE ENVELOPE ATTACHER
# -----------------------------------------------------------------------------

def attach_provenance_to_response(
    response: Dict[str, Any],
    tool_executions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Attaches standardized source_provenance and live_sources fields to a response envelope
    while strictly preserving every existing field (reply, intent, status, session_id, request,
    plan, itinerary, recommendation, action, hotel, budget_evaluation, knowledge_sources, etc.).
    """
    if not isinstance(response, dict):
        return response

    collected_provenance: List[Dict[str, Any]] = []

    # 1. Collect from explicit tool_executions passed or stored in response
    executions = tool_executions or response.get("tool_executions") or []
    for exec_info in executions:
        if not isinstance(exec_info, dict):
            continue
        t_name = exec_info.get("tool", "")
        t_result = exec_info.get("result") or exec_info.get("results")
        records = extract_provenance_from_tool_result(t_name, t_result)
        collected_provenance.extend(records)

    # 2. Check for weather payload directly attached to response
    if "weather" in response and isinstance(response["weather"], dict):
        collected_provenance.extend(extract_provenance_from_weather(response["weather"]))

    # 3. Check for knowledge_sources directly attached to response
    if "knowledge_sources" in response and isinstance(response["knowledge_sources"], list):
        rag_sim_result = {
            "sources": response["knowledge_sources"],
            "retrieved_at": response.get("retrieved_at") or get_utc_now_iso(),
            "location": response.get("last_tourism_place"),
        }
        collected_provenance.extend(extract_provenance_from_rag(rag_sim_result))

    # 4. Check for availability or booking directly attached
    if "availability_result" in response and isinstance(response["availability_result"], dict):
        collected_provenance.extend(extract_provenance_from_tool_result("check_slot_availability", response["availability_result"]))
    if "rpa_execution" in response and isinstance(response["rpa_execution"], dict):
        collected_provenance.extend(extract_provenance_from_tool_result("execute_authorized_booking", response["rpa_execution"]))
    if "operational_notices" in response and isinstance(response["operational_notices"], dict):
        collected_provenance.extend(extract_provenance_from_tool_result("query_operational_notices", response["operational_notices"]))
    if "verified_contacts" in response and isinstance(response["verified_contacts"], dict):
        collected_provenance.extend(extract_provenance_from_tool_result("lookup_verified_contacts", response["verified_contacts"]))

    # 5. If response is a plan or itinerary without tools
    if response.get("plan") and not collected_provenance:
        collected_provenance.extend(extract_provenance_from_tool_result("evaluate_yatra_plan", response["plan"]))

    # 6. Default internal conversational provenance if no tool provenance was extracted
    if not collected_provenance:
        intent = response.get("intent", "GENERAL")
        collected_provenance.append(create_provenance(
            source_name="Yatra AI Conversational Assistant",
            source_type=SourceType.CURATED_DATA,
            freshness_status=FreshnessStatus.NOT_APPLICABLE,
            verification_status=VerificationStatus.VERIFIED_INTERNAL_KNOWLEDGE,
            source_tier="tier_3_curated_catalog",
            domain=intent.lower() if intent else "conversational",
        ))

    # Deduplicate while preserving distinct sources and locations
    deduped = deduplicate_provenance(collected_provenance)

    # Identify purely live external sources
    live_records = [
        r for r in deduped
        if r.get("freshness_status") == FreshnessStatus.LIVE.value
        and r.get("source_type") == SourceType.LIVE_API.value
    ]

    response["source_provenance"] = deduped
    response["live_sources"] = live_records

    return response
