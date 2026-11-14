"""
rag/normalizer.py
Synonym and Terminology Normalization Layer for Yatra AI Knowledge Retrieval.

Maps varied natural-language terminology, colloquialisms, and synonyms used by devotees
to standardized knowledge-base concepts solely for embedding and vector retrieval.

Preserves the original user query intact for all conversational responses, UI displays,
and agent prompt context. Normalization is strictly an internal retrieval optimization.
"""

import re
from typing import Dict, List, Tuple


class QueryTerminologyNormalizer:
    """
    Lightweight, maintainable synonym and phrase normalization engine for RAG queries.
    Maps non-standard devotee terminology to knowledge-base vocabulary before hashing.
    """

    # Multi-word phrase replacements (checked first, ordered longest to shortest)
    PHRASE_MAPPINGS: List[Tuple[str, str]] = [
        # Registration & passes
        ("cost for the yatra parchi", "rfid card yatra parchi free of cost fee"),
        ("fee or cost", "rfid card yatra parchi free of cost fee"),
        ("any fee", "rfid card yatra parchi free of cost fee"),
        ("is there any fee", "rfid card yatra parchi free of cost fee"),
        ("rain heavily during monsoon", "monsoon rain rainfall track status open poncho"),
        ("rain during monsoon", "monsoon rain rainfall track status open poncho"),
        ("best time of year", "best time to visit season climate optimal months march summer autumn"),
        ("best time of the year", "best time to visit season climate optimal months march summer autumn"),
        ("best time to visit", "best time to visit season climate optimal months march summer autumn"),
        ("electronic tracking badge", "rfid card mandatory pilgrim pass"),
        ("digital tracking badge", "rfid card mandatory pilgrim pass"),
        ("electronic tracking card", "rfid card mandatory pilgrim pass"),
        ("electronic pass", "rfid card mandatory pilgrim pass"),
        ("pilgrim pass", "rfid card pilgrim registration pass"),
        ("entry token", "yatra parchi rfid card"),
        ("yatra slip", "yatra registration parchi slip"),

        # Trek assistance & transport
        ("electric transport", "battery operated vehicle electric car"),
        ("electric cart", "battery operated vehicle electric car"),
        ("electric carts", "battery operated vehicle electric car"),
        ("electric car", "battery operated vehicle electric car"),
        ("electric sedan", "battery operated vehicle electric car"),
        ("battery cart", "battery operated vehicle electric car"),
        ("battery vehicle", "battery operated vehicle electric car"),
        ("battery cars", "battery operated vehicle electric car"),
        ("aerial gondola", "bhairon baba aerial ropeway cable car"),
        ("aerial cableway", "bhairon baba aerial ropeway cable car"),
        ("aerial ropeway", "bhairon baba aerial ropeway cable car"),
        ("cableway ride", "bhairon baba aerial ropeway cable car"),
        ("ropeway ride", "bhairon baba aerial ropeway cable car"),
        ("cableway connection", "bhairon baba aerial ropeway cable car"),
        ("cableway", "bhairon ropeway cable car"),
        ("cable car", "bhairon ropeway cable car"),
        ("private helicopter", "helicopter darshan sanjichhat"),
        ("palanquin service", "palki palanquin trek assistance"),
        ("porter service", "pithoo porter trek assistance"),

        # Senior citizen & elderly assistance
        ("senior citizen assistance", "senior citizen elderly assistance battery car palki wheelchair"),
        ("senior citizens", "senior citizen elderly assistance battery car palki wheelchair"),
        ("senior citizen", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly people", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly persons", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly pilgrims", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly parents", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly devotees", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly travellers", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly travelers", "senior citizen elderly assistance battery car palki wheelchair"),
        ("elderly", "senior citizen elderly assistance battery car palki wheelchair"),
        ("physically challenged", "physically challenged wheelchair senior citizen assistance"),
        ("differently abled", "physically challenged wheelchair senior citizen assistance"),
        ("wheelchair assistance", "wheelchair"),

        # Community meals & dining
        ("free langars and bhojanalayas", "langar bhojanalaya free food community kitchen"),
        ("free langars", "langar bhojanalaya free food community kitchen"),
        ("free langar", "langar bhojanalaya free food community kitchen"),
        ("community meals", "langar free meal food"),
        ("community meal", "langar free meal food"),
        ("complimentary community meal", "langar free meal food"),
        ("free feast", "langar bhojanalaya free food"),
        ("community kitchen", "langar bhojanalaya free food"),

        # Sacred locations & legends
        ("three natural rock forms", "holy pindies maha kali maha lakshmi maha saraswati"),
        ("natural rock forms", "holy pindies maha kali maha lakshmi maha saraswati"),
        ("three pindies", "holy pindies maha kali maha lakshmi maha saraswati"),
        ("meditate for nine months", "garbh joon ardhkuwari nine months meditation"),
        ("meditated for nine months", "garbh joon ardhkuwari nine months meditation"),
        ("nine months", "garbh joon ardhkuwari nine months"),
        ("narrow tunnel", "garbh joon cave ardhkuwari"),
        ("symbolic rebirth", "garbh joon ardhkuwari nine months"),
        ("limestone stalagmite pillar", "shiv khori stalagmite lingam"),
        ("limestone stalagmite", "shiv khori stalagmite lingam"),
        ("stalagmite pillar", "shiv khori stalagmite lingam"),
        ("natural lingam", "shiv khori stalagmite lingam"),
        ("holy cave shrine", "bhawan sanctum holy cave vaishno devi"),
        ("prayer sessions", "aarti morning evening prayer timings"),
        ("prayer session", "aarti morning evening prayer timings"),
        ("bhasmasura", "bhasmasura lord shiva cave"),

        # Routes & trekking
        ("older banganga trail", "traditional trek route banganga"),
        ("gentler walkway", "tarakote marg modern gentler route"),
        ("alternative route", "tarakote marg alternative pony free route"),
        ("return route", "bhairon bhawan katra trek return route"),
        ("avoid ponies", "tarakote marg pony free walking track"),

        # Facilities & accommodation
        ("nocturnal lodging", "accommodation dormitory rooms stay"),
        ("night accommodation", "accommodation dormitory rooms stay"),
        ("night stay", "accommodation dormitory rooms stay"),
        ("luggage storage or lockers", "cloakroom locker facility"),
        ("luggage storage", "cloakroom locker facility"),
        ("medical aid", "24x7 medical dispensary oxygen kiosk"),
        ("oxygen kiosk", "medical center oxygen emergency cylinder"),
        ("breathlessness", "oxygen kiosk medical emergency center"),

        # Prohibited items & rules
        ("drone photography", "prohibited items drone rules banned"),
        ("drone", "prohibited items drone rules banned"),
        ("forbidden inside", "prohibited items leather mobile tobacco"),
        ("forbidden items", "prohibited items leather mobile tobacco"),
        ("banned items", "prohibited items leather mobile tobacco"),
        ("prohibited inside", "prohibited items leather mobile tobacco"),

        # Regional attractions & culture
        ("hill resort", "patnitop sanasar hill station"),
        ("hill retreat", "patnitop hill station meadow"),
        ("snow slope", "nathatop sanasar patnitop snow"),
        ("cheese dish", "kaladi traditional dogra cheese kulcha"),
        ("dogra culture", "dogra royal dynasty heritage jammu"),
    ]

    # Single-word term replacements
    WORD_MAPPINGS: Dict[str, str] = {
        "tariff": "fare cost price",
        "tariffs": "fares cost price",
        "lodging": "accommodation dormitory room",
        "fare": "fare cost ticket",
        "gondola": "ropeway cable car",
        "cableway": "ropeway",
        "feast": "langar meal",
        "prasad": "prasad offering bhet",
        "elderly": "senior citizen elderly",
        "wheelchair": "wheelchair senior citizen",
        "wheelchairs": "wheelchair senior citizen",
    }

    def __init__(self):
        # Compile phrase regex patterns for fast case-insensitive matching
        self._compiled_phrases = [
            (re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE), replacement)
            for phrase, replacement in self.PHRASE_MAPPINGS
        ]

    def normalize_for_retrieval(self, query: str) -> str:
        """
        Transforms a user query into an enriched, normalized retrieval string.
        Applies phrase substitutions followed by single-word terminology expansions.
        Does NOT alter the original query object.
        """
        if not query or not query.strip():
            return ""

        text = query.replace("-", " ").strip()

        # 1. Apply multi-word phrase mappings
        for pattern, replacement in self._compiled_phrases:
            text = pattern.sub(replacement, text)

        # 2. Apply single-word terminology mappings
        words = text.split()
        normalized_words = []
        for word in words:
            clean_word = re.sub(r"[^a-zA-Z0-9]", "", word.lower())
            if clean_word in self.WORD_MAPPINGS:
                normalized_words.append(self.WORD_MAPPINGS[clean_word])
            else:
                normalized_words.append(word)

        normalized_query = " ".join(normalized_words)
        return normalized_query
