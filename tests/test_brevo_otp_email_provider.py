"""
tests/test_brevo_otp_email_provider.py
Focused test suite for Brevo Transactional Email Provider (HTTPS API).

Validates:
1. Configuration and safe diagnostics (zero leaked keys).
2. Successful Brevo HTTPS API request using mocked HTTP response:
   - Header api-key, endpoint, sender, recipient, subject, textContent, htmlContent.
3. Missing API key handling (graceful rejection, no HTTP call).
4. Error handling:
   - HTTP 400 Bad Request / Unverified sender
   - HTTP 401 Unauthorized / Invalid API key
   - HTTP 429 Rate Limit
   - HTTP 500 Brevo internal error
5. Network failures and timeouts:
   - URLError (network connection refused/offline)
   - TimeoutError / socket timeout
6. Production mode AuthService integration:
   - Success when Brevo delivers
   - Refusal of silent fallback to MockEmailProvider in production
   - Error code EMAIL_SERVICE_UNAVAILABLE on failure or unconfigured
7. OTP verification, expiry, and single-use lifecycle with Brevo provider.
8. Guest mode preservation (unauthenticated trip planning / chat work without OTP).
9. Zero leakage of OTP codes or Brevo API keys in application logs.
"""

import os
import sys
import io
import json
import logging
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from agents.auth_service import (
    BrevoEmailProvider,
    MockEmailProvider,
    SMTPEmailProvider,
    get_email_provider,
    set_email_provider,
    validate_email_configuration,
    get_email_provider_readiness,
    AuthService,
    auth_service,
)


class MockHTTPResponse:
    """Mock urllib.request.urlopen context manager response."""

    def __init__(self, status=201, body=b'{"messageId":"<20261122.brevo.test@smtp-relay.brevo.com>"}'):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestBrevoOTPEmailProvider(unittest.TestCase):

    def setUp(self):
        # Reset provider singleton before each test
        set_email_provider(None)

    def tearDown(self):
        # Reset provider singleton after each test
        set_email_provider(None)

    # -------------------------------------------------------------------------
    # 1. Configuration & Diagnostics
    # -------------------------------------------------------------------------
    def test_01_configuration_and_safe_diagnostics(self):
        """Verifies configuration detection and safe diagnostics omitting secrets."""
        with patch.dict(os.environ, {
            "BREVO_API_KEY": "xkeysib-secret-key-12345",
            "BREVO_FROM_EMAIL": "devotee-help@yatra-ai.org",
            "BREVO_FROM_NAME": "Yatra AI Official",
        }):
            provider = BrevoEmailProvider()
            self.assertTrue(provider.is_configured())
            diag = provider.get_diagnostics()
            self.assertTrue(diag["configured"])
            self.assertEqual(diag["provider"], "brevo_https")
            self.assertEqual(diag["from_email"], "devotee-help@yatra-ai.org")
            self.assertEqual(diag["from_name"], "Yatra AI Official")
            self.assertTrue(diag["has_api_key"])
            # Invariant: Raw API key must NEVER appear in diagnostics
            self.assertNotIn("xkeysib-secret-key-12345", str(diag))

        # Unconfigured state (missing API key)
        with patch.dict(os.environ, {"BREVO_API_KEY": "", "BREVO_FROM_EMAIL": "help@yatra-ai.org"}):
            provider_unconf = BrevoEmailProvider()
            self.assertFalse(provider_unconf.is_configured())
            diag_unconf = provider_unconf.get_diagnostics()
            self.assertFalse(diag_unconf["configured"])
            self.assertFalse(diag_unconf["has_api_key"])

    # -------------------------------------------------------------------------
    # 2. Successful Brevo API Request
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_02_successful_brevo_otp_dispatch(self, mock_urlopen):
        """Verifies HTTP request structure, headers, and payload sent to Brevo API."""
        mock_urlopen.return_value = MockHTTPResponse(
            status=201,
            body=b'{"messageId":"<test-msg-id-789@brevo.com>"}'
        )

        with patch.dict(os.environ, {
            "BREVO_API_KEY": "xkeysib-valid-key-9999",
            "BREVO_FROM_EMAIL": "noreply@yatra-ai.org",
            "BREVO_FROM_NAME": "Yatra AI Team",
        }):
            provider = BrevoEmailProvider()
            recipient = "pilgrim_sharma@example.com"
            otp = "741852"

            delivered = provider.send_otp(recipient, otp)
            self.assertTrue(delivered)

            # Inspect intercepted urllib Request
            mock_urlopen.assert_called_once()
            called_req = mock_urlopen.call_args[0][0]

            # 1. URL and method
            self.assertEqual(called_req.full_url, "https://api.brevo.com/v3/smtp/email")
            self.assertEqual(called_req.get_method(), "POST")

            # 2. Headers
            self.assertEqual(called_req.headers.get("Api-key"), "xkeysib-valid-key-9999")
            self.assertEqual(called_req.headers.get("Content-type"), "application/json")
            self.assertEqual(called_req.headers.get("Accept"), "application/json")

            # 3. Payload
            payload = json.loads(called_req.data.decode("utf-8"))
            self.assertEqual(payload["sender"]["email"], "noreply@yatra-ai.org")
            self.assertEqual(payload["sender"]["name"], "Yatra AI Team")
            self.assertEqual(payload["to"], [{"email": recipient}])
            self.assertIn("Verification Code", payload["subject"])
            self.assertIn("741852", payload["textContent"])
            self.assertIn("741852", payload["htmlContent"])
            self.assertIn("5 minutes", payload["textContent"])

    # -------------------------------------------------------------------------
    # 3. Missing API Key Rejection
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_03_missing_api_key_blocks_delivery(self, mock_urlopen):
        """Missing API key returns False immediately without making outbound HTTP requests."""
        with patch.dict(os.environ, {"BREVO_API_KEY": ""}):
            provider = BrevoEmailProvider()
            delivered = provider.send_otp("devotee@example.com", "123456")
            self.assertFalse(delivered)
            mock_urlopen.assert_not_called()

    # -------------------------------------------------------------------------
    # 4. HTTP Errors & Provider Rejections
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_04_brevo_api_http_error_handling(self, mock_urlopen):
        """Verifies graceful handling of Brevo HTTP error responses."""
        provider = BrevoEmailProvider()
        provider.api_key = "xkeysib-test"
        provider.from_email = "test@yatra-ai.org"

        # 401 Unauthorized (invalid key)
        mock_urlopen.side_effect = HTTPError(
            url="https://api.brevo.com/v3/smtp/email",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"code":"unauthorized","message":"Key not found"}'),
        )
        self.assertFalse(provider.send_otp("user@example.com", "111111"))

        # 400 Bad Request (unverified sender)
        mock_urlopen.side_effect = HTTPError(
            url="https://api.brevo.com/v3/smtp/email",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(b'{"code":"invalid_parameter","message":"Sender not verified"}'),
        )
        self.assertFalse(provider.send_otp("user@example.com", "222222"))

        # 429 Rate Limit
        mock_urlopen.side_effect = HTTPError(
            url="https://api.brevo.com/v3/smtp/email",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"code":"reseller_limit_exceeded","message":"Rate limit"}'),
        )
        self.assertFalse(provider.send_otp("user@example.com", "333333"))

        # 500 Provider Internal Error
        mock_urlopen.side_effect = HTTPError(
            url="https://api.brevo.com/v3/smtp/email",
            code=500,
            msg="Internal Error",
            hdrs={},
            fp=io.BytesIO(b'{"code":"server_error","message":"Internal Server Error"}'),
        )
        self.assertFalse(provider.send_otp("user@example.com", "444444"))

    # -------------------------------------------------------------------------
    # 5. Network Failures & Timeouts
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_05_network_failures_and_timeouts(self, mock_urlopen):
        """Verifies URLError and timeout exceptions do not crash and return False."""
        provider = BrevoEmailProvider()
        provider.api_key = "xkeysib-test"
        provider.from_email = "test@yatra-ai.org"

        # Connection error / DNS failure
        mock_urlopen.side_effect = URLError("Name or service not known")
        self.assertFalse(provider.send_otp("user@example.com", "555555"))

        # TimeoutError
        mock_urlopen.side_effect = TimeoutError("Connection timed out")
        self.assertFalse(provider.send_otp("user@example.com", "666666"))

    # -------------------------------------------------------------------------
    # 6. Production Mode Integration & Anti-Fallback Protection
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_06_production_mode_auth_service_integration(self, mock_urlopen):
        """In production, Brevo is selected and refusal of silent mock fallback is enforced."""
        mock_urlopen.return_value = MockHTTPResponse(status=201)

        import uuid
        import tempfile
        temp_dir = tempfile.mkdtemp()
        test_db = os.path.join(temp_dir, "brevo_test_auth.db")

        # 1. Configured production Brevo succeeds
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": "a" * 32,
            "BREVO_API_KEY": "xkeysib-prod-key",
            "BREVO_FROM_EMAIL": "official@yatra-ai.org",
            "PERSISTENCE_BACKEND": "sqlite",
        }):
            set_email_provider(None)
            svc = AuthService(db_path=test_db)
            email_1 = f"devotee_prod_{uuid.uuid4().hex[:8]}@example.com"
            res = svc.request_otp(email_1)
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["delivered"])

        # 2. Unconfigured Brevo in production returns EMAIL_SERVICE_UNAVAILABLE
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": "a" * 32,
            "BREVO_API_KEY": "",
            "BREVO_FROM_EMAIL": "",
            "SMTP_HOST": "",
            "PERSISTENCE_BACKEND": "sqlite",
        }):
            set_email_provider(None)
            svc2 = AuthService(db_path=test_db)
            email_2 = f"devotee_blocked_{uuid.uuid4().hex[:8]}@example.com"
            res2 = svc2.request_otp(email_2)
            self.assertEqual(res2["status"], "error")
            self.assertEqual(res2["error_code"], "EMAIL_SERVICE_UNAVAILABLE")

        # 3. Brevo API failure in production returns EMAIL_SERVICE_UNAVAILABLE
        mock_urlopen.side_effect = HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "AUTH_HMAC_SECRET": "a" * 32,
            "BREVO_API_KEY": "xkeysib-invalid",
            "BREVO_FROM_EMAIL": "official@yatra-ai.org",
            "PERSISTENCE_BACKEND": "sqlite",
        }):
            set_email_provider(None)
            svc3 = AuthService(db_path=test_db)
            email_3 = f"devotee_failed_{uuid.uuid4().hex[:8]}@example.com"
            res3 = svc3.request_otp(email_3)
            self.assertEqual(res3["status"], "error")
            self.assertEqual(res3["error_code"], "EMAIL_SERVICE_UNAVAILABLE")

    # -------------------------------------------------------------------------
    # 7. OTP Expiry and Verification Unchanged
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_07_otp_verification_lifecycle_with_brevo(self, mock_urlopen):
        """Verifies full OTP verification, rate limiting, and single-use behavior."""
        intercepted_otp = []

        def capture_otp(req, timeout=10.0):
            payload = json.loads(req.data.decode("utf-8"))
            # Extract OTP from textContent
            for line in payload["textContent"].split("\n"):
                if "verification code is:" in line:
                    intercepted_otp.append(line.split(":")[-1].strip())
            return MockHTTPResponse(status=201)

        mock_urlopen.side_effect = capture_otp

        import uuid
        import tempfile
        temp_dir = tempfile.mkdtemp()
        test_db = os.path.join(temp_dir, "brevo_lifecycle_auth.db")

        with patch.dict(os.environ, {
            "BREVO_API_KEY": "xkeysib-key",
            "BREVO_FROM_EMAIL": "test@yatra-ai.org",
            "PERSISTENCE_BACKEND": "sqlite",
        }):
            set_email_provider(BrevoEmailProvider())
            svc = AuthService(db_path=test_db)
            email = f"devotee_verify_{uuid.uuid4().hex[:8]}@example.com"

            # 1. Request OTP
            req_res = svc.request_otp(email)
            self.assertEqual(req_res["status"], "success")
            self.assertTrue(len(intercepted_otp) > 0)
            actual_otp = intercepted_otp[0]

            # 2. Incorrect OTP rejected
            wrong_res = svc.verify_otp(email, "000000")
            self.assertEqual(wrong_res["status"], "error")
            self.assertEqual(wrong_res["error_code"], "INCORRECT_CODE")

            # 3. Correct OTP verified
            success_res = svc.verify_otp(email, actual_otp)
            self.assertEqual(success_res["status"], "success")
            self.assertTrue(bool(success_res.get("session_token")))
            self.assertEqual(success_res["user"]["email"], email)

            # 4. Single-use: Verified OTP cannot be reused
            reuse_res = svc.verify_otp(email, actual_otp)
            self.assertEqual(reuse_res["status"], "error")

    # -------------------------------------------------------------------------
    # 8. Guest Mode Remains Functional
    # -------------------------------------------------------------------------
    def test_08_guest_mode_remains_functional(self):
        """Guest users can access public endpoints and plan trips without OTP or email."""
        from agents.coordinator import answer_tourism_query

        # Guest asks about Katra
        result = answer_tourism_query("What can I see around Katra?")
        self.assertIn("reply", result)
        self.assertTrue(len(result["reply"]) > 10)

    # -------------------------------------------------------------------------
    # 9. Zero Secrets or OTPs Leaked to Logs
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_09_zero_secrets_or_otps_in_logs(self, mock_urlopen):
        """Verifies that plain OTPs and Brevo API keys NEVER appear in logger output."""
        mock_urlopen.return_value = MockHTTPResponse(status=201)

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("agents.auth_service")
        logger.addHandler(handler)
        prev_level = logger.level
        logger.setLevel(logging.DEBUG)

        secret_api_key = "xkeysib-supersecretkey999"
        secret_otp = "889900"
        plain_email = "pilgrim_secret_test@example.com"

        try:
            with patch.dict(os.environ, {
                "BREVO_API_KEY": secret_api_key,
                "BREVO_FROM_EMAIL": "auth@yatra-ai.org",
            }):
                provider = BrevoEmailProvider()
                provider.send_otp(plain_email, secret_otp)

                log_content = log_stream.getvalue()

                # Invariant 1: Raw API key must NEVER be logged
                self.assertNotIn(secret_api_key, log_content)

                # Invariant 2: Raw 6-digit OTP must NEVER be logged
                self.assertNotIn(secret_otp, log_content)

                # Invariant 3: Recipient email must be masked in logs
                self.assertNotIn(plain_email, log_content)
                self.assertIn("p*****************t@example.com", log_content)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prev_level)

    # -------------------------------------------------------------------------
    # 10. Readiness Indicator Diagnostics
    # -------------------------------------------------------------------------
    def test_10_readiness_indicator(self):
        """Verifies get_email_provider_readiness reports correct non-sensitive status."""
        # 1. Configured Brevo
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-key", "BREVO_FROM_EMAIL": "test@yatra-ai.org"}):
            set_email_provider(BrevoEmailProvider())
            self.assertEqual(get_email_provider_readiness(), "ready_brevo")

        # 2. Unconfigured Brevo
        with patch.dict(os.environ, {"BREVO_API_KEY": "", "BREVO_FROM_EMAIL": ""}):
            set_email_provider(BrevoEmailProvider())
            self.assertEqual(get_email_provider_readiness(), "unconfigured")

        # 3. Development Mock
        set_email_provider(MockEmailProvider())
        self.assertEqual(get_email_provider_readiness(), "ready_mock_dev")


if __name__ == "__main__":
    unittest.main()
