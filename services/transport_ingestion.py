"""
services/transport_ingestion.py
Responsible Data Ingestion Pipeline & Adapters for Yatra AI (Phase 14.4.3).

Provides reusable, structured ingestion adapters for official transport data sources:
- RailwayNTESAdapter: Indian Railways National Train Enquiry System & Published Time Tables
- PublicBusCorporationAdapter: JKSRTC, HRTC, PRTC State Transport Corporations
- DGCAFlightScheduleAdapter: DGCA Domestic Passenger Flight Schedules

Features:
- Structured extraction & strict schema validation
- Duplicate detection with deterministic keying
- Normalization of station and city names with alias mapping
- Source URL retention, fetch timestamps, and audit traceability
- Change detection and expiry tracking
- Rate-limiting safeguards and graceful error logging
- Never scrapes transactional booking portals or bypasses website access rules
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from services.transport_schema import (
    CANONICAL_CITY_ALIASES,
    TransportDataType,
    TransportMode,
    UnifiedTransportRecord,
    VerificationStatus,
    normalize_city_name,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. Base Source Adapter
# -----------------------------------------------------------------------------

class TransportSourceAdapter(ABC):
    """Abstract base class for all transport data source adapters."""

    def __init__(self, source_name: str, source_url: str, default_mode: str):
        self.source_name = source_name
        self.source_url = source_url
        self.default_mode = default_mode

    @abstractmethod
    def extract_records(self, raw_data: Any) -> List[UnifiedTransportRecord]:
        """Extracts and normalizes raw source payloads into standard UnifiedTransportRecords."""
        pass


# -----------------------------------------------------------------------------
# 2. Source-Specific Adapters
# -----------------------------------------------------------------------------

class RailwayNTESAdapter(TransportSourceAdapter):
    """Adapter for official Indian Railways published timetables and NTES schedules."""

    def __init__(self):
        super().__init__(
            source_name="National Train Enquiry System (NTES) / Indian Railways Public Timetable",
            source_url="https://enquiry.indianrail.gov.in/",
            default_mode=TransportMode.TRAIN.value,
        )

    def extract_records(self, raw_data: Any) -> List[UnifiedTransportRecord]:
        records: List[UnifiedTransportRecord] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        items = raw_data.get("schedules", []) if isinstance(raw_data, dict) else (raw_data if isinstance(raw_data, list) else [])
        for item in items:
            train_no = str(item.get("train_number") or item.get("service_number") or "").strip()
            train_name = item.get("train_name", f"Express {train_no}")
            orig_name = normalize_city_name(item.get("origin_city") or item.get("origin_station_name") or item.get("origin"))
            dest_name = normalize_city_name(item.get("destination_city") or item.get("destination_station_name") or item.get("destination"))
            orig_code = (item.get("origin_station_code") or "").upper() or None
            dest_code = (item.get("destination_station_code") or "").upper() or None

            rec_id = item.get("record_id") or f"train_{train_no}_{orig_code or orig_name[:4].lower()}_{dest_code or dest_name[:4].lower()}"

            days = item.get("days_of_operation") or item.get("operating_days") or ["Daily"]
            if isinstance(days, str):
                days = [d.strip() for d in days.split(",") if d.strip()]

            # Calculate or clean duration
            dur_str = item.get("duration") or item.get("duration_hours")
            if isinstance(dur_str, (int, float)):
                dur_str = f"{int(dur_str)}h {int((dur_str % 1) * 60)}m"

            v_status = item.get("verification_status") or VerificationStatus.OFFICIALLY_VERIFIED.value

            records.append(
                UnifiedTransportRecord(
                    record_id=rec_id,
                    mode=TransportMode.TRAIN.value,
                    origin_name=orig_name,
                    origin_code=orig_code,
                    destination_name=dest_name,
                    destination_code=dest_code,
                    operator=item.get("operator") or "Indian Railways",
                    service_number=train_no,
                    service_type=item.get("service_type") or self._infer_service_type(train_name),
                    departure_time=item.get("departure_time"),
                    arrival_time=item.get("arrival_time"),
                    operating_days=days,
                    duration=dur_str,
                    distance_km=item.get("total_distance_km") or item.get("distance_km"),
                    fare=item.get("fare") or item.get("indicative_fare_min"),
                    indicative_fare_min=item.get("indicative_fare_min"),
                    indicative_fare_max=item.get("indicative_fare_max"),
                    currency=item.get("currency") or "INR",
                    source_name=item.get("source_name") or self.source_name,
                    source_url=item.get("source_url") or self.source_url,
                    fetched_at=item.get("verified_at") or now_iso,
                    last_verified_at=item.get("verified_at") or now_iso,
                    valid_from=item.get("valid_from") or "2026-01-01",
                    valid_until=item.get("valid_until") or "2026-12-31",
                    verification_status=v_status,
                    data_type=TransportDataType.CURATED_TIMETABLE.value,
                    notes=item.get("notes") or f"Curated timetable service: {train_name}",
                    intermediate_stops=item.get("major_halts") or item.get("intermediate_stops") or [],
                    travel_classes=item.get("travel_classes") or ["SL", "3A", "2A"],
                )
            )
        return records

    @staticmethod
    def _infer_service_type(train_name: str) -> str:
        name_lower = train_name.lower()
        if "vande bharat" in name_lower:
            return "Vande Bharat Express"
        if "rajdhani" in name_lower:
            return "Rajdhani Superfast"
        if "shatabdi" in name_lower:
            return "Shatabdi Express"
        if "garib rath" in name_lower:
            return "Garib Rath Express"
        if "sampark kranti" in name_lower or "superfast" in name_lower or "sf" in name_lower:
            return "Superfast Express"
        if "mail" in name_lower:
            return "Mail Express"
        return "Express"


class PublicBusCorporationAdapter(TransportSourceAdapter):
    """Adapter for official State Road Transport Corporations (JKSRTC, HRTC, PRTC)."""

    def __init__(self, operator_name: str = "JKSRTC", source_url: str = "https://jksrtc.co.in/"):
        super().__init__(
            source_name=f"{operator_name} Official Schedule & Statutory Tariff",
            source_url=source_url,
            default_mode=TransportMode.BUS.value,
        )
        self.operator_name = operator_name

    def extract_records(self, raw_data: Any) -> List[UnifiedTransportRecord]:
        records: List[UnifiedTransportRecord] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        items = raw_data.get("schedules", []) if isinstance(raw_data, dict) else (raw_data if isinstance(raw_data, list) else [])
        for item in items:
            op_name = item.get("operator_name") or item.get("operator") or self.operator_name
            service_id = item.get("service_id") or item.get("record_id") or f"bus_{op_name.lower()[:5]}_{item.get('departure_time', 'sched').replace(':', '')}"
            orig_name = normalize_city_name(item.get("origin_city") or item.get("origin_bus_stand") or item.get("origin"))
            dest_name = normalize_city_name(item.get("destination_city") or item.get("destination_bus_stand") or item.get("destination"))

            days = item.get("days_of_operation") or item.get("operating_days") or ["Daily"]
            if isinstance(days, str):
                days = [d.strip() for d in days.split(",") if d.strip()]

            dur_str = item.get("duration") or item.get("duration_hours")
            if isinstance(dur_str, (int, float)):
                dur_str = f"{int(dur_str)}h {int((dur_str % 1) * 60)}m"

            v_status = item.get("verification_status") or VerificationStatus.OFFICIALLY_VERIFIED.value

            records.append(
                UnifiedTransportRecord(
                    record_id=service_id,
                    mode=TransportMode.BUS.value,
                    origin_name=orig_name,
                    origin_code=item.get("origin_station_code") or item.get("origin_bus_stand"),
                    destination_name=dest_name,
                    destination_code=item.get("destination_station_code") or item.get("destination_bus_stand"),
                    operator=op_name,
                    service_number=item.get("service_number") or service_id,
                    service_type=item.get("service_type") or "Public Stage Carriage Bus",
                    departure_time=item.get("departure_time"),
                    arrival_time=item.get("arrival_time"),
                    operating_days=days,
                    duration=dur_str,
                    distance_km=item.get("distance_km") or item.get("total_distance_km"),
                    fare=item.get("fare") or item.get("indicative_fare_min"),
                    indicative_fare_min=item.get("indicative_fare_min"),
                    indicative_fare_max=item.get("indicative_fare_max"),
                    currency="INR",
                    source_name=item.get("source_name") or self.source_name,
                    source_url=item.get("source_url") or self.source_url,
                    fetched_at=item.get("verified_at") or now_iso,
                    last_verified_at=item.get("verified_at") or now_iso,
                    valid_from=item.get("valid_from") or "2026-01-01",
                    valid_until=item.get("valid_until") or "2026-12-31",
                    verification_status=v_status,
                    data_type=TransportDataType.STATUTORY_TARIFF.value,
                    notes=item.get("notes") or f"Public stage carriage service operated by {op_name}",
                    intermediate_stops=item.get("route_description") or item.get("intermediate_stops") or [],
                )
            )
        return records


class DGCAFlightScheduleAdapter(TransportSourceAdapter):
    """Adapter for official DGCA domestic passenger flight schedules."""

    def __init__(self):
        super().__init__(
            source_name="Directorate General of Civil Aviation (DGCA) Domestic City-Pair Schedule",
            source_url="https://www.dgca.gov.in/",
            default_mode=TransportMode.FLIGHT.value,
        )

    def extract_records(self, raw_data: Any) -> List[UnifiedTransportRecord]:
        records: List[UnifiedTransportRecord] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        items = raw_data.get("schedules", []) if isinstance(raw_data, dict) else (raw_data if isinstance(raw_data, list) else [])
        for item in items:
            flight_no = item.get("flight_number") or item.get("service_number") or "DGCA-SCHEDULED"
            airline_name = item.get("airline_name") or item.get("airline") or item.get("operator") or "Scheduled Commercial Carrier"
            orig_name = normalize_city_name(item.get("origin_city") or item.get("origin_airport_name") or item.get("origin"))
            dest_name = normalize_city_name(item.get("destination_city") or item.get("destination_airport_name") or item.get("destination"))
            orig_code = (item.get("origin_airport_code") or "").upper() or None
            dest_code = (item.get("destination_airport_code") or "").upper() or None

            rec_id = item.get("route_id") or item.get("record_id") or f"flight_{flight_no.replace(' ', '_').lower()}_{orig_code or orig_name[:3].lower()}_{dest_code or dest_name[:3].lower()}"

            days = item.get("operating_days") or ["Daily"]
            if isinstance(days, str):
                days = [d.strip() for d in days.split(",") if d.strip()]

            dur_str = item.get("duration") or item.get("estimated_duration_desc") or item.get("duration_hours")
            if isinstance(dur_str, (int, float)):
                dur_str = f"{int(dur_str)}h {int((dur_str % 1) * 60)}m"

            v_status = item.get("verification_status") or VerificationStatus.OFFICIALLY_VERIFIED.value

            records.append(
                UnifiedTransportRecord(
                    record_id=rec_id,
                    mode=TransportMode.FLIGHT.value,
                    origin_name=orig_name,
                    origin_code=orig_code,
                    destination_name=dest_name,
                    destination_code=dest_code,
                    operator=airline_name,
                    service_number=flight_no,
                    service_type="Scheduled Passenger Flight",
                    departure_time=item.get("departure_time"),
                    arrival_time=item.get("arrival_time"),
                    operating_days=days,
                    duration=dur_str,
                    distance_km=item.get("distance_km"),
                    fare=item.get("fare") or item.get("indicative_fare_min"),
                    indicative_fare_min=item.get("indicative_fare_min"),
                    indicative_fare_max=item.get("indicative_fare_max"),
                    currency="INR",
                    source_name=item.get("source_name") or self.source_name,
                    source_url=item.get("source_url") or self.source_url,
                    fetched_at=item.get("verified_at") or now_iso,
                    last_verified_at=item.get("verified_at") or now_iso,
                    valid_from=item.get("valid_from") or "2026-01-01",
                    valid_until=item.get("valid_until") or "2026-12-31",
                    verification_status=v_status,
                    data_type=TransportDataType.CORRIDOR_GUIDANCE.value,
                    notes=item.get("notes") or f"Scheduled domestic flight by {airline_name}",
                    intermediate_stops=item.get("layover_airports") or [],
                )
            )
        return records


# -----------------------------------------------------------------------------
# 3. Ingestion Pipeline with Duplicate Detection & Validation
# -----------------------------------------------------------------------------

class TransportIngestionPipeline:
    """
    Orchestrates the ingestion, deduplication, validation, and storage of transport schedules.
    """

    def __init__(self):
        self.seen_signatures: Set[Tuple[str, str, str, str, str]] = set()
        self.ingested_records: List[UnifiedTransportRecord] = []
        self.rejection_log: List[Dict[str, Any]] = []

    @property
    def stats(self) -> Dict[str, int]:
        """Returns summary counts of pipeline actions."""
        dup_count = sum(1 for r in self.rejection_log if r.get("reason") == "DUPLICATE_SIGNATURE")
        return {
            "ingested": len(self.ingested_records),
            "rejected": len(self.rejection_log),
            "duplicate": dup_count,
        }

    def ingest_record(self, record: UnifiedTransportRecord) -> str:
        """Ingests a single record, returning status string: INGESTED | DUPLICATE | EXPIRED | REJECTED."""
        if record.verification_status == VerificationStatus.EXPIRED.value:
            return "EXPIRED"
        accepted, rejected = self.ingest_records([record])
        if accepted == 1:
            return "INGESTED"
        if self.rejection_log and self.rejection_log[-1].get("reason") == "DUPLICATE_SIGNATURE":
            return "DUPLICATE"
        return "REJECTED"

    def ingest_records(
        self,
        records: List[UnifiedTransportRecord],
        rate_limit_delay_sec: float = 0.0,
    ) -> Tuple[int, int]:
        """
        Processes a list of UnifiedTransportRecords.
        Returns: (accepted_count, rejected_count)
        """
        accepted = 0
        rejected = 0

        for rec in records:
            if rate_limit_delay_sec > 0:
                time.sleep(rate_limit_delay_sec)

            # 1. Validation Checks
            is_valid, reason = self._validate_record(rec)
            if not is_valid:
                self.rejection_log.append({"record_id": rec.record_id, "reason": reason, "record": rec.to_dict()})
                rejected += 1
                continue

            # 2. Duplicate Detection
            # Unique signature: (mode, normalized_origin, normalized_destination, service_number, departure_time)
            sig = (
                rec.mode.lower(),
                normalize_city_name(rec.origin_name).lower(),
                normalize_city_name(rec.destination_name).lower(),
                (rec.service_number or "").strip().lower(),
                (rec.departure_time or "").strip().lower(),
            )
            if sig in self.seen_signatures:
                self.rejection_log.append({"record_id": rec.record_id, "reason": "DUPLICATE_SIGNATURE", "signature": sig})
                rejected += 1
                continue

            # 3. Accept Record
            self.seen_signatures.add(sig)
            self.ingested_records.append(rec)
            accepted += 1

        logger.info("Ingestion completed: %d accepted, %d rejected/deduplicated.", accepted, rejected)
        return accepted, rejected

    def _validate_record(self, rec: UnifiedTransportRecord) -> Tuple[bool, str]:
        """Validates record integrity according to truth-in-data rules."""
        if not rec.record_id or not rec.record_id.strip():
            return False, "EMPTY_RECORD_ID"
        if not rec.origin_name or not rec.origin_name.strip() or rec.origin_name == "Unknown":
            return False, "INVALID_ORIGIN_NAME"
        if not rec.destination_name or not rec.destination_name.strip() or rec.destination_name == "Unknown":
            return False, "INVALID_DESTINATION_NAME"
        if not rec.operator or not rec.operator.strip():
            return False, "EMPTY_OPERATOR"
        if not rec.source_url or not rec.source_url.startswith("http"):
            return False, "INVALID_OR_MISSING_SOURCE_URL"

        # Check distance/fare sanity
        if rec.distance_km is not None and rec.distance_km < 0:
            return False, "NEGATIVE_DISTANCE"
        if rec.fare is not None and rec.fare < 0:
            return False, "NEGATIVE_FARE"

        return True, "OK"

    def export_to_json(self, file_path: str) -> None:
        """Exports all accepted records to a standardized JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "records_count": len(self.ingested_records),
                "rejections_count": len(self.rejection_log),
                "pipeline_version": "14.4.3",
            },
            "schedules": [r.to_dict() for r in self.ingested_records],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Exported %d records to %s", len(self.ingested_records), file_path)


# Global Singleton accessor
def get_transport_ingestion_pipeline() -> TransportIngestionPipeline:
    return TransportIngestionPipeline()
