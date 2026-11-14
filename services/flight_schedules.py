"""
services/flight_schedules.py
Curated Flight Timetable & Service Registry for Yatra AI.

Provides authoritative, human-verified domestic passenger flight route guidance
connecting nationwide origins to Jammu Airport (IXJ / Satwari) — the nearest
airport serving the Shri Mata Vaishno Devi pilgrimage in Katra (~50 km via NH-44/NH-144).

Adheres strictly to truth-in-data principles:
- Schedules reflect official published DGCA seasonal timetables and scheduled carrier operations.
- Live GPS/ADS-B telemetry, seat count reservations, and dynamic surge airfares are NOT claimed.
- Fail-closed handling on missing, corrupt, or unverified records.
"""

from datetime import datetime
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import CuratedFlightSchedule
from utils.provenance import VerificationStatus

logger = logging.getLogger(__name__)

DEFAULT_FLIGHT_SCHEDULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "curated_flight_schedules.json",
)

_CACHE_LOCK = threading.RLock()
_CACHED_PATH: Optional[str] = None
_CACHED_SCHEDULES: List[CuratedFlightSchedule] = []
_CACHED_METADATA: Dict[str, Any] = {}
_CACHED_AIRPORTS: List[Dict[str, Any]] = []
_CACHED_MTIME: float = 0.0


# Normalization dictionary mapping city names, abbreviations, and IATA codes
_CITY_AIRPORT_MAP: Dict[str, str] = {
    # Delhi
    "del": "DEL",
    "delhi": "DEL",
    "new delhi": "DEL",
    "indira gandhi": "DEL",
    "igi": "DEL",
    # Mumbai
    "bom": "BOM",
    "mumbai": "BOM",
    "bombay": "BOM",
    "csmia": "BOM",
    # Srinagar
    "sxr": "SXR",
    "srinagar": "SXR",
    # Bengaluru
    "blr": "BLR",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "kempegowda": "BLR",
    # Hyderabad
    "hyd": "HYD",
    "hyderabad": "HYD",
    "secunderabad": "HYD",
    # Kolkata
    "ccu": "CCU",
    "kolkata": "CCU",
    "calcutta": "CCU",
    # Ahmedabad
    "amd": "AMD",
    "ahmedabad": "AMD",
    # Chennai
    "maa": "MAA",
    "chennai": "MAA",
    "madras": "MAA",
    # Pune
    "pnq": "PNQ",
    "pune": "PNQ",
    # Lucknow
    "lko": "LKO",
    "lucknow": "LKO",
    # Jaipur
    "jai": "JAI",
    "jaipur": "JAI",
    # Chandigarh
    "ixc": "IXC",
    "chandigarh": "IXC",
    # Amritsar
    "atq": "ATQ",
    "amritsar": "ATQ",
    # Jammu / Katra destination
    "ixj": "IXJ",
    "jammu": "IXJ",
    "satwari": "IXJ",
    "katra": "IXJ",
    "vaishno devi": "IXJ",
    "shri mata vaishno devi": "IXJ",
}


def normalize_airport_or_city(query: Optional[str]) -> Optional[str]:
    """Normalizes an airport code, city name, or variant into its standard IATA code."""
    if not query:
        return None
    cleaned = query.strip().lower()
    return _CITY_AIRPORT_MAP.get(cleaned, cleaned.upper() if len(cleaned) == 3 else query.strip())


def load_curated_flight_schedules(
    file_path: Optional[str] = None,
    force_reload: bool = False,
) -> Tuple[List[CuratedFlightSchedule], Dict[str, Any]]:
    """Loads and caches curated flight schedules and metadata from JSON file.

    Returns:
        Tuple of (List[CuratedFlightSchedule], Dict[str, Any] metadata).
        Returns empty list on file error or corruption.
    """
    global _CACHED_PATH, _CACHED_SCHEDULES, _CACHED_METADATA, _CACHED_AIRPORTS, _CACHED_MTIME

    path = file_path or DEFAULT_FLIGHT_SCHEDULES_PATH

    with _CACHE_LOCK:
        if not os.path.exists(path):
            logger.warning("Curated flight schedules file not found at: %s", path)
            return [], {"error": "FILE_NOT_FOUND", "path": path}

        try:
            mtime = os.path.getmtime(path)
            if not force_reload and _CACHED_PATH == path and _CACHED_MTIME == mtime:
                return list(_CACHED_SCHEDULES), dict(_CACHED_METADATA)

            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if not isinstance(raw, dict):
                logger.error("Curated flight schedules root must be a JSON dictionary: %s", path)
                return [], {"error": "INVALID_FORMAT", "path": path}

            raw_schedules = raw.get("schedules", [])
            metadata = raw.get("metadata", {})
            airports = raw.get("airports", [])

            schedules: List[CuratedFlightSchedule] = []
            for item in raw_schedules:
                try:
                    sch = CuratedFlightSchedule(**item)
                    schedules.append(sch)
                except Exception as exc:
                    logger.error(
                        "Failed to parse flight schedule record '%s': %s",
                        item.get("route_id", "UNKNOWN"),
                        exc,
                    )

            _CACHED_PATH = path
            _CACHED_SCHEDULES = schedules
            _CACHED_METADATA = metadata
            _CACHED_AIRPORTS = airports
            _CACHED_MTIME = mtime

            logger.info(
                "Successfully loaded %d curated flight schedules from %s",
                len(schedules),
                path,
            )
            return list(_CACHED_SCHEDULES), dict(_CACHED_METADATA)

        except Exception as exc:
            logger.error("Error reading curated flight schedules from %s: %s", path, exc)
            return [], {"error": "READ_ERROR", "details": str(exc), "path": path}


def search_curated_flight_schedules(
    origin: Optional[str] = None,
    destination: Optional[str] = "Jammu",
    travel_date: Optional[str] = None,
    route_type: Optional[str] = None,
    dataset_path: Optional[str] = None,
) -> Tuple[List[CuratedFlightSchedule], Dict[str, Any]]:
    """Searches curated flight schedules matching origin, destination, and travel date.

    Adheres to fail-closed principles:
    - Normalizes origin/destination names and airport codes.
    - If origin is unsupported, returns empty list without defaulting to Delhi.
    - Checks operating days if a travel_date is specified.

    Returns:
        Tuple of (matching_schedules, search_metadata).
    """
    all_schedules, metadata = load_curated_flight_schedules(file_path=dataset_path)

    if not all_schedules:
        return [], {
            "query": {"origin": origin, "destination": destination, "travel_date": travel_date},
            "total_matches": 0,
            "status": "REGISTRY_UNAVAILABLE",
            "metadata": metadata,
        }

    # Normalize destination (defaults to IXJ/Jammu)
    norm_dest = normalize_airport_or_city(destination) or "IXJ"

    # If origin is missing, fail closed and request clarification
    if not origin or not str(origin).strip():
        return [], {
            "query": {"origin": origin, "destination": destination, "travel_date": travel_date},
            "total_matches": 0,
            "status": "ORIGIN_REQUIRED",
            "message": "Origin city or airport is required to search flight routes.",
            "metadata": metadata,
        }

    norm_origin = normalize_airport_or_city(origin)

    # Determine day of week if travel_date is provided
    day_name: Optional[str] = None
    if travel_date:
        try:
            dt = datetime.fromisoformat(travel_date.replace("Z", "+00:00"))
            day_name = dt.strftime("%a")  # e.g., 'Mon', 'Tue'
        except Exception:
            pass

    matches: List[CuratedFlightSchedule] = []
    for s in all_schedules:
        # Match destination (IXJ / Jammu / Katra)
        dest_match = (
            s.destination_airport_code.upper() == norm_dest.upper()
            or s.destination_city.lower() == (destination or "").lower()
            or (norm_dest.upper() == "IXJ" and s.destination_airport_code.upper() == "IXJ")
        )
        if not dest_match:
            continue

        # Match origin
        origin_code = s.origin_airport_code.upper()
        origin_city = s.origin_city.lower()
        query_origin_raw = (origin or "").strip().lower()

        origin_match = (
            origin_code == norm_origin.upper()
            or origin_city == query_origin_raw
            or query_origin_raw in origin_city
            or (norm_origin.upper() == "DEL" and origin_code == "DEL")
            or (norm_origin.upper() == "BOM" and origin_code == "BOM")
            or (norm_origin.upper() == "BLR" and origin_code == "BLR")
            or (norm_origin.upper() == "SXR" and origin_code == "SXR")
            or (norm_origin.upper() == "HYD" and origin_code == "HYD")
            or (norm_origin.upper() == "CCU" and origin_code == "CCU")
            or (norm_origin.upper() == "AMD" and origin_code == "AMD")
            or (norm_origin.upper() == "MAA" and origin_code == "MAA")
            or (norm_origin.upper() == "PNQ" and origin_code == "PNQ")
            or (norm_origin.upper() == "LKO" and origin_code == "LKO")
            or (norm_origin.upper() == "JAI" and origin_code == "JAI")
            or (norm_origin.upper() == "IXC" and origin_code == "IXC")
            or (norm_origin.upper() == "ATQ" and origin_code == "ATQ")
        )
        if not origin_match:
            continue

        # Route type filter if specified
        if route_type:
            rt_req = route_type.upper()
            if rt_req == "CONNECTING":
                if s.route_type.upper() != "CONNECTING" and s.schedule_type != "CONNECTING_HUB_GUIDANCE":
                    continue
            elif s.route_type.upper() != rt_req:
                continue

        # Operating day filter if travel_date was supplied
        if day_name and s.operating_days:
            is_daily = any(d.lower() in ("daily", "all") for d in s.operating_days)
            if not is_daily and not any(day_name.lower() in d.lower() for d in s.operating_days):
                continue

        matches.append(s)

    status = "SUCCESS" if matches else "ROUTE_NOT_IN_CURATED_REGISTRY"
    message = (
        f"Found {len(matches)} curated flight schedule(s) for {origin} -> Jammu (IXJ)."
        if matches
        else f"Direct or connecting flight guidance from {origin} to Jammu (IXJ) is not available in the curated registry. Consider travelling via New Delhi hub or checking direct railway options."
    )

    return matches, {
        "query": {
            "origin": origin,
            "normalized_origin": norm_origin,
            "destination": destination,
            "normalized_destination": norm_dest,
            "travel_date": travel_date,
            "route_type": route_type,
        },
        "total_matches": len(matches),
        "status": status,
        "message": message,
        "ground_transfer_advisory": (
            "Jammu Airport (IXJ) is situated approximately 50 km from Katra base camp (~1.5 hours). "
            "Authorized Prepaid Taxis operate directly from the airport terminal arrivals booth. "
            "Public JKRTC buses depart from Jammu Railway Station / General Bus Stand (~8 km from the airport)."
        ),
        "metadata": metadata,
    }
