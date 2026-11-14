import re
"""
services/railway_schedules.py
Curated Railway Timetable & Station Registry Service for Yatra AI.

Provides authoritative, human-verified timetable schedules for major train services
connecting New Delhi, Western India, Central India, and Uttarakhand to
Shri Mata Vaishno Devi Katra (SVDK) and Jammu Tawi (JAT).

Adheres strictly to truth-in-data principles:
- Timetables reflect official published Indian Railways operational schedules.
- Live running status, GPS tracking, and real-time platform allocations are NOT claimed.
- Fail-closed handling on missing, corrupt, or unverified records.
"""

from datetime import datetime
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import (
    CuratedTrainSchedule,
    StationInfo,
)
from utils.provenance import (
    VerificationStatus,
)

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "curated_railway_schedules.json",
)

_CACHE_LOCK = threading.RLock()
_CACHED_PATH: Optional[str] = None
_CACHED_SCHEDULES: List[CuratedTrainSchedule] = []
_CACHED_STATIONS: List[StationInfo] = []
_CACHED_METADATA: Dict[str, Any] = {}
_CACHED_MTIME: float = 0.0

# Standard 3-letter day abbreviations matching Python datetime.weekday()
_WEEKDAY_MAP = {
    0: "MON",
    1: "TUE",
    2: "WED",
    3: "THU",
    4: "FRI",
    5: "SAT",
    6: "SUN",
}


def load_curated_schedules(
    file_path: Optional[str] = None,
    force_reload: bool = False,
) -> Tuple[List[CuratedTrainSchedule], List[StationInfo], Dict[str, Any]]:
    """Loads and caches curated train schedules and station information from JSON file.

    Returns:
        Tuple of (List[CuratedTrainSchedule], List[StationInfo], Dict[str, Any] metadata).
        Returns empty lists on file error or corruption.
    """
    global _CACHED_PATH, _CACHED_SCHEDULES, _CACHED_STATIONS, _CACHED_METADATA, _CACHED_MTIME

    path = file_path or DEFAULT_SCHEDULES_PATH

    with _CACHE_LOCK:
        if not os.path.exists(path):
            logger.warning("Curated railway schedules file not found at: %s", path)
            return [], [], {"error": "FILE_NOT_FOUND", "path": path}

        try:
            mtime = os.path.getmtime(path)
            if not force_reload and _CACHED_PATH == path and _CACHED_MTIME == mtime:
                return list(_CACHED_SCHEDULES), list(_CACHED_STATIONS), dict(_CACHED_METADATA)

            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if not isinstance(raw, dict):
                logger.error("Curated railway schedules root must be a JSON dictionary: %s", path)
                return [], [], {"error": "INVALID_FORMAT", "path": path}

            raw_meta = raw.get("metadata", {})
            raw_stations = raw.get("stations", [])
            raw_schedules = raw.get("schedules", [])

            # Parse StationInfo instances
            stations: List[StationInfo] = []
            for s in raw_stations:
                if not isinstance(s, dict) or "station_code" not in s:
                    continue
                stations.append(
                    StationInfo(
                        station_code=str(s.get("station_code", "")).strip().upper(),
                        station_name=str(s.get("station_name", "")).strip(),
                        city=str(s.get("city", "")).strip(),
                        state=str(s.get("state", "")).strip(),
                        latitude=s.get("latitude"),
                        longitude=s.get("longitude"),
                        elevation_meters=s.get("elevation_meters"),
                        division=s.get("division"),
                        zone=s.get("zone"),
                    )
                )

            # Parse CuratedTrainSchedule instances
            schedules: List[CuratedTrainSchedule] = []
            for r in raw_schedules:
                if not isinstance(r, dict) or "train_number" not in r:
                    continue

                v_stat = r.get("verification_status", VerificationStatus.UNVERIFIED.value)
                # If record is missing source_name or source_url, it cannot claim VERIFIED_CURATED_SOURCE
                src_name = r.get("source_name")
                src_url = r.get("source_url")
                if not src_name or not src_url:
                    v_stat = VerificationStatus.UNVERIFIED.value

                schedules.append(
                    CuratedTrainSchedule(
                        train_number=str(r.get("train_number", "")).strip(),
                        train_name=str(r.get("train_name", "")).strip(),
                        origin_station_code=str(r.get("origin_station_code", "")).strip().upper(),
                        origin_station_name=str(r.get("origin_station_name", "")).strip(),
                        destination_station_code=str(r.get("destination_station_code", "")).strip().upper(),
                        destination_station_name=str(r.get("destination_station_name", "")).strip(),
                        departure_time=str(r.get("departure_time", "")).strip(),
                        arrival_time=str(r.get("arrival_time", "")).strip(),
                        days_of_operation=[d.strip().upper() for d in r.get("days_of_operation", []) if isinstance(d, str)],
                        travel_classes=[c.strip().upper() for c in r.get("travel_classes", []) if isinstance(c, str)],
                        major_halts=r.get("major_halts", []),
                        total_distance_km=r.get("total_distance_km"),
                        duration_hours=r.get("duration_hours"),
                        catering_available=r.get("catering_available"),
                        indicative_fare_min=r.get("indicative_fare_min"),
                        indicative_fare_max=r.get("indicative_fare_max"),
                        fare_classification=r.get("fare_classification", "UNAVAILABLE"),
                        fare_disclaimer=r.get(
                            "fare_disclaimer",
                            "Railway fares are unavailable in static demonstration registry. Real-time booking fares vary based on Tatkal quotas, dynamic surge pricing, and catering selections; check official IRCTC portal (irctc.co.in)."
                        ),
                        source_name=src_name or "Unknown Source",
                        source_url=src_url,
                        source_circular_reference=r.get("source_circular_reference"),
                        verified_at=r.get("verified_at"),
                        verified_by=r.get("verified_by"),
                        verification_status=v_stat,
                        is_live_status=False,  # Explicit fail-safe
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
            _CACHED_STATIONS = stations
            _CACHED_METADATA = raw_meta

            return list(_CACHED_SCHEDULES), list(_CACHED_STATIONS), dict(_CACHED_METADATA)

        except Exception as exc:
            logger.error("Failed loading curated railway schedules from %s: %s", path, exc)
            return [], [], {"error": "LOAD_FAILURE", "message": str(exc), "path": path}


def search_curated_schedules(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    train_number: Optional[str] = None,
    travel_date: Optional[str] = None,
    class_code: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Tuple[List[CuratedTrainSchedule], Dict[str, Any]]:
    """Searches curated train schedules matching origin, destination, train number, and operating day.

    Args:
        origin: Station code (e.g. 'NDLS', 'BDTS') or city name (e.g. 'Delhi', 'Mumbai').
        destination: Station code (e.g. 'SVDK', 'JAT') or city name (e.g. 'Katra', 'Jammu').
        train_number: Exact or partial train number (e.g. '22439').
        travel_date: ISO date string (YYYY-MM-DD) to check weekly operating day.
        class_code: Optional travel class filter (e.g. 'CC', '2A', 'SL').
        file_path: Optional override path for dataset.

    Returns:
        Tuple of (filtered List[CuratedTrainSchedule], metadata dict).
    """
    schedules, stations, metadata = load_curated_schedules(file_path=file_path)

    if not schedules:
        return [], metadata

    # Determine operating day of week if travel_date is supplied
    day_code: Optional[str] = None
    if travel_date:
        try:
            # Handle YYYY-MM-DD
            dt = datetime.fromisoformat(str(travel_date).split("T")[0])
            day_code = _WEEKDAY_MAP.get(dt.weekday())
        except Exception:
            logger.debug("Could not parse travel_date '%s' for operating day lookup.", travel_date)

    # Build station code/city lookup map for fuzzy matching
    city_to_codes: Dict[str, List[str]] = {}
    code_to_city: Dict[str, str] = {}
    for stn in stations:
        code_to_city[stn.station_code] = stn.city.lower()
        c_low = stn.city.lower()
        if c_low not in city_to_codes:
            city_to_codes[c_low] = []
        city_to_codes[c_low].append(stn.station_code)

    def _matches_location(loc_query: str, station_code: str, station_name: str) -> bool:
        q = loc_query.strip().lower()
        s_code = station_code.lower()
        s_name = station_name.lower()
        s_city = code_to_city.get(station_code, "")

        if q == s_code or q == s_city or (len(q) >= 4 and q in s_name) or re.search(r"\b" + re.escape(q) + r"\b", s_name):
            return True

        # Common city aliases with exact token matching to avoid substring collision (e.g. 'ju' in 'junction')
        aliases = {
            "delhi": ["ndls", "dli", "delhi", "new delhi"],
            "katra": ["svdk", "katra", "shri mata vaishno devi"],
            "jammu": ["jat", "jammu", "jammu tawi"],
            "mumbai": ["bdts", "mumbai", "bandra", "bombay", "csmt", "bct"],
            "indore": ["indb", "indore"],
            "rishikesh": ["ynrk", "rishikesh", "yog nagari"],
            "ambala": ["umb", "ambala"],
            "ludhiana": ["ldh", "ludhiana"],
            "udhampur": ["mctm", "uhp", "udhampur"],
            "amritsar": ["asr", "amritsar"],
            "chandigarh": ["cdg", "chandigarh"],
            "jalandhar": ["jrc", "juc", "jalandhar"],
            "jaipur": ["jp", "jaipur"],
            "jodhpur": ["ju", "jodhpur"],
            "ahmedabad": ["adi", "ahmedabad"],
            "bhopal": ["bpl", "bhopal"],
            "lucknow": ["lko", "lucknow"],
            "varanasi": ["bsb", "varanasi", "banaras", "kashi"],
            "patna": ["pnbe", "patna"],
            "haridwar": ["hw", "haridwar"],
            "pune": ["pune", "poona"],
            "kolkata": ["hwh", "sdah", "kolkata", "calcutta"],
            "bengaluru": ["sbc", "bengaluru", "bangalore"],
            "bangalore": ["sbc", "bengaluru", "bangalore"],
            "hyderabad": ["sc", "hyderabad", "secunderabad"],
        }
        for alias_key, alias_vals in aliases.items():
            if q == alias_key or any(v == q for v in alias_vals):
                for v in alias_vals:
                    if v == s_code or v == s_city:
                        return True
                    if len(v) >= 4 and v in s_name:
                        return True
                    if re.search(r"\b" + re.escape(v) + r"\b", s_name):
                        return True
        return False

    filtered: List[CuratedTrainSchedule] = []
    for s in schedules:
        # Match train number
        if train_number:
            tn = str(train_number).strip()
            if tn != s.train_number and tn not in s.train_number:
                continue

        # Match origin
        if origin:
            if not _matches_location(origin, s.origin_station_code, s.origin_station_name):
                # Also check intermediate halts for origin
                origin_matched = False
                for h in s.major_halts:
                    if isinstance(h, dict):
                        h_code = str(h.get("station_code", "")).strip().upper()
                        h_name = str(h.get("station_name", "")).strip()
                    else:
                        h_code = ""
                        h_name = str(h).strip()
                    if _matches_location(origin, h_code, h_name):
                        origin_matched = True
                        break
                if not origin_matched:
                    continue

        # Match destination
        if destination:
            if not _matches_location(destination, s.destination_station_code, s.destination_station_name):
                # Also check intermediate halts for destination
                dest_matched = False
                for h in s.major_halts:
                    if isinstance(h, dict):
                        h_code = str(h.get("station_code", "")).strip().upper()
                        h_name = str(h.get("station_name", "")).strip()
                    else:
                        h_code = ""
                        h_name = str(h).strip()
                    if _matches_location(destination, h_code, h_name):
                        dest_matched = True
                        break
                if not dest_matched:
                    continue

        # Match day of operation if applicable
        if day_code and s.days_of_operation:
            if day_code not in s.days_of_operation:
                continue

        # Match class code
        if class_code:
            c_target = class_code.strip().upper()
            if not any(c_target == c or c_target in c for c in s.travel_classes):
                continue

        filtered.append(s)

    meta_copy = dict(metadata)
    if origin and not filtered:
        meta_copy["coverage_limitation"] = {
            "status": "ROUTE_NOT_IN_CURATED_REGISTRY",
            "origin": origin,
            "destination": destination or "Katra",
            "message": (
                f"No direct verified express trains found in the curated Katra/Jammu railway timetable for origin '{origin}'. "
                "Curated verified routes currently cover primary corridors: New Delhi (NDLS), Mumbai (BDTS), Indore (INDB), "
                "Rishikesh (YNRK), Ambala (UMB), and Ludhiana (LDH). For other origins, pilgrims should check connecting trains "
                "via New Delhi or Jammu Tawi using IRCTC or call NTES at 139."
            ),
            "supported_origins": [
                "Delhi / New Delhi (NDLS)",
                "Mumbai (BDTS)",
                "Indore (INDB)",
                "Rishikesh (YNRK)",
                "Ambala Cantt (UMB)",
                "Ludhiana (LDH)",
                "Jammu (JAT)",
            ],
        }

    return filtered, meta_copy


def get_train_by_number(
    train_number: str,
    file_path: Optional[str] = None,
) -> Optional[CuratedTrainSchedule]:
    """Retrieves a single curated train schedule by its official train number."""
    schedules, _, _ = load_curated_schedules(file_path=file_path)
    tn = str(train_number).strip()
    for s in schedules:
        if s.train_number == tn:
            return s
    return None


def get_station_by_code_or_city(
    query: str,
    file_path: Optional[str] = None,
) -> Optional[StationInfo]:
    """Retrieves station metadata matching station code or city name."""
    _, stations, _ = load_curated_schedules(file_path=file_path)
    q = str(query).strip().lower()
    for stn in stations:
        if stn.station_code.lower() == q or stn.city.lower() == q:
            return stn
    return None
