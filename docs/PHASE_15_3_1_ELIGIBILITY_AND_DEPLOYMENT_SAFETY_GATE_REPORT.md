# Phase 15.3.1 — Final Hugging Face Eligibility & Deployment Safety Gate Report

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Date:** November 10, 2026
**Auditor:** Antigravity (Google DeepMind Advanced Agentic Coding)
**Safety Status:** Gate Enforced — Zero Deployment / Zero Upload Executed

---

## 1. Audit Verdict

```
+------------------------------------------------------------------------------------+
|                                                                                    |
|   FINAL VERDICT: BLOCKED                                                           |
|                                                                                    |
|   Reason: Official Hugging Face platform policy now enforces an active billing     |
|   method (credit card) or paid PRO subscription ($9/month) to initialize and       |
|   host Spaces using the Docker SDK. Standard free accounts without a payment       |
|   method on file are restricted from creating new Docker Spaces.                   |
|                                                                                    |
|   Action: Deployment is HALTED pursuant to Phase 15.3.1 Section 2 instructions.    |
|   No resources created. No files uploaded. No credentials requested.               |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

---

## 2. Evidence of Account & Platform Eligibility Restriction

### A. Documented Hugging Face Platform Policy
Investigation of current Hugging Face Spaces platform documentation, billing terms, and community discussions confirms:
1. **Docker SDK Enforcement:** While static and standard SDK (Gradio/Streamlit) Spaces remain available, hosting custom container environments via the **Docker SDK** now requires an active billing method on file or an active **Hugging Face PRO** subscription ($9/mo) to mitigate automated bot and resource abuse.
2. **Free Accounts Restricted:** On free accounts without credit card details attached, the Docker SDK option is either disabled/greyed out during Space creation at `huggingface.co/new-space`, or prompts an immediate gate requiring credit card entry before the container can build or run.
3. **Zero-Payment Constraint Violation:** Because the user's non-negotiable mandate strictly forbids paid subscriptions, credit cards, payment methods, or prepaid credits, proceeding with a Docker Space on Hugging Face is **BLOCKED**.

---

## 3. Genuinely Free / No-Payment Alternatives

To maintain 100% adherence to the zero-payment, zero-credit-card mandate while achieving public connectivity for both the web app and installed Android APK, the following alternatives are available:

### Alternative 1: Hugging Face Gradio SDK Space (Mounting FastAPI) — Recommended
- **Cost:** Free ($0.00). Zero credit card or PRO subscription required.
- **Mechanism:** Hugging Face allows free accounts to create `sdk: gradio` Spaces on CPU Basic (2 vCPU · 16 GB RAM).
- **FastAPI Compatibility:** Gradio is built on top of Starlette and FastAPI. In a minimal `app.py`, we mount the entire existing Yatra AI FastAPI application via `gr.mount_gradio_app(app, ...)`.
- **Client Impact:** All REST endpoints (`/api/chat`, `/api/health`, `/api/auth/*`) remain identical and exposed on `https://<username>-<spacename>.hf.space`. Both the web app and installed APK connect identically.

### Alternative 2: Cloudflare Quick Tunnel (Mode B)
- **Cost:** Free ($0.00). Zero credit card.
- **Mechanism:** The backend runs locally and is exposed via Cloudflare Quick Tunnel (`https://<subdomain>.trycloudflare.com`).
- **Client Impact:** Both web and Android APK already validate and approve `*.trycloudflare.com`. However, requires the laptop to remain powered on.

### Alternative 3: Render Free Web Service
- **Cost:** Free ($0.00). Free web service does not require a credit card when deployed via GitHub.
- **Limitations:** 512 MB RAM limit and sleeps after 15 minutes of inactivity (30–60s cold start).

---

## 4. Re-Audit of Deployment Payload & Exclusion Boundaries

The deployment payload was independently audited to confirm that zero secrets, credentials, local databases, or client trees can leak.

### Payload Verification Table

| File / Directory | Size / Path | Audit Finding | Exclusion Mechanism | Safe? |
| :--- | :--- | :--- | :--- | :---: |
| `.env` & `.env.*` | Local secrets (`MONGO_URI`, `GROQ_API_KEY`) | **EXCLUDED** | `.dockerignore` + `deploy_huggingface_space.py` filter | **SAFE** |
| `data/*.db` & `*.sqlite*` | `data/auth_store.db`, `data/sessions.db` | **EXCLUDED** | Explicit exclusion in `.dockerignore` and script | **SAFE** |
| `frontend/` | React client tree (Cloudflare Pages) | **EXCLUDED** | Excluded from container payload | **SAFE** |
| `android/` | React Native Android source & APK tree | **EXCLUDED** | Excluded from container payload | **SAFE** |
| `node_modules/` | Build dependencies | **EXCLUDED** | Excluded from container payload | **SAFE** |
| `tools/` | `tools/cloudflared.exe` (52.82 MB) | **EXCLUDED** | Excluded; container payload reduced to **12.65 MB** | **SAFE** |
| Curated Data JSONs | `curated_*.json`, `vector_store.json` | **INCLUDED** | Read-only static knowledge base baked into container | **SAFE** |

> [!IMPORTANT]
> **Manual Browser Upload Safety Note:** A browser drag-and-drop upload does **not** process `.dockerignore`. If a web interface upload is ever performed, only the following folders and files must be selected: `Dockerfile`, `requirements.txt`, `agent.py`, `config.py`, `db.py`, `explore_data.py`, `mongo_db.py`, `mongodb_agent.py`, `weather.py`, `agents/`, `backend/`, `data/*.json`, `knowledge_base/`, `rag/`, `services/`, and `utils/`. **Never upload the project root or `.env` via browser.**

---

## 5. Runtime Configuration & Safety Invariant Validation

The codebase was audited to verify production security invariants:

1. **`PERSISTENCE_BACKEND=mongodb` Fail-Safe:**
   - In `agents/mongo_store.py` (`_get_coll`), when MongoDB is unreachable, the system raises:
     `RuntimeError("CRITICAL PERSISTENCE FAILURE: ... Refusing silent fallback to ephemeral storage.")`
   - In `backend/main.py` (`health_ready`), the readiness probe returns HTTP `503 Service Unavailable` with `{"database": "unavailable_mongodb", "mongodb": "offline"}`.
   - **Zero silent fallback to SQLite in cloud persistence mode.**

2. **Production Auth Secret Gate:**
   - In `agents/auth_service.py` (`validate_and_get_auth_secret`), running with `APP_ENV=production` requires an explicit, unique `AUTH_HMAC_SECRET` of at least 32 characters.
   - Refuses to start with missing, weak, or development default secrets.

3. **Strict Production CORS Filter:**
   - In `backend/main.py` (`resolve_cors_origins`), running in `APP_ENV=production` strictly permits `https://yatra-ai.pages.dev`.
   - Insecure HTTP, localhost (`localhost:5173`, `localhost:3000`), private LAN IPs (`192.168.*`, `10.*`), and wildcards (`*`) are strictly blocked with security violation warnings.
   - Verified via unit test suite: 10/10 CORS tests passing.

---

## 6. Android Runtime Backend Configuration Audit

The installed Android application code was audited for runtime URL adaptability:

1. **User Dynamic Entry:** `android/src/components/ConnectionModal.jsx` and `android/src/screens/SettingsScreen.jsx` provide a dedicated UI for the user to view the active backend and enter a custom public HTTPS URL.
2. **Pre-Save Health Check:** The modal invokes `checkBackendHealth(candidateUrl)` against `/api/health` before allowing the configuration to be saved.
3. **Hardware-Backed Keystore Persistence:** `android/src/utils/storage.js` uses `expo-secure-store` for session tokens and `AsyncStorage` for the backend URL.
4. **Token Isolation Gate:** Calling `setBackendUrl(newUrl)` triggers `await clearAuthToken()`. Session tokens from a previous server are immediately destroyed before connecting to a new origin, preventing token leakage.
5. **No Rebuild Required:** `android/src/utils/urlValidator.js` validates public HTTPS domains against regex patterns including `*.hf.space` and `*.trycloudflare.com`. Changing the backend endpoint does **not** require rebuilding the APK.
   *(Note: Physical confirmation on the installed APK will occur once a reachable public endpoint is provisioned).*

---

## 7. Next Safe Actions

1. **Do not create or pay for a Hugging Face Docker Space.**
2. **Review Alternative 1 (Hugging Face Gradio SDK mounting FastAPI):**
   - If approved, we can create a lightweight `app.py` wrapper that runs the existing FastAPI app inside a free Gradio Space without Docker, requiring $0.00 and zero credit card.
3. **Wait for user direction before taking any further action.**
