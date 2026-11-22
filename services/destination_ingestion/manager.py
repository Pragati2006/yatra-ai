"""
services/destination_ingestion/manager.py
Orchestration layer for J&K destination ingestion, querying, and catalog unification.
"""

import logging
from typing import List, Dict, Any, Optional

import explore_data
from .scraper import DestinationScraper, OFFICIAL_SOURCES
from .storage import DestinationStorage
from .models import DestinationRecord

logger = logging.getLogger(__name__)


class DestinationManager:
    """
    Coordinates web scraping, deduplication, persistent MongoDB storage,
    and unified catalog synthesis for Yatra AI.
    """

    def __init__(self, storage: Optional[DestinationStorage] = None, scraper: Optional[DestinationScraper] = None):
        self.storage = storage or DestinationStorage()
        self.scraper = scraper or DestinationScraper()
        self._memory_cache: Optional[List[Dict[str, Any]]] = None

    def ingest_official_sources(self, force_refresh: bool = False) -> List[DestinationRecord]:
        """Scrapes official government portals, deduplicates, and saves to storage."""
        records = self.scraper.run_full_scrape(force_refresh=force_refresh)
        self.storage.save_destinations(records)
        self._memory_cache = [r.to_dict() for r in records]
        return records

    def get_ingested_destinations(self) -> List[Dict[str, Any]]:
        """Returns all ingested destination records from MongoDB or local storage."""
        if self._memory_cache is None:
            self._memory_cache = self.storage.load_destinations()
        return self._memory_cache

    def get_new_destinations(self) -> List[Dict[str, Any]]:
        """Returns only newly ingested destinations that were not already in the curated catalog."""
        all_dest = self.get_ingested_destinations()
        return [d for d in all_dest if not d.get("is_curated", False)]

    def get_unified_places_catalog(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Combines the baseline curated explore_data.PLACES with newly ingested official destinations.
        When MongoDB Atlas is active, retrieves directly from the 'tourist_attractions' collection.
        When offline, uses local explore_data.PLACES and ingested_destinations.json fallback.
        Preserves null entry_fee and timings.
        """
        import mongo_db

        if mongo_db.is_available() and mongo_db.tourist_attractions is not None:
            try:
                coll = mongo_db.tourist_attractions
                mongo_filter = {}
                if category and category != "All":
                    mongo_filter = {
                        "$or": [
                            {"category": category},
                            {"category_type": category},
                            {"region": category},
                            {"district": category},
                        ]
                    }
                records = list(coll.find(mongo_filter, {"_id": 0}))
                if records:
                    try:
                        from services.destination_ingestion.storage import get_verified_images_map
                        images_map = get_verified_images_map()
                        for r in records:
                            rname = r.get("name")
                            if rname in images_map and not r.get("image_gallery"):
                                img_data = images_map[rname]
                                r["image_url"] = img_data.get("image_url")
                                r["image_gallery"] = img_data.get("image_gallery", [])
                                r["image_verified"] = img_data.get("photo_count", 0) > 0
                                r["image_count"] = img_data.get("photo_count", 0)
                    except Exception:
                        pass
                    return records
            except Exception as exc:
                logger.warning("MongoDB direct catalog query failed, falling back to local: %s", exc)
                mongo_db.mark_offline(exc)

        # Local fallback
        curated_places = explore_data.get_places(category=category)
        curated_names = {p["name"].lower().strip() for p in explore_data.PLACES}

        # Filter new destinations
        new_places = []
        for d in self.get_new_destinations():
            # Check category filter if provided
            if category and category != "All":
                if d.get("category") != category and d.get("region") != category and d.get("district") != category:
                    continue

            # Ensure not in curated
            if d.get("name", "").lower().strip() not in curated_names:
                # Format into explore_data place format
                new_places.append({
                    "name": d["name"],
                    "category": d["category"],
                    "category_type": d.get("category_type", "tourist_attraction"),
                    "district": d.get("district"),
                    "region": d.get("region"),
                    "state": d.get("state", "Jammu and Kashmir"),
                    "latitude": d.get("latitude"),
                    "longitude": d.get("longitude"),
                    "coordinates": d.get("coordinates") or ({"lat": d["latitude"], "lng": d["longitude"]} if d.get("latitude") and d.get("longitude") else None),
                    "coordinates_source": d.get("coordinates_source"),
                    "distance": d.get("distance"),
                    "timings": d.get("timings"),
                    "timings_verified": d.get("timings_verified", False),
                    "entry_fee": d.get("entry_fee"),
                    "entry_fee_verified": d.get("entry_fee_verified", False),
                    "description": d["description"],
                    "historical_background": d.get("historical_background") or "",
                    "source_url": d["source_url"],
                    "source_domain": d.get("source_domain", ""),
                    "verification_status": d.get("verification_status", "OFFICIALLY_VERIFIED"),
                    "provenance": d.get("provenance"),
                    "is_curated": False,
                    "image": d.get("image"),
                    "image_url": d.get("image_url"),
                    "image_gallery": d.get("image_gallery", []),
                    "image_verified": d.get("image_verified", False),
                    "image_count": d.get("image_count", 0),
                    "video_search": d.get("video_search"),
                })

        # Enrich local curated places with verified images if not already attached
        try:
            from services.destination_ingestion.storage import get_verified_images_map
            images_map = get_verified_images_map()
            for cp in curated_places:
                cname = cp.get("name")
                if cname in images_map and not cp.get("image_gallery"):
                    img_data = images_map[cname]
                    cp["image_url"] = img_data.get("image_url")
                    cp["image_gallery"] = img_data.get("image_gallery", [])
                    cp["image_verified"] = img_data.get("photo_count", 0) > 0
                    cp["image_count"] = img_data.get("photo_count", 0)
        except Exception:
            pass

        return curated_places + new_places

    def find_destination(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Finds a destination across both curated and enriched catalogs."""
        if not name_or_query:
            return None
        import mongo_db
        import re

        target = name_or_query.strip()
        if mongo_db.is_available() and mongo_db.tourist_attractions is not None:
            try:
                coll = mongo_db.tourist_attractions
                doc = coll.find_one({"name": {"$regex": f"^{re.escape(target)}$", "$options": "i"}}, {"_id": 0})
                if doc:
                    return doc
            except Exception:
                pass

        # 1. Check curated catalog
        curated = explore_data.get_place_by_name(target)
        if curated:
            return curated

        # 2. Check enriched catalog
        return self.storage.get_destination_by_name(target)


# Global singleton instance
_default_manager = DestinationManager()


def get_destination_manager() -> DestinationManager:
    return _default_manager
