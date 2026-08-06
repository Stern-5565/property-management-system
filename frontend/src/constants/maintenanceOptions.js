/**
 * Mirrors backend/app/schemas/maintenance.py's CategoryValue/
 * PriorityValue/MaintenanceStatusValue/ChangeableStatusValue Literal
 * definitions. STATUS_OPTIONS is filter-only (every status, including
 * Completed/Cancelled); CHANGEABLE_STATUS_OPTIONS is what the
 * change-status action actually accepts - Completed/Cancelled are
 * deliberately excluded there, since those only happen through the
 * dedicated complete/cancel actions (see MaintenanceRequestDetailPage).
 */
export const CATEGORY_OPTIONS = [
  { value: "Plumbing", label: "Plumbing" },
  { value: "Electrical", label: "Electrical" },
  { value: "Heating", label: "Heating" },
  { value: "Appliance", label: "Appliance" },
  { value: "Structural", label: "Structural" },
  { value: "Security", label: "Security" },
  { value: "Cleaning", label: "Cleaning" },
  { value: "General", label: "General" },
  { value: "Other", label: "Other" },
];

export const PRIORITY_OPTIONS = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
  { value: "Emergency", label: "Emergency" },
];

export const STATUS_OPTIONS = [
  { value: "Reported", label: "Reported" },
  { value: "Assigned", label: "Assigned" },
  { value: "In Progress", label: "In Progress" },
  { value: "Waiting for Parts", label: "Waiting for Parts" },
  { value: "Waiting for Approval", label: "Waiting for Approval" },
  { value: "Completed", label: "Completed" },
  { value: "Cancelled", label: "Cancelled" },
];

export const CHANGEABLE_STATUS_OPTIONS = [
  { value: "Reported", label: "Reported" },
  { value: "Assigned", label: "Assigned" },
  { value: "In Progress", label: "In Progress" },
  { value: "Waiting for Parts", label: "Waiting for Parts" },
  { value: "Waiting for Approval", label: "Waiting for Approval" },
];
