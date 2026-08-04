"""Tests for AuthService - business rules.

Uses a throwaway Employee+User pair (created and torn down per test via the
temp_user fixture) rather than any of the 5 real seeded demo accounts -
login legitimately mutates LastLoginAt/FailedLoginAttempts, and
change-password tests would otherwise permanently break a demo account's
documented "Password123!" login. See test_landlord_service.py for more on
why this project uses explicit create/cleanup rather than transaction-
rollback fixtures.
"""

from datetime import date

import pytest

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.employee import Employee
from app.models.user import User
from app.services.auth_service import AuthService

FIXTURE_PASSWORD = "Password123!"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def service(db):
    # Shares the SAME session as temp_user below (both fixtures request the
    # `db` fixture, and pytest hands out one instance of it per test) -
    # important, because a change made through one session isn't visible
    # through another until it's committed AND the other session either
    # re-queries or is told to refresh. Two independent SessionLocal()
    # calls here would silently make every mutation test below a no-op.
    return AuthService(db)


@pytest.fixture
def temp_user(db):
    employee = Employee(
        FirstName="Test",
        LastName="Fixture",
        Email="auth.test.fixture@example.com",
        HireDate=date(2024, 1, 1),
        IsActive=True,
    )
    db.add(employee)
    db.flush()

    user = User(
        EmployeeId=employee.EmployeeId,
        Username="auth.test.fixture",
        Email="auth.test.fixture@example.com",
        PasswordHash=hash_password(FIXTURE_PASSWORD),
        IsActive=True,
        FailedLoginAttempts=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        yield user
    finally:
        db.delete(user)
        db.delete(employee)
        db.commit()


def test_authenticate_with_correct_credentials_returns_tokens(service: AuthService, temp_user: User) -> None:
    user, access_token, refresh_token = service.authenticate(temp_user.Email, FIXTURE_PASSWORD)

    assert user.UserId == temp_user.UserId
    assert access_token
    assert refresh_token
    assert user.FailedLoginAttempts == 0
    assert user.LastLoginAt is not None


def test_authenticate_with_wrong_password_raises_and_increments_failed_attempts(
    service: AuthService, temp_user: User
) -> None:
    with pytest.raises(AppError) as exc_info:
        service.authenticate(temp_user.Email, "WrongPassword")

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert exc_info.value.status_code == 401

    service.db.refresh(temp_user)
    assert temp_user.FailedLoginAttempts == 1


def test_authenticate_with_unknown_email_raises_same_generic_error(service: AuthService) -> None:
    """Same error code/message as a wrong password - the API must not
    reveal whether an email is registered at all."""
    with pytest.raises(AppError) as exc_info:
        service.authenticate("nobody-at-all@example.com", "whatever")

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert exc_info.value.message == "Incorrect email or password."


def test_authenticate_with_inactive_user_raises_same_generic_error(service: AuthService, temp_user: User) -> None:
    temp_user.IsActive = False
    service.db.commit()

    with pytest.raises(AppError) as exc_info:
        service.authenticate(temp_user.Email, FIXTURE_PASSWORD)

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert exc_info.value.message == "Incorrect email or password."


def test_refresh_access_token_issues_a_new_token(service: AuthService, temp_user: User) -> None:
    _user, _access_token, refresh_token = service.authenticate(temp_user.Email, FIXTURE_PASSWORD)

    new_access_token = service.refresh_access_token(refresh_token)
    assert new_access_token


def test_refresh_access_token_rejects_an_access_token(service: AuthService, temp_user: User) -> None:
    _user, access_token, _refresh_token = service.authenticate(temp_user.Email, FIXTURE_PASSWORD)

    with pytest.raises(AppError) as exc_info:
        service.refresh_access_token(access_token)
    assert exc_info.value.code == "INVALID_TOKEN"


def test_refresh_access_token_rejects_token_for_deactivated_user(service: AuthService, temp_user: User) -> None:
    _user, _access_token, refresh_token = service.authenticate(temp_user.Email, FIXTURE_PASSWORD)

    temp_user.IsActive = False
    service.db.commit()

    with pytest.raises(AppError) as exc_info:
        service.refresh_access_token(refresh_token)
    assert exc_info.value.code == "INVALID_TOKEN"


def test_change_password_with_correct_current_password_succeeds(service: AuthService, temp_user: User) -> None:
    service.change_password(temp_user, FIXTURE_PASSWORD, "NewPassword456!")

    # The new password now works; the old one no longer does.
    user, _access, _refresh = service.authenticate(temp_user.Email, "NewPassword456!")
    assert user.UserId == temp_user.UserId

    with pytest.raises(AppError):
        service.authenticate(temp_user.Email, FIXTURE_PASSWORD)


def test_change_password_with_wrong_current_password_is_rejected(service: AuthService, temp_user: User) -> None:
    with pytest.raises(AppError) as exc_info:
        service.change_password(temp_user, "WrongCurrentPassword", "NewPassword456!")

    assert exc_info.value.code == "INVALID_CURRENT_PASSWORD"
    assert exc_info.value.status_code == 400
