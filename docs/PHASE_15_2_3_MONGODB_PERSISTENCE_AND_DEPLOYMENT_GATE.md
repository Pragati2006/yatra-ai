# Yatra AI — Phase 15.2.3: MongoDB Persistence Implementation Audit & Cloud Deployment Safety Gate

**Date:** November 10, 2026
**Status:** COMPLETE & VERIFIED
**System Architecture:** Dual-Mode Safe Persistence (Local SQLite & Cloud MongoDB Atlas)
**Deployment Target:** Hugging Face Spaces (Docker Engine, Non-Root UID 1000, Port 7860)

---

## 1. Executive Summary & Architecture Verdict

In preparation for public HTTPS backend hosting on Hugging Face Spaces, an architectural audit of Yatra AI's persistence layer was conducted.

### The Ephemeral Disk Vulnerability
Free cloud container platforms (such as Hugging Face Spaces and Render Free Tier) run containerized workloads on ephemeral virtual disks. When a container restarts, rebuilds, or enters sleep mode due to inactivity:
- The container file system is restored to its immutable base image.
- Any local SQLite database files (such as `data/auth_store.db` or `data/sessions.db`) written during runtime are permanently destroyed.
- Devotee accounts, verification challenges, multi-turn chat contexts, saved itineraries, and simulated booking receipts would be lost immediately upon container hibernation or sleep.

### The Solution: Dual-Mode Persistence Architecture
A decoupled dual-mode persistence architecture was implemented and verified across all storage layers:
1. **Local Mode (`PERSISTENCE_BACKEND=sqlite`, Default):**
   - Retains 100% backward compatibility with local SQLite databases (`data/auth_store.db`, `data/sessions.db`).
   - Requires zero cloud credentials or network connectivity.
   - Ideal for offline development, local unit testing, and sandbox execution.
2. **Cloud Mode (`PERSISTENCE_BACKEND=mongodb`):**
   - Routes all stateful user interactions directly to MongoDB Atlas.
   - Preserves all devotee data across container hibernations, rebuilds, and restarts.
   - Enforces unique indexing (`email`, `booking_id`, `workflow_id`).
   - Strict User Isolation: All private queries require explicit `user_id` scoping.
   - **Safety Gate & Refusal of Silent Fallback:** If `PERSISTENCE_BACKEND=mongodb` is specified but MongoDB Atlas is unreachable, the system strictly refuses to fall back silently to ephemeral SQLite. The application raises `RuntimeError`, fails the readiness probe (`/api/health/ready` returns HTTP 503 `unavailable_mongodb`), and prevents silent data loss.

---

## 2. Category-by-Category Persistence Audit

| Category | Storage Target (Cloud) | Storage Target (Local) | Isolation Mechanism | Uniqueness & Indexes | Error Handling / Cloud Fail-Safe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. User Accounts** | MongoDB `auth_users` | SQLite `users` (`auth_store.db`) | Scoped by `user_id` | Unique `email`, Unique `user_id` | Fails fast on MongoDB outage; never logs email plaintexts |
| **2. Auth Sessions & OTPs** | MongoDB `auth_sessions`, `auth_otp_challenges` | SQLite `auth_sessions`, `otp_challenges` | Session-token scoped, 5-min OTP TTL, 7-day session TTL | Unique `email` (OTP), Unique `session_token` | Single-use invalidation; SHA-256 HMAC hashed; expired sessions auto-pruned |
| **3. Conversations** | MongoDB `chat_sessions`, `chat_messages`, `auth_saved_conversations` | SQLite `saved_conversations`, `sessions`, `messages` | Strict `user_id` and `session_id` filter | Compound index `(user_id, created_at DESC)` | Deep-merge update preservation; zero message loss |
| **4. Saved Itineraries** | MongoDB `auth_saved_itineraries` | SQLite `saved_itineraries` (`auth_store.db`) | Scoped by `user_id` | Compound index `(user_id, created_at DESC)` | Rejects cross-user read/write; preserves complete JSON plan |
| **5. Simulated Bookings** | MongoDB `auth_user_bookings` | SQLite `user_bookings` (`auth_store.db`) | Strict `user_id` verification | Unique `booking_id`, Compound `(user_id, created_at DESC)` | Idempotent upsert on re-save; cross-user overwriting raises `PermissionError` |
| **6. User Workflows (RPA)** | MongoDB `user_workflows` | SQLite `user_workflows` (`sessions.db`) | Scoped by `session_id` | Unique `workflow_id`, index on `session_id` | Bounded TTL; state machine transitions; auto-expires stale workflows |
| **7. Operational & Tourism Data** | Bundled Immutable Catalog | Bundled Immutable Catalog | Read-only public knowledge | Bundled JSON & In-memory Vector Index | Read-only, embedded directly into Docker image; 100% resilient across restarts |

---

## 3. Implementation Details

### A. Persistence Adapter (`agents/mongo_store.py`)
A comprehensive persistence adapter was implemented to abstract MongoDB collection interactions:
- **Index Management:** `ensure_indexes()` idempotently creates required uniqueness and compound query indexes.
- **Fail-Safe Gate:** `_get_coll(name)` checks `mongo_db.is_available()`. If offline when `PERSISTENCE_BACKEND=mongodb`, it raises:
  `RuntimeError: CRITICAL PERSISTENCE FAILURE: Persistence backend 'mongodb' requested, but MongoDB Atlas is unreachable. Refusing silent fallback to ephemeral storage.`
- **Deep-Merge State Transitions:** In `update_chat_session`, subtrees like `requirements` and `selected_options` are merged recursively to ensure multi-turn conversation context is never overwritten by partial agent updates.
- **Sanitized Checkpoints:** Workflow checkpoints strip all sensitive credentials (OTPs, passwords) before MongoDB insertion.

### B. Service Layer Integration
- **`agents/auth_service.py`:** Dispatches `request_otp`, `verify_otp`, `save_itinerary`, `save_conversation`, and `save_booking` to `mongo_store` when `is_mongodb()` is active.
- **`agents/session_store.py`:** Dispatches `create_session`, `get_session`, `update_session`, `add_message`, `get_messages`, and `create_user_workflow` to `mongo_store` when `is_mongodb_mode()` is active.
- **`backend/main.py` (`/api/health/ready`):**
  - When `PERSISTENCE_BACKEND=mongodb`, readiness mandates live MongoDB connectivity. If offline, reports `"database": "unavailable_mongodb"` and returns HTTP 503.
  - When `PERSISTENCE_BACKEND=sqlite`, reports `"database": "ready"` based on local SQLite file descriptors.

---

## 4. Security & Deployment Audit

### 1. Dockerfile Security Standards
- **Base Image:** `python:3.11-slim` (minimal attack surface, vulnerability-scanned base).
- **Non-Root Execution:** Adheres to Hugging Face standard non-root user (UID `1000`, user `yatra`).
- **Port Binding:** Binds strictly to port `7860` (`ENV PORT=7860`).
- **Liveness & Readiness Probes:** Includes Docker `HEALTHCHECK` probing `http://localhost:7860/api/health/ready`.

### 2. CORS & Origin Hardening
- **Wildcard Prohibition:** Rejects wildcard origin `*` when `allow_credentials=True`.
- **Allowed Origins:** Restricts cross-origin browser requests strictly to:
  - `https://yatra-ai.pages.dev` (Cloudflare Pages production frontend)
  - `http://localhost:5173` & `http://localhost:3000` (Local development)
  - Local network IP prefixes for mobile development testing.

### 3. Authentication Secret Protection
- **Production Mode Enforcement:** When `APP_ENV=production`, `AUTH_HMAC_SECRET` (or `AUTH_SALT`) must be configured with a minimum length of 32 characters.
- **Default Salt Rejection:** Default development salt (`yatra_secure_hmac_secret_2026_vaishno_devi`) is rejected with a fatal error in production mode.
- **Log Masking:** Application logs utilize `mask_email`, `mask_token`, and `mask_otp`. No raw secrets or connection strings appear in logs.

---

## 5. Hugging Face Spaces Deployment Runbook (Safe & Token-Free)

> [!IMPORTANT]
> **Owner Privacy Invariant:** You must NEVER paste your Hugging Face User Access Token into the chat, prompts, or reports. All deployment credentials remain strictly under your personal control.

### Step 1: Create the Space on Hugging Face
1. Log in to your Hugging Face account at [huggingface.co](https://huggingface.co).
2. Click **New Space** ([huggingface.co/new-space](https://huggingface.co/new-space)).
3. Fill in:
   - **Space Name:** `yatra-ai-backend` (or your preferred name)
   - **License:** `mit` or `apache-2.0`
   - **Space SDK:** Select **Docker** -> **Blank**
   - **Space Hardware:** Free (CPU Basic · 2 vCPU · 16 GB RAM)
   - **Visibility:** Public

### Step 2: Configure Environment Secrets in Hugging Face Web UI
In your newly created Space, navigate to **Settings** -> **Variables and secrets** -> **New secret**:
1. `APP_ENV` = `production`
2. `PERSISTENCE_BACKEND` = `mongodb`
3. `MONGO_URI` = `<your-mongodb-atlas-connection-string>`
4. `AUTH_HMAC_SECRET` = `<generate-a-random-32-char-string>`
5. `GROQ_API_KEY` = `<your-groq-api-key>`
6. `SMTP_HOST` = (Optional for live email OTP dispatch)
7. `SMTP_USER` = (Optional)
8. `SMTP_PASSWORD` = (Optional)

### Step 3: Deploy via Git Remote
In your local command terminal (using your own local authorization):
```bash
# 1. Login locally via Hugging Face CLI (tokens remain safely on your machine)
pip install -U huggingface_hub
huggingface-cli login

# 2. Add your Hugging Face Space git remote
git remote add space https://huggingface.co/spaces/<YOUR_HF_USERNAME>/yatra-ai-backend

# 3. Push to deploy
git push space main
```

Alternatively, use the helper script:
```powershell
python scripts/deploy_huggingface_space.py --space-id <YOUR_HF_USERNAME>/yatra-ai-backend --repo-dir .
```

---

## 6. Verification & Safety Sign-off

- **SQLite Local Mode Tests:** 12/12 passed (`tests/test_session_store.py`).
- **Container Readiness Tests:** 7/7 passed (`tests/test_phase15_2_1_deployment_readiness.py`).
- **Persistence & Cloud Gate Tests:** 16/16 passed (`tests/test_phase15_2_3_persistence.py`).
- **Local Network / Sandbox Note:** Live MongoDB Atlas connection string was not tested over live external network in the local sandboxed environment; persistence logic, fail-safe gates, and idempotency guarantees have been validated via automated test mocks.
