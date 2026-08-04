"""Tests for EmployeeService - business rules.

Same throwaway-row-with-cleanup convention as test_landlord_service.py -
see that file's module docstring for why. The linked-User cascade test
creates its own throwaway User row too, since Employee/User are two
separate tables joined only by Users.EmployeeId.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.employee_service import EmployeeService

TODAY = date.today()


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield EmployeeService(db)
    finally:
        db.close()


def _new_employee_payload(**overrides) -> EmployeeCreate:
    defaults = {
        "FirstName": "Test",
        "LastName": "Fixture",
        "Email": "test.fixture.employee@example.com",
        "HireDate": TODAY - timedelta(days=30),
    }
    defaults.update(overrides)
    return EmployeeCreate(**defaults)


def test_create_and_get_employee(service: EmployeeService) -> None:
    created = service.create_employee(_new_employee_payload())
    try:
        fetched = service.get_employee(created.EmployeeId)
        assert fetched.FirstName == "Test"
        assert fetched.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_get_employee_raises_not_found_for_missing_id(service: EmployeeService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.get_employee(999_999)
    assert exc_info.value.code == "EMPLOYEE_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_create_employee_rejects_duplicate_email(service: EmployeeService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.create_employee(_new_employee_payload(Email="daniel.osei@propertymanager.example"))
    assert exc_info.value.code == "DUPLICATE_EMAIL"
    assert exc_info.value.status_code == 409


def test_update_employee_changes_fields_and_bumps_updated_at(service: EmployeeService) -> None:
    created = service.create_employee(_new_employee_payload())
    original_updated_at = created.UpdatedAt
    try:
        updated = service.update_employee(
            created.EmployeeId,
            EmployeeUpdate(**{**_new_employee_payload().model_dump(), "JobTitle": "Renamed Title"}),
        )
        assert updated.JobTitle == "Renamed Title"
        assert updated.UpdatedAt >= original_updated_at
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_employee_allows_keeping_its_own_email(service: EmployeeService) -> None:
    created = service.create_employee(_new_employee_payload())
    try:
        updated = service.update_employee(created.EmployeeId, _new_employee_payload())
        assert updated.Email == "test.fixture.employee@example.com"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_employee_rejects_email_used_by_another_employee(service: EmployeeService) -> None:
    created = service.create_employee(_new_employee_payload())
    try:
        with pytest.raises(AppError) as exc_info:
            service.update_employee(
                created.EmployeeId,
                EmployeeUpdate(**{**_new_employee_payload().model_dump(), "Email": "daniel.osei@propertymanager.example"}),
            )
        assert exc_info.value.code == "DUPLICATE_EMAIL"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_set_active_status_deactivates_and_reactivates(service: EmployeeService) -> None:
    created = service.create_employee(_new_employee_payload())
    try:
        deactivated = service.set_active_status(created.EmployeeId, False)
        assert deactivated.IsActive is False

        reactivated = service.set_active_status(created.EmployeeId, True)
        assert reactivated.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_employee_with_open_maintenance_assignments_is_blocked_and_leaves_it_unchanged(
    service: EmployeeService,
) -> None:
    daniel = service.db.execute(select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")).scalar_one()

    with pytest.raises(AppError) as exc_info:
        service.deactivate_employee(daniel.EmployeeId)

    assert exc_info.value.code == "EMPLOYEE_HAS_OPEN_MAINTENANCE_ASSIGNMENTS"
    assert exc_info.value.status_code == 409

    # Confirm the rejected attempt didn't change the seeded employee -
    # other tests depend on this data staying exactly as seeded.
    service.db.refresh(daniel)
    assert daniel.IsActive is True


def test_deactivating_employee_cascades_to_linked_user_account(service: EmployeeService) -> None:
    """Enforces "inactive employees cannot log in" (scope doc section
    5.7) - login checks User.IsActive, a different row, so deactivating
    the Employee alone wouldn't actually block login without this."""
    employee = service.create_employee(_new_employee_payload())
    user = User(
        EmployeeId=employee.EmployeeId,
        Username="test.fixture.cascade.user",
        Email="test.fixture.cascade.user@example.com",
        PasswordHash="not-a-real-hash",
        IsActive=True,
        FailedLoginAttempts=0,
    )
    service.db.add(user)
    service.db.commit()
    try:
        service.set_active_status(employee.EmployeeId, False)

        service.db.refresh(user)
        assert user.IsActive is False
    finally:
        service.db.delete(user)
        service.db.delete(employee)
        service.db.commit()


def test_reactivating_employee_does_not_restore_linked_user_account(service: EmployeeService) -> None:
    """The cascade is one-way - see EmployeeService's module docstring for
    why reactivation deliberately doesn't auto-restore login access."""
    employee = service.create_employee(_new_employee_payload())
    user = User(
        EmployeeId=employee.EmployeeId,
        Username="test.fixture.no_restore.user",
        Email="test.fixture.no_restore.user@example.com",
        PasswordHash="not-a-real-hash",
        IsActive=True,
        FailedLoginAttempts=0,
    )
    service.db.add(user)
    service.db.commit()
    try:
        service.set_active_status(employee.EmployeeId, False)
        service.set_active_status(employee.EmployeeId, True)

        service.db.refresh(user)
        assert user.IsActive is False
    finally:
        service.db.delete(user)
        service.db.delete(employee)
        service.db.commit()
