import pytest
import os
import sys
from pathlib import Path

# Add workspace to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from models.database import db
from models.user_model import User, UserRole

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Seed test user
        user = User(
            name="Dr. Test Physician",
            email="testdoctor@brainsight.ai",
            role=UserRole.DOCTOR
        )
        user.set_password("securepassword123")
        db.session.add(user)
        db.session.commit()

        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_user_password_hashing():
    user = User(name="Nurse Test", email="nurse@test.com", role=UserRole.CLINICAL_STAFF)
    user.set_password("mypassword")
    assert user.password_hash != "mypassword"
    assert user.check_password("mypassword") is True
    assert user.check_password("wrongpassword") is False

def test_login_success(client):
    res = client.post("/api/auth/login", json={
        "email": "testdoctor@brainsight.ai",
        "password": "securepassword123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["message"] == "Authentication successful"
    assert data["user"]["email"] == "testdoctor@brainsight.ai"
    assert data["user"]["role"] == UserRole.DOCTOR

def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={
        "email": "testdoctor@brainsight.ai",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.get_json()["error"]

def test_auth_me_and_logout(client):
    # Log in
    client.post("/api/auth/login", json={
        "email": "testdoctor@brainsight.ai",
        "password": "securepassword123"
    })

    # Check /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Verify session cleared
    me_after = client.get("/api/auth/me")
    assert me_after.get_json()["authenticated"] is False
