"""
services/live_data/adapters/curated_contact_adapter.py
Verified Contact Registry Provider Adapter for Yatra AI.

Integrates the human-verified, official contact directory into the Phase 9.5
Live Data Architecture under DataDomain.EMERGENCY.

Governance Rules:
- Primary emergency number 112 is always prioritized and displayed.
- Unverified numbers are suppressed by default.
- Operating hours and non-emergency administrative distinctions are strictly preserved.
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
from services.verified_contacts import (
    DEFAULT_CONTACTS_PATH,
    query_verified_contacts,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    get_utc_now_iso,
)

logger = logging.getLogger(__name__)


class VerifiedContactAdapter(BaseLiveDataProvider):
    """Provider adapter serving verified emergency and operational helpline contacts."""

    def __init__(self, contacts_file_path: Optional[str] = None):
        super().__init__()
        self._contacts_file_path = contacts_file_path or DEFAULT_CONTACTS_PATH

    @property
    def provider_id(self) -> str:
        return "verified_contact_registry"

    @property
    def provider_name(self) -> str:
        return "Verified Emergency & Operational Contact Registry"

    @property
    def domain(self) -> str:
        return DataDomain.EMERGENCY.value

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
        return os.path.exists(self._contacts_file_path)

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        if not isinstance(data, dict) or "contacts" not in data:
            return False, "Payload must be a dictionary containing a 'contacts' list."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Retrieves verified contacts according to request parameters."""
        category = request.params.get("category")
        jurisdiction = request.params.get("jurisdiction") or request.location
        include_unverified = request.params.get("include_unverified", False)

        contacts, metadata = query_verified_contacts(
            category=category,
            jurisdiction=jurisdiction,
            include_unverified=include_unverified,
            file_path=self._contacts_file_path,
        )

        prov = self.build_provenance(
            request=request,
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            source_url="https://112.gov.in",
            disclaimer=(
                "Curated directory of statutory and official administrative helplines. "
                "For active life-safety emergencies, dial 112 directly."
            ),
        )

        result_data = {
            "contacts": contacts,
            "total_contacts": len(contacts),
            "primary_emergency_directive": metadata.get("primary_emergency_directive"),
            "primary_emergency_number": metadata.get("primary_emergency_number", "112"),
            "metadata": metadata,
        }

        status_code = "SUCCESS" if contacts else "NO_RESULTS"

        return LiveDataResult(
            status=status_code,
            domain=self.domain,
            data=result_data,
            provider_id=self.provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=FreshnessStatus.NOT_APPLICABLE.value,
            verification_status=self.default_verification_status,
            advisory=metadata.get("disclaimer"),
        )


CuratedContactAdapter = VerifiedContactAdapter
