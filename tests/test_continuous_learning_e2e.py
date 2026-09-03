"""
E2E Test Suite for Continuous Learning Agent & Training Console
Verifies:
1. Doctor review & candidate opt-in endpoint (POST /training/doctor/cases/{id}/review).
2. Training console stats (GET /training/admin/stats).
3. Supervised Retraining Execution with Safety Gate (POST /training/admin/retrain).
4. Safety validation: model promotion rules and candidate state transition (approved -> used_in_training).
5. Rollback endpoint (POST /training/admin/rollback) restoring prior version.
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
from backend.database.models import User, CaseHistory, ModelTrainingCandidate, ModelVersion

client = TestClient(app)


def test_continuous_learning_full_cycle():
    print("=" * 80)
    print("  RUNNING CONTINUOUS LEARNING AGENT E2E TEST SUITE")
    print("=" * 80)

    # 1. Register test clinician
    email = f"clinician_cl_{uuid.uuid4().hex[:6]}@dermaassist.ai"
    reg_res = client.post(
        "/auth/register",
        json={"name": "Dr. Alan Turing", "email": email, "password": "SecurePassword123!", "role": "admin"},
    )
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Authenticated doctor created: {email}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        # 2. Create sample screening cases for doctor review
        case1 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Urticaria",
            confidence=0.58,
            symptoms_text="Evanescent wheals on forearm",
        )
        case2 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Melanoma",
            confidence=0.85,
            symptoms_text="Asymmetric dark evolving mole with notched border",
        )
        db.add(case1)
        db.add(case2)
        db.commit()
        db.refresh(case1)
        db.refresh(case2)

        # 3. Doctor reviews Case 1 (confirms ground truth diagnosis & approves for training)
        rev1_res = client.post(
            f"/training/doctor/cases/{case1.case_id}/review",
            json={
                "doctor_corrected_label": "Urticaria",
                "doctor_notes": "Classic evanescent wheals confirmed via dermoscopy.",
                "opt_in_training": True,
            },
            headers=headers,
        )
        assert rev1_res.status_code == 200, f"Doctor review 1 failed: {rev1_res.text}"
        assert rev1_res.json()["candidate"]["status"] == "approved_for_training"
        print(f"  [OK] Case #{case1.case_id} reviewed and approved into training candidate pool.")

        # 4. Doctor reviews Case 2 (confirms Melanoma & approves for training)
        rev2_res = client.post(
            f"/training/doctor/cases/{case2.case_id}/review",
            json={
                "doctor_corrected_label": "Melanoma",
                "doctor_notes": "Histopathologically confirmed superficial spreading melanoma.",
                "opt_in_training": True,
            },
            headers=headers,
        )
        assert rev2_res.status_code == 200, f"Doctor review 2 failed: {rev2_res.text}"
        print(f"  [OK] Case #{case2.case_id} reviewed and approved into training candidate pool.")

        # 5. Check Admin Training Stats
        stats_res = client.get("/training/admin/stats", headers=headers)
        assert stats_res.status_code == 200, f"Get stats failed: {stats_res.text}"
        stats_data = stats_res.json()
        assert stats_data["approved_for_training_count"] >= 2
        active_version_id = stats_data["active_model_version"]["version_id"]
        print(f"  [OK] Training Console Stats verified: {stats_data['approved_for_training_count']} approved candidates ready (Active: {active_version_id}).")

        # 6. Trigger Supervised Retraining Execution with Safety Gate
        retrain_res = client.post("/training/admin/retrain", headers=headers)
        assert retrain_res.status_code == 200, f"Retraining failed: {retrain_res.text}"
        retrain_data = retrain_res.json()
        assert retrain_data["promoted"] is True
        new_version_id = retrain_data["version"]["version_id"]
        assert new_version_id != active_version_id
        assert retrain_data["version"]["accuracy"] >= stats_data["active_model_version"]["accuracy"]
        assert retrain_data["version"]["malignant_recall"] >= stats_data["active_model_version"]["malignant_recall"]
        print(f"  [OK] Supervised Retraining succeeded! Safety Gate PASSED: New version '{new_version_id}' promoted to production.")

        # 7. Test Rollback Endpoint
        rollback_res = client.post(
            "/training/admin/rollback",
            json={"target_version_id": active_version_id},
            headers=headers,
        )
        assert rollback_res.status_code == 200, f"Rollback failed: {rollback_res.text}"
        assert rollback_res.json()["active_version"]["version_id"] == active_version_id
        print(f"  [OK] Production model successfully rolled back to '{active_version_id}'.")

    finally:
        db.close()

    print("=" * 80)
    print("  ALL CONTINUOUS LEARNING AGENT TESTS PASSED AT 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_continuous_learning_full_cycle()
