/**
 * GET /api/rent-payments/overdue - a guaranteed-live overdue list (due
 * date passed AND not fully paid, matching SQL Report 2 exactly), unlike
 * filtering the main list by PaymentStatus=Overdue which only reflects
 * the last-known stored status - see rentPaymentService.js. Not
 * paginated, same shape as TenancyEndingSoonPage.
 */
import { Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { listOverduePayments } from "../../services/rentPaymentService";
import { getErrorMessage } from "../../utilities/apiError";
import { downloadCsv } from "../../utilities/csvExport";

const CSV_COLUMNS = [
  { key: "PaymentReference", header: "Payment Reference", value: (row) => row.PaymentReference },
  { key: "PropertyReference", header: "Property", value: (row) => row.PropertyReference },
  { key: "TenantName", header: "Tenant", value: (row) => row.TenantName },
  { key: "DueDate", header: "Due Date", value: (row) => row.DueDate },
  { key: "AmountOutstanding", header: "Amount Outstanding", value: (row) => row.AmountOutstanding },
];

export function RentPaymentOverduePage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadOverdue = useCallback(() => {
    setLoading(true);
    setError(null);
    listOverduePayments()
      .then(setItems)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadOverdue();
  }, [loadOverdue]);

  return (
    <div>
      <PageHeader
        title="Overdue rent payments"
        description="Due date has passed and the payment isn't fully paid, calculated live."
        actions={
          <button type="button" className="button button--secondary" onClick={() => downloadCsv("overdue-payments.csv", CSV_COLUMNS, items)} disabled={items.length === 0}>
            Export CSV
          </button>
        }
      />

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadOverdue}
        emptyMessage="Nothing is overdue right now."
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
          { key: "AmountOutstanding", header: "Outstanding", render: (row) => `£${row.AmountOutstanding}` },
          {
            key: "PaymentStatus",
            header: "Status",
            render: (row) => <StatusBadge status={row.PaymentStatus} />,
          },
        ]}
      />

      <p>
        <Link to="/rent-payments">← Back to rent payments</Link>
      </p>
    </div>
  );
}
