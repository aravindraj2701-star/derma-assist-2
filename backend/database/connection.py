"""
Database connection — SQLAlchemy engine and session factory with SSL support and fallback resilience.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings, PROJECT_ROOT

logger = logging.getLogger("derma_assist.database")

Base = declarative_base()


def _build_engine():
    raw_url = (settings.DATABASE_URL or "").strip()

    # Handle empty or default
    if not raw_url:
        sqlite_path = PROJECT_ROOT / "derma_assist.db"
        raw_url = f"sqlite:///{sqlite_path.as_posix()}"

    # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # SQLite
    if raw_url.startswith("sqlite"):
        if raw_url.startswith("sqlite:///./") or raw_url == "sqlite:///derma_assist.db":
            sqlite_path = PROJECT_ROOT / "derma_assist.db"
            raw_url = f"sqlite:///{sqlite_path.as_posix()}"
        print(f"[DB] Connected to SQLite database: {raw_url}")
        return create_engine(
            raw_url,
            connect_args={"check_same_thread": False},
            echo=(settings.APP_ENV == "development"),
        )

    # PostgreSQL / MySQL
    # Check if host is internal (e.g. Render internal dpg-xxx or localhost)
    is_internal = (
        "localhost" in raw_url
        or "127.0.0.1" in raw_url
        or ("dpg-" in raw_url and ".render.com" not in raw_url)
    )

    # Strategy 1: Attempt connection with appropriate SSL setting
    connect_attempts = []
    if not is_internal and "sslmode=" not in raw_url:
        connect_attempts.append({"sslmode": "require"})
    connect_attempts.append({})  # No explicit sslmode (uses server default or URL param)

    last_error = None
    for connect_args in connect_attempts:
        try:
            eng = create_engine(
                raw_url,
                connect_args=connect_args,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=(settings.APP_ENV == "development"),
            )
            with eng.connect() as conn:
                pass
            print(f"[DB] Successfully connected to PostgreSQL (SSL: {bool(connect_args.get('sslmode'))})")
            return eng
        except Exception as e:
            last_error = e

    # If all PostgreSQL attempts failed, fall back to SQLite
    print(f"[DB WARNING] Failed to connect to PostgreSQL ({last_error}).")
    print("[DB WARNING] Falling back to local SQLite database so the API remains online.")
    sqlite_path = PROJECT_ROOT / "derma_assist.db"
    return create_engine(
        f"sqlite:///{sqlite_path.as_posix()}",
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
