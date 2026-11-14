"""
services/live_data/adapters/curated_bus_adapter.py
Curated Bus Timetable & Service Provider Adapter for Yatra AI.

Integrates curated, human-verified public bus schedules and statutory stage carriage
information into the Unified Live Data Architecture under DataDomain.TRANSPORT.

Adheres strictly to truth-in-data principles:
- Exposes official published JKRTC operating corridors and J&K STA statutory per-km fare slabs.
- NEVER claims live GPS location, real-time vehicle telemetry, or dynamic seat availability.
- Fails closed on missing or corrupted bus schedule data without fabricating routes or fares.
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


class CuratedBusAdapter(BaseLiveDataProvider):
    """Provider adapter serving curated, source-attributed bus schedules for Katra/Jammu corridors."""

    def __init__(self, dataset_path: Optional[str] = None):
        super().__init__()
        self._dataset_path = dataset_path or DEFAULT_BUS_SCHEDULES_PATH

    @property
    def provider_id(self) -> str:
        return "curated_bus_schedules"

    @property
    def provider_name(self) -> str:
        return "Curated JKRTC & STA Vaishno Devi Bus Schedules"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 12

    @property
    def timeout_seconds(self) -> float:
        return 2.0

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
        """Verifies existence of curated bus schedules dataset."""
        return os.path.exists(self._dataset_path)

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Validates that payload conforms to bus query response format."""
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        if "schedules" not in data or not isinstance(data["schedules"], list):
            return False, "Payload must contain a 'schedules' list."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Retrieves verified bus schedules based on request parameters."""
        origin = request.params.get("origin") or request.location
        destination = request.params.get("destination") or "Katra"
        service_id = request.params.get("service_id")
        travel_date = (
            request.params.get("travel_date")
            or request.params.get("date")
            or request.params.get("start_date")
        )

        if not origin and request.location:
            origin = request.location

        try:
            schedules, meta = search_curated_bus_schedules(
                origin=origin,
                destination=destination,
                service_id=service_id,
                travel_date=travel_date,
                file_path=self._dataset_path,
            )

            # Check if dataset failed to load (file missing / corrupt)
            if meta.get("error"):
                prov = self.build_provenance(
                    request=request,
                    source_url="https://jaktrans.jk.gov.in/",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer="Curated bus schedule dataset is temporarily unavailable.",
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
                    advisory="Bus schedule registry is currently offline. Please consult JKRTC directly.",
                )

            serialized_schedules = [s.to_dict() for s in schedules]

            prov = self.build_provenance(
                request=request,
                source_url=meta.get("source_url", "https://jaktrans.jk.gov.in/"),
                freshness_status=FreshnessStatus.CACHED.value,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                disclaimer=(
                    "Bus schedules reflect official published JKRTC timetable windows and J&K State "
                    "Transport Authority (STA) statutory stage carriage fare slabs. Live GPS location, "
                    "real-time dynamic seat reservations, and synthetic minute-level timetables are not connected. "
                    "Confirm departures and tariffs directly at bus stand counters or jksrtc.co.in."
                ),
            )

            data_payload = {
                "origin": origin,
                "destination": destination,
                "travel_date": travel_date,
                "count": len(serialized_schedules),
                "schedules": serialized_schedules,
                "live_status_available": False,
                "live_status_notice": (
                    "Live bus tracking and dynamic seat reservation are not connected in this phase. "
                    "Displayed information represents published operating windows and statutory fare slabs."
                ),
                "authority": meta.get("authority", "Government of Jammu & Kashmir Transport Department & JKRTC"),
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
                availability_verified=False,  # Seat availability is NOT checked dynamically
                claims_breakdown={
                    "statutory_fare_slabs": "VERIFIED_STA_NOTIFICATION",
                    "operating_windows": "VERIFIED_JKRTC_OPERATIONS",
                    "live_tracking": "NOT_CONNECTED",
                    "seat_reservation": "NOT_CHECKED",
                },
                advisory=(
                    "Stage carriage and public bus guide only. Purchase tickets directly at bus stand counters "
                    "or verify online booking availability at jksrtc.co.in."
                ),
            )

        except Exception as exc:
            logger.error("CuratedBusAdapter execution error: %s", exc, exc_info=True)
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
