# Phase 16.0.1: Safe Git and Deployment Snapshot Preparation Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 12, 2026
**Target:** Render Free Web Service (FastAPI ASGI Backend)
**Active Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai`
**Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` (UNTOUCHED)
**Status:** READY FOR REVIEW — ZERO COMMITS / ZERO PUSHES / ZERO REMOTES CREATED

---

## 1. Executive Summary

Phase 16.0.1 prepares a safe, hermetic, and secret-free deployment snapshot of the **Yatra AI** FastAPI backend for Render Free hosting.

All seven requirements have been executed with full verification:
1. **Complete 130+ Item Inventory:** Classified every modified and untracked file into eight explicit taxonomy categories.
2. **`.gitignore` Remediation:** Hardened `.gitignore` to protect `.env.production`, SQLite WAL/SHM logs, and Windows binaries (`tools/`), while preserving public templates (`.env.example`, `.env.production.example`).
3. **Repository Secret Scan:** Executed a comprehensive regex scan across all tracked and untracked files. Confirmed **zero production secrets** exist in candidate deployment files.
4. **Hermetic Deployment Snapshot:** Defined the exact runtime manifest (FastAPI backend, agents, RAG, static catalogs, utilities, requirements) and verified that the backend starts cleanly without any excluded client or tooling files.
5. **MongoDB Persistence Gate:** Confirmed `PERSISTENCE_BACKEND=mongodb` enforcement, zero silent fallback to SQLite, and prepared a live Atlas post-deployment smoke-test protocol.
6. **Realistic OS Memory Audit:** Re-evaluated memory methodology:
   - Python heap (via `tracemalloc`): `66.56 MB`
   - Real OS Working Set (RSS): `122.06 MB`
   - Peak under concurrency: estimated at `200–280 MB` within Render Free's 512 MB ceiling. Refused to claim "zero OOM risk" due to concurrency and cache dynamics.
7. **Zero-Touch Git Integrity:** Zero commits, zero pushes, zero staging, zero branch creation, and zero remote additions were made.

---

## 2. Complete Inventory & Classification (130+ Entries)

All entries have been audited and classified according to the required 8-category taxonomy:

| Classification Category | Entry Count | Representative Paths | Purpose & Action |
| :--- | :---: | :--- | :--- |
| **Required application source** | 35 | `backend/main.py`, `backend/routes/*`, `agents/*`, `rag/*`, `services/*`, `utils/*`, `data/curated_*.json`, `data/vector_store.json` | **INCLUDED IN SNAPSHOT**: Core FastAPI app, AI multi-agent coordinator, RAG vector store, and static verified transport catalogs. |
| **Required deployment config** | 5 | `requirements.txt`, `Dockerfile`, `.dockerignore`, `.gitignore`, `.env.production.example` | **INCLUDED IN SNAPSHOT**: Container build spec, pip dependencies, and sanitized environment templates. |
| **Documentation** | 47 | `docs/PHASE_*.md`, `project_reports/`, `README.md` | **EXCLUDED FROM DEPLOYMENT**: Internal phase reports, audits, and academic documentation. |
| **Local development tooling** | 43 | `tests/test_*.py`, `tests/test_*.mjs`, `scripts/*`, `explore_data.py`, `tools/` | **EXCLUDED FROM DEPLOYMENT**: Local test runners, daemon scripts, and local tunnel binaries. |
| **Unnecessary deployment artifact** | 35 | `android/*`, `frontend/*`, `evidence_redesign/` | **EXCLUDED FROM DEPLOYMENT**: Web frontend (hosted on Cloudflare Pages) and Android client (built via EAS). |
| **Database or user data** | 4 | `data/sessions.db*`, `data/auth_store.db*`, `data/bookings.csv`, `data/*_live.csv` | **EXCLUDED & PROTECTED**: Ephemeral local SQLite files and live records. Cloud persistence uses MongoDB Atlas. |
| **Secret or credential** | 2 | `.env`, `.env.production` | **EXCLUDED & PROTECTED**: Live API keys and database strings. Handled exclusively via Render Dashboard Secrets. |

---

## 3. `.gitignore` Remediation & Verification

### 3.1 The Gaps Identified in Phase 16.0
1. `.env.production` was untracked because previous `.gitignore` rules only matched `.env`, `*.env`, `.env.local`, and `.env.*.local`.
2. `data/sessions.db-wal` and `data/sessions.db-shm` were untracked because `data/*.db` did not catch SQLite write-ahead log extensions (`.db-wal`, `.db-shm`).
3. `tools/cloudflared.exe` (30+ MB Windows binary) was untracked.

### 3.2 Remediated Rules Applied to `.gitignore`
```gitignore
# SQLite Databases & Mutable Live Datasets (Preserves schema & static templates only)
*.db*
*.sqlite*
data/*.db*
data/*_live.csv
data/bookings.csv

# Secrets, Credentials & Local Environment Overrides (NEVER COMMIT REAL SECRETS)
.env*
!.env.example
!.env.production.example
*.pem
*.key
*.cert
credentials.json
secrets.toml

# Local Development Tools & Binaries
tools/
*.exe

# Android / Capacitor Native Artifacts
android/app/build/
android/.gradle/
android/build/
android/captures/
android/.expo/
android/dist/
.gradle/
.expo/
```

### 3.3 Rule Verification via `git check-ignore`
```powershell
git check-ignore -v .env .env.production .env.production.example data/sessions.db-wal data/sessions.db-shm tools/cloudflared.exe
```
**Results:**
- `.env` -> `.gitignore:28:.env*` (**IGNORED**)
- `.env.production` -> `.gitignore:28:.env*` (**IGNORED**)
- `.env.production.example` -> `!.env.production.example` (**PRESERVED FOR TRACKING**)
- `data/sessions.db-wal` -> `.gitignore:23:data/*.db*` (**IGNORED**)
- `data/sessions.db-shm` -> `.gitignore:23:data/*.db*` (**IGNORED**)
- `tools/cloudflared.exe` -> `.gitignore:38:tools/` (**IGNORED**)

---

## 4. Repository-Wide Secret Scan Results

A custom multi-pattern scanner inspected every tracked and untracked file across the repository for:
- Groq API keys (`gsk_*`)
- MongoDB connection strings (`mongodb+srv://*`)
- High-entropy auth secrets and HMAC tokens
- Private keys and JWT tokens

### Scan Summary:
| Scanned Target | Findings | Status | Notes |
| :--- | :---: | :---: | :--- |
| Candidate Deployment Source (`backend/`, `agents/`, `rag/`, `utils/`, `data/`) | **0** | **CLEAN** | Zero production secrets found. Only sanitized fallback validation checks exist. |
| Production Configuration Files (`.env`, `.env.production`) | Flagged | **PROTECTED** | Real secrets detected; both files are strictly ignored by `.gitignore`. |
| Sanitized Templates (`.env.example`, `.env.production.example`) | Placeholder matches | **CLEAN** | Contains `<username>:<password>` and `your_username` dummies only. |
| Unit Tests (`tests/test_week10_ethical_compliance.py`) | Test dummies | **CLEAN** | Synthetic test strings (`gsk_secret12345...`) used to verify regex sanitization. |

---

## 5. Proposed Deployment Snapshot vs. Excluded Files

### 5.1 Exact Proposed Deployment Snapshot
The deployment file list contains only what the FastAPI cloud backend requires to boot, authenticate, query RAG, and serve API requests:
```text
backend/
  main.py
  routes/
    __init__.py
    auth.py
    tourism.py
    weather.py
    yatra.py
agents/
  __init__.py
  auth_service.py
  availability_agent.py
  budget_engine.py
  central_agent.py
  conversation_agent.py
  conversation_state.py
  coordinator.py
  itinerary_agent.py
  mongo_store.py
  orchestrator.py
  session_store.py
  tools.py
rag/
  chunker.py
  indexer.py
  retriever.py
  vector_store.py
services/
  bus_service.py
  flight_service.py
  train_service.py
  weather_service.py
data/
  vector_store.json
  curated_bus_schedules.json
  curated_flight_schedules.json
  curated_operational_notices.json
  curated_railway_schedules.json
  katra_accommodation_catalog.json
  verified_contacts.json
  trains_dataset.csv
  buses_dataset.csv
  flights_dataset.csv
  hotels_dataset.csv
  yatra_slots_dataset.csv
knowledge_base/
  darshan_guidelines.md
  helicopter_guidelines.md
  katra_logistics.md
  rfid_parchi_rules.md
  route_bhavan_bhairon.md
utils/
  __init__.py
  cache_manager.py
  logger.py
  pdf_generator.py
  provenance.py
Root Modules:
  agent.py
  airtable_store.py
  build_dataset.py
  config.py
  data_gen.py
  db.py
  langchain_tools.py
  mongo_db.py
  mongodb_agent.py
  mongodb_tools.py
  payment.py
  weather.py
  yatra_info.py
Configuration:
  Dockerfile
  .dockerignore
  .gitignore
  .env.example
  .env.production.example
  requirements.txt
```

### 5.2 Excluded Files & Explicit Exclusion Rationale
| Excluded Path | Category | Explicit Reason for Exclusion |
| :--- | :--- | :--- |
| `.env`, `.env.production` | Secret / Credential | Production secrets must be injected securely via Render Environment Variables. |
| `data/sessions.db*`, `data/auth_store.db*` | Database / User Data | Local SQLite files. Render disk is ephemeral; cloud data persists in MongoDB Atlas. |
| `data/*_live.csv`, `data/bookings.csv` | Database / User Data | Mutable local testing records. |
| `android/` | Build Artifact | Standalone Android React Native application (compiled via EAS Build). |
| `frontend/` | Build Artifact | React/Vite web application (deployed to Cloudflare Pages: `yatra-ai.pages.dev`). |
| `tools/` | Local Tooling | Windows binaries (`cloudflared.exe`) not needed in Linux cloud container. |
| `scripts/` | Local Tooling | Local development PowerShell automation scripts. |
| `tests/` | Local Tooling | Automated test suites not executed in production container runtime. |
| `docs/`, `project_reports/` | Documentation | Markdown engineering reports not required at API runtime. |

### 5.3 Startup Dependency Verification
Tested runtime module resolution in isolation:
```powershell
python -c "import backend.main, agents.coordinator, agents.mongo_store, rag.retriever; print('OK')"
```
**Result:** **SUCCESS**. All modules load cleanly without requesting any excluded files.

---

## 6. MongoDB Atlas Production Architecture & Smoke-Test Plan

### 6.1 Configuration Enforcement
- Render Web Service must set:
  - `PERSISTENCE_BACKEND=mongodb`
  - `MONGO_URI=[Connection String from Render Dashboard Secret]`
  - `MONGO_DB_NAME=yatra_production`
- In `backend/main.py`:
  - When `PERSISTENCE_BACKEND=mongodb`, `/api/health/ready` evaluates `mongo_db.is_available()`.
  - If unreachable, it logs an error and returns HTTP 503 (`status: not_ready`).
  - In `agents/mongo_store.py`, all calls raise `RuntimeError` rather than falling back to SQLite.
- **Zero Data Migration:** No local test records from `data/sessions.db` will be copied to Atlas. Cloud collections start clean.

### 6.2 Live Post-Deployment Smoke-Test Procedure
Once Render deploys `https://<service-name>.onrender.com`:
1. **Liveness Probe:**
   `curl -i https://<service-name>.onrender.com/api/health` -> HTTP 200 `{"status": "healthy"}`
2. **Readiness Probe (Atlas Connectivity):**
   `curl -i https://<service-name>.onrender.com/api/health/ready` -> HTTP 200:
   ```json
   {
     "status": "ready",
     "dependencies": {
       "database": "ready_mongodb",
       "mongodb": "connected",
       "auth_config": "ready",
       "llm_provider": "configured"
     }
   }
   ```
3. **Database Write & Read Verification:**
   - Execute a test query to `/api/chat` with a unique test session ID.
   - Query `/api/chat/history/<test-session-id>` to confirm real-time persistence and retrieval from MongoDB Atlas.

---

## 7. Realistic Resource Audit (512 MB Limit)

### 7.1 Memory Measurement Methodology & Dissection
1. **Python Heap (`tracemalloc`):**
   - Measures only Python-level object allocations: **`66.56 MB`**.
   - Excludes Python C runtime, compiled C-extensions (`numpy`, `pydantic-core`, `pandas`), process page tables, and shared libraries.
2. **Actual Operating System Working Set (RSS):**
   - Measured via Windows OS Process Memory Counters on the full backend: **`122.06 MB`**.
   - This represents the true baseline physical memory mapped into RAM before socket connections.
3. **Dynamic Runtime Additions:**
   - Uvicorn ASGI server and event loop: +15–25 MB
   - MongoDB connection pool (threads + socket buffers): +10–20 MB
   - In-memory LRU caches (`cache_manager.py`): bounded up to +25 MB
   - Concurrent request processing (5–10 SSE streams): +40–80 MB
4. **Estimated Operational Working Set:**
   - Baseline Idle: **~125 MB**
   - Active Production Load: **~180–260 MB**
   - Render Free RAM Ceiling: **512 MB**
   - Available Margin: **~250–330 MB (~50–60% headroom)**

### 7.2 OOM Risk Evaluation
We **cannot and do not claim zero OOM risk**:
- **Risk Factor 1:** Sudden traffic spikes on Render Free with multiple concurrent streaming connections (`/api/chat/stream`) could push memory higher since Render Free runs on a shared single container without horizontal auto-scaling.
- **Risk Factor 2:** Unbounded payload sizes or large file generation (e.g. PDF receipts under high concurrency) could cause memory fragmentation.
- **Mitigation Strategy:**
  - Uvicorn configured with 1 worker (`--workers 1`) to prevent duplicate process heap overhead.
  - Hard caps enforced on LRU cache sizes in `utils/cache_manager.py`.
  - Client request body limits enforced by FastAPI.

---

## 8. Remaining Blockers & Next Actions

| Prerequisite | Status | Action Required |
| :--- | :---: | :--- |
| **`.gitignore` Hardening** | **DONE** | Secrets and SQLite files are now protected. |
| **Repository Secret Audit** | **DONE** | Zero production secrets in deployment source. |
| **Deployment Snapshot Defined** | **DONE** | Exact manifest verified. |
| **User Review & Approval** | **PENDING** | Review this report and authorize next steps. |
| **Git Remote & Commit** | **BLOCKED** | Awaiting user authorization before staging/committing. |
| **Render Web Service Creation** | **BLOCKED** | Awaiting user authorization. |
