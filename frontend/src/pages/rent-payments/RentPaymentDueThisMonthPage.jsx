/**
 * GET /api/rent-payments/due - payments due within the current calendar
 * month, matching SQL Report 1. Not paginated, same shape as
 * RentPaymentOverduePage.
 */
import { Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { listDueThisMonthPayments } from "../../services/rentPaymentService";
import { getErrorMessage } from "../../utilities/apiError";
import { downloadCsv } from "../../utilities/csvExport";

const CSV_COLUMNS = [
  { key: "PaymentReference", header: "Payment Reference", value: (row) => row.PaymentReference },
  { key: "PropertyReference", header: "Property", value: (row) => row.PropertyReference },
  { key: "TenantName", header: "Tenant", value: (row) => row.TenantName },
  { key: "DueDate", header: "Due Date", value: (row) => row.DueDate },
  { key: "AmountOutstanding", header: "Amount Outstanding", value: (row) => row.AmountOutstanding },
];

export function RentPaymentDueThisMonthPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDue = useCallback(() => {
    setLoading(true);
    setError(null);
    listDueThisMonthPayments()
      .then(setItems)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadDue();
  }, [loadDue]);

  return (
    <div>
      <PageHeader
        title="Rent payments due this month"
        description="Every rent payment with a due date in the current calendar month."
        actions={
          <button
            type="button"
            className="button button--secondary"
            onClick={() => downloadCsv("due-this-month-payments.csv", CSV_COLUMNS, items)}
            disabled={items.length === 0}
          >
            Export CSV
          </button>
        }
      />

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadDue}
        emptyMessage="Nothing is due this month."
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
