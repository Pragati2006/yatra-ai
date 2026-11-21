"""
services/live_data/adapters/live_accommodation_adapter.py
Live Hotel & Accommodation Provider Adapter for Yatra AI.

Integrates upstream live accommodation APIs (e.g. SerpApi Google Hotels Engine or MakCorps)
under DataDomain.ACCOMMODATION with server-side API keys, strict timeouts, input validation,
truth-in-data provenance tracking, and reliable fail-closed fallback to CuratedAccommodationAdapter.

Supports:
- Real hotel search in Katra and around Vaishno Devi
- Actual room rates and currency formatting (INR)
- Check-in and check-out date range filtering
- Guest count parameterization
- Genuine availability indicators (never fabricated)

No credit card required for developer tier:
- SerpApi (https://serpapi.com/) provides 250 free monthly searches for Google Hotels with NO credit card.
"""

from datetime import datetime, timedelta
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
import urllib.error

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
    get_utc_now_iso,
)
from utils.masking import sanitize_log_message

logger = logging.getLogger(__name__)


class LiveAccommodationAdapter(BaseLiveDataProvider):
    """Live hotel and accommodation provider adapter for Katra/Jammu region."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        super().__init__()
        self._api_key = (
            api_key
            if api_key is not None
            else (
                os.getenv("SERPAPI_API_KEY")
                or os.getenv("HOTEL_API_KEY")
                or os.getenv("MAKCORPS_API_KEY")
            )
        )
        self._base_url = base_url or os.getenv("HOTEL_API_URL", "https://serpapi.com/search.json")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "live_accommodation_booking_adapter"

    @property
    def provider_name(self) -> str:
        return "SerpApi Google Hotels Provider"

    @property
    def domain(self) -> str:
        return DataDomain.ACCOMMODATION.value

    @property
    def priority(self) -> int:
        return 1  # Higher priority than curated adapter (priority 100)

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @property
    def is_simulated(self) -> bool:
        return False

    @property
    def is_source_verified(self) -> bool:
        return True

    @property
    def default_source_type(self) -> str:
        return SourceType.LIVE_API.value

    @property
    def default_verification_status(self) -> str:
        return VerificationStatus.VERIFIED_EXTERNAL_API.value

    def is_configured(self) -> bool:
        """Fails closed if no active API credentials are provided in the environment."""
        return bool(self._api_key and self._api_key.strip())

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Validates structure of returned live hotel data."""
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        if "properties" not in data and "hotels" not in data and "live_status_available" not in data:
            return False, "Payload missing hotel inventory fields."
        return True, None

    def _execute_http_get(self, endpoint_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[ProviderError]]:
        """Safely executes an HTTP GET with strict timeout and error handling."""
        headers = {"User-Agent": "YatraAI/1.0", "Accept": "application/json"}
        req = urllib.request.Request(endpoint_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                return data, None
        except urllib.error.HTTPError as http_err:
            if http_err.code == 429:
                logger.warning("Hotel API rate limit reached (HTTP 429)")
                self.record_execution_failure(ProviderErrorType.RATE_LIMIT)
                err = ProviderError(
                    error_type=ProviderErrorType.RATE_LIMIT.value,
                    message="Hotel API quota reached. Fallback to curated Katra accommodations.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=429,
                )
                return None, err
            elif http_err.code in (401, 403):
                logger.warning("Hotel API authentication failed (HTTP %d)", http_err.code)
                self.record_execution_failure(ProviderErrorType.AUTH_FAILURE)
                err = ProviderError(
                    error_type=ProviderErrorType.AUTH_FAILURE.value,
                    message=f"Hotel API credentials unauthorized (HTTP {http_err.code}).",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=http_err.code,
                )
                return None, err
            else:
                logger.warning("Hotel API returned HTTP error: %d", http_err.code)
                err = ProviderError(
                    error_type=ProviderErrorType.UNKNOWN.value,
                    message=f"Hotel API HTTP error {http_err.code}",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=http_err.code,
                )
                return None, err
        except urllib.error.URLError as url_err:
            clean_reason = sanitize_log_message(str(url_err.reason))
            logger.warning("Hotel API connection failed: %s", clean_reason)
            err = ProviderError(
                error_type=ProviderErrorType.TIMEOUT.value if "timed out" in str(url_err.reason).lower() else ProviderErrorType.UNAVAILABLE.value,
                message=f"Hotel API connection failure: {clean_reason}",
                provider_id=self.provider_id,
                domain=self.domain,
            )
            return None, err
        except Exception as exc:
            clean_exc = sanitize_log_message(str(exc))
            logger.warning("Hotel API unexpected error: %s", clean_exc)
            err = ProviderError(
                error_type=ProviderErrorType.UNKNOWN.value,
                message=f"Hotel API unexpected error: {clean_exc}",
                provider_id=self.provider_id,
                domain=self.domain,
            )
            return None, err

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """
        Executes live query against the configured upstream accommodation gateway.
        If credentials are absent or upstream fails, gracefully returns UNAVAILABLE to allow fallback.
        """
        city = request.params.get("city") or request.location or "Katra"
        guests = int(request.params.get("guests") or request.params.get("pax") or 1)
        check_in = request.params.get("check_in_date") or request.params.get("check_in")
        check_out = request.params.get("check_out_date") or request.params.get("check_out")

        # Default dates to tomorrow and day-after if not specified
        today = datetime.now()
        if not check_in:
            check_in = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if not check_out:
            check_out = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        if not self.is_configured():
            prov = self.build_provenance(
                request=request,
                source_url="https://www.maavaishnodevi.org/",
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="Live accommodation gateway key is not configured in server environment. Curated catalog fallback active.",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={
                    "city": city,
                    "live_status_available": False,
                    "reason": "SERPAPI_API_KEY or HOTEL_API_KEY environment variable not configured",
                },
                provider_id=self.provider_id,
                source_provenance=prov,
                error=ProviderError(
                    error_type=ProviderErrorType.MISSING_CREDENTIALS.value,
                    message="Live accommodation credentials unset; fallback to curated catalog required.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

        # Build SerpApi Google Hotels request
        query_str = f"Hotels in {city} Vaishno Devi"
        params = {
            "engine": "google_hotels",
            "q": query_str,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": str(guests),
            "currency": "INR",
            "gl": "in",
            "hl": "en",
            "api_key": self._api_key.strip(),
        }
        endpoint = f"{self._base_url.rstrip('/')}?{urllib.parse.urlencode(params)}"

        data, err = self._execute_http_get(endpoint)
        if err or not data:
            prov = self.build_provenance(
                request=request,
                source_url="https://www.google.com/travel/hotels",
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer=f"Live hotel query failed: {err.message if err else 'No data'}",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={"city": city, "properties": [], "live_status_available": False},
                provider_id=self.provider_id,
                source_provenance=prov,
                error=err,
            )

        # Parse hotel properties from SerpApi response
        raw_properties = data.get("properties") or []
        hotels_list = []
        for p in raw_properties[:10]:
            name = p.get("name")
            if not name:
                continue
            rate_info = p.get("rate_per_night", {})
            rate_str = rate_info.get("lowest") or rate_info.get("extracted_lowest") or p.get("price")
            rating = p.get("overall_rating")
            description = p.get("description") or p.get("hotel_class") or "Hotel near Katra"
            amenities = p.get("amenities", [])

            hotels_list.append({
                "name": name,
                "city": city,
                "rate_per_night": rate_str or "Rates upon enquiry",
                "currency": "INR",
                "overall_rating": rating,
                "description": description,
                "amenities": amenities[:4],
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
                "is_live_offer": bool(rate_str),
                "link": p.get("link"),
            })

        prov = self.build_provenance(
            request=request,
            source_url="https://www.google.com/travel/hotels",
            freshness_status=FreshnessStatus.LIVE.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,
            disclaimer=f"Live hotel rates retrieved from {self.provider_name}.",
        )
        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data={
                "city": city,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
                "hotels": hotels_list,
                "properties": hotels_list,
                "total_found": len(hotels_list),
                "live_status_available": True,
                "provider": self.provider_name,
            },
            provider_id=self.provider_id,
            source_provenance=prov,
        )
