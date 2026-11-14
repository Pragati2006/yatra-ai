# Phase 15.4 — Actual Quick Tunnel Deployment & End-to-End Connectivity Verification Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 10, 2026
**Auditor & Orchestrator:** Antigravity (Google DeepMind Advanced Agentic Coding)
**Status:** Live Public HTTPS Backend Successfully Deployed & Verified Over Cloudflare Edge

---

## 1. Executive Summary & Live Public Endpoint

Pursuant to Phase 15.4 instructions, the local FastAPI production backend and Cloudflare Quick Tunnel have been successfully launched and verified. Both the Cloudflare Pages web application and the installed physical Android APK can now communicate over public HTTPS with the unified backend.

### Live Connection Details

| Attribute | Live Value |
| :--- | :--- |
| **Active Public HTTPS Backend URL** | `https://sustainability-charleston-tourist-paint.trycloudflare.com` |
| **Public Health Endpoint** | `https://sustainability-charleston-tourist-paint.trycloudflare.com/api/health` |
| **Public Readiness Endpoint** | `https://sustainability-charleston-tourist-paint.trycloudflare.com/api/health/ready` |
| **Web Frontend Production URL** | `https://yatra-ai.pages.dev/?backend=https://sustainability-charleston-tourist-paint.trycloudflare.com` |
| **Active Persistence Backend** | `sqlite` (`data/sessions.db` & `data/auth_store.db`) |
| **AI LLM Inference** | Groq API (`llama-3.3-70b-versatile`) — **CONFIGURED & ACTIVE** |
| **Authentication HMAC Secret** | 256-bit cryptographically secure hex secret — **CONFIGURED & ACTIVE** |
| **Production CORS** | Strictly allows `https://yatra-ai.pages.dev`; rejects HTTP and localhost |
| **Tunnel Provider** | Cloudflare Quick Tunnel (`tools/cloudflared.exe` v2026.10.7) |
| **Cost & Card Requirement** | **$0.00 · Zero Credit Card · Zero Paid Subscriptions** |

---

## 2. Pre-Deployment Configuration Audit Matrix

| Audit Item | Scope | Implementation | Verification Result |
| :--- | :--- | :--- | :---: |
| **1. Persistence Backend** | Database Selection | `.env.production` (`PERSISTENCE_BACKEND=sqlite`) | **VERIFIED:** Uses persistent local SQLite (`data/sessions.db` and `data/auth_store.db`). |
| **2. Production DB Requirement** | Cloud vs Local | `backend/main.py` lines 185–214 | **VERIFIED:** MongoDB is only enforced if `PERSISTENCE_BACKEND=mongodb`; SQLite mode verifies local tables. |
| **3. SQLite Fallback Guard** | Anti-Data-Loss | `agents/mongo_store.py` line 42 | **VERIFIED:** When MongoDB mode is requested, silent fallback to SQLite is strictly disabled. |
| **4. Startup Script DB Check** | Storage Validation | `scripts/start_backend_production.ps1` lines 81–92 | **VERIFIED:** Verifies data directory writability and database paths before launching. |
| **5. Interface & Port Binding** | Network Binding | `scripts/start_backend_production.ps1` | **VERIFIED:** Binds safely to `127.0.0.1:8000`. |
| **6. Production CORS Policy** | Origin Whitelist | `backend/main.py` lines 99–102 | **VERIFIED:** Explicitly permits `https://yatra-ai.pages.dev`; rejects insecure/LAN origins. |
| **7. Android URL Persistence** | Installed APK | `android/src/utils/urlValidator.js` & `storage.js` | **VERIFIED:** Regex allows `*.trycloudflare.com`; stores URL in device storage without rebuild. |

---

## 3. Local Backend Startup Verification

The production launcher `scripts/start_backend_production.ps1` was executed with `.env.production`:

- **Data Directory:** `C:\Users\praga\OneDrive\Documents\Minor Project\data` [WRITABLE]
- **Auth Store DB:** `C:\Users\praga\OneDrive\Documents\Minor Project\data\auth_store.db`
- **Sessions DB:** `C:\Users\praga\OneDrive\Documents\Minor Project\data\sessions.db`
- **Authentication Secret:** Strong 256-bit hex signing secret validated.
- **Server Process:** Uvicorn ASGI daemon running on `http://127.0.0.1:8000`.
- **Pre-flight Status:** Production mode enforced (`APP_ENV=production`, `ENABLE_DEV_TEST_ENDPOINTS=false`).

---

## 4. Public Endpoint Live Smoke Test Results

All smoke tests were executed using live HTTP requests directed at the public Cloudflare edge URL (`https://sustainability-charleston-tourist-paint.trycloudflare.com`):

| Test # | Target Endpoint | HTTP Method | Response Code | Verified Live Behavior | Status |
| :---: | :--- | :---: | :---: | :--- | :---: |
| **1** | `/api/health` | `GET` | **200 OK** | `{"status": "healthy", "service": "Yatra Booking Agent"}` | **PASS** (Live) |
| **2** | `/api/health/ready` | `GET` | **200 OK** | `{"status": "ready", "dependencies": {"database": "ready", "mongodb": "offline_fallback_active", "auth_config": "ready", "llm_provider": "configured"}}` | **PASS** (Live) |
| **3** | `/api/tourism/` | `POST` | **200 OK** | Returned structured pilgrimage knowledge base payload with provenance metadata for query `"Bhairavnath Temple"`. | **PASS** (Live) |
| **4** | `/api/chat` | `POST` | **200 OK** | Live multi-turn agent response from Groq LLaMA 3.3: generated darshan timings and 2-day itinerary; initialized session `2bdcb770-0d4e-4449-8503-4cae7bb3d785`. | **PASS** (Live) |
| **5** | `/api/chat/history/{session_id}` | `GET` | **200 OK** | Confirmed 2 persistent chat messages stored and retrieved from `data/sessions.db`. | **PASS** (Live) |
| **6** | `/api/yatra/authorize` | `POST` | **200 OK** | Plan human authorization gate passed: returned `{"status": "success"}` on valid session; returned `{"status": "authorization_required"}` on invalid session. | **PASS** (Live) |
| **7** | Production CORS Check | `OPTIONS` | **Headers Verified** | Sent `Origin: https://yatra-ai.pages.dev` -> Returned `Access-Control-Allow-Origin: https://yatra-ai.pages.dev`. Sent `Origin: http://localhost:3000` -> `Access-Control-Allow-Origin` strictly omitted. | **PASS** (Live) |

---

## 5. Web Application Connection Guide (Cloudflare Pages)

To connect the live public web frontend:

1. Open your browser and navigate to:
   ```
   https://yatra-ai.pages.dev/?backend=https://sustainability-charleston-tourist-paint.trycloudflare.com
   ```
2. The web frontend detects the proposed URL parameter and displays the connection banner:
   *"Connect to proposed backend: https://sustainability-charleston-tourist-paint.trycloudflare.com"*.
3. Click **"Connect"**:
   - The frontend validates the origin against `APPROVED_TUNNEL_HOST_PATTERN`.
   - Sends a probe to `/api/health`.
   - Persists the backend URL in `localStorage`.
   - Cleans the URL parameter from the browser bar.
4. The web application is now actively connected to your local backend over public HTTPS.

---

## 6. Installed Android APK Connection Guide (Physical Phone)

On your physical Android device where the Yatra AI standalone APK is installed:

1. Open the **Yatra AI** application.
2. In the top navigation bar, tap the **Connection Settings** icon (or navigate to Settings).
3. In the Backend URL text box, enter:
   ```
   https://sustainability-charleston-tourist-paint.trycloudflare.com
   ```
4. Tap **"Test Connection"**:
   - The app dispatches a background GET request to `/api/health`.
   - A confirmation dialog appears: *"Connected to Yatra AI Backend: healthy"*.
5. Tap **"Save and Connect"**:
   - The app securely calls `setRuntimeApiUrl()`.
   - The URL is saved in persistent device storage.
   - Any prior session tokens from other backends are automatically cleared (`await clearAuthToken()`) to guarantee token isolation.
6. Return to the Chat screen. The mobile app will now send live pilgrimage and booking queries through the Cloudflare tunnel directly to your laptop!

---

## 7. Network Independence & Operational Requirements

- **Laptop State:** The student's laptop must remain powered on with sleep/hibernate disabled, and connected to the internet, because the FastAPI server and `cloudflared.exe` process are hosted locally.
- **Physical Phone Network Independence:** The Android phone does **NOT** need to be on the same Wi-Fi. It can connect via **Mobile Data (4G/5G)**, college Wi-Fi, or any external cellular network. Traffic is routed securely through Cloudflare's global edge network.
- **Restarting the Tunnel Safely:**
  If the laptop restarts or the tunnel process closes:
  1. Start the backend:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_production.ps1
     ```
  2. Start the tunnel:
     ```powershell
     .\tools\cloudflared.exe tunnel --url http://127.0.0.1:8000 --no-autoupdate
     ```
  3. Copy the newly printed `*.trycloudflare.com` URL into the web browser and Android Connection Settings.

---

## 8. Verification Classification Matrix

| Verification Aspect | Status Label | Details |
| :--- | :---: | :--- |
| Public HTTPS Health & Readiness | **VERIFIED LIVE** | HTTP 200 responses received across public Cloudflare edge network. |
| AI Chat & RAG Retrieval | **VERIFIED LIVE** | Groq LLaMA 3.3 inference and pilgrimage knowledge base retrieved. |
| Multi-turn Chat Persistence | **VERIFIED LIVE** | Messages stored and retrieved from SQLite `data/sessions.db`. |
| Plan Human Authorization Gate | **VERIFIED LIVE** | Fails closed on invalid session; approves on verified session. |
| Production CORS Strictness | **VERIFIED LIVE** | `https://yatra-ai.pages.dev` permitted; localhost rejected. |
| Token Destruction on Origin Change | **VERIFIED LOCALLY IN CODE** | `android/src/services/api.js` line 61 explicitly calls `clearAuthToken()`. |
| Android Public Host Policy | **VERIFIED LOCALLY IN CODE** | `android/src/utils/urlValidator.js` validates `*.trycloudflare.com` regex. |
| End-to-End Physical Android Test | **AWAITING USER INPUT** | Ready for user to enter tunnel URL on physical phone and test live. |
