"""
End-to-End Test Suite for Admin Console, Role Guarding, Login Activity Tracking, and Safety Checks.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import User, LoginActivity, AdminAuditLog
from backend.services.auth_service import create_jwt
from backend.utils.hash_utils import hash_password
from scripts.promote_admin import promote_or_create_admin

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_users():
    """Setup clean state before each test."""
    db = SessionLocal()
    try:
        test_emails = [
            "test_patient_admin_suite@example.com",
            "test_doctor_admin_suite@example.com",
            "test_admin_1_suite@example.com",
            "test_admin_2_suite@example.com",
            "test_cli_admin_suite@example.com",
        ]
        db.query(LoginActivity).filter(LoginActivity.email.in_(test_emails)).delete(synchronize_session=False)
        db.query(AdminAuditLog).delete(synchronize_session=False)
        db.query(User).filter(User.email.in_(test_emails)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    yield


def _create_user(email: str, name: str, role: str = "patient", is_active: bool = True, password: str = "password123") -> User:
    db = SessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_registration_role_selection_and_defaults():
    """Verify signup supports role selection (patient/doctor/admin) and defaults safely."""
    # 1. Register with role='admin'
    res_admin = client.post(
        "/auth/register",
        json={
            "name": "Admin Registrant",
            "email": "test_patient_admin_suite@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["user"]["role"] == "admin"
    assert data_admin["user"]["is_active"] is True

    # 2. Register without specifying role -> defaults to patient
    res_default = client.post(
        "/auth/register",
        json={
            "name": "Default Patient",
            "email": "test_doctor_admin_suite@example.com",
            "password": "password123",
        },
    )
    assert res_default.status_code == 200
    data_default = res_default.json()
    assert data_default["user"]["role"] == "patient"


def test_login_activity_logging_success_and_failure():
    """Verify login attempts (both success and failure) are logged into login_activity table."""
    _create_user(
        email="test_patient_admin_suite@example.com",
        name="Test Patient",
        password="correctpassword",
    )

    # 1. Failed login attempt
    fail_res = client.post(
        "/auth/login",
        json={
            "email": "test_patient_admin_suite@example.com",
            "password": "wrongpassword",
        },
    )
    assert fail_res.status_code == 401

    # 2. Successful login attempt
    succ_res = client.post(
        "/auth/login",
        json={
            "email": "test_patient_admin_suite@example.com",
            "password": "correctpassword",
        },
    )
    assert succ_res.status_code == 200

    # 3. Check login_activity records in DB
    db = SessionLocal()
    try:
        activities = (
            db.query(LoginActivity)
            .filter(LoginActivity.email == "test_patient_admin_suite@example.com")
            .order_by(LoginActivity.login_at.asc())
            .all()
        )
        assert len(activities) >= 2
        assert activities[0].success is False
        assert activities[0].failure_reason == "Invalid password"
        assert activities[1].success is True
    finally:
        db.close()


def test_admin_route_authorization_guard():
    """Verify non-admin roles (patient, doctor) receive 403 Forbidden on all /admin/* endpoints."""
    patient = _create_user("test_patient_admin_suite@example.com", "Patient User", role="patient")
    doctor = _create_user("test_doctor_admin_suite@example.com", "Doctor User", role="doctor")

    patient_token = create_jwt(patient.user_id, patient.email, role="patient", is_active=True)
    doctor_token = create_jwt(doctor.user_id, doctor.email, role="doctor", is_active=True)

    endpoints = [
        ("GET", "/admin/stats"),
        ("GET", "/admin/users"),
        ("GET", "/admin/login-activity"),
        ("GET", f"/admin/users/{patient.user_id}"),
        ("PATCH", f"/admin/users/{patient.user_id}/role", {"role": "doctor"}),
        ("PATCH", f"/admin/users/{patient.user_id}/status", {"status": "suspended"}),
    ]

    for item in endpoints:
        method = item[0]
        url = item[1]
        json_body = item[2] if len(item) > 2 else None

        # Test Patient
        headers = {"Authorization": f"Bearer {patient_token}"}
        if method == "GET":
            res = client.get(url, headers=headers)
        elif method == "PATCH":
            res = client.patch(url, headers=headers, json=json_body)
        assert res.status_code == 403, f"Patient should be forbidden on {url}, got {res.status_code}"

        # Test Doctor
        headers = {"Authorization": f"Bearer {doctor_token}"}
        if method == "GET":
            res = client.get(url, headers=headers)
        elif method == "PATCH":
            res = client.patch(url, headers=headers, json=json_body)
        assert res.status_code == 403, f"Doctor should be forbidden on {url}, got {res.status_code}"


def test_admin_account_management_and_safety_checks():
    """Verify admin operations (listing, role changes, suspensions, and last-admin lockout prevention)."""
    # Temporarily demote other non-test admins to isolate the last-admin test
    db = SessionLocal()
    other_admins = db.query(User).filter(User.role.in_(["admin", "super_admin"])).all()
    for oa in other_admins:
        oa.role = "patient"
    db.commit()
    db.close()

    admin1 = _create_user("test_admin_1_suite@example.com", "Primary Admin", role="admin")
    admin2 = _create_user("test_admin_2_suite@example.com", "Secondary Admin", role="admin")
    target = _create_user("test_patient_admin_suite@example.com", "Target Patient", role="patient")

    admin1_token = create_jwt(admin1.user_id, admin1.email, role="admin", is_active=True)
    headers = {"Authorization": f"Bearer {admin1_token}"}

    # 1. Admin gets stats
    stats_res = client.get("/admin/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_users" in stats
    assert stats["roles"]["admin"] == 2

    # 2. Admin lists users with search
    list_res = client.get("/admin/users?search=Target", headers=headers)
    assert list_res.status_code == 200
    users_data = list_res.json()
    assert users_data["total"] >= 1
    assert any(u["email"] == target.email for u in users_data["users"])

    # 3. Promote patient to doctor
    role_res = client.patch(
        f"/admin/users/{target.user_id}/role",
        headers=headers,
        json={"role": "doctor"},
    )
    assert role_res.status_code == 200
    assert role_res.json()["user"]["role"] == "doctor"

    # 4. Demote Admin 2 to patient (should succeed because Admin 1 is still active)
    demote_res = client.patch(
        f"/admin/users/{admin2.user_id}/role",
        headers=headers,
        json={"role": "patient"},
    )
    assert demote_res.status_code == 200
    assert demote_res.json()["user"]["role"] == "patient"

    # 5. SAFETY CHECK: Attempt to demote Admin 1 (now the ONLY active admin left) -> must fail with 400
    demote_last_res = client.patch(
        f"/admin/users/{admin1.user_id}/role",
        headers=headers,
        json={"role": "patient"},
    )
    assert demote_last_res.status_code == 400
    assert "lockout" in demote_last_res.json()["detail"].lower()

    # SAFETY CHECK: Attempt to suspend Admin 1 (the ONLY active admin left) -> must also fail with 400
    suspend_last_res = client.patch(
        f"/admin/users/{admin1.user_id}/status",
        headers=headers,
        json={"status": "suspended"},
    )
    assert suspend_last_res.status_code == 400
    assert "lockout" in suspend_last_res.json()["detail"].lower()

    # 6. Suspend user account
    suspend_res = client.patch(
        f"/admin/users/{target.user_id}/status",
        headers=headers,
        json={"status": "suspended"},
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["user"]["is_active"] is False

    # 7. Suspended user login should be rejected with 403
    suspended_login_res = client.post(
        "/auth/login",
        json={
            "email": target.email,
            "password": "password123",
        },
    )
    assert suspended_login_res.status_code == 403
    assert "suspended" in suspended_login_res.json()["detail"].lower()

    # 8. Reactivate user account
    reactivate_res = client.patch(
        f"/admin/users/{target.user_id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["user"]["is_active"] is True

    # 9. Reactivated user login succeeds
    reactivated_login_res = client.post(
        "/auth/login",
        json={
            "email": target.email,
            "password": "password123",
        },
    )
    assert reactivated_login_res.status_code == 200


def test_cli_promote_script():
    """Verify promote_admin.py script functions properly."""
    # Test promoting new admin
    success = promote_or_create_admin(
        email="test_cli_admin_suite@example.com",
        name="CLI Admin",
        password="cliSecurePassword123",
    )
    assert success is True

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test_cli_admin_suite@example.com").first()
        assert user is not None
        assert user.role == "admin"
        assert user.is_active is True
    finally:
        db.close()
