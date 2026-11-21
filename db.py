"""
db.py
All data access lives here, backed by CSV files instead of a database.

- data/yatra_slots_dataset.csv, data/flights_dataset.csv,
  data/trains_dataset.csv, data/buses_dataset.csv and
  data/users_dataset.csv are the static, checked-in datasets (built
  once by build_dataset.py).
- On first run, these are copied into "live" working CSVs with actual
  calendar dates computed from each row's day_offset. All searching
  and seat-decrementing happen against these live copies.
- data/bookings.csv stores completed (mock) bookings. Bookings are
  transport-mode-generic: a booking stores its transport fields
  (mode, operator/airline, number, route, price) directly on the row
  instead of a foreign key into one specific mode's table, since a
  single booking can now be a flight, train, or bus.

PERSISTENT STORAGE (users + bookings only): Streamlit Cloud's local
filesystem is wiped on every redeploy/sleep-wake, so signups and
bookings would otherwise reset constantly. If airtable_store.py detects
Airtable credentials in Streamlit secrets, users and bookings are
read/written to Airtable instead of the local CSV, so they persist
across restarts. Without that configuration, everything falls back to
local CSV files exactly as before. See README.md -> "Persistent
storage" for setup (the bookings table's columns changed in this
version - see the README's Airtable section for the updated list).

NOTE on auth: passwords are stored as plain SHA-256 hashes with no
per-user salt. That's fine for a local prototype/demo, but it is NOT
production-grade auth.
"""

import hashlib
import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd

import airtable_store

from pathlib import Path

try:
    from config import DATA_DIR
    DATA_DIR = str(DATA_DIR)
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATA_DIR = os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))

YATRA_DATASET = os.path.join(DATA_DIR, "yatra_slots_dataset.csv")
FLIGHTS_DATASET = os.path.join(DATA_DIR, "flights_dataset.csv")
TRAINS_DATASET = os.path.join(DATA_DIR, "trains_dataset.csv")
BUSES_DATASET = os.path.join(DATA_DIR, "buses_dataset.csv")
HOTELS_DATASET = os.path.join(DATA_DIR, "hotels_dataset.csv")
USERS_DATASET = os.path.join(DATA_DIR, "users_dataset.csv")

YATRA_LIVE = os.path.join(DATA_DIR, "yatra_slots_live.csv")
FLIGHTS_LIVE = os.path.join(DATA_DIR, "flights_live.csv")
TRAINS_LIVE = os.path.join(DATA_DIR, "trains_live.csv")
BUSES_LIVE = os.path.join(DATA_DIR, "buses_live.csv")
HOTELS_LIVE = os.path.join(DATA_DIR, "hotels_live.csv")
USERS_LIVE = os.path.join(DATA_DIR, "users_live.csv")
BOOKINGS_FILE = os.path.join(DATA_DIR, "bookings.csv")

BOOKINGS_COLUMNS = [
    "booking_id", "user_name", "pax_count",
    "yatra_slot_id", "category", "slot_date", "slot_time",
    "transport_mode", "transport_no", "transport_operator",
    "origin", "destination", "transport_date", "departure_time",
    "transport_price", "yatra_price",
    "hotel_id", "hotel_name", "hotel_category", "hotel_price_per_night", "hotel_nights", "hotel_total",
    "sightseeing_places",
    "total_price", "status", "created_at",
]
USERS_COLUMNS = ["username", "password_hash", "display_name", "created_at"]


def _build_live(dataset_path, live_path, date_column):
    if not os.path.exists(live_path):
        df = pd.read_csv(dataset_path)
        today = date.today()
        df[date_column] = df["day_offset"].apply(lambda d: (today + timedelta(days=int(d))).isoformat())
        df = df.drop(columns=["day_offset"])
        df.to_csv(live_path, index=False)


def ensure_live_data():
    """Create the mutable 'live' CSVs from the static dataset CSVs on first run."""
    os.makedirs(DATA_DIR, exist_ok=True)

    _build_live(YATRA_DATASET, YATRA_LIVE, "slot_date")
    _build_live(FLIGHTS_DATASET, FLIGHTS_LIVE, "flight_date")
    _build_live(TRAINS_DATASET, TRAINS_LIVE, "travel_date")
    _build_live(BUSES_DATASET, BUSES_LIVE, "travel_date")
    _build_live(HOTELS_DATASET, HOTELS_LIVE, "stay_date")

    if not os.path.exists(USERS_LIVE):
        if os.path.exists(USERS_DATASET):
            df = pd.read_csv(USERS_DATASET)
        else:
            df = pd.DataFrame(columns=USERS_COLUMNS)
        df.to_csv(USERS_LIVE, index=False)

    if not os.path.exists(BOOKINGS_FILE):
        pd.DataFrame(columns=BOOKINGS_COLUMNS).to_csv(BOOKINGS_FILE, index=False)


def search_yatra_slots(start_date, end_date, category=None, min_seats=1):
    ensure_live_data()
    df = pd.read_csv(YATRA_LIVE)
    mask = (df["slot_date"] >= start_date) & (df["slot_date"] <= end_date) & (df["seats_available"] >= min_seats)
    if category:
        mask &= df["category"] == category
    result = df[mask].sort_values(["slot_date", "price"])
    return result.to_dict("records")


def search_flights(origin, start_date, end_date, min_seats=1):
    """Searches curated authentic flight schedules; returns empty list for unsupported origins (fail-closed)."""
    try:
        from services.flight_schedules import search_curated_flight_schedules
        schedules, meta = search_curated_flight_schedules(origin=origin, travel_date=start_date)
        if not schedules:
            return []
        records = []
        for s in schedules:
            records.append({
                "id": s.route_id,
                "mode": "flight",
                "airline": s.airline_name,
                "operator": s.airline_name,
                "flight_no": s.flight_number or s.route_id,
                "transport_no": f"{s.airline_name} {s.flight_number}" if s.flight_number else s.airline_name,
                "origin": s.origin_city,
                "origin_airport_code": s.origin_airport_code,
                "origin_airport_name": s.origin_airport_name,
                "destination": s.destination_city,
                "destination_airport_code": s.destination_airport_code,
                "destination_airport_name": s.destination_airport_name,
                "route_type": s.route_type,
                "layover_airports": s.layover_airports,
                "travel_date": start_date,
                "departure_time": s.departure_time,
                "arrival_time": s.arrival_time,
                "duration_hours": s.duration_hours,
                "estimated_duration_desc": s.estimated_duration_desc,
                "schedule_type": s.schedule_type,
                "indicative_fare_min": s.indicative_fare_min,
                "indicative_fare_max": s.indicative_fare_max,
                "fare_classification": s.fare_classification,
                "fare_disclaimer": s.fare_disclaimer,
                "fare": None,
                "price": None,
                "price_per_pax": None,
                "total_transport_cost": None,
                "seats_available": None,
                "is_live_status": False,
                "notes": s.notes,
                "route_verification": s.route_verification.to_dict() if s.route_verification else None,
                "airline_verification": s.airline_verification.to_dict() if s.airline_verification else None,
                "timetable_verification": s.timetable_verification.to_dict() if s.timetable_verification else None,
                "fare_verification": s.fare_verification.to_dict() if s.fare_verification else None,
            })
        return records
    except Exception as exc:
        logger.warning(f"Error querying curated flight schedules: {exc}")
        return []


def search_trains(origin, start_date, end_date, min_seats=1):
    """Searches curated authentic railway schedules; returns empty list for unsupported origins (fail-closed)."""
    try:
        from services.railway_schedules import search_curated_schedules
        schedules, meta = search_curated_schedules(origin=origin, travel_date=start_date)
        if not schedules:
            return []
        records = []
        for s in schedules:
            classes = getattr(s, 'travel_classes', None) or ['Standard']
            for tc in classes:
                records.append({
                    "id": f"train_{s.train_number}_{tc}",
                    "train_no": s.train_number,
                    "train_name": s.train_name,
                    "operator": "Indian Railways",
                    "transport_no": f"{s.train_number} ({tc})",
                    "mode": "train",
                    "origin": s.origin_station_name,
                    "origin_station_code": s.origin_station_code,
                    "destination": s.destination_station_name,
                    "destination_station_code": s.destination_station_code,
                    "travel_date": start_date,
                    "departure_time": s.departure_time,
                    "arrival_time": s.arrival_time,
                    "travel_class": tc,
                    "price": None,
                    "fare": None,
                    "indicative_fare_min": None,
                    "indicative_fare_max": None,
                    "seats_available": None,
                    "availability_verified": False,
                    "seat_availability": "NOT_CHECKED",
                    "is_live_status": False,
                    "verification_status": s.verification_status,
                    "fare_classification": "UNAVAILABLE",
                    "fare_disclaimer": s.fare_disclaimer,
                    "source_circular_reference": s.source_circular_reference,
                    "route_verification": s.route_verification.to_dict() if hasattr(s.route_verification, "to_dict") else s.route_verification,
                    "operator_verification": s.operator_verification.to_dict() if hasattr(s.operator_verification, "to_dict") else s.operator_verification,
                    "timetable_verification": s.timetable_verification.to_dict() if hasattr(s.timetable_verification, "to_dict") else s.timetable_verification,
                    "fare_verification": s.fare_verification.to_dict() if hasattr(s.fare_verification, "to_dict") else s.fare_verification,
                })
        return records
    except Exception:
        return []


def search_buses(origin, start_date, end_date, min_seats=1):
    """Searches curated authentic bus schedules; returns empty list for unsupported origins (fail-closed)."""
    try:
        from services.bus_schedules import search_curated_bus_schedules
        schedules, meta = search_curated_bus_schedules(origin=origin, travel_date=start_date)
        if not schedules:
            return []
        records = []
        for s in schedules:
            indicative_price = s.indicative_fare_min or 90
            dep_time = s.departure_time
            arr_time = s.arrival_time
            fare_class = s.fare_classification or "STATUTORY_NOTIFIED_PER_KM_SLAB"
            bus_name = f"{s.operator_name} {s.bus_type or s.service_type}".strip()
            records.append({
                "id": s.service_id,
                "mode": "bus",
                "name": bus_name,
                "operator": s.operator_name,
                "operator_type": s.operator_type,
                "bus_type": s.bus_type,
                "transport_no": s.service_id,
                "origin": s.origin_city,
                "destination": s.destination_city,
                "origin_bus_stand": s.origin_bus_stand,
                "destination_bus_stand": s.destination_bus_stand,
                "boarding_points": s.boarding_points,
                "dropping_points": s.dropping_points,
                "travel_date": start_date,
                "departure_time": dep_time,
                "departure_window": s.departure_window,
                "operating_hours": s.operating_hours,
                "arrival_time": arr_time,
                "duration_mins": int((s.duration_hours or 1.5) * 60),
                "duration_hours": s.duration_hours,
                "price": None,
                "fare": None,
                "indicative_fare_min": s.indicative_fare_min,
                "indicative_fare_max": s.indicative_fare_max,
                "fare_classification": fare_class,
                "fare_disclaimer": s.fare_disclaimer,
                "seats_available": 40,
                "status": "ROUTE GUIDANCE",
                "is_live_status": False,
                "verification_status": s.verification_status,
                "route_verification": s.route_verification.to_dict() if s.route_verification else None,
                "operator_verification": s.operator_verification.to_dict() if s.operator_verification else None,
                "timetable_verification": s.timetable_verification.to_dict() if s.timetable_verification else None,
                "fare_verification": s.fare_verification.to_dict() if s.fare_verification else None,
                "source_name": s.source_name,
                "source_circular_reference": s.source_circular_reference,
                "booking_url": s.booking_url,
                "availability_status": s.availability_status,
                "availability_source": s.availability_source,
                "journey_type": s.journey_type,
                "connecting_details": s.connecting_details,
            })
        return records
    except Exception:
        return []


def search_hotels(check_in_date, category=None, min_rooms=1):
    """Searches hotels available on a given check-in date (bookings are
    modeled as a single stay-date snapshot per property - the same
    property/price row is reused across the length of stay, since real
    per-night rate variation data isn't available; see README)."""
    ensure_live_data()
    df = pd.read_csv(HOTELS_LIVE)
    mask = (df["stay_date"] == check_in_date) & (df["rooms_available"] >= min_rooms)
    if category:
        mask &= df["category"] == category
    result = df[mask].sort_values(["price_per_night"])
    return result.to_dict("records")


def get_distinct_origins():
    """All cities served by at least one transport mode without synthetic CSV leakage."""
    ensure_live_data()
    origins = set()
    for path in (FLIGHTS_LIVE, TRAINS_LIVE):
        origins |= set(pd.read_csv(path)["origin"].unique().tolist())
    try:
        from services.bus_schedules import load_curated_bus_schedules
        schedules, _ = load_curated_bus_schedules()
        for s in schedules:
            if s.origin_city:
                origins.add(s.origin_city)
    except Exception:
        origins.update(["Jammu", "Udhampur", "Delhi"])
    return sorted(origins)


def _load_bookings_df():
    if airtable_store.is_configured():
        return airtable_store.read_df("bookings", BOOKINGS_COLUMNS)
    ensure_live_data()
    return pd.read_csv(BOOKINGS_FILE)


def create_booking(user_name, pax_count, yatra_slot, transport, total_price, hotel=None, hotel_nights=0,
                    sightseeing_places=None):
    """
    yatra_slot: dict from search_yatra_slots (has id, category, slot_date, slot_time, price)
    transport: dict from search_flights/search_trains/search_buses (has mode,
               transport_no, operator, origin, destination, travel_date,
               departure_time, price, seats_available)
    hotel: optional dict from search_hotels (has id, name, category,
           price_per_night, rooms_available). One room is booked
           regardless of pax_count (simplification - see README).
    hotel_nights: number of nights, used only for the total_price already
                  computed by the caller and for display in the booking.
    sightseeing_places: optional list of place names (from
               explore_data.get_places()) the pilgrim plans to visit
               after darshan. Informational only - not bookable/priced,
               same as the rest of the Explore Katra content - so it
               doesn't affect total_price. Stored as a single
               semicolon-joined string for simple CSV/Airtable storage.
    """
    ensure_live_data()
    booking_id = "VD" + uuid.uuid4().hex[:8].upper()

    if yatra_slot and yatra_slot.get("id"):
        slots = pd.read_csv(YATRA_LIVE)
        idx = slots.index[slots["id"] == yatra_slot["id"]]
        if len(idx) and slots.loc[idx[0], "seats_available"] >= pax_count:
            slots.loc[idx[0], "seats_available"] -= pax_count
            slots.to_csv(YATRA_LIVE, index=False)

    live_map = {"flight": FLIGHTS_LIVE, "train": TRAINS_LIVE, "bus": BUSES_LIVE}
    live_path = live_map.get(transport.get("mode"))
    if live_path and transport.get("id"):
        tdf = pd.read_csv(live_path)
        idx = tdf.index[tdf["id"] == transport["id"]]
        if len(idx) and tdf.loc[idx[0], "seats_available"] >= pax_count:
            tdf.loc[idx[0], "seats_available"] -= pax_count
            tdf.to_csv(live_path, index=False)

    if hotel and hotel.get("id"):
        hdf = pd.read_csv(HOTELS_LIVE)
        idx = hdf.index[hdf["id"] == hotel["id"]]
        if len(idx) and hdf.loc[idx[0], "rooms_available"] >= 1:
            hdf.loc[idx[0], "rooms_available"] -= 1
            hdf.to_csv(HOTELS_LIVE, index=False)

    new_row = {
        "booking_id": booking_id,
        "user_name": user_name,
        "pax_count": pax_count,
        "yatra_slot_id": yatra_slot.get("id") if yatra_slot else None,
        "category": yatra_slot.get("category") if yatra_slot else None,
        "slot_date": yatra_slot.get("slot_date") if yatra_slot else None,
        "slot_time": yatra_slot.get("slot_time") if yatra_slot else None,
        "transport_mode": transport.get("mode"),
        "transport_no": transport.get("transport_no"),
        "transport_operator": transport.get("operator"),
        "origin": transport.get("origin"),
        "destination": transport.get("destination"),
        "transport_date": transport.get("travel_date"),
        "departure_time": transport.get("departure_time"),
        "transport_price": transport.get("price"),
        "yatra_price": yatra_slot.get("price") if yatra_slot else None,
        "hotel_id": hotel.get("id") if hotel else None,
        "hotel_name": hotel.get("name") if hotel else None,
        "hotel_category": hotel.get("category") if hotel else None,
        "hotel_price_per_night": hotel.get("price_per_night") if hotel else None,
        "hotel_nights": hotel_nights if hotel else None,
        "hotel_total": (hotel.get("price_per_night", 0) * hotel_nights) if hotel else None,
        "sightseeing_places": "; ".join(sightseeing_places) if sightseeing_places else None,
        "total_price": total_price,
        "status": "CONFIRMED",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    if airtable_store.is_configured():
        airtable_store.append_row("bookings", BOOKINGS_COLUMNS, new_row)
    else:
        bookings = pd.read_csv(BOOKINGS_FILE)
        new_row_df = pd.DataFrame([new_row])
        valid_cols = [c for c in new_row_df.columns if not new_row_df[c].isna().all()]
        if bookings.empty or bookings.dropna(how="all").empty:
            bookings = new_row_df
        else:
            non_na_bookings = bookings.dropna(axis=1, how="all")
            bookings = pd.concat([non_na_bookings, new_row_df[valid_cols]], ignore_index=True)
        bookings = bookings.reindex(columns=BOOKINGS_COLUMNS)
        bookings.to_csv(BOOKINGS_FILE, index=False)

    return booking_id


def get_booking(booking_id):
    ensure_live_data()
    bookings = _load_bookings_df()
    row = bookings[bookings["booking_id"] == booking_id]
    if row.empty:
        return None
    d = row.iloc[0].to_dict()
    return {k: (None if pd.isna(v) else v) for k, v in d.items()}


def list_bookings(user_name=None):
    ensure_live_data()
    bookings = _load_bookings_df()
    if bookings.empty:
        return []
    if user_name:
        bookings = bookings[bookings["user_name"] == user_name]
        if bookings.empty:
            return []
    return bookings.sort_values("created_at", ascending=False).to_dict("records")


# ---------------------------------------------------------------------
# User accounts (demo auth for the login page)
# ---------------------------------------------------------------------

def _hash_pw(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_users_df():
    if airtable_store.is_configured():
        df = airtable_store.read_df("users", USERS_COLUMNS)
        if os.path.exists(USERS_DATASET):
            seed = pd.read_csv(USERS_DATASET)
            df = pd.concat([seed, df], ignore_index=True).drop_duplicates("username", keep="last")
        return df
    ensure_live_data()
    return pd.read_csv(USERS_LIVE)


def create_user(username, password, display_name):
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password are required."

    users = _load_users_df()
    if (users["username"] == username).any():
        return False, "That username is already taken."

    new_row = {
        "username": username,
        "password_hash": _hash_pw(password),
        "display_name": display_name.strip() or username,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    if airtable_store.is_configured():
        airtable_store.append_row("users", USERS_COLUMNS, new_row)
    else:
        ensure_live_data()
        users = pd.read_csv(USERS_LIVE)
        users = pd.concat([users, pd.DataFrame([new_row])], ignore_index=True)
        users.to_csv(USERS_LIVE, index=False)

    return True, None


def verify_user(username, password):
    username = username.strip().lower()
    users = _load_users_df()
    match = users[users["username"] == username]
    if match.empty:
        return None
    if str(match.iloc[0]["password_hash"]) == _hash_pw(password):
        return match.iloc[0]["display_name"]
    return None
