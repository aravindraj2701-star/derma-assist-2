"""
Derma Assist — FastAPI Application Entry Point

AI-Powered Skin Disease Detection and Clinical Decision Support System.

IMPORTANT DISCLAIMER:
This application is a decision-support tool for educational purposes.
It does NOT replace professional medical advice, diagnosis, or treatment.
Always consult a qualified dermatologist for skin-related concerns.
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["PYTHONMALLOC"] = "malloc"
os.environ["MALLOC_ARENA_MAX"] = "2"

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database.init_db import init_database
from backend.database.connection import SessionLocal
from backend.services.symptom_matcher import init_symptom_matcher

# Import routers
from backend.routers import auth, predict, history, diseases, health, admin, dataset, reminders, chat, training
from backend.services.reminder_service import start_reminder_background_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # --- Startup ---
    print("=" * 60, flush=True)
    print("  DERMA ASSIST — Starting up...", flush=True)
    print("=" * 60, flush=True)

    # Initialize database tables
    init_database()

    # Initialize symptom matcher
    try:
        db = SessionLocal()
        try:
            init_symptom_matcher(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[MATCHER NOTICE] Symptom matcher initialization notice: {e}", flush=True)

    # Start Background Follow-up Reminder Dispatcher Worker
    try:
        start_reminder_background_worker(SessionLocal, interval_seconds=60)
    except Exception as e:
        print(f"[WORKER NOTICE] Reminder background worker notice: {e}", flush=True)

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Pre-warm AI Models and Visual Reference Embeddings
    try:
        from backend.services.symptom_first_pipeline import get_trained_model
        from backend.services.reference_embedding_service import build_or_load_reference_index
        from backend.services.dataset_service import init_canonical_references
        print("  Pre-warming neural models and reference image embeddings...", flush=True)
        init_canonical_references()
        get_trained_model()
        build_or_load_reference_index()
        print("  AI models and reference index pre-warmed successfully!", flush=True)
    except Exception as e:
        print(f"[PREWARM NOTICE] Pre-warming notice: {e}", flush=True)

    print(f"  Environment: {settings.APP_ENV}", flush=True)
    print(f"  LLM Provider: {settings.LLM_PROVIDER}", flush=True)
    print(f"  Model Path: {settings.MODEL_PATH}", flush=True)
    print("=" * 60, flush=True)
    print("  DERMA ASSIST — Ready!", flush=True)
    print("=" * 60, flush=True)

    yield

    # --- Shutdown ---
    print("[APP] Shutting down...", flush=True)


# Create FastAPI app
app = FastAPI(
    title="Derma Assist API",
    description=(
        "AI-Powered Skin Disease Detection and Clinical Decision Support System. "
        "This is a screening support tool and does NOT replace professional diagnosis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — supports local dev, Vercel, Render, and all custom domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Normalize HTTP exceptions to clean JSON with status and message."""
    detail_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "status_code": exc.status_code,
            "message": detail_msg,
            "detail": detail_msg,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """Catch-all for internal server errors returning clear JSON."""
    error_msg = str(exc) or "Internal server error occurred during processing."
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "status_code": 500,
            "message": error_msg,
            "detail": error_msg,
        },
    )


# Register routers (both direct and /api prefixes for full deployment compatibility)
all_routers = [
    auth.router, predict.router, history.router, diseases.router,
    health.router, admin.router, dataset.router, reminders.router,
    chat.router, training.router
]
for r in all_routers:
    app.include_router(r)
    app.include_router(r, prefix="/api")

# Root endpoint
@app.get("/")
def root():
    return {
        "name": "Derma Assist API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "disclaimer": (
            "This is an AI-assisted screening tool for educational purposes. "
            "It does NOT replace professional medical advice."
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(settings.APP_ENV == "development"),
    )
