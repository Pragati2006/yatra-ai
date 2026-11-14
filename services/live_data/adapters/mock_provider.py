"""
services/live_data/adapters/mock_provider.py
Deterministic Mock Provider for Testing Yatra AI Live Data Architecture.

Provides simulated outcomes (success, empty, timeout, malformed, error, unavailable)
strictly marked as SIMULATED_DATA with SIMULATION_ONLY verification.
MUST NEVER be registered in production registries.
"""

import time
from typing import Any, Dict, Optional, Tuple

from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderRequest,
)
from services.live_data.exceptions import (
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    get_utc_now_iso,
)


class MockTestLiveDataProvider(BaseLiveDataProvider):
    """Deterministic mock provider for framework unit & integration testing."""

    SCENARIO_SUCCESS = "success"
    SCENARIO_EMPTY = "empty"
    SCENARIO_TIMEOUT = "timeout"
    SCENARIO_MALFORMED = "malformed"
    SCENARIO_UNAVAILABLE = "unavailable"
    SCENARIO_ERROR = "error"
    SCENARIO_MISSING_CREDS = "missing_creds"
    SCENARIO_SCHEMA_INVALID = "schema_invalid"

    def __init__(
        self,
        provider_id: str = "mock_test_provider",
        provider_name: str = "Mock Test Demonstration Provider",
        domain: str = DataDomain.WEATHER.value,
        priority: int = 50,
        scenario: str = SCENARIO_SUCCESS,
        timeout_seconds: float = 1.0,
        custom_payload: Optional[Dict[str, Any]] = None,
        is_simulated: bool = True,
        is_source_verified: bool = False,
    ):
        super().__init__()
        self._provider_id = provider_id
        self._provider_name = provider_name
        self._domain = domain
        self._priority = priority
        self.scenario = scenario
        self._timeout_seconds = timeout_seconds
        self.custom_payload = custom_payload or {"mock_metric": 42, "description": "Deterministic mock test data"}
        self._is_simulated = is_simulated
        self._is_source_verified = is_source_verified
        self.call_count = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @property
    def is_simulated(self) -> bool:
        return self._is_simulated

    @property
    def is_source_verified(self) -> bool:
        return self._is_source_verified

    @property
    def default_source_type(self) -> str:
        if self.is_simulated:
            return SourceType.SIMULATED_DATA.value
        return SourceType.LIVE_API.value

    @property
    def default_verification_status(self) -> str:
        if self.is_simulated:
            return VerificationStatus.SIMULATION_ONLY.value
        if self.is_source_verified:
            return VerificationStatus.VERIFIED_EXTERNAL_API.value
        return VerificationStatus.UNVERIFIED.value

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        if self.scenario == self.SCENARIO_SCHEMA_INVALID:
            return False, "Simulated schema validation failure"
        return True, None

    def is_configured(self) -> bool:
        if self.scenario == self.SCENARIO_MISSING_CREDS:
            return False
        return True

    def is_available(self) -> bool:
        if self.scenario == self.SCENARIO_UNAVAILABLE:
            return False
        return super().is_available()

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Executes deterministic mock scenario."""
        self.call_count += 1

        if self.scenario == self.SCENARIO_TIMEOUT:
            # Simulate upstream delay exceeding provider timeout
            time.sleep(self.timeout_seconds + 0.5)
            raise ProviderTimeoutError(
                f"Mock provider '{self.provider_id}' simulated timeout.",
                provider_id=self.provider_id,
                domain=self.domain,
            )

        if self.scenario == self.SCENARIO_ERROR:
            raise ProviderExecutionError(
                "Simulated upstream provider connection failure.",
                provider_id=self.provider_id,
                domain=self.domain,
            )

        if self.scenario == self.SCENARIO_MALFORMED:
            # Raise malformed data exception
            raise ProviderMalformedResponseError(
                "Upstream provider returned malformed JSON payload.",
                provider_id=self.provider_id,
                domain=self.domain,
            )

        if self.scenario == self.SCENARIO_EMPTY:
            prov = self.build_provenance(
                request=request,
                freshness_status=FreshnessStatus.SIMULATED.value,
                verification_status=VerificationStatus.SIMULATION_ONLY.value,
                disclaimer="Simulated test provider; no records returned.",
            )
            return LiveDataResult(
                status="NO_RESULTS",
                domain=self.domain,
                data=[],
                provider_id=self.provider_id,
                source_provenance=prov,
                freshness_status=FreshnessStatus.SIMULATED.value,
                verification_status=VerificationStatus.SIMULATION_ONLY.value,
                advisory="Mock provider returned 0 records for testing.",
            )

        # Default: SCENARIO_SUCCESS
        fresh = FreshnessStatus.SIMULATED.value if self.is_simulated else FreshnessStatus.LIVE.value
        v_status = self.default_verification_status
        prov = self.build_provenance(
            request=request,
            freshness_status=fresh,
            verification_status=v_status,
            source_type=self.default_source_type,
            disclaimer="Simulated test demonstration data; not for operational use." if self.is_simulated else None,
            notes="MockTestLiveDataProvider deterministic test execution.",
        )
        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data=self.custom_payload,
            provider_id=self.provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=fresh,
            verification_status=v_status,
            advisory="Deterministic test response generated successfully.",
        )
