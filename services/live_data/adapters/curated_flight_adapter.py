"""
services/live_data/adapters/curated_flight_adapter.py
Curated Flight Timetable & Service Provider Adapter for Yatra AI.

Integrates curated, human-verified public domestic flight schedules and route guidance
into the Unified Live Data Architecture under DataDomain.TRANSPORT.

Adheres strictly to truth-in-data principles:
- Exposes official published DGCA seasonal operating corridors and airline timetables connecting to Jammu (IXJ).
- NEVER claims live aircraft telemetry (ADS-B), real-time seat counts, or dynamic fare surges.
- Fails closed on missing or unsupported flight routes without fabricating flights or defaulting to Delhi.
"""

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional, Tuple

from services.flight_schedules import (
    DEFAULT_FLIGHT_SCHEDULES_PATH,
    search_curated_flight_schedules,
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


class CuratedFlightAdapter(BaseLiveDataProvider):
    """Provider adapter serving curated, source-attributed domestic flight schedules for Jammu Airport (IXJ)."""

    def __init__(self, dataset_path: Optional[str] = None):
        super().__init__()
        self._dataset_path = dataset_path or DEFAULT_FLIGHT_SCHEDULES_PATH

    @property
    def provider_id(self) -> str:
        return "curated_flight_schedules"

    @property
    def provider_name(self) -> str:
        return "Curated DGCA & Airline Vaishno Devi Flight Schedules"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 13

    @property
    def timeout_seconds(self) -> float:
        return 2.0

    @property
    def is_simulated(self) -> bool:
        return False

    def is_configured(self) -> bool:
        """Returns True if the curated flight schedules file exists and is accessible."""
        return os.path.exists(self._dataset_path)

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Executes flight schedule query against the curated dataset."""
        params = request.params or {}
        origin = params.get("origin") or request.location
        destination = params.get("destination", "Jammu")
        travel_date = params.get("travel_date")
        route_type = params.get("route_type")

        # If origin is completely missing, return fail-closed validation error
        if not origin or not str(origin).strip():
            error = ProviderError(
                error_type=ProviderErrorType.VALIDATION_ERROR.value,
                message="Origin city or airport code is required to search flight schedules.",
                provider_id=self.provider_id,
            )
            return LiveDataResult.error_result(
                domain=self.domain,
                provider_id=self.provider_id,
                error=error,
            )

        try:
            schedules, search_meta = search_curated_flight_schedules(
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                route_type=route_type,
                dataset_path=self._dataset_path,
            )
        except Exception as exc:
            logger.error("Curated flight adapter search error: %s", exc)
            error = ProviderError(
                error_type=ProviderErrorType.DATA_PARSING_ERROR.value,
                message=f"Failed to query curated flight schedules: {str(exc)}",
                provider_id=self.provider_id,
            )
            return LiveDataResult.error_result(
                domain=self.domain,
                provider_id=self.provider_id,
                error=error,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        serialized_schedules = [s.to_dict() for s in schedules]
        meta_dict = search_meta.get("metadata", {})

        source_prov = {
            "source_type": SourceType.CURATED_DATA.value,
            "source_name": meta_dict.get("authority", "Airports Authority of India & Scheduled Commercial Airlines"),
            "source_url": meta_dict.get("primary_official_source", "https://www.aai.aero/en/airports/jammu"),
            "curator": meta_dict.get("curator", "Yatra AI Transport Curatorial Desk"),
            "audit_status": meta_dict.get("audit_status", "AUDITED_PHASE_9_8_2"),
            "disclaimer": meta_dict.get(
                "disclaimer",
                "Flight schedule guidance based on published DGCA/airline timetables. Confirm real-time fares and seat availability on official airline website.",
            ),
        }

        claims = {
            "route_authority": meta_dict.get("authority", "Airports Authority of India & DGCA"),
            "verification_status": VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            "query_origin": origin,
            "total_matching_schedules": len(serialized_schedules),
            "ground_transfer_advisory": search_meta.get("ground_transfer_advisory"),
        }

        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data={
                "schedules": serialized_schedules,
                "search_metadata": search_meta,
                "origin": origin,
                "destination": destination,
                "total_count": len(serialized_schedules),
            },
            provider_id=self.provider_id,
            retrieval_timestamp=now_iso,
            data_timestamp=now_iso,
            freshness_status=FreshnessStatus.CACHED.value,
            verification_status=VerificationStatus.VERIFIED_CURATED_SOURCE.value,
            availability_verified=False,  # Strictly False: flight guidance, not live booking
            is_cached=False,
            claims_breakdown=claims,
            source_provenance=source_prov,
            advisory=search_meta.get("ground_transfer_advisory"),
        )
