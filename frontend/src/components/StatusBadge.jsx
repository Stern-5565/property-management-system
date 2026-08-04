/**
 * Renders any of the backend's status/priority strings (PropertyStatus,
 * TenancyStatus, PaymentStatus, MaintenanceStatus, Priority, IsActive's
 * "Active"/"Inactive") as a small colored pill, inferring a tone
 * automatically from the value so most call sites don't need to think
 * about color at all: <StatusBadge status={payment.PaymentStatus} />.
 *
 * The map only needs to be "good enough" - anything not covered falls
 * back to a neutral grey rather than guessing wrong, and any call site
 * can override it explicitly with the `tone` prop when the default
 * doesn't fit (e.g. a module treating "Draft" as more serious than the
 * default heuristic assumes).
 */
const TONE_BY_STATUS = {
  active: "success",
  occupied: "success",
  paid: "success",
  completed: "success",
  assigned: "info",
  reported: "info",
  low: "info",
  pending: "warning",
  "partially paid": "warning",
  "ending soon": "warning",
  "in progress": "warning",
  "waiting for parts": "warning",
  "waiting for approval": "warning",
  upcoming: "warning",
  draft: "warning",
  medium: "warning",
  overdue: "danger",
  cancelled: "danger",
  vacant: "danger",
  inactive: "danger",
  unavailable: "danger",
  emergency: "danger",
  high: "danger",
  archived: "neutral",
  "under maintenance": "neutral",
  ended: "neutral",
};

export function StatusBadge({ status, tone }) {
  const resolvedTone = tone ?? TONE_BY_STATUS[status?.toLowerCase()] ?? "neutral";
  return <span className={`status-badge status-badge--${resolvedTone}`}>{status}</span>;
}
