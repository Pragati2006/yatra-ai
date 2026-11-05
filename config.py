"""
config.py
Centralized configuration and project path resolution for Yatra AI.
Anchors all relative paths to PROJECT_ROOT regardless of current working directory.
"""

import os
from pathlib import Path

# Project root directory is anchored to this file's directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Centralized data directory (can be overridden by DATA_DIR env var)
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")).resolve()

# Database file paths
AUTH_DB_PATH = Path(os.getenv("AUTH_DB_PATH", DATA_DIR / "auth_store.db")).resolve()
SESSIONS_DB_PATH = Path(os.getenv("SESSIONS_DB_PATH", DATA_DIR / "sessions.db")).resolve()

# Ensure DATA_DIR exists
os.makedirs(DATA_DIR, exist_ok=True)
