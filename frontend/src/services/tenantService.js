/**
 * Wraps /api/tenants - see backend/app/api/routes/tenants.py. Same
 * activate/deactivate shape as landlordService.js (PATCH /status takes
 * IsActive either direction; DELETE is the guarded deactivate).
 */
import { apiClient } from "../api/client";

export async function listTenants({ page = 1, pageSize = 20, search, isActive } = {}) {
  const { data } = await apiClient.get("/tenants", {
    params: { page, page_size: pageSize, search: search || undefined, is_active: isActive },
  });
  return data; // PaginatedResponse<TenantListItem>
}

export async function getTenant(tenantId) {
  const { data } = await apiClient.get(`/tenants/${tenantId}`);
  return data; // TenantResponse
}

export async function createTenant(payload) {
  const { data } = await apiClient.post("/tenants", payload);
  return data;
}

export async function updateTenant(tenantId, payload) {
  const { data } = await apiClient.put(`/tenants/${tenantId}`, payload);
  return data;
}

export async function setTenantStatus(tenantId, isActive) {
  const { data } = await apiClient.patch(`/tenants/${tenantId}/status`, { IsActive: isActive });
  return data;
}

/** Soft-delete - rejected if the tenant still has an active, upcoming, or
 * draft tenancy (TENANT_HAS_ACTIVE_TENANCY, 409). Use
 * setTenantStatus(id, true) to reactivate. */
export async function deactivateTenant(tenantId) {
  await apiClient.delete(`/tenants/${tenantId}`);
}
