"""
services/bus_schedules.py
Curated Bus Timetable & Service Registry for Yatra AI.

Provides authoritative, human-verified public bus schedules and feeder route guidance
connecting Jammu (General Bus Stand & Railway Station Rail Head), Udhampur, and Delhi ISBT
to Shri Mata Vaishno Devi Katra Central Bus Stand.

Adheres strictly to truth-in-data principles:
- Schedules reflect official published JKRTC timetable windows and J&K State Transport Authority (STA) statutory stage carriage fare slabs.
- Live GPS tracking, real-time dynamic seat reservations, and synthetic minute-level timetables are NOT claimed.
- Fail-closed handling on missing, corrupt, or unverified records.
"""

from datetime import datetime
import json
import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import CuratedBusSchedule
from utils.provenance import VerificationStatus

logger = logging.getLogger(__name__)

DEFAULT_BUS_SCHEDULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "curated_bus_schedules.json",
)

_CACHE_LOCK = threading.RLock()
_CACHED_PATH: Optional[str] = None
_CACHED_SCHEDULES: List[CuratedBusSchedule] = []
_CACHED_METADATA: Dict[str, Any] = {}
_CACHED_MTIME: float = 0.0


def load_curated_bus_schedules(
    file_path: Optional[str] = None,
    force_reload: bool = False,
) -> Tuple[List[CuratedBusSchedule], Dict[str, Any]]:
    """Loads and caches curated bus schedules and metadata from JSON file.

    Returns:
        Tuple of (List[CuratedBusSchedule], Dict[str, Any] metadata).
        Returns empty list on file error or corruption.
    """
    global _CACHED_PATH, _CACHED_SCHEDULES, _CACHED_METADATA, _CACHED_MTIME

    path = file_path or DEFAULT_BUS_SCHEDULES_PATH

    with _CACHE_LOCK:
        if not os.path.exists(path):
            logger.warning("Curated bus schedules file not found at: %s", path)
            return [], {"error": "FILE_NOT_FOUND", "path": path}

        try:
            mtime = os.path.getmtime(path)
            if not force_reload and _CACHED_PATH == path and _CACHED_MTIME == mtime:
                return list(_CACHED_SCHEDULES), dict(_CACHED_METADATA)

            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if not isinstance(raw, dict):
                logger.error("Curated bus schedules root must be a JSON dictionary: %s", path)
                return [], {"error": "INVALID_FORMAT", "path": path}

            raw_meta = raw.get("metadata", {})
            raw_schedules = raw.get("schedules", [])

            schedules: List[CuratedBusSchedule] = []
            for r in raw_schedules:
                if not isinstance(r, dict) or "service_id" not in r:
                    continue

                v_stat = r.get("verification_status", VerificationStatus.UNVERIFIED.value)
                src_name = r.get("source_name")
                src_url = r.get("source_url")
                src_ref = r.get("source_circular_reference")
                v_by = r.get("verified_by")
                v_at = r.get("verified_at")

                # Fail-closed: missing source provenance cannot claim VERIFIED_CURATED_SOURCE
                if not (src_name and src_url and src_ref and v_by and v_at):
                    v_stat = VerificationStatus.UNVERIFIED.value

                schedules.append(
                    CuratedBusSchedule(
                        service_id=str(r.get("service_id", "")).strip(),
                        operator_name=str(r.get("operator_name", "")).strip(),
                        service_type=str(r.get("service_type", "")).strip(),
                        origin_bus_stand=str(r.get("origin_bus_stand", "")).strip(),
                        destination_bus_stand=str(r.get("destination_bus_stand", "")).strip(),
                        origin_city=str(r.get("origin_city", "")).strip(),
                        destination_city=str(r.get("destination_city", "")).strip(),
                        route_description=r.get("route_description"),
                        operating_hours=r.get("operating_hours"),
                        frequency_minutes=r.get("frequency_minutes"),
                        departure_window=r.get("departure_window"),
                        departure_time=r.get("departure_time"),
                        arrival_time=r.get("arrival_time"),
                        duration_hours=r.get("duration_hours"),
                        indicative_fare_min=r.get("indicative_fare_min"),
                        indicative_fare_max=r.get("indicative_fare_max"),
                        fare_classification=r.get("fare_classification", "STATUTORY_NOTIFIED_PER_KM_SLAB"),
                        fare_disclaimer=r.get(
                            "fare_disclaimer",
                            "Governed by J&K State Transport Authority Notification No. 01-P-MVD of 2026. "
                            "Ordinary stage carriage passenger tariff approximately subject to vehicle category and highway toll. "
                            "Purchase tickets directly at bus stand counter."
                        ),
                        helpline_numbers=r.get("helpline_numbers", []),
                        source_name=src_name or "Unknown Source",
                        source_url=src_url,
                        source_circular_reference=src_ref,
                        verified_at=v_at,
                        verified_by=v_by,
                        verification_status=v_stat,
                        is_live_status=False,  # Explicit fail-safe: never live tracking
                        notes=r.get("notes"),
                        route_verification=r.get("route_verification"),
                        operator_verification=r.get("operator_verification"),
                        timetable_verification=r.get("timetable_verification"),
                        fare_verification=r.get("fare_verification"),
                    )
                )

            _CACHED_PATH = path
            _CACHED_MTIME = mtime
            _CACHED_SCHEDULES = schedules
            _CACHED_METADATA = raw_meta

            return list(_CACHED_SCHEDULES), dict(_CACHED_METADATA)

        except Exception as exc:
            logger.error("Failed loading curated bus schedules from %s: %s", path, exc)
            return [], {"error": "LOAD_FAILURE", "message": str(exc), "path": path}


def search_curated_bus_schedules(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    service_id: Optional[str] = None,
    travel_date: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Tuple[List[CuratedBusSchedule], Dict[str, Any]]:
    """Searches curated bus schedules matching origin, destination, or service_id.

    Args:
        origin: City name (e.g. 'Jammu', 'Delhi', 'Udhampur') or bus stand name.
        destination: City name (e.g. 'Katra') or bus stand name.
        service_id: Specific bus service ID.
        travel_date: Optional ISO date string (YYYY-MM-DD).
        file_path: Optional path to override dataset.

    Returns:
        Tuple of (filtered List[CuratedBusSchedule], metadata dict).
        If origin is supplied but route is not in curated registry, populates
        coverage_limitation metadata.
    """
    schedules, metadata = load_curated_bus_schedules(file_path=file_path)

    if not schedules:
        return [], metadata

    def _matches_location(loc_query: str, city: str, bus_stand: str) -> bool:
        q = loc_query.strip().lower()
        c = city.strip().lower()
        stand = bus_stand.strip().lower()

        # If query explicitly indicates a village, settlement, or nearby area, fail direct match
        if any(w in q for w in ("village", "near", "rural", "settlement", "hamlet", "outskirts")):
            return False

        if q == c or q in stand:
            return True

        # Token match: e.g. "mandi" in "mandi isbt"
        if re.search(r'\b' + re.escape(c) + r'\b', q) and not any(w in q for w in ("from", "to", "via", "near")):
            return True

        # Common aliases
        aliases = {
            "delhi": ["delhi", "new delhi", "isbt", "kashmiri gate", "kashmere gate", "ndls"],
            "katra": ["katra", "central bus stand", "svdk", "shri mata vaishno devi"],
            "jammu": ["jammu", "jammu tawi", "gbs", "general bus stand", "rail head", "jat"],
            "udhampur": ["udhampur", "uhp", "battal"],
            "chandigarh": ["chandigarh", "cdg", "isbt 43", "isbt sector 43"],
            "amritsar": ["amritsar", "asr", "amritsar isbt"],
            "shimla": ["shimla", "simla", "isbt tutikandi"],
            "dharamshala": ["dharamshala", "dharamsala", "mcleodganj"],
            "manali": ["manali"],
            "mandi": ["mandi"],
            "pathankot": ["pathankot", "ptk", "ptkc"],
            "srinagar": ["srinagar", "sxr"],
            "jalandhar": ["jalandhar", "jrc"],
            "ludhiana": ["ludhiana", "ldh"],
        }
        for alias_key, alias_vals in aliases.items():
            if q == alias_key or any(v == q for v in alias_vals):
                if c == alias_key or any(v in c or v in stand for v in alias_vals):
                    return True
        return False

    filtered: List[CuratedBusSchedule] = []
    for s in schedules:
        # Match service ID
        if service_id:
            sid = str(service_id).strip().lower()
            if sid != s.service_id.lower() and sid not in s.service_id.lower():
                continue

        # Match origin
        if origin:
            if not _matches_location(origin, s.origin_city, s.origin_bus_stand):
                continue

        # Match destination
        if destination:
            if not _matches_location(destination, s.destination_city, s.destination_bus_stand):
                continue

        filtered.append(s)

    meta_copy = dict(metadata)
    if origin and not filtered:
        meta_copy["coverage_limitation"] = {
            "status": "ROUTE_NOT_IN_CURATED_BUS_REGISTRY",
            "origin": origin,
            "destination": destination or "Katra",
            "message": (
                f"No verified public bus services found in the curated Katra/Jammu bus registry for origin '{origin}'. "
                "Curated bus coverage is currently limited to verified corridors connecting Jammu (General Bus Stand & Rail Head), "
                "Udhampur, and Delhi ISBT to Katra. For other origins, pilgrims should travel by train/flight to Jammu or Delhi "
                "and connect via high-frequency local feeder buses or JKRTC pilgrim services."
            ),
            "supported_origins": [
                "Jammu (General Bus Stand)",
                "Jammu (Railway Station Rail Head)",
                "Udhampur (Bus Stand)",
                "Delhi (ISBT Kashmiri Gate)",
            ],
        }

    return filtered, meta_copy


def get_bus_service_by_id(
    service_id: str,
    file_path: Optional[str] = None,
) -> Optional[CuratedBusSchedule]:
    """Retrieves a single curated bus service by its unique service_id."""
    schedules, _ = load_curated_bus_schedules(file_path=file_path)
    sid = str(service_id).strip().lower()
    for s in schedules:
        if s.service_id.lower() == sid:
            return s
    return None


def get_bus_service_summary(
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Provides a high-level summary of curated bus corridors."""
    schedules, metadata = load_curated_bus_schedules(file_path=file_path)
    return {
        "total_corridors": len(schedules),
        "supported_origins": list(sorted({s.origin_city for s in schedules})),
        "destinations": list(sorted({s.destination_city for s in schedules})),
        "operators": list(sorted({s.operator_name for s in schedules})),
        "service_types": list(sorted({s.service_type for s in schedules})),
        "metadata": metadata,
    }
