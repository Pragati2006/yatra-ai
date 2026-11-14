# Phase 16.0.2.11 — Final Exact Staging Manifest Reconciliation Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Repository Target:** Active `yatra-ai` repository ONLY
**Deployment Target:** Render Free Native Python Web Service (FastAPI)
**Audit Mode:** STRICT READ-ONLY AUDIT & CHANGE-CONTROL VERIFICATION
**Timestamp:** 2026-11-14T22:52:00+05:30
**Audit Verdict:** `ACCEPT — READY FOR HUMAN EXACT STAGING APPROVAL`

---

## Executive Summary

Phase 16.0.2.11 provides the final technical reconciliation of the repository inventory, exact staging manifest, dataset provenance, security isolation, and Render environment contract prior to any Git staging (`git add`), commit, push, or cloud service creation.

Key findings and reconciled metrics:
1. **Repository Inventory Reconciled to 494 Files:** The repository contains exactly **210 tracked files** (66 modified, 144 unmodified) and **284 clean untracked files**, yielding exactly **494 unique non-ignored files** ($210 + 284 = 494$). The previous 493-file count in Phase 16.0.2.10 reflected the state before `docs/PHASE_16_0_2_10_FINAL_MANIFEST_RECONCILIATION_REPORT.md` was generated; upon its creation, the untracked file count became 284.
2. **Untracked Directory Collapsing Explained:** `git status --porcelain=v1` reports **127 untracked entries** because Git collapses 9 untracked subdirectories (`android/`, `docs/screenshots/`, `knowledge_base/`, `project_reports/`, `rag/`, `scripts/`, `services/`, and 2 frontend components folders) containing 166 individual files into directory markers (`?? dir/`), plus 118 direct untracked files ($9 + 118 = 127$). In contrast, `git ls-files --others --exclude-standard` recurses into every folder, enumerating all **284 individual clean files** ($166 + 118 = 284$).
3. **Section 8.4 Arithmetic Typo Resolved:** The Section 8.4 title in Phase 16.0.2.10 stated '247 Files' due to a calculation error ($247 - 237 = 10$). The 5 constituent groups sum to exactly **237 files**: `tests/` (96), `docs/` (70), `project_reports/` (54), `scripts/` (11), and legacy CLI modules (6) ($96 + 70 + 54 + 11 + 6 = 237$). The documentation discrepancy (69 vs 70) is resolved: `docs/` contained 69 files prior to Phase 16.0.2.10, and 70 files with that phase's report included.
4. **Category A Sub-Classification Audited (89 Files):** Category A decomposes into **78 REQUIRED files** (65 core Python modules + 13 curated production data assets), **9 CONDITIONAL files** (4 conditional Python modules: `airtable_store.py`, `utils/pdf_generator.py`, `agents/rpa_agent.py`, `services/live_data/adapters/mock_provider.py` + 5 synthetic baseline CSVs), and **2 DEVELOPMENT-ONLY files** (`rag/evaluation.py` and `services/transport_ingestion.py`).
5. **Zero Secrets Tracked in Git:** Verified that `.env`, `.env.production`, SQLite databases (`*.db`, `*.db-wal`, `*.db-shm`), `data/*_live.csv`, `data/bookings.csv`, and keys are completely ignored by `.gitignore` and **NOT TRACKED** in Git.
6. **Render Environment Contract Verified:** All 10 environment variables were traced to consuming source code. It is formally proven that `APP_ENV=production` alone is sufficient for full production enforcement while setting both `APP_ENV=production` and `ENV=production` ensures complete backwards compatibility.
7. **Two Defensible Manifests Produced:** Manifest A (Minimum Render Runtime: 88 files) and Manifest B (Exact Repository Staging Candidate: 494 files partitioned into 8 mutually exclusive classes with 0 overlaps).
8. **Zero Git Mutations Executed:** No files staged, no commits created, no pushes performed, and no Render service created. Working tree preserved.

---

## Task 1 — Repository Inventory Reconciliation

### Baseline Git Measurement
- **Repository Root:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
- **Current Branch:** `main`
- **HEAD Commit:** `db54ba33f6049caec6894bb8e943be20656fa02c`
- **Tracked Files:** `210`
- **Modified Tracked Files:** `66`
- **Unmodified Tracked Files:** `144` ($210 - 66 = 144$)
- **Added / Deleted / Renamed Tracked Files:** `0`
- **Untracked Porcelain Entries:** `127` (shown by `git status --porcelain=v1`)
- **Individual Clean Untracked Files:** `284` (shown by `git ls-files --others --exclude-standard`)
- **Ignored Files:** `32,205` (node_modules, build outputs, local test environments, pycache)
- **Total Unique Non-Ignored Files:** `494` ($210 + 284 = 494$)

### Directory-Collapsed Untracked Entries vs. Individual Untracked Files
`git status --porcelain=v1` groups untracked subdirectories into single `?? dir/` tokens to keep status output compact. The 127 untracked porcelain entries comprise:
- **9 Untracked Subdirectories:**
  1. `android/`: 46 files (Expo React Native mobile application)
  2. `docs/screenshots/`: 7 files (Phase 12.2.2 public acceptance screenshots)
  3. `frontend/src/components/chat/provenance/`: 6 files (Provenance UI components)
  4. `frontend/src/components/common/`: 1 file (`VerificationBadge.jsx`)
  5. `knowledge_base/`: 6 files (Curated pilgrimage & tourism RAG JSONs)
  6. `project_reports/`: 54 files (Historical phase reports)
  7. `rag/`: 9 files (RAG pipeline modules)
  8. `scripts/`: 11 files (Verification and build automation scripts)
  9. `services/`: 26 files (Live data architecture, adapters, and transport engines)
  - **Subtotal in Untracked Directories:** $46 + 7 + 6 + 1 + 6 + 54 + 9 + 11 + 26 = 166 \text{ files}$
- **118 Direct Untracked Files:** Individual untracked files located at repository root or inside already-tracked directories (e.g. 57 untracked markdown reports in `docs/`, 39 untracked tests in `tests/`, 22 untracked files in `frontend/src/`).
- **Sum of Untracked Porcelain Entries:** $9 \text{ (dirs)} + 118 \text{ (files)} = 127 \text{ entries}$.
- **Sum of Individual Untracked Files:** $166 \text{ (inside dirs)} + 118 \text{ (direct files)} = 284 \text{ files}$.

### Mathematical Resolution of the 493 vs 494 File Count
- In Phase 16.0.2.10 prior to generating its report, the untracked file count was 283 ($210 \text{ tracked} + 283 \text{ untracked} = 493$).
- When `docs/PHASE_16_0_2_10_FINAL_MANIFEST_RECONCILIATION_REPORT.md` was saved, it added exactly 1 file to `docs/`, raising untracked files to 284 ($210 + 284 = 494$).
- Thus, the current repository state is independently verified at exactly **494 non-ignored files**.

---

## Task 2 — Correction of Section 8.4 Arithmetic & 69 vs 70 Docs Resolution

### Breakdown of the 237 Files
Phase 16.0.2.10 Section 8.4 listed 5 groups totaling 237 files but bore a header stating '247 Files' due to a typographic arithmetic error ($247 - 237 = 10$). The exact verified file counts by actual filesystem path are:

| Directory / Group | Tracked Files | Untracked Files | Total Clean Files | Scope Description |
| :--- | :---: | :---: | :---: | :--- |
| `tests/` | 57 | 39 | **96** | Automated test suite (unit, integration, e2e, security) |
| `docs/` | 6 | 64 | **70** | Architecture, security, deployment, and milestone docs |
| `project_reports/` | 0 | 54 | **54** | Milestone project reports (phases 1-14) |
| `scripts/` | 0 | 11 | **11** | Local dev and test automation utilities |
| Standalone Legacy Modules | 6 | 0 | **6** | `mongodb_agent.py`, `langchain_tools.py`, `mongodb_tools.py`, `payment.py`, `build_dataset.py`, `data_gen.py` |
| **Verified Subtotal** | **69** | **168** | **237** | **Zero omissions, zero double counts** |

### Documentation Count Reconciliation (69 vs 70 Files)
The 69 vs 70 documentation file discrepancy is fully resolved as follows:
- **Before Phase 16.0.2.10:** `docs/` contained 69 files: 55 markdown reports (`.md`), 1 JSON test artifact (`phase12_2_2_acceptance_results.json`), 6 root screenshots, and 7 subdirectory screenshots in `docs/screenshots/` ($55 + 1 + 6 + 7 = 69$).
- **After Phase 16.0.2.10:** Creation of `docs/PHASE_16_0_2_10_FINAL_MANIFEST_RECONCILIATION_REPORT.md` increased markdown reports to 56, bringing the total to exactly **70 files** ($56 + 1 + 6 + 7 = 70$).
- Upon creation of this Phase 16.0.2.11 report, the count will be 71 files ($57 + 1 + 6 + 7 = 71$).

---

## Task 3 — Comprehensive Audit of 89 Category A Runtime & Data Files

Every file in Category A (89 files) has been audited against production call paths and classified into one of three mutually exclusive categories:
- **REQUIRED (78 files):** Imported or executed during normal FastAPI startup and core conversational flows.
- **CONDITIONAL (9 files):** Executed only under specific runtime conditions or unseeded fallbacks.
- **DEVELOPMENT-ONLY (2 files):** Offline evaluation or ingestion tools with zero production runtime references.

### Dataset Taxonomy
1. **Curated Production Data (13 files - REQUIRED):** Pre-computed, authoritative domain assets loaded into memory at startup or query time.
   - `data/curated_railway_schedules.json` (Loaded by `services/live_data/adapters/curated_railway_adapter.py`)
   - `data/curated_bus_schedules.json` (Loaded by `services/live_data/adapters/curated_bus_adapter.py`)
   - `data/curated_flight_schedules.json` (Loaded by `services/live_data/adapters/curated_flight_adapter.py`)
   - `data/katra_accommodation_catalog.json` (Loaded by `services/accommodation_catalog.py`)
   - `data/curated_operational_notices.json` (Loaded by `services/operational_notices.py`)
   - `data/verified_contacts.json` (Loaded by `services/verified_contacts.py`)
   - `data/vector_store.json` (Pre-indexed semantic RAG embeddings loaded by `rag/vector_store.py`)
   - `knowledge_base/cultural_and_historical.json` (Curated pilgrimage RAG source loaded by `rag/retriever.py`)
   - `knowledge_base/jk_regional_tourism.json` (Curated tourism RAG source loaded by `rag/retriever.py`)
   - `knowledge_base/routes_and_trekking.json` (Curated route RAG source loaded by `rag/retriever.py`)
   - `knowledge_base/vaishno_devi_pilgrimage.json` (Curated shrine RAG source loaded by `rag/retriever.py`)
   - `knowledge_base/yatra_faqs.json` (Curated FAQ RAG source loaded by `rag/retriever.py`)
   - `knowledge_base/yatra_registration_guidance.json` (Curated registration RAG source loaded by `rag/retriever.py`)
2. **Conditional Fallback Data (1 file in Cat B + 5 CSVs in Cat A - CONDITIONAL):**
   - `data/users_dataset.csv` (Cat B): Accessed by `db.py` only if legacy CSV authentication is invoked; completely bypassed when `PERSISTENCE_BACKEND=mongodb`.
   - `data/trains_dataset.csv`, `data/buses_dataset.csv`, `data/flights_dataset.csv`, `data/hotels_dataset.csv`, `data/yatra_slots_dataset.csv` (Cat A): Synthetic baseline CSVs accessed by `db.py` when live adapters or MongoDB collections are unseeded.
3. **Offline-Only Data Generators (Category C):**
   - `build_dataset.py` and `data_gen.py`: Offline synthetic generator scripts; excluded from production.

### Detailed Audit Table for Conditional & Development-Only Category A Files

| File Path | Classification | Size (bytes) | Exact Production Call Path & Source Reference | Runtime Condition / Justification |
| :--- | :---: | :---: | :--- | :--- |
| `airtable_store.py` | **CONDITIONAL** | 3,136 | `db.py:40` (`import airtable_store`) | Top-level import required to avoid `ModuleNotFoundError` on `import db`; runtime storage executed only if Airtable credentials configured in `st.secrets` |
| `utils/pdf_generator.py` | **CONDITIONAL** | 5,297 | `backend/routes/yatra.py:34` (`from utils import pdf_generator`) | Invoked only when user requests a downloadable PDF receipt via `/api/yatra/booking/pdf` |
| `agents/rpa_agent.py` | **CONDITIONAL** | 126,244 | `agents/coordinator.py:34` & `backend/routes/yatra.py:32` | Invoked only during the final booking execution handoff flow when user confirms booking |
| `services/live_data/adapters/mock_provider.py` | **CONDITIONAL** | 6,797 | `services/live_data/adapters/__init__.py:12` | Invoked only when `MOCK_LIVE_DATA=true` or live external providers fail |
| `data/trains_dataset.csv` | **CONDITIONAL** | 50,463 | `db.py:53` (`search_trains`) | Fallback dataset loaded only when curated live railway adapter is unavailable |
| `data/buses_dataset.csv` | **CONDITIONAL** | 4,561 | `db.py:78` (`search_buses`) | Fallback dataset loaded only when curated live bus adapter is unavailable |
| `data/flights_dataset.csv` | **CONDITIONAL** | 20,797 | `db.py:102` (`search_flights`) | Fallback dataset loaded only when curated live flight adapter is unavailable |
| `data/hotels_dataset.csv` | **CONDITIONAL** | 21,149 | `db.py:128` (`search_hotels`) | Fallback dataset loaded only when curated accommodation catalog is unavailable |
| `data/yatra_slots_dataset.csv` | **CONDITIONAL** | 18,775 | `db.py:155` (`get_darshan_availability`) | Fallback dataset loaded only when live shrine board slot adapter is unavailable |
| `rag/evaluation.py` | **DEVELOPMENT-ONLY** | 30,399 | None (0 production references; tested in `tests/test_phase7_1_rag_reliability.py`) | Offline retrieval evaluation utility computing MRR, Hit@K, and NDCG benchmark metrics |
| `services/transport_ingestion.py` | **DEVELOPMENT-ONLY** | 19,915 | None (0 production references; tested in `tests/test_phase14_4_3_transport_expansion.py`) | Standalone ETL script used to transform raw timetable text into curated transit JSON catalogs |

### Summary of Category A Audit
- **REQUIRED:** 78 files (65 Core Python Modules + 13 Curated Production Data Assets)
- **CONDITIONAL:** 9 files (4 Conditional Python Modules + 5 Synthetic Baseline CSVs)
- **DEVELOPMENT-ONLY:** 2 files (`rag/evaluation.py`, `services/transport_ingestion.py`)
- **Total Category A Files:** $78 + 9 + 2 = 89 \text{ files}$.

---

## Task 4 — Git Secret Exclusion Verification

A thorough read-only audit of Git tracked files confirmed zero secrets or mutable local state in version control:

| Sensitive Pattern / Target | Git Tracking Status | `.gitignore` Rule | Verification Command | Safety Verdict |
| :--- | :---: | :--- | :--- | :---: |
| `.env` | **UNTRACKED** | Line 28: `.env*` | `git ls-files .env` -> empty | **PASS** |
| `.env.production` | **UNTRACKED** | Line 28: `.env*` | `git ls-files .env.production` -> empty | **PASS** |
| `*.db` / `*.sqlite` | **UNTRACKED** | Line 21: `*.db*` | `git ls-files '*.db*'` -> empty | **PASS** |
| `data/*.db*` | **UNTRACKED** | Line 23: `data/*.db*` | `git ls-files 'data/*.db*'` -> empty | **PASS** |
| `data/bookings.csv` | **UNTRACKED** | Line 25: `data/bookings.csv` | `git ls-files data/bookings.csv` -> empty | **PASS** |
| `data/*_live.csv` | **UNTRACKED** | Line 26: `data/*_live.csv` | `git ls-files 'data/*_live.csv'` -> empty | **PASS** |
| Private keys (`*.pem`, `*.key`) | **UNTRACKED** | Standard Git exclusion | `git ls-files '*.pem' '*.key'` -> empty | **PASS** |
| Cloud credentials | **UNTRACKED** | Standard Git exclusion | `git ls-files '*serviceAccount*'` -> empty | **PASS** |

> [!IMPORTANT]
> **Zero Secret Exposure Guarantee:** No environment variable values, API keys, credentials, or private connection strings were printed, staged, or exposed during this audit.

---

## Task 5 — Render Environment Contract Verification

Every required and optional environment variable has been traced directly to its consuming source code:

### 1. `APP_ENV`
- **Status:** Optional (defaults to `development`; must be set to `production` on Render).
- **Alias:** `ENV` via `os.getenv('APP_ENV', os.getenv('ENV', 'development')).lower()`.
- **Production Safety:** Safe locally; in production enforces strict security requirements.
- **Consuming Files:** `backend/main.py:31`, `config.py:48`, `agents/auth_service.py:47`, `backend/routes/auth.py:49, 59`, `Dockerfile:11`.
- **Failure Mode:** If unset, defaults to `development` (displays security warnings). In `production` mode, triggers runtime assertions requiring `AUTH_HMAC_SECRET` >= 32 chars.
- **Sufficiency Proof:** Setting `APP_ENV=production` alone IS SUFFICIENT because `APP_ENV` is checked first. Setting both `APP_ENV=production` and `ENV=production` ensures complete backwards compatibility.

### 2. `ENV`
- **Status:** Optional backwards-compatibility alias for `APP_ENV`.
- **Alias:** Checked as fallback if `APP_ENV` is unset.
- **Consuming Files:** `config.py:48`, `agents/auth_service.py:47`, `backend/main.py:31`, `backend/routes/auth.py:49`, `Dockerfile:12`.

### 3. `PORT`
- **Status:** Optional locally; automatically injected by Render on container/native startup.
- **Default:** `8000` (`backend/main.py:366`), `7860` (`Dockerfile:13`).
- **Consuming Files:** `backend/main.py:366` (`port = int(os.getenv('PORT', 8000))`), `Dockerfile:13, 44`, `start.sh:17`.
- **Failure Mode:** If missing, falls back to 8000; if non-integer, raises `ValueError`.

### 4. `PERSISTENCE_BACKEND`
- **Status:** Mandatory on Render (`PERSISTENCE_BACKEND=mongodb`); optional locally (defaults to `sqlite`).
- **Consuming Files:** `agents/mongo_store.py:32`, `backend/main.py:183, 192`.
- **Failure Mode:** If missing on Render, falls back to ephemeral local SQLite (data lost on restart). When set to `mongodb`, `/api/health/readiness` strictly verifies MongoDB Atlas connectivity.

### 5. `MONGO_URI`
- **Status:** Mandatory when `PERSISTENCE_BACKEND=mongodb`; optional in offline CSV/SQLite mode.
- **Default:** None (unset).
- **Consuming Files:** `mongo_db.py:8, 28, 77`, `backend/main.py:220`, `utils/masking.py:16, 184`.
- **Failure Mode:** When unset, circuit breaker engages; in production readiness check, returns `503 Service Unavailable`. Masking ensures URI credentials are redacted (`[REDACTED]`).

### 6. `MONGO_DB_NAME`
- **Status:** Optional (safe default provided).
- **Default:** `yatra-booking-agent` (`mongo_db.py:9`).
- **Consuming Files:** `mongo_db.py:9, 36, 68, 87, 139`.

### 7. `AUTH_HMAC_SECRET`
- **Status:** Mandatory in production (`APP_ENV=production`); optional in development.
- **Alias:** `AUTH_SALT` via `os.getenv('AUTH_HMAC_SECRET', os.getenv('AUTH_SALT', ''))`.
- **Production Safety:** Default salt is strictly blocked in production.
- **Consuming Files:** `agents/auth_service.py:55, 64, 69, 74, 79, 95, 96, 144`.
- **Failure Mode:** If missing, default salt, or < 32 characters in production, FastAPI startup aborts with `RuntimeError: CRITICAL DEPLOYMENT ERROR: AUTH_HMAC_SECRET must be explicitly configured with at least 32 characters`.

### 8. `CORS_ALLOWED_ORIGINS`
- **Status:** Optional (safe production defaults pre-configured).
- **Default:** `http://localhost:5173, http://localhost:3000, https://yatra-ai.pages.dev, https://yatra-agent.pages.dev`.
- **Consuming Files:** `backend/main.py:57, 65`.
- **Failure Mode:** If empty or unset, falls back to safe origin list; if populated, parses comma-separated origins.

### 9. `COOKIE_SECURE`
- **Status:** Optional.
- **Default:** `false` (dev HTTP mode).
- **Consuming Files:** `backend/routes/auth.py:62` (`return request.url.scheme == 'https' or os.getenv('COOKIE_SECURE', 'false').lower() == 'true'`).
- **Production Note:** Under Render's reverse proxy terminating TLS, `request.url.scheme == 'https'` automatically enforces secure cookies; setting `COOKIE_SECURE=true` provides explicit defense-in-depth.

### 10. `GROQ_API_KEY`
- **Status:** Optional for basic service startup and knowledge base lookup; mandatory for conversational LLM chat.
- **Default:** None (unset).
- **Consuming Files:** `backend/main.py:238`, `agents/central_agent.py:7723, 7781, 14474`, `agents/coordinator.py:216`, `utils/masking.py:15, 181`.
- **Failure Mode:** If unset, service starts in degraded/deterministic mode; fallback handler responds with verified knowledge base facts. Keys matching `gsk_*` are automatically masked.

---

## Task 6 — Two Separate Deployment Manifests

### MANIFEST A — Minimum Render Runtime Manifest (88 Files)

Manifest A contains the minimum set of files required to run the Yatra AI FastAPI application natively on Render:
- **Mandatory Core Runtime (78 files):** Core application code, router endpoints, agents, services, live data framework, and curated production knowledge base.
- **Conditional Runtime Fallbacks (9 files):** Defensive compatibility layers (`airtable_store.py`, `utils/pdf_generator.py`, `agents/rpa_agent.py`, `mock_provider.py`) and synthetic baseline CSVs.
- **Build Dependency Manifest (1 file):** `requirements.txt`.
- **Total Minimum Render Runtime Package:** $78 + 9 + 1 = 88 \text{ files}$ (or 90 files including `Dockerfile` and `start.sh` for containerized runtime).

| # | Path | Category | Classification | Size (bytes) | Full SHA-256 Checksum |
| :-: | :--- | :--- | :--- | :---: | :--- |
| 1 | `agent.py` | Core Runtime | **REQUIRED** | 34,085 | `2faa2974d6f5fd76bfa9d475d534f2ffb52a9a3fbc49a6ab3ee7ebdc7c0a98fe` |
| 2 | `agents/__init__.py` | Core Runtime | **REQUIRED** | 571 | `c48758dcd08c8dca5ea2dae508faa738a5b3bbcae6071d17d9d5d2982ebd5521` |
| 3 | `agents/auth_service.py` | Core Runtime | **REQUIRED** | 71,912 | `1aba6858bbba47743707d6bacc10c34bce1c9d20094550782c5e2a65c3747a1e` |
| 4 | `agents/availability_agent.py` | Core Runtime | **REQUIRED** | 17,997 | `8f075aa625dd5d5ef622a15d8ec38ea1429d1dcfe61ea7e8aca6d3ff6988ed62` |
| 5 | `agents/budget_engine.py` | Core Runtime | **REQUIRED** | 24,992 | `533b882d3155f5c55852aae3feb7b969e1be2635930745c0ceaabba12ab9fe2f` |
| 6 | `agents/central_agent.py` | Core Runtime | **REQUIRED** | 180,465 | `524ba9c97f5dd69f43ca2ad0ab448106c777d70faf6294bf63ec7f7659143e92` |
| 7 | `agents/content_agent.py` | Core Runtime | **REQUIRED** | 961 | `90beb3328f2f3f1bb2c350652636c6e8c5508b2f09425965e9a0601d79629294` |
| 8 | `agents/conversation_agent.py` | Core Runtime | **REQUIRED** | 46,036 | `185bec8413493c463b8ab16313b7b45581deeaca227d19237acf64f999f19f8f` |
| 9 | `agents/conversation_state.py` | Core Runtime | **REQUIRED** | 40,352 | `5be15c04fa4c1259c5066b95affde9271ae2e714ac99a47badffc389b85ac408` |
| 10 | `agents/coordinator.py` | Core Runtime | **REQUIRED** | 33,431 | `da3a3d57dd37bb29d6e17f1a8ee46d306da15e6eba2226e830badaf4cbc1a81b` |
| 11 | `agents/itinerary_agent.py` | Core Runtime | **REQUIRED** | 62,637 | `395816b4703b1792b4e50b2e1cbd700569563ebf839d107a1ba712c63454ce50` |
| 12 | `agents/knowledge_agent.py` | Core Runtime | **REQUIRED** | 13,287 | `9a74e2e8d5111fb94a54c406d79a26dd3576a4678af15fb6820a7dc7f08c157c` |
| 13 | `agents/mongo_store.py` | Core Runtime | **REQUIRED** | 27,294 | `c2627617833e2c970e6ea76fad01adc28a6d86c8cca793d74ee0ffe8f06ff757` |
| 14 | `agents/orchestrator.py` | Core Runtime | **REQUIRED** | 121,182 | `bfee43d7195d47322e65edb2a0da368b1385990cf5fc7ffaa54580af0e83c1a8` |
| 15 | `agents/recommendation_agent.py` | Core Runtime | **REQUIRED** | 9,293 | `0d94dea3a0055f2246b4d34602fc0b11a5da9a00c5fb2bfaef48a2a699382987` |
| 16 | `agents/session_store.py` | Core Runtime | **REQUIRED** | 38,018 | `726bdedddea4942768ead0fe3cd8c418b3bc564f63ff47076aea07f53032102b` |
| 17 | `agents/tools.py` | Core Runtime | **REQUIRED** | 17,111 | `3257e3d3e95f0e5497817b5dc0c25d0f56b7b599406bc5fda9b7c27f7043ed80` |
| 18 | `backend/main.py` | Core Runtime | **REQUIRED** | 14,468 | `e2f9f0550f98326bd410f919f3c2aaba3cc7e710f4f220ed2fe934964f0a2793` |
| 19 | `backend/routes/auth.py` | Core Runtime | **REQUIRED** | 23,974 | `f7e6626b6b17f8b2753ba7adb897d9cf29bf0a9b4aa5441ac62627154faade92` |
| 20 | `backend/routes/tourism.py` | Core Runtime | **REQUIRED** | 509 | `bf0a00a292655ecbf48f6420959678c089f53d80f156321047cd36b363dc4a60` |
| 21 | `backend/routes/weather.py` | Core Runtime | **REQUIRED** | 435 | `541f34b591d6cb497f2fe13f687cb23dca74d1cf74f6101dd19eb577363c058b` |
| 22 | `backend/routes/yatra.py` | Core Runtime | **REQUIRED** | 43,382 | `352aa57fe77feecb8848a003f38b68ab0bac7626ddf0e05ab3bc408aa04b39b8` |
| 23 | `config.py` | Core Runtime | **REQUIRED** | 1,728 | `1502b3e26aedf241f259a1da5f184e62b25afbdd2a49c2ba3c76be6394179752` |
| 24 | `data/curated_bus_schedules.json` | Core Runtime | **REQUIRED** | 33,787 | `782157781d91043a4dfcbe4b59225a83f2dc334890a63dbed5644d9a529928cc` |
| 25 | `data/curated_flight_schedules.json` | Core Runtime | **REQUIRED** | 72,035 | `343ab55f41a11d0c22c02c67ac79e366f3d5fa72a41a07b953f2ec47f0ef52ff` |
| 26 | `data/curated_operational_notices.json` | Core Runtime | **REQUIRED** | 3,121 | `7146619d149ff5f07d79d66c0d1eac7b99b9e02015fd9772d427771b508009d7` |
| 27 | `data/curated_railway_schedules.json` | Core Runtime | **REQUIRED** | 115,687 | `0fc39640c6b72abcd3f2966c4df3daf129cff4141fab21c10cf014ce02cd8546` |
| 28 | `data/katra_accommodation_catalog.json` | Core Runtime | **REQUIRED** | 30,278 | `3a803336b45fedf7b3fa9af5eb88f05f7b8a3e88080b6774915d6c53b552a614` |
| 29 | `data/vector_store.json` | Core Runtime | **REQUIRED** | 442,750 | `042f6b09dcfda4de91c12fd45a620ad29596b4de90d79d2f2e171ae271bfacf2` |
| 30 | `data/verified_contacts.json` | Core Runtime | **REQUIRED** | 7,203 | `4baafaadea9b5581a5ce1a7286e9d5fa58455e91658bfc345ff8c8880738f7b7` |
| 31 | `db.py` | Core Runtime | **REQUIRED** | 21,233 | `deee6469f74f8b2f6c1454131b01b3a9fe94e22143a1295c12d920d9faf089af` |
| 32 | `explore_data.py` | Core Runtime | **REQUIRED** | 40,861 | `980cc4e394115e43282d5e7e3a9c6eb7894bb1ff8f2c907e1e2de02ae46289e6` |
| 33 | `knowledge_base/cultural_and_historical.json` | Core Runtime | **REQUIRED** | 4,502 | `84f474a10e6da0b795168596aa6b55e2111c71442e6dfe6573e31b1587a4a562` |
| 34 | `knowledge_base/jk_regional_tourism.json` | Core Runtime | **REQUIRED** | 8,527 | `1619ff2cc4f10a3b8227b0d91372c459396452f05ca38274457510ddd8da429a` |
| 35 | `knowledge_base/routes_and_trekking.json` | Core Runtime | **REQUIRED** | 4,945 | `9d71da3bc1adb637c62f2c4021efcde6c12f1a41e46133dac57f2d843ffcdc6d` |
| 36 | `knowledge_base/vaishno_devi_pilgrimage.json` | Core Runtime | **REQUIRED** | 7,005 | `eb12fa2f530cd91a259f53a9f597aa905cf1edf534eef1fe8bc3813a7a6f50be` |
| 37 | `knowledge_base/yatra_faqs.json` | Core Runtime | **REQUIRED** | 4,956 | `17e26f033e998f57537385561749153e998dc0613fbbc4f32831f52edac518c1` |
| 38 | `knowledge_base/yatra_registration_guidance.json` | Core Runtime | **REQUIRED** | 5,487 | `1db1f42621ec3b9ec575a0a0bd71a0d615954fe3a6cd64b6f03e5bad5f16d6af` |
| 39 | `mongo_db.py` | Core Runtime | **REQUIRED** | 4,282 | `055b2e6165bd696ae0f56cb06b7f5f4c7df0f6768131195a52d3371d13f70256` |
| 40 | `rag/chunker.py` | Core Runtime | **REQUIRED** | 5,588 | `46c4f9d640519282582cd2ecaafba2cf9815292f360c591fcd2719edeb57e962` |
| 41 | `rag/classifier.py` | Core Runtime | **REQUIRED** | 19,904 | `ae8a12d634ba22f14ea9bb00dc37766d63eab7fb388c09dcdb6fb25cb18dc401` |
| 42 | `rag/embeddings.py` | Core Runtime | **REQUIRED** | 11,648 | `00df8dd9e9278de78910f1fa5e4b70b46528835eafc42ad9d2a71a2175795f3b` |
| 43 | `rag/ingestion.py` | Core Runtime | **REQUIRED** | 6,126 | `1b2ceefb1c4c12b5cf9dfa075113941eab21622b4f782d7b3a494cd29e6f5a21` |
| 44 | `rag/normalizer.py` | Core Runtime | **REQUIRED** | 10,396 | `b9fe874788ca999ce8c87c19c287158d0327bd96bed471c5f23c23d2cc77e25f` |
| 45 | `rag/retriever.py` | Core Runtime | **REQUIRED** | 16,812 | `22f6522b534d794420f542cccc5d19f30722b2e6806be49af216322b9ab25a88` |
| 46 | `rag/schema.py` | Core Runtime | **REQUIRED** | 4,511 | `0eb184141c190702969c72f81b2cbd7272924a9ddd8ea7e295a201e57983edf3` |
| 47 | `rag/vector_store.py` | Core Runtime | **REQUIRED** | 9,946 | `f0aa23d8cfc7e6529b6b14e67fd9bf6f60564d34464054241643a3d52565b4cf` |
| 48 | `services/__init__.py` | Core Runtime | **REQUIRED** | 33 | `fa39384bc20992af097a88d57f7d4a83e2de2c48928e9d8ba533e3bc71837251` |
| 49 | `services/accommodation_catalog.py` | Core Runtime | **REQUIRED** | 15,984 | `a22a019bf9dff3c389d214311773920355f737f39484f10384bc8a3215db76c7` |
| 50 | `services/bus_schedules.py` | Core Runtime | **REQUIRED** | 12,032 | `ba799aa96ee71876f6f6551acfeb06f9c9a16b9293da89e12e348ce8cbc72ce3` |
| 51 | `services/connecting_journey_engine.py` | Core Runtime | **REQUIRED** | 64,500 | `8995d632fec0bfcb2e972236aba0ee91bf921231466ed4406a1fc86508db5fe0` |
| 52 | `services/flight_schedules.py` | Core Runtime | **REQUIRED** | 11,020 | `58d3b74dc1166c4fb05cbbcd2ed0c6d04593a879bb9909399037e7c4309efd13` |
| 53 | `services/geo_resolver.py` | Core Runtime | **REQUIRED** | 71,490 | `426d92caf593721db727c2a93c9739184685c45086f6950713a0d8ea00ec7398` |
| 54 | `services/live_data/__init__.py` | Core Runtime | **REQUIRED** | 2,042 | `75d776c3b4cbf2b3758aaa16f52882025a68533b33c64a2b88264b49ba3f9912` |
| 55 | `services/live_data/adapters/__init__.py` | Core Runtime | **REQUIRED** | 775 | `a5db411501b1a5a5c72d69f9393978ea551a15ebd035a843b19ffb3adc11f9d2` |
| 56 | `services/live_data/adapters/curated_accommodation_adapter.py` | Core Runtime | **REQUIRED** | 7,564 | `a702f99c5dd508383dbb3e2e25f966eee360c89484e7c58746bc3ce2999d588a` |
| 57 | `services/live_data/adapters/curated_bus_adapter.py` | Core Runtime | **REQUIRED** | 9,116 | `277e906343170ad3416f32c0acfd57c4a5de3c49af471494b6eb7d0a3e196309` |
| 58 | `services/live_data/adapters/curated_contact_adapter.py` | Core Runtime | **REQUIRED** | 4,407 | `f4fd22c273d456b695a5db324e7245d9fda244043290470687cadbf03c841754` |
| 59 | `services/live_data/adapters/curated_flight_adapter.py` | Core Runtime | **REQUIRED** | 6,219 | `5d32b7200e13e8d4fed70a5311e6cf89fd2107fb9dc9c7c99b594b5807ce82d3` |
| 60 | `services/live_data/adapters/curated_operational_notices_adapter.py` | Core Runtime | **REQUIRED** | 6,162 | `29bc515d450725bee46599e57a3e1445d2e74f3999bc3e3dfb2d2587c22dcdf2` |
| 61 | `services/live_data/adapters/curated_railway_adapter.py` | Core Runtime | **REQUIRED** | 9,073 | `a6554a8723bf19044590ec98529dc499bb515ef80b44c9e3d2ff9a5f12ad31a4` |
| 62 | `services/live_data/adapters/weather_adapter.py` | Core Runtime | **REQUIRED** | 6,311 | `cb15ecbe771f21fab5f88fff62ed5c342003e992eabc98125b59c191fabeffd3` |
| 63 | `services/live_data/base.py` | Core Runtime | **REQUIRED** | 16,195 | `83637d594fd3ae1ef13305572f820a6e9767c3ed19362530c587959ead8b687f` |
| 64 | `services/live_data/contracts.py` | Core Runtime | **REQUIRED** | 44,464 | `c54fd6c78bffca58863cf2b0ff4ad5b3b2c7011cf35c795cc6984c5cb12e6dbe` |
| 65 | `services/live_data/exceptions.py` | Core Runtime | **REQUIRED** | 1,592 | `2fbf625ba4e077f4d509d2f9b90677cbd6ec849caa2e0300659312b9681173df` |
| 66 | `services/live_data/manager.py` | Core Runtime | **REQUIRED** | 38,356 | `84c6fa571ead681019c5619c2f8f09c295afbd33f476fb55c942c481c8b7659a` |
| 67 | `services/live_data/registry.py` | Core Runtime | **REQUIRED** | 3,876 | `580a87e3086d321e78da417ef010f141ce126072f3baf36381f16b4b11d894a2` |
| 68 | `services/operational_notices.py` | Core Runtime | **REQUIRED** | 13,396 | `a975935f03a03248515af11d15b5c96677a1c1966a1b0988fa5de8c1d9389984` |
| 69 | `services/railway_schedules.py` | Core Runtime | **REQUIRED** | 16,511 | `b1517edc7d477d502910c2b25ab1e0d4dd6180b685a1002fcce47149c7f8a378` |
| 70 | `services/transport_schema.py` | Core Runtime | **REQUIRED** | 10,661 | `c9b0f68c42e5decea305b612509865cf675ce61d54276473b6824403b996d2ca` |
| 71 | `services/verified_contacts.py` | Core Runtime | **REQUIRED** | 6,013 | `11ab5ef2d794ee88efebd9fac51153b03c35b2d5e00c905fdf96743c9aceeabd` |
| 72 | `utils/__init__.py` | Core Runtime | **REQUIRED** | 1,787 | `1bd86a2fa35e4c6c4020bbfb4ecee5005a5280be808fff122e827d886a7cb68e` |
| 73 | `utils/cache_manager.py` | Core Runtime | **REQUIRED** | 19,001 | `fbe87e02dc16e0cf14189949226ce7865742c6f860d8f8531edf2fef969b746a` |
| 74 | `utils/logger.py` | Core Runtime | **REQUIRED** | 7,711 | `df76085034bf1506974416e4e70a0fd831d8411b474089920d6be25b9b59928b` |
| 75 | `utils/masking.py` | Core Runtime | **REQUIRED** | 6,981 | `06314a47ab8afc7c67d65539a3c24b34171d3930adbc4b0e76988ee7b7ab332c` |
| 76 | `utils/provenance.py` | Core Runtime | **REQUIRED** | 31,565 | `3a4d05952b37a2c446b7730b60bc494f8668ef766fd00df4c48ccd48453633c3` |
| 77 | `weather.py` | Core Runtime | **REQUIRED** | 42,553 | `afbfffcb582e6d93fb777eb6c091b8fe51353b85bcd2eb603e77f523aa6a6f6c` |
| 78 | `yatra_info.py` | Core Runtime | **REQUIRED** | 5,810 | `1f610839fdcc7b468fed89532fce22c2b3f53d97f57efaa6227f89a0cf899147` |
| 79 | `agents/rpa_agent.py` | Fallback Layer | **CONDITIONAL** | 126,244 | `51231c3f8179e7007dc7ce7bed80ba7e708217b1a1bfe9693c27749b8620eee6` |
| 80 | `airtable_store.py` | Fallback Layer | **CONDITIONAL** | 3,136 | `04ef1ce6218a58697aa797f2359455dc9505932dff8d8723f5dea2df8e83c1ca` |
| 81 | `data/buses_dataset.csv` | Fallback Layer | **CONDITIONAL** | 4,561 | `632d1ee84d17f83e6906d1d5156f7b5da7e098d71084bae389584badbec961fb` |
| 82 | `data/flights_dataset.csv` | Fallback Layer | **CONDITIONAL** | 20,797 | `a9c97181ecbd8e1c0da0693c33de07309dae428afd959fcbd63a671f97aec4be` |
| 83 | `data/hotels_dataset.csv` | Fallback Layer | **CONDITIONAL** | 21,149 | `803c190ea257cb333d81c8878f006268e7242693f57d3f7a7eb5b3d1847f3ed7` |
| 84 | `data/trains_dataset.csv` | Fallback Layer | **CONDITIONAL** | 50,463 | `45fa10a07e00f3935794ec462185127ce7d84635436c7a1e518c4a1d15e325a2` |
| 85 | `data/yatra_slots_dataset.csv` | Fallback Layer | **CONDITIONAL** | 18,775 | `1b7fd01c4c08d03f189a8952f2b48a79e30b2ef9ea586af150cb468a11b551b5` |
| 86 | `services/live_data/adapters/mock_provider.py` | Fallback Layer | **CONDITIONAL** | 6,797 | `1b687f727bfd5cfb875b3c2eff7b2fc72bc809d73d6456deb068c66f1b9051d5` |
| 87 | `utils/pdf_generator.py` | Fallback Layer | **CONDITIONAL** | 5,297 | `cadabdb1b52caf783751edb054d374b1410b469f990e20adf9090eef77f6a140` |
| 88 | `requirements.txt` | Build Config | **BUILD_MANIFEST** | 703 | `781a0faddb03cd3d3445507fc3994bd952f215c467083cb23cff9afbdeb3b654` |

---

### MANIFEST B — Exact Repository Staging Candidate (Complete Enumeration of All 494 Files)

Manifest B enumerates every non-ignored file in the repository across 8 mutually exclusive classes:
1. **Class 1: Backend runtime** (118 files = 89 Cat A + 1 Cat B + 28 Static Place Photos)
2. **Class 2: Frontend application** (86 files under `frontend/`)
3. **Class 3: Android application** (46 files under `android/`)
4. **Class 4: Repository configuration and safe templates** (6 files: `.gitignore`, `Dockerfile`, `render.yaml`, `requirements.txt`, `start.sh`, `.env.example`)
5. **Class 5: Required documentation** (125 files = 70 `docs/` + 54 `project_reports/` + 1 `README.md`)
6. **Class 6: Tests and test fixtures** (96 files under `tests/`)
7. **Class 7: Optional development files** (11 files under `scripts/`)
8. **Class 8: Excluded legacy/offline files** (6 files: `mongodb_agent.py`, `langchain_tools.py`, `mongodb_tools.py`, `payment.py`, `build_dataset.py`, `data_gen.py`)

Staging Recommendation Breakdown:
- **YES (Proposed for Staging):** **430 files** (Production Backend, Frontend, Docs, Tests, Config, Static Assets)
- **HUMAN_REVIEW (Pending Explicit Approval):** **58 files** (`data/users_dataset.csv` [1], `scripts/` [11], `android/` [46])
- **NO (Excluded Legacy/Offline):** **6 files** (Historical CLI and generator modules)
- **Total Reconciled Files:** $430 + 58 + 6 = 494 \text{ files}$

| # | Exact Relative Path | Class | Git Status | Tracked? | Size (bytes) | Staging Proposal | Full 64-Character SHA-256 Checksum |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| 1 | `agent.py` | Class 1 | `MODIFIED` | `True` | 34,085 | YES | `2faa2974d6f5fd76bfa9d475d534f2ffb52a9a3fbc49a6ab3ee7ebdc7c0a98fe` |
| 2 | `agents/__init__.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 571 | YES | `c48758dcd08c8dca5ea2dae508faa738a5b3bbcae6071d17d9d5d2982ebd5521` |
| 3 | `agents/auth_service.py` | Class 1 | `MODIFIED` | `True` | 71,912 | YES | `1aba6858bbba47743707d6bacc10c34bce1c9d20094550782c5e2a65c3747a1e` |
| 4 | `agents/availability_agent.py` | Class 1 | `MODIFIED` | `True` | 17,997 | YES | `8f075aa625dd5d5ef622a15d8ec38ea1429d1dcfe61ea7e8aca6d3ff6988ed62` |
| 5 | `agents/budget_engine.py` | Class 1 | `MODIFIED` | `True` | 24,992 | YES | `533b882d3155f5c55852aae3feb7b969e1be2635930745c0ceaabba12ab9fe2f` |
| 6 | `agents/central_agent.py` | Class 1 | `UNTRACKED` | `False` | 180,465 | YES | `524ba9c97f5dd69f43ca2ad0ab448106c777d70faf6294bf63ec7f7659143e92` |
| 7 | `agents/content_agent.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 961 | YES | `90beb3328f2f3f1bb2c350652636c6e8c5508b2f09425965e9a0601d79629294` |
| 8 | `agents/conversation_agent.py` | Class 1 | `MODIFIED` | `True` | 46,036 | YES | `185bec8413493c463b8ab16313b7b45581deeaca227d19237acf64f999f19f8f` |
| 9 | `agents/conversation_state.py` | Class 1 | `UNTRACKED` | `False` | 40,352 | YES | `5be15c04fa4c1259c5066b95affde9271ae2e714ac99a47badffc389b85ac408` |
| 10 | `agents/coordinator.py` | Class 1 | `MODIFIED` | `True` | 33,431 | YES | `da3a3d57dd37bb29d6e17f1a8ee46d306da15e6eba2226e830badaf4cbc1a81b` |
| 11 | `agents/itinerary_agent.py` | Class 1 | `MODIFIED` | `True` | 62,637 | YES | `395816b4703b1792b4e50b2e1cbd700569563ebf839d107a1ba712c63454ce50` |
| 12 | `agents/knowledge_agent.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 13,287 | YES | `9a74e2e8d5111fb94a54c406d79a26dd3576a4678af15fb6820a7dc7f08c157c` |
| 13 | `agents/mongo_store.py` | Class 1 | `UNTRACKED` | `False` | 27,294 | YES | `c2627617833e2c970e6ea76fad01adc28a6d86c8cca793d74ee0ffe8f06ff757` |
| 14 | `agents/orchestrator.py` | Class 1 | `MODIFIED` | `True` | 121,182 | YES | `bfee43d7195d47322e65edb2a0da368b1385990cf5fc7ffaa54580af0e83c1a8` |
| 15 | `agents/recommendation_agent.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 9,293 | YES | `0d94dea3a0055f2246b4d34602fc0b11a5da9a00c5fb2bfaef48a2a699382987` |
| 16 | `agents/rpa_agent.py` | Class 1 | `MODIFIED` | `True` | 126,244 | YES | `51231c3f8179e7007dc7ce7bed80ba7e708217b1a1bfe9693c27749b8620eee6` |
| 17 | `agents/session_store.py` | Class 1 | `MODIFIED` | `True` | 38,018 | YES | `726bdedddea4942768ead0fe3cd8c418b3bc564f63ff47076aea07f53032102b` |
| 18 | `agents/tools.py` | Class 1 | `MODIFIED` | `True` | 17,111 | YES | `3257e3d3e95f0e5497817b5dc0c25d0f56b7b599406bc5fda9b7c27f7043ed80` |
| 19 | `airtable_store.py` | Class 1 | `MODIFIED` | `True` | 3,136 | YES | `04ef1ce6218a58697aa797f2359455dc9505932dff8d8723f5dea2df8e83c1ca` |
| 20 | `assets/images/places/Achabal.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 79,491 | YES | `18a35a8f27e78969361fe38cebcfcaf4b02d8d21dff79a232eca69507f25306f` |
| 21 | `assets/images/places/Ardhkuwari, Maa Vaishno Devi!.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 92,334 | YES | `3e13bedba359c3ca1c507d6dff51de9abc2bd4ba06fd5b5b069251c16181a1d3` |
| 22 | `assets/images/places/Baba Dhansar.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 60,388 | YES | `3440b17fc44ccaf987869e473c0e876b3c968a5937529516656cb40c4b294f19` |
| 23 | `assets/images/places/Bahu Fort & Bagh-e-bahu.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 55,630 | YES | `6925a17f20e1e426e88ad9c9d4f27e17742c1037f49d6fe6db0e504a82f22dae` |
| 24 | `assets/images/places/Ban Ganga.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 1,791,873 | YES | `a96cbda5e3c3c3455a1a6e575371bb1f1b03c6b3e8019dc0740ac5b8638156c8` |
| 25 | `assets/images/places/Bhairavnath Temple.png` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 1,546,359 | YES | `eb812d1bf1cd59b9d70d6f7c28a65c95045a523f7ad1fda2c16f5b7d09525bcf` |
| 26 | `assets/images/places/Charan paduka.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 187,114 | YES | `083943948f571989612c8842d8c96e1add4fed13a3c3e2db9a1ba806e5abb7dd` |
| 27 | `assets/images/places/Dal Lake.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 80,928 | YES | `2a71daecaed13d90b9df4fb1cd0ef2dd4fa2d37e1adaadc932c4cff617f87573` |
| 28 | `assets/images/places/Dera Baba Banda Bahadur.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 256,128 | YES | `c62bb4053be1aec17c43acb17cd63a0e384cd44ab5ac4e47d12c427f201374f9` |
| 29 | `assets/images/places/Gulmarg.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 50,924 | YES | `7e6dc4c4ba4402bfc457f33614138df2b42e0ace4bfa797888c7d9b61177fabe` |
| 30 | `assets/images/places/Himkoti.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 35,255 | YES | `50e060adc9ad85c8f6ebfc91826a2e3557f357ce138dcc89ab0b07c973fa4f8d` |
| 31 | `assets/images/places/Jhajjar Kotli.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 47,854 | YES | `55cc48a5fd24e5b3c005ad5a8ac66934c9254b87688900a09574e3989ef2816c` |
| 32 | `assets/images/places/Kheer Bhawani Mandir.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 62,337 | YES | `c2c220d1f21cfe18656238f60ba1d8f6bc68dc4332fe6846df58bacb40cfa58c` |
| 33 | `assets/images/places/Mansar Lake.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 453,756 | YES | `89095d6a0722cd591a355285c9e891e34f5952240e8e4299e5a48fc7ade688d0` |
| 34 | `assets/images/places/Martand Sun Temple.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 159,262 | YES | `d77dc077b248474992c307d86d0c2d8d1f3e697bc8536c14d28b9d3bbbc8475e` |
| 35 | `assets/images/places/Nau Devi Temple.avif` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 47,427 | YES | `35bbe87c7e00ded09e0b1f91ddfca17d216ae13a98b9c6f211d73ebd25a5d48d` |
| 36 | `assets/images/places/Pahalgam.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 56,167 | YES | `ea92bffbcde42b5d7870c392a8d1973b70cf12352e2ffe34caa8f928204ccd75` |
| 37 | `assets/images/places/Patnitop.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 245,103 | YES | `729424cb12adc8cf50f53c45479c73a96152b5cd5bb364857b2669d127568fbd` |
| 38 | `assets/images/places/Peer Kho Cave Temple.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 343,948 | YES | `5e3c7fbf157aa6a0a49cc9740d301c0f9fc15859b7010768657b5e1f19813df4` |
| 39 | `assets/images/places/Raghunath Temple.webp` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 62,942 | YES | `584e44e1bea04d8279b2f982167ec475c2e1ac0fdc9e0ca9395cc48efc7f05e5` |
| 40 | `assets/images/places/Sanasar.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 92,514 | YES | `53e86af7b59f3359135ac24490c90eb9d3bae7ea37de14a83ca44d39d975ddfa` |
| 41 | `assets/images/places/Shankracharya Mandir.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 38,904 | YES | `9d2cfedc3e979ed0a74ddb0d1616b75a2b83b8f4d80afbcca9daaaab1b52ff85` |
| 42 | `assets/images/places/Shiv Khori.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 184,107 | YES | `529aa43dc62e9cae805f1bb641205efeb272b557f06d67a3544dba290cd770a1` |
| 43 | `assets/images/places/Sinthan top.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 42,728 | YES | `813c072f9fdaf518c8b418efb9096521296c053ac72a88104816f13810629cf6` |
| 44 | `assets/images/places/Sonmarg.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 95,470 | YES | `bc8844883e139b0b9a123ad08470c2324a7fb7c3280b8d89a18eee68ad6a3b72` |
| 45 | `assets/images/places/Verinag.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 194,420 | YES | `6adef280f8201e61c3518a043427777de86d72c26cb898cc8620e7603213e160` |
| 46 | `assets/images/places/amar mahal.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 40,088 | YES | `78a0dd28f5c96e23a54b5cbb61d4685009d7038682fb7affc56e42c11ec2ea64` |
| 47 | `assets/images/places/vaishno devi.jpg` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 35,353 | YES | `d8aa816561abc93feeedae84c3fb87d256f7dc3457309c7f28c51ec7558ad736` |
| 48 | `backend/main.py` | Class 1 | `MODIFIED` | `True` | 14,468 | YES | `e2f9f0550f98326bd410f919f3c2aaba3cc7e710f4f220ed2fe934964f0a2793` |
| 49 | `backend/routes/auth.py` | Class 1 | `MODIFIED` | `True` | 23,974 | YES | `f7e6626b6b17f8b2753ba7adb897d9cf29bf0a9b4aa5441ac62627154faade92` |
| 50 | `backend/routes/tourism.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 509 | YES | `bf0a00a292655ecbf48f6420959678c089f53d80f156321047cd36b363dc4a60` |
| 51 | `backend/routes/weather.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 435 | YES | `541f34b591d6cb497f2fe13f687cb23dca74d1cf74f6101dd19eb577363c058b` |
| 52 | `backend/routes/yatra.py` | Class 1 | `MODIFIED` | `True` | 43,382 | YES | `352aa57fe77feecb8848a003f38b68ab0bac7626ddf0e05ab3bc408aa04b39b8` |
| 53 | `config.py` | Class 1 | `MODIFIED` | `True` | 1,728 | YES | `1502b3e26aedf241f259a1da5f184e62b25afbdd2a49c2ba3c76be6394179752` |
| 54 | `data/buses_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 4,561 | YES | `632d1ee84d17f83e6906d1d5156f7b5da7e098d71084bae389584badbec961fb` |
| 55 | `data/curated_bus_schedules.json` | Class 1 | `UNTRACKED` | `False` | 33,787 | YES | `782157781d91043a4dfcbe4b59225a83f2dc334890a63dbed5644d9a529928cc` |
| 56 | `data/curated_flight_schedules.json` | Class 1 | `UNTRACKED` | `False` | 72,035 | YES | `343ab55f41a11d0c22c02c67ac79e366f3d5fa72a41a07b953f2ec47f0ef52ff` |
| 57 | `data/curated_operational_notices.json` | Class 1 | `UNTRACKED` | `False` | 3,121 | YES | `7146619d149ff5f07d79d66c0d1eac7b99b9e02015fd9772d427771b508009d7` |
| 58 | `data/curated_railway_schedules.json` | Class 1 | `UNTRACKED` | `False` | 115,687 | YES | `0fc39640c6b72abcd3f2966c4df3daf129cff4141fab21c10cf014ce02cd8546` |
| 59 | `data/flights_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 20,797 | YES | `a9c97181ecbd8e1c0da0693c33de07309dae428afd959fcbd63a671f97aec4be` |
| 60 | `data/hotels_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 21,149 | YES | `803c190ea257cb333d81c8878f006268e7242693f57d3f7a7eb5b3d1847f3ed7` |
| 61 | `data/katra_accommodation_catalog.json` | Class 1 | `UNTRACKED` | `False` | 30,278 | YES | `3a803336b45fedf7b3fa9af5eb88f05f7b8a3e88080b6774915d6c53b552a614` |
| 62 | `data/trains_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 50,463 | YES | `45fa10a07e00f3935794ec462185127ce7d84635436c7a1e518c4a1d15e325a2` |
| 63 | `data/users_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 225 | HUMAN_REVIEW | `a0d4d0174549c39e313600ae826924aa08a600b922d53438a4f39238e1b55e5f` |
| 64 | `data/vector_store.json` | Class 1 | `UNTRACKED` | `False` | 442,750 | YES | `042f6b09dcfda4de91c12fd45a620ad29596b4de90d79d2f2e171ae271bfacf2` |
| 65 | `data/verified_contacts.json` | Class 1 | `UNTRACKED` | `False` | 7,203 | YES | `4baafaadea9b5581a5ce1a7286e9d5fa58455e91658bfc345ff8c8880738f7b7` |
| 66 | `data/yatra_slots_dataset.csv` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 18,775 | YES | `1b7fd01c4c08d03f189a8952f2b48a79e30b2ef9ea586af150cb468a11b551b5` |
| 67 | `db.py` | Class 1 | `MODIFIED` | `True` | 21,233 | YES | `deee6469f74f8b2f6c1454131b01b3a9fe94e22143a1295c12d920d9faf089af` |
| 68 | `explore_data.py` | Class 1 | `MODIFIED` | `True` | 40,861 | YES | `980cc4e394115e43282d5e7e3a9c6eb7894bb1ff8f2c907e1e2de02ae46289e6` |
| 69 | `knowledge_base/cultural_and_historical.json` | Class 1 | `UNTRACKED` | `False` | 4,502 | YES | `84f474a10e6da0b795168596aa6b55e2111c71442e6dfe6573e31b1587a4a562` |
| 70 | `knowledge_base/jk_regional_tourism.json` | Class 1 | `UNTRACKED` | `False` | 8,527 | YES | `1619ff2cc4f10a3b8227b0d91372c459396452f05ca38274457510ddd8da429a` |
| 71 | `knowledge_base/routes_and_trekking.json` | Class 1 | `UNTRACKED` | `False` | 4,945 | YES | `9d71da3bc1adb637c62f2c4021efcde6c12f1a41e46133dac57f2d843ffcdc6d` |
| 72 | `knowledge_base/vaishno_devi_pilgrimage.json` | Class 1 | `UNTRACKED` | `False` | 7,005 | YES | `eb12fa2f530cd91a259f53a9f597aa905cf1edf534eef1fe8bc3813a7a6f50be` |
| 73 | `knowledge_base/yatra_faqs.json` | Class 1 | `UNTRACKED` | `False` | 4,956 | YES | `17e26f033e998f57537385561749153e998dc0613fbbc4f32831f52edac518c1` |
| 74 | `knowledge_base/yatra_registration_guidance.json` | Class 1 | `UNTRACKED` | `False` | 5,487 | YES | `1db1f42621ec3b9ec575a0a0bd71a0d615954fe3a6cd64b6f03e5bad5f16d6af` |
| 75 | `mongo_db.py` | Class 1 | `MODIFIED` | `True` | 4,282 | YES | `055b2e6165bd696ae0f56cb06b7f5f4c7df0f6768131195a52d3371d13f70256` |
| 76 | `rag/chunker.py` | Class 1 | `UNTRACKED` | `False` | 5,588 | YES | `46c4f9d640519282582cd2ecaafba2cf9815292f360c591fcd2719edeb57e962` |
| 77 | `rag/classifier.py` | Class 1 | `UNTRACKED` | `False` | 19,904 | YES | `ae8a12d634ba22f14ea9bb00dc37766d63eab7fb388c09dcdb6fb25cb18dc401` |
| 78 | `rag/embeddings.py` | Class 1 | `UNTRACKED` | `False` | 11,648 | YES | `00df8dd9e9278de78910f1fa5e4b70b46528835eafc42ad9d2a71a2175795f3b` |
| 79 | `rag/evaluation.py` | Class 1 | `UNTRACKED` | `False` | 30,399 | YES | `23d82d3f6166f6813f1c8ea1fcdff0d0379fcfa58b1265759bada0dd4f0a8488` |
| 80 | `rag/ingestion.py` | Class 1 | `UNTRACKED` | `False` | 6,126 | YES | `1b2ceefb1c4c12b5cf9dfa075113941eab21622b4f782d7b3a494cd29e6f5a21` |
| 81 | `rag/normalizer.py` | Class 1 | `UNTRACKED` | `False` | 10,396 | YES | `b9fe874788ca999ce8c87c19c287158d0327bd96bed471c5f23c23d2cc77e25f` |
| 82 | `rag/retriever.py` | Class 1 | `UNTRACKED` | `False` | 16,812 | YES | `22f6522b534d794420f542cccc5d19f30722b2e6806be49af216322b9ab25a88` |
| 83 | `rag/schema.py` | Class 1 | `UNTRACKED` | `False` | 4,511 | YES | `0eb184141c190702969c72f81b2cbd7272924a9ddd8ea7e295a201e57983edf3` |
| 84 | `rag/vector_store.py` | Class 1 | `UNTRACKED` | `False` | 9,946 | YES | `f0aa23d8cfc7e6529b6b14e67fd9bf6f60564d34464054241643a3d52565b4cf` |
| 85 | `services/__init__.py` | Class 1 | `UNTRACKED` | `False` | 33 | YES | `fa39384bc20992af097a88d57f7d4a83e2de2c48928e9d8ba533e3bc71837251` |
| 86 | `services/accommodation_catalog.py` | Class 1 | `UNTRACKED` | `False` | 15,984 | YES | `a22a019bf9dff3c389d214311773920355f737f39484f10384bc8a3215db76c7` |
| 87 | `services/bus_schedules.py` | Class 1 | `UNTRACKED` | `False` | 12,032 | YES | `ba799aa96ee71876f6f6551acfeb06f9c9a16b9293da89e12e348ce8cbc72ce3` |
| 88 | `services/connecting_journey_engine.py` | Class 1 | `UNTRACKED` | `False` | 64,500 | YES | `8995d632fec0bfcb2e972236aba0ee91bf921231466ed4406a1fc86508db5fe0` |
| 89 | `services/flight_schedules.py` | Class 1 | `UNTRACKED` | `False` | 11,020 | YES | `58d3b74dc1166c4fb05cbbcd2ed0c6d04593a879bb9909399037e7c4309efd13` |
| 90 | `services/geo_resolver.py` | Class 1 | `UNTRACKED` | `False` | 71,490 | YES | `426d92caf593721db727c2a93c9739184685c45086f6950713a0d8ea00ec7398` |
| 91 | `services/live_data/__init__.py` | Class 1 | `UNTRACKED` | `False` | 2,042 | YES | `75d776c3b4cbf2b3758aaa16f52882025a68533b33c64a2b88264b49ba3f9912` |
| 92 | `services/live_data/adapters/__init__.py` | Class 1 | `UNTRACKED` | `False` | 775 | YES | `a5db411501b1a5a5c72d69f9393978ea551a15ebd035a843b19ffb3adc11f9d2` |
| 93 | `services/live_data/adapters/curated_accommodation_adapter.py` | Class 1 | `UNTRACKED` | `False` | 7,564 | YES | `a702f99c5dd508383dbb3e2e25f966eee360c89484e7c58746bc3ce2999d588a` |
| 94 | `services/live_data/adapters/curated_bus_adapter.py` | Class 1 | `UNTRACKED` | `False` | 9,116 | YES | `277e906343170ad3416f32c0acfd57c4a5de3c49af471494b6eb7d0a3e196309` |
| 95 | `services/live_data/adapters/curated_contact_adapter.py` | Class 1 | `UNTRACKED` | `False` | 4,407 | YES | `f4fd22c273d456b695a5db324e7245d9fda244043290470687cadbf03c841754` |
| 96 | `services/live_data/adapters/curated_flight_adapter.py` | Class 1 | `UNTRACKED` | `False` | 6,219 | YES | `5d32b7200e13e8d4fed70a5311e6cf89fd2107fb9dc9c7c99b594b5807ce82d3` |
| 97 | `services/live_data/adapters/curated_operational_notices_adapter.py` | Class 1 | `UNTRACKED` | `False` | 6,162 | YES | `29bc515d450725bee46599e57a3e1445d2e74f3999bc3e3dfb2d2587c22dcdf2` |
| 98 | `services/live_data/adapters/curated_railway_adapter.py` | Class 1 | `UNTRACKED` | `False` | 9,073 | YES | `a6554a8723bf19044590ec98529dc499bb515ef80b44c9e3d2ff9a5f12ad31a4` |
| 99 | `services/live_data/adapters/mock_provider.py` | Class 1 | `UNTRACKED` | `False` | 6,797 | YES | `1b687f727bfd5cfb875b3c2eff7b2fc72bc809d73d6456deb068c66f1b9051d5` |
| 100 | `services/live_data/adapters/weather_adapter.py` | Class 1 | `UNTRACKED` | `False` | 6,311 | YES | `cb15ecbe771f21fab5f88fff62ed5c342003e992eabc98125b59c191fabeffd3` |
| 101 | `services/live_data/base.py` | Class 1 | `UNTRACKED` | `False` | 16,195 | YES | `83637d594fd3ae1ef13305572f820a6e9767c3ed19362530c587959ead8b687f` |
| 102 | `services/live_data/contracts.py` | Class 1 | `UNTRACKED` | `False` | 44,464 | YES | `c54fd6c78bffca58863cf2b0ff4ad5b3b2c7011cf35c795cc6984c5cb12e6dbe` |
| 103 | `services/live_data/exceptions.py` | Class 1 | `UNTRACKED` | `False` | 1,592 | YES | `2fbf625ba4e077f4d509d2f9b90677cbd6ec849caa2e0300659312b9681173df` |
| 104 | `services/live_data/manager.py` | Class 1 | `UNTRACKED` | `False` | 38,356 | YES | `84c6fa571ead681019c5619c2f8f09c295afbd33f476fb55c942c481c8b7659a` |
| 105 | `services/live_data/registry.py` | Class 1 | `UNTRACKED` | `False` | 3,876 | YES | `580a87e3086d321e78da417ef010f141ce126072f3baf36381f16b4b11d894a2` |
| 106 | `services/operational_notices.py` | Class 1 | `UNTRACKED` | `False` | 13,396 | YES | `a975935f03a03248515af11d15b5c96677a1c1966a1b0988fa5de8c1d9389984` |
| 107 | `services/railway_schedules.py` | Class 1 | `UNTRACKED` | `False` | 16,511 | YES | `b1517edc7d477d502910c2b25ab1e0d4dd6180b685a1002fcce47149c7f8a378` |
| 108 | `services/transport_ingestion.py` | Class 1 | `UNTRACKED` | `False` | 19,915 | YES | `25f5d9ae3f8d8dd0122499cd09caac32c3cc953102cb6018062a2b8d6f01f417` |
| 109 | `services/transport_schema.py` | Class 1 | `UNTRACKED` | `False` | 10,661 | YES | `c9b0f68c42e5decea305b612509865cf675ce61d54276473b6824403b996d2ca` |
| 110 | `services/verified_contacts.py` | Class 1 | `UNTRACKED` | `False` | 6,013 | YES | `11ab5ef2d794ee88efebd9fac51153b03c35b2d5e00c905fdf96743c9aceeabd` |
| 111 | `utils/__init__.py` | Class 1 | `MODIFIED` | `True` | 1,787 | YES | `1bd86a2fa35e4c6c4020bbfb4ecee5005a5280be808fff122e827d886a7cb68e` |
| 112 | `utils/cache_manager.py` | Class 1 | `UNTRACKED` | `False` | 19,001 | YES | `fbe87e02dc16e0cf14189949226ce7865742c6f860d8f8531edf2fef969b746a` |
| 113 | `utils/logger.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 7,711 | YES | `df76085034bf1506974416e4e70a0fd831d8411b474089920d6be25b9b59928b` |
| 114 | `utils/masking.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 6,981 | YES | `06314a47ab8afc7c67d65539a3c24b34171d3930adbc4b0e76988ee7b7ab332c` |
| 115 | `utils/pdf_generator.py` | Class 1 | `MODIFIED` | `True` | 5,297 | YES | `cadabdb1b52caf783751edb054d374b1410b469f990e20adf9090eef77f6a140` |
| 116 | `utils/provenance.py` | Class 1 | `UNTRACKED` | `False` | 31,565 | YES | `3a4d05952b37a2c446b7730b60bc494f8668ef766fd00df4c48ccd48453633c3` |
| 117 | `weather.py` | Class 1 | `MODIFIED` | `True` | 42,553 | YES | `afbfffcb582e6d93fb777eb6c091b8fe51353b85bcd2eb603e77f523aa6a6f6c` |
| 118 | `yatra_info.py` | Class 1 | `TRACKED_UNMODIFIED` | `True` | 5,810 | YES | `1f610839fdcc7b468fed89532fce22c2b3f53d97f57efaa6227f89a0cf899147` |
| 119 | `frontend/index.html` | Class 2 | `MODIFIED` | `True` | 844 | YES | `f36e70fcfc2c2e93467d6ef9261eb451dad1c5bf8e5da108dfd7b7b121f2225f` |
| 120 | `frontend/package.json` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 549 | YES | `66238279bd5e485e8cf4bd59e62b8b5e4882ae1bf7910a69f0be34171b62b66e` |
| 121 | `frontend/public/_redirects` | Class 2 | `UNTRACKED` | `False` | 20 | YES | `32a91e4d018194555c7f64f23faf2512270c3a248844b0c107f5f480366483eb` |
| 122 | `frontend/public/assets/images/places/Achabal.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 79,491 | YES | `18a35a8f27e78969361fe38cebcfcaf4b02d8d21dff79a232eca69507f25306f` |
| 123 | `frontend/public/assets/images/places/Ardhkuwari, Maa Vaishno Devi!.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 92,334 | YES | `3e13bedba359c3ca1c507d6dff51de9abc2bd4ba06fd5b5b069251c16181a1d3` |
| 124 | `frontend/public/assets/images/places/Baba Dhansar.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 60,388 | YES | `3440b17fc44ccaf987869e473c0e876b3c968a5937529516656cb40c4b294f19` |
| 125 | `frontend/public/assets/images/places/Bahu Fort & Bagh-e-bahu.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 55,630 | YES | `6925a17f20e1e426e88ad9c9d4f27e17742c1037f49d6fe6db0e504a82f22dae` |
| 126 | `frontend/public/assets/images/places/Ban Ganga.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 1,791,873 | YES | `a96cbda5e3c3c3455a1a6e575371bb1f1b03c6b3e8019dc0740ac5b8638156c8` |
| 127 | `frontend/public/assets/images/places/Bhairavnath Temple.png` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 1,546,359 | YES | `eb812d1bf1cd59b9d70d6f7c28a65c95045a523f7ad1fda2c16f5b7d09525bcf` |
| 128 | `frontend/public/assets/images/places/Charan paduka.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 187,114 | YES | `083943948f571989612c8842d8c96e1add4fed13a3c3e2db9a1ba806e5abb7dd` |
| 129 | `frontend/public/assets/images/places/Dal Lake.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 80,928 | YES | `2a71daecaed13d90b9df4fb1cd0ef2dd4fa2d37e1adaadc932c4cff617f87573` |
| 130 | `frontend/public/assets/images/places/Dera Baba Banda Bahadur.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 256,128 | YES | `c62bb4053be1aec17c43acb17cd63a0e384cd44ab5ac4e47d12c427f201374f9` |
| 131 | `frontend/public/assets/images/places/Gulmarg.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 50,924 | YES | `7e6dc4c4ba4402bfc457f33614138df2b42e0ace4bfa797888c7d9b61177fabe` |
| 132 | `frontend/public/assets/images/places/Himkoti.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 35,255 | YES | `50e060adc9ad85c8f6ebfc91826a2e3557f357ce138dcc89ab0b07c973fa4f8d` |
| 133 | `frontend/public/assets/images/places/Jhajjar Kotli.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 47,854 | YES | `55cc48a5fd24e5b3c005ad5a8ac66934c9254b87688900a09574e3989ef2816c` |
| 134 | `frontend/public/assets/images/places/Kheer Bhawani Mandir.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 62,337 | YES | `c2c220d1f21cfe18656238f60ba1d8f6bc68dc4332fe6846df58bacb40cfa58c` |
| 135 | `frontend/public/assets/images/places/Mansar Lake.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 453,756 | YES | `89095d6a0722cd591a355285c9e891e34f5952240e8e4299e5a48fc7ade688d0` |
| 136 | `frontend/public/assets/images/places/Martand Sun Temple.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 159,262 | YES | `d77dc077b248474992c307d86d0c2d8d1f3e697bc8536c14d28b9d3bbbc8475e` |
| 137 | `frontend/public/assets/images/places/Nau Devi Temple.avif` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 47,427 | YES | `35bbe87c7e00ded09e0b1f91ddfca17d216ae13a98b9c6f211d73ebd25a5d48d` |
| 138 | `frontend/public/assets/images/places/Pahalgam.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 56,167 | YES | `ea92bffbcde42b5d7870c392a8d1973b70cf12352e2ffe34caa8f928204ccd75` |
| 139 | `frontend/public/assets/images/places/Patnitop.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 245,103 | YES | `729424cb12adc8cf50f53c45479c73a96152b5cd5bb364857b2669d127568fbd` |
| 140 | `frontend/public/assets/images/places/Peer Kho Cave Temple.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 343,948 | YES | `5e3c7fbf157aa6a0a49cc9740d301c0f9fc15859b7010768657b5e1f19813df4` |
| 141 | `frontend/public/assets/images/places/Raghunath Temple.webp` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 62,942 | YES | `584e44e1bea04d8279b2f982167ec475c2e1ac0fdc9e0ca9395cc48efc7f05e5` |
| 142 | `frontend/public/assets/images/places/Sanasar.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 92,514 | YES | `53e86af7b59f3359135ac24490c90eb9d3bae7ea37de14a83ca44d39d975ddfa` |
| 143 | `frontend/public/assets/images/places/Shankracharya Mandir.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 38,904 | YES | `9d2cfedc3e979ed0a74ddb0d1616b75a2b83b8f4d80afbcca9daaaab1b52ff85` |
| 144 | `frontend/public/assets/images/places/Shiv Khori.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 184,107 | YES | `529aa43dc62e9cae805f1bb641205efeb272b557f06d67a3544dba290cd770a1` |
| 145 | `frontend/public/assets/images/places/Sinthan top.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 42,728 | YES | `813c072f9fdaf518c8b418efb9096521296c053ac72a88104816f13810629cf6` |
| 146 | `frontend/public/assets/images/places/Sonmarg.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 95,470 | YES | `bc8844883e139b0b9a123ad08470c2324a7fb7c3280b8d89a18eee68ad6a3b72` |
| 147 | `frontend/public/assets/images/places/Verinag.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 194,420 | YES | `6adef280f8201e61c3518a043427777de86d72c26cb898cc8620e7603213e160` |
| 148 | `frontend/public/assets/images/places/amar mahal.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 40,088 | YES | `78a0dd28f5c96e23a54b5cbb61d4685009d7038682fb7affc56e42c11ec2ea64` |
| 149 | `frontend/public/assets/images/places/vaishno devi.jpg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 35,353 | YES | `d8aa816561abc93feeedae84c3fb87d256f7dc3457309c7f28c51ec7558ad736` |
| 150 | `frontend/public/favicon.svg` | Class 2 | `MODIFIED` | `True` | 1,736 | YES | `4b13f88a486b60a43f366ab1db2e3b6939cce89ee76df145e72bac9f41a5d1ce` |
| 151 | `frontend/public/icons.svg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 5,031 | YES | `b45fa506195cfcdef406ba9f0c77b36ddc1a7c224040926ec70abc2fdea7b93a` |
| 152 | `frontend/public/manifest.webmanifest` | Class 2 | `UNTRACKED` | `False` | 689 | YES | `71a54610e48d1021f6601c4df62ba0e10c347d97bfe708363f0144df73fc7aaa` |
| 153 | `frontend/public/yatra-logo.svg` | Class 2 | `UNTRACKED` | `False` | 1,737 | YES | `5b4d10d53a4a57dae776692842d832abccef538c34b341d74b34948e82b43576` |
| 154 | `frontend/src/App.css` | Class 2 | `MODIFIED` | `True` | 8,097 | YES | `e70d0f7c007ca1d02d7051d745eca501626569d2a58029be8669e37b0a437418` |
| 155 | `frontend/src/App.jsx` | Class 2 | `MODIFIED` | `True` | 17,728 | YES | `12305b6c5ad46c6564a988f35bf0df1309043f869249820bfd481633008b262e` |
| 156 | `frontend/src/assets/hero.png` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 13,057 | YES | `881ffbcaafc212e49addad08846a5b82761355fa20624253af3477ba33262c5c` |
| 157 | `frontend/src/assets/react.svg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 4,126 | YES | `35ef61ed53b323ae94a16a8ec659b3d0af3880698791133f23b084085ab1c2e5` |
| 158 | `frontend/src/assets/vite.svg` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 8,709 | YES | `5be21acd42eb7b896e517f4e0f0f11eb5c5d9e54fbbcebe9453f033008fcca6f` |
| 159 | `frontend/src/components/AIChat.jsx` | Class 2 | `MODIFIED` | `True` | 32,499 | YES | `18b8f5fd38a1868229bc6156729ee5a98e38846802cca0b85a09205bedf0cd10` |
| 160 | `frontend/src/components/AuthModal.jsx` | Class 2 | `MODIFIED` | `True` | 16,274 | YES | `9edb403b634bf87ada897b405266bcd3ae6c3cc636a5d227461bec854b4047a3` |
| 161 | `frontend/src/components/Authorization.jsx` | Class 2 | `MODIFIED` | `True` | 49,051 | YES | `1b6eec93019802df73279e5e1ad900c6e678e82a3006a80222a1187a0f3745f0` |
| 162 | `frontend/src/components/BookingConfirmation.jsx` | Class 2 | `MODIFIED` | `True` | 14,540 | YES | `4b10c2e2b105a82cea98ed9c4bb3ba896b73a01be43d4523d7f29355947d42a2` |
| 163 | `frontend/src/components/HotelCard.jsx` | Class 2 | `MODIFIED` | `True` | 5,107 | YES | `bdeb4ad3c5ce37d6f3a4a3813357a8d6632a53b352b6207d09f083d2ab5a2918` |
| 164 | `frontend/src/components/ItineraryTimeline.jsx` | Class 2 | `MODIFIED` | `True` | 28,023 | YES | `a3cdb6c31804d5afb1c43d7ff715bd205fce14c6f8ced9c3ccf211bc69cb13ba` |
| 165 | `frontend/src/components/LandingScreen.jsx` | Class 2 | `UNTRACKED` | `False` | 4,299 | YES | `22d640de06eb54b8ace15e627f6cadcdd99ce0d5a8be0add1b530d6a737beecf` |
| 166 | `frontend/src/components/Navbar.jsx` | Class 2 | `MODIFIED` | `True` | 6,861 | YES | `e1fe60bd39d0e2f824937c567d8239fa325a361edb5b8d7f0c982506866cba60` |
| 167 | `frontend/src/components/RecommendedYatra.jsx` | Class 2 | `MODIFIED` | `True` | 33,539 | YES | `30c5ae25ce386935d35669b4275fdaffe96c90710e9b8bb0613538f33532ad78` |
| 168 | `frontend/src/components/SavedTripsModal.jsx` | Class 2 | `MODIFIED` | `True` | 48,005 | YES | `1254d35bf3f032020b1e87f33d78aa5708872831cf02e7f934b320048253cc85` |
| 169 | `frontend/src/components/SettingsView.jsx` | Class 2 | `UNTRACKED` | `False` | 21,242 | YES | `1e94465859ffd3f2fc55cf96865fbe0681e717007bf6223e4866effc4e37cd48` |
| 170 | `frontend/src/components/SightseeingBrowser.jsx` | Class 2 | `MODIFIED` | `True` | 26,414 | YES | `f40ac05c209a918a7c8d7521bb67b0817d7d8bba1f992de98c42dd226d79061b` |
| 171 | `frontend/src/components/SightseeingCard.jsx` | Class 2 | `MODIFIED` | `True` | 12,499 | YES | `b4bea340d0361590e4c59c905ca21c40538f394535be7d25c45ff2b82d40bed6` |
| 172 | `frontend/src/components/TransportCard.jsx` | Class 2 | `MODIFIED` | `True` | 16,442 | YES | `73f1912ef6987d72ef0dd3b4ce50d55f3b0a6f777b648ebb49001fd357620142` |
| 173 | `frontend/src/components/TravelSearch.jsx` | Class 2 | `MODIFIED` | `True` | 14,851 | YES | `50551dd9407ea326b311645ac0598e307d6515230aac4b9ad22efd1eee6d62a0` |
| 174 | `frontend/src/components/UserInterventionModal.jsx` | Class 2 | `MODIFIED` | `True` | 31,112 | YES | `6cefb087cf1475584313d91ae5d48546850456b1ddc2b9730041928d63771690` |
| 175 | `frontend/src/components/chat/ChatHeader.jsx` | Class 2 | `MODIFIED` | `True` | 14,261 | YES | `10abcb36d94a9d469a3f433a41ea011872a9a2963e2af4140eaa17b09ac4fdb6` |
| 176 | `frontend/src/components/chat/HistoryDrawer.jsx` | Class 2 | `MODIFIED` | `True` | 12,168 | YES | `666a1c23f7c9bc2d5b9eae9170d2f75b947ef57e344c036a4d9368dca9d00334` |
| 177 | `frontend/src/components/chat/MarkdownContent.jsx` | Class 2 | `MODIFIED` | `True` | 15,132 | YES | `ee6d6551155eb8ac0f2dcdcbe8a5bf9d510453fd987bd77f37653195b03b6051` |
| 178 | `frontend/src/components/chat/MessageComposer.jsx` | Class 2 | `MODIFIED` | `True` | 17,085 | YES | `10abc836d447df20f84a896c1b0cf1837b88686d0efeb700c17213b5c5ef55c0` |
| 179 | `frontend/src/components/chat/MessageItem.jsx` | Class 2 | `MODIFIED` | `True` | 10,097 | YES | `bc166166d505f8bd500bf3ed39242c3cae201ddbafe888c72b29ea7ddbddad48` |
| 180 | `frontend/src/components/chat/WelcomeScreen.jsx` | Class 2 | `MODIFIED` | `True` | 6,394 | YES | `8bfaf8658c7945c8a16031f11fddabc75175b7082543d50ce26232bad6d29bfb` |
| 181 | `frontend/src/components/chat/cards/BookingHandoffCard.jsx` | Class 2 | `MODIFIED` | `True` | 6,435 | YES | `477f756ce8cdce3cc2b9045c47b72de74ed9e4e89984eccc6d4ba45a1fdb6fd4` |
| 182 | `frontend/src/components/chat/cards/BudgetCard.jsx` | Class 2 | `MODIFIED` | `True` | 2,907 | YES | `24ce8f00354bf73f5cb8f8e3ddd4a5058a84c143c282e8f96be67bfbb3046dde` |
| 183 | `frontend/src/components/chat/cards/HotelMiniCard.jsx` | Class 2 | `MODIFIED` | `True` | 4,707 | YES | `3fddf7ccb8413855793574ba02259003262b5e8274d7ed5416d41ba78d932ed3` |
| 184 | `frontend/src/components/chat/cards/ItineraryCard.jsx` | Class 2 | `MODIFIED` | `True` | 5,105 | YES | `c39b688535a5adf2dc58c44858e32a73c4f692a3dd22d8611c93afdd617ef596` |
| 185 | `frontend/src/components/chat/cards/OperationalNoticeCard.jsx` | Class 2 | `UNTRACKED` | `False` | 13,154 | YES | `969c8a2872b9cc02a30e5b38ba7b55053e9154dfeae7da659fe30729d2ca043c` |
| 186 | `frontend/src/components/chat/cards/PersonalizedPlanCard.jsx` | Class 2 | `MODIFIED` | `True` | 12,890 | YES | `da4c81fe3abb84c9497a80d7c2fdab7ca76b6f1f020461816da7958edef5634b` |
| 187 | `frontend/src/components/chat/cards/SightseeingAdvisoryCard.jsx` | Class 2 | `MODIFIED` | `True` | 1,403 | YES | `95b7035aad93df7b9a476bdeaf999826cd4bcd3ba3a21154005d6e63316407b3` |
| 188 | `frontend/src/components/chat/cards/TransportMiniCard.jsx` | Class 2 | `MODIFIED` | `True` | 14,326 | YES | `1c150213a039b5c826e64775c6714490d9e7fc60dcfbbd52b424ed88f0b15d17` |
| 189 | `frontend/src/components/chat/cards/VerifiedContactCard.jsx` | Class 2 | `UNTRACKED` | `False` | 9,119 | YES | `5bd0784f0971d3c87ca85ba87bed8b2f332157fb1cedcc66a826f72e0e603340` |
| 190 | `frontend/src/components/chat/cards/WeatherCard.jsx` | Class 2 | `MODIFIED` | `True` | 4,289 | YES | `165ffd4a3ad3790a94b6f02f1de8fbbfc9479db0a4211ddd80d0748e0c46f71b` |
| 191 | `frontend/src/components/chat/provenance/FreshnessIndicator.jsx` | Class 2 | `UNTRACKED` | `False` | 1,192 | YES | `c72e426ae7dddfc0f0f09f57a525727293c188dc525409e17d3823f4a5a8759d` |
| 192 | `frontend/src/components/chat/provenance/ProvenanceList.jsx` | Class 2 | `UNTRACKED` | `False` | 5,136 | YES | `2e09a703e2ba51587e2edc32f5dfc06246c1b277492cabd5f8c772603abaec78` |
| 193 | `frontend/src/components/chat/provenance/SourceBadge.jsx` | Class 2 | `UNTRACKED` | `False` | 2,121 | YES | `d8546ffc2f66cfdd63e83b72607fcc19f2e02c3c4cbfb31dac23e0ed2b60ca39` |
| 194 | `frontend/src/components/chat/provenance/SourceDetailsPopover.jsx` | Class 2 | `UNTRACKED` | `False` | 13,911 | YES | `92f3c42434f09a508ad843588e5f7e7def7832e598c276eda5ad2494acf4f286` |
| 195 | `frontend/src/components/chat/provenance/index.js` | Class 2 | `UNTRACKED` | `False` | 298 | YES | `fa4e6b5e8d14eab1e5cfddb6d2593978126027710d3dfbb242b707ed2b3b946a` |
| 196 | `frontend/src/components/chat/provenance/provenanceUtils.js` | Class 2 | `UNTRACKED` | `False` | 8,400 | YES | `6ec6e608bd64aa3e015bfd306e65334d1cdfe3c3cdf62f311a2f2b940572341a` |
| 197 | `frontend/src/components/common/YatraLogo.jsx` | Class 2 | `UNTRACKED` | `False` | 2,429 | YES | `0349414aff8b9729615876ab0955c395b06a99b8c87318cdf6df46adbb9774fb` |
| 198 | `frontend/src/index.css` | Class 2 | `MODIFIED` | `True` | 10,844 | YES | `8a69b5764b4897c7e26408df09a642692b6d75ff945957bedbb796eded1177f7` |
| 199 | `frontend/src/main.jsx` | Class 2 | `TRACKED_UNMODIFIED` | `True` | 229 | YES | `4b4b864dbe45253425d0c925337180ec07e204295179f80f59551216f466f618` |
| 200 | `frontend/src/pages/Home.jsx` | Class 2 | `MODIFIED` | `True` | 16,621 | YES | `8561c1ba07cc4c2d544d7625598eae92b8006a218a888e6013e89c620748f80b` |
| 201 | `frontend/src/pages/YatraBooking.jsx` | Class 2 | `MODIFIED` | `True` | 65,326 | YES | `82fc58ba8eb0dabda491e97059a7c2cec4b91604bce4b7089a751d9ecf523e16` |
| 202 | `frontend/src/services/api.js` | Class 2 | `MODIFIED` | `True` | 23,693 | YES | `499948326aa0413797fd0cf854c56f06984ff0749ab7614e2bba53715907603a` |
| 203 | `frontend/src/utils/pdfGenerator.js` | Class 2 | `MODIFIED` | `True` | 5,414 | YES | `a4ac6a4576a782276e2272972eed333e5ce60587cacb1af0dc07737a0e2f3c2f` |
| 204 | `frontend/vite.config.js` | Class 2 | `MODIFIED` | `True` | 503 | YES | `5f378b287b5efbe97b83d5b8a086eaf23dfbb502ce5a5075f65c0176a5d25fb9` |
| 205 | `android/.env.example` | Class 3 | `UNTRACKED` | `False` | 326 | HUMAN_REVIEW | `40742bf84d784f8bda332bad3893b5937b9db68c438bebafdb4da16a29b98f22` |
| 206 | `android/.gitignore` | Class 3 | `UNTRACKED` | `False` | 440 | HUMAN_REVIEW | `5936b94a73a28b6735de672b54c2c058a33c9ae1edb62d87d6a4418e14447805` |
| 207 | `android/App.js` | Class 3 | `UNTRACKED` | `False` | 352 | HUMAN_REVIEW | `8f5eaff00c227ed9e697fafc0ca0e50a79f265bf5eccb29e4f6218b23554cc8d` |
| 208 | `android/LICENSE` | Class 3 | `UNTRACKED` | `False` | 1,106 | HUMAN_REVIEW | `fb3ca4a837f5779e83cef89b78253a8949cfb9429c340309f62d0465ec6610b4` |
| 209 | `android/README_ANDROID.md` | Class 3 | `UNTRACKED` | `False` | 9,384 | HUMAN_REVIEW | `9775cf245c5a320f58ed9aca0b36dceae13b589b581a84119c72e244f7e9d4ba` |
| 210 | `android/app.json` | Class 3 | `UNTRACKED` | `False` | 785 | HUMAN_REVIEW | `1500d23c162914abbcd8c3377cf1401c9e26d6fc0c1d0045f2a43febe891b8dc` |
| 211 | `android/assets/android-icon-background.png` | Class 3 | `UNTRACKED` | `False` | 17,549 | HUMAN_REVIEW | `fb139c2dee362ebf2070e23b96da6fc0d43f8492de38b8af1fd7223e19b5861d` |
| 212 | `android/assets/android-icon-foreground.png` | Class 3 | `UNTRACKED` | `False` | 78,796 | HUMAN_REVIEW | `9e3d0315a33c6799de601dd34cd8bf8cc3a8d16f3bf75592baec2ceb7240b391` |
| 213 | `android/assets/android-icon-monochrome.png` | Class 3 | `UNTRACKED` | `False` | 4,140 | HUMAN_REVIEW | `6371fc2c12e33ad2215a86c281db3d682a81bebe7c957a842c13b8bf00cceb83` |
| 214 | `android/assets/favicon.png` | Class 3 | `UNTRACKED` | `False` | 1,129 | HUMAN_REVIEW | `a4e030697a7571b3e95d31860e4da55d2f98e5e861e2b55e414f45a8556828ba` |
| 215 | `android/assets/icon.png` | Class 3 | `UNTRACKED` | `False` | 393,493 | HUMAN_REVIEW | `119462bb78eb240a65c869fc067ee599639b3cb5a41953f25c07b17d2a8c7e0f` |
| 216 | `android/assets/splash-icon.png` | Class 3 | `UNTRACKED` | `False` | 17,547 | HUMAN_REVIEW | `5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8` |
| 217 | `android/eas.json` | Class 3 | `UNTRACKED` | `False` | 398 | HUMAN_REVIEW | `79053b5a130f21ebdfff9b8823057045dc4b12ea50c583aec254bb86f9d39181` |
| 218 | `android/index.js` | Class 3 | `UNTRACKED` | `False` | 307 | HUMAN_REVIEW | `5c157f4d44972d9c84415e1e4bda595b3abcd8cf733f8a9cd20935bec3eccc42` |
| 219 | `android/package-lock.json` | Class 3 | `UNTRACKED` | `False` | 211,699 | HUMAN_REVIEW | `49ec4dc244a39e35e32a74c01fa7b4c1c99b3efa2a6aea3cff40a1a186541ace` |
| 220 | `android/package.json` | Class 3 | `UNTRACKED` | `False` | 1,058 | HUMAN_REVIEW | `fa98e32c8c8af27b57a428d8268ebe76de485513b6571a4072a3d46d7a4f2dc9` |
| 221 | `android/src/__tests__/api_service.test.mjs` | Class 3 | `UNTRACKED` | `False` | 9,302 | HUMAN_REVIEW | `6f48560b201650288083f5ad123334d193d719e86f05effbf11fb7b605cdeefe` |
| 222 | `android/src/components/ChatBubble.jsx` | Class 3 | `UNTRACKED` | `False` | 6,110 | HUMAN_REVIEW | `e7220295852ac1384594759f2482b050b69c41e68c351efcd44fb788d2e734d7` |
| 223 | `android/src/components/ConnectionModal.jsx` | Class 3 | `UNTRACKED` | `False` | 14,891 | HUMAN_REVIEW | `802e99c1586d4b09ff397d885fb2e8a9063e752914728830233ab5f430b3deff` |
| 224 | `android/src/components/Header.jsx` | Class 3 | `UNTRACKED` | `False` | 4,481 | HUMAN_REVIEW | `42ce58794a58c46e1d36572101111d5458496de5bb64496641672b2656c08368` |
| 225 | `android/src/components/HotelCard.jsx` | Class 3 | `UNTRACKED` | `False` | 4,081 | HUMAN_REVIEW | `a265c298f02473b4ec3ec9a5fd5ffc0d7bef27bea5f950e822cce7a6f8139e96` |
| 226 | `android/src/components/Icons.jsx` | Class 3 | `UNTRACKED` | `False` | 16,676 | HUMAN_REVIEW | `c430e51909bd888eeb7e0e18e1f651db9a44d141387846e24068bb10fc683910` |
| 227 | `android/src/components/MarkdownView.jsx` | Class 3 | `UNTRACKED` | `False` | 12,047 | HUMAN_REVIEW | `48a17d24bef786d03bdbed51ceb881c5385bae0104bf79e10d0ef035ec83bd88` |
| 228 | `android/src/components/MessageComposer.jsx` | Class 3 | `UNTRACKED` | `False` | 15,152 | HUMAN_REVIEW | `4c274e45afacdb2fe1dbe687010e2d9737d6fec459ce2edf5d6890a1e87c8717` |
| 229 | `android/src/components/StatusBanner.jsx` | Class 3 | `UNTRACKED` | `False` | 3,271 | HUMAN_REVIEW | `c03ae111f20e06057f790d032916d6c05fefb4e0a12b68887fb450206b26616d` |
| 230 | `android/src/components/TourismCard.jsx` | Class 3 | `UNTRACKED` | `False` | 4,937 | HUMAN_REVIEW | `87edebaf4e701eae87b03aa4f762634a6ffa2dd5ac731f92bb34b32af7cf9c93` |
| 231 | `android/src/components/TransportCard.jsx` | Class 3 | `UNTRACKED` | `False` | 7,300 | HUMAN_REVIEW | `888c135fdd912eebcefb52c6c687be07af2f280159b0dc944918580230b50986` |
| 232 | `android/src/components/WeatherCard.jsx` | Class 3 | `UNTRACKED` | `False` | 5,004 | HUMAN_REVIEW | `eda980d14604e6c21450360bf2b63dd74f396c08d7d2ab846d19674e6cbcead7` |
| 233 | `android/src/components/YatraLogo.jsx` | Class 3 | `UNTRACKED` | `False` | 1,629 | HUMAN_REVIEW | `b1e595eed72d673fe99f6c8c2a62dea20bc2efe76ae163579a8c32c2a6dbad27` |
| 234 | `android/src/navigation/AppNavigator.jsx` | Class 3 | `UNTRACKED` | `False` | 5,405 | HUMAN_REVIEW | `f74d4d3ee02ecf68ec4bda09b559523d295a8bccd61cfc6fd34aa64580ec723c` |
| 235 | `android/src/screens/AccommodationScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 7,275 | HUMAN_REVIEW | `112e318ad76b899c4f93d6539dd62824c02595b7f2d99ae735f6b2aebccb5c4f` |
| 236 | `android/src/screens/AuthScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 14,593 | HUMAN_REVIEW | `0e35b250c5b92944c3faea4e579aabcb10f4908a65ef0121c0cf6df09a8241d8` |
| 237 | `android/src/screens/BookingScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 26,104 | HUMAN_REVIEW | `a01be3b52451db83d5e88e55739d3a498405ceaf762394ea9c75fe316dd73cf7` |
| 238 | `android/src/screens/ChatScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 8,060 | HUMAN_REVIEW | `c3e86d77efbe537c62c524e5602e3a44e437e7bb5f469080f9b64a593359f457` |
| 239 | `android/src/screens/HistoryScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 6,933 | HUMAN_REVIEW | `58b7bf2f1bc15ec1f74cefaa048bb503826cb963b0a7de6a384daa996ac40212` |
| 240 | `android/src/screens/SettingsScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 18,447 | HUMAN_REVIEW | `25f6c168e5eaa8fa8c81212144c963b2358138b1aecce63bc27a66395b10fbf6` |
| 241 | `android/src/screens/SplashScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 4,977 | HUMAN_REVIEW | `db522d83482b7753096e808d1e0dec8f0acf72bfdb4f44e628d0418f611eff2a` |
| 242 | `android/src/screens/TourismScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 9,071 | HUMAN_REVIEW | `23b513bbcfd561cac75c7d7e2089ac1c6153a910ea57d50a309129d7cb73cbfb` |
| 243 | `android/src/screens/TransportScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 8,585 | HUMAN_REVIEW | `180dd0e45f02bea30ff5f4736d921ff370281f1033e903bb683833dc6293a543` |
| 244 | `android/src/screens/WeatherScreen.jsx` | Class 3 | `UNTRACKED` | `False` | 5,911 | HUMAN_REVIEW | `942f1b0ec7ea8f287c6434e87ff49b89c77b3f3c9cb12cd18943c13c76efba4a` |
| 245 | `android/src/services/api.js` | Class 3 | `UNTRACKED` | `False` | 15,462 | HUMAN_REVIEW | `35fb504dde3a83be9d327022d22e1c38b4aa81a3d56a3844f6e136a380da9f64` |
| 246 | `android/src/theme/colors.js` | Class 3 | `UNTRACKED` | `False` | 1,127 | HUMAN_REVIEW | `e183f3a41f87660c303c6b99f8678df38a25a91eb66321c4a83fffee749681ff` |
| 247 | `android/src/theme/spacing.js` | Class 3 | `UNTRACKED` | `False` | 720 | HUMAN_REVIEW | `d643a789bffc5a65b1644721aa3c9d379fc8f283fe0860e4b3dc317d362a8b9c` |
| 248 | `android/src/utils/markdownParser.js` | Class 3 | `UNTRACKED` | `False` | 5,962 | HUMAN_REVIEW | `42077b4ea8ff3a3d07e427e7e210c2dedd9193523492f322fd9dbbeeffa65727` |
| 249 | `android/src/utils/storage.js` | Class 3 | `UNTRACKED` | `False` | 4,345 | HUMAN_REVIEW | `5611d760463f7a9808395a0289ed81c4a1560825c52f4db1ff505dd42a20abf8` |
| 250 | `android/src/utils/urlValidator.js` | Class 3 | `UNTRACKED` | `False` | 6,313 | HUMAN_REVIEW | `006a6acaab394fad45ef70f118b872d1cff09165b385d577c563202fc1834d8d` |
| 251 | `.dockerignore` | Class 4 | `UNTRACKED` | `False` | 1,124 | YES | `03c85f85f93b2601696b73446e61c883858f154a2f07ee71b6d2031ab82de271` |
| 252 | `.env.example` | Class 4 | `MODIFIED` | `True` | 4,372 | YES | `a3a8e67db9ae697416dd4f09552b8413dd8a61726becf470ce21cef20e824665` |
| 253 | `.env.production.example` | Class 4 | `UNTRACKED` | `False` | 3,042 | YES | `22d737061de19d6e4e1d74c80871a83224a6b725fa7651a842d946cfb4c59063` |
| 254 | `.gitignore` | Class 4 | `MODIFIED` | `True` | 1,229 | YES | `62d0a90b123e271f35b536c15e279192c738851d6bacfbf6878b43b130347f66` |
| 255 | `Dockerfile` | Class 4 | `UNTRACKED` | `False` | 1,462 | YES | `f096fd9a0bb89783889b0f8f408585b347a572ead772301687fe57510ca4acd1` |
| 256 | `requirements.txt` | Class 4 | `MODIFIED` | `True` | 703 | YES | `781a0faddb03cd3d3445507fc3994bd952f215c467083cb23cff9afbdeb3b654` |
| 257 | `README.md` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 3,218 | YES | `15c530e85dbcb3b5caab77def256fa75c640d267b069b3a0580795e9a0301750` |
| 258 | `docs/PHASE_11_2_1_ALTERNATIVE_HOSTING_INVESTIGATION.md` | Class 5 | `UNTRACKED` | `False` | 35,731 | YES | `d20a5e12de768efd32d6ed36957479d74415c1d09ba19d562e91ae66a9901af4` |
| 259 | `docs/PHASE_11_2_HOSTING_FEASIBILITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 26,917 | YES | `b1ecd6e81833bbbc97c6c997c5b0d538e8a4e8c81bba1dae42e17cc772566214` |
| 260 | `docs/PHASE_12_0_1_1_FINAL_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 11,603 | YES | `749fd0d9be8640a94906e90dea8b763c1a652524296dff6989653c88c24dcf5a` |
| 261 | `docs/PHASE_12_0_1_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 16,709 | YES | `6a54655baa715cbf94dc99eabcbc3e48f354f3a308090c3be10b1cf30374eef5` |
| 262 | `docs/PHASE_12_1_CLOUDFLARE_PAGES_DEPLOYMENT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 10,453 | YES | `2f4a22ea6c40aa711094d5949873c76ec5393f9a9a691728464773d6dafb50a4` |
| 263 | `docs/PHASE_12_2_1_SECURITY_AUDIT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 18,195 | YES | `28ea905366ea07bf1800da973a04d3f3f095186ee92f39763c3e3fd0041a342b` |
| 264 | `docs/PHASE_12_2_2_PUBLIC_BROWSER_ACCEPTANCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 12,928 | YES | `7e9e455567fb19385a6a12222a106f047f6ca117772a510a1f48b4d16f28b8cc` |
| 265 | `docs/PHASE_12_2_BACKEND_CONNECTIVITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,746 | YES | `4f55b84e15af4839b8801f77a24225c31b49d36108dedf5a92007753659582a9` |
| 266 | `docs/PHASE_12_WEB_DEPLOYMENT_PREPARATION.md` | Class 5 | `UNTRACKED` | `False` | 18,966 | YES | `584e62e631ec11135c9b479c0e537c57b69ab8d4e6184d32e5df23fb605f07a2` |
| 267 | `docs/PHASE_13_1_ANDROID_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 16,816 | YES | `b4ea9de5227520976d69c4b9852eec2f9964535c1bccbecf5c82af2b8796dc14` |
| 268 | `docs/PHASE_13_2_ANDROID_DEVICE_VALIDATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,743 | YES | `c83f0caa69baccb9222999c747a4d2691badc2cd94b99c35726c4217d41ef23a` |
| 269 | `docs/PHASE_13_3_CONVERSATIONAL_INTELLIGENCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,090 | YES | `256e84a5451ba909c8840592504f0b7a76ea955b65d6e487a9432fd2d9acdb48` |
| 270 | `docs/PHASE_13_ANDROID_APPLICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 14,842 | YES | `a93a79fbcf8ce3982dc47f1ed46147e3c4b016b192656f1a0c90530965d625b7` |
| 271 | `docs/PHASE_14_1_AUDIT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,088 | YES | `897cd64ed61464eae11d2b56a25fda36e91e4fc4615af594cae6970c5a0f7f96` |
| 272 | `docs/PHASE_14_2_UNIVERSAL_ORIGINS_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,902 | YES | `527bd4b60fc6a81b4d560e901b043b272a2149e1fea1ba65d15aa8d3bbcd718e` |
| 273 | `docs/PHASE_14_3_UNIFIED_INTELLIGENCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 15,331 | YES | `10de8136a7cbf1f7d2603421be47952fb0103768dd851268981492e1138d6ef3` |
| 274 | `docs/PHASE_14_4_2_GEOGRAPHIC_DATA_QUALITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 26,398 | YES | `7719bc49274374a269db83516a489ce4c2b2cbe7773d8dce414ff418f4f16b30` |
| 275 | `docs/PHASE_14_4_3_TRANSPORT_DATASET_EXPANSION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,490 | YES | `b7d2e555a7652af88953c4f7e7fb484c2820beae939eddc0386ca2336bd3b53b` |
| 276 | `docs/PHASE_14_4_4_INDEPENDENT_TRANSPORT_DATASET_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 26,684 | YES | `9c4eb8c9a5f6d868ce031c2e091c29ef7a9c1036dff4d95acab0ed3f6d9bef8a` |
| 277 | `docs/PHASE_14_4_ACCEPTANCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 25,381 | YES | `ad453b5a7041e0b3f75bcf3521b71edfe0defce6e55423f7fa97ebacf9be6c87` |
| 278 | `docs/PHASE_14_5_FINAL_UX_AND_CROSS_PLATFORM_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 12,917 | YES | `3b6e97ffeabe17f34d4661b033b3438879fc4ed89da5c959e5350e2726084e1e` |
| 279 | `docs/PHASE_14_6_DATA_INTEGRITY_AND_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 23,214 | YES | `f34993f517d8afbf9320d482a5e69b2a49cd8baa84b3782d3e875d23cb62a9a5` |
| 280 | `docs/PHASE_14_7_CROSS_PLATFORM_E2E_ACCEPTANCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,882 | YES | `ce8cb4ba15e257ed54200bad74e2059764fce78690229d932cf309771b1e39a9` |
| 281 | `docs/PHASE_14_8_FINAL_RELEASE_AND_HANDOVER_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 25,305 | YES | `05ff78c6b824931001dcd127161c59c8a86d38f2f4105c02ff4ee2ed0eefe554` |
| 282 | `docs/PHASE_14_9_FINAL_DOCUMENTATION_RECONCILIATION.md` | Class 5 | `UNTRACKED` | `False` | 18,180 | YES | `eb52d73ae1890a4361d4e1bf47ea0b158120ce5a21aa5e8265384094921f702c` |
| 283 | `docs/PHASE_14_CONVERSATIONAL_EXPERIENCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 16,615 | YES | `01183c642e71dcefa4bd51cbec7c788ae40b94ff5218a475232d6839c0b89ab2` |
| 284 | `docs/PHASE_14_LATENCY_OPTIMIZATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 10,962 | YES | `7a514e8596cb2b639256df5bdb1fb57c346a755c7142e11099261ceff156407a` |
| 285 | `docs/PHASE_15_0_1_VOICE_VERIFICATION_AND_ANDROID_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 16,583 | YES | `0b75d99d3a7236a9258d78ef852ccb53bc5fbe67b6df690781f42dc91eadda7b` |
| 286 | `docs/PHASE_15_0_ANDROID_PHYSICAL_DEVICE_ACCEPTANCE.md` | Class 5 | `UNTRACKED` | `False` | 16,263 | YES | `99df724baa1381adcca4b51c20a06808f68e234d80fe6b0fd0d435e389494c18` |
| 287 | `docs/PHASE_15_0_VOICE_INPUT_AUDIT_AND_IMPLEMENTATION.md` | Class 5 | `UNTRACKED` | `False` | 7,594 | YES | `accc4b331c17c7198f51cc4ad7b8a40fa451288c6a1a1eda9c670ce79c6a5e99` |
| 288 | `docs/PHASE_15_1_1_EAS_DEPENDENCY_AND_LOCKFILE_REPAIR.md` | Class 5 | `UNTRACKED` | `False` | 9,038 | YES | `58f6f740407ca77c6aa86544a5290832b6c8e022bbcdbd25c611ac0d55ad023a` |
| 289 | `docs/PHASE_15_1_ANDROID_APK_RELEASE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,531 | YES | `37bccdd6a9e3d755ce48ec5b3e185f8c6a622df30bbafa10384b51202ae29b01` |
| 290 | `docs/PHASE_15_2_1_BACKEND_DEPLOYMENT_READINESS_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 18,539 | YES | `36f5e37ea6806aa8c1d95e132c78ddbb977e612ef4d5c9465b206fab4f2d60fd` |
| 291 | `docs/PHASE_15_2_3_MONGODB_PERSISTENCE_AND_DEPLOYMENT_GATE.md` | Class 5 | `UNTRACKED` | `False` | 9,882 | YES | `be963cbe06c93202dd4db4d7b342226e7121a09e0ff9c1436da08682354553e5` |
| 292 | `docs/PHASE_15_2_4_CLOUD_DEPLOYMENT_SAFETY_CORRECTIONS.md` | Class 5 | `UNTRACKED` | `False` | 8,971 | YES | `a99a08f1c75b9acc3a0785d1919434779231bf9458241dff8d0f2a086c0efec5` |
| 293 | `docs/PHASE_15_2_BACKEND_HOSTING_AND_NETWORK_INDEPENDENCE.md` | Class 5 | `UNTRACKED` | `False` | 14,187 | YES | `904e7eb21902e6a31ed747f5249e0e20ae1ab1cb63ac11a238204cd5594271a8` |
| 294 | `docs/PHASE_15_3_1_ELIGIBILITY_AND_DEPLOYMENT_SAFETY_GATE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 8,865 | YES | `be892c8c0934ce2c050c58b21febe95c3eb2c3815e3baf0060cbc44a5d26cf7e` |
| 295 | `docs/PHASE_15_3_2_NO_PAYMENT_HOSTING_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 15,062 | YES | `b00528afb2bd9cfadcd32fa3d9974d62fb137d7e78d342b962374ab653847017` |
| 296 | `docs/PHASE_15_3_HUGGINGFACE_DEPLOYMENT_PLAN.md` | Class 5 | `UNTRACKED` | `False` | 10,493 | YES | `de7ee3ba5d671a13ec0c834957487304344b3ce50312ebe4ccf094d008a22e58` |
| 297 | `docs/PHASE_15_4_QUICK_TUNNEL_DEPLOYMENT_AND_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 9,699 | YES | `98c036e00463bc15788de5b3bbd3a932b86c1d5cd077b8e35da15ac27c39cc8f` |
| 298 | `docs/PHASE_15_5_1_ANDROID_MARKDOWN_TABLE_RENDERING_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 8,948 | YES | `8eb045601daf3676ddfa431446e17036bd7da30599f0f96612c1fbd988d5be65` |
| 299 | `docs/PHASE_15_5_2_PHYSICAL_ANDROID_TABLE_ACCEPTANCE_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 12,035 | YES | `66495f5289f32eaef223b592f4c781e886c8977d9d87fcd393aa4da953c9aab4` |
| 300 | `docs/PHASE_15_5_3_EXPO_DOCTOR_BUILD_BLOCKER_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 11,659 | YES | `c96fa6a3db59f1038da1205a7c52c48a851d62a3d9a4891b69ce6d4c08cd28ee` |
| 301 | `docs/PHASE_16_0_1_SAFE_GIT_AND_DEPLOYMENT_SNAPSHOT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,717 | YES | `cda8e4b3724c2cf52a0e0a31bfb1cda50931495b0cb0256eeb9f958ea486015c` |
| 302 | `docs/PHASE_16_0_2_10_FINAL_MANIFEST_RECONCILIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 34,421 | YES | `495d569b2440a81aa2a80b238b489138ce44c33c487404e6e052aa07bd305b9a` |
| 303 | `docs/PHASE_16_0_2_1_FINAL_DEPLOYMENT_MANIFEST_RECONCILIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 28,535 | YES | `67ef4ec3b80912c2a4a7216c155ec6b76a8fcc52a107a0aa1d40e895bc2fcff5` |
| 304 | `docs/PHASE_16_0_2_2_FINAL_INTEGRITY_AND_PRODUCTION_COMMAND_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 26,727 | YES | `8e405b3f38ac52704abd03e4c0e2c107ac4648b77875fec6f62b30cde1cf0671` |
| 305 | `docs/PHASE_16_0_2_3_FINAL_PRODUCTION_BEHAVIOR_AND_DATA_SAFETY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 15,132 | YES | `fe7b2c4b92f6fa69a7eb73a307dfe1a463b2ed48b14637b76387e2abebf7129e` |
| 306 | `docs/PHASE_16_0_2_4_DEPLOYMENT_SNAPSHOT_FINAL_RECONCILIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 16,385 | YES | `c5686d64002146d91faef39bf813b9e00d2d1384cb0eb1b60013f8f597219625` |
| 307 | `docs/PHASE_16_0_2_5_FINAL_DEPLOYMENT_MANIFEST_AND_MONGODB_EVIDENCE_RECONCILIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 37,717 | YES | `11a581d85c10cbee840e4b0d5f20e564fc6ccd010e89458cd514f69a083dfe68` |
| 308 | `docs/PHASE_16_0_2_6_FINAL_RENDER_DEPLOYMENT_SNAPSHOT_APPROVAL_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 44,536 | YES | `8711960f9320cbcc4508cccd75596d1620925db107a72bd5af7b92099a9bfc78` |
| 309 | `docs/PHASE_16_0_2_7_FINAL_GIT_HEAD_AND_DEPLOYMENT_MANIFEST_RECONCILIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 36,317 | YES | `c2cfc2a0902f9eb62a86ae4e6a17bf97b3446ada9194e0e796eeb1a4c4bd6dc5` |
| 310 | `docs/PHASE_16_0_2_8_FINAL_AIRTABLE_IMPORT_AND_MANIFEST_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 35,598 | YES | `55944d9599d1a0fe84753905975ef45448a5c8a8765ec7c80e57f65ac70fa489` |
| 311 | `docs/PHASE_16_0_2_9_FINAL_RENDER_SNAPSHOT_CLASSIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 32,998 | YES | `b258d0f2796085d9a9597485670cd9c171392955f9e54efb1e0ec9cef527c590` |
| 312 | `docs/PHASE_16_0_2_DEPLOYMENT_SNAPSHOT_INTEGRITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 20,107 | YES | `5da5c6b9d44f0a45dda4e76f981f19dce2c7f4489d44dccc7c18b4f2018bf48d` |
| 313 | `docs/PHASE_16_0_RENDER_FREE_DEPLOYMENT_READINESS_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 10,519 | YES | `810837c026b17bff80266b1447efe358d65c32fa55490cb7e97d93196d5f4607` |
| 314 | `docs/phase12_2_2_acceptance_results.json` | Class 5 | `UNTRACKED` | `False` | 441 | YES | `aefeacc4fd5993318f8623a17656280ce0d8b8120de9be6d8f775eb036e09edc` |
| 315 | `docs/phase5_booking_handoff_desktop.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 166,480 | YES | `f35d47563e531a59972b3f9feebaaa799c3e1c26f455e006fc81cc686138a922` |
| 316 | `docs/phase5_conversation_markdown_desktop.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 89,764 | YES | `409899ab9108623cff0d7a4163a61ad13e1fe30c4971aaf21537c72dd3300746` |
| 317 | `docs/phase5_history_drawer_desktop.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 179,995 | YES | `bbd12eed7d89e2c327b164b26c56e6b83c7b219c8a85626ce9c027e25941c442` |
| 318 | `docs/phase5_mobile_view.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 58,742 | YES | `a407a36ab35a27eb973c0ab24fc3a8831bd0b41a9ef3afcb9ad4fc4b8216f0d7` |
| 319 | `docs/phase5_tablet_view.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 100,463 | YES | `d2931a3a621f8f718f0fb358160104038b0d4b6b9870e4f0402983294dc0d1fc` |
| 320 | `docs/phase5_welcome_screen_desktop.png` | Class 5 | `TRACKED_UNMODIFIED` | `True` | 106,928 | YES | `38593a3ac9c62e99ba4a2b3733ab0801954698f83833368cab5d7f2b6c864ff1` |
| 321 | `docs/screenshots/phase12_2_2_01_security_banner.png` | Class 5 | `UNTRACKED` | `False` | 119,165 | YES | `29027c00ec199e25e43003ccd5db376f439bd9b47a3be8f0d4ecfc930b83bf89` |
| 322 | `docs/screenshots/phase12_2_2_02_connected_badge.png` | Class 5 | `UNTRACKED` | `False` | 106,681 | YES | `0608edc4fc2ae25646c7c08f2b217b05cacbb35b53c78a09fee245ace290c097` |
| 323 | `docs/screenshots/phase12_2_2_03_ai_chat_response.png` | Class 5 | `UNTRACKED` | `False` | 97,102 | YES | `5f9a34a001445df0a5d42345744c2f4601fb5b27c36c2dba4f0908c37e7db5b5` |
| 324 | `docs/screenshots/phase12_2_2_04_tourism_rag.png` | Class 5 | `UNTRACKED` | `False` | 126,685 | YES | `747bce3a9a35cd180ec568d72d6477503d893a8aad1ef869a1ec716f86085c16` |
| 325 | `docs/screenshots/phase12_2_2_05_booking_wizard.png` | Class 5 | `UNTRACKED` | `False` | 136,266 | YES | `14ff41f4cae8d145bb10a68d726c55e7a2ceae904d95bd5fe96a821b17203a4e` |
| 326 | `docs/screenshots/phase12_2_2_06_disconnected_state.png` | Class 5 | `UNTRACKED` | `False` | 118,882 | YES | `c6a881a8bd361e1c5b9d7a471e3c34b076e811462b70f585d58892db199580f2` |
| 327 | `docs/screenshots/phase12_2_2_07_public_pages_dev.png` | Class 5 | `UNTRACKED` | `False` | 111,379 | YES | `7de3c10942a1309e966ebcf2713b9f5005e71acedc42254bdb7f2a512d1f4bc1` |
| 328 | `project_reports/Phase_03/PHASE_3_MIGRATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 16,361 | YES | `89deae2ea94f9eb25a5725fdc50f60dc26caa09996de5b81320a632f4548a2cf` |
| 329 | `project_reports/Phase_04/PHASE_4_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 14,054 | YES | `4c650557c4c13200457418c87eb24404bfc49a24d6f00af4bcb06c488603e717` |
| 330 | `project_reports/Phase_05/PHASE_5_REDESIGN_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,937 | YES | `adf39821c24a9375f5a19e3da8a3b18c050d6f3a1f9119de074c83fa195a5fa1` |
| 331 | `project_reports/Phase_06/PHASE_6_CENTRAL_AGENT_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,167 | YES | `41d7e16d38aa2baaf18b18e2f000e170bb0c72559a2a4a03781c47d137ec1aba` |
| 332 | `project_reports/Phase_06/PHASE_6_FINAL_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 19,654 | YES | `6ab84b3a2aee7aedff7835aa0fc9997a5c5177e02affb70bf4a46b0b60db8f5d` |
| 333 | `project_reports/Phase_07/PHASE_7_1_RAG_RELIABILITY_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 23,209 | YES | `fdf9d600b48b9f5a333038795ba884f6d0736620ac894a1bd4fa3c4d3f2ca1fc` |
| 334 | `project_reports/Phase_07/PHASE_7_FINAL_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 22,018 | YES | `57356c512ad7ee021304ccdb4e0df7d6aaaca0098fbd12dc1afe5eaf93320fb2` |
| 335 | `project_reports/Phase_07/PHASE_7_RAG_KNOWLEDGE_FOUNDATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 20,658 | YES | `b8bbe29a7ad219091451149fdcf02b2d252ad64f6719f7d08bcd26b86e28f7f1` |
| 336 | `project_reports/Phase_08/PHASE_8_1_FINAL_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 15,816 | YES | `9196bbf668f702b4e1c4cae16698aab00c5aa00c35113e2a3fadee7587498ebc` |
| 337 | `project_reports/Phase_08/PHASE_8_1_WEATHER_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,997 | YES | `702ee289e66fe5edef754c5c5b592dfa900ebb01f334cef3fa4a34df751831a4` |
| 338 | `project_reports/Phase_08/PHASE_8_2_FINAL_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 14,270 | YES | `d7c6197151ce3f75c32f7035bba229e71ca48eac6e1eb7911597c6a199565a30` |
| 339 | `project_reports/Phase_08/PHASE_8_2_PROVENANCE_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 18,411 | YES | `9eca698bb441ee2d96d81e73e6ec14ad31c2398f1d244493915c2009579e29cf` |
| 340 | `project_reports/Phase_08/PHASE_8_3_CACHE_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 20,772 | YES | `4a51d14a34fc2a7b935344da9c566f80915fa46deb80a46b1be43c2c55e2f3f0` |
| 341 | `project_reports/Phase_08/PHASE_8_3_INDEPENDENT_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 18,561 | YES | `2cb0aa43e7284d41d453ca5ac359c47833dc3a6c860848369008c2dbdb21ce96` |
| 342 | `project_reports/Phase_08/PHASE_8_4_HYBRID_ORCHESTRATION_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 23,713 | YES | `e74c3f96fdc3b4367ab53d9b8d18fa398033c797b5413a1102cc669f04a3f507` |
| 343 | `project_reports/Phase_08/PHASE_8_4_INDEPENDENT_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 21,191 | YES | `fcf1ca8d3562cf63505a219b376cf8f2e9143eb1d56f1635d99e52c138519ae9` |
| 344 | `project_reports/Phase_08/PHASE_8_5_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 18,370 | YES | `fa2d5f586e0b35def812cf73f8f6a647850f4af9866ed95db394939913ca52e9` |
| 345 | `project_reports/Phase_08/PHASE_8_5_INDEPENDENT_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 25,798 | YES | `3576d3e7695ac060b8a453c9274a408506825f28175d5322172f30360746a0db` |
| 346 | `project_reports/Phase_08/PHASE_8_6_END_TO_END_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 32,989 | YES | `0497ea98439e5790aa53f948d8e34ffb0978dbea42d0fc5d5033bf5d056f1422` |
| 347 | `project_reports/Phase_08/PHASE_8_READ_ONLY_ARCHITECTURE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 34,923 | YES | `1fbf8a409fc56cc949ae0bc0b12adb96cb9ece5105fff20056d0d43baa29971b` |
| 348 | `project_reports/Phase_09/Phase_9.0/PHASE_9_0_LIVE_DATA_SOURCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 30,391 | YES | `17213004030d1f6ea4b496d423f8e6f7d2a10e3f0d92ac1604be1a46fcaa89ff` |
| 349 | `project_reports/Phase_09/Phase_9.1/PHASE_9_1A_AMADEUS_LIVE_CONNECTIVITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 10,449 | YES | `6175c3c13dd6992224ceb57b4c121c482e9ca719d2ac4175f4dd62a7cc97ea14` |
| 350 | `project_reports/Phase_09/Phase_9.1/PHASE_9_1_AMADEUS_HOTEL_FEASIBILITY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,486 | YES | `c723ef381c6986e685c5e8c1424a44344365427f8cf3c20f4f569baf5479b424` |
| 351 | `project_reports/Phase_09/Phase_9.2/PHASE_9_2_KATRA_ACCOMMODATION_INVENTORY_AND_PROVIDER_STRATEGY_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 32,969 | YES | `120447c83a3db682d9b40d9840da222c22e76e0182670df7c45f06b369d3db53` |
| 352 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_1_CLAIM_LEVEL_EVIDENCE_AND_CATALOG_APPROVAL_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 26,052 | YES | `1634e3567a0d5cbbd7740087b12a728270398d1a864cd45f38a7e9eec9d34bb1` |
| 353 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_2_FINAL_CATALOG_EVIDENCE_READINESS_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 24,054 | YES | `f79b14662f2c8ee8bbe5002ace98c396cbeb9b809e62a0877c394a4911f61e4c` |
| 354 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3A_KATRA_PROPERTY_SOURCE_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 25,524 | YES | `9bc700a5a7509d94de78d32dc5c4726141bc220c9512f3a153fa4749a6f28e42` |
| 355 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_1_PRODUCTION_ACCOMMODATION_INTEGRITY_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 21,319 | YES | `9181d590b0208dac60876421019b625a2715bdb89e2d07c6c0104d82af064f3a` |
| 356 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_2_SYNTHETIC_ACCOMMODATION_ISOLATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 19,080 | YES | `c62766eec09958223e28b41214c94ed71cfad2c50164621db23101e1c65ec7d0` |
| 357 | `project_reports/Phase_09/Phase_9.3/PHASE_9_3B_KATRA_ACCOMMODATION_CATALOG_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,155 | YES | `74e1102072484d62e22da8510b90c3e81aa65dcbbd9b4db0b975e1a89ce60745` |
| 358 | `project_reports/Phase_09/Phase_9.4/PHASE_9_4_LIVE_DATA_SOURCE_ROADMAP.md` | Class 5 | `UNTRACKED` | `False` | 41,244 | YES | `6ec2bcd0925a39d1147493ca6e9a5ad03068a9c3eaa338f6688507b11f1ad650` |
| 359 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_1_2_INDEPENDENT_SAFETY_AUDIT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 22,909 | YES | `e839a1cd1c10fdd91fa11a3ad157cc2b7cb24c7c0b009706da4644a5a7c7b2f7` |
| 360 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_1_PROVIDER_SAFETY_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 20,415 | YES | `07f892b9993ece072d378965ce796b563d53a437f3a59f6a4771e16d0206e277` |
| 361 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_1_INDEPENDENT_REMEDIATION_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 24,088 | YES | `528fce9f2f2a5bb90d00a42970758183ccf751ac27b78c04894f1c95f55853ff` |
| 362 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_1_FINAL_PROVIDER_ACCEPTANCE_AUDIT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 20,129 | YES | `64d47718d298759e24a68a18dc03f294b3605967bec2af00a7b13625a8970924` |
| 363 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_2_FINAL_CACHE_AND_REPOSITORY_VERIFICATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 15,468 | YES | `e1c036072f183552e77643077ba477d6b4aa4394e9a18addd7912be45b069b77` |
| 364 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_2_FINAL_PROVIDER_CONSISTENCY_FIX_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 10,779 | YES | `069cdf97da06df5ba554c6a494627d1bbecf185bc885693f8f155b40103a9309` |
| 365 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_2_PROVIDER_PRIVACY_CONCURRENCY_RECOVERY_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,572 | YES | `0b436e64e5e3ee53c70a9a49e07f9da6616e4afdbbd8581311bc56dd45b70f73` |
| 366 | `project_reports/Phase_09/Phase_9.5/PHASE_9_5_PROVIDER_FRAMEWORK_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 19,237 | YES | `c71f72407478029d21c13e2c04c3ea360feb525c987f79ca6aa7ef8f1207f915` |
| 367 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_1_1_SOURCE_EVIDENCE_VALIDATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,173 | YES | `623c1df858a7f1d40d264650a6b75c81e9ed4c85c1e5a5b160fc345d1ca7eff6` |
| 368 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_1_OFFICIAL_SOURCE_FEASIBILITY_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 25,499 | YES | `41cc8dcc0fc4db0d45e0e770c2fac79419f5212c84be20444a77e4be9b9437dd` |
| 369 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_1_EVIDENCE_INTEGRITY_AUDIT_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 24,878 | YES | `389d9c4741feb48eced2b616326b2e5382b79ca6114eaad82a2a1556a0bba9df` |
| 370 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_2_CRITICAL_SAFETY_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,891 | YES | `98f133cb3af96de6d07d10eed59dcac48ac8ff363dfab66c6718018c10f79d51` |
| 371 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_2_FINAL_ACCEPTANCE_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 16,472 | YES | `7425957fc03e030e2da6c699992793196e84bd31666aa95fd35e8c8d34273e4b` |
| 372 | `project_reports/Phase_09/Phase_9.6/PHASE_9_6_2_CURATED_OPERATIONAL_NOTICES_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 21,589 | YES | `cb4890da7093bd4206dc2303476312eded66866228d7f74dea709565c50e65b8` |
| 373 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_1_LIVE_DATA_SOURCE_FEASIBILITY_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 32,920 | YES | `3153e97e3243af7af86a4bc5bd992eeea72c6401360039ce5f0ccd4c6ec5878b` |
| 374 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_2_RAILWAY_ACCOMMODATION_INTELLIGENCE_ASSESSMENT.md` | Class 5 | `UNTRACKED` | `False` | 30,781 | YES | `df6153cb2854c1da87059d6b1017b82f05fd0e3bd55466c93a9a67449ff5ffb1` |
| 375 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_3A_RAILWAY_DATA_INTEGRITY_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 11,296 | YES | `defca85b144c9c0507b0dbb5dbcdf2ab243767c98ce6e3e29e9383530eb88567` |
| 376 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_3_RAILWAY_FOUNDATION_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,320 | YES | `dc964fb02ace5e2d68c06e4cd00f0ec729a537dd6bb4a34dd5591ba194035564` |
| 377 | `project_reports/Phase_09/Phase_9.7/PHASE_9_7_4_RAILRADAR_FEASIBILITY_AUDIT.md` | Class 5 | `UNTRACKED` | `False` | 24,354 | YES | `6567ce7317d84247a830d3fb147c108adef559299cd9449e08963b8d7c64ea9a` |
| 378 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_2_2_FINAL_TRANSPORT_PRESENTATION_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 17,727 | YES | `794eeb4b88d914ca8f6017bc4306f26ce7f18ed8253cee19b663f11e9188ac0b` |
| 379 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_2_TRANSPORT_TRUTHFULNESS_REMEDIATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 15,640 | YES | `e14cc21b302fd08e5f226e6c8714dea61242f7509378766ac210245d269bd441` |
| 380 | `project_reports/Phase_09/Phase_9.8/PHASE_9_8_1_CURATED_BUS_REGISTRY_IMPLEMENTATION_REPORT.md` | Class 5 | `UNTRACKED` | `False` | 13,739 | YES | `95b39d46cb39fe079a4af4ce4000128c7c5fe6b9065bbca0f316501e9cb9c86b` |
| 381 | `project_reports/README.md` | Class 5 | `UNTRACKED` | `False` | 28,161 | YES | `9c4897eb132b371e0963cdabc382065d6f168e06b474b876ff4b84ded21cd6e7` |
| 382 | `tests/__init__.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 0 | YES | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 383 | `tests/test_account_persistence.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 25,262 | YES | `e033a13c10b2bd4747316c28b74aef9961ce06bd6eed1f793027dd92518bdb61` |
| 384 | `tests/test_agent_rpa_integration_week7.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 32,345 | YES | `ef94274775a8ffcf7865dc3e4b1aefdfb591607baacac73aa0c7fd25beee3a28` |
| 385 | `tests/test_android_markdown_table.mjs` | Class 6 | `UNTRACKED` | `False` | 13,404 | YES | `f25c584007c15a4d7ce4085a166e425751ab573904d2b630e9655a8bad39f017` |
| 386 | `tests/test_api_url_validation.mjs` | Class 6 | `UNTRACKED` | `False` | 7,690 | YES | `0c1195ad361560c40a7a4bb9876c5291df9f8d6b53eb47c2360e1cd4f7a0361f` |
| 387 | `tests/test_audit_journey_e_edge_cases.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 9,302 | YES | `27029be0518535d13b8870045270e299774dd4a6de94dc7c186d22f0beb25f71` |
| 388 | `tests/test_booking_auth_security_journey.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 6,371 | YES | `82735fc6cdd4be137bf50edb4c2f0914cc95fe377974b8d4b094700e0ac0aa4f` |
| 389 | `tests/test_booking_lifecycle_audit.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,276 | YES | `e6c5549df91f0ec28db337bb73119125c8d3249b7012f326c409c822fe552fa0` |
| 390 | `tests/test_browser_auth_guest_week9.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 9,449 | YES | `427296b5b9ca6e22fa6e36831fcd3d50417ee6b5aff4b01f999df9ed0710318c` |
| 391 | `tests/test_browser_e2e_journey.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 14,873 | YES | `89e58defaa922f2e79192f754df5f35a63793b83d5de52a0abd9a869007f6b92` |
| 392 | `tests/test_browser_flexible_workflow.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 6,657 | YES | `c1c0163552e4b922e32c7d04ea9729d971d8b4c83e506313c4fa841af540d75b` |
| 393 | `tests/test_browser_my_account_e2e.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 7,547 | YES | `819618344936252fd6181f9442dc6c29984c908d8ae2f5d65a608b1e95d1005c` |
| 394 | `tests/test_budget_engine.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,083 | YES | `491a9d2bdb6fb7433903d2f12c26d7fa2d4864378963458cba3c409a5f7ccfb0` |
| 395 | `tests/test_chat_to_booking_handoff_e2e.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 9,035 | YES | `b604a3d915209850cef7bd2f6dc8af5321c51036f075ca43918b0cee8590ab26` |
| 396 | `tests/test_compact_conversational_ux.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 11,667 | YES | `120a33db5c39cadda8c31981526873af6c9c2bb5e0bee61868c34621e2e11f4c` |
| 397 | `tests/test_cors_policy.py` | Class 6 | `UNTRACKED` | `False` | 8,289 | YES | `3ea435800318ebc7562eb7f8080d4d43afda0ab7f9f5fcd322f09aee3b0c0e7f` |
| 398 | `tests/test_e2e_orchestrator_conversation.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 8,629 | YES | `07b92164fd749fb1882e9c29d4488b8bd01a634d62b4d2476d55eaac09efd374` |
| 399 | `tests/test_e2e_system_integration_week9.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 25,219 | YES | `d215f758b050a55dca69fadbe519d66d944a8ceede7ccae7286566d209a1bd36` |
| 400 | `tests/test_fastapi_endpoints.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 5,600 | YES | `0f3f030e6b8826ed4e95194c3a154054b76b7e08f6b9cdc664c414fcedab9105` |
| 401 | `tests/test_feasibility_ui_browser.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 7,502 | YES | `224e245aafb4f0db3db747e57e8f82b3739aeb2b4103bf84c355ee17b7a729c1` |
| 402 | `tests/test_featured_destinations_browser.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 8,357 | YES | `2eeec7a2d694fbf8ba7a087819fb55f6ae1288a80f3d4d2e35b689eefe8dd3b8` |
| 403 | `tests/test_flexible_booking_workflow.py` | Class 6 | `MODIFIED` | `True` | 21,501 | YES | `8c1eb049f619480244ec0e0c2b257924ffce822f8798f43a3acb7c28af98e162` |
| 404 | `tests/test_groq.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 680 | YES | `dfb141c44f3f7e7f8c1386db303968711b13279c074c344b6d2411e787d97bed` |
| 405 | `tests/test_intent_routing.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 12,936 | YES | `2299743dc2337c012363f1c461345d4a0e7a50eb9bf66ec531308cc01e1d25cc` |
| 406 | `tests/test_langchain_tools.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 6,534 | YES | `f86fc25c5b3a32919a5aba1462c489f616a0934d76b87c6c37d869ecd4d7ccfa` |
| 407 | `tests/test_mentor_requirements.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 8,727 | YES | `8dfc78be1247a27a14aebab5e8bcb0c2398d63d512735e64b3255a8d905fb233` |
| 408 | `tests/test_mongodb_coordinator_integration.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 14,530 | YES | `d9fe6542e023d220827cdbfde3ed7213fc8931f007e4213e00c8407d67252b85` |
| 409 | `tests/test_mongodb_load_week9.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,574 | YES | `3902ef4cfee5a9382a14d6ee2378c8897d4e56ae40672793378927d5c367332b` |
| 410 | `tests/test_my_account_booking_persistence.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 18,038 | YES | `6bc140366ff4f7a304414ceedab24d126c83703b34f59299e8dc9f3c2933da41` |
| 411 | `tests/test_orchestrator.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 20,967 | YES | `704b8a17b61eb5eb37cebcb26b4f5a31ba379cec952e712d64a9785fb4515ed8` |
| 412 | `tests/test_origins.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 2,707 | YES | `80e982a288675fc8a98f1ae9ef5902aa667fdb40a8913c43c6877d70af510a64` |
| 413 | `tests/test_passwordless_auth_week9.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 29,835 | YES | `2d8ed966066709abdf7130ab592eefbf856b4a00c8f9a404895705b49ffbe64f` |
| 414 | `tests/test_phase11_1_deployment_remediation.py` | Class 6 | `UNTRACKED` | `False` | 14,013 | YES | `6227ea0012c2981198277b4f7ff9d57d45ca8cc705ccd5734e809e3341b63dd2` |
| 415 | `tests/test_phase12_production_readiness.py` | Class 6 | `UNTRACKED` | `False` | 17,914 | YES | `bc33a474906072db8ab8b50eeab4ff1d7865726bbdf9c13e48d5e07b78b12631` |
| 416 | `tests/test_phase13_3_conversational_intelligence.py` | Class 6 | `UNTRACKED` | `False` | 14,808 | YES | `cbb66de942a0afb5c23b13557ca4929284d0a24383ea9a7fb9420aa10804e93c` |
| 417 | `tests/test_phase14_2_universal_origins.py` | Class 6 | `UNTRACKED` | `False` | 17,378 | YES | `ac8eb9f263a3a447ff62dfd359d935c9cea2a20d915c2a891577ba0b9d2b4028` |
| 418 | `tests/test_phase14_3_unified_intelligence.py` | Class 6 | `UNTRACKED` | `False` | 23,016 | YES | `9f4172a5a4c984aa064b741d29796a51cee93a4f8735ae145e421d29f72952ef` |
| 419 | `tests/test_phase14_4_2_data_quality.py` | Class 6 | `UNTRACKED` | `False` | 7,952 | YES | `e2015073a9b2401a2265ec74da66a7063ba1976066fd67283c15b88b19bd927f` |
| 420 | `tests/test_phase14_4_3_transport_expansion.py` | Class 6 | `UNTRACKED` | `False` | 15,876 | YES | `4be39ced21fea433761861403b2e3ffe035e32740258c6f721fdf6a33d2d0306` |
| 421 | `tests/test_phase14_4_acceptance.py` | Class 6 | `UNTRACKED` | `False` | 45,915 | YES | `0cb520c8aa76ebe401d7a59304a9954f4e6b21338f14e61cba0e66aea2877326` |
| 422 | `tests/test_phase14_5_final_ux.py` | Class 6 | `UNTRACKED` | `False` | 16,140 | YES | `daad6994fcede92efff3b53c9a49ab52c8b9399f8d664ed896056c6cb6723021` |
| 423 | `tests/test_phase14_6_data_integrity.py` | Class 6 | `UNTRACKED` | `False` | 12,041 | YES | `6e0a462f046681a43dea41dfdcd21a388387e4b9855ad2869863d6d0e2ac01f4` |
| 424 | `tests/test_phase14_conversational_benchmark.py` | Class 6 | `UNTRACKED` | `False` | 35,321 | YES | `67ab9e7ad852f005877254941d406b4c9d5ba467d0d12cdbc4d5694824b4285c` |
| 425 | `tests/test_phase15_2_1_deployment_readiness.py` | Class 6 | `UNTRACKED` | `False` | 5,135 | YES | `2b22a69a86998110af8530540d47d7ed14331a26c37f682c8206a00969b4470e` |
| 426 | `tests/test_phase15_2_3_persistence.py` | Class 6 | `UNTRACKED` | `False` | 24,239 | YES | `c72310af26e5bd3c24f8c2509f993ed0c365f6b03b930672d6ad806cc21dec8a` |
| 427 | `tests/test_phase5_conversational_ui.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,607 | YES | `6e4c706588720edf231fcd15f5cf013cbf4407c8775441ad385d501fc9a36a0d` |
| 428 | `tests/test_phase6_central_agent.py` | Class 6 | `UNTRACKED` | `False` | 23,253 | YES | `625c23fe818106397586c2b08767ff8c53b8d3249db3072e3f97fb977966da1a` |
| 429 | `tests/test_phase7_1_rag_reliability.py` | Class 6 | `UNTRACKED` | `False` | 17,673 | YES | `816fe936ab83f1499230e2db2d65e27898896c1c614ae3fd32bdd8221856ae52` |
| 430 | `tests/test_phase7_rag.py` | Class 6 | `UNTRACKED` | `False` | 26,024 | YES | `89ec94c22b27261fe66f9ae069d325b3c1a755b0239cc9877237b096bd51982a` |
| 431 | `tests/test_phase8_1_weather.py` | Class 6 | `UNTRACKED` | `False` | 27,607 | YES | `3dbcdb35d07c4c638b70e6bae80783bc2c7f58afb8abd3df3cac55559a0d977c` |
| 432 | `tests/test_phase8_2_provenance.py` | Class 6 | `UNTRACKED` | `False` | 28,639 | YES | `90009a1630fd3eddf0d475174557b49d2972e00156c23885ef737b168be8a937` |
| 433 | `tests/test_phase8_3_cache.py` | Class 6 | `UNTRACKED` | `False` | 29,993 | YES | `c1db4bfa060ca1e3816b8624f4f665aef708dd0cfe83f3e129bb8bf319091b76` |
| 434 | `tests/test_phase8_4_hybrid_orchestration.py` | Class 6 | `UNTRACKED` | `False` | 44,267 | YES | `fe4ee079c95d7287fd3857fad2e8f2c1d206858b336f42cf59f84986ad751ae2` |
| 435 | `tests/test_phase8_5_frontend_provenance.py` | Class 6 | `UNTRACKED` | `False` | 21,777 | YES | `d0d27193e24a7ff8e22c5d3dece58d04e4af4a8390a468c7840443a222bcb73c` |
| 436 | `tests/test_phase9_3b_2_isolation.py` | Class 6 | `UNTRACKED` | `False` | 12,966 | YES | `fea2a8274201c05a5625939242fbde841627026d9488db2679988143921263e6` |
| 437 | `tests/test_phase9_3b_catalog.py` | Class 6 | `UNTRACKED` | `False` | 15,757 | YES | `47fcea078a5c33c8e2ea289adbe969d6275611052c7ae0fea3c3742ea7dfc3f6` |
| 438 | `tests/test_phase9_5_1_hardening.py` | Class 6 | `UNTRACKED` | `False` | 24,085 | YES | `349f1dceca87d950a8ce49fa6e5df0b2039fa36d26ff3080d70b3a5274d11437` |
| 439 | `tests/test_phase9_5_2_2_consistency.py` | Class 6 | `UNTRACKED` | `False` | 15,292 | YES | `c99b743508d088b588b66f4322fc9957bae6b4a202d3a3913651b4038319d78c` |
| 440 | `tests/test_phase9_5_2_remediation.py` | Class 6 | `UNTRACKED` | `False` | 26,462 | YES | `de4cdfa98f6ec4b31984fcfec237af79709a26a6d6b83a4b090be96beaba9a0f` |
| 441 | `tests/test_phase9_5_provider_framework.py` | Class 6 | `UNTRACKED` | `False` | 26,803 | YES | `bbf43aaf0950add294352978481188328b4bef03a2fbc1c642a676abd1e81925` |
| 442 | `tests/test_phase9_6_2_curated_notices.py` | Class 6 | `UNTRACKED` | `False` | 41,085 | YES | `e7c22a3af0323f91d220db6ad3e827d182dc722e986d782f30ed35fdb646d9c8` |
| 443 | `tests/test_phase9_7_3_railway_foundation.py` | Class 6 | `UNTRACKED` | `False` | 15,329 | YES | `55f3c126e9141959fd155a6a20ae22e6425e816e7cb10d01f9cc50d1dcb1b246` |
| 444 | `tests/test_phase9_7_3a_railway_remediation.py` | Class 6 | `UNTRACKED` | `False` | 14,458 | YES | `590f3653b0652a7ddc491b48e38acf8e10fa93f24747d16bbe33aa599cdeaedc` |
| 445 | `tests/test_phase9_8_1_2_2_presentation.py` | Class 6 | `UNTRACKED` | `False` | 10,968 | YES | `98f45ce879a5a52811dcb20be69acd5aa08e1beb172ddf352fa66ee2034bc338` |
| 446 | `tests/test_phase9_8_1_2_remediation.py` | Class 6 | `UNTRACKED` | `False` | 14,506 | YES | `07e16278016f8f6f39dba49fda2ca7100370bf394cd22db7896769a079e9cc0b` |
| 447 | `tests/test_phase9_8_1_bus_provider.py` | Class 6 | `UNTRACKED` | `False` | 15,902 | YES | `c038843c4fe3589e3328f838bae3e2bd3a08d1c00ba3d48029144bf92a516675` |
| 448 | `tests/test_phase9_8_2_flight_registry.py` | Class 6 | `UNTRACKED` | `False` | 36,847 | YES | `a8ea52292a17b37e7661036a217baa1795f4e246cf6ea143f1a569cd5e037ed8` |
| 449 | `tests/test_phase9_8_3_1_transport_dispatch.py` | Class 6 | `UNTRACKED` | `False` | 32,163 | YES | `3f9a118761b759eb259c3a334b190596ff11fe8ed2b6cfa504862b24282fc478` |
| 450 | `tests/test_phase_2b_conversational_history.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 10,340 | YES | `cbf221aa810e0cbc9ccf4a068f5cf9289dba9d848ee96ceb5b3c2c936977dd19` |
| 451 | `tests/test_phase_2d_history_reliability.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 10,826 | YES | `22fdd7549660ca51da365406be856584b513bb67c36a92832d6d9c0fc4a0338e` |
| 452 | `tests/test_phase_2f_frontend_history.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 12,403 | YES | `48d961beee5853c45b0e1471f5be955c46aeeeca7e9f71c53820b6bcd5600e8b` |
| 453 | `tests/test_phase_4a_navigation_regression.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 10,243 | YES | `3f9c40d205302d836c0956c9a5c6dea32a159a9ac0b61b1182be9db6b7438f85` |
| 454 | `tests/test_phase_c.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 7,648 | YES | `4d831673e6e1f7a4aef83c2c12d24ea2309c97914468e26c71f107968fecf92d` |
| 455 | `tests/test_phase_d.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 8,067 | YES | `bc57f8fe08d1dd0c2822f4e8fae3ab0a4ef575a5e2e6a076be7dc88e86aa8888` |
| 456 | `tests/test_phase_e.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 9,417 | YES | `b1f7d78e373f3d739931676e0ed838900bfeea9add89831d9bf597f05fffde9d` |
| 457 | `tests/test_phase_f.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 7,934 | YES | `90f0e4c642047d1c788b1e9d0451408e149b03db6c445fb80fc3f8eb34cf88bd` |
| 458 | `tests/test_phase_g.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 16,443 | YES | `162f9507847ae99871ee901b89f53c8cd1877f5616f8d69aae9617239ce08fcd` |
| 459 | `tests/test_planning_mode_choice_browser.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,283 | YES | `e19cde4aaa455aec53fcc4f68351d253b302fa429639d59fded5fe06f9eb9378` |
| 460 | `tests/test_playwright_week4.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 7,036 | YES | `dc13ed8c4e86a81bd5229be19938ebd71ad8c0f6ad46e8ae79c31935161df6bb` |
| 461 | `tests/test_preference_aware_planner.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 23,884 | YES | `1490372556de53f300ea7ae4cc9e23ff10ba29c7a24ea21f49c7c02ee91f4ae6` |
| 462 | `tests/test_realistic_booking_journey.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 26,091 | YES | `c57211e281823bafa934af001988ffaf55fc431d05ef1d69bb734c3a20344e68` |
| 463 | `tests/test_rpa_availability_week5.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 12,809 | YES | `7f7ac9ce258dc7227fe7608142de7ff227dea96701315fd42bb3e25b5f0089ac` |
| 464 | `tests/test_rpa_error_handling_week6.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 21,008 | YES | `808ee7180d9bb165feadb650845be5c9bf39ccb79a76603f92ea0d7796b77c33` |
| 465 | `tests/test_saved_conversation_resumption.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 13,711 | YES | `82de181ac8b867aea83522c783c6b68db790906ab199595971c4974568b74a83` |
| 466 | `tests/test_sequential_booking_journey.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 24,162 | YES | `9f06f96aa07aae6606073de038288016c48a682455337643b820c23269a5c3a5` |
| 467 | `tests/test_server_authorization_security.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 12,646 | YES | `058aa55bb0695eae428f30a488c02db8d461015e8dc113917fb439e4c7f39199` |
| 468 | `tests/test_session_store.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 11,664 | YES | `fcb368d9ac5bd03cde6e451dfcceb0745e297a73d688b957ddd4300ce0648677` |
| 469 | `tests/test_sightseeing_browser_browser.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 12,789 | YES | `a7504aaf32f5af21b45e343fe45abc6c3aa92dd367e7ac885fe941e70ee3fdf0` |
| 470 | `tests/test_tool_calling_accuracy_week9.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 17,989 | YES | `a64e68246ca95275e991fc1f377bf86b33670ba6b9cfd4bed1d570446692b31b` |
| 471 | `tests/test_unified_booking_redesign_e2e.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 16,564 | YES | `08d053dde2b175e3f050cdc90a201f8db2987c9402196290fbf9928c5a637612` |
| 472 | `tests/test_user_controlled_workflow_week8.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 29,289 | YES | `688134516cdb642f467730ec726888e91f32f995be83f4d2845a376ab206d2d0` |
| 473 | `tests/test_visual_itinerary_timeline_browser.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 9,383 | YES | `fdd898ffac017796bbdbcc9c345b00787fd759c1d0f48fe6d381d5a73b5d1fd6` |
| 474 | `tests/test_voice_flow.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 5,502 | YES | `9cd3ba499cc30df5ebbac8814ba2083471eb633f58b18f1709e3a1e1a1fae864` |
| 475 | `tests/test_voice_input_architecture.mjs` | Class 6 | `UNTRACKED` | `False` | 6,027 | YES | `1aef7ab615129647a0715c4eff3f6937c2819a1cbc685a4668fdf3cddf74ccc2` |
| 476 | `tests/test_week10_ethical_compliance.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 24,433 | YES | `96ec42a986515f6056450d5d57f30950d4fc428a7b44ab64930af313a6c856bd` |
| 477 | `tests/test_yatra_prompt.py` | Class 6 | `TRACKED_UNMODIFIED` | `True` | 4,664 | YES | `f063723125cc4bb5f399335f11842de1e50aa23ef7db671478e85dfeadcf1aa3` |
| 478 | `scripts/build_frontend_for_tunnel.ps1` | Class 7 | `UNTRACKED` | `False` | 3,409 | HUMAN_REVIEW | `04ee794054fc3cac028699d6f7d3d23699968998af1f58936086b910d8259750` |
| 479 | `scripts/deploy_frontend_cloudflare.ps1` | Class 7 | `UNTRACKED` | `False` | 3,057 | HUMAN_REVIEW | `61f7a78eb26a15cbdff73570922218f7947dfd076f4b6972ee6d6c5268c0d45e` |
| 480 | `scripts/deploy_huggingface_space.py` | Class 7 | `UNTRACKED` | `False` | 5,841 | HUMAN_REVIEW | `577a95e9eddd3c777337a785940f3cc1a35b0d1002acf725da45b4bb04e85a11` |
| 481 | `scripts/measure_contacts_latency.py` | Class 7 | `UNTRACKED` | `False` | 936 | HUMAN_REVIEW | `7577bc68b53dda53f2ed9935d92f0b8ba314269c255cf5efc4feba327bf607e1` |
| 482 | `scripts/start_backend_production.ps1` | Class 7 | `UNTRACKED` | `False` | 5,900 | HUMAN_REVIEW | `64e1af010b64acaad97850709544c2601b151c214b98b139cde2643652498398` |
| 483 | `scripts/start_quick_tunnel.ps1` | Class 7 | `UNTRACKED` | `False` | 4,379 | HUMAN_REVIEW | `a722642b43b6c6f08f1e6329a086621993e3d6101ee9f932626dd1b9179d0fbf` |
| 484 | `scripts/verify_interactive_playwright.ps1` | Class 7 | `UNTRACKED` | `False` | 553 | HUMAN_REVIEW | `28c37cb5202733eab42cf7b8105f3bcb50309ca975a29bdccb6de8be8e2c4b6e` |
| 485 | `scripts/verify_interactive_playwright.py` | Class 7 | `UNTRACKED` | `False` | 6,745 | HUMAN_REVIEW | `e9508c0c4e85e19d4154d804f41e9a34966b3efe1ed96e30752f85b0c83dd6bc` |
| 486 | `scripts/verify_phase12_2_2_browser_acceptance.py` | Class 7 | `UNTRACKED` | `False` | 15,004 | HUMAN_REVIEW | `79cfa07b1650c58cb0212dfecd61e9cd3decf25c2678427257e67eb6901982e1` |
| 487 | `scripts/verify_phase16_1_1_browser_acceptance.py` | Class 7 | `UNTRACKED` | `False` | 11,589 | HUMAN_REVIEW | `546bcc3a38d07d6f0abc30a1b4a075eaa9b0f562f1b1d3ac142bd3179df488e0` |
| 488 | `scripts/verify_phase16_1_1_source_audit.mjs` | Class 7 | `UNTRACKED` | `False` | 14,305 | HUMAN_REVIEW | `98ee220c38c3a5c4adec2f426172c1db79829e96f903bcbe4509f6a635194252` |
| 489 | `build_dataset.py` | Class 8 | `TRACKED_UNMODIFIED` | `True` | 11,987 | NO | `71c68a48ba29b46f1c049b33e960015b3c42bcab7d52220ff2731b7f7b4a1353` |
| 490 | `data_gen.py` | Class 8 | `TRACKED_UNMODIFIED` | `True` | 1,091 | NO | `93b7f29a4cfadef4869bd29a7685817fab2acabe41110e9fff519033ccf66227` |
| 491 | `langchain_tools.py` | Class 8 | `TRACKED_UNMODIFIED` | `True` | 3,368 | NO | `d36301f78b643d185bb0c03fea1f611e13e70a7ec28119c1da85eb1f7f777d01` |
| 492 | `mongodb_agent.py` | Class 8 | `MODIFIED` | `True` | 8,581 | NO | `5ba02d296d671948c531a2f5e0136ff319cf3f81d00b22c943b0b5e9970d7cb7` |
| 493 | `mongodb_tools.py` | Class 8 | `TRACKED_UNMODIFIED` | `True` | 16,307 | NO | `6c694183bfd5238c72428d225712a7f1da543a0e3c3bcf3cfae9f22448de69c3` |
| 494 | `payment.py` | Class 8 | `MODIFIED` | `True` | 3,546 | NO | `cce2407f9e1dac97c083e660e74595f2ccd84fdfb002b5aea0907b3e3c0dd7a4` |

---

## Task 7 — Reconciliation of All Arithmetic Matrices

Every mathematical partition in this audit is mutually exclusive and completely closed:

### Matrix 1: Full Repository Inventory Partition (494 Files)
$$\text{Tracked Files (210)} + \text{Clean Untracked Files (284)} = 494$$
- **Tracked Files Partition:** 66 Modified Tracked + 144 Unmodified Tracked = 210
- **Untracked Files Partition:** 166 Files in 9 Untracked Dirs + 118 Direct Untracked Files = 284

### Matrix 2: Deployment Manifest Partition (102 Files)
$$\text{Cat A (89)} + \text{Cat B (1)} + \text{Cat C (6)} + \text{Cat D (6)} = 102$$
- **Category A Sub-Partition:** 78 REQUIRED + 9 CONDITIONAL + 2 DEVELOPMENT-ONLY = 89

### Matrix 3: Full Repository 8-Class Partition (494 Files)
$$\begin{aligned}
\text{Class 1 (Backend Runtime)} & : 118 \\
\text{Class 2 (Frontend App)} & : 86 \\
\text{Class 3 (Android App)} & : 46 \\
\text{Class 4 (Repo Config)} & : 6 \\
\text{Class 5 (Documentation)} & : 125 \\
\text{Class 6 (Tests & Fixtures)} & : 96 \\
\text{Class 7 (Dev Scripts)} & : 11 \\
\text{Class 8 (Legacy Excluded)} & : 6 \\
\hline
\mathbf{Total} & : 494
\end{aligned}$$

### Matrix 4: Manifest B Staging Action Partition (494 Files)
$$\text{Staging Candidate YES (430)} + \text{HUMAN\_REVIEW (58)} + \text{Excluded NO (6)} = 494$$

---

## Task 8 — Final Audit Verdict & Safety Commitments

### Final Verdict

## `ACCEPT — READY FOR HUMAN EXACT STAGING APPROVAL`

### Justification
1. **Complete Count Reconciliation:** Every file path and directory count has been independently verified against the live filesystem and Git index with zero discrepancies.
2. **Individual Enumeration:** All 494 files are individually listed with full relative paths, exact sizes, status, and un-truncated 64-character SHA-256 hashes.
3. **Zero Secrets Tracked:** No `.env`, private keys, local SQLite databases, or credentials exist in Git.
4. **Defensible Runtime Manifest:** Manifest A (88 files) provides an airtight, minimal runtime footprint for Render.
5. **Verified Environment Contract:** All 10 environment variables have been checked against consuming code.
6. **Zero Git Mutations:** The working tree is 100% preserved.

### Strict Change-Control Certification
- **No files staged (`git add` was NOT executed).**
- **No commits created (`git commit` was NOT executed).**
- **No pushes performed (`git push` was NOT executed).**
- **No Render deployment performed (no service created, no credentials sent).**
- **Backup repository `yatra-booking-agent` was NEVER accessed or modified.**
- **Active repository working tree completely preserved.**
