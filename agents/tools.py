"""
agents/tools.py
LangChain-compatible tools for tool orchestration and agent dispatch.
Exposes modular data tools for searching transport options, yatra slots,
J&K tourism knowledge, weather guidance, and Playwright RPA automation.
"""

from typing import Optional, List, Dict, Any
from langchain.tools import tool
import db
import explore_data
import weather
import yatra_info
from agents import rpa_agent


def _search_trains_via_live_manager(origin: str, start_date: str, end_date: str = None, min_seats: int = 1) -> list:
    """Queries curated railway schedules via UnifiedLiveDataManager with strict truthfulness."""
    try:
        from services.live_data.manager import get_live_data_manager
        from services.live_data.contracts import ProviderRequest, DataDomain
        mgr = get_live_data_manager()
        req = ProviderRequest(
            domain=DataDomain.TRANSPORT.value,
            location=origin,
            params={"origin": origin, "destination": "Katra", "travel_date": start_date, "mode": "train"},
        )
        res = mgr.execute_request(req, provider_id="curated_railway_schedules")
        if res.is_success and isinstance(res.data, dict):
            schedules = res.data.get("schedules", [])
            formatted = []
            for s in schedules:
                classes = s.get("travel_classes") or ["Standard"]
                for tc in classes:
                    formatted.append({
                        "id": f"train_{s.get('train_number')}_{tc}",
                        "train_no": s.get("train_number"),
                        "train_name": s.get("train_name"),
                        "operator": "Indian Railways",
                        "transport_no": f"{s.get('train_number')} ({tc})",
                        "mode": "train",
                        "origin": s.get("origin_station_name"),
                        "origin_station_code": s.get("origin_station_code"),
                        "destination": s.get("destination_station_name"),
                        "destination_station_code": s.get("destination_station_code"),
                        "travel_date": start_date,
                        "departure_time": s.get("departure_time"),
                        "arrival_time": s.get("arrival_time"),
                        "travel_class": tc,
                        "price": None,
                        "fare": None,
                        "indicative_fare_min": None,
                        "indicative_fare_max": None,
                        "seats_available": None,
                        "availability_verified": False,
                        "seat_availability": "NOT_CHECKED",
                        "status": "TIMETABLE_SCHEDULE",
                        "is_live_status": False,
                        "verification_status": s.get("verification_status", "curated_guidance"),
                        "fare_classification": "UNAVAILABLE",
                        "fare_disclaimer": s.get("fare_disclaimer") or (
                            "Railway fares are unavailable in static demonstration registry. Real-time booking fares and "
                            "availability must be checked on the official IRCTC portal (irctc.co.in)."
                        ),
                        "source_circular_reference": s.get("source_circular_reference"),
                        "source_name": s.get("source_name", "Curated Indian Railways Route Guidance"),
                        "source_url": s.get("source_url"),
                        "route_verification": s.get("route_verification") or {
                            "status": "unverified",
                            "source_name": s.get("source_name", "Indian Railways"),
                            "document_reference": None,
                            "notes": "Railway route corridor claim unverified against authoritative registry.",
                        },
                        "operator_verification": s.get("operator_verification") or {
                            "status": "unverified",
                            "source_name": "Indian Railways",
                            "document_reference": None,
                            "notes": "Railway operator claim unverified.",
                        },
                        "timetable_verification": s.get("timetable_verification") or {
                            "status": "unverified",
                            "source_name": "National Train Enquiry System (NTES)",
                            "document_reference": None,
                            "notes": "Railway timetable claim unverified.",
                        },
                        "fare_verification": s.get("fare_verification") or {
                            "status": "unverified",
                            "source_name": "IRCTC",
                            "document_reference": None,
                            "notes": "Railway fare claim unverified; check official IRCTC portal.",
                        },
                        "route_note": (
                            "Curated railway route guidance. "
                            "Timetable and live delay telemetry not connected; verify with NTES (139). "
                            "Fares must be checked on the official IRCTC portal (irctc.co.in)."
                        ),
                    })
            return formatted
    except Exception:
        pass
    return db.search_trains(origin, start_date, end_date or start_date, min_seats=min_seats)


def _search_buses_via_live_manager(origin: str, start_date: str, end_date: str = None, min_seats: int = 1) -> list:
    """Queries curated bus schedules via UnifiedLiveDataManager with strict truthfulness."""
    try:
        from services.live_data.manager import get_live_data_manager
        from services.live_data.contracts import ProviderRequest
        mgr = get_live_data_manager()
        req = ProviderRequest(
            domain="transport",
            location=origin,
            params={"origin": origin, "destination": "Katra", "travel_date": start_date, "mode": "bus"},
        )
        res = mgr.execute_request(req, provider_id="curated_bus_schedules")
        if res.is_success and isinstance(res.data, dict):
            schedules = res.data.get("schedules", [])
            formatted = []
            for s in schedules:
                dep_time = s.get("departure_time")
                arr_time = s.get("arrival_time")
                fare_class = s.get("fare_classification", "STATUTORY_NOTIFIED_PER_KM_SLAB")
                # Fares are statutory per-km slabs or seasonal market ranges; neither is a confirmed booking price
                item_fare = None

                formatted.append({
                    "id": f"bus_{s.get('service_id')}",
                    "mode": "bus",
                    "operator": s.get("operator_name"),
                    "vehicle_name": f"{s.get('operator_name')} ({s.get('service_type', 'Stage Carriage')})",
                    "origin": s.get("origin_city"),
                    "origin_bus_stand": s.get("origin_bus_stand"),
                    "destination": s.get("destination_city", "Katra"),
                    "destination_bus_stand": s.get("destination_bus_stand"),
                    "departure_time": dep_time,
                    "departure_window": s.get("departure_window"),
                    "operating_hours": s.get("operating_hours"),
                    "arrival_time": arr_time,
                    "duration_hours": s.get("duration_hours") or 2.0,
                    "price": item_fare,
                    "fare": item_fare,
                    "indicative_fare_min": s.get("indicative_fare_min"),
                    "indicative_fare_max": s.get("indicative_fare_max"),
                    "fare_classification": fare_class,
                    "fare_disclaimer": s.get("fare_disclaimer"),
                    "available_seats": 20,
                    "status": "ROUTE GUIDANCE",
                    "source_type": "curated_data",
                    "verification_status": s.get("verification_status", "verified_curated_source"),
                    "route_verification": s.get("route_verification"),
                    "operator_verification": s.get("operator_verification"),
                    "timetable_verification": s.get("timetable_verification"),
                    "fare_verification": s.get("fare_verification"),
                    "is_live_status": False,
                    "source_name": s.get("source_name"),
                    "source_url": s.get("source_url"),
                    "route_note": f"Public Stage Carriage Service ({s.get('service_type')})",
                })
            return formatted
    except Exception as exc:
        pass
    return db.search_buses(origin, start_date, end_date or start_date, min_seats=min_seats)


def _search_flights_via_live_manager(origin: str, start_date: str, end_date: str = None, min_seats: int = 1) -> list:
    """Queries curated flight schedules via UnifiedLiveDataManager with strict truthfulness."""
    try:
        from services.live_data.manager import get_live_data_manager
        from services.live_data.contracts import ProviderRequest
        mgr = get_live_data_manager()
        req = ProviderRequest(
            domain="transport",
            location=origin,
            params={"origin": origin, "destination": "Jammu", "travel_date": start_date, "mode": "flight"},
        )
        res = mgr.execute_request(req, provider_id="curated_flight_schedules")
        if res.is_success and isinstance(res.data, dict):
            schedules = res.data.get("schedules", [])
            formatted = []
            for s in schedules:
                formatted.append({
                    "id": f"flight_{s.get('route_id')}",
                    "mode": "flight",
                    "airline": s.get("airline_name"),
                    "operator": s.get("airline_name"),
                    "flight_no": s.get("flight_number") or s.get("route_id"),
                    "transport_no": f"{s.get('airline_name')} {s.get('flight_number')}" if s.get("flight_number") else s.get("airline_name"),
                    "origin": s.get("origin_city"),
                    "origin_airport_code": s.get("origin_airport_code"),
                    "origin_airport_name": s.get("origin_airport_name"),
                    "destination": s.get("destination_city"),
                    "destination_airport_code": s.get("destination_airport_code"),
                    "destination_airport_name": s.get("destination_airport_name"),
                    "route_type": s.get("route_type", "DIRECT"),
                    "layover_airports": s.get("layover_airports", []),
                    "travel_date": start_date,
                    "departure_time": s.get("departure_time"),
                    "arrival_time": s.get("arrival_time"),
                    "duration_hours": s.get("duration_hours"),
                    "estimated_duration_desc": s.get("estimated_duration_desc"),
                    "schedule_type": s.get("schedule_type"),
                    "indicative_fare_min": s.get("indicative_fare_min"),
                    "indicative_fare_max": s.get("indicative_fare_max"),
                    "fare_classification": s.get("fare_classification", "ESTIMATED_MARKET_TARIFF"),
                    "fare_disclaimer": s.get("fare_disclaimer"),
                    "fare": None,
                    "price": None,
                    "price_per_pax": None,
                    "total_transport_cost": None,
                    "seats_available": None,
                    "route_verification": s.get("route_verification"),
                    "airline_verification": s.get("airline_verification"),
                    "timetable_verification": s.get("timetable_verification"),
                    "fare_verification": s.get("fare_verification"),
                    "is_live_status": False,
                    "source_name": s.get("source_name"),
                    "source_url": s.get("source_url"),
                    "notes": s.get("notes"),
                    "ground_transfer_advisory": (
                        "Jammu Airport (IXJ) is ~50 km from Katra (~1.5h). Authorized Prepaid Taxis "
                        "operate directly from the airport arrivals terminal. Public JKRTC buses "
                        "depart from Jammu Railway Station / General Bus Stand (~8 km from the airport)."
                    ),
                })
            return formatted
    except Exception as exc:
        pass
    return db.search_flights(origin, start_date, end_date or start_date, min_seats=min_seats)

@tool
def search_transport_tool(origin: str, start_date: str, end_date: str, mode: str = None, pax: int = 1) -> list:
    """Searches available transport options (flight, train, bus) from origin city to Jammu/Katra for given dates and passenger count."""
    searchers = {
        "flight": _search_flights_via_live_manager,
        "train": _search_trains_via_live_manager,
        "bus": _search_buses_via_live_manager,
    }
    if mode and mode.lower() in searchers:
        return searchers[mode.lower()](origin, start_date, end_date, min_seats=pax)

    results = []
    for m in ("flight", "train", "bus"):
        results.extend(searchers[m](origin, start_date, end_date, min_seats=pax))
    return results


@tool
def search_yatra_slots_tool(start_date: str, end_date: str, category: str = None, min_seats: int = 1) -> list:
    """Searches available Vaishno Devi yatra darshan slots (Normal Darshan, VIP Darshan, Helicopter Darshan)."""
    return db.search_yatra_slots(start_date, end_date, category=category, min_seats=min_seats)


@tool
def get_tourism_info_tool(place_or_query: str = "") -> dict:
    """Retrieves J&K tourism information, historical background, timings, entry fee, and video search link for Katra/Jammu spots."""
    if not place_or_query:
        return {"places": explore_data.get_places()}

    place = explore_data.get_place_by_name(place_or_query)
    if place:
        return place

    query_lower = place_or_query.lower()
    matched = [
        p for p in explore_data.get_places()
        if query_lower in p["name"].lower() or query_lower in p["category"].lower() or query_lower in p["description"].lower()
    ]
    return {"matched_places": matched if matched else explore_data.get_places()}


@tool
def check_weather_tool(location: str = "Katra") -> dict:
    """Provides seasonal and current weather forecast guidance for Katra and Vaishno Devi trek."""
    try:
        return weather.get_weather_summary(location)
    except Exception as e:
        return {
            "source": "fallback",
            "summary": "Mild and pleasant",
            "low_c": 12,
            "high_c": 24,
            "advisory": f"Weather lookup fallback active: {str(e)}",
        }


@tool
def execute_rpa_booking_tool(user_name: str, pax_count: int, transport_text: str, slot_text: str, total_price: float, headless: bool = True) -> dict:
    """Executes the Playwright mock browser automation workflow for a confirmed yatra booking."""
    return rpa_agent.execute_playwright_mock_booking(
        user_name=user_name,
        pax_count=pax_count,
        transport_text=transport_text,
        slot_text=slot_text,
        total_price=total_price,
        headless=headless,
    )


@tool
def check_yatra_availability_tool(date: str, category: Optional[str] = None, headless: bool = True) -> dict:
    """Checks real-time Vaishno Devi Yatra slot availability via Playwright RPA automation against the local mock portal.

    Use this tool whenever the user asks to check availability, search open slots, or verify remaining capacity
    for Vaishno Devi Darshan on a specific date (in YYYY-MM-DD ISO format) and optional darshan category
    ('Normal Darshan', 'VIP Darshan', 'Helicopter Darshan').

    Args:
        date: The yatra date in YYYY-MM-DD ISO format (e.g., '2026-11-20' or '2026-10-20').
        category: Optional category filter: 'Normal Darshan', 'VIP Darshan', or 'Helicopter Darshan'.
        headless: Whether to execute browser automation in headless mode (default True).

    Returns:
        Structured dictionary containing status ('SUCCESS', 'HANDOVER_REQUIRED'), requested date,
        category filter, total slots, breakdown counts (available, full, unavailable), slot records
        (with session, time, price, seats), empty state flag, and audit logs.
    """
    return rpa_agent.check_yatra_slot_availability(
        requested_date=date,
        category=category,
        headless=headless,
    )


# Standard alias for LangChain tool conventions
check_yatra_availability = check_yatra_availability_tool


def get_all_tools():
    """Returns the list of LangChain tool instances for agent orchestration."""
    return [
        search_transport_tool,
        search_yatra_slots_tool,
        get_tourism_info_tool,
        check_weather_tool,
        execute_rpa_booking_tool,
        check_yatra_availability_tool,
    ]
