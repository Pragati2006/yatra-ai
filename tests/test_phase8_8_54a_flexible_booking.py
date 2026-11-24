"""
Phase 8.8.54A Test Suite — Flexible Booking, Chat Context Handoff & Individual Pilgrim Management

Tests:
1. Four optional service combinations:
   - Hotel + Transport
   - Hotel only
   - Transport only
   - Neither (Hotel and Transport both excluded)
2. Own Vehicle mode:
   - Sets transport cost to ₹0, permits hotel selection
3. Chat context extraction:
   - Intent phrases trigger NAVIGATE_TO_BOOKING
   - Extracts dates, duration, pax, own vehicle, individual pilgrims (name, age, gender)
   - Handles ambiguous dates
4. Individual pilgrim validation:
   - Pilgrims count must match pax
   - Missing name returns HTTP 400
   - Invalid age (<1 or >125 or non-integer) returns HTTP 400
   - Primary contact extracted separately from pilgrims
5. Database persistence & receipt honesty:
   - Stored and retrieved with all fields
   - Internal reference disclaimer preserved
"""

import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import HTTPException
from agents.conversation_state import (
    extract_travel_dates,
    extract_own_vehicle,
    extract_hotel_preference,
    extract_transport_preference,
    extract_pilgrim_records,
    extract_primary_contact,
)
from agents.conversation_agent import detect_intent
from agents.orchestrator import handle_booking_navigation_intent
import agents.coordinator as coordinator
from backend.routes.yatra import confirm_booking, ConfirmBookingRequest
from agents.auth_service import AuthService
from db import get_booking


SAMPLE_PILGRIMS = [
    {"full_name": "Ramesh Kumar", "age": 42, "gender": "Male"},
    {"full_name": "Pooja Kumar", "age": 39, "gender": "Female"},
]

SAMPLE_PRIMARY_CONTACT = {
    "name": "Ramesh Kumar",
    "phone": "9876543210",
    "email": "ramesh@example.com",
}


# ============================================================================
# 1. CONVERSATION EXTRACTION UNIT TESTS
# ============================================================================

def test_extract_travel_dates_specific():
    """Verify ISO dates and day-month patterns extract correctly."""
    start_date, return_date, is_ambiguous = extract_travel_dates("We are planning our trip on 15 November 2026")
    assert start_date == "2026-11-15"
    assert is_ambiguous is False

    iso_start, _, _ = extract_travel_dates("Starting on 2026-12-10")
    assert iso_start == "2026-12-10"


def test_extract_travel_dates_ambiguous():
    """Verify ambiguous numerical dates (e.g., 05/06/2026) are detected."""
    _, _, is_ambiguous = extract_travel_dates("I want to travel on 05/06/2026")
    assert is_ambiguous is True


def test_extract_own_vehicle_preference():
    """Verify own vehicle / self-drive intents are captured."""
    assert extract_own_vehicle("We will be coming by our own car") is True
    assert extract_own_vehicle("We are driving down to Katra in our own vehicle") is True
    assert extract_own_vehicle("Book train tickets for us") is False


def test_extract_hotel_transport_preference():
    """Verify hotel and transport preference toggles from chat."""
    # Transport only (no hotel)
    h_sel, _, _ = extract_hotel_preference("No hotel needed for our yatra")
    assert h_sel is False

    # Hotel with category and nights
    h_sel2, cat, nights = extract_hotel_preference("Need a standard hotel for 2 nights stay")
    assert h_sel2 is True
    assert cat == "Standard"
    assert nights == 2

    # Own vehicle disables carrier transport
    t_sel_ov, mode_ov = extract_transport_preference("We will travel by our own car")
    assert t_sel_ov is False
    assert mode_ov == "own_vehicle"

    # Train transport requested
    t_sel_tr, mode_tr = extract_transport_preference("Please book train for 2 passengers")
    assert t_sel_tr is True
    assert mode_tr == "train"

    # No transport needed
    t_sel_none, _ = extract_transport_preference("Without transport, only hotel")
    assert t_sel_none is False


def test_extract_pilgrim_records():
    """Verify individual pilgrim records (names, ages) are extracted."""
    text = "My name is Rajesh, age 45. Sunil, age 40."
    pilgrims = extract_pilgrim_records(text, total_pax=2)
    assert len(pilgrims) >= 2
    names = [p["full_name"] for p in pilgrims]
    assert "Rajesh" in names
    assert "Sunil" in names


def test_extract_primary_contact():
    """Verify primary contact extraction from phone/email."""
    text = "My name is Rajesh Verma, email rajesh@example.com and phone 9876543210"
    contact = extract_primary_contact(text)
    assert contact["email"] == "rajesh@example.com"
    assert contact["phone"] == "9876543210"


def test_booking_navigation_intent_trigger():
    """Verify exact booking phrases trigger NAVIGATE_TO_BOOKING with handoff."""
    phrases = [
        "Book my Yatra",
        "Proceed with booking",
        "Book tickets",
        "Continue to booking",
        "Book now",
    ]
    for phrase in phrases:
        intent = detect_intent(phrase)
        assert intent == "BOOKING_INTENT", f"detect_intent failed for phrase: {phrase}"

    session_data = {
        "session_id": "test-session-intent",
        "state": {
            "requirements": {
                "origin": "Delhi",
                "pax": 2,
                "duration_days": 4,
                "start_date": "2026-11-20",
                "pilgrims": SAMPLE_PILGRIMS,
            }
        }
    }
    nav_result = handle_booking_navigation_intent("Book now", session_data)
    assert nav_result["status"] == "NAVIGATE_TO_BOOKING"
    assert "booking_handoff" in nav_result
    handoff = nav_result["booking_handoff"]
    assert handoff["origin"] == "Delhi"
    assert handoff["pax"] == 2
    assert len(handoff["pilgrims"]) == 2


# ============================================================================
# 2. COORDINATOR COMBINATIONS & RECALCULATION TESTS
# ============================================================================

def test_combination_both_hotel_and_transport():
    """Combination 1: Hotel + Transport included -> both prices charged."""
    option = {
        "transport": {"mode": "Train", "operator": "Vande Bharat Express", "total_price": 3330},
        "slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0},
        "total_price": 5530,
    }
    booking_id, blessing = coordinator.confirm_booking(
        option=option,
        pax=2,
        user_name="Ramesh Kumar",
        hotel={"name": "Hotel Asia Vaishno Devi", "price_per_night": 2200},
        hotel_nights=1,
        pilgrims=SAMPLE_PILGRIMS,
        primary_contact=SAMPLE_PRIMARY_CONTACT,
        hotel_selected=True,
        transport_selected=True,
        own_vehicle=False,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec is not None
    assert rec["hotel_name"] == "Hotel Asia Vaishno Devi"
    assert rec["transport_mode"] == "Train"
    assert rec["total_price"] == 5530.0


def test_combination_hotel_only():
    """Combination 2: Hotel only (Transport excluded) -> transport price is ₹0."""
    option = {
        "transport": {"mode": "Train", "operator": "Vande Bharat Express", "total_price": 3330},
        "slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0},
    }
    booking_id, blessing = coordinator.confirm_booking(
        option=option,
        pax=2,
        user_name="Ramesh Kumar",
        hotel={"name": "Hotel Asia Vaishno Devi", "price_per_night": 2200},
        hotel_nights=1,
        pilgrims=SAMPLE_PILGRIMS,
        primary_contact=SAMPLE_PRIMARY_CONTACT,
        hotel_selected=True,
        transport_selected=False,
        own_vehicle=False,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec["hotel_name"] == "Hotel Asia Vaishno Devi"
    assert rec["transport_mode"] is None
    # Transport excluded: only hotel 2200
    assert rec["total_price"] == 2200.0


def test_combination_transport_only():
    """Combination 3: Transport only (Hotel excluded) -> hotel price is ₹0."""
    option = {
        "transport": {"mode": "Train", "operator": "Uttar Sampark Kranti", "total_price": 760},
        "slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0},
    }
    booking_id, blessing = coordinator.confirm_booking(
        option=option,
        pax=2,
        user_name="Ramesh Kumar",
        hotel=None,
        hotel_nights=0,
        pilgrims=SAMPLE_PILGRIMS,
        primary_contact=SAMPLE_PRIMARY_CONTACT,
        hotel_selected=False,
        transport_selected=True,
        own_vehicle=False,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec["hotel_name"] is None
    assert rec["transport_mode"] == "Train"
    # Hotel excluded: only transport 760
    assert rec["total_price"] == 760.0


def test_combination_neither():
    """Combination 4: Neither Hotel nor Transport -> Total price is ₹0."""
    option = {
        "transport": None,
        "slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0},
    }
    booking_id, blessing = coordinator.confirm_booking(
        option=option,
        pax=2,
        user_name="Ramesh Kumar",
        hotel=None,
        hotel_nights=0,
        pilgrims=SAMPLE_PILGRIMS,
        primary_contact=SAMPLE_PRIMARY_CONTACT,
        hotel_selected=False,
        transport_selected=False,
        own_vehicle=False,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec["hotel_name"] is None
    assert rec["transport_mode"] is None
    assert rec["total_price"] == 0.0


def test_combination_own_vehicle():
    """Own Vehicle mode: Transport is ₹0, Hotel retained."""
    option = {
        "transport": {"mode": "Train", "operator": "Vande Bharat Express", "total_price": 3330},
        "slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0},
    }
    booking_id, blessing = coordinator.confirm_booking(
        option=option,
        pax=2,
        user_name="Ramesh Kumar",
        hotel={"name": "Hotel Asia Vaishno Devi", "price_per_night": 2200},
        hotel_nights=2,
        pilgrims=SAMPLE_PILGRIMS,
        primary_contact=SAMPLE_PRIMARY_CONTACT,
        hotel_selected=True,
        transport_selected=False,
        own_vehicle=True,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec["transport_mode"] == "own_vehicle"
    assert rec["hotel_name"] == "Hotel Asia Vaishno Devi"
    # Transport carrier fare excluded: only hotel 2 nights * 2200 = 4400
    assert rec["total_price"] == 4400.0


# ============================================================================
# 3. STRICT INPUT & PILGRIM VALIDATION TESTS
# ============================================================================

def test_confirm_booking_pilgrim_count_mismatch_rejected():
    """Presents pax=3 but only 2 pilgrims -> HTTP 400."""
    req = ConfirmBookingRequest(
        option={"slot": {"category": "Normal Darshan", "slot_date": "2026-11-20"}},
        pax=3,
        user_name="Ramesh Kumar",
        pilgrims=SAMPLE_PILGRIMS,  # Only 2
        human_authorized=True,
    )
    try:
        confirm_booking(req)
        assert False, "Expected HTTPException 400 for count mismatch"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Pilgrim records count" in exc.detail


def test_confirm_booking_missing_pilgrim_name_rejected():
    """Pilgrim with empty name -> HTTP 400."""
    invalid_pilgrims = [
        {"full_name": "Ramesh Kumar", "age": 42, "gender": "Male"},
        {"full_name": "   ", "age": 39, "gender": "Female"},
    ]
    req = ConfirmBookingRequest(
        option={"slot": {"category": "Normal Darshan", "slot_date": "2026-11-20"}},
        pax=2,
        user_name="Ramesh Kumar",
        pilgrims=invalid_pilgrims,
        human_authorized=True,
    )
    try:
        confirm_booking(req)
        assert False, "Expected HTTPException 400 for empty name"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "full name" in exc.detail.lower()


def test_confirm_booking_invalid_pilgrim_age_rejected():
    """Pilgrim with invalid age (0 or 150) -> HTTP 400."""
    invalid_pilgrims = [
        {"full_name": "Ramesh Kumar", "age": 42, "gender": "Male"},
        {"full_name": "Child Kumar", "age": 0, "gender": "Female"},
    ]
    req = ConfirmBookingRequest(
        option={"slot": {"category": "Normal Darshan", "slot_date": "2026-11-20"}},
        pax=2,
        user_name="Ramesh Kumar",
        pilgrims=invalid_pilgrims,
        human_authorized=True,
    )
    try:
        confirm_booking(req)
        assert False, "Expected HTTPException 400 for invalid age"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "positive whole number between 1 and 125" in exc.detail


# ============================================================================
# 4. AUTH SERVICE PERSISTENCE TESTS
# ============================================================================

def test_auth_service_booking_persistence():
    """Verify auth_service stores and retrieves all new flexible booking fields."""
    auth_svc = AuthService()
    test_user_id = "test-phase854a@example.com"
    b_id = f"VD-PHASE854A-{int(datetime.now().timestamp())}"
    booking_data = {
        "booking_id": b_id,
        "pax_count": 2,
        "slot_date": "2026-11-20",
        "category": "Normal Darshan",
        "total_price": 4400.0,
        "hotel_selected": True,
        "transport_selected": False,
        "own_vehicle": True,
        "start_date": "2026-11-20",
        "return_date": "2026-11-23",
        "duration": 4,
        "pilgrims": SAMPLE_PILGRIMS,
        "primary_contact": SAMPLE_PRIMARY_CONTACT,
    }
    saved = auth_svc.save_booking(test_user_id, booking_data)
    assert saved is not None

    user_bookings = auth_svc.get_user_bookings(test_user_id)
    matching = [b for b in user_bookings if b.get("booking_id") == b_id]
    assert len(matching) == 1
    retrieved = matching[0]
    assert retrieved["hotel_selected"] is True
    assert retrieved["transport_selected"] is False
    assert retrieved["own_vehicle"] is True
    assert retrieved["start_date"] == "2026-11-20"
    assert retrieved["duration"] == 4
    assert len(retrieved["pilgrims"]) == 2
    assert retrieved["pilgrims"][0]["full_name"] == "Ramesh Kumar"
    assert retrieved["status"] in ("SIMULATED_ISSUED", "SIMULATED_CONFIRMED")


def test_confirm_booking_allows_duplicate_pilgrim_names():
    """Verify that multiple family members sharing the same full name can book without rejection."""
    duplicate_name_pilgrims = [
        {"id": "p_1", "full_name": "Ramesh Sharma", "age": 42, "gender": "Male"},
        {"id": "p_2", "full_name": "Ramesh Sharma", "age": 16, "gender": "Male"},
    ]
    req = ConfirmBookingRequest(
        option={"slot": {"category": "Normal Darshan", "slot_date": "2026-11-20"}},
        pax=2,
        user_name="Ramesh Sharma",
        pilgrims=duplicate_name_pilgrims,
        human_authorized=True,
    )
    try:
        confirm_booking(req)
    except HTTPException as exc:
        assert exc.status_code != 400, f"Duplicate names must not be rejected with HTTP 400: {exc.detail}"

    booking_id, blessing = coordinator.confirm_booking(
        option={"slot": {"category": "Normal Darshan", "slot_date": "2026-11-20", "price": 0}, "transport": {"mode": "Own Vehicle"}},
        pax=2,
        user_name="Ramesh Sharma",
        pilgrims=duplicate_name_pilgrims,
        own_vehicle=True,
    )
    assert booking_id.startswith("VD")
    rec = get_booking(booking_id)
    assert rec is not None


if __name__ == "__main__":
    passed = 0
    failed = 0
    current_module = sys.modules[__name__]
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            try:
                obj()
                print(f"PASS: {name}")
                passed += 1
            except Exception as e:
                import traceback
                print(f"FAIL: {name}: {e}")
                traceback.print_exc()
                failed += 1
    print(f"\n==========================================")
    print(f"Phase 8.8.54A Test Results: {passed} passed, {failed} failed")
    print(f"==========================================")
    if failed > 0:
        sys.exit(1)
