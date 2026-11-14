# Phase 15.3 — Hugging Face Spaces Cloud Backend Deployment Plan

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 10, 2026
**Status:** Pre-Deployment Audit Completed & Verified (62/62 Tests Passing)
**Target Space:** `yatra-ai-backend` on Hugging Face Spaces (Docker SDK)
**Hardware Tier:** CPU Basic · 2 vCPU · 16 GB RAM (Free Tier)

---

## 1. Executive Summary & Audit Verification

All preparatory stages (Phases 15.2.1, 15.2.2, 15.2.3, and 15.2.4) have been reconciled and verified against the actual working tree.

### 8-Point Pre-Deployment Audit Matrix

| Audit Item | Scope | Implementation File | Verification Status | Details |
| :--- | :--- | :--- | :---: | :--- |
| **1. Repository & Tree** | Git & Safety | `yatra-ai` working tree | **VERIFIED** | Active repository preserved; zero Git commits/pushes; backup repository untouched. |
| **2. Dockerfile & Exclusions** | Container Configuration | `Dockerfile`, `.dockerignore` | **VERIFIED** | Multi-stage Python 3.11-slim, non-root user (UID 1000), dynamic port `7860`, `*.db`, `.env*`, `android/`, `frontend/`, `tools/` (52.8 MB binary) excluded. |
| **3. Deployment Script** | Direct Upload | `scripts/deploy_huggingface_space.py` | **VERIFIED** | Uses `HfApi.upload_folder`, skips Git entirely, excludes local databases and secrets. Payload optimized to 12.65 MB. |
| **4. MongoDB Persistence** | 7 Data Categories | `agents/mongo_store.py`, `agents/auth_service.py` | **VERIFIED** | Multi-turn deep merge, unique email & session indexes, user isolation, 503 fail-safe on DB unreachable (16/16 tests passing). |
| **5. Port & Startup** | ASGI Binding | `backend/main.py` | **VERIFIED** | Binds to `0.0.0.0` with dynamic `PORT` environment variable (`PORT=7860` default in container). |
| **6. Production CORS** | Cross-Origin Security | `backend/main.py` | **VERIFIED** | In `APP_ENV=production`, strictly allows `https://yatra-ai.pages.dev`; rejects HTTP, localhost, private LANs, and wildcard `*` (10/10 tests passing). |
| **7. Web URL Resolution** | Client Connectivity | `frontend/src/services/api.js` | **VERIFIED** | Validates HTTPS, permits `*.hf.space`, supports dynamic URL query parameter (`?backend=...`) and localStorage persistence. |
| **8. Android URL Resolution** | Installed APK | `android/src/utils/urlValidator.js`, `ConnectionModal.jsx` | **VERIFIED** | Regex permits `*.hf.space` over HTTPS; Connection Settings modal allows direct runtime URL configuration **without requiring an APK rebuild**. |

---

## 2. Deployment Architecture

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT CLIENTS                                    |
|                                                                                   |
|   +------------------------------------+   +----------------------------------+   |
|   |   Web Application                  |   |   Installed Standalone APK       |   |
|   |   https://yatra-ai.pages.dev       |   |   (Physical Android Device)      |   |
|   +-----------------+------------------+   +-----------------+----------------+   |
|                     |                                        |                    |
|                     | HTTPS Bearer JWT                       | HTTPS Bearer JWT   |
|                     +-------------------+--------------------+                    |
|                                         |                                         |
+-----------------------------------------v-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               HUGGING FACE SPACES (Free Docker Container - Port 7860)              |
|               Endpoint: https://<username>-yatra-ai-backend.hf.space               |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   | FastAPI Application (backend/main.py)                                     |   |
|   | - Non-root user (UID 1000)                                                |   |
|   | - Strict Production CORS Policy (Allowed: https://yatra-ai.pages.dev)     |   |
|   | - Liveness: /api/health (200 OK)                                          |   |
|   | - Readiness: /api/health/ready (Verifies MongoDB Atlas connectivity)      |   |
|   +---------------------+---------------------------------+-------------------+   |
|                         |                                 |                       |
+-------------------------|---------------------------------|-----------------------+
                          |                                 |
                          v                                 v
        +-----------------------------------+     +--------------------+
        |         MongoDB Atlas             |     |      Groq API      |
        |      (Persistent Storage)         |     |  (Llama-3-70B/8B)  |
        | - auth_users                      |     +--------------------+
        | - auth_sessions                   |
        | - auth_otp_challenges             |
        | - auth_saved_conversations        |
        | - saved_itineraries               |
        | - simulated_bookings              |
        | - user_workflows                  |
        +-----------------------------------+
```

---

## 3. Hugging Face Space Provisioning & Secrets Guide

### A. Space Provisioning (Free CPU Basic Tier)
- **Space Name:** `yatra-ai-backend`
- **License:** MIT or Open Rail
- **Space SDK:** Docker (Blank)
- **Hardware:** CPU Basic · 2 vCPU · 16 GB RAM · Free (Never select paid hardware)

### B. Environment Variables & Secrets (Space Settings -> Variables and secrets)

The following configuration must be entered in the Space settings:

| Name | Type | Value / Guidance | Purpose |
| :--- | :---: | :--- | :--- |
| `APP_ENV` | Variable | `production` | Enables strict CORS and production security rules |
| `ENV` | Variable | `production` | Enforces production mode across all modules |
| `PORT` | Variable | `7860` | Hugging Face Spaces standard HTTP port |
| `HOST` | Variable | `0.0.0.0` | Container external network interface binding |
| `PERSISTENCE_BACKEND` | Variable | `mongodb` | Forces MongoDB Atlas storage; disables SQLite |
| `CORS_ALLOWED_ORIGINS` | Variable | `https://yatra-ai.pages.dev` | Explicitly permits Cloudflare Pages web app |
| `MONGO_DB_NAME` | Variable | `tourism_db` | Target MongoDB database name |
| `MONGO_URI` | **Secret** | `mongodb+srv://...` | Connection string to your MongoDB Atlas cluster |
| `GROQ_API_KEY` | **Secret** | `gsk_...` | Groq LLM inference API key |
| `AUTH_HMAC_SECRET` | **Secret** | 64-hex char random string | Session and token signing secret |

---

## 4. Zero-Git Safe Deployment Pathways

To protect all credentials and adhere to the strict prohibition on Git operations, two pathways are available:

### Pathway 1: Web Interface Upload (No Local Token Setup Required)
1. In your browser, navigate to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Name the space `yatra-ai-backend`, select **Docker**, and choose the **Blank** template on the free CPU tier.
3. In **Settings -> Variables and secrets**, add the variables and secrets listed in Section 3.
4. In the **Files** tab, click **Add file -> Upload folder** or upload the files using the drag-and-drop web UI.
   *(Note: The uploaded folder should exclude `android/`, `frontend/`, `tools/`, `.env*`, and `*.db` as defined in `.dockerignore`)*.
5. The Space will automatically trigger the Docker build and launch the container.

### Pathway 2: Local CLI / Hub API Direct Upload (Automated)
1. In a separate terminal on your laptop, run:
   ```powershell
   huggingface-cli login
   ```
   *(Enter your personal User Access Token with write permissions. It will be stored securely in your user cache without being entered into chat)*.
2. Provide your Hugging Face username in chat.
3. Antigravity will execute `scripts/deploy_huggingface_space.py`, which directly uploads the 12.65 MB application tree and provisions the Space via the official Hugging Face Hub Python SDK without touching Git.

---

## 5. Post-Deployment Live Verification & Smoke Test Protocol

Once the container reaches `RUNNING` status on Hugging Face Spaces:

1. **Liveness Probe:**
   `GET https://<username>-yatra-ai-backend.hf.space/api/health`
   *Expected: HTTP 200 `{"status": "healthy"}`*

2. **Readiness Probe:**
   `GET https://<username>-yatra-ai-backend.hf.space/api/health/ready`
   *Expected: HTTP 200 `{"status": "ready", "dependencies": {"database": "ready_mongodb", "mongodb": "connected"}}`*

3. **CORS Enforcement Check:**
   - Request with `Origin: https://yatra-ai.pages.dev` -> Allowed with `Access-Control-Allow-Origin: https://yatra-ai.pages.dev`.
   - Request with `Origin: http://localhost:3000` -> Rejected.

4. **Live Chat & RAG Retrieval:**
   - `POST /api/chat` with pilgrimage query (e.g., "What are the darshan timings for Vaishno Devi?").
   - Validates live Groq inference and curated operational data retrieval.

5. **Live Authentication & MongoDB Persistence:**
   - `POST /api/auth/otp/request` -> OTP challenge stored in MongoDB `auth_otp_challenges`.
   - `POST /api/auth/otp/verify` -> Session created in `auth_sessions` and user in `auth_users`.
   - `POST /api/auth/conversations/save` -> Conversation saved in `auth_saved_conversations`.

---

## 6. Client Connection Verification

### Web Frontend (Cloudflare Pages)
- Access `https://yatra-ai.pages.dev/?backend=https://<username>-yatra-ai-backend.hf.space`
- The application will display a one-click connection confirmation banner.
- Upon clicking "Connect", the URL is verified via `/api/health` and saved in `localStorage`.
- All subsequent chat and auth requests communicate directly with Hugging Face Spaces.

### Standalone Android APK (No Rebuild Needed)
- Open the installed Yatra AI app on your phone.
- Tap the **Connection Settings** icon in the header.
- In the backend URL field, enter `https://<username>-yatra-ai-backend.hf.space`.
- Tap **Test Connection** -> App executes a health check.
- Tap **Save and Connect** -> URL is saved to `SecureStore`.
- The Android app is now fully independent of your laptop!
