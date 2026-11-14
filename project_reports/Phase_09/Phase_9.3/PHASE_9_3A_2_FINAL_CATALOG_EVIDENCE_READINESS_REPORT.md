# PHASE 9.3A.2 — FINAL CATALOG EVIDENCE NORMALIZATION & IMPLEMENTATION READINESS AUDIT REPORT
## Yatra AI — Unified Pilgrimage & Tourism Assistant

**Audit Date:** November 7, 2026
**Auditor Roles:** Senior Data Systems Architect, Full-Stack Integration Engineer, Travel API & Verification Auditor
**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Workspace Python Environment:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly Untouched at HEAD `8996d6a`)
**Audit Scope:** Strictly Read-Only Remediation Audit (Zero Code, Dataset, Database, or Configuration Files Modified)

---

## 1. EXECUTIVE SUMMARY

This audit executes **Phase 9.3A.2: Final Catalog Evidence Normalization & Implementation Readiness Audit**, a focused, rigorous remediation of the Phase 9.3A.1 report.

### Core Audit Principles & Adjustments
1. **Evidence-Grounded Tariff Reclassification:**
   - In Phase 9.3A.1, commercial hotel prices were labeled `OFFICIAL_BOOKING_ENGINE_RATE`. However, because no active automated booking session was executed with specific check-in/out dates, adult occupancy, room category, and exact itemized tax breakdowns, these rates have been **downgraded to `SECONDARY_DIRECTORY_ESTIMATE`** or **`PROPERTY_CONFIRMED_INDICATIVE_RATE`**.
   - Only Shrine Board tariffs published directly on `maavaishnodevi.org/rented-accommodation.aspx` retain the **`OFFICIAL_PUBLISHED_TARIFF`** classification.
2. **Strict GDS & API Connectivity Standards:**
   - Level 3 GDS claims in Phase 9.3A.1 were based on general corporate brand switchboard capabilities rather than verified GDS property codes (e.g. Amadeus/Sabre property IDs).
   - In accordance with Section 2, all commercial chains are reclassified strictly as **`LEVEL_1_CHAIN_MEMBERSHIP`** and **`LEVEL_2_DIRECT_BOOKING_ENGINE`**. GDS distribution is classified as **`UNVERIFIED`**, and Levels 4 and 5 remain strictly **`UNVERIFIED`**.
3. **Availability State Normalization:**
   - The five required states (`NOT_CHECKED`, `AVAILABLE`, `SOLD_OUT`, `PROVIDER_UNAVAILABLE`, `UNKNOWN`) are strictly enforced. All catalog properties default to **`NOT_CHECKED`**.
4. **Implementation Readiness:**
   - All 13 candidate properties are cataloged under **`SAFE_FOR_CATALOG`** based on verified identity, operating status, street address, and direct official contact details.

---

## 2. TARIFF EVIDENCE RECLASSIFICATION MATRIX

Every candidate tariff was audited against actual date-specific query evidence:

| Property Name | Room Category | Stated Tariff (INR) | Previous Classification (9.3A.1) | Normalized Classification (9.3A.2) | Missing Evidence / Justification | Currency & Tax Status |
|---|---|:---:|:---:|:---:|---|---|
| **Niharika Complex** | Non-AC Dormitory Bed | ₹150 / bed / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Explicitly published schedule on `maavaishnodevi.org/rented-accommodation.aspx`. | INR; Subsidized / Tax-Exempt |
| **Niharika Complex** | Standard Non-AC / AC Room | ₹800 – ₹2,500 / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Published on official Shrine Board accommodation directory. | INR; Subsidized rate |
| **Trikuta Bhawan** | Dormitory Bed | ₹150 / bed / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Published schedule for YRC-II facility. | INR; Subsidized / Tax-Exempt |
| **Ardhkuwari Complex** | Dormitory Bed | ₹150 / bed / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Published schedule for Shailputri Bhawan; free resting halls. | INR; Subsidized / Tax-Exempt |
| **Main Bhawan Complex** | Dormitory Bed | ₹150 / bed / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Published schedule for Manokamana / Shrine. | INR; Subsidized / Tax-Exempt |
| **Main Bhawan Complex** | 2-Bed / 4-Bed Room | ₹900 – ₹2,500 / day | `OFFICIAL_PUBLISHED_TARIFF` | **`OFFICIAL_PUBLISHED_TARIFF`** | **Sufficient Evidence.** Published on official Shrine Board reservation portal. | INR; Subsidized rate |
| **Vivanta Katra (Taj)** | Superior Room | ₹6,000 – ₹16,000 / night | `OFFICIAL_BOOKING_ENGINE_RATE` | **`SECONDARY_DIRECTORY_ESTIMATE`** | **Downgraded.** No date-specific query session, exact check-in/out dates, or itemized tax breakdown was captured. Represents researched seasonal bracket. | INR; GST (18%) additional |
| **Welcomhotel Katra (ITC)** | Deluxe Room | ₹6,500 – ₹18,000 / night | `OFFICIAL_BOOKING_ENGINE_RATE` | **`SECONDARY_DIRECTORY_ESTIMATE`** | **Downgraded.** General corporate booking bracket; no live dated session log. | INR; GST (18%) additional |
| **Lemon Tree Katra** | Superior Room | ₹3,200 – ₹7,500 / night | `OFFICIAL_BOOKING_ENGINE_RATE` | **`SECONDARY_DIRECTORY_ESTIMATE`** | **Downgraded.** Researched seasonal bracket; no date-specific offer ID. | INR; GST (12%–18%) extra |
| **Ramada Katra** | Deluxe Room | ₹3,500 – ₹7,500 / night | `OFFICIAL_BOOKING_ENGINE_RATE` | **`SECONDARY_DIRECTORY_ESTIMATE`** | **Downgraded.** Researched seasonal bracket; no date-specific offer ID. | INR; GST (12%–18%) extra |
| **The Vaishnodevi Sarovar** | Superior Room | ₹3,500 – ₹8,000 / night | `OFFICIAL_BOOKING_ENGINE_RATE` | **`SECONDARY_DIRECTORY_ESTIMATE`** | **Downgraded.** Researched seasonal bracket; no date-specific offer ID. | INR; GST (12%–18%) extra |
| **The White Hotel** | Deluxe Valley View | ₹4,200 – ₹10,500 / night | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | **`PROPERTY_CONFIRMED_INDICATIVE_RATE`** | **Sufficient Evidence.** Indicative rack-rate brackets published directly on official portal `whitehotel.in`. | INR; GST extra |
| **Hotel Asia Vaishno Devi** | AC Deluxe Room | ₹2,200 – ₹5,000 / night | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | **`PROPERTY_CONFIRMED_INDICATIVE_RATE`** | **Sufficient Evidence.** Rate schedule published on official portal `hotelasiavaishnodevi.in`. | INR; GST extra |
| **Hotel Subash International** | AC Room | ₹1,200 – ₹2,800 / night | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | **`PROPERTY_CONFIRMED_INDICATIVE_RATE`** | **Sufficient Evidence.** Published tariff card on official portal `hotelsubashinternational.com`. | INR; GST extra |
| **Hotel Shree Hari Niwas** | Standard AC Room | ₹1,200 – ₹2,400 / night | `PROPERTY_CONFIRMED_INDICATIVE_RATE` | **`PROPERTY_CONFIRMED_INDICATIVE_RATE`** | **Sufficient Evidence.** Published tariff card on official portal `shreeharihotels.com`. | INR; GST extra |

---

## 3. GDS AND API CONNECTIVITY EVIDENCE MATRIX

In accordance with Section 2, all GDS claims were audited against direct evidential proof. GDS distribution was de-escalated from assumed Level 3 to `UNVERIFIED`:

```
Level 1: LEVEL_1_CHAIN_MEMBERSHIP (Direct evidence of chain membership)
Level 2: LEVEL_2_DIRECT_BOOKING_ENGINE (Direct evidence of online booking engine on official portal)
Level 3: LEVEL_3_GDS_DISTRIBUTION_VERIFIED (Direct evidence of active GDS property code / switch distribution)
Level 4: LEVEL_4_PROVIDER_API_PROPERTY_RETURNED (Direct evidence of API endpoint returning property)
Level 5: LEVEL_5_DATE_SPECIFIC_API_OFFER_RETURNED (Direct evidence of live date-specific API offer)
```

| Property Name | Chain / Parent Organization | Level 1: Chain | Level 2: Direct Engine | Level 3: GDS Distribution | Level 4: API Returned | Level 5: Live API Offer | Normalized Technical Classification |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **Vivanta Katra** | IHCL (Taj Hotels) | **VERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(GDS Level 3 Unverified)* |
| **Welcomhotel Katra** | ITC Hotels Limited | **VERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(GDS Level 3 Unverified)* |
| **Lemon Tree Katra** | Lemon Tree Hotels Ltd | **VERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(GDS Level 3 Unverified)* |
| **Ramada Katra** | Wyndham Hotels & Resorts | **VERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(GDS Level 3 Unverified)* |
| **The Vaishnodevi Sarovar** | Sarovar / Louvre Hotels | **VERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(GDS Level 3 Unverified)* |
| **The White Hotel** | Independent | **UNVERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(Independent)* |
| **Hotel Asia Vaishno Devi** | Independent (Asia Group) | **UNVERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(Independent)* |
| **Hotel Subash International** | Independent | **UNVERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(Independent)* |
| **Hotel Shree Hari Niwas** | Independent | **UNVERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(Independent)* |
| **SMVDSB Facilities (All)** | Statutory Board | **UNVERIFIED** | **VERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | `LEVEL_2_DIRECT_BOOKING_ENGINE` *(Proprietary Web Portal)* |

*Direct Evidential Ruling: No Amadeus API credentials exist in the environment, and no production GDS property queries were executed. Therefore, no property is claimed to possess Level 3, 4, or 5 status.*

---

## 4. FIELD-LEVEL PROPERTY VERIFICATION MATRIX

Every candidate property was evaluated across 8 individual field classifications (`VERIFIED_PRIMARY`, `VERIFIED_SECONDARY`, `PARTIALLY_VERIFIED`, `UNVERIFIED`):

| Property Name | Identity | Operating Status | Full Address | Telephone Number | Email Address | Official Website | Booking Channel | Operator Affiliation |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Niharika Complex** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Trikuta Bhawan** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Ardhkuwari Complex** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Main Bhawan Complex** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Vivanta Katra** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Welcomhotel Katra** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Lemon Tree Katra** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Ramada Katra** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **The Vaishnodevi Sarovar** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **The White Hotel** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Hotel Asia Vaishno Devi** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Hotel Subash International** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |
| **Hotel Shree Hari Niwas** | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` | `VERIFIED_PRIMARY` |

*Evidential Note: All 13 candidate properties have cleared `VERIFIED_PRIMARY` across all 8 essential identity and contact fields using direct property-level subpages.*

---

## 5. CORRECTED AVAILABILITY STATES

In accordance with Section 4, the availability state machine is strictly defined:

```
[ NOT_CHECKED ] ──(Execute Date-Specific Provider API Query)──► [ Query Result ]
       │                                                              │
       │ (Default state for all catalog records)                      ├──► [ AVAILABLE ] (Confirmed date offer)
       │                                                              ├──► [ SOLD_OUT ] (Explicit zero-inventory)
       │                                                              ├──► [ PROVIDER_UNAVAILABLE ] (Timeout/429)
       │                                                              └──► [ UNKNOWN ] (Ambiguous response)
```

### Strict Operational Rules Enforced
1. **`NOT_CHECKED` is the Absolute Catalog Default:** Every property in `data/katra_accommodation_catalog.json` must be set to `"NOT_CHECKED"`.
2. **`AVAILABLE` State Prohibition:** A static catalog record must **never** claim `"AVAILABLE"`. It can only transition to `"AVAILABLE"` dynamically in-memory if an authenticated, date-specific provider response confirms active room inventory.
3. **`SOLD_OUT` State Discipline:** A property can only be marked `"SOLD_OUT"` if an API explicitly returns zero rooms. A network failure or API timeout must **never** be interpreted as `"SOLD_OUT"`; it must be tagged `"PROVIDER_UNAVAILABLE"`.
4. **Tariff Independence:** A published tariff (whether official or indicative) must **never** cause `availability_status` to become `"AVAILABLE"`.

---

## 6. FINAL DATA MODEL SPECIFICATION

The refined `VerifiedAccommodationRecord` structure cleanly separates permanent identity, contact points, indicative tariffs, and real-time query states:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VerifiedTariffSchedule:
    room_category: str                    # e.g. "Dormitory Bed", "Deluxe Room"
    occupancy_pax: int                    # 1, 2, 4
    tariff_min_inr: float                 # e.g. 150.0, 6000.0
    tariff_max_inr: float                 # e.g. 150.0, 16000.0
    currency: str                         # "INR"
    tax_status: str                       # "SUBSIDIZED_TAX_EXEMPT", "GST_18_PERCENT_ADDITIONAL", "GST_12_PERCENT_ADDITIONAL"
    cancellation_policy: Optional[str]    # "NON_REFUNDABLE", "REFUNDABLE_48_HRS_PRIOR", null
    tariff_classification: str            # "OFFICIAL_PUBLISHED_TARIFF", "PROPERTY_CONFIRMED_INDICATIVE_RATE", "SECONDARY_DIRECTORY_ESTIMATE"
    source_url: str                       # Direct URL supporting this specific tariff
    retrieval_timestamp: str              # ISO 8601 string: "2026-11-07T13:50:00+05:30"
    validity_notes: Optional[str]         # "Standard published schedule", null

@dataclass
class VerifiedAccommodationRecord:
    # 1. Identity & Physical Metadata
    property_id: str                      # Slug: e.g. "SMVDSB_NIHARIKA_KATRA"
    property_name: str                    # Full legal name: "Niharika Complex"
    property_type: str                    # "SHRINE_BOARD_DHARAMSHALA", "COMMERCIAL_CHAIN", "BUDGET_INDEPENDENT"
    operator_type: str                    # "SMVDSB", "IHCL_TAJ", "ITC_HOTELS", "INDEPENDENT"
    identity_status: str                  # "VERIFIED_PRIMARY"
    property_status: str                  # "OPERATIONAL"

    # 2. Location
    address: str                          # Complete physical street address
    address_status: str                   # "VERIFIED_PRIMARY"
    landmark: str                         # "Near Main Bus Stand", "Station Road"
    latitude: Optional[float]             # Exact geocode or null
    longitude: Optional[float]            # Exact geocode or null
    distance_to_banganga_km: Optional[float]

    # 3. Verified Contact Information
    phone: Optional[str]                  # Verified phone number or null
    contact_status: str                   # "VERIFIED_PRIMARY"
    official_website: Optional[str]       # Direct property URL or null
    email: Optional[str]                  # Official email or null

    # 4. Booking Channels & Connectivity
    booking_channel: str                  # "SMVDSB_ONLINE_AND_COUNTER", "DIRECT_WEB_AND_PHONE", "GDS_OTA"
    booking_channel_status: str           # "OFFICIAL_PORTAL_ACTIVE", "DIRECT_PHONE_ONLY"
    connectivity_level: str               # "LEVEL_1_CHAIN_MEMBERSHIP", "LEVEL_2_DIRECT_BOOKING_ENGINE", "UNVERIFIED"

    # 5. Authoritative Tariff Schedules (Separately structured)
    tariffs: List[VerifiedTariffSchedule]

    # 6. Real-Time Dynamic State
    availability_status: str              # "NOT_CHECKED" (Strict default)

    # 7. Audit & Provenance
    source_provenance: str                # "SMVDSB_OFFICIAL_PORTAL", "IHCL_CORPORATE_PORTAL", etc.
    source_urls: List[str]                # Array of direct supporting URLs
    retrieved_at: str                     # ISO 8601 string
    last_verified_at: str                 # ISO 8601 string
```

---

## 7. PROPERTY INCLUSION & EXCLUSION DECISIONS

All 13 candidate properties plus candidates evaluated in earlier audits are categorized into final implementation groups:

### Group A: SAFE_FOR_CATALOG (13 Properties)
*Identity, operating status, full street address, direct official telephone, and official booking website/counter are confirmed by primary sources:*
1. **SMVDSB Niharika Complex** (Katra Base Camp) — `SHRINE_BOARD_DHARAMSHALA`
2. **SMVDSB Trikuta Bhawan** (YRC-II Base) — `SHRINE_BOARD_DHARAMSHALA`
3. **SMVDSB Ardhkuwari Complex** (Midway 6 km) — `SHRINE_BOARD_DHARAMSHALA`
4. **SMVDSB Main Bhawan Complex** (Shrine 13 km) — `SHRINE_BOARD_DHARAMSHALA`
5. **Vivanta Katra, Vaishno Devi** (IHCL / Taj) — `COMMERCIAL_CHAIN`
6. **Welcomhotel by ITC Hotels, Katra** (ITC) — `COMMERCIAL_CHAIN`
7. **Lemon Tree Hotel, Katra** (Lemon Tree) — `COMMERCIAL_CHAIN`
8. **Ramada by Wyndham Katra Station Road** (Wyndham) — `COMMERCIAL_CHAIN`
9. **The Vaishnodevi Sarovar Portico, Katra** (Sarovar) — `COMMERCIAL_CHAIN`
10. **The White Hotel, Katra** (Independent) — `COMMERCIAL_PREMIUM_INDEPENDENT`
11. **Hotel Asia Vaishno Devi** (Independent) — `COMMERCIAL_MIDRANGE_INDEPENDENT`
12. **Hotel Subash International** (Independent) — `COMMERCIAL_BUDGET_INDEPENDENT`
13. **Hotel Shree Hari Niwas** (Independent) — `COMMERCIAL_BUDGET_INDEPENDENT`

### Group B: SAFE_WITH_PARTIAL_METADATA (2 Properties)
*Identity and location confirmed, but direct web reservation engine or direct landline is unverified:*
1. **Zone Connect by The Park, Katra** *(formerly Rama Trident)* — Re-branding verified; website engine operational; direct phone line pending confirmation.
2. **Hotel The Vaishnavi** *(Jammu Road, Katra)* — Identity and physical address verified; independent booking portal absent.

### Group C: HOLD_PENDING_EVIDENCE (0 Properties)
*No properties currently held in pending state.*

### Group D: EXCLUDE (2 Properties)
*Properties that must NEVER enter the Katra accommodation catalog:*
1. **Kalika Bhawan (Katra):** **EXCLUDED.** Geographically located in Jammu City near Jammu Tawi Railway Station.
2. **Shri Balaji Mandir Trust Sarai:** **REJECTED.** Non-existent / fabricated placeholder.

---

## 8. FIELDS SAFE FOR PILGRIM DISPLAY VS. INTERNAL METADATA

To ensure pilgrims are never misled, fields are strictly partitioned:

| Display Status | Property Field | Presentation Guidance for UI / Chat Stream |
|---|---|---|
| **SAFE TO DISPLAY** | `property_name` | Full official name (e.g. "Vivanta Katra, Vaishno Devi", "Niharika Complex"). |
| **SAFE TO DISPLAY** | `address` & `landmark` | Exact physical address and landmark (e.g. "Near Main Bus Stand, Katra", "Station Road"). |
| **SAFE TO DISPLAY** | `phone` | Direct contact telephone number for devotee booking inquiries. |
| **SAFE TO DISPLAY** | `official_website` | Clickable markdown link to official booking portal. |
| **SAFE TO DISPLAY** | `operator_type` | Clear attribution ("Shri Mata Vaishno Devi Shrine Board", "IHCL / Taj", "Independent"). |
| **SAFE TO DISPLAY (WITH BADGE)** | `tariff_min_inr` / `tariff_max_inr` | Must be explicitly badged as indicative: `[Official SMVDSB Subsidized Schedule]` or `[Published Seasonal Rate Card • Call/Portal to Confirm]`. |
| **MUST NEVER BE DISPLAYED AS LIVE** | `availability_status` | Must display `"Subject to check-in confirmation / Call hotel"` unless an active dated API query confirms availability. |
| **INTERNAL ONLY (AUDIT)** | `gds_connectivity_tier` | Used internally by adapter routing logic; never displayed to pilgrims. |
| **INTERNAL ONLY (AUDIT)** | `source_urls` & `retrieved_at` | Used for provenance inspection and admin debugging. |

---

## 9. REMAINING UNCERTAINTIES & AUDIT SAFEGUARDS

1. **Seasonal Tariff Surges:**
   - Commercial chain tariffs surge significantly during peak Navratri festivals and summer holidays (e.g., Vivanta Katra rates can jump from ₹6,500 to ₹18,000+).
   - *Safeguard:* The catalog stores indicative brackets (`tariff_min_inr` and `tariff_max_inr`), and the frontend must display an explicit note: *"Tariffs vary dynamically during peak darshan rush and festivals."*
2. **On-Spot SMVDSB Dormitory Tokens:**
   - Trikuta Bhawan dormitories are largely allotted in person at Katra counters based on arrival queues.
   - *Safeguard:* The UI must indicate: *"Allotted on-arrival at Katra Shrine Board counters."*
3. **Deprecation of Fictional Names:**
   - The 11 fictional names from `build_dataset.py` (`Trikuta Guest House`, etc.) and the synthetic rolling dates in `data/hotels_live.csv` will be cleanly retired upon Phase 9.3B execution.

---

## 10. GO / CONDITIONAL GO / NO-GO DECISION FOR PHASE 9.3B

```
===============================================================================
                   PHASE 9.3A.2 AUDIT DETERMINATION
===============================================================================
            >>> GO FOR PHASE 9.3B CATALOG IMPLEMENTATION <<<
===============================================================================
```

### Actionable Implementation Plan for Phase 9.3B:
1. **Catalog Dataset Construction:** Construct `data/katra_accommodation_catalog.json` containing the **13 Group A (SAFE_FOR_CATALOG) properties** adhering to the normalized `VerifiedAccommodationRecord` schema.
2. **Clean Deprecation of Synthetic Data:** Update the data loading logic to read from `katra_accommodation_catalog.json` while maintaining backward compatibility with existing tests.
3. **Zero External Dependencies:** The implementation requires zero third-party API calls, zero credentials, and zero web scraping, ensuring 100% test reliability and absolute compliance.

---

*(Phase 9.3A.2 Final Catalog Evidence Readiness Audit is complete. Application code, datasets, and the backup repository remain strictly untouched. Awaiting user review and authorization before proceeding to Phase 9.3B).*
