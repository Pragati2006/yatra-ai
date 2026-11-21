"""
services/live_data/adapters/live_flight_adapter.py
Live Flight Provider Adapter for Yatra AI.

Integrates upstream live flight search APIs (e.g. SerpApi Google Flights Engine or Aviationstack)
under DataDomain.TRANSPORT with server-side API keys, strict timeouts, input validation,
and truth-in-data provenance tracking.

Fails closed when API keys are absent, allowing seamless fallback to CuratedFlightAdapter.
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


class LiveFlightAdapter(BaseLiveDataProvider):
    """Live flight schedules provider adapter for Jammu (IXJ) and Srinagar (SXR) corridors."""

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
                or os.getenv("FLIGHT_API_KEY")
                or os.getenv("AVIATIONSTACK_API_KEY")
            )
        )
        self._base_url = base_url or os.getenv("FLIGHT_API_URL", "https://serpapi.com/search.json")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "live_flight_telemetry_adapter"

    @property
    def provider_name(self) -> str:
        return "SerpApi Google Flights Gateway"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 2  # After live railway (1), before curated flight (10)

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
        return bool(self._api_key and self._api_key.strip())

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        return True, None

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        origin = request.params.get("origin") or request.location
        if not origin:
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                provider_id=self.provider_id,
                payload={"error": "Origin city is required to search flight schedules."},
                provenance=self.build_provenance(
                    request=request,
                    source_url="https://www.google.com/travel/flights",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer="Origin city is required to search flight schedules.",
                ),
            )
        destination = request.params.get("destination") or "Jammu"

        if not self.is_configured():
            prov = self.build_provenance(
                request=request,
                source_url="https://www.google.com/travel/flights",
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="Live flight gateway key is not configured in server environment. Curated flight schedule fallback active.",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={
                    "origin": origin,
                    "destination": destination,
                    "live_status_available": False,
                    "reason": "SERPAPI_API_KEY or FLIGHT_API_KEY environment variable not configured",
                },
                provider_id=self.provider_id,
                source_provenance=prov,
                error=ProviderError(
                    error_type=ProviderErrorType.MISSING_CREDENTIALS.value,
                    message="Live flight credentials unset; fallback to curated flights required.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

        # Map common city names to IATA codes
        iata_map = {
            "delhi": "DEL",
            "new delhi": "DEL",
            "mumbai": "BOM",
            "jammu": "IXJ",
            "srinagar": "SXR",
            "bangalore": "BLR",
            "bengaluru": "BLR",
            "hyderabad": "HYD",
            "kolkata": "CCU",
            "chandigarh": "IXC",
            "amritsar": "ATQ",
            "chennai": "MAA",
            "ahmedabad": "AMD",
            "pune": "PNQ",
            "lucknow": "LKO",
            "varanasi": "VNS",
        }
        dep_id = iata_map.get(origin.lower().strip(), origin.strip().upper())
        arr_id = iata_map.get(destination.lower().strip(), destination.strip().upper())

        today = datetime.now()
        travel_date = request.params.get("travel_date") or request.params.get("date") or (today + timedelta(days=7)).strftime("%Y-%m-%d")
        return_date = request.params.get("return_date")

        params = {
            "engine": "google_flights",
            "departure_id": dep_id,
            "arrival_id": arr_id,
            "outbound_date": travel_date,
            "currency": "INR",
            "hl": "en",
            "api_key": self._api_key.strip(),
        }
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"
        else:
            params["type"] = "2"  # One way

        endpoint = f"{self._base_url.rstrip('/')}?{urllib.parse.urlencode(params)}"

        headers = {"User-Agent": "YatraAI/1.0", "Accept": "application/json"}
        req = urllib.request.Request(endpoint, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            clean_exc = sanitize_log_message(str(exc))
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={"origin": origin, "destination": destination, "flights": []},
                provider_id=self.provider_id,
                error=ProviderError(
                    error_type=ProviderErrorType.UNKNOWN.value,
                    message=f"Flight API error: {clean_exc}",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

        best_raw = data.get("best_flights") or []
        other_raw = data.get("other_flights") or []
        combined_raw = best_raw + other_raw

        normalized_flights = []
        for item in combined_raw:
            if not isinstance(item, dict):
                continue
            legs = item.get("flights") or []
            first_leg = legs[0] if legs and isinstance(legs[0], dict) else {}
            last_leg = legs[-1] if legs and isinstance(legs[-1], dict) else first_leg
            dep_airport = first_leg.get("departure_airport") or {}
            arr_airport = last_leg.get("arrival_airport") or {}

            airline = first_leg.get("airline") or item.get("airline") or "Commercial Airline"
            fn = first_leg.get("flight_number") or ""
            price = item.get("price")
            duration_mins = item.get("total_duration") or 0

            normalized_flights.append({
                "airline": airline,
                "flight_number": fn,
                "flight_no": f"{airline} {fn}".strip(),
                "price": price,
                "price_inr": f"₹{price:,}" if isinstance(price, (int, float)) else str(price),
                "departure_time": dep_airport.get("time") or "",
                "departure_airport": dep_airport.get("name") or dep_id,
                "arrival_time": arr_airport.get("time") or "",
                "arrival_airport": arr_airport.get("name") or arr_id,
                "duration_minutes": duration_mins,
                "duration_desc": f"{duration_mins // 60}h {duration_mins % 60}m" if duration_mins else "Direct",
                "stops": max(0, len(legs) - 1),
                "is_live_status": True,
            })

        prov = self.build_provenance(
            request=request,
            source_url="https://www.google.com/travel/flights",
            freshness_status=FreshnessStatus.LIVE.value,
            verification_status=VerificationStatus.VERIFIED_EXTERNAL_API.value,
            disclaimer=f"Live flight fares retrieved from {self.provider_name}.",
        )
        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data={
                "origin": origin,
                "destination": destination,
                "origin_iata": dep_id,
                "destination_iata": arr_id,
                "travel_date": travel_date,
                "flights": normalized_flights,
                "schedules": normalized_flights,
                "live_status_available": True,
                "provider": self.provider_name,
            },
            provider_id=self.provider_id,
            source_provenance=prov,
        )
