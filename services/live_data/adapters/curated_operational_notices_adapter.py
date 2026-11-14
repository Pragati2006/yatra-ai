"""
services/live_data/adapters/curated_operational_notices_adapter.py
Curated Operational Notices Provider Adapter for Yatra AI.

Integrates the curated, human-verified operational notices registry into the
Phase 9.5 Unified Live Data Architecture under DataDomain.OPERATIONAL_NOTICE.

Adheres strictly to truth-in-data:
- Disclaims live dynamic verification of government websites (strictly zero unauthorized scraping).
- Preserves explicit REQUIRES_REVERIFICATION notices.
- Communicates NO_ACTIVE_NOTICES honestly without fabricating 'smooth operations'.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    NoticeAggregateStatus,
    ProviderError,
    ProviderErrorType,
    ProviderRequest,
)
from services.operational_notices import (
    DEFAULT_NOTICES_PATH,
    query_curated_notices,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    get_utc_now_iso,
)

logger = logging.getLogger(__name__)


class CuratedOperationalNoticesAdapter(BaseLiveDataProvider):
    """Provider adapter serving curated operational notices from verified authority records."""

    def __init__(self, notices_file_path: Optional[str] = None):
        super().__init__()
        self._notices_file_path = notices_file_path or DEFAULT_NOTICES_PATH

    @property
    def provider_id(self) -> str:
        return "curated_operational_notices"

    @property
    def provider_name(self) -> str:
        return "Curated Vaishno Devi & NH-44 Operational Notice Registry"

    @property
    def domain(self) -> str:
        return DataDomain.OPERATIONAL_NOTICE.value

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
        return os.path.exists(self._notices_file_path)

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        if not isinstance(data, dict) or "notices" not in data:
            return False, "Payload must be a dictionary containing a 'notices' list."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Retrieves verified operational notices according to request parameters."""
        location = request.location or request.params.get("location")
        route = request.params.get("route")
        category = request.params.get("category")
        severity = request.params.get("severity")
        active_only = request.params.get("active_only", True)

        notices, agg_status, metadata = query_curated_notices(
            location=location,
            route=route,
            category=category,
            severity=severity,
            active_only=active_only,
            file_path=self._notices_file_path,
        )

        if agg_status == NoticeAggregateStatus.SOURCE_UNAVAILABLE.value:
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="Curated operational notices catalog is temporarily unavailable.",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={
                    "notices": [],
                    "aggregate_status": NoticeAggregateStatus.SOURCE_UNAVAILABLE.value,
                    "total_notices": 0,
                    "metadata": {
                        "advisory": "The curated operational notice catalog is temporarily unavailable.",
                        "aggregate_status": NoticeAggregateStatus.SOURCE_UNAVAILABLE.value,
                    },
                },
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                error=ProviderError(
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message="Curated operational notices catalog is unavailable.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
                advisory="The curated operational notice catalog is temporarily unavailable.",
            )

        prov = self.build_provenance(
            request=request,
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            source_url="https://www.maavaishnodevi.org",
            disclaimer=(
                "Human-verified official notice registry. Does NOT scrape live government pages. "
                "For active transit, always re-verify with official local helplines."
            ),
        )

        result_data = {
            "notices": notices,
            "aggregate_status": agg_status,
            "total_notices": len(notices),
            "metadata": metadata,
        }

        status_code = "SUCCESS" if agg_status == NoticeAggregateStatus.HAS_NOTICES.value else "NO_RESULTS"

        return LiveDataResult(
            status=status_code,
            domain=self.domain,
            data=result_data,
            provider_id=self.provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            advisory=metadata.get("advisory"),
        )
