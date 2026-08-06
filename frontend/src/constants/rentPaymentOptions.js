/**
 * Mirrors backend/app/schemas/rent_payment.py's PaymentMethodValue/
 * PaymentStatusValue Literal definitions. PAYMENT_METHOD_OPTIONS is a
 * real form field (record-payment); PAYMENT_STATUS_OPTIONS is
 * filter-only, same reasoning as TENANCY_STATUS_OPTIONS - status is
 * never a free dropdown on a write form, it's always computed or moved
 * through a dedicated action.
 */
export const PAYMENT_METHOD_OPTIONS = [
  { value: "Bank Transfer", label: "Bank Transfer" },
  { value: "Card", label: "Card" },
  { value: "Cash", label: "Cash" },
  { value: "Direct Debit", label: "Direct Debit" },
  { value: "Standing Order", label: "Standing Order" },
  { value: "Other", label: "Other" },
];

export const PAYMENT_STATUS_OPTIONS = [
  { value: "Pending", label: "Pending" },
  { value: "Partially Paid", label: "Partially Paid" },
  { value: "Paid", label: "Paid" },
  { value: "Overdue", label: "Overdue" },
  { value: "Cancelled", label: "Cancelled" },
];
