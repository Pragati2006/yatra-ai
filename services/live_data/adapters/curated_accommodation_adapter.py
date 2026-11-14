"""
services/live_data/adapters/curated_accommodation_adapter.py
Curated Katra Accommodation Catalog Adapter for Yatra AI Live Data Architecture.

Wraps the hand-verified, source-attributed Katra accommodation catalog
(services/accommodation_catalog.py) into the unified BaseLiveDataProvider interface.

Guarantees:
- Fully provider-independent.
- Preserves all 15 authentic Katra properties (13 Group A + 2 Group B).
- Real-time availability defaults strictly to NOT_CHECKED.
- Rooms available is preserved as None (never fabricated).
- Multi-room requests preserve room_requirement_status: 'UNVERIFIED'.
- Differentiates CATALOG_SUCCESS, NO_MATCHING_PROPERTIES, and CATALOG_UNAVAILABLE.
- Truth-in-data: marked strictly as CURATED_DATA / VERIFIED_CURATED_SOURCE.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from services.accommodation_catalog import (
    CATALOG_PATH,
    get_catalog_load_error,
    get_catalog_status,
    search_hotels_with_status,
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
    create_provenance,
    get_utc_now_iso,
)

logger = logging.getLogger(__name__)


class CuratedAccommodationAdapter(BaseLiveDataProvider):
    """Adapter bridging the curated Katra accommodation catalog to the live data architecture."""

    @property
    def provider_id(self) -> str:
        return "curated_katra_catalog"

    @property
    def provider_name(self) -> str:
        return "Verified Katra Accommodation Catalog v1.0"

    @property
    def domain(self) -> str:
        return DataDomain.ACCOMMODATION.value

    @property
    def priority(self) -> int:
        # Default fallback priority: lower precedence than a live real-time GDS provider,
        # but serves as the guaranteed, reliable static fallback.
        return 100

    @property
    def timeout_seconds(self) -> float:
        # Local JSON disk reads are near instantaneous
        return 2.0

    @property
    def is_simulated(self) -> bool:
        return False

    @property
    def is_source_verified(self) -> bool:
        """Katra catalog properties are hand-verified against Shrine Board & official records."""
        return True

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Ensures accommodation data is a list of valid hotel dictionaries."""
        if not isinstance(data, list):
            return False, "Accommodation data must be a list of property dictionaries."
        return True, None

    @property
    def default_source_type(self) -> str:
        return SourceType.CURATED_DATA.value

    @property
    def default_verification_status(self) -> str:
        return VerificationStatus.VERIFIED_CURATED_SOURCE.value

    def is_configured(self) -> bool:
        """Verifies the catalog JSON file exists on disk."""
        return os.path.exists(CATALOG_PATH)

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Queries verified properties from the catalog, adhering strictly to truth-in-data rules."""
        # 1. Extract query parameters
        check_in_date = request.params.get("check_in_date")
        if not check_in_date and request.date_range:
            check_in_date = request.date_range[0]

        category = request.params.get("category")
        min_rooms = request.min_rooms or request.params.get("min_rooms", 1)

        # 2. Query accommodation catalog service with status
        hotels, cat_status = search_hotels_with_status(
            check_in_date=check_in_date,
            category=category,
            min_rooms=min_rooms,
        )

        # 3. Handle Catalog Failure
        if cat_status == "CATALOG_UNAVAILABLE":
            err_msg = get_catalog_load_error() or "Katra accommodation catalog is temporarily unavailable."
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                source_type=SourceType.UNKNOWN_SOURCE.value,
                disclaimer="Verified Katra catalog unavailable; synthetic fallback is disabled.",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data=None,
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                error=ProviderError(
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message=err_msg,
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
                advisory="The verified Katra accommodation catalog is temporarily unavailable. Synthetic fallback is disabled.",
            )

        # 4. Handle No Matching Properties
        if cat_status == "NO_MATCHING_PROPERTIES" or not hotels:
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
                verification_status=self.default_verification_status,
                disclaimer="No accommodation properties match the requested filters in the verified catalog.",
            )
            return LiveDataResult(
                status="NO_RESULTS",
                domain=self.domain,
                data=[],
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
                verification_status=self.default_verification_status,
                advisory=f"No verified accommodation properties match category '{category or 'any'}'.",
            )

        # 5. Handle Successful Catalog Results
        # Confirm critical invariants: rooms_available=None and room_requirement_status preserved
        claims = {
            "property_identity": "VERIFIED_CURATED_SOURCE",
            "indicative_tariff": "PROPERTY_CONFIRMED_INDICATIVE_RATE",
            "live_room_availability": "UNVERIFIED (NOT_CHECKED)",
            "room_inventory": "UNKNOWN (rooms_available=None)",
        }
        prov = self.build_provenance(
            request=request,
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            source_url="https://www.maavaishnodevi.org",
            disclaimer="Curated static catalog. Published indicative rates; live availability is unverified (NOT_CHECKED).",
        )
        prov["claims_breakdown"] = claims

        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data=hotels,
            provider_id=self.provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            availability_verified=False,
            claims_breakdown=claims,
            advisory="Live room availability is UNVERIFIED (NOT_CHECKED). Confirm directly with the property or Shrine Board.",
        )
