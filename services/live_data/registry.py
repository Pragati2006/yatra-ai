"""
services/live_data/registry.py
Thread-Safe Provider Registry for Yatra AI Live Data Architecture.

Maintains registrations of data providers organized by domain, offering discovery,
priority-ordered selection, and lifecycle inspection without global side-effects.
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple

from services.live_data.base import BaseLiveDataProvider
from services.live_data.contracts import ProviderMetadata

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Thread-safe catalog of registered live data providers."""

    def __init__(self):
        self._lock = threading.RLock()
        # (domain_lower, provider_id_lower) -> BaseLiveDataProvider
        self._providers: Dict[Tuple[str, str], BaseLiveDataProvider] = {}

    def register(self, provider: BaseLiveDataProvider) -> None:
        """Registers a provider instance. If a provider with the same domain and ID
        already exists, it is replaced cleanly with a warning logged.
        """
        if not isinstance(provider, BaseLiveDataProvider):
            raise TypeError(f"Expected BaseLiveDataProvider instance, got {type(provider).__name__}")

        key = (provider.domain.strip().lower(), provider.provider_id.strip().lower())
        with self._lock:
            if key in self._providers:
                logger.warning(
                    "Replacing existing provider '%s' in domain '%s'.",
                    provider.provider_id,
                    provider.domain,
                )
            self._providers[key] = provider
            logger.debug(
                "Registered provider '%s' for domain '%s' (priority=%d, simulated=%s).",
                provider.provider_id,
                provider.domain,
                provider.priority,
                provider.is_simulated,
            )

    def unregister(self, domain: str, provider_id: str) -> bool:
        """Removes a registered provider. Returns True if removed, False if not found."""
        key = (domain.strip().lower(), provider_id.strip().lower())
        with self._lock:
            if key in self._providers:
                del self._providers[key]
                logger.debug("Unregistered provider '%s' from domain '%s'.", provider_id, domain)
                return True
            return False

    def get_provider(self, domain: str, provider_id: str) -> Optional[BaseLiveDataProvider]:
        """Retrieves a specific provider by domain and provider_id."""
        key = (domain.strip().lower(), provider_id.strip().lower())
        with self._lock:
            return self._providers.get(key)

    def get_providers_for_domain(
        self,
        domain: str,
        configured_only: bool = True,
    ) -> List[BaseLiveDataProvider]:
        """Discovers all providers registered for a given domain, sorted by priority ascending
        (lower priority integer = higher selection preference).
        """
        d_lower = domain.strip().lower()
        with self._lock:
            matched = [
                prov for (dom, _), prov in self._providers.items()
                if dom == d_lower and (not configured_only or prov.is_configured())
            ]
            # Sort by priority ascending (e.g. priority 10 precedes priority 100)
            matched.sort(key=lambda p: (p.priority, p.provider_id))
            return matched

    def list_all_providers(self) -> List[ProviderMetadata]:
        """Returns metadata descriptions for all registered providers."""
        with self._lock:
            return [prov.get_metadata() for prov in self._providers.values()]

    def clear(self) -> None:
        """Removes all registered providers. Primarily used for unit test cleanup."""
        with self._lock:
            self._providers.clear()
            logger.debug("Cleared all providers from registry.")
