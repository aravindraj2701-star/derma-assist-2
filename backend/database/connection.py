"""
Database connection — SQLAlchemy engine and session factory with SSL support and fallback resilience.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("derma_assist.database")

Base = declarative_base()


def _build_engine():
    raw_url = (settings.DATABASE_URL or "").strip()

    # Handle empty or default
    if not raw_url:
        raw_url = "sqlite:///./derma_assist.db"

    # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # SQLite
    if raw_url.startswith("sqlite"):
        return create_engine(
            raw_url,
            connect_args={"check_same_thread": False},
            echo=(settings.APP_ENV == "development"),
        )

    # PostgreSQL / MySQL
    try:
        connect_args = {}
        # Ensure SSL requirement for remote cloud databases (Render, Supabase, Neon, AWS)
        if "sslmode=" not in raw_url and "localhost" not in raw_url and "127.0.0.1" not in raw_url:
            connect_args["sslmode"] = "require"

        eng = create_engine(
            raw_url,
            connect_args=connect_args,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=(settings.APP_ENV == "development"),
        )
        # Test connection immediately
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        print(f"[DB WARNING] Failed to connect to PostgreSQL ({e}).")
        print("[DB WARNING] Falling back to local SQLite database so the API remains online.")
        return create_engine(
            "sqlite:///./derma_assist.db",
            connect_args={"check_same_thread": False},
            echo=False,
        )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
