"""
agents/knowledge_agent.py
Tourism Knowledge Retrieval Agent for Jammu & Kashmir.
Indexes and retrieves deep cultural, historical, route, and pilgrim guidance
for Katra, Vaishno Devi, Jammu, Shiv Khori, and Patnitop.

Retrieval is keyword-based over the existing explore_data / yatra_info
datasets. It does not invent places or copy those datasets into a second
store.
"""

import re

import explore_data
import yatra_info

try:
    from services.destination_ingestion.manager import get_destination_manager
    _dest_manager = get_destination_manager()
except Exception:
    _dest_manager = None

# Common informal names that should resolve to an existing place record.
_PLACE_ALIASES = {
    "katra": "Katra",
    "katra town": "Katra",
    "bhairavnath": "Bhairavnath Temple",
    "bhairav nath": "Bhairavnath Temple",
    "bhairav": "Bhairavnath Temple",
    "bhairon": "Bhairavnath Temple",
    "bhaironath": "Bhairavnath Temple",
    "bhairon baba": "Bhairavnath Temple",
    "bhairon nath": "Bhairavnath Temple",
    "bhairon ghati": "Bhairavnath Temple",
    "bhaironghati": "Bhairavnath Temple",
    "bhairon temple": "Bhairavnath Temple",
    "bhairavnath temple": "Bhairavnath Temple",
    "bhawan": "Katra",
    "vaishno devi bhawan": "Katra",
    "ardhkuwari": "Ardhkuwari Cave",
    "ardh kuwari": "Ardhkuwari Cave",
    "adhkuwari": "Ardhkuwari Cave",
    "garbh joon": "Ardhkuwari Cave",
    "garbhjoon": "Ardhkuwari Cave",
    "charan paduka": "Charan Paduka",
    "charanpaduka": "Charan Paduka",
    "ban ganga": "Ban Ganga",
    "banganga": "Ban Ganga",
    "nau devi": "Nau Devi Cave Temple",
    "navdevi": "Nau Devi Cave Temple",
    "nav devi": "Nau Devi Cave Temple",
    "nau devi temple": "Nau Devi Cave Temple",
    "baba dhansar": "Baba Dhansar",
    "dhansar": "Baba Dhansar",
    "jhajjar kotli": "Jhajjar Kotli",
    "jhajjar": "Jhajjar Kotli",
    "patnitop": "Patnitop",
    "patni top": "Patnitop",
    "sanasar": "Sanasar",
    "mansar": "Mansar Lake",
    "mansar lake": "Mansar Lake",
    "raghunath": "Raghunath Temple, Jammu",
    "raghunath temple": "Raghunath Temple, Jammu",
    "raghunath mandir": "Raghunath Temple, Jammu",
    "bahu fort": "Bahu Fort & Bagh-e-Bahu",
    "bahu": "Bahu Fort & Bagh-e-Bahu",
    "bagh-e-bahu": "Bahu Fort & Bagh-e-Bahu",
    "bagh e bahu": "Bahu Fort & Bagh-e-Bahu",
    "baghe bahu": "Bahu Fort & Bagh-e-Bahu",
    "amar palace": "Amar Mahal Palace",
    "amar mahal palace": "Amar Mahal Palace",
    "amar mahal": "Amar Mahal Palace",
    "himkoti": "Himkoti",
    "him koti": "Himkoti",
    "dera baba": "Dera Baba Banda Bahadur",
    "banda bahadur": "Dera Baba Banda Bahadur",
    "dera baba banda": "Dera Baba Banda Bahadur",
    "dera baba banda bahadur": "Dera Baba Banda Bahadur",
    "shiv khori": "Shiv Khori",
    "shivkhori": "Shiv Khori",
    "peer kho": "Peer Kho Cave Temple",
    "peerkho": "Peer Kho Cave Temple",
    "srinagar": "Srinagar (Dal Lake & Gardens)",
    "dal lake": "Srinagar (Dal Lake & Gardens)",
    "gulmarg": "Gulmarg (Snow Meadow)",
    "pahalgam": "Pahalgam (Valley of Shepherds)",
    "aru valley": "Kashmir Valley",
    "aru": "Kashmir Valley",
    "chandanwari": "Kashmir Valley",
    "sonamarg": "Sonamarg (Meadow of Gold)",
    "sonmarg": "Sonamarg (Meadow of Gold)",
    "kashmir valley": "Kashmir Valley",
    "kashmir": "Kashmir Valley",
    "shankaracharya": "Shankaracharya Temple, Srinagar",
    "shankaracharya temple": "Shankaracharya Temple, Srinagar",
    "kheer bhawani": "Kheer Bhawani Temple, Tulmulla",
    "kheer bhawani temple": "Kheer Bhawani Temple, Tulmulla",
    "tulmulla": "Kheer Bhawani Temple, Tulmulla",
    "verinag": "Verinag Spring and Mughal Garden",
    "verinag spring": "Verinag Spring and Mughal Garden",
    "achabal": "Achabal Mughal Garden",
    "achabal garden": "Achabal Mughal Garden",
    "martand": "Martand Sun Temple, Mattan",
    "martand sun temple": "Martand Sun Temple, Mattan",
    "mattan": "Martand Sun Temple, Mattan",
    "sinthan top": "Sinthan Top",
    "sinthan": "Sinthan Top",
    "akhnoor fort": "Akhnoor Fort",
    "akhnoor": "Akhnoor Fort",
    "mubarak mandi": "Mubarak Mandi Palace",
    "mubarak mandi palace": "Mubarak Mandi Palace",
    "chashma shahi": "Chashma Shahi",
    "chashmashahi": "Chashma Shahi",
    "chashme shahi": "Chashma Shahi",
    "cheshma shahi": "Chashma Shahi",
    "pari mahal": "Pari Mahal",
    "parimahal": "Pari Mahal",
    "parimal": "Pari Mahal",
    "tulip garden": "Tulip Garden",
    "srinagar tulip garden": "Tulip Garden",
    "indira gandhi tulip garden": "Tulip Garden",
    "badamwari": "Badamwari",
    "badam wari": "Badamwari",
    "nigeen lake": "Nigeen Lake",
    "nigeen": "Nigeen Lake",
    "nageen lake": "Nigeen Lake",
    "nagin lake": "Nigeen Lake",
    "nagin": "Nigeen Lake",
    "hari parbat fort": "Hari Parbat Fort",
    "hari parbat": "Hari Parbat Fort",
    "dachigam": "Dachigam National Park",
    "dachigam national park": "Dachigam National Park",
    "harwan garden": "Harwan Garden",
    "harwan": "Harwan Garden",
    "botanical garden": "Botanical Garden",
    "machail mata": "Machail Mata",
    "machail": "Machail Mata",
    "kishtwar national park": "Kishtwar National Park",
    "chowgan": "Chowgan",
    "kishtwar chowgan": "Chowgan",
}

_STOPWORDS = {
    "what", "which", "where", "when", "how", "who", "tell", "me", "about",
    "the", "a", "an", "of", "for", "to", "in", "on", "at", "around", "near",
    "nearby", "can", "i", "we", "you", "is", "are", "should", "do", "does",
    "visit", "visiting", "see", "places", "place", "please", "my", "our",
    "yatra", "trip", "info", "information", "details", "some", "any",
}

# Trek-route + Katra-local sites used for "places around Katra" answers.
_NEARBY_KATRA_CATEGORIES = {"On the trek route", "Nearby temple"}
_NEARBY_KATRA_EXTRA = {"Ban Ganga", "Baba Dhansar", "Jhajjar Kotli"}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).strip()


def _tokens(text: str):
    return [t for t in _normalize(text).split() if t and t not in _STOPWORDS]


def is_place_followup(query: str) -> bool:
    """True if query appears to be a follow-up question about a previously discussed place."""
    if not query:
        return False
    q = query.lower()
    patterns = [
        r"\b(how far|distance|how to reach|how to get|how do i reach|where is it|where located)\b",
        r"\b(what (can|to) (i|we) do|activities|things to do|what to see)\b",
        r"\b(tell me more|more details|more info|about it|about this place|tell me about it)\b",
        r"\b(timings|entry fee|ticket|cost|entry)\b",
        r"\b(it|there|that place)\b",
    ]
    return any(re.search(p, q) for p in patterns)


def get_all_unified_places() -> list:
    """Returns the unified catalog across curated and officially ingested destinations."""
    if _dest_manager:
        try:
            return _dest_manager.get_unified_places_catalog()
        except Exception:
            pass
    return explore_data.get_places()


def classify_tourism_topic(query: str, last_place: str = None) -> str:
    """Classifies an information question so replies use the right existing source."""
    q = (query or "").lower()

    if re.search(r"\b(altitude|elevation|height|how high|sea level|metres high|feet high)\b", q):
        return "altitude"
    if re.search(r"\b(trekking\s+tips?|trek\s+tips?|tips\s+for\s+trekking|trek\s+advice|trekking\s+advice|trek\s+difficulty|tips\s+for.*trek|how\s+steep|steepness)\b", q):
        return "trekking_tips"
    if re.search(r"\b(transport.*bhawan|options.*bhawan|reach.*bhawan|ways to reach bhawan|battery car.*bhawan|ropeway.*bhawan|palki.*bhawan|helicopter.*bhawan|transport to bhawan|travel to bhawan)\b", q):
        return "bhavan_transport"
    if re.search(r"\b(visiting hour|visiting hours|opening hour|opening hours|open hour|open hours|when does.*open|visiting time)\b", q):
        return "visiting_hours"
    if re.search(r"\b(pack|packing|carry|bring|wear|what to pack|what to bring|what to carry|what to wear)\b", q):
        return "packing"
    if re.search(r"\b(aarti|aarthi)\b", q):
        return "aarti"
    if re.search(r"\b(register|registration|yatra slip|yatra parchi|how to register)\b", q):
        return "registration"
    if re.search(r"\b(trek route|route options|how to reach bhawan|tarakote|helicopter route)\b", q) and not find_specific_places(query):
        return "routes"
    if re.search(r"\b(helpline|contact number|phone number)\b", q):
        return "helpline"
    if re.search(r"\b(history|historical|heritage|mythology|legend|significance|background)\b", q) and re.search(
        r"\b(vaishno|vaishnavi|mata|shrine|bhawan|goddess)\b", q
    ) and not find_specific_places(query) and not (last_place and is_place_followup(query)):
        return "vaishno_history"
    specific_places = find_specific_places(query)
    non_katra_places = [p for p in specific_places if p["name"] not in ("Katra", "Srinagar (Dal Lake & Gardens)")]

    # Broad destination/sightseeing questions should be treated as
    # nearby-place queries before checking for a specific place.
    if re.search(
        r"\b(nearby|around katra|around jammu|places to (see|visit)|what places|tourist spots|sightseeing spots|places can i visit|visit in|what can i visit|suggest places|historical places)\b",
        q,
    ):
        if not non_katra_places or re.search(r"\b(kishtwar|srinagar|jammu|katra)\b", q):
            return "nearby_places"

    if specific_places or (last_place and is_place_followup(query)):
        return "place"
    if find_specific_places(query) or (last_place and is_place_followup(query)):
        return "place"

    # Regional historical or heritage queries should resolve to regional sightseeing
    if re.search(r"\b(history|historical|heritage)\b", q) and re.search(r"\b(jammu|srinagar|kishtwar|kashmir|katra)\b", q):
        return "nearby_places"

    if re.search(r"\b(history|historical|heritage|mythology|legend)\b", q):
        return "vaishno_history"
    return "general"


def find_specific_places(query: str) -> list:
    """Returns existing place dicts whose names/aliases appear in the query.
    Does not fall back to the full catalogue."""
    if not query:
        return []

    q = _normalize(query)
    places = explore_data.get_places()
    if _dest_manager:
        try:
            extra_places = _dest_manager.get_new_destinations()
            places = places + extra_places
        except Exception:
            pass
    by_name = {p["name"]: p for p in places}
    matched = []
    seen = set()

    for alias, canonical in sorted(_PLACE_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in q and canonical in by_name and canonical not in seen:
            matched.append(by_name[canonical])
            seen.add(canonical)

    query_tokens = set(_tokens(query))
    for p in places:
        if p["name"] in seen:
            continue
        name_tokens = set(_tokens(p["name"]))
        # Require a distinctive name token (ignore generic temple/cave/lake).
        distinctive = name_tokens - {"temple", "cave", "lake", "palace", "fort", "jammu", "garden", "park"}
        if distinctive and distinctive <= query_tokens:
            matched.append(p)
            seen.add(p["name"])
            continue
        # Substring: "bhairavnath" inside "bhairavnath temple"
        name_compact = "".join(_tokens(p["name"]))
        query_compact = "".join(_tokens(query))
        if name_compact and len(name_compact) >= 6 and name_compact in query_compact:
            matched.append(p)
            seen.add(p["name"])

    return matched


def get_nearby_katra_places() -> list:
    """Relevant subset around Katra / the trek — not the full J&K catalogue."""
    selected = []
    seen = set()
    priority = ["Ban Ganga", "Charan Paduka", "Ardhkuwari Cave", "Bhairavnath Temple", "Baba Dhansar", "Nau Devi Cave Temple", "Jhajjar Kotli"]
    by_name = {p["name"]: p for p in explore_data.get_places()}
    for name in priority:
        if name in by_name and name not in seen:
            selected.append(by_name[name])
            seen.add(name)

    for p in explore_data.get_places():
        distance = (p.get("distance") or "").lower()
        from_katra = "katra" in distance or "trek" in distance or "bhawan" in distance
        if p["category"] in _NEARBY_KATRA_CATEGORIES or p["name"] in _NEARBY_KATRA_EXTRA or from_katra:
            if p["name"] not in seen:
                selected.append(p)
                seen.add(p["name"])
    return selected


def get_vaishno_devi_history() -> list:
    """History drawn only from existing trek-site records that document the legend."""
    names = ("Bhairavnath Temple", "Ardhkuwari Cave", "Charan Paduka", "Ban Ganga")
    sections = []
    for name in names:
        place = explore_data.get_place_by_name(name)
        if place:
            sections.append({
                "name": place["name"],
                "historical_background": place["historical_background"],
            })
    return sections


def get_jk_tourism_knowledge(query: str = "", last_place: str = None) -> dict:
    """Retrieves curated J&K tourism facts from existing local datasets, with
    support for follow-up questions referencing a previous place."""
    topic = classify_tourism_topic(query, last_place=last_place)
    specific = find_specific_places(query) if query else []

    is_followup = False
    primary_place = None

    # Broad sightseeing queries take priority over generic place matching.
    non_hub_specific = [p for p in specific if p["name"] not in ("Katra", "Jammu")]
    has_pronoun_ref = bool(re.search(r"\b(it|its|there|that place|this place)\b", query, re.IGNORECASE)) if query else False

    if topic == "nearby_places":
        q_low = (query or "").lower()
        all_p = get_all_unified_places()
        if "jammu" in q_low:
            jammu_places = [p for p in all_p if (p.get("district") and "jammu" in p["district"].lower()) or (p.get("region") and "jammu" in p["region"].lower()) or "jammu" in p.get("category", "").lower()]
            if any(k in q_low for k in ["historic", "heritage", "palace", "fort", "ancient"]):
                matched_places = [p for p in jammu_places if any(k in (p.get("category", "") + " " + p.get("description", "")).lower() for k in ["historic", "heritage", "palace", "fort", "ancient"])]
            else:
                matched_places = jammu_places
        elif "kishtwar" in q_low:
            matched_places = [p for p in all_p if (p.get("district") and "kishtwar" in p["district"].lower()) or "kishtwar" in p["name"].lower()]
        elif "srinagar" in q_low or "kashmir" in q_low:
            matched_places = [p for p in all_p if (p.get("district") and "srinagar" in p["district"].lower()) or (p.get("region") and "kashmir" in p["region"].lower())]
        else:
            matched_places = get_nearby_katra_places()

    elif topic in ("altitude", "trekking_tips", "bhavan_transport", "visiting_hours"):
        if specific:
            primary_place = specific[0]
            matched_places = specific
        elif last_place:
            resolved = search_place_by_name(last_place)
            if resolved:
                primary_place = resolved
                matched_places = [resolved]
                is_followup = True
            else:
                matched_places = []
        else:
            matched_places = []

    elif last_place and is_place_followup(query) and (not non_hub_specific or has_pronoun_ref):
        resolved = search_place_by_name(last_place)
        if resolved:
            primary_place = resolved
            matched_places = [resolved]
            topic = "place"
            is_followup = True
        else:
            matched_places = []

    elif specific:
        primary_place = specific[0]
        matched_places = specific
        topic = "place"

    elif last_place and is_place_followup(query):
        resolved = search_place_by_name(last_place)
        if resolved:
            primary_place = resolved
            matched_places = [resolved]
            topic = "place"
            is_followup = True
        else:
            matched_places = []

    else:
        matched_places = []
    active_last_place = primary_place["name"] if primary_place else (last_place if is_followup else None)

    return {
        "query": query,
        "query_kind": topic,
        "matched_places": matched_places,
        "primary_place": primary_place,
        "last_place": active_last_place,
        "is_followup": is_followup,
        "vaishno_history": get_vaishno_devi_history() if topic == "vaishno_history" else [],
        "aarti_timings": yatra_info.get_aarti_timings(),
        "registration_info": yatra_info.get_registration_info(),
        "route_options": yatra_info.get_route_options(),
        "packing_guidance": yatra_info.get_packing_guidance(),
        "facilities": yatra_info.get_facilities(),
        "helpline": yatra_info.get_helpline(),
        "taxi_info": explore_data.get_taxi_info(),
    }


def search_place_by_name(name: str):
    """Retrieves full enriched dictionary for a specific place by name."""
    exact = explore_data.get_place_by_name(name)
    if exact:
        return exact
    if _dest_manager:
        try:
            d = _dest_manager.find_destination(name)
            if d:
                return d
        except Exception:
            pass
    found = find_specific_places(name)
    return found[0] if found else None


def get_personalized_recommendations(travel_preferences: dict = None) -> list:
    """Generates personalized tourist place recommendations in J&K based on pilgrim preferences.
    Preferences can include: 'category', 'max_distance', 'has_children', 'spirituality_level'."""
    prefs = travel_preferences or {}
    category = prefs.get("category")
    if _dest_manager:
        try:
            places = _dest_manager.get_unified_places_catalog(category=category if category != "All" else None)
        except Exception:
            places = explore_data.get_places(category=category if category != "All" else None)
    else:
        places = explore_data.get_places(category=category if category != "All" else None)

    scored_places = []
    for p in places:
        score = 10
        p_cat = (p.get("category") or "").lower()
        if prefs.get("has_children") and "trek" in p_cat:
            score -= 2
        if prefs.get("spirituality_level") == "high" and ("temple" in p_cat or "trek" in p_cat or "pilgrimage" in p_cat):
            score += 3
        if prefs.get("nature_focused") and ("nature" in p_cat or "hill" in p_cat or "garden" in p_cat or "lake" in p_cat or "park" in p_cat or "pass" in p_cat or "meadow" in p_cat):
            score += 3
        if (prefs.get("historical_focused") or prefs.get("heritage_focused") or prefs.get("cultural_focused") or prefs.get("category") == "historical" or prefs.get("interest") in ("history", "historical", "heritage", "culture")) and (
            "historic" in p_cat or "heritage" in p_cat or "palace" in p_cat or "fort" in p_cat or "ancient" in p_cat or p.get("category_type") == "historical_site"
        ):
            score += 3
        scored_places.append({"place": p, "relevance_score": score})

    scored_places.sort(key=lambda x: x["relevance_score"], reverse=True)
    return [item["place"] for item in scored_places]
