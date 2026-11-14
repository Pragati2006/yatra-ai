"""







agents/central_agent.py







Central AI Conversational Agent & LangChain Tool-Calling Architecture for Yatra AI.















Coordinates specialist capabilities via LangChain tool calling:







- Knowledge Tool: Vaishno Devi shrine history, Katra & J&K tourism facts, Aarti timings, routes, facilities.







- Weather Tool: Live Open-Meteo forecasts, seasonal Katra/Bhawan temperature averages, trek advisories.







- Transport Tool: Search trains, flights, and buses from any origin city to Jammu/Katra.







- Yatra Planning & Budget Evaluation: Deterministic plan creation, hotel selection, slot selection, budget breakdown.







- Itinerary Modification: Day-by-day itinerary customization (adding/removing places, reordering, pacing).







- Availability Checking: Real-time slot availability verification via local mock portal.







- Booking Handoff & Intent Safeguard: Structured action card (action: NAVIGATE_TO_BOOKING) for devotee handoff.







- Human-in-the-Loop Booking Gate: Explicit human authorization required before triggering Playwright RPA.















Architecture:







- Primary Engine: LangChain ChatGroq (llama-3.3-70b-versatile / llama-3.1-8b-instant) with bind_tools for multi-turn reasoning and tool selection.







- Resilience: Crisp 3.0s timeout and automatic fallback to deterministic orchestrator when offline or API unavailable.







- Persistence: Multi-turn session state tracking via agents.session_store.







"""















from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError







from dataclasses import dataclass, field







from enum import Enum







import functools







import json







import logging







import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


try:

    from dotenv import load_dotenv

    load_dotenv()

except ImportError:

    pass








import re







import time
import threading







from datetime import date, datetime, timedelta







from typing import Any, Callable, Dict, List, Optional, Tuple, Union















try:







    from langchain_groq import ChatGroq







except ImportError:







    ChatGroq = None















from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage







from langchain_core.tools import tool















import uuid

import db







import explore_data







import weather







import yatra_info







from agents import (







    budget_engine,







    conversation_agent,

    conversation_state,







    itinerary_agent,







    knowledge_agent,







    recommendation_agent,







    rpa_agent,







    session_store,







)







import agent as legacy_agent







from utils.logger import log_event















logger = logging.getLogger(__name__)















# -----------------------------------------------------------------------------







# 1. CENTRAL AI AGENT SYSTEM PROMPTS & PERSONA







# -----------------------------------------------------------------------------















CENTRAL_AGENT_SYSTEM_PROMPT = """
You are Yatra AI, an intelligent, warm, context-aware pilgrimage and travel companion for Maa Vaishno Devi Yatra and Jammu & Kashmir tourism.

Conversational Persona & Tone:
- Warm, welcoming, respectful, thoughtful, knowledgeable, and natural.
- Speak as an experienced local guide who understands both sacred reverence and practical logistics.
- Adapt tone: direct and friendly for general queries; structured and reassuring for travel planning; calm and supportive for anxious pilgrims; grounded and accurate for facts.

Greeting Policy:
- Offer the traditional greeting ("🙏 Jai Mata Di!") on initial greetings or when the user initiates devotional remarks.
- DO NOT repeat greetings, robotic salutations ("As an AI...", "Processing..."), or excessive emojis on subsequent messages or follow-ups.

"Answer First, Question Later" Policy:
- ALWAYS answer the user's specific question first before asking for anything else.
- If the user asks about weather, facilities, or attractions, answer directly and helpfully.
- When planning a trip, provide a helpful framework first, then ask at most ONE relevant question at a time. Never barrage the user with questionnaires.

Context Retention & Natural Indian Speech:
- Understand Indian English, informal phrases, and corrections ("Actually 4 of us", "What about bus?", "Weather first please").
- NEVER ask for details already established in conversation state (origin, passenger count, destination).
- Accept ANY Indian city as origin (e.g., Delhi, Pune, Chandigarh, Jaipur, Bhopal) and guide travel accordingly.

Factual Grounding & Honesty:
- Ground all facts in retrieved knowledge from official tools.
- Never invent travel dates, darshan slots, prices, or live train positions (static timetables only).
- When a service or tool is unavailable, explain honestly without fabricating details.
- CRITICAL SAFEGUARD: Never confirm bookings autonomously; booking requires explicit human confirmation via the booking wizard.
"""















# -----------------------------------------------------------------------------







# 2. LANGCHAIN TOOL DEFINITIONS







# -----------------------------------------------------------------------------















@tool







def search_yatra_knowledge(







    query: str,







    domain: Optional[str] = None,







    location: Optional[str] = None,







    language: Optional[str] = "en",







) -> dict:







    """Retrieves verified pilgrimage, religious tourism, historical, geographical,







    cultural, and travel guidance from the Yatra AI RAG knowledge foundation.







    Covers:







    - Vaishno Devi pilgrimage (history, sacred Pindies, Garbh Joon cave, Banganga, Bhairavnath)







    - Yatra registration & RFID passes, mandatory photo IDs, counters, rules







    - Trek routes (Traditional 13km, Tarakote Marg 14km, battery cars, helicopter, ropeway)







    - Pilgrim facilities (langars, 24x7 medical dispensaries, oxygen kiosks, cloakrooms, helplines)







    - J&K destinations (Patnitop, Sanasar, Shiv Khori cave, Jammu city heritage, Kashmir Valley)







    - Dogra cultural heritage, Navratri celebrations, regional cuisine







    - Frequently asked questions and practical pilgrim guidance















    Args:







        query: Natural language question or search query.







        domain: Optional knowledge domain ('vaishno_devi_pilgrimage', 'registration_guidance',







                 'routes_and_trekking', 'jk_regional_tourism', 'faqs', 'cultural_heritage').







        location: Optional location name (e.g. 'Katra', 'Ardhkuwari', 'Patnitop', 'Shiv Khori', 'Bhawan').







        language: Language code, defaults to 'en'.







    """







    from rag.retriever import get_retriever







    retriever = get_retriever()







    search_q = query







    if location and location.lower() not in query.lower():







        search_q = f"{location} {query}".strip()















    res = retriever.retrieve(query=search_q, domain=domain)















    snippets = [s["excerpt"] for s in res.get("sources", [])]







    source_titles = [s["title"] for s in res.get("sources", [])]







    source_urls = [s["source_url"] for s in res.get("sources", [])]















    return {







        "query": query,







        "answer_context": res.get("context", ""),







        "snippets": snippets,







        "source_titles": source_titles,







        "source_urls": source_urls,







        "sources": res.get("sources", []),







        "source_provenance": res.get("source_provenance", []),







        "retrieval_score": res.get("top_score", 0.0),







        "knowledge_domain": domain or (res.get("sources", [{}])[0].get("domain") if res.get("sources") else "general"),







        "retrieved_at": res.get("retrieved_at", ""),







        "confidence_assessment": "high" if res.get("top_score", 0.0) >= 0.65 else ("moderate" if res.get("top_score", 0.0) >= 0.45 else "low"),







        "relevant_found": res.get("relevant_found", False),







        "disclaimer": res.get("disclaimer"),







        "location": location,







    }























@tool







def get_tourism_knowledge(query: str = "", place: Optional[str] = None) -> dict:







    """Retrieves verified Jammu & Kashmir tourism information, Vaishno Devi shrine history,







    Aarti timings, registration guidelines, trek routes, facilities, and local attractions.















    Args:







        query: General tourism query or topic (e.g. 'aarti timings', 'yatra registration', 'history').







        place: Optional specific place name (e.g. 'Bhairavnath Temple', 'Ardhkuwari Cave', 'Patnitop').







    """







    search_term = place if place else query







    if not search_term:







        search_term = "Vaishno Devi"















    # 1. Search place in local exploration catalog







    place_info = explore_data.get_place_by_name(search_term)







    if not place_info:







        # Check alias lookup







        canonical_name = itinerary_agent.match_place_name(search_term)







        if canonical_name:







            place_info = explore_data.get_place_by_name(canonical_name)















    # 2. Search local knowledge agent







    knowledge = knowledge_agent.get_jk_tourism_knowledge(search_term)















    # 3. Search Yatra essential information







    y_info = None







    q_low = search_term.lower()







    if "aarti" in q_low:







        y_info = yatra_info.get_aarti_timings()







    elif "register" in q_low or "registration" in q_low or "slip" in q_low:







        y_info = yatra_info.get_registration_info()







    elif "pack" in q_low:







        y_info = yatra_info.get_packing_guidance()







    elif "route" in q_low:







        y_info = yatra_info.get_route_options()







    elif "facility" in q_low or "facilities" in q_low:







        y_info = yatra_info.get_facilities()







    elif "help" in q_low or "helpline" in q_low:







        y_info = yatra_info.get_helpline()















    result = {







        "query": search_term,







        "place": place_info.get("name") if place_info else (knowledge.get("place") or search_term),







        "category": place_info.get("category", "Pilgrimage") if place_info else "Pilgrimage",







        "description": place_info.get("description") if place_info else knowledge.get("description", ""),







        "historical_background": place_info.get("historical_background") if place_info else knowledge.get("history", ""),







        "timings": place_info.get("timings") if place_info else knowledge.get("timings", ""),







        "entry_fee": place_info.get("entry_fee", "Free entry") if place_info else "Free entry",







        "yatra_info": y_info if y_info else None,







        "source": "knowledge_agent",







        "source_name": "Yatra AI Regional Tourism Catalog",







        "source_type": "curated_data",







        "freshness_status": "not_applicable",







        "verification_status": "verified_curated_source",







    }







    return result























@tool







def check_weather_guidance(location: str = "Katra") -> dict:







    """Provides elevation-aware weather forecasts, seasonal temperature ranges, elevation







    differences, and pilgrim trek advisories for Katra Town, Ardhkuwari, Vaishno Devi Bhawan,







    and Bhairon Temple.















    Args:







        location: City, shrine location, or comparison query (e.g. 'Katra', 'Bhawan',







                  'Ardhkuwari', 'Bhairon', 'Compare Katra and Bhawan'). Defaults to 'Katra'.







    """







    try:







        w_summary = weather.get_multi_location_weather(location)







    except Exception as exc:







        w_summary = {







            "source": "seasonal_average",







            "summary": "Pleasant and cool",







            "condition": "Pleasant and cool",







            "low_c": 12,







            "high_c": 24,







            "advisory": f"Weather fallback active: {exc}",







            "location": location,







            "elevation_m": 750,







            "freshness_status": "fallback",







            "weather_type": "seasonal_estimate",







            "verification_status": "seasonal_estimate",







            "source_name": "Seasonal Climate Patterns (Trikuta Hills / Katra)",







            "source_url": "https://maavaishnodevi.org",







            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),







            "data_timestamp": None,







            "disclaimer": weather.SEASONAL_FALLBACK_DISCLAIMER,







            "locations": [],







            "comparison": None,







        }















    # Handle unrecognized foreign locations immediately with clarification schema







    if w_summary.get("status") == "UNRECOGNIZED_LOCATION":







        return w_summary















    # Maintain strict backwards compatibility for exact location casing if Katra was passed







    out_loc = "Katra" if location.strip().lower() == "katra" else w_summary.get("location", location)















    return {







        "location": out_loc,







        "canonical_location": w_summary.get("location_name", out_loc),







        "location_key": w_summary.get("location_key", "katra"),







        "condition": w_summary.get("condition") or w_summary.get("summary", "Pleasant"),







        "summary": w_summary.get("summary", "Pleasant"),







        "low_c": w_summary.get("low_c", 12),







        "high_c": w_summary.get("high_c", 24),







        "temperature_c": w_summary.get("temperature_c"),







        "apparent_temperature_c": w_summary.get("apparent_temperature_c"),







        "precipitation_mm": w_summary.get("precipitation_mm", 0.0),







        "precipitation_probability_pct": w_summary.get("precipitation_probability_pct", 0),







        "wind_speed_kmh": w_summary.get("wind_speed_kmh", 0.0),







        "latitude": w_summary.get("latitude", 32.99),







        "longitude": w_summary.get("longitude", 74.93),







        "elevation_m": w_summary.get("elevation_m", 750),







        "source": w_summary.get("source", "seasonal_average"),







        "source_name": w_summary.get("source_name", "Open-Meteo Weather API"),







        "source_url": w_summary.get("source_url", "https://open-meteo.com"),







        "retrieval_timestamp": w_summary.get("retrieval_timestamp") or datetime.now(timezone.utc).isoformat(),







        "data_timestamp": w_summary.get("data_timestamp"),







        "freshness_status": w_summary.get("freshness_status", "fallback"),







        "weather_type": w_summary.get("weather_type", "seasonal_estimate"),







        "verification_status": w_summary.get("verification_status", "seasonal_estimate"),







        "disclaimer": w_summary.get("disclaimer", weather.MOUNTAIN_WEATHER_DISCLAIMER),







        "advisory": w_summary.get("advisory", "Pack comfortable walking shoes and warm layers for the Bhawan trek."),







        "bhawan_elevation_note": "The Bhawan shrine (~5,200 ft) is typically 4°C to 7°C colder than Katra town. Warm woollens are recommended for evening darshan.",







        "locations": w_summary.get("locations", []),







        "is_multi_location": w_summary.get("is_multi_location", False),







        "comparison": w_summary.get("comparison"),







    }























@tool







def search_transport_options(







    origin: str,







    start_date: Optional[str] = None,







    end_date: Optional[str] = None,







    mode: Optional[str] = None,







    pax: Optional[int] = 1,







) -> dict:







    """Searches available transport options (trains, flights, buses) from the pilgrim's origin







    city to Jammu/Katra for given dates and passenger count.







    Uses the Unified Live Data Architecture under DataDomain.TRANSPORT for authentic,







    curated Indian Railways timetable schedules with honest provenance.















    Args:







        origin: Departure city (e.g. 'Delhi', 'Mumbai', 'Varanasi', 'Surat').







        start_date: Outbound travel date in YYYY-MM-DD format.







        end_date: Inbound/return travel date in YYYY-MM-DD format.







        mode: Optional travel mode filter ('train', 'flight', 'bus').







        pax: Number of pilgrims/travellers (default 1).







    """







    if not origin or not str(origin).strip():

        return {

            "status": "MISSING_ORIGIN",

            "message": "Please specify your departure city or town to check suitable travel options to Katra.",

            "options": [],

            "count": 0,

            "origin": "",

            "requires_clarification": True,

        }



    pax_val = max(1, pax or 1)







    formatted_options = []







    source_name = "Curated Indian Railways Vaishno Devi Corridor Schedules"







    source_type = "curated_data"







    freshness_status = "cached"







    verification_status = "verified_curated_source"















    include_trains = not mode or mode.lower() in ("train", "rail", "railway")







    include_flights = not mode or mode.lower() in ("flight", "flights", "air")







    include_buses = not mode or mode.lower() in ("bus", "buses")















    # 1. Query Curated Railway Adapter via Live Data Service Manager for trains







    if include_trains:







        try:







            from services.live_data.manager import get_live_data_manager







            from services.live_data.contracts import ProviderRequest, DataDomain







            mgr = get_live_data_manager()







            req = ProviderRequest(







                domain=DataDomain.TRANSPORT.value,







                location=origin,







                params={







                    "origin": origin,







                    "destination": "Katra",







                    "travel_date": start_date,







                    "pax": pax_val,







                },







            )







            res = mgr.fetch_data(req)







            if res.is_success and isinstance(res.data, dict):







                schedules = res.data.get("schedules", [])







                for s in schedules:



                    formatted_options.append({



                        "id": f"train_{s.get('train_number')}",



                        "mode": "train",



                        "operator": "Indian Railways",



                        "transport_no": f"{s.get('train_number')} {s.get('train_name')}",



                        "train_name": f"{s.get('train_number')} {s.get('train_name')}",



                        "route": f"{s.get('origin_station_name', origin)} → {s.get('destination_station_name', 'Katra')}",



                        "origin": s.get("origin_station_name", origin),



                        "destination": s.get("destination_station_name", "Katra"),



                        "departure": s.get("departure_time", "N/A"),



                        "departure_time": s.get("departure_time", "N/A"),



                        "arrival": s.get("arrival_time", "N/A"),



                        "arrival_time": s.get("arrival_time", "N/A"),



                        "price": None,



                        "fare": None,



                        "price_per_pax": None,



                        "total_transport_cost": None,



                        "indicative_fare_min": None,



                        "indicative_fare_max": None,



                        "fare_classification": "UNAVAILABLE",



                        "fare_disclaimer": s.get("fare_disclaimer") or (

                            "Railway fares are unavailable in static demonstration registry. Real-time booking fares and "

                            "availability must be checked on the official IRCTC portal (irctc.co.in)."

                        ),



                        "seats_available": None,



                        "availability_verified": False,



                        "seat_availability": "NOT_CHECKED",



                        "status": "TIMETABLE_SCHEDULE",



                        "is_connecting": False,



                        "is_live_status": False,



                        "travel_classes": s.get("travel_classes", []),



                        "days_of_operation": s.get("days_of_operation", []),



                        "route_verification": s.get("route_verification"),



                        "operator_verification": s.get("operator_verification"),



                        "timetable_verification": s.get("timetable_verification"),



                        "fare_verification": s.get("fare_verification"),



                        "route_note": (



                            "Curated railway route guidance. "



                            "Timetable and live delay telemetry not connected; verify with NTES (139). "



                            "Fares must be checked on the official IRCTC portal (irctc.co.in)."



                        ),



                    })







                if res.source_name:







                    source_name = res.source_name







                if res.source_type:







                    source_type = res.source_type







                if res.verification_status:







                    verification_status = res.verification_status







        except Exception as exc:







            logger.debug("Failed querying live data manager for trains: %s", exc)















    # 2. Check for route coverage limitation (Phase 9.7.3A remediation)







    coverage_limitation = None







    if include_trains and not any(opt.get("mode") == "train" for opt in formatted_options):







        # CRITICAL SAFETY RULE (Phase 9.7.3A): Never fall back to synthetic train datasets.







        # If origin route is not covered by curated express schedules, return explicit coverage limitation.







        coverage_limitation = {







            "mode": "train",







            "status": "ROUTE_NOT_IN_CURATED_REGISTRY",







            "origin": origin,







            "destination": "Katra / Jammu",







            "message": (







                f"No direct verified express trains found in the curated Katra/Jammu railway timetable for origin '{origin}'. "







                "Curated verified routes currently cover primary corridors: New Delhi (NDLS), Mumbai (BDTS), Indore (INDB), "







                "Rishikesh (YNRK), Ambala (UMB), and Ludhiana (LDH). For other origins, pilgrims should check connecting trains "







                "via New Delhi or Jammu Tawi using IRCTC or call NTES at 139."







            ),







            "supported_origins": [







                "Delhi / New Delhi (NDLS)",







                "Mumbai (BDTS)",







                "Indore (INDB)",







                "Rishikesh (YNRK)",







                "Ambala Cantt (UMB)",







                "Ludhiana (LDH)",







                "Jammu (JAT)",







            ],







        }















    # 3. Query Curated Flight Adapter via Live Data Service Manager for flights (Phase 9.8.2)

    flight_coverage_limitation = None

    if include_flights:

        try:

            from services.live_data.manager import get_live_data_manager

            from services.live_data.contracts import ProviderRequest

            mgr = get_live_data_manager()

            req = ProviderRequest(

                domain="transport",

                location=origin,

                params={"origin": origin, "destination": "Jammu", "travel_date": start_date},

            )

            flight_res = mgr.execute_request(req, provider_id="curated_flight_schedules")

            if flight_res.is_success and isinstance(flight_res.data, dict):

                flight_schedules = flight_res.data.get("schedules", [])

                for opt in flight_schedules[:4]:

                    formatted_options.append({

                        "id": f"flight_{opt.get('route_id')}",

                        "mode": "flight",

                        "airline": opt.get("airline_name"),

                        "operator": opt.get("airline_name", "Scheduled Airline"),

                        "transport_no": f"{opt.get('airline_name')} {opt.get('flight_number')}" if opt.get("flight_number") else opt.get("airline_name"),

                        "flight_no": opt.get("flight_number") or opt.get("route_id"),

                        "route": f"{opt.get('origin_airport_code', origin)} -> {opt.get('destination_airport_code', 'IXJ')}",

                        "origin": opt.get("origin_city", origin),

                        "origin_airport_code": opt.get("origin_airport_code"),

                        "origin_airport_name": opt.get("origin_airport_name"),

                        "destination": opt.get("destination_city", "Jammu"),

                        "destination_airport_code": opt.get("destination_airport_code", "IXJ"),

                        "destination_airport_name": opt.get("destination_airport_name"),

                        "route_type": opt.get("route_type", "DIRECT"),

                        "layover_airports": opt.get("layover_airports", []),

                        "departure": opt.get("departure_time"),

                        "departure_time": opt.get("departure_time"),

                        "arrival": opt.get("arrival_time"),

                        "arrival_time": opt.get("arrival_time"),

                        "duration_hours": opt.get("duration_hours"),

                        "estimated_duration_desc": opt.get("estimated_duration_desc"),

                        "schedule_type": opt.get("schedule_type"),

                        "indicative_fare_min": opt.get("indicative_fare_min"),

                        "indicative_fare_max": opt.get("indicative_fare_max"),

                        "fare_classification": opt.get("fare_classification", "ESTIMATED_MARKET_TARIFF"),

                        "fare_disclaimer": opt.get("fare_disclaimer"),

                        "fare": None,

                        "price": None,

                        "price_per_pax": None,

                        "total_transport_cost": None,

                        "seats_available": None,

                        "is_live_status": False,

                        "is_connecting": opt.get("route_type") == "CONNECTING" or (opt.get("route_type") == "ROUTE_GUIDANCE_ONLY" and bool(opt.get("layover_airports"))),

                        "source_type": "indicative_data",

                        "route_note": "Curated DGCA timetable guidance demonstration option; verify real-time airfares on airline portal.",

                        "ground_transfer_advisory": "Jammu Airport (IXJ) is ~50 km from Katra (~1.5h by prepaid taxi directly from arrivals terminal; public JKRTC buses depart from Jammu Railway Station ~8 km away).",

                        "route_verification": opt.get("route_verification"),

                        "airline_verification": opt.get("airline_verification"),

                        "timetable_verification": opt.get("timetable_verification"),

                        "fare_verification": opt.get("fare_verification"),

                    })

                if not flight_schedules:

                    search_meta = flight_res.data.get("search_metadata", {})

                    flight_coverage_limitation = {

                        "mode": "flight",

                        "status": search_meta.get("status", "ROUTE_NOT_IN_CURATED_FLIGHT_REGISTRY"),

                        "origin": origin,

                        "destination": "Jammu (IXJ)",

                        "message": search_meta.get("message") or f"Direct or connecting flight guidance from {origin} to Jammu (IXJ) is not available in the curated registry.",

                    }

        except Exception as exc:

            logger.debug("Failed querying live data manager for flights: %s", exc)



        if not flight_coverage_limitation and not any(o.get("mode") == "flight" for o in formatted_options):

            flight_coverage_limitation = {

                "mode": "flight",

                "status": "ROUTE_NOT_IN_CURATED_FLIGHT_REGISTRY",

                "origin": origin,

                "destination": "Jammu (IXJ)",

                "message": (

                    f"Flight guidance from {origin} to Jammu (IXJ) is not available in the curated registry. "

                    f"Pilgrims travelling from {origin} can fly via New Delhi (DEL layover) or check direct railway options."

                ),

            }







    # 4. Query Curated Bus Adapter via Live Data Service Manager for buses (Phase 9.8.1)







    bus_coverage_limitation = None







    if include_buses:







        try:







            from services.live_data.manager import get_live_data_manager







            from services.live_data.contracts import ProviderRequest, DataDomain







            mgr = get_live_data_manager()







            bus_req = ProviderRequest(







                domain=DataDomain.TRANSPORT.value,







                location=origin,







                params={







                    "origin": origin,







                    "destination": "Katra",







                    "travel_date": start_date,







                    "pax": pax_val,







                },







            )







            bus_res = mgr.fetch_data(bus_req, provider_id="curated_bus_schedules")



            if bus_res.is_success and isinstance(bus_res.data, dict):

                bus_schedules = bus_res.data.get("schedules", [])

                for b in bus_schedules:

                    indicative_fare = b.get("indicative_fare_min") or 90

                    dep_time = b.get("departure_time")

                    arr_time = b.get("arrival_time")

                    fare_class = b.get("fare_classification", "STATUTORY_NOTIFIED_PER_KM_SLAB")



                    # Honest pricing: Statutory slabs and seasonal market ranges are not confirmed booking prices

                    item_fare = None



                    formatted_options.append({

                        "id": b.get("service_id"),

                        "mode": "bus",

                        "operator": b.get("operator_name", "JKRTC"),

                        "transport_no": b.get("service_id"),

                        "route": f"{b.get('origin_bus_stand', origin)} → {b.get('destination_bus_stand', 'Katra')}",

                        "origin": b.get("origin_city", origin),

                        "destination": b.get("destination_city", "Katra"),

                        "origin_bus_stand": b.get("origin_bus_stand"),

                        "destination_bus_stand": b.get("destination_bus_stand"),

                        "departure": dep_time,

                        "departure_time": dep_time,

                        "departure_window": b.get("departure_window"),

                        "arrival": arr_time,

                        "arrival_time": arr_time,

                        "operating_hours": b.get("operating_hours"),

                        "frequency_minutes": b.get("frequency_minutes"),

                        "duration_hours": b.get("duration_hours"),

                        "price": None,

                        "fare": None,

                        "indicative_fare_min": b.get("indicative_fare_min"),

                        "indicative_fare_max": b.get("indicative_fare_max"),

                        "price_per_pax": None,

                        "total_transport_cost": None,

                        "seats_available": 40,

                        "status": "ROUTE GUIDANCE",

                        "is_connecting": False,

                        "is_live_status": False,

                        "source_type": "indicative_data",

                        "fare_classification": fare_class,

                        "fare_disclaimer": b.get("fare_disclaimer"),

                        "helpline_numbers": b.get("helpline_numbers", []),

                        "source_name": b.get("source_name", "Government of Jammu & Kashmir Transport Department & JKRTC"),

                        "source_circular_reference": b.get("source_circular_reference"),

                        "verification_status": b.get("verification_status", "verified_curated_source"),

                        "route_verification": b.get("route_verification"),

                        "operator_verification": b.get("operator_verification"),

                        "timetable_verification": b.get("timetable_verification"),

                        "fare_verification": b.get("fare_verification"),

                        "route_note": (

                            f"Curated public stage carriage demonstration schedule from {b.get('source_name', 'JKRTC')}. "

                            "Verify departures and tariffs at bus stand counter."

                        ),

                    })

                if bus_res.data.get("coverage_limitation"):







                    bus_coverage_limitation = bus_res.data.get("coverage_limitation")







        except Exception as exc:







            logger.debug("Failed querying live data manager for buses: %s", exc)















    if include_buses and not any(opt.get("mode") == "bus" for opt in formatted_options):







        if not bus_coverage_limitation:







            bus_coverage_limitation = {







                "mode": "bus",







                "status": "ROUTE_NOT_IN_CURATED_BUS_REGISTRY",







                "origin": origin,







                "destination": "Katra",







                "message": (







                    f"No verified public bus services found in the curated Katra/Jammu bus registry for origin '{origin}'. "







                    "Curated bus coverage is currently limited to verified corridors connecting Jammu (General Bus Stand & Rail Head), "







                    "Udhampur, and Delhi ISBT to Katra. For other origins, pilgrims should travel by train/flight to Jammu or Delhi "







                    "and connect via high-frequency local feeder buses or JKRTC pilgrim services."







                ),







                "supported_origins": [







                    "Jammu (General Bus Stand)",







                    "Jammu (Railway Station Rail Head)",







                    "Udhampur (Bus Stand)",







                    "Delhi (ISBT Kashmiri Gate)",







                ],







            }















    if mode and mode.lower() in ("bus", "buses"):







        coverage_limitation = bus_coverage_limitation
















    # Phase 14.2: Universal Origin & Connecting Journey Engine
    # If no direct transport options were found in the static registry for this origin,
    # invoke the ConnectingJourneyEngine to construct 2-3 practical multi-leg routes.
    # Never abandon the traveller or return an empty option list with an abrupt rejection.
    connecting_result = None
    has_train = any(opt.get("mode") == "train" for opt in formatted_options)
    if not formatted_options or (include_trains and not has_train):
        try:
            from services.connecting_journey_engine import get_connecting_journey_engine
            engine = get_connecting_journey_engine()
            conn_mode = mode if not formatted_options else "train"
            conn_res = engine.plan_connecting_journey(
                origin=origin,
                start_date=start_date,
                end_date=end_date,
                preferred_mode=conn_mode,
                pax=pax_val,
            )
            connecting_result = conn_res
            if conn_res.get("status") == "CONNECTING_ROUTES_AVAILABLE" and conn_res.get("options"):
                for opt in conn_res["options"]:
                    first_leg = opt["legs"][0] if opt.get("legs") else {}
                    last_leg = opt["legs"][-1] if opt.get("legs") else {}
                    dep_time = first_leg.get("departure_info") or "Morning departure"
                    arr_time = last_leg.get("arrival_info") or "Same day / Next day"
                    opt_mode = opt["mode"].lower().replace("-connect", "").replace("-direct", "")
                    if "bus" in opt_mode:
                        norm_mode = "bus"
                    elif "flight" in opt_mode or "air" in opt_mode:
                        norm_mode = "flight"
                    else:
                        norm_mode = "train"

                    if not formatted_options or not any(o.get("mode") == norm_mode for o in formatted_options):
                        formatted_options.append({
                            "id": opt["id"],
                            "mode": norm_mode,
                            "operator": f"{opt['primary_hub']} Connecting Corridor",
                            "transport_no": opt["title"],
                            "train_name": opt["title"],
                            "route": opt["summary_route"],
                            "origin": origin,
                            "destination": "Katra (SVDK)",
                            "departure": dep_time,
                            "departure_time": dep_time,
                            "arrival": arr_time,
                            "arrival_time": arr_time,
                            "duration_hours": opt.get("estimated_total_duration"),
                            "estimated_duration_desc": opt.get("estimated_total_duration"),
                            "price": opt.get("indicative_total_price_per_pax"),
                            "fare": opt.get("indicative_total_price_per_pax"),
                            "price_per_pax": opt.get("indicative_total_price_per_pax"),
                            "total_transport_cost": (opt.get("indicative_total_price_per_pax") * pax_val) if opt.get("indicative_total_price_per_pax") else None,
                            "indicative_fare_min": opt.get("indicative_total_price_per_pax"),
                            "fare_classification": "PARTIALLY_VERIFIED_CONNECTING",
                            "fare_disclaimer": "Local feeder fares are indicative estimates; book major rail/air legs via official IRCTC / airline portals.",
                            "seats_available": None,
                            "availability_verified": False,
                            "is_connecting": True,
                            "is_live_status": False,
                            "status": "CONNECTING_ROUTE",
                            "fallback_level": opt.get("fallback_level"),
                            "primary_hub": opt.get("primary_hub"),
                            "legs_count": opt.get("legs_count"),
                            "legs": opt.get("legs"),
                            "booking_advice": opt.get("booking_advice"),
                            "verification_status": "partially_verified",
                            "source_type": "connecting_corridor_engine",
                            "route_note": f"Multi-leg connecting journey via {opt.get('primary_hub')}. Leg 1: local feeder; onward leg: verified corridor.",
                        })
                coverage_limitation = None
                flight_coverage_limitation = None
                bus_coverage_limitation = None
            elif conn_res.get("status") == "NEEDS_CLARIFICATION":
                coverage_limitation = None
                flight_coverage_limitation = None
                bus_coverage_limitation = None
        except Exception as exc:
            logger.warning("Connecting journey engine lookup failed: %s", exc)

    ret = {







        "origin": origin,







        "destination": "Katra / Jammu",







        "dates": f"{start_date} to {end_date}",







        "pax": pax_val,







        "options_count": len(formatted_options),







        "options": formatted_options[:8],







        "source_name": source_name,







        "source_type": source_type,







        "freshness_status": freshness_status,







        "verification_status": verification_status,







        "live_status_available": False,







        "live_status_notice": (







            "Live train and bus delay/GPS telemetry is not connected in this phase. "







            "Displayed train times are published timetable schedules; check NTES (139) for live status. "







            "Displayed bus schedules represent statutory stage carriage guidelines; confirm at counter."







        ),







        "disclaimer": (







            "Curated train schedules are sourced from official published Indian Railways timetables. "







            "Bus schedules are sourced from official JKRTC operating schedules and J&K STA statutory tariff notifications. "







            "Flight schedules are indicative regional demonstration options. "







            "Real-time delays, platform numbers, and dynamic bookings must be confirmed via IRCTC, NTES (139), JKRTC, or carriers."







        ),







    }







    if coverage_limitation:







        ret["coverage_limitation"] = coverage_limitation







    if flight_coverage_limitation:

        ret["flight_coverage_limitation"] = flight_coverage_limitation

    if any(o.get("mode") == "flight" for o in formatted_options):

        ret["ground_transfer_advisory"] = (

            "Jammu Airport (IXJ) is the nearest airport for Vaishno Devi pilgrimage (~50 km from Katra, ~1.5 hours). "

            "Authorized Prepaid Taxis operate directly from the airport terminal arrivals booth. "

            "Alternatively, public JKRTC buses depart from Jammu Railway Station and General Bus Stand (~8 km from the airport)."

        )

    if bus_coverage_limitation:







        ret["bus_coverage_limitation"] = bus_coverage_limitation








    if connecting_result:
        ret["connecting_journey"] = connecting_result
        if connecting_result.get("status") == "CONNECTING_ROUTES_AVAILABLE":
            ret["is_connecting"] = True
            ret["strategy_summary"] = connecting_result.get("strategy_summary")
        elif connecting_result.get("status") == "NEEDS_CLARIFICATION":
            ret["requires_clarification"] = True
            ret["clarification_prompt"] = connecting_result.get("clarification_prompt")

    return ret























@tool







def query_train_live_status(train_number: str) -> dict:







    """Checks the real-time operational running status, delay, and platform allocation







    for a specific train number.







    Note: Live external telemetry (NTES / RailRadar) is NOT connected in this phase.







    This tool retrieves the official static timetable schedule and honestly clarifies







    that real-time running status is not available, directing pilgrims to official sources.















    Args:







        train_number: Indian Railways train number (e.g. '22439', '22477', '22461', '12445').







    """







    from services.railway_schedules import get_train_by_number







    tn = str(train_number).strip()







    schedule = get_train_by_number(tn)















    if schedule:







        return {







            "status": "LIVE_TELEMETRY_NOT_CONNECTED",







            "train_number": schedule.train_number,







            "train_name": schedule.train_name,







            "route": f"{schedule.origin_station_name} ({schedule.origin_station_code}) → {schedule.destination_station_name} ({schedule.destination_station_code})",







            "scheduled_departure": schedule.departure_time,







            "scheduled_arrival": schedule.arrival_time,







            "days_of_operation": schedule.days_of_operation,







            "major_halts": schedule.major_halts,







            "is_live_status": False,







            "live_delay_minutes": None,  # CRITICAL: Delay must be None, not 0!







            "platform_number": None,     # CRITICAL: Platform must be None







            "message": (







                f"Live GPS tracking and real-time delay telemetry for Train #{schedule.train_number} ({schedule.train_name}) "







                "are NOT connected in this phase. Official published schedule indicates departure at "







                f"{schedule.departure_time} from {schedule.origin_station_code} and arrival at {schedule.arrival_time} at {schedule.destination_station_code}."







            ),







            "verification_status": schedule.verification_status,







            "source_name": schedule.source_name,







            "source_url": schedule.source_url or "https://enquiry.indianrail.gov.in/",







            "next_steps": "For live running position, current delay, and platform assignment, dial 139 (Rail Madad) or check enquiry.indianrail.gov.in.",







            "disclaimer": "Static timetable schedule from official published records. Live telemetry requires active external provider integration.",







        }















    return {







        "status": "TRAIN_NOT_FOUND",







        "train_number": tn,







        "is_live_status": False,







        "message": f"Train #{tn} was not found in the curated Katra/Jammu corridor schedule registry.",







        "next_steps": "Verify the train number or check the National Train Enquiry System (139 / enquiry.indianrail.gov.in).",







        "disclaimer": "Curated registry covers primary express trains serving Shri Mata Vaishno Devi Katra and Jammu Tawi.",







    }























@tool







def search_accommodation_options(







    query: Optional[str] = None,







    category: Optional[str] = None,







    min_budget: Optional[float] = None,







    max_budget: Optional[float] = None,







    landmark: Optional[str] = None,







    operator_type: Optional[str] = None,







) -> dict:







    """Searches verified Katra accommodation properties including Shri Mata Vaishno Devi Shrine Board







    (SMVDSB) dharamshalas/guest houses, branded corporate chain hotels, and verified independent properties.







    All properties include verified addresses, contact numbers, official website URLs, and published indicative rates.







    Real-time availability status defaults strictly to NOT_CHECKED (advising direct verification with property).















    Args:







        query: Search term matching property name, landmark, address, or operator (e.g. 'Niharika', 'Vivanta', 'Bus Stand').







        category: Category filter ('Dharamshala' / 'SMVDSB', 'Budget', 'Mid-Range', 'Premium').







        min_budget: Minimum indicative price in INR.







        max_budget: Maximum indicative price in INR.







        landmark: Katra landmark filter (e.g. 'Railway Station', 'Bus Stand', 'Banganga', 'Main Bhawan').







        operator_type: Operator filter ('SMVDSB', 'CORPORATE_CHAIN', 'INDEPENDENT').







    """







    from services.accommodation_catalog import search_properties







    results = search_properties(







        query=query,







        category=category,







        min_budget=min_budget,







        max_budget=max_budget,







        landmark=landmark,







        operator_type=operator_type,







    )







    formatted = []







    for p in results:







        formatted.append({







            "property_id": p.property_id,







            "name": p.property_name,







            "property_type": p.property_type,







            "operator_type": p.operator_type,







            "address": p.address,







            "landmark": p.landmark,







            "phone": p.phone,







            "official_website": p.official_website,







            "booking_channel": p.booking_channel,







            "indicative_min_price": p.indicative_min_price,







            "indicative_max_price": p.indicative_max_price,







            "tariff_disclaimer": p.tariff_disclaimer,







            "availability_status": p.availability_status,







            "source_provenance": p.source_provenance,







            "source_urls": p.source_urls,







            "identity_status": p.identity_status,







        })







    return {







        "status": "SUCCESS",







        "query": query,







        "category": category,







        "landmark": landmark,







        "count": len(formatted),







        "accommodations": formatted,







        "source_name": "Verified Katra Accommodation Catalog",







        "source_type": "curated_data",







        "freshness_status": "verified_catalog",







        "verification_status": "verified_curated_source",







        "disclaimer": "Tariffs are published indicative schedules or secondary estimates. Real-time availability is NOT_CHECKED; confirm directly with the property or SMVDSB portal.",







    }























@tool







def query_operational_notices(







    location: Optional[str] = None,







    route: Optional[str] = None,







    category: Optional[str] = None,







) -> dict:







    """Retrieves verified official operational notices, route advisories, suspension notices,







    and trek restrictions for Vaishno Devi tracks and connecting corridors (Jammu, Katra, Udhampur, Ramban, NH-44).







    All advisories are source-attributed official circulars or administrative advisories.















    Args:







        location: Optional location name (e.g. 'Vaishno Devi', 'Katra', 'Sanjichhat', 'Bhawan', 'Ramban', 'NH-44').







        route: Optional specific route corridor (e.g. 'Traditional Track', 'Tarakote Marg', 'Himkoti Track', 'NH-44 Corridor').







        category: Optional category filter ('YATRA_SUSPENSION', 'ROUTE_CLOSURE', 'TRAFFIC_ADVISORY', 'WEATHER_WARNING', etc.).







    """







    try:







        from services.live_data.manager import get_live_data_manager







        from services.live_data.contracts import ProviderRequest, DataDomain







        mgr = get_live_data_manager()







        req = ProviderRequest(







            domain=DataDomain.OPERATIONAL_NOTICE.value,







            location=location or "Vaishno Devi",







            params={"route": route, "category": category, "active_only": True},







        )







        res = mgr.fetch_data(req)







        data = res.data if isinstance(res.data, dict) else {}







        notices = data.get("notices", [])







        if not res.is_success and not data.get("aggregate_status"):







            agg_status = "SOURCE_UNAVAILABLE"







        else:







            agg_status = data.get("aggregate_status", "NO_ACTIVE_NOTICES" if res.is_success else "SOURCE_UNAVAILABLE")







        return {







            "status": "SUCCESS" if res.is_success else "UNAVAILABLE",







            "aggregate_status": agg_status,







            "notices": notices,







            "count": len(notices),







            "advisory": data.get("advisory", ""),







            "source_name": res.source_name or "Curated Vaishno Devi Operational Notices Registry",







            "source_type": res.source_type or "curated_data",







            "freshness_status": res.freshness_status or "not_applicable",







            "verification_status": res.verification_status or "verified_curated_source",







            "disclaimer": res.disclaimer or "Official notices from verified registry. Ground conditions on tracks may evolve.",







        }







    except Exception as exc:







        from services.operational_notices import query_curated_notices







        notices, agg_status, meta = query_curated_notices(location=location, route=route, category=category)







        return {







            "status": "SUCCESS" if agg_status != "SOURCE_UNAVAILABLE" else "UNAVAILABLE",







            "aggregate_status": agg_status,







            "notices": notices,







            "count": len(notices),







            "advisory": meta.get("advisory", ""),







            "source_name": "Curated Vaishno Devi Operational Notices Registry",







            "source_type": "curated_data",







            "freshness_status": "not_applicable",







            "verification_status": "verified_curated_source",







            "disclaimer": "Official notices from verified registry. Ground conditions on tracks may evolve.",







        }























@tool







def lookup_verified_contacts(







    category: Optional[str] = None,







    jurisdiction: Optional[str] = None,







) -> dict:







    """Retrieves verified emergency, Shrine Board assistance, traffic control, and medical helplines.







    Always maintains 112 as the primary statutory emergency contact for immediate life-safety emergencies.







    Includes verified SMVDSB Call Centre, Katra Police, Traffic Control Units (Ramban, Jammu, Udhampur), and Ambulance (108).















    Args:







        category: Optional category filter ('NATIONAL_EMERGENCY', 'SHRINE_BOARD_ASSISTANCE', 'TRAFFIC_CONTROL', 'LOCAL_POLICE', 'MEDICAL_ASSISTANCE').







        jurisdiction: Optional jurisdiction filter ('Pan-India', 'Vaishno Devi & Katra', 'NH-44 Ramban', 'Jammu', 'Udhampur').







    """







    try:







        from services.live_data.manager import get_live_data_manager







        from services.live_data.contracts import ProviderRequest, DataDomain







        mgr = get_live_data_manager()







        req = ProviderRequest(







            domain=DataDomain.EMERGENCY.value,







            location=jurisdiction or "Katra",







            params={"category": category, "jurisdiction": jurisdiction},







        )







        res = mgr.fetch_data(req)







        data = res.data if isinstance(res.data, dict) else {}







        contacts = data.get("contacts", [])







        return {







            "status": "SUCCESS" if res.is_success else "UNAVAILABLE",







            "primary_emergency_number": data.get("primary_emergency_number", "112"),







            "primary_emergency_directive": data.get("primary_emergency_directive", {}),







            "contacts": contacts,







            "count": len(contacts),







            "source_name": res.source_name or "Verified Authority Contact Registry",







            "source_type": res.source_type or "curated_data",







            "freshness_status": res.freshness_status or "not_applicable",







            "verification_status": res.verification_status or "verified_curated_source",







            "disclaimer": res.disclaimer or "For immediate life-safety emergencies, dial 112 directly.",







        }







    except Exception as exc:







        from services.verified_contacts import query_verified_contacts







        contacts, meta = query_verified_contacts(category=category, jurisdiction=jurisdiction)







        return {







            "status": "SUCCESS",







            "primary_emergency_number": meta.get("primary_emergency_number", "112"),







            "primary_emergency_directive": meta.get("primary_emergency_directive", {}),







            "contacts": contacts,







            "count": len(contacts),







            "source_name": "Verified Authority Contact Registry",







            "source_type": "curated_data",







            "freshness_status": "not_applicable",







            "verification_status": "verified_curated_source",







            "disclaimer": meta.get("disclaimer", "For immediate life-safety emergencies, dial 112 directly."),







        }























@tool







def evaluate_yatra_plan(







    origin: str,







    duration_days: Optional[int] = 4,







    pax: Optional[int] = 1,







    start_date: Optional[str] = None,







    mode: Optional[str] = None,







    budget: Optional[float] = None,







    hotel_category: Optional[str] = None,







    pacing: Optional[str] = None,







) -> dict:







    """
    if duration_days is None:
        duration_days = 4
    if pax is None:
        pax = 1
Generates a comprehensive Yatra pilgrimage plan combining transport, darshan slot,







    verified Katra hotel accommodation, day-by-day itinerary, and itemized budget evaluation.















    Args:







        origin: Starting city (e.g. 'Delhi', 'Chandigarh', 'Jaipur').







        duration_days: Length of the trip in days (typically 3 to 6).







        pax: Number of pilgrims travelling.







        start_date: Outbound travel date in YYYY-MM-DD ISO format.







        mode: Preferred transport mode ('train', 'flight', 'bus').







        budget: Total planned trip budget in INR.







        hotel_category: Preferred hotel tier ('Budget', 'Mid-Range', 'Premium').







        pacing: Pacing preference ('relaxed', 'balanced', 'packed').







    """







    req = {







        "origin": origin,







        "duration_days": max(2, int(duration_days or 4)),







        "pax": max(1, int(pax or 1)),







        "mode": mode,







        "budget": budget,







        "hotel_category": hotel_category,







        "pacing": pacing or "balanced",







    }







    if start_date:







        req["start_date"] = start_date







        try:







            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()







            d_end = d_start + timedelta(days=req["duration_days"])







            req["end_date"] = d_end.isoformat()







        except Exception:







            pass















    import agents.orchestrator as orchestrator

    plan_res = orchestrator.coordinate_plan(req)







    return {







        "status": plan_res.get("status", "PLAN_READY"),







        "request": plan_res.get("request", req),







        "selected_options": plan_res.get("selected_options"),







        "budget_evaluation": plan_res.get("budget_evaluation"),







        "itinerary_days_count": len(plan_res.get("itinerary") or []),







        "itinerary": plan_res.get("itinerary"),







        "hotel": plan_res.get("hotel"),







        "total_cost": (plan_res.get("budget_evaluation") or {}).get("total_cost"),







        "feasible": (plan_res.get("budget_evaluation") or {}).get("is_feasible", True),







    }























@tool







def modify_itinerary(







    command: str,







    current_itinerary: Optional[List[Dict[str, Any]]] = None,







) -> dict:







    """Customizes or updates a day-by-day pilgrimage itinerary by adding destinations







    (e.g., 'Add Patnitop to Day 3', 'Include Shiv Khori'), removing activities, or shifting days.















    Args:







        command: The natural-language modification instruction.







        current_itinerary: Optional existing itinerary list to update.







    """







    if not current_itinerary:







        dummy_req = {"duration_days": 4, "origin": "Delhi", "pax": 2}







        current_itinerary = itinerary_agent.generate_default_itinerary(dummy_req)















    cmd = itinerary_agent.parse_itinerary_command(command, itinerary=current_itinerary)







    if cmd.get("ambiguous"):







        return {







            "status": "AMBIGUOUS",







            "message": cmd.get("ambiguity_prompt", "Which day or activity would you like to modify?"),







            "itinerary": current_itinerary,







        }















    valid, err_msg = itinerary_agent.validate_itinerary_command(current_itinerary, cmd)







    if not valid:







        return {







            "status": "INVALID_COMMAND",







            "message": err_msg,







            "itinerary": current_itinerary,







        }















    if cmd["action"] == "SHOW":







        reply, new_ctx = itinerary_agent.format_show_reply(current_itinerary, cmd)







        return {







            "status": "SHOW",







            "reply": reply,







            "itinerary": current_itinerary,







        }







    else:







        updated_itin, summary, new_ctx = itinerary_agent.apply_itinerary_edit(current_itinerary, cmd)







        return {







            "status": "EDIT_APPLIED",







            "summary": summary,







            "updated_itinerary": updated_itin,







            "days_count": len(updated_itin),







        }























@tool







def check_slot_availability(







    date: Optional[str] = None,







    category: Optional[str] = None,







    headless: bool = True,







) -> dict:







    """Checks real-time Vaishno Devi Darshan slot availability via the mock booking portal







    for a specific date in YYYY-MM-DD format and optional darshan category.















    Args:







        date: The pilgrimage date in YYYY-MM-DD ISO format (e.g. '2026-10-20' or '2026-11-20').







        category: Optional darshan category ('Normal Darshan', 'VIP Darshan', 'Helicopter Darshan').







        headless: Whether to execute browser automation headlessly (default True).







    """







    res = rpa_agent.check_yatra_slot_availability(







        requested_date=date,







        category=category,







        headless=headless,







    )







    if isinstance(res, dict):







        res["source_name"] = "Local Sandboxed Mock Yatra Booking Portal"







        res["source_type"] = "simulated_data"







        res["freshness_status"] = "simulated"







        res["verification_status"] = "simulation_only"







        res["disclaimer"] = "Simulated demonstration portal data; not an official Shri Mata Vaishno Devi Shrine Board reservation."







    return res























@tool







def request_booking_intent(user_confirmation_text: str = "") -> dict:







    """Generates the structured booking handoff card (action: NAVIGATE_TO_BOOKING)







    when the devotee expresses an intention to proceed with booking.







    Does NOT finalize or charge without explicit human authorization.















    Args:







        user_confirmation_text: The user text indicating booking interest.







    """







    return {







        "action": "NAVIGATE_TO_BOOKING",







        "status": "BOOKING_INTENT_TRIGGERED",







        "human_confirmation_required": True,







        "message": "🙏 Booking handoff initiated. Devotee must review details and explicitly confirm authorization.",







    }























@tool







def execute_authorized_booking(







    user_name: str,







    pax_count: int,







    transport_text: str,







    slot_text: str,







    total_price: float,







    human_authorized: bool = False,







    session_id: Optional[str] = None,







    plan_version: Optional[int] = None,







) -> dict:







    """Executes the Playwright mock browser booking workflow ONLY when explicit human







    authorization has been granted. Strictly blocks automatic execution without authorization.















    Args:







        user_name: Name of the primary devotee.







        pax_count: Number of pilgrims.







        transport_text: Transport description (e.g. 'Vande Bharat Train from Delhi').







        slot_text: Darshan category and session time.







        total_price: Total mock price in INR.







        human_authorized: Boolean flag indicating explicit human approval.







        session_id: Active session identifier.







        plan_version: Plan revision number being authorized.







    """







    if not human_authorized:







        return {







            "status": "AUTHORIZATION_REQUIRED",







            "message": "Human authorization gate active: devotee must explicitly confirm booking before RPA can execute.",







            "authorized": False,







        }















    res = rpa_agent.execute_playwright_mock_booking(







        user_name=user_name,







        pax_count=pax_count,







        transport_text=transport_text,







        slot_text=slot_text,







        total_price=total_price,







        headless=True,







    )







    if isinstance(res, dict):







        res["source_name"] = "Local Sandboxed Mock Yatra Booking Portal (Playwright RPA)"







        res["source_type"] = "simulated_data"







        res["freshness_status"] = "simulated"







        res["verification_status"] = "simulation_only"







        res["disclaimer"] = "Simulated demonstration booking; no financial transaction or real Shrine Board booking occurred."







    return res























CENTRAL_TOOLS = [







    search_yatra_knowledge,







    get_tourism_knowledge,







    check_weather_guidance,







    search_transport_options,







    search_accommodation_options,







    query_operational_notices,







    lookup_verified_contacts,







    query_train_live_status,







    evaluate_yatra_plan,







    modify_itinerary,







    check_slot_availability,







    request_booking_intent,







    execute_authorized_booking,







]















CENTRAL_TOOL_MAP = {t.name: t for t in CENTRAL_TOOLS}


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class LLMCircuitBreaker:
    """Thread-safe circuit breaker preventing cascading latency when external LLM APIs
    experience network failures, rate limits (HTTP 429), or service unavailabilities (HTTP 503).
    """

    def __init__(self, failure_threshold: int = 2, recovery_timeout: float = 45.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self.last_error = None
        self._lock = threading.Lock()

    def can_attempt(self) -> bool:
        with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if (now - self.last_failure_time) >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("LLMCircuitBreaker transitioned from OPEN to HALF_OPEN (probing canary request)")
                    return True
                return False
            if self.state == CircuitState.HALF_OPEN:
                return True
            return True

    def record_success(self):
        with self._lock:
            if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("LLMCircuitBreaker canary succeeded. Transitioning from %s to CLOSED", self.state.value)
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0
            self.last_error = None

    def record_failure(self, error: Any = None):
        with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.monotonic()
            self.last_error = str(error) if error else "Unknown error"
            if self.state == CircuitState.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    logger.warning(
                        "LLMCircuitBreaker tripped to OPEN after %d consecutive failures (error: %s). Cooldown window: %.1fs",
                        self.consecutive_failures,
                        self.last_error,
                        self.recovery_timeout,
                    )
                self.state = CircuitState.OPEN

    def reset(self):
        with self._lock:
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0
            self.last_failure_time = 0.0
            self.last_error = None

    @property
    def current_state(self) -> str:
        with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.OPEN and (now - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            return self.state.value


llm_circuit_breaker = LLMCircuitBreaker(failure_threshold=2, recovery_timeout=45.0)


def select_tools_for_turn(
    user_text: str,
    intent: Optional[str] = None,
    current_request: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """Selects a focused, domain-relevant subset of tools for the current turn.
    Reduces prompt size, token consumption, and Groq LLM latency.
    """
    txt = (user_text or "").lower()

    # Domain indicators
    is_weather = any(w in txt for w in ["weather", "temperature", "forecast", "rain", "snow", "cold", "climate", "mausam"])
    is_transport = any(w in txt for w in ["train", "flight", "bus", "travel", "reach", "journey", "transport", "route", "how to go", "how to reach", "fare", "ticket", "vande bharat", "railway", "airport"])
    is_accommodation = any(w in txt for w in ["hotel", "stay", "room", "bhavan", "accommodation", "dharamshala", "guest house", "lodge"])
    is_yatra = any(w in txt for w in ["yatra", "darshan", "aarti", "trek", "track", "rfid", "parchi", "helicopter", "battery car", "palki", "bhawan", "ardhkuwari", "sanctum", "shrine", "history", "timings", "guidelines", "rules"])
    is_contact = any(w in txt for w in ["contact", "helpline", "phone", "number", "emergency", "call", "reach board"])
    is_notices = any(w in txt for w in ["notice", "advisory", "closed", "open", "landslide", "status", "operation", "warning"])
    is_booking = any(w in txt for w in ["book", "reserve", "slot", "availability", "payment"])

    selected: List[Any] = []

    if is_weather:
        selected.extend([check_weather_guidance, query_operational_notices])
    if is_transport:
        selected.extend([search_transport_options, query_operational_notices, query_train_live_status])
    if is_accommodation:
        selected.extend([search_accommodation_options])
    if is_yatra:
        selected.extend([search_yatra_knowledge, get_tourism_knowledge, query_operational_notices])
    if is_contact:
        selected.extend([lookup_verified_contacts, query_operational_notices])
    if is_notices and not (is_transport or is_weather or is_yatra):
        selected.append(query_operational_notices)
    if is_booking:
        selected.extend([check_slot_availability, request_booking_intent])

    # Deduplicate while preserving order
    unique_tools: List[Any] = []
    for t in selected:
        if t not in unique_tools:
            unique_tools.append(t)

    if unique_tools:
        return unique_tools

    # If full trip planning intent, bind full tool suite
    if intent in ("PLAN_YATRA", "ITINERARY", "BOOKING_INTENT") or "plan" in txt or "trip" in txt or "itinerary" in txt:
        return CENTRAL_TOOLS

    # General conversation or single question: return foundational tools
    return [search_yatra_knowledge, get_tourism_knowledge, query_operational_notices]















# -----------------------------------------------------------------------------







# 3. LLM FACTORY & RESILIENT CONNECTION CONFIGURATION







# -----------------------------------------------------------------------------















@functools.lru_cache(maxsize=1)

def get_groq_llm(model: Optional[str] = None, temperature: float = 0.1) -> Optional[Any]:

    """Returns a ChatGroq instance configured with crisp timeout (4.0s) and max_retries (1).

    Defaults to verified Groq catalog model 'openai/gpt-oss-20b' with 'openai/gpt-oss-120b' fallback.

    Can be configured via GROQ_MODEL environment variable.

    """

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key or ChatGroq is None:

        return None



    raw_model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    # Clean deprecated or non-existent model identifiers to verified Groq models

    if raw_model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gpt-oss-20b"):

        target_model = "openai/gpt-oss-20b"

    elif raw_model in ("gpt-oss-120b",):

        target_model = "openai/gpt-oss-120b"

    else:

        target_model = raw_model



    try:

        return ChatGroq(

            model=target_model,

            temperature=temperature,

            api_key=api_key,

            request_timeout=4.0,

            max_retries=1,

        )

    except Exception as exc:

        logger.warning("CentralAgent failed to initialize ChatGroq with %s: %s; attempting fallback", target_model, exc)

        return get_fallback_groq_llm(temperature=temperature)





@functools.lru_cache(maxsize=1)

def get_fallback_groq_llm(temperature: float = 0.1) -> Optional[Any]:

    """Returns a ChatGroq fallback instance using 'openai/gpt-oss-120b'."""

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key or ChatGroq is None:

        return None

    fallback_model = os.environ.get("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")

    try:

        return ChatGroq(

            model=fallback_model,

            temperature=temperature,

            api_key=api_key,

            request_timeout=4.0,

            max_retries=1,

        )

    except Exception as exc:

        logger.warning("CentralAgent fallback ChatGroq initialization also failed: %s", exc)

        return None























# -----------------------------------------------------------------------------







# 4. STRUCTURED TOOL EXECUTION DATA MODELS & SAFE RUNNERS







# -----------------------------------------------------------------------------















class ToolExecutionStatus(str, Enum):







    """Execution outcome status for central agent specialist tools."""







    SUCCESS = "success"







    PARTIAL_SUCCESS = "partial_success"







    FAILURE = "failure"







    TIMEOUT = "timeout"







    UNAVAILABLE = "unavailable"







    SKIPPED = "skipped"







    INVALID_TOOL_RESPONSE = "invalid_tool_response"























@dataclass







class ToolExecutionRecord:







    """Strongly-typed execution record for an individual specialist tool invocation."""







    tool: str







    args: Dict[str, Any]







    status: str







    result: Any







    duration_ms: float = 0.0







    error: Optional[str] = None







    is_fallback: bool = False















    def to_dict(self) -> Dict[str, Any]:







        """Serializes tool execution record for the API response envelope."""







        return {







            "tool": self.tool,







            "args": self.args,







            "status": self.status,







            "result": self.result,







            "duration_ms": round(self.duration_ms, 2),







            "error": self.error,







        }























def is_simple_greeting(text: str) -> bool:

    """Identifies pure devotional greetings or salutations that require no tool calls."""

    if not text:

        return False

    tl = text.strip().lower()

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

        "itinerary", "days", "pax", "people", "adults", "from", "ticket", "helicopter"

    }

    if any(w in planning_triggers for w in words):

        return False

    return all(w in greeting_vocab for w in words)





def is_simple_acknowledgment(text: str) -> bool:

    """Identifies pure gratitude or acknowledgment messages requiring no tools."""

    if not text:

        return False

    tl = text.strip().lower()

    t_clean = re.sub(r"[^\w\s]", " ", tl).strip()

    words = t_clean.split()

    if not words:

        return False

    ack_vocab = {

        "thank", "you", "so", "much", "very", "a", "lot", "thanks", "dhanyawad",

        "shukriya", "ok", "okay", "got", "it", "understood", "alright", "noted",

        "perfect", "great", "nice", "fine", "sure", "sounds", "good", "for", "the", "help", "ji", "helpful", "information", "info", "guidance", "support", "assistance", "answering", "advice", "appreciate", "appreciated", "grateful",
        "that", "was", "this", "is", "are", "am", "been", "being", "have", "has", "had",
        "my", "your", "me", "us", "we", "he", "she", "they", "all", "just", "really",
        "exactly", "absolutely", "indeed", "certainly", "of", "with", "and", "too", "as", "well"

    }

    planning_triggers = {

        "plan", "planning", "book", "booking", "trip", "hotel", "train", "flight",

        "bus", "weather", "route", "track", "stay", "darshan", "cost", "budget"

    }

    if any(w in planning_triggers for w in words):

        return False

    return all(w in ack_vocab for w in words)





def is_help_query(text: str) -> bool:
    """Identifies requests for assistance, system capabilities, or user help."""
    if not text:
        return False
    t_clean = re.sub(r"[^\w\s]", " ", text.strip().lower()).strip()
    if t_clean in ("help", "menu", "options", "what can you do", "features", "how can you help", "commands", "guide", "user guide"):
        return True
    if (t_clean.startswith("help") or t_clean.endswith("help") or
        "how to use" in t_clean or "how do i use" in t_clean or
        "what can you do" in t_clean or "what do you do" in t_clean or
        "help me" in t_clean or "i need help" in t_clean or
        "need assistance" in t_clean or "how to" in t_clean):
        planning_triggers = {"booking", "hotel", "train", "flight", "weather", "darshan", "cost"}
        if not any(w in t_clean.split() for w in planning_triggers):
            return True
    return False


def is_accommodation_info_query(text: str) -> bool:
    """Identifies informational queries about Shrine Board bhawans and accommodations."""
    if not text:
        return False
    tl = text.lower()
    has_stay_word = any(w in tl for w in ["stay", "bhavan", "bhawan", "hotel", "room", "accommodation", "dharamshala", "rest house", "dormitory", "guest house"])
    is_planning = any(w in tl for w in ["i am travelling", "from delhi", "plan a trip", "pax", "adults", "budget"])
    is_booking = any(w in tl for w in ["book", "reserve", "payment", "execute", "rpa"])
    return has_stay_word and not is_planning and not is_booking


def _handle_deterministic_accommodation_turn(
    user_text: str,
    session_id=None,
    current_request=None,
    current_itinerary=None,
    last_tourism_place=None,
    last_itinerary_context=None,
):
    sid = session_id or session_store.create_session()["session_id"]
    tl = user_text.lower()
    detected_place = "Bhawan" if "bhawan" in tl else "Katra"

    reply = (
        "🏨 **Verified Accommodations & Official Shrine Board Bhawans**\n\n"
        "For devotees visiting Shri Mata Vaishno Devi Ji, the **Shri Mata Vaishno Devi Shrine Board (SMVDSB)** "
        "provides clean, well-maintained, and subsidized accommodation across the holy track:\n\n"
        "**1. At Bhawan (Sanctum Area):**\n"
        "- **Main Bhawan Complex:** Regular and family rooms close to the sanctum.\n"
        "- **Manokamana Bhawan:** AC & non-AC rooms and family accommodation.\n"
        "- **Kalika Bhawan & Saraswati Dham:** Subsidized dormitory hall beds and private rooms.\n\n"
        "**2. At Ardhkuwari (Midpoint):**\n"
        "- **Ardhkuwari Rest House:** Dormitory facilities for resting before the holy cave darshan.\n\n"
        "**3. At Katra Base Camp:**\n"
        "- **Niharika Complex:** Central Katra near the Yatra Registration counter and Bus Stand.\n"
        "- **Shakti Bhawan & Ashirwad Bhawan:** Peaceful rooms managed by the Shrine Board.\n"
        "- **Trikuta Bhawan:** Located directly adjacent to the Shri Mata Vaishno Devi Katra Railway Station.\n\n"
        "📌 *Booking Note:* Shrine Board rooms open online exactly 60 days in advance on the official portal `maavaishnodevi.org`. "
        "Private certified Katra hotels (Budget, Standard, Luxury) are also readily available."
    )

    res = {
        "reply": reply,
        "intent": "ACCOMMODATION",
        "status": "SUCCESS",
        "session_id": sid,
        "request": current_request or {},
        "plan": None,
        "itinerary": current_itinerary,
        "recommendation": None,
        "action": None,
        "hotel": None,
        "budget_evaluation": None,
        "knowledge_sources": ["SMVDSB Official Accommodation Catalog & Bhawan Registry"],
        "last_tourism_place": detected_place,
        "last_itinerary_context": last_itinerary_context,
        "source": "central_agent_deterministic",
        "response_source": "central_agent",
        "knowledge_source": "central_agent_accommodation_catalog",
        "tool_executions": [],
        "execution_mode": "deterministic_accommodation",
        "partial_failure": False,
        "circuit_breaker_state": llm_circuit_breaker.current_state,
    }
    from utils.provenance import attach_provenance_to_response
    return attach_provenance_to_response(res)























def is_operational_notice_query(text: str) -> bool:







    """Detects whether a user query pertains to track closures, traffic advisories, or operational circulars."""







    if not text:







        return False







    tl = text.strip().lower()







    patterns = [







        r"\b(closure|closed|shut|blocked|landslide|suspension|suspended|resumption|restricted|restriction|halted)\b",







        r"\b(track|route|marg|nh-?44|road|corridor|passage)\s+(status|condition|open|advisory|update)\b",







        r"\b(is\s+(the\s+)?(track|yatra|route|marg|road|nh-?44)\s+(open|closed|blocked|halted|safe))\b",







        r"\b(operational\s+(notices?|advisories?|circulars?|updates?)|traffic\s+advisories?)\b",







        r"\b(rfid\s+(notice|rule|mandatory|circular)|fake\s+(website|agents?)|unauthorized\s+agents?)\b",







        r"\b(is\s+the\s+yatra\s+(running|operational|open|closed|suspended))\b",







    ]







    return any(re.search(p, tl) for p in patterns)























def is_verified_contact_query(text: str) -> bool:







    """Detects whether a user query asks for emergency contacts, helplines, or authority directory numbers."""







    if not text:







        return False







    tl = text.strip().lower()







    patterns = [







        r"\b(emergency\s*(number|numbers|contact|contacts|helpline|helplines)|police\s*number|ambulance\s*number|hospital\s*number)\b",







        r"\b(police|ambulance|hospital|emergency|shrine\s*board)\b.{0,30}\b(number|numbers|contact|contacts|phone|station|desk|helpline)\b",







        r"\b(helplines?|toll[\s-]*free|call\s*cent(?:er|re)|contact\s*(number|numbers|details|registry))\b",







        r"\b(traffic\s*control\s*unit|tcu\s*(ramban|jammu|udhampur)|katra\s*police)\b",







        r"\b(shrine\s*board\s*(helpline|phone|contact|number)|smvdsb\s*(helpline|contact))\b",







        r"\b(who\s+to\s+call|emergency\s+assistance|urgent\s+help)\b",







        r"\b(112|108|1077|1091)\b",







    ]







    return any(re.search(p, tl) for p in patterns)























def _execute_single_tool_safe(







    tool_name: str,







    tool_args: Dict[str, Any],







    session_id: Optional[str] = None,







    timeout_seconds: float = 5.0,







) -> ToolExecutionRecord:







    """Executes a single specialist tool within a strict timeout boundary.







    Catches exceptions, validates responses, and guarantees no raw stack traces or keys leak.







    """







    target_tool = CENTRAL_TOOL_MAP.get(tool_name)







    if not target_tool:







        return ToolExecutionRecord(







            tool=tool_name,







            args=tool_args,







            status=ToolExecutionStatus.UNAVAILABLE.value,







            result={"status": "unavailable", "error": f"Tool '{tool_name}' is not registered."},







            error=f"Unregistered tool: {tool_name}",







        )















    # Critical Booking Authorization Gate







    if tool_name == "execute_authorized_booking":







        is_auth = tool_args.get("human_authorized", False)







        if session_id:







            try:







                sess = session_store.get_session(session_id)







                sess_auth = (sess.get("state") or {}).get("authorization", {})







                if not sess_auth.get("granted", False):







                    is_auth = False







            except Exception:







                pass















        if not is_auth:







            return ToolExecutionRecord(







                tool=tool_name,







                args=tool_args,







                status=ToolExecutionStatus.FAILURE.value,







                result={







                    "status": "BLOCKED",







                    "error": "Human authorization required before triggering booking execution.",







                    "human_confirmation_required": True,







                },







                error="Human authorization required",







            )















    t0 = time.perf_counter()







    res = None















    try:







        # Bounded execution with per-tool timeout







        with ThreadPoolExecutor(max_workers=1) as executor:







            future = executor.submit(target_tool.invoke, tool_args)







            try:







                res = future.result(timeout=timeout_seconds)







            except FutureTimeoutError:







                dur = (time.perf_counter() - t0) * 1000.0







                return ToolExecutionRecord(







                    tool=tool_name,







                    args=tool_args,







                    status=ToolExecutionStatus.TIMEOUT.value,







                    result={"status": "timeout", "error": f"Tool '{tool_name}' timed out after {timeout_seconds}s.", "tool": tool_name},







                    duration_ms=dur,







                    error=f"Timeout after {timeout_seconds}s",







                )







    except Exception as exc:







        dur = (time.perf_counter() - t0) * 1000.0







        clean_err = str(exc)







        if len(clean_err) > 200:







            clean_err = clean_err[:200] + "..."







        return ToolExecutionRecord(







            tool=tool_name,







            args=tool_args,







            status=ToolExecutionStatus.FAILURE.value,







            result={"status": "failed", "error": "Specialist service temporarily encountered an error.", "tool": tool_name},







            duration_ms=dur,







            error=clean_err,







        )















    dur = (time.perf_counter() - t0) * 1000.0















    # Validate output structure







    if not isinstance(res, (dict, list, str)):







        return ToolExecutionRecord(







            tool=tool_name,







            args=tool_args,







            status=ToolExecutionStatus.INVALID_TOOL_RESPONSE.value,







            result={"status": "invalid_tool_response", "error": "Tool returned non-serializable response structure."},







            duration_ms=dur,







            error="Malformed tool response structure",







        )















    # Classify outcome status







    status = ToolExecutionStatus.SUCCESS.value







    if isinstance(res, dict):







        if res.get("status") in ("UNAVAILABLE", "UNRECOGNIZED_LOCATION") or res.get("relevant_found") is False:







            status = ToolExecutionStatus.UNAVAILABLE.value







        elif res.get("status") in ("FAILED", "ERROR", "BLOCKED") or "error" in res:







            status = ToolExecutionStatus.FAILURE.value







        elif res.get("is_multi_location") and res.get("freshness_status") == "partial_live":







            status = ToolExecutionStatus.PARTIAL_SUCCESS.value















    return ToolExecutionRecord(







        tool=tool_name,







        args=tool_args,







        status=status,







        result=res,







        duration_ms=dur,







    )























def _execute_tool_batch(







    tool_calls: List[Dict[str, Any]],







    seen_calls: Dict[str, ToolExecutionRecord],







    session_id: Optional[str] = None,







    per_tool_timeout: float = 5.0,







) -> List[Tuple[Dict[str, Any], ToolExecutionRecord]]:







    """Executes a batch of tool calls from a single LLM reasoning step.







    Runs independent tool calls concurrently via ThreadPoolExecutor.







    Prevents duplicate executions by reusing seen signatures.







    """







    ordered_results: List[Optional[Tuple[Dict[str, Any], ToolExecutionRecord]]] = [None] * len(tool_calls)







    pending_to_run: List[Tuple[int, Dict[str, Any], str, Dict[str, Any], str]] = []







    batch_duplicates: Dict[str, List[Tuple[int, Dict[str, Any], Dict[str, Any]]]] = {}







    registered_sigs: Set[str] = set()















    for idx, call in enumerate(tool_calls):







        t_name = call.get("name") or ""







        raw_args = call.get("args") or {}















        # Safely parse args if string







        if isinstance(raw_args, str):







            try:







                t_args = json.loads(raw_args)







            except Exception:







                rec = ToolExecutionRecord(







                    tool=t_name,







                    args={},







                    status=ToolExecutionStatus.INVALID_TOOL_RESPONSE.value,







                    result={"status": "invalid_tool_response", "error": "Malformed tool call arguments JSON."},







                    error="Malformed JSON arguments",







                )







                ordered_results[idx] = (call, rec)







                continue







        else:







            t_args = dict(raw_args)















        # Build unique signature for loop & duplicate protection







        sig_key = f"{t_name}:{json.dumps(t_args, sort_keys=True, default=str)}"







        if sig_key in seen_calls:







            # Reused duplicate call without re-hitting external provider







            prior = seen_calls[sig_key]







            rec = ToolExecutionRecord(







                tool=t_name,







                args=t_args,







                status=ToolExecutionStatus.SKIPPED.value,







                result=prior.result,







                duration_ms=0.0,







                error="(Duplicate tool call prevented)",







            )







            ordered_results[idx] = (call, rec)







        elif sig_key in registered_sigs:







            # Duplicate within the same turn's batch







            batch_duplicates.setdefault(sig_key, []).append((idx, call, t_args))







        else:







            registered_sigs.add(sig_key)







            pending_to_run.append((idx, call, t_name, t_args, sig_key))















    # Single call fast-path







    if len(pending_to_run) == 1:







        idx, call, t_name, t_args, sig_key = pending_to_run[0]







        rec = _execute_single_tool_safe(t_name, t_args, session_id=session_id, timeout_seconds=per_tool_timeout)







        seen_calls[sig_key] = rec







        ordered_results[idx] = (call, rec)







    elif len(pending_to_run) > 1:







        # Concurrent execution of independent tool calls







        max_workers = min(4, len(pending_to_run))







        with ThreadPoolExecutor(max_workers=max_workers) as batch_exec:







            future_to_item = {







                batch_exec.submit(







                    _execute_single_tool_safe,







                    t_name,







                    t_args,







                    session_id=session_id,







                    timeout_seconds=per_tool_timeout,







                ): (idx, call, sig_key)







                for idx, call, t_name, t_args, sig_key in pending_to_run







            }







            for fut in future_to_item:







                idx, call, sig_key = future_to_item[fut]







                try:







                    rec = fut.result()







                except Exception as b_err:







                    rec = ToolExecutionRecord(







                        tool=call.get("name", "unknown"),







                        args=call.get("args") or {},







                        status=ToolExecutionStatus.FAILURE.value,







                        result={"status": "failed", "error": "Execution batch error."},







                        error=str(b_err),







                    )







                seen_calls[sig_key] = rec







                ordered_results[idx] = (call, rec)















    # Populate in-batch duplicates with the executed primary result







    for sig_key, dup_list in batch_duplicates.items():







        primary_rec = seen_calls.get(sig_key)







        primary_res = primary_rec.result if primary_rec else None







        for dup_idx, dup_call, dup_args in dup_list:







            rec = ToolExecutionRecord(







                tool=dup_call.get("name") or "",







                args=dup_args,







                status=ToolExecutionStatus.SKIPPED.value,







                result=primary_res,







                duration_ms=0.0,







                error="(Duplicate tool call prevented)",







            )







            ordered_results[dup_idx] = (dup_call, rec)















    return [item for item in ordered_results if item is not None]























def _synthesize_partial_fallback(







    executed_tools: List[Dict[str, Any]],







    user_text: str,







    session_id: str,







    req: Dict[str, Any],







    state: Dict[str, Any],







    intent: str,







    captured_plan: Optional[Dict[str, Any]] = None,







    captured_itinerary: Optional[List[Dict[str, Any]]] = None,







    captured_sources: Optional[List[Dict[str, Any]]] = None,







    detected_place: Optional[str] = None,







    captured_availability: Optional[Dict[str, Any]] = None,







    captured_action: Optional[str] = None,







    captured_budget: Optional[Dict[str, Any]] = None,







    captured_hotel: Optional[Dict[str, Any]] = None,







    last_itinerary_context: Optional[Dict[str, Any]] = None,







    captured_operational_notices: Optional[Dict[str, Any]] = None,







    captured_verified_contacts: Optional[Dict[str, Any]] = None,







) -> Dict[str, Any]:







    """Generates an honest, devotional synthesis when one or more tools fail or LLM synthesis aborts.







    Guarantees that successful tool results survive, failures are disclosed, and no data is fabricated.







    """







    successful_tools = [t for t in executed_tools if t.get("status") == ToolExecutionStatus.SUCCESS.value]







    failed_tools = [







        t for t in executed_tools







        if t.get("status") in (







            ToolExecutionStatus.FAILURE.value,







            ToolExecutionStatus.TIMEOUT.value,







            ToolExecutionStatus.INVALID_TOOL_RESPONSE.value,







            ToolExecutionStatus.UNAVAILABLE.value,







        )







    ]















    has_prior_turns = False

    try:

        from agents.session_store import session_store

        msgs = session_store.get_messages(session_id) if session_id else []

        has_prior_turns = len(msgs) > 1

    except Exception:

        pass



    parts: List[str] = []

    if not has_prior_turns or any(w in user_text.lower() for w in ("hi", "hello", "namaste", "jai mata di", "pranam")):

        parts.append("🙏 **Jai Mata Di!**")















    if not successful_tools and failed_tools:







        # Complete failure across all invoked tools







        parts.append(







            "We are currently experiencing temporary connectivity issues with our specialist pilgrimage services. "







            "Please consult the official Shri Mata Vaishno Devi Shrine Board helpline (1800-180-7198) or visit "







            "[maavaishnodevi.org](https://www.maavaishnodevi.org) for urgent assistance."







        )







        status_val = "UNAVAILABLE"







    else:







        # Partial success: Synthesize successful results







        parts.append("Here is the verified guidance retrieved for your holy pilgrimage:")















        for st in successful_tools:







            t_name = st.get("tool")







            res = st.get("result") or {}















            if t_name == "check_weather_guidance" and isinstance(res, dict):







                loc = res.get("canonical_location") or res.get("location", "Katra")







                cond = res.get("condition") or res.get("summary", "Pleasant")







                low = res.get("low_c")







                high = res.get("high_c")







                adv = res.get("advisory", "")







                parts.append(f"\n🌤️ **Weather Guidance ({loc}):** {cond}, {low}°C - {high}°C. {adv}".strip())















            elif t_name == "search_transport_options" and isinstance(res, dict):







                orig = res.get("origin", "Origin")







                opts = res.get("options") or []







                parts.append(f"\n🚆 **Transport Options ({orig} → Katra):**")







                if opts:







                    for o in opts[:3]:







                        parts.append(f"- **{o.get('operator')}** ({o.get('route')}): ₹{o.get('price_per_pax', 0)} per pilgrim, departure {o.get('departure', 'N/A')}.")







                else:







                    parts.append("- Indicative transport schedules are currently being updated.")















            elif t_name == "search_yatra_knowledge" and isinstance(res, dict):







                ctx = res.get("answer_context") or ""







                if not ctx and res.get("snippets"):







                    ctx = res["snippets"][0]







                if ctx:







                    parts.append(f"\n📖 **Pilgrimage Guidance:**\n{ctx}")















            elif t_name == "evaluate_yatra_plan" and isinstance(res, dict):







                b_eval = res.get("budget_evaluation") or {}







                tot = b_eval.get("grand_total") or res.get("total_cost", 0)







                parts.append(f"\n📋 **Pilgrimage Itinerary Plan:** Generated comprehensive plan evaluated at ₹{tot:,.2f}.")















            elif t_name == "query_operational_notices" and isinstance(res, dict):







                notices = res.get("notices") or []







                if notices:







                    parts.append(f"\n📢 **Operational Notices ({len(notices)} recorded):**")







                    for n in notices[:3]:







                        sev_icon = "🚨" if n.get("severity") in ("CRITICAL", "HIGH") else "⚠️"







                        parts.append(f"- {sev_icon} **{n.get('notice_title')}** ({n.get('affected_location')}): {n.get('translated_summary') or n.get('notice_text')}")







                else:







                    parts.append("\n📢 **Operational Notices:** No active disruption notices recorded in curated registry; upstream conditions unconfirmed.")















            elif t_name == "lookup_verified_contacts" and isinstance(res, dict):







                parts.append("\n🚨 **Emergency Directives:** For immediate emergencies, dial **112** (Pan-India ERSS).")







                contacts = res.get("contacts") or []







                if contacts:







                    parts.append("**Verified Helplines:**")







                    for c in contacts[:4]:







                        if not c.get("is_primary_emergency"):







                            parts.append(f"- **{c.get('organization')}**: `{c.get('telephone_number')}` ({c.get('operating_hours')})")















        # Append honest disclosure for failed capabilities







        if failed_tools:







            failed_descriptions = []







            for ft in failed_tools:







                fn = ft.get("tool", "")







                if "weather" in fn:







                    failed_descriptions.append("live weather forecasts")







                elif "transport" in fn:







                    failed_descriptions.append("transport timetables")







                elif "knowledge" in fn or "tourism" in fn:







                    failed_descriptions.append("tourism knowledge details")







                elif "plan" in fn or "hotel" in fn:







                    failed_descriptions.append("accommodation and hotel tariffs")







                elif "availability" in fn:







                    failed_descriptions.append("slot availability checking")







                elif "notice" in fn or "operational" in fn:







                    failed_descriptions.append("operational notices and travel advisories")







                elif "contact" in fn or "emergency" in fn:







                    failed_descriptions.append("verified helpline directory")







                else:







                    failed_descriptions.append(fn)















            parts.append(







                f"\n\n⚠️ **Notice:** Information regarding {', '.join(failed_descriptions)} could not be retrieved at this time "







                "due to a temporary service timeout or unavailability. To maintain accuracy, we have not estimated or invented these details."







            )







            status_val = "PARTIAL_SUCCESS"







        else:







            status_val = "PLAN_READY" if captured_plan else "SUCCESS"















    reply_text = "\n".join(parts)















    res_envelope: Dict[str, Any] = {







        "reply": reply_text,







        "intent": intent,







        "status": status_val,







        "session_id": session_id,







        "request": req,







        "plan": captured_plan or state.get("pending_options"),







        "itinerary": captured_itinerary or state.get("itinerary"),







        "recommendation": state.get("recommendation"),







        "action": captured_action,







        "hotel": captured_hotel or state.get("hotel"),







        "budget_evaluation": captured_budget or state.get("budget_evaluation"),







        "knowledge_sources": captured_sources or [],







        "last_tourism_place": detected_place,







        "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),







        "source": "central_agent_langchain",







        "response_source": "central_agent",







        "knowledge_source": "langchain_tool_registry",







        "tool_executions": executed_tools,







        "partial_failure": bool(failed_tools),







        "execution_mode": "hybrid_partial_fallback",







    }















    if captured_availability:







        res_envelope["availability_result"] = captured_availability







        res_envelope["intent"] = "AVAILABILITY"















    if captured_operational_notices:







        res_envelope["operational_notices"] = captured_operational_notices















    if captured_verified_contacts:







        res_envelope["verified_contacts"] = captured_verified_contacts















    try:







        from utils.provenance import attach_provenance_to_response







        res_envelope = attach_provenance_to_response(res_envelope, tool_executions=executed_tools)







    except Exception as prov_err:







        logger.warning("Failed to attach provenance in partial fallback synthesis: %s", prov_err)







        res_envelope.setdefault("source_provenance", [])







        res_envelope.setdefault("live_sources", [])















    if session_id:







        try:







            session_store.add_message(







                session_id=session_id,







                role="assistant",







                content=reply_text,







                metadata={







                    "intent": intent,







                    "source": "central_agent_langchain",







                    "tool_executions": executed_tools,







                    "source_provenance": res_envelope.get("source_provenance", []),







                    "data_provenance": res_envelope.get("data_provenance", res_envelope.get("source_provenance", [])),







                    "live_sources": res_envelope.get("live_sources", []),







                    "is_cached": res_envelope.get("is_cached", False),







                    "partial_failure": bool(failed_tools),







                    "execution_mode": "hybrid_partial_fallback",







                    "knowledge_sources": captured_sources or [],







                },







            )







        except Exception as sess_err:







            logger.debug("Silently ignored session message persistence in fallback: %s", sess_err)















    return res_envelope























def _handle_deterministic_operational_notice_turn(







    user_text: str,







    session_id: Optional[str] = None,







    current_request: Optional[Dict[str, Any]] = None,







    current_itinerary: Optional[List[Dict[str, Any]]] = None,







    last_tourism_place: Optional[str] = None,







    last_itinerary_context: Optional[Dict[str, Any]] = None,







) -> Dict[str, Any]:







    sid = session_id or session_store.create_session()["session_id"]







    tl = user_text.lower()







    req_route = None







    if "tarakote" in tl:







        req_route = "Tarakote Marg"







    elif "traditional" in tl:







        req_route = "Traditional Track"







    elif "himkoti" in tl:







        req_route = "Himkoti Track"







    elif "nh" in tl or "highway" in tl:







        req_route = "NH-44 Corridor"















    notice_res = query_operational_notices.invoke({"route": req_route})







    notices = notice_res.get("notices") or []







    agg_status = notice_res.get("aggregate_status")















    parts = ["🙏 **Jai Mata Di!** Here is the current official operational notice guidance:"]



    if "helicopter" in tl:

        parts.append(

            "\n🚁 **Helicopter Operations Guidance:**\n"

            "- **Operating Schedule:** Scheduled daily flights between Katra Helipad and Sanjichhat operate normally from ~8:00 AM to 5:00 PM.\n"

            "- **Weather Sensitivity:** Flights are subject to real-time mountain visibility and wind conditions; high winds, heavy rain, or dense valley fog can cause temporary holds.\n"

            "- **Operational Inquiries:** For real-time helipad clearance, devotees can verify directly at Katra Helipad or contact the Shrine Board toll-free helpline (1800-180-7198)."

        )

    elif "battery" in tl:

        parts.append(

            "\n⚡ **Battery Car Operations Status:**\n"

            "- **Operating Route:** Adhkuwari to Bhawan via Himkoti route.\n"

            "- **Operating Hours:** 6:30 AM to 10:00 PM daily (subject to track clearance).\n"

            "- **Priority:** Boarding preference is reserved for senior citizens (60+) and differently-abled pilgrims."

        )

    elif "ropeway" in tl:

        parts.append(

            "\n🚡 **Bhairon Ropeway Operations Status:**\n"

            "- **Operating Hours:** 8:00 AM to 5:00 PM between Bhawan and Bhairon Temple.\n"

            "- **Weather Clearance:** Suspended during severe mountain gusts or torrential rainfall."

        )



    if agg_status == "HAS_NOTICES" and notices:







        for n in notices:







            sev_icon = "🚨" if n.get("severity") in ("CRITICAL", "HIGH") else "⚠️"







            parts.append(f"\n{sev_icon} **{n.get('notice_title')}**")







            parts.append(f"- **Authority:** {n.get('issuing_authority')}")







            parts.append(f"- **Route/Location:** {n.get('affected_location')} ({n.get('affected_route') or 'General'})")







            parts.append(f"- **Summary:** {n.get('translated_summary') or n.get('notice_text')}")







            if n.get("notice_lifecycle_status") == "REQUIRES_REVERIFICATION":







                parts.append("⚠️ *Note: Expected validity horizon has lapsed without official withdrawal. Confirm directly before travel.*")







    elif agg_status == "SOURCE_UNAVAILABLE":







        parts.append(







            "\n⚠️ **Operational Notice Information Unavailable:** The curated notice registry could not be accessed at this time. "







            "This does not mean that routes are clear or that no disruptions exist. "







            "Please verify current conditions directly with the Shrine Board Central Office (1800-180-7212) or Traffic Police (112) before travelling."







        )







    else:







        parts.append(







            "\nNo active track closures or suspension notices are recorded in the curated registry as of today. "







            "Please note: upstream live track status remains unconfirmed without direct Shrine Board verification. "







            "We strongly recommend checking at the Katra Yatra Registration Counter or calling SMVDSB helpline (1800-180-7212) before trekking."







        )















    reply_text = "\n".join(parts)







    res = {







        "reply": reply_text,







        "intent": "OPERATIONAL_NOTICE",







        "status": "SUCCESS",







        "session_id": sid,







        "request": current_request or {},







        "plan": None,







        "itinerary": current_itinerary,







        "recommendation": None,







        "action": None,







        "hotel": None,







        "budget_evaluation": None,







        "knowledge_sources": [],







        "operational_notices": notice_res,







        "last_tourism_place": last_tourism_place,







        "last_itinerary_context": last_itinerary_context,







        "source": "central_agent_deterministic",







        "response_source": "central_agent",







        "knowledge_source": "curated_operational_notices",







        "tool_executions": [{







            "tool": "query_operational_notices",







            "args": {"route": req_route},







            "status": "SUCCESS",







            "result": notice_res,







            "duration_ms": 1.0,







        }],







        "execution_mode": "deterministic_operational_notice",







        "partial_failure": False,
        "circuit_breaker_state": llm_circuit_breaker.current_state,







    }







    from utils.provenance import attach_provenance_to_response







    return attach_provenance_to_response(res)























def _handle_deterministic_verified_contacts_turn(







    user_text: str,







    session_id: Optional[str] = None,







    current_request: Optional[Dict[str, Any]] = None,







    current_itinerary: Optional[List[Dict[str, Any]]] = None,







    last_tourism_place: Optional[str] = None,







    last_itinerary_context: Optional[Dict[str, Any]] = None,







) -> Dict[str, Any]:







    sid = session_id or session_store.create_session()["session_id"]







    contact_res = lookup_verified_contacts.invoke({})







    contacts = contact_res.get("contacts") or []















    parts = [







        "🙏 **Jai Mata Di!** Here are the verified official emergency and helpline contacts:",







        "\n🚨 **PRIMARY STATUTORY EMERGENCY (Pan-India & J&K): Dial 112** (24x7 for Police, Fire, Ambulance & Life Safety)",







        "\n**Official Authority Directories:**",







    ]







    for c in contacts:







        if c.get("is_primary_emergency"):







            continue







        cat_icon = "🏥" if "MEDICAL" in c.get("category", "") else ("🚦" if "TRAFFIC" in c.get("category", "") else ("👮" if "POLICE" in c.get("category", "") else "🔱"))







        parts.append(f"- {cat_icon} **{c.get('organization')}**: `{c.get('telephone_number')}` ({c.get('service_description')}) — *Hours: {c.get('operating_hours')}*")















    reply_text = "\n".join(parts)







    res = {







        "reply": reply_text,







        "intent": "VERIFIED_CONTACTS",







        "status": "SUCCESS",







        "session_id": sid,







        "request": current_request or {},







        "plan": None,







        "itinerary": current_itinerary,







        "recommendation": None,







        "action": None,







        "hotel": None,







        "budget_evaluation": None,







        "knowledge_sources": [],







        "verified_contacts": contact_res,







        "last_tourism_place": last_tourism_place,







        "last_itinerary_context": last_itinerary_context,







        "source": "central_agent_deterministic",







        "response_source": "central_agent",







        "knowledge_source": "verified_contacts_registry",







        "tool_executions": [{







            "tool": "lookup_verified_contacts",







            "args": {},







            "status": "SUCCESS",







            "result": contact_res,







            "duration_ms": 1.0,







        }],







        "execution_mode": "deterministic_verified_contacts",







        "partial_failure": False,
        "circuit_breaker_state": llm_circuit_breaker.current_state,







    }







    from utils.provenance import attach_provenance_to_response







    return attach_provenance_to_response(res)























# -----------------------------------------------------------------------------







# 5. CONVERSATIONAL TURN ORCHESTRATION & SAFEGUARDED ROUTING







# -----------------------------------------------------------------------------















def process_conversational_turn(







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







    """Central AI Agent entry point for Yatra AI with Hybrid Orchestration & Partial Fallback.















    Execution Flow:







    1. Deterministic Booking Gate: Explicit booking navigation and authorization confirmations







       are routed immediately to deterministic logic (LLM is NEVER permitted to confirm bookings).







    2. Deterministic Greeting Fast-Path: Simple devotional greetings are served instantly without tool calls.







    3. Multi-Tool Reasoning (LLM): If an active LLM is available, executes tool calls with bounded







       iterations, per-tool timeouts, concurrent independent execution, and loop prevention.







    4. Partial Failure Protection: Failures or timeouts in individual tools do not drop successful results.







    5. Deterministic Fallback: When the LLM is unavailable, times out, or throws an error,







       automatically falls back to the deterministic orchestrator pipeline.







    """







    import agents.orchestrator as orchestrator

    from agents import conversation_state



    t_start = time.perf_counter()

    timing: Dict[str, Any] = {

        "intent_ms": 0.0,

        "rag_ms": 0.0,

        "tools_ms": 0.0,

        "llm_ttft_ms": 0.0,

        "llm_total_ms": 0.0,

        "total_ms": 0.0,

    }



    # Fast-Path Guard 1: Pure Devotional Greetings (< 1ms, zero I/O)

    if is_simple_greeting(user_text):

        sid = session_id or str(uuid.uuid4())

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** Welcome to Yatra AI, your devoted pilgrimage and travel companion for Maa Vaishno Devi. "

                "How may I assist your holy yatra today? You can ask me about live Katra & Bhawan weather, trek routes, "

                "mandatory RFID registration guidelines, available trains, or planning a complete personalized itinerary."

            ),

            "intent": "GENERAL",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_greeting",

            "tool_executions": [],

            "execution_mode": "deterministic_greeting",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

            "timing": timing,

        }

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)



    # Fast-Path Guard 2: Pure Acknowledgments & Gratitude (< 1ms, zero I/O)

    if is_simple_acknowledgment(user_text):

        sid = session_id or str(uuid.uuid4())

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** You are most welcome! May Mata Rani shower Her divine blessings upon your holy pilgrimage. "

                "Whenever you need assistance with Katra weather, helicopter updates, train schedules, or trek advisories, "

                "I am always here to guide you."

            ),

            "intent": "ACKNOWLEDGMENT",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_acknowledgment",

            "tool_executions": [],

            "execution_mode": "deterministic_acknowledgment",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

            "timing": timing,

        }

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)



    # Fast-Path Guard 3: User Help / Capabilities (< 1ms, zero I/O)

    if is_help_query(user_text):

        sid = session_id or str(uuid.uuid4())

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** Here is what I can assist you with for your sacred pilgrimage to Maa Vaishno Devi:\n\n"

                "- 🌦️ **Live Weather & Altitude Guidance:** Real-time conditions across Katra, Ardhkuwari, Bhawan, and Bhairon Temple.\n"

                "- 🚆 **Transport & Connectivity:** Direct and connecting trains, flights, and bus schedules from any Indian city.\n"

                "- 🏨 **Verified Accommodations:** Official Shrine Board bhavans and registered Katra hotels.\n"

                "- 📜 **Track & Trek Advisories:** Official notices on Traditional Track vs Tarakote Marg, battery cars, palkis, and ropeway.\n"

                "- 🎫 **Registration & Rules:** Mandatory RFID Yatra Registration Parchi guidelines, valid IDs, and sanctum dress code.\n"

                "- 🗺️ **Comprehensive Itinerary:** Customized multi-day pilgrimage planning with real-time budget optimization."

            ),

            "intent": "HELP",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_help",

            "tool_executions": [],

            "execution_mode": "deterministic_help",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

            "timing": timing,

        }

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)



    # Fast-Path Guard 4: Official Operational Notices & Helplines (Direct retrieval, no LLM required)

    if is_operational_notice_query(user_text):

        notice_res = _handle_deterministic_operational_notice_turn(

            user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context

        )

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        notice_res["timing"] = timing

        return notice_res



    if is_verified_contact_query(user_text):

        contact_res = _handle_deterministic_verified_contacts_turn(

            user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context

        )

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        contact_res["timing"] = timing

        return contact_res



    # Step 0: Hydrate session and update structured conversation state (for planning/multi-turn stateful interactions)

    session = None

    if session_id:

        try:

            session = session_store.get_session(session_id)

        except Exception:

            session = None



    if not session or session.get("_corrupted"):

        initial_st = {}

        if current_request:

            initial_st["requirements"] = current_request

        if current_itinerary:

            initial_st["itinerary"] = current_itinerary

        if last_tourism_place:

            initial_st["last_tourism_place"] = last_tourism_place

        if last_itinerary_context:

            initial_st["last_itinerary_context"] = last_itinerary_context

        session = session_store.create_session(session_id=session_id, initial_state=initial_st)



    sid = session["session_id"]

    updated_session = conversation_state.update_conversation_state(user_text, current_state=session)

    merged_req = updated_session.get("state", {}).get("requirements", {})

    session_store.update_session(sid, updates={"requirements": merged_req})

    session["state"]["requirements"] = merged_req

    current_request = merged_req



    # Guardrail: Rejection of adversarial attempts to bypass statutory RFID/security/registration

    lower_text = (user_text or "").lower()

    if re.search(r"\b(bypass|hack|crack|circumvent|counterfeit|spoof|clone)\b", lower_text) and re.search(

        r"\b(rfid|scanner|checkpost|checkpoint|gate|registration|parchi|yatra card|access card|card)\b", lower_text

    ):

        refusal_reply = (

            "🙏 **Jai Mata Di!**\n\n"

            "I cannot assist with bypassing security protocols, RFID access scanners, or registration check-posts.\n\n"

            "Under statutory regulations of the **Shri Mata Vaishno Devi Shrine Board (SMVDSB)**, obtaining an official "

            "**RFID Yatra Access Card** at Katra registration counters is **compulsory and mandatory** for every pilgrim before "

            "entering the yatra track at Banganga or Tarakote Marg. The RFID card is issued free of charge 24x7 and ensures "

            "pilgrim safety, tracking, crowd management, and statutory insurance coverage throughout the pilgrimage."

        )

        session_store.add_message(sid, "user", user_text)

        session_store.add_message(sid, "assistant", refusal_reply)

        return {

            "status": "SUCCESS",

            "reply": refusal_reply,

            "intent": "ADVERSARIAL_GUARDRAIL",

            "plan": None,

            "session_id": sid,

            "model_used": "deterministic_safety_guardrail",

            "source": "safety_guardrail",

        }















    # Step 1: Resolve active LLM







    active_llm = llm if llm is not None else get_groq_llm()















    # Step 2: Enforce Booking Safeguard (Deterministic Routing)







    # Invariant: LLM must NEVER autonomously confirm bookings or bypass human authorization.







    t0_intent = time.perf_counter()

    intent = conversation_agent.detect_intent(user_text)

    timing["intent_ms"] = round((time.perf_counter() - t0_intent) * 1000.0, 2)















    if intent in ("BOOKING_INTENT", "BOOKING"):







        b_res = orchestrator.orchestrate_conversational_turn(







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







        b_res["execution_mode"] = "deterministic_booking"







        b_res.setdefault("partial_failure", False)







        return b_res















    # Step 3: Fast-Path for Simple Greetings, Acknowledgments & Help (Zero-latency deterministic responses)

    if is_simple_greeting(user_text) or intent == "GREETING":

        sid = session_id or session_store.create_session()["session_id"]

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** Welcome to Yatra AI, your devoted pilgrimage and travel companion for Maa Vaishno Devi. "

                "How may I assist your holy yatra today? You can ask me about live Katra & Bhawan weather, trek routes, "

                "mandatory RFID registration guidelines, available trains, or planning a complete personalized itinerary."

            ),

            "intent": "GENERAL",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_greeting",

            "tool_executions": [],

            "execution_mode": "deterministic_greeting",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

        }

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res["timing"] = timing

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)



    if is_simple_acknowledgment(user_text) or intent == "ACKNOWLEDGMENT":

        sid = session_id or session_store.create_session()["session_id"]

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** You are most welcome! May Mata Rani shower Her divine blessings upon your holy pilgrimage. "

                "Whenever you need assistance with Katra weather, helicopter updates, train schedules, or trek advisories, "

                "I am always here to guide you."

            ),

            "intent": "ACKNOWLEDGMENT",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_acknowledgment",

            "tool_executions": [],

            "execution_mode": "deterministic_acknowledgment",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

        }

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res["timing"] = timing

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)



    if is_help_query(user_text) or intent == "HELP":

        sid = session_id or session_store.create_session()["session_id"]

        res = {

            "reply": (

                "🙏 **Jai Mata Di!** Here is what I can assist you with for your sacred pilgrimage to Maa Vaishno Devi:\n\n"

                "- 🌦️ **Live Weather & Altitude Guidance:** Real-time conditions across Katra, Ardhkuwari, Bhawan, and Bhairon Temple.\n"

                "- 🚆 **Transport & Connectivity:** Direct and connecting trains, flights, and bus schedules from any Indian city.\n"

                "- 🏨 **Verified Accommodations:** Official Shrine Board bhavans and registered Katra hotels.\n"

                "- 📜 **Track & Trek Advisories:** Official notices on Traditional Track vs Tarakote Marg, battery cars, palkis, and ropeway.\n"

                "- 🎫 **Registration & Rules:** Mandatory RFID Yatra Registration Parchi guidelines, valid IDs, and sanctum dress code.\n"

                "- 🗺️ **Comprehensive Itinerary:** Customized multi-day pilgrimage planning with real-time budget optimization."

            ),

            "intent": "HELP",

            "status": "SUCCESS",

            "session_id": sid,

            "request": current_request or {},

            "plan": None,

            "itinerary": current_itinerary,

            "recommendation": None,

            "action": None,

            "hotel": None,

            "budget_evaluation": None,

            "knowledge_sources": [],

            "last_tourism_place": last_tourism_place,

            "last_itinerary_context": last_itinerary_context,

            "source": "central_agent_deterministic",

            "response_source": "central_agent",

            "knowledge_source": "central_agent_help",

            "tool_executions": [],

            "execution_mode": "deterministic_help",

            "partial_failure": False,
            "circuit_breaker_state": llm_circuit_breaker.current_state,

        }

        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        res["timing"] = timing

        from utils.provenance import attach_provenance_to_response

        return attach_provenance_to_response(res)















    # Step 3B: Deterministic Operational Notices & Contacts Fast-Path (when LLM is not active)







    if active_llm is None or not hasattr(active_llm, "bind_tools") or not llm_circuit_breaker.can_attempt():







        if is_operational_notice_query(user_text):







            return _handle_deterministic_operational_notice_turn(







                user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context







            )







        if is_verified_contact_query(user_text):







            return _handle_deterministic_verified_contacts_turn(







                user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context







            )
        if is_accommodation_info_query(user_text):
            return _handle_deterministic_accommodation_turn(
                user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context
            )















    # Step 4: Execute LLM Tool-Calling Pipeline with Partial Failure Protection & Circuit Breaker
    llm_turn_error = None
    if active_llm and hasattr(active_llm, "bind_tools"):
        if not llm_circuit_breaker.can_attempt():
            cb_state = llm_circuit_breaker.current_state
            logger.info("CentralAgent LLM circuit breaker is %s; bypassing LLM call to deterministic orchestrator.", cb_state)
            llm_turn_error = f"Circuit breaker {cb_state} (rate limit / network timeout recovery window)"
        else:
            try:
                res = _execute_llm_tool_calling_turn(
                    user_text=user_text,
                    active_llm=active_llm,
                    session_id=session_id,
                    current_request=current_request,
                    current_itinerary=current_itinerary,
                    last_tourism_place=last_tourism_place,
                    last_itinerary_context=last_itinerary_context,
                    pending_options=pending_options,
                    t_start=t_start,
                    timing=timing,
                )
                llm_circuit_breaker.record_success()
                res["circuit_breaker_state"] = llm_circuit_breaker.current_state
                return res
            except Exception as exc:
                llm_turn_error = f"{type(exc).__name__}: {exc}"
                llm_circuit_breaker.record_failure(exc)
                logger.error(
                    "CentralAgent LLM tool-calling encountered error (%s) with model %s; circuit breaker state is %s; executing graceful deterministic fallback.",
                    exc,
                    getattr(active_llm, "model_name", "unknown"),
                    llm_circuit_breaker.current_state,
                )















    # Step 5: Fallback: Run deterministic orchestrator pipeline







    if is_operational_notice_query(user_text):







        return _handle_deterministic_operational_notice_turn(







            user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context







        )







    if is_verified_contact_query(user_text):







        return _handle_deterministic_verified_contacts_turn(







            user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context







        )
        if is_accommodation_info_query(user_text):
            return _handle_deterministic_accommodation_turn(
                user_text, session_id, current_request, current_itinerary, last_tourism_place, last_itinerary_context
            )















    fallback_res = orchestrator.orchestrate_conversational_turn(







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







    fallback_res["execution_mode"] = "deterministic_fallback"
    fallback_res.setdefault("partial_failure", False)
    fallback_res.setdefault("tool_executions", [])
    fallback_res["llm_attempted"] = (active_llm is not None)
    fallback_res["model"] = getattr(active_llm, "model_name", None)
    fallback_res["circuit_breaker_state"] = llm_circuit_breaker.current_state
    if "llm_turn_error" in locals() and llm_turn_error:
        fallback_res["llm_error"] = llm_turn_error
        if "Circuit breaker" in llm_turn_error:
            fallback_res["fallback_reason"] = "LLM circuit breaker OPEN (API network/rate-limit recovery window)"
        else:
            fallback_res["fallback_reason"] = f"LLM execution error: {llm_turn_error}"
    elif active_llm is None:
        fallback_res["fallback_reason"] = "No active LLM configured or available (GROQ_API_KEY unset or ChatGroq unavailable)"
    else:
        fallback_res["fallback_reason"] = "Deterministic routing applied"
    timing["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)
    fallback_res["timing"] = timing
    return fallback_res























def _execute_llm_tool_calling_turn(
    user_text: str,
    active_llm: Any,
    session_id: Optional[str] = None,
    current_request: Optional[Dict[str, Any]] = None,
    current_itinerary: Optional[List[Dict[str, Any]]] = None,
    last_tourism_place: Optional[str] = None,
    last_itinerary_context: Optional[Dict[str, Any]] = None,
    pending_options: Optional[Any] = None,
    t_start: Optional[float] = None,
    timing: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:







    """Executes multi-tool reasoning and execution cycle using LangChain bind_tools.







    Features:







    - Bounded iterations (max 3) and per-tool timeout (5.0s).







    - Concurrent independent tool execution via ThreadPoolExecutor.







    - Duplicate tool-call prevention and loop avoidance.







    - Partial failure resilience (successful tools survive if another tool fails).







    """







    # Step A: Hydrate session







    session = None







    if session_id:







        try:







            session = session_store.get_session(session_id)







        except Exception:







            session = None















    if not session or session.get("_corrupted"):







        initial_st = {}







        if current_request:







            initial_st["requirements"] = current_request







        if current_itinerary:







            initial_st["itinerary"] = current_itinerary







        if last_tourism_place:







            initial_st["last_tourism_place"] = last_tourism_place







        if last_itinerary_context:







            initial_st["last_itinerary_context"] = last_itinerary_context







        session = session_store.create_session(session_id=session_id, initial_state=initial_st)















    sid = session["session_id"]







    state = session.get("state", {})







    req = dict(state.get("requirements", {}))
    try:
        extracted = conversation_agent.extract_requirements(user_text, req)
        if extracted:
            for k, v in extracted.items():
                if v is not None:
                    if k == "pax" and v == 1 and req.get("pax", 1) > 1 and "1" not in user_text and "one" not in user_text.lower() and "solo" not in user_text.lower():
                        continue
                    req[k] = v
    except Exception as exc:
        logger.warning("Failed to extract requirements in central_agent: %s", exc)

    if current_request:
        for k, v in current_request.items():
            if v is not None:
                req[k] = v

    state["requirements"] = req
    session_store.update_session(sid, updates={"requirements": req})















    # Step B: Record user message







    intent = conversation_agent.detect_intent(user_text)







    session_store.add_message(







        session_id=sid,







        role="user",







        content=user_text,







        metadata={"intent": intent},







    )















    # Step C: Prepare Messages







    system_prompt = CENTRAL_AGENT_SYSTEM_PROMPT







    if req:







        state_summary = conversation_state.format_state_summary({"requirements": req})

        system_prompt += (

            f"\n\nCURRENT CONFIRMED CONVERSATION STATE:\n{state_summary}\n"

            f"Requirements Details: {json.dumps(req)}\n\n"

            "CRITICAL CONVERSATIONAL RULES:\n"

            "1. NEVER ask the pilgrim for any detail already present in CURRENT CONFIRMED CONVERSATION STATE (origin, destination, pilgrim count, travel style, etc.).\n"

            "2. Acknowledge supplied details warmly and ask ONLY for the next missing information (e.g. travel dates/duration) if needed.\n"

            "3. If the user enters ANY Indian city as origin (e.g. Pune, Jaipur, Chandigarh, Lucknow), accept it and provide authentic route guidance.\n"

        )







    if state.get("selected_options"):







        sel_tr = (state.get("selected_options") or {}).get("transport") or {}







        sel_ht = state.get("hotel") or {}







        system_prompt += f"\nActive Plan: Selected Transport={sel_tr.get('mode', 'N/A')}, Hotel={sel_ht.get('name', 'N/A')}"















    messages = [SystemMessage(content=system_prompt)]















    # Include recent session turns for multi-turn context







    recent_history = session_store.get_messages(sid)



    if recent_history:

        for msg in recent_history[-5:-1]:  # Limit to last 4 messages (2 user turns, 2 assistant turns)

            if msg.get("role") == "user":

                messages.append(HumanMessage(content=msg.get("content", "")))

            elif msg.get("role") == "assistant":

                asst_content = msg.get("content", "")

                if len(asst_content) > 250:

                    asst_content = asst_content[:240].rsplit(" ", 1)[0] + "... [prior response summary]"

                messages.append(AIMessage(content=asst_content))















    messages.append(HumanMessage(content=user_text))















    # Step D: Bind tools & execute tool-calling loop







    turn_tools = select_tools_for_turn(user_text=user_text, intent=intent, current_request=req)
    llm_with_tools = active_llm.bind_tools(turn_tools)
    t0_llm = time.perf_counter()
    llm_cumulative_ms = 0.0
    used_fallback_provider = False
    try:
        response = llm_with_tools.invoke(messages)
        llm_cumulative_ms += (time.perf_counter() - t0_llm) * 1000.0
    except Exception as exc:
        logger.warning(
            "Primary LLM invocation failed (%s: %s). Attempting fallback model...",
            getattr(active_llm, "model_name", "primary"),
            exc,
        )
        fallback_llm = get_fallback_groq_llm()
        if fallback_llm and getattr(fallback_llm, "model_name", "") != getattr(active_llm, "model_name", ""):
            try:
                active_llm = fallback_llm
                llm_with_tools = fallback_llm.bind_tools(turn_tools)
                t0_fb = time.perf_counter()
                response = llm_with_tools.invoke(messages)
                llm_cumulative_ms += (time.perf_counter() - t0_fb) * 1000.0
                used_fallback_provider = True
            except Exception as exc2:
                logger.error(
                    "Fallback LLM invocation also failed (%s: %s). Escalating to deterministic orchestrator.",
                    getattr(fallback_llm, "model_name", "fallback"),
                    exc2,
                )
                raise exc2
        else:
            raise exc















    executed_tools_info: List[Dict[str, Any]] = []







    seen_calls: Dict[str, ToolExecutionRecord] = {}















    captured_plan = None







    captured_itinerary = None







    captured_recommendation = None







    captured_action = None







    captured_budget = None







    captured_hotel = None







    captured_availability = None







    captured_operational_notices = None







    captured_verified_contacts = None







    captured_sources = []







    detected_place = last_tourism_place or state.get("last_tourism_place")















    iteration = 0







    max_iterations = 3















    while getattr(response, "tool_calls", None) and iteration < max_iterations:







        iteration += 1







        messages.append(response)















        # Batch execute tools with concurrency and duplicate prevention







        batch_results = _execute_tool_batch(







            tool_calls=response.tool_calls,







            seen_calls=seen_calls,







            session_id=sid,







            per_tool_timeout=5.0,







        )















        for call, rec in batch_results:







            call_id = call.get("id") or f"call_{rec.tool}_{iteration}"







            executed_tools_info.append(rec.to_dict())















            t_name = rec.tool







            t_result = rec.result















            # Capture structured assets for UI response envelope on success







            if rec.status == ToolExecutionStatus.SUCCESS.value and isinstance(t_result, dict):







                if t_name == "evaluate_yatra_plan":







                    captured_plan = t_result







                    captured_itinerary = t_result.get("itinerary")







                    captured_budget = t_result.get("budget_evaluation")







                    captured_hotel = t_result.get("hotel")







                elif t_name == "modify_itinerary":







                    captured_itinerary = t_result.get("updated_itinerary")







                elif t_name == "check_slot_availability":







                    captured_availability = t_result







                elif t_name == "request_booking_intent":







                    captured_action = t_result.get("action", "NAVIGATE_TO_BOOKING")







                elif t_name == "search_yatra_knowledge":







                    for s in (t_result.get("sources") or []):







                        if s not in captured_sources:







                            captured_sources.append(s)







                    if t_result.get("location"):







                        detected_place = t_result.get("location") or detected_place







                elif t_name == "get_tourism_knowledge":







                    detected_place = t_result.get("place") or detected_place







                elif t_name == "query_operational_notices":







                    captured_operational_notices = t_result







                elif t_name == "lookup_verified_contacts":







                    captured_verified_contacts = t_result















            # Prepare message content for LLM







            if rec.status in (







                ToolExecutionStatus.FAILURE.value,







                ToolExecutionStatus.TIMEOUT.value,







                ToolExecutionStatus.INVALID_TOOL_RESPONSE.value,







            ):







                tool_msg_content = json.dumps({







                    "status": rec.status,







                    "tool": t_name,







                    "error": rec.error or "Service temporarily unavailable.",







                    "notice": (







                        f"Specialist tool '{t_name}' failed with status '{rec.status}'. "







                        "State honestly to the user that this specific capability was unavailable, "







                        "and do NOT invent or fabricate facts, prices, or schedules for it."







                    )







                })







            else:
                if t_name == "search_yatra_knowledge" and isinstance(t_result, dict):
                    compact_dict = {
                        "query": t_result.get("query"),
                        "context": (t_result.get("answer_context") or "")[:1200],
                        "sources": (t_result.get("source_titles") or [])[:3],
                    }
                    tool_msg_content = json.dumps(compact_dict)
                elif isinstance(t_result, dict):
                    dumped = json.dumps(t_result, default=str)
                    if len(dumped) > 1500:
                        tool_msg_content = dumped[:1400] + "... [truncated for length]"
                    else:
                        tool_msg_content = dumped
                else:
                    tool_msg_content = str(t_result)[:1500]















            messages.append(ToolMessage(







                content=tool_msg_content,







                tool_call_id=call_id,







                name=t_name,







            ))















        # Re-invoke LLM with tool outputs to produce synthesis







        try:







            t0_synth = time.perf_counter()
            response = active_llm.invoke(messages)
            llm_cumulative_ms += (time.perf_counter() - t0_synth) * 1000.0







        except Exception as synth_err:







            logger.warning("LLM re-invocation/synthesis failed (%s); utilizing partial fallback synthesis.", synth_err)







            return _synthesize_partial_fallback(







                executed_tools=executed_tools_info,







                user_text=user_text,







                session_id=sid,







                req=req,







                state=state,







                intent=intent,







                captured_plan=captured_plan,







                captured_itinerary=captured_itinerary,







                captured_sources=captured_sources,







                detected_place=detected_place,







                captured_availability=captured_availability,







                captured_action=captured_action,







                captured_budget=captured_budget,







                captured_hotel=captured_hotel,







                last_itinerary_context=last_itinerary_context,







                captured_operational_notices=captured_operational_notices,







                captured_verified_contacts=captured_verified_contacts,







            )















    # Step E: Extract final reply text







    reply_content = getattr(response, "content", "")







    if isinstance(reply_content, list):







        reply_text = "\n".join(str(c) for c in reply_content)







    else:







        reply_text = str(reply_content or "")















    # If model ended on tool calls without synthesis (iteration limit reached)







    if getattr(response, "tool_calls", None) and not reply_text.strip():







        return _synthesize_partial_fallback(







            executed_tools=executed_tools_info,







            user_text=user_text,







            session_id=sid,







            req=req,







            state=state,







            intent=intent,







            captured_plan=captured_plan,







            captured_itinerary=captured_itinerary,







            captured_sources=captured_sources,







            detected_place=detected_place,







            captured_availability=captured_availability,







            captured_action=captured_action,







            captured_budget=captured_budget,







            captured_hotel=captured_hotel,







            last_itinerary_context=last_itinerary_context,







            captured_operational_notices=captured_operational_notices,







            captured_verified_contacts=captured_verified_contacts,







        )















    if not reply_text.strip():







        reply_text = "🙏 **Jai Mata Di!** Your request has been processed successfully."















    # Assess partial failure status







    has_failed_tools = any(







        t.get("status") in (







            ToolExecutionStatus.FAILURE.value,







            ToolExecutionStatus.TIMEOUT.value,







            ToolExecutionStatus.INVALID_TOOL_RESPONSE.value,







            ToolExecutionStatus.UNAVAILABLE.value,







        )







        for t in executed_tools_info







    )







    has_successful_tools = any(







        t.get("status") == ToolExecutionStatus.SUCCESS.value







        for t in executed_tools_info







    )















    status_val = "SUCCESS"







    if captured_plan:







        status_val = "PLAN_READY"







    elif has_failed_tools and not has_successful_tools:







        status_val = "UNAVAILABLE"







    elif has_failed_tools and has_successful_tools:







        status_val = "PARTIAL_SUCCESS"















    # Step F: Assemble standardized response envelope







    final_res: Dict[str, Any] = {







        "reply": reply_text,







        "intent": intent,







        "status": status_val,







        "session_id": sid,







        "request": req,







        "plan": captured_plan or state.get("pending_options"),







        "itinerary": captured_itinerary or state.get("itinerary"),







        "recommendation": captured_recommendation or state.get("recommendation"),







        "action": captured_action,







        "hotel": captured_hotel or state.get("hotel"),







        "budget_evaluation": captured_budget or state.get("budget_evaluation"),







        "knowledge_sources": captured_sources,







        "last_tourism_place": detected_place,







        "last_itinerary_context": last_itinerary_context or state.get("last_itinerary_context"),







        "source": "central_agent_langchain",







        "response_source": "central_agent",







        "knowledge_source": "langchain_tool_registry",







        "tool_executions": executed_tools_info,







        "partial_failure": has_failed_tools,







        "execution_mode": (
            "rag_assisted_llm" if any(t.get("tool") in ("search_yatra_knowledge", "get_tourism_knowledge") for t in executed_tools_info)
            else "tool_assisted_llm" if executed_tools_info
            else "provider_fallback" if used_fallback_provider
            else "llm"
        ),
        "circuit_breaker_state": llm_circuit_breaker.current_state,
        "provider_fallback": used_fallback_provider,







    }















    if captured_availability:







        final_res["availability_result"] = captured_availability







        final_res["intent"] = "AVAILABILITY"















    if captured_operational_notices:







        final_res["operational_notices"] = captured_operational_notices















    if captured_verified_contacts:







        final_res["verified_contacts"] = captured_verified_contacts















    try:







        from utils.provenance import attach_provenance_to_response







        final_res = attach_provenance_to_response(final_res, tool_executions=executed_tools_info)







    except Exception as prov_err:







        logger.warning("Failed to attach provenance to CentralAgent response: %s", prov_err)







        final_res.setdefault("source_provenance", [])







        final_res.setdefault("live_sources", [])















    # Persist assistant turn in session store







    session_store.add_message(







        session_id=sid,







        role="assistant",







        content=reply_text,







        metadata={







            "intent": intent,







            "source": "central_agent_langchain",







            "tool_executions": executed_tools_info,







            "source_provenance": final_res.get("source_provenance", []),







            "data_provenance": final_res.get("data_provenance", final_res.get("source_provenance", [])),







            "live_sources": final_res.get("live_sources", []),







            "is_cached": final_res.get("is_cached", False),







            "partial_failure": has_failed_tools,







            "execution_mode": final_res.get("execution_mode", "hybrid_llm"),







            "knowledge_sources": captured_sources,







        },







    )















    # Update session state with newly generated assets







    updates: Dict[str, Any] = {







        "last_tourism_place": detected_place,







    }







    if captured_itinerary:







        updates["itinerary"] = captured_itinerary







    if captured_budget:







        updates["budget_evaluation"] = captured_budget







    if captured_hotel:







        updates["hotel"] = captured_hotel















    session_store.update_session(sid, updates=updates)















    timing_dict = timing if timing is not None else {}
    timing_dict["llm_ms"] = round(llm_cumulative_ms, 2)
    if t_start:
        timing_dict["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)
    final_res["timing"] = timing_dict
    final_res["model"] = getattr(active_llm, "model_name", "openai/gpt-oss-20b")
    final_res["llm_attempted"] = True
    final_res["llm_latency_ms"] = round(llm_cumulative_ms, 2)
    return final_res























# -----------------------------------------------------------------------------







# 9. LIVE DATA ARCHITECTURE BRIDGE (PHASE 9.5)







# -----------------------------------------------------------------------------















def query_live_data_service(







    domain: str,







    params: Optional[Dict[str, Any]] = None,







    location: Optional[str] = None,







    session_id: Optional[str] = None,







    bypass_cache: bool = False,







) -> Dict[str, Any]:







    """Integration bridge allowing conversational tools and orchestrators to retrieve







    live, cached, or curated information through the UnifiedLiveDataManager.







    Preserves response envelope standards, session isolation, and truth-in-data provenance.







    """







    from services.live_data.contracts import ProviderRequest







    from services.live_data.manager import get_live_data_manager















    manager = get_live_data_manager()







    req = ProviderRequest(







        domain=domain,







        params=params or {},







        location=location,







        session_id=session_id,







    )







    result = manager.execute_request(req, bypass_cache=bypass_cache)







    return result.to_dict()





def process_conversational_turn_stream(

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

):

    """

    Streaming generator for conversational turns.

    Yields events in SSE-compatible dictionaries:

      {"type": "start", "session_id": sid}

      {"type": "token", "content": word_or_token}

      {"type": "done", "response": complete_response_dict}

    """

    t0 = time.perf_counter()

    full_res = process_conversational_turn(

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

    sid = full_res.get("session_id") or session_id or "new"

    yield {"type": "start", "session_id": sid}



    reply_text = full_res.get("reply") or ""

    tokens = re.findall(r"\S+\s*|\s+", reply_text)

    if not tokens:

        tokens = [reply_text]



    chunk_size = 3

    for i in range(0, len(tokens), chunk_size):

        chunk = "".join(tokens[i : i + chunk_size])

        yield {"type": "token", "content": chunk}



    timing = full_res.get("timing") or {}

    timing["total_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    full_res["timing"] = timing

    full_res["latency_breakdown"] = timing



    yield {"type": "done", "response": full_res}
