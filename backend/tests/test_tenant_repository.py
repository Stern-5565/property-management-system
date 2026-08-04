"""Tests for TenantRepository - direct database access, no business rules.

Read-only against the seeded demo data (12 tenants) - no cleanup needed.
"""

from app.database.session import SessionLocal
from app.repositories.tenant_repository import TenantRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, TenantRepository(db)


def test_get_by_id_returns_none_for_missing_tenant() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_email_finds_tenant() -> None:
    db, repo = get_repo()
    try:
        tenant = repo.get_by_email("john.okafor@example.com")
        assert tenant is not None
        assert tenant.LastName == "Okafor"
    finally:
        db.close()


def test_list_returns_all_seeded_tenants() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search=None, is_active=None)
        assert total == 12
        assert len(items) == 12
    finally:
        db.close()


def test_list_search_matches_last_name() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="Bennett", is_active=None)
        # Laura Bennett and Oliver Bennett both share this surname.
        assert total == 2
    finally:
        db.close()


def test_list_search_matches_phone() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="07700 900201", is_active=None)
        assert total == 1
        assert items[0].FirstName == "John"
    finally:
        db.close()


def test_has_active_tenancies_true_for_tenant_with_ending_soon_tenancy() -> None:
    db, repo = get_repo()
    try:
        john = repo.get_by_email("john.okafor@example.com")  # AGR-1001, Ending Soon
        assert repo.has_active_tenancies(john.TenantId) is True
    finally:
        db.close()


def test_has_active_tenancies_false_for_tenant_with_only_ended_tenancy() -> None:
    db, repo = get_repo()
    try:
        ahmed = repo.get_by_email("ahmed.hassan@example.com")  # AGR-1003, Ended
        assert repo.has_active_tenancies(ahmed.TenantId) is False
    finally:
        db.close()


def test_has_active_tenancies_true_for_upcoming_tenancy() -> None:
    db, repo = get_repo()
    try:
        amelia = repo.get_by_email("amelia.foster@example.com")  # AGR-1012, Upcoming
        assert repo.has_active_tenancies(amelia.TenantId) is True
    finally:
        db.close()
