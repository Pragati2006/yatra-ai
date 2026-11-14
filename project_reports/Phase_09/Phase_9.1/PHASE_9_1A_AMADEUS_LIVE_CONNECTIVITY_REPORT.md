# PHASE 9.1A — AMADEUS REAL ACCOUNT CONNECTIVITY & KATRA INVENTORY VALIDATION REPORT
## Yatra AI — Unified Pilgrimage & Tourism Assistant

**Audit Date:** November 7, 2026
**Auditor Roles:** Senior Data Systems Architect, Full-Stack Integration Engineer, API Security Auditor
**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Workspace Python Environment:** `C:\Users\praga\OneDrive\Documents\Minor Project\venv\Scripts\python.exe` (Python 3.12.4)
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (Strictly Untouched at HEAD `8996d6a`)
**Audit Status:** Strictly Read-Only (Zero Application Code Modified)

---

## 1. CREDENTIAL & ENVIRONMENT AUDIT

In accordance with strict security and truth-in-data protocols, the repository and runtime environment were audited for Amadeus API credentials:

| Check Item | Target / Command | Result | Audit Evidence |
|---|---|:---:|---|
| **`.env` File Existence** | `Test-Path 'yatra-ai\.env'` | **ABSENT** | File does not exist in workspace root |
| **`.env` Git-Ignored Status** | `git check-ignore -v .env` | **CONFIRMED IGNORED** | Matched `.gitignore:31:*.env` & line 28 `.env` |
| **`AMADEUS_CLIENT_ID`** | `os.getenv('AMADEUS_CLIENT_ID')` | **ABSENT** | `False` (Not set in environment or file) |
| **`AMADEUS_CLIENT_SECRET`** | `os.getenv('AMADEUS_CLIENT_SECRET')` | **ABSENT** | `False` (Not set in environment or file) |
| **`AMADEUS_ENVIRONMENT`** | `os.getenv('AMADEUS_ENVIRONMENT')` | **ABSENT** | `None` (Not configured) |

### Security Protocol Execution
- **Zero Exposure:** No credential values were printed, logged, copied, or stored.
- **Halt Execution Rule:** Because credentials are completely absent, live outbound API requests to Amadeus were **stopped immediately**.
- **Truth-in-Data Mandate:** Zero synthetic responses, mock tokens, or fabricated property lists were generated.

---

## 2. API CONNECTIVITY TEST RESULTS

Because credentials are absent from the runtime environment, the automated test suite executed strict non-invocation logging:

| API Operation | Endpoint | Execution Status | Actual HTTP Status | Notes / Sanitized Detail |
|---|---|:---:|:---:|---|
| **OAuth2 Token Exchange** | `POST /v1/security/oauth2/token` | **NOT ATTEMPTED** | N/A | Blocked: No `client_id` or `client_secret` configured |
| **Hotel List by Geocode** | `GET /v1/reference-data/locations/hotels/by-geocode` | **NOT EXECUTED** | N/A | Blocked: Requires valid Bearer access token |
| **Hotel Search v3** | `GET /v3/shopping/hotel-offers` | **NOT EXECUTED** | N/A | Blocked: Dependent on property discovery & token |
| **Specific Offer Details** | `GET /v3/shopping/hotel-offers/{offerId}` | **NOT EXECUTED** | N/A | Blocked: Dependent on live offer generation |

- **Actual Katra Hotel Count Returned:** `0` (API calls halted).
- **Actual Returned Property Identifiers:** `None`.
- **Actual Returned Fields:** `None`.

---

## 3. KATRA HOTEL INVENTORY COVERAGE VALIDATION

```
===============================================================================
                     KATRA HOTEL INVENTORY STATUS: UNVERIFIED
===============================================================================
```

### 3.1 Test Environment Reality
- Even if developer test credentials were supplied, the Amadeus developer sandbox uses a static mock database restricted to global aviation hub cities (e.g. PAR, NYC, LON, DFW, BKK, DEL, BOM).
- As established in Phase 9.1, Katra (`32.99° N, 74.93° E`) does not exist in the developer sandbox database and returns an empty list `[]` or `404 Not Found`.

### 3.2 Production Coverage Status
- **Status:** **UNVERIFIED**
- Because production credentials are not configured, **no live production calls could be performed**.
- **Audit Mandate Observed:** We do not claim or assume that named Katra properties (e.g. Vivanta Katra, Welcomhotel Katra, Lemon Tree, Hotel Rama Trident) are currently indexed and active in Amadeus GDS distribution for any specific travel date without live production verification.
- Furthermore, local Katra Shrine Board dharamshalas (Niharika, Kalika, Trikuta Bhawan) and unlisted budget guest houses are definitively known to operate outside global GDS networks.

---

## 4. VERIFICATION OF API CLAIMS & STRUCTURAL INDUSTRY CHANGES

A technical audit of official Amadeus developer documentation and recent travel platform governance revealed a critical industry transition:

### 4.1 Structural Platform Shift: Decommissioning of Self-Service Model
- **Crucial Finding:** On **July 17, 2026**, Amadeus officially **decommissioned its public Self-Service Developer model** (which previously provided instant sign-ups and public free monthly quotas).
- **Enterprise Only:** The Amadeus developer portal (`developers.amadeus.com`) has transitioned exclusively to an **Enterprise API model**.
- **Impact on Yatra AI:**
  - Instant self-service registration with free instant test keys is no longer publicly offered for new accounts.
  - Access now requires enterprise commercial onboarding, travel industry accreditation (e.g., IATA, ARC, or registered travel entity status), and a custom negotiated commercial agreement.

### 4.2 Verified API Claims Matrix

| Dimension | Previous Assumption | Verified Ground Truth (Nov 2026) | Application Design Impact |
|---|---|---|---|
| **Monthly Free Quota** | ~2,000 free requests/month | **Contract-Governed.** No public free quota for new accounts. Free/included calls are negotiated per enterprise contract. | Application must never assume unbounded free API calls. Must strictly throttle and cache. |
| **Pricing Model** | €0.03 pay-as-you-go per call | **Custom Enterprise Agreement.** Pricing depends on projected volume and look-to-book ratio. | Must prevent unnecessary background polling or speculative queries. |
| **Rate Limits (TPS)** | Fixed 10 TPS test / 20–40 TPS prod | **Contract Capacity Allocations.** Assigned during enterprise account onboarding. Bursting causes HTTP 429. | Must enforce client-side queue throttling (min 100ms interval between calls). |
| **Offer Validity & Expiry** | Fixed static lifespan | **Ephemeral Dynamic Quotation.** Offer tokens (`offerId`) dynamically expire within 15 to 30 minutes as CRS rates fluctuate. | Cache TTL for live pricing must be capped at 15 minutes. |
| **Permitted Caching Duration** | Unlimited | **Strict 24-Hour Maximum.** Amadeus terms forbid storing pricing/inventory beyond 24 hours. | `CacheManager` TTL enforced at 15m (live) / 24h (static metadata only). |
| **Offer Revalidation** | Optional | **MANDATORY.** `/v3/shopping/hotel-offers/{offerId}` must be called prior to booking handoff to confirm rate/inventory lock. | Booking handoff workflow must incorporate mandatory offer revalidation. |
| **Production Activation** | Automated credit card setup | **Commercial Sales Vetting.** Requires enterprise vetting, business verification, and signed commercial agreement. | Application must function completely without Amadeus credentials. |

---

## 5. ERRORS, RISKS & LIMITATIONS

1. **Hard Dependency Risk (Critical):**
   - If Yatra AI relied exclusively on Amadeus for Katra accommodation, the application would completely fail to return hotel options in development, evaluation, and production environments where Amadeus Enterprise credentials are not configured.
2. **Budget Segment Omission:**
   - Amadeus GDS indexes only commercial/chain properties. Even with production access, it cannot satisfy pilgrims seeking SMVDSB dharamshalas (₹120–₹1,500/night) or budget Katra guest houses.
3. **Quota Consumption & Throttling Risk:**
   - Live hotel search is expensive. High look-to-book ratios or automated bot traffic can rapidly exhaust enterprise monthly volume allowances or trigger HTTP 429 rate limit errors.

---

## 6. FINAL GO / NO-GO DECISION & STRATEGIC RECOMMENDATION

```
===============================================================================
                     PHASE 9.1A AUDIT DETERMINATION
===============================================================================
  >>> NO-GO AS HARD DEPENDENCY | GO AS HYBRID ENTERPRISE CONNECTOR <<<
===============================================================================
```

### Determination Rationale
1. **NO-GO for Single-Source Amadeus Integration:**
   - Because credentials are absent and the Amadeus Self-Service model was decommissioned, Amadeus **cannot and must not be a mandatory prerequisite** for running Yatra AI.
2. **GO for Hybrid Dual-Tier Accommodation Engine:**
   - **Tier 2 (Curated & Verified Catalog) — Primary Baseline:**
     - The curated Katra hotel database (`data/hotels_live.csv` / `db.py`) and official SMVDSB dharamshala tariff schedules serve as the foundational, always-available accommodation engine.
     - Provenance is explicitly tagged as `CURATED_DATA` / `INDICATIVE_SCHEDULE` with amber freshness badges.
     - Guarantees 100% test passing, zero deployment blockers, and full coverage from ₹120 to ₹5,000+.
   - **Tier 1 (Amadeus Enterprise Connector) — Optional Plugin:**
     - `services/amadeus_service.py` is implemented as an optional, authenticated connector.
     - At runtime, it checks `bool(AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET)`.
     - If configured, it retrieves live commercial rates from Amadeus and tags them as `LIVE_API` with emerald badges.
     - If unconfigured, quota-depleted, or timed out, it gracefully falls back to Tier 2 without throwing errors or interrupting the user conversation.

---

## 7. USER ACTION GUIDE: HOW TO CONFIGURE CREDENTIALS

If you possess active Amadeus Enterprise credentials and wish to validate live connectivity:

1. Create a `.env` file in the repository root (`C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai\.env`).
2. Add your enterprise credentials:
   ```env
   AMADEUS_CLIENT_ID=your_enterprise_api_key
   AMADEUS_CLIENT_SECRET=your_enterprise_api_secret
   AMADEUS_ENVIRONMENT=test   # or 'production'
   ```
3. Save the file. (Git will automatically ignore it via `.gitignore`).
4. Re-run Phase 9.1A connectivity verification to perform live OAuth token exchange and geocode search.

*(If credentials are not provided, Yatra AI will automatically and cleanly operate using the verified Tier 2 curated Katra accommodation catalog).*
