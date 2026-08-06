/**
 * GET /api/properties - same shape as LandlordsListPage.jsx (search,
 * filters, pagination all drive one fetch effect). The Landlord filter's
 * options come from a one-off GET /api/landlords?is_active=true, fetched
 * once on mount - see landlordService.listLandlords.
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
import { CAN_MANAGE_PROPERTIES } from "../../constants/roles";
import { PROPERTY_TYPE_OPTIONS, PROPERTY_STATUS_OPTIONS } from "../../constants/propertyOptions";
import { listProperties } from "../../services/propertyService";
import { listLandlords } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";

const PAGE_SIZE = 20;

export function PropertiesListPage() {
  const { user } = useAuth();
  const canManage = hasAnyRole(user, CAN_MANAGE_PROPERTIES);
  const location = useLocation();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState("");
  const [landlordId, setLandlordId] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [propertyStatus, setPropertyStatus] = useState("");
  const [isActiveFilter, setIsActiveFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast ?? null);
  const [landlordOptions, setLandlordOptions] = useState([]);

  useEffect(() => {
    if (location.state?.toast) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    listLandlords({ pageSize: 100, isActive: true })
      .then((data) => setLandlordOptions(data.items.map((l) => ({ value: String(l.LandlordId), label: l.DisplayName }))))
      .catch(() => setLandlordOptions([])); // filter dropdown just stays empty - not worth its own error UI
  }, []);

  const loadProperties = useCallback(() => {
    setLoading(true);
    setError(null);
    listProperties({
      page,
      pageSize: PAGE_SIZE,
      search,
      landlordId: landlordId || undefined,
      propertyType: propertyType || undefined,
      propertyStatus: propertyStatus || undefined,
      isActive: isActiveFilter === "" ? undefined : isActiveFilter === "true",
    })
      .then((data) => {
        setItems(data.items);
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, search, landlordId, propertyType, propertyStatus, isActiveFilter]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  function handleClearFilters() {
    setLandlordId("");
    setPropertyType("");
    setPropertyStatus("");
    setIsActiveFilter("");
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Properties"
        description="Every property in the portfolio, across all landlords."
        actions={
          canManage && (
            <Link to="/properties/new" className="button">
              + New Property
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
          placeholder="Search reference, address, city, postcode…"
        />
      </div>

      <FilterPanel title="Filters" onClear={handleClearFilters}>
        <SelectField
          label="Landlord"
          name="landlordId"
          value={landlordId}
          onChange={(event) => {
            setLandlordId(event.target.value);
            setPage(1);
          }}
          placeholder="Any landlord"
          options={landlordOptions}
        />
        <SelectField
          label="Property type"
          name="propertyType"
          value={propertyType}
          onChange={(event) => {
            setPropertyType(event.target.value);
            setPage(1);
          }}
          placeholder="Any type"
          options={PROPERTY_TYPE_OPTIONS}
        />
        <SelectField
          label="Status"
          name="propertyStatus"
          value={propertyStatus}
          onChange={(event) => {
            setPropertyStatus(event.target.value);
            setPage(1);
          }}
          placeholder="Any status"
          options={PROPERTY_STATUS_OPTIONS}
        />
        <SelectField
          label="Active"
          name="isActiveFilter"
          value={isActiveFilter}
          onChange={(event) => {
            setIsActiveFilter(event.target.value);
            setPage(1);
          }}
          placeholder="Any"
          options={[
            { value: "true", label: "Active" },
            { value: "false", label: "Inactive" },
          ]}
        />
      </FilterPanel>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadProperties}
        emptyMessage="No properties match your search/filters."
        rows={items}
        getRowKey={(row) => row.PropertyId}
        columns={[
          {
            key: "PropertyReference",
            header: "Reference",
            render: (row) => <Link to={`/properties/${row.PropertyId}`}>{row.PropertyReference}</Link>,
          },
          { key: "AddressLine1", header: "Address" },
          { key: "City", header: "City" },
          { key: "PropertyType", header: "Type" },
          { key: "Bedrooms", header: "Beds" },
          { key: "MonthlyRent", header: "Monthly rent", render: (row) => `£${row.MonthlyRent}` },
          { key: "PropertyStatus", header: "Status", render: (row) => <StatusBadge status={row.PropertyStatus} /> },
        ]}
      />

      {!loading && !error && (
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={totalItems} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}
