"""
services/live_data/__init__.py
Live Data Architecture Package for Yatra AI.

Provides provider-independent live, cached, and curated data access with:
- Standardized data contracts (LiveDataResult, ProviderRequest, ProviderError, ProviderMetadata).
- BaseLiveDataProvider abstract interface.
- Thread-safe ProviderRegistry.
- UnifiedLiveDataManager with single-flight cache coordination.
- Curated and live provider adapters.
"""

from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import (
    ContactCategory,
    DataDomain,
    LiveDataResult,
    NoticeAggregateStatus,
    NoticeCategory,
    NoticeLifecycleStatus,
    OperationalNotice,
    ProviderError,
    ProviderErrorType,
    ProviderLifecycle,
    ProviderMetadata,
    ProviderRequest,
    VerifiedContact,
)
from services.live_data.exceptions import (
    LiveDataError,
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderMalformedResponseError,
    ProviderNotFoundError,
    ProviderTimeoutError,
    ProviderValidationError,
    UnsupportedDomainError,
)
from services.live_data.manager import (
    UnifiedLiveDataManager,
    get_live_data_manager,
    reset_live_data_manager,
)
from services.live_data.registry import ProviderRegistry

__all__ = [
    # Base and Interfaces
    "BaseLiveDataProvider",
    "ProviderRegistry",
    "UnifiedLiveDataManager",
    "get_live_data_manager",
    "reset_live_data_manager",
    # Contracts
    "ContactCategory",
    "DataDomain",
    "LiveDataResult",
    "NoticeAggregateStatus",
    "NoticeCategory",
    "NoticeLifecycleStatus",
    "OperationalNotice",
    "ProviderError",
    "ProviderErrorType",
    "ProviderLifecycle",
    "ProviderMetadata",
    "ProviderRequest",
    "VerifiedContact",
    # Exceptions
    "LiveDataError",
    "ProviderConfigurationError",
    "ProviderExecutionError",
    "ProviderMalformedResponseError",
    "ProviderNotFoundError",
    "ProviderTimeoutError",
    "ProviderValidationError",
    "UnsupportedDomainError",
]
