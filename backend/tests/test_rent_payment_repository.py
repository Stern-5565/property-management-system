"""Tests for RentPaymentRepository - direct database access, no business
rules. Read-only against the seeded demo data (30 rent payments) - no
cleanup needed.
"""

from app.database.session import SessionLocal
from app.repositories.rent_payment_repository import RentPaymentRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, RentPaymentRepository(db)


def test_get_by_id_returns_none_for_missing_payment() -> None:
    db, repo = get_repo()
    try:
        assert repo.get_by_id(999_999) is None
    finally:
        db.close()


def test_get_by_reference_finds_payment() -> None:
    db, repo = get_repo()
    try:
        payment = repo.get_by_reference("PAY-00001")
        assert payment is not None
        assert payment.PaymentStatus == "Paid"
    finally:
        db.close()


def test_list_returns_all_seeded_payments() -> None:
    db, repo = get_repo()
    try:
        items, total = repo.list(
            page=1, page_size=100, tenancy_id=None, property_id=None, tenant_id=None,
            payment_status=None, due_date_from=None, due_date_to=None,
        )
        assert total == 30
    finally:
        db.close()


def test_list_filters_by_status_matches_known_counts() -> None:
    db, repo = get_repo()
    try:
        _, paid_total = repo.list(
            page=1, page_size=100, tenancy_id=None, property_id=None, tenant_id=None,
            payment_status="Paid", due_date_from=None, due_date_to=None,
        )
        assert paid_total == 23

        _, partial_total = repo.list(
            page=1, page_size=100, tenancy_id=None, property_id=None, tenant_id=None,
            payment_status="Partially Paid", due_date_from=None, due_date_to=None,
        )
        assert partial_total == 2

        _, cancelled_total = repo.list(
            page=1, page_size=100, tenancy_id=None, property_id=None, tenant_id=None,
            payment_status="Cancelled", due_date_from=None, due_date_to=None,
        )
        assert cancelled_total == 1
    finally:
        db.close()


def test_list_filters_by_property_id() -> None:
    db, repo = get_repo()
    try:
        payment = repo.get_by_reference("PAY-00001")  # PM-0001, John Okafor
        property_id = payment.Tenancy.PropertyId

        items, total = repo.list(
            page=1, page_size=100, tenancy_id=None, property_id=property_id, tenant_id=None,
            payment_status=None, due_date_from=None, due_date_to=None,
        )
        # AGR-1001 has PAY-00001 through PAY-00004
        assert total == 4
    finally:
        db.close()


def test_list_overdue_matches_report_2() -> None:
    db, repo = get_repo()
    try:
        overdue = repo.list_overdue()
        # Matches database/07-report-queries.sql, Report 2's known result
        # against this same seeded data: 4 rows, not just the 2 whose
        # STORED status happens to say "Overdue". PAY-00008 (AGR-1002) and
        # PAY-00028 (AGR-1010) are stored as "Partially Paid" - some money
        # was received, so calculate_payment_status() reports that as the
        # single status label - but their due dates have ALSO passed with
        # a balance still outstanding, so the (intentionally more
        # inclusive) overdue query correctly flags them for chasing too. A
        # payment can legitimately be "Partially Paid" (the status label)
        # AND appear on the overdue attention list at the same time - the
        # two answer different questions.
        references = {p.PaymentReference for p in overdue}
        assert references == {"PAY-00004", "PAY-00008", "PAY-00019", "PAY-00028"}
    finally:
        db.close()


def test_list_due_this_month_matches_report_1() -> None:
    db, repo = get_repo()
    try:
        due_this_month = repo.list_due_this_month()
        # Matches Report 1's known result: the 7 August-2026 rows.
        assert len(due_this_month) == 7
    finally:
        db.close()
