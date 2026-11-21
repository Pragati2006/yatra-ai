"""
services/live_data/adapters/live_railway_adapter.py
Live Railway Telemetry Provider Adapter for Yatra AI.

Integrates upstream live railway telemetry APIs (e.g., RailCore, irctc.dev, or RapidAPI)
under DataDomain.TRANSPORT with server-side API keys, strict timeouts, input validation,
truth-in-data provenance tracking, and reliable fail-closed fallback to CuratedRailwayAdapter.

Supports:
- Live Train Running Status (current station, delay minutes, last update)
- Train Route & Timetable Schedules (intermediate halts, arrival/departure times, running days)
- Train Search Between Stations (e.g. New Delhi to Shri Mata Vaishno Devi Katra)

No credit card required for developer tier:
- RailCore (https://railcore.tech/) offers 2,000 free requests/month with no payment details.
- irctc.dev (https://irctc.dev/) offers 10,000 free trial credits.
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


class LiveRailwayAdapter(BaseLiveDataProvider):
    """Live telemetry provider adapter for Indian Railways trains connecting to Katra/Jammu."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 8.0,
    ):
        super().__init__()
        self._api_key = (
            api_key
            if api_key is not None
            else (
                os.getenv("RAILCORE_API_KEY")
                or os.getenv("RAILWAY_API_KEY")
                or os.getenv("IRCTC_DEV_API_KEY")
                or os.getenv("RAPIDAPI_KEY")
            )
        )
        # Determine provider flavor and base URL
        if os.getenv("IRCTC_DEV_API_KEY") or "irctc.dev" in (base_url or ""):
            self._provider_type = "irctc_dev"
            self._base_url = base_url or os.getenv("RAILWAY_API_URL", "https://api.irctc.dev/api/v1")
        elif os.getenv("RAPIDAPI_KEY") and not (os.getenv("RAILCORE_API_KEY") or os.getenv("RAILWAY_API_KEY")):
            self._provider_type = "rapidapi"
            self._base_url = base_url or os.getenv("RAILWAY_API_URL", "https://irctc-real-time-api.p.rapidapi.com/api/v1")
        else:
            self._provider_type = "railcore"
            self._base_url = base_url or os.getenv("RAILWAY_API_URL", "https://ir.railcore.tech/v1")

        self._timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "live_railway_telemetry_adapter"

    @property
    def provider_name(self) -> str:
        if self._provider_type == "irctc_dev":
            return "irctc.dev Live Railway Gateway"
        elif self._provider_type == "rapidapi":
            return "RapidAPI Indian Railways Gateway"
        return "RailCore Indian Railways API"

    @property
    def domain(self) -> str:
        return DataDomain.TRANSPORT.value

    @property
    def priority(self) -> int:
        return 1  # Higher priority than curated adapter (priority 10)

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
        return VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value

    def is_configured(self) -> bool:
        """Fails closed if no active API credentials are provided in the environment."""
        return bool(self._api_key and self._api_key.strip())

    def validate_payload(self, data: Any) -> Tuple[bool, Optional[str]]:
        """Validates structure of returned live railway data."""
        if not isinstance(data, dict):
            return False, "Payload must be a dictionary."
        if not data.get("live_status_available") and not data.get("schedules") and not data.get("trains"):
            return False, "Payload missing railway data fields."
        return True, None

    def _build_request_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "YatraAI/1.0", "Accept": "application/json"}
        if self._provider_type == "railcore":
            headers["X-RailCore-Key"] = self._api_key.strip()
        elif self._provider_type == "irctc_dev":
            headers["x-api-key"] = self._api_key.strip()
        elif self._provider_type == "rapidapi":
            headers["X-RapidAPI-Key"] = self._api_key.strip()
            headers["X-RapidAPI-Host"] = urllib.parse.urlparse(self._base_url).netloc
        return headers

    def _execute_http_get(self, endpoint_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[ProviderError]]:
        """Safely executes an HTTP GET with strict timeout and error handling."""
        headers = self._build_request_headers()
        req = urllib.request.Request(endpoint_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                status_code = resp.getcode()
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                return data, None
        except urllib.error.HTTPError as http_err:
            if http_err.code == 429:
                logger.warning("Railway API rate limit reached (HTTP 429)")
                self.record_execution_failure(ProviderErrorType.RATE_LIMIT)
                err = ProviderError(
                    error_type=ProviderErrorType.RATE_LIMIT.value,
                    message="Railway API rate limit reached. Fallback to curated timetable.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=429,
                )
                return None, err
            elif http_err.code in (401, 403):
                logger.warning("Railway API authentication failed (HTTP %d)", http_err.code)
                self.record_execution_failure(ProviderErrorType.AUTH_FAILURE)
                err = ProviderError(
                    error_type=ProviderErrorType.AUTH_FAILURE.value,
                    message=f"Railway API credentials unauthorized (HTTP {http_err.code}).",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=http_err.code,
                )
                return None, err
            else:
                logger.warning("Railway API returned HTTP error: %d", http_err.code)
                err = ProviderError(
                    error_type=ProviderErrorType.UNKNOWN.value,
                    message=f"Railway API HTTP error {http_err.code}",
                    provider_id=self.provider_id,
                    domain=self.domain,
                    status_code=http_err.code,
                )
                return None, err
        except urllib.error.URLError as url_err:
            clean_reason = sanitize_log_message(str(url_err.reason))
            logger.warning("Railway API connection failed: %s", clean_reason)
            err = ProviderError(
                error_type=ProviderErrorType.TIMEOUT.value if "timed out" in str(url_err.reason).lower() else ProviderErrorType.UNAVAILABLE.value,
                message=f"Railway API connection failure: {clean_reason}",
                provider_id=self.provider_id,
                domain=self.domain,
            )
            return None, err
        except Exception as exc:
            clean_exc = sanitize_log_message(str(exc))
            logger.warning("Railway API unexpected error: %s", clean_exc)
            err = ProviderError(
                error_type=ProviderErrorType.UNKNOWN.value,
                message=f"Railway API unexpected error: {clean_exc}",
                provider_id=self.provider_id,
                domain=self.domain,
            )
            return None, err

    def fetch_live_data(self, request: ProviderRequest) -> LiveDataResult:
        """
        Executes query against upstream live railway gateway.
        Fails closed with UNAVAILABLE if credentials are unset or query fails,
        enabling seamless fallback to CuratedRailwayAdapter.
        """
        origin = request.params.get("origin") or request.location
        if not origin and request.params.get("action") != "live_status":
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                provider_id=self.provider_id,
                payload={"error": "Origin location is required to search railway schedules."},
                provenance=self.build_provenance(
                    request=request,
                    source_url="https://enquiry.indianrail.gov.in/",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer="Origin location is required to search railway schedules.",
                ),
            )
        origin = origin or "Delhi"
        destination = request.params.get("destination") or "Katra"
        action = request.params.get("action", "train_search")
        train_no = str(request.params.get("train_number") or request.params.get("train_no") or "").strip()

        if not self.is_configured():
            prov = self.build_provenance(
                request=request,
                source_url="https://enquiry.indianrail.gov.in/",
                freshness_status=FreshnessStatus.UNAVAILABLE.value,
                verification_status=VerificationStatus.UNVERIFIED.value,
                disclaimer="Live railway gateway key is not configured in server environment. Curated schedule fallback active.",
            )
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={
                    "origin": origin,
                    "destination": destination,
                    "live_status_available": False,
                    "reason": "RAILCORE_API_KEY or RAILWAY_API_KEY environment variable not configured",
                },
                provider_id=self.provider_id,
                source_provenance=prov,
                error=ProviderError(
                    error_type=ProviderErrorType.MISSING_CREDENTIALS.value,
                    message="Live railway credentials unset; fallback to curated schedules required.",
                    provider_id=self.provider_id,
                    domain=self.domain,
                ),
            )

        # 1. Live Train Status Query
        if action in ("live_status", "train_status") and train_no:
            endpoint = f"{self._base_url.rstrip('/')}/trains/{train_no}/live"
            data, err = self._execute_http_get(endpoint)
            if err or not data:
                prov = self.build_provenance(
                    request=request,
                    source_url="https://enquiry.indianrail.gov.in/",
                    freshness_status=FreshnessStatus.UNAVAILABLE.value,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    disclaimer=f"Live train status query failed: {err.message if err else 'No data'}",
                )
                return LiveDataResult(
                    status="UNAVAILABLE",
                    domain=self.domain,
                    data={"train_number": train_no, "live_status_available": False},
                    provider_id=self.provider_id,
                    source_provenance=prov,
                    error=err,
                )

            # Parse and normalize live telemetry
            payload = data.get("data") if isinstance(data.get("data"), dict) else data
            current_station = (
                payload.get("current_station_name")
                or payload.get("current_station")
                or payload.get("station_name")
                or "In Transit"
            )
            current_code = payload.get("current_station_code") or payload.get("station_code") or ""
            delay_mins = int(payload.get("delay_minutes") or payload.get("delay") or 0)
            last_updated = payload.get("last_reported_at") or payload.get("last_updated") or payload.get("status_as_of") or get_utc_now_iso()
            status_text = payload.get("status_text") or ("On Time" if delay_mins <= 5 else f"Delayed by {delay_mins} mins")
            speed = payload.get("speed_kmph")
            approaching = payload.get("approaching_station_name") or payload.get("next_stop", {}).get("station_name") if isinstance(payload.get("next_stop"), dict) else None

            prov = self.build_provenance(
                request=request,
                source_url=f"https://enquiry.indianrail.gov.in/mntes/q?opt=TrainRunningStatus&trainNo={train_no}",
                freshness_status=FreshnessStatus.LIVE.value,
                verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                disclaimer=f"Live running telemetry retrieved from {self.provider_name}.",
            )
            return LiveDataResult(
                status="SUCCESS",
                domain=self.domain,
                data={
                    "train_number": train_no,
                    "train_name": payload.get("train_name", ""),
                    "live_status_available": True,
                    "current_station": current_station,
                    "current_station_code": current_code,
                    "delay_minutes": delay_mins,
                    "is_on_time": delay_mins <= 5,
                    "status_text": status_text,
                    "last_updated": last_updated,
                    "speed_kmph": speed,
                    "approaching_station": approaching,
                    "provider": self.provider_name,
                },
                provider_id=self.provider_id,
                source_provenance=prov,
            )

        # 2. Train Schedule / Route Query
        if action in ("train_schedule", "schedule") and train_no:
            endpoint = f"{self._base_url.rstrip('/')}/trains/{train_no}/schedule"
            data, err = self._execute_http_get(endpoint)
            if (err or not data) and self._provider_type == "railcore":
                # Fallback to /route if /schedule fails
                endpoint = f"{self._base_url.rstrip('/')}/trains/{train_no}/route"
                data, err = self._execute_http_get(endpoint)

            if err or not data:
                return LiveDataResult(
                    status="UNAVAILABLE",
                    domain=self.domain,
                    data={"train_number": train_no, "schedule_available": False},
                    provider_id=self.provider_id,
                    error=err,
                )
            payload = data.get("data") if isinstance(data.get("data"), dict) else data
            prov = self.build_provenance(
                request=request,
                source_url="https://enquiry.indianrail.gov.in/",
                freshness_status=FreshnessStatus.LIVE.value,
                verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
                disclaimer=f"Train schedule retrieved from {self.provider_name}.",
            )
            return LiveDataResult(
                status="SUCCESS",
                domain=self.domain,
                data={
                    "train_number": train_no,
                    "train_name": payload.get("train_name", ""),
                    "runs_on": payload.get("running_days", payload.get("runs_on", [])),
                    "halts": payload.get("stops", payload.get("halts", payload.get("stations", []))),
                    "live_status_available": False,
                    "schedule_available": True,
                    "provider": self.provider_name,
                },
                provider_id=self.provider_id,
                source_provenance=prov,
            )

        # 3. Train Search Query (between stations)
        stn_map = {
            "delhi": "NDLS",
            "new delhi": "NDLS",
            "old delhi": "DLI",
            "katra": "SVDK",
            "smvd katra": "SVDK",
            "shri mata vaishno devi katra": "SVDK",
            "jammu": "JAT",
            "jammu tawi": "JAT",
            "chandigarh": "CDG",
            "amritsar": "ASR",
            "haridwar": "HW",
            "kanpur": "CNB",
            "lucknow": "LKO",
            "mumbai": "MMCT",
            "pune": "PUNE",
            "varanasi": "BSB",
            "bhopal": "BPL",
            "patna": "PNBE",
        }
        from_code = stn_map.get(origin.lower().strip(), origin.strip().upper())
        to_code = stn_map.get(destination.lower().strip(), destination.strip().upper())
        today = datetime.now()
        travel_date = request.params.get("travel_date") or request.params.get("date") or (today + timedelta(days=1)).strftime("%Y-%m-%d")

        if self._provider_type == "railcore":
            endpoint = f"{self._base_url.rstrip('/')}/routes/trains?from={urllib.parse.quote(from_code)}&to={urllib.parse.quote(to_code)}&date={urllib.parse.quote(travel_date)}"
        else:
            endpoint = f"{self._base_url.rstrip('/')}/trains/search?from={urllib.parse.quote(origin)}&to={urllib.parse.quote(destination)}"

        data, err = self._execute_http_get(endpoint)
        if err or not data:
            return LiveDataResult(
                status="UNAVAILABLE",
                domain=self.domain,
                data={"origin": origin, "destination": destination, "trains": []},
                provider_id=self.provider_id,
                error=err,
            )

        payload = data.get("data") if isinstance(data.get("data"), (dict, list)) else data
        raw_trains = []
        if isinstance(payload, dict):
            raw_trains = payload.get("trains") or payload.get("data") or []
        elif isinstance(payload, list):
            raw_trains = payload

        normalized_trains = []
        for t in raw_trains:
            if isinstance(t, dict):
                normalized_trains.append({
                    "train_number": str(t.get("train_number") or ""),
                    "train_name": t.get("train_name") or t.get("extended_train_name") or "",
                    "origin_station_code": t.get("from_station_code") or from_code,
                    "origin_station_name": t.get("from_station_name") or origin,
                    "destination_station_code": t.get("to_station_code") or to_code,
                    "destination_station_name": t.get("to_station_name") or destination,
                    "departure_time": t.get("departure_time") or t.get("from_std") or "",
                    "arrival_time": t.get("arrival_time") or t.get("to_sta") or "",
                    "duration_minutes": t.get("duration_minutes") or 0,
                    "duration_hours": round(float(t.get("duration_minutes") or 0) / 60.0, 1) if t.get("duration_minutes") else None,
                    "days_of_operation": t.get("running_days") or [],
                    "travel_classes": t.get("classes") or [],
                    "live_status_available": True,
                })

        prov = self.build_provenance(
            request=request,
            source_url="https://enquiry.indianrail.gov.in/",
            freshness_status=FreshnessStatus.LIVE.value,
            verification_status=VerificationStatus.VERIFIED_OFFICIAL_SOURCE.value,
            disclaimer=f"Train route search retrieved from {self.provider_name}.",
        )
        return LiveDataResult(
            status="SUCCESS",
            domain=self.domain,
            data={
                "origin": origin,
                "destination": destination,
                "trains": normalized_trains,
                "schedules": normalized_trains,
                "live_status_available": True,
                "provider": self.provider_name,
            },
            provider_id=self.provider_id,
            source_provenance=prov,
        )
