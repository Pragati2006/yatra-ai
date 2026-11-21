"""
services/live_data/adapters/bus_data_adapter.py
Official Bus Transport Adapter for Jammu & Kashmir (JKRTC & STA Corridors).

Integrates official published timetables, statutory stage carriage operating
windows, and notified per-km fare slabs into the Unified Live Data Architecture
under DataDomain.TRANSPORT.

Adheres strictly to Truth-in-Data principles:
1. Published Schedule: Explicitly labeled as official timetable/operating window.
2. Live Tracking: Explicitly labeled as NOT_CONNECTED (no public GPS/GTFS-RT feed exists for J&K).
3. Fare Classification: Explicitly labeled as STATUTORY_GOVT_NOTIFIED_TARIFF under J&K STA Notification No. 01-P-MVD of 2026.
4. Seat Availability: Explicitly labeled as COUNTER_TICKETING / UNRESERVED.
5. Zero Fabrication: No synthetic GPS coordinates, delay minutes, or artificial seat counts.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

from services.bus_schedules import (
    DEFAULT_BUS_SCHEDULES_PATH,
    search_curated_bus_schedules,
)
from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderRequest,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class BusDataAdapter(BaseLiveDataProvider):
    """Modular Bus Transport Adapter providing verified JKRTC & STA bus services."""

    def __init__(self, dataset_path: Optional[str] = None):
        super().__init__()
        self._dataset_path = dataset_path or DEFAULT_BUS_SCHEDULES_PATH

    @property
    def provider_id(self) -> str:
        return "bus_data_adapter"

    @property
    def provider_name(self) -> str:
        return "Jammu-Kashmir & Katra Multi-Operator Bus Service Gateway (JKRTC, HRTC, PRTC & Private Operators)"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 2  # Higher priority than fallback curated bus adapter (priority 12)

    @property
    def timeout_seconds(self) -> float:
        return 3.0

    @property
    def is_simulated(self) -> bool:
        return False

    @property
    def is_source_verified(self) -> bool:
        return True

    @property
    def default_source_type(self) -> str:
        return SourceType.CURATED_DATA.value

    @property
    def default_verification_status(self) -> str:
        return VerificationStatus.VERIFIED_CURATED_SOURCE.value

    def is_configured(self) -> bool:
        return os.path.exists(self._dataset_path)

    def validate_request(self, request: ProviderRequest) -> None:
        if request.domain.strip().lower() != self.domain:
            raise ValueError(f"Domain '{request.domain}' is not supported by {self.provider_id}")

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        if "schedules" not in data or not isinstance(data["schedules"], list):
            return False, "Payload must contain a 'schedules' list."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        origin = request.params.get("origin") or request.location
        destination = request.params.get("destination") or "Katra"
        service_id = request.params.get("service_id")
        travel_date = (
            request.params.get("travel_date")
            or request.params.get("date")
            or request.params.get("start_date")
        )

        operator_type = request.params.get("operator_type")
        bus_type = request.params.get("bus_type")
        journey_type = request.params.get("journey_type")
        direct_only = bool(request.params.get("direct_only", False))
        max_fare = request.params.get("max_fare")
        sort_by = request.params.get("sort_by")

        if not origin and request.location:
            origin = request.location

        try:
            schedules, meta = search_curated_bus_schedules(
                origin=origin,
                destination=destination,
                service_id=service_id,
                travel_date=travel_date,
                file_path=self._dataset_path,
                operator_type=operator_type,
                bus_type=bus_type,
                journey_type=journey_type,
                direct_only=direct_only,
                max_fare=max_fare,
                sort_by=sort_by,
            )

            if meta.get("error"):
                prov = self.build_provenance(
                    request=request,
                    source_url="https://jaktrans.jk.gov.in/",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer="Bus transport registry is temporarily unavailable.",
                )
                return LiveDataResult(
                    status="UNAVAILABLE",
                    domain=self.domain,
                    data={
                        "schedules": [],
                        "count": 0,
                        "origin": origin,
                        "destination": destination,
                        "live_status_available": False,
                    },
                    provider_id=self.provider_id,
                    source_provenance=prov,
                    error=ProviderError(
                        error_type=ProviderErrorType.UNAVAILABLE.value,
                        message=f"Bus schedule registry unavailable: {meta.get('message', meta.get('error'))}",
                        provider_id=self.provider_id,
                        domain=self.domain,
                    ),
                    advisory="Official bus schedule registry is offline. Please consult JKRTC counters directly.",
                )

            serialized_schedules = [s.to_dict() for s in schedules]

            prov = self.build_provenance(
                request=request,
                source_url=meta.get("source_url", "https://jaktrans.jk.gov.in/"),
                freshness_status=FreshnessStatus.CACHED.value,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                disclaimer=(
                    "Bus schedules reflect official published JKRTC timetable windows and J&K State "
                    "Transport Authority (STA) statutory stage carriage fare slabs. Live GPS telemetry, "
                    "real-time dynamic seat reservations, and synthetic minute-level timetables are not connected. "
                    "Tickets can be purchased at bus stand counters or on board from conductors. Interstate reservations on jksrtc.co.in."
                ),
            )

            direct_count = sum(1 for s in schedules if s.journey_type == "DIRECT")
            connecting_count = sum(1 for s in schedules if s.journey_type == "CONNECTING")
            government_count = sum(1 for s in schedules if s.operator_type == "government")
            private_count = sum(1 for s in schedules if s.operator_type == "private")
            operators_found = list(sorted({s.operator_name for s in schedules}))

            data_payload = {
                "origin": origin,
                "destination": destination,
                "travel_date": travel_date,
                "count": len(serialized_schedules),
                "direct_count": direct_count,
                "connecting_count": connecting_count,
                "government_count": government_count,
                "private_count": private_count,
                "operators": operators_found,
                "schedules": serialized_schedules,
                "schedule_type": "PUBLISHED_OFFICIAL_TIMETABLE",
                "live_tracking": "NOT_CONNECTED",
                "live_tracking_notice": (
                    "Live GPS tracking is not connected for public stage carriages in Jammu & Kashmir. "
                    "No public GTFS-RT telemetry feed is published by J&K transport authorities."
                ),
                "fare_classification": "STATUTORY_GOVT_NOTIFIED_TARIFF",
                "fare_notice": (
                    "Fares reflect statutory notified maximum tariffs under J&K STA Notification No. 01-P-MVD of 2026 for government services, "
                    "and published operator tariff ranges for private Volvo/BharatBenz services. "
                    "Tickets are purchased directly at bus stand counters, on board, or via operator booking websites."
                ),
                "seat_availability": "COUNTER_TICKETING_UNRESERVED",
                "seat_availability_notice": (
                    "Seats on regional stage carriages are unreserved and allocated on arrival. "
                    "Advance online seat selection is available for private sleeper buses and interstate Volvo coaches via their respective booking portals."
                ),
                "booking_portals": {
                    "JKRTC": "https://jksrtc.co.in/",
                    "HRTC": "https://hrtchp.com/",
                    "Laxmi Holidays": "https://www.laxmiholidays.com/",
                    "Zingbus": "https://www.zingbus.com/",
                    "FlixBus": "https://www.flixbus.in/",
                    "IntrCity": "https://www.intrcity.com/",
                    "Ram Dalal Holidays": "https://www.ramdalaltravels.com/",
                    "RedBus (Aggregator)": "https://www.redbus.in/bus-tickets/delhi-to-katra",
                },
                "helpline_contacts": {
                    "jammu_general_bus_stand": "0191-2476290",
                    "srinagar_trc": "0194-2472436",
                    "katra_central_bus_stand": "01991-232049",
                    "udhampur_bus_stand": "01992-270220",
                    "jksrtc_central_helpline": "+91-9149473175",
                    "official_portal": "https://jksrtc.co.in/",
                },
                "authority": meta.get("authority", "Government of Jammu & Kashmir Transport Department, STA & JKRTC"),
            }

            if meta.get("coverage_limitation"):
                data_payload["coverage_limitation"] = meta.get("coverage_limitation")

            return LiveDataResult(
                status="SUCCESS",
                domain=self.domain,
                data=data_payload,
                provider_id=self.provider_id,
                source_provenance=prov,
                retrieval_timestamp=prov.get("retrieval_timestamp"),
                data_timestamp=meta.get("last_audit_date"),
                freshness_status=FreshnessStatus.CACHED.value,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                availability_verified=False,
                claims_breakdown={
                    "published_schedule": "OFFICIAL_JKRTC_STA_TIMETABLE",
                    "live_tracking": "NOT_CONNECTED",
                    "statutory_fare": "VERIFIED_STA_NOTIFICATION_01_P_MVD_2026",
                    "seat_availability": "COUNTER_TICKETING_UNRESERVED",
                },
                advisory=(
                    "Stage carriage and public bus service guide. Fares and timings are governed by official STA notifications. "
                    "Tickets are issued at bus stand counters or on board by conductors. For interstate Volvo services, verify online booking at jksrtc.co.in."
                ),
            )

        except Exception as exc:
            logger.error("BusDataAdapter query error: %s", exc, exc_info=True)
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="An unexpected error occurred while querying bus schedule data.",
            )
            return LiveDataResult(
                status="ERROR",
                domain=self.domain,
                data={
                    "schedules": [],
                    "count": 0,
                    "live_status_available": False,
                },
                provider_id=self.provider_id,
                source_provenance=prov,
                error=ProviderError(
                    error_type=ProviderErrorType.UNKNOWN.value,
                    message=f"Bus adapter query failure: {str(exc)}",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

