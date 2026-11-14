"""
weather.py
Elevation-Aware Multi-Location Weather Integration for Yatra AI (Phase 8 Checkpoint 8.1).

Provides live numerical weather forecasts from Open-Meteo REST API and researched
altitude-adjusted seasonal climate patterns across the four sacred pilgrimage locations:
1. Katra Town: Latitude 32.99, Longitude 74.93, Elevation 750 m (Base town)
2. Ardhkuwari: Latitude 33.02, Longitude 74.95, Elevation 1,400 m (Midway milestone & Garbh Joon)
3. Vaishno Devi Bhawan: Latitude 33.03, Longitude 74.95, Elevation 1,585 m (Sanctum Sanctorum, ~5,200 ft)
4. Bhairon Temple: Latitude 33.04, Longitude 74.95, Elevation 2,011 m (Highest peak shrine, ~6,600 ft)

Capabilities:
- Live Open-Meteo API queries incorporating exact latitude, longitude, and elevation.
- Verified Open-Meteo request parameters using standardized 'weather_code'.
- Researched altitude-adjusted seasonal averages as fallback when offline or beyond forecast window.
- Independent location failure isolation (partial failure support).
- Natural language location resolution distinguishing pilgrimage locations, default base town, and unrecognized locations.
- Structured provenance metadata (timezone-aware ISO 8601 retrieval timestamp, provider data timestamp with offset, freshness status, verification status).
- Strict backward compatibility with existing legacy get_weather and get_weather_summary functions.
"""

from datetime import date, datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import requests

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 1. CONFIGURED REFERENCE PILGRIMAGE LOCATIONS & ELEVATIONS
# -----------------------------------------------------------------------------

PILGRIMAGE_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "katra": {
        "key": "katra",
        "name": "Katra Town",
        "latitude": 32.99,
        "longitude": 74.93,
        "elevation_m": 750,
        "description": "Base town for the pilgrimage trek and primary transport hub",
    },
    "ardhkuwari": {
        "key": "ardhkuwari",
        "name": "Ardhkuwari",
        "latitude": 33.02,
        "longitude": 74.95,
        "elevation_m": 1400,
        "description": "Midway trek milestone (~6 km from Katra) and sacred Garbh Joon cave",
    },
    "bhawan": {
        "key": "bhawan",
        "name": "Vaishno Devi Bhawan",
        "latitude": 33.03,
        "longitude": 74.95,
        "elevation_m": 1585,
        "description": "Sacred sanctum sanctorum and main Darshan shrine (~5,200 ft)",
    },
    "bhairon": {
        "key": "bhairon",
        "name": "Bhairon Temple",
        "latitude": 33.04,
        "longitude": 74.95,
        "elevation_m": 2011,
        "description": "Highest peak shrine (~6,600 ft) accessible via trek or passenger ropeway",
    },
}

DEFAULT_LOCATION_KEY = "katra"
FORECAST_WINDOW_DAYS = 15  # Open-Meteo's short-range numerical forecast horizon

# -----------------------------------------------------------------------------
# 2. STANDARD DISCLAIMERS & METADATA CONTRACTS
# -----------------------------------------------------------------------------

MOUNTAIN_WEATHER_DISCLAIMER = (
    "Model-based numerical forecast from Open-Meteo. Mountain weather in the Trikuta Hills "
    "can change rapidly; high-altitude conditions may vary from numerical predictions. "
    "This is not an on-site shrine sensor measurement."
)

SEASONAL_FALLBACK_DISCLAIMER = (
    "Seasonal Climate Estimate — Not a Live Forecast. Based on India Meteorological "
    "Department (IMD) historical climatological normals for Katra base station (Index 42050) "
    "and standard environmental lapse rates (~6.5°C/km) across the Trikuta Hills pilgrimage gradient. "
    "Live weather retrieval was unavailable."
)

# -----------------------------------------------------------------------------
# 3. RESEARCHED ALTITUDE-ADJUSTED SEASONAL CLIMATE PATTERNS
# -----------------------------------------------------------------------------
# Grounded in India Meteorological Department (IMD) climatological normals for Katra / Reasi
# and standard atmospheric lapse rate modeling (~6.5°C per 1,000m rise) across the 4 elevations.
# month -> { location_key -> (low_c, high_c, summary, advisory) }

SEASONAL_CLIMATE_PATTERNS: Dict[int, Dict[str, Tuple[int, int, str, str]]] = {
    1: {  # January
        "katra": (5, 15, "Cold, often foggy mornings", "Cold base town mornings; warm layers required for starting the trek."),
        "ardhkuwari": (2, 11, "Chilly mountain winds, morning fog", "Chilly midway trek; carry windcheater and thermal innerwear."),
        "bhawan": (0, 8, "Freezing nights, occasional light snow", "Freezing temperatures at Bhawan; heavy woollens and gloves mandatory."),
        "bhairon": (-2, 6, "Sub-zero freezing winds, snow flurries", "Sub-zero peak winds; heavy winter protection and non-slip boots required."),
    },
    2: {  # February
        "katra": (7, 18, "Cold, clearing through the month", "Still cool at night; a jacket is recommended for early morning starts."),
        "ardhkuwari": (4, 14, "Cool and breezy", "Cool mountain winds; light jacket advised during daytime trek."),
        "bhawan": (2, 11, "Cold nights, chilly mountain breeze", "Cold evenings and nights; warm woollens required for night Darshan."),
        "bhairon": (0, 9, "Very cold and windy", "High windchill at peak; warm headwear and jacket advised."),
    },
    3: {  # March
        "katra": (11, 23, "Mild and pleasant", "Good trekking weather, comfortable daytime temperatures."),
        "ardhkuwari": (8, 19, "Pleasant daytime trekking", "Comfortable daytime trek; light sweater advised for evenings."),
        "bhawan": (6, 16, "Brisk and cool, chilly evenings", "Cool mountain weather; warm layer recommended for evening Aarti."),
        "bhairon": (3, 13, "Cold mountain breeze, clear skies", "Brisk peak weather; jacket required."),
    },
    4: {  # April
        "katra": (15, 28, "Warm and pleasant", "Good trekking weather before summer heat sets in."),
        "ardhkuwari": (12, 24, "Comfortable mountain air", "Pleasant trek conditions; stay well hydrated."),
        "bhawan": (10, 21, "Pleasant daytime, cool evenings", "Pleasant Darshan conditions; light shawl/jacket for nights."),
        "bhairon": (7, 18, "Breezy and pleasant", "Refreshing breeze at peak; comfortable for pilgrimage."),
    },
    5: {  # May
        "katra": (19, 32, "Hot daytime", "Start early treks to avoid midday Katra heat; carry ample water."),
        "ardhkuwari": (16, 28, "Warm with mountain breeze", "Midway temperatures are noticeably cooler than Katra town."),
        "bhawan": (14, 25, "Pleasant mountain daytime", "Comfortable Darshan temperatures; cool night breeze."),
        "bhairon": (11, 22, "Pleasantly cool and breezy", "Cool refuge from base heat; ideal daytime visit."),
    },
    6: {  # June
        "katra": (22, 35, "Very hot, humid before monsoon", "Hottest month in Katra; start treks after sunset or before dawn."),
        "ardhkuwari": (19, 31, "Warm and humid", "Humid ascent; stay hydrated with mineral water along the route."),
        "bhawan": (17, 27, "Mild and comfortable", "Pleasant relief from plain heat; comfortable Darshan weather."),
        "bhairon": (14, 24, "Cool mountain breeze", "Pleasantly cool mountain peak."),
    },
    7: {  # July
        "katra": (22, 32, "Monsoon - heavy rain likely", "Trek route can be slippery; check landslide advisories."),
        "ardhkuwari": (19, 28, "Misty with frequent rain showers", "Slippery tracks; rain ponchos and sturdy footwear essential."),
        "bhawan": (16, 24, "Foggy, rain showers; slippery tracks", "Wet conditions; keep electronics in waterproof pouches."),
        "bhairon": (13, 21, "Cloud-covered, high rain risk", "Ropeway service may pause during dense fog or lightning."),
    },
    8: {  # August
        "katra": (21, 31, "Monsoon - heavy rain likely", "Trek route can be slippery; watch for weather advisories."),
        "ardhkuwari": (18, 27, "Humid, frequent rain showers", "Slippery ascents; rain poncho and trekking pole recommended."),
        "bhawan": (15, 23, "Cool, foggy, wet track conditions", "Rain showers common; carry waterproof rain gear."),
        "bhairon": (12, 20, "Chilly, rain and fog", "High mountain fog; take caution on exposed steps."),
    },
    9: {  # September
        "katra": (19, 29, "Monsoon tapering off", "Rain becomes less frequent; very pleasant trekking window."),
        "ardhkuwari": (16, 25, "Pleasant clearing breeze", "Clear mountain air returning; lush green hills."),
        "bhawan": (13, 22, "Comfortable trekking, cool evenings", "Crisp mountain weather; light woollens for evening Darshan."),
        "bhairon": (10, 19, "Brisk breeze, panoramic views", "Clear viewpoints; light jacket recommended."),
    },
    10: {  # October
        "katra": (13, 26, "Pleasant and dry (Peak yatra window)", "Widely considered the best month for the yatra; dry and clear."),
        "ardhkuwari": (10, 22, "Crisp mountain air, great visibility", "Comfortable trekking; cooler night temperatures."),
        "bhawan": (8, 19, "Cool daytime, chilly night Darshan", "Chilly nights (~8°C); warm layers required for evening/night Aarti."),
        "bhairon": (5, 16, "Cold mountain winds, clear views", "Cold winds at peak; warm jacket and muffler advised."),
    },
    11: {  # November
        "katra": (8, 22, "Pleasant, cooling down", "Dry and comfortable; Katra nights turn cold."),
        "ardhkuwari": (5, 18, "Cold morning and evening air", "Chilly mountain trek; fleece jacket and warm socks advised."),
        "bhawan": (3, 15, "Cold evenings, warm layers mandatory", "Cold nights at Bhawan (~3°C); thermal innerwear and woollens required."),
        "bhairon": (1, 12, "Freezing winds, thermal wear required", "Near-freezing peak temperatures; heavy woollens and gloves advised."),
    },
    12: {  # December
        "katra": (5, 16, "Cold winter days", "Cold Katra town; warm jacket required for starting trek."),
        "ardhkuwari": (2, 12, "Very cold, morning frost", "Frost on tracks; non-slip walking shoes and heavy woollens required."),
        "bhawan": (0, 9, "Freezing nights, possible light snowfall", "Freezing temperatures at Bhawan; thermals, heavy jacket, and cap mandatory."),
        "bhairon": (-2, 7, "Sub-zero freeze, icy winds and snow", "Sub-zero conditions; heavy winter gear and gloves required."),
    },
}

# Backwards compatibility alias for Katra seasonal table
SEASONAL_AVERAGES: Dict[int, Tuple[int, int, str, str]] = {
    m: SEASONAL_CLIMATE_PATTERNS[m]["katra"] for m in range(1, 13)
}

# -----------------------------------------------------------------------------
# 4. WMO WEATHER CODE MAPPINGS
# -----------------------------------------------------------------------------

WEATHER_CODE_SUMMARY: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# -----------------------------------------------------------------------------
# 5. NATURAL LANGUAGE LOCATION RESOLUTION & INTENT CLASSIFICATION
# -----------------------------------------------------------------------------

def resolve_location_intent(query_or_location: Optional[str] = None) -> Tuple[str, List[str], Optional[str]]:
    """Resolves natural language queries into canonical pilgrimage location keys or flags unrecognized locations.

    Returns:
        (status, resolved_keys, unrecognized_token)
        - 'MATCHED': One or more valid pilgrimage locations matched.
        - 'DEFAULT_KATRA': General weather inquiry without a foreign location mentioned.
        - 'UNRECOGNIZED_LOCATION': A specific unrecognized location was requested.
    """
    if not query_or_location or not str(query_or_location).strip():
        return ("DEFAULT_KATRA", [DEFAULT_LOCATION_KEY], None)

    t = str(query_or_location).lower().strip()

    # 1. Multi-location / all keywords
    all_keywords = [
        "all", "all four", "all locations", "entire trek", "entire route",
        "full route", "complete trek", "every location", "along the trek",
        "whole trek", "all stops", "all four pilgrimage locations",
    ]
    if any(re.search(rf"\b{re.escape(kw)}\b", t) for kw in all_keywords):
        return ("MATCHED", ["katra", "ardhkuwari", "bhawan", "bhairon"], None)

    found: List[str] = []

    # Check Bhairon
    if any(k in t for k in ("bhairon", "bhairavnath", "bhairo")):
        found.append("bhairon")

    # Check Bhawan
    if any(k in t for k in ("bhawan", "sanctum", "shrine", "darshan", "main temple", "mandir")):
        found.append("bhawan")
    elif "vaishno devi" in t and "katra" not in t and "ardhkuwari" not in t and "bhairon" not in t:
        found.append("bhawan")

    # Check Ardhkuwari
    if any(k in t for k in ("ardhkuwari", "adhkuwari", "ardh kuwari", "adh kuwari", "garbh joon", "garbhjoon", "midway", "halfway")):
        found.append("ardhkuwari")

    # Check Katra
    if any(k in t for k in ("katra", "base town", "base", "railway station")):
        found.append("katra")

    if found:
        canonical_order = ["katra", "ardhkuwari", "bhawan", "bhairon"]
        return ("MATCHED", [k for k in canonical_order if k in found], None)

    # If no pilgrimage location matched, determine whether this is a general query or a foreign location
    clean_t = re.sub(r"[^\w\s]", " ", t)
    tokens = clean_t.split()
    generic_words = {
        "what", "is", "the", "like", "in", "at", "for", "on", "a", "an", "tell", "me",
        "about", "how", "cold", "hot", "temperature", "weather", "forecast", "update",
        "today", "tomorrow", "tonight", "weekend", "please", "can", "you", "check",
        "current", "conditions", "will", "it", "be", "there", "give", "any", "rain",
        "raining", "snow", "snowing", "chilly", "breeze", "wind", "now", "right"
    }
    non_generic = [tok for tok in tokens if tok not in generic_words]

    if not non_generic:
        # User asked for weather generally without naming an unknown location
        return ("DEFAULT_KATRA", [DEFAULT_LOCATION_KEY], None)

    # A foreign/unsupported location was specifically requested
    m_prep = re.search(r"\b(?:in|at|for|around|of)\s+([a-zA-Z0-9_\-]+)\b", t)
    if m_prep and m_prep.group(1).lower() not in generic_words:
        unrecognized_name = m_prep.group(1).title()
    else:
        unrecognized_name = " ".join(non_generic).title()

    return ("UNRECOGNIZED_LOCATION", [], unrecognized_name)


def resolve_locations(query_or_location: Optional[str] = None) -> List[str]:
    """Resolves natural language queries into canonical pilgrimage location keys.

    Supported Locations:
    - 'katra': Katra Town (750 m)
    - 'ardhkuwari': Ardhkuwari Midway & Garbh Joon (1,400 m)
    - 'bhawan': Vaishno Devi Bhawan Shrine (1,585 m)
    - 'bhairon': Bhairon Temple Peak (2,011 m)

    Returns:
        List of location keys in geographical ascending order. Defaults to ['katra'].
    """
    status, keys, _ = resolve_location_intent(query_or_location)
    return keys if keys else [DEFAULT_LOCATION_KEY]


def get_location_info(location_key: str) -> Dict[str, Any]:
    """Returns configured coordinates and metadata for a given location key."""
    norm_key = location_key.lower().strip()
    return PILGRIMAGE_LOCATIONS.get(norm_key, PILGRIMAGE_LOCATIONS[DEFAULT_LOCATION_KEY])

# -----------------------------------------------------------------------------
# 6. SEASONAL FALLBACK ESTIMATOR (OFFLINE / ERROR RESILIENT)
# -----------------------------------------------------------------------------

def _seasonal_fallback(target_date: date, location_key: str = "katra") -> Dict[str, Any]:
    """Generates an altitude-grounded seasonal climate estimate based on IMD normals.
    Guaranteed never to raise an exception or fail offline.
    """
    loc_info = get_location_info(location_key)
    month = target_date.month
    month_data = SEASONAL_CLIMATE_PATTERNS.get(month, SEASONAL_CLIMATE_PATTERNS[10])
    loc_climate = month_data.get(loc_info["key"], month_data["katra"])

    low_c, high_c, summary, advisory = loc_climate
    retrieval_time = datetime.now(timezone.utc).isoformat()

    return {
        "location": loc_info["name"],
        "location_key": loc_info["key"],
        "latitude": loc_info["latitude"],
        "longitude": loc_info["longitude"],
        "elevation_m": loc_info["elevation_m"],
        "date": target_date.isoformat(),
        "summary": summary,
        "condition": summary,
        "low_c": low_c,
        "high_c": high_c,
        "temperature_c": None,
        "apparent_temperature_c": None,
        "precipitation_mm": 0.0,
        "precipitation_probability_pct": 0,
        "wind_speed_kmh": 0.0,
        "advisory": advisory,
        "source": "seasonal_average",
        "source_name": "Curated Regional Climatological Baseline (IMD Katra Normals & Standard Lapse-Rate Model)",
        "source_url": "https://mausam.imd.gov.in",
        "source_tier": "tier_3_curated_catalog",
        "source_type": "curated_data",
        "climatological_methodology": (
            "Historical climatological normals from India Meteorological Department (IMD) "
            "for Katra base station (Index 42050), combined with standard atmospheric environmental "
            "lapse rate adjustments (~6.5°C per 1,000 m elevation rise) for Ardhkuwari (1,400 m), "
            "Bhawan (1,585 m), and Bhairon (2,011 m). These are seasonal planning baselines, not live measurements."
        ),
        "retrieval_timestamp": retrieval_time,
        "data_timestamp": None,
        "freshness_status": "fallback",
        "weather_type": "seasonal_estimate",
        "verification_status": "curated_climatological_estimate",
        "disclaimer": SEASONAL_FALLBACK_DISCLAIMER,
    }

# -----------------------------------------------------------------------------
# 7. OPEN-METEO LIVE FORECAST FETCHER
# -----------------------------------------------------------------------------

def _fetch_live_forecast_location(
    loc_key: str,
    target_date: date,
    timeout: float = 1.5,
) -> Optional[Dict[str, Any]]:
    """Queries Open-Meteo REST API using exact latitude, longitude, and elevation.
    Uses verified 'weather_code' parameter. Returns structured live forecast dict or None on failure.
    """
    loc_info = get_location_info(loc_key)
    retrieval_time = datetime.now(timezone.utc).isoformat()

    # Verified Open-Meteo API v1 parameter specification:
    # Uses 'weather_code' for both daily and current metrics
    params: Dict[str, Any] = {
        "latitude": loc_info["latitude"],
        "longitude": loc_info["longitude"],
        "elevation": loc_info["elevation_m"],
        "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,weather_code",
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "timezone": "auto",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    }

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("Open-Meteo live forecast request failed for %s: %s", loc_key, exc)
        return None

    # Parse daily slice
    daily = data.get("daily", {})
    daily_times = daily.get("time", [])
    if not daily_times:
        logger.debug("Open-Meteo returned empty daily forecast for %s", loc_key)
        return None

    # Weather condition code (check standardized weather_code first)
    w_code = 0
    if daily.get("weather_code"):
        w_code = daily["weather_code"][0]
    elif daily.get("weathercode"):
        w_code = daily["weathercode"][0]
    elif data.get("current", {}).get("weather_code") is not None:
        w_code = data["current"]["weather_code"]

    summary = WEATHER_CODE_SUMMARY.get(w_code, "Forecast available")

    # Temperatures
    low_c_vals = daily.get("temperature_2m_min", [])
    high_c_vals = daily.get("temperature_2m_max", [])
    if not low_c_vals or not high_c_vals:
        return None

    low_c = round(low_c_vals[0])
    high_c = round(high_c_vals[0])

    # Apparent temperatures
    app_max_vals = daily.get("apparent_temperature_max", [])
    app_min_vals = daily.get("apparent_temperature_min", [])
    apparent_temp_c = None
    if app_max_vals and app_min_vals:
        apparent_temp_c = round((app_max_vals[0] + app_min_vals[0]) / 2.0, 1)

    # Precipitation and wind
    precip_sum_vals = daily.get("precipitation_sum", [])
    precip_mm = float(precip_sum_vals[0]) if precip_sum_vals else 0.0

    precip_prob_vals = daily.get("precipitation_probability_max", [])
    precip_prob_pct = int(precip_prob_vals[0]) if precip_prob_vals else 0

    wind_vals = daily.get("wind_speed_10m_max", [])
    wind_kmh = float(wind_vals[0]) if wind_vals else 0.0

    # Current conditions if present
    current = data.get("current", {})
    current_temp = current.get("temperature_2m")
    if current.get("apparent_temperature") is not None:
        apparent_temp_c = float(current.get("apparent_temperature"))

    # Timezone-aware provider data timestamp
    provider_tz = data.get("timezone", "Asia/Kolkata")
    provider_offset_sec = data.get("utc_offset_seconds", 19800)
    raw_time = current.get("time") or (daily_times[0] if daily_times else None)

    if raw_time:
        offset_hours = int(provider_offset_sec // 3600)
        offset_mins = int((abs(provider_offset_sec) % 3600) // 60)
        sign = "+" if provider_offset_sec >= 0 else "-"
        provider_data_timestamp = f"{raw_time}{sign}{offset_hours:02d}:{offset_mins:02d}"
    else:
        provider_data_timestamp = None

    # Build contextual trekking advisory
    advisory = _build_location_advisory(loc_key, low_c, high_c, precip_prob_pct, precip_mm, wind_kmh)

    # Elevation reported by provider or configured reference
    actual_elevation = data.get("elevation", loc_info["elevation_m"])

    return {
        "location": loc_info["name"],
        "location_key": loc_info["key"],
        "latitude": loc_info["latitude"],
        "longitude": loc_info["longitude"],
        "elevation_m": int(round(actual_elevation)),
        "date": target_date.isoformat(),
        "summary": summary,
        "condition": summary,
        "low_c": low_c,
        "high_c": high_c,
        "temperature_c": current_temp,
        "apparent_temperature_c": apparent_temp_c,
        "precipitation_mm": precip_mm,
        "precipitation_probability_pct": precip_prob_pct,
        "wind_speed_kmh": wind_kmh,
        "advisory": advisory,
        "source": "forecast",
        "source_name": "Open-Meteo Weather API",
        "source_url": "https://open-meteo.com",
        "source_tier": "tier_2_open_api",
        "source_type": "live_api",
        "retrieval_timestamp": retrieval_time,
        "data_timestamp": provider_data_timestamp,
        "provider_timezone": provider_tz,
        "provider_utc_offset_seconds": provider_offset_sec,
        "freshness_status": "live",
        "weather_type": "live_forecast",
        "verification_status": "verified_external_api",
        "disclaimer": MOUNTAIN_WEATHER_DISCLAIMER,
    }


def _build_location_advisory(
    loc_key: str,
    low_c: int,
    high_c: int,
    precip_prob: int,
    precip_mm: float,
    wind_kmh: float,
) -> str:
    """Generates practical pilgrim advisories based on elevation and live forecast metrics."""
    parts = []

    if precip_prob >= 50 or precip_mm > 2.0:
        parts.append("Rain or showers predicted; carrying waterproof rain ponchos and non-slip trekking footwear is essential.")
    elif precip_prob >= 25:
        parts.append("Chance of scattered rain showers; keep an umbrella or light rain protection handy.")

    if wind_kmh > 25:
        parts.append("High mountain wind gusts expected; hold belongings securely and take care along exposed sections.")

    if loc_key == "bhairon":
        if low_c <= 3:
            parts.append("Sub-zero/near-freezing night chills at Bhairon peak (~6,600 ft); heavy woollens, thermal wear, and windproof jacket mandatory.")
        else:
            parts.append("Exposed high-altitude shrine (~6,600 ft); noticeably colder than Katra town with strong winds. Warm jacket recommended.")
    elif loc_key == "bhawan":
        if low_c <= 5:
            parts.append("Cold night temperatures at Bhawan (~5,200 ft); warm woollens and thermal layers strongly advised for evening/night Darshan and Aarti.")
        else:
            parts.append("Bhawan runs noticeably cooler than Katra town; warm layers recommended for evening Darshan.")
    elif loc_key == "ardhkuwari":
        parts.append("Midway milestone (~1,400 m). Mountain breeze is brisk; keep a light jacket or shawl accessible for waiting at the Garbh Joon cave.")
    else:  # Katra
        if high_c >= 32:
            parts.append("Warm/hot in Katra town; start early morning or evening treks to avoid midday heat.")
        else:
            parts.append("Pleasant conditions in Katra base town; comfortable walking attire and good trekking shoes recommended.")

    return " ".join(parts)

# -----------------------------------------------------------------------------
# 8. MULTI-LOCATION & COMPARISON ENGINE
# -----------------------------------------------------------------------------

def clear_weather_cache() -> int:
    """Clears all cached weather entries across all locations."""
    try:
        from utils.cache_manager import get_cache_manager
        return get_cache_manager().clear()
    except Exception:
        return 0


def fetch_location_weather(
    location_key: str,
    target_date: Optional[date] = None,
    timeout: float = 5.0,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Fetches weather for a single pilgrimage location with seamless caching and fallback.
    - Fresh cache hit: returns cached payload with source_type='cached_api', freshness_status='cached'.
    - Cache miss: calls live provider, updates cache, returns with source_type='live_api', freshness_status='live'.
    - Provider failure: checks for usable stale cache (within max stale window) before falling back to seasonal model.
    Never raises an exception.
    """
    if target_date is None:
        target_date = date.today()

    days_out = (target_date - date.today()).days
    if not (0 <= days_out <= FORECAST_WINDOW_DAYS):
        return _seasonal_fallback(target_date, location_key=location_key)

    if not use_cache:
        live = _fetch_live_forecast_location(location_key, target_date, timeout=timeout)
        if live:
            return live
        return _seasonal_fallback(target_date, location_key=location_key)

    loc_info = get_location_info(location_key)
    try:
        from utils.cache_manager import (
            DEFAULT_MAX_STALE_WEATHER,
            DEFAULT_TTL_WEATHER,
            generate_weather_cache_key,
            get_cache_manager,
        )
        cache_key = generate_weather_cache_key(
            location_key=loc_info["key"],
            target_date_str=target_date.isoformat(),
            latitude=loc_info["latitude"],
            longitude=loc_info["longitude"],
            elevation_m=loc_info["elevation_m"],
        )
        cache_mgr = get_cache_manager()

        def _do_fetch():
            return _fetch_live_forecast_location(location_key, target_date, timeout=timeout)

        payload, outcome_status = cache_mgr.get_or_fetch(
            key=cache_key,
            fetcher_callable=_do_fetch,
            category="weather",
            ttl=DEFAULT_TTL_WEATHER,
            max_stale=DEFAULT_MAX_STALE_WEATHER,
            request_params={
                "location": loc_info["key"],
                "date": target_date.isoformat(),
                "latitude": loc_info["latitude"],
                "longitude": loc_info["longitude"],
                "elevation_m": loc_info["elevation_m"],
            },
            source_identifier="open_meteo",
        )

        if payload is not None:
            if outcome_status == "live":
                return payload
            elif outcome_status == "cached":
                cached_res = dict(payload)
                cached_res["source_type"] = "cached_api"
                cached_res["freshness_status"] = "cached"
                cached_res["verification_status"] = "verified_external_api"
                cached_res["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()
                return cached_res
            elif outcome_status == "stale":
                stale_res = dict(payload)
                stale_res["source_type"] = "cached_api"
                stale_res["freshness_status"] = "stale"
                stale_res["verification_status"] = "verified_external_api"
                stale_res["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()
                stale_res["disclaimer"] = (
                    "Stale Weather Forecast — Provider Unavailable. "
                    "Mountain conditions can change rapidly. Check local Shrine Board advisories before commencing the trek."
                )
                return stale_res
    except Exception as exc:
        logger.debug("Cache retrieval failed for %s, falling back to direct fetch: %s", location_key, exc)
        live = _fetch_live_forecast_location(location_key, target_date, timeout=timeout)
        if live:
            return live

    return _seasonal_fallback(target_date, location_key=location_key)


def get_multi_location_weather(
    query_or_locations: Union[str, List[str]],
    target_date_str: Optional[str] = None,
    timeout: float = 5.0,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Coordinates weather retrieval across one or multiple pilgrimage locations.

    Args:
        query_or_locations: Location string, comparison query, or list of location keys.
        target_date_str: Optional ISO date string (YYYY-MM-DD). Defaults to today.
        timeout: Network request timeout in seconds.

    Returns:
        Consolidated dictionary containing primary location weather, individual
        locations list, structured comparison, and provenance metadata.
    """
    # 1. Parse target date
    target_date = date.today()
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except Exception:
            target_date = date.today()

    # 2. Resolve location intent
    is_list = isinstance(query_or_locations, list)
    if is_list:
        resolved_keys = []
        for item in query_or_locations:
            s, ks, _ = resolve_location_intent(str(item))
            resolved_keys.extend(ks)
        # Deduplicate preserving order
        dedup_keys = []
        for k in resolved_keys:
            if k in PILGRIMAGE_LOCATIONS and k not in dedup_keys:
                dedup_keys.append(k)
        resolved_keys = dedup_keys if dedup_keys else [DEFAULT_LOCATION_KEY]
        status = "MATCHED"
        unrec_token = None
    else:
        status, resolved_keys, unrec_token = resolve_location_intent(str(query_or_locations))

    # 3. Handle unrecognized location explicitly (do not silently substitute Katra)
    if status == "UNRECOGNIZED_LOCATION":
        retrieval_time = datetime.now(timezone.utc).isoformat()
        clarification_msg = (
            f"🙏 **Jai Mata Di!** Yatra AI provides specialized mountain weather forecasts "
            f"exclusively for the Maa Vaishno Devi pilgrimage trek route. We could not recognize "
            f"'{unrec_token}' as a supported pilgrimage location.\n\n"
            f"Supported pilgrimage locations:\n"
            f"1. **Katra Town** (~750 m) — Base town and transit hub\n"
            f"2. **Ardhkuwari** (~1,400 m) — Midway milestone & Garbh Joon cave\n"
            f"3. **Vaishno Devi Bhawan** (~1,585 m) — Main Sanctum Sanctorum\n"
            f"4. **Bhairon Temple** (~2,011 m) — High-altitude peak shrine\n\n"
            f"Please ask about one of these pilgrimage locations, or ask to compare them."
        )
        return {
            "status": "UNRECOGNIZED_LOCATION",
            "location": unrec_token,
            "unrecognized_location": unrec_token,
            "clarification_message": clarification_msg,
            "supported_locations": ["Katra Town", "Ardhkuwari", "Vaishno Devi Bhawan", "Bhairon Temple"],
            "summary": f"Location '{unrec_token}' not recognized on the pilgrimage trek route",
            "condition": "Location not supported",
            "low_c": None,
            "high_c": None,
            "temperature_c": None,
            "apparent_temperature_c": None,
            "precipitation_mm": 0.0,
            "precipitation_probability_pct": 0,
            "wind_speed_kmh": 0.0,
            "advisory": "Please specify Katra Town, Ardhkuwari, Bhawan, or Bhairon Temple.",
            "source": "unrecognized_location",
            "source_name": "Yatra AI Pilgrimage Weather Service",
            "source_url": "https://maavaishnodevi.org",
            "retrieval_timestamp": retrieval_time,
            "data_timestamp": None,
            "freshness_status": "unavailable",
            "weather_type": "unrecognized_location",
            "verification_status": "unrecognized_location",
            "disclaimer": "Location outside the Vaishno Devi pilgrimage trek boundary.",
            "locations": [],
            "location_keys": [],
            "is_multi_location": False,
            "comparison": None,
            "is_default_location": False,
        }

    # 4. Fetch each location independently (failure isolation)
    location_results: List[Dict[str, Any]] = []
    for k in resolved_keys:
        res = fetch_location_weather(k, target_date=target_date, timeout=timeout, use_cache=use_cache)
        location_results.append(res)

    if not location_results:
        location_results.append(_seasonal_fallback(target_date, location_key=DEFAULT_LOCATION_KEY))

    # 5. Determine primary location
    primary = location_results[0]

    # 6. Build structured comparison if multiple locations were retrieved
    comparison = None
    if len(location_results) > 1:
        comparison = _build_locations_comparison(location_results)

    # 7. Aggregate freshness status across locations
    statuses = set(r.get("freshness_status") for r in location_results)
    if statuses == {"live"}:
        agg_freshness = "live"
        agg_source_type = "live_api"
    elif statuses == {"cached"}:
        agg_freshness = "cached"
        agg_source_type = "cached_api"
    elif "live" in statuses:
        agg_freshness = "partial_live"
        agg_source_type = "live_api"
    elif "cached" in statuses:
        agg_freshness = "cached"
        agg_source_type = "cached_api"
    elif "stale" in statuses:
        agg_freshness = "stale"
        agg_source_type = "cached_api"
    elif "fallback" in statuses:
        agg_freshness = "fallback"
        agg_source_type = "curated_data"
    else:
        agg_freshness = "unavailable"
        agg_source_type = "unknown_source"

    has_live = any(r.get("weather_type") == "live_forecast" for r in location_results)
    has_cached = any(r.get("freshness_status") in ("cached", "stale") for r in location_results)
    agg_type = "live_forecast" if (has_live or has_cached) else "seasonal_estimate"
    agg_verif = "verified_external_api" if (has_live or has_cached) else "curated_climatological_estimate"
    agg_disclaimer = MOUNTAIN_WEATHER_DISCLAIMER if (has_live or has_cached) else SEASONAL_FALLBACK_DISCLAIMER

    # 8. Assemble consolidated response envelope
    consolidated: Dict[str, Any] = {
        "status": "SUCCESS",
        "location": primary["location"],
        "location_name": primary["location"],
        "location_key": primary["location_key"],
        "latitude": primary["latitude"],
        "longitude": primary["longitude"],
        "elevation_m": primary["elevation_m"],
        "date": primary["date"],
        "summary": primary["summary"],
        "condition": primary["condition"],
        "low_c": primary["low_c"],
        "high_c": primary["high_c"],
        "temperature_c": primary.get("temperature_c"),
        "apparent_temperature_c": primary.get("apparent_temperature_c"),
        "precipitation_mm": primary.get("precipitation_mm", 0.0),
        "precipitation_probability_pct": primary.get("precipitation_probability_pct", 0),
        "wind_speed_kmh": primary.get("wind_speed_kmh", 0.0),
        "advisory": primary["advisory"],
        "source": primary["source"],
        "source_name": primary["source_name"],
        "source_url": primary["source_url"],
        "source_tier": "tier_2_open_api" if (has_live or has_cached) else "tier_3_curated_catalog",
        "source_type": agg_source_type,
        "retrieval_timestamp": primary["retrieval_timestamp"],
        "data_timestamp": primary.get("data_timestamp"),
        "provider_timezone": primary.get("provider_timezone"),
        "provider_utc_offset_seconds": primary.get("provider_utc_offset_seconds"),
        "freshness_status": agg_freshness,
        "weather_type": agg_type,
        "verification_status": agg_verif,
        "disclaimer": agg_disclaimer,
        "locations": location_results,
        "location_keys": [r["location_key"] for r in location_results],
        "is_multi_location": len(location_results) > 1,
        "comparison": comparison,
        "is_default_location": (status == "DEFAULT_KATRA"),
        "default_location_note": "No location specified; defaulting to Katra Town (Pilgrimage Base Town, ~750 m)." if (status == "DEFAULT_KATRA") else None,
    }

    try:
        from utils.provenance import extract_provenance_from_weather
        consolidated["source_provenance"] = extract_provenance_from_weather(consolidated)
    except Exception:
        consolidated["source_provenance"] = []

    return consolidated


def _build_locations_comparison(location_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes objective, model-grounded differences between multiple locations.
    Does NOT manufacture hardcoded lapse-rate adjustments; uses actual returned data.
    """
    sorted_by_elev = sorted(location_results, key=lambda x: x.get("elevation_m", 0))
    lowest = sorted_by_elev[0]
    highest = sorted_by_elev[-1]

    elevation_diff = highest.get("elevation_m", 0) - lowest.get("elevation_m", 0)
    high_diff = lowest.get("high_c", 0) - highest.get("high_c", 0)
    low_diff = lowest.get("low_c", 0) - highest.get("low_c", 0)

    comparison_lines = []
    for loc in sorted_by_elev:
        comparison_lines.append(
            f"• **{loc['location']}** (~{loc['elevation_m']} m): {loc['condition']}, "
            f"{loc['low_c']}°C to {loc['high_c']}°C "
            f"({loc['source_name']})"
        )

    summary_text = (
        f"Elevation difference between {lowest['location']} and {highest['location']} is {elevation_diff} m. "
        f"Maximum temperature is {high_diff}°C cooler and minimum night temperature is {low_diff}°C colder "
        f"at {highest['location']} compared to {lowest['location']}. "
        f"Devotees ascending towards Bhawan and Bhairon should carry warmer clothing."
    )

    return {
        "locations_compared": [l["location"] for l in sorted_by_elev],
        "lowest_location": lowest["location"],
        "highest_location": highest["location"],
        "elevation_difference_m": elevation_diff,
        "temperature_difference_c": {
            "high_difference": high_diff,
            "low_difference": low_diff,
        },
        "summary_text": summary_text,
        "details_markdown": "\n".join(comparison_lines),
    }

# -----------------------------------------------------------------------------
# 9. BACKWARD-COMPATIBLE PUBLIC INTERFACES
# -----------------------------------------------------------------------------

def get_weather(date_str: str, location: str = "Katra") -> Dict[str, Any]:
    """Returns weather info for a given YYYY-MM-DD date and optional location.
    Guaranteed backwards-compatible with existing callers. Never raises.
    """
    return get_multi_location_weather(query_or_locations=location, target_date_str=date_str)


def get_weather_summary(location: str = "Katra") -> Dict[str, Any]:
    """Returns today's weather summary for Katra, Bhawan, or any pilgrimage location.
    Guaranteed backwards-compatible with existing callers. Never raises.
    """
    today_str = date.today().isoformat()
    return get_weather(today_str, location=location)
