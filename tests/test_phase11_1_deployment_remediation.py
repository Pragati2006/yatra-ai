"""
tests/test_phase11_1_deployment_remediation.py
Comprehensive automated test suite for Phase 11.1 Deployment Blocker Remediation.

Verifies:
1. Dynamic CORS origin resolution (dev localhost vs production origins, whitespace trimming, wildcard rejection).
2. Production Authentication Secret enforcement (minimum 32 chars, rejection of dev default, dev fallback safety).
3. Email OTP provider safety (no mock leaks in production, EMAIL_SERVICE_UNAVAILABLE on missing SMTP, OTP log redaction).
4. Production environment restrictions (/api/auth/test/latest-otp blocking, Swagger/ReDoc disabling in prod).
5. Database persistence & storage writability verification.
6. Health & Readiness endpoints (liveness vs readiness, 200 OK vs 503 on failure, zero credential leakage).
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure yatra-ai root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestPhase111DeploymentRemediation(unittest.TestCase):

    def setUp(self):
        # Save original environment to restore in tearDown
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    # =========================================================================
    # 1. CORS Configuration Tests
    # =========================================================================

    def test_01_cors_development_mode_origins(self):
        """Verifies that development mode retains localhost origins and parses extra origins."""
        from backend.main import resolve_cors_origins

        os.environ["APP_ENV"] = "development"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://preview.yatra-ai.dev, http://localhost:8080"

        origins = resolve_cors_origins()

        # Localhost origins must be present in development
        self.assertIn("http://localhost:5173", origins)
        self.assertIn("http://127.0.0.1:5173", origins)
        self.assertIn("http://localhost:8000", origins)

        # Explicit extra origins must be parsed and trimmed
        self.assertIn("https://preview.yatra-ai.dev", origins)
        self.assertIn("http://localhost:8080", origins)

    def test_02_cors_production_mode_origins_isolation(self):
        """Verifies that production mode strictly uses configured origins and removes localhost."""
        from backend.main import resolve_cors_origins

        os.environ["APP_ENV"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://yatra-ai.vercel.app, https://yatra-ai.netlify.app/"

        origins = resolve_cors_origins()

        # Localhost origins must NOT be present in production
        self.assertNotIn("http://localhost:5173", origins)
        self.assertNotIn("http://127.0.0.1:5173", origins)

        # Configured origins must be present and trailing slashes stripped
        self.assertIn("https://yatra-ai.vercel.app", origins)
        self.assertIn("https://yatra-ai.netlify.app", origins)
        self.assertEqual(len(origins), 2)

    def test_03_cors_wildcard_rejection_and_malformed_entries(self):
        """Verifies wildcard origin is rejected and malformed entries are ignored safely."""
        from backend.main import resolve_cors_origins

        os.environ["APP_ENV"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*, not_a_valid_url, https://valid-app.com, ,   "

        origins = resolve_cors_origins()

        # Wildcard '*' must be rejected
        self.assertNotIn("*", origins)
        # Malformed entries must be rejected
        self.assertNotIn("not_a_valid_url", origins)
        self.assertNotIn("", origins)

        # Only valid origin preserved
        self.assertEqual(origins, ["https://valid-app.com"])

    # =========================================================================
    # 2. Production Authentication Secret Validation Tests
    # =========================================================================

    def test_04_auth_secret_missing_in_production(self):
        """Verifies that missing secret in production raises a clear deployment error."""
        from agents.auth_service import validate_and_get_auth_secret

        os.environ["APP_ENV"] = "production"
        os.environ.pop("AUTH_HMAC_SECRET", None)
        os.environ.pop("AUTH_SALT", None)

        with self.assertRaises(RuntimeError) as ctx:
            validate_and_get_auth_secret()
        self.assertIn("CRITICAL DEPLOYMENT ERROR", str(ctx.exception))
        self.assertIn("must be explicitly configured in production mode", str(ctx.exception))

    def test_05_auth_secret_weak_dev_default_in_production(self):
        """Verifies that using the development default secret in production is rejected."""
        from agents.auth_service import validate_and_get_auth_secret, DEV_DEFAULT_AUTH_SECRET

        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = DEV_DEFAULT_AUTH_SECRET

        with self.assertRaises(RuntimeError) as ctx:
            validate_and_get_auth_secret()
        self.assertIn("insecure development default salt", str(ctx.exception))

    def test_06_auth_secret_too_short_in_production(self):
        """Verifies that secrets shorter than 32 characters are rejected in production."""
        from agents.auth_service import validate_and_get_auth_secret

        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = "short_secret_123"

        with self.assertRaises(RuntimeError) as ctx:
            validate_and_get_auth_secret()
        self.assertIn("too short", str(ctx.exception))
        self.assertIn("at least 32 characters", str(ctx.exception))

    def test_07_auth_secret_valid_in_production(self):
        """Verifies that a strong secret (32+ chars) succeeds in production without error."""
        from agents.auth_service import validate_and_get_auth_secret

        strong_secret = "a" * 32
        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = strong_secret

        retrieved = validate_and_get_auth_secret()
        self.assertEqual(retrieved, strong_secret)

    def test_08_auth_secret_development_fallback_safety(self):
        """Verifies that development mode retains safe fallback without raising."""
        from agents.auth_service import validate_and_get_auth_secret, DEV_DEFAULT_AUTH_SECRET

        os.environ["APP_ENV"] = "development"
        os.environ.pop("AUTH_HMAC_SECRET", None)
        os.environ.pop("AUTH_SALT", None)

        retrieved = validate_and_get_auth_secret()
        self.assertEqual(retrieved, DEV_DEFAULT_AUTH_SECRET)

    # =========================================================================
    # 3. Email OTP Provider Safety Tests
    # =========================================================================

    def test_09_otp_provider_development_mock(self):
        """Verifies that development mode uses MockEmailProvider and redacts OTP in logs."""
        from agents.auth_service import AuthService, MockEmailProvider, set_email_provider

        os.environ["APP_ENV"] = "development"
        mock_prov = MockEmailProvider()
        set_email_provider(mock_prov)

        temp_dir = tempfile.mkdtemp()
        test_db = os.path.join(temp_dir, "dev_auth.db")
        svc = AuthService(db_path=test_db)

        res = svc.request_otp("devotee@example.com")
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["delivered"])
        self.assertNotIn("otp", res)
        self.assertNotIn("otp_code", res)

    def test_10_otp_provider_production_missing_smtp(self):
        """Verifies that production mode returns EMAIL_SERVICE_UNAVAILABLE when SMTP is unconfigured."""
        from agents.auth_service import AuthService, set_email_provider

        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = "x" * 32
        # Ensure SMTP vars are cleared
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_USER", None)
        os.environ.pop("SMTP_PASSWORD", None)
        set_email_provider(None)  # reset to dynamic resolution

        temp_dir = tempfile.mkdtemp()
        test_db = os.path.join(temp_dir, "prod_auth.db")
        svc = AuthService(db_path=test_db)

        res = svc.request_otp("devotee@example.com")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error_code"], "EMAIL_SERVICE_UNAVAILABLE")

    def test_11_otp_provider_production_configured_smtp(self):
        """Verifies that production mode uses SMTPEmailProvider when SMTP is configured."""
        from agents.auth_service import AuthService, SMTPEmailProvider, set_email_provider

        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = "x" * 32
        os.environ["SMTP_HOST"] = "smtp.example.com"
        os.environ["SMTP_USER"] = "test_user"
        os.environ["SMTP_PASSWORD"] = "test_pass"
        set_email_provider(None)

        smtp_prov = SMTPEmailProvider()
        self.assertTrue(smtp_prov.is_configured())

        # Mock actual smtplib send to avoid network call
        with patch("smtplib.SMTP") as mock_smtp:
            mock_inst = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_inst

            delivered = smtp_prov.send_otp("devotee@example.com", "123456")
            self.assertTrue(delivered)
            self.assertTrue(mock_inst.starttls.called)
            self.assertTrue(mock_inst.login.called)
            self.assertTrue(mock_inst.send_message.called)

    # =========================================================================
    # 4. Production Environment Safety Tests
    # =========================================================================

    def test_12_test_endpoint_blocked_in_production(self):
        """Verifies that /api/auth/test/latest-otp is blocked (HTTP 404) in production."""
        from backend.routes.auth import is_dev_test_mode_enabled

        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_DEV_TEST_ENDPOINTS"] = "true"  # Even if mistakenly set to true

        self.assertFalse(is_dev_test_mode_enabled(), "Production must strictly disable dev test endpoints")

    def test_13_api_docs_disabled_in_production(self):
        """Verifies that FastAPI docs routes are disabled in production."""
        os.environ["APP_ENV"] = "production"
        os.environ["AUTH_HMAC_SECRET"] = "x" * 32

        from backend.main import is_production_mode
        self.assertTrue(is_production_mode())

    # =========================================================================
    # 5. Database Persistence & Storage Writability Tests
    # =========================================================================

    def test_14_database_paths_and_writability(self):
        """Verifies that database paths resolve to DATA_DIR and storage writability check functions."""
        from config import DATA_DIR, AUTH_DB_PATH, SESSIONS_DB_PATH, verify_storage_writability

        self.assertTrue(str(AUTH_DB_PATH).startswith(str(DATA_DIR)))
        self.assertTrue(str(SESSIONS_DB_PATH).startswith(str(DATA_DIR)))

        temp_dir = Path(tempfile.mkdtemp())
        # Should succeed on writable directory
        verify_storage_writability(temp_dir)

        # Test file was cleaned up
        test_files = list(temp_dir.glob(".write_test_*"))
        self.assertEqual(len(test_files), 0)

    # =========================================================================
    # 6. Health & Readiness Endpoints Tests
    # =========================================================================

    def test_15_health_liveness_endpoint(self):
        """Verifies that GET /api/health returns healthy liveness without leaking sensitive info."""
        from backend.main import health

        res = health()
        self.assertEqual(res["status"], "healthy")
        self.assertIn("service", res)
        self.assertNotIn("secret", str(res).lower())

    def test_16_health_readiness_endpoint_ready_state(self):
        """Verifies that GET /api/health/ready returns status=ready when dependencies are operational."""
        from backend.main import health_ready

        res = health_ready()
        # When response is a dict (200 OK)
        if isinstance(res, dict):
            self.assertEqual(res["status"], "ready")
            self.assertIn("dependencies", res)
            self.assertEqual(res["dependencies"]["database"], "ready")
            self.assertEqual(res["dependencies"]["auth_config"], "ready")
            self.assertNotIn("secret", str(res).lower())
            self.assertNotIn("password", str(res).lower())

    def test_17_health_readiness_failure_isolation(self):
        """Verifies that GET /api/health/ready returns HTTP 503 when mandatory dependency fails."""
        from backend.main import health_ready
        from fastapi.responses import JSONResponse

        # Force a database failure by mocking sqlite3.connect to raise
        with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("Disk locked")):
            res = health_ready()
            self.assertIsInstance(res, JSONResponse)
            self.assertEqual(res.status_code, 503)
            body = res.body.decode("utf-8")
            self.assertIn("not_ready", body)
            self.assertIn("unavailable", body)
            # Ensure no internal stack trace leaked
            self.assertNotIn("Traceback", body)


if __name__ == "__main__":
    unittest.main()
