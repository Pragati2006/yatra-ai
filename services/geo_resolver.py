"""
services/geo_resolver.py
Universal Indian Geographic Place & Transport Hub Resolution Engine for Yatra AI.

Phase 14.2 Core Component:
- Resolves any origin location in India: Metros, Tier-2/3 cities, small towns,
  villages, district headquarters, and remote settlements across all states and UTs.
- Extracts sub-location/village semantics (e.g. "a small village near Mandi" -> base town Mandi, HP).
- Identifies strategic nearby transport hubs:
  * Nearest operational railway station (with station code and connectivity tier).
  * Nearest intercity bus terminal.
  * Nearest commercial airport.
  * Primary connecting gateway hub towards Katra / Jammu.
- Distinguishes direct road neighbours (Reasi, Udhampur) from regional corridors (Kangra, Punjab, Delhi).
- Detects ambiguous place names (e.g., Bilaspur in HP vs CG) and generates polite clarification prompts.
- Combines an extensive in-memory curated Indian geography registry with an offline-resilient,
  rate-limited Nominatim (OpenStreetMap) fallback cached via utils.cache_manager.
- Guarantees 100% fail-safe operation: NEVER throws unhandled exceptions, NEVER abruptly rejects an origin.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ResolvedLocation:
    """Structured resolution of a user-supplied Indian origin."""
    raw_input: str
    clean_name: str
    base_town: str
    district: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    is_village_or_settlement: bool = False
    is_ambiguous: bool = False
    ambiguity_candidates: List[Dict[str, str]] = field(default_factory=list)
    is_invalid: bool = False
    nearest_railway_station: Optional[Dict[str, Any]] = None
    nearest_bus_terminal: Optional[Dict[str, Any]] = None
    nearest_airport: Optional[Dict[str, Any]] = None
    primary_gateway_hub: str = "New Delhi"
    corridor_type: str = "NORTHERN_CONNECTING"
    approx_road_distance_to_katra_km: Optional[int] = None
    resolution_source: str = "curated_geographic_registry"
    confidence: float = 1.0
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Extensive Curated Indian Geographic & Transport Hub Knowledge Base
# =============================================================================

# Comprehensive registry of Indian towns, districts, regional centers, and gateway corridors
INDIAN_GEO_REGISTRY: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Jammu & Kashmir (Local & Regional Direct Corridors)
    # -------------------------------------------------------------------------
    "katra": {
        "name": "Katra",
        "district": "Reasi",
        "state": "Jammu & Kashmir",
        "railway": {"code": "SVDK", "name": "Shri Mata Vaishno Devi Katra", "dist_km": 0, "tier": "TERMINAL"},
        "bus": {"name": "Katra Central Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Civil Enclave", "dist_km": 50},
        "gateway": "Katra",
        "corridor": "DESTINATION_BASE",
        "dist_to_katra": 0,
        "notes": "Base camp for holy Bhawan trek.",
    },
    "reasi": {
        "name": "Reasi",
        "district": "Reasi",
        "state": "Jammu & Kashmir",
        "railway": {"code": "SVDK", "name": "Shri Mata Vaishno Devi Katra", "dist_km": 28, "tier": "MAJOR"},
        "bus": {"name": "Reasi Main Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 72},
        "gateway": "Katra",
        "corridor": "DIRECT_ROAD_NEIGHBOUR",
        "dist_to_katra": 28,
        "notes": "Direct adjacent district headquarter; 45 mins by local feeder bus / shared cab on Reasi-Katra road.",
    },
    "udhampur": {
        "name": "Udhampur",
        "district": "Udhampur",
        "state": "Jammu & Kashmir",
        "railway": {"code": "UHP", "name": "Udhampur Railway Station", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Udhampur Main Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 65},
        "gateway": "Udhampur / Katra",
        "corridor": "DIRECT_ROAD_NEIGHBOUR",
        "dist_to_katra": 42,
        "notes": "Adjacent hub; 1 hour by frequent local bus or direct DMU shuttle train to Katra.",
    },
    "jammu": {
        "name": "Jammu",
        "district": "Jammu",
        "state": "Jammu & Kashmir",
        "railway": {"code": "JAT", "name": "Jammu Tawi", "dist_km": 0, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Jammu General Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Civil Enclave", "dist_km": 6},
        "gateway": "Jammu",
        "corridor": "PRIMARY_GATEWAY",
        "dist_to_katra": 50,
        "notes": "Primary multi-modal gateway to Katra; 1.5h by prepaid taxi or frequent JKRTC buses.",
    },
    "samba": {
        "name": "Samba",
        "district": "Samba",
        "state": "Jammu & Kashmir",
        "railway": {"code": "SMBX", "name": "Samba Railway Station", "dist_km": 3, "tier": "SECONDARY"},
        "bus": {"name": "Samba Bus Stand (NH44)", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 38},
        "gateway": "Jammu",
        "corridor": "JAMMU_CORRIDOR",
        "dist_to_katra": 88,
        "notes": "Located on NH44 south of Jammu; direct buses to Jammu / Katra.",
    },
    "kathua": {
        "name": "Kathua",
        "district": "Kathua",
        "state": "Jammu & Kashmir",
        "railway": {"code": "KTHU", "name": "Kathua Railway Station", "dist_km": 4, "tier": "MAJOR"},
        "bus": {"name": "Kathua Main Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 80},
        "gateway": "Jammu / Pathankot",
        "corridor": "JAMMU_CORRIDOR",
        "dist_to_katra": 130,
        "notes": "Border district of J&K; connected via NH44 to Jammu and Pathankot.",
    },
    "ramban": {
        "name": "Ramban",
        "district": "Ramban",
        "state": "Jammu & Kashmir",
        "railway": {"code": "UHP", "name": "Udhampur", "dist_km": 85, "tier": "MAJOR"},
        "bus": {"name": "Ramban Bus Stand (NH44)", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 140},
        "gateway": "Udhampur",
        "corridor": "MOUNTAIN_ROAD_CORRIDOR",
        "dist_to_katra": 115,
        "notes": "Located on Jammu-Srinagar NH44; shared cabs and state buses run daily to Udhampur and Katra.",
    },
    "doda": {
        "name": "Doda",
        "district": "Doda",
        "state": "Jammu & Kashmir",
        "railway": {"code": "UHP", "name": "Udhampur", "dist_km": 110, "tier": "MAJOR"},
        "bus": {"name": "Doda Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 165},
        "gateway": "Udhampur",
        "corridor": "MOUNTAIN_ROAD_CORRIDOR",
        "dist_to_katra": 145,
        "notes": "Chenab valley district; connected via Batote (NH244) to Udhampur and Katra.",
    },
    "kishtwar": {
        "name": "Kishtwar",
        "district": "Kishtwar",
        "state": "Jammu & Kashmir",
        "railway": {"code": "UHP", "name": "Udhampur", "dist_km": 160, "tier": "MAJOR"},
        "bus": {"name": "Kishtwar Main Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 215},
        "gateway": "Udhampur",
        "corridor": "MOUNTAIN_ROAD_CORRIDOR",
        "dist_to_katra": 195,
        "notes": "Eastern mountainous district; accessible via Batote and NH244 to Udhampur / Katra.",
    },
    "rajouri": {
        "name": "Rajouri",
        "district": "Rajouri",
        "state": "Jammu & Kashmir",
        "railway": {"code": "JAT", "name": "Jammu Tawi", "dist_km": 145, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Rajouri Main Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 150},
        "gateway": "Jammu",
        "corridor": "PIR_PANJAL_CORRIDOR",
        "dist_to_katra": 140,
        "notes": "Connected via NH144A through Akhnoor/Reasi or via Jammu to Katra.",
    },
    "poonch": {
        "name": "Poonch",
        "district": "Poonch",
        "state": "Jammu & Kashmir",
        "railway": {"code": "JAT", "name": "Jammu Tawi", "dist_km": 235, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Poonch Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 240},
        "gateway": "Jammu / Rajouri",
        "corridor": "PIR_PANJAL_CORRIDOR",
        "dist_to_katra": 210,
        "notes": "Connected via Rajouri along NH144A towards Jammu and Katra.",
    },
    "srinagar": {
        "name": "Srinagar",
        "district": "Srinagar",
        "state": "Jammu & Kashmir",
        "railway": {"code": "SINA", "name": "Srinagar (Banihal line)", "dist_km": 5, "tier": "REGIONAL"},
        "bus": {"name": "TRC / Batamaloo Bus Stand", "dist_km": 0},
        "airport": {"code": "SXR", "name": "Sheikh ul-Alam Airport", "dist_km": 12},
        "gateway": "Banihal / Jammu",
        "corridor": "KASHMIR_CORRIDOR",
        "dist_to_katra": 230,
        "notes": "Connected via NH44 through Banihal-Qazigund tunnel or regional train to Banihal + road.",
    },
    "anantnag": {
        "name": "Anantnag",
        "district": "Anantnag",
        "state": "Jammu & Kashmir",
        "railway": {"code": "ANT", "name": "Anantnag Railway Station", "dist_km": 3, "tier": "REGIONAL"},
        "bus": {"name": "Anantnag Bus Stand", "dist_km": 0},
        "airport": {"code": "SXR", "name": "Srinagar Airport", "dist_km": 55},
        "gateway": "Banihal / Udhampur",
        "corridor": "KASHMIR_CORRIDOR",
        "dist_to_katra": 195,
        "notes": "South Kashmir center; convenient road/rail link through Banihal tunnel towards Udhampur/Katra.",
    },

    # -------------------------------------------------------------------------
    # Himachal Pradesh (Direct Neighboring State & Hill Towns)
    # -------------------------------------------------------------------------
    "palampur": {
        "name": "Palampur",
        "district": "Kangra",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 115, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Palampur Main Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Kangra / Gaggal Airport", "dist_km": 38},
        "gateway": "Pathankot",
        "corridor": "KANGRA_VALLEY_CORRIDOR",
        "dist_to_katra": 225,
        "notes": "Scenic tea-capital in Kangra Valley; travel via Kangra to Pathankot for direct trains to Katra.",
    },
    "mandi": {
        "name": "Mandi",
        "district": "Mandi",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 210, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Mandi ISBT", "dist_km": 0},
        "airport": {"code": "KUU", "name": "Kullu Bhuntar Airport", "dist_km": 60},
        "gateway": "Pathankot / Kiratpur / Chandigarh",
        "corridor": "HIMACHAL_CENTRAL_CORRIDOR",
        "dist_to_katra": 290,
        "notes": "Major central Himachal hub on NH154/NH21; road to Pathankot or Kiratpur Sahib for direct trains.",
    },
    "dharamshala": {
        "name": "Dharamshala",
        "district": "Kangra",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 85, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Dharamshala Main Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Gaggal Kangra Airport", "dist_km": 14},
        "gateway": "Pathankot",
        "corridor": "KANGRA_VALLEY_CORRIDOR",
        "dist_to_katra": 195,
        "notes": "Connected by road via Gaggal to Pathankot (2.5h) for direct express trains to Katra.",
    },
    "kangra": {
        "name": "Kangra",
        "district": "Kangra",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 75, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Kangra Main Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Gaggal Airport", "dist_km": 8},
        "gateway": "Pathankot",
        "corridor": "KANGRA_VALLEY_CORRIDOR",
        "dist_to_katra": 185,
        "notes": "Direct road to Pathankot on NH154; frequent HRTC express buses connect to Jammu.",
    },
    "una": {
        "name": "Una",
        "district": "Una",
        "state": "Himachal Pradesh",
        "railway": {"code": "UHL", "name": "Una Himachal Railway Station", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Una Old / New Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 125},
        "gateway": "Una / Jalandhar / Pathankot",
        "corridor": "HIMACHAL_FOOTHILLS_CORRIDOR",
        "dist_to_katra": 250,
        "notes": "Has its own broad gauge railhead (Vande Bharat terminal from Delhi); road connects via Hoshiarpur to Jalandhar/Pathankot.",
    },
    "chamba": {
        "name": "Chamba",
        "district": "Chamba",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTK", "name": "Pathankot Railway Station", "dist_km": 120, "tier": "MAJOR"},
        "bus": {"name": "Chamba Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Gaggal Airport", "dist_km": 130},
        "gateway": "Pathankot",
        "corridor": "RAVI_VALLEY_CORRIDOR",
        "dist_to_katra": 220,
        "notes": "Travels along Ravi valley road via Banikhet/Dunera to Pathankot for onward Katra trains.",
    },
    "dalhousie": {
        "name": "Dalhousie",
        "district": "Chamba",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 80, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Dalhousie Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Gaggal Kangra Airport", "dist_km": 105},
        "gateway": "Pathankot",
        "corridor": "RAVI_VALLEY_CORRIDOR",
        "dist_to_katra": 190,
        "notes": "Direct scenic hill road to Pathankot (2.5 hours); direct trains and buses from Pathankot to Katra.",
    },
    "shimla": {
        "name": "Shimla",
        "district": "Shimla",
        "state": "Himachal Pradesh",
        "railway": {"code": "KLK", "name": "Kalka Railway Station", "dist_km": 88, "tier": "MAJOR"},
        "bus": {"name": "Shimla ISBT Tutikandi", "dist_km": 0},
        "airport": {"code": "SLV", "name": "Jubarhati Shimla Airport", "dist_km": 20},
        "gateway": "Chandigarh / Kalka",
        "corridor": "SHIMLA_CHANDIGARH_CORRIDOR",
        "dist_to_katra": 420,
        "notes": "Toy train or road to Kalka/Chandigarh; connect via direct trains (Hemkunt / Vande Bharat) to Katra.",
    },
    "solan": {
        "name": "Solan",
        "district": "Solan",
        "state": "Himachal Pradesh",
        "railway": {"code": "KLK", "name": "Kalka Railway Station", "dist_km": 42, "tier": "MAJOR"},
        "bus": {"name": "Solan Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 68},
        "gateway": "Chandigarh / Kalka",
        "corridor": "SHIMLA_CHANDIGARH_CORRIDOR",
        "dist_to_katra": 380,
        "notes": "Located on NH5 near Kalka/Chandigarh for onward rail/bus journeys to Katra.",
    },
    "kullu": {
        "name": "Kullu",
        "district": "Kullu",
        "state": "Himachal Pradesh",
        "railway": {"code": "CDG", "name": "Chandigarh Railway Station", "dist_km": 250, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Kullu Bus Stand Sarvari", "dist_km": 0},
        "airport": {"code": "KUU", "name": "Bhuntar Airport", "dist_km": 10},
        "gateway": "Pathankot / Chandigarh",
        "corridor": "BEAS_VALLEY_CORRIDOR",
        "dist_to_katra": 350,
        "notes": "Connected via Mandi/Aut to Pathankot or Kiratpur Sahib for onward trains to Katra.",
    },
    "manali": {
        "name": "Manali",
        "district": "Kullu",
        "state": "Himachal Pradesh",
        "railway": {"code": "CDG", "name": "Chandigarh Railway Station", "dist_km": 290, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Manali Private / HRTC Bus Stand", "dist_km": 0},
        "airport": {"code": "KUU", "name": "Bhuntar Airport", "dist_km": 50},
        "gateway": "Pathankot / Chandigarh",
        "corridor": "BEAS_VALLEY_CORRIDOR",
        "dist_to_katra": 390,
        "notes": "Direct overnight buses run to Chandigarh and Pathankot connecting to Katra trains.",
    },
    "hamirpur": {
        "name": "Hamirpur",
        "district": "Hamirpur",
        "state": "Himachal Pradesh",
        "railway": {"code": "UHL", "name": "Una Himachal", "dist_km": 65, "tier": "MAJOR"},
        "bus": {"name": "Hamirpur Main Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Kangra Airport", "dist_km": 75},
        "gateway": "Una / Pathankot",
        "corridor": "HIMACHAL_CENTRAL_CORRIDOR",
        "dist_to_katra": 255,
        "notes": "Connects via Una or Nadaun/Kangra to Pathankot for train routes to Katra.",
    },
    "bilaspur_hp": {
        "name": "Bilaspur",
        "district": "Bilaspur",
        "state": "Himachal Pradesh",
        "railway": {"code": "ANSB", "name": "Anandpur Sahib / Kiratpur", "dist_km": 55, "tier": "MAJOR"},
        "bus": {"name": "Bilaspur Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 130},
        "gateway": "Kiratpur / Chandigarh",
        "corridor": "HIMACHAL_FOOTHILLS_CORRIDOR",
        "dist_to_katra": 310,
        "notes": "Town in Himachal Pradesh on NH205/NH154; connects via Kiratpur Sahib to direct trains.",
    },
    "sundernagar": {
        "name": "Sundernagar",
        "district": "Mandi",
        "state": "Himachal Pradesh",
        "railway": {"code": "ANSB", "name": "Anandpur Sahib", "dist_km": 90, "tier": "MAJOR"},
        "bus": {"name": "Sundernagar Bus Stand", "dist_km": 0},
        "airport": {"code": "KUU", "name": "Bhuntar Airport", "dist_km": 78},
        "gateway": "Kiratpur / Pathankot",
        "corridor": "HIMACHAL_CENTRAL_CORRIDOR",
        "dist_to_katra": 275,
        "notes": "Located 22 km south of Mandi on NH21; connects to Pathankot or Kiratpur Sahib.",
    },
    "baijnath": {
        "name": "Baijnath",
        "district": "Kangra",
        "state": "Himachal Pradesh",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 130, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Baijnath Bus Stand", "dist_km": 0},
        "airport": {"code": "DHM", "name": "Kangra Airport", "dist_km": 50},
        "gateway": "Pathankot",
        "corridor": "KANGRA_VALLEY_CORRIDOR",
        "dist_to_katra": 240,
        "notes": "Ancient temple town 16 km past Palampur; road connects via Kangra to Pathankot.",
    },

    # -------------------------------------------------------------------------
    # Punjab (Direct Rail & Road Gateway Corridor)
    # -------------------------------------------------------------------------
    "pathankot": {
        "name": "Pathankot",
        "district": "Pathankot",
        "state": "Punjab",
        "railway": {"code": "PTKC", "name": "Pathankot Cantt", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Pathankot Maharana Pratap Inter-State Bus Stand", "dist_km": 0},
        "airport": {"code": "IXJ", "name": "Jammu Airport", "dist_km": 105},
        "gateway": "Pathankot",
        "corridor": "PRIMARY_GATEWAY",
        "dist_to_katra": 110,
        "notes": "Crucial railway junction connecting Himachal Pradesh and Punjab to Jammu and Katra (2-2.5h by train/bus).",
    },
    "amritsar": {
        "name": "Amritsar",
        "district": "Amritsar",
        "state": "Punjab",
        "railway": {"code": "ASR", "name": "Amritsar Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Amritsar ISBT", "dist_km": 0},
        "airport": {"code": "ATQ", "name": "Sri Guru Ram Dass Jee International Airport", "dist_km": 11},
        "gateway": "Amritsar / Pathankot",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 255,
        "notes": "Direct express trains (Ravi Express, Tata Jat Express) connect via Pathankot to Katra; daily direct buses run on NH44.",
    },
    "jalandhar": {
        "name": "Jalandhar",
        "district": "Jalandhar",
        "state": "Punjab",
        "railway": {"code": "JUC", "name": "Jalandhar City / JRC Cantt", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Shaheed-e-Azam Bhagat Singh ISBT", "dist_km": 0},
        "airport": {"code": "ATQ", "name": "Amritsar Airport", "dist_km": 85},
        "gateway": "Jalandhar",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 215,
        "notes": "Major junction on Delhi-Amritsar-Jammu corridor; almost all Katra-bound trains halt here.",
    },
    "ludhiana": {
        "name": "Ludhiana",
        "district": "Ludhiana",
        "state": "Punjab",
        "railway": {"code": "LDH", "name": "Ludhiana Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Ludhiana Bus Stand", "dist_km": 0},
        "airport": {"code": "LUH", "name": "Sahnewal Airport", "dist_km": 15},
        "gateway": "Ludhiana",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 275,
        "notes": "Verified railway corridor with direct Vande Bharat, Malwa, and Uttar Sampark Kranti express trains to SVDK Katra.",
    },
    "gurdaspur": {
        "name": "Gurdaspur",
        "district": "Gurdaspur",
        "state": "Punjab",
        "railway": {"code": "GSP", "name": "Gurdaspur Railway Station", "dist_km": 1, "tier": "SECONDARY"},
        "bus": {"name": "Gurdaspur Bus Stand", "dist_km": 0},
        "airport": {"code": "ATQ", "name": "Amritsar Airport", "dist_km": 75},
        "gateway": "Pathankot",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 145,
        "notes": "Located 35 km south of Pathankot on the Amritsar-Pathankot highway.",
    },
    "batala": {
        "name": "Batala",
        "district": "Gurdaspur",
        "state": "Punjab",
        "railway": {"code": "BAT", "name": "Batala Junction", "dist_km": 2, "tier": "SECONDARY"},
        "bus": {"name": "Batala Bus Stand", "dist_km": 0},
        "airport": {"code": "ATQ", "name": "Amritsar Airport", "dist_km": 42},
        "gateway": "Pathankot / Amritsar",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 180,
        "notes": "Industrial hub in Majha region; direct rail/bus routes run to Pathankot for Katra transfers.",
    },
    "hoshiarpur": {
        "name": "Hoshiarpur",
        "district": "Hoshiarpur",
        "state": "Punjab",
        "railway": {"code": "HSX", "name": "Hoshiarpur Railway Station", "dist_km": 2, "tier": "SECONDARY"},
        "bus": {"name": "Hoshiarpur Main Bus Stand", "dist_km": 0},
        "airport": {"code": "ATQ", "name": "Amritsar Airport", "dist_km": 110},
        "gateway": "Jalandhar / Pathankot",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 200,
        "notes": "Connects via Jalandhar (40 km) or Dasuya to Pathankot for direct Katra trains.",
    },
    "patiala": {
        "name": "Patiala",
        "district": "Patiala",
        "state": "Punjab",
        "railway": {"code": "PTA", "name": "Patiala Railway Station", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Patiala New Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 60},
        "gateway": "Ambala / Ludhiana",
        "corridor": "PUNJAB_MAINLINE_CORRIDOR",
        "dist_to_katra": 340,
        "notes": "Connects via Ambala Cantt (50 km) or Rajpura for direct express trains to SVDK Katra.",
    },
    "bathinda": {
        "name": "Bathinda",
        "district": "Bathinda",
        "state": "Punjab",
        "railway": {"code": "BTI", "name": "Bathinda Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Bathinda Bus Stand", "dist_km": 0},
        "airport": {"code": "BVP", "name": "Bathinda Airport", "dist_km": 25},
        "gateway": "Ludhiana / Firozpur",
        "corridor": "MALWA_PUNJAB_CORRIDOR",
        "dist_to_katra": 380,
        "notes": "Major junction in southwestern Punjab; trains connect via Firozpur/Jalandhar or Ludhiana to Katra.",
    },

    # -------------------------------------------------------------------------
    # Chandigarh & Haryana (Direct High-Speed Corridor)
    # -------------------------------------------------------------------------
    "chandigarh": {
        "name": "Chandigarh",
        "district": "Chandigarh",
        "state": "Chandigarh",
        "railway": {"code": "CDG", "name": "Chandigarh Junction", "dist_km": 5, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "ISBT Sector 43 / Sector 17", "dist_km": 0},
        "airport": {"code": "IXC", "name": "Shaheed Bhagat Singh International Airport", "dist_km": 12},
        "gateway": "Chandigarh",
        "corridor": "PRIMARY_GATEWAY",
        "dist_to_katra": 380,
        "notes": "Direct Vande Bharat and Hemkunt Express trains; daily JKRTC deluxe buses operate from ISBT 43.",
    },
    "ambala": {
        "name": "Ambala",
        "district": "Ambala",
        "state": "Haryana",
        "railway": {"code": "UMB", "name": "Ambala Cantt Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Ambala Cantt Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 40},
        "gateway": "Ambala",
        "corridor": "PRIMARY_GATEWAY",
        "dist_to_katra": 395,
        "notes": "Verified corridor; key railway junction with direct Vande Bharat and express connections to Katra.",
    },
    "panipat": {
        "name": "Panipat",
        "district": "Panipat",
        "state": "Haryana",
        "railway": {"code": "PNP", "name": "Panipat Junction", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Panipat Bus Stand (NH44)", "dist_km": 0},
        "airport": {"code": "DEL", "name": "Indira Gandhi International Airport", "dist_km": 105},
        "gateway": "Delhi / Ambala",
        "corridor": "DELHI_AMBALA_CORRIDOR",
        "dist_to_katra": 540,
        "notes": "Key halt on Delhi-Ambala-Katra trunk route; express trains (e.g. Uttar Sampark Kranti) halt here.",
    },
    "karnal": {
        "name": "Karnal",
        "district": "Karnal",
        "state": "Haryana",
        "railway": {"code": "KUN", "name": "Karnal Railway Station", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Karnal Bus Stand (NH44)", "dist_km": 0},
        "airport": {"code": "DEL", "name": "Delhi Airport", "dist_km": 140},
        "gateway": "Delhi / Ambala",
        "corridor": "DELHI_AMBALA_CORRIDOR",
        "dist_to_katra": 505,
        "notes": "Located on GT Road (NH44); convenient train stops connecting directly to Katra and Jammu.",
    },
    "gurugram": {
        "name": "Gurugram",
        "district": "Gurugram",
        "state": "Haryana",
        "railway": {"code": "NDLS", "name": "New Delhi Railway Station", "dist_km": 32, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Gurugram Bus Stand / IFFCO Chowk", "dist_km": 0},
        "airport": {"code": "DEL", "name": "IGI Airport Terminal 3", "dist_km": 16},
        "gateway": "New Delhi",
        "corridor": "NATIONAL_CAPITAL_REGION",
        "dist_to_katra": 670,
        "notes": "Connect via New Delhi (NDLS) for morning Vande Bharat or flights to Jammu (IXJ).",
    },

    # -------------------------------------------------------------------------
    # National Capital & Metropolitan Gateways
    # -------------------------------------------------------------------------
    "delhi": {
        "name": "Delhi",
        "district": "New Delhi",
        "state": "Delhi",
        "railway": {"code": "NDLS", "name": "New Delhi Railway Station", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Maharana Pratap ISBT Kashmiri Gate", "dist_km": 0},
        "airport": {"code": "DEL", "name": "Indira Gandhi International Airport", "dist_km": 15},
        "gateway": "New Delhi",
        "corridor": "PRIMARY_GATEWAY",
        "dist_to_katra": 640,
        "notes": "National hub with 8h Vande Bharat Express (22439), Uttar Sampark Kranti, flights, and JKRTC buses.",
    },
    "mumbai": {
        "name": "Mumbai",
        "district": "Mumbai",
        "state": "Maharashtra",
        "railway": {"code": "BDTS", "name": "Bandra Terminus / CSMT", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Mumbai Central Bus Stand", "dist_km": 0},
        "airport": {"code": "BOM", "name": "Chhatrapati Shivaji Maharaj International", "dist_km": 15},
        "gateway": "Mumbai",
        "corridor": "WESTERN_CORRIDOR",
        "dist_to_katra": 1850,
        "notes": "Direct Swaraj Express (12471) to Katra; direct/connecting flights to Jammu (IXJ).",
    },
    "kolkata": {
        "name": "Kolkata",
        "district": "Kolkata",
        "state": "West Bengal",
        "railway": {"code": "HWH", "name": "Howrah / Sealdah", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Esplanade Bus Terminus", "dist_km": 0},
        "airport": {"code": "CCU", "name": "Netaji Subhash Chandra Bose Airport", "dist_km": 16},
        "gateway": "Kolkata / New Delhi",
        "corridor": "EASTERN_CORRIDOR",
        "dist_to_katra": 2080,
        "notes": "Direct Himgiri Express (12331) to Jammu Tawi, or flights connecting via New Delhi.",
    },
    "bengaluru": {
        "name": "Bengaluru",
        "district": "Bengaluru Urban",
        "state": "Karnataka",
        "railway": {"code": "SBC", "name": "KSR Bengaluru", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Kempegowda Bus Station (Majestic)", "dist_km": 0},
        "airport": {"code": "BLR", "name": "Kempegowda International Airport", "dist_km": 35},
        "gateway": "New Delhi / Bengaluru",
        "corridor": "SOUTHERN_CORRIDOR",
        "dist_to_katra": 2650,
        "notes": "Direct long-haul trains (e.g. Karnataka Express to NDLS) and 1-stop flights via DEL to Jammu.",
    },
    "chennai": {
        "name": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "railway": {"code": "MAS", "name": "MGR Chennai Central", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Puratchi Thalaivar Dr. MGR Bus Terminus (CMBT)", "dist_km": 0},
        "airport": {"code": "MAA", "name": "Chennai International Airport", "dist_km": 18},
        "gateway": "New Delhi / Chennai",
        "corridor": "SOUTHERN_CORRIDOR",
        "dist_to_katra": 2780,
        "notes": "Direct Andaman Express (16031) to SVDK Katra, or flights via New Delhi to Jammu.",
    },
    "hyderabad": {
        "name": "Hyderabad",
        "district": "Hyderabad",
        "state": "Telangana",
        "railway": {"code": "SC", "name": "Secunderabad Junction", "dist_km": 0, "tier": "NATIONAL_TERMINAL"},
        "bus": {"name": "Mahatma Gandhi Bus Station (MGBS)", "dist_km": 0},
        "airport": {"code": "HYD", "name": "Rajiv Gandhi International Airport", "dist_km": 25},
        "gateway": "New Delhi / Hyderabad",
        "corridor": "DECCAN_CORRIDOR",
        "dist_to_katra": 2150,
        "notes": "Telangana Express to NDLS + Vande Bharat to Katra; 1-stop flights via DEL to IXJ.",
    },
    "pune": {
        "name": "Pune",
        "district": "Pune",
        "state": "Maharashtra",
        "railway": {"code": "PUNE", "name": "Pune Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Shivajinagar / Swargate Bus Stand", "dist_km": 0},
        "airport": {"code": "PNQ", "name": "Pune International Airport", "dist_km": 10},
        "gateway": "Mumbai / New Delhi",
        "corridor": "WESTERN_CORRIDOR",
        "dist_to_katra": 1980,
        "notes": "Express train/cab to Mumbai (CSMT/BDTS) or New Delhi for direct Vande Bharat / Swaraj Express.",
    },
    "ahmedabad": {
        "name": "Ahmedabad",
        "district": "Ahmedabad",
        "state": "Gujarat",
        "railway": {"code": "ADI", "name": "Ahmedabad Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Geeta Mandir Central Bus Stand", "dist_km": 0},
        "airport": {"code": "AMD", "name": "Sardar Vallabhbhai Patel International", "dist_km": 12},
        "gateway": "Ahmedabad",
        "corridor": "GUJARAT_CORRIDOR",
        "dist_to_katra": 1420,
        "notes": "Direct Sarvodaya Express (12473) and Hapa-SVDK Express (12475) to Katra; daily flights via DEL.",
    },

    # -------------------------------------------------------------------------
    # Central, Northern & Eastern Tier-2 / Tier-3 Regional Hubs
    # -------------------------------------------------------------------------
    "jaipur": {
        "name": "Jaipur",
        "district": "Jaipur",
        "state": "Rajasthan",
        "railway": {"code": "JP", "name": "Jaipur Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Sindhi Camp Central Bus Stand", "dist_km": 0},
        "airport": {"code": "JAI", "name": "Jaipur International Airport", "dist_km": 12},
        "gateway": "Delhi / Jammu",
        "corridor": "RAJASTHAN_CORRIDOR",
        "dist_to_katra": 880,
        "notes": "Direct Pooja SF Express (12413) to Jammu Tawi; or Shatabdi/Vande Bharat to NDLS for Katra connection.",
    },
    "lucknow": {
        "name": "Lucknow",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "railway": {"code": "LKO", "name": "Lucknow Charbagh", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Alambagh / Kaiserbagh Bus Stand", "dist_km": 0},
        "airport": {"code": "LKO", "name": "Chaudhary Charan Singh International", "dist_km": 12},
        "gateway": "New Delhi / Jammu",
        "corridor": "UP_CENTRAL_CORRIDOR",
        "dist_to_katra": 1050,
        "notes": "Direct Begampura Express (12237) to Jammu Tawi, or Tejas/Shatabdi to New Delhi for Katra trains.",
    },
    "varanasi": {
        "name": "Varanasi",
        "district": "Varanasi",
        "state": "Uttar Pradesh",
        "railway": {"code": "BSB", "name": "Varanasi Junction (Cantonment)", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Varanasi Cantt Bus Stand", "dist_km": 0},
        "airport": {"code": "VNS", "name": "Lal Bahadur Shastri International", "dist_km": 22},
        "gateway": "New Delhi / Jammu",
        "corridor": "UP_EASTERN_CORRIDOR",
        "dist_to_katra": 1320,
        "notes": "Direct Begampura Express (12237) to Jammu Tawi; Vande Bharat Express to New Delhi for Katra connection.",
    },
    "kanpur": {
        "name": "Kanpur",
        "district": "Kanpur Nagar",
        "state": "Uttar Pradesh",
        "railway": {"code": "CNB", "name": "Kanpur Central", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Jhakarkati Bus Station", "dist_km": 0},
        "airport": {"code": "KNU", "name": "Kanpur Chakeri Airport", "dist_km": 14},
        "gateway": "New Delhi",
        "corridor": "UP_CENTRAL_CORRIDOR",
        "dist_to_katra": 1120,
        "notes": "Frequent 4.5h Shatabdi / Vande Bharat to New Delhi (NDLS), connecting directly to Katra trains.",
    },
    "patna": {
        "name": "Patna",
        "district": "Patna",
        "state": "Bihar",
        "railway": {"code": "PNBE", "name": "Patna Junction", "dist_km": 1, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Bairiya ISBT Patna", "dist_km": 0},
        "airport": {"code": "PAT", "name": "Jay Prakash Narayan Airport", "dist_km": 6},
        "gateway": "New Delhi",
        "corridor": "BIHAR_CORRIDOR",
        "dist_to_katra": 1640,
        "notes": "Direct Archana Express (12355) runs twice weekly to Jammu; Rajdhani/Tejas connects via NDLS to Katra.",
    },
    "bhopal": {
        "name": "Bhopal",
        "district": "Bhopal",
        "state": "Madhya Pradesh",
        "railway": {"code": "BPL", "name": "Bhopal Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Kushabhau Thakre ISBT", "dist_km": 0},
        "airport": {"code": "BHO", "name": "Raja Bhoj Airport", "dist_km": 12},
        "gateway": "Bhopal / Delhi",
        "corridor": "CENTRAL_INDIA_CORRIDOR",
        "dist_to_katra": 1390,
        "notes": "Direct Malwa Express (12919) runs daily through Bhopal directly to SVDK Katra.",
    },
    "indore": {
        "name": "Indore",
        "district": "Indore",
        "state": "Madhya Pradesh",
        "railway": {"code": "INDB", "name": "Indore Junction", "dist_km": 1, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Sarwate / Gangwal Bus Stand", "dist_km": 0},
        "airport": {"code": "IDR", "name": "Devi Ahilyabai Holkar Airport", "dist_km": 8},
        "gateway": "Indore",
        "corridor": "CENTRAL_INDIA_CORRIDOR",
        "dist_to_katra": 1490,
        "notes": "Verified corridor; origin of daily Malwa Express (12919) running directly to SVDK Katra.",
    },
    "surat": {
        "name": "Surat",
        "district": "Surat",
        "state": "Gujarat",
        "railway": {"code": "ST", "name": "Surat Railway Station", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Surat Central Bus Station", "dist_km": 0},
        "airport": {"code": "STV", "name": "Surat International Airport", "dist_km": 15},
        "gateway": "Surat / Ahmedabad",
        "corridor": "GUJARAT_CORRIDOR",
        "dist_to_katra": 1680,
        "notes": "Direct Swaraj Express (12471) and Sarvodaya Express (12473) connect directly to SVDK Katra.",
    },
    "haridwar": {
        "name": "Haridwar",
        "district": "Haridwar",
        "state": "Uttarakhand",
        "railway": {"code": "HW", "name": "Haridwar Junction", "dist_km": 1, "tier": "MAJOR"},
        "bus": {"name": "Haridwar Bus Stand", "dist_km": 0},
        "airport": {"code": "DED", "name": "Jolly Grant Dehradun Airport", "dist_km": 38},
        "gateway": "Haridwar / Ambala",
        "corridor": "UTTARAKHAND_CORRIDOR",
        "dist_to_katra": 580,
        "notes": "Direct Hemkunt Express (14609) connects Rishikesh/Haridwar directly to SVDK Katra.",
    },
    "dehradun": {
        "name": "Dehradun",
        "district": "Dehradun",
        "state": "Uttarakhand",
        "railway": {"code": "DDN", "name": "Dehradun Terminal", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "ISBT Dehradun", "dist_km": 0},
        "airport": {"code": "DED", "name": "Jolly Grant Airport", "dist_km": 25},
        "gateway": "Haridwar / Ambala",
        "corridor": "UTTARAKHAND_CORRIDOR",
        "dist_to_katra": 610,
        "notes": "Connects via Haridwar (Hemkunt Express to Katra) or via Ambala/Chandigarh.",
    },
    "guwahati": {
        "name": "Guwahati",
        "district": "Kamrup Metropolitan",
        "state": "Assam",
        "railway": {"code": "GHY", "name": "Guwahati Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "ISBT Betkuchi Guwahati", "dist_km": 0},
        "airport": {"code": "GAU", "name": "Lokpriya Gopinath Bordoloi International", "dist_km": 22},
        "gateway": "New Delhi / Kolkata",
        "corridor": "NORTHEAST_CORRIDOR",
        "dist_to_katra": 2420,
        "notes": "Direct weekly Lohit Express (15651) to Jammu Tawi; connecting flights operate via New Delhi to Jammu.",
    },
    "bilaspur_cg": {
        "name": "Bilaspur",
        "district": "Bilaspur",
        "state": "Chhattisgarh",
        "railway": {"code": "BSP", "name": "Bilaspur Junction", "dist_km": 0, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Hi-Tech Bus Stand Bilaspur", "dist_km": 3},
        "airport": {"code": "PAB", "name": "Bilaspur Airport (Bilasa Devi)", "dist_km": 11},
        "gateway": "New Delhi / Nagpur",
        "corridor": "CENTRAL_CONNECTING",
        "dist_to_katra": 1650,
        "notes": "Major SECR railway division headquarters in Chhattisgarh; connects via New Delhi or direct express trains.",
    },
    "anandpur_pb": {
        "name": "Anandpur Sahib",
        "district": "Rupnagar",
        "state": "Punjab",
        "railway": {"code": "ANSB", "name": "Anandpur Sahib Railway Station", "dist_km": 1, "tier": "MAJOR"},
        "bus": {"name": "Anandpur Sahib Bus Stand", "dist_km": 0},
        "airport": {"code": "CDG", "name": "Chandigarh Airport", "dist_km": 95},
        "gateway": "Una / Chandigarh",
        "corridor": "HIMACHAL_FOOTHILLS_CORRIDOR",
        "dist_to_katra": 320,
        "notes": "Holy Sikh pilgrimage city on Sutlej river; direct rail link on Una Himachal - New Delhi line via Kiratpur Sahib.",
    },
    "anandpur_or": {
        "name": "Anandapur",
        "district": "Kendujhar",
        "state": "Odisha",
        "railway": {"code": "BHC", "name": "Bhadrak Railway Station", "dist_km": 42, "tier": "MAJOR"},
        "bus": {"name": "Anandapur Bus Stand", "dist_km": 0},
        "airport": {"code": "BBI", "name": "Bhubaneswar Airport", "dist_km": 140},
        "gateway": "Bhubaneswar / New Delhi",
        "corridor": "EASTERN_CORRIDOR",
        "dist_to_katra": 2180,
        "notes": "Municipality in Keonjhar district, Odisha on Baitarani river; connects via Bhadrak or Bhubaneswar to New Delhi.",
    },
    "aurangabad_mh": {
        "name": "Chhatrapati Sambhajinagar (Aurangabad)",
        "district": "Chhatrapati Sambhajinagar",
        "state": "Maharashtra",
        "railway": {"code": "AWB", "name": "Aurangabad Railway Station", "dist_km": 2, "tier": "MAJOR"},
        "bus": {"name": "Central Bus Stand Aurangabad", "dist_km": 1},
        "airport": {"code": "IXU", "name": "Aurangabad Airport", "dist_km": 9},
        "gateway": "Mumbai / New Delhi",
        "corridor": "WESTERN_CORRIDOR",
        "dist_to_katra": 1720,
        "notes": "Major tourism city in Maharashtra (Ajanta/Ellora gateway); connects via Mumbai or New Delhi express trains.",
    },
    "aurangabad_br": {
        "name": "Aurangabad",
        "district": "Aurangabad",
        "state": "Bihar",
        "railway": {"code": "AUBR", "name": "Anugraha Narayan Road", "dist_km": 15, "tier": "MAJOR"},
        "bus": {"name": "Aurangabad Old Bus Stand", "dist_km": 0},
        "airport": {"code": "GAY", "name": "Gaya Airport", "dist_km": 72},
        "gateway": "Gaya / New Delhi",
        "corridor": "EASTERN_CORRIDOR",
        "dist_to_katra": 1480,
        "notes": "District headquarters in Magadh division, Bihar on Grand Trunk Road (NH-19); connects via Anugraha Narayan Road.",
    },
    "rampur_up": {
        "name": "Rampur",
        "district": "Rampur",
        "state": "Uttar Pradesh",
        "railway": {"code": "RMU", "name": "Rampur Junction", "dist_km": 1, "tier": "MAJOR"},
        "bus": {"name": "Rampur Bus Stand", "dist_km": 0},
        "airport": {"code": "DEL", "name": "Indira Gandhi International Airport", "dist_km": 205},
        "gateway": "Moradabad / New Delhi",
        "corridor": "NORTHERN_CONNECTING",
        "dist_to_katra": 740,
        "notes": "City in western Uttar Pradesh on Moradabad-Bareilly mainline; direct express trains connect via Moradabad to Katra.",
    },
    "rampur_hp": {
        "name": "Rampur Bushahr",
        "district": "Shimla",
        "state": "Himachal Pradesh",
        "railway": {"code": "SML", "name": "Shimla Railway Station (Toy Train)", "dist_km": 130, "tier": "NARROW_GAUGE"},
        "bus": {"name": "Rampur Bushahr Bus Stand", "dist_km": 0},
        "airport": {"code": "SLV", "name": "Shimla Airport (Jubbarhatti)", "dist_km": 150},
        "gateway": "Shimla / Chandigarh",
        "corridor": "HIMACHAL_CENTRAL_CORRIDOR",
        "dist_to_katra": 490,
        "notes": "Historic town on Sutlej river in Shimla district on NH-5; road transport connects via Shimla/Chandigarh to Katra.",
    },
    "pratapgarh_up": {
        "name": "Pratapgarh",
        "district": "Pratapgarh",
        "state": "Uttar Pradesh",
        "railway": {"code": "PBH", "name": "Maa Belha Devi Dham Pratapgarh Junction", "dist_km": 1, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "Pratapgarh Roadways Depot", "dist_km": 0},
        "airport": {"code": "IXD", "name": "Prayagraj Airport", "dist_km": 65},
        "gateway": "Prayagraj / Lucknow",
        "corridor": "EASTERN_CORRIDOR",
        "dist_to_katra": 1150,
        "notes": "Major railway junction in eastern UP; direct superfast trains connect via Lucknow/Ambala to Katra.",
    },
    "pratapgarh_rj": {
        "name": "Pratapgarh",
        "district": "Pratapgarh",
        "state": "Rajasthan",
        "railway": {"code": "MDS", "name": "Mandsaur Railway Station", "dist_km": 32, "tier": "MAJOR"},
        "bus": {"name": "Pratapgarh RSRTC Central Bus Stand", "dist_km": 0},
        "airport": {"code": "UDR", "name": "Maharana Pratap Airport Udaipur", "dist_km": 145},
        "gateway": "Mandsaur / Kota / Delhi",
        "corridor": "WESTERN_CORRIDOR",
        "dist_to_katra": 1280,
        "notes": "District in southern Rajasthan; connects via Mandsaur railway station or Ratlam/Kota to Katra.",
    },
    "kochi": {
        "name": "Kochi",
        "district": "Ernakulam",
        "state": "Kerala",
        "railway": {"code": "ERS", "name": "Ernakulam Junction", "dist_km": 2, "tier": "MAJOR_JUNCTION"},
        "bus": {"name": "KSRTC Bus Station Ernakulam", "dist_km": 0},
        "airport": {"code": "COK", "name": "Cochin International Airport", "dist_km": 28},
        "gateway": "New Delhi",
        "corridor": "SOUTHERN_CORRIDOR",
        "dist_to_katra": 3150,
        "notes": "Direct weekly Himsagar Express (16317) to Katra; 1-stop flights via DEL to Jammu.",
    },
}

# Ambiguous Indian placenames that exist in multiple states
AMBIGUOUS_INDIAN_PLACES: Dict[str, List[Dict[str, str]]] = {
    "bilaspur": [
        {"state": "Himachal Pradesh", "district": "Bilaspur", "context": "Hill town on NH205/NH154 connecting via Kiratpur Sahib / Anandpur Sahib to Katra."},
        {"state": "Chhattisgarh", "district": "Bilaspur", "context": "Major railway junction (SECR HQ) in Chhattisgarh connecting via New Delhi to Katra."},
    ],
    "anandpur": [
        {"state": "Punjab", "district": "Rupnagar", "context": "Holy Sikh pilgrimage town (Anandpur Sahib) near Nangal/Kiratpur connecting directly via Una/Rupnagar to Katra."},
        {"state": "Odisha", "district": "Kendujhar", "context": "Municipality in Keonjhar district, Odisha connecting via Bhubaneswar / New Delhi to Katra."},
    ],
    "aurangabad": [
        {"state": "Maharashtra", "district": "Chhatrapati Sambhajinagar", "context": "Historical tourist hub in Maharashtra connecting via Mumbai/Delhi to Katra."},
        {"state": "Bihar", "district": "Aurangabad", "context": "District in southern Bihar on the Grand Trunk road connecting via Patna/Delhi to Katra."},
    ],
    "rampur": [
        {"state": "Uttar Pradesh", "district": "Rampur", "context": "City in western UP near Moradabad connecting via New Delhi to Katra."},
        {"state": "Himachal Pradesh", "district": "Shimla", "context": "Rampur Bushahr on Sutlej river in HP connecting via Shimla/Chandigarh to Katra."},
    ],
    "pratapgarh": [
        {"state": "Uttar Pradesh", "district": "Pratapgarh", "context": "District in eastern UP near Prayagraj connecting via Lucknow/Delhi."},
        {"state": "Rajasthan", "district": "Pratapgarh", "context": "District in southern Rajasthan connecting via Chittorgarh/Delhi."},
    ],
}

# Sub-location & village extraction regex patterns
VILLAGE_PATTERNS = [
    # "a small village near Mandi" / "village near Palampur" / "hamlet near Dharamshala"
    r"\b(?:a\s+)?(?:small\s+)?(?:village|settlement|hamlet|township|gram|kasba|area)\s+(?:near|around|close\s+to|in|of)\s+([A-Za-z\s]+)",
    # "Rewalsar near Mandi" / "Bir near Palampur"
    r"\b([A-Za-z\s]{3,25})\s+(?:near|close\s+to|outside)\s+([A-Za-z\s]{3,20})",
    # "remote area in Reasi district"
    r"\b(?:remote\s+)?(?:village|area|settlement)\s+in\s+([A-Za-z\s]+)\s+district",
]


# =============================================================================
# GeoResolver Engine Class
# =============================================================================

class GeoResolver:
    """
    Intelligent Geographic Entity & Transport Hub Resolver for Yatra AI.
    Features:
    - Zero-latency local knowledge base for major cities, regional centers, and hill towns.
    - Automatic village / rural entity normalization (extracting base hub and district).
    - Ambiguity detection with polite clarification generation.
    - Safe rate-limited external OSM/Nominatim lookup with fallback cache.
    - Guaranteed zero-rejection policy.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GeoResolver, cls).__new__(cls)
                cls._instance._init_resolver()
            return cls._instance

    def _init_resolver(self):
        self._cache = get_cache_manager()
        logger.info("Universal Indian GeoResolver initialized with %d curated hubs.", len(INDIAN_GEO_REGISTRY))

    def resolve_origin(self, user_origin_text: str) -> ResolvedLocation:
        """
        Resolves any free-text Indian origin into a structured ResolvedLocation.
        Never throws an exception or rejects an origin.
        """
        if not user_origin_text or not str(user_origin_text).strip():
            return ResolvedLocation(
                raw_input="",
                clean_name="Unspecified",
                base_town="New Delhi",
                district="New Delhi",
                state="Delhi",
                resolution_source="fallback_unspecified",
                confidence=0.0,
            )

        raw = str(user_origin_text).strip()
        raw_clean = re.sub(r"[\s,;]+", " ", raw).strip()
        lower_raw = raw_clean.lower()

        # 0. Check for invalid, nonsensical, or foreign origins
        if self._is_invalid_or_foreign_origin(raw_clean):
            return ResolvedLocation(
                raw_input=raw,
                clean_name=raw_clean,
                base_town=raw_clean,
                is_invalid=True,
                primary_gateway_hub="Unresolved Origin",
                corridor_type="UNRESOLVED_LOCATION",
                resolution_source="unresolved_location",
                confidence=0.0,
                notes=f"'{raw_clean}' is not recognized as a valid Indian town or district.",
            )

        # 1. Check for Village / Sub-Location semantics
        village_match = self._extract_village_and_base(raw)
        if village_match:
            sub_name, base_town = village_match
            base_norm = base_town.lower().strip()
            if base_norm in INDIAN_GEO_REGISTRY:
                hub_data = INDIAN_GEO_REGISTRY[base_norm]
                return ResolvedLocation(
                    raw_input=raw,
                    clean_name=f"{sub_name.title()} (near {hub_data['name']})",
                    base_town=hub_data["name"],
                    district=hub_data.get("district"),
                    state=hub_data.get("state"),
                    is_village_or_settlement=True,
                    nearest_railway_station=hub_data.get("railway"),
                    nearest_bus_terminal=hub_data.get("bus"),
                    nearest_airport=hub_data.get("airport"),
                    primary_gateway_hub=hub_data.get("gateway", "New Delhi"),
                    corridor_type=hub_data.get("corridor", "RURAL_CONNECTING"),
                    approx_road_distance_to_katra_km=hub_data.get("dist_to_katra"),
                    resolution_source="curated_village_base_mapping",
                    confidence=0.95,
                    notes=f"Rural / sub-location identified near {hub_data['name']}, {hub_data.get('state')}. Local road/bus feeder connects to {hub_data['name']}.",
                )
            else:
                # Base town not in curated DB -> resolve base town via Nominatim or state inference
                return self._resolve_fallback_town(sub_name, base_town, raw)

        # 2. Check for Ambiguous Location (e.g. Bilaspur, Anandpur, Aurangabad)
        ambig_key = self._check_ambiguity(lower_raw)
        if ambig_key:
            candidates = AMBIGUOUS_INDIAN_PLACES[ambig_key]
            tokens = set(re.split(r"[\s,;]+", lower_raw))
            state_abbrevs = {
                "himachal pradesh": "hp", "chhattisgarh": "cg", "maharashtra": "mh",
                "bihar": "br", "uttar pradesh": "up", "rajasthan": "rj",
                "punjab": "pb", "odisha": "or", "west bengal": "wb"
            }
            state_codes = {
                "Himachal Pradesh": "hp", "Chhattisgarh": "cg", "Maharashtra": "mh",
                "Bihar": "br", "Uttar Pradesh": "up", "Rajasthan": "rj",
                "Punjab": "pb", "Odisha": "or", "West Bengal": "wb"
            }
            # Check if user already disambiguated by mentioning state, district, or alias
            for cand in candidates:
                c_st = cand["state"].lower()
                c_dist = cand.get("district", "").lower()
                abbrev = state_abbrevs.get(c_st, "")
                is_match = (
                    c_st in lower_raw
                    or (c_dist and c_dist != ambig_key and c_dist in lower_raw)
                    or (abbrev and abbrev in tokens)
                    or (ambig_key == "anandpur" and cand["state"] == "Punjab" and ("sahib" in tokens or "takht" in tokens or "kesgarh" in lower_raw or "punjab" in lower_raw or "pb" in tokens))
                    or (ambig_key == "anandpur" and cand["state"] == "Odisha" and ("odisha" in lower_raw or "or" in tokens or "keonjhar" in lower_raw or "kendujhar" in lower_raw))
                    or (ambig_key == "bilaspur" and cand["state"] == "Chhattisgarh" and ("secr" in lower_raw or "chhattisgarh" in lower_raw or "cg" in tokens))
                    or (ambig_key == "bilaspur" and cand["state"] == "Himachal Pradesh" and ("himachal" in lower_raw or "hp" in tokens or "kiratpur" in lower_raw))
                    or (ambig_key == "aurangabad" and cand["state"] == "Maharashtra" and ("maharashtra" in lower_raw or "mh" in tokens or "sambhajinagar" in lower_raw))
                    or (ambig_key == "aurangabad" and cand["state"] == "Bihar" and ("bihar" in lower_raw or "br" in tokens))
                    or (ambig_key == "rampur" and cand["state"] == "Uttar Pradesh" and ("uttar pradesh" in lower_raw or "up" in tokens or "moradabad" in lower_raw))
                    or (ambig_key == "rampur" and cand["state"] == "Himachal Pradesh" and ("himachal" in lower_raw or "hp" in tokens or "bushahr" in lower_raw))
                    or (ambig_key == "pratapgarh" and cand["state"] == "Uttar Pradesh" and ("uttar pradesh" in lower_raw or "up" in tokens or "prayagraj" in lower_raw))
                    or (ambig_key == "pratapgarh" and cand["state"] == "Rajasthan" and ("rajasthan" in lower_raw or "rj" in tokens or "mandsaur" in lower_raw))
                )
                if is_match:
                    code = state_codes.get(cand["state"], cand["state"][:2].lower())
                    cand_key = f"{ambig_key}_{code}"
                    if cand_key in INDIAN_GEO_REGISTRY:
                        hub = INDIAN_GEO_REGISTRY[cand_key]
                        return self._build_from_hub(raw, hub, "curated_disambiguated")
                    return self._build_manual_location(raw, cand["state"], cand["district"], raw_clean.title())

            # Remains genuinely ambiguous
            return ResolvedLocation(
                raw_input=raw,
                clean_name=ambig_key.title(),
                base_town=ambig_key.title(),
                is_ambiguous=True,
                ambiguity_candidates=candidates,
                primary_gateway_hub="Awaiting Clarification",
                corridor_type="AMBIGUOUS_LOCATION",
                resolution_source="ambiguity_flagged",
                confidence=0.5,
                notes=f"'{ambig_key.title()}' exists in multiple Indian states: {', '.join(c['state'] for c in candidates)}.",
            )

        # 3. Direct lookup in Curated Registry (Exact or Alias)
        hub_match = self._find_in_curated_registry(lower_raw)
        if hub_match:
            return self._build_from_hub(raw, hub_match, "curated_geographic_registry")

        # 4. Check for state/district qualifiers in text (e.g. "Kullu, HP", "Rewari, Haryana")
        state_match = self._extract_state_and_city(raw_clean)
        if state_match:
            city_part, state_part = state_match
            city_norm = city_part.lower().strip()
            if city_norm in INDIAN_GEO_REGISTRY:
                hub = INDIAN_GEO_REGISTRY[city_norm]
                return self._build_from_hub(raw, hub, "curated_state_qualified")
            # Try OSM lookup for the qualified location
            return self._query_osm_or_fallback(raw, city_part, state_part)

        # 5. Query OpenStreetMap / Nominatim with timeout & Cache
        return self._query_osm_or_fallback(raw, raw_clean, None)

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _extract_village_and_base(self, text: str) -> Optional[Tuple[str, str]]:
        """Extracts sub-location/village name and base town without capturing trailing parameters."""
        t = text.strip()
        stop_clauses = {
            "for", "with", "on", "in", "by", "and", "to", "at", "during", "starting",
            "from", "we", "two", "three", "four", "five", "couple", "solo", "adults",
            "adult", "pilgrim", "pilgrims", "person", "persons", "people", "tomorrow",
            "today", "yesterday", "days", "day", "nights", "night"
        }
        for pat in VILLAGE_PATTERNS:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                if len(m.groups()) == 1:
                    raw_base = m.group(1).strip()
                    words = [w for w in re.split(r"[\s,;]+", raw_base) if w]
                    clean_words = []
                    for w in words:
                        if w.lower() in stop_clauses:
                            break
                        clean_words.append(w)
                    if clean_words:
                        return ("Village", " ".join(clean_words))
                elif len(m.groups()) == 2:
                    raw_sub = m.group(1).strip()
                    raw_base = m.group(2).strip()
                    sub_words = [w for w in re.split(r"[\s,;]+", raw_sub) if w and w.lower() not in stop_clauses]
                    base_words = []
                    for w in re.split(r"[\s,;]+", raw_base):
                        if w.lower() in stop_clauses:
                            break
                        base_words.append(w)
                    if base_words:
                        sub_str = " ".join(sub_words) if sub_words else "Village"
                        return (sub_str, " ".join(base_words))
        return None

    def _is_invalid_or_foreign_origin(self, text_clean: str) -> bool:
        """Identifies non-geographic gibberish, foreign locations, or invalid inputs."""
        t = text_clean.strip().lower()
        if not t or len(t) < 3:
            return True
        # Pure numbers or non-alphabetic symbols
        if re.match(r"^[\d\W_]+$", t):
            return True
        # Foreign places / non-Indian queries
        foreign_places = {
            "new york", "london", "paris", "tokyo", "singapore", "dubai", "sydney",
            "toronto", "berlin", "bangkok", "rome", "chicago", "san francisco",
            "usa", "uk", "canada", "australia", "germany", "france", "china",
            "atlantis", "mars", "moon", "wonderland", "narnia", "hogwarts"
        }
        if t in foreign_places:
            return True
        # Keyboard mashing / gibberish check
        # Check for 5+ consecutive consonants (e.g. asdfghjk -> sdfghjk)
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", t):
            return True
        # Common keyboard mash sequences
        if any(km in t for km in ("asdf", "sdfg", "dfgh", "fghj", "ghjk", "qwerty", "zxcvb")):
            return True
        words = t.split()
        for w in words:
            if len(w) >= 4 and not re.search(r"[aeiouy]", w):
                return True
            if re.match(r"^(.)\1{3,}$", w):
                return True
        return False

    def _check_ambiguity(self, text_lower: str) -> Optional[str]:
        """Checks if the origin is one of the ambiguous Indian place names."""
        tokens = re.split(r"[\s,;]+", text_lower)
        for ambig in AMBIGUOUS_INDIAN_PLACES:
            if ambig in tokens or text_lower == ambig:
                return ambig
        return None

    def _find_in_curated_registry(self, text_lower: str) -> Optional[Dict[str, Any]]:
        """Finds matching hub in curated registry."""
        # Direct key match
        if text_lower in INDIAN_GEO_REGISTRY:
            return INDIAN_GEO_REGISTRY[text_lower]

        # Token match (e.g. "from Mandi town" -> "mandi")
        tokens = re.split(r"[\s,;]+", text_lower)
        for token in tokens:
            if token in INDIAN_GEO_REGISTRY:
                return INDIAN_GEO_REGISTRY[token]

        return None

    def _extract_state_and_city(self, text: str) -> Optional[Tuple[str, str]]:
        """Parses city and state qualifier (e.g. 'Palampur, Himachal Pradesh')."""
        if "," in text:
            parts = [p.strip() for p in text.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return (parts[0], parts[1])
        return None

    def _build_from_hub(self, raw_input: str, hub: Dict[str, Any], source: str) -> ResolvedLocation:
        return ResolvedLocation(
            raw_input=raw_input,
            clean_name=hub["name"],
            base_town=hub["name"],
            district=hub.get("district"),
            state=hub.get("state"),
            nearest_railway_station=hub.get("railway"),
            nearest_bus_terminal=hub.get("bus"),
            nearest_airport=hub.get("airport"),
            primary_gateway_hub=hub.get("gateway", "New Delhi"),
            corridor_type=hub.get("corridor", "NORTHERN_CONNECTING"),
            approx_road_distance_to_katra_km=hub.get("dist_to_katra"),
            resolution_source=source,
            confidence=1.0,
            notes=hub.get("notes"),
        )

    def _build_manual_location(self, raw: str, state: str, district: str, clean_name: str) -> ResolvedLocation:
        # Determine gateway by state
        gateway = "New Delhi"
        if state in ("Jammu & Kashmir", "Jammu and Kashmir"):
            gateway = "Jammu / Katra"
            corridor = "JAMMU_CORRIDOR"
        elif state in ("Himachal Pradesh", "Punjab"):
            gateway = "Pathankot / Chandigarh"
            corridor = "NORTHERN_CONNECTING"
        elif state in ("Maharashtra", "Gujarat", "Goa"):
            gateway = "Mumbai / New Delhi"
            corridor = "WESTERN_CORRIDOR"
        else:
            corridor = "NATIONAL_INTERCONNECTING"

        return ResolvedLocation(
            raw_input=raw,
            clean_name=clean_name,
            base_town=clean_name,
            district=district,
            state=state,
            primary_gateway_hub=gateway,
            corridor_type=corridor,
            resolution_source="state_inferred_resolution",
            confidence=0.85,
            notes=f"Located in {district}, {state}. Primary connecting gateway: {gateway}.",
        )

    def _resolve_fallback_town(self, sub_name: str, base_town: str, raw: str) -> ResolvedLocation:
        """Resolves sub-location when the base town is not in the curated registry."""
        clean = f"{sub_name.title()} (near {base_town.title()})"
        return ResolvedLocation(
            raw_input=raw,
            clean_name=clean,
            base_town=base_town.title(),
            is_village_or_settlement=True,
            primary_gateway_hub="New Delhi / Jammu",
            corridor_type="RURAL_CONNECTING",
            resolution_source="sublocation_heuristic",
            confidence=0.8,
            notes=f"Rural settlement identified near {base_town.title()}. First leg will use local road/bus to {base_town.title()}.",
        )

    def _query_osm_or_fallback(self, raw: str, location_query: str, state_hint: Optional[str]) -> ResolvedLocation:
        """
        Attempts cached/live OpenStreetMap Nominatim lookup with a 2.0s timeout.
        If offline, rate-limited, or failed, falls back gracefully to structured heuristic.
        """
        cache_key = f"geo_osm_{re.sub(r'[^a-zA-Z0-9]', '_', location_query.lower())}"
        cached_val = self._cache.get(cache_key)
        if cached_val and isinstance(cached_val, dict):
            return ResolvedLocation(**cached_val)

        # Attempt safe live lookup
        query_str = f"{location_query}, India"
        if state_hint:
            query_str = f"{location_query}, {state_hint}, India"

        url = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({
                "q": query_str,
                "format": "json",
                "countrycodes": "in",
                "addressdetails": "1",
                "limit": "1",
            })
        )

        headers = {
            "User-Agent": "YatraAI-PilgrimageAssistant/1.0 (Educational Academic Project; contact@yatra-ai.local)",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and isinstance(data, list) and len(data) > 0:
                        top = data[0]
                        addr = top.get("address", {})
                        state = addr.get("state") or state_hint or "India"
                        district = addr.get("state_district") or addr.get("county") or addr.get("city")
                        display_name = top.get("display_name", location_query)
                        clean_city = (
                            addr.get("city")
                            or addr.get("town")
                            or addr.get("village")
                            or addr.get("hamlet")
                            or location_query.title()
                        )

                        # Determine primary connecting hub based on state
                        hub = "New Delhi"
                        corridor = "NATIONAL_INTERCONNECTING"
                        if state in ("Jammu and Kashmir", "Jammu & Kashmir"):
                            hub = "Jammu / Katra"
                            corridor = "JAMMU_CORRIDOR"
                        elif state in ("Himachal Pradesh", "Punjab"):
                            hub = "Pathankot / Chandigarh"
                            corridor = "NORTHERN_CONNECTING"
                        elif state in ("Maharashtra", "Gujarat"):
                            hub = "Mumbai / New Delhi"
                            corridor = "WESTERN_CORRIDOR"

                        res = ResolvedLocation(
                            raw_input=raw,
                            clean_name=clean_city,
                            base_town=clean_city,
                            district=district,
                            state=state,
                            primary_gateway_hub=hub,
                            corridor_type=corridor,
                            resolution_source="nominatim_osm_live",
                            confidence=0.88,
                            notes=f"Resolved via OpenStreetMap geographic registry in {district or state}, {state}.",
                        )
                        self._cache.set(cache_key, asdict(res), ttl=86400.0)
                        return res
        except Exception as exc:
            logger.debug("Nominatim live lookup skipped / timed out (%s); using graceful heuristic fallback.", exc)

        # Graceful fallback: Never reject!
        # Treat as an authentic Indian town/region
        clean_cap = location_query.title()
        fallback_res = ResolvedLocation(
            raw_input=raw,
            clean_name=clean_cap,
            base_town=clean_cap,
            state=state_hint,
            primary_gateway_hub="New Delhi / Jammu",
            corridor_type="GENERIC_INDIAN_ORIGIN",
            resolution_source="graceful_universal_fallback",
            confidence=0.75,
            notes=(
                f"Acknowledged starting point: {clean_cap}. "
                "Connecting route organized via nearest regional transport interchange to Katra."
            ),
        )
        self._cache.set(cache_key, asdict(fallback_res), ttl=3600.0)
        return fallback_res


# Global Singleton accessor
def get_geo_resolver() -> GeoResolver:
    return GeoResolver()
