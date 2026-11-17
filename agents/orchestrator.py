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

    if not req.get("origin"):
        missing.append("origin")

    if not req.get("_pax_explicit") and not req.get("group_type") and "pax" not in explicit:
        if "origin" not in missing:
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
            "sort_price": total_combo if has_fare else float("inf"),
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

    distinct_combos.sort(key=lambda c: c.get("sort_price", float("inf")))
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

    options.sort(key=lambda c: c.get("sort_price", float("inf")))
    combos = options
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

    selected_hotel = hotels[0] if hotels else None
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
        "selected_option": selected_combo,
        "hotel": selected_hotel,
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
    """Formats a concise, devotional conversational response for yatra plans."""
    origin = req.get("origin") or (transport.get("origin") if isinstance(transport, dict) else None) or "your departure city"
    pax = max(1, req.get("pax") or 1)
    duration = req.get("duration_days") or 4
    mode = (transport.get("mode") or "train").lower()

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

    rooms = budget_engine.calculate_rooms_required(pax)
    nights = max(1, duration - 1)
    grand_total = budget_eval.get("grand_total")
    total_str = f"₹{grand_total:,.0f}" if grand_total is not None else "Calculated at booking"

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

    lines = [
        f"{weather_note}{accessibility_note}🙏 **Jai Mata Di!** Your {duration}-day Vaishno Devi trip is ready for {pax} pilgrim{'s' if pax > 1 else ''} from {origin}.\n",
        f"🚆 **{origin} → Katra** by {mode}",
        f"🛕 **{slot_display}**",
        f"🏨 **{rooms} room{'s' if rooms > 1 else ''} · {nights} night{'s' if nights > 1 else ''}**",
        f"💰 **Estimated total:** {total_str}",
    ]

    # Add authentic connecting transit guidance for non-hub origins
    try:
        from agents import conversation_state
        transit_info = conversation_state.get_transit_guidance_for_origin(origin)
        if transit_info and not transit_info.get("has_verified_direct") and transit_info.get("guidance_text"):
            lines.append(f"\n📍 **Connecting Transit Guidance:** {transit_info['guidance_text']}")
    except Exception:
        pass

    if infeasible_places:
        inf_notes = []
        for inf in infeasible_places:
            p_name = inf.get("place", "Excursion")
            p_reason = inf.get("reason", f"cannot comfortably fit within a {duration}-day trip without physical exhaustion")
            inf_notes.append(f"{p_name} ({p_reason})")
        lines.append(f"\n⚠️ **Sightseeing Feasibility Advisory:** {'; '.join(inf_notes)}")

    lines.append("\nWould you like to explore your itinerary or modify anything?")
    return "\n".join(lines)


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
    res.setdefault("status", "SUCCESS")
    reply = res.get("reply", "")
    intent = res.get("intent", default_intent)
    plan_version = res.get("plan_version")
    status = res.get("status")

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
