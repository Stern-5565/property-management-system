/**
 * Client-side CSV export - the scope doc's Prompt 22 "CSV export button"
 * requirement has no backend endpoint behind it (no /export route
 * anywhere in app/api/routes), so this builds a CSV directly from
 * whatever rows are already loaded in the page and triggers a browser
 * download via a Blob + temporary <a download>. No library added for
 * this - same "avoid unnecessary complexity" reasoning as
 * ConfirmationDialog's hand-rolled focus handling.
 *
 * `columns` shape: [{ key, header, value(row) }] - deliberately separate
 * from DataTable's `columns` (which uses `render` and can return JSX);
 * `value` here must return a plain string/number since it's going into a
 * text file, not the DOM.
 */
function escapeCsvValue(value) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  if (/[",\n]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

export function downloadCsv(filename, columns, rows) {
  const headerLine = columns.map((column) => escapeCsvValue(column.header)).join(",");
  const dataLines = rows.map((row) => columns.map((column) => escapeCsvValue(column.value(row))).join(","));
  const csvContent = [headerLine, ...dataLines].join("\r\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
