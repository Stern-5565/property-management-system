/**
 * GET /api/maintenance-requests/workload - one row per employee who
 * currently has at least one open (not Completed/Cancelled) assignment,
 * "who's busy, and with what" (see maintenanceService.js). Administrator/
 * PropertyManager/ReadOnly only - a management view, distinct from a
 * MaintenanceEmployee's own assigned-work list (which is just the
 * regular, server-narrowed request list - see
 * MaintenanceRequestsListPage). Not paginated, same shape as the other
 * modules' attention-list pages (TenancyEndingSoonPage,
 * RentPaymentOverduePage).
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_VIEW_EMPLOYEES } from "../../constants/roles";
import { getWorkload } from "../../services/maintenanceService";
import { getErrorMessage } from "../../utilities/apiError";

export function MaintenanceWorkloadPage() {
  const { user } = useAuth();
  const canSeeEmployees = hasAnyRole(user, CAN_VIEW_EMPLOYEES);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadWorkload = useCallback(() => {
    setLoading(true);
    setError(null);
    getWorkload()
      .then(setItems)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadWorkload();
  }, [loadWorkload]);

  return (
    <div>
      <PageHeader
        title="Maintenance workload"
        description="Employees with at least one open (not completed or cancelled) maintenance request assigned to them."
      />

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadWorkload}
        emptyMessage="No employee currently has an open assignment."
        rows={items}
        getRowKey={(row) => row.EmployeeId}
        getRowClassName={(row) => (row.EmergencyOpenCount > 0 ? "data-table__row--emergency" : "")}
        columns={[
          {
            key: "EmployeeName",
            header: "Employee",
            render: (row) =>
              canSeeEmployees ? <Link to={`/employees/${row.EmployeeId}`}>{row.EmployeeName}</Link> : row.EmployeeName,
          },
          { key: "IsActive", header: "Active", render: (row) => (row.IsActive ? "Yes" : "No") },
          { key: "OpenRequestCount", header: "Open requests", render: (row) => row.OpenRequestCount },
          { key: "EmergencyOpenCount", header: "Emergency open", render: (row) => row.EmergencyOpenCount },
        ]}
      />

      <p>
        <Link to="/maintenance">← Back to maintenance requests</Link>
      </p>
    </div>
  );
}
