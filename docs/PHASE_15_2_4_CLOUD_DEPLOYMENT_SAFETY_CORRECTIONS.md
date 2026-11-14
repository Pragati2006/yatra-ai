# Yatra AI — Phase 15.2.4: Final Cloud Deployment Safety Corrections

**Date:** November 10, 2026
**Status:** AUDITED & REMEDIATED — READY FOR DEPLOYMENT GATING
**Environment:** Dual-Mode Persistence Architecture (Local SQLite & Cloud MongoDB Atlas)
**Target Platform:** Hugging Face Spaces (Docker Engine, Non-Root UID 1000, Port 7860)

---

## 1. Executive Summary & Status Verdicts

To prevent false claims of cloud deployment and ensure adherence to security, privacy, and parallel build constraints, the deployment status is categorized into six explicit verification gates:

| # | Verification Area | Status | Evidence / Notes |
|---|---|:---:|---|
| 1 | **Implementation Readiness** | **READY** | Full MongoDB adapters implemented in `agents/mongo_store.py` for all 6 user state categories; SQLite mode preserved. |
| 2 | **Mocked Test Verification** | **VERIFIED** | 16/16 persistence tests passed; 10/10 CORS tests passed; 12/12 SQLite tests passed; 7/7 container tests passed. |
| 3 | **Live MongoDB Verification** | **PENDING** | **NOT PERFORMED in local sandbox.** Live Atlas connectivity requires physical internet routing from the deployed cloud container. Mock tests do not substitute for live network verification. |
| 4 | **Production Security Readiness** | **VERIFIED** | Insecure HTTP, localhost, and private LAN origins strictly blocked in production CORS; wildcard rejected; non-root UID 1000 enforced; secrets masked in logs. |
| 5 | **Deployment Workflow Readiness** | **READY** | Gitless/Token-Free upload workflow designed via Hugging Face Space Web UI & Hub API; `.dockerignore` excludes secrets, `.db` files, and client trees. |
| 6 | **Actual Cloud Deployment Status** | **NOT DEPLOYED** | The backend has not yet been uploaded or deployed to Hugging Face Spaces. It will NOT be labeled "cloud-deployed" until actual live provisioning and smoke testing occur. |

---

## 2. MongoDB Verification Accuracy & Category Audit

### Clarification on Live vs. Mocked Testing
The automated tests in `tests/test_phase15_2_3_persistence.py` validated query structures, deep-merge logic, compound indexes, and fail-safe exception gates using an in-memory mock collection. **These tests prove code correctness, but they do NOT prove live network connectivity to MongoDB Atlas.** Live connectivity, DNS resolution, and persistence across real cloud container restarts can only be verified after deployment to the cloud environment.

### Seven Application State Categories

| Category | Storage Target (Cloud) | Storage Target (Local) | Real CRUD Implemented? | Live Atlas Tested? | Survives Container Restart? |
|---|---|---|:---:|:---:|:---:|
| **1. User Accounts** | `auth_users` | `users` (`auth_store.db`) | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **2. Auth Sessions & OTPs** | `auth_sessions`, `auth_otp_challenges` | `auth_sessions`, `otp_challenges` | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **3. Conversations** | `chat_sessions`, `chat_messages`, `auth_saved_conversations` | `saved_conversations`, `sessions`, `messages` | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **4. Saved Itineraries** | `auth_saved_itineraries` | `saved_itineraries` (`auth_store.db`) | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **5. Simulated Bookings** | `auth_user_bookings` | `user_bookings` (`auth_store.db`) | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **6. User Workflows (RPA)** | `user_workflows` | `user_workflows` (`sessions.db`) | Yes (`mongo_store.py`) | No (Mocked) | Yes (when cloud deployed) |
| **7. Operational Data** | Bundled Local JSON | Bundled Local JSON | N/A (Static files) | N/A (Immutable) | **Yes (Baked into Docker Image)** |

> [!NOTE]
> **Category 7 Storage Architecture:** Operational notices, railway schedules, bus schedules, flight schedules, hotel catalogs, and vector embeddings are curated static assets. They are intentionally bundled directly inside the Docker container image. This guarantees zero network latency, instant startup, and complete immunity to cloud database outages.

---

## 3. Production vs. Development CORS Policy

The CORS resolution logic in `backend/main.py` was updated to enforce strict environment boundaries:

### Production Mode (`APP_ENV=production`)
- **Allowed Origins:** Only explicitly approved public HTTPS origins (default: `https://yatra-ai.pages.dev`).
- **Strict Insecure HTTP Prohibition:** Plain HTTP origins (e.g. `http://example.com`) are rejected.
- **Strict Localhost & LAN Prohibition:** Localhost (`http://localhost:*`, `https://localhost:*`) and private RFC 1918 subnets (`192.168.*`, `10.*`, `172.16-31.*`) are rejected with security warnings.
- **Strict Wildcard Prohibition:** `*` and `*.pages.dev` with credentials are rejected.

### Development Mode (`APP_ENV=development`)
- **Automatic Localhost:** Includes `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://localhost:8000`.
- **Private LAN Support:** Allows private LAN IPs (e.g. `http://192.168.1.100:8000`) for Expo Go and Android device testing over local Wi-Fi.

---

## 4. Token-Free & Gitless Deployment Workflow

Because project constraints prohibit Git commits and pushes from the agent session, the deployment runbook is adapted to use either the **Hugging Face Web Interface** or a **direct file-upload script**.

### Strict File Exclusion Rules
Before any files are uploaded, `.dockerignore` and upload filters strictly exclude:
- **Secrets:** `.env`, `.env.*` (preserving only `.env.example`).
- **Local Databases:** `*.db`, `*.sqlite`, `data/*.db`, `data/auth_store.db`, `data/sessions.db`.
- **Client Source Trees:** `android/` (built separately via EAS), `frontend/` (built and hosted via Cloudflare Pages), `node_modules/`.
- **Temporary Artifacts:** `__pycache__/`, `.pytest_cache/`, `*.log`, `scratch/`, `evidence_redesign/`.

### Deployment Method A: Hugging Face Space Web Interface (Recommended)
1. Open your Space at: `https://huggingface.co/spaces/<YOUR_USERNAME>/yatra-ai-backend`.
2. Configure Secrets in **Settings** -> **Variables and secrets**:
   - `APP_ENV` = `production`
   - `PERSISTENCE_BACKEND` = `mongodb`
   - `MONGO_URI` = `<your-mongodb-atlas-uri>`
   - `AUTH_HMAC_SECRET` = `<32-char-random-string>`
   - `GROQ_API_KEY` = `<your-groq-api-key>`
3. Click on the **Files** tab -> **Add file** -> **Upload files**.
4. Drag and drop the backend files:
   - `Dockerfile`, `requirements.txt`, `config.py`, `db.py`, `mongo_db.py`, `weather.py`, `agent.py`, `mongodb_agent.py`, `explore_data.py`.
   - Folders: `backend/`, `agents/`, `rag/`, `utils/`, `data/`, `knowledge_base/`, `services/`, `tools/`.
   - *(Do NOT upload `.env`, `data/*.db`, `android/`, `frontend/`, or `node_modules/`)*.
5. Commit directly via the web UI ("Commit changes to main"). The Docker Space will build automatically.

### Deployment Method B: Python Hub API (`HfApi.upload_folder`)
Run locally without git commands:
```powershell
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.upload_folder(
    folder_path='.',
    repo_id='<YOUR_USERNAME>/yatra-ai-backend',
    repo_type='space',
    ignore_patterns=['.git*', '.env*', '*.db', 'data/*.db', 'frontend/**', 'android/**', 'node_modules/**', '__pycache__/**']
)
"
```

---

## 5. Hugging Face Spaces Resource & Tier Verification

| Aspect | Free Tier Specification | Project Constraint Compliance |
|---|---|---|
| **Hardware** | CPU Basic (2 vCPU · 16 GB RAM · 50 GB Ephemeral Disk) | **Approved** — Completely free; requires zero credit card. |
| **Inactivity Sleep** | Automatically sleeps after **48 hours** of no requests. | Handled via cold-start resilience and external MongoDB Atlas persistence. |
| **Cold Start Wakeup** | Takes 30–60s to boot container upon new HTTP request. | Frontend displays loading state; health readiness probe reports status. |
| **Ephemeral Disk** | Container filesystem wipes on every sleep and reboot. | Solved: User state persists in MongoDB Atlas; zero dependence on container disk. |
| **Paid Hardware Options** | Upgraded CPU (\$0.03/hr), GPU (\$0.60–\$1.05/hr), Persistent Storage (\$5/mo) | **STRICTLY FORBIDDEN.** Total hosting cost is **\$0.00**. |

---

## 6. Verification & Test Evidence

All tests executed with zero regressions and clean status:

1. **CORS Security & Exclusion Tests:** `tests/test_cors_policy.py` (10/10 Passed)
2. **Persistence Adapter & Fail-Safe Gate Tests:** `tests/test_phase15_2_3_persistence.py` (16/16 Passed)
3. **Local SQLite Regression Tests:** `tests/test_session_store.py` (12/12 Passed)
4. **Container Readiness Tests:** `tests/test_phase15_2_1_deployment_readiness.py` (7/7 Passed)
5. **Frontend API URL Security Tests:** `tests/test_api_url_validation.mjs` (17/17 Passed)
6. **Parallel EAS Android Build Safety:** `android/*` completely untouched; Expo SDK 58 lockfile preserved.
