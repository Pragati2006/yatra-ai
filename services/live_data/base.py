"""
services/live_data/base.py
Abstract Base Class for Live Data Providers in Yatra AI.

Enforces consistent identification, input validation, execution, timeout policies,
error handling, and provenance generation across all upstream data adapters.
"""

from abc import ABC, abstractmethod
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import (
    DataDomain,
    LiveDataResult,
    ProviderError,
    ProviderErrorType,
    ProviderMetadata,
    ProviderOperationalStatus,
    ProviderRequest,
)
from services.live_data.exceptions import (
    ProviderConfigurationError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    create_provenance,
    get_utc_now_iso,
    normalize_freshness_status,
    normalize_source_type,
    normalize_verification_status,
)

logger = logging.getLogger(__name__)


class BaseLiveDataProvider(ABC):
    """Abstract base class for all live, cached, and curated data providers."""

    def __new__(cls, *args, **kwargs):
        """Eagerly creates the instance and initializes its synchronization primitives
        and lifecycle metric attributes before any subclass __init__ or method can run.
        Guarantees thread-safe lock availability from the moment of instantiation.
        """
        instance = super().__new__(cls)
        instance._state_lock = threading.RLock()
        instance._total_requests = 0
        instance._successful_requests = 0
        instance._consecutive_failures = 0
        instance._cooldown_seconds = 60.0
        instance._failure_threshold = 3
        instance._unavailable_since = None
        instance._half_open_probe_active = False
        instance._last_retrieval_timestamp = None
        instance._last_verified_timestamp = None
        return instance

    def __init__(self) -> None:
        """Eagerly ensures reentrant synchronization lock and lifecycle metrics exist."""
        if not hasattr(self, "_state_lock"):
            self._state_lock = threading.RLock()

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine-readable identifier for this provider (e.g., 'open_meteo_weather')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable display name for the source (e.g., 'Open-Meteo Weather Service')."""
        pass

    @property
    @abstractmethod
    def domain(self) -> str:
        """Data domain serviced by this provider (e.g., 'weather', 'accommodation')."""
        pass

    @property
    def priority(self) -> int:
        """Selection priority for this provider within its domain.
        Lower values indicate higher preference (e.g., 10 > 100). Default is 100.
        """
        return 100

    @property
    def timeout_seconds(self) -> float:
        """Maximum permitted execution duration in seconds before raising ProviderTimeoutError."""
        return 5.0

    @property
    def is_simulated(self) -> bool:
        """True if the provider produces simulated or mock demonstration data."""
        return False

    @property
    def is_source_verified(self) -> bool:
        """True if the upstream identity and data authority has been independently verified.
        Unverified or third-party endpoints must remain False.
        """
        return False

    @property
    def default_source_type(self) -> str:
        """Default SourceType classification for provenance records."""
        if self.is_simulated:
            return SourceType.SIMULATED_DATA.value
        return SourceType.LIVE_API.value

    @property
    def default_verification_status(self) -> str:
        """Default VerificationStatus classification for provenance records."""
        if self.is_simulated:
            return VerificationStatus.SIMULATION_ONLY.value
        if self.is_source_verified:
            return VerificationStatus.VERIFIED_EXTERNAL_API.value
        return VerificationStatus.UNVERIFIED.value

    @property
    def _lock(self) -> threading.RLock:
        """Internal recursive lock ensuring thread-safe lifecycle and metrics updates."""
        return self._state_lock

    @property
    def cooldown_seconds(self) -> float:
        """Cooldown period in seconds after circuit breaker trips to UNAVAILABLE
        before a half-open trial probe is permitted. Default: 60.0 seconds.
        """
        with self._lock:
            return getattr(self, "_cooldown_seconds", 60.0)

    @cooldown_seconds.setter
    def cooldown_seconds(self, value: float) -> None:
        with self._lock:
            self._cooldown_seconds = float(value)

    @property
    def failure_threshold(self) -> int:
        """Number of consecutive failures required to trip circuit breaker to UNAVAILABLE."""
        with self._lock:
            return getattr(self, "_failure_threshold", 3)

    @failure_threshold.setter
    def failure_threshold(self, value: int) -> None:
        with self._lock:
            self._failure_threshold = max(1, int(value))

    @property
    def operational_status(self) -> str:
        """Realized operational status of the provider."""
        with self._lock:
            if not self.is_configured():
                return ProviderOperationalStatus.UNCONFIGURED.value
            if hasattr(self, "_operational_status"):
                return self._operational_status
            return ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value

    @operational_status.setter
    def operational_status(self, value: str) -> None:
        with self._lock:
            self._operational_status = value
            if value == ProviderOperationalStatus.UNAVAILABLE.value:
                self._unavailable_since = time.monotonic()
                self._half_open_probe_active = False
            elif value == ProviderOperationalStatus.OPERATIONAL.value:
                self._consecutive_failures = 0
                self._half_open_probe_active = False
                self._unavailable_since = None

    @property
    def consecutive_failures(self) -> int:
        with self._lock:
            return getattr(self, "_consecutive_failures", 0)

    @property
    def total_requests(self) -> int:
        with self._lock:
            return getattr(self, "_total_requests", 0)

    @property
    def successful_requests(self) -> int:
        with self._lock:
            return getattr(self, "_successful_requests", 0)

    @property
    def last_retrieval_timestamp(self) -> Optional[str]:
        with self._lock:
            return getattr(self, "_last_retrieval_timestamp", None)

    @property
    def last_verified_timestamp(self) -> Optional[str]:
        with self._lock:
            return getattr(self, "_last_verified_timestamp", None)

    @property
    def unavailable_since(self) -> Optional[float]:
        with self._lock:
            return getattr(self, "_unavailable_since", None)

    @property
    def is_half_open_probe_active(self) -> bool:
        with self._lock:
            return getattr(self, "_half_open_probe_active", False)

    def is_available(self) -> bool:
        """Determines if the provider is currently ready for request execution.
        Returns True for OPERATIONAL, DEGRADED, and CONFIGURED_PENDING_VERIFICATION.
        If UNAVAILABLE, returns True ONLY IF the cooldown period has expired (signaling
        that a half-open canary probe is eligible to be reserved).
        If HALF_OPEN, returns False for concurrent non-canary callers.
        """
        if not self.is_configured():
            return False

        with self._lock:
            st = self.operational_status
            if st in (
                ProviderOperationalStatus.OPERATIONAL.value,
                ProviderOperationalStatus.DEGRADED.value,
                ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value,
            ):
                return True

            if st == ProviderOperationalStatus.UNAVAILABLE.value:
                unav_since = getattr(self, "_unavailable_since", None)
                if unav_since is None:
                    return False
                return (time.monotonic() - unav_since) >= self.cooldown_seconds

            if st == ProviderOperationalStatus.HALF_OPEN.value:
                # Canary probe already active in flight
                return False

            return False

    def reserve_canary_probe(self) -> bool:
        """Atomically transitions provider from UNAVAILABLE to HALF_OPEN to reserve
        the single canary probe. Returns True if successfully reserved, False otherwise.
        """
        with self._lock:
            if not self.is_configured():
                return False

            st = self.operational_status
            if st == ProviderOperationalStatus.UNAVAILABLE.value:
                unav_since = getattr(self, "_unavailable_since", None)
                if unav_since is not None and (time.monotonic() - unav_since) >= self.cooldown_seconds:
                    self._operational_status = ProviderOperationalStatus.HALF_OPEN.value
                    self._half_open_probe_active = True
                    return True
                return False

            return False

    def record_execution_success(self) -> None:
        """Atomically records a successful upstream query execution, transitioning to OPERATIONAL state."""
        with self._lock:
            self._operational_status = ProviderOperationalStatus.OPERATIONAL.value
            self._consecutive_failures = 0
            self._unavailable_since = None
            self._half_open_probe_active = False
            self._total_requests = getattr(self, "_total_requests", 0) + 1
            self._successful_requests = getattr(self, "_successful_requests", 0) + 1
            now = get_utc_now_iso()
            self._last_retrieval_timestamp = now
            self._last_verified_timestamp = now

    def record_execution_failure(self, error_type: Optional[ProviderErrorType] = None) -> None:
        """Atomically records an execution failure, incrementing failure counter and degrading status.
        If in HALF_OPEN state or consecutive failures reach threshold, transitions to UNAVAILABLE
        and resets the cooldown timer using monotonic clock.
        """
        with self._lock:
            self._total_requests = getattr(self, "_total_requests", 0) + 1
            self._consecutive_failures = getattr(self, "_consecutive_failures", 0) + 1
            self._last_retrieval_timestamp = get_utc_now_iso()
            self._half_open_probe_active = False

            current_status = getattr(self, "_operational_status", ProviderOperationalStatus.CONFIGURED_PENDING_VERIFICATION.value)
            if current_status == ProviderOperationalStatus.HALF_OPEN.value:
                # Canary probe failed: immediately return to UNAVAILABLE and restart cooldown
                self._operational_status = ProviderOperationalStatus.UNAVAILABLE.value
                self._unavailable_since = time.monotonic()
            elif self._consecutive_failures >= self.failure_threshold:
                self._operational_status = ProviderOperationalStatus.UNAVAILABLE.value
                self._unavailable_since = time.monotonic()
            else:
                self._operational_status = ProviderOperationalStatus.DEGRADED.value

    def release_canary_probe(self, success: bool = False) -> None:
        """Failsafe method ensuring that if an unexpected exception or crash occurred
        during canary probe execution, the provider is never left stuck in HALF_OPEN.
        """
        with self._lock:
            current_status = getattr(self, "_operational_status", None)
            if current_status == ProviderOperationalStatus.HALF_OPEN.value:
                if success:
                    self.record_execution_success()
                else:
                    self.record_execution_failure(ProviderErrorType.UNKNOWN)

    def is_configured(self) -> bool:
        """Evaluates whether all required credentials, endpoints, or environment variables are present.
        Must execute locally and NEVER make outbound network calls during configuration checks.
        """
        return True

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Validates upstream response payload schema and semantic integrity.
        Subclasses should override to enforce domain schema rules.
        Returns (True, None) if valid, or (False, "reason") if invalid.
        """
        return True, None

    def validate_request(self, request: ProviderRequest) -> None:
        """Validates that the incoming request conforms to this provider's domain and required fields.
        Raises ProviderValidationError if invalid.
        """
        if not isinstance(request, ProviderRequest):
            raise ProviderValidationError(
                f"Expected ProviderRequest instance, got {type(request).__name__}",
                provider_id=self.provider_id,
                domain=self.domain,
            )

        # Domain matching validation
        if request.domain.strip().lower() != self.domain.strip().lower():
            raise ProviderValidationError(
                f"Domain mismatch: provider '{self.provider_id}' serves domain '{self.domain}', "
                f"but request specified '{request.domain}'",
                provider_id=self.provider_id,
                domain=self.domain,
            )

        request.validate()

    @abstractmethod
    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """Executes the data retrieval from the upstream source and returns a normalized LiveDataResult.
        Must not throw unhandled exceptions: catch and wrap unexpected failures cleanly.
        """
        pass

    def get_metadata(self) -> ProviderMetadata:
        """Returns descriptive metadata for registry discovery and inspection."""
        return ProviderMetadata(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            domain=self.domain,
            is_configured=self.is_configured(),
            operational_status=self.operational_status,
            is_source_verified=self.is_source_verified,
            priority=self.priority,
            is_simulated=self.is_simulated,
            consecutive_failures=self.consecutive_failures,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            last_retrieval_timestamp=self.last_retrieval_timestamp,
            last_verified_timestamp=self.last_verified_timestamp,
        )

    def build_provenance(
        self,
        request: ProviderRequest,
        freshness_status: str = FreshnessStatus.LIVE.value,
        verification_status: Optional[str] = None,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        data_timestamp: Optional[str] = None,
        location: Optional[str] = None,
        disclaimer: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Helper to construct a fully validated provenance record matching Yatra AI schemas."""
        s_type = source_type or self.default_source_type
        v_status = verification_status or self.default_verification_status

        # Enforcement: If source is not verified, cannot claim VERIFIED_EXTERNAL_API
        if not self.is_source_verified and v_status == VerificationStatus.VERIFIED_EXTERNAL_API.value:
            v_status = VerificationStatus.UNVERIFIED.value

        loc = location or request.location

        return create_provenance(
            source_name=self.provider_name,
            source_type=s_type,
            freshness_status=freshness_status,
            verification_status=v_status,
            retrieval_timestamp=get_utc_now_iso(),
            source_url=source_url,
            data_timestamp=data_timestamp,
            location=loc,
            disclaimer=disclaimer,
            domain=self.domain,
            notes=notes,
        )
