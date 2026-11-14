"""
services/live_data/adapters/__init__.py
Live Data Provider Adapters Package.
"""

from services.live_data.adapters.curated_accommodation_adapter import CuratedAccommodationAdapter
from services.live_data.adapters.curated_contact_adapter import CuratedContactAdapter, VerifiedContactAdapter
from services.live_data.adapters.curated_operational_notices_adapter import CuratedOperationalNoticesAdapter
from services.live_data.adapters.mock_provider import MockTestLiveDataProvider
from services.live_data.adapters.weather_adapter import OpenMeteoWeatherAdapter

__all__ = [
    "CuratedAccommodationAdapter",
    "CuratedContactAdapter",
    "CuratedOperationalNoticesAdapter",
    "MockTestLiveDataProvider",
    "OpenMeteoWeatherAdapter",
    "VerifiedContactAdapter",
]
