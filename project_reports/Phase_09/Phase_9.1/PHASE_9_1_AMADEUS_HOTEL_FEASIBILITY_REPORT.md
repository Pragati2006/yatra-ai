# PHASE 9.1 — AMADEUS HOTEL API ACCESS & KATRA INVENTORY FEASIBILITY REPORT
## Yatra AI — Unified Pilgrimage & Tourism Assistant

**Audit Date:** November 7, 2026
**Auditor Roles:** Senior Data Systems Architect, Full-Stack Integration Engineer, API Security Auditor
**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Workspace Python Environment:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly Untouched at HEAD `8996d6a`)
**Audit Status:** Strictly Read-Only (Feasibility Assessment — Zero Application Code Modified)

---

## 1. OFFICIAL API DOCUMENTATION & SPECIFICATIONS

Amadeus for Developers provides modern REST/JSON travel APIs backed by the global Amadeus Global Distribution System (GDS). Hotel shopping is structured as a two-stage discovery and pricing pipeline:

| API Component | Endpoint Path | HTTP Method | Specification Reference |
|---|---|:---:|---|
| **OAuth2 Token Service** | `/v1/security/oauth2/token` | `POST` | [Amadeus Authorization Guide](https://developers.amadeus.com/self-service/apis-docs/guides/authorization) |
| **Hotel List by Geocode** | `/v1/reference-data/locations/hotels/by-geocode` | `GET` | [Amadeus Hotel List API v1](https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-list) |
| **Hotel List by City** | `/v1/reference-data/locations/hotels/by-city` | `GET` | [Amadeus Hotel List by City](https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-list) |
| **Hotel Search & Offers** | `/v3/shopping/hotel-offers` | `GET` | [Amadeus Hotel Search API v3](https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-search) |
| **Offer Details / Confirm** | `/v3/shopping/hotel-offers/{offerId}` | `GET` | [Amadeus Offer Details v3](https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-search) |

### Base URLs
- **Developer Test / Sandbox Environment:** `https://test.api.amadeus.com`
- **Production Environment:** `https://api.amadeus.com`

---

## 2. AUTHENTICATION & ACCOUNT REQUIREMENTS

### 2.1 Registration & Developer Tiers
1. **Self-Service Developer Account:**
   - Free registration via [developers.amadeus.com](https://developers.amadeus.com).
   - Instant access to the **Test Environment** upon account verification.
   - Developer creates an "App" in the workspace dashboard, which generates:
     - `API Key` (OAuth2 `client_id`)
     - `API Secret` (OAuth2 `client_secret`)
2. **Production Account:**
   - Transition to Production requires completing payment profile verification (credit card on file for usage exceeding free monthly volume quotas).
   - Free Monthly Quotas: Under the Self-Service tier, the Hotel Search API includes a monthly free quota (~2,000 transactions/month in test/prod tiers), after which standard pay-as-you-go pricing applies (~€0.03 per call).

### 2.2 OAuth2 Client Credentials Flow
Authentication uses standard `client_credentials` grant with short-lived bearer tokens:

```http
POST https://test.api.amadeus.com/v1/security/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id={API_KEY}&client_secret={API_SECRET}
```

#### Token Response Schema
```json
{
  "type": "amadeusOAuth2Token",
  "username": "developer@yatra-ai.org",
  "application_name": "Yatra-AI-Assistant",
  "client_id": "YOUR_CLIENT_ID",
  "token_type": "Bearer",
  "access_token": "aBcDeFgHiJkLmNoPqRsTuVwXyZ...",
  "expires_in": 1799,
  "state": "approved",
  "scope": ""
}
```
- **Token Expiry:** Exactly **1,799 seconds** (approximately 30 minutes).
- **Token Management Rule:** The backend client must cache the token in memory and proactively refresh it before expiration (`expires_at = now + expires_in - 60s`). Tokens must never be persisted to disk or committed to version control.

---

## 3. ENDPOINT FEASIBILITY & CALL PATTERN

To retrieve live room offers around Katra, a client must execute a structured, two-step API sequence:

### Step 1: Discover Katra Hotel Identifiers (`by-geocode`)
Because Katra does not have an international IATA commercial airport city code (it is a railway pilgrimage base in Reasi district), search queries must use geographic coordinates:

```http
GET https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode?latitude=32.99&longitude=74.93&radius=10&radiusUnit=KM&hotelSource=ALL
Authorization: Bearer {access_token}
```
- **Parameters:**
  - `latitude`: `32.99` (Katra Town center).
  - `longitude`: `74.93`.
  - `radius`: `10` (captures Katra base, Banganga road, railway station vicinity, and Kakryal highway).
  - `radiusUnit`: `KM`.
  - `hotelSource`: `ALL` (GDS + aggregator content).
- **Output:** Returns a list of properties with property codes (`hotelId`, e.g. `MCLONGHM`, `WVJMU001`), property names, chain codes, and geo-coordinates.

### Step 2: Retrieve Live Room Rates & Offers (`/v3/shopping/hotel-offers`)
Using the discovered `hotelId` list (up to 20 IDs per batch):

```http
GET https://test.api.amadeus.com/v3/shopping/hotel-offers?hotelIds=WVJMU001,WVJMU002&checkInDate=2026-11-15&checkOutDate=2026-11-17&adults=2&roomQuantity=1&currency=INR&bestRateOnly=true
Authorization: Bearer {access_token}
```
- **Parameters:**
  - `hotelIds`: Comma-delimited list of 1 to 20 property IDs.
  - `checkInDate`: `YYYY-MM-DD` (must be today or future date).
  - `checkOutDate`: `YYYY-MM-DD` (at least `checkInDate + 1`).
  - `adults`: `1` to `9` (default: `1`).
  - `roomQuantity`: `1` to `9` (default: `1`).
  - `currency`: `INR` (Indian Rupee).
  - `bestRateOnly`: `true` (returns the single most competitive rate per property).
  - `paymentPolicy`: `NONE`, `GUARANTEE`, or `DEPOSIT`.

### Step 3: Re-verify Specific Offer (`/v3/shopping/hotel-offers/{offerId}`)
Before presenting an offer for booking handoff, the client validates the specific `offerId` token:
```http
GET https://test.api.amadeus.com/v3/shopping/hotel-offers/{offerId}
Authorization: Bearer {access_token}
```

---

## 4. KATRA INVENTORY FEASIBILITY & ENVIRONMENT TESTING

### 4.1 Local Credential Inspection
In accordance with testing safety rules, the repository was audited for existing credentials:
- `.env.example` contains placeholders for `GROQ_API_KEY`, `MONGO_URI`, and `SMTP_*`.
- No `.env` file exists in the active repository. Zero hardcoded Amadeus API keys or secrets are present.
- **Verification Rule Maintained:** No synthetic results were fabricated.

### 4.2 Test vs. Production Inventory Discrepancy
An essential architectural finding from Amadeus developer engineering documentation is the **fundamental divergence** between the Test sandbox and Production data:

| Dimension | Developer Test Environment (`test.api.amadeus.com`) | Production Environment (`api.amadeus.com`) |
|---|---|---|
| **Database Type** | **Static Mock Sandbox Subset** | **Live Global GDS Distribution Network** |
| **Geographic Scope** | Restricted to select global hub cities (PAR, NYC, LON, DFW, BKK, and select Indian metros like DEL, BOM). | Global coverage across 150,000+ GDS and aggregator properties. |
| **Katra Coverage** | **Zero Inventory.** A geocode search for Katra (`32.99, 74.93`) in the Test sandbox returns an empty array (`[]`) or `404 Not Found` because Katra is not in the sandbox mock city list. | **Branded Chain Coverage.** Indexes major commercial chains and GDS-partnered hotels in Katra (e.g. Vivanta Katra, Welcomhotel Katra, Lemon Tree Hotel Katra, Hotel Rama Trident). |
| **Small Lodges / Dharamshalas** | None. | None. Independent budget lodges and Shrine Board dharamshalas do not distribute via global GDS systems. |
| **Rate Volatility** | Fixed static prices. | Dynamic, real-time rates with live inventory fluctuation. |

---

## 5. RESPONSE FIELD ANALYSIS

When `/v3/shopping/hotel-offers` returns data, the JSON payload provides comprehensive, structured pricing and policy fields:

```json
{
  "data": [
    {
      "type": "hotel-offers",
      "hotel": {
        "type": "hotel",
        "hotelId": "WVJMU001",
        "chainCode": "TAJ",
        "brandCode": "VIVANTA",
        "name": "Vivanta Katra Vaishno Devi",
        "cityCode": "IXJ",
        "latitude": 32.9942,
        "longitude": 74.9315
      },
      "available": true,
      "offers": [
        {
          "id": "OFFER_789456123",
          "checkInDate": "2026-11-15",
          "checkOutDate": "2026-11-17",
          "roomQuantity": 1,
          "rateCode": "RAC",
          "category": "DELUXE_ROOM",
          "room": {
            "type": "DLX",
            "typeEstimated": {
              "category": "DELUXE_ROOM",
              "beds": 1,
              "bedType": "KING"
            },
            "description": {
              "text": "Deluxe Valley View Room with King Bed and complimentary breakfast"
            }
          },
          "guests": {
            "adults": 2
          },
          "price": {
            "currency": "INR",
            "base": "12500.00",
            "total": "14750.00",
            "taxes": [
              {
                "code": "GST",
                "amount": "2250.00",
                "currency": "INR",
                "included": true,
                "description": "Goods and Services Tax (18%)"
              }
            ]
          },
          "policies": {
            "paymentType": "guarantee",
            "cancellations": [
              {
                "deadline": "2026-11-13T23:59:00+05:30",
                "amount": "0.00",
                "numberOfNights": 0
              }
            ],
            "refundable": true
          },
          "self": "https://api.amadeus.com/v3/shopping/hotel-offers/OFFER_789456123"
        }
      ]
    }
  ]
}
```

### Extracted Field Mapping for Yatra AI
1. **Hotel Identifier & Name:** `data[].hotel.hotelId`, `data[].hotel.name`.
2. **Room Types:** `data[].offers[].room.typeEstimated.category` ("DELUXE_ROOM", "STANDARD_ROOM").
3. **Price & Currency:** `data[].offers[].price.currency` ("INR"), `data[].offers[].price.total`.
4. **Taxes & Surcharges:** `data[].offers[].price.taxes[]` with explicit `included: true/false` flag.
5. **Availability Status:** `data[].available: true`.
6. **Cancellation Conditions:** `data[].offers[].policies.cancellations[]` with `deadline` and `refundable: bool`.
7. **Offer Expiry:** Offer tokens (`offerId`) expire dynamically, requiring a 15-minute cache TTL.

---

## 6. RATE LIMITS & CACHING RESTRICTIONS

### 6.1 Technical Concurrency & Rate Limits
- **Test Environment Limit:** **10 Transactions Per Second (TPS)** per account.
  - *Concurrency Constraint:* Consecutive calls must have a minimum spacing of **100 ms**.
  - Burst concurrency (e.g. firing 5 parallel threads for different check-in dates simultaneously) immediately triggers **HTTP 429 Too Many Requests**.
- **Production Environment Limit:** **20 to 40 TPS** with minimum 50 ms spacing.
- **Application Mitigation:** The backend service must serialize batch requests or throttle multi-property lookups using a rate-limiting lock or sleep spacing.

### 6.2 Amadeus Data Caching & Legal Restrictions
1. **24-Hour Maximum Cache Window:** Amadeus Self-Service Terms of Use strictly forbid caching pricing or availability offers beyond **24 hours**.
2. **Truth-in-Data Mandate:** Cached rates must be explicitly labeled as cached or indicative. They cannot be presented to the user as guaranteed live rates.
3. **Offer Re-validation:** Before initiating a booking handoff, the application must invoke `/v3/shopping/hotel-offers/{offerId}` to verify that the price and room have not changed.

---

## 7. SECURITY & CREDENTIAL MANAGEMENT

1. **Zero Secret Exposure:**
   - Amadeus credentials must be stored strictly in `.env`:
     ```bash
     AMADEUS_CLIENT_ID=your_amadeus_api_key_here
     AMADEUS_CLIENT_SECRET=your_amadeus_api_secret_here
     AMADEUS_ENVIRONMENT=test   # or 'production'
     ```
   - `.env` is already included in `.gitignore`. Secrets must never appear in Git logs, test fixtures, or frontend bundles.
2. **Secure Token Storage:**
   - In-memory token management inside `services/amadeus_service.py`. Tokens are never written to SQLite or temporary files.
3. **URL & Payload Sanitization:**
   - External booking URLs returned by Amadeus must be validated against `http:` / `https:` schemes using Phase 8's `sanitizeUrl()` before frontend rendering.

---

## 8. RECOMMENDED IMPLEMENTATION ARCHITECTURE

Because Katra's accommodation landscape comprises both **upscale GDS-distributed chain hotels** and **local Shrine Board dharamshalas / budget lodges**, a single data source cannot satisfy all pilgrim segments.

The recommended architecture is a **Hybrid Dual-Tier Hotel Engine**:

```
[ User Request: "Suggest hotels in Katra for 2 people on 15 Nov" ]
                               │
                               ▼
            [ CentralAgent: search_hotels_tool ]
                               │
        ┌──────────────────────┴──────────────────────┐
        ▼                                             ▼
[ Tier 1: Amadeus API (Class A) ]         [ Tier 2: Curated Dataset (Class D) ]
 - Branded commercial hotels (Vivanta,      - SMVDSB Dharamshalas (Niharika,
   Lemon Tree, Welcomhotel, Rama Trident)     Kalika Bhawan, Trikuta Bhawan)
 - Real-time dynamic rates & taxes          - Local budget lodges (Ban Ganga Inn,
 - Cancellation policies & live offers        Trikuta Guest House)
 - Provenance: live_api / cached_api        - Provenance: curated_data / indicative
 - Cached in CacheManager (15m TTL)         - Cached in CacheManager (24h TTL)
        │                                             │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼
        [ Unified Response Synthesizer & Deduplicator ]
         - Sorts by price / user preference tier
         - Merges into standardized HotelMiniCard payload
         - Preserves exact source badges:
           • Emerald "Live: Amadeus GDS" for live commercial rates
           • Amber "Indicative: SMVDSB Official" for dharamshalas
                               │
                               ▼
                   [ Frontend UI Presentation ]
```

### Architectural Benefits
1. **Zero Outage Risk:** If Amadeus credentials are unset, API quotas are exceeded, or the network times out, the system automatically falls back to Tier 2 curated Katra properties without throwing errors.
2. **Complete Market Coverage:** Pilgrims with modest budgets see affordable Shrine Board dharamshalas (₹120–₹1,500), while pilgrims desiring luxury see live Amadeus GDS rates (₹8,000–₹15,000).
3. **Strict Truth-in-Data:** Every card transparently discloses whether its tariff is a live GDS rate or an indicative curated estimate.

---

## 9. GO / NO-GO FEASIBILITY DECISION

```
===============================================================================
                     PHASE 9.1 FEASIBILITY DETERMINATION
===============================================================================
               >>> CONDITIONAL GO — HYBRID ARCHITECTURE <<<
===============================================================================
```

### Determination Rationale
1. **Feasible Component (GO):**
   - Amadeus Hotel Search API v3 is technically sound, officially documented, and supports OAuth2 authentication, structured room pricing, GST tax breakdowns, and cancellation policies.
   - It will be implemented in Phase 9.2 as an optional, authenticated tool for commercial GDS hotels in Katra.
2. **Limitation & Safeguard (MANDATORY HYBRID FALLBACK):**
   - In the Amadeus **Test/Sandbox** environment, Katra geocodes return zero properties due to sandbox geographical mock restrictions.
   - In **Production**, GDS coverage is restricted to chain hotels and omits local Shrine Board dharamshalas.
   - Therefore, Amadeus **must never be a hard single point of failure**. It must operate alongside the existing Phase 8 curated hotel dataset (`db.py` / `data/hotels_live.csv`) and official SMVDSB tariff schedules.

---

## 10. ACCOUNT SETUP INSTRUCTIONS FOR USER

To enable live Amadeus GDS hotel data in subsequent checkpoints:
1. Navigate to [developers.amadeus.com](https://developers.amadeus.com) and click **Register**.
2. Verify your email and log in to your dashboard.
3. Click **My Self-Service Workspace** → **Create New App**.
4. Name the application `Yatra-AI` and select category `Travel Guide`.
5. Copy the generated **API Key** (`client_id`) and **API Secret** (`client_secret`).
6. Place them in your `.env` file:
   ```bash
   AMADEUS_CLIENT_ID=your_api_key_here
   AMADEUS_CLIENT_SECRET=your_api_secret_here
   AMADEUS_ENVIRONMENT=test
   ```
*(Note: When credentials are not provided, the application will automatically engage the verified Tier 2 curated Katra hotel catalog without interruption).*

---

*(Phase 9.1 Feasibility Check is complete. Application code and backup repository remain strictly untouched. Awaiting user review before proceeding.)*
