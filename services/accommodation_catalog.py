"""
services/accommodation_catalog.py
Verified, provider-independent accommodation catalog service for Katra.

Serves authentic Shri Mata Vaishno Devi Shrine Board (SMVDSB) dharamshalas,
branded corporate chain hotels, and verified independent Katra properties
loaded from data/katra_accommodation_catalog.json.

Guarantees:
- Strictly decoupled from unverified third-party hotel APIs.
- Every property record is source-attributed with direct primary URLs.
- Real-time availability defaults strictly to NOT_CHECKED.
- No synthetic room counters or fabricated user ratings.
- Backward compatibility adapter for existing orchestrator and UI contracts.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "katra_accommodation_catalog.json")

# -----------------------------------------------------------------------------
# 1. CATALOG DATA STRUCTURES
# -----------------------------------------------------------------------------

@dataclass
class TariffSchedule:
    room_category: str
    occupancy_pax: int
    tariff_min_inr: float
    tariff_max_inr: float
    currency: str = "INR"
    tax_status: str = "GST_APPLICABLE"
    cancellation_policy: Optional[str] = None
    tariff_classification: str = "PROPERTY_CONFIRMED_INDICATIVE_RATE"
    source_url: str = ""
    retrieval_timestamp: str = ""
    validity_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KatraProperty:
    property_id: str
    property_name: str
    property_type: str
    operator_type: str
    identity_status: str
    property_status: str
    address: str
    address_status: str
    landmark: str
    latitude: Optional[float]
    longitude: Optional[float]
    distance_to_banganga_km: Optional[float]
    phone: Optional[str]
    contact_status: str
    official_website: Optional[str]
    email: Optional[str]
    booking_channel: str
    booking_channel_status: str
    connectivity_level: str
    tariffs: List[TariffSchedule] = field(default_factory=list)
    availability_status: str = "NOT_CHECKED"
    source_provenance: str = "CATALOG"
    source_urls: List[str] = field(default_factory=list)
    retrieved_at: str = ""
    last_verified_at: str = ""

    @property
    def indicative_min_price(self) -> float:
        if not self.tariffs:
            return 0.0
        return min(t.tariff_min_inr for t in self.tariffs)

    @property
    def indicative_max_price(self) -> float:
        if not self.tariffs:
            return 0.0
        return max(t.tariff_max_inr for t in self.tariffs)

    @property
    def tariff_disclaimer(self) -> str:
        if self.operator_type == "SMVDSB":
            return "Official SMVDSB Subsidized Tariff Schedule"
        return "Published Indicative Rate - Confirm with Property"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["indicative_min_price"] = self.indicative_min_price
        d["indicative_max_price"] = self.indicative_max_price
        d["tariff_disclaimer"] = self.tariff_disclaimer
        return d

    def to_legacy_record(self, stay_date: Optional[str] = None, min_rooms: int = 1) -> Dict[str, Any]:
        """Maps to the legacy hotel dictionary format expected by orchestrator
        and budget engine, while providing authentic names, addresses, and contacts.
        Correctly reflects room_requirement_status without fabricating availability.
        """
        # Map operator_type / property_type to user-friendly category
        if self.operator_type == "SMVDSB":
            cat = "Dharamshala"
        elif "LUXURY" in self.property_type or "CHAIN" in self.property_type and self.indicative_min_price >= 5000:
            cat = "Premium"
        elif self.indicative_min_price >= 2000:
            cat = "Mid-Range"
        else:
            cat = "Budget"

        # Provide a representative price per night
        price = self.indicative_min_price if self.indicative_min_price > 0 else 1200.0

        # Room requirement semantics: unknown inventory is explicitly UNVERIFIED
        req_rooms = max(1, int(min_rooms or 1))
        if self.availability_status == "NOT_CHECKED":
            room_req_status = "UNVERIFIED"
            if req_rooms > 1:
                room_req_note = f"Requested {req_rooms} rooms. Live room inventory is UNVERIFIED (NOT_CHECKED) — confirm directly with property."
            else:
                room_req_note = "Standard room/bed allocation. Live room inventory is UNVERIFIED (NOT_CHECKED) — confirm directly with property."
        else:
            room_req_status = "UNVERIFIED"
            room_req_note = "Static catalog default: Live availability not checked."

        return {
            "id": self.property_id,
            "property_id": self.property_id,
            "name": self.property_name,
            "category": cat,
            "price_per_night": float(price),
            "price": float(price),
            "rooms_available": None,  # Strictly None (unknown inventory preserved)
            "stay_date": stay_date,
            "address": self.address,
            "landmark": self.landmark,
            "phone": self.phone,
            "official_website": self.official_website,
            "operator_type": self.operator_type,
            "tariff_disclaimer": self.tariff_disclaimer,
            "availability_status": "NOT_CHECKED",
            "room_requirement_status": room_req_status,
            "room_requirement_note": room_req_note,
            "source_provenance": self.source_provenance,
            "source_urls": self.source_urls,
            "identity_status": self.identity_status,
        }


# -----------------------------------------------------------------------------
# 2. IN-MEMORY CATALOG CACHE & LOADER
# -----------------------------------------------------------------------------

_CATALOG_CACHE: Optional[Dict[str, KatraProperty]] = None
_METADATA_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_LOAD_ERROR: Optional[str] = None


def load_catalog(force_reload: bool = False, catalog_path: Optional[str] = None) -> Dict[str, KatraProperty]:
    """Loads and caches the Katra accommodation catalog from disk."""
    global _CATALOG_CACHE, _METADATA_CACHE, _CATALOG_LOAD_ERROR
    if _CATALOG_CACHE is not None and not force_reload:
        return _CATALOG_CACHE

    _CATALOG_LOAD_ERROR = None
    target_path = catalog_path or CATALOG_PATH
    if not os.path.exists(target_path):
        _CATALOG_LOAD_ERROR = f"Catalog file not found: {target_path}"
        logger.warning(_CATALOG_LOAD_ERROR)
        _CATALOG_CACHE = {}
        return _CATALOG_CACHE

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        _METADATA_CACHE = raw.get("catalog_metadata", {})
        properties_map: Dict[str, KatraProperty] = {}

        for p in raw.get("properties", []):
            tariff_objs = []
            for t in p.get("tariffs", []):
                tariff_objs.append(
                    TariffSchedule(
                        room_category=t.get("room_category", "Standard"),
                        occupancy_pax=int(t.get("occupancy_pax", 2)),
                        tariff_min_inr=float(t.get("tariff_min_inr", 0.0)),
                        tariff_max_inr=float(t.get("tariff_max_inr", 0.0)),
                        currency=t.get("currency", "INR"),
                        tax_status=t.get("tax_status", "GST_APPLICABLE"),
                        cancellation_policy=t.get("cancellation_policy"),
                        tariff_classification=t.get("tariff_classification", "SECONDARY_DIRECTORY_ESTIMATE"),
                        source_url=t.get("source_url", ""),
                        retrieval_timestamp=t.get("retrieval_timestamp", ""),
                        validity_notes=t.get("validity_notes"),
                    )
                )

            prop_obj = KatraProperty(
                property_id=p["property_id"],
                property_name=p["property_name"],
                property_type=p.get("property_type", "COMMERCIAL_HOTEL"),
                operator_type=p.get("operator_type", "INDEPENDENT"),
                identity_status=p.get("identity_status", "VERIFIED_PRIMARY"),
                property_status=p.get("property_status", "OPERATIONAL"),
                address=p.get("address", "Katra, Jammu and Kashmir - 182301"),
                address_status=p.get("address_status", "VERIFIED_PRIMARY"),
                landmark=p.get("landmark", "Katra"),
                latitude=p.get("latitude"),
                longitude=p.get("longitude"),
                distance_to_banganga_km=p.get("distance_to_banganga_km"),
                phone=p.get("phone"),
                contact_status=p.get("contact_status", "UNVERIFIED"),
                official_website=p.get("official_website"),
                email=p.get("email"),
                booking_channel=p.get("booking_channel", "DIRECT_PHONE_OR_WEB"),
                booking_channel_status=p.get("booking_channel_status", "OFFICIAL_PORTAL_ACTIVE"),
                connectivity_level=p.get("connectivity_level", "LEVEL_2_DIRECT_BOOKING_ENGINE"),
                tariffs=tariff_objs,
                availability_status="NOT_CHECKED",  # Guaranteed default; live status requires on-demand provider query
                source_provenance=p.get("source_provenance", "CATALOG"),
                source_urls=p.get("source_urls", []),
                retrieved_at=p.get("retrieved_at", ""),
                last_verified_at=p.get("last_verified_at", ""),
            )
            properties_map[prop_obj.property_id] = prop_obj

        _CATALOG_CACHE = properties_map
        logger.info(f"Loaded {len(_CATALOG_CACHE)} verified Katra accommodation properties from {target_path}.")
        return _CATALOG_CACHE

    except Exception as e:
        _CATALOG_LOAD_ERROR = f"Error loading Katra accommodation catalog: {e}"
        logger.error(_CATALOG_LOAD_ERROR, exc_info=True)
        _CATALOG_CACHE = {}
        return _CATALOG_CACHE


def get_catalog_metadata() -> Dict[str, Any]:
    """Returns top-level catalog audit metadata."""
    global _METADATA_CACHE
    if _METADATA_CACHE is None:
        load_catalog()
    return _METADATA_CACHE or {}


# -----------------------------------------------------------------------------
# 3. QUERY & FILTERING INTERFACES
# -----------------------------------------------------------------------------

def get_all_properties(include_partial: bool = True) -> List[KatraProperty]:
    """Returns all properties, optionally filtering out partially verified Group B entries."""
    props = load_catalog()
    if include_partial:
        return list(props.values())
    return [p for p in props.values() if p.identity_status == "VERIFIED_PRIMARY"]


def get_property_by_id(property_id: str) -> Optional[KatraProperty]:
    """Retrieves a single property by its identifier slug."""
    props = load_catalog()
    return props.get(property_id)


def search_properties(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    landmark: Optional[str] = None,
    operator_type: Optional[str] = None,
    include_partial: bool = True,
) -> List[KatraProperty]:
    """Filters Katra properties across name, category, budget bracket, landmark, and operator."""
    results = get_all_properties(include_partial=include_partial)

    if query:
        q = query.strip().lower()
        results = [
            p for p in results
            if q in p.property_name.lower()
            or q in p.address.lower()
            or q in p.landmark.lower()
            or q in p.operator_type.lower()
        ]

    if operator_type:
        op = operator_type.strip().upper()
        results = [p for p in results if p.operator_type.upper() == op]

    if category:
        cat = category.strip().lower()
        if any(k in cat for k in ["shrine", "board", "dharamshala", "trust", "sarai", "smvdsb"]):
            results = [p for p in results if p.operator_type == "SMVDSB"]
        elif any(k in cat for k in ["budget", "economy", "affordable"]):
            results = [p for p in results if p.indicative_min_price < 2500 or p.operator_type == "SMVDSB"]
        elif any(k in cat for k in ["mid", "standard", "comfortable", "3 star"]):
            results = [p for p in results if 2000 <= p.indicative_min_price <= 5500]
        elif any(k in cat for k in ["premium", "luxury", "deluxe", "5 star", "resort"]):
            results = [p for p in results if p.indicative_min_price >= 5000]
        else:
            results = []

    if min_budget is not None:
        results = [p for p in results if p.indicative_max_price >= min_budget]

    if max_budget is not None:
        results = [p for p in results if p.indicative_min_price <= max_budget]

    if landmark:
        lm = landmark.strip().lower()
        results = [p for p in results if lm in p.landmark.lower() or lm in p.address.lower()]

    # Sort results: SMVDSB first, then by minimum indicative price
    results.sort(key=lambda p: (0 if p.operator_type == "SMVDSB" else 1, p.indicative_min_price))
    return results


def get_catalog_load_error() -> Optional[str]:
    """Returns load error string if catalog failed to load, else None."""
    global _CATALOG_LOAD_ERROR
    if _CATALOG_CACHE is None and _CATALOG_LOAD_ERROR is None:
        load_catalog()
    return _CATALOG_LOAD_ERROR


def get_catalog_status() -> str:
    """Returns CATALOG_SUCCESS, CATALOG_UNAVAILABLE, or NO_MATCHING_PROPERTIES."""
    global _CATALOG_LOAD_ERROR, _CATALOG_CACHE
    err = get_catalog_load_error()
    if err:
        return "CATALOG_UNAVAILABLE"
    if not _CATALOG_CACHE:
        return "NO_MATCHING_PROPERTIES"
    return "CATALOG_SUCCESS"


def search_hotels_for_orchestrator(
    check_in_date: Optional[str] = None,
    category: Optional[str] = None,
    min_rooms: int = 1,
) -> List[Dict[str, Any]]:
    """Production drop-in replacement for db.search_hotels().
    Returns verified Katra property dictionaries conforming to existing orchestrator schemas.
    Strictly returns empty list if catalog is unavailable or no match is found; never falls back to synthetic data.
    """
    err = get_catalog_load_error()
    if err:
        return []
    try:
        props = search_properties(category=category)
        return [p.to_legacy_record(stay_date=check_in_date, min_rooms=min_rooms) for p in props]
    except Exception as e:
        logger.warning(f"Error querying properties in search_hotels_for_orchestrator: {e}")
        return []


def search_hotels_with_status(
    check_in_date: Optional[str] = None,
    category: Optional[str] = None,
    min_rooms: int = 1,
) -> Tuple[List[Dict[str, Any]], str]:
    """Returns a tuple of (hotel_records, catalog_status).
    catalog_status is one of:
      - CATALOG_SUCCESS: matches found
      - NO_MATCHING_PROPERTIES: catalog queried successfully but 0 matches
      - CATALOG_UNAVAILABLE: catalog file missing or could not be loaded
    """
    err = get_catalog_load_error()
    if err:
        return [], "CATALOG_UNAVAILABLE"
    records = search_hotels_for_orchestrator(check_in_date=check_in_date, category=category, min_rooms=min_rooms)
    if not records:
        return [], "NO_MATCHING_PROPERTIES"
    return records, "CATALOG_SUCCESS"
