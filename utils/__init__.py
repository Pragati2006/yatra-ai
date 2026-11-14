"""
utils package
Week 10: Ethical Boundary, Compliance, Data Masking, and Structured Logging.
"""

from utils.masking import (
    mask_email,
    mask_otp,
    mask_token,
    mask_api_key,
    mask_phone,
    mask_name,
    mask_sensitive_data,
    sanitize_log_message,
)
from utils.logger import (
    get_structured_logger,
    log_event,
    set_correlation_id,
    get_correlation_id,
)
from utils.provenance import (
    SourceType,
    FreshnessStatus,
    VerificationStatus,
    ProvenanceRecord,
    create_provenance,
    validate_provenance,
    normalize_source_type,
    normalize_freshness_status,
    normalize_verification_status,
    get_utc_now_iso,
    deduplicate_provenance,
    extract_provenance_from_tool_result,
    attach_provenance_to_response,
)
from utils.cache_manager import (
    CacheState,
    CacheEntry,
    CacheManager,
    generate_cache_key,
    generate_weather_cache_key,
    get_cache_manager,
    reset_cache_manager,
)

__all__ = [
    "mask_email",
    "mask_otp",
    "mask_token",
    "mask_api_key",
    "mask_phone",
    "mask_name",
    "mask_sensitive_data",
    "sanitize_log_message",
    "get_structured_logger",
    "log_event",
    "set_correlation_id",
    "get_correlation_id",
    "SourceType",
    "FreshnessStatus",
    "VerificationStatus",
    "ProvenanceRecord",
    "create_provenance",
    "validate_provenance",
    "normalize_source_type",
    "normalize_freshness_status",
    "normalize_verification_status",
    "get_utc_now_iso",
    "deduplicate_provenance",
    "extract_provenance_from_tool_result",
    "attach_provenance_to_response",
    "CacheState",
    "CacheEntry",
    "CacheManager",
    "generate_cache_key",
    "generate_weather_cache_key",
    "get_cache_manager",
    "reset_cache_manager",
]
