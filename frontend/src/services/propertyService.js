/**
 * Wraps /api/properties - see backend/app/api/routes/properties.py.
 *
 * Note: unlike landlordService.js, there is NO reactivate call here -
 * the backend has no endpoint for it. PropertyStatusUpdate (PATCH
 * /status) only ever sets the operational PropertyStatus enum (Vacant/
 * Occupied/...), never IsActive; IsActive only ever goes false, via
 * DELETE. See PropertyDetailPage.jsx for how that's presented.
 */
import { apiClient } from "../api/client";

export async function listProperties({
  page = 1,
  pageSize = 20,
  search,
  landlordId,
  propertyType,
  propertyStatus,
  isActive,
} = {}) {
  const { data } = await apiClient.get("/properties", {
    params: {
      page,
      page_size: pageSize,
      search: search || undefined,
      landlord_id: landlordId || undefined,
      property_type: propertyType || undefined,
      property_status: propertyStatus || undefined,
      is_active: isActive,
    },
  });
  return data; // PaginatedResponse<PropertyListItem>
}

export async function getProperty(propertyId) {
  const { data } = await apiClient.get(`/properties/${propertyId}`);
  return data; // PropertyResponse
}

export async function createProperty(payload) {
  const { data } = await apiClient.post("/properties", payload);
  return data;
}

export async function updateProperty(propertyId, payload) {
  const { data } = await apiClient.put(`/properties/${propertyId}`, payload);
  return data;
}

export async function setPropertyStatus(propertyId, propertyStatus) {
  const { data } = await apiClient.patch(`/properties/${propertyId}/status`, { PropertyStatus: propertyStatus });
  return data;
}

/** Soft-delete - rejected if the property still has an active, upcoming,
 * or draft tenancy (PROPERTY_HAS_ACTIVE_TENANCIES, 409). */
export async function deactivateProperty(propertyId) {
  await apiClient.delete(`/properties/${propertyId}`);
}
