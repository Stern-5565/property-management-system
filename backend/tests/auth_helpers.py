"""Shared test helper for logging in as one of the seeded demo users.

Not a test file itself (no test_ prefix, so pytest won't collect it).
"""

from fastapi.testclient import TestClient

DEMO_PASSWORD = "Password123!"

ADMIN_EMAIL = "sarah.mitchell@propertymanager.example"  # Administrator
PROPERTY_MANAGER_EMAIL = "james.carter@propertymanager.example"  # PropertyManager
MAINTENANCE_EMPLOYEE_EMAIL = "daniel.osei@propertymanager.example"  # MaintenanceEmployee
READ_ONLY_EMAIL = "emma.wilson@propertymanager.example"  # ReadOnly


def get_access_token(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD) -> str:
    response = client.post("/api/auth/login", json={"Email": email, "Password": password})
    assert response.status_code == 200, f"Login failed for {email}: {response.text}"
    return response.json()["access_token"]


def auth_headers(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_access_token(client, email, password)}"}
