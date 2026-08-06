/**
 * GET /api/tenancies/expiring?days=N - the scope doc's "Expiring
 * tenancies" attention list (Prompt 21). Not paginated (see
 * tenancyService.js) - it's a short list meant to be scanned, not
 * browsed, so DataTable is used here without a Pagination component
 * alongside it, unlike every list page in this app.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { SelectField } from "../../components/SelectField";
import { StatusBadge } from "../../components/StatusBadge";
import { listExpiringTenancies } from "../../services/tenancyService";
import { getErrorMessage } from "../../utilities/apiError";

const DAYS_OPTIONS = [
  { value: "30", label: "Next 30 days" },
  { value: "60", label: "Next 60 days" },
  { value: "90", label: "Next 90 days" },
];

export function TenancyEndingSoonPage() {
  const [days, setDays] = useState("30");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadExpiring = useCallback(() => {
    setLoading(true);
    setError(null);
    listExpiringTenancies(Number(days))
      .then(setItems)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [days]);

  useEffect(() => {
    loadExpiring();
  }, [loadExpiring]);

  return (
    <div>
      <PageHeader title="Tenancies ending soon" description="Active or Ending Soon tenancies whose end date falls within the chosen window." />

      <div className="list-page__toolbar">
        <SelectField label="Window" name="days" value={days} onChange={(event) => setDays(event.target.value)} options={DAYS_OPTIONS} />
      </div>

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadExpiring}
        emptyMessage="No tenancies are ending in this window."
        rows={items}
        getRowKey={(row) => row.TenancyId}
        columns={[
          {
            key: "Property",
            header: "Property",
            render: (row) => <Link to={`/tenancies/${row.TenancyId}`}>{row.PropertyReference}</Link>,
          },
          { key: "Tenant", header: "Tenant", render: (row) => row.TenantName },
          { key: "EndDate", header: "End date", render: (row) => row.EndDate },
          { key: "MonthlyRent", header: "Monthly rent", render: (row) => `£${row.MonthlyRent}` },
          {
            key: "TenancyStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.TenancyStatus} />,
          },
        ]}
      />

      <p>
        <Link to="/tenancies">← Back to tenancies</Link>
      </p>
    </div>
  );
}
