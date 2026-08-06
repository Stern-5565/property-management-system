/**
 * Wraps /api/tenancies - see backend/app/api/routes/tenancies.py. Unlike
 * every module before this one, there is no free-text `search` param
 * (TenancyRepository.list only filters by property_id/tenant_id/
 * tenancy_status - see the backend repository) and no generic status
 * PATCH - status only ever moves through the dedicated activate/end/
 * cancel actions below, since which transitions are legal depends on the
 * tenancy's current status (see tenancy_service.py).
 */
import { apiClient } from "../api/client";

export async function listTenancies({ page = 1, pageSize = 20, propertyId, tenantId, tenancyStatus } = {}) {
  const { data } = await apiClient.get("/tenancies", {
    params: {
      page,
      page_size: pageSize,
      property_id: propertyId || undefined,
      tenant_id: tenantId || undefined,
      tenancy_status: tenancyStatus || undefined,
    },
  });
  return data; // PaginatedResponse<TenancyListItem>
}

/** GET /api/tenancies/expiring - Active/Ending Soon tenancies whose
 * EndDate falls within the next `days` days. Not paginated - it's meant
 * to be a short attention list, not a full browse. */
export async function listExpiringTenancies(days = 30) {
  const { data } = await apiClient.get("/tenancies/expiring", { params: { days } });
  return data; // TenancyListItem[]
}

export async function getTenancy(tenancyId) {
  const { data } = await apiClient.get(`/tenancies/${tenancyId}`);
  return data; // TenancyResponse
}

/** Always creates a Draft - there is no way to create a tenancy in any
 * other status directly. */
export async function createTenancy(payload) {
  const { data } = await apiClient.post("/tenancies", payload);
  return data;
}

/** Only permitted while the tenancy is still Draft
 * (TENANCY_NOT_EDITABLE, 409 otherwise) - see tenancy_service.py. */
export async function updateTenancy(tenancyId, payload) {
  const { data } = await apiClient.put(`/tenancies/${tenancyId}`, payload);
  return data;
}

/** Draft -> Active (if StartDate has arrived) or Upcoming otherwise.
 * Rejected if the property/tenant is inactive or another live tenancy
 * already covers those dates on the same property
 * (TENANCY_DATE_CONFLICT, 409). */
export async function activateTenancy(tenancyId) {
  const { data } = await apiClient.post(`/tenancies/${tenancyId}/activate`);
  return data;
}

/** Active/Ending Soon -> Ended. endDate defaults to today on the server
 * if omitted; must be after the tenancy's StartDate
 * (TENANCY_INVALID_END_DATE, 409 otherwise). */
export async function endTenancy(tenancyId, endDate) {
  const { data } = await apiClient.post(`/tenancies/${tenancyId}/end`, { EndDate: endDate || null });
  return data;
}

/** Anything not already Ended/Cancelled -> Cancelled
 * (TENANCY_ALREADY_FINAL, 409 otherwise). */
export async function cancelTenancy(tenancyId) {
  const { data } = await apiClient.post(`/tenancies/${tenancyId}/cancel`);
  return data;
}
