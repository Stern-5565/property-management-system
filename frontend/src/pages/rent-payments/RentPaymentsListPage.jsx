/**
 * GET /api/rent-payments - filters by Property/Tenant/Status/due-date
 * range, same dropdown-filter shape as TenanciesListPage (no free-text
 * search here either). Also doubles as the "payment history by tenancy"
 * view (Prompt 22): TenancyDetailPage links here with a `?tenancyId=`
 * query param, read once on mount via useSearchParams - not a visible
 * filter control, just a precise `tenancy_id` param passed straight to
 * the API (more exact than approximating via property+tenant), shown as
 * a dismissible banner instead of a dropdown.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { Pagination } from "../../components/Pagination";
import { FilterPanel } from "../../components/FilterPanel";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { StatusBadge } from "../../components/StatusBadge";
import { Toast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { hasAnyRole } from "../../utilities/permissions";
import { CAN_MANAGE_RENT_PAYMENTS } from "../../constants/roles";
import { PAYMENT_STATUS_OPTIONS } from "../../constants/rentPaymentOptions";
import { listPayments } from "../../services/rentPaymentService";
import { listProperties } from "../../services/propertyService";
import { listTenants } from "../../services/tenantService";
import { getTenancy } from "../../services/tenancyService";
import { getErrorMessage } from "../../utilities/apiError";
import { downloadCsv } from "../../utilities/csvExport";

const PAGE_SIZE = 20;

const CSV_COLUMNS = [
  { key: "PaymentReference", header: "Payment Reference", value: (row) => row.PaymentReference },
  { key: "PropertyReference", header: "Property", value: (row) => row.PropertyReference },
  { key: "TenantName", header: "Tenant", value: (row) => row.TenantName },
  { key: "DueDate", header: "Due Date", value: (row) => row.DueDate },
  { key: "AmountDue", header: "Amount Due", value: (row) => row.AmountDue },
  { key: "AmountPaid", header: "Amount Paid", value: (row) => row.AmountPaid },
  { key: "AmountOutstanding", header: "Amount Outstanding", value: (row) => row.AmountOutstanding },
  { key: "PaymentStatus", header: "Status", value: (row) => row.PaymentStatus },
];

export function RentPaymentsListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_RENT_PAYMENTS);
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [propertyFilter, setPropertyFilter] = useState("");
  const [tenantFilter, setTenantFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dueDateFrom, setDueDateFrom] = useState("");
  const [dueDateTo, setDueDateTo] = useState("");
  const [tenancyFilter, setTenancyFilter] = useState(searchParams.get("tenancyId") ?? "");
  const [tenancyFilterLabel, setTenancyFilterLabel] = useState(null);
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [tenantOptions, setTenantOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname + location.search, { replace: true, state: {} });
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

  useEffect(() => {
    if (!tenancyFilter) {
      setTenancyFilterLabel(null);
      return;
    }
    getTenancy(tenancyFilter)
      .then((tenancy) => setTenancyFilterLabel(`${tenancy.PropertyReference} — ${tenancy.TenantName}`))
      .catch(() => setTenancyFilterLabel(`#${tenancyFilter}`));
  }, [tenancyFilter]);

  const loadPayments = useCallback(() => {
    setLoading(true);
    setError(null);
    listPayments({
      page,
      pageSize: PAGE_SIZE,
      tenancyId: tenancyFilter || undefined,
      propertyId: propertyFilter || undefined,
      tenantId: tenantFilter || undefined,
      paymentStatus: statusFilter || undefined,
      dueDateFrom: dueDateFrom || undefined,
      dueDateTo: dueDateTo || undefined,
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, tenancyFilter, propertyFilter, tenantFilter, statusFilter, dueDateFrom, dueDateTo]);

  useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  function handleExportCsv() {
    downloadCsv("rent-payments.csv", CSV_COLUMNS, items);
  }

  return (
    <div>
      <PageHeader
        title="Rent Payments"
        description="Every rent obligation, from first due date through to paid, partially paid, or cancelled."
        actions={
          <>
            <Link to="/rent-payments/overdue" className="button button--secondary">
              Overdue
            </Link>
            <Link to="/rent-payments/due-this-month" className="button button--secondary">
              Due this month
            </Link>
            <button type="button" className="button button--secondary" onClick={handleExportCsv} disabled={items.length === 0}>
              Export CSV
            </button>
            {canManage && (
              <Link to="/rent-payments/new" className="button">
                + New Payment
              </Link>
            )}
          </>
        }
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      {tenancyFilter && (
        <p className="filter-banner">
          Showing payment history for tenancy {tenancyFilterLabel ?? `#${tenancyFilter}`}.{" "}
          <button
            type="button"
            className="button button--secondary"
            onClick={() => {
              setTenancyFilter("");
              setPage(1);
            }}
          >
            Clear
          </button>
        </p>
      )}

      <FilterPanel
        title="Filters"
        onClear={() => {
          setPropertyFilter("");
          setTenantFilter("");
          setStatusFilter("");
          setDueDateFrom("");
          setDueDateTo("");
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
          options={PAYMENT_STATUS_OPTIONS}
        />
        <DateField
          label="Due from"
          name="dueDateFrom"
          value={dueDateFrom}
          onChange={(event) => {
            setDueDateFrom(event.target.value);
            setPage(1);
          }}
        />
        <DateField
          label="Due to"
          name="dueDateTo"
          value={dueDateTo}
          onChange={(event) => {
            setDueDateTo(event.target.value);
            setPage(1);
          }}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadPayments}
        emptyMessage="No rent payments match your filters."
        rows={items}
        getRowKey={(row) => row.RentPaymentId}
        columns={[
          {
            key: "PaymentReference",
            header: "Reference",
            render: (row) => <Link to={`/rent-payments/${row.RentPaymentId}`}>{row.PaymentReference}</Link>,
          },
          { key: "Property", header: "Property", render: (row) => row.PropertyReference },
          { key: "Tenant", header: "Tenant", render: (row) => row.TenantName },
          { key: "DueDate", header: "Due date", render: (row) => row.DueDate },
          { key: "AmountDue", header: "Amount due", render: (row) => `£${row.AmountDue}` },
          { key: "AmountPaid", header: "Amount paid", render: (row) => `£${row.AmountPaid}` },
          { key: "AmountOutstanding", header: "Outstanding", render: (row) => `£${row.AmountOutstanding}` },
          {
            key: "PaymentStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.PaymentStatus} />,
          },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}
