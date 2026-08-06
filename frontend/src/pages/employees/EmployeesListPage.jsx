/**
 * GET /api/employees - same shape as TenantsListPage.jsx, but action
 * buttons gate on CAN_MANAGE_EMPLOYEES (Administrator-only, narrower than
 * every other module's CAN_MANAGE_X - see roles.js).
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
import { CAN_MANAGE_EMPLOYEES } from "../../constants/roles";
import { listEmployees } from "../../services/employeeService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function EmployeesListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_EMPLOYEES);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadEmployees = useCallback(() => {
    setLoading(true);
    setError(null);
    listEmployees({
      page,
      pageSize: PAGE_SIZE,
      search,
      isActive: isActiveFilter === "" ? undefined : isActiveFilter === "true",
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, search, isActiveFilter]);

  useEffect(() => {
    loadEmployees();
  }, [loadEmployees]);

  return (
    <div>
      <PageHeader
        title="Employees"
        description="Staff accounts who work for the property management company."
        actions={
          canManage && (
            <Link to="/employees/new" className="button">
              + New Employee
            </Link>
          )
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
          placeholder="Search name, email, phone, job title, department…"
        />
      </div>

      <FilterPanel
        title="Filters"
        onClear={() => {
          setIsActiveFilter("");
          setPage(1);
        }}
      >
        <SelectField
          label="Status"
          name="isActiveFilter"
          value={isActiveFilter}
          onChange={(event) => {
            setIsActiveFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={[
            { value: "true", label: "Active" },
            { value: "false", label: "Inactive" },
          ]}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadEmployees}
        emptyMessage="No employees match your search/filters."
        rows={items}
        getRowKey={(row) => row.EmployeeId}
        columns={[
          {
            key: "Name",
            header: "Name",
            render: (row) => <Link to={`/employees/${row.EmployeeId}`}>{`${row.FirstName} ${row.LastName}`}</Link>,
          },
          { key: "Email", header: "Email", render: (row) => row.Email ?? "—" },
          { key: "JobTitle", header: "Job title", render: (row) => row.JobTitle ?? "—" },
          { key: "Department", header: "Department", render: (row) => row.Department ?? "—" },
          {
            key: "IsActive",
            header: "Status",
            render: (row) => <StatusBadge status={row.IsActive ? "Active" : "Inactive"} />,
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}
