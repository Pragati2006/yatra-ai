"""
services/destination_ingestion/deduplicator.py
Deduplication and conflict-resolution engine for J&K destination ingestion.
Ensures manually verified curated records in explore_data.PLACES are never overwritten.
"""

import re
import explore_data
from typing import Optional, Tuple, Dict, Any


def normalize_name(name: str) -> str:
    """Normalizes destination names for robust comparison."""
    if not name:
        return ""
    n = name.lower()
    # Remove common geographic suffixes / prefixes
    n = re.sub(r"\b(district|jammu|kashmir|srinagar|kishtwar|temple|palace|fort|garden|lake)\b", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n.strip()


# Known canonical mapping between official portal slugs and curated catalog names
KNOWN_CURATED_MATCHES = {
    "bagh-e-bahu": "Bahu Fort & Bagh-e-Bahu",
    "bahu fort jammu": "Bahu Fort & Bagh-e-Bahu",
    "amar mahal jammu": "Amar Mahal Palace",
    "raghunath temple jammu": "Raghunath Temple, Jammu",
    "dal lake": "Srinagar (Dal Lake & Gardens)",
}


def find_curated_match(name: str, url: str = "") -> Optional[Dict[str, Any]]:
    """
    Checks if a destination is already present in explore_data.PLACES.
    Returns the curated place dict if found, else None.
    """
    if not name:
        return None

    # Check known direct matches
    raw_lower = name.strip().lower()
    if raw_lower in KNOWN_CURATED_MATCHES:
        match_name = KNOWN_CURATED_MATCHES[raw_lower]
        return explore_data.get_place_by_name(match_name)

    for k, v in KNOWN_CURATED_MATCHES.items():
        if k in url.lower():
            return explore_data.get_place_by_name(v)

    norm = normalize_name(name)
    if not norm:
        return None

    # Check against explore_data.PLACES
    for p in explore_data.PLACES:
        p_name = p.get("name", "")
        # Exact match
        if p_name.lower() == name.strip().lower():
            return p
        # Normalized match
        p_norm = normalize_name(p_name)
        if p_norm and (p_norm == norm or (len(norm) >= 5 and norm in p_norm)):
            return p

    return None


def resolve_deduplication(
    raw_name: str,
    source_url: str = ""
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Evaluates whether a candidate place is a duplicate of a curated record.
    Returns:
        (is_duplicate, duplicate_of_name, curated_record)
    """
    curated = find_curated_match(raw_name, source_url)
    if curated:
        return True, curated.get("name"), curated
    return False, None, None
