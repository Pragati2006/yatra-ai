# Phase 9.3B: Verified Katra Accommodation Catalog Implementation Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly Untouched)
**Python Runtime:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Date:** November 7, 2026
**Status:** **COMPLETED & VERIFIED (18/18 Tests Passing, 100% Regression Integrity)**

---

## 1. Executive Summary

Phase 9.3B replaces the legacy synthetic hotel dataset (`hotels_dataset.csv`, containing randomized prices and fictional property names like "Hotel Jai Mata Di" and "Katra Grand") with an authentic, source-attributed, provider-independent **Katra Accommodation Catalog**.

Following the claim-level evidence validations established in **Phase 9.3A.1** and **Phase 9.3A.2**, the catalog incorporates:
- **13 Group A Verified Primary Properties:** Including 4 authentic Shri Mata Vaishno Devi Shrine Board (SMVDSB) pilgrim complexes (Niharika Complex, Trikuta Bhawan, Ardhkuwari Complex, Main Bhawan Complex), 5 corporate branded chain properties (Vivanta Katra, Welcomhotel Katra, Lemon Tree Katra, Ramada by Wyndham Katra, The Vaishnodevi Sarovar Portico), and 4 verified independent Katra hotels (The White Hotel, Hotel Asia Vaishno Devi, Hotel Subash International, Hotel Shree Hari Niwas).
- **2 Group B Partially Verified Properties:** Zone Connect by The Park Katra and Hotel The Vaishnavi, retaining explicit partial verification provenance.
- **Strict Exclusions Enforced:** **Kalika Dham** (demonstrated in Phase 9.3A.1 to be situated in Jammu City 48 km south of Katra) and **Shri Balaji Mandir Trust Sarai** (unverifiable entity) are strictly excluded to safeguard pilgrims against geographical routing errors.
- **Honest Availability Default:** Every record strictly defaults to `availability_status = "NOT_CHECKED"`. Static records are prohibited from claiming `AVAILABLE` or fabricating live room counts.
- **Tariff Attribution:** Every rate is labeled with its validated classification (`OFFICIAL_PUBLISHED_TARIFF`, `PROPERTY_CONFIRMED_INDICATIVE_RATE`, or `SECONDARY_DIRECTORY_ESTIMATE`).

All 18 requirements across schema, catalog service, agent orchestration, tool calling, frontend UI, and test suites are fully implemented and passing.

---

## 2. Catalog Dataset Architecture (`data/katra_accommodation_catalog.json`)

The dataset is located at `data/katra_accommodation_catalog.json`.

### 2.1 Schema Definition
Each property conforms to a strict, typed schema:
```json
{
  "property_id": "SMVDSB_NIHARIKA_COMPLEX",
  "property_name": "Niharika Complex (Yatri Niwas, Shakti Bhawan & Ashirwad)",
  "property_type": "SMVDSB_PILGRIM_ACCOMMODATION",
  "operator_type": "SMVDSB",
  "identity_status": "VERIFIED_PRIMARY",
  "property_status": "OPERATIONAL",
  "address": "Shakti Bhawan, Niharika Complex, Near Main Bus Stand, Katra, Reasi District, Jammu and Kashmir - 182301",
  "address_status": "VERIFIED_PRIMARY",
  "landmark": "Near Katra Main Bus Stand",
  "latitude": 32.9912,
  "longitude": 74.9318,
  "distance_to_banganga_km": 1.5,
  "phone": "01991-234053",
  "contact_status": "VERIFIED_PRIMARY",
  "official_website": "https://www.maavaishnodevi.org/rented-accommodation.aspx",
  "email": null,
  "booking_channel": "SMVDSB_OFFICIAL_PORTAL",
  "booking_channel_status": "OFFICIAL_PORTAL_ACTIVE",
  "connectivity_level": "LEVEL_1_DIRECT_PORTAL",
  "availability_status": "NOT_CHECKED",
  "source_provenance": "CATALOG",
  "source_urls": [
    "https://www.maavaishnodevi.org/rented-accommodation.aspx",
    "https://www.maavaishnodevi.org/"
  ],
  "tariffs": [
    {
      "room_category": "Dormitory Bed (Air Cooled)",
      "occupancy_pax": 1,
      "tariff_min_inr": 150.0,
      "tariff_max_inr": 150.0,
      "currency": "INR",
      "tax_status": "TAX_EXEMPT_SUBSIDIZED",
      "cancellation_policy": "Non-refundable for subsidized dormitory beds as per SMVDSB rules",
      "tariff_classification": "OFFICIAL_PUBLISHED_TARIFF",
      "source_url": "https://www.maavaishnodevi.org/rented-accommodation.aspx",
      "retrieval_timestamp": "2026-11-07T13:30:00+05:30",
      "validity_notes": "Official SMVDSB subsidized tariff schedule"
    }
  ]
}
```

### 2.2 Property Inventory Summary (15 Curated Properties)

| Property ID | Property Name | Category / Operator | Min Rate (INR) | Max Rate (INR) | Tariff Classification | Official Website / Source |
|---|---|---|---|---|---|---|
| `SMVDSB_NIHARIKA_COMPLEX` | Niharika Complex (Yatri Niwas, Shakti Bhawan & Ashirwad) | SMVDSB | ₹150 | ₹1,500 | `OFFICIAL_PUBLISHED_TARIFF` | [maavaishnodevi.org](https://www.maavaishnodevi.org/rented-accommodation.aspx) |
| `SMVDSB_TRIKUTA_BHAWAN` | Trikuta Bhawan | SMVDSB | ₹150 | ₹150 | `OFFICIAL_PUBLISHED_TARIFF` | [maavaishnodevi.org](https://www.maavaishnodevi.org/rented-accommodation.aspx) |
| `SMVDSB_ARDHKUWARI_COMPLEX` | Ardhkuwari Complex (Shailputri Bhawan & Rest Halls) | SMVDSB | ₹150 | ₹1,200 | `OFFICIAL_PUBLISHED_TARIFF` | [maavaishnodevi.org](https://www.maavaishnodevi.org/rented-accommodation.aspx) |
| `SMVDSB_MAIN_BHAWAN_COMPLEX` | Main Bhawan Complex (Manokamana, Vaishnavi & Gauri Bhawans) | SMVDSB | ₹150 | ₹2,100 | `OFFICIAL_PUBLISHED_TARIFF` | [maavaishnodevi.org](https://www.maavaishnodevi.org/rented-accommodation.aspx) |
| `HTL_VIVANTA_KATRA` | Vivanta Katra, Vaishno Devi | Chain / Luxury (IHCL) | ₹6,000 | ₹15,000 | `SECONDARY_DIRECTORY_ESTIMATE` | [vivantahotels.com](https://www.vivantahotels.com/en-in/hotels/vivanta-katra/) |
| `HTL_WELCOMHOTEL_KATRA` | Welcomhotel by ITC Hotels, Katra | Chain / Luxury (ITC) | ₹6,500 | ₹16,000 | `SECONDARY_DIRECTORY_ESTIMATE` | [itchotels.com](https://www.itchotels.com/in/en/welcomhotelkatra) |
| `HTL_LEMON_TREE_KATRA` | Lemon Tree Hotel, Katra | Chain / Upper Midscale | ₹3,200 | ₹7,500 | `SECONDARY_DIRECTORY_ESTIMATE` | [lemontreehotels.com](https://www.lemontreehotels.com/lemon-tree-hotel/katra/hotel-katra.aspx) |
| `HTL_RAMADA_WYNDHAM_KATRA` | Ramada by Wyndham Katra Station Road | Chain / Midscale (Wyndham) | ₹3,500 | ₹8,000 | `SECONDARY_DIRECTORY_ESTIMATE` | [wyndhamhotels.com](https://www.wyndhamhotels.com/ramada/katra-india/ramada-katra-station-road/overview) |
| `HTL_SAROVAR_PORTICO_KATRA` | The Vaishnodevi Sarovar Portico, Katra | Chain / Midscale (Sarovar) | ₹3,500 | ₹7,000 | `SECONDARY_DIRECTORY_ESTIMATE` | [sarovarhotels.com](https://www.sarovarhotels.com/the-vaishnodevi-sarovar-portico-katra/) |
| `HTL_WHITE_HOTEL_KATRA` | The White Hotel, Katra | Independent / Upscale | ₹4,200 | ₹9,500 | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | [thewhitehotelkatra.com](https://www.thewhitehotelkatra.com/) |
| `HTL_ASIA_VAISHNODEVI_KATRA` | Hotel Asia Vaishno Devi | Independent / Mid-Range | ₹2,200 | ₹4,500 | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | [hotelasiavaishnodevi.com](https://www.hotelasiavaishnodevi.com/) |
| `HTL_SUBASH_INTERNATIONAL_KATRA` | Hotel Subash International | Independent / Budget | ₹1,200 | ₹2,800 | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | [subashhotels.com](http://www.subashhotels.com/) |
| `HTL_SHREE_HARI_NIWAS_KATRA` | Hotel Shree Hari Niwas | Independent / Budget | ₹1,200 | ₹2,600 | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | [shreehariniwas.com](http://www.shreehariniwas.com/) |
| `HTL_ZONE_CONNECT_KATRA` (Group B) | Zone Connect by The Park, Katra | Chain / Midscale | ₹2,800 | ₹6,000 | `SECONDARY_DIRECTORY_ESTIMATE` | [zonebythepark.com](https://www.zonebythepark.com/) |
| `HTL_VAISHNAVI_BUDGET_KATRA` (Group B) | Hotel The Vaishnavi | Independent / Economy | ₹1,000 | ₹2,200 | `SECONDARY_DIRECTORY_ESTIMATE` | [hotelthevaishnavi.in](https://hotelthevaishnavi.in/) |

---

## 3. Provider-Independent Catalog Service (`services/accommodation_catalog.py`)

The module `services/accommodation_catalog.py` serves as the decoupled abstraction layer for accommodation data.

### 3.1 Key Classes & Functions
- **`TariffSchedule` & `KatraProperty` Dataclasses:** Formalize the property record structure and guarantee field typing.
- **`load_catalog(force_reload=False)`:** Loads and caches `katra_accommodation_catalog.json` in memory. Strictly forces loaded `availability_status` to `"NOT_CHECKED"`.
- **`get_property_by_id(property_id)`:** Retrieves a single property by its identifier slug.
- **`get_all_properties(include_partial=True)`:** Returns all properties, optionally excluding Group B entries.
- **`search_properties(query, category, min_budget, max_budget, landmark, operator_type)`:** High-performance in-memory filtering engine supporting:
  - Multi-token keyword search (name, landmark, address, operator).
  - Categorization rules: `SMVDSB` (dharamshala/board), `Budget` (< ₹2,500 or SMVDSB), `Mid-Range` (₹2,000–₹5,500), `Premium` (≥ ₹5,000).
  - Budget filtering with min/max caps.
  - Automatic ordering prioritizing authentic SMVDSB facilities first, followed by ascending indicative minimum tariffs.
- **`to_legacy_record()` & `search_hotels_for_orchestrator()`:** Backward-compatibility adapters converting verified properties into dictionaries conformant with existing orchestrator, budget engine, and frontend contracts:
  - `price_per_night`: Indicative minimum rate.
  - `rooms_available`: Strictly `None` (preventing synthetic room countdowns).
  - `availability_status`: Strictly `"NOT_CHECKED"`.
  - `tariff_disclaimer`: Authentic badge text.

---

## 4. System-Wide Integration Details

### 4.1 Backend Route Integration (`backend/routes/yatra.py`)
In `backend/routes/yatra.py`, `@router.post("/accommodation")` was updated to support authentic catalog records where `rooms_available` is `None`:
```python
    # Filter by minimum rooms if specified, accepting verified catalog properties
    # where rooms_available is None (indicating live availability NOT_CHECKED)
    hotels = [
        hotel
        for hotel in hotels
        if hotel.get("rooms_available") is None or hotel.get("rooms_available", 0) >= request.min_rooms
    ]
```
This ensures verified properties with `rooms_available=None` are returned with full metadata rather than being accidentally filtered out.

### 4.2 Coordinator Integration (`agents/coordinator.py`)
In `agents/coordinator.py`, `get_hotel_options` was updated to query `search_hotels_for_orchestrator`, falling back to `db.search_hotels` only if catalog retrieval fails:
```python
def get_hotel_options(check_in_date, category=None):
    """HotelAgent duty - retrieves verified Katra accommodation catalog properties.
    Falls back to db.search_hotels if catalog retrieval fails."""
    try:
        from services.accommodation_catalog import search_hotels_for_orchestrator
        hotels = search_hotels_for_orchestrator(check_in_date=check_in_date, category=category)
        if hotels:
            return hotels
    except Exception as e:
        logger.warning(f"Error querying verified Katra accommodation catalog: {e}. Falling back to db.search_hotels.")
    return db.search_hotels(check_in_date, category=category)
```

### 4.3 Orchestrator Integration (`agents/orchestrator.py`)
In `agents/orchestrator.py`, lines 596–601 in `coordinate_plan()` were updated to query `search_hotels_for_orchestrator`:
```python
    # 5. Accommodation Search
    rooms_needed = budget_engine.calculate_rooms_required(pax)
    hotel_nights = max(1, duration - 1)
    try:
        from services.accommodation_catalog import search_hotels_for_orchestrator
        hotels = search_hotels_for_orchestrator(start_date, category=hotel_pref, min_rooms=rooms_needed)
        if not hotels and hotel_pref:
            hotels = search_hotels_for_orchestrator(start_date, category=None, min_rooms=rooms_needed)
    except Exception as e:
        logger.warning(f"Error querying verified Katra accommodation catalog in orchestrator: {e}. Falling back to db.search_hotels.")
        hotels = db.search_hotels(start_date, category=hotel_pref, min_rooms=rooms_needed)
        if not hotels and hotel_pref:
            # Fall back to any category on that stay date
            hotels = db.search_hotels(start_date, category=None, min_rooms=rooms_needed)

    selected_hotel = hotels[0] if hotels else None
```

### 4.4 Central Agent Tool Calling Integration (`agents/central_agent.py`)
In `agents/central_agent.py`:
1. **Tool Definition:** Added `@tool def search_accommodation_options(...)` exposing keyword, category, min/max budget, landmark, and operator filters.
2. **Registry:** Added `search_accommodation_options` to `CENTRAL_TOOLS` and `CENTRAL_TOOL_MAP`.
3. **Prompt Grounding:** Updated `CENTRAL_AGENT_SYSTEM_PROMPT` to document capability #10 with strict instructions on availability defaults.

### 4.5 Frontend User Experience (`frontend/src/components/chat/cards/HotelMiniCard.jsx` & `HotelCard.jsx`)
In `HotelMiniCard.jsx` and `HotelCard.jsx`:
- **Removed Fabricated Ratings:** Eliminated all hardcoded devotee ratings (e.g. `⭐ 4.5/5`).
- **Removed False Room Counters:** If `rooms_available` is `None`, renders honest status `Live Availability: Not Checked • Contact Property Directly` instead of inventing room counts.
- **Rendered Authentic Contacts:** Direct click-to-call links (`tel:{phone}`) and official website links (`href={official_website}`).
- **Provenance Badging:** Integrated with `FreshnessIndicator` (`customText="Curated Catalog"`), displaying `Official SMVDSB Subsidized Tariff Schedule` or `Published Indicative Tariff`.

---

## 5. Verification & Test Suite Results

The dedicated test suite `tests/test_phase9_3b_catalog.py` was executed with the designated Python 3.12 workspace interpreter.

### 5.1 Requirement Test Results Matrix (18/18 Passing)

| Test Method | Requirement Description | Verification Scope | Status | Execution Time |
|---|---|---|---|---|
| `test_01_catalog_loading_from_disk` | Catalog Loading & Metadata | `data/katra_accommodation_catalog.json` loads 15 properties | **PASS** | 0.002s |
| `test_02_schema_validation` | Typed Schema Completeness | All required property and tariff fields present | **PASS** | 0.003s |
| `test_03_group_a_properties_verified_primary` | Group A Status Verification | 13 properties carry `identity_status == "VERIFIED_PRIMARY"` | **PASS** | 0.002s |
| `test_04_group_b_properties_partially_verified` | Group B Status Verification | 2 properties carry `identity_status == "PARTIALLY_VERIFIED"` | **PASS** | 0.001s |
| `test_05_exclusion_of_ineligible_properties` | Strict Exclusion Compliance | Kalika Dham (Jammu) & Balaji Mandir Trust absent | **PASS** | 0.002s |
| `test_06_null_handling_for_unknown_fields` | Preserved Nulls | No invented dummy coordinates or phone numbers | **PASS** | 0.001s |
| `test_07_tariff_classification_validation` | Tariff Attribution Audit | Tariffs classified according to verified evidence | **PASS** | 0.002s |
| `test_08_availability_status_default_not_checked` | Default Availability Rule | All properties strictly default to `NOT_CHECKED` | **PASS** | 0.001s |
| `test_09_prevention_of_static_available_status` | Prevention of False `AVAILABLE` | Assert no static records claim live confirmation | **PASS** | 0.001s |
| `test_10_prevention_of_false_sold_out_status` | Prevention of False `SOLD_OUT` | Assert no static records claim sold out without check | **PASS** | 0.001s |
| `test_11_source_url_validation` | Provenance Link Integrity | All primary source URLs are valid HTTP/HTTPS links | **PASS** | 0.002s |
| `test_12_search_by_name` | Name & Keyword Search | Exact matches for Niharika, Vivanta, White Hotel | **PASS** | 0.002s |
| `test_13_search_by_category` | Category Filtering | SMVDSB (4), Dharamshala (4), Budget (8), Premium (2) | **PASS** | 0.003s |
| `test_14_budget_filtering` | Price Range Filtering | min_budget and max_budget boundary checks | **PASS** | 0.002s |
| `test_15_landmark_filtering` | Geographical Filtering | Bus Stand, Railway Station, Banganga, Bhawan | **PASS** | 0.002s |
| `test_16_orchestrator_adapter_legacy_compatibility` | Orchestrator Adapter Schema | Legacy dictionary schema conformant, `rooms_available=None` | **PASS** | 0.002s |
| `test_17_production_path_exclusion_of_synthetic_hotels` | Production Path Cleansing | Fictional names absent; authentic SMVDSB & Vivanta present | **PASS** | 0.003s |
| `test_18_central_agent_tool_search_accommodation` | LangChain Tool Calling | `search_accommodation_options` execution via Central Agent | **PASS** | 3.400s |

**Overall Suite Outcome:** `Ran 18 tests in 3.435s — OK (0 failures, 0 errors)`.

---

### 5.2 Regression Test Suite Results

Existing test suites were executed to ensure full backward compatibility:
- **`tests/test_phase8_5_frontend_provenance.py`:** **22/22 Passing** (Ran 22 tests in 4.974s — OK). Verified `HotelMiniCard.jsx` disclaimers and provenance indicators.
- **`tests/test_phase8_4_hybrid_orchestration.py`:** **30/30 Passing** (Ran 30 tests in 3.079s — OK). Verified LLM fallback and coordinator routing.
- **`tests/test_phase8_3_cache.py`:** **40/40 Passing** (Ran 40 tests in 0.376s — OK). Verified SQLite caching, TTL expiration, and session preservation.
- **`tests/test_phase8_2_provenance.py`:** **33/33 Passing** (Ran 33 tests in 0.384s — OK).
- **`tests/test_phase8_1_weather.py`:** **27/27 Passing** (Ran 27 tests in 0.114s — OK).
- **`tests/test_phase7_rag.py`:** **25/25 Passing** (Ran 25 tests in 1.157s — OK).
- **`tests/test_phase6_central_agent.py`:** **20/20 Passing** (Ran 20 tests in 1.923s — OK).
- **`tests/test_budget_engine.py`:** **16/16 Passing** (Ran 16 tests in 0.006s — OK). Verified mathematical accuracy with `rooms_available=None`.
- **`tests/test_orchestrator.py`:** Core unit and conversational planning tests passing (`test_proceed_when_required_info_available`, `test_tool_coordination_and_consolidated_output`, `test_budget_recalculation_after_changes`, `test_existing_api_compatibility`).

---

## 6. Deprecation & Replacement of Synthetic Data in Production

The following table documents the complete transition from synthetic mock data to verified catalog data in production query paths:

| Production Route / Function | Prior Implementation | Phase 9.3B Implementation | Audit Status |
|---|---|---|---|
| `coordinator.get_hotel_options()` | Directly queried `db.search_hotels()` returning `hotels_live.csv` with randomized prices and fictional names ("Hotel Jai Mata Di"). | Calls `services.accommodation_catalog.search_hotels_for_orchestrator()`. Returns authentic 15 Katra properties. | **VERIFIED IN PRODUCTION PATH** |
| `orchestrator.coordinate_plan()` | Selected first hotel from `db.search_hotels()` with fabricated `rooms_available` counter. | Calls `services.accommodation_catalog.search_hotels_for_orchestrator()`. Defaults `rooms_available` to `None`. | **VERIFIED IN PRODUCTION PATH** |
| `backend/routes/yatra.py` (`/accommodation`) | Filtered out properties with `rooms_available < min_rooms` (which would eliminate authentic unpolled catalog properties). | Explicitly supports `rooms_available is None or >= min_rooms`. | **VERIFIED IN PRODUCTION PATH** |
| `agents/central_agent.py` | Lacked an explicit accommodation search tool. | Implemented `@tool search_accommodation_options` with keyword, budget, landmark, and operator filters. | **VERIFIED IN CENTRAL AGENT** |
| `HotelMiniCard.jsx` | Displayed `⭐ 4.5/5 Devotee Rating` and hardcoded `"Near Katra Main Market"`. | Displays real address, landmark, direct telephone link, official website link, and honest `NOT_CHECKED` disclaimer. | **VERIFIED IN FRONTEND** |
| `HotelCard.jsx` | Displayed `5 rooms left` when room count was absent. | Displays `Live Availability: Not Checked` when room count is absent. | **VERIFIED IN FRONTEND** |

---

## 7. Audit Compliance & Next Steps

### 7.1 Safety & Environment Commitments Followed
1. **Backup Repository Untouched:** `git status` confirms `yatra-booking-agent` remains 100% clean and unmodified.
2. **Designated Virtual Environment:** All tests executed with `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe`.
3. **No Unsanctioned Web Scraping:** Zero scraping against external portals or CAPTCHA bypasses; catalog was built purely from verified public filings and official portals.
4. **Honest Data Provenance:** Zero fabrication of real-time availability; every record transparently communicates its `NOT_CHECKED` status.

### 7.2 Recommendations for Phase 9.4 (Live Data Integration Roadmap)
1. **On-Demand SMVDSB Portal Polling:** Implement an authenticated or headless session poller to fetch real-time accommodation slot availability for Niharika and Trikuta Bhawans during active user checkout.
2. **Authorized Commercial GDS Integration:** Transition commercial chain properties (Vivanta, Welcomhotel, Lemon Tree) to live rates once commercial GDS credentials (Amadeus Enterprise or Sabre) are authorized.
3. **Automated Rate Expiry & Refresh:** Implement a periodic background task updating secondary directory estimates every 30 days.
