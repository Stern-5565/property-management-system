"""Tests for DashboardService.

safe_percentage is a pure function (no I/O) - tested directly, including
the zero-denominator case that matters most for the scope doc's "handle
empty databases" / "prevent division by zero" requirements. The
get_summary/get_occupancy checks below are lighter integration checks
against the real seeded data - see test_dashboard_repository.py for the
full breakdown of expected values and test_dashboard_api.py for the
end-to-end HTTP versions of the same numbers.
"""

from app.database.session import SessionLocal
from app.services.dashboard_service import DashboardService, safe_percentage


def test_safe_percentage_normal_case() -> None:
    assert safe_percentage(6, 9) == 66.7


def test_safe_percentage_zero_numerator() -> None:
    assert safe_percentage(0, 10) == 0.0


def test_safe_percentage_zero_denominator_does_not_raise() -> None:
    """The exact scenario an empty database produces: zero properties,
    zero rent due, etc. - must return 0.0, never raise ZeroDivisionError."""
    assert safe_percentage(0, 0) == 0.0


def test_safe_percentage_rounds_to_one_decimal_place() -> None:
    assert safe_percentage(1, 3) == 33.3


def test_get_summary_matches_seeded_data() -> None:
    db = SessionLocal()
    try:
        service = DashboardService(db)
        summary = service.get_summary()
        assert summary.TotalActiveProperties == 9
        assert summary.OccupiedProperties == 6
        assert summary.OccupancyPercentage == 66.7
        assert summary.ActiveTenancies == 6
        assert summary.OpenMaintenanceRequests == 12
        assert summary.EmergencyMaintenanceRequests == 4
    finally:
        db.close()


def test_get_occupancy_percentages_sum_to_roughly_100() -> None:
    db = SessionLocal()
    try:
        service = DashboardService(db)
        occupancy = service.get_occupancy()
        total_percentage = sum(item.PercentageOfPortfolio for item in occupancy.StatusBreakdown)
        # Each figure is independently rounded to 1dp, so the sum can be
        # off by a rounding hair - not exactly 100.0.
        assert 99.0 <= total_percentage <= 101.0
    finally:
        db.close()


def test_get_maintenance_summary_orders_emergency_first() -> None:
    db = SessionLocal()
    try:
        service = DashboardService(db)
        summary = service.get_maintenance_summary()
        priorities = [item.Priority for item in summary.StatusBreakdown]
        emergency_positions = [i for i, p in enumerate(priorities) if p == "Emergency"]
        low_positions = [i for i, p in enumerate(priorities) if p == "Low"]
        assert emergency_positions and low_positions
        assert max(emergency_positions) < min(low_positions)
    finally:
        db.close()
