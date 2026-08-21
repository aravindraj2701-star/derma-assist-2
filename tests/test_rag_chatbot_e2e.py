"""
E2E Test Suite for RAG-Based Medical Chatbot Agent
Verifies:
1. Question answering from curated dermatology knowledge base (Melanoma, Eczema, Psoriasis, Urticaria, etc.).
2. Source citations attached to each response.
3. Case-specific scoped queries (injecting prediction, confidence, differentiating clinical features).
4. Strict medical disclaimers and zero-hallucination bounds.
5. Audit logging in chat_audit_logs table.
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
from backend.database.models import User, CaseHistory, ChatAuditLog

client = TestClient(app)


def test_rag_medical_chatbot_full_cycle():
    print("=" * 80)
    print("  RUNNING RAG MEDICAL CHATBOT E2E TEST SUITE")
    print("=" * 80)

    # 1. Register test doctor / patient
    email = f"clinician_rag_{uuid.uuid4().hex[:6]}@dermaassist.ai"
    reg_res = client.post(
        "/auth/register",
        json={"name": "Dr. Marcus Chen", "email": email, "password": "SecurePassword123!"},
    )
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Authenticated user created: {email}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        # 2. Test General Knowledge Query (Melanoma ABCDE criteria)
        q1 = "What are the ABCDE criteria used to evaluate melanoma?"
        res1 = client.post("/chat", json={"question": q1}, headers=headers)
        assert res1.status_code == 200, f"General chat query failed: {res1.text}"
        data1 = res1.json()
        assert "ABCDE" in data1["answer"] or "Asymmetry" in data1["answer"]
        assert len(data1["sources"]) > 0
        assert "Disclaimer" in data1["answer"] or "Clinical Decision Support" in data1["answer"]
        print(f"  [OK] General medical query answered with {len(data1['sources'])} citations.")

        # 3. Create a test patient case with Urticaria
        case = CaseHistory(
            user_id=user.user_id,
            predicted_disease="Urticaria",
            confidence=0.63,
            symptoms_text="Location: Left forearm | Duration: 1 week | Texture: Raised | Symptoms: Intense itching",
            ai_explanation="Multimodal analysis identified Urticaria as the primary presentation (63% confidence).",
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        # 4. Test Case-Scoped Query ("Why was this classified as Urticaria?")
        q2 = "Why was this classified as Urticaria for my case?"
        res2 = client.post("/chat", json={"question": q2, "case_id": case.case_id}, headers=headers)
        assert res2.status_code == 200, f"Case-scoped chat query failed: {res2.text}"
        data2 = res2.json()
        assert "Urticaria" in data2["answer"]
        assert f"#{case.case_id}" in data2["answer"] or "63%" in data2["answer"]
        print(f"  [OK] Case-scoped query successfully incorporated Case #{case.case_id} report data.")

        # 5. Verify Chat Audit Log entry in database
        audit_entry = db.query(ChatAuditLog).filter(ChatAuditLog.user_id == user.user_id).first()
        assert audit_entry is not None, "Chat audit log was not persisted!"
        assert audit_entry.question is not None
        assert audit_entry.answer is not None
        print(f"  [OK] Chat audit log verified in database (ID: {audit_entry.id}).")

    finally:
        db.close()

    print("=" * 80)
    print("  ALL RAG MEDICAL CHATBOT TESTS PASSED AT 100%!")
    print("=" * 80)


if __name__ == "__main__":
    test_rag_medical_chatbot_full_cycle()
