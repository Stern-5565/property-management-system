/**
 * Wraps /api/landlords - see backend/app/api/routes/landlords.py for the
 * routes this mirrors, and services/authService.js for the pattern every
 * module's service file follows.
 */
import { apiClient } from "../api/client";

export async function listLandlords({ page = 1, pageSize = 20, search, isActive } = {}) {
  const { data } = await apiClient.get("/landlords", {
    params: { page, page_size: pageSize, search: search || undefined, is_active: isActive },
  });
  return data; // PaginatedResponse<LandlordListItem>
}

export async function getLandlord(landlordId) {
  const { data } = await apiClient.get(`/landlords/${landlordId}`);
  return data; // LandlordResponse
}

export async function createLandlord(payload) {
  const { data } = await apiClient.post("/landlords", payload);
  return data;
}

export async function updateLandlord(landlordId, payload) {
  const { data } = await apiClient.put(`/landlords/${landlordId}`, payload);
  return data;
}

export async function setLandlordStatus(landlordId, isActive) {
  const { data } = await apiClient.patch(`/landlords/${landlordId}/status`, { IsActive: isActive });
  return data;
}

/** Soft-delete (deactivate) - the backend rejects this if the landlord
 * still has active properties (LANDLORD_HAS_ACTIVE_PROPERTIES, 409). Use
 * setLandlordStatus(id, true) to reactivate; there's no equivalent
 * "un-delete" endpoint since this was never a hard delete to begin with. */
export async function deactivateLandlord(landlordId) {
  await apiClient.delete(`/landlords/${landlordId}`);
}
