"""End-to-end HTTP tests for the Dashboard API routes.

All read-only - no throwaway rows, no cleanup needed. Logged in as the
Administrator demo user throughout; permission-boundary tests live
separately in test_dashboard_permissions.py. Expected values match
test_dashboard_repository.py - see that file's module docstring for
where they came from.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)


def test_summary_returns_expected_kpis() -> None:
    response = client.get("/api/dashboard/summary", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["TotalActiveProperties"] == 9
    assert body["OccupiedProperties"] == 6
    assert body["VacantProperties"] == 2
    assert body["OccupancyPercentage"] == 66.7
    assert body["ActiveTenancies"] == 6
    assert float(body["RentDueThisMonth"]) == 8825.00
    assert float(body["RentCollectedThisMonth"]) == 3325.00
    assert float(body["OutstandingRent"]) == 6475.00
    assert body["OpenMaintenanceRequests"] == 12
    assert body["EmergencyMaintenanceRequests"] == 4
    assert body["TenanciesEndingSoon"] == 1


def test_rent_summary_monthly_collection_matches_current_month_total() -> None:
    response = client.get("/api/dashboard/rent-summary", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert float(body["RentCollectedThisMonth"]) == 3325.00
    assert body["CollectionRatePercent"] == 37.7
    latest_point = body["MonthlyCollection"][-1]
    assert float(latest_point["TotalCollected"]) == float(body["RentCollectedThisMonth"])
    assert latest_point["MonthLabel"].startswith("August")


def test_rent_summary_respects_months_back_query_param() -> None:
    response = client.get("/api/dashboard/rent-summary", params={"months_back": 1}, headers=HEADERS)

    assert response.status_code == 200
    assert len(response.json()["MonthlyCollection"]) <= 1


def test_occupancy_breakdown_matches_seeded_data() -> None:
    response = client.get("/api/dashboard/occupancy", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["TotalProperties"] == 9
    breakdown = {item["PropertyStatus"]: item["PropertyCount"] for item in body["StatusBreakdown"]}
    assert breakdown == {"Occupied": 6, "Vacant": 2, "Under Maintenance": 1}


def test_maintenance_summary_excludes_terminal_statuses() -> None:
    response = client.get("/api/dashboard/maintenance-summary", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["OpenRequests"] == 12
    assert body["EmergencyRequests"] == 4
    statuses = {item["MaintenanceStatus"] for item in body["StatusBreakdown"]}
    assert "Completed" not in statuses
    assert "Cancelled" not in statuses


def test_recent_activity_respects_limit_and_returns_predictable_shape() -> None:
    response = client.get("/api/dashboard/recent-activity", params={"limit": 3}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body) <= 3
    for item in body:
        assert "AuditLogId" in item
        assert "Action" in item
        assert "EntityName" in item
        assert "CreatedAt" in item
