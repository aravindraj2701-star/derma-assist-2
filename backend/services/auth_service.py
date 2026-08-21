"""
Authentication Service — Google OAuth token verification and JWT management.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models import User


def verify_google_token(token: str) -> dict:
    """
    Verify a Google ID token and return user info.
    In development mode without a Google Client ID, accepts a mock token format.
    """
    # Development bypass — accept mock tokens for local testing
    if settings.APP_ENV == "development" and not settings.GOOGLE_CLIENT_ID:
        return _create_dev_user(token)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        return {
            "google_id": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")


def _create_dev_user(token: str) -> dict:
    """Create a development user from a mock token."""
    return {
        "google_id": "dev_" + token[:20],
        "email": "dev@dermaassist.local",
        "name": "Dev User",
        "picture": "",
    }


def create_jwt(user_id: int, email: str, role: str = "patient", is_active: bool = True) -> str:
    """Create a JWT access token for the session containing sub, email, role, and active status."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role or "patient",
        "is_active": bool(is_active),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to get the currently authenticated user and check suspension status."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Support "Bearer <token>" format
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    payload = decode_jwt(token)
    user_id = int(payload.get("sub", 0))

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact the administrator.",
        )

    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that enforces strict server-side Admin role check.
    Returns 403 Forbidden for non-admin accounts.
    """
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrative privileges required. Access denied.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your administrative account is suspended.",
        )
    return user


def get_optional_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency that returns User if valid Bearer token is provided, or None."""
    if not authorization:
        return None
    try:
        token = authorization
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        payload = decode_jwt(token)
        user_id = int(payload.get("sub", 0))
        user = db.query(User).filter(User.user_id == user_id).first()
        if user and not user.is_active:
            return None
        return user
    except Exception:
        return None


def log_login_activity(
    db: Session,
    email: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    failure_reason: Optional[str] = None,
):
    """Log every login attempt (success or failure) to login_activity table."""
    from backend.database.models import LoginActivity

    try:
        activity = LoginActivity(
            user_id=user_id,
            email=email.strip().lower() if email else None,
            login_at=datetime.utcnow(),
            ip_address=ip_address or "127.0.0.1",
            user_agent=user_agent or "Unknown",
            success=success,
            failure_reason=failure_reason,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity
    except Exception as e:
        print(f"[AUTH] Failed to log login activity: {e}")
        db.rollback()
        return None


def log_admin_action(
    db: Session,
    admin_id: int,
    action: str,
    target_user_id: int,
    details: Optional[str] = None,
):
    """Log administrative actions (role changes, account suspensions) to admin_audit_log."""
    from backend.database.models import AdminAuditLog

    try:
        audit = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            timestamp=datetime.utcnow(),
            details=details,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit
    except Exception as e:
        print(f"[AUTH] Failed to log admin audit: {e}")
        db.rollback()
        return None


def upsert_user(db: Session, google_info: dict) -> User:
    """Create or update a user from Google profile info."""
    user = None
    if google_info.get("google_id"):
        user = db.query(User).filter(User.google_id == google_info["google_id"]).first()

    if not user and google_info.get("email"):
        user = db.query(User).filter(User.email == google_info["email"]).first()

    if user:
        # Update google_id/name/picture if changed
        if google_info.get("google_id"):
            user.google_id = google_info["google_id"]
        user.name = google_info.get("name", user.name)
        user.profile_picture = google_info.get("picture", user.profile_picture)
        db.commit()
        return user

    # Create new user - always default to 'patient' role
    user = User(
        google_id=google_info.get("google_id"),
        email=google_info["email"],
        name=google_info.get("name", ""),
        profile_picture=google_info.get("picture", ""),
        role="patient",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

