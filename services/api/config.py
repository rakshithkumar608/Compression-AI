"""
Configuration settings for EcoCompress AI FastAPI Backend.
Anchors database and artifact paths safely to D: drive.
"""

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    # App Settings
    app_name: str = "EcoCompress AI Core API"
    app_version: str = "0.2.0"
    debug: bool = False

    # Server Bindings
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # CORS Configuration
    frontend_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Storage Paths (Guarded to D: drive)
    base_dir: Path = Path("D:/Projects/Compression AI")
    data_dir: Path = Path(os.getenv("ECOCOMPRESS_DATA_DIR", "D:/Projects/Compression AI/data"))
    db_path: Path = Path(os.getenv("ECOCOMPRESS_DB_PATH", "D:/Projects/Compression AI/data/ecocompress.db"))
    artifacts_dir: Path = Path(os.getenv("ECOCOMPRESS_ARTIFACTS_DIR", "D:/Projects/Compression AI/artifacts"))


settings = Settings()

# Ensure runtime directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
