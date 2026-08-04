"""Tests for MaintenanceService - business rules.

Throwaway requests are attached to an EXISTING seeded property (PM-0002)
rather than needing a fresh property fixture - same approach as
test_rent_payment_service.py attaching to an existing seeded tenancy. A
throwaway request can have MaintenanceNotes attached to it, and there's no
cascading delete on that FK (see maintenance_note.py / the "avoid
unnecessary cascading deletes" modeling rule), so cleanup always deletes
notes before the request itself.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.employee import Employee
from app.models.maintenance_note import MaintenanceNote
from app.models.property import Property
from app.models.user import User
from app.schemas.maintenance import MaintenanceRequestCreate, MaintenanceRequestUpdate
from app.services.maintenance_service import MaintenanceService

TODAY = date.today()


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield MaintenanceService(db)
    finally:
        db.close()


@pytest.fixture
def property_id(service: MaintenanceService) -> int:
    property_ = service.db.execute(select(Property).where(Property.PropertyReference == "PM-0002")).scalar_one()
    return property_.PropertyId


@pytest.fixture
def daniel_employee_id(service: MaintenanceService) -> int:
    employee = service.db.execute(
        select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")
    ).scalar_one()
    return employee.EmployeeId


@pytest.fixture
def daniel_user(service: MaintenanceService) -> User:
    return service.db.execute(select(User).where(User.Email == "daniel.osei@propertymanager.example")).scalar_one()


def _payload(property_id: int, **overrides) -> MaintenanceRequestCreate:
    defaults = {
        "PropertyId": property_id,
        "RequestReference": "MR-SVC-TEST-001",
        "Title": "Test maintenance request",
        "Category": "General",
        "Priority": "Medium",
    }
    defaults.update(overrides)
    return MaintenanceRequestCreate(**defaults)


def _delete(service: MaintenanceService, request) -> None:
    notes = service.db.execute(select(MaintenanceNote).where(MaintenanceNote.MaintenanceRequestId == request.MaintenanceRequestId)).scalars().all()
    for note in notes:
        service.db.delete(note)
    service.db.delete(request)
    service.db.commit()


# ---------- create / update ----------


def test_create_request_starts_as_reported(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        assert request.MaintenanceStatus == "Reported"
        assert request.AssignedEmployeeId is None
    finally:
        _delete(service, request)


def test_create_request_rejects_unknown_property(service: MaintenanceService, admin_user_id: int) -> None:
    with pytest.raises(AppError) as exc_info:
        service.create_request(_payload(999_999), user_id=admin_user_id)
    assert exc_info.value.code == "PROPERTY_NOT_FOUND"


def test_create_request_rejects_duplicate_reference(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_request(_payload(property_id), user_id=admin_user_id)
        assert exc_info.value.code == "DUPLICATE_REQUEST_REFERENCE"
    finally:
        _delete(service, request)


def test_get_request_raises_not_found_for_missing_id(service: MaintenanceService, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    with pytest.raises(AppError) as exc_info:
        service.get_request(999_999, viewer=admin)
    assert exc_info.value.code == "MAINTENANCE_REQUEST_NOT_FOUND"


def test_update_request_rejected_once_terminal(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.cancel_request(request.MaintenanceRequestId, notes=None, user_id=admin_user_id)
        with pytest.raises(AppError) as exc_info:
            service.update_request(request.MaintenanceRequestId, MaintenanceRequestUpdate(**_payload(property_id).model_dump()), user_id=admin_user_id)
        assert exc_info.value.code == "MAINTENANCE_REQUEST_CLOSED"
    finally:
        _delete(service, request)


# ---------- assignment ----------


def test_assign_employee_moves_reported_request_to_assigned(
    service: MaintenanceService, property_id: int, daniel_employee_id: int, admin_user_id: int
) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        assigned = service.assign_employee(request.MaintenanceRequestId, daniel_employee_id, user_id=admin_user_id)
        assert assigned.AssignedEmployeeId == daniel_employee_id
        assert assigned.MaintenanceStatus == "Assigned"
    finally:
        _delete(service, request)


def test_assign_employee_rejects_unknown_employee(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        with pytest.raises(AppError) as exc_info:
            service.assign_employee(request.MaintenanceRequestId, 999_999, user_id=admin_user_id)
        assert exc_info.value.code == "EMPLOYEE_NOT_FOUND"
    finally:
        _delete(service, request)


def test_assign_employee_rejects_inactive_employee(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    inactive_employee = Employee(
        FirstName="Test",
        LastName="Inactive",
        Email="test.inactive.employee@example.com",
        HireDate=TODAY,
        IsActive=False,
    )
    service.db.add(inactive_employee)
    service.db.flush()
    try:
        with pytest.raises(AppError) as exc_info:
            service.assign_employee(request.MaintenanceRequestId, inactive_employee.EmployeeId, user_id=admin_user_id)
        assert exc_info.value.code == "EMPLOYEE_INACTIVE"
    finally:
        _delete(service, request)
        service.db.delete(inactive_employee)
        service.db.commit()


# ---------- priority / status / notes / costs (assignment-restricted actions) ----------


def test_change_priority_updates_priority(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        updated = service.change_priority(request.MaintenanceRequestId, "Emergency", user_id=admin_user_id)
        assert updated.Priority == "Emergency"
    finally:
        _delete(service, request)


def test_change_status_rejected_for_employee_not_assigned(
    service: MaintenanceService, property_id: int, admin_user_id: int, daniel_user: User
) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)  # not assigned to Daniel
    try:
        with pytest.raises(AppError) as exc_info:
            service.change_status(request.MaintenanceRequestId, "In Progress", actor=daniel_user)
        assert exc_info.value.code == "MAINTENANCE_NOT_ASSIGNED_TO_YOU"
    finally:
        _delete(service, request)


def test_change_status_allowed_for_assigned_employee(
    service: MaintenanceService, property_id: int, daniel_employee_id: int, admin_user_id: int, daniel_user: User
) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.assign_employee(request.MaintenanceRequestId, daniel_employee_id, user_id=admin_user_id)
        updated = service.change_status(request.MaintenanceRequestId, "In Progress", actor=daniel_user)
        assert updated.MaintenanceStatus == "In Progress"
    finally:
        _delete(service, request)


def test_add_note_by_assigned_employee_appends_note(
    service: MaintenanceService, property_id: int, daniel_employee_id: int, admin_user_id: int, daniel_user: User
) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.assign_employee(request.MaintenanceRequestId, daniel_employee_id, user_id=admin_user_id)
        updated = service.add_note(request.MaintenanceRequestId, "Checked the unit, ordering a part.", actor=daniel_user)
        assert len(updated.MaintenanceNotes) == 1
        assert updated.MaintenanceNotes[0].NoteText == "Checked the unit, ordering a part."
        assert updated.MaintenanceNotes[0].EmployeeId == daniel_employee_id
    finally:
        _delete(service, request)


def test_enter_costs_updates_estimated_and_actual(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        updated = service.enter_costs(request.MaintenanceRequestId, estimated_cost=150, actual_cost=None, actor=admin)
        assert updated.EstimatedCost == 150
        assert updated.ActualCost is None

        updated = service.enter_costs(request.MaintenanceRequestId, estimated_cost=None, actual_cost=165, actor=admin)
        assert updated.EstimatedCost == 150  # untouched
        assert updated.ActualCost == 165
    finally:
        _delete(service, request)


def test_enter_costs_rejected_on_cancelled_request(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.cancel_request(request.MaintenanceRequestId, notes=None, user_id=admin_user_id)
        with pytest.raises(AppError) as exc_info:
            service.enter_costs(request.MaintenanceRequestId, estimated_cost=100, actual_cost=None, actor=admin)
        assert exc_info.value.code == "MAINTENANCE_ALREADY_CANCELLED"
    finally:
        _delete(service, request)


# ---------- complete / cancel ----------


def test_complete_request_sets_completion_fields(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        completed = service.complete_request(
            request.MaintenanceRequestId,
            completed_date=None,
            resolution_notes="Fixed the issue.",
            actual_cost=90,
            actor=admin,
        )
        assert completed.MaintenanceStatus == "Completed"
        assert completed.CompletedDate == TODAY
        assert completed.ResolutionNotes == "Fixed the issue."
        assert completed.ActualCost == 90
    finally:
        _delete(service, request)


def test_complete_request_rejects_completion_date_before_reported_date(
    service: MaintenanceService, property_id: int, admin_user_id: int
) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        with pytest.raises(AppError) as exc_info:
            service.complete_request(
                request.MaintenanceRequestId,
                completed_date=TODAY - timedelta(days=30),
                resolution_notes="Backdated by mistake.",
                actual_cost=None,
                actor=admin,
            )
        assert exc_info.value.code == "MAINTENANCE_INVALID_COMPLETION_DATE"
    finally:
        _delete(service, request)


def test_complete_request_rejected_when_already_completed(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.complete_request(request.MaintenanceRequestId, completed_date=None, resolution_notes="Done.", actual_cost=None, actor=admin)
        with pytest.raises(AppError) as exc_info:
            service.complete_request(request.MaintenanceRequestId, completed_date=None, resolution_notes="Done again?", actual_cost=None, actor=admin)
        assert exc_info.value.code == "MAINTENANCE_ALREADY_COMPLETED"
    finally:
        _delete(service, request)


def test_cancel_request_rejects_already_completed_request(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    admin = service.db.execute(select(User).where(User.UserId == admin_user_id)).scalar_one()
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.complete_request(request.MaintenanceRequestId, completed_date=None, resolution_notes="Done.", actual_cost=None, actor=admin)
        with pytest.raises(AppError) as exc_info:
            service.cancel_request(request.MaintenanceRequestId, notes=None, user_id=admin_user_id)
        assert exc_info.value.code == "MAINTENANCE_ALREADY_COMPLETED"
    finally:
        _delete(service, request)


def test_cancel_request_rejects_already_cancelled_request(service: MaintenanceService, property_id: int, admin_user_id: int) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        service.cancel_request(request.MaintenanceRequestId, notes=None, user_id=admin_user_id)
        with pytest.raises(AppError) as exc_info:
            service.cancel_request(request.MaintenanceRequestId, notes=None, user_id=admin_user_id)
        assert exc_info.value.code == "MAINTENANCE_ALREADY_CANCELLED"
    finally:
        _delete(service, request)


# ---------- MaintenanceEmployee's restricted view ----------


def test_list_requests_restricts_maintenance_employee_to_own_assignments(
    service: MaintenanceService, property_id: int, daniel_employee_id: int, admin_user_id: int, daniel_user: User
) -> None:
    assigned_to_daniel = service.create_request(_payload(property_id, RequestReference="MR-SVC-TEST-002"), user_id=admin_user_id)
    unassigned = service.create_request(_payload(property_id, RequestReference="MR-SVC-TEST-003"), user_id=admin_user_id)
    try:
        service.assign_employee(assigned_to_daniel.MaintenanceRequestId, daniel_employee_id, user_id=admin_user_id)

        items, total = service.list_requests(
            page=1,
            page_size=100,
            search=None,
            property_id=None,
            tenant_id=None,
            assigned_employee_id=None,  # Daniel asks for everything...
            category=None,
            priority=None,
            maintenance_status=None,
            reported_date_from=None,
            reported_date_to=None,
            sort_by="ReportedDate",
            sort_dir="desc",
            viewer=daniel_user,  # ...but only sees his own.
        )
        references = {i.RequestReference for i in items}
        assert "MR-SVC-TEST-002" in references
        assert "MR-SVC-TEST-003" not in references
        assert all(i.AssignedEmployeeId == daniel_employee_id for i in items if i.RequestReference.startswith("MR-SVC-TEST"))
    finally:
        _delete(service, assigned_to_daniel)
        _delete(service, unassigned)


def test_get_request_rejected_for_employee_not_assigned(
    service: MaintenanceService, property_id: int, admin_user_id: int, daniel_user: User
) -> None:
    request = service.create_request(_payload(property_id), user_id=admin_user_id)
    try:
        with pytest.raises(AppError) as exc_info:
            service.get_request(request.MaintenanceRequestId, viewer=daniel_user)
        assert exc_info.value.code == "MAINTENANCE_NOT_ASSIGNED_TO_YOU"
    finally:
        _delete(service, request)
