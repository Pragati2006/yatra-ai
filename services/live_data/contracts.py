"""
services/live_data/contracts.py
Normalized Data Contracts & Typed Enums for the Yatra AI Live Data Architecture.

Defines standardized, provider-independent request, response, error, and metadata models:
- ProviderLifecycle: Conceptual lifecycle states of data providers.
- ProviderOperationalStatus: Realized operational health verified through actual execution.
- ProviderErrorType: Standardized, sanitized error classifications.
- DataDomain: Supported data domains (weather, accommodation, operational notices, capacity, emergency, transport).
- ProviderMetadata: Descriptive metadata for provider discovery, verification, and registration.
- ProviderRequest: Validated, domain-specific request container with strict private session isolation.
- ProviderError: Sanitized, safe error representation omitting internal secrets, PII, and stack traces.
- LiveDataResult: Unified result container strictly adhering to truth-in-data provenance.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from utils.provenance import (
    FreshnessStatus,
    ProvenanceRecord,
    SourceType,
    VerificationStatus,
    create_provenance,
    get_utc_now_iso,
    normalize_freshness_status,
    normalize_source_type,
    normalize_verification_status,
    validate_provenance,
)


# -----------------------------------------------------------------------------
# 1. STANDARDIZED ENUMS
# -----------------------------------------------------------------------------

class ProviderLifecycle(str, Enum):
    """Conceptual lifecycle state of a live data provider."""
    CONFIGURED = "CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    REQUEST_SUCCESS = "REQUEST_SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    TIMED_OUT = "TIMED_OUT"
    MALFORMED_DATA = "MALFORMED_DATA"
    ERROR = "ERROR"


class ProviderOperationalStatus(str, Enum):
    """Realized operational readiness of a provider established through actual execution."""
    UNCONFIGURED = "UNCONFIGURED"
    CONFIGURED_PENDING_VERIFICATION = "CONFIGURED_PENDING_VERIFICATION"
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    HALF_OPEN = "HALF_OPEN"


class ProviderErrorType(str, Enum):
    """Standardized error classifications for provider failures."""
    UNAVAILABLE = "UNAVAILABLE"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    AUTH_FAILURE = "AUTH_FAILURE"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    NO_RESULTS = "NO_RESULTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"


class DataDomain(str, Enum):
    """Supported data domains across pilgrimage and tourism operations."""
    WEATHER = "weather"
    ACCOMMODATION = "accommodation"
    OPERATIONAL_NOTICE = "operational_notice"
    CAPACITY = "capacity"
    EMERGENCY = "emergency"
    TRANSPORT = "transport"
    GENERAL = "general"


class NoticeCategory(str, Enum):
    """Standardized operational notice categories for pilgrimage and regional transit."""
    YATRA_SUSPENSION = "YATRA_SUSPENSION"
    YATRA_RESUMPTION = "YATRA_RESUMPTION"
    REGISTRATION_RESTRICTION = "REGISTRATION_RESTRICTION"
    ROUTE_CLOSURE = "ROUTE_CLOSURE"
    ROUTE_RESTRICTION = "ROUTE_RESTRICTION"
    TRAFFIC_ADVISORY = "TRAFFIC_ADVISORY"
    WEATHER_WARNING = "WEATHER_WARNING"
    FACILITY_DISRUPTION = "FACILITY_DISRUPTION"
    GENERAL_OPERATIONAL_NOTICE = "GENERAL_OPERATIONAL_NOTICE"


class NoticeLifecycleStatus(str, Enum):
    """Semantic lifecycle state of an operational advisory directive."""
    PUBLISHED = "PUBLISHED"
    ACTIVE = "ACTIVE"
    REQUIRES_REVERIFICATION = "REQUIRES_REVERIFICATION"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class NoticeAggregateStatus(str, Enum):
    """Aggregate result classification for an operational notice registry query."""
    HAS_NOTICES = "HAS_NOTICES"
    NO_ACTIVE_NOTICES = "NO_ACTIVE_NOTICES"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class ContactCategory(str, Enum):
    """Structured categories for verified emergency and operational contact helplines."""
    NATIONAL_EMERGENCY = "NATIONAL_EMERGENCY"
    SHRINE_BOARD_ASSISTANCE = "SHRINE_BOARD_ASSISTANCE"
    TRAFFIC_CONTROL = "TRAFFIC_CONTROL"
    LOCAL_POLICE = "LOCAL_POLICE"
    MEDICAL_ASSISTANCE = "MEDICAL_ASSISTANCE"


@dataclass
class OperationalNotice:
    """Normalized, strongly-typed operational advisory container with provenance."""
    notice_id: str
    notice_title: str
    notice_text: str
    issuing_authority: str
    source_url: str
    affected_location: str
    affected_route: Optional[str] = None
    category: str = NoticeCategory.GENERAL_OPERATIONAL_NOTICE.value
    severity: str = "ADVISORY"  # 'INFO', 'ADVISORY', 'WARNING', 'CRITICAL'
    publication_timestamp: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_status: str = VerificationStatus.UNVERIFIED.value
    notice_lifecycle_status: str = NoticeLifecycleStatus.ACTIVE.value
    superseded_by_notice_id: Optional[str] = None
    supersedes_notice_id: Optional[str] = None
    translated_summary: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes notice to dictionary, ensuring clean ISO format."""
        return asdict(self)


@dataclass
class VerifiedContact:
    """Structured container for an officially verified contact or helpline."""
    contact_id: str
    organization: str
    telephone_number: str
    service_description: str
    category: str = ContactCategory.NATIONAL_EMERGENCY.value
    geographic_jurisdiction: str = "Pan-India"
    operating_hours: str = "24x7"
    source_url: str = ""
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_status: str = VerificationStatus.UNVERIFIED.value
    is_primary_emergency: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes contact to clean dictionary."""
        return asdict(self)


# -----------------------------------------------------------------------------
# 1.3 RAILWAY & TRANSIT DATA CONTRACTS (Phase 9.7.3)
# -----------------------------------------------------------------------------

class TrainRunningStatusType(str, Enum):
    """Real-time operational running states for an active train service."""
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    ARRIVED = "ARRIVED"
    CANCELLED = "CANCELLED"
    DIVERTED = "DIVERTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class TrainRunningStatus:
    """Normalized live running status for an active train service with strict truth-in-data."""
    train_number: str
    train_name: str
    journey_date: Optional[str] = None
    source_station_code: Optional[str] = None
    source_station_name: Optional[str] = None
    destination_station_code: Optional[str] = None
    destination_station_name: Optional[str] = None
    current_station_code: Optional[str] = None
    current_station_name: Optional[str] = None
    # CRITICAL RULE: Unknown delay must be None, NOT 0.
    delay_departure_minutes: Optional[int] = None
    delay_arrival_minutes: Optional[int] = None
    status: str = TrainRunningStatusType.UNKNOWN.value
    # CRITICAL RULE: Unknown platform numbers and times must remain None (unknown).
    platform_number: Optional[str] = None
    expected_arrival_time: Optional[str] = None
    expected_departure_time: Optional[str] = None
    last_reported_timestamp: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    data_source: str = "curated_railway_schedule"
    data_authority: str = "indicative_aggregator"
    verification_status: str = VerificationStatus.UNVERIFIED.value
    # CRITICAL RULE: Do not represent static timetable information as live train status.
    is_live_status: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes running status to dictionary."""
        return asdict(self)


@dataclass
class StationInfo:
    """Standardized metadata container for railway stations."""
    station_code: str
    station_name: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_meters: Optional[int] = None
    division: Optional[str] = None
    zone: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes station info to dictionary."""
        return asdict(self)


def _is_generic_homepage_url(url: Optional[str]) -> bool:
    """Checks whether a URL is a generic root homepage rather than a specific evidentiary document."""
    if not url:
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url.strip())
        path = parsed.path.strip()
        return path in ("", "/", "/index.html", "/index.php") and not parsed.query
    except Exception:
        return False


@dataclass
class ClaimVerification:
    """Fine-grained verification claim for transport attributes."""
    status: str = VerificationStatus.UNVERIFIED.value
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    reference_url: Optional[str] = None
    document_reference: Optional[str] = None
    effective_date: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        # 1. Status normalization
        if not self.status:
            self.status = VerificationStatus.UNVERIFIED.value

        # 2. Fail-closed: unverified claims must NEVER possess verification timestamps, verifier identity, or invented effective dates
        if self.status == VerificationStatus.UNVERIFIED.value:
            self.verified_at = None
            self.verified_by = None
            self.effective_date = None
            # If a generic homepage URL was supplied as source_url on an unverified claim,
            # preserve it under reference_url and clear source_url so it is not mistaken for verified evidence.
            if self.source_url and _is_generic_homepage_url(self.source_url):
                if not self.reference_url:
                    self.reference_url = self.source_url
                self.source_url = None

        # 3. Fail-closed: verified claims must have adequate evidentiary support
        elif self.status in (
            VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            VerificationStatus.PARTIALLY_VERIFIED.value,
        ):
            # Must possess source name, and either source_url (non-generic) or document_reference
            has_source = bool(self.source_name and (self.source_url or self.document_reference))
            has_generic_homepage_without_doc = bool(self.source_url and _is_generic_homepage_url(self.source_url) and not self.document_reference)

            if not has_source or has_generic_homepage_without_doc:
                self.status = VerificationStatus.UNVERIFIED.value
                self.verified_at = None
                self.verified_by = None
                self.effective_date = None
                if self.source_url and _is_generic_homepage_url(self.source_url):
                    if not self.reference_url:
                        self.reference_url = self.source_url
                    self.source_url = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes claim verification to dictionary."""
        return asdict(self)


@dataclass
class CuratedTrainSchedule:
    """Authoritative, human-verified timetable record for Katra/Jammu railway corridors."""
    train_number: str
    train_name: str
    origin_station_code: str
    origin_station_name: str
    destination_station_code: str
    destination_station_name: str
    departure_time: str
    arrival_time: str
    days_of_operation: List[str]
    travel_classes: List[str]
    major_halts: List[Dict[str, Any]]
    total_distance_km: Optional[int] = None
    duration_hours: Optional[float] = None
    catering_available: Optional[bool] = None
    indicative_fare_min: Optional[int] = None
    indicative_fare_max: Optional[int] = None
    fare_classification: str = "UNAVAILABLE"
    fare_disclaimer: str = (
        "Railway fares are unavailable in static demonstration registry. Real-time booking fares vary based on "
        "Tatkal quotas, dynamic surge pricing, and catering selections; check official IRCTC portal (irctc.co.in)."
    )
    source_name: str = "Curated Indian Railways Route Guidance"
    source_url: Optional[str] = None
    source_circular_reference: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_status: str = VerificationStatus.VERIFIED_CURATED_SOURCE.value
    is_live_status: bool = False  # Always False for static timetable
    notes: Optional[str] = None
    route_verification: Optional[ClaimVerification] = None
    operator_verification: Optional[ClaimVerification] = None
    timetable_verification: Optional[ClaimVerification] = None
    fare_verification: Optional[ClaimVerification] = None

    def __post_init__(self):
        # Strict fail-safe: railway schedules are static timetable schedules, never live running status
        self.is_live_status = False

        # Convert claim dicts to ClaimVerification instances if passed as dicts, or default to unverified if None
        for attr in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
            val = getattr(self, attr)
            if isinstance(val, dict):
                setattr(self, attr, ClaimVerification(**val))
            elif val is None:
                field_label = attr.replace("_verification", "")
                setattr(
                    self,
                    attr,
                    ClaimVerification(
                        status=VerificationStatus.UNVERIFIED.value,
                        notes=f"Railway {field_label} claim verification unstated or unverified.",
                    ),
                )

        # Fail-closed rules for timetable & fare claims:
        # Timetable verification cannot be verified without substantiated non-generic document reference
        if self.timetable_verification and self.timetable_verification.status in (
            VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            VerificationStatus.VERIFIED_CURATED_SOURCE.value,
        ):
            doc_ref = (self.timetable_verification.document_reference or "").lower()
            if not doc_ref or any(kw in doc_ref for kw in ("unpublished", "guidance", "inquiry", "window", "wtt", "working timetable")):
                self.timetable_verification.status = VerificationStatus.UNVERIFIED.value
                self.timetable_verification.verified_at = None
                self.timetable_verification.verified_by = None
                self.timetable_verification.effective_date = None
                self.timetable_verification.document_reference = None

        # Route verification fail-closed: generic directory or administrative citations cannot substantiate specific corridor claims
        if self.route_verification and self.route_verification.status in (
            VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            VerificationStatus.VERIFIED_CURATED_SOURCE.value,
        ):
            doc_ref = (self.route_verification.document_reference or "").lower()
            if not doc_ref or any(kw in doc_ref for kw in ("system directory", "directory", "homepage", "guidance")):
                self.route_verification.status = VerificationStatus.UNVERIFIED.value
                self.route_verification.verified_at = None
                self.route_verification.verified_by = None
                self.route_verification.effective_date = None
                self.route_verification.document_reference = None

        # Fare verification cannot be verified_official_source or verified_curated_source if it is an estimated, base tariff, or unavailable
        if self.fare_verification:
            doc_ref = (self.fare_verification.document_reference or "").lower()
            if (
                self.fare_classification in ("ESTIMATED_MARKET_TARIFF", "ESTIMATED_PUBLISHED_BASE_TARIFF", "UNAVAILABLE")
                or not doc_ref
                or any(kw in doc_ref for kw in ("tariff table", "base passenger tariff", "estimate", "unavailable"))
            ):
                if self.fare_verification.status in (
                    VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                    VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                ):
                    self.fare_verification.status = VerificationStatus.UNVERIFIED.value
                    self.fare_verification.verified_at = None
                    self.fare_verification.verified_by = None
                    self.fare_verification.effective_date = None
                    self.fare_verification.document_reference = None

        # When fare is unavailable or unverified, purge numerical min/max values
        if self.fare_classification == "UNAVAILABLE" or (self.fare_verification and self.fare_verification.status == VerificationStatus.UNVERIFIED.value):
            self.indicative_fare_min = None
            self.indicative_fare_max = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes schedule to dictionary."""
        d = asdict(self)
        for attr in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
            val = getattr(self, attr)
            if val and hasattr(val, "to_dict"):
                d[attr] = val.to_dict()
        return d


@dataclass
class CuratedBusSchedule:
    """Authoritative, human-verified public bus schedule record for Katra/Jammu corridors."""
    service_id: str
    operator_name: str
    service_type: str  # e.g., STAGE_CARRIAGE_FREQUENCY, PILGRIM_SHUTTLE, REGIONAL_FEEDER_GUIDANCE, INTERSTATE_SCHEDULED_WINDOW
    origin_bus_stand: str
    destination_bus_stand: str
    origin_city: str
    destination_city: str
    route_description: Optional[str] = None
    operating_hours: Optional[str] = None
    frequency_minutes: Optional[int] = None
    departure_window: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_hours: Optional[float] = None
    indicative_fare_min: Optional[int] = None
    indicative_fare_max: Optional[int] = None
    fare_classification: str = "STATUTORY_NOTIFIED_PER_KM_SLAB"
    fare_disclaimer: str = (
        "Governed by J&K State Transport Authority Notification No. 01-P-MVD of 2026. "
        "Ordinary stage carriage passenger tariff subject to vehicle category and highway toll. "
        "Purchase tickets directly at bus stand counter."
    )
    helpline_numbers: List[str] = field(default_factory=list)
    source_name: str = "Government of Jammu & Kashmir Transport Department & JKRTC"
    source_url: Optional[str] = None
    source_circular_reference: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_status: str = VerificationStatus.VERIFIED_CURATED_SOURCE.value
    is_live_status: bool = False  # Always False for static schedule guidance
    notes: Optional[str] = None
    # Claim-level verification breakdown (Phase 9.8.1.2)
    route_verification: Optional[ClaimVerification] = None
    operator_verification: Optional[ClaimVerification] = None
    timetable_verification: Optional[ClaimVerification] = None
    fare_verification: Optional[ClaimVerification] = None
    # Multi-operator discovery & journey metadata (Phase 6)
    operator_type: str = "government"  # "government" | "private"
    boarding_points: List[str] = field(default_factory=list)
    dropping_points: List[str] = field(default_factory=list)
    bus_type: Optional[str] = None
    booking_url: Optional[str] = None
    availability_status: str = "COUNTER_TICKETING_UNRESERVED"
    availability_source: str = "Official Counter / Station"
    journey_type: str = "DIRECT"  # "DIRECT" | "CONNECTING" | "LOCAL_REGIONAL"
    connecting_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Strict fail-safe: bus schedules are timetable/statutory guidance, never live tracking
        self.is_live_status = False

        # Convert claim dicts to ClaimVerification instances if passed as dicts
        for attr in ("route_verification", "operator_verification", "timetable_verification", "fare_verification"):
            val = getattr(self, attr)
            if isinstance(val, dict):
                setattr(self, attr, ClaimVerification(**val))

        # Fail-closed rules for timetable & fare claims:
        # 1. Root URL without deep schedule document reference cannot claim verified_official_source for timetable
        if self.timetable_verification:
            doc_ref = (self.timetable_verification.document_reference or "").lower()
            if self.timetable_verification.status in (
                VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            ):
                if not doc_ref or any(kw in doc_ref for kw in ("unpublished", "guidance", "inquiry", "window")):
                    self.timetable_verification.status = VerificationStatus.INDICATIVE_INFORMATION.value

        # 2. Fare verification cannot be verified_official_source if it is an estimated market tariff
        if self.fare_verification:
            if self.fare_classification == "ESTIMATED_MARKET_TARIFF" and self.fare_verification.status == VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value:
                self.fare_verification.status = VerificationStatus.INDICATIVE_INFORMATION.value

        # Fail-closed verification downgrade if primary evidence missing
        valid_verified_statuses = (
            VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            VerificationStatus.PARTIALLY_VERIFIED.value,
        )
        if (
            not self.source_name
            or not self.source_url
            or not self.source_circular_reference
            or not self.verified_at
            or not self.verified_by
            or self.verification_status not in valid_verified_statuses
        ):
            self.verification_status = VerificationStatus.UNVERIFIED.value

    def to_dict(self) -> Dict[str, Any]:
        """Serializes bus schedule to dictionary."""
        return asdict(self)


@dataclass
class CuratedFlightSchedule:
    """Authoritative, human-verified public flight schedule record connecting nationwide origins to Jammu (IXJ)."""
    route_id: str
    airline_name: str
    airline_code: str
    origin_airport_code: str
    origin_airport_name: str
    origin_city: str
    destination_airport_code: str = "IXJ"
    destination_airport_name: str = "Jammu Airport (Satwari)"
    destination_city: str = "Jammu"
    flight_number: Optional[str] = None
    route_type: str = "DIRECT"  # DIRECT, CONNECTING, ROUTE_GUIDANCE_ONLY
    layover_airports: List[str] = field(default_factory=list)
    operating_days: List[str] = field(default_factory=lambda: ["Daily"])
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_hours: Optional[float] = None
    estimated_duration_desc: Optional[str] = None
    schedule_type: str = "PUBLISHED_COMMERCIAL_TIMETABLE"  # PUBLISHED_COMMERCIAL_TIMETABLE, CONNECTING_SERVICE_WINDOW, ROUTE_GUIDANCE_ONLY
    schedule_effective_period: Optional[str] = None
    indicative_fare_min: Optional[int] = None
    indicative_fare_max: Optional[int] = None
    fare_currency: str = "INR"
    fare_classification: str = "ESTIMATED_MARKET_TARIFF"  # ESTIMATED_MARKET_TARIFF, UNAVAILABLE
    fare_disclaimer: str = (
        "Indicative market airfare range based on advance purchase tariffs. "
        "Real-time ticket prices, baggage fees, and seat availability vary dynamically "
        "by carrier and demand. Confirm live fares directly on official airline portals."
    )
    source_name: str = "Airports Authority of India & Published Airline Timetables"
    source_url: Optional[str] = None
    source_reference: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    verification_status: str = VerificationStatus.VERIFIED_CURATED_SOURCE.value
    is_live_status: bool = False  # Strictly False: static schedule guidance, not live telemetry
    availability_verified: bool = False  # Strictly False: student project does not integrate airline seat reservation APIs
    seat_count: Optional[int] = None  # Strictly None
    notes: Optional[str] = None
    record_updated_at: Optional[str] = None
    audited_at: Optional[str] = None
    # Claim-level verification breakdown
    route_verification: Optional[ClaimVerification] = None
    airline_verification: Optional[ClaimVerification] = None
    timetable_verification: Optional[ClaimVerification] = None
    fare_verification: Optional[ClaimVerification] = None

    def __post_init__(self):
        # Strict fail-safe: flight schedules are timetable/guidance, never live tracking or booking inventory
        self.is_live_status = False
        self.availability_verified = False
        self.seat_count = None

        # Convert claim dicts to ClaimVerification instances if passed as dicts
        for attr in ("route_verification", "airline_verification", "timetable_verification", "fare_verification"):
            val = getattr(self, attr)
            if isinstance(val, dict):
                setattr(self, attr, ClaimVerification(**val))

        # Fail-closed rules for timetable & duration:
        # If departure time is absent or schedule is guidance-only, static duration is unsupported
        if not self.departure_time or self.route_type in ("CONNECTING", "ROUTE_GUIDANCE_ONLY"):
            self.duration_hours = None
            self.estimated_duration_desc = None
            if not self.departure_time and self.schedule_type != "CONNECTING_HUB_GUIDANCE":
                self.schedule_type = "ROUTE_GUIDANCE_ONLY"

        if self.timetable_verification:
            if not self.departure_time or self.route_type in ("CONNECTING", "ROUTE_GUIDANCE_ONLY"):
                if self.timetable_verification.status in (
                    VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                    VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                    VerificationStatus.PARTIALLY_VERIFIED.value,
                ):
                    self.timetable_verification.status = (
                        VerificationStatus.UNVERIFIED.value
                        if not self.departure_time
                        else VerificationStatus.INDICATIVE_INFORMATION.value
                    )
            elif self.timetable_verification.status == VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value:
                # Seasonal commercial flight timetable slots downgrade to partially_verified
                self.timetable_verification.status = VerificationStatus.PARTIALLY_VERIFIED.value

            if self.timetable_verification.status == VerificationStatus.UNVERIFIED.value:
                self.timetable_verification.verified_at = None
                self.timetable_verification.verified_by = None
                self.timetable_verification.effective_date = None

        # Fail-closed rules for fare verification:
        if self.indicative_fare_min is None and self.indicative_fare_max is None:
            self.fare_classification = "UNAVAILABLE"

        if self.fare_verification:
            if self.fare_classification in ("ESTIMATED_MARKET_TARIFF", "UNAVAILABLE"):
                if self.fare_verification.status in (
                    VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                    VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                    VerificationStatus.PARTIALLY_VERIFIED.value,
                ):
                    self.fare_verification.status = (
                        VerificationStatus.INDICATIVE_INFORMATION.value
                        if self.fare_classification == "ESTIMATED_MARKET_TARIFF"
                        else VerificationStatus.UNVERIFIED.value
                    )

            if self.fare_verification.status == VerificationStatus.UNVERIFIED.value:
                self.fare_verification.verified_at = None
                self.fare_verification.verified_by = None
                self.fare_verification.effective_date = None

        # Record-level verification check
        if (
            not self.source_name
            or not self.source_url
            or not self.verified_at
            or not self.verified_by
            or self.verification_status != VerificationStatus.VERIFIED_CURATED_SOURCE.value
        ):
            self.verification_status = VerificationStatus.UNVERIFIED.value

    def to_dict(self) -> Dict[str, Any]:
        """Serializes flight schedule to dictionary, converting ClaimVerification instances."""
        d = asdict(self)
        for attr in ("route_verification", "airline_verification", "timetable_verification", "fare_verification"):
            val = getattr(self, attr)
            if val and hasattr(val, "to_dict"):
                d[attr] = val.to_dict()
        return d


# -----------------------------------------------------------------------------
# 2. PROVIDER METADATA
# -----------------------------------------------------------------------------

@dataclass
class ProviderMetadata:
    """Descriptive metadata and capability specification for a provider."""
    provider_id: str
    provider_name: str
    domain: str
    is_configured: bool = False
    operational_status: str = ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value
    is_source_verified: bool = False
    priority: int = 100  # Lower number = higher selection priority (e.g., 10 > 100)
    capabilities: List[str] = field(default_factory=list)
    last_retrieval_timestamp: Optional[str] = None
    last_verified_timestamp: Optional[str] = None
    is_simulated: bool = False
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes metadata to clean dictionary, preserving empty/None timestamp if unretrieved."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


# -----------------------------------------------------------------------------
# 3. PROVIDER REQUEST & RECURSIVE PRIVACY ISOLATION
# -----------------------------------------------------------------------------

_PRIVATE_FIELD_KEYWORDS: Tuple[str, ...] = (
    "booking", "pnr", "passenger", "pax_name", "pax", "user_id", "email",
    "phone", "mobile", "contact", "contact_number", "aadhaar", "passport",
    "pan_card", "pan_number", "voter_id", "id_number", "driving_license",
    "license_number", "credit_card", "card_number", "cvv", "upi", "upi_id",
    "token", "secret", "auth", "otp", "password", "res_id", "voucher",
    "name", "full_name", "customer_name", "first_name", "last_name",
    "dob", "date_of_birth"
)

# Public identifier keywords that must not be falsely flagged by substring matching
_PUBLIC_NAME_EXCLUSIONS: Tuple[str, ...] = (
    "hotel_name", "property_name", "location_name", "city_name",
    "domain_name", "source_name", "provider_name", "landmark_name",
    "service_name", "place_name", "station_name", "route_name",
    "state_name", "country_name", "category_name"
)


def _normalize_key_name(key: Any) -> Tuple[str, str]:
    """Normalizes field name into (snake_cased, alphanumeric_clean) formats,
    resolving case differences, hyphens, and camelCase variations.
    """
    s = str(key)
    # Convert camelCase to snake_case
    s_snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()
    s_snake = re.sub(r"[- \.]", "_", s_snake)
    s_clean = re.sub(r"[^a-z0-9]", "", s.lower())
    return s_snake, s_clean


def is_private_key_name(key: Any) -> bool:
    """Evaluates whether a field key represents a private, PII, or security-sensitive identifier.
    Excludes public metadata attributes like hotel_name, location_name, or source_name.
    """
    s_snake, s_clean = _normalize_key_name(key)

    # Check public exclusions first
    if any(ex in s_snake for ex in _PUBLIC_NAME_EXCLUSIONS):
        return False

    # Check for specific person name field rules
    person_name_prefixes = ("pax_", "passenger_", "customer_", "user_", "devotee_", "first_", "last_", "full_", "guest_")
    if s_snake == "name" or s_clean == "name":
        return True
    if any(s_snake == prefix + "name" for prefix in person_name_prefixes):
        return True

    # Check against all normalized private keywords
    for kw in _PRIVATE_FIELD_KEYWORDS:
        if kw in ("name", "full_name", "customer_name", "first_name", "last_name", "pax_name"):
            continue  # Already handled precisely above
        kw_snake, kw_clean = _normalize_key_name(kw)
        if kw_snake in s_snake or kw_clean in s_clean:
            return True

    return False


def contains_private_data(data: Any, depth: int = 0, max_depth: int = 10) -> bool:
    """Recursively inspects dictionaries, lists, tuples, sets, and objects for private
    PII, booking, passenger, or security-sensitive fields at every nesting level.
    Fails closed (returns True) on excessive recursion depth or unsupported structures.
    """
    if depth > max_depth:
        # Fail closed on excessively deep or circular structures
        return True

    if isinstance(data, dict):
        for k, v in data.items():
            if is_private_key_name(k):
                return True
            if contains_private_data(v, depth + 1, max_depth):
                return True
        return False

    elif isinstance(data, (list, tuple, set)):
        for item in data:
            if contains_private_data(item, depth + 1, max_depth):
                return True
        return False

    elif isinstance(data, (str, int, float, bool, bytes)) or data is None:
        return False

    # Fail closed for unexpected or unsupported complex objects
    return True


@dataclass
class ProviderRequest:
    """Validated input container for live data provider operations with strict privacy safeguards."""
    domain: str
    params: Dict[str, Any] = field(default_factory=dict)
    location: Optional[str] = None
    date_range: Optional[Tuple[str, str]] = None
    freshness_preference: Optional[str] = None  # e.g., 'cached_ok', 'live_preferred', 'force_refresh'
    session_id: Optional[str] = None
    min_rooms: Optional[int] = 1
    is_private_request: bool = False

    def is_private(self) -> bool:
        """Determines if the request contains private user identifiers, session context,
        or reservation details that MUST NOT enter the shared public cache.
        Recursively inspects all nested structures and fails closed on uncertain inputs.
        """
        if self.is_private_request:
            return True
        return contains_private_data(self.params)

    def validate(self) -> None:
        """Validates core request invariants before dispatch."""
        if not self.domain or not str(self.domain).strip():
            raise ValueError("ProviderRequest must specify a non-empty domain.")

        # If date_range is provided, ensure format validity (YYYY-MM-DD)
        if self.date_range:
            start, end = self.date_range
            iso_date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
            if not iso_date_pattern.match(str(start)) or not iso_date_pattern.match(str(end)):
                raise ValueError(f"Invalid date_range format: ({start}, {end}). Expected YYYY-MM-DD.")

    def to_cache_params(self) -> Dict[str, Any]:
        """Extracts deterministic parameters for public cache key generation.
        Strictly and recursively strips all private devotee identifiers, tokens,
        credentials, and nested private structures.
        """
        def _sanitize_dict(d: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
            if depth > 10:
                return {}
            out: Dict[str, Any] = {}
            for k, v in d.items():
                if is_private_key_name(k):
                    continue
                if isinstance(v, dict):
                    sanitized_v = _sanitize_dict(v, depth + 1)
                    if sanitized_v:
                        out[k] = sanitized_v
                elif isinstance(v, (list, tuple)):
                    sanitized_list = []
                    for item in v:
                        if isinstance(item, dict):
                            s_item = _sanitize_dict(item, depth + 1)
                            if s_item:
                                sanitized_list.append(s_item)
                        elif not contains_private_data(item, depth + 1):
                            sanitized_list.append(item)
                    out[k] = sanitized_list if isinstance(v, list) else tuple(sanitized_list)
                elif not contains_private_data(v, depth + 1):
                    out[k] = v
            return out

        filtered = _sanitize_dict(self.params)

        if self.location:
            filtered["location"] = str(self.location).strip().lower()
        if self.date_range:
            filtered["start_date"] = self.date_range[0]
            filtered["end_date"] = self.date_range[1]
        if self.min_rooms and self.min_rooms > 1:
            filtered["min_rooms"] = self.min_rooms

        return filtered


# -----------------------------------------------------------------------------
# 4. PROVIDER ERROR
# -----------------------------------------------------------------------------

@dataclass
class ProviderError:
    """Sanitized, safe error representation omitting secrets, stack traces, and raw URLs."""
    error_type: Union[ProviderErrorType, str]
    message: str
    provider_id: str
    domain: str
    status_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # Normalize error_type to string value
        if isinstance(self.error_type, Enum):
            self.error_type = self.error_type.value

        # Sanitize message to prevent accidental credential or API key leakage
        sanitized = str(self.message)
        sanitized = re.sub(r"(key|token|secret|password|bearer)=[\w\-]+", r"\1=[REDACTED]", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"Bearer\s+[\w\-]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
        self.message = sanitized

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "error_type": self.error_type,
            "message": self.message,
            "provider_id": self.provider_id,
            "domain": self.domain,
        }
        if self.status_code is not None:
            d["status_code"] = self.status_code
        if self.details:
            d["details"] = self.details
        return d


# -----------------------------------------------------------------------------
# 5. LIVE DATA RESULT
# -----------------------------------------------------------------------------

@dataclass
class LiveDataResult:
    """Unified, strongly-typed result container for live and cached data retrieval."""
    status: str  # 'SUCCESS', 'NO_RESULTS', 'ERROR', 'UNAVAILABLE', 'FALLBACK'
    domain: str
    data: Optional[Any] = None
    provider_id: str = ""
    source_provenance: Optional[Dict[str, Any]] = None
    retrieval_timestamp: str = field(default_factory=get_utc_now_iso)
    data_timestamp: Optional[str] = None
    freshness_status: str = FreshnessStatus.NOT_APPLICABLE.value
    verification_status: str = VerificationStatus.UNVERIFIED.value
    availability_verified: bool = False
    claims_breakdown: Optional[Dict[str, str]] = None
    error: Optional[ProviderError] = None
    advisory: Optional[str] = None
    is_cached: bool = False
    cached_state: Optional[str] = None

    def __post_init__(self):
        # Normalize freshness and verification
        self.freshness_status = normalize_freshness_status(self.freshness_status)
        self.verification_status = normalize_verification_status(self.verification_status)

        # Enforce truth-in-data validation rules:
        # Rule 1: Static curated data can never be marked as live
        if self.source_provenance and self.source_provenance.get("source_type") in (
            SourceType.CURATED_DATA.value, SourceType.STATIC_RAG.value
        ) and self.freshness_status == FreshnessStatus.LIVE.value:
            self.freshness_status = FreshnessStatus.NOT_APPLICABLE.value

        # Rule 2: Simulated data must always have simulation verification status
        if self.source_provenance and self.source_provenance.get("source_type") == SourceType.SIMULATED_DATA.value:
            self.verification_status = VerificationStatus.SIMULATION_ONLY.value

        # Rule 3: Unavailable data cannot be marked as verified_external_api
        if self.freshness_status == FreshnessStatus.UNAVAILABLE.value:
            self.verification_status = VerificationStatus.UNVERIFIED.value

        # Ensure retrieval_timestamp is timezone-aware ISO 8601 UTC
        if not self.retrieval_timestamp:
            self.retrieval_timestamp = get_utc_now_iso()
        elif not ("+" in self.retrieval_timestamp or self.retrieval_timestamp.endswith("Z")):
            self.retrieval_timestamp = f"{self.retrieval_timestamp}+00:00"

        # Validate or build provenance if data is present but source_provenance is missing
        if self.source_provenance is None and self.provider_id:
            s_type = SourceType.CACHED_API.value if self.is_cached else (
                SourceType.CURATED_DATA.value if self.freshness_status == FreshnessStatus.NOT_APPLICABLE.value else SourceType.LIVE_API.value
            )
            self.source_provenance = create_provenance(
                source_name=self.provider_id,
                source_type=s_type,
                freshness_status=self.freshness_status,
                verification_status=self.verification_status,
                retrieval_timestamp=self.retrieval_timestamp,
                data_timestamp=self.data_timestamp,
                domain=self.domain,
            )

    @property
    def is_success(self) -> bool:
        """Determines if the result represents a successful retrieval."""
        return self.status == "SUCCESS" and self.data is not None

    @property
    def is_empty(self) -> bool:
        """Determines if the result represents a successful query that returned 0 matching records."""
        return self.status == "NO_RESULTS"

    @property
    def source_type(self) -> Optional[str]:
        """Convenience accessor for source_type from source_provenance."""
        if isinstance(self.source_provenance, dict):
            return self.source_provenance.get("source_type")
        return None

    @property
    def source_name(self) -> Optional[str]:
        """Convenience accessor for source_name from source_provenance."""
        if isinstance(self.source_provenance, dict):
            return self.source_provenance.get("source_name")
        return None

    @property
    def disclaimer(self) -> Optional[str]:
        """Convenience accessor for disclaimer from source_provenance or advisory."""
        if isinstance(self.source_provenance, dict) and self.source_provenance.get("disclaimer"):
            return self.source_provenance.get("disclaimer")
        return self.advisory

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the result to a clean dictionary matching Yatra AI response conventions."""
        res: Dict[str, Any] = {
            "status": self.status,
            "domain": self.domain,
            "data": self.data,
            "provider_id": self.provider_id,
            "retrieval_timestamp": self.retrieval_timestamp,
            "data_timestamp": self.data_timestamp,
            "freshness_status": self.freshness_status,
            "verification_status": self.verification_status,
            "availability_verified": self.availability_verified,
            "is_cached": self.is_cached,
        }
        if self.claims_breakdown:
            res["claims_breakdown"] = self.claims_breakdown
        if self.source_provenance:
            res["source_provenance"] = self.source_provenance
        if self.error:
            res["error"] = self.error.to_dict()
        if self.advisory:
            res["advisory"] = self.advisory
        if self.cached_state:
            res["cached_state"] = self.cached_state
        return res
