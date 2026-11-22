"""
services/destination_ingestion/scraper.py
Permitted Web Scraper and Factual Attribute Extractor for Official J&K District Tourism Portals.

Adheres strictly to:
- NIC Government Portal Website Policies & Indian Copyright Act (Section 52(1))
- Extracts factual attributes (names, coordinates, districts, categories, source URLs)
- Generates concise original descriptions (never copies copyrighted text)
- Excludes photographs per copyright conditions
- Incorporates caching, rate-limiting, and error resilience
"""

import hashlib
import json
import logging
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup

from .models import DestinationRecord, ProvenanceInfo
from .deduplicator import resolve_deduplication

logger = logging.getLogger(__name__)

# Official source registry
OFFICIAL_SOURCES = [
    {
        "district": "Jammu",
        "region": "Jammu",
        "index_url": "https://jammu.nic.in/tourism/tourist-places/",
        "domain": "jammu.nic.in",
        "authority": "District Administration Jammu, National Informatics Centre",
    },
    {
        "district": "Srinagar",
        "region": "Kashmir",
        "index_url": "https://srinagar.nic.in/tourist-places/",
        "domain": "srinagar.nic.in",
        "authority": "District Administration Srinagar, National Informatics Centre",
    },
    {
        "district": "Kishtwar",
        "region": "Jammu",
        "index_url": "https://kishtwar.nic.in/tourist-places/",
        "domain": "kishtwar.nic.in",
        "authority": "District Administration Kishtwar, National Informatics Centre",
    },
    {
        "district": "Kashmir Region",
        "region": "Kashmir",
        "index_url": "https://www.kashmirtourismofficial.com/",
        "domain": "www.kashmirtourismofficial.com",
        "authority": "Directorate of Tourism Kashmir, Government of J&K",
        "is_portal": True,
    }
]

# Standard curated mapping of factual overviews for officially scraped destinations
# Written in original prose based on verified public facts from NIC portals
FACTUAL_DESCRIPTIONS = {
    "akhnoor fort": {
        "category": "Historic Fort",
        "category_type": "historical_site",
        "description": "An imposing two-tiered historical fort perched on a cliff overlooking the Chenab River, celebrated for ancient Harappan excavations and its sacred riverfront coronation ghat.",
        "historical_background": "Initiated in 1762 by Raja Tegh Singh and completed in 1802 by Raja Alam Singh, this ASI-protected monument marks the historic coronation site of Maharaja Gulab Singh at Jia Pota Ghat.",
    },
    "mubarak mandi palace": {
        "category": "Heritage Palace",
        "category_type": "historical_site",
        "description": "The historic royal residence of the Dogra Maharajas overlooking the Tawi River, showcasing a grand synthesis of Rajasthani, Mughal, and European Baroque architecture.",
        "historical_background": "Built over several centuries by the Dogra dynasty as their seat of governance until 1925, the palace complex houses historic courtyards, the Pink Hall, and rare Pahari miniature paintings.",
    },
    "badamwari": {
        "category": "Historic Garden",
        "category_type": "nature_destination",
        "description": "A sprawling historic almond garden at the foot of Hari Parbat, renowned for its soft white and pink blossoms heralding the arrival of spring in the Kashmir Valley.",
        "historical_background": "Dating back to the 14th century during the Sultanate period and revived under the Dogra era, Badamwari features traditional Kashmiri stone domes and watercourses.",
    },
    "botanical garden": {
        "category": "Botanical Garden",
        "category_type": "nature_destination",
        "description": "A vast 80-hectare botanical sanctuary nestled between Dal Lake and the Zabarwan hills, featuring rich collections of temperate flora and ornamental lakes.",
        "historical_background": "Founded in 1969 to preserve regional Himalayan plant biodiversity and provide a quiet contemplative green space for visitors and botanical research.",
    },
    "chashma shahi": {
        "category": "Mughal Garden",
        "category_type": "nature_destination",
        "description": "A charming terraced Mughal garden arranged around a pure freshwater mountain spring, offering panoramic vistas across Dal Lake and the Zabarwan range.",
        "historical_background": "Commissioned in 1632 CE by Mughal governor Ali Mardan Khan as a gift for Emperor Shah Jahan's elder son Prince Dara Shikoh, renowned for its therapeutic spring water.",
    },
    "dachigam national park": {
        "category": "National Park",
        "category_type": "nature_destination",
        "description": "A pristine high-altitude wildlife sanctuary spanning Himalayan temperate forests, recognized as the last refuge of the critically endangered Hangul (Kashmir stag).",
        "historical_background": "Originally created as a protected royal game preserve by the Maharaja of Jammu and Kashmir to supply clean drinking water to Srinagar, designated a National Park in 1981.",
    },
    "hari parbat fort": {
        "category": "Historic Fort",
        "category_type": "historical_site",
        "description": "A historic hilltop fortress dominating Srinagar's skyline, surrounded by sites of deep religious significance spanning Hindu, Muslim, and Sikh traditions.",
        "historical_background": "First fortified with a surrounding stone rampart by Emperor Akbar in 1590 CE, the crowning bastion was completed in 1808 by Afghan governor Atta Mohammad Khan.",
    },
    "harwan garden": {
        "category": "Ancient Heritage & Garden",
        "category_type": "historical_site",
        "description": "A peaceful terraced garden situated beside an ancient Buddhist excavation site at the base of the Mahadev mountain ridge, fed by alpine mountain springs.",
        "historical_background": "Overlooks the ancient Harwan Buddhist monastery where the 4th Buddhist Council under Kushan Emperor Kanishka is believed to have convened around the 1st-2nd century CE.",
    },
    "nigeen lake": {
        "category": "Lake & Waterways",
        "category_type": "nature_destination",
        "description": "A peaceful, willow-fringed freshwater lake adjacent to Dal Lake, favored for its clear waters, houseboats, and serene shikara rides.",
        "historical_background": "Historically regarded as the 'jewel in the ring' of Srinagar's water bodies, Nigeen was a traditional retreat for travelers seeking tranquility away from the central urban bustle.",
    },
    "pari mahal": {
        "category": "Heritage Garden",
        "category_type": "historical_site",
        "description": "An enchanting seven-terraced monument and garden situated high above Dal Lake on the Zabarwan spur, famous for classical Islamic architecture and sunset views.",
        "historical_background": "Constructed in the mid-17th century by Mughal Prince Dara Shikoh to serve as an astronomical observatory and center for Sufi and Vedic philosophical discourse.",
    },
    "tulip garden": {
        "category": "Botanical Garden",
        "category_type": "nature_destination",
        "description": "Asia's largest tulip expanse situated at the foothills of the Zabarwan range, presenting vibrant multi-colored blooms each spring overlooking Dal Lake.",
        "historical_background": "Established in 2007 by the Jammu and Kashmir government to boost valley floriculture, cultivating over 1.5 million tulips of multiple rare varieties.",
    },
    "chowgan": {
        "category": "Highland Meadow",
        "category_type": "nature_destination",
        "description": "A sprawling natural highland meadow in the heart of Kishtwar town, surrounded by ancient deodar pines and serving as the focal point for community festivals and sports.",
        "historical_background": "Centuries old, the Chaugan ground served as the central assembly field for the ancient rajas of Kishtwar and remains an indispensable civic space for cultural celebrations.",
    },
    "kishtwar national park": {
        "category": "National Park",
        "category_type": "nature_destination",
        "description": "An expansive high-altitude alpine national park characterized by rugged gorges, glaciers, and endangered Himalayan wildlife including the snow leopard and musk deer.",
        "historical_background": "Notified in 1981 to conserve the fragile high-altitude ecosystem and biodiversity of the upper Catchment of the Chenab River basin in the Greater Himalayas.",
    },
    "machail mata": {
        "category": "Pilgrimage / Temple",
        "category_type": "religious_site",
        "description": "A sacred high-altitude Himalayan shrine dedicated to Goddess Chandi Mata, set in the Paddar valley and visited by thousands during the annual Machail Yatra.",
        "historical_background": "Revered for centuries across the Chenab Valley, the pilgrimage was popularized in the 1980s by Thakur Kulveer Singh, transforming the remote mountain hamlet into a major pilgrimage center.",
    },
    "sinthan top": {
        "category": "High-Altitude Pass",
        "category_type": "nature_destination",
        "description": "A dramatic 12,300-foot mountain pass offering 360-degree snow-capped Himalayan panoramas along the scenic highway connecting the Kashmir Valley with Kishtwar.",
        "historical_background": "Historically an ancient trekking route across the Pir Panjal, modern infrastructure transformed the pass into a key alpine corridor connecting Jammu's Chenab basin with southern Kashmir.",
    }
}


class DestinationScraper:
    """
    Polite and legally compliant scraper for official J&K government tourism portals.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        rate_limit_delay: float = 0.5,
        cache_ttl_seconds: int = 86400,
        user_agent: str = "YatraAI-DestinationIngestion/1.0 (+https://github.com/yatra-ai/destinations)"
    ):
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl_seconds = cache_ttl_seconds
        self.user_agent = user_agent
        self.last_request_time = 0.0

        if cache_dir is None:
            self.cache_dir = Path(__file__).resolve().parent.parent.parent / "scratch" / "destination_cache"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def fetch_url(self, url: str, force_refresh: bool = False) -> Optional[str]:
        """Fetches page content with polite rate limiting and file caching."""
        cache_path = self._get_cache_path(url)
        if not force_refresh and cache_path.exists():
            try:
                mtime = cache_path.stat().st_mtime
                if (time.time() - mtime) < self.cache_ttl_seconds:
                    return cache_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.debug("Failed reading cache for %s: %s", url, e)

        # Rate limiting delay
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12, context=self.ssl_ctx) as res:
                self.last_request_time = time.time()
                if res.status != 200:
                    logger.warning("HTTP status %s for %s", res.status, url)
                    return None
                html = res.read().decode("utf-8", errors="ignore")
                try:
                    cache_path.write_text(html, encoding="utf-8")
                except Exception as e:
                    logger.debug("Failed saving cache for %s: %s", url, e)
                return html
        except Exception as exc:
            logger.warning("Network/HTTP error fetching %s: %s", url, exc)
            return None

    def discover_destination_urls(self, source_info: Dict[str, Any]) -> List[str]:
        """Discovers canonical tourist place URLs from an index page."""
        index_url = source_info["index_url"]
        html = self.fetch_url(index_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        discovered = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Must be a tourist-place link on the official domain
            if "/tourist-place/" in href and not any(k in href for k in ["facebook.com", "x.com", "twitter.com", "sharer"]):
                # Clean trailing parameters and ensure standard trailing slash
                cleaned = href.split("?")[0].rstrip("/") + "/"
                if cleaned.startswith("http"):
                    discovered.add(cleaned)
                elif cleaned.startswith("/"):
                    discovered.add(f"https://{source_info['domain']}{cleaned}")

        return sorted(list(discovered))

    def parse_destination_page(
        self,
        url: str,
        source_info: Dict[str, Any]
    ) -> Optional[DestinationRecord]:
        """
        Parses an official district tourist place page and extracts factual attributes.
        Composes original concise descriptions to ensure full copyright compliance.
        """
        html = self.fetch_url(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            return None

        # 1. Destination Name
        h1 = main.find("h1") or main.find("h2")
        name = h1.get_text(strip=True) if h1 else None
        if not name or len(name) < 2:
            return None

        # Clean name artifacts (e.g. trailing "Jammu" if present in title)
        name_clean = re.sub(r"\s+", " ", name).strip()

        # 2. Extract Coordinates from Google Maps Direction link
        coords = None
        coords_source = None
        for a in main.find_all("a", href=True):
            href = a["href"]
            match = re.search(r"maps/dir//([0-9\.\-]+),([0-9\.\-]+)", href)
            if match:
                try:
                    lat = round(float(match.group(1)), 6)
                    lon = round(float(match.group(2)), 6)
                    coords = (lat, lon)
                    coords_source = f"{source_info['authority']} official map direction"
                    break
                except ValueError:
                    pass

        # 3. Category from .show-category or metadata
        official_category = "Not specified"
        cat_span = soup.find("div", class_="show-category")
        if cat_span and cat_span.find("span"):
            official_category = cat_span.find("span").get_text(strip=True)

        # 4. Deduplication Resolution against Curated Catalog
        is_dup, dup_of, curated_place = resolve_deduplication(name_clean, url)

        # Generate unique ID
        slug = re.sub(r"[^a-z0-9]+", "-", name_clean.lower()).strip("-")
        dest_id = f"dest-{slug}"

        # 5. Formulate original concise description & category mapping
        name_key = name_clean.lower()
        factual = FACTUAL_DESCRIPTIONS.get(name_key)
        if not factual:
            # Fallback search by key fragment
            for k, v in FACTUAL_DESCRIPTIONS.items():
                if k in name_key or name_key in k:
                    factual = v
                    break

        if factual:
            category = factual["category"]
            category_type = factual["category_type"]
            description = factual["description"]
            historical_background = factual["historical_background"]
        elif curated_place:
            category = curated_place.get("category", official_category)
            category_type = curated_place.get("category_type", "historical_site")
            description = curated_place.get("description", f"Notable destination in {source_info['district']}.")
            historical_background = curated_place.get("historical_background")
        else:
            category = official_category if official_category != "Not specified" else "Tourist Destination"
            category_type = "tourist_attraction"
            description = f"Prominent scenic and cultural destination in District {source_info['district']} documented by the district administration."
            historical_background = f"Maintained and preserved as an official destination of interest under District {source_info['district']} administration."

        # Verification Status and Curated Protection
        if is_dup:
            verification_status = "CURATED_PRESERVED"
            is_curated = True
        else:
            verification_status = "OFFICIALLY_VERIFIED"
            is_curated = False

        # Build Provenance metadata
        provenance = ProvenanceInfo(
            authority=source_info["authority"],
            source_url=url,
            source_domain=source_info["domain"],
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        record = DestinationRecord(
            id=dest_id,
            name=name_clean,
            district=source_info["district"],
            region=source_info["region"],
            state="Jammu and Kashmir",
            category=category,
            category_type=category_type,
            latitude=coords[0] if coords else None,
            longitude=coords[1] if coords else None,
            coordinates_source=coords_source,
            distance=None,  # Not invented; preserved as null if not officially stated
            timings=None,  # Not invented; preserved as null if not officially stated
            timings_verified=False,
            entry_fee=None,  # Not invented; preserved as null if not officially stated
            entry_fee_verified=False,
            description=description,
            historical_background=historical_background,
            source_url=url,
            source_domain=source_info["domain"],
            verification_status=verification_status,
            provenance=provenance,
            is_curated=is_curated,
            duplicate_of=dup_of,
            image=None,  # Photographs omitted per copyright compliance
            image_notice="Photographs omitted per copyright compliance policy",
            video_search=f"https://www.youtube.com/results?search_query={urllib.parse.quote(name_clean + ' ' + source_info['district'])}",
        )

        return record

    def run_full_scrape(
        self,
        sources: Optional[List[Dict[str, Any]]] = None,
        force_refresh: bool = False
    ) -> List[DestinationRecord]:
        """Executes polite scraping across all configured official sources."""
        target_sources = sources or OFFICIAL_SOURCES
        all_records = []
        seen_urls = set()

        for src in target_sources:
            if src.get("is_portal"):
                continue  # Skip pure portal aggregators
            logger.info("Scanning official source: %s (%s)", src["district"], src["index_url"])
            urls = self.discover_destination_urls(src)
            for u in urls:
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                record = self.parse_destination_page(u, src)
                if record:
                    all_records.append(record)

        return all_records
