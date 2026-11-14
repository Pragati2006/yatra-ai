"""
tests/test_cors_policy.py
Phase 15.2.4: Production and Development CORS Policy & Deployment Exclusion Test Suite.

Verifies:
1. Production mode allows only explicitly approved public HTTPS frontend origins.
2. Production mode strictly excludes localhost and private LAN origins.
3. Production mode rejects wildcard '*' origins.
4. Production mode always preserves the official frontend origin (https://yatra-ai.pages.dev).
5. Development mode allows localhost and private LAN origins for web and Android development.
6. Deployment exclusion rules in .dockerignore and deploy_huggingface_space.py exclude secrets, local SQLite DBs, and client trees.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.main import resolve_cors_origins, is_local_or_lan_origin

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestCorsPolicyAndDeploymentExclusions(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. Private LAN / Localhost Origin Classifier
    # -------------------------------------------------------------------------
    def test_01_is_local_or_lan_origin(self):
        """Correctly classifies localhost, loopback, and RFC 1918 private subnets."""
        self.assertTrue(is_local_or_lan_origin("http://localhost:5173"))
        self.assertTrue(is_local_or_lan_origin("http://127.0.0.1:8000"))
        self.assertTrue(is_local_or_lan_origin("https://localhost:3000"))
        self.assertTrue(is_local_or_lan_origin("http://192.168.1.100:8000"))
        self.assertTrue(is_local_or_lan_origin("http://10.0.2.2:8000"))
        self.assertTrue(is_local_or_lan_origin("http://172.20.10.4:8000"))

        # Public internet domains must return False
        self.assertFalse(is_local_or_lan_origin("https://yatra-ai.pages.dev"))
        self.assertFalse(is_local_or_lan_origin("https://preview.pages.dev"))
        self.assertFalse(is_local_or_lan_origin("https://api.example.com"))

    # -------------------------------------------------------------------------
    # 2. Production CORS Policy
    # -------------------------------------------------------------------------
    def test_02_production_cors_allows_only_approved_public_origins(self):
        """In production mode, only explicit public HTTPS origins are permitted."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "https://preview.pages.dev,https://custom.pages.dev",
        }, clear=True):
            origins = resolve_cors_origins()
            self.assertIn("https://preview.pages.dev", origins)
            self.assertIn("https://custom.pages.dev", origins)
            self.assertIn("https://yatra-ai.pages.dev", origins)

            # Localhost must NOT be present
            self.assertNotIn("http://localhost:5173", origins)
            self.assertNotIn("http://localhost:3000", origins)

    def test_03_production_cors_strictly_rejects_localhost_and_private_lan(self):
        """In production mode, localhost and private LAN origins in env are strictly rejected."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "http://localhost:5173,https://localhost:3000,http://192.168.1.50:8000,https://yatra-ai.pages.dev",
        }, clear=True):
            origins = resolve_cors_origins()
            self.assertNotIn("http://localhost:5173", origins)
            self.assertNotIn("https://localhost:3000", origins)
            self.assertNotIn("http://192.168.1.50:8000", origins)
            self.assertEqual(origins, ["https://yatra-ai.pages.dev"])

    def test_04_production_cors_strictly_rejects_insecure_http_origins(self):
        """In production mode, insecure HTTP origins are strictly rejected."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "http://insecure-frontend.pages.dev,https://secure-frontend.pages.dev",
        }, clear=True):
            origins = resolve_cors_origins()
            self.assertNotIn("http://insecure-frontend.pages.dev", origins)
            self.assertIn("https://secure-frontend.pages.dev", origins)
            self.assertIn("https://yatra-ai.pages.dev", origins)

    def test_05_production_cors_strictly_rejects_wildcard(self):
        """In production mode, wildcard '*' is rejected to prevent credential leaks."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "*,https://preview.pages.dev",
        }, clear=True):
            origins = resolve_cors_origins()
            self.assertNotIn("*", origins)
            self.assertIn("https://preview.pages.dev", origins)
            self.assertIn("https://yatra-ai.pages.dev", origins)

    def test_06_production_cors_default_is_only_official_frontend(self):
        """When CORS_ALLOWED_ORIGINS is unset in production, only the official frontend is allowed."""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            origins = resolve_cors_origins()
            self.assertEqual(origins, ["https://yatra-ai.pages.dev"])

    # -------------------------------------------------------------------------
    # 3. Development CORS Policy
    # -------------------------------------------------------------------------
    def test_07_development_cors_includes_localhost_dev_servers(self):
        """In development mode, standard localhost origins are automatically included."""
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            origins = resolve_cors_origins()
            self.assertIn("http://localhost:5173", origins)
            self.assertIn("http://127.0.0.1:5173", origins)
            self.assertIn("http://localhost:3000", origins)
            self.assertIn("http://localhost:8000", origins)
            self.assertIn("https://yatra-ai.pages.dev", origins)

    def test_08_development_cors_permits_private_lan_for_android_testing(self):
        """In development mode, private LAN origins are accepted for physical Android device testing."""
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "CORS_ALLOWED_ORIGINS": "http://192.168.1.15:8000,http://10.0.2.2:8000",
        }, clear=True):
            origins = resolve_cors_origins()
            self.assertIn("http://192.168.1.15:8000", origins)
            self.assertIn("http://10.0.2.2:8000", origins)
            self.assertIn("http://localhost:5173", origins)

    # -------------------------------------------------------------------------
    # 4. Deployment File Exclusion Checks
    # -------------------------------------------------------------------------
    def test_09_dockerignore_excludes_databases_secrets_and_clients(self):
        """Verify .dockerignore excludes SQLite databases, secrets, and client directories."""
        dockerignore_path = PROJECT_ROOT / ".dockerignore"
        self.assertTrue(dockerignore_path.exists())
        content = dockerignore_path.read_text(encoding="utf-8")

        # Local SQLite databases
        self.assertIn("*.db", content)
        self.assertIn("data/*.db", content)
        self.assertIn("data/auth_store.db", content)
        self.assertIn("data/sessions.db", content)

        # Secrets
        self.assertIn(".env", content)
        self.assertIn(".env.*", content)

        # Clients (not needed in Python backend container)
        self.assertIn("frontend/", content)
        self.assertIn("android/", content)
        self.assertIn("node_modules/", content)

    def test_10_deploy_script_ignores_databases_and_clients(self):
        """Verify deploy_huggingface_space.py ignore_list excludes databases and client trees."""
        deploy_script_path = PROJECT_ROOT / "scripts" / "deploy_huggingface_space.py"
        self.assertTrue(deploy_script_path.exists())
        content = deploy_script_path.read_text(encoding="utf-8")

        self.assertIn('"*.db"', content)
        self.assertIn('"data/*.db"', content)
        self.assertIn('"frontend"', content)
        self.assertIn('"android"', content)
        self.assertIn('".env"', content)


if __name__ == "__main__":
    unittest.main()
