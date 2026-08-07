/**
 * The 10 MVP reports (documentation/project-scope.md, "Ten MVP reports")
 * and, for each, which filter controls ReportViewPage should render -
 * title/description/columns/totals all come from the backend response
 * itself (see reportService.js), so this file only needs to describe the
 * one thing the backend response can't: what filter INPUTS to show
 * before that response exists yet.
 *
 * `filters` entry shape: { name, label, type }. `name` must match the
 * query param the backend route actually accepts (see
 * app/api/routes/reports.py) - this is the "reusable reporting pattern"
 * Prompt 25 asks for: ReportViewPage renders any report from this list
 * plus whatever the backend returns, never a hardcoded per-report page.
 */
export const REPORT_DEFINITIONS = [
  {
    key: "rent-due-this-month",
    label: "Rent Due This Month",
    filters: [{ name: "property_id", label: "Property", type: "property-select" }],
  },
  {
    key: "overdue-rent",
    label: "Overdue Rent",
    filters: [
      { name: "property_id", label: "Property", type: "property-select" },
      { name: "landlord_id", label: "Landlord", type: "landlord-select" },
    ],
  },
  {
    key: "monthly-rent-collected",
    label: "Monthly Rent Collected",
    filters: [
      { name: "period_start", label: "From", type: "date" },
      { name: "period_end", label: "To", type: "date" },
    ],
  },
  {
    key: "rent-by-landlord",
    label: "Rent Collected by Landlord",
    filters: [
      { name: "period_start", label: "From", type: "date" },
      { name: "period_end", label: "To", type: "date" },
      { name: "landlord_id", label: "Landlord", type: "landlord-select" },
    ],
  },
  {
    key: "occupancy",
    label: "Occupancy Report",
    filters: [],
  },
  {
    key: "vacant-properties",
    label: "Vacant Properties",
    filters: [{ name: "landlord_id", label: "Landlord", type: "landlord-select" }],
  },
  {
    key: "tenancies-ending-soon",
    label: "Tenancies Ending Soon",
    filters: [
      { name: "days_ahead", label: "Window", type: "days-ahead" },
      { name: "property_id", label: "Property", type: "property-select" },
    ],
  },
  {
    key: "maintenance-by-status",
    label: "Open Maintenance by Status and Priority",
    filters: [],
  },
  {
    key: "maintenance-costs-by-property",
    label: "Maintenance Costs by Property",
    filters: [{ name: "landlord_id", label: "Landlord", type: "landlord-select" }],
  },
  {
    key: "property-income",
    label: "Property Income and Performance",
    filters: [
      { name: "period_start", label: "From", type: "date" },
      { name: "period_end", label: "To", type: "date" },
      { name: "landlord_id", label: "Landlord", type: "landlord-select" },
    ],
  },
];
