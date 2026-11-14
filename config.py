"""
config.py
Centralized configuration and project path resolution for Yatra AI.
Anchors all relative paths to PROJECT_ROOT regardless of current working directory.
"""

import os
from pathlib import Path

# Project root directory is anchored to this file's directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Automatically load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# Centralized data directory (can be overridden by DATA_DIR env var)
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")).resolve()

# Database file paths
AUTH_DB_PATH = Path(os.getenv("AUTH_DB_PATH", DATA_DIR / "auth_store.db")).resolve()
SESSIONS_DB_PATH = Path(os.getenv("SESSIONS_DB_PATH", DATA_DIR / "sessions.db")).resolve()


def verify_storage_writability(dir_path: Path) -> None:
    """Verifies that the target directory exists and is writable."""
    os.makedirs(dir_path, exist_ok=True)
    test_file = dir_path / f".write_test_{os.getpid()}"
    try:
        with open(test_file, "w") as f:
            f.write("ok")
        if os.path.exists(test_file):
            os.remove(test_file)
    except Exception as exc:
        raise RuntimeError(
            f"CRITICAL STORAGE ERROR: Database directory '{dir_path}' is not writable: {exc}. "
            f"Ensure persistent volume is mounted and permissions allow read/write access."
        ) from exc


# Ensure DATA_DIR exists
os.makedirs(DATA_DIR, exist_ok=True)

# Validate storage writability in production
_env = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()
if _env in ("production", "prod", "live"):
    verify_storage_writability(DATA_DIR)

