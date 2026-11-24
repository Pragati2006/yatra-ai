"""
agents/orchestrator.py
Central Conversational Trip Orchestrator for Vaishno Devi Yatra.

Coordinates:
- Requirement extraction and state accumulation
- Missing-field identification (origin, pax, travel dates/duration)
- Selective follow-up prompts without repetitive questioning
- Multi-tool coordination (transport, darshan slots, accommodation, sightseeing, itinerary)
- Deterministic budget and feasibility evaluation via agents.budget_engine
- Persistent session state via agents.session_store
- Conversational replanning (budget changes, mode switches, hotel updates, pax edits)
- Human authorization gate and sandboxed Playwright mock RPA execution
"""

import json
import logging
import math
import os
import re
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

import agent as legacy_agent
import agents.coordinator as coordinator
import db
import explore_data
from agents import budget_engine, content_agent, conversation_agent, itinerary_agent, recommendation_agent, rpa_agent, session_store


# -----------------------------------------------------------------------------
# 1. Requirement & Preference Extraction Helpers
# -----------------------------------------------------------------------------

def extract_budget_preference(text: str) -> Optional[float]:
    """Extracts explicit numeric budget amount (e.g. ₹20,000, 15000, 25k) from text."""
    if not text:
        return None
    t = text.strip()

    # Pattern 1: 'budget of 20,000', 'budget is ₹15000', 'budget: 25k', 'under 20000'
    m = re.search(
        r"(?:budget(?:\s*of|\s*is|\s*around|\s*under|\s*:)?\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand|lakh|lac)?\b)",
        t,
        re.IGNORECASE,
    )
    if m:
        num_str = m.group(1).replace(",", "")
        multiplier = m.group(2)
        try:
            val = float(num_str)
            if multiplier:
                mult_lower = multiplier.lower()
                if mult_lower in ("k", "thousand"):
                    val *= 1000
                elif mult_lower in ("lakh", "lac"):
                    val *= 100000
            return val
        except Exception:
            pass

    # Pattern 2: '₹20,000 budget' or 'Rs 20000 total budget'
    m2 = re.search(
        r"(?:₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand|lakh|lac)?\s*(?:total\s*)?(?:budget)?\b",
        t,
        re.IGNORECASE,
    )
    if m2:
        num_str = m2.group(1).replace(",", "")
        multiplier = m2.group(2)
        try:
            val = float(num_str)
            if multiplier:
                mult_lower = multiplier.lower()
                if mult_lower in ("k", "thousand"):
                    val *= 1000
                elif mult_lower in ("lakh", "lac"):
                    val *= 100000
            return val
        except Exception:
            pass

    return None


def extract_budget_details(text: str, pax: int = 1) -> Tuple[Optional[float], Optional[str], Optional[float]]:
    """
    Extracts budget amount, budget_type ('total' or 'per_person'), and per_person amount.
    Returns: (total_budget, budget_type, budget_per_person)
    """
    if not text:
        return None, None, None
    t = text.lower()
    pax_val = max(1, pax or 1)

    # Check for per-person / per-head phrasing
    is_per_person = bool(re.search(r"\b(?:per\s*(?:person|head|pilgrim|pax|traveller|traveler)|each)\b", t))

    # Pattern for per-person budget: '5000 per person', '₹4000 per head', 'per person budget 6000'
    m_per = re.search(
        r"(?:(?:budget\s*(?:of|is|:)?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand)?\s*(?:per\s*(?:person|head|pilgrim|pax|traveller|traveler)|each))|"
        r"(?:(?:per\s*(?:person|head|pilgrim|pax|traveller|traveler)|each)\s*(?:budget\s*(?:of|is|:)?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand)?)",
        t,
    )
    if m_per:
        num_str = (m_per.group(1) or m_per.group(3) or "").replace(",", "")
        mult = m_per.group(2) or m_per.group(4)
        if num_str:
            try:
                per_val = float(num_str)
                if mult and mult.lower() in ("k", "thousand"):
                    per_val *= 1000
                total_val = per_val * pax_val
                return total_val, "per_person", per_val
            except Exception:
                pass

    # Fall back to standard budget extraction
    b_val = extract_budget_preference(text)
    if b_val is not None:
        if is_per_person:
            return b_val * pax_val, "per_person", b_val
        else:
            return b_val, "total", round(b_val / pax_val, 2)

    return None, None, None


def extract_hotel_preference(text: str) -> Optional[str]:
    """Extracts hotel category preference (Budget, Mid-Range, Premium)."""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["cheaper hotel", "cheap hotel", "budget hotel", "affordable accommodation", "budget stay", "affordable hotel", "low cost hotel"]):
        return "Budget"
    if any(k in t for k in ["luxury hotel", "luxury stay", "5 star", "premium hotel", "resort"]):
        return "Premium"
    if any(k in t for k in ["mid-range", "mid range", "3 star", "comfortable hotel", "standard hotel"]):
        return "Mid-Range"
    return None


def extract_pacing_preference(text: str) -> Optional[str]:
    """Extracts travel pacing (relaxed, balanced, packed)."""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["relaxed", "unhurried", "slow pace", "no rush", "peaceful", "leisurely", "less hectic", "easy pace"]):
        return "relaxed"
    if any(k in t for k in ["packed", "tight", "fast", "busy", "maximum", "cover everything", "cover all places", "packed itinerary"]):
        return "packed"
    if any(k in t for k in ["balanced", "moderate", "standard pace"]):
        return "balanced"
    return None


def extract_interests(text: str) -> List[str]:
    """Extracts user travel interest categories."""
    if not text:
        return []
    t = text.lower()
    interests = []
    if any(k in t for k in ["religious", "holy", "darshan", "temple", "shrine", "puja", "aarti", "spiritual", "worship"]):
        interests.append("religious")
    if any(k in t for k in ["nature", "waterfall", "greenery", "stream", "lake", "scenic", "meadow", "hills", "valley"]):
        interests.append("nature")
    if any(k in t for k in ["heritage", "history", "historical", "culture", "cultural", "palace", "fort", "museum", "dogra"]):
        interests.append("culture")
    if any(k in t for k in ["family", "kids", "children", "parents", "elders", "family-friendly"]):
        interests.append("family")
    if any(k in t for k in ["adventure", "trekking", "climbing", "paragliding", "skiing"]):
        interests.append("adventure")
    return interests


def extract_sightseeing_choice(text: str) -> Optional[str]:
    """Extracts whether user wants to choose places, receive recommendations, or decide later."""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["choose later", "decide later", "later", "not now", "skip sightseeing", "no sightseeing", "decide in katra"]):
        return "later"
    if any(k in t for k in ["recommend", "recommendations", "suggest", "curated", "you choose", "what do you suggest", "give recommendations"]):
        return "recommend"
    if any(k in t for k in ["choose places", "select places", "i want to choose", "i will choose", "pick places", "i want to visit"]):
        return "choose"
    return None


def extract_mobility_preference(text: str) -> Optional[str]:
    """Extracts optional accessibility / mobility requirements."""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["senior citizen", "elderly", "minimal walking", "difficulty walking", "can't walk much", "cannot walk much", "slow walking", "knee pain"]):
        return "Minimal walking / Senior"
    if any(k in t for k in ["wheelchair", "battery car", "palki", "pony", "palanquin", "helicopter"]):
        return "Pony / Palki / Battery Car"
    if any(k in t for k in ["standard walking", "normal walking", "can walk", "trek on foot"]):
        return "Standard walking"
    return None


def extract_places_from_text(text: str) -> List[str]:
    """Extracts explicit destination names mentioned in free text."""
    if not text:
        return []
    t = text.lower()
    found = []
    for raw_key, canonical in itinerary_agent.CANONICAL_PLACES.items():
        if raw_key in t and canonical not in ("Sightseeing", "Rest") and canonical not in found:
            found.append(canonical)
    for place_name in itinerary_agent.DESTINATION_LOGISTICS.keys():
        if place_name.lower() in t and place_name not in found:
            found.append(place_name)

    # Also capture candidate destination names from explicit add/visit patterns
    # e.g., "also add Eiffel Tower to our trip", "add Patnitop to our trip", "include Taj Mahal"
    add_match = re.search(
        r"\b(?:also\s+)?(?:add|include|visit|go to|put)\s+(?:a\s+trip\s+to\s+)?([A-Za-z0-9\s'&]+?)(?:\s+(?:to|in|into|for)\s+(?:our\s+|the\s+)?(?:trip|itinerary|plan)|\s+as well|[.,!?]|$)",
        text,
        re.IGNORECASE,
    )
    if add_match:
        cand = add_match.group(1).strip()
        cand_clean = re.sub(r"^(?:a|an|the|our|my|some)\s+", "", cand, flags=re.IGNORECASE).strip()
        lower_cand = cand_clean.lower()
        stopwords = {
            "hotel", "train", "flight", "bus", "rest", "sightseeing", "day", "days",
            "budget", "more", "pax", "person", "people", "trip", "plan", "itinerary",
            "place", "places", "destination", "destinations", "option", "options"
        }
        if cand_clean and len(cand_clean) >= 3 and lower_cand not in stopwords:
            canonical_cand = itinerary_agent.match_place_name(cand_clean)
            final_name = canonical_cand if canonical_cand else cand_clean
            if final_name not in found and final_name not in ("Sightseeing", "Rest"):
                found.append(final_name)

    return found


def extract_trip_requirements(user_text: str, current_req: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extracts structured requirements and user preferences from free text and merges with current state.
    Distinguishes user-specified values from defaults.
    """
    req = dict(current_req) if current_req else {}

    # 1. Structured extraction via conversation_state
    try:
        from agents import conversation_state
        state_wrap = {"requirements": req, "pending_ambiguity": req.get("pending_ambiguity")}
        updated_wrap = conversation_state.update_conversation_state(user_text, current_state=state_wrap)
        req.update(updated_wrap["requirements"])
        if updated_wrap.get("pending_ambiguity") is None and "pending_ambiguity" in req:
            req["pending_ambiguity"] = None
    except Exception:
        pass

    # 2. Base extraction from legacy/conversation agent
    parsed = legacy_agent.parse_request(user_text, current_request=req)
    req.update(parsed)

    # 3. Check if pax was explicitly provided in user text
    pax_extracted = legacy_agent._extract_pax(user_text)
    if pax_extracted is not None:
        req["pax"] = pax_extracted
        req["pilgrim_count"] = pax_extracted
        req["_pax_explicit"] = True
    elif req.get("_pax_explicit"):
        pass  # retain prior explicit mark
    elif req.get("pax") and req.get("pax") > 1:
        req["_pax_explicit"] = True
    else:
        req["_pax_explicit"] = False

    # 4. Check explicit origin
    origin_extracted = legacy_agent._extract_origin(user_text)
    if origin_extracted:
        has_explicit_phrase = bool(re.search(
            r"\b(?:from|out\s+of|leaving|travelling\s+from|traveling\s+from|departing\s+from|starting\s+from|starting\s+city\s+to|departure\s+city|departure\s+from|change\s+(?:my\s+)?(?:departure\s+city|starting\s+city|origin)\s+to)\s+([A-Za-z]+)",
            user_text,
            re.IGNORECASE,
        ))
        if not req.get("origin") or (has_explicit_phrase and "," not in req.get("origin", "")):
            req["origin"] = origin_extracted

    # 5. Check explicit duration
    dur_extracted = legacy_agent._extract_duration(user_text)
    if dur_extracted:
        req["duration_days"] = dur_extracted

    # 6. Check explicit dates
    if legacy_agent.has_explicit_date(user_text):
        st_date, en_date = legacy_agent._extract_date_range(user_text)
        req["start_date"] = st_date
        req["end_date"] = en_date
        req["_date_explicit"] = True
    elif req.get("_date_explicit"):
        pass
    else:
        req["_date_explicit"] = False

    # 7. Check budget (total vs per person)
    tot_b, b_type, per_p_b = extract_budget_details(user_text, pax=req.get("pax", 1))
    if tot_b is not None:
        req["total_budget"] = tot_b
        req["budget_type"] = b_type
        req["budget_per_person"] = per_p_b

    # 8. Check hotel category preference
    h_pref = extract_hotel_preference(user_text)
    if h_pref:
        req["accommodation_preference"] = h_pref

    # 9. Check pacing / travel style
    pace_pref = extract_pacing_preference(user_text)
    if pace_pref:
        req["travel_style"] = pace_pref
        req["_pace_explicit"] = True
    elif not req.get("travel_style"):
        req["travel_style"] = "balanced"  # sensible default

    # 10. Check travel interests
    extracted_interests = extract_interests(user_text)
    if extracted_interests:
        curr_interests = set(req.get("interests", []))
        curr_interests.update(extracted_interests)
        req["interests"] = list(curr_interests)
    elif not req.get("interests"):
        req["interests"] = ["religious"]  # sensible default

    # 11. Check sightseeing choice
    sc = extract_sightseeing_choice(user_text)
    if sc:
        req["sightseeing_choice"] = sc
    elif not req.get("sightseeing_choice"):
        req["sightseeing_choice"] = "recommend"  # sensible default

    # 12. Check mobility considerations (optional)
    mob = extract_mobility_preference(user_text)
    if mob:
        req["mobility"] = mob

    # 13. Check explicit destinations mentioned in text
    destinations = extract_places_from_text(user_text)
    if destinations:
        curr_places = list(req.get("sightseeing_places", []))
        for d in destinations:
            if d not in curr_places:
                curr_places.append(d)
        req["sightseeing_places"] = curr_places

    # 14. Destination specification & ambiguity check
    explicit_fields = set(req.get("_explicit_fields") or [])
    pilgrim_terms = (
        "vaishno", "devi", "katra", "bhawan", "darshan", "parchi", "yatra",
        "pilgrim", "pilgrims", "shrine", "temple", "ardhkuwari", "bhairon",
        "mata rani", "mata", "sanctum"
    )
    has_pilgrim_context = any(w in user_text.lower() for w in pilgrim_terms)
    explicit_dest_mentioned = bool(destinations) or any(k in user_text.lower() for k in ("katra", "vaishno", "patnitop", "srinagar", "shiv khori", "jammu"))

    if explicit_dest_mentioned:
        pass
    elif has_pilgrim_context:
        req["destination"] = "Katra"
        explicit_fields.add("destination")
    elif "destination" in explicit_fields or req.get("destination"):
        # Retain existing destination from prior turn
        pass
    elif req.get("origin"):
        req["destination"] = None
    else:
        req["destination"] = "Katra"

    req["_explicit_fields"] = list(explicit_fields)
    req["_last_user_text"] = user_text
    return req


# -----------------------------------------------------------------------------
# 2. Missing Mandatory Fields Detection & Follow-up Prompting
# -----------------------------------------------------------------------------

def detect_missing_mandatory_fields(req: Dict[str, Any]) -> List[str]:
    """
    Evaluates requirements against the mandatory checklist:
    - origin: departure city is strictly required for transport search
    - duration_or_dates: either an explicit trip duration or calendar dates must be known
    - pax: required only if unknown or not explicitly provided when other details are also missing
    """
    try:
        from agents import conversation_state
        return conversation_state.evaluate_missing_slots({"requirements": req})
    except Exception:
        pass

    explicit = set(req.get("_explicit_fields") or [])
    missing = []

    if "destination" in req and req.get("destination") is None:
        missing.append("destination")

    if not req.get("origin"):
        missing.append("origin")

    if not req.get("_pax_explicit") and not req.get("group_type") and "pax" not in explicit:
        if "origin" not in missing and not req.get("duration_days") and not req.get("_date_explicit"):
            missing.append("pax")

    if not req.get("duration_days") and not req.get("_date_explicit"):
        if "origin" not in missing and "pax" not in missing:
            missing.append("duration_or_dates")

    return missing


def generate_missing_info_question(missing: List[str], req: Dict[str, Any]) -> str:
    """Generates a concise, polite follow-up question covering ONLY the missing details."""
    try:
        from agents import conversation_state
        return conversation_state.generate_smart_missing_prompt(missing, {"requirements": req})
    except Exception:
        pass

    origin = req.get("origin")
    pax = req.get("pax")
    pax_word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(pax, str(pax) if pax else "")

    if "destination" in missing:
        return (
            "🙏 **Jai Mata Di!** Which destination or pilgrimage circuit in Jammu & Kashmir would you like to visit? "
            "(For example: Maa Vaishno Devi / Katra, Srinagar & Kashmir Valley, Patnitop, or Shiv Khori)."
        )

    # Phase 14.5: Single-Question Clarification Policy (Priority: 1. origin, 2. pax, 3. duration_or_dates)
    if "origin" in missing:
        if pax:
            return f"Sure! I'll help you plan a comfortable Vaishno Devi trip for {pax_word}. Which city will you be traveling from?"
        return (
            "🙏 **Jai Mata Di!** Planning a pilgrimage to **Maa Vaishno Devi** is a sacred journey. "
            "Which city or town will you be travelling from to begin your yatra?"
        )

    if "pax" in missing:
        origin_str = f" from {origin}" if origin else ""
        return f"Got it — travelling from **{origin}** to Katra. How many pilgrims will be traveling{origin_str}?"

    if "duration_or_dates" in missing:
        origin_str = f" from {origin}" if origin else ""
        return f"What travel dates or trip duration (number of days) do you prefer for your Vaishno Devi trip{origin_str}?"

    return "Could you please clarify your travel details?"


# -----------------------------------------------------------------------------
# 3. Tool Coordination & Consolidated Plan Pipeline
# -----------------------------------------------------------------------------

def coordinate_plan(req: Dict[str, Any], session_id: Optional[str] = None, plan_version: int = 1) -> Dict[str, Any]:
    """
    Coordinates transport search, darshan slots, accommodation, sightseeing, itinerary,
    and deterministic budget evaluation into a consolidated plan dictionary.
    """
    origin = req.get("origin")
    if not origin or not str(origin).strip():
        msg = (
            "🙏 **Jai Mata Di!** Which city or town will you be travelling from? "
            "Please specify your departure location so I can search suitable transport options for you."
        )
        return {
            "status": "NEEDS_INFO",
            "reply": msg,
            "plan": {"status": "NEEDS_INFO", "message": msg, "options": []},
            "requirements": req,
            "request": req,
            "recommendation": None,
            "diff": {},
            "missing_fields": ["origin"],
            "selected_options": None,
            "budget_evaluation": None,
            "itinerary": None,
            "session_id": session_id,
        }
    pax = max(1, req.get("pax") or req.get("pilgrims") or 1)
    duration = req.get("duration_days") or req.get("duration") or req.get("days") or 4
    cat_pref = req.get("category", "Normal Darshan")
    mode_pref = req.get("mode")
    total_budget = req.get("total_budget")
    hotel_pref = req.get("accommodation_preference")

    # Determine date window
    today_iso = date.today().isoformat()
    start_date = req.get("start_date") or today_iso
    end_date = req.get("end_date")
    if not end_date:
        try:
            st_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = (st_dt + timedelta(days=max(1, duration - 1))).isoformat()
        except Exception:
            end_date = (date.today() + timedelta(days=13)).isoformat()

    # 1. Transport Search
    transport_results, is_direct = legacy_agent._search_transport({
        "origin": origin,
        "start_date": start_date,
        "end_date": end_date,
        "pax": pax,
        "mode": mode_pref,
    })

    # Phase 14.2: Universal Origin & Connecting Journey Engine
    # If direct transport is not in local prototype database, construct authentic connecting options
    if not transport_results:
        try:
            from services.connecting_journey_engine import get_connecting_journey_engine
            engine = get_connecting_journey_engine()
            conn_res = engine.plan_connecting_journey(
                origin=origin,
                start_date=start_date,
                end_date=end_date,
                preferred_mode=mode_pref,
                pax=pax,
            )
            if conn_res.get("status") == "NEEDS_CLARIFICATION":
                msg = conn_res.get("clarification_prompt")
                return {
                    "status": "NEEDS_CLARIFICATION",
                    "reply": msg,
                    "plan": {"status": "NEEDS_CLARIFICATION", "message": msg, "options": []},
                    "requirements": req,
                    "request": req,
                    "recommendation": recommendation_agent.generate_recommendation(req),
                    "diff": {},
                    "missing_fields": [],
                    "selected_options": None,
                    "budget_evaluation": None,
                    "itinerary": None,
                    "session_id": session_id,
                }
            elif conn_res.get("status") == "CONNECTING_ROUTES_AVAILABLE" and conn_res.get("options"):
                transport_results = []
                for opt in conn_res["options"]:
                    first_leg = opt["legs"][0] if opt.get("legs") else {}
                    last_leg = opt["legs"][-1] if opt.get("legs") else {}
                    opt_mode = opt["mode"].lower().replace("-connect", "").replace("-direct", "")
                    if "bus" in opt_mode:
                        norm_mode = "bus"
                    elif "flight" in opt_mode or "air" in opt_mode:
                        norm_mode = "flight"
                    else:
                        norm_mode = "train"

                    price_est = opt.get("indicative_total_price_per_pax") or 450
                    transport_results.append({
                        "id": opt["id"],
                        "mode": norm_mode,
                        "operator": f"{opt['primary_hub']} Connecting Corridor",
                        "transport_no": opt["title"],
                        "train_name": opt["title"],
                        "name": opt["title"],
                        "route": opt["summary_route"],
                        "origin": origin,
                        "destination": "Katra (SVDK)",
                        "departure": first_leg.get("departure_info") or "06:00 AM",
                        "departure_time": "06:00",
                        "arrival": last_leg.get("arrival_info") or "06:00 PM",
                        "arrival_time": "18:00",
                        "duration_mins": 360,
                        "travel_date": start_date,
                        "indicative_fare_min": price_est,
                        "price": price_est,
                        "fare": price_est,
                        "is_connecting": True,
                        "legs": opt.get("legs"),
                        "summary_route": opt.get("summary_route"),
                        "primary_hub": opt.get("primary_hub"),
                        "fallback_level": opt.get("fallback_level"),
                        "booking_advice": opt.get("booking_advice"),
                        "verification_status": "partially_verified",
                        "fare_classification": "PARTIALLY_VERIFIED_CONNECTING",
                    })
        except Exception as exc:
            logger.warning("Connecting route search in orchestrator failed: %s", exc)

    # 2. Darshan Slot Search
    slots = db.search_yatra_slots(start_date, end_date, category=cat_pref, min_seats=pax)
    if not slots:
        slots = db.search_yatra_slots(start_date, end_date, min_seats=pax)
    if not slots:
        slots = [
            {"slot_id": "slot_std_morning", "slot_date": start_date, "slot_time": "09:00", "category": "Normal Darshan", "price": 0, "status": "AVAILABLE", "seats": 100},
            {"slot_id": "slot_std_evening", "slot_date": start_date, "slot_time": "18:00", "category": "Normal Darshan", "price": 0, "status": "AVAILABLE", "seats": 100},
        ]

    # 3. Feasibility / Availability check
    if not transport_results or not slots:
        msg = (
            f"🙏 **Jai Mata Di!** I could not assemble a viable route from **{origin}** for {start_date} to {end_date}.\n\n"
            "• Would you like me to widen the travel dates or check another travel mode?"
        )
        return {
            "status": "NO_AVAILABILITY",
            "reply": msg,
            "plan": {"status": "NO_AVAILABILITY", "message": msg, "options": []},
            "requirements": req,
            "request": req,
            "recommendation": recommendation_agent.generate_recommendation(req),
            "diff": {},
            "missing_fields": [],
            "selected_options": None,
            "budget_evaluation": None,
            "itinerary": None,
            "session_id": session_id,
        }

    # 4. Rank timing-safe combinations with distinct transport options
    # Deduplicate transport: each distinct transport service gets paired with its best feasible slot.
    distinct_combos = []
    seen_transport_ids = set()

    for tr in transport_results:
        tr_id = (tr.get("mode"), tr.get("id"))
        if tr_id in seen_transport_ids:
            continue

        arrival = legacy_agent._transport_arrival_datetime(tr)
        matching_slots = []
        for s in slots:
            buffer_hours = legacy_agent.DARSHAN_PREP_BUFFER_HOURS.get(s.get("category"), 8)
            earliest_slot = arrival + timedelta(hours=buffer_hours)
            if legacy_agent._slot_datetime(s) >= earliest_slot:
                matching_slots.append(s)

        if not matching_slots:
            matching_slots = slots

        # Sort matching slots: prioritize requested category, then lowest price, then earliest slot
        matching_slots.sort(key=lambda s: (0 if s.get("category") == cat_pref else 1, s.get("price", 0), legacy_agent._slot_datetime(s)))
        best_slot = matching_slots[0]

        arrival_dt = legacy_agent._transport_arrival_datetime(tr)
        tr_enriched = dict(tr)
        tr_enriched["arrival_time"] = arrival_dt.strftime("%H:%M")
        tr_enriched["arrival_date"] = arrival_dt.strftime("%Y-%m-%d")
        dur = tr_enriched.get("duration_mins", 0)
        if dur:
            tr_enriched["duration_str"] = f"{dur // 60}h {dur % 60}m"
        # FA-06: Strict separation of verified booking fares from indicative market estimates
        price_num = tr_enriched.get("price") or tr_enriched.get("fare")
        if price_num is not None:
            tr_enriched["fare_per_person"] = price_num
            tr_enriched["total_fare"] = price_num * pax
            total_fare_for_combo = price_num
            fare_desc = f"(₹{tr_enriched['total_fare']:,})"
            has_fare = True
        else:
            tr_enriched["fare_per_person"] = None
            tr_enriched["total_fare"] = None
            if tr_enriched.get("indicative_fare_min") is not None:
                tr_enriched["estimated_fare_per_person"] = tr_enriched.get("indicative_fare_min")
                tr_enriched["estimated_total_fare"] = tr_enriched.get("indicative_fare_min") * pax
                total_fare_for_combo = tr_enriched.get("indicative_fare_min")
                fare_desc = f"(Est. ~₹{tr_enriched['estimated_total_fare']:,} · dynamic airfare)"
                has_fare = True
            else:
                total_fare_for_combo = 0
                fare_desc = "(Tariff/Estimate subject to carrier)"
                has_fare = False

        slot_price = best_slot.get("price") or 0
        total_combo = (total_fare_for_combo + slot_price) * pax
        mode_title = tr_enriched.get("mode", "transport").title()
        bundle_exp = (
            f"Includes {mode_title} for {pax} traveler{'s' if pax > 1 else ''} "
            f"{fare_desc} and confirmed {best_slot.get('category', 'Darshan')} slot."
        )
        combo = {
            "transport": tr_enriched,
            "flight": tr_enriched,
            "slot": best_slot,
            "total_price": total_combo if has_fare else None,
            "sort_price": total_combo if has_fare else None,
            "bundle_explanation": bundle_exp,
        }

        seen_transport_ids.add(tr_id)
        distinct_combos.append(combo)

    if not distinct_combos:
        msg = (
            "🙏 **Jai Mata Di!** I found travel options and darshan slots separately, but no timing-safe combination "
            "(transport arrival would arrive too late for the available darshan slots). "
            "Would you like me to widen the date range or check a different travel mode?"
        )
        return {
            "status": "NO_COMBINATION",
            "reply": msg,
            "plan": {"status": "NO_COMBINATION", "message": msg, "options": []},
            "requirements": req,
            "request": req,
            "recommendation": recommendation_agent.generate_recommendation(req),
            "diff": {},
            "missing_fields": [],
            "selected_options": None,
            "budget_evaluation": None,
            "itinerary": None,
            "session_id": session_id,
        }

    distinct_combos.sort(key=lambda c: c.get("sort_price") if c.get("sort_price") is not None else 999999999.0)
    options = []
    if not mode_pref:
        # Diversity across available modes first (e.g. 1 flight, 1 train, 1 bus)
        seen_modes = set()
        for c in distinct_combos:
            m = c["transport"]["mode"]
            if m not in seen_modes:
                seen_modes.add(m)
                options.append(c)
                if len(options) >= 3:
                    break

    for c in distinct_combos:
        if len(options) >= 3:
            break
        if c not in options:
            options.append(c)

    options.sort(key=lambda c: c.get("sort_price") if c.get("sort_price") is not None else 999999999.0)
    combos = options

    # Check if user explicitly selected a train or transport option
    user_tr = req.get("selected_transport") or req.get("selected_train") or req.get("train_number")
    if user_tr:
        user_tr_str = str(user_tr).lower()
        matched_combo = next(
            (c for c in distinct_combos if user_tr_str in str(c["transport"].get("train_number", "")).lower()
             or user_tr_str in str(c["transport"].get("transport_no", "")).lower()
             or user_tr_str in str(c["transport"].get("name", "")).lower()
             or user_tr_str in str(c["transport"].get("operator", "")).lower()
             or user_tr_str in str(c["transport"].get("id", "")).lower()),
            None,
        )
        if matched_combo:
            selected_combo = matched_combo
            if selected_combo not in combos:
                combos.insert(0, selected_combo)
            else:
                combos.remove(selected_combo)
                combos.insert(0, selected_combo)
        else:
            selected_combo = combos[0]
    else:
        selected_combo = combos[0]

    selected_tr = selected_combo["transport"]
    selected_slot = selected_combo["slot"]

    # Record the selected transport's mode without mutating unstated user preference
    if selected_tr.get("mode"):
        req["selected_mode"] = selected_tr["mode"]

    # 5. Accommodation Search (Verified Katra Catalog Exclusive)
    rooms_needed = budget_engine.calculate_rooms_required(pax)
    hotel_nights = max(1, duration - 1)
    catalog_error = None
    try:
        from services.accommodation_catalog import search_hotels_with_status
        hotels, cat_status = search_hotels_with_status(
            check_in_date=start_date,
            category=hotel_pref,
            min_rooms=rooms_needed,
        )
        if not hotels and hotel_pref and cat_status != "CATALOG_UNAVAILABLE":
            # Broaden to any category in verified catalog
            hotels, cat_status = search_hotels_with_status(
                check_in_date=start_date,
                category=None,
                min_rooms=rooms_needed,
            )
        if cat_status == "CATALOG_UNAVAILABLE":
            catalog_error = "CATALOG_UNAVAILABLE"
            hotels = []
    except Exception as e:
        logger.warning(f"Error querying verified Katra accommodation catalog in orchestrator: {e}")
        catalog_error = "CATALOG_UNAVAILABLE"
        hotels = []

    user_selected_hotel = req.get("selected_hotel") or req.get("hotel")
    reject_niharika = bool(req.get("reject_niharika") or req.get("_reject_niharika"))

    available_hotels = list(hotels)
    if reject_niharika:
        available_hotels = [
            h for h in available_hotels
            if "niharika" not in h.get("name", "").lower() and "niharika" not in h.get("id", "").lower()
        ]

    selected_hotel = None
    if user_selected_hotel:
        if isinstance(user_selected_hotel, dict) and user_selected_hotel.get("name"):
            target_name = user_selected_hotel.get("name", "").lower()
            selected_hotel = next(
                (h for h in available_hotels if h.get("name", "").lower() == target_name or target_name in h.get("name", "").lower()),
                user_selected_hotel,
            )
        elif isinstance(user_selected_hotel, str):
            target_str = user_selected_hotel.lower()
            selected_hotel = next(
                (h for h in available_hotels if target_str in h.get("name", "").lower() or target_str in h.get("id", "").lower()),
                None,
            )

    if not selected_hotel and available_hotels:
        if hotel_pref == "Premium":
            selected_hotel = next((h for h in available_hotels if h.get("category") == "Premium"), available_hotels[-1])
        elif hotel_pref == "Mid-Range":
            selected_hotel = next((h for h in available_hotels if h.get("category") == "Mid-Range"), available_hotels[0])
        elif hotel_pref == "Budget":
            selected_hotel = next((h for h in available_hotels if h.get("category") in ("Budget", "Dharamshala")), available_hotels[0])
        else:
            selected_hotel = available_hotels[0]

    if catalog_error == "CATALOG_UNAVAILABLE":
        req["accommodation_advisory"] = "Katra accommodation recommendations are temporarily unavailable due to catalog retrieval failure. Transport and darshan arrangements are confirmed."
    elif not selected_hotel:
        req["accommodation_advisory"] = "No matching Katra accommodation properties found for the requested criteria. Accommodation is unselected."

    # 6. Sightseeing Selection & Preference Grounding
    raw_user_places = req.get("sightseeing_places") or req.get("selected_places")
    if not raw_user_places and isinstance(req.get("sightseeing"), (list, tuple, str)):
        raw_user_places = req.get("sightseeing")

    if isinstance(raw_user_places, str):
        raw_user_places = [raw_user_places]
    elif not isinstance(raw_user_places, (list, tuple)):
        raw_user_places = []

    user_places = []
    for p in raw_user_places:
        if isinstance(p, dict) and p.get("name"):
            user_places.append(p["name"])
        elif isinstance(p, str) and p.strip() and p.strip().lower() not in ("true", "false", "none", "null"):
            user_places.append(p.strip())

    # 7. Day-by-Day Itinerary Generation via Deterministic Engine
    itinerary_days = itinerary_agent.build_itinerary(
        selected_combo,
        hotel=selected_hotel,
        hotel_nights=hotel_nights,
        sightseeing_places=user_places,
        request=req,
    )

    infeasible_places = getattr(itinerary_days, "infeasible_places", [])
    feasible_places = getattr(itinerary_days, "feasible_places", [])

    # Enrich feasible places for UI cards / selected options
    all_places = content_agent.get_all_places_enriched()
    selected_places = []
    for fp in feasible_places:
        matched = next(
            (p for p in all_places if (itinerary_agent.match_place_name(p["name"]) == itinerary_agent.match_place_name(fp)) or (p["name"].lower() == fp.lower())),
            None,
        )
        if matched:
            selected_places.append(matched)
        else:
            logistics = itinerary_agent.get_destination_logistics(fp)
            selected_places.append({
                "name": fp,
                "category": logistics.get("region", "Sightseeing"),
                "distance": logistics.get("travel_time_desc", "Local Katra"),
                "description": logistics.get("suitability", "Attraction in Jammu & Kashmir"),
            })

    # 8. Deterministic Budget Engine Calculation
    road_transfer_est = 1500.0 if selected_tr.get("mode") == "flight" else 500.0
    meals_est = float(350 * pax * duration)

    budget_eval = budget_engine.calculate_budget(
        pax=pax,
        transport=selected_tr,
        darshan_slot=selected_slot,
        accommodation=selected_hotel,
        estimated_costs={
            "local_road_transfer": road_transfer_est,
            "meals_and_refreshments": meals_est,
        },
        total_budget=total_budget,
        is_round_trip=True,
        estimate_return_if_missing=True,
        check_in_date=start_date,
        check_out_date=end_date,
        duration_days=duration,
    )

    # 9. Format Consolidated Plan Card Response
    reply = _format_consolidated_reply(
        req=req,
        transport=selected_tr,
        slot=selected_slot,
        hotel=selected_hotel,
        sightseeing=selected_places,
        budget_eval=budget_eval,
        itinerary=itinerary_days,
        infeasible_places=infeasible_places,
    )

    selected_options = {
        "transport": selected_tr,
        "darshan_slot": selected_slot,
        "accommodation": selected_hotel,
        "sightseeing": selected_places,
    }

    plan_output = {
        "status": "PLAN_READY",
        "pax": pax,
        "options": combos[:3],
        "available_options": combos[:3],
        "selected_option": selected_combo,
        "hotel": selected_hotel,
        "hotels": available_hotels[:6],
        "available_hotels": available_hotels[:6],
        "itinerary": itinerary_days,
        "budget_evaluation": budget_eval,
        "infeasible_places": infeasible_places,
        "feasible_places": feasible_places,
    }

    rec = recommendation_agent.generate_recommendation(req)

    return {
        "status": "PLAN_READY",
        "reply": reply,
        "plan": plan_output,
        "plan_version": plan_version,
        "requirements": req,
        "request": req,
        "recommendation": rec,
        "diff": {},
        "missing_fields": [],
        "selected_options": selected_options,
        "budget_evaluation": budget_eval,
        "itinerary": itinerary_days,
        "infeasible_places": infeasible_places,
        "feasible_places": feasible_places,
        "hotel": selected_hotel,
        "hotels": available_hotels[:6],
        "available_hotels": available_hotels[:6],
        "available_options": combos[:3],
        "options": combos[:3],
        "session_id": session_id,
        "authorization_required": True,
        "rpa_ready": True,
    }


def _format_consolidated_reply(
    req: Dict[str, Any],
    transport: Dict[str, Any],
    slot: Dict[str, Any],
    hotel: Optional[Dict[str, Any]],
    sightseeing: List[Dict[str, Any]],
    budget_eval: Dict[str, Any],
    itinerary: List[Dict[str, Any]],
    infeasible_places: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Formats a comprehensive, devotional conversational response for yatra plans."""
    origin = req.get("origin") or (transport.get("origin") if isinstance(transport, dict) else None) or "your departure city"
    pax = max(1, req.get("pax") or 1)
    duration = req.get("duration_days") or (len(itinerary) if itinerary else 4)
    nights = max(1, duration - 1)
    rooms = budget_engine.calculate_rooms_required(pax)
    mode = (transport.get("mode") or "train").lower()
    mode_title = mode.title()
    dest = req.get("destination") or "Katra"

    slot_cat = slot.get("category", "Normal Darshan")
    slot_date = slot.get("slot_date", "")
    date_str = slot_date
    if slot_date:
        try:
            dt = datetime.strptime(slot_date, "%Y-%m-%d")
            date_str = f"{dt.day} {dt.strftime('%B')}"
        except Exception:
            date_str = slot_date
    slot_display = f"{slot_cat} · {date_str}" if date_str else slot_cat

    # Weather note
    weather_note = ""
    user_query = str(req.get("_last_user_text") or "").lower()
    if any(w in user_query for w in ["weather", "climate", "temperature", "temp", "cold", "forecast"]):
        try:
            import weather
            w_data = weather.get_weather("Katra")
            if w_data and not w_data.get("fallback"):
                temp = w_data.get("temperature", 22)
                cond = w_data.get("condition", "Pleasant")
                weather_note = f"🌤️ **Current Katra Weather:** {temp}°C, {cond}. Comfortable conditions for undertaking the holy yatra.\n\n"
            else:
                weather_note = "🌤️ **Katra Climate:** Pleasant with cool mountain evenings (15°C to 24°C). Ideal for undertaking the holy trek.\n\n"
        except Exception:
            weather_note = "🌤️ **Katra Climate:** Pleasant with cool mountain evenings (15°C to 24°C). Ideal for undertaking the holy trek.\n\n"

    # Accessibility note
    accessibility_note = ""
    if any(w in user_query for w in ["elderly", "senior", "parents", "wheelchair", "battery car", "palki", "pony"]):
        try:
            from rag.retriever import get_retriever
            retriever = get_retriever()
            rag_res = retriever.retrieve(user_query, conversation_context={"last_tourism_place": "Katra"})
            if rag_res.get("relevant_found") and rag_res.get("context"):
                clean_lines = [l for l in rag_res["context"].split("\n") if not l.startswith("--- Source:")]
                summary = " ".join(clean_lines[:4]).strip()
                if summary:
                    accessibility_note = f"♿ **Accessibility & Senior Pilgrim Guidance:** {summary}\n\n"
        except Exception:
            pass

    # Optional compact summary mode
    if req.get("compact_summary"):
        grand_total = budget_eval.get("grand_total")
        total_str = f"₹{grand_total:,.0f}" if grand_total is not None else "Calculated at booking"
        lines = [
            f"{weather_note}{accessibility_note}🙏 **Jai Mata Di!** Your {duration}-day Vaishno Devi trip is ready for {pax} pilgrim{'s' if pax > 1 else ''} from {origin}.\n",
            f"🚆 **{origin} → Katra** by {mode}",
            f"🛕 **{slot_display}**",
            f"🏨 **{rooms} room{'s' if rooms > 1 else ''} · {nights} night{'s' if nights > 1 else ''}**",
            f"💰 **Estimated total:** {total_str}",
            "\nWould you like to explore your itinerary or modify anything?",
        ]
        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Transport Details & Cost Computation
    # -------------------------------------------------------------------------
    t_name = transport.get("name") or transport.get("operator") or f"{origin} to Katra {mode_title}"
    t_op = transport.get("operator") or ("Northern Railways" if mode == "train" else ("FlixBus" if mode == "bus" else "Air Carrier"))
    t_dep = transport.get("departure_time") or "Morning / Evening schedule"
    t_arr = transport.get("arrival_time") or "Next morning / Afternoon"
    t_dur = transport.get("duration_str") or (f"{transport.get('duration_hours', 12)}h" if transport.get("duration_hours") else "")

    t_fare_pp = (
        transport.get("price")
        or transport.get("fare")
        or transport.get("indicative_fare_min")
        or transport.get("estimated_fare_per_person")
        or (800.0 if mode == "train" else (650.0 if mode == "bus" else 3500.0))
    )
    try:
        t_fare_pp = float(t_fare_pp)
    except Exception:
        t_fare_pp = 650.0
    t_fare_rt_pp = t_fare_pp * 2.0
    total_group_transit = t_fare_rt_pp * pax

    # -------------------------------------------------------------------------
    # Hotel Details & Cost Computation
    # -------------------------------------------------------------------------
    h_name = hotel.get("name", "Niharika Complex (Yatri Niwas, Shakti Bhawan & Ashirwad)") if hotel else "Niharika Complex (Yatri Niwas)"
    h_cat = hotel.get("category", "Dharamshala") if hotel else "Dharamshala"
    try:
        h_rate = float((hotel.get("price_per_night") if hotel else None) or (hotel.get("price") if hotel else None) or 500.0)
    except Exception:
        h_rate = 500.0
    total_hotel = rooms * nights * h_rate
    h_addr = hotel.get("address") or hotel.get("landmark") or "Near Main Bus Stand, Katra Base"

    # -------------------------------------------------------------------------
    # Meals, Transfers, Buffer & Grand Total
    # -------------------------------------------------------------------------
    meals_cost = float(350.0 * pax * duration)
    local_transfer = 1500.0 if mode == "flight" else 500.0
    buffer_amt = 500.0
    yatra_parchi = 0.0

    grand_total_calc = total_group_transit + total_hotel + meals_cost + local_transfer + buffer_amt
    grand_total = budget_eval.get("grand_total") if (budget_eval.get("grand_total") is not None and budget_eval.get("grand_total") > 0) else grand_total_calc
    per_person_cost = grand_total / pax

    total_budget = req.get("total_budget") or budget_eval.get("total_budget")
    if total_budget:
        try:
            total_budget = float(total_budget)
            budget_pp = total_budget / pax
        except Exception:
            total_budget = None
            budget_pp = None
    else:
        budget_pp = None

    sections = []

    # -------------------------------------------------------------------------
    # Section 1: Trip Overview
    # -------------------------------------------------------------------------
    overview_lines = [
        f"{weather_note}{accessibility_note}🙏 **Jai Mata Di!** Your {duration}-day Vaishno Devi trip is ready for {pax} pilgrim{'s' if pax > 1 else ''} from {origin}.\n",
        "### 📋 Trip Overview",
        f"• **Destination:** Shri Mata Vaishno Devi Shrine & Katra Base Town, Jammu & Kashmir",
        f"• **Starting Location:** {origin}",
        f"• **Duration:** {duration} Days / {nights} Nights",
        f"• **Travellers:** {pax} Pilgrims ({rooms} room{'s' if rooms > 1 else ''} allocated at 2 adults/room)",
    ]
    if total_budget:
        overview_lines.append(f"• **Group Budget:** ₹{total_budget:,.0f} (₹{budget_pp:,.0f} per person)")
    overview_lines.append(f"• **Darshan Category:** {slot_display}")
    overview_lines.append(f"• **Primary Transit:** {origin} → Katra by {mode_title}")
    overview_lines.append(f"• **Key Assumptions:** Dedicated full day for the 13 km sacred trek; {rooms} rooms for {nights} nights; balanced meal allowance of ₹350/person/day.")
    sections.append("\n".join(overview_lines))

    # -------------------------------------------------------------------------
    # Section 2: Day-Wise Itinerary
    # -------------------------------------------------------------------------
    if itinerary:
        itin_lines = ["### 📅 Day-Wise Itinerary"]
        for day in itinerary:
            d_num = day.get("day_number", 1)
            d_title = day.get("title", f"Day {d_num}")
            d_base = day.get("base_location", "Katra Base Town")
            d_exertion = day.get("exertion_level", "Moderate")
            itin_lines.append(f"\n#### Day {d_num}: {d_title}")
            itin_lines.append(f"*Base: {d_base} | Exertion: {d_exertion}*")

            acts = day.get("activities", [])
            for act in acts:
                itin_lines.append(f"• {act}")

            if d_num == 1:
                itin_lines.append(f"• 🍽️ **Meals:** Welcome refreshments upon arrival; early traditional Dogra vegetarian dinner in Katra.")
                itin_lines.append(f"• 🏨 **Stay:** Overnight at {h_name} ({h_cat})")
            elif d_num == 2:
                itin_lines.append(f"• 🍽️ **Meals:** Early energizing breakfast; pure vegetarian snacks & free shrine langar along the holy trail (Himkoti & Bhawan); dinner upon descent.")
                itin_lines.append(f"• 🏨 **Stay:** Overnight rest & recovery at {h_name} ({h_cat})")
            elif d_num < duration:
                itin_lines.append(f"• 🍽️ **Meals:** Leisure breakfast; traditional Dogra lunch; evening market dry fruit and souvenir stroll.")
                itin_lines.append(f"• 🏨 **Stay:** Overnight at {h_name} ({h_cat})")
            else:
                itin_lines.append(f"• 🍽️ **Meals:** Morning breakfast in Katra; transit lunch / refreshments for departure journey.")
                itin_lines.append(f"• 🚆 **Stay:** Return transit journey to {origin}")

        sections.append("\n".join(itin_lines))

    # -------------------------------------------------------------------------
    # Section 3: Transport Recommendations
    # -------------------------------------------------------------------------
    trans_lines = [
        f"### 🚆 Transport Recommendation ({origin} ➔ Katra)",
        f"• **Recommended Service:** {t_name}",
        f"• **Operator:** {t_op} | Mode: {mode_title}",
    ]
    if t_dep and t_arr:
        trans_lines.append(f"• **Timings:** Departure ~{t_dep} ➔ Arrival ~{t_arr} ({t_dur})")
    trans_lines.append(f"• **Indicative Fare:** ₹{t_fare_pp:,.0f} per person one-way (~₹{t_fare_rt_pp:,.0f} round-trip)")
    trans_lines.append(f"• **Total Group Transport Cost:** ₹{total_group_transit:,.0f} (Round-trip for {pax} pilgrims)")
    trans_lines.append(f"• **Local Transfers:** Katra Railway Station / Bus Stand to hotel via local auto (₹100–150 per vehicle)")
    trans_lines.append("• **Travel Tip:** Pre-booking is recommended during festive peaks (Navratri / summer).")
    sections.append("\n".join(trans_lines))

    # Connecting transit guidance for non-hub origins
    try:
        from agents import conversation_state
        transit_info = conversation_state.get_transit_guidance_for_origin(origin)
        if transit_info and not transit_info.get("has_verified_direct") and transit_info.get("guidance_text"):
            sections.append(f"📍 **Connecting Transit Guidance:** {transit_info['guidance_text']}")
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # Section 4: Accommodation Arrangements
    # -------------------------------------------------------------------------
    hotel_lines = [
        "### 🏨 Accommodation Arrangements",
        f"• **Recommended Property:** {h_name}",
        f"• **Category:** {h_cat} | **Allocation:** {rooms} room{'s' if rooms > 1 else ''} for {nights} night{'s' if nights > 1 else ''} ({pax} guests)",
        f"• **Tariff:** ₹{h_rate:,.0f} per room/night | **Total Stay Cost:** ₹{total_hotel:,.0f} for {nights} nights",
        f"• **Address / Landmark:** {h_addr}",
        "• **Curated Category Alternatives in Katra:**",
        "  - *Pilgrim / Subsidized:* SMVDSB Yatri Niwas (Niharika, Shakti Bhawan) at ₹150–500/night",
        "  - *Standard Hotel:* Registered Private AC Hotel (near Bus Stand) at ₹1,000–1,800/night",
        "  - *Premium Comfort:* 3-Star / 4-Star Resort (with in-house dining) at ₹2,500–4,500/night",
    ]
    sections.append("\n".join(hotel_lines))

    # -------------------------------------------------------------------------
    # Section 5: Budget Breakdown & Honesty
    # -------------------------------------------------------------------------
    budget_lines = [
        f"### 💰 Budget Breakdown & Cost Estimate ({pax} Pilgrims · {duration} Days)",
        f"• 🚆 **Intercity Travel ({mode_title} Round-trip):** ₹{total_group_transit:,.0f} (~₹{t_fare_rt_pp:,.0f}/person)",
        f"• 🏨 **Accommodation ({rooms} rooms × {nights} nights):** ₹{total_hotel:,.0f}",
        f"• 🍽️ **Meals & Refreshments (₹350/person/day):** ₹{meals_cost:,.0f}",
        f"• 🛺 **Local Katra Transfers:** ₹{local_transfer:,.0f}",
        f"• 🎫 **Yatra Registration (RFID Parchi):** ₹0 (Free mandatory pilgrimage pass)",
        f"• 🛡️ **Contingency / Emergency Buffer:** ₹{buffer_amt:,.0f}",
        f"• 📊 **Estimated Total Group Cost:** ₹{grand_total:,.0f}",
        f"• 👤 **Estimated Cost Per Person:** ₹{per_person_cost:,.0f}",
    ]
    if total_budget:
        if grand_total <= total_budget:
            surplus = total_budget - grand_total
            surplus_pp = surplus / pax
            budget_lines.append(
                f"\n✅ **Budget Assessment (Within Budget):** Your ₹{total_budget:,.0f} group budget (₹{budget_pp:,.0f}/person) "
                f"comfortably covers this 4-day plan with a remaining buffer of **₹{surplus:,.0f}** (₹{surplus_pp:,.0f}/person). "
                "This surplus can be used for prasad, dry fruits shopping, or battery car/pony services on the holy trek."
            )
        else:
            deficit = grand_total - total_budget
            deficit_pp = deficit / pax
            budget_lines.append(
                f"\n⚠️ **Budget Honesty Assessment:** For {pax} pilgrims over {duration} days, ₹{total_budget:,.0f} works out to "
                f"₹{budget_pp:,.0f} per person. Estimated expenses total ₹{grand_total:,.0f} (shortfall of ₹{deficit:,.0f} or ₹{deficit_pp:,.0f}/person). "
                "To remain strictly within your budget, consider utilizing free Shrine Board langar meals and booking subsidized Shrine Board bhavans."
            )
    budget_lines.append("\n*Note: Fares and hotel tariffs reflect published baseline rates and standard seasonal estimates. Exact rates are confirmed at booking.*")
    sections.append("\n".join(budget_lines))

    # Infeasible places advisory
    if infeasible_places:
        inf_notes = []
        for inf in infeasible_places:
            p_name = inf.get("place", "Excursion")
            p_reason = inf.get("reason", f"cannot comfortably fit within a {duration}-day trip without physical exhaustion")
            inf_notes.append(f"{p_name} ({p_reason})")
        sections.append(f"⚠️ **Sightseeing Feasibility Advisory:** {'; '.join(inf_notes)}")

    # -------------------------------------------------------------------------
    # Section 6: Customization & Next Steps
    # -------------------------------------------------------------------------
    custom_lines = [
        "### ⚙️ Customization & Next Steps",
        "You can easily adjust this plan! Simply reply with your preference:",
        "• *“Switch hotel to standard private hotel”* or *“Show premium resorts”*",
        "• *“Change travel mode to flight or train”*",
        "• *“Add Baba Dhansar or Patnitop”* or *“Keep only Katra & Bhawan”*",
        "• *“Adjust trip duration to 3 days”* or *“Update budget”*",
        "• *“Confirm booking”* or *“Book Yatra Parchi”* to proceed with registration and reservations.",
    ]
    sections.append("\n".join(custom_lines))

    return "\n\n".join(sections)


def format_concise_edit_reply(diff: Dict[str, Any], req: Dict[str, Any], updated_plan: Dict[str, Any], new_version: int) -> str:
    """Formats a natural, conversational response for trip modifications without information overload."""
    pax = req.get("pax", 1)
    duration = req.get("duration_days", 4)
    origin = req.get("origin") or "your departure city"
    mode = (req.get("mode") or "train").title()
    b_eval = updated_plan.get("budget_evaluation") or {}
    g_total = b_eval.get("grand_total")
    total_str = f"₹{g_total:,.0f}" if g_total is not None else None

    infeasible = updated_plan.get("infeasible_places") or []
    advisory = ""
    if infeasible:
        inf_notes = []
        for inf in infeasible:
            p_name = inf.get("place", "Excursion")
            p_reason = inf.get("reason", f"cannot comfortably fit within {duration} days without physical exhaustion")
            inf_notes.append(f"{p_name} ({p_reason})")
        advisory = f"\n\n⚠️ **Sightseeing Feasibility Advisory:** {'; '.join(inf_notes)}"

    # Check for single specific edits for natural conversational dialogue
    if diff and len(diff) == 1:
        if "pax" in diff:
            return (
                f"Done! I've updated your trip for {pax} pilgrim{'s' if pax > 1 else ''} (Plan Revision #{new_version}). "
                f"Everything else remains unchanged.\n\n"
                f"💰 **Updated total:** {total_str or 'Calculated'}"
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )
        if "mode" in diff:
            return (
                f"Done! I've updated your travel mode to {mode} from {origin} to Katra (Plan Revision #{new_version}). "
                "Everything else remains unchanged.\n\n"
                f"💰 **Updated total:** {total_str or 'Calculated'}"
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )
        if "duration_days" in diff:
            return (
                f"Done! I've updated your trip duration to {duration} days (Plan Revision #{new_version}). "
                "Your day-by-day itinerary and stay have been synchronized."
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )
        if "accommodation_preference" in diff or "hotel" in diff:
            h_pref = req.get("accommodation_preference", "Standard")
            return (
                f"Done! I've updated your stay preference to {h_pref} (Plan Revision #{new_version}). "
                "Hotel arrangements have been updated."
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )
        if "total_budget" in diff:
            target_b = req.get("total_budget")
            within = b_eval.get("within_budget")
            status = "which fits comfortably within your budget" if within else f"which exceeds your target by ₹{b_eval.get('over_budget_amount', 0):,.0f}"
            return (
                f"Got it! Your budget is now set to ₹{target_b:,.0f} (Plan Revision #{new_version}). "
                f"Your estimated total is {total_str}, {status}."
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )
        if "sightseeing" in diff or "sightseeing_places" in diff or "sightseeing_choice" in diff:
            return (
                f"Done! I've updated your sightseeing preferences (Plan Revision #{new_version}). "
                "Your itinerary and timing schedule have been synchronized."
                f"{advisory}\n\n"
                "Would you like to explore your updated itinerary or modify anything else?"
            )

    # Multiple or composite changes
    changes = []
    if diff:
        for k, info in diff.items():
            label = info.get("label", k)
            new_v = info.get("new", "")
            changes.append(f"• **{label}:** {new_v}")
    changes_text = "\n".join(changes) if changes else f"• **Trip preferences updated**"

    return (
        f"Done! I've updated your trip (Plan Revision #{new_version}):\n"
        f"{changes_text}\n\n"
        f"*Everything else remains unchanged.*"
        f"{advisory}\n\n"
        "Would you like to explore your updated itinerary or modify anything else?"
    )


def format_itemized_cost_breakdown(session_data: Dict[str, Any]) -> str:
    """Formats a dedicated, progressive-disclosure cost breakdown when user requests it."""
    state = session_data.get("state", {})
    b_eval = state.get("budget_evaluation") or {}
    req = state.get("requirements") or {}
    opts = state.get("selected_options") or {}
    version = state.get("plan_version", 1)

    if not b_eval or not opts:
        return (
            "🙏 **Jai Mata Di!** You don't have an active trip plan yet.\n\n"
            "Total pilgrimage expenses typically range between ₹2,000 to ₹6,500 per person depending on your starting city, travel mode, hotel category, and optional services (such as helicopter or battery car tickets).\n\n"
            "Tell me where you will be travelling from (and number of pilgrims), and I will generate an exact itemized budget breakdown with transport schedules and verified tariffs!"
        )

    verified = b_eval.get("verified_costs", {})
    estimated = b_eval.get("estimated_costs", {})
    tr = opts.get("transport") or {}
    slot = opts.get("darshan_slot") or {}
    hotel = opts.get("accommodation") or {}

    pax = max(1, req.get("pax", 1))
    duration = req.get("duration_days", 4)
    origin_val = req.get("origin") or tr.get("origin")
    tr_route = tr.get("display_route") or (f"{origin_val} → Katra" if origin_val else "Katra Journey")
    mode = (tr.get("mode") or "train").title()
    # FA-06 & Correction E: Strict separation of verified bookings from estimated expenses & full reconciliation
    tr_price_num = tr.get("price") or tr.get("fare")
    tr_has_verified_price = tr_price_num is not None
    tr_is_estimated = (
        not tr_has_verified_price
        and (
            tr.get("fare_classification") == "ESTIMATED_MARKET_TARIFF"
            or tr.get("indicative_fare_min") is not None
        )
    )
    if tr_has_verified_price:
        tr_total = float(tr.get("total_fare") or (tr_price_num * pax))
        est_tr_fare = 0.0
    elif tr_is_estimated:
        tr_total = 0.0
        est_tr_fare = float((tr.get("indicative_fare_min") or 0) * pax)
    else:
        tr_total = 0.0
        est_tr_fare = 0.0

    slot_fee = float((slot.get("price") or 0) * pax)
    slot_cat = slot.get("category", "Normal Darshan")
    hotel_name = hotel.get("name", "Local Katra Hotel")
    hotel_price = float(hotel.get("price_per_night") or 0)
    rooms = budget_engine.calculate_rooms_required(pax)
    nights = max(1, duration - 1)
    hotel_total = float(hotel_price * rooms * nights)

    v_total = float(verified.get("total_verified", tr_total + slot_fee + hotel_total))
    e_total = float(estimated.get("total_estimated", 0))
    raw_grand_total = b_eval.get("grand_total")
    grand_total = float(raw_grand_total) if raw_grand_total is not None else None
    per_person = round(grand_total / pax) if grand_total is not None else None

    lines = [
        f"💰 **Detailed Cost Breakdown (Plan Revision #{version}):**\n",
        f"**1. Verified Direct Bookings:** ₹{v_total:,.2f}",
    ]
    if tr_has_verified_price:
        lines.append(f"• **Transport ({tr_route} by {mode}):** ₹{tr_total:,.2f}")
    elif tr_is_estimated:
        lines.append(f"• **Transport ({tr_route} by {mode}):** Dynamic market fare payable at booking (indicative estimate below)")
    else:
        lines.append(f"• **Transport ({tr_route} by {mode}):** Airfare unavailable (dynamic pricing on airline website)")

    lines.extend([
        f"• **Darshan Slot ({slot_cat}):** {'Free' if slot_fee == 0 else f'₹{slot_fee:,.2f}'}",
        f"• **Stay ({hotel_name} · {rooms} rooms × {nights} nights):** ₹{hotel_total:,.2f}\n",
        f"**2. Estimated Expenses (Illustrative):** ₹{e_total:,.2f}",
    ])

    # Correction E: Fully reconciled itemized sub-bullets matching e_total
    est_items = estimated.get("items", {})
    label_map = {
        "estimated_outbound_transport": f"Outbound Airfare ({tr_route} · Indicative)" if mode == "Flight" else f"Outbound Transport ({tr_route} · Indicative)",
        "estimated_return_transport": f"Return Airfare ({tr_route} · Indicative)" if mode == "Flight" else f"Return Transport ({tr_route} · Indicative)",
        "local_road_transfer": "Local Road Transfers",
        "meals_and_refreshments": "Meals & Refreshments",
    }
    has_est_bullet = False
    for item_k, item_amt in est_items.items():
        if item_amt and float(item_amt) > 0:
            has_est_bullet = True
            lbl = label_map.get(item_k, item_k.replace("_", " ").title())
            note = " *(dynamic airline pricing)*" if "transport" in item_k else ""
            lines.append(f"• **{lbl}:** ₹{float(item_amt):,.2f}{note}")

    if tr_is_estimated and est_tr_fare > 0 and "estimated_outbound_transport" not in est_items:
        has_est_bullet = True
        lines.append(f"• **Outbound Airfare ({tr_route} · Indicative):** ₹{est_tr_fare:,.2f} *(dynamic airline pricing)*")

    if not has_est_bullet:
        lines.append("• *No estimated expenses added*")

    lines.append("")
    if grand_total is not None and per_person is not None:
        lines.append(f"**Estimated Grand Total:** ₹{grand_total:,.2f} *(~₹{per_person:,.2f} per pilgrim)*")
    else:
        lines.append("**Estimated Grand Total:** Payable at booking (transport fare unverified)")

    target_b = req.get("total_budget")
    if target_b:
        if b_eval.get("within_budget"):
            lines.append(f"✅ **Within Budget:** Target ₹{target_b:,.2f} (Remaining: ₹{b_eval.get('remaining_budget', 0):,.2f})")
        else:
            lines.append(f"⚠️ **Over Budget:** Target ₹{target_b:,.2f} (Exceeded by ₹{b_eval.get('over_budget_amount', 0):,.2f})")

    lines.append("\nWould you like to authorize this booking or adjust your stay/travel mode?")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 4. Conversational Replanning Engine
# -----------------------------------------------------------------------------

def is_replanning_query(user_text: str) -> bool:
    """Detects if user message is an explicit trip modification / replanning request."""
    if not user_text:
        return False
    t = user_text.lower().strip()

    # 1. Pure informational tourism queries are NOT replanning requests
    # (e.g. "Tell me about Patnitop", "What is Patnitop?", "How far is Patnitop?")
    if re.search(r"\b(?:tell me (?:about|more about)|what is|where is|how is|how far|history of|info on|information (?:about|on)|details of|describe|timings?)\b", t):
        if not re.search(r"\b(?:add|include|put|change|switch)\b", t):
            return False

    replanning_keywords = [
        "budget is", "change budget", "budget to", "my budget", "make budget", "total budget",
        "fit this into our budget", "fit our budget", "within budget", "check budget", "is it in budget",
        "fit my budget", "in our budget",
        "change mode", "switch to", "travel by", "change to", "change it to", "switch it to",
        "change to train", "change to flight", "change to bus", "by train", "by flight", "by bus",
        "cheaper hotel", "different hotel", "change hotel", "luxury hotel", "budget hotel",
        "second option", "option 2", "third option", "select another hotel", "other hotels",
        "don't want niharika", "dont want niharika", "change my train", "change transport",
        "change my travel date", "change travel date", "change date to", "travel on",
        "make it relaxed", "make it packed", "make it balanced",
        "travelling with", "traveling with", "make pax", "members",
        "number of travellers", "number of travelers", "number of pilgrims", "travellers to", "travelers to", "pilgrims to",
        "change travellers", "change travelers", "change the number of", "change pax to",
        "change origin to", "starting from", "shift to", "make it 5 days", "make it 3 days", "make it 6 days", "extend trip",
        "also add", "also visit", "also include", "add place", "choose later", "decide later",
    ]
    if any(k in t for k in replanning_keywords):
        return True
    if re.search(r"\b(?:change|switch|prefer)\s+(?:it\s+)?(?:mode\s+)?to\s+(?:train|flight|bus)\b", t):
        return True
    if re.search(r"\bwe are (\d+|a group of|family of)\b", t):
        return True
    if re.search(r"\b(?:add|include|visit|put)\s+.+?\s+(?:to|in|into)\s+(?:our\s+|the\s+)?(?:trip|itinerary|plan)\b", t):
        return True
    if bool(extract_places_from_text(user_text)) and any(w in t for w in ["add", "include", "put", "trip", "plan"]):
        return True
    return False


def handle_replanning(user_text: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies selective replanning: updates only modified components,
    recalculates budget, and syncs itinerary.
    """
    state = session_data.get("state", {})
    req = dict(state.get("requirements", {}))
    old_req = dict(req)
    session_id = session_data.get("session_id")

    # 1. Budget update (total vs per-person)
    tot_b, b_type, per_p_b = extract_budget_details(user_text, pax=req.get("pax", 1))
    if tot_b is not None:
        req["total_budget"] = tot_b
        req["budget_type"] = b_type
        req["budget_per_person"] = per_p_b
    else:
        new_budget = extract_budget_preference(user_text)
        if new_budget is not None:
            req["total_budget"] = new_budget

    # 2. Travel mode change
    new_mode = legacy_agent._extract_mode(user_text)
    if new_mode:
        req["mode"] = new_mode

    # 3. Passenger count change
    new_pax = legacy_agent._extract_pax(user_text)
    if new_pax is not None:
        req["pax"] = new_pax
        req["_pax_explicit"] = True

    # 4. Origin change
    has_explicit_origin = bool(re.search(
        r"\b(?:from|out of|leaving|travelling from|traveling from|departing from|starting from|starting city to|city to|from city|starting city|change my starting city to|change origin to)\s+([A-Za-z]+)",
        user_text,
        re.IGNORECASE,
    ))
    new_origin = legacy_agent._extract_origin(user_text)
    if new_origin and (has_explicit_origin or not req.get("origin")):
        req["origin"] = new_origin

    # 5. Hotel category change
    new_h_pref = extract_hotel_preference(user_text)
    if new_h_pref:
        req["accommodation_preference"] = new_h_pref

    # 6. Duration change
    new_dur = legacy_agent._extract_duration(user_text)
    if new_dur:
        req["duration_days"] = new_dur

    # 7. Travel style / pacing change
    p_pref = extract_pacing_preference(user_text)
    if p_pref:
        req["travel_style"] = p_pref
    else:
        prefs = recommendation_agent.extract_preferences(user_text)
        if prefs.get("travel_style"):
            req["travel_style"] = prefs["travel_style"]
        if prefs.get("group_type"):
            req["group_type"] = prefs["group_type"]

    # 8. Interests change
    extracted_interests = extract_interests(user_text)
    if extracted_interests:
        curr_interests = set(req.get("interests", []))
        curr_interests.update(extracted_interests)
        req["interests"] = list(curr_interests)

    # 9. Sightseeing choice change ("later", "recommend")
    new_sc = extract_sightseeing_choice(user_text)
    if new_sc:
        req["sightseeing_choice"] = new_sc

    # 10. Mobility considerations
    mob = extract_mobility_preference(user_text)
    if mob:
        req["mobility"] = mob

    # 11. Sightseeing destinations in replanning
    new_places = extract_places_from_text(user_text)
    if new_places:
        curr_places = list(req.get("sightseeing_places", []))
        for np in new_places:
            if np not in curr_places:
                curr_places.append(np)
        req["sightseeing_places"] = curr_places

    # 12. Date updates in replanning
    if legacy_agent.has_explicit_date(user_text):
        st_date, en_date = legacy_agent._extract_date_range(user_text)
        if st_date:
            req["start_date"] = st_date
            req["_date_explicit"] = True
            if en_date:
                req["end_date"] = en_date
                try:
                    d1 = datetime.strptime(st_date, "%Y-%m-%d")
                    d2 = datetime.strptime(en_date, "%Y-%m-%d")
                    req["duration_days"] = max(1, (d2 - d1).days + 1)
                except Exception:
                    pass

    # 13. Hotel rejection or selection in replanning
    tl_rep = user_text.lower()
    if "niharika" in tl_rep and any(w in tl_rep for w in ["don't want", "dont want", "not want", "reject", "other", "different"]):
        req["reject_niharika"] = True
        req["_reject_niharika"] = True
        req.pop("selected_hotel", None)
        req.pop("hotel", None)

    # 14. Train selection in replanning
    for t_num in ("22439", "22440", "22477", "22478", "22461", "12445"):
        if t_num in tl_rep:
            req["selected_transport"] = t_num
            req["mode"] = "train"
            break
    if "vande bharat" in tl_rep:
        req["selected_transport"] = "22439"
        req["mode"] = "train"

    curr_version = state.get("plan_version", 1)
    new_version = curr_version + 1
    had_previous_auth = bool(state.get("authorized_plan_version") or state.get("authorization", {}).get("granted"))

    # Archive previous booking if one exists for earlier revision
    prior_rpa = state.get("rpa_execution") or {}
    prior_booking_id = prior_rpa.get("booking_id")
    booking_history = list(state.get("booking_history") or [])
    if prior_booking_id and not any(b.get("booking_id") == prior_booking_id for b in booking_history):
        booking_history.append({
            "booking_id": prior_booking_id,
            "plan_version": curr_version,
            "status": "CONFIRMED_PRIOR_REVISION",
            "note": f"Confirmed under Revision #{curr_version}. Prototype does not perform automatic cancellation or refunds.",
        })

    rpa_state = {
        "status": "PENDING_RECONFIRMATION" if prior_booking_id else "NOT_TRIGGERED",
        "booking_id": None,
        "plan_version": new_version,
        "previous_booking": {
            "booking_id": prior_booking_id,
            "plan_version": curr_version,
            "status": "CONFIRMED_PRIOR_REVISION",
            "note": f"Previous booking {prior_booking_id} remains on file for Revision #{curr_version}. Automatic cancellation/modification is not supported by prototype.",
        } if prior_booking_id else None,
        "screenshot_path": None,
        "logs": [],
    }

    revoked_auth = {
        "pending": True,
        "granted": False,
        "authorized_at": None,
        "authorized_for_version": None,
        "plan_version": new_version,
        "revoked_reason": "plan_modified",
    }

    # 7. Re-coordinate plan with updated requirements
    updated_plan = coordinate_plan(req, session_id=session_id, plan_version=new_version)

    # 8. Check if query was asking about budget feasibility without specifying a new budget number
    feasibility_queries = ["fit this into our budget", "fit our budget", "within budget", "is it in budget", "fit in budget", "fit my budget", "in our budget"]
    if any(q in user_text.lower() for q in feasibility_queries) and new_budget is None:
        target_b = req.get("total_budget")
        b_eval = updated_plan.get("budget_evaluation") or {}
        g_total = b_eval.get("grand_total")
        if target_b and g_total:
            if b_eval.get("within_budget"):
                rem = b_eval.get("remaining_budget", 0.0)
                msg = (
                    f"🙏 **Jai Mata Di! Yes, your plan fits within your budget.**\n\n"
                    f"• **Target Budget:** ₹{target_b:,.2f}\n"
                    f"• **Estimated Total:** ₹{g_total:,.2f}\n"
                    f"• **Remaining Surplus:** ₹{rem:,.2f}\n\n"
                    "Would you like to authorize this booking (reply **'Confirm booking'**)?"
                )
            else:
                over = b_eval.get("over_budget_amount", 0.0)
                msg = (
                    f"🙏 **Jai Mata Di! Currently, your estimated total exceeds your budget.**\n\n"
                    f"• **Target Budget:** ₹{target_b:,.2f}\n"
                    f"• **Estimated Total:** ₹{g_total:,.2f}\n"
                    f"• **Budget Exceeded By:** ₹{over:,.2f}\n\n"
                    "_Tip: You can reply **'find a cheaper hotel'** or **'change to train'** to reduce total costs._"
                )
            updated_plan["reply"] = msg
        elif not target_b:
            updated_plan["reply"] = (
                "🙏 **Jai Mata Di!** To check whether this yatra fits within your budget, "
                "could you please share your target budget amount (e.g. ₹15,000 or ₹25,000)?"
            )
    else:
        # Compute edit diff
        diff = legacy_agent.get_changed_fields(old_req, req)
        updated_plan["diff"] = diff
        if diff:
            updated_plan["reply"] = format_concise_edit_reply(diff, req, updated_plan, new_version)

    if prior_booking_id:
        updated_plan["reply"] += (
            f"\n\n⚠️ **Notice:** Your trip requirements have changed (Plan Revision #{new_version}). "
            f"Previous authorization has been reset. Note: Prior booking **{prior_booking_id}** remains on file for Revision #{curr_version} "
            "(automatic cancellation/refunds are not supported by this prototype). "
            f"Please review the updated plan and reply **'Confirm booking'** when ready to authorize Revision #{new_version}."
        )
    elif had_previous_auth:
        updated_plan["reply"] += (
            f"\n\n⚠️ **Notice:** Your trip requirements have changed (Plan Revision #{new_version}). "
            f"Previous authorization is no longer valid. Please review the updated plan and reply **'Confirm booking'** when ready to authorize Revision #{new_version}."
        )

    # Persist back to session
    session_store.update_session(
        session_id=session_id,
        updates={
            "requirements": req,
            "selected_options": updated_plan.get("selected_options"),
            "budget_evaluation": updated_plan.get("budget_evaluation"),
            "itinerary": updated_plan.get("itinerary"),
            "plan_version": new_version,
            "authorized_plan_version": None,
            "authorization": revoked_auth,
            "rpa_execution": rpa_state,
            "booking_history": booking_history,
            "pending_options": updated_plan.get("plan", {}).get("options"),
        },
        status="PLAN_REVISED",
    )

    updated_plan["status"] = "PLAN_REVISED"
    updated_plan["plan_version"] = new_version
    updated_plan["authorization"] = revoked_auth
    updated_plan["authorization_required"] = True

    return updated_plan


# -----------------------------------------------------------------------------
# 5. Human Authorization Gate & RPA Execution
# -----------------------------------------------------------------------------

def handle_booking_navigation_intent(
    user_text: str,
    session_data: Dict[str, Any],
    pending_options: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Handles booking-intent and navigation requests from chat without executing bookings.
    Transfers the complete recommended trip context to the guided booking experience:
    - Number of pilgrims
    - Origin and destination
    - Selected travel dates
    - Recommended itinerary
    - Selected accommodation and transport
    - Budget and estimated cost
    - Feasible and infeasible destination advisories
    Returns status: 'NAVIGATE_TO_BOOKING' and action: 'NAVIGATE_TO_BOOKING'.
    Never generates a booking ID, confirms a booking, or executes RPA.
    """
    session_data = session_data or {}
    state = session_data.get("state", {})
    sid = session_data.get("session_id")
    req = dict(state.get("requirements", {}))
    curr_version = state.get("plan_version", 1)

    # 1. Update any user-supplied requirements from the text (e.g. "for 2 pilgrims")
    from agents import conversation_state
    session_data = conversation_state.update_conversation_state(user_text, session_data)
    state = session_data.get("state", state)
    req = dict(state.get("requirements", req))

    parsed_req = legacy_agent.parse_request(user_text, current_request=req)
    for k, v in parsed_req.items():
        if v is not None and v != "":
            req[k] = v
    pax_val = legacy_agent._extract_pax(user_text)
    if pax_val:
        req["pax"] = pax_val

    # 2. Check if we have an active travel plan / options
    sel_opt = dict(state.get("selected_options") or {})
    tr = sel_opt.get("transport") or {}
    slot = sel_opt.get("darshan_slot") or {}
    hotel = state.get("hotel") or sel_opt.get("accommodation") or {}
    itin = list(state.get("itinerary") or [])
    budget_eval = dict(state.get("budget_evaluation") or {})
    feasible = list(state.get("feasible_places") or [])
    infeasible = list(state.get("infeasible_places") or [])

    options_list = []
    if pending_options:
        if isinstance(pending_options, dict) and "options" in pending_options:
            options_list = pending_options["options"]
        elif isinstance(pending_options, list):
            options_list = pending_options
    elif state.get("pending_options"):
        st_opts = state["pending_options"]
        if isinstance(st_opts, dict) and "options" in st_opts:
            options_list = st_opts["options"]
        elif isinstance(st_opts, list):
            options_list = st_opts

    # If no options exist yet, but we have origin, plan options dynamically
    if not options_list and req.get("origin"):
        try:
            if hasattr(coordinator, "plan_travel_and_darshan"):
                plan_res = coordinator.plan_travel_and_darshan(req)
            elif hasattr(coordinator, "build_plan"):
                plan_res = coordinator.build_plan(req)
            else:
                plan_res = legacy_agent.build_plan(req)
            if plan_res and isinstance(plan_res, dict):
                plan_opts = plan_res.get("options") or []
                if plan_opts:
                    options_list = plan_opts
                    if not sel_opt.get("transport"):
                        sel_opt["transport"] = plan_opts[0].get("transport") or plan_opts[0].get("flight")
                        sel_opt["darshan_slot"] = plan_opts[0].get("slot")
        except Exception as exc:
            logger.warning("Failed to auto-plan options for booking intent: %s", exc)

    # Pick the top recommended option if not yet chosen
    selected_option = None
    if options_list:
        selected_option = options_list[0]
    elif tr or slot:
        selected_option = {
            "transport": tr,
            "flight": tr,
            "slot": slot,
            "total_price": budget_eval.get("grand_total") or 1660.0,
        }

    # If itinerary missing, generate day-wise itinerary
    if not itin and req.get("origin"):
        try:
            places = feasible if feasible else ["Bhairavnath Temple"]
            if hasattr(coordinator, "generate_itinerary"):
                itin_res = coordinator.generate_itinerary(
                    option=selected_option,
                    hotel=hotel,
                    hotel_nights=max(1, req.get("duration_days", 4) - 1),
                    sightseeing_places=places,
                    request=req,
                )
            elif hasattr(coordinator, "build_final_itinerary"):
                itin_res = coordinator.build_final_itinerary(
                    option=selected_option,
                    hotel=hotel,
                    hotel_nights=max(1, req.get("duration_days", 4) - 1),
                    sightseeing_places=places,
                    request=req,
                )
            else:
                itin_res = itinerary_agent.build_itinerary(
                    selected_option,
                    hotel=hotel,
                    hotel_nights=max(1, req.get("duration_days", 4) - 1),
                    sightseeing_places=places,
                    request=req,
                )
            if itin_res and isinstance(itin_res, dict):
                itin = itin_res.get("itinerary") or []
                if itin_res.get("feasible_places"):
                    feasible = itin_res["feasible_places"]
                if itin_res.get("infeasible_places"):
                    infeasible = itin_res["infeasible_places"]
        except Exception as exc:
            logger.warning("Failed to auto-generate itinerary for booking intent: %s", exc)

    # 3. Check for essential missing details (e.g. no origin specified)
    if not req.get("origin"):
        reply = (
            "🙏 **Jai Mata Di!** Before proceeding to booking, please tell me your departure city "
            "(e.g. Delhi, Mumbai, Jammu) and how many pilgrims are travelling."
        )
        return {
            "intent": "BOOKING_INTENT",
            "status": "NEEDS_INFO",
            "reply": reply,
            "session_id": sid,
            "missing_fields": ["origin"],
            "request": req,
        }

    # 4. Construct clean consolidated plan
    plan_dict = {
        "options": options_list,
        "selected_option": selected_option,
        "hotel": hotel if (hotel and isinstance(hotel, dict) and hotel.get("name")) else None,
        "itinerary": itin,
        "budget_evaluation": budget_eval,
        "feasible_places": feasible,
        "infeasible_places": infeasible,
        "status": "PLAN_READY",
    }

    reply = (
        "🙏 **Jai Mata Di!** Let's continue with your selected Yatra. "
        "I'm opening your recommended itinerary so you can review the details and proceed with the booking."
    )

    # Update session with preserved requirements and state
    if sid:
        try:
            session_store.update_session(
                session_id=sid,
                updates={
                    "requirements": req,
                    "selected_options": sel_opt,
                    "itinerary": itin,
                    "pending_options": options_list,
                    "feasible_places": feasible,
                    "infeasible_places": infeasible,
                },
                status="NAVIGATING_TO_BOOKING",
            )
        except Exception as exc:
            logger.warning("Failed to update session for booking intent: %s", exc)

    pax_count = req.get("pax") or 1
    hotel_sel = req.get("hotel_selected")
    if hotel_sel is None:
        hotel_sel = True if hotel else True
    own_veh = bool(req.get("own_vehicle", False))
    trans_sel = req.get("transport_selected")
    if trans_sel is None:
        trans_sel = False if own_veh else True

    booking_handoff = {
        "primary_contact": req.get("primary_contact") or {"name": "", "phone": "", "email": ""},
        "pax": pax_count,
        "pilgrims": req.get("pilgrims") or [],
        "start_date": req.get("start_date") or req.get("travel_date") or "2026-11-10",
        "return_date": req.get("return_date"),
        "duration": req.get("duration_days") or 4,
        "origin": req.get("origin") or "Delhi",
        "destination": req.get("destination") or "Katra",
        "hotel_selected": hotel_sel,
        "selected_hotel": hotel if (hotel_sel and hotel and isinstance(hotel, dict) and hotel.get("name")) else None,
        "hotel_nights": req.get("hotel_nights") or max(1, (req.get("duration_days") or 4) - 1),
        "transport_selected": trans_sel,
        "selected_transport": (selected_option.get("transport") or selected_option.get("flight")) if (trans_sel and not own_veh and selected_option) else None,
        "own_vehicle": own_veh,
        "budget": req.get("total_budget") or budget_eval.get("grand_total"),
        "accessibility": req.get("accessibility_requirements") or [],
        "prefilled_fields": list(req.get("_explicit_fields") or []),
    }

    return {
        "intent": "BOOKING_INTENT",
        "status": "NAVIGATE_TO_BOOKING",
        "action": "NAVIGATE_TO_BOOKING",
        "reply": reply,
        "session_id": sid,
        "plan_version": curr_version,
        "request": req,
        "plan": plan_dict,
        "itinerary": itin,
        "selected_option": selected_option,
        "options": options_list,
        "hotel": hotel if (hotel and isinstance(hotel, dict) and hotel.get("name")) else None,
        "budget_evaluation": budget_eval,
        "feasible_places": feasible,
        "infeasible_places": infeasible,
        "booking_handoff": booking_handoff,
        "bookingHandoff": booking_handoff,
        "primary_contact": booking_handoff["primary_contact"],
        "pilgrims": booking_handoff["pilgrims"],
        "own_vehicle": own_veh,
        "hotel_selected": hotel_sel,
        "transport_selected": trans_sel,
        "step": 2,
    }


def handle_booking_authorization(
    user_text: str,
    session_data: Dict[str, Any],
    human_authorized: bool = False,
    pending_options: Optional[Any] = None,
    authorized_plan_version: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Enforces the Human-in-the-Loop authorization gate before triggering Playwright mock RPA.
    Treats authorization as approval of a specific plan version, not permanent permission for all future changes.
    Uses session-level locking to guarantee idempotency and avoid duplicate bookings under concurrent requests.
    """
    session_data = session_data or {}
    state = session_data.get("state", {})
    session_id = session_data.get("session_id")
    req = state.get("requirements", {})
    selected_options = state.get("selected_options") or {}
    budget_eval = state.get("budget_evaluation") or {}

    curr_version = state.get("plan_version", 1)
    prev_authorized_version = state.get("authorized_plan_version")
    revoked_reason = state.get("authorization", {}).get("revoked_reason")

    t_lower = (user_text or "").lower()
    is_booking_intent = any(
        bi in t_lower
        for bi in [
            "i want to", "help me", "how to", "proceed with booking",
            "continue with the booking", "continue to booking", "proceed to booking"
        ]
    )
    explicit_confirm_keywords = [
        "confirm booking", "yes, confirm", "yes confirm", "authorize booking",
        "yes, authorize", "yes authorize", "yes, proceed with authorization", "i confirm",
        "yes, proceed", "yes proceed", "confirm my option"
    ]
    has_confirm_keyword = any(w in t_lower for w in explicit_confirm_keywords) and not is_booking_intent

    # Human authorization logic
    if human_authorized:
        if authorized_plan_version is not None and authorized_plan_version != curr_version:
            is_confirmed = False
        else:
            is_confirmed = True
    elif has_confirm_keyword:
        is_confirmed = True
    else:
        is_confirmed = False

    # Idempotency / Duplicate Booking Check:
    # If this exact plan revision is already confirmed and has a valid booking ID on file:
    existing_rpa = state.get("rpa_execution") or {}
    existing_bid = existing_rpa.get("booking_id")
    already_booked_this_version = (
        bool(existing_bid)
        and (state.get("authorized_plan_version") == curr_version)
        and bool(state.get("authorization", {}).get("granted"))
    )

    if already_booked_this_version and (is_confirmed or has_confirm_keyword):
        reply = (
            "🙏 **Jai Mata Di! Your booking is already confirmed!**\n\n"
            f"• **Booking Confirmation ID:** **{existing_bid}**\n"
            f"• **Plan Version:** Revision #{curr_version}\n"
            "• **Status:** Confirmed & On File\n\n"
            "_No duplicate charge or booking was created. May Mata Vaishno Devi bless your pilgrimage!_"
        )
        return {
            "intent": "BOOKING",
            "reply": reply,
            "status": "success",
            "booking_id": existing_bid,
            "plan_version": curr_version,
            "duplicate_prevented": True,
            "rpa_info": existing_rpa,
            "session_id": session_id,
            "requirements": req,
            "request": req,
            "selected_options": selected_options,
            "budget_evaluation": budget_eval,
            "plan": None,
            "itinerary": None,
            "last_tourism_place": state.get("last_tourism_place"),
            "last_itinerary_context": state.get("last_itinerary_context"),
            "tool_execution": {
                "tool": "execute_rpa_booking_tool",
                "status": "already_confirmed",
                "results": existing_rpa,
            },
        }

    # If selected_options is not populated in session, check pending_options from caller
    tr = selected_options.get("transport") or {}
    slot = selected_options.get("darshan_slot") or {}
    hotel = selected_options.get("accommodation") or {}

    pax = req.get("pax", 1)
    origin = req.get("origin") or tr.get("origin") or "your departure city"

    opts = pending_options.get("options") if isinstance(pending_options, dict) else (pending_options if isinstance(pending_options, list) else None)
    if not opts and state.get("pending_options"):
        st_opts = state["pending_options"]
        opts = st_opts.get("options") if isinstance(st_opts, dict) else (st_opts if isinstance(st_opts, list) else None)

    opt = None
    if opts:
        opt_match = re.search(r"option\s*(\d+)", t_lower)
        if opt_match:
            idx = int(opt_match.group(1)) - 1
            if 0 <= idx < len(opts):
                opt = opts[idx]
        if not opt and len(opts) > 0:
            opt = opts[0]

    if opt:
        tr = opt.get("transport") or opt.get("flight") or tr
        slot = opt.get("slot") or slot

    tr_text = f"{tr.get('mode', 'Train')} from {origin}"
    slot_text = slot.get("category", "Normal Darshan")
    grand_total = budget_eval.get("grand_total")
    if grand_total is None and opt and opt.get("total_price"):
        grand_total = opt["total_price"]
    if grand_total is None:
        grand_total = 1000.0

    # 1. Gate: If not explicitly authorized -> Show review summary
    if not is_confirmed:
        mode_label = tr.get("mode", "Train").title()
        cat_label = slot.get("category", "Normal Darshan")
        op_label = tr.get("operator", "Railways")
        price = grand_total

        revision_notice = ""
        if revoked_reason == "plan_modified" or (prev_authorized_version and prev_authorized_version != curr_version):
            prev_v = prev_authorized_version or (curr_version - 1)
            revision_notice = (
                f"⚠️ **Plan Revised (Revision #{curr_version}):** Your trip plan has been modified since the previous authorization.\n"
                f"Prior approval for Revision #{prev_v} cannot authorize this updated plan.\n\n"
            )

        reply = (
            "🙏 **Jai Mata Di! Human Confirmation Required**\n\n"
            f"{revision_notice}"
            "You are about to proceed with the following booking:\n"
            f"• **Plan Version:** Revision #{curr_version}\n"
            f"• **Route:** {origin} → Katra\n"
            f"• **Transport:** {mode_label} ({op_label})\n"
            f"• **Yatra Slot:** {cat_label}\n"
            f"• **Passengers:** {pax} pilgrim{'s' if pax > 1 else ''}\n"
            f"• **Estimated Total:** ₹{price:,.2f}\n\n"
            "⚠️ **Confirmation Gate:** Do you authorize our Playwright RPA agent to execute this booking?\n\n"
            "_Reply **'Confirm booking'** or **'Yes, proceed'** to execute authorization._"
        )

        if session_id:
            session_store.update_session(
                session_id=session_id,
                updates={
                    "plan_version": curr_version,
                    "authorization": {
                        "pending": True,
                        "granted": False,
                        "plan_version": curr_version,
                        "authorized_for_version": None,
                        "revoked_reason": revoked_reason,
                    },
                },
                status="AWAITING_AUTHORIZATION",
            )

        return {
            "intent": "BOOKING",
            "reply": reply,
            "status": "authorization_required",
            "plan_version": curr_version,
            "session_id": session_id,
            "requirements": req,
            "request": req,
            "selected_options": selected_options,
            "budget_evaluation": budget_eval,
            "plan": None,
            "itinerary": None,
            "last_tourism_place": state.get("last_tourism_place"),
            "last_itinerary_context": state.get("last_itinerary_context"),
            "tool_execution": {
                "tool": "execute_rpa_booking_tool",
                "status": "pending_human_confirmation",
            },
        }

    # 2. Gate Passed: Execute Playwright Mock RPA
    lock = session_store.get_session_lock(session_id) if session_id else threading.Lock()
    with lock:
        # Re-check under lock in case a concurrent request already executed
        if session_id:
            fresh_session = session_store.get_session(session_id)
            if fresh_session:
                st = fresh_session.get("state", {})
                cv = st.get("plan_version", 1)
                existing_rpa = st.get("rpa_execution") or {}
                existing_bid = existing_rpa.get("booking_id")
                if (
                    bool(existing_bid)
                    and (st.get("authorized_plan_version") == cv)
                    and bool(st.get("authorization", {}).get("granted"))
                ):
                    reply = (
                        "🙏 **Jai Mata Di! Your booking is already confirmed!**\n\n"
                        f"• **Booking Confirmation ID:** **{existing_bid}**\n"
                        f"• **Plan Version:** Revision #{cv}\n"
                        "• **Status:** Confirmed & On File\n\n"
                        "_No duplicate charge or booking was created. May Mata Vaishno Devi bless your pilgrimage!_"
                    )
                    return {
                        "intent": "BOOKING",
                        "reply": reply,
                        "status": "success",
                        "booking_id": existing_bid,
                        "plan_version": cv,
                        "duplicate_prevented": True,
                        "rpa_info": existing_rpa,
                        "session_id": session_id,
                        "requirements": req,
                        "request": req,
                        "selected_options": selected_options,
                        "budget_evaluation": budget_eval,
                        "plan": None,
                        "itinerary": None,
                        "last_tourism_place": state.get("last_tourism_place"),
                        "last_itinerary_context": state.get("last_itinerary_context"),
                        "tool_execution": {
                            "tool": "execute_rpa_booking_tool",
                            "status": "already_confirmed",
                            "results": existing_rpa,
                        },
                    }
                state = st

        rpa_info = rpa_agent.execute_playwright_mock_booking(
            user_name="Guest-User",
            pax_count=pax,
            transport_text=tr_text,
            slot_text=slot_text,
            total_price=float(grand_total),
            headless=True,
        )

        booking_id = rpa_info.get("booking_id", f"VD-RPA-{int(datetime.now().timestamp())}")

        reply = (
            "🙏 **Jai Mata Di! Booking Executed & Confirmed!**\n\n"
            f"Your confirmation ID is **{booking_id}**.\n\n"
            f"• **Plan Version Authorized:** Revision #{curr_version}\n"
            "• **Playwright RPA Execution:** Verified via browser automation agent.\n"
            f"• **Total Paid (Mock):** ₹{rpa_info.get('total_price', grand_total):,.2f}\n\n"
            "May Mata Vaishno Devi grant you a safe, blessed, and memorable yatra!"
        )

        booking_history = list(state.get("booking_history") or [])
        new_record = {
            "booking_id": booking_id,
            "plan_version": curr_version,
            "status": "CONFIRMED",
            "authorized_at": datetime.now().isoformat(),
            "total_price": float(grand_total),
        }
        booking_history.append(new_record)

        rpa_info_copy = dict(rpa_info)
        rpa_info_copy["plan_version"] = curr_version

        if session_id:
            session_store.update_session(
                session_id=session_id,
                updates={
                    "authorized_plan_version": curr_version,
                    "authorization": {
                        "pending": False,
                        "granted": True,
                        "plan_version": curr_version,
                        "authorized_for_version": curr_version,
                        "authorized_at": datetime.now().isoformat(),
                        "revoked_reason": None,
                    },
                    "rpa_execution": rpa_info_copy,
                    "booking_history": booking_history,
                },
                status="BOOKING_CONFIRMED",
            )

    return {
        "intent": "BOOKING",
        "reply": reply,
        "status": "success",
        "booking_id": booking_id,
        "plan_version": curr_version,
        "rpa_info": rpa_info,
        "session_id": session_id,
        "requirements": req,
        "request": req,
        "selected_options": selected_options,
        "budget_evaluation": budget_eval,
        "plan": None,
        "itinerary": None,
        "last_tourism_place": state.get("last_tourism_place"),
        "last_itinerary_context": state.get("last_itinerary_context"),
        "tool_execution": {
            "tool": "execute_rpa_booking_tool",
            "status": "success",
            "results": rpa_info,
        },
    }


# -----------------------------------------------------------------------------
# 6. Main Orchestrator Dispatcher
# -----------------------------------------------------------------------------

def _finalize_turn_response(res: Dict[str, Any], sid: str, default_intent: str = "UNKNOWN") -> Dict[str, Any]:
    """Helper to ensure session_id is present and the assistant reply is recorded in history."""
    res["session_id"] = sid
    res.setdefault("action", None)
    res.setdefault("hotel", None)
    res.setdefault("recommendation", None)
    res.setdefault("budget_evaluation", None)
    res.setdefault("knowledge_sources", [])
    res.setdefault("destination_images", [])
    res.setdefault("matched_destination", None)
    res.setdefault("status", "SUCCESS")
    reply = res.get("reply", "")
    intent = res.get("intent", default_intent)
    plan_version = res.get("plan_version")
    status = res.get("status")

    # Ensure selected_option is populated for legacy/API compatibility if selected_options is present
    if res.get("selected_options") and not res.get("selected_option"):
        res["selected_option"] = res["selected_options"]

    # Ensure response_source and knowledge_source are present
    if "response_source" not in res or "knowledge_source" not in res:
        if intent == "TOURISM":
            res.setdefault("source", "local_fallback")
            res.setdefault("response_source", "conversation_agent")
            res.setdefault("knowledge_source", "local_fallback")
        elif intent == "WEATHER":
            res.setdefault("source", "weather_service")
            res.setdefault("response_source", "weather_service")
            res.setdefault("knowledge_source", "weather_service")
        elif intent in ("AVAILABILITY", "BOOKING"):
            res.setdefault("source", "rpa_playwright")
            res.setdefault("response_source", "rpa_agent")
            res.setdefault("knowledge_source", "rpa_playwright")
        elif intent == "ITINERARY":
            res.setdefault("source", "itinerary_agent")
            res.setdefault("response_source", "itinerary_agent")
            res.setdefault("knowledge_source", "itinerary_templates")
        else:
            res.setdefault("source", "trip_orchestrator")
            res.setdefault("response_source", "conversation_agent")
            res.setdefault("knowledge_source", "local_catalog")

    # Guard: Non-tourism responses must NEVER have knowledge_source="atlas"
    if intent != "TOURISM" and res.get("knowledge_source") == "atlas":
        res["knowledge_source"] = "local_catalog"

    meta = {}
    if intent:
        meta["intent"] = intent
    if plan_version is not None:
        meta["plan_version"] = plan_version
    if status:
        meta["status"] = status
    if res.get("source"):
        meta["source"] = res["source"]
    if res.get("response_source"):
        meta["response_source"] = res["response_source"]
    if res.get("knowledge_source"):
        meta["knowledge_source"] = res["knowledge_source"]
    if res.get("destination_images"):
        meta["destination_images"] = res["destination_images"]
    if res.get("matched_destination"):
        meta["matched_destination"] = res["matched_destination"]

    # Size-bounded structured card payload for safe cold-reload restoration
    rec = res.get("recommendation")
    if isinstance(rec, dict) and (rec.get("profile") or rec.get("approach_bullets") or rec.get("title")):
        meta["recommendation"] = {
            "title": str(rec.get("title", "YOUR PERSONALIZED YATRA PLAN")),
            "profile": rec.get("profile", {}),
            "approach_bullets": [str(b) for b in rec.get("approach_bullets", rec.get("bullets", []))][:5],
            "suggested_places": [
                {
                    "name": str(p.get("name", "")),
                    "category": str(p.get("category", "")),
                    "distance": str(p.get("distance", "")),
                    "description": str(p.get("description", ""))[:200],
                    "image": str(p.get("image", "")),
                }
                for p in (rec.get("suggested_places") or rec.get("places") or [])[:4]
                if isinstance(p, dict)
            ],
            "reasoning": str(rec.get("reasoning", ""))[:500],
            "budget_note": str(rec.get("budget_note", ""))[:200],
        }

    infeasible = res.get("infeasible_places")
    if not infeasible and isinstance(res.get("plan"), dict):
        infeasible = res.get("plan", {}).get("infeasible_places")
    if infeasible and isinstance(infeasible, list):
        meta["infeasible_places"] = infeasible[:10]

    feasible = res.get("feasible_places")
    if not feasible and isinstance(res.get("plan"), dict):
        feasible = res.get("plan", {}).get("feasible_places")
    if feasible and isinstance(feasible, list):
        meta["feasible_places"] = feasible[:10]

    req = res.get("request") or res.get("requirements")
    if isinstance(req, dict):
        meta["request"] = {
            "pax": req.get("pax"),
            "group_type": req.get("group_type"),
            "duration_days": req.get("duration_days"),
            "travel_style": req.get("travel_style"),
            "trip_focus": req.get("trip_focus"),
            "total_budget": req.get("total_budget"),
        }

    plan_data = res.get("plan")
    if isinstance(plan_data, dict) and plan_data.get("status"):
        meta["plan"] = {"status": plan_data.get("status")}

    try:
        _prev_a = session_store.get_messages(sid)
        if not _prev_a or _prev_a[-1].get("role") != "assistant" or _prev_a[-1].get("content") != reply:
            session_store.add_message(
                session_id=sid,
                role="assistant",
                content=reply,
                metadata=meta or None,
            )
    except Exception as exc:
        logger.warning("Failed to persist assistant message to SQLite for session %s: %s", sid, type(exc).__name__)

    try:
        from utils.provenance import attach_provenance_to_response
        res = attach_provenance_to_response(res)
    except Exception as prov_err:
        logger.warning("Failed to attach provenance to orchestrator response: %s", prov_err)
        res.setdefault("source_provenance", [])
        res.setdefault("live_sources", [])

    return res


def handle_availability_query(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
    llm: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Week 7 Agent-RPA Integration (Corrected Live Flow):
    Delegates natural-language availability checks to the LangChain LLM tool-calling agent
    (availability_agent.run_availability_agent) when available, and safely falls back
    to deterministic extraction when offline or when the LLM/API is unavailable.
    """
    sid = session["session_id"]
    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if current_request:
        req.update(current_request)

    from agents import availability_agent

    # 1. Delegate to the LangChain tool-calling agent
    agent_res = availability_agent.run_availability_agent(
        user_query=user_text,
        llm=llm,
        context=state,
        headless=True,
    )

    exec_mode = agent_res.get("execution_mode", "deterministic_fallback")
    extracted_params = agent_res.get("extracted_params") or {}

    # 2. Missing date check -> request clarification, do not fabricate
    if agent_res.get("status") == "NEEDS_INFO" or (not agent_res.get("tool_selected") and extracted_params.get("missing_date")):
        prompt = agent_res.get("reply") or conversation_agent.format_missing_date_prompt()
        session_store.update_session(
            sid,
            updates={"awaiting_availability_date": True},
            status="AWAITING_INPUT",
        )
        return {
            "intent": "AVAILABILITY",
            "status": "NEEDS_INFO",
            "reply": prompt,
            "extracted_params": extracted_params if extracted_params else {"missing_date": True, "date": None},
            "availability_result": None,
            "execution_mode": exec_mode,
            "plan": {"status": "NEEDS_INFO", "message": prompt},
            "request": req,
            "itinerary": state.get("itinerary"),
        }

    # 3. Invalid date check -> reject with explanation
    if agent_res.get("status") == "INVALID_INPUT" or extracted_params.get("invalid_date"):
        prompt = agent_res.get("reply")
        return {
            "intent": "AVAILABILITY",
            "status": "INVALID_INPUT",
            "reply": prompt,
            "extracted_params": extracted_params,
            "availability_result": None,
            "execution_mode": exec_mode,
            "plan": {"status": "NEEDS_INFO", "message": prompt},
            "request": req,
            "itinerary": state.get("itinerary"),
        }

    # 4. Unsupported category check -> inform user of valid categories
    if agent_res.get("status") == "UNSUPPORTED_CATEGORY" or extracted_params.get("unsupported_category"):
        prompt = agent_res.get("reply")
        return {
            "intent": "AVAILABILITY",
            "status": "UNSUPPORTED_CATEGORY",
            "reply": prompt,
            "extracted_params": extracted_params,
            "availability_result": None,
            "execution_mode": exec_mode,
            "plan": {"status": "NEEDS_INFO", "message": prompt},
            "request": req,
            "itinerary": state.get("itinerary"),
        }

    # 5. Tool selected and executed
    tool_result = agent_res.get("tool_result") or {}
    tool_args = agent_res.get("tool_args") or {}
    date_val = tool_args.get("date")
    cat_val = tool_args.get("category")
    reply = agent_res.get("reply")

    # 6. Update session state (contextual follow-ups, audit history)
    # Read-only check: does NOT alter plan_version or human authorization
    session_store.update_session(
        sid,
        updates={
            "last_availability_date": date_val,
            "last_availability_category": cat_val,
            "last_availability_result": tool_result,
            "awaiting_availability_date": False,
        },
    )

    tool_status = "success"
    if tool_result.get("handover_required") or tool_result.get("status") == "HANDOVER_REQUIRED":
        tool_status = "handover"
    elif tool_result.get("status") in ("FAILED", "ERROR"):
        tool_status = "error"

    final_params = extracted_params if extracted_params else {
        "date": date_val,
        "category": cat_val,
        "missing_date": False,
        "invalid_date": False,
        "unsupported_category": False,
    }

    return {
        "intent": "AVAILABILITY",
        "status": "SUCCESS" if tool_status == "success" else tool_status.upper(),
        "reply": reply,
        "availability_result": tool_result,
        "extracted_params": final_params,
        "execution_mode": exec_mode,
        "tool_execution": {
            "tool": agent_res.get("tool_name", "check_yatra_availability_tool"),
            "status": tool_status,
            "results": tool_result,
            "execution_mode": exec_mode,
        },
        "plan": None,
        "request": req,
        "itinerary": state.get("itinerary"),
    }


def handle_train_search_intent(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from services import railway_schedules as rs
    req = current_request or session.get("state", {}).get("requirements", {})
    t_lower = (user_text or "").lower()

    extracted_origin = None
    for city in ["delhi", "new delhi", "chandigarh", "amritsar", "haridwar", "kanpur", "lucknow", "mumbai", "pune", "varanasi", "bhopal", "patna"]:
        if city in t_lower:
            extracted_origin = city.title()
            break
    if not extracted_origin and req.get("origin"):
        extracted_origin = req.get("origin")

    if not extracted_origin:
        m = re.search(r"\bfrom\s+([a-zA-Z\s]+?)(?:\s+to|\s+train|\s*$)", t_lower)
        if m:
            cand = m.group(1).strip()
            if cand and cand not in ("train", "trains", "katra", "jammu", "the"):
                extracted_origin = cand.title()

    if not extracted_origin:
        reply = (
            "🚆 **Train Search to Shri Mata Vaishno Devi Katra (SVDK)**\n\n"
            "Which departure city or station would you like to search trains from? "
            "(e.g., **New Delhi**, **Chandigarh**, **Amritsar**, **Haridwar**, or **Kanpur**)"
        )
        return {
            "intent": "TRAIN_SEARCH",
            "status": "NEEDS_INFO",
            "reply": reply,
            "session_id": session.get("session_id"),
            "request": req,
        }

    trains_result = rs.search_curated_schedules(origin=extracted_origin, destination="SVDK")
    direct_trains = trains_result[0] if isinstance(trains_result, tuple) and trains_result else []

    # Attempt live train route search via UnifiedLiveDataManager if configured
    live_trains = []
    live_provider_name = None
    try:
        from services.live_data.manager import get_live_data_manager
        from services.live_data.contracts import ProviderRequest, DataDomain
        mgr = get_live_data_manager()
        req_live = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location=extracted_origin,
            params={"action": "train_search", "origin": extracted_origin, "destination": "SVDK"},
        )
        res_live = mgr.execute_request(req_live, provider_id="live_railway_telemetry_adapter")
        if res_live.is_success and isinstance(res_live.data, dict) and res_live.data.get("trains"):
            live_trains = res_live.data.get("trains", [])
            live_provider_name = res_live.data.get("provider", "Live Indian Railways Gateway")
    except Exception as exc:
        logger.debug("Live railway query skipped: %s", exc)

    if live_trains:
        lines = [
            f"🚆 **Available Trains from {extracted_origin} to Shri Mata Vaishno Devi Katra (SVDK)**\n",
            f"📡 *Live train schedules retrieved via {live_provider_name}:*\n",
        ]
        for t in live_trains[:6]:
            days = t.get("days_of_operation")
            days_str = ", ".join(days) if isinstance(days, list) and days else "Daily"
            classes = t.get("travel_classes")
            classes_str = "/".join(classes) if isinstance(classes, list) and classes else "Standard"
            dep = t.get("departure_time", "Scheduled")
            arr = t.get("arrival_time", "Scheduled")
            dur = f"{t.get('duration_hours')} hrs" if t.get("duration_hours") else f"{t.get('duration_minutes')} mins"
            lines.append(
                f"• **{t.get('train_number')} - {t.get('train_name')}**\n"
                f"  - **Departure:** {dep} ({t.get('origin_station_name') or extracted_origin}) → **Arrival:** {arr} ({t.get('destination_station_name') or 'SVDK'})\n"
                f"  - **Duration:** {dur} | **Runs:** {days_str} | **Classes:** {classes_str}\n"
            )
        lines.append(
            "📌 **Official IRCTC Booking Note:**\n"
            "Advance bookings open 120 days prior on the official IRCTC portal ([irctc.co.in](https://www.irctc.co.in)). "
            "Tatkal quota opens at 10:00 AM (AC) and 11:00 AM (Non-AC) one day prior to departure."
        )
        reply = "\n".join(lines)
        return {
            "intent": "TRAIN_SEARCH",
            "status": "SUCCESS",
            "reply": reply,
            "session_id": session.get("session_id"),
            "request": req,
            "trains": live_trains[:6],
        }

    if not direct_trains:
        trains_result_jat = rs.search_curated_schedules(origin=extracted_origin, destination="JAT")
        direct_trains = trains_result_jat[0] if isinstance(trains_result_jat, tuple) and trains_result_jat else []

    if direct_trains:
        lines = [
            f"🚆 **Available Trains from {extracted_origin} to Shri Mata Vaishno Devi Katra (SVDK)**\n",
            "*Curated scheduled departures direct to Katra base camp:*\n"
        ]
        for t in direct_trains[:5]:
            days_str = ", ".join(t.days_of_operation) if t.days_of_operation else "Daily"
            classes_str = "/".join(t.travel_classes) if t.travel_classes else "Standard"
            lines.append(
                f"• **{t.train_number} - {t.train_name}**\n"
                f"  - **Departure:** {t.departure_time} ({t.origin_station_name or extracted_origin}) → **Arrival:** {t.arrival_time} ({t.destination_station_name})\n"
                f"  - **Duration:** {t.duration_hours} hrs | **Runs:** {days_str} | **Classes:** {classes_str}\n"
                f"  - **Notes:** {t.notes or 'Direct connectivity'}\n"
            )
        lines.append(
            "📌 **Official Booking Note:**\n"
            "Advance bookings open 120 days prior on the official IRCTC portal ([irctc.co.in](https://www.irctc.co.in)). "
            "Tatkal quota opens at 10:00 AM (AC) and 11:00 AM (Non-AC) one day prior to departure."
        )
        reply = "\n".join(lines)
    else:
        reply = (
            f"🚆 **Train Connectivity from {extracted_origin} to Katra (SVDK)**\n\n"
            f"For travelers from {extracted_origin}, direct or connecting rail connections typically run via "
            f"**New Delhi (NDLS)** or **Jammu Tawi (JAT)**:\n\n"
            f"• **From New Delhi:** 22439 Vande Bharat Express (06:00), 22477 Vande Bharat Express (15:00), 22461 Shri Shakti AC Express (19:05).\n"
            f"• **Connecting Note:** Regular express trains and connecting Vande Bharat rakes operate daily from New Delhi to SVDK.\n\n"
            f"Please check real-time seat availability and booking on the official IRCTC portal ([irctc.co.in](https://www.irctc.co.in))."
        )

    return {
        "intent": "TRAIN_SEARCH",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
        "request": req,
        "trains": [
            {
                "train_number": t.train_number,
                "train_name": t.train_name,
                "departure_time": t.departure_time,
                "arrival_time": t.arrival_time,
                "days_of_operation": t.days_of_operation,
                "travel_classes": t.travel_classes,
                "duration_hours": t.duration_hours,
            }
            for t in direct_trains[:5]
        ] if direct_trains else [],
    }


def handle_train_schedule_intent(
    user_text: str,
    session: Dict[str, Any],
) -> Dict[str, Any]:
    from services import railway_schedules as rs
    tl = (user_text or "").lower()

    is_vande_bharat = "vande bharat" in tl or "22439" in tl or "22440" in tl or "22477" in tl or "22478" in tl
    is_shri_shakti = "shri shakti" in tl or "22461" in tl or "22462" in tl
    is_uttar_sampark = "uttar sampark" in tl or "12445" in tl or "12446" in tl

    if is_vande_bharat or (not is_shri_shakti and not is_uttar_sampark):
        reply = (
            "🚆 **Vande Bharat Express Timetable & Operating Schedule**\n\n"
            "**1. Train 22439 (New Delhi → Shri Mata Vaishno Devi Katra - Morning Service):**\n"
            "• **Departure:** 06:00 AM (06:00) from New Delhi (NDLS)\n"
            "• **Intermediate Halts:** Ambala Cantt (08:10), Ludhiana Jn (09:19), Jalandhar Cantt (10:00), Pathankot Cantt (11:15), Jammu Tawi (12:43)\n"
            "• **Arrival:** 02:20 PM (14:20) at SMVD Katra (SVDK) — *Total Travel Time: 8h 20m*\n"
            "• **Operating Days:** Monday, Tuesday, Thursday, Friday, Saturday, Sunday (**Weekly Off: Wednesday**; revised from original Tuesday maintenance)\n\n"
            "**2. Train 22440 (SMVD Katra → New Delhi - Return Rake):**\n"
            "• **Departure:** 02:55 PM (14:55) from SMVD Katra (SVDK)\n"
            "• **Intermediate Halts:** Jammu Tawi (16:10), Pathankot Cantt (17:29), Jalandhar Cantt (18:51), Ludhiana Jn (19:34), Ambala Cantt (20:54)\n"
            "• **Arrival:** 11:10 PM (23:10) at New Delhi (NDLS) — *Total Travel Time: 8h 15m*\n"
            "• **Operating Days:** Monday, Tuesday, Thursday, Friday, Saturday, Sunday (**Weekly Off: Wednesday**)\n\n"
            "**3. Train 22477 / 22478 (Second Afternoon Service via Udhampur):**\n"
            "• **22477 (NDLS → SVDK):** Departs NDLS at 03:00 PM (15:00), arrives Katra at 11:20 PM (23:20) (Operates 6 days a week, **Weekly Off: Wednesday**)\n"
            "• **22478 (SVDK → NDLS):** Departs Katra at 05:40 AM (05:40), arrives NDLS at 02:00 PM (14:00) (Operates 6 days a week, **Weekly Off: Wednesday**)\n\n"
            "ℹ️ **NTES & Official Reservation Advisory:**\n"
            "• Timetable reflects published Northern Railway Working Timetable schedules.\n"
            "• Real-time platform assignments and live GPS running telemetry are managed dynamically via the National Train Enquiry System (NTES / dial 139).\n"
            "• Official tickets can be booked through IRCTC ([irctc.co.in](https://www.irctc.co.in)). Catering is included in the fare."
        )
    elif is_shri_shakti:
        reply = (
            "🚆 **22461 / 22462 Shri Shakti AC Express Timetable**\n\n"
            "• **Train 22461 (New Delhi → SVDK):** Dep 19:05 (NDLS) → Arr 07:40 (SVDK) | **Daily Overnight Service**\n"
            "• **Train 22462 (SVDK → New Delhi):** Dep 23:00 (SVDK) → Arr 10:45 (NDLS) | **Daily Overnight Service**\n"
            "• **Major Halts:** Ambala Cantt, Ludhiana, Jalandhar Cantt, Pathankot Cantt, Jammu Tawi, Udhampur\n"
            "• **Classes:** 1A, 2A, 3A (Fully Air-Conditioned)\n\n"
            "ℹ️ *Live running status is tracked on NTES. Bookings via IRCTC.*"
        )
    else:
        reply = (
            "🚆 **12445 / 12446 Uttar Sampark Kranti Express Timetable**\n\n"
            "• **Train 12445 (New Delhi → SVDK):** Dep 20:50 (NDLS) → Arr 08:05 (SVDK) | **Daily Service**\n"
            "• **Train 12446 (SVDK → New Delhi):** Dep 19:55 (SVDK) → Arr 06:55 (NDLS) | **Daily Service**\n"
            "• **Classes:** 1A, 2A, 3A, SL\n\n"
            "ℹ️ *Live running status is tracked on NTES. Bookings via IRCTC.*"
        )

    return {
        "intent": "TRAIN_SCHEDULE",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
    }


def handle_live_train_status_intent(
    user_text: str,
    session: Dict[str, Any],
) -> Dict[str, Any]:
    from services.live_data.manager import get_live_data_manager
    from services.live_data.contracts import ProviderRequest, DataDomain
    import re

    tl = (user_text or "").lower()
    train_match = re.search(r"\b(22439|22440|22477|22478|22461|22462|12445|12446|\d{5})\b", tl)
    train_no = train_match.group(1) if train_match else None

    if not train_no:
        if "vande bharat" in tl:
            train_no = "22439"
        elif "shri shakti" in tl:
            train_no = "22461"
        elif "uttar sampark" in tl:
            train_no = "12445"
        else:
            train_no = "22439"

    mgr = get_live_data_manager()
    req = ProviderRequest(
        domain=DataDomain.TRANSPORT.value,
        location="SVDK",
        params={"action": "live_status", "train_number": train_no},
    )
    res = mgr.execute_request(req)

    if res.is_success and isinstance(res.data, dict) and res.data.get("live_status_available"):
        d = res.data
        train_name = d.get("train_name") or f"Train {train_no}"
        cur_station = d.get("current_station") or "In Transit"
        delay = d.get("delay_minutes", 0)
        status_txt = "🟢 On Time" if delay <= 5 else f"🟡 Delayed by {delay} mins"
        last_upd = d.get("last_updated", "Just now")
        provider_name = d.get("provider", "Live Railway Gateway")

        reply = (
            f"📡 **Live Running Telemetry: {train_no} ({train_name})**\n\n"
            f"• **Current Location:** {cur_station}\n"
            f"• **Live Status:** {status_txt}\n"
            f"• **Running Delay:** {delay} minutes\n"
            f"• **Last Telemetry Update:** {last_upd}\n"
            f"• **Source Provider:** {provider_name}\n\n"
            f"ℹ️ *Live tracking powered by upstream GPS/transponder telemetry. Confirm platform allocations upon arrival at station.*"
        )
    else:
        sched_res = handle_train_schedule_intent(f"schedule for {train_no}", session)
        reply = (
            f"📡 **Live Status Enquiry: Train {train_no}**\n\n"
            "⚠️ **Live GPS Telemetry Notice:**\n"
            "Real-time GPS running telemetry and live delay tracking require an active connection to the National Train Enquiry System (NTES) gateway via `RAILCORE_API_KEY` or `RAILWAY_API_KEY`. Currently operating in verified scheduled timetable mode.\n\n"
            + sched_res.get("reply", "")
        )

    return {
        "intent": "LIVE_TRAIN_STATUS",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
    }


def get_india_today() -> date:
    """Returns current date in Indian Standard Time (Asia/Kolkata, UTC+05:30)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata")).date()
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def _is_leap_year(year: int) -> bool:
    """Returns True if year is a leap year in the Gregorian calendar."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _resolve_next_feb_29(today: date) -> date:
    """Finds the next valid February 29 on or after today."""
    y = today.year
    while True:
        if _is_leap_year(y):
            candidate = date(y, 2, 29)
            if candidate >= today:
                return candidate
        y += 1


MONTHS_REGEX = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

INFINITIVE_VERBS = (
    r"^(?:stay|visit|pray|worship|travel|go|spend|relax|explore|attend|see|reach|celebrate|enjoy|book|check|do|get|take)\b"
)


def _parse_numeric_date(d_str: str) -> Tuple[Optional[str], Optional[date], Optional[str]]:
    """
    Parses a numeric date string in either ISO (YYYY-MM-DD, YYYY/MM/DD) or DMY (DD-MM-YYYY, DD/MM/YYYY) format.
    Returns: (iso_str, dt_val, error_message)
    """
    sep = '-' if '-' in d_str else '/'
    parts = d_str.split(sep)
    if len(parts[0]) == 4:
        fmt = f"%Y{sep}%m{sep}%d"
        fmt_name = "YYYY-MM-DD"
    else:
        fmt = f"%d{sep}%m{sep}%Y"
        fmt_name = "DD-MM-YYYY"
    try:
        dt = datetime.strptime(d_str, fmt).date()
        return dt.isoformat(), dt, None
    except ValueError:
        return None, None, f"The date '{d_str}' is invalid. Please provide a valid calendar date in {fmt_name} format."


def _clean_date_fragment(text: str) -> str:
    text = re.sub(r"^[.,;:\-\s]+|[.,;:\-\s]+$", "", text or "")
    text = re.sub(r"^(?:\b(?:date|on|for|is|from|to|at|by)\b|[:\-,;])+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[.,;:\-\s]+|[.,;:\-\s]+$", "", text)
    return text.strip()


def _find_all_dates_in_text(text: str) -> list:
    """Finds all explicit date occurrences (numeric, natural language, relative, Feb 29) in text."""
    if not text:
        return []
    found = []
    # 1. Numeric dates (ISO or DMY)
    for m in re.finditer(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", text):
        found.append((m.span(), m.group(1), "numeric"))

    # 2. Month name + day or day + Month name
    nl_pat = rf"\b(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s\-]+{MONTHS_REGEX}(?:[,\s\-]+(?:\d{{4}}))?\b|\b{MONTHS_REGEX}[\s\-]+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?(?:[,\s\-]+(?:\d{{4}}))?\b"
    for m in re.finditer(nl_pat, text, re.IGNORECASE):
        if not any(f[0][0] <= m.start() and f[0][1] >= m.end() for f in found):
            found.append((m.span(), m.group(0), "nl"))

    # 3. Relative
    for m in re.finditer(r"\b(?:day after tomorrow|tomorrow|tonight|today)\b", text, re.IGNORECASE):
        found.append((m.span(), m.group(0), "rel"))

    # 4. Feb 29
    for m in re.finditer(r"\b(?:29(?:th)?\s+feb(?:ruary)?|feb(?:ruary)?\s+29(?:th)?)\b", text, re.IGNORECASE):
        if not any(f[0][0] <= m.start() and f[0][1] >= m.end() for f in found):
            found.append((m.span(), m.group(0), "feb29"))

    found.sort(key=lambda x: x[0][0])
    return found


def _parse_single_date_fragment(
    text: str,
    today: date,
    ci_dt_for_ref: Optional[date] = None,
) -> Tuple[Optional[str], Optional[date], Optional[str]]:
    raw = _clean_date_fragment(text)
    if not raw:
        return None, None, "Check-out date was not specified after the range keyword. Please provide a valid check-out date."

    tl = raw.lower()

    # 1. Numeric date (ISO or DMY)
    m_num = re.search(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", raw)
    if m_num:
        iso_str, dt, err = _parse_numeric_date(m_num.group(1))
        return iso_str, dt, err

    # 2. Relative dates
    if "day after tomorrow" in tl:
        dt = today + timedelta(days=2)
        return dt.isoformat(), dt, None
    elif "tomorrow" in tl:
        dt = today + timedelta(days=1)
        return dt.isoformat(), dt, None
    elif "tonight" in tl or "today" in tl:
        dt = today
        return dt.isoformat(), dt, None

    # 3. February 29
    if re.search(r"\b(?:29(?:th)?\s+feb(?:ruary)?|feb(?:ruary)?\s+29(?:th)?)\b", raw, re.IGNORECASE):
        exp_year = _extract_explicit_date_year(raw)
        if exp_year is not None:
            if not _is_leap_year(exp_year):
                return None, None, f"February 29 is not a valid date in {exp_year} as it is not a leap year. Please provide a valid calendar date."
            dt = date(exp_year, 2, 29)
        else:
            if ci_dt_for_ref is not None:
                dt = _resolve_next_feb_29(ci_dt_for_ref + timedelta(days=1))
            else:
                dt = _resolve_next_feb_29(today)
        return dt.isoformat(), dt, None

    # 4. Natural language date
    if legacy_agent.has_explicit_date(raw):
        st_date, _ = legacy_agent._extract_date_range(raw)
        if not st_date:
            return None, None, f"Could not parse check-out date from '{raw}'. Please provide a valid check-out date (e.g., YYYY-MM-DD)."
        try:
            dt = datetime.strptime(st_date, "%Y-%m-%d").date()
        except ValueError:
            return None, None, f"Check-out date '{st_date}' is invalid. Please provide a valid calendar date."
        exp_year = _extract_explicit_date_year(raw)
        if exp_year is None:
            if ci_dt_for_ref is not None:
                try:
                    dt = dt.replace(year=ci_dt_for_ref.year)
                except ValueError:
                    dt = _resolve_next_feb_29(ci_dt_for_ref + timedelta(days=1))
                if dt <= ci_dt_for_ref:
                    try:
                        dt = dt.replace(year=ci_dt_for_ref.year + 1)
                    except ValueError:
                        dt = _resolve_next_feb_29(date(ci_dt_for_ref.year + 1, 1, 1))
            else:
                dt = _normalize_natural_date_year(dt, today)
        return dt.isoformat(), dt, None

    return None, None, f"Could not parse check-out date from '{raw}'. Please provide a valid check-out date (e.g., YYYY-MM-DD)."


def _extract_explicit_date_year(text: str) -> Optional[int]:
    """
    Extracts an explicit four-digit year that is directly part of a date expression.
    Ensures unrelated four-digit numbers elsewhere in the query (flight numbers like 6448,
    budgets like 2500, pin codes) are not falsely interpreted as the date's year.
    """
    if not text:
        return None

    # 1. DD Month YYYY (e.g., "15 Dec 2026", "15th December, 2026", "15-Dec-2026")
    m = re.search(rf"\b(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s\-]+{MONTHS_REGEX}[,\s\-]+(\d{{4}})\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 2. Month DD, YYYY (e.g., "Dec 15 2026", "December 15, 2026")
    m = re.search(rf"\b{MONTHS_REGEX}[\s\-]+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[,\s\-]+(\d{{4}})\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 3. YYYY-MM-DD or YYYY/MM/DD (e.g., "2026-12-15", "2026/12/15")
    m = re.search(r"\b(\d{4})[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])\b", text)
    if m:
        return int(m.group(1))

    # 4. DD-MM-YYYY or DD/MM/YYYY (e.g., "15-12-2026", "15/12/2026", "10-12-2026")
    m = re.search(r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/](?:0?[1-9]|1[0-2])[-/](\d{4})\b", text)
    if m:
        return int(m.group(1))

    # 5. Month in/of/for YYYY (e.g., "December of 2026")
    m = re.search(rf"\b{MONTHS_REGEX}\s+(?:in|of|for)\s+(\d{{4}})\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


def _normalize_natural_date_year(d: date, today: date) -> date:
    """
    Normalizes a date parsed without an explicit year to follow the Asia/Kolkata calendar:
    1. Sets year to today.year (in IST).
    2. If the date in today.year is already in the past, rolls over to today.year + 1.
    Handles leap-year/leap-day safely without unhandled ValueError.
    """
    target_year = today.year
    try:
        candidate = d.replace(year=target_year)
    except ValueError:
        return _resolve_next_feb_29(today)

    if candidate < today:
        try:
            candidate = candidate.replace(year=target_year + 1)
        except ValueError:
            return _resolve_next_feb_29(today)

    return candidate


def _detect_checkout_text(user_text: str, ci_span: Optional[Tuple[int, int]]) -> Tuple[bool, Optional[str]]:
    """
    Determines whether user_text contains an explicit check-out specification or date range.
    Returns (is_range_specified, checkout_text).
    - (True, checkout_text): A genuine range or check-out keyword was detected. If checkout_text is empty,
      it signals an incomplete range (e.g. 'from 15 Dec to', '15 Dec until', 'checkout').
    - (False, None): No genuine check-out expression was found (e.g. ordinary sentences like
      'I want to book...', 'travel to Katra on...', or 'to stay in Katra').
    """
    if not user_text:
        return False, None

    # 1. Explicit check-out keyword anywhere in query
    m_co = re.search(r"\b(?:check-?out|checkout)\s*(?:date|on|for|is|:)?\s*(.*?)(?=\bcheck-?in\b|$)", user_text, re.IGNORECASE)
    if m_co:
        raw_co = m_co.group(1).strip()
        raw_co = re.sub(r"^[.,;:\-]+|[.,;:\-]+$", "", raw_co).strip()
        return True, raw_co

    if not ci_span:
        return False, None

    before_ci = user_text[:ci_span[0]]
    after_ci = user_text[ci_span[1]:]

    # 2. until / till / through after check-in date
    m_until = re.search(r"^\s*[,-]?\s*(?:until|till|through)\s*(.*)$", after_ci, re.IGNORECASE)
    if m_until:
        raw_co = m_until.group(1).strip()
        raw_co = re.sub(r"^[.,;:\-]+|[.,;:\-]+$", "", raw_co).strip()
        return True, raw_co

    # 3. 'to' after check-in date
    m_to = re.search(r"^\s*[,-]?\s*to\s*(.*)$", after_ci, re.IGNORECASE)
    if not m_to:
        # Check if 'from' was before check-in and 'to' appears in after_ci
        if re.search(r"\bfrom\b", before_ci, re.IGNORECASE):
            m_to = re.search(r"\bto\s*(.*)$", after_ci, re.IGNORECASE)

    if m_to:
        raw_co = m_to.group(1).strip()
        raw_co = re.sub(r"^[.,;:\-]+|[.,;:\-]+$", "", raw_co).strip()
        if not raw_co:
            return True, ""
        # Do not mistake infinitive verbs ('to stay', 'to visit') for checkout dates
        if re.match(INFINITIVE_VERBS, raw_co, re.IGNORECASE):
            return False, None
        return True, raw_co

    return False, None


def _parse_explicit_checkout_date(
    co_text: str,
    ci_dt: date,
    st_date: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses and validates a check-out date from text following a check-out keyword
    (e.g., 'to', 'until', 'checkout', 'through').
    Returns (co_iso_str, error_message).
    """
    co_str, co_dt, co_err = _parse_single_date_fragment(co_text, get_india_today(), ci_dt)
    if co_err:
        return None, co_err
    if co_dt <= ci_dt:
        return None, f"Check-out date ({co_dt.isoformat()}) must be after check-in date ({st_date}). Please provide a valid date range."
    return co_str, None


def _extract_hotel_search_dates(
    user_text: str,
    req_data: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts check-in and check-out dates for hotel search.
    Returns: (check_in, check_out, error_message)
    Priority:
    1. Explicit dates in user_text (ISO YYYY-MM-DD, DD-MM-YYYY, relative phrases, February 29, or natural language)
    2. req_data.get("start_date") / req_data.get("end_date")
    3. None, None (signals live adapter to use its sensible default)
    """
    today = get_india_today()
    tl = (user_text or "").lower()

    # 0. Label handling & multiple date label detection
    ci_matches = list(re.finditer(r"\b(?:check-?in|checkin)\b", user_text or "", re.IGNORECASE))
    co_matches = list(re.finditer(r"\b(?:check-?out|checkout)\b", user_text or "", re.IGNORECASE))

    # 0a. Multiple repeated labels
    if len(ci_matches) > 1:
        return None, None, "Multiple check-in dates were specified in your request. Please specify a single check-in date."
    if len(co_matches) > 1:
        return None, None, "Multiple check-out dates were specified in your request. Please specify a single check-out date."

    # 0b. Both check-in and checkout labels present
    if ci_matches and co_matches:
        m_ci = ci_matches[0]
        m_co = co_matches[0]

        if m_ci.start() < m_co.start():
            before_text = user_text[:m_ci.start()]
            ci_raw = user_text[m_ci.end():m_co.start()]
            co_raw = user_text[m_co.end():]
        else:
            before_text = user_text[:m_co.start()]
            co_raw = user_text[m_co.end():m_ci.start()]
            ci_raw = user_text[m_ci.end():]

        # Extra conflicting date detection
        if _find_all_dates_in_text(before_text):
            return None, None, "Multiple conflicting dates were detected in your request. Please specify clear check-in and check-out dates."
        if len(_find_all_dates_in_text(ci_raw)) > 1 or len(_find_all_dates_in_text(co_raw)) > 1:
            return None, None, "Multiple conflicting dates were detected in your request. Please specify clear check-in and check-out dates."

        clean_ci = _clean_date_fragment(ci_raw)
        clean_co = _clean_date_fragment(co_raw)

        if not clean_ci:
            return None, None, "Check-in date was not specified after the check-in keyword. Please provide a valid check-in date."
        if not clean_co:
            return None, None, "Check-out date was not specified after the range keyword. Please provide a valid check-out date."

        ci_str, ci_dt, ci_err = _parse_single_date_fragment(clean_ci, today)
        if ci_err:
            return None, None, ci_err
        if ci_dt < today:
            return None, None, f"Check-in date ({ci_str}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future date."

        co_str, co_dt, co_err = _parse_single_date_fragment(clean_co, today, ci_dt)
        if co_err:
            return None, None, co_err
        if co_dt <= ci_dt:
            return None, None, f"Check-out date ({co_str}) must be after check-in date ({ci_str}). Please provide a valid date range."

        return ci_str, co_str, None

    # 0c. Standalone checkout label (checkout present, NO check-in label)
    if co_matches and not ci_matches:
        m_co = co_matches[0]
        before_co = user_text[:m_co.start()]
        after_co = user_text[m_co.end():]
        dates_before = _find_all_dates_in_text(before_co)
        if not dates_before:
            # Standalone checkout label without preceding check-in date!
            session_ci = req_data.get("start_date")
            clean_co = _clean_date_fragment(after_co)
            if not clean_co:
                return None, None, "Check-out date was not specified after the range keyword. Please provide a valid check-out date."

            if not session_ci:
                return None, None, "Check-out date was specified without a check-in date. A check-in date is required. Please provide a check-in date."

            try:
                ci_dt = datetime.strptime(session_ci, "%Y-%m-%d").date()
            except ValueError:
                return None, None, f"Invalid session check-in date: '{session_ci}'. Expected YYYY-MM-DD format."
            if ci_dt < today:
                return None, None, f"Saved trip check-in date ({session_ci}) is in the past (today is {today.isoformat()} IST). Please specify an upcoming date in your query."

            co_str, co_dt, co_err = _parse_single_date_fragment(clean_co, today, ci_dt)
            if co_err:
                return None, None, co_err
            if co_dt <= ci_dt:
                return None, None, f"Check-out date ({co_str}) must be after check-in date ({session_ci}). Please provide a valid date range."
            return session_ci, co_str, None

    # 1. Direct explicit numeric calendar formats in user_text (unified ISO and DMY in textual order):
    raw_num_matches = list(re.finditer(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", user_text or ""))
    if raw_num_matches:
        if len(raw_num_matches) > 2:
            return None, None, "Multiple conflicting dates were detected in your request. Please specify clear check-in and check-out dates."

        validated_dates = []
        for m in raw_num_matches:
            d = m.group(1)
            iso_str, dt_val, err = _parse_numeric_date(d)
            if err:
                return None, None, err
            validated_dates.append((iso_str, dt_val, m.span()))

        if validated_dates[0][1] < today:
            return None, None, f"Check-in date ({validated_dates[0][0]}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future date."

        if len(validated_dates) >= 2:
            ci_str, ci_dt, _ = validated_dates[0]
            co_str, co_dt, _ = validated_dates[1]
            if co_dt <= ci_dt:
                return None, None, f"Check-out date ({co_str}) must be after check-in date ({ci_str}). Please provide a valid date range."
            return ci_str, co_str, None
        else:
            ci_str, ci_dt, ci_span = validated_dates[0]
            is_rng, co_text = _detect_checkout_text(user_text, ci_span)
            if is_rng:
                co_str, co_err = _parse_explicit_checkout_date(co_text, ci_dt, ci_str)
                if co_err:
                    return None, None, co_err
                return ci_str, co_str, None
            return ci_str, (ci_dt + timedelta(days=1)).isoformat(), None

    # 2. Relative dates evaluated in India Standard Time
    rel_match = None
    st_date_val = None
    if "day after tomorrow" in tl:
        st_date_val = today + timedelta(days=2)
        rel_match = re.search(r"\bday after tomorrow\b", user_text or "", re.IGNORECASE)
    elif "tomorrow" in tl:
        st_date_val = today + timedelta(days=1)
        rel_match = re.search(r"\btomorrow\b", user_text or "", re.IGNORECASE)
    elif "tonight" in tl or "today" in tl:
        st_date_val = today
        rel_match = re.search(r"\b(?:tonight|today)\b", user_text or "", re.IGNORECASE)

    if st_date_val is not None:
        rel_span = rel_match.span() if rel_match else None
        is_rng, co_text = _detect_checkout_text(user_text, rel_span)
        if is_rng:
            co_str, co_err = _parse_explicit_checkout_date(co_text, st_date_val, st_date_val.isoformat())
            if co_err:
                return None, None, co_err
            return st_date_val.isoformat(), co_str, None
        return st_date_val.isoformat(), (st_date_val + timedelta(days=1)).isoformat(), None

    # 3. Explicit February 29 handling
    m_feb = re.search(r"\b(?:29(?:th)?\s+feb(?:ruary)?|feb(?:ruary)?\s+29(?:th)?)\b", user_text or "", re.IGNORECASE)
    if m_feb:
        exp_year = _extract_explicit_date_year(user_text)
        if exp_year is not None:
            if not _is_leap_year(exp_year):
                return None, None, f"February 29 is not a valid date in {exp_year} as it is not a leap year. Please provide a valid calendar date."
            ci_dt = date(exp_year, 2, 29)
            if ci_dt < today:
                return None, None, f"Check-in date ({ci_dt.isoformat()}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future date."
        else:
            ci_dt = _resolve_next_feb_29(today)

        st_date = ci_dt.isoformat()
        is_rng, co_text = _detect_checkout_text(user_text, m_feb.span())
        if is_rng:
            co_str, co_err = _parse_explicit_checkout_date(co_text, ci_dt, st_date)
            if co_err:
                return None, None, co_err
            return st_date, co_str, None
        return st_date, (ci_dt + timedelta(days=1)).isoformat(), None

    # 4. Natural language dates in user_text (e.g., "15 December 2026", "next week")
    if legacy_agent.has_explicit_date(user_text):
        st_date, _ = legacy_agent._extract_date_range(user_text)
        if not st_date:
            return None, None, "Could not parse the date specified in your request. Please provide a valid date (e.g., YYYY-MM-DD)."

        try:
            ci_dt = datetime.strptime(st_date, "%Y-%m-%d").date()
        except ValueError:
            return None, None, f"The date '{st_date}' is invalid. Please provide a valid calendar date in YYYY-MM-DD format."

        exp_year = _extract_explicit_date_year(user_text)

        # Date-aware year normalization
        if exp_year is None:
            ci_dt = _normalize_natural_date_year(ci_dt, today)
            st_date = ci_dt.isoformat()

        if ci_dt < today:
            return None, None, f"Check-in date ({st_date}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future date."

        m_nl = re.search(rf"\b(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?[\s\-]+{MONTHS_REGEX}(?:[,\s\-]+(?:\d{{4}}))?\b", user_text, re.IGNORECASE)
        if not m_nl:
            m_nl = re.search(rf"\b{MONTHS_REGEX}[\s\-]+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?(?:[,\s\-]+(?:\d{{4}}))?\b", user_text, re.IGNORECASE)
        ci_span = m_nl.span() if m_nl else None

        is_rng, co_text = _detect_checkout_text(user_text, ci_span)
        if is_rng:
            co_str, co_err = _parse_explicit_checkout_date(co_text, ci_dt, st_date)
            if co_err:
                return None, None, co_err
            return st_date, co_str, None
        else:
            return st_date, (ci_dt + timedelta(days=1)).isoformat(), None

    # 5. Session requirements (validate both check-in and check-out independently and check past dates)
    check_in = req_data.get("start_date")
    check_out = req_data.get("end_date")
    if check_in:
        try:
            ci_dt = datetime.strptime(check_in, "%Y-%m-%d").date()
        except ValueError:
            return None, None, f"Invalid session check-in date: '{check_in}'. Expected YYYY-MM-DD format."

        if ci_dt < today:
            return None, None, f"Saved trip check-in date ({check_in}) is in the past (today is {today.isoformat()} IST). Please specify an upcoming date in your query."

        if check_out:
            try:
                co_dt = datetime.strptime(check_out, "%Y-%m-%d").date()
            except ValueError:
                return None, None, f"Invalid session check-out date: '{check_out}'. Expected YYYY-MM-DD format."

            if co_dt <= ci_dt:
                return None, None, f"Check-out date ({check_out}) must be after check-in date ({check_in})."
            return check_in, check_out, None
        else:
            return check_in, (ci_dt + timedelta(days=1)).isoformat(), None
    elif check_out:
        return None, None, f"Invalid session date configuration: saved check-out date ({check_out}) is present without a check-in date. Please specify your check-in date in your query."

    return None, None, None


def _extract_flight_search_date(
    user_text: str,
    req_data: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts travel date for flight search.
    Returns: (travel_date, error_message)
    Priority:
    1. Explicit date in user_text (ISO YYYY-MM-DD, DD-MM-YYYY, relative phrases, February 29, or natural language)
    2. req_data.get("start_date")
    3. None (signals live flight adapter to use its sensible default)
    """
    today = get_india_today()
    tl = (user_text or "").lower()

    # 1. Direct explicit numeric calendar formats in user_text (unified ISO and DMY in textual order):
    raw_num_matches = re.findall(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", user_text or "")
    if raw_num_matches:
        d = raw_num_matches[0]
        iso_str, dt_val, err = _parse_numeric_date(d)
        if err:
            return None, err.replace("The date", "The travel date")

        if dt_val < today:
            return None, f"Travel date ({iso_str}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future departure date."
        return iso_str, None

    # 2. Relative dates evaluated in India Standard Time
    if "day after tomorrow" in tl:
        return (today + timedelta(days=2)).isoformat(), None
    elif "tomorrow" in tl:
        return (today + timedelta(days=1)).isoformat(), None
    elif "tonight" in tl or "today" in tl:
        return today.isoformat(), None

    # 3. Explicit February 29 handling
    is_feb_29 = bool(re.search(r"\b(?:29(?:th)?\s+feb(?:ruary)?|feb(?:ruary)?\s+29(?:th)?)\b", user_text or "", re.IGNORECASE))
    if is_feb_29:
        exp_year = _extract_explicit_date_year(user_text)
        if exp_year is not None:
            if not _is_leap_year(exp_year):
                return None, f"February 29 is not a valid date in {exp_year} as it is not a leap year. Please provide a valid calendar date."
            dt_val = date(exp_year, 2, 29)
            if dt_val < today:
                return None, f"Travel date ({dt_val.isoformat()}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future departure date."
        else:
            dt_val = _resolve_next_feb_29(today)
        return dt_val.isoformat(), None

    # 4. Natural language dates in user_text
    if legacy_agent.has_explicit_date(user_text):
        st_date, _ = legacy_agent._extract_date_range(user_text)
        if not st_date:
            return None, "Could not parse the departure date specified in your request. Please use YYYY-MM-DD format."
        try:
            dt_val = datetime.strptime(st_date, "%Y-%m-%d").date()
        except ValueError:
            return None, f"The travel date '{st_date}' is invalid. Please provide a valid calendar date in YYYY-MM-DD format."

        exp_year = _extract_explicit_date_year(user_text)

        # Date-aware year normalization
        if exp_year is None:
            dt_val = _normalize_natural_date_year(dt_val, today)
            st_date = dt_val.isoformat()

        if dt_val < today:
            return None, f"Travel date ({st_date}) cannot be in the past (today is {today.isoformat()} IST). Please provide a current or future departure date."
        return st_date, None

    # 5. Session requirements (validate and check past dates)
    travel_date = req_data.get("start_date")
    if travel_date:
        try:
            dt_val = datetime.strptime(travel_date, "%Y-%m-%d").date()
        except ValueError:
            return None, f"Invalid session travel date: '{travel_date}'. Expected YYYY-MM-DD format."

        if dt_val < today:
            return None, f"Saved trip departure date ({travel_date}) is in the past (today is {today.isoformat()} IST). Please specify an upcoming departure date in your query."
        return travel_date, None

    return None, None


def handle_hotel_search_intent(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from services.live_data.manager import get_live_data_manager
    from services.live_data.contracts import ProviderRequest, DataDomain
    import re

    tl = (user_text or "").lower()
    pax_match = re.search(r"\b(\d+)\s*(?:guests?|people|pax|persons?|adults?)\b", tl)
    guests = int(pax_match.group(1)) if pax_match else 2

    req_data = current_request or session.get("state", {}).get("requirements", {}) or {}
    check_in, check_out, date_err = _extract_hotel_search_dates(user_text, req_data)

    if date_err:
        return {
            "intent": "HOTEL_SEARCH",
            "status": "INVALID_DATE_RANGE",
            "reply": (
                f"⚠️ **Invalid Date Selection for Hotel Search**\n\n"
                f"{date_err} Please specify a valid date range for your Katra accommodation."
            ),
            "session_id": session.get("session_id"),
            "request": current_request or session.get("state", {}).get("requirements", {}),
        }

    mgr = get_live_data_manager()
    req = ProviderRequest(
        domain=DataDomain.ACCOMMODATION.value,
        location="Katra",
        params={
            "city": "Katra",
            "action": "hotel_search",
            "guests": guests,
            "check_in_date": check_in,
            "check_out_date": check_out,
        },
    )
    res = mgr.execute_request(req)

    if res.is_success and isinstance(res.data, dict) and res.data.get("properties") and res.data.get("live_status_available"):
        props = res.data.get("properties", [])
        ci_display = res.data.get("check_in", "Upcoming")
        co_display = res.data.get("check_out", "Next Day")
        prov_name = res.data.get("provider", "Live Hotels Gateway")

        hotel_lines = []
        for p in props[:5]:
            h_name = p.get("name", "Hotel")
            h_rate = p.get("rate_per_night", "Contact for price")
            h_rating = f"★ {p.get('overall_rating')}" if p.get("overall_rating") else "Verified"
            h_desc = p.get("description", "Hotel in Katra")
            hotel_lines.append(f"• **{h_name}** ({h_rating})\n  - **Rate:** {h_rate}/night | **City:** Katra\n  - *{h_desc}*")

        reply = (
            f"🏨 **Live Hotel Availability & Rates in Katra**\n\n"
            f"*Queried for {guests} guest(s) | Check-in: {ci_display} | Check-out: {co_display}*\n\n"
            + "\n\n".join(hotel_lines)
            + f"\n\nℹ️ **Live Pricing Source:** {prov_name}. Rates are subject to dynamic booking changes.\n"
            f"• Official Shrine Board Bhawans (Niharika, Kalika Dham, Trikuta Bhawan) can be reserved at [maavaishnodevi.org](https://www.maavaishnodevi.org)."
        )
    else:
        reply = (
            "🏨 **Verified Accommodations & Official Shrine Board Bhawans in Katra**\n\n"
            "Devotees visiting Shri Mata Vaishno Devi Ji have excellent staying options across Katra base camp and the trek route:\n\n"
            "**1. Official Shrine Board Bhawans (SMVDSB):**\n"
            "• **Niharika Complex:** Located right at Katra Bus Stand / Central Market. Features AC/Non-AC rooms, suites, and dormitory beds (₹150–₹1,200/night). Highly convenient for Yatra registration.\n"
            "• **Shakti Bhawan & Ashirwad Complex:** Located close to the bus stand; clean, subsidized pilgrim accommodation.\n"
            "• **Kalika Dham & Saraswati Dham:** Near Katra Railway Station, ideal for pilgrims arriving by train.\n"
            "• **Bhawans on the Track:** Main Bhawan Complex, Manokamana Bhawan, and Ardhkuwari Rest House.\n"
            "• *Booking:* Official Shrine Board rooms open online 60 days in advance at [maavaishnodevi.org](https://www.maavaishnodevi.org).\n\n"
            "**2. Recommended Katra Private Hotels:**\n"
            "• **Budget Stays (₹800 – ₹1,500/night):** Located around Jammu Road and Main Bazaar; clean rooms with Wi-Fi and hot water.\n"
            "• **Comfort / Mid-Range (₹1,800 – ₹3,500/night):** Located along Railway Road and Katra Bypass; often offer free shuttle pickup/drop to Banganga entry gate.\n"
            "• **Premium Hotels (₹4,000 – ₹7,500/night):** Luxury properties with full vegetarian dining, spa, and shrine-facing views.\n\n"
            "ℹ️ *Note: Live dynamic room rates and real-time inventory queries require a provider key (`SERPAPI_API_KEY` or `HOTEL_API_KEY`). Displaying verified Katra properties & official Shrine Board Bhawans above.*"
        )

    return {
        "intent": "HOTEL_SEARCH",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
        "request": current_request or session.get("state", {}).get("requirements", {}),
    }


def handle_flight_search_intent(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from services.live_data.manager import get_live_data_manager
    from services.live_data.contracts import ProviderRequest, DataDomain
    import re

    tl = (user_text or "").lower()

    # Destination detection (default to Jammu / IXJ for Vaishno Devi yatra)
    dest_city = "Jammu"
    if "srinagar" in tl or "sxr" in tl:
        dest_city = "Srinagar"

    # Origin detection
    extracted_origin = None
    origin_cities = [
        "delhi", "new delhi", "mumbai", "bangalore", "bengaluru", "hyderabad",
        "kolkata", "chennai", "pune", "ahmedabad", "chandigarh", "amritsar",
        "lucknow", "varanasi", "jaipur"
    ]
    for oc in origin_cities:
        if oc in tl:
            extracted_origin = oc.title()
            break

    req_data = current_request or session.get("state", {}).get("requirements", {}) or {}
    if not extracted_origin and req_data.get("origin"):
        extracted_origin = req_data.get("origin")

    if not extracted_origin:
        return {
            "intent": "FLIGHT_SEARCH",
            "status": "NEEDS_INFO",
            "reply": (
                f"✈️ **Flight Search Guidance to {dest_city} (IXJ/SXR)**\n\n"
                f"Please specify your **departure city** (e.g., Delhi, Mumbai, Bengaluru, Hyderabad, Kolkata) to search available flight schedules and airfares."
            ),
            "missing_fields": ["origin"],
            "options": [],
            "session_id": session.get("session_id"),
        }

    travel_date, date_err = _extract_flight_search_date(user_text, req_data)
    if date_err:
        return {
            "intent": "FLIGHT_SEARCH",
            "status": "INVALID_DATE",
            "reply": (
                f"✈️ **Invalid Travel Date for Flight Search**\n\n"
                f"{date_err} Please specify a valid departure date."
            ),
            "session_id": session.get("session_id"),
        }

    mgr = get_live_data_manager()
    req = ProviderRequest(
        domain=DataDomain.TRANSPORT.value,
        location=extracted_origin,
        params={
            "action": "flight_search",
            "mode": "flight",
            "origin": extracted_origin,
            "destination": dest_city,
            "travel_date": travel_date,
        },
    )

    # Attempt live flight gateway first
    res = mgr.execute_request(req, provider_id="live_flight_telemetry_adapter")
    is_live = res.is_success and isinstance(res.data, dict) and bool(res.data.get("flights"))

    if not is_live:
        # Graceful failover to curated flight schedules
        res = mgr.execute_request(req, provider_id="curated_flight_schedules")

    if res.is_success and isinstance(res.data, dict) and (res.data.get("flights") or res.data.get("schedules")):
        flights = res.data.get("flights") or res.data.get("schedules") or []
        prov_name = res.data.get("provider") or (
            "SerpApi Google Flights Gateway" if is_live else "Verified Airline Schedules"
        )
        travel_dt_display = res.data.get("travel_date") or travel_date or "Upcoming week"

        flight_lines = []
        for f in flights[:5]:
            fn = f.get("flight_no") or f.get("transport_no") or f.get("airline") or "Flight"
            fare_disp = f.get("price_inr") or (f"₹{f.get('price'):,}" if f.get("price") else None) or (f"₹{f.get('indicative_fare_min'):,}" if f.get('indicative_fare_min') else None) or "Check airline portal"
            dep_t = f.get("departure_time") or "Direct"
            arr_t = f.get("arrival_time") or "Direct"
            dur = f.get("duration_desc") or f.get("estimated_duration_desc") or "Direct"
            flight_lines.append(f"• **{fn}**\n  - **Fare:** {fare_disp} | **Departure:** {dep_t} → **Arrival:** {arr_t} ({dur})")

        transfer_note = (
            "ℹ️ **Ground Transfer to Katra Base Camp:**\n"
            "• **Jammu Airport (IXJ) to Katra:** ~50 km (~1.5 hours). Authorized Prepaid Taxis are available 24x7 outside arrivals (~₹1,500–₹2,000). Regular JKRTC direct AC/Deluxe buses depart from Jammu General Bus Stand."
            if dest_city == "Jammu" else
            "ℹ️ **Kashmir Valley Travel Note:**\n"
            "• **Srinagar Airport (SXR):** Serves Kashmir pilgrimage circuits. Road travel between Srinagar and Katra is via NH 44 (~240 km, ~6–7 hours across the Banihal Qazigund tunnel)."
        )

        source_label = "📡 **Live Google Flights Search**" if is_live else "📋 **Verified Curated Flight Schedules**"
        reply = (
            f"✈️ {source_label}: **{extracted_origin} → {dest_city}**\n\n"
            f"*Outbound travel date: {travel_dt_display} | Data Source: {prov_name}*\n\n"
            + "\n\n".join(flight_lines)
            + f"\n\n{transfer_note}\n\n"
            f"📌 *Direct airline bookings can be confirmed on airline websites or authorized travel portals.*"
        )
    else:
        reply = (
            f"✈️ **Flight Connectivity from {extracted_origin} to Jammu (IXJ)**\n\n"
            f"Direct and 1-stop flights operate daily between **{extracted_origin}** and **Jammu Airport (Satwari - IXJ)**:\n\n"
            f"• **Major Carriers:** IndiGo, Air India, SpiceJet, Akasa Air.\n"
            f"• **Average Flight Duration:** ~1h 15m to 1h 30m direct from Delhi.\n"
            f"• **Indicative Airfare:** ₹4,000 – ₹7,500 depending on advance booking.\n\n"
            f"ℹ️ *Live airfare queries require an active `SERPAPI_API_KEY` or `FLIGHT_API_KEY`. Displaying standard corridor timetable above.*"
        )

    return {
        "intent": "FLIGHT_SEARCH",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
        "flights": res.data.get("flights", []) if res.data else [],
    }


def handle_bus_search_intent(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from services.live_data.manager import get_live_data_manager
    from services.live_data.contracts import ProviderRequest, DataDomain
    from services.bus_schedules import search_curated_bus_schedules, compare_bus_and_train
    import re

    tl = (user_text or "").lower()

    # Known city names map
    city_map = {
        "katra": "Katra",
        "jammu": "Jammu",
        "udhampur": "Udhampur",
        "srinagar": "Srinagar",
        "delhi": "Delhi",
        "new delhi": "Delhi",
        "chandigarh": "Chandigarh",
        "amritsar": "Amritsar",
        "pathankot": "Pathankot",
        "jalandhar": "Jalandhar",
        "ludhiana": "Ludhiana",
        "shimla": "Shimla",
        "manali": "Manali",
        "dharamshala": "Dharamshala",
        "mandi": "Mandi",
    }

    extracted_origin = None
    extracted_dest = None

    # Check for connecting route pattern: "from X to Y and onward to Z"
    m_onward = re.search(r"\bfrom\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)\s+and\s+onward\s+to\s+([a-zA-Z\s]+)", tl)
    if m_onward:
        f_part = m_onward.group(1).strip()
        t_part = m_onward.group(3).strip()
        for k, v in city_map.items():
            if k in f_part and not extracted_origin:
                extracted_origin = v
            if k in t_part and not extracted_dest:
                extracted_dest = v

    # Check "from X to Y"
    if not (extracted_origin and extracted_dest):
        m_from_to = re.search(r"\bfrom\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)", tl)
        if m_from_to:
            f_part = m_from_to.group(1).strip()
            t_part = m_from_to.group(2).strip()
            t_part = re.sub(r"\b(buses|bus|timing|timings|schedule|fares?|today|tomorrow|and\s+onward.*)\b", "", t_part).strip()
            for k, v in city_map.items():
                if k in f_part and not extracted_origin:
                    extracted_origin = v
                if k in t_part and not extracted_dest:
                    extracted_dest = v

    # Check "to Y from X"
    if not (extracted_origin and extracted_dest):
        m_to_from = re.search(r"\bto\s+([a-zA-Z\s]+?)\s+from\s+([a-zA-Z\s]+)", tl)
        if m_to_from:
            t_part = m_to_from.group(1).strip()
            f_part = m_to_from.group(2).strip()
            f_part = re.sub(r"\b(buses|bus|timing|timings|schedule|fares?|today|tomorrow)\b", "", f_part).strip()
            for k, v in city_map.items():
                if k in t_part and not extracted_dest:
                    extracted_dest = v
                if k in f_part and not extracted_origin:
                    extracted_origin = v

    # Individual "to Y" or "from X" checks if one is missing
    if not extracted_dest:
        m_to = re.search(r"\bto\s+([a-zA-Z\s]+)", tl)
        if m_to:
            t_part = m_to.group(1).strip()
            for k, v in city_map.items():
                if k in t_part:
                    extracted_dest = v
                    break

    if not extracted_origin:
        m_from = re.search(r"\bfrom\s+([a-zA-Z\s]+)", tl)
        if m_from:
            f_part = m_from.group(1).strip()
            for k, v in city_map.items():
                if k in f_part:
                    extracted_origin = v
                    break

    # Check if origin was in current request context
    req_data = current_request or session.get("state", {}).get("requirements", {}) or {}
    if not extracted_origin and req_data.get("origin"):
        extracted_origin = req_data.get("origin")

    # Contextual defaults if still incomplete
    if "via jammu" in tl or "connecting" in tl:
        if not extracted_origin or extracted_origin.lower() in ("jammu", "katra"):
            extracted_origin = req_data.get("origin") or "Delhi"
            extracted_dest = "Katra"

    if not extracted_dest and not extracted_origin:
        extracted_origin = "Jammu"
        extracted_dest = "Katra"
    elif extracted_origin and not extracted_dest:
        if extracted_origin.lower() in ("katra",):
            extracted_dest = "Jammu"
        else:
            extracted_dest = "Katra"
    elif extracted_dest and not extracted_origin:
        if extracted_dest.lower() in ("katra",):
            extracted_origin = "Jammu"
        elif extracted_dest.lower() in ("jammu",):
            extracted_origin = "Katra"
        elif extracted_dest.lower() in ("srinagar", "udhampur"):
            extracted_origin = "Jammu"
        else:
            extracted_origin = "Jammu"

    travel_date = req_data.get("start_date")

    # 1. Check for Bus vs Train Comparison query
    if re.search(r"\b(compare|vs)\b", tl) and any(w in tl for w in ("train", "rail", "travel")):
        comp = compare_bus_and_train(origin=extracted_origin or "Delhi", destination=extracted_dest or "Katra")
        tr = comp["train"]
        bs = comp["bus"]
        ver_bs_cnt = bs.get('total_verified_services', bs.get('verified_services_count', 0))
        part_bs_cnt = bs.get('partially_verified_count', 0)
        tot_bs_cnt = bs.get('total_services', 0)
        reply = (
            f"🚄↔️🚌 **Comparative Analysis: Train vs Bus Travel ({comp['corridor']})**\n\n"
            f"**1. Train Options ({tr['flagship']} & {tr['overnight']})**\n"
            f"• ⏱️ **Duration:** {tr['duration']}\n"
            f"• 💰 **Fares:** {tr['fare_range']}\n"
            f"• 📑 **Fare Breakdown:** {tr.get('detailed_fares', tr['fare_range'])}\n"
            f"• 📚 **Source:** {tr.get('source_citation', 'Northern Railway WTT & IRCTC (Nov 2026)')}\n"
            f"• 🌐 **Booking:** {tr['booking_portal']}\n"
            f"• 👍 **Pros:** {', '.join(tr['pros'])}\n"
            f"• ⚠️ **Cons:** {', '.join(tr['cons'])}\n\n"
            f"**2. Bus Options ({tot_bs_cnt} Services: {ver_bs_cnt} Verified + {part_bs_cnt} Partially Verified / Indicative across Government & Private Fleets)**\n"
            f"• 🏛️ **Government Operators:** {', '.join(bs['government_operators'])}\n"
            f"• 🏢 **Private Operators:** {', '.join(bs['private_operators'])}\n"
            f"• 🚌 **Bus Categories:** {', '.join(bs['bus_types'])}\n"
            f"• ⏱️ **Duration:** {bs['duration']}\n"
            f"• 💰 **Indicative Fares:** {bs['fare_range']}\n"
            f"• 📑 **Tariff Breakdown:** {bs.get('detailed_fares', bs['fare_range'])}\n"
            f"• 📚 **Source:** {bs.get('source_citation', 'J&K STA & Carrier Tariffs (Nov 2026)')}\n"
            f"• 📍 **Boarding Points:** {', '.join(bs['boarding_points'])}\n"
            f"• 📍 **Dropping Points:** {', '.join(bs['dropping_points'])}\n"
            f"• 👍 **Pros:** {', '.join(bs['pros'])}\n"
            f"• ⚠️ **Cons:** {', '.join(bs['cons'])}\n\n"
            f"💡 **Pilgrim Recommendation:**\n"
            f"{comp['recommendation']}"
        )
        return {
            "intent": "BUS_SEARCH",
            "status": "SUCCESS",
            "reply": reply,
            "session_id": session.get("session_id"),
            "comparison": comp,
        }

    # 2. Extract multi-operator filter parameters
    operator_filter = None
    if any(p in tl for p in ("private and government", "government and private", "both")):
        operator_filter = None
    elif "private" in tl:
        operator_filter = "private"
    elif any(p in tl for p in ("government", "govt", "jksrtc", "hrtc", "prtc")):
        operator_filter = "government"

    bus_type_filter = None
    if "ac sleeper" in tl or "sleeper" in tl:
        bus_type_filter = "sleeper"
    elif "seater" in tl:
        bus_type_filter = "seater"
    elif "volvo" in tl:
        bus_type_filter = "volvo"
    elif "bharatbenz" in tl:
        bus_type_filter = "bharatbenz"

    direct_only = bool(re.search(r"\b(direct\s+buses\s+only|direct\s+only|direct\s+buses)\b", tl))
    connecting_requested = bool(re.search(r"\b(and\s+onward\s+to\s+katra|onward\s+to\s+katra|via\s+jammu|connecting)\b", tl))
    cheapest_requested = bool(re.search(r"\b(cheapest|lowest\s+fare|lowest\s+price)\b", tl))

    sort_by = "fare" if cheapest_requested else None
    journey_type = "CONNECTING" if connecting_requested else None

    # Query unified bus discovery service
    schedules, meta = search_curated_bus_schedules(
        origin=extracted_origin,
        destination=extracted_dest,
        operator_type=operator_filter,
        bus_type=bus_type_filter,
        journey_type=journey_type,
        direct_only=direct_only,
        sort_by=sort_by,
    )

    if schedules:
        bus_lines = []
        for s in schedules:
            op_name = s.operator_name
            op_badge = "🏛️ [Government / State Undertaking]" if s.operator_type == "government" else "🏢 [Private Fleet Operator]"
            b_type = s.bus_type or s.service_type or "Stage Carriage"
            orig_stand = s.origin_bus_stand or extracted_origin
            dest_stand = s.destination_bus_stand or extracted_dest
            op_hours = s.operating_hours or (f"{s.departure_time} - {s.arrival_time}" if s.departure_time else "Daytime Regular Service")
            freq = f"Every {s.frequency_minutes} mins" if s.frequency_minutes else "Daily Scheduled Departure"
            dur = f"~{s.duration_hours} hrs" if s.duration_hours else "~1.5 hrs"
            f_min = s.indicative_fare_min
            f_max = s.indicative_fare_max
            fare_str = f"₹{int(f_min)} - ₹{int(f_max)}" if f_min and f_max and f_min != f_max else (f"₹{int(f_min)}" if f_min else "Statutory fare")
            booking_link = f" | [Online Booking]({s.booking_url})" if s.booking_url else ""
            notes = s.notes or s.route_description or ""

            # Check if this is a connecting route
            if s.journey_type == "CONNECTING" and s.connecting_details:
                c_det = s.connecting_details
                l1 = c_det.get("leg1", {})
                l2 = c_det.get("leg2", {})
                bus_lines.append(
                    f"• **{op_name}** — 🔄 **CONNECTING ROUTE VIA JAMMU GBS**\n"
                    f"  - 🏷️ **Classification:** {op_badge}\n"
                    f"  - 📍 **Leg 1:** {l1.get('origin', orig_stand)} → {l1.get('destination', 'Jammu GBS')} ({l1.get('operator')})\n"
                    f"    - Timing: ~{l1.get('duration_hours')} hrs | Indicative Fare: ₹{l1.get('fare_min')} - ₹{l1.get('fare_max')}\n"
                    f"  - ⏱️ **Official Transfer Buffer:** {c_det.get('transfer_buffer_minutes', 60)} mins at {c_det.get('transfer_point', 'Jammu GBS')}\n"
                    f"  - 📍 **Leg 2:** {l2.get('origin', 'Jammu GBS')} → {l2.get('destination', dest_stand)} ({l2.get('operator')})\n"
                    f"    - Timing: ~{l2.get('duration_hours')} hrs | Indicative Fare: ₹{l2.get('fare_min')} - ₹{l2.get('fare_max')}\n"
                    f"  - 💰 **Combined Estimated Tariff:** {fare_str} | **Estimated Travel Time:** {dur}\n"
                    f"  - ℹ️ *{notes}*"
                )
            else:
                b_pts = f"Boarding: {', '.join(s.boarding_points)}" if s.boarding_points else f"Boarding: {orig_stand}"
                d_pts = f"Dropping: {', '.join(s.dropping_points)}" if s.dropping_points else f"Dropping: {dest_stand}"
                bus_lines.append(
                    f"• **{op_name}** ({b_type}) — {op_badge}\n"
                    f"  - 📍 **Boarding:** {b_pts}\n"
                    f"  - 📍 **Dropping:** {d_pts}\n"
                    f"  - 🕒 **Departure / Window:** {op_hours} ({freq})\n"
                    f"  - ⏱️ **Duration:** {dur}\n"
                    f"  - 💰 **Tariff:** {fare_str} ({s.fare_classification})\n"
                    f"  - 🎟️ **Availability & Booking:** {s.availability_status}{booking_link}\n"
                    f"  - ℹ️ *{notes}*"
                )

        gov_cnt = sum(1 for s in schedules if s.operator_type == "government")
        pvt_cnt = sum(1 for s in schedules if s.operator_type == "private")
        ver_cnt = sum(1 for s in schedules if s.verification_status == "verified_curated_source")
        part_cnt = sum(1 for s in schedules if s.verification_status == "partially_verified")

        filter_banner = ""
        if cheapest_requested:
            ch_s = schedules[0]
            filter_banner = (
                f"🏆 **Cheapest Bus Found (Lowest Indicative Tariff):** **{ch_s.operator_name}** ({ch_s.bus_type or ch_s.service_type})\n"
                f"💰 **Lowest Indicative Tariff:** ₹{int(ch_s.indicative_fare_min or 0)} per person ({ch_s.fare_classification})\n"
                f"🕒 **Departure:** {ch_s.departure_time or ch_s.operating_hours} | ⏱️ **Duration:** ~{ch_s.duration_hours} hrs\n"
                f"⚠️ *Disclaimer: Tariffs are indicative based on verified operator schedules; final prices vary by seat category and booking portal.*\n\n"
            )
        elif operator_filter == "private":
            filter_banner = "🏷️ *Displaying verified private bus fleet operators only.*\n\n"
        elif operator_filter == "government":
            filter_banner = "🏷️ *Displaying verified government & state transport undertakings only.*\n\n"
        elif bus_type_filter:
            filter_banner = f"🏷️ *Filtered by category: {bus_type_filter.upper()} buses.*\n\n"
        elif direct_only:
            filter_banner = "🏷️ *Displaying direct non-stop through buses only.*\n\n"
        elif connecting_requested:
            filter_banner = "🏷️ *Displaying verified connecting routes via Jammu General Bus Stand with transfer buffers.*\n\n"

        reply = (
            f"🚌 **Official Public Bus Transport — Multi-Operator Bus Transport Gateway: {extracted_origin} → {extracted_dest}**\n\n"
            f"{filter_banner}"
            f"📋 **Fleet Composition:** {len(schedules)} verified service(s) ({ver_cnt} Verified + {part_cnt} Partially Verified / Indicative; {gov_cnt} Government + {pvt_cnt} Private) from discoverable services in the curated registry (not an exhaustive catalogue of all operators in India)\n"
            f"📡 **Live GPS Tracking:** Not Connected *(No public GPS telemetry or GTFS feed in J&K)*\n"
            f"💰 **Fare Classification:** Statutory Govt-Notified Tariff *(J&K STA Notification No. 01-P-MVD of 2026 for Regional Slabs)* & Operator Published Tariffs\n"
            f"🎟️ **Seat Availability:** Counter Ticketing / Unreserved *(Tickets issued on board or at stand counters; online booking for private sleeper coaches)*\n\n"
            + "\n\n".join(bus_lines)
            + "\n\n"
            f"🌐 **Official Booking Portals & Helplines:**\n"
            f"• **JKRTC Online Booking:** https://jksrtc.co.in/ | Helpline: `+91-9149473175`\n"
            f"• **HRTC Online Portal:** https://hrtchp.com/\n"
            f"• **Laxmi Holidays:** https://www.laxmiholidays.com/\n"
            f"• **Zingbus:** https://www.zingbus.com/\n"
            f"• **FlixBus India:** https://www.flixbus.in/\n"
            f"• **IntrCity SmartBus:** https://www.intrcity.com/\n"
            f"• **Ram Dalal Holidays:** https://www.ramdalaltravels.com/\n"
            f"• **Jammu General Bus Stand (GBS):** `0191-2476290` | **Katra Central Stand:** `01991-232049`\n\n"
            f"⚠️ *Truth-in-Data Notice: Fares and operating windows reflect official operator tariffs and statutory STA notification slabs. Private sleeper buses offer advance online seat selection on carrier portals; regional stage carriages issue tickets on board or at stand counters.*"
        )
    else:
        reply = (
            f"🚌 **Bus Connectivity: {extracted_origin} → {extracted_dest}**\n\n"
            f"No verified bus service matching your criteria was found for **{extracted_origin} → {extracted_dest}**.\n\n"
            f"• **Supported Direct Bus Corridors:** Delhi, Chandigarh, Amritsar, Pathankot, Jammu, and Udhampur to Katra.\n"
            f"• **Connecting Guidance:** For other origins, travel by train/flight to Delhi or Jammu and connect via high-frequency local feeder buses or private sleeper coaches.\n"
            f"• **Helpline:** Contact Jammu General Bus Stand at `0191-2476290` or JKRTC at `+91-9149473175`."
        )

    return {
        "intent": "BUS_SEARCH",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
        "buses": [s.to_dict() for s in schedules],
    }


def handle_budget_calculation_intent(
    user_text: str,
    session: Dict[str, Any],
) -> Dict[str, Any]:
    reply = (
        "💰 **Estimated Budget & Expense Breakdown for Vaishno Devi Yatra**\n\n"
        "Here is a comprehensive itemized cost breakdown per pilgrim:\n\n"
        "**1. Statutory Registration:**\n"
        "• **RFID Yatra Registration Card (Parchi):** **FREE (₹0)** — Issued 24x7 by SMVDSB.\n\n"
        "**2. Travel to Katra (SVDK):**\n"
        "• **Vande Bharat Express (Chair Car / Executive):** ₹1,665 / ₹3,015 from New Delhi.\n"
        "• **Superfast Trains (Sleeper / 3AC):** ₹380 – ₹1,100 per person.\n"
        "• **Flights to Jammu (IXJ):** ₹3,500 – ₹6,500 (plus ₹1,500–₹2,000 for Jammu–Katra taxi).\n\n"
        "**3. Accommodation in Katra (per night):**\n"
        "• **Shrine Board Dormitory / Room:** ₹150 – ₹1,200\n"
        "• **Budget Private Hotel:** ₹800 – ₹1,500\n"
        "• **Mid-range / Premium Hotel:** ₹2,000 – ₹4,500\n\n"
        "**4. Trek Transit (Optional):**\n"
        "• **Walking on Foot (Banganga or Tarakote Marg):** **₹0**\n"
        "• **Battery Auto (Adhkuwari ↔ Bhawan):** ₹350 per person\n"
        "• **Bhairon Passenger Ropeway:** ₹100 per person (round-trip)\n"
        "• **Helicopter Service (Katra ↔ Sanjichhat):** ~₹2,100 one-way\n"
        "• **Pony / Palki:** ₹1,250 – ₹3,500 (as per official SMVDSB rate chart)\n\n"
        "**5. Food & Offerings:**\n"
        "• Shrine Board Prasad & Meals: ₹300 – ₹600 per day\n\n"
        "**Estimated Total per Pilgrim (2-day trip):**\n"
        "• **Budget Pilgrimage:** ~₹2,500 – ₹3,500\n"
        "• **Comfort Pilgrimage:** ~₹5,000 – ₹8,000\n"
        "• **Premium Pilgrimage (Flights/Helicopter):** ~₹12,000 – ₹18,000"
    )
    return {
        "intent": "BUDGET_CALCULATION",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session.get("session_id"),
    }


def handle_hotel_change(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handles hotel change, rejection of Niharika, or numbered hotel option selection."""
    from services.accommodation_catalog import search_hotels_for_orchestrator

    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if current_request:
        req.update(current_request)
    session_id = session.get("session_id")
    tl = (user_text or "").lower()

    # Load all verified Katra hotels
    all_hotels = search_hotels_for_orchestrator(check_in_date=req.get("start_date"))
    if not all_hotels:
        from services.accommodation_catalog import search_hotels_with_status
        all_hotels, _ = search_hotels_with_status()

    # Exclude mid-trek mountain stops (Ardhkuwari and Main Bhawan are trek halts, not Katra base hotels)
    katra_hotels = [h for h in all_hotels if "ardhkuwari" not in h.get("name", "").lower() and "main bhawan" not in h.get("name", "").lower()]

    # Check for rejection of Niharika Complex
    if "niharika" in tl and any(w in tl for w in ["don't want", "dont want", "not want", "reject", "other", "different", "exclude"]):
        req["reject_niharika"] = True
        req["_reject_niharika"] = True
        req.pop("selected_hotel", None)
        req.pop("hotel", None)

    # Filter available hotels based on rejection
    available = [
        h for h in katra_hotels
        if not (req.get("reject_niharika") and "niharika" in h.get("name", "").lower())
    ]
    # Prioritize Katra base camp hotels (Mid-Range & Budget first, then Premium, then Dharamshalas)
    order_map = {"Mid-Range": 1, "Budget": 2, "Premium": 3, "Dharamshala": 4}
    available = sorted(available, key=lambda h: (order_map.get(h.get("category"), 5), h.get("price_per_night", 9999)))

    new_hotel = None
    # Check for ordinal / numbered option selection: "second option", "option 2", "third option", etc.
    if re.search(r"\b(?:second\s+option|option\s+2|2nd\s+option)\b", tl):
        if len(available) > 1:
            new_hotel = available[1]
    elif re.search(r"\b(?:third\s+option|option\s+3|3rd\s+option)\b", tl):
        if len(available) > 2:
            new_hotel = available[2]
    elif re.search(r"\b(?:first\s+option|option\s+1|1st\s+option)\b", tl):
        if available:
            new_hotel = available[0]
    else:
        # Check if user mentioned a specific hotel name in text
        for h in available:
            h_name = h.get("name", "").lower()
            key_tokens = [tok for tok in h_name.split() if len(tok) > 4 and tok not in ("hotel", "complex", "shakti", "katra", "bhawan")]
            if h_name in tl or any(tok in tl for tok in key_tokens):
                new_hotel = h
                break

    if not new_hotel:
        # User requested other/different hotel: cycle away from currently selected hotel
        cur_h = state.get("selected_options", {}).get("accommodation") or {}
        cur_name = (cur_h.get("name") or "").lower()
        candidates = [h for h in available if h.get("name", "").lower() != cur_name and "niharika" not in h.get("name", "").lower()]
        new_hotel = candidates[0] if candidates else (available[0] if available else None)

    if new_hotel:
        req["selected_hotel"] = new_hotel
        req["hotel"] = new_hotel
        state.setdefault("selected_options", {})["accommodation"] = new_hotel
        if state.get("plan"):
            state["plan"]["hotel"] = new_hotel

    # Re-evaluate complete plan with updated hotel
    if not req.get("origin"):
        saved_origin = session.get("state", {}).get("requirements", {}).get("origin")
        if saved_origin:
            req["origin"] = saved_origin

    if not req.get("origin"):
        h_name = new_hotel.get("name") if new_hotel else "Updated Katra Hotel"
        h_cat = new_hotel.get("category", "Standard") if new_hotel else "Standard"
        h_price = new_hotel.get("price_per_night", 1200) if new_hotel else 1200
        reply = (
            f"🏨 **Accommodation Preference Updated — {h_name}**\n\n"
            f"• **Hotel:** {h_name} ({h_cat})\n"
            f"• **Tariff:** ₹{h_price:,.0f}/night\n\n"
            f"To calculate confirmed transport options and complete your itemized budget, please specify **which city you will be travelling from**."
        )
        return {
            "intent": "HOTEL_CHANGE",
            "reply": reply,
            "status": "NEEDS_INFO",
            "missing_fields": ["origin"],
            "hotel": new_hotel,
            "hotel_changed": True,
            "requirements": req,
            "session_id": session_id,
        }

    curr_v = state.get("plan_version", 1)
    next_v = curr_v + 1
    state["plan_version"] = next_v
    plan_res = coordinate_plan(req, session_id=session_id, plan_version=next_v)
    if not plan_res:
        plan_res = {}
    plan_res["plan_version"] = next_v
    state["plan"] = plan_res.get("plan")
    state["budget_evaluation"] = plan_res.get("budget_evaluation")
    state["itinerary"] = plan_res.get("itinerary")
    state["selected_options"] = plan_res.get("selected_options")
    state["requirements"] = req
    if session_id:
        session_store.update_session(
            session_id=session_id,
            updates={
                "plan_version": next_v,
                "requirements": req,
                "plan": plan_res.get("plan"),
                "selected_options": plan_res.get("selected_options"),
                "budget_evaluation": plan_res.get("budget_evaluation"),
                "itinerary": plan_res.get("itinerary"),
                "authorized_plan_version": None,
                "authorization": {"pending": False, "granted": False},
            }
        )

    h_name = new_hotel.get("name") if new_hotel else "Updated Katra Hotel"
    h_cat = new_hotel.get("category", "Standard") if new_hotel else "Standard"
    h_price = new_hotel.get("price_per_night", 1200) if new_hotel else 1200
    grand_tot = plan_res.get("budget_evaluation", {}).get("grand_total")
    tot_str = f"₹{grand_tot:,.0f}" if grand_tot else "Calculated"

    reply = (
        f"🏨 **Accommodation Updated: {h_name}**\n\n"
        f"🙏 **Jai Mata Di!** I have updated your stay to **{h_name}** ({h_cat} · ₹{h_price:,.0f}/night).\n\n"
        f"• **Location:** {new_hotel.get('location', 'Central Katra Base')}\n"
        f"• **Room Allocation:** {plan_res.get('budget_evaluation', {}).get('breakdown', {}).get('hotel', {}).get('rooms', 1)} room(s) for {req.get('pax', 2)} pilgrims\n"
        f"• **Updated Total Trip Estimate:** **{tot_str}** (includes round-trip transport, hotel stay, and darshan arrangements)\n\n"
        f"Would you like to review the complete booking or proceed to confirmation?"
    )

    plan_res["reply"] = reply
    plan_res["intent"] = "HOTEL_CHANGE"
    plan_res["hotel"] = new_hotel
    plan_res["available_hotels"] = available[:6]
    return plan_res


def handle_transport_change(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handles train/transport switch or specific train/bus selection."""
    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if current_request:
        req.update(current_request)
    session_id = session.get("session_id")
    tl = (user_text or "").lower()

    # Multi-operator bus mapping
    bus_operator_map = {
        "laxmi holidays": "Laxmi Holidays",
        "laxmi": "Laxmi Holidays",
        "zingbus": "Zingbus",
        "flixbus": "FlixBus",
        "intrcity": "IntrCity",
        "ram dalal": "Ram Dalal Holidays",
        "hrtc": "HRTC",
        "prtc": "PRTC",
        "punbus": "Punbus",
        "jksrtc": "JKRTC",
    }
    matched_bus_op = None
    for k, v in bus_operator_map.items():
        if k in tl:
            matched_bus_op = v
            break

    if matched_bus_op:
        req["selected_transport"] = matched_bus_op
        req["mode"] = "bus"
    elif "22439" in tl or "vande bharat" in tl:
        req["selected_transport"] = "22439"
        req["mode"] = "train"
    elif "22440" in tl:
        req["selected_transport"] = "22440"
        req["mode"] = "train"
    elif "22461" in tl or "shri shakti" in tl:
        req["selected_transport"] = "22461"
        req["mode"] = "train"
    elif "12445" in tl or "uttar sampark" in tl:
        req["selected_transport"] = "12445"
        req["mode"] = "train"
    elif "flight" in tl:
        req["mode"] = "flight"
    elif "bus" in tl:
        req["mode"] = "bus"
    elif "train" in tl:
        req["mode"] = "train"

    if not req.get("origin"):
        saved_origin = session.get("state", {}).get("requirements", {}).get("origin")
        if saved_origin:
            req["origin"] = saved_origin

    if not req.get("origin"):
        tr_desc = req.get("selected_transport") or req.get("mode") or "Transport"
        reply = (
            f"🚄↔️🚌 **Transport Preference Updated — {str(tr_desc).title()}**\n\n"
            f"• **Preferred Mode / Service:** {tr_desc}\n\n"
            f"Please specify your **departure city** so I can search confirmed schedules, timings, and fares to Katra."
        )
        return {
            "intent": "TRANSPORT_CHANGE",
            "reply": reply,
            "status": "NEEDS_INFO",
            "missing_fields": ["origin"],
            "transport_changed": True,
            "requirements": req,
            "session_id": session_id,
        }

    curr_v = state.get("plan_version", 1)
    next_v = curr_v + 1
    state["plan_version"] = next_v
    plan_res = coordinate_plan(req, session_id=session_id, plan_version=next_v)
    if not plan_res:
        plan_res = {}
    plan_res["plan_version"] = next_v
    state["plan"] = plan_res.get("plan")
    state["budget_evaluation"] = plan_res.get("budget_evaluation")
    state["itinerary"] = plan_res.get("itinerary")
    state["selected_options"] = plan_res.get("selected_options")
    state["requirements"] = req
    if session_id:
        session_store.update_session(
            session_id=session_id,
            updates={
                "plan_version": next_v,
                "requirements": req,
                "plan": plan_res.get("plan"),
                "selected_options": plan_res.get("selected_options"),
                "budget_evaluation": plan_res.get("budget_evaluation"),
                "itinerary": plan_res.get("itinerary"),
                "authorized_plan_version": None,
                "authorization": {"pending": False, "granted": False},
            }
        )

    sel_tr = plan_res.get("selected_options", {}).get("transport") or {}
    tr_name = sel_tr.get("name") or sel_tr.get("operator") or "Transport Service"
    dep_time = sel_tr.get("departure_time") or "Regular departure"
    grand_tot = plan_res.get("budget_evaluation", {}).get("grand_total")
    tot_str = f"₹{grand_tot:,.0f}" if grand_tot else "Calculated"

    if sel_tr.get("mode") == "bus":
        op_type = f" ({sel_tr.get('operator_type', 'Stage Carriage').title()})" if sel_tr.get("operator_type") else ""
        b_pts = ", ".join(sel_tr.get("boarding_points", [])) if sel_tr.get("boarding_points") else sel_tr.get("origin_bus_stand", req.get("origin", "Delhi"))
        d_pts = ", ".join(sel_tr.get("dropping_points", [])) if sel_tr.get("dropping_points") else sel_tr.get("destination_bus_stand", "Katra Central Bus Stand")
        bk_url = sel_tr.get("booking_url") or "Bus Stand Counter / Operator Portal"
        f_min = sel_tr.get("indicative_fare_min")
        f_max = sel_tr.get("indicative_fare_max")
        fare_text = f"₹{int(f_min)} - ₹{int(f_max)}" if f_min and f_max and f_min != f_max else (f"₹{int(f_min)}" if f_min else "Indicative tariff")

        reply = (
            f"🚌 **Transport Selection Updated: {tr_name}**\n\n"
            f"🙏 **Jai Mata Di!** I have updated your travel arrangement to **{tr_name}**{op_type} (Bus).\n\n"
            f"• **Route:** {sel_tr.get('origin', req.get('origin', 'Delhi'))} → Katra\n"
            f"• **Boarding:** {b_pts}\n"
            f"• **Dropping:** {d_pts}\n"
            f"• **Departure:** {dep_time} | **Arrival:** {sel_tr.get('arrival_time', 'Next morning')}\n"
            f"• **Indicative Fare:** {fare_text} per person ({sel_tr.get('fare_classification', 'Published Tariff')})\n"
            f"• **Official Booking:** {bk_url}\n"
            f"• **Updated Total Trip Estimate:** **{tot_str}**\n\n"
            f"You can review your full itinerary or say **Proceed with booking** when ready."
        )
    else:
        reply = (
            f"🚆 **Transport Selection Updated: {tr_name}**\n\n"
            f"🙏 **Jai Mata Di!** I have updated your travel arrangement to **{tr_name}** ({sel_tr.get('mode', 'train').title()}).\n\n"
            f"• **Route:** {sel_tr.get('origin', req.get('origin', 'Delhi'))} → Katra (SVDK)\n"
            f"• **Departure:** {dep_time} | **Arrival:** {sel_tr.get('arrival_time', 'Same day')}\n"
            f"• **Updated Total Trip Estimate:** **{tot_str}**\n\n"
            f"You can review your full itinerary or say **Proceed with booking** when ready."
        )

    plan_res["reply"] = reply
    plan_res["intent"] = "TRANSPORT_CHANGE"
    plan_res["selected_option"] = plan_res.get("selected_options")
    return plan_res


def handle_date_change(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handles travel date selection or date modification."""
    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if current_request:
        req.update(current_request)
    session_id = session.get("session_id")

    st_date, en_date = None, None
    if legacy_agent.has_explicit_date(user_text):
        st_date, en_date = legacy_agent._extract_date_range(user_text)

    if not st_date:
        parsed_dt, _, _, _, _ = conversation_agent.parse_and_validate_yatra_date(user_text, context=req)
        if parsed_dt:
            st_date = parsed_dt

    if not st_date:
        return {
            "status": "AWAITING_INPUT",
            "reply": (
                "📅 **Select New Travel Dates**\n\n"
                "🙏 **Jai Mata Di!** Please select your new departure date and return date below, or type your preferred dates (e.g. *25 to 28 November*)."
            ),
            "intent": "DATE_CHANGE",
            "showDatePicker": True,
            "request": req,
        }

    if st_date:
        req["start_date"] = st_date
        req["_date_explicit"] = True
        if en_date:
            req["end_date"] = en_date
            try:
                d1 = datetime.strptime(st_date, "%Y-%m-%d")
                d2 = datetime.strptime(en_date, "%Y-%m-%d")
                req["duration_days"] = max(1, (d2 - d1).days + 1)
            except Exception:
                pass
        else:
            dur = req.get("duration_days") or 4
            try:
                d1 = datetime.strptime(st_date, "%Y-%m-%d")
                req["end_date"] = (d1 + timedelta(days=max(1, dur - 1))).strftime("%Y-%m-%d")
            except Exception:
                pass

    if not req.get("origin"):
        saved_origin = session.get("state", {}).get("requirements", {}).get("origin")
        if saved_origin:
            req["origin"] = saved_origin

    if not req.get("origin"):
        st_disp = req.get("start_date", "Upcoming")
        en_disp = req.get("end_date", "")
        dur_disp = req.get("duration_days", 4)
        reply = (
            f"🗓️ **Travel Dates Updated**\n\n"
            f"• **Window:** {st_disp} to {en_disp} ({dur_disp} days)\n\n"
            f"Please specify your **departure city** so I can check transport schedules and generate your complete pilgrimage package."
        )
        return {
            "intent": "DATE_CHANGE",
            "reply": reply,
            "status": "NEEDS_INFO",
            "missing_fields": ["origin"],
            "requirements": req,
            "session_id": session_id,
        }

    curr_v = state.get("plan_version", 1)
    next_v = curr_v + 1
    state["plan_version"] = next_v
    plan_res = coordinate_plan(req, session_id=session_id, plan_version=next_v)
    if not plan_res:
        plan_res = {}
    plan_res["plan_version"] = next_v
    state["plan"] = plan_res.get("plan")
    state["budget_evaluation"] = plan_res.get("budget_evaluation")
    state["itinerary"] = plan_res.get("itinerary")
    state["selected_options"] = plan_res.get("selected_options")
    state["requirements"] = req
    if session_id:
        session_store.update_session(
            session_id=session_id,
            updates={
                "plan_version": next_v,
                "requirements": req,
                "plan": plan_res.get("plan"),
                "selected_options": plan_res.get("selected_options"),
                "budget_evaluation": plan_res.get("budget_evaluation"),
                "itinerary": plan_res.get("itinerary"),
                "authorized_plan_version": None,
                "authorization": {"pending": False, "granted": False},
            }
        )

    st_disp = req.get("start_date", "Upcoming")
    en_disp = req.get("end_date", "")
    dur_disp = req.get("duration_days", 4)
    grand_tot = plan_res.get("budget_evaluation", {}).get("grand_total")
    tot_str = f"₹{grand_tot:,.0f}" if grand_tot else "Calculated"

    reply = (
        f"📅 **Travel Dates Updated**\n\n"
        f"🙏 **Jai Mata Di!** Your yatra schedule has been updated to:\n\n"
        f"• **Departure Date:** **{st_disp}**\n"
        f"• **Return Date:** **{en_disp}** ({dur_disp} Days / {max(1, dur_disp-1)} Nights)\n"
        f"• **Darshan Slot:** Normal Darshan · {st_disp}\n"
        f"• **Updated Total Trip Estimate:** **{tot_str}**\n\n"
        f"Transport and Katra accommodation have been automatically aligned with your new dates. Say **Proceed with booking** when you are ready to continue."
    )

    plan_res["reply"] = reply
    plan_res["intent"] = "DATE_CHANGE"
    return plan_res


def handle_booking_review(
    user_text: str,
    session: Dict[str, Any],
    current_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Presents a comprehensive pre-booking summary review."""
    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if current_request:
        req.update(current_request)
    session_id = session.get("session_id")

    if not state.get("selected_options"):
        plan_res = coordinate_plan(req, session_id=session_id)
        state["plan"] = plan_res.get("plan")
        state["budget_evaluation"] = plan_res.get("budget_evaluation")
        state["itinerary"] = plan_res.get("itinerary")
        state["selected_options"] = plan_res.get("selected_options")
        state["requirements"] = req

    sel = state.get("selected_options", {})
    tr = sel.get("transport") or {}
    htl = sel.get("accommodation") or {}
    slot = sel.get("darshan_slot") or {}
    bgt = state.get("budget_evaluation") or {}

    origin = req.get("origin")
    if not origin:
        saved_origin = session.get("state", {}).get("requirements", {}).get("origin")
        origin = saved_origin or "Pending Origin"
    pax = int(req.get("pax") or 2)
    st_date = req.get("start_date") or "2026-11-25"
    en_date = req.get("end_date") or "2026-11-28"
    dur = int(req.get("duration_days") or 4)
    nights = max(1, dur - 1)
    rooms = budget_engine.calculate_rooms_required(pax)

    tr_name = tr.get("name") or tr.get("operator") or f"{origin} to Katra Train"
    tr_fare = tr.get("price") or tr.get("fare") or 1665
    htl_name = htl.get("name", "Hotel Asia Vaishno Devi")
    htl_price = htl.get("price_per_night", 2200)
    slot_desc = slot.get("category", "Normal Darshan")
    grand_tot = bgt.get("grand_total") or ((tr_fare * pax * 2) + (htl_price * rooms * nights))

    reply = (
        f"📋 **Complete Booking Review — Maa Vaishno Devi Yatra**\n\n"
        f"Please verify your journey summary before human authorization and confirmation:\n\n"
        f"**1. Pilgrims & Dates:**\n"
        f"• **Pilgrims:** {pax} adult(s)\n"
        f"• **Journey Dates:** {st_date} to {en_date} ({dur} Days / {nights} Nights)\n"
        f"• **Origin / Destination:** {origin} ➔ Katra (SVDK) & Bhawan\n\n"
        f"**2. Selected Transport:**\n"
        f"• **Service:** {tr_name} ({tr.get('mode', 'train').title()})\n"
        f"• **Timings:** Dep: {tr.get('departure_time', '06:00')} | Arr: {tr.get('arrival_time', '14:00')}\n"
        f"• **Indicative Round-trip Transport:** ₹{float(tr_fare * pax * 2):,.0f}\n\n"
        f"**3. Katra Accommodation:**\n"
        f"• **Hotel:** {htl_name} ({htl.get('category', 'Standard')})\n"
        f"• **Stay:** {rooms} room(s) for {nights} night(s) (₹{float(htl_price):,.0f}/night)\n"
        f"• **Location:** {htl.get('location', 'Central Katra Base')}\n\n"
        f"**4. Maa Vaishno Devi Darshan:**\n"
        f"• **Slot:** {slot_desc} · Scheduled for {slot.get('slot_date', st_date)}\n"
        f"• **RFID Yatra Registration:** Mandatory SMVDSB pass (₹0 statutory)\n\n"
        f"💰 **Total Estimated Cost:** **₹{float(grand_tot):,.0f}**\n\n"
        f"Ready to proceed? Say **Proceed with booking** or click **Confirm & Book** to start the booking checkpoint."
    )

    return {
        "intent": "BOOKING_REVIEW",
        "status": "PLAN_READY",
        "reply": reply,
        "session_id": session_id,
        "request": req,
        "plan": state.get("plan"),
        "selected_options": sel,
        "budget_evaluation": bgt,
        "itinerary": state.get("itinerary"),
        "hotel": htl,
        "available_hotels": state.get("plan", {}).get("available_hotels", []),
    }


def handle_my_bookings(
    user_text: str,
    session: Dict[str, Any],
) -> Dict[str, Any]:
    """Retrieves and formats saved simulated bookings."""
    session_id = session.get("session_id")
    state = session.get("state", {})
    user_id = session.get("user_id")

    saved_bookings = []
    if user_id:
        try:
            from agents.auth_service import auth_service
            saved_bookings = auth_service.get_user_bookings(user_id) or []
        except Exception as e:
            logger.debug(f"Could not load bookings from auth_service: {e}")

    session_history = state.get("booking_history") or []
    for b in session_history:
        b_id = b.get("booking_id")
        if b_id and not any(sb.get("booking_id") == b_id for sb in saved_bookings):
            saved_bookings.append(b)

    rpa_exec = state.get("rpa_execution") or {}
    cur_bid = rpa_exec.get("booking_id")
    if cur_bid and not any(sb.get("booking_id") == cur_bid for sb in saved_bookings):
        saved_bookings.append({
            "booking_id": cur_bid,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "CONFIRMED",
            "hotel": state.get("selected_options", {}).get("accommodation", {}).get("name", "Hotel Asia Vaishno Devi"),
            "total_amount": state.get("budget_evaluation", {}).get("grand_total", 8500),
            "pax": state.get("requirements", {}).get("pax", 2),
        })

    if saved_bookings:
        lines = []
        for i, b in enumerate(saved_bookings[:5], 1):
            bid = b.get("booking_id", f"VD-DEMO-{100000+i}")
            dt = b.get("created_at") or b.get("yatra_date") or "Recent"
            htl = b.get("hotel") or b.get("hotel_name") or "Katra Stay"
            amt = b.get("total_amount") or b.get("amount") or 8500
            st = b.get("status", "CONFIRMED")
            lines.append(
                f"**{i}. Booking Reference: `{bid}`** ({st})\n"
                f"   • **Date:** {dt} | **Accommodation:** {htl}\n"
                f"   • **Amount:** ₹{float(amt):,.0f} | **Pass:** [Download PDF](/api/yatra/booking/{bid}/pdf)"
            )

        reply = (
            f"📑 **Your Previous Saved Bookings**\n\n"
            f"Here are the simulated bookings linked to your session:\n\n"
            + "\n\n".join(lines)
            + f"\n\nℹ️ *All bookings can be downloaded as official-styled demo passes from your My Bookings dashboard.*"
        )
    else:
        reply = (
            "📑 **My Bookings**\n\n"
            "You do not have any saved bookings under this active session yet.\n\n"
            "Once you complete a yatra plan and authorize simulated booking, your confirmation ID, "
            "itinerary details, and downloadable demo pass will be stored here permanently for future reference."
        )

    return {
        "intent": "MY_BOOKINGS",
        "status": "SUCCESS",
        "reply": reply,
        "session_id": session_id,
        "bookings": saved_bookings,
    }


def orchestrate_conversational_turn(
    user_text: str,
    session_id: Optional[str] = None,
    current_request: Optional[Dict[str, Any]] = None,
    current_itinerary: Optional[List[Dict[str, Any]]] = None,
    last_tourism_place: Optional[str] = None,
    last_itinerary_context: Optional[Dict[str, Any]] = None,
    pending_options: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    llm: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main entry point for conversational agent orchestration.
    Loads/creates persistent session, parses requirements, checks missing fields,
    coordinates tools or replans, and returns one consolidated response.
    """
    # Step 1: Session Management
    session = None
    if session_id:
        try:
            session = session_store.get_session(session_id)
        except Exception:
            session = None

    if not session or session.get("_corrupted"):
        # Seed initial session with current_request if supplied by client
        initial_st = {}
        if current_request:
            initial_st["requirements"] = current_request
        if current_itinerary:
            initial_st["itinerary"] = current_itinerary
        if last_tourism_place:
            initial_st["last_tourism_place"] = last_tourism_place
        if last_itinerary_context:
            initial_st["last_itinerary_context"] = last_itinerary_context
        # If session_id is a saved conversation, resurrect it into session_store to preserve ID & continuity
        if session_id:
            try:
                from agents.auth_service import auth_service
                import sqlite3
                with sqlite3.connect(auth_service.db_path, timeout=5.0) as conn:
                    row = conn.cursor().execute(
                        "SELECT messages_json, user_id FROM saved_conversations WHERE conversation_id = ?",
                        (session_id.strip(),),
                    ).fetchone()
                    if row:
                        session = session_store.create_session(
                            session_id=session_id.strip(),
                            user_id=row[1],
                            initial_state=initial_st,
                        )
                        if not session_store.get_messages(session_id.strip()):
                            conv_msgs = json.loads(row[0])
                            for m in conv_msgs:
                                session_store.add_message(
                                    session_id=session_id.strip(),
                                    role=m.get("role", "user"),
                                    content=m.get("content", ""),
                                    metadata=m.get("metadata") or {
                                        "recommendation": m.get("recommendation"),
                                        "plan": m.get("plan"),
                                        "request": m.get("request"),
                                        "itinerary": m.get("itinerary"),
                                    },
                                )
            except Exception as exc:
                logger.debug("Silently ignored error checking saved conversation in orchestrator: %s", exc)

        if not session or session.get("_corrupted"):
            # Unknown or corrupted session ID: generate a fresh, secure session ID (do not reuse untrusted ID)
            session = session_store.create_session(session_id=None, initial_state=initial_st)

    sid = session["session_id"]
    state = session.get("state", {})
    req = dict(state.get("requirements", {}))
    if state.get("pending_ambiguity"):
        req["pending_ambiguity"] = state["pending_ambiguity"]
    if current_request:
        req.update(current_request)
        state["requirements"] = req

    # Detect intent
    intent = conversation_agent.detect_intent(user_text)

    # Persist user turn message exactly once per turn
    user_msg_id = None
    try:
        _prev_u = session_store.get_messages(sid)
        if not _prev_u or _prev_u[-1].get("role") != "user" or _prev_u[-1].get("content") != user_text:
            user_msg_id = session_store.add_message(
                session_id=sid,
                role="user",
                content=user_text,
                metadata={"intent": intent},
            )
    except Exception as exc:
        logger.warning("Failed to persist user message for session %s: %s", sid, type(exc).__name__)

    turn_completed = False

    def _finalize(turn_res: Dict[str, Any], default_intent: str = "UNKNOWN") -> Dict[str, Any]:
        nonlocal turn_completed
        final_res = _finalize_turn_response(turn_res, sid, default_intent=default_intent)
        turn_completed = True
        return final_res

    try:

        # 1a. Booking Navigation Request (user wants to proceed to booking with recommended Yatra)
        if intent == "BOOKING_INTENT":
            b_nav_res = handle_booking_navigation_intent(
                user_text,
                session,
                pending_options=pending_options or state.get("pending_options"),
            )
            b_nav_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            b_nav_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(b_nav_res, default_intent="BOOKING_INTENT")

        # 1b. Booking confirmation gate
        if intent == "BOOKING":
            b_res = handle_booking_authorization(
                user_text,
                session,
                human_authorized=False,
                pending_options=pending_options or state.get("pending_options"),
            )
            b_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            b_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(b_res, default_intent="BOOKING")

        # 1c. My Bookings Enquiry
        if intent == "MY_BOOKINGS":
            mb_res = handle_my_bookings(user_text, session)
            mb_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            mb_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(mb_res, default_intent="MY_BOOKINGS")

        # 1d. Booking Review / Complete Booking Summary
        if intent == "BOOKING_REVIEW":
            br_res = handle_booking_review(user_text, session, current_request=current_request or req)
            br_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            br_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(br_res, default_intent="BOOKING_REVIEW")

        # 1e. Hotel Selection / Change / Rejection
        if intent == "HOTEL_CHANGE":
            hc_res = handle_hotel_change(user_text, session, current_request=current_request or req)
            hc_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            hc_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(hc_res, default_intent="HOTEL_CHANGE")

        # 1f. Transport Selection / Train Change
        if intent == "TRANSPORT_CHANGE":
            tc_res = handle_transport_change(user_text, session, current_request=current_request or req)
            tc_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            tc_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(tc_res, default_intent="TRANSPORT_CHANGE")

        # 1g. Travel Dates Update / Selection
        if intent == "DATE_CHANGE":
            dc_res = handle_date_change(user_text, session, current_request=current_request or req)
            dc_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            dc_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(dc_res, default_intent="DATE_CHANGE")

        # 2. Weather query
        if intent == "WEATHER":
            w_res = coordinator.process_weather_message(user_text, current_request=current_request if current_request is not None else req)
            w_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            w_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(w_res, default_intent="WEATHER")

        # 3. Cost breakdown and replanning checks
        cost_breakdown_keywords = [
            "cost breakdown", "budget breakdown", "detailed cost", "expense breakdown",
            "price breakdown", "detailed budget", "breakdown of costs", "breakdown of budget",
            "explain the cost", "show costs", "view costs", "total cost breakdown", "exact total cost"
        ]
        has_active_plan = state.get("selected_options") and bool(state["selected_options"].get("transport"))
        if any(cb in user_text.lower() for cb in cost_breakdown_keywords):
            breakdown_text = format_itemized_cost_breakdown(session)
            cb_res = {
                "intent": "TRIP_PLANNING",
                "status": "PLAN_READY" if has_active_plan else "NEEDS_INFO",
                "reply": breakdown_text,
                "request": req,
                "plan": {"options": state.get("pending_options") or []},
                "itinerary": state.get("itinerary"),
                "selected_options": state.get("selected_options"),
                "budget_evaluation": state.get("budget_evaluation"),
                "last_tourism_place": last_tourism_place or state.get("last_tourism_place"),
                "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),
            }
            return _finalize(cb_res, default_intent="TRIP_PLANNING")

        if has_active_plan:
            if is_replanning_query(user_text):
                rep_res = handle_replanning(user_text, session)
                rep_res["intent"] = "TRIP_PLANNING"
                rep_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
                rep_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
                return _finalize(rep_res, default_intent="TRIP_PLANNING")
        # 4. Availability query (Week 7 RPA Tool Calling)
        if intent == "AVAILABILITY":
            avail_res = handle_availability_query(
                user_text,
                session=session,
                current_request=current_request or req,
                llm=llm,
            )
            avail_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            avail_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(avail_res, default_intent="AVAILABILITY")

        # 5. Pure tourism query (e.g. Aarti timings, Bhairavnath history, "Tell me about Patnitop")
        if intent == "TOURISM":
            active_trip_req = current_request if current_request is not None else (req if req and req.get("origin") else None)
            t_res = coordinator.answer_tourism_query(
                user_text,
                last_tourism_place=last_tourism_place or state.get("last_tourism_place"),
                current_request=active_trip_req,
            )
            t_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            if not t_res.get("request") and active_trip_req:
                t_res["request"] = active_trip_req
            session_store.update_session(sid, updates={"last_tourism_place": t_res.get("last_tourism_place")})
            return _finalize(t_res, default_intent="TOURISM")

        # 5a. Specialized Travel & Transport Intents
        if intent == "TRAIN_SEARCH":
            t_res = handle_train_search_intent(user_text, session, current_request=current_request or req)
            t_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            t_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(t_res, default_intent="TRAIN_SEARCH")

        if intent == "TRAIN_SCHEDULE":
            ts_res = handle_train_schedule_intent(user_text, session)
            ts_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            ts_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(ts_res, default_intent="TRAIN_SCHEDULE")

        if intent == "LIVE_TRAIN_STATUS":
            ts_res = handle_live_train_status_intent(user_text, session)
            ts_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            ts_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(ts_res, default_intent="LIVE_TRAIN_STATUS")

        if intent == "HOTEL_SEARCH":
            h_res = handle_hotel_search_intent(user_text, session, current_request=current_request or req)
            h_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            h_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(h_res, default_intent="HOTEL_SEARCH")

        if intent == "FLIGHT_SEARCH":
            f_res = handle_flight_search_intent(user_text, session, current_request=current_request or req)
            f_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            f_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(f_res, default_intent="FLIGHT_SEARCH")

        if intent == "BUS_SEARCH":
            b_res = handle_bus_search_intent(user_text, session, current_request=current_request or req)
            b_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            b_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(b_res, default_intent="BUS_SEARCH")

        if intent == "ALTITUDE_GUIDANCE":
            t_res = coordinator.answer_tourism_query(user_text, last_tourism_place=last_tourism_place or state.get("last_tourism_place"))
            t_res["intent"] = "ALTITUDE_GUIDANCE"
            t_res["last_tourism_place"] = t_res.get("last_tourism_place") or last_tourism_place
            t_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(t_res, default_intent="ALTITUDE_GUIDANCE")

        if intent == "TREKKING_GUIDANCE":
            t_res = coordinator.answer_tourism_query(user_text, last_tourism_place=last_tourism_place or state.get("last_tourism_place"))
            t_res["intent"] = "TREKKING_GUIDANCE"
            t_res["last_tourism_place"] = t_res.get("last_tourism_place") or last_tourism_place
            t_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(t_res, default_intent="TREKKING_GUIDANCE")

        if intent == "BHAVAN_TRANSPORT":
            t_res = coordinator.answer_tourism_query(user_text, last_tourism_place=last_tourism_place or state.get("last_tourism_place"))
            t_res["intent"] = "BHAVAN_TRANSPORT"
            t_res["last_tourism_place"] = t_res.get("last_tourism_place") or last_tourism_place
            t_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(t_res, default_intent="BHAVAN_TRANSPORT")

        if intent == "BUDGET_CALCULATION":
            b_res = handle_budget_calculation_intent(user_text, session)
            b_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            b_res["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
            return _finalize(b_res, default_intent="BUDGET_CALCULATION")

        if intent == "GREETING":
            g_res = {
                "intent": "GREETING",
                "status": "SUCCESS",
                "reply": (
                    "🙏 **Jai Mata Di!** Welcome to Yatra AI, your devoted pilgrimage and travel companion for Maa Vaishno Devi. "
                    "How may I assist your holy yatra today? You can ask me about live Katra & Bhawan weather, trek routes, "
                    "mandatory RFID registration guidelines, available trains, or planning a complete personalized itinerary."
                ),
                "session_id": sid,
                "request": req,
            }
            return _finalize(g_res, default_intent="GREETING")

        if intent == "ACKNOWLEDGMENT":
            a_res = {
                "intent": "ACKNOWLEDGMENT",
                "status": "SUCCESS",
                "reply": (
                    "🙏 **Jai Mata Di!** You are most welcome! May Mata Rani shower Her divine blessings upon your holy pilgrimage. "
                    "Whenever you need assistance with Katra weather, helicopter updates, train schedules, or trek advisories, "
                    "I am always here to guide you."
                ),
                "session_id": sid,
                "request": req,
            }
            return _finalize(a_res, default_intent="ACKNOWLEDGMENT")

        if intent == "HELP":
            h_res = {
                "intent": "HELP",
                "status": "SUCCESS",
                "reply": (
                    "🙏 **Jai Mata Di!** Here is what I can assist you with for your sacred pilgrimage to Maa Vaishno Devi:\n\n"
                    "- 🌦️ **Live Weather & Altitude Guidance:** Real-time conditions across Katra, Ardhkuwari, Bhawan, and Bhairon Temple.\n"
                    "- 🚆 **Transport & Connectivity:** Direct and connecting trains, flights, and bus schedules from any Indian city.\n"
                    "- 🏨 **Verified Accommodations:** Official Shrine Board bhavans and registered Katra hotels.\n"
                    "- 📜 **Track & Trek Advisories:** Official notices on Traditional Track vs Tarakote Marg, battery cars, palkis, and ropeway.\n"
                    "- 🎫 **Registration & Rules:** Mandatory RFID Yatra Registration Parchi guidelines, valid IDs, and sanctum dress code.\n"
                    "- 🗺️ **Comprehensive Itinerary:** Customized multi-day pilgrimage planning with real-time budget optimization."
                ),
                "session_id": sid,
                "request": req,
            }
            return _finalize(h_res, default_intent="HELP")

        # 5. Day-by-day Itinerary modification
        if intent == "ITINERARY":
            itin_res = coordinator.process_itinerary_message(
                user_text,
                current_request=current_request if current_request is not None else req,
                current_itinerary=state.get("itinerary") or current_itinerary,
                last_context=last_itinerary_context or state.get("last_itinerary_context"),
            )
            itin_res["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
            if itin_res.get("itinerary"):
                session_store.update_session(sid, updates={"itinerary": itin_res["itinerary"], "last_itinerary_context": itin_res.get("last_itinerary_context")})
            return _finalize(itin_res, default_intent="ITINERARY")

        # 6. Check for ambiguous change request ("change that", "update trip")
        if legacy_agent.is_ambiguous_change(user_text):
            diff_check = legacy_agent.get_changed_fields(current_request, req)
            if not diff_check:
                amb_res = {
                    "intent": "TRIP_PLANNING",
                    "reply": (
                        "What would you like to change — duration, travel mode, number of travellers, starting city, or something else?"
                    ),
                    "plan": {"status": "NEEDS_INFO", "message": "Clarification required."},
                    "request": current_request or req,
                    "itinerary": state.get("itinerary") or current_itinerary,
                    "recommendation": None,
                    "diff": {},
                    "session_id": sid,
                    "last_tourism_place": last_tourism_place or state.get("last_tourism_place"),
                    "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),
                }
                return _finalize(amb_res, default_intent="TRIP_PLANNING")

        # 7. Trip Planning Flow: Extract & Merge Requirements
        old_req = dict(req)
        updated_req = extract_trip_requirements(user_text, current_req=req)
        missing = detect_missing_mandatory_fields(updated_req)

        # Phase 14.4.2: If origin requires clarification (e.g. Bilaspur HP vs CG, Anandpur, or invalid/unresolved),
        # clarify origin BEFORE asking secondary questions (pax count or dates)
        orig_cand = updated_req.get("origin")
        if orig_cand and "," not in orig_cand:
            try:
                from agents import conversation_state
                guidance = conversation_state.get_transit_guidance_for_origin(orig_cand)
                if guidance.get("requires_clarification") and guidance.get("clarification_prompt"):
                    clarification_prompt = guidance["clarification_prompt"]
                    clarification_res = {
                        "intent": "TRIP_PLANNING",
                        "status": "NEEDS_CLARIFICATION",
                        "reply": clarification_prompt,
                        "plan": {"status": "NEEDS_CLARIFICATION", "message": clarification_prompt, "options": []},
                        "requirements": updated_req,
                        "request": updated_req,
                        "missing_fields": missing,
                        "itinerary": None,
                        "budget_evaluation": None,
                        "selected_options": None,
                        "diff": {},
                        "recommendation": None,
                        "session_id": sid,
                        "last_tourism_place": last_tourism_place or state.get("last_tourism_place"),
                        "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),
                    }
                    session_store.update_session(
                        sid,
                        updates={
                            "requirements": updated_req,
                            "pending_ambiguity": orig_cand.lower(),
                        },
                        status="AWAITING_CLARIFICATION",
                    )
                    return _finalize(clarification_res, default_intent="TRIP_PLANNING")
            except Exception as exc:
                logger.warning("Error checking origin clarification in orchestrator: %s", exc)

        # If mandatory fields are missing: adhere to 'Answer First, Question Later' (Phase 14)
        if missing:
            question = generate_missing_info_question(missing, updated_req)
            substantive_answer = ""
            tl = user_text.lower()

            # Check if the user's planning prompt also contained a specific question
            if any(w in tl for w in ("weather", "temperature", "forecast", "climate", "how cold", "rain")):
                try:
                    import weather
                    w_res = weather.get_weather_summary("Katra")
                    substantive_answer = f"**Weather Update:** {w_res.get('summary', 'Pleasant conditions in Katra')}. Light woollens are recommended for the evening trek to Bhawan (~5,200 ft).\n\n"
                except Exception:
                    pass
            if any(w in tl for w in ("how many days", "how long", "recommended days", "ideal duration")):
                substantive_answer += "For a Vaishno Devi pilgrimage, most devotees plan a **2 to 3 days trip** to comfortably travel, rest at Katra, and undertake the holy trek.\n\n"
            elif any(w in tl for w in ("elderly", "senior", "parents", "wheelchair", "battery car", "best time", "when to visit", "routes", "route", "trek", "langar", "lockers", "food")):
                try:
                    from rag.retriever import get_retriever
                    retriever = get_retriever()
                    rag_res = retriever.retrieve(user_text, conversation_context={"last_tourism_place": last_tourism_place or "Katra"})
                    if rag_res.get("relevant_found") and rag_res.get("context"):
                        clean_lines = [l for l in rag_res["context"].split("\n") if not l.startswith("--- Source:")]
                        substantive_answer = "\n".join(clean_lines[:8]).strip() + "\n\n"
                except Exception:
                    pass

            is_greeting = any(g in tl for g in ("jai mata di", "hello", "hi", "namaste", "pranam", "greetings"))
            prior_assistant_msgs = [m for m in session_store.get_messages(sid) if m.get("role") == "assistant"]
            if not is_greeting and len(prior_assistant_msgs) > 0:
                if question.startswith("🙏 **Jai Mata Di!**"):
                    question = question.replace("🙏 **Jai Mata Di!**", "").strip()

            if substantive_answer:
                clean_q = question
                if clean_q.startswith("🙏 **Jai Mata Di!**"):
                    clean_q = clean_q.replace("🙏 **Jai Mata Di!**", "").strip()
                full_reply = f"{substantive_answer}{clean_q}"
            else:
                full_reply = question

            session_store.update_session(
                sid,
                updates={"requirements": updated_req, "missing_fields": missing},
                status="AWAITING_INPUT",
            )
            needs_info_res = {
                "intent": "TRIP_PLANNING",
                "status": "NEEDS_INFO",
                "reply": full_reply,
                "requirements": updated_req,
                "request": updated_req,
                "missing_fields": missing,
                "plan": {"status": "NEEDS_INFO", "message": full_reply, "options": []},
                "itinerary": None,
                "budget_evaluation": None,
                "selected_options": None,
                "diff": {},
                "recommendation": None,
                "session_id": sid,
                "last_tourism_place": last_tourism_place or state.get("last_tourism_place"),
                "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),
            }
            return _finalize(needs_info_res, default_intent="TRIP_PLANNING")

        # All mandatory requirements complete -> Coordinate Full Plan Pipeline
        diff = legacy_agent.get_changed_fields(old_req, updated_req)
        had_active_plan = bool(state.get("selected_options") and state["selected_options"].get("transport"))
        had_auth = bool(state.get("authorized_plan_version") or state.get("authorization", {}).get("granted"))

        curr_version = state.get("plan_version", 1)
        if diff and had_active_plan:
            new_version = curr_version + 1

            # Archive previous booking if one exists for earlier revision
            prior_rpa = state.get("rpa_execution") or {}
            prior_booking_id = prior_rpa.get("booking_id")
            booking_history = list(state.get("booking_history") or [])
            if prior_booking_id and not any(b.get("booking_id") == prior_booking_id for b in booking_history):
                booking_history.append({
                    "booking_id": prior_booking_id,
                    "plan_version": curr_version,
                    "status": "CONFIRMED_PRIOR_REVISION",
                    "note": f"Confirmed under Revision #{curr_version}. Prototype does not perform automatic cancellation or refunds.",
                })

            rpa_state = {
                "status": "PENDING_RECONFIRMATION" if prior_booking_id else "NOT_TRIGGERED",
                "booking_id": None,
                "plan_version": new_version,
                "previous_booking": {
                    "booking_id": prior_booking_id,
                    "plan_version": curr_version,
                    "status": "CONFIRMED_PRIOR_REVISION",
                    "note": f"Previous booking {prior_booking_id} remains on file for Revision #{curr_version}. Automatic cancellation/modification is not supported by prototype.",
                } if prior_booking_id else None,
                "screenshot_path": None,
                "logs": [],
            }

            revoked_auth = {
                "pending": True,
                "granted": False,
                "authorized_at": None,
                "authorized_for_version": None,
                "plan_version": new_version,
                "revoked_reason": "plan_modified",
            }
        else:
            new_version = curr_version
            prior_booking_id = None
            booking_history = list(state.get("booking_history") or [])
            rpa_state = state.get("rpa_execution") or {
                "status": "NOT_TRIGGERED",
                "booking_id": None,
                "plan_version": new_version,
                "screenshot_path": None,
                "logs": [],
            }
            revoked_auth = state.get("authorization") or {
                "pending": True,
                "granted": False,
                "plan_version": new_version,
            }

        plan_result = coordinate_plan(updated_req, session_id=sid, plan_version=new_version)
        plan_result["diff"] = diff
        if diff and had_active_plan:
            plan_result["status"] = "PLAN_REVISED"
            plan_result["plan_version"] = new_version
            plan_result["reply"] = format_concise_edit_reply(diff, updated_req, plan_result, new_version)
            if prior_booking_id:
                plan_result["reply"] += (
                    f"\n\n⚠️ **Notice:** Your trip details were modified (Plan Revision #{new_version}). "
                    f"Previous authorization has been reset. Note: Prior booking **{prior_booking_id}** remains on file for Revision #{curr_version} "
                    "(automatic cancellation/refunds are not supported by this prototype). "
                    f"Please review the updated plan and reply **'Confirm booking'** when ready to authorize Revision #{new_version}."
                )
            elif had_auth:
                plan_result["reply"] += (
                    f"\n\n⚠️ **Notice:** Trip plan was modified (Plan Revision #{new_version}). "
                    f"Prior authorization has been reset. Reply **'Confirm booking'** when ready to authorize (Plan Revision #{new_version})."
                )

        # Persist complete plan in session store
        session_store.update_session(
            sid,
            updates={
                "requirements": updated_req,
                "missing_fields": [],
                "selected_options": plan_result.get("selected_options"),
                "budget_evaluation": plan_result.get("budget_evaluation"),
                "itinerary": plan_result.get("itinerary"),
                "pending_options": plan_result.get("plan", {}).get("options"),
                "plan_version": new_version,
                "authorized_plan_version": None if (diff and had_auth) else state.get("authorized_plan_version"),
                "authorization": revoked_auth,
                "rpa_execution": rpa_state,
                "booking_history": booking_history,
                "pending_ambiguity": updated_req.get("origin", "").lower() if plan_result.get("status") == "NEEDS_CLARIFICATION" else None,
            },
            status="AWAITING_CLARIFICATION" if plan_result.get("status") == "NEEDS_CLARIFICATION" else ("PLAN_REVISED" if (diff and had_active_plan) else "PLAN_READY"),
        )

        if diff and had_active_plan:
            plan_result["status"] = "PLAN_REVISED"

        plan_result["plan_version"] = new_version
        plan_result["authorization"] = revoked_auth
        plan_result["intent"] = "TRIP_PLANNING"
        plan_result["last_tourism_place"] = last_tourism_place or state.get("last_tourism_place")
        plan_result["last_itinerary_context"] = last_itinerary_context or state.get("last_itinerary_context")
        return _finalize(plan_result, default_intent="TRIP_PLANNING")
    finally:
        if not turn_completed and user_msg_id:
            try:
                session_store.delete_message(user_msg_id)
            except Exception as rollback_err:
                logger.warning("Failed to rollback orphaned user message %s: %s", user_msg_id, type(rollback_err).__name__)
