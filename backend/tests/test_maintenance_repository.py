"""Tests for MaintenanceRepository - direct database access, no business
rules. Read-only against the seeded demo data (20 requests, 8 notes,
comment block at database/06-seed-demo-data.sql lines 229-232 for the
exact breakdown this file's assertions are built from) - no cleanup
needed.
"""

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.employee import Employee
from app.repositories.maintenance_repository import MaintenanceRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, MaintenanceRepository(db)


def _list_kwargs(**overrides) -> dict:
    defaults = dict(
        page=1,
        page_size=100,
        search=None,
        property_id=None,
        tenant_id=None,
        assigned_employee_id=None,
        category=None,
        priority=None,
        maintenance_status=None,
        reported_date_from=None,
        reported_date_to=None,
        sort_by="ReportedDate",
        sort_dir="desc",
    )
    defaults.update(overrides)
    return defaults


def test_get_by_id_returns_none_for_missing_request() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_reference_finds_request() -> None:
    db, repo = get_repo()
    try:
        request = repo.get_by_reference("MR-0001")
        assert request is not None
        assert request.MaintenanceStatus == "Completed"
    finally:
        db.close()


def test_list_returns_all_seeded_requests() -> None:
    db, repo = get_repo()
    try:
        _, total = repo.list(**_list_kwargs())
        assert total == 20
    finally:
        db.close()


def test_list_filters_by_status_matches_known_counts() -> None:
    db, repo = get_repo()
    try:
        _, completed_total = repo.list(**_list_kwargs(maintenance_status="Completed"))
        assert completed_total == 6

        _, cancelled_total = repo.list(**_list_kwargs(maintenance_status="Cancelled"))
        assert cancelled_total == 2
    finally:
        db.close()


def test_list_filters_by_priority_finds_emergencies() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(**_list_kwargs(priority="Emergency"))
        assert total == 4
        assert {i.RequestReference for i in items} == {"MR-0002", "MR-0007", "MR-0014", "MR-0020"}
    finally:
        db.close()


def test_list_filters_by_category() -> None:
    db, repo = get_repo()
    try:
        _, total = repo.list(**_list_kwargs(category="Plumbing"))
        assert total == 3  # MR-0001, MR-0008, MR-0015
    finally:
        db.close()


def test_list_filters_by_property_id() -> None:
    db, repo = get_repo()
    try:
        request = repo.get_by_reference("MR-0001")  # PM-0001
        _, total = repo.list(**_list_kwargs(property_id=request.PropertyId))
        assert total == 3  # MR-0001, MR-0002, MR-0018
    finally:
        db.close()


def test_list_filters_by_assigned_employee_id() -> None:
    db, repo = get_repo()
    try:
        daniel = db.execute(select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")).scalar_one()
        _, total = repo.list(**_list_kwargs(assigned_employee_id=daniel.EmployeeId))
        assert total == 12
    finally:
        db.close()


def test_list_search_matches_title_and_description() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(**_list_kwargs(search="Boiler"))
        assert total == 1
        assert items[0].RequestReference == "MR-0007"
    finally:
        db.close()


def test_list_workload_aggregates_open_assignments_per_employee() -> None:
    db, repo = get_repo()
    try:
        rows = repo.list_workload()
        by_name = {f"{row.FirstName} {row.LastName}": (row.OpenRequestCount, row.EmergencyOpenCount) for row in rows}
        # Only Daniel Osei has any assignment in the seeded data. Of his 12
        # total assignments, 6 are Completed (see the module docstring
        # breakdown), leaving 6 open - 3 of them Emergency priority
        # (MR-0002, MR-0007, MR-0014).
        assert by_name["Daniel Osei"] == (6, 3)
        assert "Emma Wilson" not in by_name
    finally:
        db.close()
