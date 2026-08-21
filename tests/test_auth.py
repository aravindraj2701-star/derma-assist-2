import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import Base, engine, SessionLocal
from backend.database.models import User

client = TestClient(app)


def setup_function():
    """Clean test user if exists."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "testuser@example.com").first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def test_register_and_login_flow():
    # 1. Register new user
    reg_payload = {
        "name": "Test Dermatologist",
        "email": "testuser@example.com",
        "password": "securepassword123",
    }
    reg_res = client.post("/auth/register", json=reg_payload)
    assert reg_res.status_code == 200, reg_res.text
    data = reg_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["name"] == "Test Dermatologist"

    # 2. Duplicate registration should fail
    dup_res = client.post("/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

    # 3. Successful login
    login_payload = {
        "email": "testuser@example.com",
        "password": "securepassword123",
    }
    login_res = client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "testuser@example.com"

    # 4. Failed login with wrong password
    bad_login = {
        "email": "testuser@example.com",
        "password": "wrongpassword",
    }
    bad_res = client.post("/auth/login", json=bad_login)
    assert bad_res.status_code == 401
