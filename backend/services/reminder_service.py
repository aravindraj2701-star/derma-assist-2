"""
Reminder Service — Clinical interval re-scan and review reminder agent.
Handles severity-based scheduling, status transitions, and email dispatch.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from backend.database.models import FollowUpReminder, CaseHistory, User
from backend.services.email_service import send_follow_up_reminder_email

logger = logging.getLogger("derma_assist.reminders")


def auto_schedule_case_reminder(
    db: Session,
    case_id: int,
    user_id: int,
    predicted_disease: str,
    risk_tier: str = "benign",
    symptoms_text: str = "",
) -> FollowUpReminder:
    """
    Evaluates clinical severity and schedules an automated follow-up reminder:
    - Malignant: 5 days (urgent dermatologist evaluation)
    - Pre-cancerous: 21 days (re-check lesion morphology)
    - Benign with alarm features (bleeding, growing, spreading): 10 days
    - Benign stable: 90 days (routine monitoring)
    """
    now = datetime.utcnow()
    sym_lower = (symptoms_text or "").lower()
    dis_lower = (predicted_disease or "").lower()

    is_malignant = "malignant" in risk_tier.lower() or "melanoma" in dis_lower or "carcinoma" in dis_lower
    is_precancerous = "pre-cancerous" in risk_tier.lower() or "actinic" in dis_lower or "keratosis" in dis_lower
    has_alarm_symptoms = any(w in sym_lower for w in ["bleed", "grow", "spread", "increas", "rapid", "itch constant", "painful"])

    if is_malignant:
        scheduled_for = now + timedelta(days=5)
        severity_tier = "malignant"
        notes = "High-risk lesion pattern detected. Urgent clinical in-person dermatologist evaluation is strongly advised."
    elif is_precancerous:
        scheduled_for = now + timedelta(days=21)
        severity_tier = "precancerous"
        notes = "Pre-cancerous classification pattern. Perform interval lesion re-scan and clinical assessment within 3 weeks."
    elif has_alarm_symptoms:
        scheduled_for = now + timedelta(days=10)
        severity_tier = "benign_alarm"
        notes = "Reported dynamic symptom evolution (growth/bleeding). Re-scan lesion in 10 days to monitor for progression."
    else:
        scheduled_for = now + timedelta(days=90)
        severity_tier = "benign_stable"
        notes = "Benign presentation. Routine interval check scheduled in 3 months for preventive skin health monitoring."

    reminder = FollowUpReminder(
        case_id=case_id,
        user_id=user_id,
        reminder_type="patient_rescan",
        severity_tier=severity_tier,
        scheduled_for=scheduled_for,
        status="pending",
        notes=notes,
        created_at=now,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    logger.info(
        f"[REMINDER] Scheduled {severity_tier} reminder for Case #{case_id} "
        f"on {scheduled_for.isoformat()} (User #{user_id})"
    )
    return reminder


def get_user_reminders(db: Session, user_id: int) -> List[FollowUpReminder]:
    """Retrieve all reminders for a user ordered by due date."""
    return (
        db.query(FollowUpReminder)
        .filter(FollowUpReminder.user_id == user_id)
        .order_by(FollowUpReminder.scheduled_for.asc())
        .all()
    )


def dismiss_reminder(db: Session, reminder_id: int, user_id: int) -> Optional[FollowUpReminder]:
    """Mark a reminder as dismissed by the user."""
    reminder = (
        db.query(FollowUpReminder)
        .filter(FollowUpReminder.id == reminder_id, FollowUpReminder.user_id == user_id)
        .first()
    )
    if reminder:
        reminder.status = "dismissed"
        db.commit()
        db.refresh(reminder)
        logger.info(f"[REMINDER] Reminder #{reminder_id} dismissed by user #{user_id}")
    return reminder


def complete_reminder(db: Session, reminder_id: int, user_id: int) -> Optional[FollowUpReminder]:
    """Mark a reminder as completed (e.g. after a re-scan or doctor visit)."""
    reminder = (
        db.query(FollowUpReminder)
        .filter(FollowUpReminder.id == reminder_id, FollowUpReminder.user_id == user_id)
        .first()
    )
    if reminder:
        reminder.status = "completed"
        db.commit()
        db.refresh(reminder)
        logger.info(f"[REMINDER] Reminder #{reminder_id} marked complete by user #{user_id}")
    return reminder


def process_due_reminders(db: Session) -> int:
    """
    Scans for pending reminders that are due (scheduled_for <= now),
    dispatches notification emails, and updates status to 'sent'.
    Returns the count of dispatched reminders.
    """
    now = datetime.utcnow()
    due_reminders = (
        db.query(FollowUpReminder)
        .filter(
            FollowUpReminder.status == "pending",
            FollowUpReminder.scheduled_for <= now,
        )
        .all()
    )

    dispatched_count = 0
    for rem in due_reminders:
        user = db.query(User).filter(User.user_id == rem.user_id).first()
        case = db.query(CaseHistory).filter(CaseHistory.case_id == rem.case_id).first()

        if user and case:
            try:
                send_follow_up_reminder_email(
                    user_email=user.email,
                    user_name=user.name,
                    case_id=case.case_id,
                    predicted_disease=case.predicted_disease or "Cutaneous Lesion",
                    reminder_notes=rem.notes or "Time for your scheduled follow-up re-scan.",
                )
                rem.status = "sent"
                dispatched_count += 1
                logger.info(f"[REMINDER] Sent reminder email for Case #{case.case_id} to {user.email}")
            except Exception as e:
                logger.error(f"[REMINDER] Failed sending reminder email for ID #{rem.id}: {e}")

    if dispatched_count > 0:
        db.commit()

    return dispatched_count


# Background Worker Thread for periodic reminder processing
_worker_started = False

def start_reminder_background_worker(db_factory, interval_seconds: int = 60):
    """Starts an in-process daemon thread to process due reminders periodically."""
    global _worker_started
    if _worker_started:
        return
    _worker_started = True

    def _worker_loop():
        logger.info("[REMINDER] Background reminder dispatcher worker started.")
        while True:
            try:
                db = db_factory()
                try:
                    count = process_due_reminders(db)
                    if count > 0:
                        logger.info(f"[REMINDER] Background worker dispatched {count} due reminders.")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"[REMINDER] Error in background reminder loop: {e}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_worker_loop, daemon=True, name="DermaAssistReminderWorker")
    thread.start()
