"""
Derma Assist — Central Configuration
All settings read from environment variables with sensible defaults.
"""

import os
from pydantic_settings import BaseSettings
from pathlib import Path

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/derma_assist"

    # --- Authentication ---
    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # --- Model Paths ---
    MODEL_PATH: str = str(PROJECT_ROOT / "model" / "skin_model.h5")
    CLASS_NAMES_PATH: str = str(PROJECT_ROOT / "model" / "class_names.json")
    MODEL_CONFIG_PATH: str = str(PROJECT_ROOT / "model" / "model_config.json")

    # --- Prediction Settings ---
    IMAGE_WEIGHT: float = 0.70
    SYMPTOM_WEIGHT: float = 0.30
    LOW_CONFIDENCE_THRESHOLD: float = 0.60
    CONFLICT_THRESHOLD: float = 0.30

    # --- LLM Integration ---
    LLM_PROVIDER: str = "none"  # gemini, openai, none
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"

    # --- App Settings ---
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_IMAGE_SIZE_MB: int = 10

    # --- Transactional Email (SMTP) ---
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "support@dermaassist.ai"
    SMTP_FROM_NAME: str = "DermaAssist Clinical Support"
    SMTP_USE_TLS: bool = True

    # --- Frontend & Password Reset ---
    FRONTEND_URL: str = "http://localhost:5173"
    RESET_TOKEN_EXPIRY_MINUTES: int = 60

    # --- Seed Data ---
    DISEASES_CSV: str = str(PROJECT_ROOT / "database" / "diseases.csv")
    SYMPTOMS_CSV: str = str(PROJECT_ROOT / "database" / "disease_symptoms.csv")

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def max_image_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
