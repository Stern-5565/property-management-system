"""Tests for DashboardRepository - direct database access, no business
rules. Read-only against the seeded demo data - no cleanup needed.

Expected values below were captured directly from a live query against
this same seeded dataset (see documentation/progress-log.md's Dashboard
section) - same convention as
test_rent_payment_repository.py::test_list_overdue_matches_report_2 and
test_rent_payment_repository.py::test_list_due_this_month_matches_report_1,
which hardcode expected counts against the demo data's dates rather than
recomputing them, since the demo data's dates are themselves anchored
around a fixed "today".
"""

from app.database.session import SessionLocal
from app.repositories.dashboard_repository import DashboardRepository


def get_repo() -> tuple:
    db = SessionLocal()
    return db, DashboardRepository(db)


def test_occupancy_summary_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        total, occupied, vacant = repo.occupancy_summary()
        # 10 seeded properties, 1 archived (PM-0010, IsActive=0) - see
        # test_landlord_repository.py's has_active_properties tests.
        assert total == 9
        assert occupied == 6
        assert vacant == 2
    finally:
        db.close()


def test_occupancy_breakdown_covers_every_active_status() -> None:
    db, repo = get_repo()
    try:
        breakdown = dict(repo.occupancy_breakdown())
        assert breakdown == {"Occupied": 6, "Vacant": 2, "Under Maintenance": 1}
    finally:
        db.close()


def test_active_tenancies_count_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.active_tenancies_count() == 6
    finally:
        db.close()


def test_tenancies_ending_soon_count_within_30_days() -> None:
    db, repo = get_repo()
    try:
        assert repo.tenancies_ending_soon_count(days_ahead=30) == 1
    finally:
        db.close()


def test_tenancies_ending_soon_count_widens_with_a_longer_window() -> None:
    db, repo = get_repo()
    try:
        within_90 = repo.tenancies_ending_soon_count(days_ahead=90)
        within_30 = repo.tenancies_ending_soon_count(days_ahead=30)
        assert within_90 >= within_30
    finally:
        db.close()


def test_rent_due_this_month_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.rent_due_this_month() == 8825.00
    finally:
        db.close()


def test_rent_collected_this_month_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.rent_collected_this_month() == 3325.00
    finally:
        db.close()


def test_outstanding_rent_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.outstanding_rent() == 6475.00
    finally:
        db.close()


def test_monthly_rent_collection_includes_current_month_totalling_collected_this_month() -> None:
    db, repo = get_repo()
    try:
        rows = repo.monthly_rent_collection(months_back=6)
        assert len(rows) >= 1
        # The last row (most recent month with any collection) must equal
        # rent_collected_this_month() exactly - both describe the same
        # current-month total, computed two different ways.
        _, _, _, latest_total = rows[-1]
        assert latest_total == repo.rent_collected_this_month()
    finally:
        db.close()


def test_monthly_rent_collection_respects_months_back_window() -> None:
    db, repo = get_repo()
    try:
        wide = repo.monthly_rent_collection(months_back=12)
        narrow = repo.monthly_rent_collection(months_back=1)
        assert len(narrow) <= len(wide)
    finally:
        db.close()


def test_open_maintenance_count_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.open_maintenance_count() == 12
    finally:
        db.close()


def test_emergency_maintenance_count_matches_seeded_data() -> None:
    db, repo = get_repo()
    try:
        assert repo.emergency_maintenance_count() == 4
    finally:
        db.close()


def test_maintenance_status_breakdown_sums_to_open_count() -> None:
    db, repo = get_repo()
    try:
        breakdown = repo.maintenance_status_breakdown()
        assert sum(count for _, _, count in breakdown) == repo.open_maintenance_count()
        # None of the breakdown rows should be for a terminal status.
        assert all(status not in ("Completed", "Cancelled") for status, _, _ in breakdown)
    finally:
        db.close()


def test_recent_activity_returns_rows_ordered_newest_first() -> None:
    db, repo = get_repo()
    try:
        logs = repo.recent_activity(limit=5)
        assert len(logs) <= 5
        timestamps = [log.CreatedAt for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)
    finally:
        db.close()


def test_recent_activity_respects_limit() -> None:
    db, repo = get_repo()
    try:
        logs = repo.recent_activity(limit=2)
        assert len(logs) == 2
    finally:
        db.close()
