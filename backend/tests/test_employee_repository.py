"""Tests for EmployeeRepository - direct database access, no business
rules. Read-only against the seeded demo data (5 employees) - no cleanup
needed.
"""

from app.database.session import SessionLocal
from app.repositories.employee_repository import EmployeeRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, EmployeeRepository(db)


def test_get_by_id_returns_none_for_missing_employee() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_email_finds_employee() -> None:
    db, repo = get_repo()
    try:
        employee = repo.get_by_email("daniel.osei@propertymanager.example")
        assert employee is not None
        assert employee.LastName == "Osei"
    finally:
        db.close()


def test_get_by_email_returns_none_for_unknown_email() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_email("nobody@example.com") is None
    finally:
        db.close()


def test_list_returns_all_seeded_employees() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search=None, is_active=None)
        assert total == 5
        assert len(items) == 5
    finally:
        db.close()


def test_list_pagination_splits_results_and_reports_total() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=2, search=None, is_active=None)
        assert total == 5
        assert len(items) == 2

        items_page_2, total_page_2 = repo.list(page=2, page_size=2, search=None, is_active=None)
        assert total_page_2 == 5
        assert len(items_page_2) == 2
        assert {i.EmployeeId for i in items}.isdisjoint({i.EmployeeId for i in items_page_2})
    finally:
        db.close()


def test_list_search_matches_department() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="Finance", is_active=None)
        assert total == 1
        assert items[0].LastName == "Wilson"
    finally:
        db.close()


def test_list_search_matches_job_title_substring() -> None:
    db, repo = get_repo()
    try:
        # "Senior Property Manager" (James Carter) and "Property Manager"
        # (Priya Patel) both contain the substring.
        items, total = repo.list(page=1, page_size=20, search="Property Manager", is_active=None)
        assert total == 2
        assert {i.LastName for i in items} == {"Carter", "Patel"}
    finally:
        db.close()


def test_list_filters_by_is_active() -> None:
    db, repo = get_repo()
    try:
        # All 5 seeded employees are active - filtering for inactive ones
        # should return zero.
        items, total = repo.list(page=1, page_size=20, search=None, is_active=False)
        assert total == 0
        assert items == []
    finally:
        db.close()


def test_has_open_maintenance_assignments_true_for_daniel() -> None:
    db, repo = get_repo()
    try:
        daniel = repo.get_by_email("daniel.osei@propertymanager.example")
        assert repo.has_open_maintenance_assignments(daniel.EmployeeId) is True
    finally:
        db.close()


def test_has_open_maintenance_assignments_false_for_employee_with_none() -> None:
    db, repo = get_repo()
    try:
        sarah = repo.get_by_email("sarah.mitchell@propertymanager.example")
        assert repo.has_open_maintenance_assignments(sarah.EmployeeId) is False
    finally:
        db.close()
