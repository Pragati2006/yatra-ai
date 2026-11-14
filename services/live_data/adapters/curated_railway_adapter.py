"""
services/live_data/adapters/curated_railway_adapter.py
Curated Railway Timetable Provider Adapter for Yatra AI.

Integrates the curated, human-verified railway timetable dataset into the
Unified Live Data Architecture under DataDomain.TRANSPORT.

Adheres strictly to truth-in-data principles:
- Exposes official published Indian Railways timetable schedules for the Katra corridor.
- NEVER claims live running status, real-time GPS telemetry, or dynamic platform numbers.
- Fails closed on missing or corrupted timetable data without fabricating schedules.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderRequest,
)
from services.railway_schedules import (
    DEFAULT_SCHEDULES_PATH,
    search_curated_schedules,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class CuratedRailwayAdapter(BaseLiveDataProvider):
    """Provider adapter serving curated, source-attributed railway timetables for Katra/Jammu routes."""

    def __init__(self, dataset_path: Optional[str] = None):
        super().__init__()
        self._dataset_path = dataset_path or DEFAULT_SCHEDULES_PATH

    @property
    def provider_id(self) -> str:
        return "curated_railway_schedules"

    @property
    def provider_name(self) -> str:
        return "Curated Indian Railways Vaishno Devi Corridor Schedules"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 10

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
        """Verifies existence of curated railway timetable dataset."""
        return os.path.exists(self._dataset_path)

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Validates that payload conforms to railway query response format."""
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        if "schedules" not in data or not isinstance(data["schedules"], list):
            return False, "Payload must contain a 'schedules' list."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Retrieves verified timetable schedules based on request parameters."""
        origin = request.params.get("origin") or request.location
        destination = request.params.get("destination") or "Katra"
        train_number = request.params.get("train_number")
        travel_date = request.params.get("travel_date") or request.params.get("date") or request.params.get("start_date")
        class_code = request.params.get("class_code") or request.params.get("travel_class")

        # Fallback location check if origin was empty
        if not origin and request.location:
            origin = request.location

        try:
            schedules, meta = search_curated_schedules(
                origin=origin,
                destination=destination,
                train_number=train_number,
                travel_date=travel_date,
                class_code=class_code,
                file_path=self._dataset_path,
            )

            # Check if dataset failed to load (file missing / corrupt)
            if meta.get("error"):
                prov = self.build_provenance(
                    request=request,
                    source_url="https://enquiry.indianrail.gov.in/",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer="Curated railway timetable dataset is temporarily unavailable.",
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
                        message=f"Timetable registry unavailable: {meta.get('message', meta.get('error'))}",
                        provider_id=self.provider_id,
                        domain=self.domain,
                    ),
                    advisory="Railway timetable registry is currently offline. Please consult IRCTC directly.",
                )

            serialized_schedules = [s.to_dict() for s in schedules]

            prov = self.build_provenance(
                request=request,
                source_url=meta.get("primary_official_source", "https://enquiry.indianrail.gov.in/"),
                freshness_status=FreshnessStatus.CACHED.value,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                disclaimer=(
                    "Timetables reflect official published Indian Railways operational schedules. "
                    "Live train status, delays, and dynamic platform allocations require live NTES/RailRadar telemetry. "
                    "Confirm live status via 139 or official railway enquiry counters."
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
                    "Live train running status (delays, real-time GPS coordinates, dynamic platform allocations) "
                    "is not connected in this phase. Displayed times are published timetable schedules."
                ),
                "authority": meta.get("authority", "Official Indian Railways Timetable"),
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
                data_timestamp=meta.get("last_verified_at"),
                freshness_status=FreshnessStatus.CACHED.value,
                verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
                availability_verified=False,  # Seat availability is NOT checked dynamically
                claims_breakdown={
                    "timetable_schedule": "VERIFIED_OFFICIAL_TIMETABLE",
                    "live_running_telemetry": "NOT_CONNECTED",
                    "seat_availability": "NOT_CHECKED",
                },
                advisory=(
                    "Published timetable information only. Real-time delays and platform numbers must be verified "
                    "via NTES (139) or IRCTC before travel."
                ),
            )

        except Exception as exc:
            logger.error("CuratedRailwayAdapter execution error: %s", exc, exc_info=True)
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="An unexpected error occurred while querying railway timetable data.",
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
                    message=f"Railway adapter query failure: {str(exc)}",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )
