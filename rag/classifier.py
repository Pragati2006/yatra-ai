"""
rag/classifier.py
Domain Relevance Classification Engine for Yatra AI Knowledge Retrieval.

Classifies user queries prior to RAG vector search into supported, unsupported,
ambiguous, partially_supported, or context_dependent categories.
Reuses canonical place aliases from agents.knowledge_agent._PLACE_ALIASES.
Prevents false-positive feature-hashing collisions for general or adversarial queries.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Reuse existing place aliases from knowledge_agent to maintain consistency
try:
    from agents.knowledge_agent import _PLACE_ALIASES
except ImportError:
    _PLACE_ALIASES = {}

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Structured result of domain relevance classification."""
    status: str  # 'supported', 'unsupported', 'ambiguous', 'partially_supported', 'context_dependent'
    primary_domain: Optional[str] = None  # One of the 6 knowledge domains or None
    detected_entities: List[str] = field(default_factory=list)
    rationale: str = ""
    requires_context: bool = False
    confidence: str = "moderate"  # 'high', 'moderate', 'low', 'none'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "primary_domain": self.primary_domain,
            "detected_entities": self.detected_entities,
            "rationale": self.rationale,
            "requires_context": self.requires_context,
            "confidence": self.confidence,
        }


class DomainRelevanceClassifier:
    """
    Deterministic domain-relevance classifier and anti-collision guard.
    Evaluates whether a query genuinely pertains to Vaishno Devi and J&K tourism,
    or is an unrelated general query / adversarial keyword-overlap question.
    """

    # The 6 verified knowledge base domains
    SUPPORTED_DOMAINS = [
        "vaishno_devi_pilgrimage",
        "registration_guidance",
        "routes_and_trekking",
        "jk_regional_tourism",
        "faqs",
        "cultural_heritage",
    ]

    # High-signal multi-word keyphrases for supported domains
    DOMAIN_KEYPHRASES: Dict[str, List[str]] = {
        "vaishno_devi_pilgrimage": [
            "vaishno devi", "mata vaishno", "holy pindies", "pindies", "pindi",
            "garbh joon", "garbhjoon", "charan paduka", "banganga", "aarti",
            "atka aarti", "darshan", "trikuta", "bhawan", "holy cave", "shrine board",
            "smvdsb", "bhet", "darshan slip", "ardhkuwari", "adhkuwari", "bhairavnath",
            "bhairon", "nine months", "meditate", "meditated", "shridhar", "pandit shridhar",
            "sanctum", "sanctorum", "prayer sessions", "arrow", "baan", "langoor veer",
            "holy footprints", "footprints", "natural rock forms", "revered goddess",
        ],
        "registration_guidance": [
            "rfid", "rfid card", "pilgrim pass", "yatra slip", "yatra parchi",
            "registration counter", "yatra registration", "aadhaar", "mandatory card",
            "tracking badge", "langar", "free meal", "community meal", "community meals",
            "free food", "cloakroom", "locker", "lockers", "luggage storage",
            "medical dispensary", "oxygen kiosk", "oxygen aid", "helpline", "1800-180-7198",
            "narayana hospital", "medical facility", "medical center", "bhojanalaya",
            "blanket store", "katra railway station counter", "breathlessness",
            "nocturnal lodging", "dormitory", "night stay", "medical care", "dispensaries",
            "bhojanalayas", "rfid pass", "yatra pass", "medical facilities", "langars",
        ],
        "routes_and_trekking": [
            "tarakote", "tarakote marg", "traditional trek", "traditional route",
            "banganga route", "ropeway", "cableway", "aerial gondola", "battery car", "battery cars", "battery operated", "battery-operated", "battery operated cars", "electric cart", "electric carts", "electric transport",
            "helicopter", "helicopters", "palki", "palanquin", "pithoo", "pony", "ponies",
            "trek distance", "return route", "walking track", "bhairon ropeway",
            "sanjichhat", "himkoti", "ban ganga", "cable car", "aerial ropeway",
            "avoid ponies", "gentler route", "stairs vs ramp", "heavy luggage",
            "difficulty", "how difficult", "how steep", "can we walk", "walking time",
            "how long does it take", "how far", "track status", "night trek", "trek at night", "safe at night", "walk at night", "safe to trek at night", "safe to trek", "night trekking", "trekking at night", "monsoon", "rain on track", "difference between",
        ],
        "jk_regional_tourism": [
            "patnitop", "sanasar", "nathatop", "shiv khori", "stalagmite", "ransoo",
            "reasi", "bahu fort", "raghunath temple", "amar mahal", "dogra palace",
            "peer kho", "dal lake", "gulmarg", "pahalgam", "sonamarg", "kashmir",
            "kashmir valley", "baba dhansar", "jhajjar kotli", "mansar lake", "surinsar",
            "chenani nashri", "gondola gulmarg", "shikara", "bhasmasura", "bhasmasur",
            "skiing", "snow slope", "hill retreat",
        ],
        "faqs": [
            "best time to visit", "best time of year", "best time", "best month", "best season", "when to visit", "monsoon", "rain", "raining", "rainfall", "rainy season",
            "prohibited items", "prohibited", "allowed items",
            "forbidden", "forbidden inside", "animal products", "leather belt",
            "mobile phone", "camera allowed", "senior citizen", "senior citizens", "seniors",
            "elderly", "parents", "old age", "disability", "differently abled", "handicapped",
            "wheelchair", "wheelchairs", "battery cart senior", "weather in winter", "raincoat",
            "locker fee", "lockers", "cloakroom", "cloakrooms", "rules inside sanctum",
            "tobacco prohibited", "alcohol prohibited", "forbidden items", "what to pack",
            "drone", "drone photography", "suitable for", "safe for", "night trek", "trek at night",
        ],
        "cultural_heritage": [
            "dogra", "dogra heritage", "dogra dynasty", "kaladi", "rajma chawal",
            "bhaderwah", "sund panjeeri", "dogra cuisine", "jammu culture", "navratri",
            "gulab singh", "ranbir singh", "dogri", "traditional food", "dogra art",
        ],
    }

    # Stopwords to filter prior to generic word evaluation
    STOPWORDS: Set[str] = {
        "the", "a", "an", "of", "to", "in", "is", "for", "and", "or", "on", "at",
        "by", "from", "with", "as", "it", "this", "that", "where", "did", "how",
        "what", "can", "are", "do", "does", "be", "tell", "me", "about", "which",
        "when", "who", "why", "we", "i", "you", "our", "my", "your",
    }

    # Generic individual words that DO NOT by themselves substantiate relevance
    GENERIC_WORDS: Set[str] = {
        "temple", "cave", "water", "travel", "history", "doctor", "river",
        "food", "animal", "money", "mountain", "tree", "forest", "book",
        "card", "route", "trip", "tour", "visit", "go", "place", "best",
        "story", "man", "woman", "person", "road", "bus", "train", "flight",
    }

    # Explicit out-of-domain keywords (pop culture, world politics, international geography, tech, etc.)
    OUT_OF_DOMAIN_CUES: Set[str] = {
        "interstellar", "nolan", "movie", "actor", "actress", "hollywood", "bollywood",
        "australia", "madagascar", "japan", "france", "germany", "america", "usa", "uk",
        "prime minister", "president", "chancellor", "stock price", "apple inc", "nasdaq",
        "bitcoin", "crypto", "cryptocurrency", "blockchain", "c++", "c++20", "python",
        "singleton", "thread-safe", "docker", "kubernetes", "algorithm", "compiler",
        "lionel messi", "cristiano ronaldo", "world cup", "football", "cricket match",
        "sourdough", "baking bread", "french sourdough", "quantum computing",
        "carburetor", "ford mustang", "nuclear physics", "chemistry of water",
    }

    # Adversarial patterns that contain pilgrimage words in inappropriate / off-domain contexts
    ADVERSARIAL_PATTERNS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(beef|pork|eating beef|meat in temple)\b", re.IGNORECASE), "Dietary taboo in Hindu shrine / adversarial prompt"),
        (re.compile(r"\b(feed.*monkeys.*holy water|monkey.*holy water)\b", re.IGNORECASE), "Adversarial animal feeding scenario"),
        (re.compile(r"\b(movie about.*temple|film.*cave)\b", re.IGNORECASE), "Cinema/entertainment query"),
        (re.compile(r"\b(chemistry of.*water.*cave|chemical composition)\b", re.IGNORECASE), "Scientific analysis out of scope"),
        (re.compile(r"\b(tobacco smoke.*mountain trees|smoke.*trees)\b", re.IGNORECASE), "Hypothetical biological/environmental prompt"),
        (re.compile(r"\b(doctor.*recommend.*beef)\b", re.IGNORECASE), "Adversarial health assertion in sacred context"),
    ]

    # Context-dependent indicator phrases
    CONTEXT_DEPENDENT_PATTERNS: List[re.Pattern] = [
        re.compile(r"^(what|how) about the (return route|other route|timings|charges|fare)\b", re.IGNORECASE),
        re.compile(r"^how much (for that|does it cost|is the ticket)\b", re.IGNORECASE),
        re.compile(r"^(how far is it|what is the travel distance|what is the distance)\b", re.IGNORECASE),
        re.compile(r"^can we go there next\b", re.IGNORECASE),
        re.compile(r"^what are the timings for this\b", re.IGNORECASE),
        re.compile(r"^is it open (now|today|at night)\b", re.IGNORECASE),
        re.compile(r"^tell me more (about that|about it)\b", re.IGNORECASE),
    ]

    def __init__(self):
        # Build canonical place aliases map (case-insensitive keys)
        self.place_aliases: Dict[str, str] = {}
        for alias, canonical in _PLACE_ALIASES.items():
            self.place_aliases[alias.lower()] = canonical

        # Pre-compile multi-word domain keyphrases
        self.compiled_domain_phrases: Dict[str, List[re.Pattern]] = {}
        for domain, phrases in self.DOMAIN_KEYPHRASES.items():
            self.compiled_domain_phrases[domain] = [
                re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)
                for p in phrases
            ]

    def _extract_entities(self, text: str) -> List[str]:
        """Extracts known pilgrimage and J&K tourism entities from text."""
        entities = []
        lower_text = text.lower()

        # Check place aliases sorted by length descending (longest match priority)
        sorted_aliases = sorted(self.place_aliases.keys(), key=len, reverse=True)
        matched_spans = []

        for alias in sorted_aliases:
            start_pos = 0
            while True:
                idx = lower_text.find(alias, start_pos)
                if idx == -1:
                    break
                end_pos = idx + len(alias)
                # Word boundary check
                left_boundary = (idx == 0 or not lower_text[idx - 1].isalnum())
                right_boundary = (end_pos == len(lower_text) or not lower_text[end_pos].isalnum())
                if left_boundary and right_boundary:
                    overlap = any(s <= idx < e or s < end_pos <= e for s, e in matched_spans)
                    if not overlap:
                        matched_spans.append((idx, end_pos))
                        canonical = self.place_aliases[alias]
                        if canonical not in entities:
                            entities.append(canonical)
                start_pos = idx + len(alias)

        # Also check high-value domain entities not in place aliases
        other_entities = [
            ("rfid", "RFID Pilgrim Pass"),
            ("garbh joon", "Garbh Joon Cave"),
            ("pindies", "Holy Pindies"),
            ("holy pindies", "Holy Pindies"),
            ("tarakote marg", "Tarakote Marg"),
            ("tarakote", "Tarakote Marg"),
            ("ropeway", "Bhairon Ropeway"),
            ("cableway", "Bhairon Ropeway"),
            ("langar", "SMVDSB Langar"),
            ("battery car", "Battery Operated Vehicle"),
            ("electric cart", "Battery Operated Vehicle"),
            ("dogra heritage", "Dogra Cultural Heritage"),
            ("kaladi", "Jammu Kaladi"),
        ]

        for phrase, canonical_name in other_entities:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lower_text) and canonical_name not in entities:
                entities.append(canonical_name)

        return entities

    def classify(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classifies the user query against the 6 supported knowledge domains.

        Args:
            query: User's raw question.
            conversation_context: Optional dictionary containing previous turn info,
                                  such as 'last_tourism_place', 'recent_domain', or previous messages.

        Returns:
            ClassificationResult object with status, domain, entities, rationale, confidence.
        """
        cleaned = (query or "").strip()
        if not cleaned:
            return ClassificationResult(
                status="unsupported",
                rationale="Query string is empty",
                confidence="high",
            )

        lower_query = cleaned.lower()
        tokens = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", lower_query).split() if len(w) > 1]

        # 1. Check Adversarial Patterns (highest priority reject)
        for pattern, reason in self.ADVERSARIAL_PATTERNS:
            if pattern.search(cleaned):
                return ClassificationResult(
                    status="unsupported",
                    rationale=f"Rejected by adversarial pattern guard: {reason}",
                    confidence="high",
                )

        # 2. Check Explicit Out-of-Domain Cues
        matched_out_cues = [cue for cue in self.OUT_OF_DOMAIN_CUES if cue in lower_query]
        if matched_out_cues:
            return ClassificationResult(
                status="unsupported",
                rationale=f"Query explicitly mentions out-of-domain topics: {', '.join(matched_out_cues[:3])}",
                confidence="high",
            )

        # 3. Check for Context-Dependent Follow-Up Queries
        for cd_pattern in self.CONTEXT_DEPENDENT_PATTERNS:
            if cd_pattern.search(cleaned):
                # Try to resolve using conversation context (handling both top-level and state dict)
                st = (conversation_context.get("state") or {}) if isinstance(conversation_context, dict) else {}
                ctx_place = conversation_context.get("last_tourism_place") or st.get("last_tourism_place") if conversation_context else None
                ctx_dom = conversation_context.get("recent_domain") or st.get("recent_domain") if conversation_context else None

                if conversation_context and (ctx_place or ctx_dom):
                    resolved_domain = ctx_dom or "routes_and_trekking"
                    resolved_entity = ctx_place
                    return ClassificationResult(
                        status="context_dependent",
                        primary_domain=resolved_domain,
                        detected_entities=[resolved_entity] if resolved_entity else [],
                        rationale="Resolved context-dependent follow-up using active conversation state.",
                        requires_context=True,
                        confidence="moderate",
                    )
                else:
                    return ClassificationResult(
                        status="context_dependent",
                        primary_domain="routes_and_trekking",
                        rationale="Context-dependent question without prior entity history; applying default trekking context.",
                        requires_context=True,
                        confidence="low",
                    )

        # 4. Extract Entities
        detected_entities = self._extract_entities(cleaned)

        # 5. Calculate Domain Match Hits
        domain_scores: Dict[str, int] = {d: 0 for d in self.SUPPORTED_DOMAINS}
        for domain, patterns in self.compiled_domain_phrases.items():
            for p in patterns:
                if p.search(cleaned):
                    domain_scores[domain] += 1

        best_domain = max(domain_scores, key=domain_scores.get)
        max_score = domain_scores[best_domain]

        # 6. Check Generic Words Dilemma
        # Filter stopwords, then check if remaining content words are generic
        content_tokens = [t for t in tokens if t not in self.STOPWORDS]
        non_generic_tokens = [t for t in content_tokens if t not in self.GENERIC_WORDS]

        if content_tokens and not non_generic_tokens and not detected_entities:
            return ClassificationResult(
                status="ambiguous",
                rationale="Query contains only generic words (e.g. temple, cave, water) without specific regional entities.",
                confidence="low",
            )

        # 7. Evaluate Classification Outcome
        if detected_entities or max_score >= 1:
            # Map entity to domain if domain score is 0
            if max_score == 0 and detected_entities:
                entity = detected_entities[0]
                if entity in ["Patnitop", "Shiv Khori", "Sanasar", "Amar Mahal Palace", "Bahu Fort & Bagh-e-Bahu", "Raghunath Temple, Jammu"]:
                    best_domain = "jk_regional_tourism"
                elif entity in ["RFID Pilgrim Pass"]:
                    best_domain = "registration_guidance"
                elif entity in ["Bhairon Ropeway", "Battery Operated Vehicle", "Tarakote Marg"]:
                    best_domain = "routes_and_trekking"
                elif "Cuisine" in entity or "Dogra" in entity:
                    best_domain = "cultural_heritage"
                else:
                    best_domain = "vaishno_devi_pilgrimage"

            confidence = "high" if (detected_entities and max_score >= 1) else "moderate"
            return ClassificationResult(
                status="supported",
                primary_domain=best_domain,
                detected_entities=detected_entities,
                rationale=f"Identified domain '{best_domain}' with entities: {detected_entities}",
                requires_context=False,
                confidence=confidence,
            )

        # 8. Check for partially supported queries (e.g. mentions Katra or general yatra)
        if any(term in lower_query for term in ["yatra", "pilgrim", "devotee", "katra", "jammu", "shrine"]):
            return ClassificationResult(
                status="partially_supported",
                primary_domain="vaishno_devi_pilgrimage",
                detected_entities=detected_entities,
                rationale="Query contains general pilgrimage terminology without specific landmark.",
                confidence="low",
            )

        # 9. Default: Unsupported
        return ClassificationResult(
            status="unsupported",
            primary_domain=None,
            detected_entities=[],
            rationale="Query lacks recognized entities, domain indicators, and terminology in Yatra knowledge base.",
            requires_context=False,
            confidence="high",
        )
