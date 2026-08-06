/**
 * Mirrors backend/app/schemas/tenancy.py's TenancyStatusValue Literal.
 * Used by TenanciesListPage (filter) - never for a form field, since a
 * tenancy's status only ever changes through the dedicated activate/end/
 * cancel actions, never a free dropdown (see tenancyService.js).
 */
export const TENANCY_STATUS_OPTIONS = [
  { value: "Draft", label: "Draft" },
  { value: "Upcoming", label: "Upcoming" },
  { value: "Active", label: "Active" },
  { value: "Ending Soon", label: "Ending Soon" },
  { value: "Ended", label: "Ended" },
  { value: "Cancelled", label: "Cancelled" },
];
