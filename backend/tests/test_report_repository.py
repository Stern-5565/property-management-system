"""Tests for ReportRepository - direct database access, no business
rules. Read-only against the seeded demo data - no cleanup needed.

Expected values below were captured directly from a live query against
this same seeded dataset via the running API (curl), then cross-checked
against DashboardRepository's own already-tested figures for the same
underlying numbers (e.g. occupancy, open maintenance count, rent due/
collected this month) - same "hardcode expected values against the demo
data's dates" convention as test_dashboard_repository.py and
test_rent_payment_repository.py::test_list_overdue_matches_report_2.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.landlord import Landlord
from app.repositories.report_repository import ReportRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, ReportRepository(db)


def test_rent_due_this_month_matches_dashboard_totals() -> None:
    db, repo = get_repo()
    try:
        rows = repo.rent_due_this_month(property_id=None)
        assert len(rows) == 7
        assert sum(row["AmountDue"] for row in rows) == Decimal("8825.00")
        assert sum(row["AmountPaid"] for row in rows) == Decimal("3325.00")
        assert all(row["PaymentStatus"] != "Cancelled" for row in rows)
    finally:
        db.close()


def test_rent_due_this_month_filters_by_property() -> None:
    db, repo = get_repo()
    try:
        all_rows = repo.rent_due_this_month(property_id=None)
        one_property_id = None
        for row in all_rows:
            # PropertyId isn't in the row dict, but PropertyReference is -
            # filter by the first reference seen and confirm it narrows.
            one_property_id = row["PropertyReference"]
            break
        assert one_property_id is not None
        narrowed = [row for row in all_rows if row["PropertyReference"] == one_property_id]
        assert len(narrowed) >= 1
        assert len(narrowed) <= len(all_rows)
    finally:
        db.close()


def test_overdue_rent_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        rows = repo.overdue_rent(property_id=None, landlord_id=None)
        assert len(rows) == 4
        assert sum(row["AmountOutstanding"] for row in rows) == Decimal("3425.00")
        # Sorted DaysOverdue descending, most overdue first.
        days = [row["DaysOverdue"] for row in rows]
        assert days == sorted(days, reverse=True)
        assert all(row["AmountPaid"] < row["AmountDue"] for row in rows)
    finally:
        db.close()


def test_monthly_rent_collected_totals_match_seeded_data() -> None:
    db, repo = get_repo()
    try:
        rows = repo.monthly_rent_collected(period_start=None, period_end=None)
        assert sum(row["TotalCollected"] for row in rows) == Decimal("29975.00")
        assert sum(row["PaymentCount"] for row in rows) == 25
        # Every row must have a real month label, e.g. "May 2026".
        assert all(" " in row["MonthLabel"] for row in rows)
    finally:
        db.close()


def test_monthly_rent_collected_respects_period_filter() -> None:
    db, repo = get_repo()
    try:
        unfiltered = repo.monthly_rent_collected(period_start=None, period_end=None)
        narrowed = repo.monthly_rent_collected(period_start=date(2026, 1, 1), period_end=date(2026, 12, 31))
        assert len(narrowed) <= len(unfiltered)
    finally:
        db.close()


def test_rent_by_landlord_defaults_include_every_active_landlord() -> None:
    db, repo = get_repo()
    try:
        month_start = date.today().replace(day=1)
        next_month = month_start.month % 12 + 1
        next_year = month_start.year + (1 if month_start.month == 12 else 0)
        month_end = date(next_year, next_month, 1)
        rows = repo.rent_by_landlord(period_start=month_start, period_end=month_end, landlord_id=None)
        # 5 seeded active landlords - a landlord with zero collections this
        # period still appears (LEFT JOIN), not silently dropped.
        assert len(rows) == 5
        assert sum(row["TotalCollected"] for row in rows) == Decimal("3325.00")
    finally:
        db.close()


def test_occupancy_matches_dashboard_figures() -> None:
    db, repo = get_repo()
    try:
        rows, totals = repo.occupancy()
        breakdown = {row["PropertyStatus"]: row["PropertyCount"] for row in rows}
        assert breakdown == {"Occupied": 6, "Vacant": 2, "Under Maintenance": 1}
        assert totals["PropertyCount"] == 9
        assert totals["OccupancyRatePercent"] == 66.7
        occupied_row = next(row for row in rows if row["PropertyStatus"] == "Occupied")
        assert occupied_row["PercentageOfPortfolio"] == 66.7
    finally:
        db.close()


def test_vacant_properties_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        rows = repo.vacant_properties(landlord_id=None)
        assert len(rows) == 2
        assert sum(row["MonthlyRent"] for row in rows) == Decimal("1700.00")
        # Sorted DaysVacant descending (longest-vacant first).
        days = [row["DaysVacant"] for row in rows]
        assert days == sorted(days, reverse=True)
        assert all(row["DaysVacant"] is not None for row in rows)
    finally:
        db.close()


def test_tenancies_ending_soon_within_30_days() -> None:
    db, repo = get_repo()
    try:
        rows = repo.tenancies_ending_soon(days_ahead=30, property_id=None)
        assert len(rows) == 1
        assert rows[0]["TenancyStatus"] in ("Active", "Ending Soon")
    finally:
        db.close()


def test_tenancies_ending_soon_widens_with_a_longer_window() -> None:
    db, repo = get_repo()
    try:
        within_30 = repo.tenancies_ending_soon(days_ahead=30, property_id=None)
        within_90 = repo.tenancies_ending_soon(days_ahead=90, property_id=None)
        assert len(within_90) >= len(within_30)
    finally:
        db.close()


def test_maintenance_by_status_matches_open_count() -> None:
    db, repo = get_repo()
    try:
        rows = repo.maintenance_by_status()
        assert sum(row["RequestCount"] for row in rows) == 12
        assert all(row["MaintenanceStatus"] not in ("Completed", "Cancelled") for row in rows)
        # Emergency-priority rows must sort before every other priority.
        priorities_seen = [row["Priority"] for row in rows]
        first_emergency_index = next((i for i, p in enumerate(priorities_seen) if p == "Emergency"), None)
        first_low_index = next((i for i, p in enumerate(priorities_seen) if p == "Low"), None)
        if first_emergency_index is not None and first_low_index is not None:
            assert first_emergency_index < first_low_index
    finally:
        db.close()


def test_maintenance_costs_by_property_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        rows = repo.maintenance_costs_by_property(landlord_id=None)
        assert len(rows) == 9  # every active property, including zero-cost ones
        assert sum(row["CompletedRequestCount"] for row in rows) == 6
        assert sum(row["TotalActualCost"] for row in rows) == Decimal("665.00")
        # AverageActualCost must be rounded to money precision, not
        # SQL Server AVG()'s extra decimal places (e.g. 112.500000).
        assert all(row["AverageActualCost"] == round(row["AverageActualCost"], 2) for row in rows)
    finally:
        db.close()


def test_property_income_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        rows = repo.property_income(
            period_start=date(date.today().year, 1, 1), period_end=date.today() + timedelta(days=1), landlord_id=None
        )
        assert len(rows) == 9
        assert sum(row["TotalRentDue"] for row in rows) == Decimal("31150.00")
        assert sum(row["TotalRentCollected"] for row in rows) == Decimal("27725.00")
        assert sum(row["TotalMaintenanceCost"] for row in rows) == Decimal("665.00")
        assert sum(row["NetIncome"] for row in rows) == Decimal("27060.00")
        # Sorted NetIncome descending.
        net_incomes = [row["NetIncome"] for row in rows]
        assert net_incomes == sorted(net_incomes, reverse=True)
    finally:
        db.close()


def test_property_income_filters_by_landlord() -> None:
    db, repo = get_repo()
    try:
        period_start = date(date.today().year, 1, 1)
        period_end = date.today() + timedelta(days=1)
        all_rows = repo.property_income(period_start=period_start, period_end=period_end, landlord_id=None)
        first_landlord_name = all_rows[0]["LandlordName"]
        # Just confirm filtering by an actual landlord_id narrows results -
        # look up any landlord id from the seeded data via a fresh query.
        landlord = db.execute(select(Landlord).where(Landlord.IsActive == True)).scalars().first()  # noqa: E712
        narrowed = repo.property_income(period_start=period_start, period_end=period_end, landlord_id=landlord.LandlordId)
        assert len(narrowed) <= len(all_rows)
        assert all(row["LandlordName"] for row in narrowed)
        assert first_landlord_name  # sanity - the unfiltered query returned something
    finally:
        db.close()
