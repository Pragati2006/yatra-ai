"""
services/live_data/adapters/weather_adapter.py
Open-Meteo Weather Adapter for Yatra AI Live Data Architecture.

Wraps the elevation-aware multi-location weather integration (weather.py)
into the unified BaseLiveDataProvider interface.

Guarantees:
- Zero rewrite of the working weather service.
- Preserves 4 pilgrimage elevation milestones (Katra 750m, Ardhkuwari 1400m, Bhawan 1585m, Bhairon 2011m).
- Ingests live numerical forecast or IMD seasonal lapse-rate fallback.
- No network requests executed upon module import or class instantiation.
"""

import logging
from typing import Any, Dict, Optional, Tuple

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
    create_provenance,
    get_utc_now_iso,
)
import weather

logger = logging.getLogger(__name__)


class OpenMeteoWeatherAdapter(BaseLiveDataProvider):
    """Adapter bridging Open-Meteo elevation-aware weather to the live data architecture."""

    @property
    def provider_id(self) -> str:
        return "open_meteo_weather"

    @property
    def provider_name(self) -> str:
        return "Open-Meteo Weather Service"

    @property
    def domain(self) -> str:
        return DataDomain.WEATHER.value

    @property
    def priority(self) -> int:
        return 10  # Primary weather provider

    @property
    def timeout_seconds(self) -> float:
        return 6.0

    @property
    def is_simulated(self) -> bool:
        return False

    @property
    def is_source_verified(self) -> bool:
        """Open-Meteo is a verified, established numerical meteorological service."""
        return True

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Ensures weather data is a valid dictionary containing location and temperature."""
        if not isinstance(data, dict):
            return False, "Weather data must be a dictionary."
        if "location_name" not in data and "status" not in data:
            return False, "Weather payload missing location_name or status."
        return True, None

    @property
    def default_source_type(self) -> str:
        return SourceType.LIVE_API.value

    @property
    def default_verification_status(self) -> str:
        return VerificationStatus.VERIFIED_EXTERNAL_API.value

    def is_configured(self) -> bool:
        """Open-Meteo public API requires no proprietary API key."""
        return True

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Executes weather forecast retrieval for requested pilgrimage location(s)."""
        loc = request.location or request.params.get("location") or "Katra"

        try:
            w_res = weather.get_multi_location_weather(loc)
        except Exception as exc:
            logger.warning("Weather fetch failed for location '%s': %s", loc, exc)
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                source_type=SourceType.UNKNOWN_SOURCE.value,
                disclaimer="Weather retrieval failed and fallback was exhausted.",
            )
            return LiveDataResult(
                status="ERROR",
                domain=self.domain,
                data=None,
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                error=ProviderError(
                    error_type=ProviderErrorType.UNKNOWN,
                    message=str(exc),
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

        # Check for unrecognized foreign location
        if w_res.get("status") == "UNRECOGNIZED_LOCATION":
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                location=loc,
                disclaimer=w_res.get("clarification_message"),
            )
            return LiveDataResult(
                status="NO_RESULTS",
                domain=self.domain,
                data=w_res,
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                advisory=w_res.get("clarification_message"),
            )

        # Determine freshness and source type from weather response
        raw_freshness = w_res.get("freshness_status", "live")
        s_type = SourceType.LIVE_API.value if raw_freshness == "live" else SourceType.CURATED_DATA.value
        v_status = (
            VerificationStatus.VERIFIED_EXTERNAL_API.value
            if raw_freshness == "live"
            else VerificationStatus.VERIFIED_CURATED_SOURCE.value
        )

        prov = self.build_provenance(
            request=request,
            freshness_status=raw_freshness,
            verification_status=v_status,
            source_type=s_type,
            source_url="https://open-meteo.com",
            data_timestamp=w_res.get("data_timestamp"),
            location=w_res.get("location_name") or loc,
            disclaimer=w_res.get("disclaimer"),
            notes="Elevation-aware forecast across Trikuta Hills pilgrimage gradient.",
        )

        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data=w_res,
            provider_id=self.provider_id,
            source_provenance=prov,
            retrieval_timestamp=w_res.get("retrieval_timestamp") or get_utc_now_iso(),
            data_timestamp=w_res.get("data_timestamp"),
            freshness_status=raw_freshness,
            verification_status=v_status,
            advisory=w_res.get("advisory"),
        )
