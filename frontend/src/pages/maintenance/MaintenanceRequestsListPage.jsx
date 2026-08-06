/**
 * GET /api/maintenance-requests - the one list page in the app with BOTH
 * a SearchInput (matches Reference/Title/Description server-side) AND
 * dropdown filters (Property/Employee/Category/Priority/Status), since
 * this backend endpoint supports both - see maintenanceService.js.
 *
 * Emergency rows get a highlighted background (`getRowClassName`, a
 * small addition to DataTable - see its own comment) on top of the
 * Priority column's own "Emergency" badge, so an emergency request is
 * unmissable in a long list, not just technically identifiable - matches
 * the scope doc's "emergency requests must be easy to identify".
 *
 * For a MaintenanceEmployee, the backend auto-narrows results to their
 * own assigned requests (MaintenanceService._is_restricted_to_own_work) -
 * this page can't see or control that, so it just explains it via the
 * page description when it detects that role without full manage access,
 * satisfying the scope doc's "employee-specific assigned-work view".
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { SearchInput } from "../../components/SearchInput";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_MAINTENANCE, CAN_VIEW_MAINTENANCE, MAINTENANCE_EMPLOYEE } from "../../constants/roles";
import { CATEGORY_OPTIONS, PRIORITY_OPTIONS, STATUS_OPTIONS } from "../../constants/maintenanceOptions";
import { listRequests } from "../../services/maintenanceService";
import { listProperties } from "../../services/propertyService";
import { listEmployees } from "../../services/employeeService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function MaintenanceRequestsListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_MAINTENANCE);
  const isOwnWorkView = hasAnyRole(user, [MAINTENANCE_EMPLOYEE]) && !canManage;
  const canViewWorkload = hasAnyRole(user, CAN_VIEW_MAINTENANCE);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState("");
  const [propertyFilter, setPropertyFilter] = useState("");
  const [employeeFilter, setEmployeeFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [employeeOptions, setEmployeeOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    listProperties({ pageSize: 100 }).then((data) =>
      setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyReference }))),
    );
    if (!isOwnWorkView) {
      listEmployees({ pageSize: 100, isActive: true }).then((data) =>
        setEmployeeOptions(data.items.map((e) => ({ value: String(e.EmployeeId), label: `${e.FirstName} ${e.LastName}` }))),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRequests = useCallback(() => {
    setLoading(true);
    setError(null);
    listRequests({
      page,
      pageSize: PAGE_SIZE,
      search,
      propertyId: propertyFilter || undefined,
      assignedEmployeeId: employeeFilter || undefined,
      category: categoryFilter || undefined,
      priority: priorityFilter || undefined,
      maintenanceStatus: statusFilter || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, search, propertyFilter, employeeFilter, categoryFilter, priorityFilter, statusFilter]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  return (
    <div>
      <PageHeader
        title="Maintenance Requests"
        description={
          isOwnWorkView
            ? "Showing only requests assigned to you."
            : "Every maintenance request, from first report through to completed or cancelled."
        }
        actions={
          <>
            {canViewWorkload && (
              <Link to="/maintenance/workload" className="button button--secondary">
                Workload
              </Link>
            )}
            {canManage && (
              <Link to="/maintenance/new" className="button">
                + New Request
              </Link>
            )}
          </>
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <div className="list-page__toolbar">
        <SearchInput
          value={search}
          onSearch={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Search reference, title, description…"
        />
      </div>

      <FilterPanel
        title="Filters"
        onClear={() => {
          setPropertyFilter("");
          setEmployeeFilter("");
          setCategoryFilter("");
          setPriorityFilter("");
          setStatusFilter("");
          setPage(1);
        }}
      >
        <SelectField
          label="Property"
          name="propertyFilter"
          value={propertyFilter}
          onChange={(event) => {
            setPropertyFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any property"
          options={propertyOptions}
        />
        {!isOwnWorkView && (
          <SelectField
            label="Employee"
            name="employeeFilter"
            value={employeeFilter}
            onChange={(event) => {
              setEmployeeFilter(event.target.value);
              setPage(1);
            }}
            placeholder="Any employee"
            options={employeeOptions}
          />
        )}
        <SelectField
          label="Category"
          name="categoryFilter"
          value={categoryFilter}
          onChange={(event) => {
            setCategoryFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any category"
          options={CATEGORY_OPTIONS}
        />
        <SelectField
          label="Priority"
          name="priorityFilter"
          value={priorityFilter}
          onChange={(event) => {
            setPriorityFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any priority"
          options={PRIORITY_OPTIONS}
        />
        <SelectField
          label="Status"
          name="statusFilter"
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={STATUS_OPTIONS}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadRequests}
        emptyMessage="No maintenance requests match your search/filters."
        rows={items}
        getRowKey={(row) => row.MaintenanceRequestId}
        getRowClassName={(row) => (row.IsEmergency ? "data-table__row--emergency" : "")}
        columns={[
          {
            key: "RequestReference",
            header: "Reference",
            render: (row) => <Link to={`/maintenance/${row.MaintenanceRequestId}`}>{row.RequestReference}</Link>,
          },
          { key: "Title", header: "Title", render: (row) => row.Title },
          { key: "Property", header: "Property", render: (row) => row.PropertyReference },
          { key: "Category", header: "Category", render: (row) => row.Category },
          { key: "Priority", header: "Priority", render: (row) => <StatusBadge status={row.Priority} /> },
          { key: "Employee", header: "Assigned to", render: (row) => row.AssignedEmployeeName ?? "Unassigned" },
          {
            key: "MaintenanceStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.MaintenanceStatus} />,
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}
