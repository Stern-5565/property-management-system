/**
 * Wraps /api/maintenance-requests - see
 * backend/app/api/routes/maintenance_requests.py. Unlike Tenancy/
 * RentPayment, this module DOES have a free-text `search` param
 * (matches RequestReference/Title/Description - see
 * MaintenanceRepository.list), so the list page uses SearchInput
 * alongside its dropdown filters, not instead of it.
 *
 * Several independent action endpoints instead of one big edit -
 * assign/change-priority/cancel stay Administrator/PropertyManager only
 * (CAN_MANAGE_MAINTENANCE); change-status/notes/costs/complete also
 * accept the assigned MaintenanceEmployee (CAN_UPDATE_MAINTENANCE_WORK) -
 * see maintenance_service.py's own permission-shape docstring.
 */
import { apiClient } from "../api/client";

export async function listRequests({
  page = 1,
  pageSize = 20,
  search,
  propertyId,
  tenantId,
  assignedEmployeeId,
  category,
  priority,
  maintenanceStatus,
} = {}) {
  const { data } = await apiClient.get("/maintenance-requests", {
    params: {
      page,
      page_size: pageSize,
      search: search || undefined,
      property_id: propertyId || undefined,
      tenant_id: tenantId || undefined,
      assigned_employee_id: assignedEmployeeId || undefined,
      category: category || undefined,
      priority: priority || undefined,
      maintenance_status: maintenanceStatus || undefined,
    },
  });
  return data; // PaginatedResponse<MaintenanceRequestListItem>
}

/** GET /api/maintenance-requests/workload - one row per employee with at
 * least one open (not Completed/Cancelled) assignment, for "who's busy,
 * and with what" - Administrator/PropertyManager/ReadOnly only (a
 * management view, not the MaintenanceEmployee's own assigned-work list -
 * that's just the regular list, auto-narrowed server-side to their own
 * EmployeeId - see MaintenanceRequestsListPage). */
export async function getWorkload() {
  const { data } = await apiClient.get("/maintenance-requests/workload");
  return data; // EmployeeWorkloadItem[]
}

export async function getRequest(requestId) {
  const { data } = await apiClient.get(`/maintenance-requests/${requestId}`);
  return data; // MaintenanceRequestResponse
}

/** Always creates status "Reported", unassigned. */
export async function createRequest(payload) {
  const { data } = await apiClient.post("/maintenance-requests", payload);
  return data;
}

/** Rejected once the request is Completed/Cancelled
 * (MAINTENANCE_REQUEST_CLOSED, 409). */
export async function updateRequest(requestId, payload) {
  const { data } = await apiClient.put(`/maintenance-requests/${requestId}`, payload);
  return data;
}

/** Also flips MaintenanceStatus Reported -> Assigned automatically if it
 * was still Reported. */
export async function assignEmployee(requestId, employeeId) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/assign`, { EmployeeId: employeeId });
  return data;
}

export async function changePriority(requestId, priority) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/change-priority`, { Priority: priority });
  return data;
}

/** Cancelled is terminal - MAINTENANCE_ALREADY_COMPLETED/
 * MAINTENANCE_ALREADY_CANCELLED, 409 if already Completed/Cancelled. */
export async function cancelRequest(requestId, notes) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/cancel`, { Notes: notes || null });
  return data;
}

/** Only accepts the non-terminal subset (see CHANGEABLE_STATUS_OPTIONS) -
 * Completed/Cancelled go through completeRequest/cancelRequest instead,
 * which enforce their own required fields. */
export async function changeStatus(requestId, maintenanceStatus) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/change-status`, {
    MaintenanceStatus: maintenanceStatus,
  });
  return data;
}

export async function addNote(requestId, noteText) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/notes`, { NoteText: noteText });
  return data;
}

/** At least one of estimatedCost/actualCost must be given. Still works
 * after Completed (correcting an actual cost afterward is legitimate) -
 * only blocked once Cancelled. */
export async function enterCosts(requestId, { estimatedCost, actualCost }) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/costs`, {
    EstimatedCost: estimatedCost || null,
    ActualCost: actualCost || null,
  });
  return data;
}

/** CompletedDate defaults to today server-side if omitted. */
export async function completeRequest(requestId, { completedDate, resolutionNotes, actualCost }) {
  const { data } = await apiClient.post(`/maintenance-requests/${requestId}/complete`, {
    CompletedDate: completedDate || null,
    ResolutionNotes: resolutionNotes,
    ActualCost: actualCost || null,
  });
  return data;
}
