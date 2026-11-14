"""
rag/embeddings.py
Deterministic Feature Hashing Representation Engine for Yatra AI.

DomainTermEmbeddingModel is a lightweight, deterministic, domain-adapted feature-hashing
representation that combines character n-grams and curated pilgrimage vocabulary. It provides
lexical and subword similarity, but it is not equivalent to a pretrained dense semantic embedding model.

Key Architectural Characteristics:
- Offline Advantage: Completely offline, zero network egress, zero third-party API dependencies.
- Low Computational Cost: Sub-millisecond hashing vectorization with negligible CPU and memory footprint.
- Spelling and Transliteration Tolerance: Character 3-gram and 4-gram projections provide robust
  matching for Indian proper nouns, phonetic variations, and minor typing mistakes (e.g. Bhaironath -> Bhairavnath).
- Limitations with Conceptual Synonyms: Words with identical concepts but distinct stems (e.g. 'tariff' vs 'fare',
  'nocturnal lodging' vs 'accommodation', 'electronic tracking badge' vs 'RFID card') project to orthogonal
  coordinates unless pre-normalized.
- Sensitivity to Feature Collisions: In 256 non-negative dimensions, long chunks occupy many hashed coordinates,
  yielding a baseline collision dot product of ~0.26. Without domain gating, arbitrary English queries may match.
- Domain Filtering Mandate: A deterministic domain-relevance classifier and synonym normalization layer
  are deployed upstream to prevent collision-induced false positives and ensure accurate retrieval.
"""

from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import List, Optional


class BaseEmbeddingModel(ABC):
    """Abstract base interface for Yatra AI embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embeds a single query or document string into a normalized dense vector."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a collection of document strings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The fixed dimensionality of the embedding vectors."""
        pass


class DomainTermEmbeddingModel(BaseEmbeddingModel):
    """
    DomainTermEmbeddingModel is a lightweight, deterministic, domain-adapted feature-hashing
    representation that combines character n-grams and curated pilgrimage vocabulary. It provides
    lexical and subword similarity, but it is not equivalent to a pretrained dense semantic embedding model.

    Engineering Details:
    1. Offline Advantage: Runs in microseconds on local CPU without model weights or network egress.
    2. Typo Resilience: Subword n-grams capture inflections and Indian transliteration differences.
    3. Conceptual Synonym Limitations: Addressed via QueryTerminologyNormalizer prior to vectorization.
    4. Feature Collision Mitigation: Governed by DomainRelevanceClassifier gate to reject out-of-domain queries.
    """

    # Domain vocabulary clusters for semantic projection
    PILGRIMAGE_VOCAB = {
        # Mata Vaishno Devi Shrine & Bhawan
        "vaishno": 12.0, "devi": 12.0, "mata": 10.0, "shrine": 8.0, "bhawan": 11.0,
        "holy": 6.0, "cave": 9.0, "pindies": 11.0, "pindi": 11.0, "darshan": 10.0,
        "trikuta": 10.0, "parvat": 7.0, "smvdsb": 12.0, "board": 6.0, "devotee": 7.0,
        "pilgrim": 8.0, "pilgrimage": 8.0, "yatra": 10.0, "sanctum": 9.0, "sanctorum": 9.0,

        # Sacred Trek Locations
        "katra": 10.0, "banganga": 11.0, "ban": 5.0, "ganga": 8.0, "charan": 10.0,
        "paduka": 10.0, "ardhkuwari": 12.0, "adhkuwari": 12.0, "garbh": 11.0, "joon": 11.0,
        "sanjichhat": 11.0, "sanji": 6.0, "chhat": 6.0, "bhairon": 11.0, "bhairavnath": 12.0,
        "temple": 7.0, "tarakote": 11.0, "marg": 8.0, "himkoti": 10.0, "track": 6.0,
        "meditate": 11.0, "meditated": 11.0, "meditation": 11.0, "months": 9.0, "nine": 9.0,
        "goddess": 10.0, "mother": 8.0, "divine": 8.0, "legend": 9.0, "story": 8.0,
        "altitude": 9.0, "elevation": 9.0, "height": 8.0, "distance": 8.0, "reach": 8.0,

        # Rituals, Worship & Ceremonies
        "aarti": 11.0, "morning": 6.0, "evening": 6.0, "timings": 8.0, "timing": 8.0,
        "atka": 10.0, "pooja": 8.0, "puja": 8.0, "havan": 8.0, "prasad": 9.0,
        "chuni": 7.0, "bhet": 7.0, "coconut": 6.0, "shringar": 8.0, "prayer": 8.0,

        # Registration & Entry Procedures
        "parchi": 11.0, "slip": 9.0, "registration": 11.0, "register": 10.0,
        "rfid": 12.0, "card": 7.0, "badge": 8.0, "counter": 8.0, "mandatory": 9.0,
        "identity": 8.0, "aadhaar": 10.0, "passport": 9.0, "photo": 7.0, "free": 8.0,
        "chowk": 7.0, "railway": 7.0, "station": 6.0,

        # Trek Assistance & Transport
        "pony": 9.0, "ponies": 9.0, "palki": 10.0, "palkis": 10.0, "palanquin": 10.0, "pithoo": 10.0,
        "pithoos": 10.0, "porter": 8.0, "porters": 8.0, "battery": 10.0, "car": 7.0, "electric": 8.0, "cart": 8.0,
        "vehicle": 7.0, "ropeway": 11.0, "cable": 7.0, "helicopter": 11.0,
        "helipad": 9.0, "flight": 8.0, "walking": 6.0, "stairs": 7.0, "ramp": 7.0,
        "transport": 8.0, "elderly": 10.0, "senior": 10.0, "seniors": 10.0,
        "parents": 8.0, "wheelchair": 12.0, "wheelchairs": 12.0,
        "physically": 10.0, "challenged": 10.0, "disability": 9.0, "disabled": 9.0, "handicapped": 9.0,

        # Facilities, Comfort & Safety
        "langar": 12.0, "langars": 12.0, "food": 8.0, "bhojanalaya": 12.0, "bhojanalayas": 12.0,
        "kitchen": 9.0, "kitchens": 9.0, "meal": 6.0, "water": 6.0,
        "medical": 10.0, "center": 6.0, "dispensary": 9.0, "emergency": 9.0,
        "doctor": 8.0, "oxygen": 10.0, "first": 6.0, "aid": 6.0, "ambulance": 9.0,
        "locker": 11.0, "lockers": 11.0, "cloakroom": 11.0, "cloakrooms": 11.0,
        "blanket": 9.0, "accommodation": 9.0, "dormitory": 9.0, "room": 7.0,
        "rest": 6.0, "helpline": 11.0, "luggage": 10.0, "storage": 9.0,
        "facility": 7.0, "facilities": 7.0, "breathlessness": 9.0,
        "night": 11.0, "illuminated": 10.0, "lighting": 9.0, "light": 8.0, "safety": 8.0, "safe": 8.0,

        # Packing, Climate & Rules
        "packing": 9.0, "shoes": 9.0, "woollen": 9.0, "warm": 7.0, "raincoat": 9.0,
        "umbrella": 7.0, "prohibited": 11.0, "prohibit": 10.0, "banned": 11.0, "forbidden": 10.0,
        "restricted": 9.0, "alcohol": 9.0, "tobacco": 9.0, "drone": 9.0, "leather": 8.0,
        "camera": 7.0, "phone": 6.0, "bypass": 11.0, "hack": 10.0, "script": 8.0,
        "operating": 9.0, "suspended": 11.0, "suspension": 10.0,
        "monsoon": 12.0, "rain": 11.0, "rainfall": 11.0, "raining": 10.0, "heavy": 7.0,
        "heavily": 7.0, "poncho": 8.0, "ponchos": 8.0, "weather": 9.0, "climate": 8.0,
        "seasons": 9.0, "season": 9.0, "summer": 10.0, "winter": 10.0, "autumn": 10.0,
        "spring": 8.0, "march": 9.0, "best": 9.0, "time": 8.0, "visit": 8.0,
        "fee": 11.0, "cost": 10.0, "charge": 9.0,

        # Regional J&K Tourism & Heritage
        "patnitop": 11.0, "sanasar": 10.0, "nathatop": 10.0, "snow": 7.0,
        "shiv": 10.0, "khori": 11.0, "reasi": 9.0, "stalagmite": 9.0, "lingam": 9.0,
        "jammu": 9.0, "bahu": 10.0, "fort": 8.0, "raghunath": 11.0, "amar": 9.0,
        "mahal": 9.0, "dogra": 10.0, "heritage": 8.0, "palace": 8.0,
        "srinagar": 9.0, "dal": 9.0, "lake": 7.0, "gulmarg": 10.0, "pahalgam": 10.0,
        "sonamarg": 10.0, "gondola": 9.0, "meadow": 7.0, "kashmir": 8.0,
        "baba": 7.0, "dhansar": 10.0, "nau": 8.0, "jhajjar": 9.0, "kotli": 9.0,
        "mansar": 9.0, "surinsar": 9.0, "peer": 7.0, "kho": 9.0,
    }

    STOPWORDS = {
        "the", "a", "an", "of", "to", "in", "is", "for", "and", "or", "on", "at",
        "by", "from", "with", "as", "it", "this", "that", "where", "did", "how",
        "what", "can", "are", "do", "does", "be", "tell", "me", "about", "which",
        "when", "who", "why", "we", "i", "you", "our", "my", "your",
    }

    def __init__(self, dim: int = 256):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", (text or "").lower())
        return [w for w in cleaned.split() if len(w) > 1 and w not in self.STOPWORDS]

    def _hash_to_coord(self, token: str, seed: int = 0) -> int:
        h = hashlib.md5(f"{token}_{seed}".encode("utf-8")).hexdigest()
        return int(h, 16) % self._dim

    def embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        # 1. Domain vocabulary projection
        for token in tokens:
            weight = self.PILGRIMAGE_VOCAB.get(token, 2.0)
            coord1 = self._hash_to_coord(token, seed=42)
            coord2 = self._hash_to_coord(token, seed=108)
            vec[coord1] += weight * 3.0
            vec[coord2] += weight * 1.5

        # 2. Subword 3-gram and 4-gram hashing for robust morphology and typo tolerance
        for token in tokens:
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    tri = token[i:i + 3]
                    coord = self._hash_to_coord(tri, seed=7)
                    vec[coord] += 0.5
            if len(token) >= 4:
                for i in range(len(token) - 3):
                    four = token[i:i + 4]
                    coord = self._hash_to_coord(four, seed=13)
                    vec[coord] += 0.6

        # 3. L2 Normalization
        norm_sq = sum(x * x for x in vec)
        if norm_sq > 0:
            norm = math.sqrt(norm_sq)
            vec = [x / norm for x in vec]

        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class MockEmbeddingModel(BaseEmbeddingModel):
    """Predictable mock embedder for lightning-fast testing and boundary conditions."""

    def __init__(self, dim: int = 256, constant_val: Optional[float] = None):
        self._dim = dim
        self._constant_val = constant_val

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        if self._constant_val is not None:
            vec = [self._constant_val] * self._dim
        else:
            # Deterministic hash-based mock
            vec = [0.0] * self._dim
            for i, ch in enumerate(text[:32]):
                coord = (ord(ch) * (i + 1)) % self._dim
                vec[coord] += 1.0

        norm_sq = sum(x * x for x in vec)
        if norm_sq > 0:
            norm = math.sqrt(norm_sq)
            return [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_model(model_type: str = "domain_term", **kwargs) -> BaseEmbeddingModel:
    """Factory creating configured embedding provider."""
    if model_type == "domain_term":
        return DomainTermEmbeddingModel(dim=kwargs.get("dim", 256))
    elif model_type == "mock":
        return MockEmbeddingModel(dim=kwargs.get("dim", 256), constant_val=kwargs.get("constant_val"))
    raise ValueError(f"Unknown embedding model type: {model_type}")
