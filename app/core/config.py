"""Application settings.

Deliberately dependency-free (no pydantic) so it works regardless of the
pydantic v1/v2 version shipped with the installed FastAPI.
"""

import os
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _env_list(name: str, default):
    raw = os.environ.get(name)
    if not raw:
        return default
    return [value.strip() for value in raw.split(",") if value.strip()]


class Settings:
    def __init__(self) -> None:
        self.PORT: int = int(os.environ.get("PORT", "8000"))
        self.NODE_ENV: str = os.environ.get("NODE_ENV", "development")
        self.ALLOWED_ORIGINS = _env_list(
            "ALLOWED_ORIGINS",
            [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ],
        )
        self.STORAGE_DIR: str = os.environ.get(
            "STORAGE_DIR", str(_BACKEND_ROOT / "storage")
        )
        self.MAX_FILE_MB: int = int(os.environ.get("MAX_FILE_MB", "100"))
        self.MAX_TOTAL_MB: int = int(os.environ.get("MAX_TOTAL_MB", "500"))
        self.MAX_PAGES: int = int(os.environ.get("MAX_PAGES", "100"))
        self.JOB_TTL_MIN: int = int(os.environ.get("JOB_TTL_MIN", "30"))
        self.POST_DOWNLOAD_GRACE_MIN: int = int(
            os.environ.get("POST_DOWNLOAD_GRACE_MIN", "5")
        )
        self.CONCURRENCY: int = int(os.environ.get("CONCURRENCY", "2"))
        self.DOWNLOAD_SECRET: str = os.environ.get("DOWNLOAD_SECRET", "change_me")
        self.CRON_SECRET: str = os.environ.get("CRON_SECRET", "change_me")
        self.PYTHON_BIN: str = os.environ.get("PYTHON_BIN", "python")
        self.WORKER_DIR: str = os.environ.get("WORKER_DIR", str(_BACKEND_ROOT / "app"))
        self.PY_WORKER_TIMEOUT_SEC: int = int(
            os.environ.get("PY_WORKER_TIMEOUT_SEC", "300")
        )
        self.PY_WORKER_MEM_MB: int = int(os.environ.get("PY_WORKER_MEM_MB", "0"))


settings = Settings()
