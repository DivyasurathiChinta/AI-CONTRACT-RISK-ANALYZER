"""
app/main.py
-----------
FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from routers import upload, analysis
from app.config import settings
from utils.logger import logger, format_api_error
from services.gemini_service import get_gemini_service

import os


# ──────────────────────────────────────────────────────────────────────────────
# Application Lifespan
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)

    os.makedirs(settings.upload_dir, exist_ok=True)

    logger.info(
        f"Upload directory: {os.path.abspath(settings.upload_dir)}"
    )

    if not settings.validate_gemini_key():

        logger.error(
            "⚠️ GEMINI_API_KEY is not configured."
        )

    else:

        logger.info(
            f"Gemini configured ({settings.gemini_model})"
        )

        # Test Gemini connection at startup
        try:

            gemini = get_gemini_service()

            response = gemini.generate(
                "Reply only with OK"
            )

            logger.info(
                f"Gemini startup test passed: {response}"
            )

        except Exception as e:

            logger.exception(
                "Gemini startup test FAILED"
            )

    logger.info(
        f"API docs: http://{settings.api_host}:{settings.api_port}/docs"
    )

    logger.info(f"Debug mode: {settings.debug}")
    logger.info("Server ready ✓")

    yield

    logger.info("Server shutting down...")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="""
## AI Contract Risk Analyzer API

Automatically analyze legal contracts using Google Gemini AI.

### Features
- PDF Upload
- Clause Extraction
- Risk Analysis
- Missing Clause Detection
- Executive Summary

### Tech Stack
- FastAPI
- Google Gemini 2.0 Flash
- PyMuPDF
- Streamlit
""",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ──────────────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:3000",
        "https://*.streamlit.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Global Exception Handler
# ──────────────────────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on {}", request.url.path)

    return JSONResponse(
        status_code=500,
        content={
            "detail": format_api_error(exc),
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(analysis.router)


# ──────────────────────────────────────────────────────────────────────────────
# Root
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():

    return JSONResponse(
        content={
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "gemini_test": "/test-gemini",
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Root"])
async def health_check():

    gemini_ok = settings.validate_gemini_key()

    upload_dir_ok = os.path.exists(
        settings.upload_dir
    )

    overall_healthy = (
        gemini_ok and upload_dir_ok
    )

    return JSONResponse(
        status_code=200 if overall_healthy else 503,
        content={
            "status": (
                "healthy"
                if overall_healthy
                else "degraded"
            ),
            "checks": {
                "gemini_api": (
                    "configured"
                    if gemini_ok
                    else "missing_api_key"
                ),
                "upload_directory": (
                    "exists"
                    if upload_dir_ok
                    else "missing"
                ),
            },
            "version": settings.app_version,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Gemini Debug Endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/test-gemini")
async def test_gemini():

    try:

        gemini = get_gemini_service()

        response = gemini.generate(
            "Reply only with SUCCESS"
        )

        return {
            "success": True,
            "model": settings.gemini_model,
            "response": response,
        }

    except Exception as e:

        logger.exception(
            "Gemini test endpoint failed"
        )

        return {
            "success": False,
            "model": settings.gemini_model,
            "error": str(e),
            "error_type": type(e).__name__,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Dev Server
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )