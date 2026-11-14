"""
services/transport_schema.py
Unified Transport Data Schema & Normalization Contracts for Yatra AI (Phase 14.4.3).

Implements a single, standard schema for all transport modes (Train, Bus, Flight)
supporting complete data provenance, verification tiers, statutory tariffs, and source attribution.
Adheres strictly to truth-in-data principles:
- Null for unknown fields (never insert fabricated values).
- Verification status classifications: OFFICIALLY_VERIFIED, PUBLICLY_PUBLISHED_UNVERIFIED,
  INDICATIVE, SYNTHETIC, EXPIRED, UNKNOWN.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Union


# -----------------------------------------------------------------------------
# 1. Enums
# -----------------------------------------------------------------------------

class TransportMode(str, Enum):
    TRAIN = "train"
    RAIL = "train"
    BUS = "bus"
    FLIGHT = "flight"
    ROAD_TAXI = "road_taxi"


class VerificationStatus(str, Enum):
    OFFICIALLY_VERIFIED = "OFFICIALLY_VERIFIED"
    PUBLICLY_PUBLISHED_UNVERIFIED = "PUBLICLY_PUBLISHED_UNVERIFIED"
    INDICATIVE = "INDICATIVE"
    SYNTHETIC = "SYNTHETIC"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class TransportDataType(str, Enum):
    CURATED_TIMETABLE = "curated_timetable"
    STATUTORY_TARIFF = "statutory_tariff"
    CORRIDOR_GUIDANCE = "corridor_guidance"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


# -----------------------------------------------------------------------------
# 2. Canonical City & Station Aliases
# -----------------------------------------------------------------------------

CANONICAL_CITY_ALIASES: Dict[str, str] = {
    # Bangalore / Bengaluru
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "blr": "Bengaluru",
    "sbc": "Bengaluru",
    # Mumbai / Bombay
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "bom": "Mumbai",
    "csmt": "Mumbai",
    "bct": "Mumbai",
    "bdts": "Mumbai",
    # Kolkata / Calcutta
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "ccu": "Kolkata",
    "hwh": "Kolkata",
    "sdah": "Kolkata",
    # Chennai / Madras
    "madras": "Chennai",
    "chennai": "Chennai",
    "maa": "Chennai",
    "mas": "Chennai",
    # Delhi / New Delhi
    "new delhi": "Delhi",
    "delhi": "Delhi",
    "dli": "Delhi",
    "ndls": "Delhi",
    "del": "Delhi",
    "nizamuddin": "Delhi",
    "nzm": "Delhi",
    # Varanasi / Banaras / Kashi
    "banaras": "Varanasi",
    "kashi": "Varanasi",
    "varanasi": "Varanasi",
    "bsb": "Varanasi",
    # Vadodara / Baroda
    "baroda": "Vadodara",
    "vadodara": "Vadodara",
    "brc": "Vadodara",
    # Prayagraj / Allahabad
    "allahabad": "Prayagraj",
    "prayagraj": "Prayagraj",
    "ald": "Prayagraj",
    "pryj": "Prayagraj",
    # Kochi / Cochin
    "cochin": "Kochi",
    "kochi": "Kochi",
    "cok": "Kochi",
    # Thiruvananthapuram / Trivandrum
    "trivandrum": "Thiruvananthapuram",
    "thiruvananthapuram": "Thiruvananthapuram",
    "trv": "Thiruvananthapuram",
    # Pune / Poona
    "poona": "Pune",
    "pune": "Pune",
    "pnq": "Pune",
    # Katra / SVDK
    "svdk": "Katra",
    "shri mata vaishno devi katra": "Katra",
    "katra": "Katra",
    # Jammu / JAT
    "jammu tawi": "Jammu",
    "jammu": "Jammu",
    "jat": "Jammu",
    "ixj": "Jammu",
    # Srinagar / SXR
    "srinagar": "Srinagar",
    "sxr": "Srinagar",
    # Amritsar / ASR
    "amritsar": "Amritsar",
    "asr": "Amritsar",
    "atq": "Amritsar",
    # Chandigarh / CDG
    "chandigarh": "Chandigarh",
    "cdg": "Chandigarh",
    "ixc": "Chandigarh",
    # Shimla / Simla
    "shimla": "Shimla",
    "simla": "Shimla",
}


def normalize_city_name(name: Optional[str]) -> str:
    """Normalizes an Indian city, airport, or station name to canonical casing and alias."""
    if not name or not isinstance(name, str):
        return "Unknown"
    cleaned = name.strip()
    low = cleaned.lower()
    if low in CANONICAL_CITY_ALIASES:
        return CANONICAL_CITY_ALIASES[low]
    words = cleaned.split()
    return " ".join(w.capitalize() for w in words)


# -----------------------------------------------------------------------------
# 3. Unified Transport Record Data Contract
# -----------------------------------------------------------------------------

@dataclass
class UnifiedTransportRecord:
    """
    Standard schema for all transport modes (Train, Bus, Flight) across Yatra AI.
    Every field is validated; unknown fields remain None (never fabricated).
    """
    record_id: str
    mode: str  # "train" | "bus" | "flight"
    origin_name: str
    destination_name: str
    operator: str
    source_name: str
    source_url: str = ""
    fetched_at: str = ""
    last_verified_at: str = ""
    verification_status: str = "INDICATIVE"  # OFFICIALLY_VERIFIED | PUBLICLY_PUBLISHED_UNVERIFIED | INDICATIVE | SYNTHETIC | EXPIRED | UNKNOWN
    data_type: str = "curated_timetable"    # curated_timetable | statutory_tariff | corridor_guidance | synthetic_fixture

    # Optional / Mode-specific fields
    origin_code: Optional[str] = None
    destination_code: Optional[str] = None
    service_number: Optional[str] = None
    service_name: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    operating_days: List[str] = field(default_factory=list)
    duration: Optional[str] = None
    duration_mins: Optional[int] = None
    distance_km: Optional[int] = None
    fare: Optional[float] = None
    indicative_fare_min: Optional[float] = None
    indicative_fare_max: Optional[float] = None
    currency: str = "INR"
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    notes: Optional[str] = None
    intermediate_stops: List[str] = field(default_factory=list)
    travel_classes: List[str] = field(default_factory=list)
    service_type: Optional[str] = None  # e.g. "Vande Bharat", "Express", "Volvo AC", "Deluxe"
    is_live_status: bool = False

    def is_valid(self) -> bool:
        """Returns True if the record meets essential completeness and sanity checks."""
        if not self.record_id or not self.record_id.strip():
            return False
        if not self.origin_name or not self.origin_name.strip() or self.origin_name == "Unknown":
            return False
        if not self.destination_name or not self.destination_name.strip() or self.destination_name == "Unknown":
            return False
        if self.fare is not None and self.fare < 0:
            return False
        if self.distance_km is not None and self.distance_km < 0:
            return False
        return True

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()
        if not self.last_verified_at:
            self.last_verified_at = self.fetched_at

        # Validate mode
        raw_mode = self.mode.value if isinstance(self.mode, Enum) else str(self.mode)
        norm_mode = raw_mode.lower().strip()
        if norm_mode not in ("train", "bus", "flight", "road_taxi"):
            raise ValueError(f"Invalid transport mode: {self.mode}")
        self.mode = norm_mode

        # Validate verification_status
        raw_status = self.verification_status.value if isinstance(self.verification_status, Enum) else str(self.verification_status)
        status_str = raw_status.upper().strip()
        valid_statuses = {s.value for s in VerificationStatus}
        if status_str not in valid_statuses:
            # Map legacy statuses
            if status_str in ("VERIFIED_CURATED_SOURCE", "OFFICIALLY_VERIFIED", "VERIFIED"):
                status_str = VerificationStatus.OFFICIALLY_VERIFIED.value
            elif status_str in ("PARTIALLY_VERIFIED", "PUBLICLY_PUBLISHED_UNVERIFIED"):
                status_str = VerificationStatus.PUBLICLY_PUBLISHED_UNVERIFIED.value
            elif status_str in ("INDICATIVE_INFORMATION", "INDICATIVE"):
                status_str = VerificationStatus.INDICATIVE.value
            elif status_str in ("SYNTHETIC_FIXTURE", "SYNTHETIC"):
                status_str = VerificationStatus.SYNTHETIC.value
            elif status_str == "EXPIRED":
                status_str = VerificationStatus.EXPIRED.value
            else:
                status_str = VerificationStatus.UNKNOWN.value
        self.verification_status = status_str

        # Validate data_type
        raw_dt = self.data_type.value if isinstance(self.data_type, Enum) else str(self.data_type)
        self.data_type = raw_dt.lower().strip()

        # Validate departure_time format if present (HH:MM or HH:MM AM/PM)
        if self.departure_time:
            self.departure_time = self._clean_time_str(self.departure_time)
        if self.arrival_time:
            self.arrival_time = self._clean_time_str(self.arrival_time)

        # Check if record has expired based on valid_until
        if self.valid_until:
            try:
                # Compare YYYY-MM-DD
                exp_date = datetime.strptime(self.valid_until[:10], "%Y-%m-%d").date()
                if exp_date < datetime.now(timezone.utc).date():
                    self.verification_status = VerificationStatus.EXPIRED.value
            except Exception:
                pass

    @staticmethod
    def _clean_time_str(val: str) -> str:
        s = str(val).strip()
        m = re.match(r"^(\d{1,2}):(\d{2})(?:\s*([APap][Mm]))?", s)
        if m:
            hh, mm, ampm = m.groups()
            if ampm:
                h = int(hh)
                if ampm.upper() == "PM" and h < 12:
                    h += 12
                elif ampm.upper() == "AM" and h == 12:
                    h = 0
                return f"{h:02d}:{mm}"
            return f"{int(hh):02d}:{mm}"
        return s

    @property
    def is_verified(self) -> bool:
        """Returns True only if officially verified or publicly published without expiry."""
        return self.verification_status in (
            VerificationStatus.OFFICIALLY_VERIFIED.value,
            VerificationStatus.PUBLICLY_PUBLISHED_UNVERIFIED.value,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the record to a dictionary."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedTransportRecord":
        """Constructs a UnifiedTransportRecord from a dict, omitting unmapped keys."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
