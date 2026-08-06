/**
 * GET /api/tenants - same shape as LandlordsListPage.jsx.
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
import { CAN_MANAGE_TENANTS } from "../../constants/roles";
import { listTenants } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function TenantsListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_TENANTS);
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

  const loadTenants = useCallback(() => {
    setLoading(true);
    setError(null);
    listTenants({
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
    loadTenants();
  }, [loadTenants]);

  return (
    <div>
      <PageHeader
        title="Tenants"
        description="Everyone who rents (or has rented) a property through PropertyManager."
        actions={
          canManage && (
            <Link to="/tenants/new" className="button">
              + New Tenant
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
          placeholder="Search name, email, phone…"
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
        onRetry={loadTenants}
        emptyMessage="No tenants match your search/filters."
        rows={items}
        getRowKey={(row) => row.TenantId}
        columns={[
          {
            key: "Name",
            header: "Name",
            render: (row) => <Link to={`/tenants/${row.TenantId}`}>{`${row.FirstName} ${row.LastName}`}</Link>,
          },
          { key: "Email", header: "Email", render: (row) => row.Email ?? "—" },
          { key: "Phone", header: "Phone", render: (row) => row.Phone ?? "—" },
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
