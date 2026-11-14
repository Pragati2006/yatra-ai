"""
services/verified_contacts.py
Verified Contact & Emergency Helpline Registry for Yatra AI.

Provides structured, official contact directories across:
- NATIONAL_EMERGENCY (Primary: 112)
- SHRINE_BOARD_ASSISTANCE (SMVDSB 24x7 Call Centre & Protocol)
- TRAFFIC_CONTROL (TCU Ramban, TCU Jammu, TCU Udhampur)
- LOCAL_POLICE (Katra Police Station)
- MEDICAL_ASSISTANCE (National Ambulance Service 108)

Governance & Safety Rules:
- 112 is always maintained as the primary statutory emergency contact.
- Unverified numbers are suppressed from emergency recommendations by default.
- Operating hours and non-emergency administrative distinctions are strictly preserved.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from services.live_data.contracts import (
    ContactCategory,
    VerifiedContact,
)
from utils.provenance import (
    VerificationStatus,
    get_utc_now_iso,
)

logger = logging.getLogger(__name__)

DEFAULT_CONTACTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "verified_contacts.json",
)

DEFAULT_PRIMARY_DIRECTIVE: Dict[str, str] = {
    "number": "112",
    "service": "Emergency Response Support System (ERSS)",
    "advisory": (
        "For immediate life-safety emergencies (Police, Fire, Ambulance, Disaster), "
        "dial the national emergency number 112 directly. 112 is operational 24x7 across India and J&K."
    ),
}


def load_verified_contacts(file_path: Optional[str] = None) -> Tuple[List[VerifiedContact], Dict[str, Any]]:
    """Loads verified contacts from storage.
    Returns (contacts_list, primary_directive_metadata).
    """
    path = file_path or DEFAULT_CONTACTS_PATH
    if not os.path.exists(path):
        logger.warning("Verified contacts catalog not found at '%s'.", path)
        return [], DEFAULT_PRIMARY_DIRECTIVE

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        raw_contacts = payload.get("contacts", [])
        primary_dir = payload.get("primary_emergency_directive", DEFAULT_PRIMARY_DIRECTIVE)

        contacts: List[VerifiedContact] = []
        for c in raw_contacts:
            raw_v_status = c.get("verification_status")
            v_status = raw_v_status if raw_v_status else VerificationStatus.UNVERIFIED.value
            contact = VerifiedContact(
                contact_id=str(c.get("contact_id", "")),
                organization=str(c.get("organization", "")),
                telephone_number=str(c.get("telephone_number", "")),
                service_description=str(c.get("service_description", "")),
                category=c.get("category", ContactCategory.NATIONAL_EMERGENCY.value),
                geographic_jurisdiction=c.get("geographic_jurisdiction", "Pan-India"),
                operating_hours=c.get("operating_hours", "24x7"),
                source_url=c.get("source_url", ""),
                verified_at=c.get("verified_at"),
                verified_by=c.get("verified_by"),
                verification_status=v_status,
                is_primary_emergency=bool(c.get("is_primary_emergency", False)),
                notes=c.get("notes"),
            )
            contacts.append(contact)

        return contacts, primary_dir
    except Exception as exc:
        logger.error("Failed to load verified contacts from '%s': %s", path, exc)
        return [], DEFAULT_PRIMARY_DIRECTIVE


def query_verified_contacts(
    category: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    include_unverified: bool = False,
    file_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Queries verified contacts with jurisdiction matching, category filtering,
    and automatic unverified contact suppression.

    Returns:
        (contacts_list, metadata)
    """
    all_contacts, primary_dir = load_verified_contacts(file_path=file_path)

    filtered: List[VerifiedContact] = []
    for c in all_contacts:
        # Suppress unverified contacts by default
        if not include_unverified and c.verification_status == VerificationStatus.UNVERIFIED.value:
            continue

        # Match category if specified
        if category:
            cat_clean = category.strip().upper()
            if c.category.upper() != cat_clean:
                # Do not drop primary emergency number 112 when general emergency queried
                if not (cat_clean == "EMERGENCY" and c.is_primary_emergency):
                    continue

        # Match jurisdiction if specified
        if jurisdiction:
            jur_clean = jurisdiction.strip().lower()
            c_jur = c.geographic_jurisdiction.strip().lower()
            # If contact is Pan-India or universal emergency, always retain
            is_universal = c.is_primary_emergency or "pan-india" in c_jur
            if not is_universal and jur_clean not in c_jur and c_jur not in jur_clean:
                continue

        filtered.append(c)

    # Sort so primary emergency contact (112) appears first, followed by life-safety category order (F-04 Remediation)
    category_order = {
        ContactCategory.NATIONAL_EMERGENCY.value: 1,
        ContactCategory.MEDICAL_ASSISTANCE.value: 2,
        ContactCategory.LOCAL_POLICE.value: 3,
        ContactCategory.TRAFFIC_CONTROL.value: 4,
        ContactCategory.SHRINE_BOARD_ASSISTANCE.value: 5,
    }
    filtered.sort(key=lambda x: (not x.is_primary_emergency, category_order.get(x.category, 99), x.organization))

    metadata = {
        "total_contacts": len(filtered),
        "primary_emergency_directive": primary_dir,
        "primary_emergency_number": "112",
        "retrieval_timestamp": get_utc_now_iso(),
        "disclaimer": (
            "Contact directory maintained via human-verified official authority sources. "
            "For urgent physical peril or life-safety emergencies, immediately dial 112 directly."
        ),
    }

    return [c.to_dict() for c in filtered], metadata
