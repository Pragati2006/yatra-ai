"""
agents/conversation_state.py
============================
Unified Travel Planning Conversation State & Intelligent Context Retention Module.

This module provides deterministic, reliable, multi-turn conversation state
management for Yatra AI, addressing Phase 13.3 requirements:
1. Structured conversation state fields (origin, destination, pilgrim_count,
   travel_date, return_date, duration_days, journey_type, transport_preference,
   accommodation_preference, budget, darshan_requirements, accessibility).
2. Entity extraction covering natural language variations (e.g. "two adults", "3 pilgrims",
   "couple", "family of 4", "add one more pilgrim", "travel by train instead").
3. Nationwide Indian origin support with alias normalization and connecting transit guidance.
4. Intelligent missing-slot evaluation: asks ONLY for truly missing details and never
   repeats questions for already supplied information.
5. Strict conversation and user isolation.
6. Zero fabrication of fares, seat counts, or live schedules for unverified corridors.
"""

import re
import json
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

# -----------------------------------------------------------------------------
# 1. Indian Cities & Location Normalization Registry
# -----------------------------------------------------------------------------

CITY_ALIASES = {
    # Delhi & NCR
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "ndls": "Delhi",
    "dli": "Delhi",
    "ncr": "Delhi",
    "noida": "Delhi",
    "gurgaon": "Delhi",
    "gurugram": "Delhi",
    "faridabad": "Delhi",
    "ghaziabad": "Delhi",

    # Maharashtra / West
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "bom": "Mumbai",
    "cstm": "Mumbai",
    "csmt": "Mumbai",
    "bct": "Mumbai",
    "navi mumbai": "Mumbai",
    "thane": "Mumbai",
    "pune": "Pune",
    "pnq": "Pune",
    "nagpur": "Nagpur",
    "nashik": "Nashik",
    "aurangabad": "Aurangabad",
    "chhatrapati sambhajinagar": "Aurangabad",

    # Gujarat
    "ahmedabad": "Ahmedabad",
    "adi": "Ahmedabad",
    "surat": "Surat",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
    "rajkot": "Rajkot",

    # Jammu & Kashmir / Punjab / Northern Corridor
    "jammu": "Jammu",
    "jammu tawi": "Jammu",
    "jat": "Jammu",
    "udhampur": "Udhampur",
    "katra": "Katra",
    "svdk": "Katra",
    "srinagar": "Srinagar",
    "chandigarh": "Chandigarh",
    "cdg": "Chandigarh",
    "amritsar": "Amritsar",
    "asr": "Amritsar",
    "ludhiana": "Ludhiana",
    "jalandhar": "Jalandhar",
    "pathankot": "Pathankot",
    "bathinda": "Bathinda",
    "shimla": "Shimla",
    "dharamshala": "Dharamshala",
    "manali": "Manali",
    "dehradun": "Dehradun",
    "haridwar": "Haridwar",
    "rishikesh": "Rishikesh",

    # Rajasthan
    "jaipur": "Jaipur",
    "jp": "Jaipur",
    "jodhpur": "Jodhpur",
    "udaipur": "Udaipur",
    "bikaner": "Bikaner",
    "ajmer": "Ajmer",
    "kota": "Kota",

    # Central & UP / Bihar
    "lucknow": "Lucknow",
    "lko": "Lucknow",
    "kanpur": "Kanpur",
    "varanasi": "Varanasi",
    "banaras": "Varanasi",
    "kashi": "Varanasi",
    "bsb": "Varanasi",
    "prayagraj": "Prayagraj",
    "allahabad": "Prayagraj",
    "ald": "Prayagraj",
    "agra": "Agra",
    "gorakhpur": "Gorakhpur",
    "mathura": "Mathura",
    "ayodhya": "Ayodhya",
    "bhopal": "Bhopal",
    "bpl": "Bhopal",
    "indore": "Indore",
    "idr": "Indore",
    "gwalior": "Gwalior",
    "jabalpur": "Jabalpur",
    "patna": "Patna",
    "pnbe": "Patna",
    "gaya": "Gaya",

    # East & North-East
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "ccu": "Kolkata",
    "hwh": "Kolkata",
    "howrah": "Kolkata",
    "bhubaneswar": "Bhubaneswar",
    "bbs": "Bhubaneswar",
    "cuttack": "Cuttack",
    "ranchi": "Ranchi",
    "jamshedpur": "Jamshedpur",
    "guwahati": "Guwahati",
    "ghy": "Guwahati",
    "shillong": "Shillong",
    "siliguri": "Siliguri",

    # South India
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "blr": "Bangalore",
    "sbc": "Bangalore",
    "chennai": "Chennai",
    "madras": "Chennai",
    "mas": "Chennai",
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "sc": "Hyderabad",
    "kochi": "Kochi",
    "cochin": "Kochi",
    "cok": "Kochi",
    "thiruvananthapuram": "Thiruvananthapuram",
    "trivandrum": "Thiruvananthapuram",
    "trv": "Thiruvananthapuram",
    "coimbatore": "Coimbatore",
    "madurai": "Madurai",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "vijayawada": "Vijayawada",
}

# -----------------------------------------------------------------------------
# 1. Indian State Variants & Disambiguation Mapping
# -----------------------------------------------------------------------------

INDIAN_STATE_VARIANTS = {
    "himachal pradesh": "Himachal Pradesh",
    "himachal": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "chhattisgarh": "Chhattisgarh",
    "cg": "Chhattisgarh",
    "punjab": "Punjab",
    "pb": "Punjab",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "maharashtra": "Maharashtra",
    "mh": "Maharashtra",
    "bihar": "Bihar",
    "br": "Bihar",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "rajasthan": "Rajasthan",
    "rj": "Rajasthan",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "haryana": "Haryana",
    "hr": "Haryana",
    "gujarat": "Gujarat",
    "gj": "Gujarat",
    "karnataka": "Karnataka",
    "tamil nadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "kerala": "Kerala",
    "kl": "Kerala",
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    "assam": "Assam",
    "jharkhand": "Jharkhand",
    "jh": "Jharkhand",
    "uttarakhand": "Uttarakhand",
    "uk": "Uttarakhand",
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "telangana": "Telangana",
    "ts": "Telangana",
    "delhi": "Delhi",
    "goa": "Goa",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
}

# Stopwords that must not be mistaken for origin cities after "from"
DESTINATION_WORDS = {
    "katra", "vaishno", "devi", "vaishno devi", "mata vaishno devi", "bhawan", "sanjichhat",
    "adhkuwari", "ardhkuwari", "bhairon ghati", "bhairavnath", "banganga",
    "charan paduka", "himkoti", "tarakote", "jammu", "patnitop", "shiv khori",
    "srinagar", "kashmir", "gulmarg", "pahalgam",
}

ORIGIN_STOPWORDS = {
    "the", "a", "an", "my", "our", "here", "there", "home", "next", "this",
    "that", "it", "them", "these", "those", "last", "for", "with", "by", "in",
    "during", "and", "to", "or", "on", "at", "around", "travelling", "traveling",
    "visiting", "going", "planning", "train", "flight", "bus", "is", "city",
    "starting", "from", "change", "make", "instead", "rather", "want", "prefer",
    "meant", "trip", "yatra", "day", "days", "duration", "time", "date", "dates",
    "cost", "price", "amount", "total", "people", "pax", "person", "persons",
    "pilgrim", "pilgrims", "members", "traveller", "travellers", "traveler",
    "travelers", "adult", "adults", "child", "children", "kids", "senior",
    "seniors", "relaxed", "budget", "family", "solo", "couple", "friends",
    "group", "pilgrimage", "now", "today", "tomorrow", "yesterday",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "tonight", "morning", "evening", "night", "week", "month", "year",
    "weekend", "start", "leave", "depart",
}

# -----------------------------------------------------------------------------
# 2. Number Words Mapping
# -----------------------------------------------------------------------------

WORDS_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "twenty": 20, "single": 1,
}

# -----------------------------------------------------------------------------
# 3. Deterministic Entity Extraction Functions
# -----------------------------------------------------------------------------

def extract_pilgrim_count(text: str, current_pax: Optional[int] = None) -> Tuple[Optional[int], bool]:
    """
    Extracts number of pilgrims from text.
    Supports digits, word numbers, 'adults', 'children', 'couple', 'solo',
    and incremental adjustments ('add one more pilgrim').
    Returns (pax_count, is_explicit).
    """
    if not text:
        return None, False

    t = text.lower().strip()

    # 1. Incremental addition: "add one more pilgrim", "add 2 more people"
    add_match = re.search(r"\badd\s+(\d+|one|two|three|four|five)\s*(?:more\s+)?(?:pilgrim|person|people|pax|member|traveller|adult)?s?\b", t)
    if add_match:
        val_str = add_match.group(1)
        inc = WORDS_TO_NUM.get(val_str, int(val_str) if val_str.isdigit() else 1)
        base = current_pax if (current_pax and current_pax > 0) else 1
        return base + inc, True

    # 2. Explicit replacement: "change to 3 pilgrims", "make it 4", "change pilgrims to 5"
    change_match = re.search(r"\b(?:change|update|set|make\s+it|make\s+that)\s+(?:pax|pilgrims|travellers|people|count\s+to|to)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", t)
    if change_match:
        val_str = change_match.group(1)
        num = WORDS_TO_NUM.get(val_str, int(val_str) if val_str.isdigit() else None)
        if num and num > 0:
            return num, True

    # 3. Multi-group combination: "2 adults and 1 child", "two adults and two kids"
    combo_match = re.search(
        r"\b(\d+|one|two|three|four|five|six)\s*(?:adults?|grown-ups?)\s*(?:and|&|\+)\s*(\d+|one|two|three|four|five)\s*(?:children|child|kids?|minors?)\b",
        t
    )
    if combo_match:
        a_str, c_str = combo_match.group(1), combo_match.group(2)
        a_num = WORDS_TO_NUM.get(a_str, int(a_str) if a_str.isdigit() else 0)
        c_num = WORDS_TO_NUM.get(c_str, int(c_str) if c_str.isdigit() else 0)
        if a_num + c_num > 0:
            return a_num + c_num, True

    # 4. Standard count with noun (digits): e.g. "2 adults", "3 pilgrims", "4 people", "5 travellers"
    digit_match = re.search(
        r"(\d+)\s*(?:people|pax|person|persons|members|pilgrims|travellers|travelers|adults|adult|seniors|children|kids)\b",
        t
    )
    if digit_match:
        return max(1, int(digit_match.group(1))), True

    # 5. Standard count with noun (word numbers): e.g. "two adults", "three pilgrims", "four people"
    for word, num in WORDS_TO_NUM.items():
        if re.search(r"\b" + word + r"\s*(?:people|pax|person|persons|members|pilgrims|travellers|travelers|adults|adult|seniors|children|kids)\b", t):
            return num, True

    # 6. Specific phrasing: "we are 3", "5 of us", "there will be 5 of us", "group of 4", "family of 5"
    of_us_match = re.search(
        r"\b(?:there\s+will\s+be|there\s+are|we\s+are|it\s+is|it\s+will\s+be)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+of\s+us\b",
        t
    )
    if of_us_match:
        val_str = of_us_match.group(1)
        num = WORDS_TO_NUM.get(val_str, int(val_str) if val_str.isdigit() else None)
        if num and num > 0:
            return num, True

    phrase_match = re.search(
        r"\b(?:we\s+are|there\s+will\s+be|there\s+are|group\s+of|family\s+of|total\s+of)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        t
    )
    if phrase_match:
        val_str = phrase_match.group(1)
        num = WORDS_TO_NUM.get(val_str, int(val_str) if val_str.isdigit() else None)
        if num and not re.search(r"\b" + str(val_str) + r"\s*days?\b", t):
            return num, True

    # 7. Idiomatic group indicators: "couple" -> 2, "solo" -> 1
    if re.search(r"\b(?:couple|me\s+and\s+my\s+(?:wife|husband|spouse|partner))\b", t):
        return 2, True
    if re.search(r"\b(?:solo|alone|just\s+me|just\s+myself|travelling\s+alone)\b", t):
        return 1, True
    if re.search(r"\b(?:me\s+and\s+my\s+parents)\b", t):
        return 3, True

    # 8. "for X" where X is a word or digit, not followed by days
    for_match = re.search(r"\bfor\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", t)
    if for_match:
        val_str = for_match.group(1)
        if not re.search(r"\bfor\s+" + val_str + r"\s*days?\b", t):
            num = WORDS_TO_NUM.get(val_str, int(val_str) if val_str.isdigit() else None)
            if num:
                return num, True

    return None, False


def extract_origin_city(text: str) -> Optional[str]:
    """
    Extracts and normalizes the departure/origin location from free text.
    Supports arbitrary Indian cities, towns, and transit hubs.
    Prevents Katra/Vaishno Devi destinations from being misclassified as origin.
    """
    if not text:
        return None

    t = text.strip()

    # 0. Check for sub-location / rural / village pattern via GeoResolver:
    try:
        from services.geo_resolver import get_geo_resolver
        geo = get_geo_resolver()
        if re.search(r"\b(?:village|hamlet|settlement|township|kasba|gram|remote|near)\b", t, re.IGNORECASE):
            resolved = geo.resolve_origin(t)
            if resolved and resolved.is_village_or_settlement:
                return resolved.clean_name
    except Exception:
        pass

    # Pattern 0A: Check for State-qualified origins (e.g. 'Bilaspur in Himachal Pradesh', 'Bilaspur, HP', 'Bilaspur CG', 'Anandpur in Punjab', 'Aurangabad, Bihar')
    for state_cand_raw, canon_state in sorted(INDIAN_STATE_VARIANTS.items(), key=lambda x: len(x[0]), reverse=True):
        state_match = re.search(
            r"(?:(?:from|out\s+of|leaving(?:\s+from)?|travelling\s+from|traveling\s+from|departing\s+from|starting\s+from|departure(?:\s+from)?|actually\s+from)\s+)?\b([A-Za-z]+)\b\s*(?:in|,|\s)\s*\b" + re.escape(state_cand_raw) + r"\b",
            t,
            re.IGNORECASE,
        )
        if state_match:
            city_cand = state_match.group(1).strip()
            if city_cand.lower() not in ORIGIN_STOPWORDS and city_cand.lower() not in DESTINATION_WORDS:
                if len(city_cand) >= 3:
                    return f"{city_cand.capitalize()}, {canon_state}"

    # Pattern A: Explicit origin markers
    explicit_pat = (
        r"\b(?:from|out\s+of|leaving(?:\s+from)?|travelling\s+from|traveling\s+from|"
        r"departing\s+from|starting\s+from|starting\s+city\s+(?:to|is)?|origin(?:\s+is)?|"
        r"we\s+are\s+from|i\s+am\s+from|coming\s+from|start\s+from|"
        r"departure\s+(?:city\s+)?(?:to|is|from)?|"
        r"(?:change|switch|make|set|update)\s+(?:the\s+|my\s+)?(?:departure\s+city|starting\s+city|departure|origin|city)\s*(?:to|as)?|"
        r"switch\s+(?:origin|city|departure)?\s*to|"
        r"flying\s+from|fly\s+from|train\s+from|bus\s+from|actually\s+from)\s+([A-Za-z\s]+)"
    )
    m = re.search(explicit_pat, t, re.IGNORECASE)
    if m:
        candidate_raw = m.group(1).strip()
        words = re.split(r"[\s,;]+", candidate_raw)
        clean_words = []
        for w in words:
            wl = w.lower()
            if wl in ORIGIN_STOPWORDS or wl in DESTINATION_WORDS:
                break
            if re.match(r"^[A-Za-z]+$", w):
                clean_words.append(w)
            if len(clean_words) >= 3:  # City names rarely exceed 3 words
                break

        if clean_words:
            candidate = " ".join(clean_words).strip()
            # Normalize candidate
            cand_lower = candidate.lower()
            if cand_lower in CITY_ALIASES:
                return CITY_ALIASES[cand_lower]
            if cand_lower not in DESTINATION_WORDS and len(candidate) >= 3:
                return " ".join([w.capitalize() for w in clean_words])

    # Pattern B: Direct city mentions if text is very short (e.g. user answering "Delhi" or "Pune")
    cleaned_short = re.sub(r"[^A-Za-z\s]", "", t).strip()
    words = cleaned_short.split()
    if 1 <= len(words) <= 3:
        cand_lower = cleaned_short.lower()
        if cand_lower in CITY_ALIASES:
            return CITY_ALIASES[cand_lower]
        if all(w.lower() not in ORIGIN_STOPWORDS and w.lower() not in DESTINATION_WORDS for w in words):
            if len(cleaned_short) >= 3:
                return " ".join([w.capitalize() for w in words])

    return None


def extract_destination_location(text: str) -> Optional[str]:
    """
    Extracts the destination location from text if mentioned.
    Returns None if no specific destination is mentioned.
    """
    if not text:
        return None

    t = text.lower()
    if "patnitop" in t:
        return "Patnitop"
    if "shiv khori" in t:
        return "Shiv Khori"
    if "srinagar" in t and "from srinagar" not in t:
        return "Srinagar"
    if "jammu" in t and "jammu tawi" not in t and "from jammu" not in t:
        if "to jammu" in t or "visit jammu" in t or "stay in jammu" in t:
            return "Jammu"
    if "katra" in t or "vaishno" in t or "bhawan" in t or "darshan" in t:
        return "Katra"

    return None


def extract_travel_mode(text: str) -> Optional[str]:
    """Extracts preferred mode of transport."""
    if not text:
        return None
    t = text.lower()
    if re.search(r"\b(train|rail|railway|vande\s+bharat|express)\b", t):
        return "train"
    if re.search(r"\b(flight|fly|flying|plane|air|airline)\b", t):
        return "flight"
    if re.search(r"\b(bus|volvo|coach|road)\b", t):
        return "bus"
    if re.search(r"\b(helicopter|heli)\b", t):
        return "helicopter"
    return None


def extract_darshan_category(text: str) -> Optional[str]:
    """Extracts darshan category."""
    if not text:
        return None
    t = text.lower()
    if "helicopter" in t or "heli" in t:
        return "Helicopter Darshan"
    if "vip" in t or "special aarti" in t or "atka aarti" in t:
        return "VIP Darshan"
    if "normal" in t or "general" in t or "standard darshan" in t:
        return "Normal Darshan"
    return None


def extract_duration_days(text: str) -> Optional[int]:
    """Extracts duration of trip in days."""
    if not text:
        return None
    t = text.lower()
    m = re.search(r"(\d+)\s*[\s-]*days?\b", t)
    if m:
        return int(m.group(1))
    for word, num in WORDS_TO_NUM.items():
        if re.search(r"\b" + word + r"\s*[\s-]*days?\b", t):
            return num
    # Nights + 1 logic (e.g. 3 nights 4 days or 2 nights)
    nm = re.search(r"(\d+)\s*nights?\b", t)
    if nm:
        return int(nm.group(1)) + 1
    return None


def extract_budget_preference(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extracts budget value and style."""
    if not text:
        return None, None
    t = text.lower()
    bm = re.search(r"(?:₹|rs\.?|inr|budget\s*(?:of|is)?)\s*(\d+(?:,\d+)?(?:\s*k)?)", t)
    if bm:
        raw_val = bm.group(1).replace(",", "").strip()
        if raw_val.endswith("k"):
            val = float(raw_val[:-1]) * 1000
        else:
            val = float(raw_val)
        return val, "custom"

    if re.search(r"\b(luxury|premium|deluxe|5-star|five\s+star)\b", t):
        return None, "luxury"
    if re.search(r"\b(budget|economy|cheap|affordable|dharamshala)\b", t):
        return None, "budget"
    if re.search(r"\b(balanced|standard|moderate)\b", t):
        return None, "balanced"

    return None, None


def extract_accessibility_needs(text: str) -> List[str]:
    """Extracts accessibility and elderly pilgrim assistance requests."""
    if not text:
        return []
    t = text.lower()
    needs = []
    if re.search(r"\b(battery\s*car|electric\s*car)\b", t):
        needs.append("battery_car")
    if re.search(r"\b(wheelchair|physically\s*challenged|handicap|disabled)\b", t):
        needs.append("wheelchair")
    if re.search(r"\b(senior|elderly|parents|grandparents|old\s*age)\b", t):
        needs.append("senior_citizen")
    if re.search(r"\b(palki|palanquin)\b", t):
        needs.append("palki")
    if re.search(r"\b(pony|horse|ghodi)\b", t):
        needs.append("pony")
    return needs


MONTH_NAME_TO_NUM = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def extract_travel_dates(text: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Extracts start_date and return_date as YYYY-MM-DD.
    Returns (start_date, return_date, is_ambiguous).
    Detects ambiguous slash/dot formats like 05/06/2026.
    """
    if not text:
        return None, None, False

    t = text.strip()
    is_ambiguous = False
    start_date = None
    return_date = None

    # Check for ambiguous numerical slash/dot date (e.g. 05/06/2026 or 06/05/2026)
    slash_match = re.search(r"\b(\d{1,2})[/\.](\d{1,2})[/\.](\d{4})\b", t)
    if slash_match:
        n1, n2, y = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        if 1 <= n1 <= 12 and 1 <= n2 <= 12 and n1 != n2:
            is_ambiguous = True

    months_pat = "|".join(MONTH_NAME_TO_NUM.keys())
    # Match "15 December 2026" or "15th Dec 2026"
    dm_match = re.findall(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({months_pat})\b(?:\s*,?\s*(\d{{4}}))?",
        t,
        re.I
    )
    # Match "December 15, 2026"
    md_match = re.findall(
        rf"\b({months_pat})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:\s*,?\s*(\d{{4}}))?",
        t,
        re.I
    )

    found_dates = []
    for day_str, m_str, y_str in dm_match:
        d = int(day_str)
        m = MONTH_NAME_TO_NUM[m_str.lower()]
        y = int(y_str) if y_str else 2026
        if 1 <= d <= 31:
            found_dates.append(f"{y:04d}-{m:02d}-{d:02d}")

    for m_str, day_str, y_str in md_match:
        d = int(day_str)
        m = MONTH_NAME_TO_NUM[m_str.lower()]
        y = int(y_str) if y_str else 2026
        if 1 <= d <= 31:
            ds = f"{y:04d}-{m:02d}-{d:02d}"
            if ds not in found_dates:
                found_dates.append(ds)

    # ISO dates: YYYY-MM-DD
    iso_match = re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    for y, m, d in iso_match:
        ds = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        if ds not in found_dates:
            found_dates.append(ds)

    if found_dates:
        start_date = found_dates[0]
        if len(found_dates) > 1:
            return_date = found_dates[1]

    return start_date, return_date, is_ambiguous


def extract_own_vehicle(text: str) -> bool:
    """Extracts whether the user is travelling using their own vehicle/car."""
    if not text:
        return False
    t = text.lower()
    return bool(re.search(
        r"\b(own\s+vehicle|own\s+car|our\s+own\s+vehicle|our\s+own\s+car|my\s+own\s+car|my\s+own\s+vehicle|"
        r"personal\s+vehicle|personal\s+car|driving\s+down|driving\s+our\s+car|driving\s+by\s+car|"
        r"by\s+own\s+car|by\s+our\s+car|with\s+our\s+car|in\s+our\s+own\s+vehicle|in\s+my\s+own\s+car|"
        r"drive\s+down|driving\s+to\s+katra|by\s+road\s+in\s+my\s+car)\b",
        t
    ))


def extract_hotel_preference(text: str) -> Tuple[Optional[bool], Optional[str], Optional[int]]:
    """
    Extracts hotel booking selection, category, and night count.
    Returns (hotel_selected, category, nights).
    """
    if not text:
        return None, None, None
    t = text.lower()
    hotel_selected = None
    hotel_cat = None
    nights = None

    if re.search(r"\b(no\s+hotel|without\s+hotel|don't\s+need\s+(a\s+)?hotel|dont\s+need\s+(a\s+)?hotel|no\s+stay|own\s+stay|own\s+arrangement\s+for\s+stay|stay\s+with\s+(friends?|relatives?|family)|no\s+accommodation)\b", t):
        hotel_selected = False
    elif re.search(r"\b(need\s+(a\s+)?hotel|book\s+(a\s+)?hotel|hotel\s+booking|require\s+(a\s+)?hotel|with\s+hotel|hotel\s+in\s+katra|standard\s+hotel|budget\s+hotel|luxury\s+hotel|hotel\s+stay|need\s+accommodation)\b", t):
        hotel_selected = True

    nm = re.search(r"\b(\d+)\s*(?:nights?|night\s+stay)\b", t)
    if nm:
        nights = int(nm.group(1))

    if re.search(r"\b(luxury|5\s*star|deluxe)\b", t):
        hotel_cat = "Luxury"
    elif re.search(r"\b(budget|dormitory|cheap)\b", t):
        hotel_cat = "Budget"
    elif re.search(r"\b(standard|moderate)\b", t):
        hotel_cat = "Standard"

    return hotel_selected, hotel_cat, nights


def extract_transport_preference(text: str) -> Tuple[Optional[bool], Optional[str]]:
    """
    Extracts transport booking selection and mode.
    Returns (transport_selected, mode).
    """
    if not text:
        return None, None
    t = text.lower()
    if extract_own_vehicle(text):
        return False, "own_vehicle"
    if re.search(r"\b(no\s+transport|without\s+transport|don't\s+need\s+transport|dont\s+need\s+transport)\b", t):
        return False, None
    if re.search(r"\b(train|flight|bus|cab|taxi|helicopter|transport\s+needed|book\s+transport|need\s+transport|travel\s+by\s+train|travel\s+by\s+flight|travel\s+by\s+bus)\b", t):
        mode = "train"
        if "flight" in t or "air" in t:
            mode = "flight"
        elif "bus" in t:
            mode = "bus"
        elif "cab" in t or "taxi" in t:
            mode = "cab"
        elif "helicopter" in t:
            mode = "helicopter"
        return True, mode
    return None, None


def extract_pilgrim_records(text: str, total_pax: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Extracts individual pilgrim records from conversation.
    Returns a list of dicts: [{'full_name': '...', 'age': ...}]
    """
    if not text:
        return []

    pilgrims = []

    # 1. Primary booker phrasing: "My name is X and I am Y" / "I am X, age Y"
    me_match = re.search(
        r"(?:my\s+name\s+is|i\s+am|myself)\s+([A-Za-z]+)(?:\s*,?\s*(?:and\s+)?(?:i\s+am\s+)?(?:age\s+)?(\d{1,3}))?",
        text,
        re.I
    )
    if me_match:
        p_name = me_match.group(1).strip().capitalize()
        p_age = int(me_match.group(2)) if me_match.group(2) else None
        if p_name.lower() not in ("planning", "travelling", "going", "looking", "interested", "from", "with"):
            pilgrims.append({"full_name": p_name, "age": p_age})

    # 2. Pattern for lists: "Name, age 20", "Name - 20", "Name (20)", "Name: 20", "Name is 20"
    list_items = re.findall(
        r"\b([A-Z][a-zA-Z]+)\s*(?:,|:|-|\()?\s*(?:age|aged|is)?\s*(\d{1,3})\s*(?:\)|years?\s*old)?\b",
        text
    )
    for name, age_str in list_items:
        clean_name = name.strip().capitalize()
        if clean_name.lower() in (
            "we", "are", "people", "person", "pilgrim", "pilgrims", "adult", "adults",
            "december", "january", "november", "october", "katra", "delhi", "jammu",
            "hotel", "yatra", "train", "flight", "bus", "car", "start", "travel"
        ):
            continue
        age = int(age_str)
        if 1 <= age <= 120:
            if not any(p["full_name"].lower() == clean_name.lower() for p in pilgrims):
                pilgrims.append({"full_name": clean_name, "age": age})

    return pilgrims


def extract_primary_contact(text: str, pilgrims: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Extracts primary contact booker information (name, phone, email)."""
    contact = {"name": "", "phone": "", "email": ""}
    if not text:
        return contact

    pm = re.search(r"\b(?:\+?91[\s-]?)?([6-9]\d{9})\b", text)
    if pm:
        contact["phone"] = pm.group(1)

    em = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
    if em:
        contact["email"] = em.group(1)

    nm = re.search(
        r"(?:my\s+name\s+is|i\s+am|contact(?:\s+person)?(?:\s+is)?|booker(?:\s+is)?)\s+([A-Za-z]+)",
        text,
        re.I
    )
    if nm:
        cand = nm.group(1).strip().capitalize()
        if cand.lower() not in ("planning", "travelling", "going", "looking", "interested", "from", "on", "with"):
            contact["name"] = cand
    elif pilgrims and len(pilgrims) > 0 and pilgrims[0].get("full_name"):
        contact["name"] = pilgrims[0]["full_name"]

    return contact


# -----------------------------------------------------------------------------
# 4. Nationwide Connecting Transit Guidance (Part D)
# -----------------------------------------------------------------------------

TRANSIT_HUBS_DIRECT = {
    "Delhi", "Jammu", "Udhampur", "Katra", "Amritsar", "Chandigarh",
    "Ludhiana", "Jalandhar", "Pathankot", "Jaipur", "Jodhpur", "Ahmedabad",
    "Bhopal", "Indore", "Lucknow", "Varanasi", "Patna", "Haridwar",
    "Rishikesh", "Pune", "Mumbai", "Kolkata", "Bangalore", "Bengaluru",
    "Chennai", "Hyderabad", "Srinagar", "Dharamshala", "Manali", "Mandi", "Shimla",
}

REGION_CONNECTING_GUIDANCE = {
    # Maharashtra / West
    "Pune": {
        "hub": "Mumbai / New Delhi",
        "guidance": "From Pune, pilgrims typically take an express train or short flight to Mumbai (CSMT/BCT) or New Delhi (NDLS), connecting directly to the Vande Bharat Express or direct trains to SVDK / Katra.",
    },
    "Nagpur": {
        "hub": "New Delhi",
        "guidance": "From Nagpur, express trains (e.g. Andaman Express / Grand Trunk connecting via NDLS) or flights connect to Jammu and Katra.",
    },
    # Gujarat
    "Surat": {
        "hub": "Ahmedabad / Mumbai",
        "guidance": "From Surat, direct superfast trains run via Ahmedabad (Sarvodaya Exp) to Katra, or pilgrims connect via Mumbai/Delhi.",
    },
    "Vadodara": {
        "hub": "Ahmedabad",
        "guidance": "From Vadodara, direct express trains (Sarvodaya Exp) connect via Ahmedabad to SVDK Katra.",
    },
    # Rajasthan
    "Jaipur": {
        "hub": "Delhi / Jammu",
        "guidance": "From Jaipur, daily trains (Pooja SF Express 12413 / Shalimar Exp) run directly to Jammu Tawi, or pilgrims connect via New Delhi.",
    },
    "Jodhpur": {
        "hub": "Delhi",
        "guidance": "From Jodhpur, overnight trains connect to New Delhi, followed by the morning Vande Bharat to Katra.",
    },
    # UP / Bihar / Central
    "Lucknow": {
        "hub": "Delhi / Jammu",
        "guidance": "From Lucknow, direct trains (Begampura Express 12237) run to Jammu Tawi, or pilgrims travel via New Delhi to Katra.",
    },
    "Varanasi": {
        "hub": "Delhi / Jammu",
        "guidance": "From Varanasi, direct trains (Begampura Express 12237) connect to Jammu Tawi, or pilgrims take direct flights to New Delhi / Jammu.",
    },
    "Kanpur": {
        "hub": "Delhi",
        "guidance": "From Kanpur, frequent Shatabdi and Vande Bharat trains reach New Delhi (4.5h), with seamless onward connections to SVDK Katra.",
    },
    "Patna": {
        "hub": "Delhi",
        "guidance": "From Patna, direct express trains (Archana Express 12355) run to Jammu Tawi twice weekly, or pilgrims connect via New Delhi.",
    },
    "Bhopal": {
        "hub": "Delhi",
        "guidance": "From Bhopal, direct trains (Malwa Express 12919) run directly to Shri Mata Vaishno Devi Katra (SVDK).",
    },
    "Indore": {
        "hub": "Delhi",
        "guidance": "From Indore, the Malwa Express (12919) connects directly to Shri Mata Vaishno Devi Katra (SVDK).",
    },
    # South India
    "Hyderabad": {
        "hub": "New Delhi / Jammu",
        "guidance": "From Hyderabad, daily flights connect to Jammu (IXJ with DEL layover) or direct express trains (e.g. Telangana Exp) reach New Delhi for the Vande Bharat to Katra.",
    },
    "Kochi": {
        "hub": "New Delhi / Bangalore",
        "guidance": "From Kochi, flights operate via New Delhi or Bengaluru to Jammu Civil Enclave (IXJ), or direct long-distance trains (Himsagar Express) connect to Katra.",
    },
    # North-East
    "Guwahati": {
        "hub": "New Delhi / Kolkata",
        "guidance": "From Guwahati, connecting flights operate via New Delhi to Jammu (IXJ), or the Lohit Express (15651) runs weekly to Jammu Tawi.",
    },
}


def get_transit_guidance_for_origin(origin: str) -> Dict[str, Any]:
    """
    Returns authentic route status for an origin city:
    - is_direct_curated: whether direct static timetable schedules are in local dataset
    - transit_hub: recommended connecting hub if not direct
    - guidance_text: truthful travel guidance without inventing fares or flight numbers
    """
    norm = CITY_ALIASES.get(origin.lower(), origin)
    if norm in TRANSIT_HUBS_DIRECT:
        return {
            "origin": norm,
            "has_verified_direct": True,
            "transit_hub": None,
            "guidance_text": f"Direct verified schedules from {norm} to Jammu / Katra are available in our curated registry.",
        }

    # Universal Origin & Connecting Journey Engine integration
    try:
        from services.connecting_journey_engine import get_connecting_journey_engine
        engine = get_connecting_journey_engine()
        conn_res = engine.plan_connecting_journey(origin)
        if conn_res and conn_res.get("status") == "CONNECTING_ROUTES_AVAILABLE":
            resolved = conn_res.get("resolved_location", {})
            gateway = resolved.get("primary_gateway_hub") or "New Delhi / Jammu"
            return {
                "origin": resolved.get("clean_name", origin),
                "has_verified_direct": False,
                "transit_hub": gateway,
                "guidance_text": conn_res.get("strategy_summary"),
                "connecting_options": conn_res.get("options", []),
                "fallback_level": conn_res.get("fallback_level"),
            }
        elif conn_res and conn_res.get("status") == "NEEDS_CLARIFICATION":
            return {
                "origin": origin,
                "has_verified_direct": False,
                "transit_hub": None,
                "guidance_text": conn_res.get("clarification_prompt"),
                "requires_clarification": True,
                "clarification_prompt": conn_res.get("clarification_prompt"),
                "fallback_level": "Level 5: Additional Clarification",
            }
        elif conn_res and conn_res.get("status") == "UNRESOLVED_LOCATION":
            return {
                "origin": origin,
                "has_verified_direct": False,
                "transit_hub": None,
                "guidance_text": conn_res.get("clarification_prompt"),
                "requires_clarification": True,
                "is_invalid": True,
                "clarification_prompt": conn_res.get("clarification_prompt"),
                "fallback_level": "Level 5: Unresolved Location",
            }
    except Exception:
        pass

    info = REGION_CONNECTING_GUIDANCE.get(norm)
    if info:
        return {
            "origin": norm,
            "has_verified_direct": False,
            "transit_hub": info["hub"],
            "guidance_text": info["guidance"],
        }

    return {
        "origin": norm,
        "has_verified_direct": False,
        "transit_hub": "New Delhi / Jammu",
        "guidance_text": (
            f"From {norm}, direct timetable telemetry to Katra/Jammu is not in our verified prototype dataset. "
            "Pilgrims generally connect via New Delhi (NDLS) or Jammu Tawi (JAT) by express train or flight. "
            "We can plan your Katra stay, yatra registration, and darshan itinerary seamlessly."
        ),
    }


# -----------------------------------------------------------------------------
# 5. Core State Merge & Slot Logic
# -----------------------------------------------------------------------------

def update_conversation_state(text: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extracts all travel planning entities from text and merges with existing conversation state.
    Preserves all previously supplied information.
    Applies explicit corrections and updates.
    """
    raw_state = current_state or {}
    if "state" in raw_state and isinstance(raw_state["state"], dict):
        st = dict(raw_state["state"])
        is_full_session = True
    else:
        st = dict(raw_state)
        is_full_session = False
    req = dict(st.get("requirements") or {})
    explicit_fields = set(req.get("_explicit_fields") or [])

    # 1. Pax
    pax_val, is_explicit_pax = extract_pilgrim_count(text, current_pax=req.get("pax"))
    if is_explicit_pax and pax_val is not None:
        req["pax"] = pax_val
        req["pilgrim_count"] = pax_val
        req["_pax_explicit"] = True
        explicit_fields.add("pax")
    elif not req.get("pax"):
        req["pax"] = 1
        req["pilgrim_count"] = 1

    # 1.5 Pending Ambiguity Disambiguation (Follow-up Turn)
    pending_amb = st.get("pending_ambiguity") or req.get("pending_ambiguity")
    t_clean = text.lower().strip()
    origin_val = extract_origin_city(text)

    if pending_amb:
        p_lower = pending_amb.lower()
        disambiguated = None
        # Check if user provides state or district that resolves the pending ambiguous origin
        if p_lower == "bilaspur":
            if any(w in t_clean for w in ("himachal", "hp")):
                disambiguated = "Bilaspur, Himachal Pradesh"
            elif any(w in t_clean for w in ("chhattisgarh", "cg", "raipur")):
                disambiguated = "Bilaspur, Chhattisgarh"
        elif p_lower == "anandpur":
            if any(w in t_clean for w in ("punjab", "pb", "sahib", "rupnagar")):
                disambiguated = "Anandpur Sahib, Punjab"
            elif any(w in t_clean for w in ("odisha", "orissa", "kendujhar", "keonjhar")):
                disambiguated = "Anandpur, Odisha"
        elif p_lower == "aurangabad":
            if any(w in t_clean for w in ("maharashtra", "mh", "sambhaji")):
                disambiguated = "Aurangabad, Maharashtra"
            elif any(w in t_clean for w in ("bihar", "br")):
                disambiguated = "Aurangabad, Bihar"
        elif p_lower == "rampur":
            if any(w in t_clean for w in ("himachal", "hp", "bushahr", "shimla")):
                disambiguated = "Rampur, Himachal Pradesh"
            elif any(w in t_clean for w in ("uttar pradesh", "up", "moradabad")):
                disambiguated = "Rampur, Uttar Pradesh"
        elif p_lower == "pratapgarh":
            if any(w in t_clean for w in ("rajasthan", "rj")):
                disambiguated = "Pratapgarh, Rajasthan"
            elif any(w in t_clean for w in ("uttar pradesh", "up", "prayagraj", "allahabad")):
                disambiguated = "Pratapgarh, Uttar Pradesh"

        if disambiguated:
            req["origin"] = disambiguated
            explicit_fields.add("origin")
            st["pending_ambiguity"] = None
            req["pending_ambiguity"] = None
        elif origin_val and origin_val.lower() != p_lower:
            # User explicitly switched to a different origin
            req["origin"] = origin_val
            explicit_fields.add("origin")
            st["pending_ambiguity"] = None
            req["pending_ambiguity"] = None
    elif origin_val:
        req["origin"] = origin_val
        explicit_fields.add("origin")

    # 3. Destination
    dest_val = extract_destination_location(text)
    pilgrim_terms = (
        "vaishno", "devi", "katra", "bhawan", "darshan", "parchi", "yatra",
        "pilgrim", "pilgrims", "shrine", "temple", "ardhkuwari", "bhairon",
        "mata rani", "mata", "sanctum"
    )
    has_pilgrim_context = any(w in text.lower() for w in pilgrim_terms)

    if dest_val:
        req["destination"] = dest_val
        explicit_fields.add("destination")
    elif has_pilgrim_context:
        req["destination"] = "Katra"
        explicit_fields.add("destination")
    elif req.get("destination"):
        # Retain destination already established in conversation state
        pass
    elif origin_val:
        req["destination"] = None
    else:
        req["destination"] = "Katra"

    # 4. Mode
    mode_val = extract_travel_mode(text)
    if mode_val:
        req["mode"] = mode_val
        req["transport_preference"] = mode_val
        explicit_fields.add("mode")

    # 5. Darshan Category
    cat_val = extract_darshan_category(text)
    if cat_val:
        req["category"] = cat_val
        req["darshan_preference"] = cat_val
        explicit_fields.add("category")

    # 6. Duration
    dur_val = extract_duration_days(text)
    if dur_val:
        req["duration_days"] = dur_val
        explicit_fields.add("duration_days")

    # 7. Budget
    budget_val, budget_style = extract_budget_preference(text)
    if budget_val:
        req["total_budget"] = budget_val
        req["budget"] = budget_val
        explicit_fields.add("budget")
    if budget_style:
        req["travel_style"] = budget_style

    # 8. Accessibility
    acc_needs = extract_accessibility_needs(text)
    if acc_needs:
        existing_acc = list(req.get("accessibility_requirements") or [])
        for n in acc_needs:
            if n not in existing_acc:
                existing_acc.append(n)
        req["accessibility_requirements"] = existing_acc
        explicit_fields.add("accessibility_requirements")

    # 9. Travel Dates (start_date, return_date, date ambiguity)
    start_d, return_d, date_ambiguous = extract_travel_dates(text)
    if date_ambiguous:
        st["pending_date_ambiguity"] = True
        req["pending_date_ambiguity"] = True
    else:
        if start_d:
            req["start_date"] = start_d
            req["travel_date"] = start_d
            req["_date_explicit"] = True
            explicit_fields.add("start_date")
            st["pending_date_ambiguity"] = False
            req["pending_date_ambiguity"] = False
        if return_d:
            req["return_date"] = return_d
            explicit_fields.add("return_date")

    # 10. Own Vehicle Preference
    if extract_own_vehicle(text):
        req["own_vehicle"] = True
        req["transport_selected"] = False
        req["mode"] = "own_vehicle"
        req["transport_preference"] = "own_vehicle"
        explicit_fields.add("own_vehicle")

    # 11. Hotel Preference
    h_sel, h_cat, h_nights = extract_hotel_preference(text)
    if h_sel is not None:
        req["hotel_selected"] = h_sel
        explicit_fields.add("hotel_selected")
    if h_cat:
        req["hotel_category"] = h_cat
        req["accommodation_preference"] = h_cat
        explicit_fields.add("hotel_category")
    if h_nights:
        req["hotel_nights"] = h_nights
        explicit_fields.add("hotel_nights")

    # 12. Transport Selection
    t_sel, t_mode = extract_transport_preference(text)
    if t_sel is not None:
        req["transport_selected"] = t_sel
        explicit_fields.add("transport_selected")
    if t_mode and not req.get("own_vehicle"):
        req["mode"] = t_mode
        req["transport_preference"] = t_mode
        explicit_fields.add("mode")

    # 13. Individual Pilgrim Records
    extracted_pilgrims = extract_pilgrim_records(text, total_pax=req.get("pax"))
    if extracted_pilgrims:
        existing_pilgrims = list(req.get("pilgrims") or [])
        if len(extracted_pilgrims) >= len(existing_pilgrims):
            req["pilgrims"] = extracted_pilgrims
        else:
            merged = {p["full_name"].lower(): p for p in existing_pilgrims if p.get("full_name")}
            for p in extracted_pilgrims:
                merged[p["full_name"].lower()] = p
            req["pilgrims"] = list(merged.values())
        explicit_fields.add("pilgrims")

    # 14. Primary Contact / Booker Information
    contact = extract_primary_contact(text, pilgrims=req.get("pilgrims"))
    existing_contact = dict(req.get("primary_contact") or {})
    for k in ("name", "phone", "email"):
        if contact.get(k):
            existing_contact[k] = contact[k]
            explicit_fields.add(f"primary_contact_{k}")
    req["primary_contact"] = existing_contact

    req["_explicit_fields"] = list(explicit_fields)
    st["requirements"] = req
    if is_full_session:
        raw_state["state"] = st
        return raw_state
    return st


def evaluate_missing_slots(state: Dict[str, Any]) -> List[str]:
    """
    Evaluates what slots are genuinely missing and required for the next step.
    Never marks origin, destination, or pax as missing if they have already been provided.
    """
    req = state.get("requirements") or {}
    explicit = set(req.get("_explicit_fields") or [])
    missing = []

    # Date ambiguity clarification takes immediate priority
    if state.get("pending_date_ambiguity") or req.get("pending_date_ambiguity"):
        missing.append("date_clarification")
        return missing

    # Destination: required if explicitly None or ambiguous in trip request
    if "destination" in req and req.get("destination") is None:
        missing.append("destination")

    # Origin is strictly required for transport planning
    if not req.get("origin"):
        missing.append("origin")

    # Pax: required if not explicitly specified and not default (unless origin and duration are both already provided)
    if not req.get("_pax_explicit") and "pax" not in explicit and not req.get("group_type"):
        if "origin" not in missing and not req.get("duration_days") and not req.get("_date_explicit"):
            missing.append("pax")

    # Travel date or duration: required to query exact timetables
    if not req.get("duration_days") and not req.get("_date_explicit"):
        # Only ask if origin and pax are already established
        if "origin" not in missing and "pax" not in missing:
            missing.append("duration_or_dates")

    return missing


def normalize_city_name(city: Optional[str]) -> Optional[str]:
    """Normalizes an Indian city or station name to canonical casing and alias."""
    if not city or not isinstance(city, str):
        return None
    cleaned = city.strip()
    c_lower = cleaned.lower()
    if c_lower in CITY_ALIASES:
        return CITY_ALIASES[c_lower]
    # Title-case each word
    words = cleaned.split()
    return " ".join([w.capitalize() for w in words])


def is_connecting_route(origin: Optional[str]) -> bool:
    """Returns True if origin requires a connecting journey (not a direct curated hub)."""
    if not origin:
        return False
    norm = normalize_city_name(origin)
    return norm not in TRANSIT_HUBS_DIRECT


def format_state_summary(state: Dict[str, Any]) -> str:
    """Produces a clean markdown summary of currently agreed travel state."""
    req = state.get("requirements") or {}
    items = []
    if req.get("origin"):
        items.append(f"**Origin:** {req['origin']}")
    if req.get("destination"):
        items.append(f"**Destination:** {req['destination']}")
    if req.get("pax"):
        items.append(f"**Pilgrims:** {req['pax']}")
    if req.get("duration_days"):
        items.append(f"**Duration:** {req['duration_days']} Days")
    if req.get("mode"):
        items.append(f"**Transport:** {req['mode'].capitalize()}")
    if req.get("category"):
        items.append(f"**Darshan:** {req['category']}")
    if req.get("total_budget"):
        items.append(f"**Budget:** ₹{req['total_budget']:,.0f}")
    if req.get("accessibility_requirements"):
        items.append(f"**Assistance:** {', '.join(req['accessibility_requirements'])}")
    return " • ".join(items) if items else "Planning in progress"


def generate_smart_missing_prompt(missing_slots: List[str], state: Dict[str, Any]) -> str:
    """
    Generates a courteous, helpful response adhering strictly to the
    'Answer First, Question Later' principle (Phase 14).
    Frames practical travel guidance first, then asks at most ONE relevant follow-up question.
    """
    req = state.get("requirements") or {}
    origin = req.get("origin")
    pax = req.get("pax", 1)
    pax_str = f"{pax} pilgrims" if pax > 1 else "solo pilgrim"
    if pax == 2:
        pax_str = "two adults"

    if "date_clarification" in missing_slots:
        return (
            "🙏 **Jai Mata Di!** To ensure your travel dates are accurate, could you please clarify your date with the month name? "
            "(For example: '15 December 2026' or '5 June 2026')."
        )

    if "destination" in missing_slots:
        return (
            "🙏 **Jai Mata Di!** Which destination or pilgrimage circuit in Jammu & Kashmir would you like to visit? "
            "(For example: Maa Vaishno Devi / Katra, Srinagar & Kashmir Valley, Patnitop, or Shiv Khori)."
        )

    if "origin" in missing_slots:
        explicit_pax = req.get("_pax_explicit") or ("pax" in (req.get("_explicit_fields") or []))
        if not explicit_pax:
            return (
                "🙏 **Jai Mata Di!** Planning a pilgrimage to **Maa Vaishno Devi** is a sacred and memorable journey. "
                "The pilgrimage base is **Katra**, from where devotees undertake the holy 13 km trek up to **Bhawan** "
                "(via Banganga and Adhkuwari). Most pilgrims plan for **2 to 3 days** to comfortably complete the yatra, darshan, and return trek.\n\n"
                "I can help you coordinate connecting trains or flights, select verified hotels in Katra, and check darshan slot guidance.\n\n"
                "Which city or town will you be travelling from to begin your journey?"
            )
        else:
            return (
                f"Certainly! A pilgrimage for **{pax_str}** to **Maa Vaishno Devi** can be planned smoothly. "
                "The yatra begins at **Katra** base camp before proceeding on the holy 13 km trek up to Bhawan (typically a 2 to 3 days trip).\n\n"
                "Which city or town will you be travelling from so I can recommend the best connecting transport options?"
            )

    # Truth-in-data: If origin requires clarification or is invalid, address that BEFORE requesting passenger count
    if origin:
        guidance = get_transit_guidance_for_origin(origin)
        if guidance.get("requires_clarification") and guidance.get("clarification_prompt"):
            return guidance["clarification_prompt"]

    if "pax" in missing_slots:
        transit_note = ""
        if origin:
            guidance = get_transit_guidance_for_origin(origin)
            if guidance.get("has_verified_direct"):
                transit_note = f"\n\n*Travel tip:* Direct rail connectivity is available from **{origin}** to Shri Mata Vaishno Devi Katra (SVDK)."
            elif guidance.get("transit_hub") and guidance.get("transit_hub") != "Clarification Required":
                transit_note = f"\n\n*Travel tip:* Convenient connections from **{origin}** run via **{guidance['transit_hub']}** to Jammu/Katra."
        return (
            f"Got it — travelling from **{origin}** to Katra.{transit_note}\n\n"
            "How many pilgrims will be joining the journey?"
        )

    if "duration_or_dates" in missing_slots:
        origin_str = f" from **{origin}**" if origin else ""
        recommended_duration = "3 to 4 days" if origin and origin.lower() not in ("delhi", "chandigarh", "jammu") else "2 to 3 days"
        return (
            f"Certainly! I'm organizing your sacred Vaishno Devi pilgrimage{origin_str} for **{pax_str}**.\n\n"
            f"For a comfortable yatra{origin_str}, most pilgrims find a **{recommended_duration} trip** ideal to allow for travel, "
            "rest at Katra base, and the 13 km trek up to Bhawan.\n\n"
            "What travel dates or trip duration (number of days) do you prefer for checking transport schedules and darshan slots?"
        )

    return "Could you please share your preferred travel dates or duration to continue planning?"
