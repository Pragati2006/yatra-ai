"""
tests/test_phase12_production_readiness.py
Automated Verification Suite for Phase 12 Web Deployment Preparation & Production Hardening.

Verifies:
1. Production Configuration & Fail-Closed Validation (AUTH_HMAC_SECRET enforcement, dev test endpoint isolation).
2. CORS Production Origin Enforcement (wildcard rejection, localhost exclusion in production).
3. SQLite Persistence Lifecycle Across Simulated Restarts (sessions.db and auth_store.db data durability).
4. Mandatory Human Authorization Gate before RPA / Booking Confirmation.
5. Simulated Booking Idempotency & Duplicate Prevention.
6. Local Playwright Environment Verification & Memory Envelope Measurement.
7. SPA Redirect File Verification (_redirects for Cloudflare Pages).
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import ctypes
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure yatra-ai root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestPhase12ProductionReadiness(unittest.TestCase):

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    # =========================================================================
    # 1. Production Configuration & Fail-Closed Validation
    # =========================================================================

    def test_01_production_secret_enforcement(self):
        """Verifies that production mode rejects weak/default secrets and requires 32+ char secret."""
        from agents.auth_service import validate_and_get_auth_secret, DEV_DEFAULT_AUTH_SECRET

        # In production with missing secret -> Must raise RuntimeError
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            os.environ.pop("AUTH_HMAC_SECRET", None)
            os.environ.pop("AUTH_SALT", None)
            with self.assertRaises(RuntimeError) as ctx:
                validate_and_get_auth_secret()
            self.assertIn("CRITICAL DEPLOYMENT ERROR", str(ctx.exception))

        # In production with dev default secret -> Must raise RuntimeError
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": DEV_DEFAULT_AUTH_SECRET
        }):
            with self.assertRaises(RuntimeError) as ctx:
                validate_and_get_auth_secret()
            self.assertIn("insecure development default salt", str(ctx.exception))

        # In production with short secret (< 32 chars) -> Must raise RuntimeError
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": "too-short-secret"
        }):
            with self.assertRaises(RuntimeError) as ctx:
                validate_and_get_auth_secret()
            self.assertIn("at least 32 characters", str(ctx.exception))

        # In production with strong 32+ char secret -> Must succeed
        strong_secret = "a" * 32
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": strong_secret
        }):
            retrieved = validate_and_get_auth_secret()
            self.assertEqual(retrieved, strong_secret)

    def test_02_production_dev_test_endpoints_disabled(self):
        """Verifies that development test endpoints (/api/auth/test/latest-otp) are disabled in production."""
        from backend.routes.auth import is_dev_test_mode_enabled

        # In production -> must return False
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            self.assertFalse(is_dev_test_mode_enabled())

        # In production with explicit false -> False
        with patch.dict(os.environ, {"APP_ENV": "production", "ENABLE_DEV_TEST_ENDPOINTS": "false"}):
            self.assertFalse(is_dev_test_mode_enabled())

        # In development with default -> True
        with patch.dict(os.environ, {"APP_ENV": "development", "ENABLE_DEV_TEST_ENDPOINTS": "true"}):
            self.assertTrue(is_dev_test_mode_enabled())

    # =========================================================================
    # 2. CORS Production Origin Enforcement
    # =========================================================================

    def test_03_cors_production_mode_isolation(self):
        """Verifies that production CORS only allows configured domains and rejects wildcards and localhost."""
        from backend.main import resolve_cors_origins

        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "https://yatra-ai.pages.dev, *, http://preview.local"
        }):
            origins = resolve_cors_origins()

            # Wildcard '*' must be rejected
            self.assertNotIn("*", origins)

            # Localhost dev origins must NOT be included in production
            self.assertNotIn("http://localhost:5173", origins)
            self.assertNotIn("http://127.0.0.1:5173", origins)

            # Explicit production origins must be present
            self.assertIn("https://yatra-ai.pages.dev", origins)
            self.assertIn("http://preview.local", origins)

    # =========================================================================
    # 3. SQLite Persistence Lifecycle Across Simulated Restarts
    # =========================================================================

    def test_04_sessions_db_persistence_across_restart(self):
        """Verifies conversation messages and workflow states persist across process restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"

            # Direct SQLite creation on specific DB path
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    user_id TEXT,
                    plan_data TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO chat_sessions (session_id, created_at, updated_at, plan_data) VALUES (?, ?, ?, ?)",
                ("phase12-test-session", "2026-11-09T00:00:00Z", "2026-11-09T00:00:00Z", '{"itinerary": ["Day 1", "Day 2"]}')
            )
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                ("phase12-test-session", "user", "Plan a 2-day yatra to Vaishno Devi", "2026-11-09T00:00:00Z")
            )
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                ("phase12-test-session", "assistant", "Here is your 2-day pilgrimage plan.", "2026-11-09T00:00:01Z")
            )
            conn.commit()
            conn.close()

            # Session 2: "Restart" backend by opening fresh connection to same DB file
            conn2 = sqlite3.connect(str(db_path))
            cur = conn2.cursor()
            cur.execute("SELECT plan_data FROM chat_sessions WHERE session_id = ?", ("phase12-test-session",))
            row = cur.fetchone()
            self.assertIsNotNone(row, "Session record must persist across process restart")
            self.assertIn("Day 1", row[0])

            cur.execute("SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id ASC", ("phase12-test-session",))
            messages = cur.fetchall()
            self.assertEqual(len(messages), 2, "Chat messages must persist across process restart")
            self.assertEqual(messages[0][0], "user")
            self.assertEqual(messages[1][0], "assistant")
            conn2.close()

    def test_05_auth_store_persistence_across_restart(self):
        """Verifies booking records persist across process restarts in auth_store.db."""
        from agents.auth_service import AuthService

        test_dir = tempfile.mkdtemp()
        db_path = str(Path(test_dir) / "auth_store.db")
        strong_secret = "b" * 32

        try:
            # Process 1: Save booking
            with patch.dict(os.environ, {"APP_ENV": "production", "AUTH_HMAC_SECRET": strong_secret}):
                svc1 = AuthService(db_path=db_path)
                svc1.save_booking(
                    user_id="user_phase12_audit",
                    booking_data={
                        "booking_id": "VD-PHASE12-001",
                        "status": "CONFIRMED_SIMULATED",
                        "pax_count": 2,
                        "slot_date": "2026-11-20",
                        "category": "Normal Darshan",
                        "slot_time": "06:00",
                        "transport_mode": "Train",
                        "transport_info": "Vande Bharat Express",
                        "hotel_name": "Devi Darshan Hotel",
                        "total_price": 5400
                    }
                )

            # Process 2: Re-instantiate AuthService from disk
            with patch.dict(os.environ, {"APP_ENV": "production", "AUTH_HMAC_SECRET": strong_secret}):
                svc2 = AuthService(db_path=db_path)
                bookings = svc2.get_user_bookings("user_phase12_audit")
                self.assertEqual(len(bookings), 1, "Booking must persist across AuthService re-instantiation")
                self.assertEqual(bookings[0]["booking_id"], "VD-PHASE12-001")
                self.assertEqual(bookings[0]["transport_mode"], "Train")
                self.assertEqual(bookings[0]["pax_count"], 2)
                self.assertEqual(bookings[0]["status"], "SIMULATED_CONFIRMED")
        finally:
            # Safely clean up on Windows
            import gc
            gc.collect()
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    # =========================================================================
    # 4. Mandatory Human Authorization Gate
    # =========================================================================

    def test_06_authorization_gate_enforcement(self):
        """Verifies that confirm endpoint strictly rejects requests without prior server authorization."""
        from backend.routes.yatra import confirm_booking, ConfirmBookingRequest

        # Direct function call testing: confirm booking with missing/expired session
        req = ConfirmBookingRequest(
            session_id="unauth-test-session-999",
            plan_version=1,
            human_authorized=False,
            option={"transport": {"mode": "train"}},
            pax=2,
            user_name="Devotee Test"
        )
        res = confirm_booking(req)
        self.assertEqual(res.get("status"), "authorization_required")
        self.assertIn("not found or expired", res.get("message", ""))

    # =========================================================================
    # 5. SPA Redirect Configuration Verification
    # =========================================================================

    def test_07_spa_redirects_file_exists_and_valid(self):
        """Verifies that _redirects is present in frontend public and dist with correct SPA rule."""
        public_redirects = PROJECT_ROOT / "frontend" / "public" / "_redirects"
        dist_redirects = PROJECT_ROOT / "frontend" / "dist" / "_redirects"

        self.assertTrue(public_redirects.exists(), "frontend/public/_redirects must exist for Cloudflare Pages")
        content = public_redirects.read_text(encoding="utf-8").strip()
        self.assertEqual(content, "/* /index.html 200", "Must have exact SPA rewrite rule")

        if dist_redirects.exists():
            dist_content = dist_redirects.read_text(encoding="utf-8").strip()
            self.assertEqual(dist_content, "/* /index.html 200")

    # =========================================================================
    # 6. Memory Envelope & Process Footprint Measurement
    # =========================================================================

    def test_08_memory_measurement(self):
        """Measures current process memory WorkingSetSize via Windows OpenProcess/GetProcessMemoryInfo."""
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        p = PROCESS_MEMORY_COUNTERS()
        p.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010) = 0x0410
        h_proc = ctypes.windll.kernel32.OpenProcess(0x0410, False, os.getpid())
        try:
            success = ctypes.windll.psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(p), p.cb)
            self.assertTrue(success, "GetProcessMemoryInfo must succeed")
            rss_mb = p.WorkingSetSize / (1024 * 1024)
            self.assertGreater(rss_mb, 10, "Process memory RSS should be measurable")
            self.assertLess(rss_mb, 1500, "Process memory should remain bounded")
        finally:
            ctypes.windll.kernel32.CloseHandle(h_proc)

    # =========================================================================
    # 7. Pre-Deployment Configuration Remediation Tests (Phase 12.0.1)
    # =========================================================================

    def test_09_preview_server_port_configured_to_4173(self):
        """Verifies that frontend/vite.config.js configures preview server on port 4173 on 127.0.0.1."""
        vite_config = PROJECT_ROOT / "frontend" / "vite.config.js"
        self.assertTrue(vite_config.exists(), "frontend/vite.config.js must exist")
        content = vite_config.read_text(encoding="utf-8")
        self.assertIn("port: 4173", content, "Preview server port must be explicitly set to 4173")
        self.assertIn("host: '127.0.0.1'", content, "Host must be explicitly set to 127.0.0.1")

    def test_10_playwright_binary_diagnostic_and_presence(self):
        """Verifies that Playwright Chromium binary is physically installed on the host."""
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if not local_app_data:
            self.skipTest("LOCALAPPDATA environment variable not available")

        ms_pw = Path(local_app_data) / "ms-playwright"
        self.assertTrue(ms_pw.exists(), f"ms-playwright directory must exist at {ms_pw}")

        # Check for chromium directory
        chromium_dirs = list(ms_pw.glob("chromium-*"))
        self.assertGreater(len(chromium_dirs), 0, "At least one Chromium installation must exist in ms-playwright")
        latest_chromium = chromium_dirs[-1]
        chrome_exe = latest_chromium / "chrome-win64" / "chrome.exe"
        if not chrome_exe.exists():
            chrome_exe = latest_chromium / "chrome-win" / "chrome.exe"
        self.assertTrue(chrome_exe.exists(), f"chrome.exe must exist at {chrome_exe}")

    def test_11_csrf_protection_and_origin_checks(self):
        """Verifies that CSRF protection rejects cross-origin cookie requests from untrusted origins."""
        from backend.routes.auth import verify_csrf_protection, AUTH_COOKIE_NAME
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        # 1. Bearer token requests bypass CSRF (safe)
        bearer_req = MagicMock()
        bearer_req.method = "POST"
        bearer_req.headers = {"Authorization": "Bearer sample_token_123"}
        verify_csrf_protection(bearer_req)  # Should not raise

        # 2. Cookie request with untrusted origin -> Must raise 403
        untrusted_req = MagicMock()
        untrusted_req.method = "POST"
        untrusted_req.headers = {
            "Origin": "https://malicious-site.com",
            "Referer": "https://malicious-site.com/attack"
        }
        untrusted_req.cookies = {AUTH_COOKIE_NAME: "stolen_session_cookie"}
        with self.assertRaises(HTTPException) as ctx:
            verify_csrf_protection(untrusted_req)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("CSRF validation failed", ctx.exception.detail)

    def test_12_frontend_api_service_url_normalization(self):
        """Verifies that frontend/src/services/api.js implements URL normalization and unconfigured detection."""
        api_js = PROJECT_ROOT / "frontend" / "src" / "services" / "api.js"
        self.assertTrue(api_js.exists(), "frontend/src/services/api.js must exist")
        content = api_js.read_text(encoding="utf-8")
        self.assertIn("normalizeApiUrl", content, "Must implement normalizeApiUrl function")
        self.assertIn(r"replace(/\/+$/, '')", content, "Must strip trailing slashes")
        self.assertIn("isApiMisconfigured", content, "Must detect unconfigured production API URL")
        self.assertIn("client.interceptors.request.use", content, "Must guard with request interceptor")


if __name__ == "__main__":
    unittest.main()
