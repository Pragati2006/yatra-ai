"""
utils/cache_manager.py
In-Memory Data Freshness & Cache Engine for Yatra AI.

Provides a thread-safe, process-local in-memory cache with:
- Configurable Time-To-Live (TTL) and Maximum Stale Age policies.
- Deterministic parameter-based cache key generation (never uses raw user prompts).
- Fresh cache hits, expired entry detection, and graceful stale fallback.
- Explicit single-flight request coordination to prevent duplicate concurrent API requests.
- Strict provenance integration (never marks cached or stale data as live).
- Bounded capacity with LRU and expired entry eviction.
- Lightweight observability and diagnostic statistics.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. ENUMS & CONFIGURATION DEFAULTS
# -----------------------------------------------------------------------------

class CacheState(str, Enum):
    """Lifecycle state of a cache entry upon lookup."""
    FRESH = "fresh"                    # Within active TTL window
    STALE = "stale"                    # Past TTL but within permitted max_stale window
    EXPIRED_UNUSABLE = "expired"       # Past max_stale; cannot be used as fallback
    MISS = "miss"                      # Not present in cache


# Initial configuration defaults (configurable via environment variables)
DEFAULT_TTL_WEATHER: float = float(os.getenv("CACHE_TTL_WEATHER", "1800.0"))         # 30 minutes
DEFAULT_MAX_STALE_WEATHER: float = float(os.getenv("CACHE_MAX_STALE_WEATHER", "21600.0"))  # 6 hours
DEFAULT_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "500"))


# -----------------------------------------------------------------------------
# 2. CACHE ENTRY DATA MODEL
# -----------------------------------------------------------------------------

@dataclass
class CacheEntry:
    """Strongly-typed in-memory cache entry retaining complete temporal metadata."""
    key: str
    payload: Any
    created_at: str                        # Timezone-aware ISO 8601 UTC timestamp
    created_at_mono: float                 # monotonic clock for clock-skew-immune expiration
    expires_at: str                        # Timezone-aware ISO 8601 UTC expiration timestamp
    expires_at_mono: float                 # monotonic expiration point
    ttl_seconds: float                     # Configured TTL in seconds
    max_stale_seconds: float               # Maximum age beyond TTL for stale fallback
    category: str                          # Domain category (e.g., 'weather')
    source_identifier: str = "open_meteo"  # Upstream source identifier
    request_params: Optional[Dict[str, Any]] = None
    last_retrieved_at: Optional[str] = None
    hit_count: int = 0

    def is_fresh(self, current_mono: float) -> bool:
        """Determines if the entry is within its active TTL window."""
        return current_mono < self.expires_at_mono

    def is_stale_usable(self, current_mono: float) -> bool:
        """Determines if the entry is expired but still within permitted stale fallback window."""
        return self.expires_at_mono <= current_mono <= (self.expires_at_mono + self.max_stale_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entry metadata (omitting complex internal mono floats)."""
        return {
            "key": self.key,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "ttl_seconds": self.ttl_seconds,
            "max_stale_seconds": self.max_stale_seconds,
            "category": self.category,
            "source_identifier": self.source_identifier,
            "request_params": self.request_params,
            "last_retrieved_at": self.last_retrieved_at,
            "hit_count": self.hit_count,
        }


# -----------------------------------------------------------------------------
# 3. DETERMINISTIC CACHE KEY GENERATION
# -----------------------------------------------------------------------------

def generate_cache_key(category: str, params: Dict[str, Any]) -> str:
    """Generates a normalized, deterministic cache key from structured parameters.
    Never uses raw user queries or unstructured natural language prompts.
    """
    cat = str(category).strip().lower()
    items = []
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, float):
            items.append(f"{k}:{v:.4f}")
        elif isinstance(v, (list, tuple)):
            items.append(f"{k}:{','.join(str(x) for x in sorted(v))}")
        else:
            items.append(f"{k}:{str(v).strip().lower()}")

    canonical_str = "|".join(items)
    digest = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]
    return f"{cat}:{digest}"


def generate_weather_cache_key(
    location_key: str,
    target_date_str: str,
    latitude: float,
    longitude: float,
    elevation_m: int,
    provider: str = "open_meteo",
) -> str:
    """Builds a human-readable deterministic cache key for elevation-aware weather.
    Ensures that Katra (750m), Ardhkuwari (1400m), Bhawan (1585m), and Bhairon (2011m)
    always produce strictly separate, non-colliding keys.
    """
    norm_loc = str(location_key).strip().lower()
    return f"weather:{provider}:{norm_loc}:{target_date_str}:{latitude:.2f}:{longitude:.2f}:{elevation_m}"


# -----------------------------------------------------------------------------
# 4. CENTRAL IN-MEMORY CACHE MANAGER
# -----------------------------------------------------------------------------

class CacheManager:
    """Centralized, thread-safe, in-memory caching engine for Yatra AI."""

    def __init__(
        self,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        ttl_weather: float = DEFAULT_TTL_WEATHER,
        max_stale_weather: float = DEFAULT_MAX_STALE_WEATHER,
        monotonic_clock: Optional[Callable[[], float]] = None,
        utc_clock: Optional[Callable[[], str]] = None,
    ):
        self.max_entries = max_entries
        self._lock = threading.RLock()
        self._single_flight_mutex = threading.Lock()
        self._in_flight_locks: Dict[str, threading.Lock] = {}

        # Default category policies
        self.ttl_policies: Dict[str, float] = {
            "weather": ttl_weather,
            "default": 300.0,
        }
        self.max_stale_policies: Dict[str, float] = {
            "weather": max_stale_weather,
            "default": 1800.0,
        }

        # Controllable clocks for deterministic unit testing
        self._mono_clock = monotonic_clock or time.monotonic
        self._utc_clock = utc_clock or (lambda: datetime.now(timezone.utc).isoformat())

        # Storage & telemetry
        self._entries: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stale_fallbacks": 0,
            "refresh_successes": 0,
            "refresh_failures": 0,
            "evictions": 0,
        }

    # -------------------------------------------------------------------------
    # Internal Time & Helpers
    # -------------------------------------------------------------------------

    def _now_mono(self) -> float:
        return self._mono_clock()

    def _now_utc_iso(self) -> str:
        return self._utc_clock()

    # -------------------------------------------------------------------------
    # Core Cache Operations
    # -------------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Returns payload on a fresh cache hit; returns None on miss or expiration."""
        payload, status, _ = self.get_with_status(key)
        if status == CacheState.FRESH.value:
            return payload
        return None

    def get_with_status(self, key: str) -> Tuple[Optional[Any], str, Optional[CacheEntry]]:
        """Evaluates entry state and returns (payload, status_string, entry).
        Status is one of: 'fresh', 'stale', 'expired', 'miss'.
        """
        now_m = self._now_mono()
        now_utc = self._now_utc_iso()

        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                self._stats["misses"] += 1
                return None, CacheState.MISS.value, None

            entry.last_retrieved_at = now_utc

            if entry.is_fresh(now_m):
                entry.hit_count += 1
                self._stats["hits"] += 1
                return entry.payload, CacheState.FRESH.value, entry

            elif entry.is_stale_usable(now_m):
                # Stale fallback available; does not increment hit until caller confirms use
                return entry.payload, CacheState.STALE.value, entry

            else:
                self._stats["misses"] += 1
                return None, CacheState.EXPIRED_UNUSABLE.value, entry

    def record_stale_fallback(self, key: str) -> None:
        """Records telemetry when a caller actively consumes a stale entry as fallback."""
        with self._lock:
            self._stats["stale_fallbacks"] += 1

    def record_refresh_result(self, success: bool) -> None:
        """Records telemetry when a background or expired refresh attempt finishes."""
        with self._lock:
            if success:
                self._stats["refresh_successes"] += 1
            else:
                self._stats["refresh_failures"] += 1

    def set(
        self,
        key: str,
        payload: Any,
        ttl: Optional[float] = None,
        max_stale: Optional[float] = None,
        category: str = "default",
        request_params: Optional[Dict[str, Any]] = None,
        source_identifier: str = "open_meteo",
    ) -> CacheEntry:
        """Stores a payload with category-specific TTL and maximum stale window.
        Enforces maximum capacity via LRU / expired entry eviction.
        """
        now_m = self._now_mono()
        now_utc = self._now_utc_iso()

        # Resolve TTL and stale policies
        cat_key = category.lower().strip()
        ttl_val = ttl if ttl is not None else self.ttl_policies.get(cat_key, self.ttl_policies["default"])
        stale_val = max_stale if max_stale is not None else self.max_stale_policies.get(cat_key, self.max_stale_policies["default"])

        expires_mono = now_m + ttl_val
        # Format human-readable ISO expiration
        try:
            cur_dt = datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
            exp_dt = datetime.fromtimestamp(cur_dt.timestamp() + ttl_val, tz=timezone.utc)
            expires_utc = exp_dt.isoformat()
        except Exception:
            expires_utc = now_utc

        entry = CacheEntry(
            key=key,
            payload=payload,
            created_at=now_utc,
            created_at_mono=now_m,
            expires_at=expires_utc,
            expires_at_mono=expires_mono,
            ttl_seconds=ttl_val,
            max_stale_seconds=stale_val,
            category=cat_key,
            source_identifier=source_identifier,
            request_params=request_params,
            last_retrieved_at=now_utc,
            hit_count=0,
        )

        with self._lock:
            # Capacity guard: Evict if necessary before inserting new entry
            if len(self._entries) >= self.max_entries and key not in self._entries:
                self._evict_one_entry(now_m)

            self._entries[key] = entry

        return entry

    def invalidate(self, key: str) -> bool:
        """Removes a specific entry from the cache. Returns True if found."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def clear(self) -> int:
        """Clears all cached entries and resets in-flight mutexes. Returns count cleared."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            with self._single_flight_mutex:
                self._in_flight_locks.clear()
            return count

    # -------------------------------------------------------------------------
    # Eviction Strategy
    # -------------------------------------------------------------------------

    def _evict_one_entry(self, current_mono: float) -> None:
        """Eviction strategy:
        1. First evict any entry that is completely expired past max_stale.
        2. If none, evict the entry with the oldest last_retrieved_at (LRU).
        """
        # Pass 1: Completely expired
        expired_keys = [
            k for k, e in self._entries.items()
            if current_mono > (e.expires_at_mono + e.max_stale_seconds)
        ]
        if expired_keys:
            evict_k = expired_keys[0]
            del self._entries[evict_k]
            self._stats["evictions"] += 1
            return

        # Pass 2: LRU by last_retrieved_at timestamp or created_at_mono
        oldest_k = min(self._entries.keys(), key=lambda k: self._entries[k].created_at_mono)
        del self._entries[oldest_k]
        self._stats["evictions"] += 1

    # -------------------------------------------------------------------------
    # Single-Flight Request Coordination
    # -------------------------------------------------------------------------

    def get_or_fetch(
        self,
        key: str,
        fetcher_callable: Callable[[], Optional[Any]],
        category: str = "weather",
        ttl: Optional[float] = None,
        max_stale: Optional[float] = None,
        request_params: Optional[Dict[str, Any]] = None,
        source_identifier: str = "open_meteo",
    ) -> Tuple[Optional[Any], str]:
        """Coordinates retrieval across fresh cache, provider fetch, and stale fallback.
        Ensures thread-safe single-flight execution so identical concurrent queries
        do not trigger duplicate external provider calls.

        Returns:
            (payload, provenance_status) where provenance_status is one of:
            - 'live': Freshly retrieved from external provider and saved to cache
            - 'cached': Returned from fresh cache within TTL
            - 'stale': Returned from expired cache because provider fetch failed
            - 'fallback': No usable cache was found; caller should use fallback
            - 'miss': Provider failed and no cache was found
        """
        # Step A: Fast-path check for fresh cache hit
        payload, status, entry = self.get_with_status(key)
        if status == CacheState.FRESH.value and payload is not None:
            return payload, "cached"

        # Step B: Coordinate single-flight lock per key
        with self._single_flight_mutex:
            if key not in self._in_flight_locks:
                self._in_flight_locks[key] = threading.Lock()
            flight_lock = self._in_flight_locks[key]

        # Acquire lock for this specific key
        with flight_lock:
            # Re-check cache inside lock (another thread may have completed the fetch)
            payload, status, entry = self.get_with_status(key)
            if status == CacheState.FRESH.value and payload is not None:
                return payload, "cached"

            # Execute provider fetch
            fresh_data = None
            try:
                fresh_data = fetcher_callable()
            except Exception as exc:
                logger.debug("Provider fetch failed inside single-flight for %s: %s", key, exc)
                fresh_data = None

            if fresh_data is not None:
                # Provider success: update cache and return live
                self.record_refresh_result(success=True)
                self.set(
                    key=key,
                    payload=fresh_data,
                    ttl=ttl,
                    max_stale=max_stale,
                    category=category,
                    request_params=request_params,
                    source_identifier=source_identifier,
                )
                return fresh_data, "live"

            # Provider failed: check for stale fallback
            self.record_refresh_result(success=False)
            if entry and entry.is_stale_usable(self._now_mono()):
                self.record_stale_fallback(key)
                return entry.payload, "stale"

            # No usable stale cache available
            return None, "fallback"

    # -------------------------------------------------------------------------
    # Telemetry & Observability
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns snapshot of current cache statistics and entry distributions."""
        now_m = self._now_mono()
        with self._lock:
            fresh_count = sum(1 for e in self._entries.values() if e.is_fresh(now_m))
            expired_count = sum(1 for e in self._entries.values() if not e.is_fresh(now_m))

            cat_counts: Dict[str, int] = {}
            for e in self._entries.values():
                cat_counts[e.category] = cat_counts.get(e.category, 0) + 1

            return {
                "total_entries": len(self._entries),
                "fresh_entries": fresh_count,
                "expired_entries": expired_count,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "stale_fallbacks": self._stats["stale_fallbacks"],
                "refresh_successes": self._stats["refresh_successes"],
                "refresh_failures": self._stats["refresh_failures"],
                "evictions": self._stats["evictions"],
                "max_entries": self.max_entries,
                "categories": cat_counts,
            }


# -----------------------------------------------------------------------------
# 5. GLOBAL CACHE MANAGER SINGLETON
# -----------------------------------------------------------------------------

_GLOBAL_CACHE_MANAGER: Optional[CacheManager] = None
_GLOBAL_INIT_LOCK = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Returns the process-local CacheManager singleton instance."""
    global _GLOBAL_CACHE_MANAGER
    if _GLOBAL_CACHE_MANAGER is None:
        with _GLOBAL_INIT_LOCK:
            if _GLOBAL_CACHE_MANAGER is None:
                _GLOBAL_CACHE_MANAGER = CacheManager()
    return _GLOBAL_CACHE_MANAGER


def reset_cache_manager(custom_manager: Optional[CacheManager] = None) -> CacheManager:
    """Resets or replaces the global cache manager (used in automated test fixtures)."""
    global _GLOBAL_CACHE_MANAGER
    with _GLOBAL_INIT_LOCK:
        if _GLOBAL_CACHE_MANAGER is not None:
            _GLOBAL_CACHE_MANAGER.clear()
        _GLOBAL_CACHE_MANAGER = custom_manager if custom_manager is not None else CacheManager()
    return _GLOBAL_CACHE_MANAGER
