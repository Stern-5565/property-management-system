"""End-to-end HTTP tests for the auth routes themselves."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.main import app
from app.models.employee import Employee
from app.models.user import User
from tests.auth_helpers import ADMIN_EMAIL, DEMO_PASSWORD

client = TestClient(app)


def test_login_with_correct_credentials_returns_tokens() -> None:
    response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": DEMO_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_with_wrong_password_returns_401_with_generic_message() -> None:
    response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": "WrongPassword"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_unknown_email_returns_same_generic_error() -> None:
    response = client.post("/api/auth/login", json={"Email": "nobody@example.com", "Password": "whatever"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_malformed_email_with_422() -> None:
    response = client.post("/api/auth/login", json={"Email": "not-an-email", "Password": "whatever"})

    assert response.status_code == 422


def test_get_me_returns_current_user_profile_and_roles() -> None:
    login_response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": DEMO_PASSWORD})
    token = login_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["Email"] == ADMIN_EMAIL
    assert body["Roles"] == ["Administrator"]


def test_get_me_without_a_token_returns_401() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_refresh_returns_a_new_access_token() -> None:
    login_response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": DEMO_PASSWORD})
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_refresh_with_an_access_token_instead_of_refresh_token_is_rejected() -> None:
    login_response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": DEMO_PASSWORD})
    access_token = login_response.json()["access_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout_requires_authentication_and_returns_no_content() -> None:
    login_response = client.post("/api/auth/login", json={"Email": ADMIN_EMAIL, "Password": DEMO_PASSWORD})
    token = login_response.json()["access_token"]

    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204

    unauthenticated_response = client.post("/api/auth/logout")
    assert unauthenticated_response.status_code == 401


@pytest.fixture
def temp_user_for_password_change():
    """A throwaway account, isolated from the real demo users, for
    change-password tests - see test_auth_service.py for why."""
    db = SessionLocal()
    password = "Password123!"
    employee = Employee(
        FirstName="Api",
        LastName="Fixture",
        Email="auth.api.test.fixture@example.com",
        HireDate=date(2024, 1, 1),
        IsActive=True,
    )
    db.add(employee)
    db.flush()
    user = User(
        EmployeeId=employee.EmployeeId,
        Username="auth.api.test.fixture",
        Email="auth.api.test.fixture@example.com",
        PasswordHash=hash_password(password),
        IsActive=True,
        FailedLoginAttempts=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        yield user, password
    finally:
        db.delete(user)
        db.delete(employee)
        db.commit()
        db.close()


def test_change_password_via_api(temp_user_for_password_change: tuple[User, str]) -> None:
    user, password = temp_user_for_password_change

    login_response = client.post("/api/auth/login", json={"Email": user.Email, "Password": password})
    token = login_response.json()["access_token"]

    change_response = client.post(
        "/api/auth/change-password",
        json={"CurrentPassword": password, "NewPassword": "BrandNewPassword789!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_response.status_code == 204

    old_password_login = client.post("/api/auth/login", json={"Email": user.Email, "Password": password})
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/api/auth/login", json={"Email": user.Email, "Password": "BrandNewPassword789!"}
    )
    assert new_password_login.status_code == 200


def test_change_password_with_weak_new_password_returns_422(temp_user_for_password_change: tuple[User, str]) -> None:
    user, password = temp_user_for_password_change

    login_response = client.post("/api/auth/login", json={"Email": user.Email, "Password": password})
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/auth/change-password",
        json={"CurrentPassword": password, "NewPassword": "alllettersnodigits"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
