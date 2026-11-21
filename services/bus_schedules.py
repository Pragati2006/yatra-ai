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
                if v_stat in ("OFFICIALLY_VERIFIED", "VERIFIED", VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value):
                    v_stat = VerificationStatus.VERIFIED_CURATED_SOURCE.value
                elif v_stat in ("PARTIALLY_VERIFIED", "SEASONAL_VERIFIED"):
                    v_stat = VerificationStatus.PARTIALLY_VERIFIED.value

                src_name = r.get("source_name")
                src_url = r.get("source_url")
                src_ref = r.get("source_circular_reference")
                v_by = r.get("verified_by")
                v_at = r.get("verified_at")

                # Fail-closed: missing source provenance cannot claim verified status
                if not (src_name and src_url and src_ref and v_by and v_at):
                    v_stat = VerificationStatus.UNVERIFIED.value
                else:
                    orig = str(r.get("origin_city", "")).strip().lower()
                    dest = str(r.get("destination_city", "")).strip().lower()
                    op_name = str(r.get("operator_name", "")).strip().lower()
                    j_type = str(r.get("journey_type", "")).strip().upper()

                    # Phase 6.2 Evidence Verification Guards:
                    # 1. JKRTC official interstate timetables publish Delhi-Jammu; direct Delhi-Katra or
                    # Pathankot-Katra stage carriage is unsupported as a verified schedule.
                    if "jksrtc" in op_name or "jkrtc" in op_name:
                        if orig == "delhi" and dest == "katra" and j_type == "DIRECT":
                            v_stat = VerificationStatus.PARTIALLY_VERIFIED.value
                        elif orig == "pathankot" and dest == "katra" and j_type == "DIRECT":
                            v_stat = VerificationStatus.PARTIALLY_VERIFIED.value

                    # 2. Sub-verification fail-closed: If timetable is unverified or route is partially verified
                    time_v = (r.get("timetable_verification") or {}).get("status")
                    route_v = (r.get("route_verification") or {}).get("status")
                    if time_v == "unverified" or route_v in ("partially_verified", "unverified"):
                        v_stat = VerificationStatus.PARTIALLY_VERIFIED.value

                    # 3. Multi-leg connecting journeys with estimated layovers cannot claim direct verified stage carriage
                    if j_type == "CONNECTING":
                        v_stat = VerificationStatus.PARTIALLY_VERIFIED.value

                    # 4. Domain-only URLs without route-specific paths cannot support fully verified status
                    from urllib.parse import urlparse
                    parsed = urlparse(str(src_url or ""))
                    if parsed.path in ("", "/", "/index.html"):
                        v_stat = VerificationStatus.PARTIALLY_VERIFIED.value

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
                        operator_type=str(r.get("operator_type", "government")).strip().lower(),
                        boarding_points=r.get("boarding_points") or ([str(r.get("origin_bus_stand", ""))] if r.get("origin_bus_stand") else []),
                        dropping_points=r.get("dropping_points") or ([str(r.get("destination_bus_stand", ""))] if r.get("destination_bus_stand") else []),
                        bus_type=r.get("bus_type") or r.get("service_type"),
                        booking_url=r.get("booking_url"),
                        availability_status=r.get("availability_status", "COUNTER_TICKETING_UNRESERVED"),
                        availability_source=r.get("availability_source", "Official Counter / Station"),
                        journey_type=str(r.get("journey_type", "DIRECT")).strip().upper(),
                        connecting_details=r.get("connecting_details"),
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
    operator_type: Optional[str] = None,
    bus_type: Optional[str] = None,
    journey_type: Optional[str] = None,
    direct_only: bool = False,
    max_fare: Optional[float] = None,
    sort_by: Optional[str] = None,
) -> Tuple[List[CuratedBusSchedule], Dict[str, Any]]:
    """Searches curated bus schedules matching origin, destination, or service_id.

    Supports operator classification (government vs private), bus category filtering
    (sleeper, seater, AC), journey type filtering (direct vs connecting), and fare sorting.

    Args:
        origin: City name (e.g. 'Jammu', 'Delhi', 'Chandigarh', 'Amritsar') or bus stand name.
        destination: City name (e.g. 'Katra') or bus stand name.
        service_id: Specific bus service ID.
        travel_date: Optional ISO date string (YYYY-MM-DD).
        file_path: Optional path to override dataset.
        operator_type: Optional filter ('government', 'private').
        bus_type: Optional filter substring ('sleeper', 'seater', 'ac', 'volvo', 'bharatbenz').
        journey_type: Optional filter ('DIRECT', 'CONNECTING').
        direct_only: If True, only returns DIRECT journeys (excludes connecting transfers).
        max_fare: Optional maximum indicative minimum fare limit.
        sort_by: Optional sort order ('fare', 'departure', 'duration').

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
            "delhi": ["delhi", "new delhi", "isbt kashmiri gate", "isbt kashmere gate", "kashmiri gate", "kashmere gate", "ndls", "majnu ka tila", "anand vihar"],
            "katra": ["katra", "central bus stand", "svdk", "shri mata vaishno devi"],
            "jammu": ["jammu", "jammu tawi", "gbs", "general bus stand", "rail head", "jat"],
            "udhampur": ["udhampur", "uhp", "battal"],
            "chandigarh": ["chandigarh", "cdg", "isbt 43", "isbt sector 43", "sector 43"],
            "amritsar": ["amritsar", "asr", "amritsar isbt"],
            "shimla": ["shimla", "simla", "isbt tutikandi", "tutikandi"],
            "dharamshala": ["dharamshala", "dharamsala", "mcleodganj"],
            "manali": ["manali"],
            "mandi": ["mandi"],
            "pathankot": ["pathankot", "ptk", "ptkc"],
            "srinagar": ["srinagar", "sxr", "trc"],
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

        # Filter by operator_type
        if operator_type:
            op_t = operator_type.strip().lower()
            if s.operator_type.lower() != op_t:
                continue

        # Filter by direct_only
        if direct_only and s.journey_type.upper() != "DIRECT":
            continue

        # Filter by journey_type
        if journey_type:
            j_t = journey_type.strip().upper()
            if s.journey_type.upper() != j_t:
                continue

        # Filter by bus_type
        if bus_type:
            bt_q = bus_type.strip().lower()
            combined_type = f"{s.bus_type or ''} {s.service_type or ''}".lower()
            if bt_q == "ac":
                if "ac" not in combined_type and "volvo" not in combined_type and "bharatbenz" not in combined_type:
                    continue
            elif bt_q == "sleeper":
                if "sleeper" not in combined_type:
                    continue
            elif bt_q == "seater":
                if "seater" not in combined_type and "ordinary" not in combined_type:
                    continue
            else:
                if bt_q not in combined_type:
                    continue

        # Filter by max_fare
        if max_fare is not None:
            f_val = s.indicative_fare_min if s.indicative_fare_min is not None else s.indicative_fare_max
            if f_val is not None and f_val > max_fare:
                continue

        filtered.append(s)

    # Apply sorting
    if sort_by == "fare":
        filtered.sort(key=lambda x: (x.indicative_fare_min if x.indicative_fare_min is not None else 999999))
    elif sort_by == "departure":
        filtered.sort(key=lambda x: (x.departure_time or "99:99"))
    elif sort_by == "duration":
        filtered.sort(key=lambda x: (x.duration_hours if x.duration_hours is not None else 9999))

    meta_copy = dict(metadata)
    if origin and not filtered:
        meta_copy["coverage_limitation"] = {
            "status": "ROUTE_NOT_IN_CURATED_BUS_REGISTRY",
            "origin": origin,
            "destination": destination or "Katra",
            "message": (
                f"No verified public bus services found in the curated Katra/Jammu bus registry for origin '{origin}'. "
                "Curated bus coverage includes verified corridors connecting Jammu (General Bus Stand & Rail Head), "
                "Udhampur, Delhi (ISBT & Majnu Ka Tila), Chandigarh, Amritsar, Pathankot, and Srinagar to Katra. "
                "For other origins, pilgrims should travel by train/flight to Jammu or Delhi and connect via high-frequency local feeder buses or verified operator services."
            ),
            "supported_origins": [
                "Delhi (ISBT Kashmiri Gate / Majnu Ka Tila)",
                "Jammu (General Bus Stand / Railway Station)",
                "Katra (Central Bus Stand)",
                "Udhampur (District Bus Stand)",
                "Chandigarh (ISBT Sector 43)",
                "Amritsar (ISBT)",
                "Pathankot (Bus Stand)",
                "Srinagar (Tourist Reception Centre - TRC)",
            ],
        }

    return filtered, meta_copy


def get_cheapest_bus(
    origin: str,
    destination: str = "Katra",
    direct_only: bool = False,
    file_path: Optional[str] = None,
) -> Optional[CuratedBusSchedule]:
    """Returns the bus schedule with lowest minimum indicative fare for the route."""
    schedules, _ = search_curated_bus_schedules(
        origin=origin,
        destination=destination,
        direct_only=direct_only,
        file_path=file_path,
        sort_by="fare",
    )
    return schedules[0] if schedules else None


def get_direct_buses(
    origin: str,
    destination: str = "Katra",
    file_path: Optional[str] = None,
) -> List[CuratedBusSchedule]:
    """Returns only direct, through bus services to the destination."""
    schedules, _ = search_curated_bus_schedules(
        origin=origin,
        destination=destination,
        direct_only=True,
        file_path=file_path,
    )
    return schedules


def get_connecting_buses(
    origin: str,
    destination: str = "Katra",
    file_path: Optional[str] = None,
) -> List[CuratedBusSchedule]:
    """Returns verified connecting bus services with official transfer hubs."""
    schedules, _ = search_curated_bus_schedules(
        origin=origin,
        destination=destination,
        journey_type="CONNECTING",
        file_path=file_path,
    )
    return schedules


def compare_bus_and_train(
    origin: str = "Delhi",
    destination: str = "Katra",
) -> Dict[str, Any]:
    """Generates a side-by-side comparison between train and bus travel for Katra."""
    bus_schedules, _ = search_curated_bus_schedules(origin=origin, destination=destination)

    # Separate private and government buses
    gov_buses = [b for b in bus_schedules if b.operator_type == "government"]
    pvt_buses = [b for b in bus_schedules if b.operator_type == "private"]
    verified_buses = [b for b in bus_schedules if b.verification_status == "verified_curated_source"]
    partial_buses = [b for b in bus_schedules if b.verification_status == "partially_verified"]

    return {
        "corridor": f"{origin} ↔ {destination}",
        "train": {
            "mode": "train",
            "flagship": "Vande Bharat Express (22439 / 22477)",
            "overnight": "Shri Shakti Express (22461) / Uttar Sampark Kranti (12445)",
            "duration": "8h 00m (Vande Bharat) / 11h 30m (Overnight Superfast)",
            "fare_range": "₹1,665 (Chair Car) / ₹3,015 (Executive) / ₹380–₹1,100 (Sleeper/3AC)",
            "booking_portal": "https://www.irctc.co.in/",
            "pros": ["Fastest surface transit (8h)", "On-board catering", "Arrives directly at SVDK station"],
            "cons": ["High advance booking demand", "Tatkal fills within minutes"],
        },
        "bus": {
            "mode": "bus",
            "government_operators": ["JKRTC", "HRTC", "PRTC / Punbus"],
            "private_operators": ["Laxmi Holidays", "Zingbus", "FlixBus", "IntrCity SmartBus", "Ram Dalal Holidays"],
            "bus_types": ["Volvo 9600 AC Sleeper (2+1)", "BharatBenz AC Sleeper", "Deluxe 2+2 AC Seater", "Ordinary Stage Carriage"],
            "duration": "12h 00m – 14h 30m (Estimated)",
            "duration_estimate": "12h 00m – 14h 30m (Overnight Highway Corridor Estimate)",
            "fare_range": "₹750 – ₹1,900 (Indicative)",
            "indicative_fare_range": "₹750 – ₹1,900 (Indicative range depending on seater vs sleeper & operator)",
            "boarding_points": ["ISBT Kashmiri Gate", "Majnu Ka Tila", "Karnal Bypass", "Anand Vihar"],
            "dropping_points": ["Katra New Bus Stand", "Subhash Parking Katra", "Kachi Parking Katra"],
            "pros": ["Flexible departure times (multiple evening slots)", "Reclining sleeper berths", "Last-minute seat availability"],
            "cons": ["Longer transit time (~12–14h)", "Highway traffic and mountain weather dependent"],
            "total_services": len(bus_schedules),
            "total_verified_services": len(verified_buses),
            "verified_services_count": len(verified_buses),
            "partially_verified_count": len(partial_buses),
            "government_count": len(gov_buses),
            "private_count": len(pvt_buses),
        },
        "recommendation": (
            "For speed and maximum comfort, the **Vande Bharat Express (22439)** is the top recommendation (8 hours). "
            "If train tickets are waitlisted, **Premium AC Sleeper Buses (Laxmi Holidays / Zingbus / IntrCity / JKRTC Volvo)** "
            "provide reliable overnight transit departing Delhi around 18:00–21:30 and arriving Katra refreshed by 08:30–10:30."
        ),
    }


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
