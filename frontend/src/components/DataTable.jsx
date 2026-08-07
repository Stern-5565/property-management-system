/**
 * Generic list-page table. Every module's list page (Landlords,
 * Properties, ... - see documentation/progress-log.md's frontend module
 * plan) renders one of these: pass it `columns` (what to show) and `rows`
 * (the page of data from the module's API service), and it handles the
 * loading/error/empty states that would otherwise be re-implemented on
 * every page.
 *
 * `columns` shape: [{ key, header, render?(row) }]. `render` is optional -
 * without it, the cell just shows `row[key]`; with it, a column can show
 * a computed value or another component (e.g. <StatusBadge
 * status={row.PaymentStatus} />) without DataTable needing to know
 * anything about that column's content.
 *
 * `getRowClassName` is optional (added for Maintenance's emergency-row
 * highlighting - see MaintenanceRequestsListPage) - lets a row carry an
 * extra class (e.g. a background tint) without DataTable needing to know
 * why.
 *
 * `totals` is optional (added for the Reports module - Prompt 25's
 * "totals where relevant" requirement) - a single object shaped like a
 * row (only the columns where a total makes sense need a key), rendered
 * as a `<tfoot>` row through the exact same `column.render`/`row[key]`
 * logic as every body row, so a currency column's total gets the same
 * £-prefix formatting as its body cells for free. The first column
 * always shows the word "Total" instead, regardless of whether `totals`
 * has a value for that column's key.
 */
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorMessage } from "./ErrorMessage";
import { EmptyState } from "./EmptyState";

export function DataTable({
  columns,
  rows,
  getRowKey = (row, index) => row.id ?? index,
  getRowClassName,
  loading = false,
  error = null,
  onRetry,
  emptyMessage = "No records found.",
  totals,
}) {
  if (loading) {
    return (
      <div className="data-table__status">
        <LoadingSpinner label="Loading records…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-table__status">
        <ErrorMessage message={error} onRetry={onRetry} />
      </div>
    );
  }

  if (rows.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key} scope="col">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={getRowKey(row, index)} className={getRowClassName ? getRowClassName(row) : undefined}>
            {columns.map((column) => (
              <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
      {totals && (
        <tfoot>
          <tr className="data-table__totals-row">
            {columns.map((column, index) => (
              <td key={column.key}>
                {index === 0
                  ? "Total"
                  : column.key in totals
                    ? column.render
                      ? column.render(totals)
                      : totals[column.key]
                    : ""}
              </td>
            ))}
          </tr>
        </tfoot>
      )}
    </table>
  );
}
