"""
Derma Assist — FastAPI Application Entry Point

AI-Powered Skin Disease Detection and Clinical Decision Support System.

IMPORTANT DISCLAIMER:
This application is a decision-support tool for educational purposes.
It does NOT replace professional medical advice, diagnosis, or treatment.
Always consult a qualified dermatologist for skin-related concerns.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

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
    print("=" * 60)
    print("  DERMA ASSIST — Starting up...")
    print("=" * 60)

    # Initialize database tables
    init_database()

    # Initialize symptom matcher
    db = SessionLocal()
    try:
        init_symptom_matcher(db)
    finally:
        db.close()

    # Start Background Follow-up Reminder Dispatcher Worker
    start_reminder_background_worker(SessionLocal, interval_seconds=60)

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    print(f"  Environment: {settings.APP_ENV}")
    print(f"  LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  Model Path: {settings.MODEL_PATH}")
    print("=" * 60)
    print("  DERMA ASSIST — Ready!")
    print("=" * 60)

    yield

    # --- Shutdown ---
    print("[APP] Shutting down...")


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(diseases.router)
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(dataset.router)
app.include_router(reminders.router)
app.include_router(chat.router)
app.include_router(training.router)

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
