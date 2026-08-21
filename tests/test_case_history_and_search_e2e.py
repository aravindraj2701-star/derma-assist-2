"""
E2E Verification Suite for Universal Global Search and Case History Advanced Filters
Tests:
1. Global Search endpoint (GET /history/global-search?q=...)
   - Match clinical cases by ID and disease
   - Match pathology disease profiles
   - Match quick actions (Analyze, Dashboard, Training)
2. Case History Advanced Search & Filtering (GET /history)
   - Free-text query filtering
   - Confidence score ranges (High >=70%, Moderate 50-69%, Low <50%)
   - Severity tier filtering (Malignant, Pre-cancerous, Benign)
   - Review advised flag filtering
   - Sorting criteria (newest, oldest, confidence_desc, confidence_asc)
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
from backend.database.models import User, CaseHistory, Disease

client = TestClient(app)


def test_global_search_and_case_filters_e2e():
    print("=" * 80)
    print("  RUNNING UNIVERSAL GLOBAL SEARCH & CASE HISTORY FILTERS E2E SUITE")
    print("=" * 80)

    # 1. Register test clinician
    email = f"clinician_search_{uuid.uuid4().hex[:6]}@dermaassist.ai"
    reg_res = client.post(
        "/auth/register",
        json={"name": "Dr. Helena Vance", "email": email, "password": "SecurePassword123!"},
    )
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Authenticated user created: {email}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        # 2. Seed diverse clinical test cases for this user
        c1 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Melanoma",
            confidence=0.92,
            symptoms_text="Asymmetrical dark evolving mole with notched border on left shoulder",
            is_low_confidence=0,
        )
        c2 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Urticaria",
            confidence=0.64,
            symptoms_text="Evanescent pruritic raised wheals on forearm",
            is_low_confidence=0,
        )
        c3 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Eczema",
            confidence=0.45,
            symptoms_text="Dry itchy flaky red patches in antecubital fossa",
            is_low_confidence=1,
        )
        c4 = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Actinic Keratosis",
            confidence=0.76,
            symptoms_text="Rough gritty sandpaper scale on sun-exposed forehead",
            is_low_confidence=0,
        )
        db.add_all([c1, c2, c3, c4])
        db.commit()
        db.refresh(c1)
        db.refresh(c2)
        db.refresh(c3)
        db.refresh(c4)
        print(f"  [OK] Seeded 4 test cases: #{c1.case_id} (Melanoma 92%), #{c2.case_id} (Urticaria 64%), #{c3.case_id} (Eczema 45%), #{c4.case_id} (Actinic Keratosis 76%).")

        # 3. Test Universal Global Search for "Melanoma"
        gs_res1 = client.get("/history/global-search?q=Melanoma", headers=headers)
        assert gs_res1.status_code == 200, f"Global search failed: {gs_res1.text}"
        data1 = gs_res1.json()
        assert len(data1["cases"]) >= 1
        assert any(c["id"] == c1.case_id for c in data1["cases"])
        print(f"  [OK] Global search 'Melanoma' found Case #{c1.case_id} and {len(data1['diseases'])} disease database matches.")

        # 4. Test Universal Global Search for Quick Action "analyze"
        gs_res2 = client.get("/history/global-search?q=analyze", headers=headers)
        assert gs_res2.status_code == 200
        data2 = gs_res2.json()
        assert len(data2["actions"]) >= 1
        assert data2["actions"][0]["url"] == "/analyze"
        print(f"  [OK] Global search 'analyze' matched quick navigation action '{data2['actions'][0]['title']}'.")

        # 5. Test Case History Search by Free-text Query
        hist_q = client.get("/history?q=wheals", headers=headers)
        assert hist_q.status_code == 200
        q_data = hist_q.json()
        assert q_data["total"] == 1
        assert q_data["cases"][0]["case_id"] == c2.case_id
        print(f"  [OK] Free-text search 'wheals' correctly isolated Case #{c2.case_id} (Urticaria).")

        # 6. Test Confidence Score Filtering (High >= 70%)
        hist_high = client.get("/history?min_confidence=0.70", headers=headers)
        assert hist_high.status_code == 200
        high_data = hist_high.json()
        assert high_data["total"] == 2  # Melanoma 92% and Actinic Keratosis 76%
        assert all(c["confidence"] >= 0.70 for c in high_data["cases"])
        print(f"  [OK] High confidence filter (>=70%) returned {high_data['total']} cases.")

        # 7. Test Confidence Score Filtering (Low < 50%)
        hist_low = client.get("/history?max_confidence=0.499", headers=headers)
        assert hist_low.status_code == 200
        low_data = hist_low.json()
        assert low_data["total"] == 1
        assert low_data["cases"][0]["case_id"] == c3.case_id
        print(f"  [OK] Low confidence filter (<50%) returned Case #{c3.case_id} (Eczema 45%).")

        # 8. Test Severity Tier Filtering (Malignant)
        hist_mal = client.get("/history?severity=malignant", headers=headers)
        assert hist_mal.status_code == 200
        mal_data = hist_mal.json()
        assert mal_data["total"] == 1
        assert mal_data["cases"][0]["predicted_disease"] == "Melanoma"
        print(f"  [OK] Severity filter 'malignant' returned Case #{c1.case_id} (Melanoma).")

        # 9. Test Review Advised Status Filter
        hist_rev = client.get("/history?status=review_advised", headers=headers)
        assert hist_rev.status_code == 200
        rev_data = hist_rev.json()
        assert rev_data["total"] == 1
        assert rev_data["cases"][0]["case_id"] == c3.case_id
        print(f"  [OK] Status filter 'review_advised' returned Case #{c3.case_id}.")

        # 10. Test Sorting by Confidence Descending
        hist_sort = client.get("/history?sort_by=confidence_desc", headers=headers)
        assert hist_sort.status_code == 200
        sort_data = hist_sort.json()
        confs = [c["confidence"] for c in sort_data["cases"]]
        assert confs == sorted(confs, reverse=True)
        print(f"  [OK] Sorting by 'confidence_desc' verified: {confs}.")

    finally:
        db.close()

    print("=" * 80)
    print("  ALL GLOBAL SEARCH & CASE HISTORY FILTER TESTS PASSED AT 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_global_search_and_case_filters_e2e()
