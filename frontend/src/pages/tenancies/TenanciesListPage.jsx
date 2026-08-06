/**
 * GET /api/tenancies - same list-page shape as every other module, but
 * with dropdown filters (Property/Tenant/Status) instead of a free-text
 * SearchInput, since the backend has no search param for this module
 * (see tenancyService.js). Property/Tenant filter options are loaded the
 * same way PropertyFormPage loads its landlord dropdown - a single
 * pageSize:100 call, not a new shared "options loader" abstraction for
 * just these two call sites.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_TENANCIES } from "../../constants/roles";
import { TENANCY_STATUS_OPTIONS } from "../../constants/tenancyOptions";
import { listTenancies } from "../../services/tenancyService";
import { listProperties } from "../../services/propertyService";
import { listTenants } from "../../services/tenantService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function TenanciesListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_TENANCIES);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [propertyFilter, setPropertyFilter] = useState("");
  const [tenantFilter, setTenantFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [tenantOptions, setTenantOptions] = useState([]);
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
    listTenants({ pageSize: 100 }).then((data) =>
      setTenantOptions(data.items.map((t) => ({ value: String(t.TenantId), label: `${t.FirstName} ${t.LastName}` }))),
    );
  }, []);

  const loadTenancies = useCallback(() => {
    setLoading(true);
    setError(null);
    listTenancies({
      page,
      pageSize: PAGE_SIZE,
      propertyId: propertyFilter || undefined,
      tenantId: tenantFilter || undefined,
      tenancyStatus: statusFilter || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, propertyFilter, tenantFilter, statusFilter]);

  useEffect(() => {
    loadTenancies();
  }, [loadTenancies]);

  return (
    <div>
      <PageHeader
        title="Tenancies"
        description="Every tenancy agreement, from first draft through to ended or cancelled."
        actions={
          <>
            <Link to="/tenancies/ending-soon" className="button button--secondary">
              Ending soon
            </Link>
            {canManage && (
              <Link to="/tenancies/new" className="button">
                + New Tenancy
              </Link>
            )}
          </>
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      <FilterPanel
        title="Filters"
        onClear={() => {
          setPropertyFilter("");
          setTenantFilter("");
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
        <SelectField
          label="Tenant"
          name="tenantFilter"
          value={tenantFilter}
          onChange={(event) => {
            setTenantFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any tenant"
          options={tenantOptions}
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
          options={TENANCY_STATUS_OPTIONS}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadTenancies}
        emptyMessage="No tenancies match your filters."
        rows={items}
        getRowKey={(row) => row.TenancyId}
        columns={[
          {
            key: "Property",
            header: "Property",
            render: (row) => <Link to={`/tenancies/${row.TenancyId}`}>{row.PropertyReference}</Link>,
          },
          { key: "Tenant", header: "Tenant", render: (row) => row.TenantName },
          { key: "StartDate", header: "Start date", render: (row) => row.StartDate },
          { key: "EndDate", header: "End date", render: (row) => row.EndDate ?? "—" },
          { key: "MonthlyRent", header: "Monthly rent", render: (row) => `£${row.MonthlyRent}` },
          {
            key: "TenancyStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.TenancyStatus} />,
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}
