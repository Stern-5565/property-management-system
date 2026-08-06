/**
 * Wraps /api/employees - see backend/app/api/routes/employees.py. Same
 * activate/deactivate shape as landlordService.js/tenantService.js
 * (PATCH /status takes IsActive either direction; DELETE is the guarded
 * deactivate, blocked on open maintenance assignments and cascading to
 * the linked User account one-way - see employee_service.py).
 */
import { apiClient } from "../api/client";

export async function listEmployees({ page = 1, pageSize = 20, search, isActive } = {}) {
  const { data } = await apiClient.get("/employees", {
    params: { page, page_size: pageSize, search: search || undefined, is_active: isActive },
  });
  return data; // PaginatedResponse<EmployeeListItem>
}

export async function getEmployee(employeeId) {
  const { data } = await apiClient.get(`/employees/${employeeId}`);
  return data; // EmployeeResponse
}

export async function createEmployee(payload) {
  const { data } = await apiClient.post("/employees", payload);
  return data;
}

export async function updateEmployee(employeeId, payload) {
  const { data } = await apiClient.put(`/employees/${employeeId}`, payload);
  return data;
}

export async function setEmployeeStatus(employeeId, isActive) {
  const { data } = await apiClient.patch(`/employees/${employeeId}/status`, { IsActive: isActive });
  return data;
}

/** Soft-delete - rejected if the employee still has open maintenance
 * assignments (EMPLOYEE_HAS_OPEN_MAINTENANCE_ASSIGNMENTS, 409). Also
 * deactivates their linked User account's login access, one-way (see
 * employee_service.py - reactivating here does NOT restore login).
 * Use setEmployeeStatus(id, true) to reactivate. */
export async function deactivateEmployee(employeeId) {
  await apiClient.delete(`/employees/${employeeId}`);
}
