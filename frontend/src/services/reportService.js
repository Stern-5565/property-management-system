/**
 * Wraps /api/reports/* - see backend/app/api/routes/reports.py. Every
 * report shares one response shape (`{ReportKey, Title, Description,
 * Columns, Rows, Totals, GeneratedAt}` - see app/schemas/reports.py), so
 * this file needs only one function, not ten - `reportKey` plus whatever
 * filter params the caller has for that particular report (each report's
 * own filter shape is described in constants/reportDefinitions.js, not
 * here).
 */
import { apiClient } from "../api/client";

const REPORT_ENDPOINTS = {
  "rent-due-this-month": "/reports/rent-due-this-month",
  "overdue-rent": "/reports/overdue-rent",
  "monthly-rent-collected": "/reports/monthly-rent-collected",
  "rent-by-landlord": "/reports/rent-by-landlord",
  occupancy: "/reports/occupancy",
  "vacant-properties": "/reports/vacant-properties",
  "tenancies-ending-soon": "/reports/tenancies-ending-soon",
  "maintenance-by-status": "/reports/maintenance-by-status",
  "maintenance-costs-by-property": "/reports/maintenance-costs-by-property",
  "property-income": "/reports/property-income",
};

/** `filters` is a plain object of whatever query params this report
 * accepts (property_id, landlord_id, period_start, period_end,
 * days_ahead, ...) - undefined/empty values are dropped rather than sent
 * as empty-string query params, since the backend treats "not given" and
 * "given but blank" differently for a `date | None` filter. */
export async function getReport(reportKey, filters = {}) {
  const endpoint = REPORT_ENDPOINTS[reportKey];
  if (!endpoint) {
    throw new Error(`Unknown report key: ${reportKey}`);
  }
  const params = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params[key] = value;
    }
  }
  const { data } = await apiClient.get(endpoint, { params });
  return data; // ReportResponse
}
