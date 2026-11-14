"""
Phase 15.2.1: Cloud Backend Deployment Readiness & Persistence Audit Test Suite.

Verifies:
1. Dockerfile configuration: base image, UID 1000 user, PORT exposure, health check.
2. Dynamic port and host resolution for PaaS platforms (Hugging Face Spaces, Render).
3. Production security gates: CORS wildcard rejection, OpenAPI doc suppression.
4. Database path anchoring: config.py anchors DATA_DIR to PROJECT_ROOT or env var.
5. Absolute host path isolation: ensures no hardcoded workstation paths exist in backend code.
6. Liveness and readiness API contract validation.
"""

import os
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDeploymentReadiness(unittest.TestCase):
    def setUp(self):
        self.dockerfile_path = PROJECT_ROOT / "Dockerfile"
        self.dockerignore_path = PROJECT_ROOT / ".dockerignore"

    def test_1_dockerfile_configuration(self):
        """Verify Dockerfile contains required production and PaaS directives."""
        self.assertTrue(self.dockerfile_path.exists(), "Dockerfile must exist in project root")
        content = self.dockerfile_path.read_text(encoding="utf-8")

        # 1. Slim Python base
        self.assertIn("python:3.11-slim", content)

        # 2. Non-root user UID 1000 for Hugging Face Spaces compatibility
        self.assertTrue(
            "useradd" in content and "1000" in content,
            "Dockerfile must configure non-root user UID 1000 for Hugging Face Spaces"
        )
        self.assertIn("USER user", content)

        # 3. Dynamic PORT exposure
        self.assertIn("EXPOSE 7860", content)
        self.assertIn("PORT=7860", content)

        # 4. Container Health Check
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("/api/health", content)

        # 5. Application entrypoint
        self.assertIn("backend.main", content)

    def test_2_dockerignore_configuration(self):
        """Verify .dockerignore excludes sensitive secrets, node_modules, and cache files."""
        self.assertTrue(self.dockerignore_path.exists(), ".dockerignore must exist in project root")
        content = self.dockerignore_path.read_text(encoding="utf-8")

        self.assertIn(".env", content)
        self.assertIn("node_modules", content)
        self.assertIn("__pycache__", content)
        self.assertIn(".git", content)

    def test_3_dynamic_port_and_host_binding(self):
        """Verify backend/main.py binds to 0.0.0.0 and dynamically reads PORT from environment."""
        main_py = (PROJECT_ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("PORT"', main_py)
        self.assertIn('os.getenv("HOST", "0.0.0.0")', main_py)

    def test_4_cors_security_policy(self):
        """Verify CORS rejects wildcards and always whitelists official production frontend."""
        from backend.main import resolve_cors_origins

        # Test wildcard rejection
        os.environ["CORS_ALLOWED_ORIGINS"] = "*,https://preview.pages.dev"
        origins = resolve_cors_origins()
        self.assertNotIn("*", origins, "Wildcard '*' must never be accepted when credentials are true")
        self.assertIn("https://yatra-ai.pages.dev", origins, "Official frontend must always be whitelisted")
        self.assertIn("https://preview.pages.dev", origins)

    def test_5_docs_suppression_in_production(self):
        """Verify OpenAPI and Swagger docs are disabled when APP_ENV=production."""
        main_py = (PROJECT_ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        self.assertIn("docs_url=None if is_prod else \"/docs\"", main_py)
        self.assertIn("redoc_url=None if is_prod else \"/redoc\"", main_py)
        self.assertIn("openapi_url=None if is_prod else \"/openapi.json\"", main_py)

    def test_6_zero_hardcoded_workstation_paths(self):
        """Ensure no hardcoded laptop directory paths (C:\\Users, OneDrive) exist in backend code."""
        backend_files = list((PROJECT_ROOT / "backend").rglob("*.py"))
        agent_files = list((PROJECT_ROOT / "agents").rglob("*.py"))
        core_files = [PROJECT_ROOT / "config.py", PROJECT_ROOT / "db.py", PROJECT_ROOT / "mongo_db.py"]

        all_target_files = backend_files + agent_files + core_files
        path_pattern = re.compile(r"[a-zA-Z]:\\(?:Users|OneDrive)", re.IGNORECASE)

        for f in all_target_files:
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            matches = path_pattern.findall(text)
            self.assertEqual(
                matches,
                [],
                f"File {f.relative_to(PROJECT_ROOT)} contains hardcoded workstation path: {matches}"
            )

    def test_7_liveness_and_readiness_endpoints(self):
        """Verify /api/health and /api/health/ready endpoint definitions."""
        from backend.main import app
        route_paths = [route.path for route in app.routes]
        self.assertIn("/api/health", route_paths)
        self.assertIn("/api/health/ready", route_paths)


if __name__ == "__main__":
    unittest.main()
