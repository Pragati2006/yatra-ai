"""
services/live_data/exceptions.py
Standard Exception Hierarchy for Yatra AI Live Data Architecture.

Defines clear, distinct exceptions for provider configuration, execution,
network timeouts, input validation, and malformed upstream responses.
"""

from typing import Optional


class LiveDataError(Exception):
    """Base exception for all live data framework errors."""
    def __init__(self, message: str, provider_id: Optional[str] = None, domain: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id
        self.domain = domain


class ProviderNotFoundError(LiveDataError):
    """Raised when no provider is registered or configured for a requested domain."""
    pass


class UnsupportedDomainError(LiveDataError):
    """Raised when an unrecognized data domain is requested."""
    pass


class ProviderConfigurationError(LiveDataError):
    """Raised when a provider lacks necessary credentials, endpoints, or environment config."""
    pass


class ProviderValidationError(LiveDataError):
    """Raised when incoming request parameters fail schema or invariant validation."""
    pass


class ProviderExecutionError(LiveDataError):
    """Raised when an unexpected error occurs during provider execution."""
    pass


class ProviderTimeoutError(LiveDataError):
    """Raised when an upstream provider request exceeds configured timeout."""
    pass


class ProviderMalformedResponseError(LiveDataError):
    """Raised when an upstream provider returns unparseable or schema-violating data."""
    pass
