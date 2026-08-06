/**
 * GET /api/landlords, with search/status filter/pagination all driving
 * one fetch effect - see loadLandlords below. Communicates with FastAPI
 * only through services/landlordService.js; this component never calls
 * apiClient directly.
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
import { CAN_MANAGE_LANDLORDS } from "../../constants/roles";
import { listLandlords } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function LandlordsListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_LANDLORDS);
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

  // Consume the one-time "created/updated/deactivated" toast passed via
  // navigate(..., { state: { toast } }) from the detail/form pages, then
  // clear it from history state so a refresh doesn't re-show it.
  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadLandlords = useCallback(() => {
    setLoading(true);
    setError(null);
    listLandlords({
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
    loadLandlords();
  }, [loadLandlords]);

  return (
    <div>
      <PageHeader
        title="Landlords"
        description="Everyone who owns a property managed through PropertyManager."
        actions={
          canManage && (
            <Link to="/landlords/new" className="button">
              + New Landlord
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
          placeholder="Search name, company, email, phone…"
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
        onRetry={loadLandlords}
        emptyMessage="No landlords match your search/filters."
        rows={items}
        getRowKey={(row) => row.LandlordId}
        columns={[
          {
            key: "DisplayName",
            header: "Name",
            render: (row) => <Link to={`/landlords/${row.LandlordId}`}>{row.DisplayName}</Link>,
          },
          { key: "City", header: "City" },
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
