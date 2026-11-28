"""
agents/itinerary_editor.py

Phase 8.8.58 — Smart Partial Itinerary Editor, Schema Validator, & Privacy Sanitizer.

Core invariants:
1. Partial edits mutate ONLY the targeted day/field(s). Unaffected days, timings,
   preferences, and booking references remain strictly untouched.
2. Any edit preview generates an explicit before/after payload + diff summary without
   persisting changes until approved via apply.
3. Duration reductions that would discard populated days flag `requires_confirmation`
   and require explicit `confirm_impact=True`.
4. AI-assisted single-day regeneration strictly validates output against schema and
   rejects malformed/incomplete payloads without mutating the itinerary.
5. Shared itinerary payloads strip private user PII, booking secrets, payment details,
   OTP/session artifacts, and unmasked member emails.
"""

import copy
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import explore_data
from agents import itinerary_agent
from utils.masking import mask_email

logger = logging.getLogger(__name__)


class ItineraryEditValidationError(ValueError):
    """Raised when an edit request or generated AI day payload fails schema validation."""

    def __init__(self, message: str, status_code: int = 422, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


PRIVATE_FIELD_KEYS = {
    "phone",
    "phone_number",
    "mobile",
    "contact_phone",
    "whatsapp",
    "otp",
    "otp_code",
    "session_token",
    "token_hash",
    "password",
    "secret",
    "booking_secret",
    "credentials",
    "payment_id",
    "payment_status",
    "payment_method",
    "transaction_id",
    "razorpay",
    "stripe",
    "card",
    "card_number",
    "aadhaar",
    "pan",
    "passport",
    "id_number",
    "identity_doc",
    "identity_document",
    "receipt_json",
    "receipt",
    "private_notes",
    "raw_email",
}


def _strip_private_keys_recursive(obj: Any) -> Any:
    """Recursively strips sensitive/private keys from arbitrary JSON-like structures."""
    if isinstance(obj, list):
        return [_strip_private_keys_recursive(item) for item in obj]
    if isinstance(obj, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in obj.items():
            k_lower = str(k).strip().lower()
            if k_lower in PRIVATE_FIELD_KEYS:
                continue
            if any(tok in k_lower for tok in ("phone", "aadhaar", "passport", "password", "secret", "otp", "payment", "receipt", "token")):
                # Allow benign labels like "token_count" only if clearly harmless; safest to omit token/secret keys
                if k_lower not in ("has_token",):
                    continue
            if k_lower == "email" and isinstance(v, str) and "@" in v:
                cleaned[k] = mask_email(v)
                continue
            cleaned[k] = _strip_private_keys_recursive(v)
        return cleaned
    return obj


def _sanitize_booking_refs_for_shared(booking_refs: Any, is_owner: bool) -> List[Dict[str, Any]]:
    """Sanitizes booking references so private booking receipts/secrets are never shared."""
    if not isinstance(booking_refs, list):
        return []
    if is_owner:
        return copy.deepcopy(booking_refs)

    safe_refs: List[Dict[str, Any]] = []
    for ref in booking_refs:
        if isinstance(ref, dict):
            safe_refs.append({
                "type": ref.get("type") or ref.get("category") or "Trip Reservation",
                "label": ref.get("label") or ref.get("hotel_name") or ref.get("transport_mode") or "Reserved Segment",
                "date": ref.get("date") or ref.get("slot_date") or None,
                "slot_time": ref.get("slot_time") or None,
                "redacted": True,
            })
        elif isinstance(ref, str):
            safe_refs.append({"type": "Trip Reservation", "label": "Linked booking (private)", "redacted": True})
    return safe_refs


def sanitize_itinerary_data_for_member(
    data: Any,
    is_owner: bool = False,
) -> Dict[str, Any]:
    """Returns a deep-copied, privacy-safe itinerary payload appropriate for the caller's role."""
    normalized = normalize_itinerary_data(data)
    if is_owner:
        return normalized

    cleaned = _strip_private_keys_recursive(normalized)
    if isinstance(cleaned, dict):
        cleaned["booking_refs"] = _sanitize_booking_refs_for_shared(normalized.get("booking_refs"), is_owner=False)
        # Ensure user/request contact info is scrubbed if present inside request snapshot
        if isinstance(cleaned.get("request"), dict):
            cleaned["request"] = _strip_private_keys_recursive(cleaned["request"])
    return cleaned


def activity_to_text(act: Any) -> str:
    """Extracts human-readable text from a string or structured activity object."""
    if isinstance(act, dict):
        place = act.get("place") or ""
        text = act.get("activity") or act.get("description") or act.get("title") or place
        return str(text or "").strip()
    return str(act or "").strip()


def normalize_activity(act: Any) -> Dict[str, Any]:
    """Converts string or dict activity to structured dictionary while preserving fields."""
    if isinstance(act, dict):
        out = copy.deepcopy(act)
        text = str(out.get("activity") or out.get("description") or out.get("title") or "").strip()
        place = out.get("place") or itinerary_agent.match_place_name(text) or None
        out["activity"] = text or (f"Visit {place}" if place else "Pilgrimage Activity")
        out["time"] = str(out.get("time") or out.get("slot") or "").strip()
        out["duration"] = str(out.get("duration") or "").strip()
        if place:
            out["place"] = place
        out.setdefault("notes", "")
        return out

    raw = str(act or "").strip()
    time_str = ""
    body = raw
    m = re.match(r"^(Morning|Afternoon|Evening|Night|\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*:\s*(.+)$", raw, flags=re.IGNORECASE)
    if m:
        time_str = m.group(1).strip()
        body = m.group(2).strip()
    place = itinerary_agent.match_place_name(body)
    duration = ""
    if place:
        logi = itinerary_agent.get_destination_logistics(place)
        if logi and logi.get("duration_hours"):
            hrs = logi["duration_hours"]
            duration = f"{hrs:g} hr{'s' if hrs != 1 else ''}"
    out: Dict[str, Any] = {
        "time": time_str,
        "duration": duration,
        "activity": body or "Pilgrimage Activity",
        "notes": "",
    }
    if place:
        out["place"] = place
    return out


def _extract_destinations_from_days(days: List[Dict[str, Any]], fallback_dest: str = "Shri Mata Vaishno Devi Shrine") -> List[str]:
    """Extracts unique ordered destination names mentioned across days."""
    found: List[str] = []
    for d in days or []:
        if not isinstance(d, dict):
            continue
        for act in d.get("activities") or []:
            place = act.get("place") if isinstance(act, dict) else itinerary_agent.match_place_name(str(act))
            if not place:
                place = itinerary_agent.match_place_name(activity_to_text(act))
            if place and place not in found:
                found.append(place)
    if not found and fallback_dest:
        found.append(fallback_dest)
    return found


def normalize_itinerary_data(raw_data: Any, title_fallback: str = "Vaishno Devi Yatra Itinerary") -> Dict[str, Any]:
    """
    Normalizes any legacy or rich itinerary structure into a uniform schema
    while preserving existing extra fields (`request`, `hotel`, `budget_evaluation`,
    `feasible_places`, `infeasible_places`, `booking_refs`, etc.) and existing
    day/activity shapes.
    """
    if isinstance(raw_data, list):
        days = copy.deepcopy(raw_data)
        base: Dict[str, Any] = {"days": days}
    elif isinstance(raw_data, dict):
        base = copy.deepcopy(raw_data)
        if "days" not in base or not isinstance(base.get("days"), list):
            if isinstance(base.get("itinerary"), list):
                base["days"] = copy.deepcopy(base["itinerary"])
            else:
                base["days"] = []
    else:
        base = {"days": []}

    req = base.get("request") if isinstance(base.get("request"), dict) else {}
    days = base["days"]

    # Ensure each day has day_number and activities list
    for idx, d in enumerate(days):
        if not isinstance(d, dict):
            days[idx] = {"day_number": idx + 1, "title": f"Day {idx + 1}", "activities": []}
            d = days[idx]
        if not d.get("day_number"):
            d["day_number"] = d.get("day") or (idx + 1)
        if not isinstance(d.get("activities"), list):
            if isinstance(d.get("schedule"), list):
                d["activities"] = d["schedule"]
            else:
                d["activities"] = []
        if not d.get("title"):
            d["title"] = d.get("theme") or f"Day {d['day_number']} Program"

    start_date = base.get("start_date") or req.get("start_date") or (days[0].get("date") if days and isinstance(days[0], dict) else None)
    duration_days = base.get("duration_days") or req.get("duration_days") or len(days) or 1
    end_date = base.get("end_date") or req.get("end_date")
    if not end_date and start_date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(start_date)):
        try:
            dt = datetime.strptime(str(start_date), "%Y-%m-%d")
            end_date = (dt + timedelta(days=max(0, int(duration_days) - 1))).strftime("%Y-%m-%d")
        except Exception:
            end_date = None

    travellers = base.get("travellers_count") or base.get("pax") or req.get("pax") or 2
    try:
        travellers = max(1, int(travellers))
    except Exception:
        travellers = 2

    title = (base.get("title") or title_fallback or "Vaishno Devi Yatra Itinerary").strip()
    destination = base.get("destination") or req.get("destination") or "Shri Mata Vaishno Devi Shrine"
    destinations = base.get("destinations")
    if not isinstance(destinations, list) or not destinations:
        destinations = _extract_destinations_from_days(days, fallback_dest=destination)

    base["title"] = title
    base["destination"] = destination
    base["destinations"] = destinations
    if start_date:
        base["start_date"] = str(start_date)
    if end_date:
        base["end_date"] = str(end_date)
    base["duration_days"] = int(len(days) or duration_days)
    base["travellers_count"] = travellers
    base.setdefault("notes", "")
    if not isinstance(base.get("preferences"), dict):
        base["preferences"] = {
            "pace": req.get("pace") or "moderate",
            "mobility": req.get("mobility") or "standard",
            "category": req.get("category") or "Normal Darshan",
        }
    if not isinstance(base.get("booking_refs"), list):
        base["booking_refs"] = []

    return base


def extract_itinerary_summary_fields(data: Any, title: str = "Vaishno Devi Yatra Itinerary") -> Dict[str, Any]:
    """Extracts summary metadata columns for fast list card rendering."""
    norm = normalize_itinerary_data(data, title_fallback=title)
    return {
        "title": norm.get("title") or title,
        "destination": norm.get("destination") or "Shri Mata Vaishno Devi Shrine",
        "destinations": norm.get("destinations") or [],
        "start_date": norm.get("start_date"),
        "end_date": norm.get("end_date"),
        "duration_days": norm.get("duration_days") or len(norm.get("days") or []),
        "travellers_count": norm.get("travellers_count") or 2,
    }


def _find_day_index(days: List[Dict[str, Any]], day_number: int) -> int:
    """Finds day index matching `day_number`, raising ItineraryEditValidationError if missing."""
    for idx, d in enumerate(days):
        if int(d.get("day_number") or (idx + 1)) == int(day_number):
            return idx
    raise ItineraryEditValidationError(
        f"Day {day_number} does not exist in this {len(days)}-day itinerary.",
        status_code=400,
    )


def _format_day_date(start_date: Optional[str], day_number: int) -> str:
    if start_date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(start_date)):
        try:
            dt = datetime.strptime(str(start_date), "%Y-%m-%d") + timedelta(days=day_number - 1)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return f"Day {day_number}"


def _resolve_place_info(place_name: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    canonical = itinerary_agent.match_place_name(place_name) or place_name.strip()
    logi = itinerary_agent.get_destination_logistics(canonical)
    return canonical, logi


DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_GROQ_MAX_TOKENS = 2048


def get_selected_groq_model() -> str:
    """Returns configured GROQ_MODEL or the verified active default model."""
    configured = os.environ.get("GROQ_MODEL", "").strip()
    return configured or DEFAULT_GROQ_MODEL


def build_day_regeneration_response_format() -> Dict[str, Any]:
    """Strict JSON Schema response_format matching _validate_regenerated_day_payload."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "yatra_day_regeneration",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "day_number": {"type": "integer"},
                    "title": {"type": "string"},
                    "activities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "string"},
                                "duration": {"type": "string"},
                                "activity": {"type": "string"},
                                "place": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                            "required": ["time", "duration", "activity", "place", "notes"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["day_number", "title", "activities"],
                "additionalProperties": False,
            },
        },
    }


def _extract_llm_content(res: Any) -> str:
    """Extracts strictly final message content, never reading reasoning fields or reprs."""
    content = getattr(res, "content", None)
    if isinstance(content, str):
        return content.strip()
    return ""


def _call_groq_day_regeneration(
    day_obj: Dict[str, Any],
    context_meta: Dict[str, Any],
    instruction: str,
) -> Optional[str]:
    """
    Calls the configured ChatGroq model (if GROQ_API_KEY is present) to regenerate ONLY the
    selected day as strict JSON. Returns None if Groq is unconfigured or errors out.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        return None

    day_num = int(day_obj.get("day_number") or 1)
    model_name = get_selected_groq_model()

    known_places = [p["name"] for p in explore_data.PLACES[:20]]
    prompt = (
        f"You are regenerating ONLY Day {day_num} of a pilgrimage itinerary to {context_meta.get('destination', 'Vaishno Devi / Katra')}.\n"
        f"Preferences: {json.dumps(context_meta.get('preferences', {}))}\n"
        f"Current Day {day_num}: {json.dumps(day_obj)}\n"
        f"User instruction: {instruction or 'Refresh activities with balanced devotional pace'}\n"
        f"Valid local destinations you may include: {', '.join(known_places)}.\n"
        "Respond with ONLY valid JSON matching the schema: "
        f"day_number={day_num}, non-empty title, and non-empty activities list where each activity has time, duration, activity, place, notes."
    )

    try:
        llm = ChatGroq(
            model=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=DEFAULT_GROQ_MAX_TOKENS,
            model_kwargs={"response_format": build_day_regeneration_response_format()},
        )
        res = llm.invoke(prompt)
        return _extract_llm_content(res)
    except Exception as exc:
        err_msg = str(exc).lower()
        # Fallback to JSON Object Mode only if the active model rejects strict json_schema syntax
        if "json_schema" in err_msg or "response_format" in err_msg:
            try:
                llm_obj = ChatGroq(
                    model=model_name,
                    api_key=api_key,
                    temperature=0.3,
                    max_tokens=DEFAULT_GROQ_MAX_TOKENS,
                    model_kwargs={"response_format": {"type": "json_object"}},
                )
                res_obj = llm_obj.invoke(prompt)
                return _extract_llm_content(res_obj)
            except Exception as exc2:
                logger.warning("Groq single-day JSON object fallback failed (%s): %s", model_name, type(exc2).__name__)
                return None
        logger.warning("Groq single-day regeneration fallback triggered (%s): %s", model_name, type(exc).__name__)
        return None


def _validate_regenerated_day_payload(raw_output: Any, expected_day_number: int) -> Dict[str, Any]:
    """
    Strictly validates AI-generated single-day payload against the itinerary day schema.
    Raises ItineraryEditValidationError if malformed, incomplete, or mismatched.
    """
    parsed = raw_output
    if isinstance(raw_output, str):
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            parsed = json.loads(cleaned)
        except Exception as exc:
            raise ItineraryEditValidationError(
                f"Malformed AI response for Day {expected_day_number}: invalid JSON.",
                details={"reason": str(exc)},
            ) from exc

    if not isinstance(parsed, dict):
        raise ItineraryEditValidationError(
            f"Malformed AI response for Day {expected_day_number}: expected a JSON object."
        )

    # Reject multi-day structure when only regenerating one day
    if "days" in parsed and isinstance(parsed["days"], list):
        raise ItineraryEditValidationError(
            "AI output attempted to replace the full itinerary instead of a single day."
        )

    returned_day = parsed.get("day_number")
    if returned_day is not None:
        try:
            if int(returned_day) != int(expected_day_number):
                raise ItineraryEditValidationError(
                    f"AI returned Day {returned_day} instead of requested Day {expected_day_number}."
                )
        except (TypeError, ValueError):
            raise ItineraryEditValidationError("AI returned invalid day_number.")

    title = parsed.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ItineraryEditValidationError(
            f"Incomplete AI response for Day {expected_day_number}: missing day title."
        )

    acts = parsed.get("activities")
    if not isinstance(acts, list) or len(acts) == 0:
        raise ItineraryEditValidationError(
            f"Incomplete AI response for Day {expected_day_number}: activities list cannot be empty."
        )

    validated_acts: List[Dict[str, Any]] = []
    for item in acts:
        if isinstance(item, str):
            if not item.strip():
                raise ItineraryEditValidationError("AI returned empty activity string.")
            validated_acts.append(normalize_activity(item))
        elif isinstance(item, dict):
            act_text = str(item.get("activity") or item.get("description") or "").strip()
            if not act_text:
                raise ItineraryEditValidationError(
                    f"Incomplete activity in AI response for Day {expected_day_number}: missing activity description."
                )
            validated_acts.append(normalize_activity(item))
        else:
            raise ItineraryEditValidationError("AI returned unsupported activity item type.")

    return {
        "title": title.strip(),
        "activities": validated_acts,
    }


def _build_deterministic_day_refresh(
    day_obj: Dict[str, Any],
    context_meta: Dict[str, Any],
    instruction: str,
) -> Dict[str, Any]:
    """Deterministic local fallback for regenerating ONLY the selected day cleanly."""
    instr_lower = (instruction or "").lower()
    day_num = int(day_obj.get("day_number") or 1)
    prefs = day_obj.get("preferences") or context_meta.get("preferences") or {}
    pace = str(prefs.get("pace") or ("relaxed" if "relax" in instr_lower or "rest" in instr_lower else "moderate")).lower()

    # Check if user instruction specifically mentions a canonical destination
    matched_place = itinerary_agent.match_place_name(instruction)
    if "rest" in instr_lower or "relax" in instr_lower or "light" in instr_lower:
        return {
            "title": "Restorative Recovery & Gentle Local Stroll",
            "activities": [
                {"time": "09:00 AM", "duration": "2 hrs", "activity": "Unhurried morning breakfast and foot/muscle rest at Katra hotel", "notes": "Gentle pace"},
                {"time": "12:00 PM", "duration": "1.5 hrs", "activity": "Visit Ban Ganga Courtyard & light prasad shopping", "place": "Banganga Temple", "notes": ""},
                {"time": "05:00 PM", "duration": "1.5 hrs", "activity": "Calm evening Darshani Deodi viewpoint walk and early dinner", "place": "Darshani Deodi", "notes": ""},
            ],
        }

    if matched_place:
        logi = itinerary_agent.get_destination_logistics(matched_place) or {}
        hrs = logi.get("duration_hours") or 2
        return {
            "title": f"{matched_place} Devotional Excursion",
            "activities": [
                {"time": "08:30 AM", "duration": f"{hrs:g} hrs", "activity": f"Morning visit to {matched_place}", "place": matched_place, "notes": ""},
                {"time": "02:30 PM", "duration": "2 hrs", "activity": "Return to Katra base for lunch and afternoon relaxation", "notes": f"{pace.title()} pace"},
                {"time": "06:30 PM", "duration": "1.5 hrs", "activity": "Evening Aarti contemplation & local market stroll in Katra", "notes": ""},
            ],
        }

    # Rotate curated Katra/nearby devotional & heritage spots not heavily used on this day
    existing_text = " ".join(activity_to_text(a).lower() for a in day_obj.get("activities") or [])
    candidate_places = [
        p["name"] for p in explore_data.PLACES
        if p.get("name") and p["name"].lower() not in existing_text
        and (itinerary_agent.get_destination_logistics(p["name"]) or {}).get("region") in ("local_katra", "nearby_excursion")
    ]
    pick1 = candidate_places[0] if len(candidate_places) > 0 else "Nau Devi Cave Temple"
    pick2 = candidate_places[1] if len(candidate_places) > 1 else "Baba Dhansar"

    if pace == "relaxed":
        acts = [
            {"time": "09:30 AM", "duration": "2 hrs", "activity": f"Calm morning darshan at {pick1}", "place": pick1, "notes": "Relaxed pace"},
            {"time": "04:00 PM", "duration": "2 hrs", "activity": "Leisurely Katra Main Bazaar & Shrine Museum stroll", "notes": ""},
        ]
    else:
        acts = [
            {"time": "08:30 AM", "duration": "2 hrs", "activity": f"Morning visit to {pick1}", "place": pick1, "notes": ""},
            {"time": "01:30 PM", "duration": "2.5 hrs", "activity": f"Afternoon scenic darshan at {pick2}", "place": pick2, "notes": ""},
            {"time": "06:30 PM", "duration": "1.5 hrs", "activity": "Evening Bhajan Sandhya & Katra bazaar", "notes": ""},
        ]

    return {
        "title": f"Day {day_num} Curated Local Shrine & Cultural Circuit",
        "activities": acts,
    }


def preview_itinerary_edit(
    raw_data: Any,
    edit_payload: Dict[str, Any],
    llm_caller: Optional[Callable[[Dict[str, Any], Dict[str, Any], str], Any]] = None,
) -> Dict[str, Any]:
    """
    Computes a non-mutating Before/After preview for a targeted itinerary edit.
    Strictly leaves unaffected days, timings, preferences, and booking_refs intact.
    """
    if not isinstance(edit_payload, dict):
        raise ItineraryEditValidationError("Edit payload must be a JSON object.", status_code=400)

    op = str(edit_payload.get("operation") or "").strip().lower()
    if not op:
        raise ItineraryEditValidationError("Missing required 'operation' field.", status_code=400)

    before = normalize_itinerary_data(raw_data)
    after = copy.deepcopy(before)
    days: List[Dict[str, Any]] = after["days"]
    diff_summary: List[str] = []
    affected_days: List[int] = []
    impact_warning: Optional[str] = None
    requires_confirmation = False
    validation_source = "deterministic"

    # 1. Regenerate a SINGLE selected day
    if op == "regenerate_day":
        day_num = int(edit_payload.get("day_number") or 0)
        if day_num < 1:
            raise ItineraryEditValidationError("day_number >= 1 is required for regenerate_day.", status_code=400)
        idx = _find_day_index(days, day_num)
        target_day = days[idx]
        instruction = str(edit_payload.get("instruction") or "").strip()

        ai_raw = None
        if llm_caller is not None:
            ai_raw = llm_caller(target_day, {"destination": after.get("destination"), "preferences": after.get("preferences")}, instruction)
            validation_source = "ai_validated"
        elif edit_payload.get("ai_response") is not None:
            # Explicit AI output payload for validation testing
            ai_raw = edit_payload.get("ai_response")
            validation_source = "ai_validated"
        elif edit_payload.get("use_ai", True):
            ai_raw = _call_groq_day_regeneration(
                target_day,
                {"destination": after.get("destination"), "preferences": after.get("preferences")},
                instruction,
            )
            if ai_raw is not None:
                validation_source = "groq_validated"

        if ai_raw is not None:
            validated_day = _validate_regenerated_day_payload(ai_raw, day_num)
        else:
            if edit_payload.get("require_ai"):
                raise ItineraryEditValidationError("AI service unavailable to regenerate day.", status_code=503)
            validated_day = _build_deterministic_day_refresh(
                target_day,
                {"destination": after.get("destination"), "preferences": after.get("preferences")},
                instruction,
            )
            validation_source = "deterministic_grounded"

        old_title = target_day.get("title")
        target_day["title"] = validated_day["title"]
        target_day["activities"] = validated_day["activities"]
        affected_days.append(day_num)
        diff_summary.append(
            f"Day {day_num}: Regenerated schedule ('{old_title}' -> '{target_day['title']}'), preserving all other days and bookings."
        )

    # 2. Add destination / activity to selected day
    elif op == "add_destination":
        day_num = int(edit_payload.get("day_number") or 0)
        place_raw = str(edit_payload.get("place") or edit_payload.get("activity") or "").strip()
        if day_num < 1 or not place_raw:
            raise ItineraryEditValidationError("day_number and place are required for add_destination.", status_code=400)
        idx = _find_day_index(days, day_num)
        target_day = days[idx]
        place_name, logi = _resolve_place_info(place_raw)
        time_str = str(edit_payload.get("time") or "02:30 PM").strip()
        dur_str = str(edit_payload.get("duration") or (f"{logi['duration_hours']:g} hrs" if logi and logi.get("duration_hours") else "1.5 hrs")).strip()
        notes_str = str(edit_payload.get("notes") or "").strip()

        existing_texts = [activity_to_text(a).lower() for a in target_day["activities"]]
        if any(place_name.lower() in t for t in existing_texts):
            raise ItineraryEditValidationError(
                f"'{place_name}' is already scheduled on Day {day_num}.",
                status_code=400,
            )

        new_act = {
            "time": time_str,
            "duration": dur_str,
            "activity": str(edit_payload.get("activity") or f"Visit {place_name}").strip(),
            "place": place_name,
            "notes": notes_str,
        }
        target_day["activities"].append(new_act)
        affected_days.append(day_num)
        diff_summary.append(f"Day {day_num}: Added destination '{place_name}' at {time_str} ({dur_str}).")

    # 3. Remove destination / activity from selected day
    elif op == "remove_destination":
        day_num = int(edit_payload.get("day_number") or 0)
        if day_num < 1:
            raise ItineraryEditValidationError("day_number >= 1 is required for remove_destination.", status_code=400)
        idx = _find_day_index(days, day_num)
        target_day = days[idx]
        acts = target_day["activities"]
        if not acts:
            raise ItineraryEditValidationError(f"Day {day_num} has no activities to remove.", status_code=400)

        act_idx = edit_payload.get("activity_index")
        place_raw = str(edit_payload.get("place") or "").strip()
        removed_label = None

        if act_idx is not None:
            act_idx = int(act_idx)
            if act_idx < 0 or act_idx >= len(acts):
                raise ItineraryEditValidationError("activity_index out of range.", status_code=400)
            removed = acts.pop(act_idx)
            removed_label = activity_to_text(removed)
        elif place_raw:
            match_i = next((i for i, a in enumerate(acts) if place_raw.lower() in activity_to_text(a).lower()), None)
            if match_i is None:
                raise ItineraryEditValidationError(f"'{place_raw}' not found on Day {day_num}.", status_code=404)
            removed = acts.pop(match_i)
            removed_label = activity_to_text(removed)
        else:
            raise ItineraryEditValidationError("Provide activity_index or place to remove.", status_code=400)

        affected_days.append(day_num)
        diff_summary.append(f"Day {day_num}: Removed '{removed_label}'.")

    # 4. Replace destination on selected day
    elif op == "replace_destination":
        day_num = int(edit_payload.get("day_number") or 0)
        new_place_raw = str(edit_payload.get("new_place") or "").strip()
        if day_num < 1 or not new_place_raw:
            raise ItineraryEditValidationError("day_number and new_place are required for replace_destination.", status_code=400)
        idx = _find_day_index(days, day_num)
        target_day = days[idx]
        acts = target_day["activities"]

        act_idx = edit_payload.get("activity_index")
        old_place_raw = str(edit_payload.get("old_place") or "").strip()
        match_i = None
        if act_idx is not None:
            act_idx = int(act_idx)
            if act_idx < 0 or act_idx >= len(acts):
                raise ItineraryEditValidationError("activity_index out of range.", status_code=400)
            match_i = act_idx
        elif old_place_raw:
            match_i = next((i for i, a in enumerate(acts) if old_place_raw.lower() in activity_to_text(a).lower()), None)

        if match_i is None:
            raise ItineraryEditValidationError(f"Target activity to replace not found on Day {day_num}.", status_code=404)

        old_norm = normalize_activity(acts[match_i])
        new_place, logi = _resolve_place_info(new_place_raw)
        new_dur = str(edit_payload.get("duration") or (f"{logi['duration_hours']:g} hrs" if logi and logi.get("duration_hours") else old_norm.get("duration") or "2 hrs"))
        acts[match_i] = {
            "time": str(edit_payload.get("time") or old_norm.get("time") or "10:00 AM"),
            "duration": new_dur,
            "activity": f"Visit {new_place}",
            "place": new_place,
            "notes": old_norm.get("notes") or "",
        }
        affected_days.append(day_num)
        diff_summary.append(f"Day {day_num}: Replaced '{old_norm['activity']}' with 'Visit {new_place}'.")

    # 5. Change timings & visit durations
    elif op == "update_timing":
        day_num = int(edit_payload.get("day_number") or 0)
        if day_num < 1:
            raise ItineraryEditValidationError("day_number >= 1 is required for update_timing.", status_code=400)
        idx = _find_day_index(days, day_num)
        target_day = days[idx]
        acts = target_day["activities"]

        act_idx = edit_payload.get("activity_index")
        if act_idx is not None:
            act_idx = int(act_idx)
            if act_idx < 0 or act_idx >= len(acts):
                raise ItineraryEditValidationError("activity_index out of range.", status_code=400)
            norm_act = normalize_activity(acts[act_idx])
            if edit_payload.get("time") is not None:
                norm_act["time"] = str(edit_payload["time"]).strip()
            if edit_payload.get("duration") is not None:
                norm_act["duration"] = str(edit_payload["duration"]).strip()
            acts[act_idx] = norm_act
            diff_summary.append(
                f"Day {day_num}: Updated timing for '{norm_act['activity']}' -> {norm_act['time'] or 'Flexible'} ({norm_act['duration'] or 'Flexible duration'})."
            )
        else:
            timings = copy.deepcopy(target_day.get("timings") or {})
            if edit_payload.get("start_time") is not None:
                timings["start_time"] = str(edit_payload["start_time"]).strip()
            if edit_payload.get("end_time") is not None:
                timings["end_time"] = str(edit_payload["end_time"]).strip()
            target_day["timings"] = timings
            diff_summary.append(f"Day {day_num}: Updated day schedule window ({timings.get('start_time', '')} - {timings.get('end_time', '')}).")

        affected_days.append(day_num)

    # 6. Modify day-specific (or itinerary) preferences
    elif op == "update_preferences":
        day_num = edit_payload.get("day_number")
        prefs_patch = edit_payload.get("preferences")
        if not isinstance(prefs_patch, dict) or not prefs_patch:
            raise ItineraryEditValidationError("preferences dictionary is required.", status_code=400)

        if day_num is not None:
            day_num = int(day_num)
            idx = _find_day_index(days, day_num)
            target_day = days[idx]
            cur_prefs = copy.deepcopy(target_day.get("preferences") or {})
            for k, v in prefs_patch.items():
                cur_prefs[str(k)] = v
            target_day["preferences"] = cur_prefs
            affected_days.append(day_num)
            diff_summary.append(f"Day {day_num}: Updated day preferences ({', '.join(f'{k}={v}' for k, v in prefs_patch.items())}).")
        else:
            cur_prefs = copy.deepcopy(after.get("preferences") or {})
            for k, v in prefs_patch.items():
                cur_prefs[str(k)] = v
            after["preferences"] = cur_prefs
            diff_summary.append(f"Trip Preferences: Updated ({', '.join(f'{k}={v}' for k, v in prefs_patch.items())}).")

    # 7. Add or edit notes (day, activity, or itinerary)
    elif op == "update_notes":
        notes_val = str(edit_payload.get("notes") if edit_payload.get("notes") is not None else "").strip()
        day_num = edit_payload.get("day_number")
        act_idx = edit_payload.get("activity_index")

        if day_num is not None:
            day_num = int(day_num)
            idx = _find_day_index(days, day_num)
            target_day = days[idx]
            if act_idx is not None:
                act_idx = int(act_idx)
                if act_idx < 0 or act_idx >= len(target_day["activities"]):
                    raise ItineraryEditValidationError("activity_index out of range.", status_code=400)
                norm_act = normalize_activity(target_day["activities"][act_idx])
                norm_act["notes"] = notes_val
                target_day["activities"][act_idx] = norm_act
                diff_summary.append(f"Day {day_num}: Updated note on '{norm_act['activity']}'.")
            else:
                target_day["notes"] = notes_val
                diff_summary.append(f"Day {day_num}: Updated day notes.")
            affected_days.append(day_num)
        else:
            after["notes"] = notes_val
            diff_summary.append("Trip Notes: Updated itinerary notes.")

    # 8. Adjust number of days without silently deleting existing content
    elif op == "adjust_duration":
        try:
            new_duration = itinerary_agent.validate_duration(edit_payload.get("duration_days"), allow_none=False)
        except ValueError as exc:
            raise ItineraryEditValidationError(str(exc), status_code=400) from exc

        cur_len = len(days)
        start_date = after.get("start_date")

        if new_duration == cur_len:
            diff_summary.append(f"Trip duration remains {cur_len} days.")
        elif new_duration > cur_len:
            for d_num in range(cur_len + 1, new_duration + 1):
                days.append({
                    "day_number": d_num,
                    "date": _format_day_date(start_date, d_num),
                    "title": f"Extended Sacred Pilgrimage & Leisure (Day {d_num})",
                    "activities": [
                        {"time": "09:30 AM", "duration": "2 hrs", "activity": "Flexible local shrine visit & Katra relaxation", "notes": ""},
                    ],
                })
                affected_days.append(d_num)
            after["duration_days"] = new_duration
            if start_date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(start_date)):
                dt = datetime.strptime(str(start_date), "%Y-%m-%d")
                after["end_date"] = (dt + timedelta(days=new_duration - 1)).strftime("%Y-%m-%d")
            diff_summary.append(f"Extended trip duration from {cur_len} to {new_duration} days (existing Days 1-{cur_len} preserved).")
        else:
            removed_days = days[new_duration:]
            populated_removed = [
                int(d.get("day_number") or (new_duration + i + 1))
                for i, d in enumerate(removed_days)
                if (d.get("activities") or d.get("notes"))
            ]
            affected_days.extend(int(d.get("day_number") or (new_duration + i + 1)) for i, d in enumerate(removed_days))
            if populated_removed:
                requires_confirmation = True
                impact_warning = (
                    f"Reducing trip duration from {cur_len} to {new_duration} days will remove "
                    f"Day(s) {', '.join(str(x) for x in populated_removed)} which contain existing activities or notes."
                )
            days[:] = days[:new_duration]
            after["duration_days"] = new_duration
            if start_date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(start_date)):
                dt = datetime.strptime(str(start_date), "%Y-%m-%d")
                after["end_date"] = (dt + timedelta(days=new_duration - 1)).strftime("%Y-%m-%d")
            diff_summary.append(f"Adjusted trip duration from {cur_len} to {new_duration} days.")

    # 9. Update itinerary-level metadata (title, dates, travellers)
    elif op == "update_metadata":
        if edit_payload.get("title") is not None:
            new_title = str(edit_payload["title"]).strip()
            if not new_title:
                raise ItineraryEditValidationError("Title cannot be empty.", status_code=400)
            after["title"] = new_title
            diff_summary.append(f"Title updated to '{new_title}'.")
        if edit_payload.get("start_date") is not None:
            sd = str(edit_payload["start_date"]).strip()
            after["start_date"] = sd
            if re.match(r"^\d{4}-\d{2}-\d{2}$", sd):
                dt = datetime.strptime(sd, "%Y-%m-%d")
                dur = len(days) or int(after.get("duration_days") or 1)
                after["end_date"] = (dt + timedelta(days=dur - 1)).strftime("%Y-%m-%d")
            diff_summary.append(f"Start date updated to {sd}.")
        if edit_payload.get("end_date") is not None:
            after["end_date"] = str(edit_payload["end_date"]).strip()
            diff_summary.append(f"End date updated to {after['end_date']}.")
        if edit_payload.get("travellers_count") is not None:
            try:
                pax = max(1, int(edit_payload["travellers_count"]))
            except Exception as exc:
                raise ItineraryEditValidationError("travellers_count must be a positive integer.", status_code=400) from exc
            after["travellers_count"] = pax
            diff_summary.append(f"Travellers count updated to {pax}.")
    else:
        raise ItineraryEditValidationError(f"Unsupported edit operation: '{op}'.", status_code=400)

    # Refresh top-level derived destinations list accurately from final days
    after["destinations"] = _extract_destinations_from_days(days, fallback_dest=after.get("destination") or "Shri Mata Vaishno Devi Shrine")
    after["duration_days"] = len(days)

    return {
        "operation": op,
        "before": before,
        "after": after,
        "diff_summary": diff_summary,
        "affected_days": sorted(set(affected_days)),
        "impact_warning": impact_warning,
        "requires_confirmation": requires_confirmation,
        "validation_source": validation_source,
    }

