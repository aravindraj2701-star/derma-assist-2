"""
Reminders Router — Clinical follow-up interval re-scan endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.connection import get_db
from backend.database.models import User, FollowUpReminder
from backend.services.auth_service import get_current_user
from backend.services.reminder_service import (
    get_user_reminders,
    dismiss_reminder,
    complete_reminder,
    process_due_reminders,
)

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("")
def list_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all follow-up reminders for the current user,
    including real-time due count and status summary.
    """
    reminders = get_user_reminders(db, current_user.user_id)
    now = datetime.utcnow()

    due_count = sum(1 for r in reminders if r.status == "pending" and r.scheduled_for <= now)
    pending_count = sum(1 for r in reminders if r.status in ("pending", "sent"))

    return {
        "reminders": [r.to_dict() for r in reminders],
        "total": len(reminders),
        "due_count": due_count,
        "pending_count": pending_count,
    }


@router.post("/{reminder_id}/dismiss")
def dismiss_user_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss an active follow-up reminder."""
    reminder = dismiss_reminder(db, reminder_id, current_user.user_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found or unauthorized.",
        )
    return {
        "status": "success",
        "message": "Reminder dismissed successfully.",
        "reminder": reminder.to_dict(),
    }


@router.post("/{reminder_id}/complete")
def complete_user_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a follow-up reminder as completed (e.g. after re-scan or consultation)."""
    reminder = complete_reminder(db, reminder_id, current_user.user_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found or unauthorized.",
        )
    return {
        "status": "success",
        "message": "Reminder marked as completed.",
        "reminder": reminder.to_dict(),
    }


@router.post("/process-due")
def trigger_due_reminders_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin / Clinician trigger to process and dispatch due reminders immediately."""
    dispatched = process_due_reminders(db)
    return {
        "status": "success",
        "dispatched_count": dispatched,
        "message": f"Processed due reminders. Dispatched {dispatched} reminder emails.",
    }
