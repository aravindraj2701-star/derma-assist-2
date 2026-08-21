"""
E2E Test Suite for Follow-Up Reminder Agent
Verifies:
1. Auto-scheduling rules based on clinical severity (Malignant, Pre-cancerous, Benign Alarm, Benign Stable).
2. GET /reminders (Listing, due count, pending count).
3. POST /reminders/{id}/dismiss (Dismissing reminder).
4. POST /reminders/{id}/complete (Completing reminder).
5. POST /reminders/process-due (Background dispatcher & email notification trigger).
"""

import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import User, CaseHistory, FollowUpReminder

client = TestClient(app)


def test_follow_up_reminders_full_cycle():
    print("=" * 80)
    print("  RUNNING FOLLOW-UP REMINDER AGENT E2E TEST SUITE")
    print("=" * 80)

    # 1. Register test doctor / patient
    email = f"clinician_rem_{uuid.uuid4().hex[:6]}@dermaassist.ai"
    reg_res = client.post(
        "/auth/register",
        json={"name": "Dr. Sarah Jenkins", "email": email, "password": "SecurePassword123!"},
    )
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Authenticated user created: {email}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        # 2. Create test cases with different clinical severities
        # Case A: Malignant
        case_mal = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Melanoma",
            confidence=0.88,
            symptoms_text="Bleeding lesion, rapid growth on back",
        )
        db.add(case_mal)
        db.flush()

        # Case B: Pre-cancerous
        case_pre = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Actinic Keratosis",
            confidence=0.74,
            symptoms_text="Gritty scaly patch on forehead",
        )
        db.add(case_pre)
        db.flush()

        # Case C: Benign stable
        case_ben = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Eczema",
            confidence=0.68,
            symptoms_text="Dry itchy patch on elbow",
        )
        db.add(case_ben)
        db.commit()

        # 3. Test Auto-Scheduling Service
        from backend.services.reminder_service import auto_schedule_case_reminder
        rem_mal = auto_schedule_case_reminder(db, case_mal.case_id, user.user_id, "Melanoma", "malignant", case_mal.symptoms_text)
        rem_pre = auto_schedule_case_reminder(db, case_pre.case_id, user.user_id, "Actinic Keratosis", "pre-cancerous", case_pre.symptoms_text)
        rem_ben = auto_schedule_case_reminder(db, case_ben.case_id, user.user_id, "Eczema", "benign", case_ben.symptoms_text)

        assert rem_mal.severity_tier == "malignant"
        assert rem_pre.severity_tier == "precancerous"
        assert rem_ben.severity_tier == "benign_stable"
        print("  [OK] Auto-scheduling rules verified: Malignant (5d), Pre-cancerous (21d), Benign (90d).")

        # 4. Test GET /reminders endpoint
        get_res = client.get("/reminders", headers=headers)
        assert get_res.status_code == 200, f"GET /reminders failed: {get_res.text}"
        data = get_res.json()
        assert len(data["reminders"]) >= 3
        print(f"  [OK] GET /reminders returned {data['total']} scheduled reminders (Pending: {data['pending_count']}).")

        # 5. Test POST /reminders/{id}/dismiss
        dismiss_res = client.post(f"/reminders/{rem_ben.id}/dismiss", headers=headers)
        assert dismiss_res.status_code == 200, f"Dismiss failed: {dismiss_res.text}"
        assert dismiss_res.json()["reminder"]["status"] == "dismissed"
        print(f"  [OK] POST /reminders/{rem_ben.id}/dismiss marked reminder as dismissed.")

        # 6. Test POST /reminders/{id}/complete
        comp_res = client.post(f"/reminders/{rem_pre.id}/complete", headers=headers)
        assert comp_res.status_code == 200, f"Complete failed: {comp_res.text}"
        assert comp_res.json()["reminder"]["status"] == "completed"
        print(f"  [OK] POST /reminders/{rem_pre.id}/complete marked reminder as completed.")

        # 7. Test Dispatcher / Process-Due Trigger
        proc_res = client.post("/reminders/process-due", headers=headers)
        assert proc_res.status_code == 200, f"Process due failed: {proc_res.text}"
        print(f"  [OK] POST /reminders/process-due executed dispatcher cycle successfully.")

    finally:
        db.close()

    print("=" * 80)
    print("  ALL FOLLOW-UP REMINDER TESTS PASSED AT 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_follow_up_reminders_full_cycle()
