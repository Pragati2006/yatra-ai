"""
services/live_data/manager.py
Unified Live Data Manager for Yatra AI.

Coordinates provider discovery, priority selection, request validation,
thread-safe single-flight cache operations (reusing utils/cache_manager.py),
stale-if-error fallback preservation, error sanitization, and structured
truth-in-data provenance attachment (reusing utils/provenance.py).
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.live_data.base import BaseLiveDataProvider
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
    ProviderNotFoundError,
    ProviderTimeoutError,
    ProviderValidationError,
    UnsupportedDomainError,
)
from services.live_data.registry import ProviderRegistry
from utils.cache_manager import (
    CacheManager,
    CacheState,
    generate_cache_key,
    get_cache_manager,
)
from utils.provenance import (
    FreshnessStatus,
    SourceType,
    VerificationStatus,
    create_provenance,
    get_utc_now_iso,
    validate_provenance,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. DEFAULT DOMAIN FRESHNESS POLICIES (TTL seconds, Max Stale seconds)
# -----------------------------------------------------------------------------

DEFAULT_DOMAIN_CACHE_POLICIES: Dict[str, Tuple[float, float]] = {
    DataDomain.WEATHER.value: (
        float(os.getenv("CACHE_TTL_WEATHER", "1800.0")),        # 30 minutes
        float(os.getenv("CACHE_MAX_STALE_WEATHER", "21600.0")),  # 6 hours
    ),
    DataDomain.ACCOMMODATION.value: (
        float(os.getenv("CACHE_TTL_ACCOMMODATION", "900.0")),    # 15 minutes
        float(os.getenv("CACHE_MAX_STALE_ACCOMMODATION", "3600.0")),  # 1 hour
    ),
    DataDomain.OPERATIONAL_NOTICE.value: (
        float(os.getenv("CACHE_TTL_NOTICES", "900.0")),          # 15 minutes
        float(os.getenv("CACHE_MAX_STALE_NOTICES", "7200.0")),   # 2 hours
    ),
    DataDomain.CAPACITY.value: (
        float(os.getenv("CACHE_TTL_CAPACITY", "900.0")),         # 15 minutes
        float(os.getenv("CACHE_MAX_STALE_CAPACITY", "14400.0")), # 4 hours
    ),
    DataDomain.EMERGENCY.value: (
        float(os.getenv("CACHE_TTL_EMERGENCY", "604800.0")),     # 7 days
        float(os.getenv("CACHE_MAX_STALE_EMERGENCY", "2592000.0")),  # 30 days
    ),
    DataDomain.TRANSPORT.value: (
        float(os.getenv("CACHE_TTL_TRANSPORT", "86400.0")),      # 24 hours
        float(os.getenv("CACHE_MAX_STALE_TRANSPORT", "604800.0")),  # 7 days
    ),
}

DEFAULT_FALLBACK_TTL: float = 900.0       # 15 minutes
DEFAULT_FALLBACK_MAX_STALE: float = 3600.0 # 1 hour

EMERGENCY_CRITICAL_ADVISORY: str = (
    "CRITICAL EMERGENCY NOTICE: This emergency contact information is cached and has not been dynamically reverified. "
    "Facility availability, phone routing, or operating hours may have changed. For immediate police, fire, or medical "
    "emergencies, dial the national emergency number 112 directly."
)

STATUTORY_EMERGENCY_DATA: Dict[str, Any] = {
    "universal_emergency": "112",
    "police": "100",
    "police_control_room": "100",
    "ambulance_medical": "108",
    "fire": "101",
    "fire_service": "101",
    "disaster_management": "1077",
    "women_helpline": "1091",
    "katra_police_station": "+91-1991-232010",
    "shrine_board_call_centre_toll_free": "1800-180-7212",
    "shrine_board_call_centre_landline": "+91-1991-234804",
    "shrine_board_protocol_office_hours": "+91-1991-232029 (10:00 AM - 5:00 PM)",
    "shrine_board_central_office": "1800-180-7212",  # Backward-compatible 24x7 call centre alias
    "smvdsb_call_centre_toll_free": "1800-180-7212",
    "smvdsb_administrative_protocol": "+91-1991-232029 (10:00 AM - 5:00 PM)",
    "categories": {
        "national_emergency": {
            "service": "Emergency Response Support System (ERSS)",
            "number": "112",
            "jurisdiction": "Pan-India / UT of Jammu & Kashmir",
            "source_url": "https://112.gov.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "ambulance_medical": {
            "service": "National Ambulance Service (NAS)",
            "number": "108",
            "jurisdiction": "UT of Jammu & Kashmir",
            "source_url": "https://nhmjk.nic.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "police": {
            "service": "Police Control Room / Katra Police Station",
            "number": "100 / +91-1991-232010",
            "jurisdiction": "Katra / Reasi District, J&K",
            "source_url": "https://reasi.nic.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "fire": {
            "service": "Fire & Emergency Services",
            "number": "101",
            "jurisdiction": "Pan-India / UT of J&K",
            "source_url": "https://fireandemergency.jk.gov.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "disaster_management": {
            "service": "District Disaster Management Authority (DDMA) EOC",
            "number": "1077",
            "jurisdiction": "District Reasi, J&K",
            "source_url": "https://reasi.nic.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "women_helpline": {
            "service": "Women in Distress Helpline",
            "number": "1091",
            "jurisdiction": "Pan-India / J&K Police",
            "source_url": "https://jkpolice.gov.in",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "shrine_board_call_centre": {
            "service": "Shri Mata Vaishno Devi Shrine Board (SMVDSB) 24x7 Call Centre",
            "numbers": ["1800-180-7212 (Toll Free)", "+91-1991-234804"],
            "jurisdiction": "Katra / Bhawan / SMVDSB Pilgrimage",
            "source_url": "https://www.maavaishnodevi.org",
            "verification_date": "2026-11-07",
            "availability": "24x7",
        },
        "administrative_office": {
            "service": "SMVDSB Protocol Department (Administrative Office Only)",
            "number": "+91-1991-232029",
            "jurisdiction": "Katra Spiritual Growth Centre",
            "source_url": "https://www.maavaishnodevi.org",
            "verification_date": "2026-11-07",
            "availability": "Office Hours Only (10:00 AM - 5:00 PM)",
            "note": "Administrative protocol desk; not a 24x7 emergency helpline",
        },
    },
}

STATUTORY_EMERGENCY_DISCLAIMER: str = (
    "Live emergency services directory is currently unavailable. Displaying statutory national emergency helplines. "
    "For immediate life-safety emergencies, dial 112 directly."
)


# -----------------------------------------------------------------------------
# 2. UNIFIED LIVE DATA MANAGER IMPLEMENTATION
# -----------------------------------------------------------------------------

class UnifiedLiveDataManager:
    """Orchestrates live data retrieval across registered providers with cache coordination."""

    @classmethod
    def get_instance(cls) -> "UnifiedLiveDataManager":
        """Convenience classmethod returning the process-wide UnifiedLiveDataManager singleton."""
        return get_live_data_manager()

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        self._registry = registry or ProviderRegistry()
        self._cache_manager = cache_manager or get_cache_manager()
        self._policies_lock = threading.RLock()
        self._cache_policies: Dict[str, Tuple[float, float]] = dict(DEFAULT_DOMAIN_CACHE_POLICIES)

    @property
    def registry(self) -> ProviderRegistry:
        """Returns the underlying provider registry."""
        return self._registry

    @property
    def cache_manager(self) -> CacheManager:
        """Returns the underlying cache manager."""
        return self._cache_manager

    # -------------------------------------------------------------------------
    # Provider Registration & Discovery
    # -------------------------------------------------------------------------

    def register_provider(self, provider: BaseLiveDataProvider) -> None:
        """Registers a data provider in the manager's registry."""
        self._registry.register(provider)

    def get_provider(self, domain: str, provider_id: str) -> Optional[BaseLiveDataProvider]:
        """Looks up a specific registered provider."""
        return self._registry.get_provider(domain, provider_id)

    def discover_providers(
        self,
        domain: str,
        configured_only: bool = True,
    ) -> List[BaseLiveDataProvider]:
        """Discovers providers for a domain, ordered by priority ascending."""
        return self._registry.get_providers_for_domain(domain, configured_only=configured_only)

    # -------------------------------------------------------------------------
    # Cache Policy Management
    # -------------------------------------------------------------------------

    def get_cache_policy(self, domain: str) -> Tuple[float, float]:
        """Retrieves configured (ttl_seconds, max_stale_seconds) for a domain."""
        dom = str(domain).strip().lower()
        with self._policies_lock:
            return self._cache_policies.get(dom, (DEFAULT_FALLBACK_TTL, DEFAULT_FALLBACK_MAX_STALE))

    def set_cache_policy(self, domain: str, ttl: float, max_stale: float) -> None:
        """Overrides cache policy for a given domain."""
        dom = str(domain).strip().lower()
        with self._policies_lock:
            self._cache_policies[dom] = (float(ttl), float(max_stale))

    # -------------------------------------------------------------------------
    # Provider Execution & Cache Coordination
    # -------------------------------------------------------------------------

    def fetch_data(
        self,
        request: ProviderRequest,
        provider_id: Optional[str] = None,
        bypass_cache: bool = False,
    ) -> LiveDataResult:
        """Alias for execute_request."""
        return self.execute_request(request, provider_id=provider_id, bypass_cache=bypass_cache)

    def execute_request(
        self,
        request: ProviderRequest,
        provider_id: Optional[str] = None,
        bypass_cache: bool = False,
    ) -> LiveDataResult:
        """Executes a live data retrieval request through eligible providers, coordinating
        thread-safe caching, single-flight request deduplication, and graceful stale fallback.
        """
        # Step 1: Input Validation
        if not isinstance(request, ProviderRequest):
            raise ProviderValidationError(f"Expected ProviderRequest, got {type(request).__name__}")
        request.validate()

        dom = request.domain.strip().lower()

        # Step 2: Provider Selection
        provider: Optional[BaseLiveDataProvider] = None
        if provider_id:
            provider = self._registry.get_provider(dom, provider_id)
            if not provider:
                return self._build_error_result(
                    request=request,
                    provider_id=provider_id,
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message=f"Requested provider '{provider_id}' is not registered for domain '{dom}'.",
                )
            if not provider.is_configured():
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.MISSING_CREDENTIALS,
                    message=f"Provider '{provider.provider_id}' is not configured (missing credentials or config).",
                )
        else:
            candidates = self._registry.get_providers_for_domain(dom, configured_only=True)
            if not candidates:
                logger.warning("No configured provider available for domain '%s'.", dom)
                return self._build_error_result(
                    request=request,
                    provider_id="none",
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message=f"No active provider is configured for data domain '{dom}'.",
                )
            provider = candidates[0]

        # Step 3: Check Provider Availability & Half-Open Canary Reservation
        canary_reserved = False
        with provider._lock:
            current_st = provider.operational_status
            if current_st == ProviderOperationalStatus.UNAVAILABLE.value:
                if provider.reserve_canary_probe():
                    canary_reserved = True
                    logger.info("Reserved half-open canary probe for provider '%s'", provider.provider_id)
                else:
                    return self._build_error_result(
                        request=request,
                        provider_id=provider.provider_id,
                        error_type=ProviderErrorType.UNAVAILABLE,
                        message=f"Provider '{provider.provider_id}' is currently unavailable (circuit-breaker tripped or cooldown active).",
                    )
            elif current_st == ProviderOperationalStatus.HALF_OPEN.value:
                # Canary probe already active in flight by another concurrent worker
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message=f"Provider '{provider.provider_id}' is currently testing upstream recovery (canary probe in progress).",
                )
            elif not provider.is_available():
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.UNAVAILABLE,
                    message=f"Provider '{provider.provider_id}' is currently unavailable (unconfigured or offline).",
                )

        # Step 4: Validate request against selected provider
        try:
            provider.validate_request(request)
        except Exception as exc:
            if canary_reserved:
                provider.release_canary_probe(success=False)
            logger.warning("Request validation failed for provider '%s': %s", provider.provider_id, exc)
            return self._build_error_result(
                request=request,
                provider_id=provider.provider_id,
                error_type=ProviderErrorType.VALIDATION_ERROR,
                message=str(exc),
            )

        # Step 5: Handle Private Requests (Complete Public Cache Bypass)
        if request.is_private():
            logger.info("Executing private request for domain '%s' (bypassing shared public cache)", dom)
            timeout = provider.timeout_seconds
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(provider.fetch_live_data, request)
                    res = future.result(timeout=timeout)

                # Payload schema validation
                val_ok, val_err = provider.validate_payload(res.data)
                if not val_ok:
                    res.verification_status = VerificationStatus.UNVERIFIED.value
                    if res.source_provenance:
                        res.source_provenance["verification_status"] = VerificationStatus.UNVERIFIED.value
                        res.source_provenance["disclaimer"] = f"Payload validation issue: {val_err}"

                # Update provider lifecycle
                provider.record_execution_success()
                res.is_cached = False
                res.cached_state = None
                return res
            except FutureTimeoutError:
                provider.record_execution_failure(ProviderErrorType.TIMEOUT)
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.TIMEOUT,
                    message=f"Provider '{provider.provider_id}' timed out after {timeout}s.",
                )
            except Exception as exc:
                provider.record_execution_failure(ProviderErrorType.UNKNOWN)
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.UNKNOWN,
                    message=f"Provider execution failed: {exc}",
                )
            finally:
                if canary_reserved:
                    provider.release_canary_probe(success=(provider.operational_status == ProviderOperationalStatus.OPERATIONAL.value))

        # Step 6: Public Cache Handling (Non-private requests)
        ttl, max_stale = self.get_cache_policy(dom)
        cache_params = request.to_cache_params()
        cache_key = generate_cache_key(category=f"live_{dom}", params=cache_params)

        # Handle bypass_cache preference
        force_refresh = bypass_cache or (request.freshness_preference == "force_refresh")

        if not force_refresh and not canary_reserved:
            # Check fast-path fresh cache hit (canary probes must not use cached data)
            cached_payload, cache_state, entry = self._cache_manager.get_with_status(cache_key)
            if cache_state == CacheState.FRESH.value and cached_payload is not None:
                logger.debug("Cache hit (fresh) for domain '%s' key '%s'", dom, cache_key)
                return self._wrap_cached_result(
                    cached_data=cached_payload,
                    request=request,
                    provider=provider,
                    freshness=FreshnessStatus.CACHED.value,
                    cached_state="fresh",
                )

        # Step 7: Execute provider fetch via thread-safe single-flight coordination
        last_fetch_result: Optional[LiveDataResult] = None
        last_fetch_error: Optional[Exception] = None

        def _fetch_wrapper() -> Optional[Dict[str, Any]]:
            nonlocal last_fetch_result, last_fetch_error
            logger.info("Executing upstream fetch for provider '%s' (domain '%s')", provider.provider_id, dom)
            timeout = provider.timeout_seconds
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(provider.fetch_live_data, request)
                try:
                    res = future.result(timeout=timeout)
                    last_fetch_result = res
                    # Payload validation check
                    val_ok, val_err = provider.validate_payload(res.data)
                    if not val_ok:
                        res.verification_status = VerificationStatus.UNVERIFIED.value
                        if res.source_provenance:
                            res.source_provenance["verification_status"] = VerificationStatus.UNVERIFIED.value
                            res.source_provenance["disclaimer"] = f"Payload validation issue: {val_err}"
                    # Return dictionary representation for cache
                    return res.to_dict()
                except FutureTimeoutError:
                    logger.warning("Provider '%s' timed out after %0.1fs", provider.provider_id, timeout)
                    last_fetch_error = ProviderTimeoutError(
                        f"Provider '{provider.provider_id}' timed out after {timeout}s",
                        provider_id=provider.provider_id,
                        domain=dom,
                    )
                    raise last_fetch_error
                except Exception as exc:
                    logger.warning("Provider '%s' execution raised: %s", provider.provider_id, exc)
                    last_fetch_error = exc
                    raise exc

        try:
            # If canary_reserved is True, bypass cached data in get_or_fetch
            if canary_reserved:
                # Direct execute for canary probe
                try:
                    raw_dict = _fetch_wrapper()
                except Exception as fetch_exc:
                    err_type = ProviderErrorType.TIMEOUT if isinstance(fetch_exc, ProviderTimeoutError) else ProviderErrorType.UNKNOWN
                    provider.record_execution_failure(err_type)
                    if dom == DataDomain.EMERGENCY.value:
                        return self._build_emergency_fallback_result(
                            request=request,
                            provider_id=provider.provider_id,
                        )
                    return self._build_error_result(
                        request=request,
                        provider_id=provider.provider_id,
                        error_type=err_type,
                        message=f"Canary recovery probe failed: {fetch_exc}",
                    )

                if last_fetch_result is not None and last_fetch_result.is_success:
                    provider.record_execution_success()
                    # Also populate cache with fresh canary response
                    self._cache_manager.set(
                        key=cache_key,
                        payload=raw_dict,
                        ttl=ttl,
                        max_stale=max_stale,
                        category=f"live_{dom}",
                        request_params=cache_params,
                        source_identifier=provider.provider_id,
                    )
                    return last_fetch_result
                elif last_fetch_result is not None and last_fetch_result.status == "NO_RESULTS":
                    provider.record_execution_success()
                    return last_fetch_result
                else:
                    provider.record_execution_failure()
                    return self._build_error_result(
                        request=request,
                        provider_id=provider.provider_id,
                        error_type=ProviderErrorType.UNKNOWN,
                        message="Canary recovery probe failed.",
                    )

            # Normal path: execute through cache manager
            raw_payload, prov_status = self._cache_manager.get_or_fetch(
                key=cache_key,
                fetcher_callable=_fetch_wrapper,
                category=f"live_{dom}",
                ttl=ttl,
                max_stale=max_stale,
                request_params=cache_params,
                source_identifier=provider.provider_id,
            )

            # Case A: Live success or structured empty result returned
            if prov_status == "live" and raw_payload is not None:
                provider.record_execution_success()
                return self._reconstitute_result(
                    payload=raw_payload,
                    request=request,
                    provider=provider,
                    freshness=raw_payload.get("freshness_status", FreshnessStatus.LIVE.value),
                    is_cached=False,
                )

            # Case B: Stale fallback returned by cache_manager
            if prov_status == "stale" and raw_payload is not None:
                provider.record_execution_failure()
                adv = (
                    EMERGENCY_CRITICAL_ADVISORY
                    if dom == DataDomain.EMERGENCY.value
                    else "Data retrieved from cache. Upstream provider unavailable; refresh pending."
                )
                return self._reconstitute_result(
                    payload=raw_payload,
                    request=request,
                    provider=provider,
                    freshness=FreshnessStatus.STALE.value,
                    is_cached=True,
                    cached_state="stale",
                    advisory=adv,
                )

            # Case C: Fresh cache hit from another in-flight worker
            if prov_status == "cached" and raw_payload is not None:
                return self._reconstitute_result(
                    payload=raw_payload,
                    request=request,
                    provider=provider,
                    freshness=FreshnessStatus.CACHED.value,
                    is_cached=True,
                    cached_state="fresh",
                )

            # Case D: Provider failed and no usable cache exists
            if last_fetch_error is not None:
                provider.record_execution_failure(
                    ProviderErrorType.TIMEOUT if isinstance(last_fetch_error, ProviderTimeoutError) else ProviderErrorType.UNKNOWN
                )
                # Life-safety policy: emergency domain fallback to statutory numbers
                if dom == DataDomain.EMERGENCY.value:
                    return self._build_emergency_fallback_result(
                        request=request,
                        provider_id=provider.provider_id,
                    )
                if isinstance(last_fetch_error, ProviderTimeoutError):
                    return self._build_error_result(
                        request=request,
                        provider_id=provider.provider_id,
                        error_type=ProviderErrorType.TIMEOUT,
                        message=f"Provider '{provider.provider_id}' timed out after {provider.timeout_seconds}s.",
                    )
                return self._build_error_result(
                    request=request,
                    provider_id=provider.provider_id,
                    error_type=ProviderErrorType.UNKNOWN,
                    message=f"Provider execution failed: {last_fetch_error}",
                )

            # Case E: Provider returned None or empty
            if last_fetch_result is not None and last_fetch_result.status == "NO_RESULTS":
                provider.record_execution_success()
                return last_fetch_result

            provider.record_execution_failure(ProviderErrorType.NO_RESULTS)
            if dom == DataDomain.EMERGENCY.value:
                return self._build_emergency_fallback_result(
                    request=request,
                    provider_id=provider.provider_id,
                )
            return self._build_error_result(
                request=request,
                provider_id=provider.provider_id,
                error_type=ProviderErrorType.NO_RESULTS,
                message=f"Provider '{provider.provider_id}' returned no usable data.",
            )
        finally:
            if canary_reserved:
                provider.release_canary_probe(success=(provider.operational_status == ProviderOperationalStatus.OPERATIONAL.value))

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _wrap_cached_result(
        self,
        cached_data: Any,
        request: ProviderRequest,
        provider: BaseLiveDataProvider,
        freshness: str,
        cached_state: str,
    ) -> LiveDataResult:
        """Wraps cached data into a LiveDataResult with provenance."""
        if isinstance(cached_data, dict) and "data" in cached_data and "status" in cached_data:
            return self._reconstitute_result(
                payload=cached_data,
                request=request,
                provider=provider,
                freshness=freshness,
                is_cached=True,
                cached_state=cached_state,
            )

        adv = None
        if request.domain.strip().lower() == DataDomain.EMERGENCY.value and freshness == FreshnessStatus.STALE.value:
            adv = EMERGENCY_CRITICAL_ADVISORY

        prov = provider.build_provenance(
            request=request,
            freshness_status=freshness,
            source_type=SourceType.CACHED_API.value,
        )
        return LiveDataResult(
            status="SUCCESS",
            domain=request.domain,
            data=cached_data,
            provider_id=provider.provider_id,
            source_provenance=prov,
            freshness_status=freshness,
            verification_status=provider.default_verification_status,
            availability_verified=False,
            claims_breakdown=None,
            is_cached=True,
            cached_state=cached_state,
            advisory=adv,
        )

    def _reconstitute_result(
        self,
        payload: Dict[str, Any],
        request: ProviderRequest,
        provider: BaseLiveDataProvider,
        freshness: str,
        is_cached: bool,
        cached_state: Optional[str] = None,
        advisory: Optional[str] = None,
    ) -> LiveDataResult:
        """Reconstructs LiveDataResult from cached dictionary, updating temporal freshness
        while faithfully preserving verification, availability flags, and claims breakdowns.
        """
        data = payload.get("data")
        status = payload.get("status", "SUCCESS")
        data_ts = payload.get("data_timestamp")

        # Check if observation data_timestamp is older than max_stale
        if data_ts:
            try:
                ts_str = data_ts.replace("Z", "+00:00")
                parsed_dt = datetime.fromisoformat(ts_str)
                ttl_val, max_stale_val = self.get_cache_policy(request.domain)
                age = (datetime.now(timezone.utc) - parsed_dt).total_seconds()
                if age > max_stale_val:
                    freshness = FreshnessStatus.STALE.value
            except Exception:
                pass

        if request.domain.strip().lower() == DataDomain.EMERGENCY.value and freshness == FreshnessStatus.STALE.value:
            advisory = EMERGENCY_CRITICAL_ADVISORY

        v_status = payload.get("verification_status") or provider.default_verification_status
        if payload.get("verification_status") == VerificationStatus.UNVERIFIED.value:
            v_status = VerificationStatus.UNVERIFIED.value

        # Extract and preserve claims breakdown and availability verification
        claims_breakdown = payload.get("claims_breakdown")
        if claims_breakdown is None and isinstance(payload.get("source_provenance"), dict):
            claims_breakdown = payload.get("source_provenance", {}).get("claims_breakdown")

        # Safe default: never infer verified availability for legacy or unstated cache entries
        availability_verified = bool(payload.get("availability_verified", False))

        prov = provider.build_provenance(
            request=request,
            freshness_status=freshness,
            verification_status=v_status,
            source_type=SourceType.CACHED_API.value if is_cached else provider.default_source_type,
            data_timestamp=data_ts,
            disclaimer=payload.get("source_provenance", {}).get("disclaimer"),
        )
        if claims_breakdown:
            prov["claims_breakdown"] = claims_breakdown

        return LiveDataResult(
            status=status,
            domain=request.domain,
            data=data,
            provider_id=provider.provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            data_timestamp=data_ts,
            freshness_status=freshness,
            verification_status=v_status,
            availability_verified=availability_verified,
            claims_breakdown=claims_breakdown,
            is_cached=is_cached,
            cached_state=cached_state,
            advisory=advisory or payload.get("advisory"),
        )

    def _build_emergency_fallback_result(
        self,
        request: ProviderRequest,
        provider_id: str,
    ) -> LiveDataResult:
        """Returns safe, unverified statutory emergency fallback when provider fails."""
        prov = create_provenance(
            source_name="National Emergency Helplines (Statutory Fallback)",
            source_type=SourceType.CURATED_DATA.value,
            freshness_status=FreshnessStatus.UNAVAILABLE.value,
            verification_status=VerificationStatus.UNVERIFIED.value,
            domain=request.domain,
            disclaimer=STATUTORY_EMERGENCY_DISCLAIMER,
        )
        return LiveDataResult(
            status="UNAVAILABLE",
            domain=request.domain,
            data=STATUTORY_EMERGENCY_DATA,
            provider_id=provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=FreshnessStatus.UNAVAILABLE.value,
            verification_status=VerificationStatus.UNVERIFIED.value,
            error=ProviderError(
                error_type=ProviderErrorType.UNAVAILABLE,
                message="Live emergency provider unavailable. Displaying statutory numbers only.",
                provider_id=provider_id,
                domain=request.domain,
            ),
            advisory=STATUTORY_EMERGENCY_DISCLAIMER,
        )

    def _build_error_result(
        self,
        request: ProviderRequest,
        provider_id: str,
        error_type: ProviderErrorType,
        message: str,
    ) -> LiveDataResult:
        """Constructs a clean failure result conforming to truth-in-data standards."""
        prov = create_provenance(
            source_name=provider_id if provider_id != "none" else "Yatra AI Live Data Manager",
            source_type=SourceType.UNKNOWN_SOURCE.value,
            freshness_status=FreshnessStatus.UNAVAILABLE.value,
            verification_status=VerificationStatus.UNVERIFIED.value,
            domain=request.domain,
            disclaimer=message,
        )
        err = ProviderError(
            error_type=error_type,
            message=message,
            provider_id=provider_id,
            domain=request.domain,
        )
        return LiveDataResult(
            status="UNAVAILABLE" if error_type in (ProviderErrorType.UNAVAILABLE, ProviderErrorType.MISSING_CREDENTIALS) else "ERROR",
            domain=request.domain,
            data=None,
            provider_id=provider_id,
            source_provenance=prov,
            retrieval_timestamp=get_utc_now_iso(),
            freshness_status=FreshnessStatus.UNAVAILABLE.value,
            verification_status=VerificationStatus.UNVERIFIED.value,
            error=err,
            advisory=message,
        )


# -----------------------------------------------------------------------------
# 3. GLOBAL SINGLETON ACCESSOR
# -----------------------------------------------------------------------------

_GLOBAL_MANAGER: Optional[UnifiedLiveDataManager] = None
_GLOBAL_MANAGER_LOCK = threading.Lock()


def get_live_data_manager() -> UnifiedLiveDataManager:
    """Returns the process-wide UnifiedLiveDataManager singleton with default production adapters registered."""
    global _GLOBAL_MANAGER
    with _GLOBAL_MANAGER_LOCK:
        if _GLOBAL_MANAGER is None:
            mgr = UnifiedLiveDataManager()
            try:
                from services.live_data.adapters.curated_accommodation_adapter import CuratedAccommodationAdapter
                from services.live_data.adapters.curated_bus_adapter import CuratedBusAdapter
                from services.live_data.adapters.curated_contact_adapter import VerifiedContactAdapter
                from services.live_data.adapters.curated_operational_notices_adapter import CuratedOperationalNoticesAdapter
                from services.live_data.adapters.curated_flight_adapter import CuratedFlightAdapter
                from services.live_data.adapters.curated_railway_adapter import CuratedRailwayAdapter
                from services.live_data.adapters.weather_adapter import OpenMeteoWeatherAdapter

                if CuratedAccommodationAdapter().is_configured():
                    mgr.register_provider(CuratedAccommodationAdapter())
                if CuratedOperationalNoticesAdapter().is_configured():
                    mgr.register_provider(CuratedOperationalNoticesAdapter())
                if VerifiedContactAdapter().is_configured():
                    mgr.register_provider(VerifiedContactAdapter())
                if CuratedRailwayAdapter().is_configured():
                    mgr.register_provider(CuratedRailwayAdapter())
                if CuratedBusAdapter().is_configured():
                    mgr.register_provider(CuratedBusAdapter())
                if CuratedFlightAdapter().is_configured():
                    mgr.register_provider(CuratedFlightAdapter())
                mgr.register_provider(OpenMeteoWeatherAdapter())
            except Exception as exc:
                logger.debug("Failed registering default live data adapters: %s", exc)
            _GLOBAL_MANAGER = mgr
        return _GLOBAL_MANAGER


def reset_live_data_manager() -> None:
    """Resets the process-wide UnifiedLiveDataManager singleton (for test isolation)."""
    global _GLOBAL_MANAGER
    with _GLOBAL_MANAGER_LOCK:
        _GLOBAL_MANAGER = None
