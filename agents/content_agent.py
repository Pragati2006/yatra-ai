"""
agents/content_agent.py
Owns "enrichment" content for places: historical background and video
links. Thin wrapper over explore_data.py's static, researched dataset -
kept as its own agent because it's a distinct responsibility (content
lookup) from transport/darshan/hotel search or itinerary assembly.
"""

import explore_data

try:
    from services.destination_ingestion.manager import get_destination_manager
    _dest_manager = get_destination_manager()
except Exception:
    _dest_manager = None


def get_history(place_name):
    place = get_enriched_place(place_name)
    if not place:
        return None
    return place.get("historical_background")


def get_video_link(place_name):
    place = get_enriched_place(place_name)
    if not place:
        return None
    return place.get("video_search")


def get_enriched_place(place_name):
    """Returns the full place dict (description, history, video link, etc.)."""
    place = explore_data.get_place_by_name(place_name)
    if place:
        return place
    if _dest_manager:
        try:
            return _dest_manager.find_destination(place_name)
        except Exception:
            pass
    return None


def get_all_places_enriched(category=None):
    if _dest_manager:
        try:
            return _dest_manager.get_unified_places_catalog(category)
        except Exception:
            pass
    return explore_data.get_places(category)
