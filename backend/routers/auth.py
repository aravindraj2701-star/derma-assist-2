"""
Auth Router — Google Sign-In, Email Login/Register, JWT tokens, and Password Reset Flow.
"""

import secrets
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.services.auth_service import (
    verify_google_token,
    create_jwt,
    upsert_user,
    get_current_user,
    log_login_activity,
)
from backend.database.models import User, PasswordResetToken
from backend.utils.hash_utils import hash_password, verify_password
from backend.services.email_service import (
    send_account_created_email,
    send_password_reset_email,
    send_password_changed_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class GoogleLoginRequest(BaseModel):
    token: str


class EmailRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "patient"


class EmailLoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _get_user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "Unknown")


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """Fetch current user profile and role."""
    return {"user": user.to_dict()}


@router.post("/google", response_model=LoginResponse)
def google_login(
    request: GoogleLoginRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate with Google OAuth.
    Accepts a Google ID token, verifies it, creates/updates the user,
    logs activity, and returns a JWT access token.
    """
    ip_addr = _get_client_ip(req)
    user_agent = _get_user_agent(req)

    # Verify Google token
    google_info = verify_google_token(request.token)

    # Upsert user in database
    user = upsert_user(db, google_info)

    # Check if suspended
    if not user.is_active:
        log_login_activity(
            db=db,
            email=user.email,
            user_id=user.user_id,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=False,
            failure_reason="Account suspended",
        )
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact the administrator.",
        )

    # Log successful login
    log_login_activity(
        db=db,
        email=user.email,
        user_id=user.user_id,
        ip_address=ip_addr,
        user_agent=user_agent,
        success=True,
    )

    # Create JWT with role and status
    access_token = create_jwt(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )

    return LoginResponse(
        access_token=access_token,
        user=user.to_dict(),
    )


@router.post("/register", response_model=LoginResponse)
def register(
    request: EmailRegisterRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Register a new user with name, email, password, and chosen role (patient/doctor/admin).
    """
    ip_addr = _get_client_ip(req)
    user_agent = _get_user_agent(req)

    clean_name = request.name.strip()
    clean_email = request.email.strip().lower()
    requested_role = (request.role or "patient").strip().lower()
    if requested_role not in ("patient", "doctor", "admin"):
        requested_role = "patient"

    if not clean_name:
        raise HTTPException(status_code=400, detail="Please enter your full name.")
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Check if user already exists
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        log_login_activity(
            db=db,
            email=clean_email,
            user_id=existing.user_id,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=False,
            failure_reason="Registration attempt with already existing email",
        )
        raise HTTPException(status_code=400, detail="Email is already registered. Please sign in.")

    # Create new user with selected role
    hashed = hash_password(request.password)
    user = User(
        name=clean_name,
        email=clean_email,
        hashed_password=hashed,
        google_id=None,
        profile_picture=None,
        role=requested_role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log registration activity
    log_login_activity(
        db=db,
        email=user.email,
        user_id=user.user_id,
        ip_address=ip_addr,
        user_agent=user_agent,
        success=True,
        failure_reason="Initial registration & login",
    )

    # Send Welcome Email in background
    send_account_created_email(user, background_tasks)

    # Create JWT
    access_token = create_jwt(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )

    return LoginResponse(
        access_token=access_token,
        user=user.to_dict(),
    )


@router.post("/login", response_model=LoginResponse)
def login(
    request: EmailLoginRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email and password.
    Verifies credentials, checks active status, logs activity, and returns a JWT access token.
    """
    ip_addr = _get_client_ip(req)
    user_agent = _get_user_agent(req)

    clean_email = request.email.strip().lower()

    if not clean_email or not request.password:
        raise HTTPException(status_code=400, detail="Please enter both email and password.")

    # Find user by email
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not user.hashed_password:
        log_login_activity(
            db=db,
            email=clean_email,
            user_id=None,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=False,
            failure_reason="User not found or no password set",
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Check account active status
    if not user.is_active:
        log_login_activity(
            db=db,
            email=clean_email,
            user_id=user.user_id,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=False,
            failure_reason="Account suspended",
        )
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact the administrator.",
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        log_login_activity(
            db=db,
            email=clean_email,
            user_id=user.user_id,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=False,
            failure_reason="Invalid password",
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Log successful login
    log_login_activity(
        db=db,
        email=user.email,
        user_id=user.user_id,
        ip_address=ip_addr,
        user_agent=user_agent,
        success=True,
    )

    # Create JWT
    access_token = create_jwt(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )

    return LoginResponse(
        access_token=access_token,
        user=user.to_dict(),
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Initiates a password reset workflow.
    Always returns a generic confirmation message to prevent email enumeration attacks.
    If the email exists, invalidates previous unused tokens and generates a secure reset link.
    """
    clean_email = request.email.strip().lower()
    generic_msg = "If an account exists for this email, a reset link has been sent."

    if not clean_email or "@" not in clean_email:
        # Still return generic message for safe handling
        return MessageResponse(message=generic_msg)

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        # Anti-enumeration: return success message even if user does not exist
        return MessageResponse(message=generic_msg)

    # Invalidate / clean up previous unused tokens for this user
    previous_tokens = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.user_id, PasswordResetToken.used == False)
        .all()
    )
    for old_tok in previous_tokens:
        old_tok.used = True

    # Generate secure random token
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRY_MINUTES)

    reset_token = PasswordResetToken(
        token=token_str,
        user_id=user.user_id,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token)
    db.commit()

    # Build reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token_str}"

    # Asynchronously dispatch reset email
    send_password_reset_email(user, reset_link, background_tasks)

    return MessageResponse(message=generic_msg)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Validates a password reset token and updates the user's password.
    Marks the token as used and dispatches a security confirmation email.
    """
    token_str = request.token.strip()
    new_pwd = request.new_password

    if not token_str:
        raise HTTPException(
            status_code=400,
            detail="Missing password reset token. Please check the link from your email.",
        )

    if len(new_pwd) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters.",
        )

    # Find reset token
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == token_str)
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unrecognized password reset link. Please request a new one.",
        )

    # Check if token is already used
    if reset_token.used:
        raise HTTPException(
            status_code=400,
            detail="This password reset link has already been used. Please request a new one.",
        )

    # Check if token is expired
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="This password reset link has expired. Please request a new one.",
        )

    # Find user
    user = db.query(User).filter(User.user_id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    # Update password & mark token used
    user.hashed_password = hash_password(new_pwd)
    reset_token.used = True
    db.commit()

    # Asynchronously dispatch password changed notification email
    send_password_changed_email(user, background_tasks)

    return MessageResponse(
        message="Your password has been successfully reset. You may now sign in."
    )

