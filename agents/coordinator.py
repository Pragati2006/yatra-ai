
"""
agents/coordinator.py
The orchestrator. Owns no data-fetching logic itself - it routes a
pilgrim's free-text message to the right specialist agent(s) and
assembles their outputs into one response, which is the core of the
"multi-agent" architecture:

  ConversationAgent  -> understands the message (any language) and
                         phrases replies with devotional warmth
  TransportAgent /
  DarshanAgent        -> (agent.py's build_plan, already tested) finds
                         and ranks real-timing-safe transport + darshan
                         combinations
  HotelAgent           -> (db.search_hotels) finds hotel options
  SightseeingAgent      -> (explore_data.py via ContentAgent) suggests
                         places, with real history + video links
  ItineraryAgent         -> assembles the final day-wise plan

This module doesn't touch Streamlit at all - app.py calls into it and
handles all rendering, so the agent logic stays testable on its own.
"""
import logging
import os
import re
from typing import Optional, Dict, Any, List
import agent as legacy_agent
import db
from agents import conversation_agent, content_agent, itinerary_agent, knowledge_agent, recommendation_agent, rpa_agent

logger = logging.getLogger(__name__)


def get_greeting():
    return conversation_agent.greeting()


def process_itinerary_message(user_text, current_request=None, current_itinerary=None, last_context=None):
    """Handles day-by-day itinerary queries and edits."""
    if not current_itinerary:
        if current_request:
            current_itinerary = itinerary_agent.generate_default_itinerary(current_request)
        else:
            dummy_req = {"duration_days": 4, "origin": "Delhi", "pax": 1}
            current_itinerary = itinerary_agent.generate_default_itinerary(dummy_req)

    cmd = itinerary_agent.parse_itinerary_command(user_text, itinerary=current_itinerary, context=last_context)

    if cmd.get("ambiguous"):
        return {
            "intent": "ITINERARY",
            "reply": f"🙏 **Jai Mata Di!**\n\n{cmd.get('ambiguity_prompt', 'Which activity or day would you like to modify?')}",
            "plan": {"status": "NEEDS_INFO", "message": "Clarification required."},
            "request": current_request,
            "itinerary": current_itinerary,
            "recommendation": None,
            "last_itinerary_context": last_context,
            "source": "itinerary_agent",
            "response_source": "itinerary_agent",
            "knowledge_source": "itinerary_templates",
        }

    valid, err_msg = itinerary_agent.validate_itinerary_command(current_itinerary, cmd)
    if not valid:
        return {
            "intent": "ITINERARY",
            "reply": f"🙏 **Jai Mata Di!**\n\n{err_msg}",
            "plan": {"status": "NEEDS_INFO", "message": err_msg},
            "request": current_request,
            "itinerary": current_itinerary,
            "recommendation": None,
            "last_itinerary_context": last_context,
            "source": "itinerary_agent",
            "response_source": "itinerary_agent",
            "knowledge_source": "itinerary_templates",
        }

    if cmd["action"] == "SHOW":
        reply, new_ctx = itinerary_agent.format_show_reply(current_itinerary, cmd)
        return {
            "intent": "ITINERARY",
            "reply": reply,
            "plan": None,
            "request": current_request,
            "itinerary": current_itinerary,
            "recommendation": None,
            "last_itinerary_context": new_ctx or last_context,
            "source": "itinerary_agent",
            "response_source": "itinerary_agent",
            "knowledge_source": "itinerary_templates",
        }
    else:
        updated_itinerary, edit_summary, new_ctx = itinerary_agent.apply_itinerary_edit(current_itinerary, cmd)
        full_reply = f"{edit_summary}\n\n" + itinerary_agent.format_full_itinerary_card(updated_itinerary)
        return {
            "intent": "ITINERARY",
            "reply": full_reply,
            "plan": None,
            "request": current_request,
            "itinerary": updated_itinerary,
            "recommendation": None,
            "last_itinerary_context": new_ctx or last_context,
            "source": "itinerary_agent",
            "response_source": "itinerary_agent",
            "knowledge_source": "itinerary_templates",
        }


def process_trip_message(user_text, current_request=None, current_itinerary=None, api_key=None, base_url=None):
    """Entry point for the conversational trip search.
    Returns a dict: {reply, plan, request, recommendation, itinerary} where plan is build_plan()'s output
    (status, options, etc.), reply is the natural-language message, request is the state-accumulated
    trip request dict, and recommendation is the personalized travel recommendation."""
    request = conversation_agent.understand_request(user_text, current_request=current_request, api_key=api_key, base_url=base_url)

    # Check for ambiguous change request
    if legacy_agent.is_ambiguous_change(user_text):
        diff_check = legacy_agent.get_changed_fields(current_request, request)
        if not diff_check:
            return {
                "reply": (
                    "🙏 **Jai Mata Di!**\n\n"
                    "What would you like to change — duration, travel mode, number of travellers, starting city, or something else?"
                ),
                "plan": {"status": "NEEDS_INFO", "message": "Clarification required."},
                "request": current_request or request,
                "itinerary": current_itinerary,
                "recommendation": None,
            }

    plan = legacy_agent.build_plan(request)

    # Use the selected transport mode for itinerary generation.
    # This prevents the itinerary from defaulting to Train when
    # the actual selected option is a Flight/Bus/etc.
    if (
        request
        and not request.get("mode")
        and plan.get("options")
    ):
        selected_option = plan["options"][0]
        transport = selected_option.get("transport") or selected_option.get("flight")

        if transport and transport.get("mode"):
            request["mode"] = transport["mode"]

    reply = conversation_agent.craft_reply(
        user_text,
        plan["status"],
        plan,
        api_key=api_key,
        base_url=base_url,
    )

    rec = recommendation_agent.generate_recommendation(request)

# Sync or generate itinerary

    # Sync or generate itinerary
    itinerary = current_itinerary
    if not itinerary and request and request.get("duration_days"):
        itinerary = itinerary_agent.generate_default_itinerary(request)
    elif itinerary and request and request.get("duration_days"):
        itinerary = itinerary_agent.sync_itinerary_duration(current_itinerary, request["duration_days"], request)

    # Compute edit diff if previous request existed
    diff = legacy_agent.get_changed_fields(current_request, request)
    edit_summary = ""
    if diff:
        edit_summary = legacy_agent.format_edit_confirmation(diff)

    # Assemble response
    reply_parts = []
    if edit_summary:
        reply_parts.append(edit_summary)
    if rec and (request.get("group_type") or request.get("travel_style") or request.get("trip_focus") or request.get("origin") or request.get("duration_days")):
        reply_parts.append(rec["formatted_card"])
    reply_parts.append(reply)

    final_reply = "\n\n---\n".join(reply_parts)

    return {
        "reply": final_reply,
        "plan": plan,
        "request": request,
        "itinerary": itinerary,
        "recommendation": rec,
        "diff": diff,
        "source": "trip_coordinator",
        "response_source": "conversation_agent",
        "knowledge_source": "local_catalog",
    }


def get_trip_recommendation(request):
    """Coordinator-facing wrapper for recommendation engine."""
    return recommendation_agent.generate_recommendation(request)


def detect_intent(user_text):
    """Coordinator-facing wrapper so app.py does not import conversation_agent."""
    return conversation_agent.detect_intent(user_text)


def answer_tourism_query(user_text, last_tourism_place=None, current_request=None):
    """
    Handles tourism queries using MongoDB-grounded LangChain tool-calling
    powered by Groq (openai/gpt-oss-20b).
    When MongoDB retrieval and LLM response succeed, uses the grounded LLM answer.
    When MongoDB or Groq is unavailable, smoothly falls back to the local knowledge agent.
    """
    # Step 1: Query the MongoDB-powered LangChain agent only if MongoDB Atlas is actively connected.
    mongodb_result = {}
    mongodb_error = None

    try:
        import mongo_db
        if mongo_db.is_available() and os.environ.get("GROQ_API_KEY"):
            import mongodb_agent
            mongodb_result = mongodb_agent.answer_mongodb_query(user_text)
    except Exception as exc:
        mongodb_error = str(exc)

    # Condition A: MongoDB retrieval and LLM response succeeded
    if (
        mongodb_result.get("status") in ("success", "no_tool_call")
        and mongodb_result.get("answer")
        and len(mongodb_result["answer"].strip()) > 10
    ):
        llm_reply = mongodb_result["answer"].strip()

        # Extract place and classification for context tracking without running duplicate local pipeline
        query_kind = knowledge_agent.classify_tourism_topic(user_text, last_place=last_tourism_place)
        specific_places = knowledge_agent.find_specific_places(user_text)
        detected_place = specific_places[0]["name"] if specific_places else last_tourism_place

        return {
            "intent": "TOURISM",
            "reply": llm_reply,
            "plan": None,
            "request": current_request,
            "itinerary": None,
            "query_kind": query_kind,
            "last_tourism_place": detected_place,
            "mongodb_tool_results": mongodb_result.get("tool_results", []),
            "mongodb_status": mongodb_result.get("status", "success"),
            "source": "mongodb_llm",
            "response_source": mongodb_result.get("response_source", "mongodb_llm"),
            "knowledge_source": mongodb_result.get("knowledge_source", "atlas"),
        }

    # Condition B / C / D: Fallback to existing local knowledge_agent, RAG, and conversation_agent
    knowledge = knowledge_agent.get_jk_tourism_knowledge(
        user_text,
        last_place=last_tourism_place,
    )

    # Check if query is asking for facilities, safety, regulations, or practical guidance
    is_facility_or_guidance = bool(re.search(
        r"\b(locker|lockers|cloakroom|cloakrooms|luggage|storage|deposit|langar|langars|bhojanalaya|bhojanalayas|food|eating|meals?|kitchen|wheelchair|wheelchairs|elderly|senior|seniors|parents|disabled|disability|handicapped|battery car|battery cars|electric car|electric vehicle|palki|palkis|palanquin|pithoo|porter|prohibited|banned|allowed|not allowed|forbidden|rules inside|restrictions|items|leather|tobacco|alcohol|drone|night|safe at night|trek at night|illuminated|lighting|dark|helicopter|helipad|ropeway|cable car|operating|suspended|suspension|rfid|parchi|yatra slip|registration counter|how to register|mandatory pass|medical|dispensary|oxygen|emergency|doctor|hospital|first aid|ambulance|what to wear|dress code|documents|id card)\b",
        user_text,
        re.IGNORECASE
    ))

    # If legacy knowledge agent did not match a specific topic or place, query RAG knowledge foundation
    is_general_unmatched = (
        knowledge.get("query_kind") == "general"
        and not knowledge.get("matched_places")
    )

    rag_used = False
    rag_sources = []
    if is_facility_or_guidance or is_general_unmatched:
        try:
            from rag.retriever import get_retriever
            retriever = get_retriever()
            rag_res = retriever.retrieve(
                user_text,
                conversation_context={"last_tourism_place": last_tourism_place},
            )
            if rag_res.get("relevant_found") and rag_res.get("context"):
                rag_used = True
                rag_sources = rag_res.get("sources") or []
                clean_lines = [l for l in rag_res["context"].split("\n") if not l.startswith("--- Source:")]
                body = "\n".join(clean_lines).strip()
                top_src = rag_sources[0] if rag_sources else {}
                src_title = top_src.get("title", "Official Shri Mata Vaishno Devi Shrine Board Documentation")
                src_url = top_src.get("source_url", "")
                citation = f"\n\n*Verified Source: [{src_title}]({src_url})*" if src_url else f"\n\n*Verified Source: {src_title}*"
                reply = f"🙏 **Jai Mata Di!**\n\n{body}{citation}"
            else:
                reply = conversation_agent.format_tourism_reply(knowledge)
        except Exception as rag_err:
            logger.debug("Local RAG retrieval error in coordinator: %s", rag_err)
            reply = conversation_agent.format_tourism_reply(knowledge)
    else:
        reply = conversation_agent.format_tourism_reply(knowledge)

    result = {
        "intent": "TOURISM",
        "reply": reply,
        "plan": None,
        "request": current_request,
        "itinerary": None,
        "query_kind": "rag_knowledge" if rag_used else knowledge.get("query_kind"),
        "last_tourism_place": knowledge.get("last_place"),
        "mongodb_tool_results": mongodb_result.get("tool_results", []),
        "mongodb_status": mongodb_result.get(
            "status",
            "error" if mongodb_error else "fallback",
        ),
        "source": "rag_knowledge" if rag_used else "local_fallback",
        "response_source": "rag_retriever" if rag_used else "conversation_agent",
        "knowledge_source": "rag_foundation" if rag_used else "local_fallback",
        "knowledge_sources": rag_sources if rag_used else [],
    }

    if mongodb_error:
        result["mongodb_error"] = mongodb_error

    return result

def process_weather_message(user_text, current_request=None):
    """Handles weather guidance queries using elevation-aware weather tool."""
    import weather
    from agents import tools
    loc_query = user_text if user_text else "Katra"
    try:
        w = tools.check_weather_tool.invoke({"location": loc_query})
    except Exception:
        w = weather.get_weather_summary(loc_query)

    if w.get("status") == "UNRECOGNIZED_LOCATION":
        reply = w.get("clarification_message") or (
            f"🙏 **Jai Mata Di!** Location '{w.get('location')}' was not recognized along the Vaishno Devi trek route. "
            "Supported pilgrimage locations are:\n"
            "1. **Katra Town** (~750 m)\n"
            "2. **Ardhkuwari** (~1,400 m)\n"
            "3. **Vaishno Devi Bhawan** (~1,585 m)\n"
            "4. **Bhairon Temple** (~2,011 m)\n\n"
            "Please specify one of these locations or ask to compare them."
        )
        res = {
            "intent": "WEATHER",
            "status": "UNRECOGNIZED_LOCATION",
            "reply": reply,
            "plan": None,
            "request": current_request,
            "itinerary": None,
            "source": "weather_service",
            "response_source": "weather_service",
            "knowledge_source": "weather_service",
            "weather": w,
            "tool_execution": {
                "tool": "check_weather_tool",
                "status": "unrecognized_location",
                "results": w
            }
        }
        try:
            from utils.provenance import attach_provenance_to_response
            return attach_provenance_to_response(res)
        except Exception:
            return res

    summary = w.get("summary") or w.get("condition", "Pleasant")
    low_c = w.get("low_c", 12)
    high_c = w.get("high_c", 24)
    advisory = w.get("advisory", "")
    source = w.get("source", "seasonal_average")
    loc_name = w.get("location_name") or w.get("location") or "Katra"

    src_label = "Live Forecast (Open-Meteo)" if source == "forecast" else "Seasonal Climate Estimate"

    # Multi-location or comparison reply formatting
    if w.get("is_multi_location") and w.get("comparison"):
        comp = w["comparison"]
        loc_bullets = "\n".join([
            f"• **{l['location']} (~{l['elevation_m']} m):** {l.get('condition', 'Clear')}, {l['low_c']}°C to {l['high_c']}°C"
            for l in w.get("locations", [])
        ])
        reply = (
            "🙏 **Jai Mata Di! Pilgrimage Trek Weather Guidance & Comparison:**\n\n"
            f"{loc_bullets}\n\n"
            f"• **Elevation & Climate Comparison:** {comp.get('summary_text', '')}\n"
            f"• **Data Source:** {src_label}\n"
            f"• **Pilgrim Advisory:** {advisory}\n\n"
            f"_{w.get('disclaimer', weather.MOUNTAIN_WEATHER_DISCLAIMER)}_"
        )
    elif "bhawan" in str(user_text).lower():
        elev_val = w.get('elevation_m', 1585)
        reply = (
            "🙏 **Jai Mata Di! Vaishno Devi Bhawan Weather Guidance:**\n\n"
            f"• **Elevation:** ~{elev_val:,} m (~5,200 ft)\n"
            f"• **Condition:** {summary}\n"
            f"• **Temperature Range:** {low_c}°C to {high_c}°C\n"
            f"• **Data Source:** {src_label}\n"
            f"• **Pilgrim Advisory:** {advisory}\n\n"
            "_The Bhawan shrine (~5,200 ft) runs significantly colder than Katra town. Warm woollens and thermal wear are strongly recommended._"
        )
    elif "ardhkuwari" in str(user_text).lower() or "garbh" in str(user_text).lower():
        elev_val = w.get('elevation_m', 1400)
        reply = (
            "🙏 **Jai Mata Di! Ardhkuwari Weather Guidance:**\n\n"
            f"• **Elevation:** ~{elev_val:,} m\n"
            f"• **Condition:** {summary}\n"
            f"• **Temperature Range:** {low_c}°C to {high_c}°C\n"
            f"• **Data Source:** {src_label}\n"
            f"• **Pilgrim Advisory:** {advisory}\n\n"
            "_Midway trek milestone — keep a light jacket accessible while waiting for Garbh Joon cave Darshan._"
        )
    elif "bhairon" in str(user_text).lower():
        elev_val = w.get('elevation_m', 2011)
        reply = (
            "🙏 **Jai Mata Di! Bhairon Temple Weather Guidance:**\n\n"
            f"• **Elevation:** ~{elev_val:,} m (~6,600 ft)\n"
            f"• **Condition:** {summary}\n"
            f"• **Temperature Range:** {low_c}°C to {high_c}°C\n"
            f"• **Data Source:** {src_label}\n"
            f"• **Pilgrim Advisory:** {advisory}\n\n"
            "_Highest point of pilgrimage (~6,600 ft) — high wind exposure and sub-zero night chills in winter. Heavy woollens and windproof jacket required._"
        )
    else:
        # Default Katra Town formatting - preserves exact test expectation 'Katra Weather Guidance'
        default_note = "\n• **Selection Note:** Location was not specified; showing Katra Town base elevation (~750 m). You can also ask for Ardhkuwari, Bhawan, or Bhairon Temple." if w.get("is_default_location") else ""
        reply = (
            "🙏 **Jai Mata Di! Katra Weather Guidance:**\n\n"
            f"• **Location:** {loc_name} (~{w.get('elevation_m', 750)} m){default_note}\n"
            f"• **Condition:** {summary}\n"
            f"• **Temperature Range:** {low_c}°C to {high_c}°C\n"
            f"• **Data Source:** {src_label}\n"
            f"• **Pilgrim Advisory:** {advisory}\n\n"
            "_The Bhawan shrine (~5,200 ft) runs several degrees cooler than Katra town — pack an extra warm layer for evening treks._"
        )

    res = {
        "intent": "WEATHER",
        "reply": reply,
        "plan": None,
        "request": current_request,
        "itinerary": None,
        "source": "weather_service",
        "response_source": "weather_service",
        "knowledge_source": "weather_service",
        "weather": w,
        "tool_execution": {
            "tool": "check_weather_tool",
            "status": "success",
            "results": w
        }
    }
    try:
        from utils.provenance import attach_provenance_to_response
        return attach_provenance_to_response(res)
    except Exception:
        return res


def process_booking_message(user_text, current_request=None, pending_options=None):
    """Handles booking execution with Human-in-the-Loop confirmation gate."""
    from agents import tools

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
        "yes, authorize", "yes authorize", "yes, proceed with authorization", "i confirm"
    ]
    is_explicit_confirmed = any(w in t_lower for w in explicit_confirm_keywords) and not is_booking_intent

    opt = None
    if pending_options and pending_options.get("options"):
        opt_match = re.search(r"option\s*(\d+)", t_lower)
        if opt_match:
            idx = int(opt_match.group(1)) - 1
            if 0 <= idx < len(pending_options["options"]):
                opt = pending_options["options"][idx]
        if not opt:
            opt = pending_options["options"][0]

    pax = current_request.get("pax", 1) if current_request else 1
    tr = (opt.get("transport") or opt.get("flight") or {}) if opt else {}
    origin = (current_request.get("origin") if current_request else None) or tr.get("origin") or "your departure point"
    s = (opt.get("slot") or {}) if opt else {}

    # Human Confirmation Gate: require explicit confirmation before invoking RPA
    if not is_explicit_confirmed:
        mode_label = tr.get("mode", "Train").title()
        cat_label = s.get("category", "Normal Darshan")
        op_label = tr.get("operator", "Railways")
        price = opt.get("total_price", 1000) if opt else 1000

        reply = (
            "🙏 **Jai Mata Di! Human Confirmation Required**\n\n"
            "You are about to proceed with the following booking:\n"
            f"• **Route:** {origin} → Katra\n"
            f"• **Transport:** {mode_label} ({op_label})\n"
            f"• **Yatra Slot:** {cat_label}\n"
            f"• **Passengers:** {pax} pilgrim{'s' if pax > 1 else ''}\n"
            f"• **Estimated Total:** ₹{price}\n\n"
            "⚠️ **Confirmation Gate:** Do you authorize our Playwright RPA agent to execute this booking?\n\n"
            "_Reply **'Confirm booking'** or **'Yes, proceed'** to execute authorization._"
        )
        return {
            "intent": "BOOKING",
            "reply": reply,
            "plan": None,
            "request": current_request,
            "itinerary": None,
            "source": "rpa_playwright",
            "response_source": "rpa_agent",
            "knowledge_source": "rpa_playwright",
            "tool_execution": {
                "tool": "execute_rpa_booking_tool",
                "status": "pending_human_confirmation"
            }
        }

    # Explicit confirmation present -> execute RPA tool
    rpa_kwargs = {
        "user_name": "Guest-User",
        "pax_count": pax,
        "transport_text": f"{tr.get('mode', 'train')} from {origin}",
        "slot_text": s.get("category", "Normal Darshan"),
        "total_price": float(opt.get("total_price", 1000) if opt else 1000),
        "headless": True,
    }

    try:
        rpa_info = tools.execute_rpa_booking_tool.invoke(rpa_kwargs)
    except Exception:
        rpa_info = rpa_agent.execute_playwright_mock_booking(
            user_name="Guest-User",
            pax_count=pax,
            transport_text=f"{tr.get('mode', 'train')} from {origin}",
            slot_text=s.get("category", "Normal Darshan"),
            total_price=float(opt.get("total_price", 1000) if opt else 1000),
            headless=True,
        )

    reply = (
        "🙏 **Jai Mata Di! Booking Executed & Confirmed!**\n\n"
        f"Your confirmation ID is **{rpa_info['booking_id']}**.\n"
        f"• **Playwright RPA Execution:** Verified via browser automation agent.\n"
        f"• **Total Paid (Mock):** ₹{rpa_info.get('total_price', 1000)}\n\n"
        "May Mata Vaishno Devi grant you a safe, blessed, and memorable yatra!"
    )

    return {
        "intent": "BOOKING",
        "reply": reply,
        "plan": None,
        "request": current_request,
        "itinerary": None,
        "source": "rpa_playwright",
        "response_source": "rpa_agent",
        "knowledge_source": "rpa_playwright",
        "rpa_info": rpa_info,
        "tool_execution": {
            "tool": "execute_rpa_booking_tool",
            "status": "success",
            "results": rpa_info
        }
    }


def route_message(
    user_text,
    current_request=None,
    current_itinerary=None,
    last_tourism_place=None,
    last_itinerary_context=None,
    pending_options=None,
    api_key=None,
    base_url=None,
    session_id=None,
    llm=None,
):
    """Top-level dispatcher and entry point for the persistent conversational trip orchestrator.
    Routes to agents.orchestrator.orchestrate_conversational_turn while maintaining backward
    compatibility for existing callers and legacy wizard routes.
    """
    import agents.central_agent as central_agent
    return central_agent.process_conversational_turn(
        user_text=user_text,
        session_id=session_id,
        current_request=current_request,
        current_itinerary=current_itinerary,
        last_tourism_place=last_tourism_place,
        last_itinerary_context=last_itinerary_context,
        pending_options=pending_options,
        api_key=api_key,
        base_url=base_url,
        llm=llm,
    )


def route_message_stream(
    user_text,
    current_request=None,
    current_itinerary=None,
    last_tourism_place=None,
    last_itinerary_context=None,
    pending_options=None,
    api_key=None,
    base_url=None,
    session_id=None,
    llm=None,
):
    """Streaming generator wrapper routing to central_agent.process_conversational_turn_stream."""
    import agents.central_agent as central_agent
    return central_agent.process_conversational_turn_stream(
        user_text=user_text,
        session_id=session_id,
        current_request=current_request,
        current_itinerary=current_itinerary,
        last_tourism_place=last_tourism_place,
        last_itinerary_context=last_itinerary_context,
        pending_options=pending_options,
        api_key=api_key,
        base_url=base_url,
        llm=llm,
    )



def get_hotel_options(check_in_date, category=None):
    """HotelAgent duty - retrieves verified Katra accommodation catalog properties.
    Returns empty list on failure or unmatched search; strictly refuses to expose synthetic hotels."""
    try:
        from services.accommodation_catalog import search_hotels_for_orchestrator
        return search_hotels_for_orchestrator(check_in_date=check_in_date, category=category)
    except Exception as e:
        logger.warning(f"Error querying verified Katra accommodation catalog in coordinator: {e}")
        return []


def get_sightseeing_places(category=None):
    """SightseeingAgent duty - real places with history + video links attached."""
    return content_agent.get_all_places_enriched(category)


def get_place_content(place_name):
    return content_agent.get_enriched_place(place_name)


def get_tourism_knowledge(query: str = ""):
    """KnowledgeAgent duty - retrieves J&K tourism facts and route knowledge."""
    return knowledge_agent.get_jk_tourism_knowledge(query)


def get_personalized_places(travel_preferences: dict = None):
    """KnowledgeAgent duty - generates personalized tourist recommendations."""
    return knowledge_agent.get_personalized_recommendations(travel_preferences)


def build_final_itinerary(option, hotel=None, hotel_nights=0, sightseeing_places=None, request=None):
    return itinerary_agent.build_itinerary(option, hotel=hotel, hotel_nights=hotel_nights, sightseeing_places=sightseeing_places, request=request)


def confirm_booking(option, pax, user_name, hotel=None, hotel_nights=0, sightseeing_places=None):
    """Delegates to the existing, tested booking logic, then adds a
    devotional confirmation message on top."""
    if isinstance(option, dict) and "flight" not in option and "transport" in option:
        option = dict(option)
        option["flight"] = option["transport"]
    booking_id = legacy_agent.confirm_booking(
        option, pax, user_name,
        hotel=hotel, hotel_nights=hotel_nights,
        sightseeing_places=sightseeing_places,
    )
    blessing = conversation_agent.confirmation_blessing()
    return booking_id, blessing


def execute_rpa_demo(user_name, pax_count, transport_text, slot_text, total_price, headless=True):
    """RPAAgent duty - runs safe Playwright mock booking workflow."""
    return rpa_agent.execute_playwright_mock_booking(
        user_name=user_name,
        pax_count=pax_count,
        transport_text=transport_text,
        slot_text=slot_text,
        total_price=total_price,
        headless=headless,
    )


def check_slot_availability_rpa(requested_date=None, category=None, headless=True, max_attempts=3):
    """RPAAgent duty (Week 5 & 6) - runs Playwright task to navigate mock portal calendar, retry with backoff, and extract slot statuses."""
    return rpa_agent.check_yatra_slot_availability(
        requested_date=requested_date,
        category=category,
        headless=headless,
        max_attempts=max_attempts,
    )


def process_availability_message(user_text, session_id=None, current_request=None):
    """RPAAgent duty (Week 7) - conversational availability checking wrapper routing to orchestrator with LangChain RPA tool."""
    import agents.central_agent as central_agent
    return central_agent.process_conversational_turn(
        user_text=user_text,
        session_id=session_id,
        current_request=current_request,
    )


def start_user_controlled_workflow(
    session_id: str,
    user_name: str,
    pax_count: int,
    transport_text: str,
    slot_text: str,
    total_price: float,
    checkpoint_mode: Optional[str] = None,
    headless: bool = True,
    db_path: Optional[str] = None,
):
    """RPAAgent duty (Week 8) - initiates user-controlled RPA workflow pausing at security checkpoints."""
    return rpa_agent.execute_user_controlled_booking_workflow(
        session_id=session_id,
        workflow_id=None,
        user_name=user_name,
        pax_count=pax_count,
        transport_text=transport_text,
        slot_text=slot_text,
        total_price=total_price,
        checkpoint_mode=checkpoint_mode,
        user_confirmed_action=False,
        headless=headless,
        db_path=db_path,
    )


def resume_user_controlled_workflow(
    session_id: str,
    workflow_id: str,
    user_confirmed_action: bool = True,
    manual_input_value: Optional[str] = None,
    simulate_manual_clearance: bool = False,
    headless: bool = True,
    db_path: Optional[str] = None,
):
    """RPAAgent duty (Week 8) - resumes paused RPA workflow upon explicit user confirmation and validation."""
    return rpa_agent.execute_user_controlled_booking_workflow(
        session_id=session_id,
        workflow_id=workflow_id,
        user_confirmed_action=user_confirmed_action,
        manual_input_value=manual_input_value,
        simulate_manual_clearance=simulate_manual_clearance,
        headless=headless,
        db_path=db_path,
    )


def cancel_user_controlled_workflow(
    session_id: str,
    workflow_id: str,
    reason: str = "User cancelled workflow",
    db_path: Optional[str] = None,
):
    """RPAAgent duty (Week 8) - safely cancels a paused user-controlled workflow."""
    from agents import session_store
    return session_store.cancel_user_workflow(
        workflow_id=workflow_id,
        session_id=session_id,
        reason=reason,
        db_path=db_path,
    )


def get_user_controlled_workflow_status(
    session_id: str,
    workflow_id: str,
    db_path: Optional[str] = None,
):
    """RPAAgent duty (Week 8) - retrieves current status of user-controlled workflow with session validation."""
    from agents import session_store
    return session_store.get_user_workflow(
        workflow_id=workflow_id,
        session_id=session_id,
        db_path=db_path,
    )



