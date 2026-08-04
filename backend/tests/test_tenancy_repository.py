"""Tests for TenancyRepository - direct database access, no business rules.

Read-only against the seeded demo data (12 tenancies) - no cleanup needed.
"""

from datetime import date

from app.database.session import SessionLocal
from app.repositories.tenancy_repository import TenancyRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, TenancyRepository(db)


def test_get_by_id_returns_none_for_missing_tenancy() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_agreement_reference_finds_tenancy() -> None:
    db, repo = get_repo()
    try:
        tenancy = repo.get_by_agreement_reference("AGR-1001")
        assert tenancy is not None
        assert tenancy.TenancyStatus == "Ending Soon"
    finally:
        db.close()


def test_list_returns_all_seeded_tenancies() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, property_id=None, tenant_id=None, tenancy_status=None)
        assert total == 12
    finally:
        db.close()


def test_list_filters_by_status() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(page=1, page_size=20, property_id=None, tenant_id=None, tenancy_status="Ended")
        assert total == 4  # AGR-1003, AGR-1008, AGR-1009, AGR-1011
    finally:
        db.close()


def test_list_filters_by_property_id() -> None:
    db, repo = get_repo()
    try:
        pm_0001_tenancy = repo.get_by_agreement_reference("AGR-1001")
        items, total = repo.list(
            page=1, page_size=20, property_id=pm_0001_tenancy.PropertyId, tenant_id=None, tenancy_status=None
        )
        # PM-0001 has AGR-1001 (Ending Soon) and AGR-1012 (Upcoming)
        assert total == 2
    finally:
        db.close()


def test_list_expiring_within_30_days_matches_report_7() -> None:
    db, repo = get_repo()
    try:
        # Matches database/07-report-queries.sql, Report 7's known result
        # against this same seeded data: only AGR-1001 (PM-0001, ends
        # 2026-08-31) falls within 30 days of "today" (2026-08-04).
        expiring = repo.list_expiring(days=30)
        assert len(expiring) == 1
        assert expiring[0].AgreementReference == "AGR-1001"
    finally:
        db.close()


def test_find_overlapping_tenancy_detects_conflict_on_same_property() -> None:
    db, repo = get_repo()
    try:
        # AGR-1002 on PM-0003 runs 2025-11-01 to 2026-10-31 (Active).
        # A candidate tenancy on the same property overlapping that range
        # should be detected as a conflict.
        agr_1002 = repo.get_by_agreement_reference("AGR-1002")
        conflict = repo.find_overlapping_tenancy(
            property_id=agr_1002.PropertyId,
            exclude_tenancy_id=999_999,  # not excluding the real tenancy
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 1),
        )
        assert conflict is not None
        assert conflict.AgreementReference == "AGR-1002"
    finally:
        db.close()


def test_find_overlapping_tenancy_excludes_itself() -> None:
    db, repo = get_repo()
    try:
        agr_1002 = repo.get_by_agreement_reference("AGR-1002")
        conflict = repo.find_overlapping_tenancy(
            property_id=agr_1002.PropertyId,
            exclude_tenancy_id=agr_1002.TenancyId,
            start_date=agr_1002.StartDate,
            end_date=agr_1002.EndDate,
        )
        assert conflict is None
    finally:
        db.close()


def test_find_overlapping_tenancy_returns_none_for_non_overlapping_dates() -> None:
    db, repo = get_repo()
    try:
        agr_1002 = repo.get_by_agreement_reference("AGR-1002")  # 2025-11-01 to 2026-10-31
        conflict = repo.find_overlapping_tenancy(
            property_id=agr_1002.PropertyId,
            exclude_tenancy_id=999_999,
            start_date=date(2027, 1, 1),
            end_date=date(2027, 6, 1),
        )
        assert conflict is None
    finally:
        db.close()
