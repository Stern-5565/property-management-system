/**
 * Wraps /api/dashboard/* - see backend/app/api/routes/dashboard.py. Every
 * route here is read-only (no request bodies) and every response schema
 * fills its own numeric defaults server-side (0, 0.0, empty list) rather
 * than nullable fields - see app/schemas/dashboard.py's own docstring -
 * so DashboardPage never needs to null-check a KPI figure.
 */
import { apiClient } from "../api/client";

export async function getSummary() {
  const { data } = await apiClient.get("/dashboard/summary");
  return data; // DashboardSummaryResponse
}

export async function getRentSummary(monthsBack = 6) {
  const { data } = await apiClient.get("/dashboard/rent-summary", { params: { months_back: monthsBack } });
  return data; // RentSummaryResponse
}

export async function getOccupancy() {
  const { data } = await apiClient.get("/dashboard/occupancy");
  return data; // OccupancyResponse
}

export async function getMaintenanceSummary() {
  const { data } = await apiClient.get("/dashboard/maintenance-summary");
  return data; // MaintenanceSummaryResponse
}

export async function getRecentActivity(limit = 10) {
  const { data } = await apiClient.get("/dashboard/recent-activity", { params: { limit } });
  return data; // RecentActivityItem[]
}
