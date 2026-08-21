"""
Health Router — Liveness check endpoint.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness check — returns OK if the server is running."""
    return {
        "status": "healthy",
        "service": "Derma Assist API",
        "version": "1.0.0",
    }
