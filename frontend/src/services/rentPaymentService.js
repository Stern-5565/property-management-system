/**
 * Wraps /api/rent-payments - see backend/app/api/routes/rent_payments.py.
 * Like Tenancy, there is no generic status PATCH - a payment only ever
 * moves through recordPayment (accumulates AmountPaid, supports multiple
 * partial payments) or cancelPayment (terminal). PaymentStatus in every
 * response is always the server's live-calculated value, never something
 * this file computes client-side - see rent_payment_service.py's
 * calculate_payment_status docstring for why.
 */
import { apiClient } from "../api/client";

export async function listPayments({
  page = 1,
  pageSize = 20,
  tenancyId,
  propertyId,
  tenantId,
  paymentStatus,
  dueDateFrom,
  dueDateTo,
} = {}) {
  const { data } = await apiClient.get("/rent-payments", {
    params: {
      page,
      page_size: pageSize,
      tenancy_id: tenancyId || undefined,
      property_id: propertyId || undefined,
      tenant_id: tenantId || undefined,
      payment_status: paymentStatus || undefined,
      due_date_from: dueDateFrom || undefined,
      due_date_to: dueDateTo || undefined,
    },
  });
  return data; // PaginatedResponse<RentPaymentListItem>
}

/** GET /api/rent-payments/overdue - a guaranteed-live overdue list (due
 * date passed AND not fully paid), matching SQL Report 2 exactly. Not
 * paginated - a short attention list, same shape as Tenancy's
 * /expiring. */
export async function listOverduePayments() {
  const { data } = await apiClient.get("/rent-payments/overdue");
  return data; // RentPaymentListItem[]
}

/** GET /api/rent-payments/due - payments due this calendar month. Not
 * paginated. */
export async function listDueThisMonthPayments() {
  const { data } = await apiClient.get("/rent-payments/due");
  return data; // RentPaymentListItem[]
}

export async function getPayment(paymentId) {
  const { data } = await apiClient.get(`/rent-payments/${paymentId}`);
  return data; // RentPaymentResponse
}

/** Creates a Pending (or, if DueDate is already past, Overdue)
 * obligation. AmountPaid always starts at 0. */
export async function createPayment(payload) {
  const { data } = await apiClient.post("/rent-payments", payload);
  return data;
}

/** Only permitted while AmountPaid is still 0 and the payment isn't
 * Cancelled (PAYMENT_NOT_EDITABLE / PAYMENT_ALREADY_CANCELLED, 409
 * otherwise) - see rent_payment_service.py. */
export async function updatePayment(paymentId, payload) {
  const { data } = await apiClient.put(`/rent-payments/${paymentId}`, payload);
  return data;
}

/** AmountPaid here is the amount being paid NOW, not a new running
 * total - the server ADDS it to whatever's already recorded, so calling
 * this more than once accumulates correctly toward AmountDue (partial
 * payments). */
export async function recordPayment(paymentId, { amountPaid, paymentDate, paymentMethod, notes }) {
  const { data } = await apiClient.post(`/rent-payments/${paymentId}/record-payment`, {
    AmountPaid: amountPaid,
    PaymentDate: paymentDate || null,
    PaymentMethod: paymentMethod,
    Notes: notes || null,
  });
  return data;
}

/** Terminal - PAYMENT_ALREADY_CANCELLED, 409 if already cancelled. */
export async function cancelPayment(paymentId, notes) {
  const { data } = await apiClient.post(`/rent-payments/${paymentId}/cancel`, { Notes: notes || null });
  return data;
}
