"""
Health Router — Liveness and system diagnostics endpoint.
"""

from fastapi import APIRouter
from backend.database.connection import check_db_connection
from backend.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness check — returns server status, version, and database connectivity."""
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status.get("connected") else "degraded",
        "service": "Derma Assist API",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "database": db_status,
    }
