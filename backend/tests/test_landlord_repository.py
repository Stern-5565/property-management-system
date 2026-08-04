"""Tests for LandlordRepository - direct database access, no business rules.

Read-only against the seeded demo data, so no cleanup is needed here (unlike
test_landlord_service.py and test_landlord_api.py, which create throwaway
rows because they exercise write operations).
"""

from app.database.session import SessionLocal
from app.repositories.landlord_repository import LandlordRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, LandlordRepository(db)


def test_get_by_id_returns_none_for_missing_landlord() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_email_finds_landlord() -> None:
    db, repo = get_repo()
    try:
        landlord = repo.get_by_email("robert.jenkins@example.com")
        assert landlord is not None
        assert landlord.LastName == "Jenkins"
    finally:
        db.close()


def test_get_by_email_returns_none_for_unknown_email() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_email("nobody@example.com") is None
    finally:
        db.close()


def test_list_returns_all_seeded_landlords() -> None:
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
        # No overlap between pages.
        assert {i.LandlordId for i in items}.isdisjoint({i.LandlordId for i in items_page_2})
    finally:
        db.close()

def test_list_search_matches_company_name() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="Green Oak", is_active=None)
        assert total == 1
        assert items[0].CompanyName == "Green Oak Properties Ltd"
    finally:
        db.close()


def test_list_search_matches_partial_email_case_insensitively() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="FIONA.CAMPBELL", is_active=None)
        assert total == 1
        assert items[0].LastName == "Campbell"
    finally:
        db.close()


def test_list_search_matches_last_name() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, search="O'Brien", is_active=None)
        assert total == 1
    finally:
        db.close()


def test_list_filters_by_is_active() -> None:
    db, repo = get_repo()
    try:
        # All 5 seeded landlords are active - filtering for inactive ones
        # should return zero.
        items, total = repo.list(page=1, page_size=20, search=None, is_active=False)
        assert total == 0
        assert items == []
    finally:
        db.close()


def test_has_active_properties_true_for_landlord_with_active_property() -> None:
    db, repo = get_repo()
    try:
        robert = repo.get_by_email("robert.jenkins@example.com")
        assert repo.has_active_properties(robert.LandlordId) is True
    finally:
        db.close()


def test_has_active_properties_false_for_landlord_with_only_archived_property() -> None:
    db, repo = get_repo()
    try:
        # Michael O'Brien's only property, PM-0010, is Archived (IsActive=0).
        michael = repo.get_by_email("michael.obrien@example.com")
        assert repo.has_active_properties(michael.LandlordId) is False
    finally:
        db.close()
