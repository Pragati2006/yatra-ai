"""
agents/conversation_agent.py
Handles understanding the pilgrim's free-text message (in whatever
language they write in) and generating warm, culturally appropriate
replies. This is the "front door" agent other agents don't talk to
directly - the Coordinator calls it first to understand intent, and
last to phrase the final reply.

Two modes:
  - LLM-powered (if ANTHROPIC_API_KEY is set): uses Claude, which can
    genuinely read/respond in Hindi, Hinglish, English, or other
    languages the pilgrim writes in, and naturally weaves in respectful
    devotional phrasing.
  - Rule-based fallback (no key needed): reuses the existing, tested
    regex-based extraction from agent.py, and uses a small template
    bank for devotional phrasing. Always English in this mode - honest
    limitation, not a fake multilingual claim.
"""

import json
import os
import random
import re
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List

import agent as legacy_agent  # the existing, tested transport/darshan parsing + ranking logic

# ---------------------------------------------------------------------------
# Supported Darshan Categories (Week 7 RPA Availability Checking)
# ---------------------------------------------------------------------------
SUPPORTED_CATEGORIES = [
    "Normal Darshan",
    "VIP Darshan",
    "Helicopter Darshan",
]

_MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_AVAILABILITY_PATTERNS = [
    r"\b(check|find|lookup|see|show|tell me|is there|are there)\b.{0,30}\b(availability|available slots?|open slots?|darshan slots?|yatra slots?|slot status|vacant slots?)\b",
    r"\b(slot|slots|darshan)\s+(availability|status)\b",
    r"\b(check|is|are)\s+(any\s+)?(vip|normal|helicopter)?\s*(darshan)?\s*availability\b",
    r"\b(any slots available|slots available|available slots|open slots)\b",
    r"\bcheck availability\b",
]

# ---------------------------------------------------------------------------
# Intent Detection — rule-based, no API key required
# ---------------------------------------------------------------------------

# Signals that a message is CLEARLY a tourism/info question and NOT a booking
_TOURISM_QUESTION_PATTERNS = [
    r"\bwhat\b.{0,60}\b(place|places|visit|see|explore|history|about|temple|fort|lake|cave|trek|route|timing|timings|pack|packing|bring|carry|register|registration|aarti|facility|facilities|guide|tips|advice|info|information|weather|distance|know|helpline|contact|steps|do|see)\b",
    r"\btell me\b.{0,50}\b(about|history|heritage|timing|route|place|site|temple|cave|fort|trek|more)\b",
    r"\bhow\b.{0,40}\b(reach|get|go|visit|register|trek|climb|pack|far)\b",
    r"\bwhere\b.{0,40}\b(is|are|can i|should i|to visit|to see|to go|to trek)\b",
    r"\b(history|historical|heritage|mythology|legend|background|significance)\b",
    r"\b(aarti|aarthi)\s*timings?\b",
    r"\b(packing|what to pack|what to bring|what to carry|what to wear|should i pack|should we pack)\b",
    r"\b(yatra registration|yatra parchi|yatra slip|how to register|registration steps)\b",
    r"\b(trek route|which route|how to reach bhawan)\b",
    r"\b(nearby places|nearby attractions|nearby destinations|places to see|places to visit|tourist spots|sightseeing spots|tourist attractions|attractions)\b",
    r"\b(give me|show me|tell me)\b.{0,50}\b(attraction|attractions|place|places|sightseeing)\b",
    r"\b(show\s+me\s+|show\s+|see\s+|view\s+|display\s+|look\s+at\s+)?(pictures?|photos?|photographs?|images?|pics?|gallery)\s+(of|for|about|from|at)\b",
    r"\b(do\s+you\s+have\s+)?(pictures?|photos?|photographs?|images?|pics?)\s+(of|for|about|from|at)\b",
    r"\b(pictures?|photos?|photographs?|images?|pics?)\b.{0,30}\b(place|places|destination|destinations|attraction|attractions|temple|fort|garden|lake|shrine)\b",
    r"\b(bhairavnath|bhairon|bhairon ghati|ardhkuwari|charan paduka|ban ganga|shiv khori|patnitop|sanasar|mansar|bahu fort|amar mahal|raghunath|peer kho|himkoti|baba dhansar|jhajjar kotli|nau devi|sinthan|sinthan top|gulmarg|pahalgam|sonamarg|srinagar|dal lake|shankaracharya|kheer bhawani|verinag|achabal|martand|machail|machail mata|sarthal|sarthal devi|kishtwar|chowgan|akhnoor|akhnoor fort|pari mahal|parimahal|parimal|dachigam|botanical garden|naranag|chashma shahi|chashme shahi|cheshma shahi|badamwari|tulip garden|hari parbat|harwan|harwan garden|nigeen|nigeen lake|nagin lake|mubarak mandi)\b",
    r"\b(visiting\s+hours?|opening\s+hours?|open\s+hours?|when\s+does.*open|visiting\s+timings?)\b",
    r"\b(vaishno devi history|vaishno devi significance|vaishno devi legend|about vaishno devi|what is vaishno devi|what is (the )?(vaishno devi )?yatra|tell me about (the )?yatra)\b",
    r"\b(how far|what (can|to) (i|we) do|tell me more|how to reach|how do i reach|what is the distance|where is it|where located|tell me about it)\b",
    r"\b(suitable for|safe for|can.*visit|can.*go|is it (safe|possible|difficult|steep|easy)|how difficult|trek difficulty)\b",
    r"\b(elderly|senior citizen|seniors?|parents?|old age|aged|handicapped|disabled|wheelchair|wheelchairs)\b",
    r"\b(battery car|battery cars|electric vehicle|palki|palkis|palanquin|pithoo|pithoos|porter|ropeway|cable car|helicopter)\b",
    r"\b(best time|best month|when to visit|when should|rush|crowd|off season|peak season|navratri|winter|monsoon|snow|snowfall)\b",
    r"\b(night trek|trek at night|safe at night|safe for women|solo travel|dress code|clothes|clothing|what to wear)\b",
    r"\b(langar|langars|bhojanalaya|food|eating|meals?|drinking water|medical|dispensary|oxygen|locker|lockers|cloakroom|luggage|dormitory|stay at bhawan)\b",
    r"\b(with (kids|children|baby|infant|toddler|family)|pram|stroller)\b",
    r"\b(photo id|documents?|which id|id card|identity proof|aadhaar|passport)\b",
    r"\b(difference between|traditional track|tarakote marg|which track|which trail)\b",
    r"\b(prohibited|banned|allowed|not allowed|forbidden|rules inside|restrictions|items strictly prohibited|items prohibited|can i carry|can we carry|is.*allowed|what items)\b",
    r"\b(python|script|bypass|hack|scrape)\b",
]

# Words after "from" that are destinations, trek landmarks or grammar, not origin cities.
_FROM_ORIGIN_STOPWORDS = {
    "the", "a", "an", "my", "our", "here", "there", "home", "katra", "jammu",
    "bhawan", "next", "this", "last", "for", "with", "by", "in", "during",
    "and", "to", "or", "there", "here", "banganga", "ban ganga", "ardhkuwari",
    "adhkuwari", "sanjichhat", "bhairon", "bhairavnath", "himkoti", "tarakote",
}

# Signals that are STRONG booking/planning intent — override tourism detection
_TRIP_PLANNING_PATTERNS = [
    r"\b(\d+)\s*(people|pax|person|persons|members|pilgrims)\b",
    r"\b(book|booking|reserve|reservation)\b",
    r"\b(find|search|look for|check|get me)\b.{0,30}\b(flight|train|bus|travel|transport|darshan slot|options)\b",
    r"\b(vip darshan|helicopter darshan|normal darshan)\b",
    r"\b(travelling|traveling|trip to|going to|plan.*yatra|i want.*travel|i want.*darshan)\b",
    r"\b(proceed|confirm|authorise|authorize|complete booking)\b",
    r"\b(change\s+(?:destination|origin|starting\s+city|departure|mode|dates?|duration|pax|pilgrims?|hotel|stay)|switch\s+to\s+(?:train|flight|bus)|add\s+(?:one|two|\d+)\s+more\s+pilgrim)\b",
]


_ITINERARY_PATTERNS = [
    r"\b(show|view|see|display|what am i doing|tell me about|what is on|what's on|what is)\b.{0,30}\b(itinerary|day\s*\d+|schedule)\b",
    r"\b(day[- ]by[- ]day\s+itinerary|daily\s+itinerary|trip\s+schedule)\b",
    r"\bday\s*\d+\b",
    r"\b(move|shift|transfer)\b.{0,40}\b(to day\s*\d+|day\s*\d+)\b",
    r"\b(add|put|include)\b.{0,40}\b(on day\s*\d+|to day\s*\d+|day\s*\d+)\b",
    r"\b(remove|delete|drop|take out)\b.{0,40}\b(from day\s*\d+|day\s*\d+)\b",
    r"\b(replace|swap)\b.{0,40}\bwith\b",
    r"\b(add a rest day|make day\s*\d+.*rest|rest day)\b",
    r"\b(make day\s*\d+.*(relaxed|devotional|packed|sightseeing)|change day\s*\d+)\b",
    r"\bmove (that|it) to day\s*\d+\b",
    r"\b(show my itinerary|show itinerary|view itinerary|my itinerary)\b",
]


def _has_trip_origin_phrase(text_lower):
    """True when the pilgrim names a departure city, regardless of capitalization.
    Ignores destination words such as Katra/Jammu so tourism questions are not
    misread as booking requests."""
    m = re.search(
        r"\b(?:from|out of|leaving|travelling from|traveling from|departing from|starting from)\s+([a-z]+(?:\s+[a-z]+)?)",
        text_lower,
    )
    if not m:
        return False
    words = m.group(1).split()
    clean = []
    for w in words:
        if w in _FROM_ORIGIN_STOPWORDS:
            break
        clean.append(w)
    return bool(clean) and len("".join(clean)) >= 3


_WEATHER_PATTERNS = [
    r"\b(weather|temperature|forecast|climate|how cold|is it raining|rain forecast|snow in katra|what to wear for weather|weather in katra)\b",
]

# Information requests about the booking process (should explain, NOT execute booking)
_BOOKING_INFO_PATTERNS = [
    r"\bhow\s+(can\s+i|do\s+i|to|should\s+i)\s+(book|reserve)\b",
    r"\b(what\s+is|explain|tell\s+me)\s+(about\s+)?(the\s+)?booking\s+(process|procedure|steps|method|flow)\b",
    r"\bhow\s+does\s+(the\s+)?booking(\s+process)?\s+work\b",
    r"\bwhere\s+can\s+i\s+book\b",
]

# Booking Intent / Navigation Requests (expressing desire to proceed to booking with recommended Yatra)
# Must trigger navigation to guided booking experience — NEVER auto-confirm or execute RPA
_BOOKING_INTENT_PATTERNS = [
    r"\b(book\s+my\s+yatra|book\s+tickets|book\s+yatra|book\s+now|book\s+this)\b",
    r"\b(proceed\s+with\s+booking|proceed\s+to\s+booking|continue\s+with\s+booking|continue\s+to\s+booking|continue\s+with\s+the\s+booking)\b",
    r"\b(i\s+want\s+to|help\s+me|let\s+me|can\s+i|ready\s+to|like\s+to|want\s+to|please)\b.{0,40}\b(proceed\s+with\s+(the\s+)?booking|continue\s+with\s+(the\s+)?booking|continue\s+to\s+booking|proceed\s+to\s+booking|book\s+(this|the)\s+(recommended|plan|yatra|trip|itinerary)|book\s+this|book\s+now|book\s+tickets)\b",
    r"\b(book\s+this\s+(plan|itinerary|yatra|trip|recommendation)|book\s+the\s+recommended\s+(yatra|trip|plan|itinerary))\b",
    r"\b(i\s+want\s+to\s+book|want\s+to\s+book\s+this|help\s+me\s+book|help\s+me\s+continue\s+with\s+the\s+booking)\b",
    r"\b(proceed\s+with\s+the\s+recommended\s+itinerary|proceed\s+with\s+the\s+recommended\s+yatra)\b",
    r"^(book\s+my\s+yatra|proceed\s+with\s+booking|book\s+tickets|continue\s+to\s+booking|book\s+now)\.?$",
]

# Explicit Confirmation of Booking Authorization (only when user explicitly confirms)
_BOOKING_CONFIRMATION_PATTERNS = [
    r"^(yes,?\s*)?confirm\s+booking\.?$",
    r"^(yes,?\s*)?authorize\s+booking\.?$",
    r"^yes,?\s*(confirm|authorize)\.?$",
    r"^confirm\s+my\s+option\.?$",
    r"^yes,?\s*confirm\s+(trip|booking|plan)\.?$",
    r"^i\s+confirm(\s+booking)?\.?$",
    r"^execute\s+rpa\.?$",
    r"^(yes,?\s*)?proceed\.?$",
    r"^book\s+(this\s+)?option(\s+\d+)?\.?$",
]

# Legacy backward-compatible booking pattern list (strictly confirmation)
_BOOKING_PATTERNS = _BOOKING_CONFIRMATION_PATTERNS


def _is_pure_greeting(tl: str) -> bool:
    if not tl:
        return False
    t_clean = re.sub(r"[^\w\s]", " ", tl).strip()
    words = t_clean.split()
    if not words:
        return False
    greeting_vocab = {
        "jai", "mata", "di", "ji", "maata", "bhole", "nath", "hello", "hi",
        "hey", "namaste", "namaskar", "pranam", "good", "morning", "evening",
        "afternoon", "hare", "krishna", "ram", "shree", "radhe", "har", "mahadev",
        "there", "assistant", "yatra", "ai"
    }
    planning_triggers = {
        "plan", "planning", "book", "booking", "trip", "hotel", "train", "flight",
        "bus", "weather", "route", "track", "stay", "darshan", "cost", "budget",
        "itinerary", "days", "pax", "people", "adults", "from"
    }
    if any(w in planning_triggers for w in words):
        return False
    return all(w in greeting_vocab for w in words)


def _is_pure_acknowledgment(tl: str) -> bool:
    if not tl:
        return False
    t_clean = re.sub(r"[^\w\s]", " ", tl).strip()
    words = t_clean.split()
    if not words:
        return False
    ack_vocab = {
        "thank", "you", "so", "much", "very", "a", "lot", "thanks", "dhanyawad",
        "shukriya", "ok", "okay", "got", "it", "understood", "alright", "noted",
        "perfect", "great", "nice", "fine", "sure", "sounds", "good", "for", "the", "help", "ji"
    }
    planning_triggers = {
        "plan", "planning", "book", "booking", "trip", "hotel", "train", "flight",
        "bus", "weather", "route", "track", "stay", "darshan", "cost", "budget"
    }
    if any(w in planning_triggers for w in words):
        return False
    return all(w in ack_vocab for w in words)


def _is_pure_help(tl: str) -> bool:
    if not tl:
        return False
    t_clean = re.sub(r"[^\w\s]", " ", tl).strip()
    return t_clean in ("help", "menu", "options", "what can you do", "features", "how can you help")


_LIVE_TRAIN_STATUS_PATTERNS = [
    r"\b(live\s+train\s+status|live\s+status|running\s+status|train\s+running\s+status|current\s+location\s+of\s+train|train\s+delay\s+status|train\s+status)\b",
    r"\bwhere\s+is\s+(?:the\s+|my\s+)?train\b",
    r"\bwhere\s+is\s+(?:train\s+)?\d{5}\b",
    r"\btrack\s+(?:train\s+)?\d{5}\b",
    r"\bis\s+(?:train\s+)?\d{5}\s+(?:running\s+)?on\s+time\b",
    r"\bdelay\s+of\s+(?:train\s+)?\d{5}\b",
]

_TRAIN_SCHEDULE_PATTERNS = [
    r"\b(train\s+schedule|train\s+timetable|train\s+timings?|timetable|schedule\s+of\s+(?:the\s+)?train)\b",
    r"\b(vande\s+bharat|shri\s+shakti|uttar\s+sampark|malwa|swaraj|hemkunt|rajdhani|jammu\s+mail)\b.{0,30}\b(schedule|timetable|timing|timings)\b",
    r"\b(schedule|timetable|timing|timings)\b.{0,30}\b(vande\s+bharat|shri\s+shakti|uttar\s+sampark|malwa|swaraj|hemkunt|rajdhani|jammu\s+mail)\b",
    r"\b(train\s+time|train\s+times|railway\s+timetable)\b",
]

_TRAIN_SEARCH_PATTERNS = [
    r"\b(train|trains)\s+(?:from|between|to)\b",
    r"\b(search|find|check|show|get|list|available)\s+(?:me\s+)?(?:the\s+)?(train|trains|railways?)\b",
    r"\b(train|trains)\s+from\s+[a-z]+(?:\s+[a-z]+)?\s+to\s+(?:katra|jammu|svdk|jat)\b",
    r"\b(train|trains)\s+to\s+(?:katra|jammu|svdk|jat)\b",
]

_FLIGHT_SEARCH_PATTERNS = [
    r"\b(flight|flights|air\s+tickets?|airlines?)\s+(?:from|between|to)\b",
    r"\b(search|find|check|show|get|list|available)\s+(?:me\s+)?(?:the\s+)?(flight|flights|airfare)\b",
    r"\b(flight|flights)\s+to\s+(?:jammu|srinagar|ixj|sxr)\b",
    r"\b[a-zA-Z\s]+?\s+to\s+[a-zA-Z\s]+?\s+(?:flight|flights|airfare|air\s+ticket)\b",
    r"\b(flight|flights)\s+(search|booking|ticket|tickets|fares?|options?)\b",
]

_BUS_SEARCH_PATTERNS = [
    r"\b(bus|buses|jksrtc|stage\s+carriage)\s+(?:from|between|to)\b",
    r"\b(search|find|check|show|get|list|available)\s+(?:me\s+)?(?:the\s+)?(?:all\s+)?(?:private\s+and\s+government\s+|government\s+and\s+private\s+|private\s+|government\s+|ac\s+|sleeper\s+|direct\s+|connecting\s+)?(bus|buses|jksrtc)\b",
    r"\b(bus|buses)\s+from\s+[a-z]+(?:\s+[a-z]+)?\s+to\s+[a-z]+(?:\s+[a-z]+)?\b",
    r"\b(bus|buses)\s+to\s+(?:katra|jammu|udhampur|srinagar)\b",
    r"\b[a-zA-Z\s]+?\s+to\s+[a-zA-Z\s]+?\s+(?:bus|buses|bus\s+schedule|bus\s+timing|bus\s+fare)\b",
    r"\b(bus|buses)\s+(search|booking|ticket|tickets|fares?|schedule|timetable|timing|timings|options?)\b",
    r"\b(?:which\s+is\s+the\s+|show\s+(?:me\s+)?(?:the\s+)?)?cheapest\s+(?:verified\s+)?(?:bus|option|transport|service)\b",
    r"\b(show|find|list)\s+(?:all\s+)?(ac\s+sleeper|sleeper|volvo|direct|connecting)\s+buses\b",
    r"\b(show|list|find)\s+(?:all\s+)?direct\s+buses(?:\s+only)?\b",
    r"\b(show|list|find)\s+(?:all\s+)?connecting\s+buses(?:\s+via\s+[a-zA-Z\s]+)?\b",
    r"\b(show|list|find)\s+(?:both\s+)?(?:private\s+and\s+government|government\s+and\s+private)\s+buses\b",
    r"\b(show|list|find)\s+(?:private|government)\s+buses\b",
    r"\bcompare\s+(?:the\s+)?(?:bus\s+and\s+train|train\s+and\s+bus)(?:\s+travel)?\b",
    r"\b(bus\s+vs\s+train|train\s+vs\s+bus)\b",
    r"\bbuses\s+from\s+[a-zA-Z\s]+?\s+to\s+[a-zA-Z\s]+?\s+and\s+onward\s+to\s+[a-zA-Z\s]+\b",
]

_HOTEL_PATTERNS = [
    r"\b(hotels?|stay|stays|accommodation|accommodations|rooms?|lodging|guest\s*house|guest\s*houses|bhawan\s+stay|dormitory|dormitories|where\s+to\s+stay)\b",
]

_ALTITUDE_PATTERNS = [
    r"\b(altitude|elevation|height|how\s+high|sea\s+level|metres\s+high|meters\s+high|feet\s+high)\b",
]

_TREKKING_PATTERNS = [
    r"\b(trekking\s+tip|trekking\s+tips|trek\s+tips|tips\s+for\s+trekking|trek\s+advice|trekking\s+advice|tips\s+for.*trek|how\s+steep|steepness|trek\s+difficulty|difficulty\s+of.*trek)\b",
]

_BHAVAN_TRANSPORT_PATTERNS = [
    r"\b(transport\s+options?\s+to\s+bhawan|transport\s+to\s+bhawan|options\s+to\s+bhawan|ways\s+to\s+reach\s+bhawan|how\s+to\s+reach\s+bhawan)\b",
    r"\b(battery\s+car|electric\s+vehicle|palki|palanquin|pithoo|porter|ropeway|cable\s+car|helicopter)\b.{0,30}\b(to\s+bhawan|bhawan|shrine)\b",
    r"\b(how\s+to\s+climb|modes\s+of\s+transport.*bhawan|transportation.*bhawan)\b",
]

_BUDGET_CALCULATION_PATTERNS = [
    r"\b(budget\s+breakdown|cost\s+breakdown|expense\s+breakdown|price\s+breakdown|detailed\s+budget|detailed\s+cost|calculate\s+budget|how\s+much\s+will\s+it\s+cost|total\s+cost)\b",
]

_MY_BOOKINGS_PATTERNS = [
    r"\b(show|view|see|check|get|fetch|list|display)\b.{0,30}\b(my\s+)?(?:previous|past|saved|recent|prior)\s+bookings?\b",
    r"\b(my\s+bookings|previous\s+bookings?|past\s+bookings?|saved\s+bookings?|prior\s+bookings?)\b",
]

_BOOKING_REVIEW_PATTERNS = [
    r"\b(review|check|verify|summary\s+of|show\s+me)\b.{0,30}\b(my\s+)?(?:booking\s+details|booking\s+summary|trip\s+summary|plan\s+summary|booking\s+review|complete\s+booking)\b",
    r"\b(review\s+my\s+booking|booking\s+review|review\s+booking|show\s+me\s+the\s+complete\s+booking|complete\s+booking\s+details)\b",
]

_HOTEL_CHANGE_PATTERNS = [
    r"\b(i\s+don'?t\s+want|not\s+want|reject|exclude)\b.{0,40}\b(niharika|hotel|stay|accommodation)\b",
    r"\b(change|switch|replace|select|pick|choose)\b.{0,40}\b(hotel|stay|accommodation|option\s+\d+|second\s+option|first\s+option|third\s+option)\b",
    r"\b(show\s+me\s+other\s+hotels|other\s+hotels|different\s+hotel|another\s+hotel|alternative\s+hotels?)\b",
    r"\b(change\s+my\s+hotel|switch\s+hotel|select\s+another\s+hotel|change\s+hotel|select\s+hotel)\b",
]

_TRANSPORT_CHANGE_PATTERNS = [
    r"\b(change|switch|replace|select|pick|choose)\b.{0,40}\b(train|flight|bus|transport|mode)\b",
    r"\b(can\s+we\s+take|take|use|travel\s+by|travel\s+via)\b.{0,30}\b(train|flight|bus|vande\s+bharat|shri\s+shakti|uttar\s+sampark)\b",
    r"\b(select|choose|pick)\s+(?:train\s+)?(?:\d{5}|vande\s+bharat|shri\s+shakti|uttar\s+sampark)\b",
    r"\b(select|choose|pick|switch\s+to|change\s+to)\s+(?:the\s+)?(?:laxmi\s+holidays|zingbus|flixbus|intrcity|ram\s+dalal|jksrtc|hrtc|prtc)(?:\s+(?:bus|option))?\b",
    r"\b(change\s+my\s+train|switch\s+to\s+train|switch\s+to\s+flight|switch\s+to\s+bus|change\s+my\s+selected\s+bus)\b",
]

_DATE_CHANGE_PATTERNS = [
    r"\b(change|update|reschedule|switch|modify|shift)\b.{0,30}\b(my\s+)?(travel\s+)?dates?\b",
    r"\b(change|shift|move)\b.{0,30}\b(travel\s+date|departure\s+date|date)\s+to\b",
    r"\b(we\s+want\s+to\s+travel\s+on|i\s+want\s+to\s+travel\s+on|travel\s+date\s+is|departing\s+on|travel\s+on)\b",
    r"\b(let'?s\s+travel|travel|travelling|trip\s+dates?)\s+(?:from\s+)?\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\s+to\s+\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\b",
    r"\b(?:from\s+)?\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\s+to\s+\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\b",
]


def detect_intent(user_text):
    """Classifies the pilgrim's message into one of:
      - 'BOOKING'          : explicit booking execution / authorization confirmation
      - 'BOOKING_INTENT'   : intention to proceed to booking with recommended Yatra (triggers navigation)
      - 'MY_BOOKINGS'      : view previous or saved simulated bookings
      - 'BOOKING_REVIEW'   : review currently planned booking summary
      - 'HOTEL_CHANGE'     : modify hotel selection or reject specific hotel
      - 'TRANSPORT_CHANGE' : modify transport selection or pick specific train
      - 'DATE_CHANGE'      : update travel dates
      - 'WEATHER'          : weather forecast or climate guidance question
      - 'ITINERARY'        : day-by-day itinerary view or modification request
      - 'TOURISM'          : informational/tourism question — do NOT start booking flow
      - 'AVAILABILITY'     : live slot availability check
      - 'TRAIN_SEARCH'     : train connectivity or option search
      - 'TRAIN_SCHEDULE'   : train timetable / schedule details
      - 'LIVE_TRAIN_STATUS': real-time running status enquiry
      - 'FLIGHT_SEARCH'    : air travel connectivity search
      - 'HOTEL_SEARCH'     : accommodation / Katra hotel search
      - 'ALTITUDE_GUIDANCE': altitude / elevation queries
      - 'TREKKING_GUIDANCE': trek tips, gradient, route advisory
      - 'BHAVAN_TRANSPORT' : transit modes from Katra to Bhawan
      - 'BUDGET_CALCULATION': cost calculation / expense breakdown
      - 'TRIP_PLANNING'    : booking/travel search request
      - 'UNKNOWN'          : ambiguous; default to TRIP_PLANNING to preserve existing behaviour
    """
    t = (user_text or "").strip()
    tl = t.lower()

    # 1. Informational questions about how to book -> treat as tourism info
    for pat in _BOOKING_INFO_PATTERNS:
        if re.search(pat, tl):
            return "TOURISM"

    # 1b. Check for previous / saved bookings requests
    for pat in _MY_BOOKINGS_PATTERNS:
        if re.search(pat, tl):
            return "MY_BOOKINGS"

    # 1c. Check for booking review / complete booking summary request
    for pat in _BOOKING_REVIEW_PATTERNS:
        if re.search(pat, tl):
            return "BOOKING_REVIEW"

    # 2. Check for booking intent / navigation requests (user wants to proceed with recommended plan)
    for pat in _BOOKING_INTENT_PATTERNS:
        if re.search(pat, tl):
            return "BOOKING_INTENT"

    # 3. Check for explicit booking confirmation/execution intent
    for pat in _BOOKING_CONFIRMATION_PATTERNS:
        if re.search(pat, tl):
            return "BOOKING"

    # 3b. Check for selective modification intents (hotel, transport, date)
    for pat in _HOTEL_CHANGE_PATTERNS:
        if re.search(pat, tl):
            return "HOTEL_CHANGE"

    for pat in _TRANSPORT_CHANGE_PATTERNS:
        if re.search(pat, tl):
            return "TRANSPORT_CHANGE"

    for pat in _DATE_CHANGE_PATTERNS:
        if re.search(pat, tl):
            return "DATE_CHANGE"

    # 3.5 Check for comprehensive trip planning requests before single-domain checks
    for pat in (
        r"\b(help\s+me\s+plan|plan\s+(a|our|my)|planning\s+(a|our|my)|plan\s+this)\b",
        r"\b(plan.*trip|planning.*trip|plan.*pilgrimage|planning.*pilgrimage|plan.*yatra|planning.*yatra)\b",
    ):
        if re.search(pat, tl):
            return "TRIP_PLANNING"

    # 4. Check for weather intent
    for pat in _WEATHER_PATTERNS:
        if re.search(pat, tl):
            return "WEATHER"

    # 5. Check for specialized transport & timetable queries (precede generic trip planning origin phrases)
    for pat in _LIVE_TRAIN_STATUS_PATTERNS:
        if re.search(pat, tl):
            return "LIVE_TRAIN_STATUS"

    for pat in _TRAIN_SCHEDULE_PATTERNS:
        if re.search(pat, tl):
            return "TRAIN_SCHEDULE"

    for pat in _TRAIN_SEARCH_PATTERNS:
        if re.search(pat, tl):
            return "TRAIN_SEARCH"

    for pat in _FLIGHT_SEARCH_PATTERNS:
        if re.search(pat, tl):
            return "FLIGHT_SEARCH"

    for pat in _BUS_SEARCH_PATTERNS:
        if re.search(pat, tl):
            return "BUS_SEARCH"

    # 6. Check for hotel and accommodation intent
    for pat in _HOTEL_PATTERNS:
        if re.search(pat, tl):
            return "HOTEL_SEARCH"

    # 7. Check for altitude & trekking guidance
    for pat in _ALTITUDE_PATTERNS:
        if re.search(pat, tl):
            return "ALTITUDE_GUIDANCE"

    for pat in _TREKKING_PATTERNS:
        if re.search(pat, tl):
            return "TREKKING_GUIDANCE"

    # 8. Check for transport options to Bhawan
    for pat in _BHAVAN_TRANSPORT_PATTERNS:
        if re.search(pat, tl):
            return "BHAVAN_TRANSPORT"

    # 9. Budget calculation & itemized expense breakdown
    for pat in _BUDGET_CALCULATION_PATTERNS:
        if re.search(pat, tl):
            return "BUDGET_CALCULATION"

    # 10. Check for itinerary intent
    for pat in _ITINERARY_PATTERNS:
        if re.search(pat, tl):
            return "ITINERARY"

    # 11. Check for RPA availability checking intent (Week 7)
    for pat in _AVAILABILITY_PATTERNS:
        if re.search(pat, tl):
            return "AVAILABILITY"

    # 12. Strong trip-planning signals take priority (case-insensitive)
    for pat in _TRIP_PLANNING_PATTERNS:
        if re.search(pat, tl):
            return "TRIP_PLANNING"
    if _has_trip_origin_phrase(tl):
        return "TRIP_PLANNING"

    # 13. Check for pure tourism/information patterns
    for pat in _TOURISM_QUESTION_PATTERNS:
        if re.search(pat, tl):
            return "TOURISM"

    # 14. Fast-path: Greetings, acknowledgments, help
    if _is_pure_greeting(tl):
        return "GREETING"
    if _is_pure_acknowledgment(tl):
        return "ACKNOWLEDGMENT"
    if _is_pure_help(tl):
        return "HELP"

    # 15. Default — treat as trip planning (preserves prior behaviour)
    return "UNKNOWN"


def extract_requirements(text: str, current_request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper to extract trip requirements from text using legacy parser."""
    try:
        return legacy_agent.parse_request(text, current_request=current_request)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Week 7: RPA Availability Parameter Extraction & Natural Language Parsing
# ---------------------------------------------------------------------------

def parse_and_validate_yatra_date(text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[str], bool, bool, Optional[str]]:
    """
    Extracts and validates a date from natural-language user query.
    Returns: (iso_date, raw_matched_str, is_missing, is_invalid, error_reason)

    Rules:
    1. Converts understandable natural-language dates to ISO format (YYYY-MM-DD).
    2. Validates calendar correctness (e.g. 2026-02-31 is invalid).
    3. If user says 'Check availability' without a date and context has no unambiguous date,
       returns is_missing=True (do NOT fabricate or invent dates).
    4. Follow-up queries (e.g. 'Are any slots available on that date?') use unambiguous
       context from context.get('last_availability_date') or context.get('requirements', {}).get('start_date').
    """
    if not text:
        text = ""
    t = text.strip()
    tl = t.lower()

    # Relative dates
    ref_date = date.today()
    if re.search(r"\bday after tomorrow\b", tl):
        target = ref_date + timedelta(days=2)
        return target.isoformat(), "day after tomorrow", False, False, None
    elif re.search(r"\btomorrow\b", tl):
        target = ref_date + timedelta(days=1)
        return target.isoformat(), "tomorrow", False, False, None
    elif re.search(r"\btoday\b", tl):
        return ref_date.isoformat(), "today", False, False, None

    # Pattern 1: ISO format YYYY-MM-DD or YYYY/MM/DD
    m_iso = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", t)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        raw = m_iso.group(0)
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d"), raw, False, False, None
        except ValueError as ve:
            return None, raw, False, True, str(ve)

    # Pattern 2: DD-MM-YYYY or DD/MM/YYYY
    m_dmy = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", t)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        raw = m_dmy.group(0)
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d"), raw, False, False, None
        except ValueError as ve:
            return None, raw, False, True, str(ve)

    # Pattern 3: Natural language: "20 November 2026", "20th Nov 2026", "20 Nov", "20th November"
    # Match: DD [st/nd/rd/th] Month [YYYY]
    m_nat1 = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|sept|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)(?:\s*,?\s*(\d{4}))?\b",
        tl,
    )
    if m_nat1:
        d = int(m_nat1.group(1))
        m_str = m_nat1.group(2)
        m = _MONTH_MAP[m_str]
        y_str = m_nat1.group(3)
        y = int(y_str) if y_str else 2026  # target baseline year
        raw = m_nat1.group(0)
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d"), raw, False, False, None
        except ValueError as ve:
            return None, raw, False, True, str(ve)

    # Pattern 4: Natural language: "November 20, 2026" or "Nov 20th 2026"
    m_nat2 = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|sept|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b",
        tl,
    )
    if m_nat2:
        m_str = m_nat2.group(1)
        m = _MONTH_MAP[m_str]
        d = int(m_nat2.group(2))
        y_str = m_nat2.group(3)
        y = int(y_str) if y_str else 2026
        raw = m_nat2.group(0)
        try:
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d"), raw, False, False, None
        except ValueError as ve:
            return None, raw, False, True, str(ve)

    # Check for invalid day expressions like "32nd Nov", "35th October"
    m_inv_day = re.search(r"\b(\d{2,3})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|sept|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)", tl)
    if m_inv_day and int(m_inv_day.group(1)) > 31:
        return None, m_inv_day.group(0), False, True, f"Day {m_inv_day.group(1)} is invalid for calendar months"

    # Follow-up context resolution: e.g. "on that date", "same date", or follow-up question
    has_date_ref = bool(re.search(r"\b(that date|that day|same date|same day|that time)\b", tl))
    if context:
        ctx_date = context.get("last_availability_date")
        if not ctx_date and isinstance(context.get("requirements"), dict):
            ctx_date = context["requirements"].get("start_date")
        if not ctx_date and isinstance(context.get("current_request"), dict):
            ctx_date = context["current_request"].get("start_date")

        if ctx_date:
            if has_date_ref or ("availability" in tl or "slot" in tl):
                return ctx_date, "previous context date", False, False, None

    # No date supplied
    return None, None, True, False, None


def extract_and_validate_category(text: str) -> Tuple[Optional[str], Optional[str], bool, Optional[str]]:
    """
    Extracts and validates darshan category from user text against supported categories.
    Returns: (normalized_category, raw_matched_str, unsupported_category_flag, unsupported_val)
    """
    if not text:
        return None, None, False, None
    tl = text.lower()

    # Check for unsupported category phrases first
    unsupported_match = re.search(
        r"\b(super\s*vip|royal(?:\s+darshan)?|gold(?:\s+darshan)?|platinum(?:\s+darshan)?|vvip|executive(?:\s+darshan)?|special\s+priority)\b",
        tl,
    )
    if unsupported_match:
        raw_val = unsupported_match.group(0).strip().title()
        return None, raw_val, True, raw_val

    # Helicopter Darshan
    if re.search(r"\b(helicopter|heli)\b", tl):
        return "Helicopter Darshan", "Helicopter Darshan", False, None

    # VIP Darshan
    if re.search(r"\bvip\b", tl):
        return "VIP Darshan", "VIP Darshan", False, None

    # Normal Darshan
    if re.search(r"\b(normal(?:\s+darshan)?|regular(?:\s+darshan)?|general(?:\s+darshan)?|standard(?:\s+darshan)?)\b", tl):
        return "Normal Darshan", "Normal Darshan", False, None

    # None specified
    return None, None, False, None


def extract_availability_parameters(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    High-level parameter extractor mapping user natural language into structured RPA parameters.
    Ensures:
    - Dates are converted to ISO YYYY-MM-DD.
    - Dates are validated against calendar rules.
    - Category values are checked against supported mock portal categories.
    - Does not invent dates or categories when missing.
    - Accurately reports missing or invalid fields.
    """
    iso_date, raw_date, is_missing, is_invalid, invalid_reason = parse_and_validate_yatra_date(text, context=context)
    cat, raw_cat, unsupported_cat, unsupported_val = extract_and_validate_category(text)

    return {
        "date": iso_date,
        "category": cat,
        "raw_date": raw_date,
        "raw_category": raw_cat,
        "missing_date": is_missing,
        "invalid_date": is_invalid,
        "invalid_date_reason": invalid_reason,
        "unsupported_category": unsupported_cat,
        "unsupported_category_value": unsupported_val,
    }


def format_missing_date_prompt() -> str:
    """Friendly devotional clarification prompt when user has not specified a date."""
    return (
        "🙏 **Jai Mata Di!**\n\n"
        "To check live yatra darshan availability via our Playwright RPA agent, please specify your preferred date "
        "(e.g., **'20 November 2026'** or **'2026-10-20'**).\n\n"
        "You can also specify a category such as **Normal Darshan**, **VIP Darshan**, or **Helicopter Darshan**."
    )


def format_invalid_date_prompt(raw_date: Optional[str], reason: Optional[str] = "") -> str:
    """Devotional prompt rejecting an invalid calendar date."""
    reason_str = f" ({reason})" if reason else ""
    raw_str = f" **'{raw_date}'**" if raw_date else ""
    return (
        "🙏 **Jai Mata Di!**\n\n"
        f"The requested date{raw_str} is invalid{reason_str}. "
        "Please provide a valid calendar date in `YYYY-MM-DD` or `DD Month YYYY` format (e.g., **'20 November 2026'**)."
    )


def format_unsupported_category_prompt(category_val: Optional[str]) -> str:
    """Devotional prompt rejecting an unsupported darshan category."""
    cat_str = f" **'{category_val}'**" if category_val else ""
    return (
        "🙏 **Jai Mata Di!**\n\n"
        f"The requested category{cat_str} is not recognized by the Shrine Board booking system.\n\n"
        "The supported darshan categories are:\n"
        "1. **Normal Darshan** (Standard pilgrim darshan)\n"
        "2. **VIP Darshan** (Special Aarti & priority queue)\n"
        "3. **Helicopter Darshan** (Katra-Sanjhichhat helicopter service)\n\n"
        "Which category would you like to check?"
    )


def format_availability_reply(result: Dict[str, Any], requested_date: str, category: Optional[str] = None) -> str:
    """
    Interprets structured Week 5 & Week 6 RPA availability results and generates
    a warm, natural-language response.
    Handles:
    A. Successful check with slots (capacity, times, price, status)
    B. Empty calendar (no slots open, without describing as system error)
    C. Recovered error (transient failure resolved via Week 6 retry)
    D. Human handover (safe pause, reason, technical details)
    """
    # Case D: Human Handover Required
    if result.get("handover_required") or result.get("status") == "HANDOVER_REQUIRED":
        reason = result.get("handover_reason") or "Automated checking could not safely verify page state."
        guidance = result.get("guidance") or "Please verify slot availability directly on the Shrine Board portal."
        attempts = result.get("retry_attempts_used", 1)
        return (
            "🙏 **Jai Mata Di! Human Handover Notice**\n\n"
            f"Automated availability checking for **{requested_date}** could not safely continue.\n\n"
            f"• **Reason:** {reason}\n"
            f"• **Attempts Made:** {attempts}\n"
            f"• **Safety Protocol:** Our RPA agent safely paused to avoid unverified or misleading availability claims.\n"
            f"• **Pilgrim Guidance:** {guidance}\n\n"
            "_Our pilgrim support team has been notified. You may also check official Shrine Board offline counters at Katra._"
        )

    # Case F: Hard Failure (non-handover failure)
    if result.get("status") == "FAILED" or result.get("status") == "ERROR":
        err_msg = result.get("error") or "Unknown portal communication error."
        return (
            "🙏 **Jai Mata Di!**\n\n"
            f"Unable to retrieve slot availability for **{requested_date}** due to a portal communication issue: {err_msg}.\n\n"
            "Please try again in a few moments or specify another date."
        )

    # Case B: No Available Slots / Empty Calendar
    is_empty = result.get("is_empty", False)
    total_slots = result.get("total_slots", 0)
    slots = result.get("slots", [])

    cat_label = f" for **{category}**" if category else ""

    if is_empty or total_slots == 0:
        return (
            "🙏 **Jai Mata Di! Availability Status**\n\n"
            f"No yatra darshan slots are currently open for **{requested_date}**{cat_label}.\n\n"
            "ℹ️ *Note:* This is not a system error; the quota for this date is either fully allocated or not yet released by the Shrine Board.\n\n"
            "**Recommendation:** Please consider checking adjacent dates (e.g., 2026-10-20 or 2026-10-21) or an alternative darshan category."
        )

    # Case A & C: Successful extraction
    avail_count = result.get("available_count", sum(1 for s in slots if s.get("availability_status") == "available"))
    full_count = result.get("full_count", sum(1 for s in slots if s.get("availability_status") == "full"))
    unavail_count = result.get("unavailable_count", sum(1 for s in slots if s.get("availability_status") == "unavailable"))

    lines = [
        "🙏 **Jai Mata Di! Yatra Slot Availability**\n",
        f"Availability for **{requested_date}**{cat_label}: found **{total_slots}** slot{'s' if total_slots != 1 else ''} "
        f"({avail_count} available, {full_count} full, {unavail_count} unavailable):\n",
    ]

    # Mention Week 6 recovery if applicable
    if result.get("recovered"):
        lines.append("_Note: Slot statuses were successfully extracted after recovering from transient portal latency via automated retry._\n")

    for s in slots:
        slot_id = s.get("slot_id", "SLOT")
        slot_name = s.get("slot_name", "Darshan")
        session = s.get("session", "")
        slot_time = s.get("time", "")
        status = s.get("availability_status", "available")
        capacity = s.get("remaining_capacity")
        price = s.get("price", 0.0)

        price_str = f"₹{int(price)}" if price else "Free (Included)"

        if status == "available":
            cap_str = f"🟢 **Available** ({capacity} seats left)" if capacity is not None else "🟢 **Available**"
        elif status == "full":
            cap_str = "🔴 **Full** (0 seats left)"
        else:
            cap_str = "⚪ **Unavailable**"

        session_str = f" • _{session}_" if session else ""
        time_str = f" • 🕒 {slot_time}" if slot_time else ""

        lines.append(f"• **{slot_id}** — **{slot_name}**{time_str}{session_str}")
        lines.append(f"  - Status: {cap_str} | Fare: **{price_str}**")

    lines.append("\nMay Mata Vaishno Devi grant you a blessed and fulfilling yatra! Would you like to proceed with booking travel and stay for this date?")

    return "\n".join(lines)


DEVOTIONAL_GREETINGS = [
    "🙏 Jai Mata Di! Let's plan your yatra.",
    "🙏 Jai Mata Di, welcome! Tell me about your trip.",
    "🙏 Jai Mata Di! Happy to help you plan your darshan.",
]
DEVOTIONAL_CONFIRMATIONS = [
    "🙏 Jai Mata Di — your booking is confirmed. Wishing you a blessed yatra!",
    "🙏 Jai Mata Di! May your darshan be peaceful and fulfilling.",
]


def _has_llm():
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def greeting():
    return random.choice(DEVOTIONAL_GREETINGS)


def confirmation_blessing():
    return random.choice(DEVOTIONAL_CONFIRMATIONS)


def understand_request(user_text, current_request=None, api_key=None, base_url=None):
    """Returns a structured trip request dict (pax, origin, category,
    mode, start_date, end_date) - same shape build_plan() expects,
    regardless of which mode produced it, merging with current_request if present."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            return _understand_with_llm(user_text, current_request=current_request, api_key=key, base_url=base_url)
        except Exception:
            pass  # fall back safely rather than breaking the conversation
    return legacy_agent.parse_request(user_text, current_request=current_request)


def _understand_with_llm(user_text, current_request=None, api_key=None, base_url=None):
    from datetime import date
    from openai import OpenAI

    url = base_url or os.environ.get("OPENAI_BASE_URL", None)
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key, base_url=url) if url else OpenAI(api_key=api_key)
    today = date.today().isoformat()
    prev_state_str = json.dumps(current_request) if current_request else "None"

    system = f"""Extract Vaishno Devi yatra trip details from the pilgrim's message as JSON only.
The message may be in Hindi, Hinglish, English, or another language - understand it regardless of language.
Today's date is {today}.
Previous trip request state: {prev_state_str}
If previous state exists, update and merge any new/clarified details from the message into that state.
Fields: pax (integer, default 1), origin (Indian city name in English, or null),
category (one of "Normal Darshan","VIP Darshan","Helicopter Darshan", or null),
mode (one of "flight","train","bus", or null if no preference stated),
duration_days (integer or null), season (string or null), sightseeing (boolean),
start_date (YYYY-MM-DD), end_date (YYYY-MM-DD). If no dates mentioned, use the next 14 days.
Respond with ONLY valid JSON, no markdown or extra text."""

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()
    parsed = json.loads(raw)
    return legacy_agent.merge_requests(current_request, parsed, text=user_text)


def format_tourism_reply(tourism_result):
    """Formats a tourism knowledge/content result into a readable, structured reply string
    based on query_kind so questions are answered directly and consistently."""
    import explore_data

    kind = tourism_result.get("query_kind") or "general"
    places = tourism_result.get("matched_places") or []
    primary = tourism_result.get("primary_place") or (places[0] if places else None)
    query = (tourism_result.get("query") or "").lower()
    is_followup = tourism_result.get("is_followup", False)

    # 0a. Altitude & Elevation Inquiries
    if kind == "altitude":
        p = primary or (places[0] if places else None)
        if p and p.get("altitude_m"):
            name = p.get("name", "Bhairon Ghati")
            alt_m = p.get("altitude_m")
            alt_ft = round(alt_m * 3.28084)
            cat_name = p.get("category_type", "Religious Site").replace("_", " ").title()
            return (
                f"🙏 **Jai Mata Di!**\n\n"
                f"### Altitude of {name}\n\n"
                f"**The altitude of {name} is approximately {alt_m:,} metres ({alt_ft:,} feet) above sea level.**\n\n"
                f"• **Elevation:** ~{alt_m} m / ~{alt_ft} ft\n"
                f"• **Category:** {cat_name}\n"
                f"• **Location:** {p.get('location_route') or p.get('distance', '')}\n\n"
                f"**Climatic & Trek Advisory:**\n"
                f"• Temperatures at this elevation are typically 5°C to 8°C cooler than Katra base town. Carrying a light windcheater or jacket is advised year-round.\n"
                f"• For pilgrims climbing on foot, the incline from Bhawan is steep (~426 m elevation gain over 2 km). A passenger ropeway is also available from Bhawan.\n\n"
                f"_Would you like trekking tips or ropeway details for {name}?_"
            )
        else:
            return (
                "🙏 **Jai Mata Di!**\n\n"
                "### Elevation Profile along the Vaishno Devi Pilgrimage Route\n\n"
                "• **Katra Base Town:** ~750 m (~2,460 ft)\n"
                "• **Ban Ganga:** ~800 m (~2,625 ft)\n"
                "• **Charan Paduka:** ~1,030 m (~3,380 ft)\n"
                "• **Ardhkuwari Temple:** ~1,400 m (~4,593 ft)\n"
                "• **Sanjichhat (Helipad):** ~1,768 m (~5,800 ft)\n"
                "• **Holy Cave Shrine (Bhawan):** ~1,585 m (~5,200 ft)\n"
                "• **Bhairavnath Temple (Bhairon Ghati):** ~2,011 m (~6,600 ft) *(Highest point of pilgrimage)*\n\n"
                "**Nearby Regional Altitudes:**\n"
                "• **Patnitop Hill Station:** ~2,024 m (~6,640 ft)\n"
                "• **Sinthan Top Mountain Pass:** ~3,748 m (~12,296 ft)\n\n"
                "_Which destination's weather or trek conditions would you like to explore?_"
            )

    # 0b. Trekking Guidance & Route Tips
    if kind == "trekking_tips":
        p = primary or (places[0] if places else None)
        place_name = p.get("name", "Bhairon Ghati") if p else "Bhairon Ghati"
        return (
            f"🙏 **Jai Mata Di!**\n\n"
            f"### Trekking Tips & Advisory for {place_name}\n\n"
            f"The stretch to {place_name} (~2,011 m elevation) is the steepest section of the pilgrimage:\n\n"
            "**Key Trekking Advice:**\n"
            "1. **Steep Gradient & Pacing:** The 2 km uphill trek from Bhawan rises sharply by ~426 metres. Maintain a steady, relaxed pace and take 2-minute breathers rather than prolonged halts.\n"
            "2. **Footwear:** Wear broken-in sports shoes or trekking shoes with deep rubber tread. Avoid leather shoes, flat slippers, or sandals.\n"
            "3. **Passenger Ropeway Option:** A modern cable car operates between Bhawan and Bhairon Temple. It takes only ~3–5 minutes (approx ₹100 round-trip) and is strongly recommended for elderly pilgrims, children, and those with knee or breathing difficulties.\n"
            "4. **Hydration & Warm Clothing:** Keep hydrated with warm water or lemon electrolytes. Because of the 2,011 m altitude, strong cold winds are frequent—carry a windcheater or fleece jacket.\n"
            "5. **Spiritual Completeness:** As per sacred tradition, the Vaishno Devi Yatra is believed to be blessed and fulfilled only after seeking the darshan of Baba Bhairavnath.\n\n"
            "_Would you like details on ropeway operating hours or pony/palki availability?_"
        )

    # 0c. Transport Options to Bhawan
    if kind == "bhavan_transport":
        return (
            "🙏 **Jai Mata Di!**\n\n"
            "### Transport Options to Reach Bhawan from Katra\n"
            "*The Shri Mata Vaishno Devi Shrine Board (SMVDSB) provides multiple transit modes across the 13 km route:*\n\n"
            "1. **Walking / Foot Trek (Traditional Route):**\n"
            "   • Distance: ~13 km from Banganga to Bhawan via Charan Paduka and Ardhkuwari.\n"
            "   • Paved track with overhead sheds, water coolers, medical booths, and vegetarian eateries throughout.\n\n"
            "2. **Tarakote Marg (Alternative Walking Route):**\n"
            "   • Distance: ~12 km gentler gradient track from Katra to Ardhkuwari.\n"
            "   • Exclusively for pedestrians—no ponies or mules permitted. Very clean, quiet, and eco-friendly.\n\n"
            "3. **Battery-Operated Auto / Electric Vehicles:**\n"
            "   • Operates between Ardhkuwari and Bhawan (~5.5 km) on the alternate Himkoti route.\n"
            "   • Dedicated priority for senior citizens, persons with disabilities, and medical cases. Nominal fare (approx ₹350), subject to queue token.\n\n"
            "4. **Helicopter Service:**\n"
            "   • Operates between Katra Helipad and Sanjichhat Helipad (~8 minutes flying time).\n"
            "   • Remaining distance from Sanjichhat to Bhawan is ~2.5 km (walk, battery car, or palki). Advance booking via official Shrine Board portal.\n\n"
            "5. **Palki / Palanquin & Pithoo Service:**\n"
            "   • Available from Katra and Ardhkuwari. Palkis are carried by 4 porters; pithoos carry small children or luggage at fixed official rates.\n\n"
            "6. **Ponies / Mules:**\n"
            "   • Available along the traditional route from Banganga. Strict government-fixed tariff based on destination.\n\n"
            "**Connecting Bhawan to Bhairon Temple:**\n"
            "• **Bhairon Ropeway (Cable Car):** Takes ~3–5 minutes from Bhawan to Bhairon Temple (~₹100 per passenger round-trip).\n\n"
            "_Would you like to check current weather conditions or hotel stays in Katra?_"
        )

    # 1. Aarti Timings
    if kind == "aarti":
        aarti = tourism_result.get("aarti_timings") or {}
        morning = aarti.get("morning", {})
        summer = aarti.get("evening_summer", {})
        winter = aarti.get("evening_winter", {})
        return (
            "🙏 **Jai Mata Di!**\n\n"
            "### Aarti Timings at Vaishno Devi Shrine\n"
            "*Darshan pauses completely during these daily Aarti windows at the main Bhawan:*\n\n"
            "**Daily Schedule:**\n"
            f"• **Morning Aarti:** {morning.get('start', '-')} – {morning.get('end', '-')} ({morning.get('note', '')})\n"
            f"• **Evening Aarti (Summer, Apr–Sep):** {summer.get('start', '-')} – {summer.get('end', '-')}\n"
            f"• **Evening Aarti (Winter, Oct–Mar):** {winter.get('start', '-')} – {winter.get('end', '-')}\n\n"
            "**Important Note for Pilgrims:**\n"
            f"{aarti.get('general_note', '')}\n\n"
            "_Would you like to check trek route options or Yatra Slip registration steps next?_"
        )

    # 2. Packing Guidance
    if kind == "packing":
        packing = tourism_result.get("packing_guidance") or {}
        recs = "\n".join(f"• {item}" for item in packing.get("recommended", []))
        restricted = "\n".join(f"• {item}" for item in packing.get("commonly_restricted", []))
        disclaimer = packing.get("disclaimer", "")
        return (
            "🙏 **Jai Mata Di!**\n\n"
            "### Packing Guidance for Vaishno Devi Yatra\n"
            "*Essential items to pack and items to avoid during your trek:*\n\n"
            "**Recommended Essentials:**\n"
            f"{recs}\n\n"
            "**Restricted & Prohibited Items:**\n"
            f"{restricted}\n\n"
            "**Practical Tips:**\n"
            "• Keep your trek bag lightweight. Cloakroom and locker facilities are available at Katra and Bhawan for extra luggage.\n"
            "• Wear well-broken-in sports or trekking shoes to avoid blisters during the 13 km climb.\n\n"
            f"_{disclaimer}_\n\n"
            "_Would you like to check Aarti timings or route options next?_"
        )

    # 3. Yatra Registration
    if kind == "registration":
        reg = tourism_result.get("registration_info") or {}
        steps = "\n".join(f"• {step}" for step in reg.get("how_to_register", []))
        need = "\n".join(f"• {item}" for item in reg.get("what_youll_need", []))
        return (
            "🙏 **Jai Mata Di!**\n\n"
            "### Vaishno Devi Yatra Registration (Yatra Slip / Parchi)\n"
            f"*Yatra registration is mandatory for every pilgrim and is **{reg.get('cost', 'Free')}**.*\n\n"
            "**Key Requirements:**\n"
            f"• {reg.get('mandatory_note', '')}\n\n"
            "**How to Register:**\n"
            f"{steps}\n\n"
            "**What You Need to Bring:**\n"
            f"{need}\n\n"
            f"**Important Reminder:** {reg.get('reminder', '')}\n\n"
            "_Would you like to search travel options to Katra or view trek route options?_"
        )

    # 4. Route Options
    if kind == "routes":
        parts = [
            "🙏 **Jai Mata Di!**\n\n"
            "### Trek & Travel Route Options to Bhawan\n"
            "*Detailed routes available for reaching the main Shrine from Katra base town:*"
        ]
        for route in tourism_result.get("route_options") or []:
            parts.append(
                f"**{route['name']}** ({route.get('distance', '')}, {route.get('duration', '')})\n"
                f"• **Path:** {route.get('path', '')}\n"
                f"• **Details:** {route.get('notes', '')}"
            )

        return "\n\n".join(parts)

    # 5. Helpline
    if kind == "helpline":
        helpline = tourism_result.get("helpline") or {}
        return (
            "🙏 **Jai Mata Di!**\n\n"
            "### Official Yatra Helpline Information\n\n"
            f"• **Toll-Free Helpline:** `{helpline.get('official_yatra_helpline', '-')}`\n"
            f"• **Note:** {helpline.get('note', '')}\n\n"
            "_Feel free to ask about Aarti timings, packing guidance, or registration steps._"
        )

    # 6. Vaishno History
    if kind == "vaishno_history" and not primary:
        sections = tourism_result.get("vaishno_history") or []
        parts = [
            "🙏 **Jai Mata Di!**\n\n"
            "### History & Sacred Legend of Vaishno Devi\n"
            "*Drawn from existing trek-site records documenting the pilgrimage legend:*\n"
        ]
        for section in sections:
            parts.append(f"**{section['name']}**\n{section['historical_background']}")
        if not sections:
            parts.append("I don't have a standalone Vaishno Devi history article in the current knowledge set.")

        return "\n\n".join(parts)

    # 7. Nearby Places (Concise, no dump)
    if kind == "nearby_places" and places:
        q_low = (tourism_result.get("query") or "").lower()
        if "jammu" in q_low:
            title_text = "Key Historical & Cultural Places in/near Jammu" if any(k in q_low for k in ["historic", "heritage", "palace", "fort", "ancient"]) else "Key Places to Visit in/near Jammu"
            sub_text = "*Verified destinations across Jammu City and surrounding heritage circuits:*"
            travel_note = "\n**Local Travel Note:** Taxis and local autos are readily available in Jammu city for temple and heritage palace circuits.\n"
        elif "kishtwar" in q_low:
            title_text = "Places to Visit in Kishtwar"
            sub_text = "*Verified mountain destinations and pilgrimage shrines in Kishtwar District:*"
            travel_note = "\n**Local Travel Note:** Accessible via scenic mountain drive from Jammu/Katra via NH-244.\n"
        elif "srinagar" in q_low or "kashmir" in q_low:
            title_text = "Places to Visit in Srinagar & Kashmir Valley"
            sub_text = "*Verified Mughal gardens, lakes, and heritage sites across Srinagar:*"
            travel_note = "\n**Local Travel Note:** Accessible from Jammu/Katra via NH-44 corridor or direct flight into Srinagar.\n"
        else:
            title_text = "Key Places to Visit Around Katra"
            sub_text = "*Concise guide to popular shrines and spots along the trek and around Katra town:*"
            travel_note = "\n**Local Travel Note:** Private taxis or auto-rickshaws are readily available in Katra town for nearby temples and nature spots.\n"

        lines = [
            "🙏 **Jai Mata Di!**\n\n",
            f"### {title_text}\n",
            f"{sub_text}\n\n",
        ]
        for p in places[:7]:
            dist_str = p.get('distance') or (f"District {p['district']}" if p.get('district') else (f"{p['region']} Region" if p.get('region') else ''))
            lines.append(
                f"• **{p['name']}** ({p.get('category', '')}, {dist_str}): {p.get('description', '')}\n"
            )
        lines.append(travel_note)

        return "".join(lines)

    # 8. Visiting Hours Specific Query
    if kind == "visiting_hours":
        p = primary or (places[0] if places else None)
        if p:
            name = p.get("name", "")
            is_religious = p.get("category_type") == "religious_site"
            alt_m = p.get("altitude_m")
            alt_str = f"~{alt_m:,} m (~{round(alt_m * 3.28084):,} ft)" if alt_m else "N/A"
            if is_religious:
                darshan = p.get("darshan_timings") or p.get("timings", "Open 24 hours (brief pauses during daily Aarti)")
                aarti = p.get("aarti_timings") or "Morning & Evening (refer to daily schedule)"
                return (
                    f"🙏 **Jai Mata Di!**\n\n"
                    f"### Visiting & Darshan Hours: {name}\n\n"
                    f"• **Darshan Timings:** {darshan}\n"
                    f"• **Aarti Timings:** {aarti}\n"
                    f"• **Altitude:** {alt_str}\n"
                    f"• **Entry Fee:** {p.get('entry_fee', 'Free')}\n"
                    f"• **Category:** Religious Site\n"
                    f"• **Location:** {p.get('location_route') or p.get('distance', '')}\n\n"
                    f"**Pilgrim Advisory:**\n"
                    f"{p.get('religious_information') or p.get('description', '')}\n"
                )
            else:
                vh = p.get("visiting_hours") or "Daytime access (approx. 06:00 - 17:00), strictly subject to weather conditions and seasonal road clearance"
                best_time = p.get("best_time_to_visit", "April to October")
                entry = p.get("entry_fee", "Free / Nil")
                access = p.get("accessibility", "Accessible by motorable road, weather permitting")
                seasonal = p.get("seasonal_restrictions", "Subject to seasonal snow/weather clearances")
                cat_name = p.get("category_type", "Tourist Destination").replace("_", " ").title()
                return (
                    f"🙏 **Jai Mata Di!**\n\n"
                    f"### Visiting Hours & Travel Guide: {name}\n\n"
                    f"• **Visiting Hours:** {vh}\n"
                    f"• **Altitude:** {alt_str}\n"
                    f"• **Category:** {cat_name}\n"
                    f"• **Best Time to Visit:** {best_time}\n"
                    f"• **Entry Fee:** {entry}\n"
                    f"• **Accessibility:** {access}\n"
                    f"• **Seasonal Restrictions:** {seasonal}\n\n"
                    f"**Overview:**\n"
                    f"{p.get('description', '')}\n\n"
                    f"**Note:** {name} is a scenic nature/tourism destination. Please confirm road and weather clearance before visiting.\n"
                )

    # 9. Single Place / Place Follow-up Question
    primary = tourism_result.get("primary_place") or (places[0] if (places and kind in ("place", "visiting_hours")) else None)
    if primary:
        p = primary
        category = p.get("category", "")
        travel_note = explore_data.get_local_travel_note(category)
        is_religious = p.get("category_type") == "religious_site"
        alt_m = p.get("altitude_m")
        alt_str = f"~{alt_m:,} m (~{round(alt_m * 3.28084):,} ft)" if alt_m else "N/A"

        if category == "On the trek route":
            route_pos_label = "Pilgrimage Route Position"
            route_pos = p.get("location_route") or "Located directly along the main Vaishno Devi trek route between Katra and Bhawan."
        elif category in ("Nearby temple", "Nature"):
            route_pos_label = "Pilgrimage Route Position"
            route_pos = p.get("location_route") or "Located near Katra base town — easily visited as a short excursion before or after the trek."
        elif category in ("Hill station", "Hill station / adventure"):
            route_pos_label = "Pilgrimage Route Position"
            route_pos = p.get("location_route") or "A prominent hill station in the Jammu region, commonly visited as a full-day trip from Katra or Jammu."
        elif category == "Kashmir" or p.get("region") == "Kashmir":
            route_pos_label = "Location & Route"
            route_pos = p.get("location_route") or "Located in the Kashmir Valley."
        else:
            route_pos_label = "Pilgrimage Route Position"
            route_pos = p.get("location_route") or "Located in or near Jammu city, convenient for pilgrims arriving or departing via Jammu."

        if is_followup and re.search(r"\b(how far|distance|where is|location)\b", query):
            return (
                f"🙏 **Jai Mata Di!**\n\n"
                f"### Distance & Travel: {p['name']}\n\n"
                f"• **Distance:** {p.get('distance', 'N/A')}\n"
                f"• **Altitude:** {alt_str}\n"
                f"• **Category:** {category}\n"
                f"• **{route_pos_label}:** {route_pos}\n"
                f"• **Local Travel Note:** {travel_note}\n\n"
                f"**Overview:** {p.get('description', '')}\n\n"
            )

        if is_followup and re.search(r"\b(what (can|to) (i|we) do|activities|things to do|see)\b", query):
            practical_lines = [
                f"• **Altitude:** {alt_str}",
                f"• **Entry Fee:** {p.get('entry_fee', 'Free')}",
                f"• **Distance:** {p.get('distance', 'N/A')}",
            ]
            if is_religious:
                practical_lines.insert(0, f"• **Darshan Timings:** {p.get('darshan_timings') or p.get('timings', 'Open 24 hours')}")
            else:
                practical_lines.insert(0, f"• **Visiting Hours:** {p.get('visiting_hours') or 'Daytime access'}")
                if p.get("best_time_to_visit"):
                    practical_lines.append(f"• **Best Time to Visit:** {p['best_time_to_visit']}")

            return (
                f"🙏 **Jai Mata Di!**\n\n"
                f"### What to Do & See at {p['name']}\n\n"
                f"**Main Attractions & Highlights:**\n"
                f"• {p.get('description', '')}\n"
                f"• **Historical / Cultural Background:** {p.get('historical_background', '')}\n\n"
                f"**Practical Information:**\n"
                + "\n".join(practical_lines) + "\n\n"
            )

        # Entry fee formatting without inventing facts
        fee_val = p.get('entry_fee')
        if fee_val:
            fee_str = fee_val
        elif p.get('is_curated', True):
            fee_str = 'Free'
        else:
            fee_str = 'Information not officially published (consult local district authorities)'

        # Visiting hours formatting without inventing facts
        timing_val = p.get('darshan_timings') or p.get('visiting_hours') or p.get('timings')
        if timing_val:
            timing_str = timing_val
        elif p.get('is_curated', True):
            timing_str = 'Open 24 hours' if is_religious else 'Daytime access (weather permitting)'
        else:
            timing_str = 'Information not officially published (consult local district authorities)'

        # Standard Place Card
        practical_info = [
            f"• **Altitude:** {alt_str}",
            f"• **Entry Fee:** {fee_str}",
            f"• **Local Travel:** {travel_note}",
        ]
        if is_religious:
            practical_info.insert(0, f"• **Darshan Timings:** {timing_str}")
            if p.get("aarti_timings"):
                practical_info.insert(1, f"• **Aarti Timings:** {p['aarti_timings']}")
        else:
            practical_info.insert(0, f"• **Visiting Hours:** {timing_str}")
            if p.get("best_time_to_visit"):
                practical_info.append(f"• **Best Time to Visit:** {p['best_time_to_visit']}")
            if p.get("accessibility"):
                practical_info.append(f"• **Accessibility:** {p['accessibility']}")

        source_note = ""
        if p.get("source_url"):
            domain = p.get("source_domain") or "District Administration"
            source_note = f"\n\n*Verified official record: [{domain}]({p['source_url']})*"

        return (
            f"🙏 **Jai Mata Di!**\n\n"
            f"### {p['name']}\n"
            f"*{category} · {p.get('distance', '')} · Altitude: {alt_str}*\n\n"
            f"**Overview**\n"
            f"{p.get('description', '')}\n\n"
            f"**Significance & Background**\n"
            f"{p.get('historical_background', '')}\n\n"
            f"**{route_pos_label}**\n"
            f"{route_pos}\n\n"
            f"**Practical Information**\n"
            + "\n".join(practical_info)
            + f"{source_note}\n\n"
        )

    # 9. Fallback
    return (
        "🙏 **Jai Mata Di!**\n\n"
        "I can help with places around Katra, Aarti timings, packing guidance, Yatra registration, "
        "and historical legends of shrines like Bhairavnath and Ardhkuwari. "
        "Feel free to ask any tourism question or tell me where you're traveling from to plan your trip!"
    )


def craft_reply(user_text, plan_status, context, api_key=None, base_url=None):
    """Generates the natural-language reply shown to the pilgrim,
    adapted to their language if an LLM is available, with devotional
    tone woven in. Falls back to plain templated English otherwise."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            return _craft_reply_with_llm(user_text, plan_status, context, key, base_url)
        except Exception:
            pass
    return _craft_reply_template(plan_status, context)


def _craft_reply_template(plan_status, context):
    templates = {
        "NEEDS_INFO": f"🙏 Jai Mata Di! {context.get('message', 'Could you share a bit more about your trip?')}",
        "NO_AVAILABILITY": f"🙏 I couldn't find matching options for those dates. {context.get('message', '')}",
        "NO_COMBINATION": f"🙏 {context.get('message', 'No valid combination found for those dates.')}",
        "PLAN_READY": (
            f"🙏 Jai Mata Di! I found {context.get('alt_flights_count', 0)} travel option(s) and "
            f"{context.get('alt_slots_count', 0)} darshan slot option(s). Here are the best matches — "
            "take a look below."
        ),
    }
    return templates.get(plan_status, "🙏 Jai Mata Di! Let me know how I can help with your yatra.")


def _craft_reply_with_llm(user_text, plan_status, context, api_key, base_url=None):
    from openai import OpenAI

    url = base_url or os.environ.get("OPENAI_BASE_URL", None)
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key, base_url=url) if url else OpenAI(api_key=api_key)
    system = """You are a warm, respectful assistant helping pilgrims plan a Vaishno Devi yatra.
Reply in the SAME language/style the pilgrim used in their message (Hindi, Hinglish, English, etc).
Keep replies short (2-3 sentences), naturally include a respectful devotional touch such as
"Jai Mata Di" where it fits, and never invent booking details not present in the context provided."""

    user_msg = f"Pilgrim's message: {user_text}\nSearch result status: {plan_status}\nContext: {context}"
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
