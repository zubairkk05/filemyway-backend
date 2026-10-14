"""FileMyWay PDF Tools Backend - FastAPI application.

Run with:  uvicorn app.main:app --reload --port 8000
"""

import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import router as api_v1

app = FastAPI(
    title="FileMyWay PDF Tools API",
    description="All-in-one free PDF tools: convert, merge, split, compress and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1, prefix="/api/v1")

storage_dir = pathlib.Path(settings.STORAGE_DIR)
storage_dir.mkdir(parents=True, exist_ok=True)


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "FileMyWay PDF Tools API",
        "status": "ok",
        "docs": "/docs",
        "api": "/api/v1/tools",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint showing engine status."""
    engines = {}
    try:
        import pikepdf  # noqa: F401

        engines["pikepdf"] = "available"
    except ImportError:
        engines["pikepdf"] = "unavailable"

    try:
        from PIL import Image  # noqa: F401

        engines["pillow"] = "available"
    except ImportError:
        engines["pillow"] = "unavailable"

    return {
        "status": "ok",
        "engines": engines,
        "concurrency": settings.CONCURRENCY,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
