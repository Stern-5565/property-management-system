/**
 * The one generic report page every entry in REPORT_DEFINITIONS renders
 * through (route: /reports/:reportKey) - the "reusable reporting
 * pattern" Prompt 25 explicitly asks for building before implementing
 * the remaining reports. Title/description/columns/totals all come from
 * the backend response itself (see reportService.js); this page only
 * needs to know, per report, which filter INPUTS to render before that
 * response exists (constants/reportDefinitions.js).
 *
 * CSV export re-serializes the exact rows already in `report.Rows` -
 * the same rows the table is showing, which only ever came from the
 * backend's own filtered response, never re-filtered/re-sorted on the
 * client. That's what satisfies Prompt 25's "the backend must apply
 * filters and create export data" without a second server-side export
 * endpoint - see reports.py's own docstring for the full reasoning.
 *
 * Print uses the browser's own window.print() plus a global `@media
 * print` rule (global.css) that hides the sidebar/header/filters/action
 * buttons - no separate "print view" markup to keep in sync with the
 * screen view.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DataTable } from "../../components/DataTable";
import { SelectField } from "../../components/SelectField";
import { DateField } from "../../components/DateField";
import { ErrorMessage } from "../../components/ErrorMessage";
import { REPORT_DEFINITIONS } from "../../constants/reportDefinitions";
import { getReport } from "../../services/reportService";
import { listProperties } from "../../services/propertyService";
import { listLandlords } from "../../services/landlordService";
import { getErrorMessage } from "../../utilities/apiError";
import { downloadCsv } from "../../utilities/csvExport";

const DAYS_AHEAD_OPTIONS = [
  { value: "30", label: "Next 30 days" },
  { value: "60", label: "Next 60 days" },
  { value: "90", label: "Next 90 days" },
];

function formatReportCell(value, type) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (type === "currency") return `£${value}`;
  if (type === "percent") return `${value}%`;
  return value;
}

function defaultFilterValues(definition) {
  const values = {};
  for (const filter of definition?.filters ?? []) {
    values[filter.name] = filter.type === "days-ahead" ? "30" : "";
  }
  return values;
}

export function ReportViewPage() {
  const { reportKey } = useParams();
  const definition = REPORT_DEFINITIONS.find((d) => d.key === reportKey);

  const [filters, setFilters] = useState(() => defaultFilterValues(definition));
  const [propertyOptions, setPropertyOptions] = useState([]);
  const [landlordOptions, setLandlordOptions] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const needsPropertyOptions = definition?.filters.some((f) => f.type === "property-select") ?? false;
  const needsLandlordOptions = definition?.filters.some((f) => f.type === "landlord-select") ?? false;

  useEffect(() => {
    setFilters(defaultFilterValues(definition));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportKey]);

  useEffect(() => {
    if (needsPropertyOptions) {
      listProperties({ pageSize: 100 }).then((data) =>
        setPropertyOptions(data.items.map((p) => ({ value: String(p.PropertyId), label: p.PropertyReference }))),
      );
    }
    if (needsLandlordOptions) {
      listLandlords({ pageSize: 100 }).then((data) =>
        setLandlordOptions(data.items.map((l) => ({ value: String(l.LandlordId), label: l.DisplayName }))),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportKey]);

  const loadReport = useCallback(() => {
    if (!definition) {
      return;
    }
    setLoading(true);
    setError(null);
    getReport(reportKey, filters)
      .then(setReport)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [reportKey, filters, definition]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  function updateFilter(name) {
    return (event) => setFilters((prev) => ({ ...prev, [name]: event.target.value }));
  }

  const columns = useMemo(() => {
    if (!report) {
      return [];
    }
    return report.Columns.map((column) => ({
      key: column.key,
      header: column.header,
      render: (row) => formatReportCell(row[column.key], column.type),
    }));
  }, [report]);

  function handleExportCsv() {
    if (!report) {
      return;
    }
    const csvColumns = report.Columns.map((column) => ({
      key: column.key,
      header: column.header,
      value: (row) => row[column.key],
    }));
    downloadCsv(`${reportKey}.csv`, csvColumns, report.Rows);
  }

  if (!definition) {
    return <ErrorMessage message="Unknown report." />;
  }

  return (
    <div>
      <PageHeader
        title={report?.Title ?? definition.label}
        description={report?.Description}
        actions={
          <>
            <button type="button" className="button button--secondary" onClick={() => window.print()} disabled={!report}>
              Print
            </button>
            <button
              type="button"
              className="button button--secondary"
              onClick={handleExportCsv}
              disabled={!report || report.Rows.length === 0}
            >
              Export CSV
            </button>
          </>
        }
      />

      {definition.filters.length > 0 && (
        <div className="report-page__filters">
          {definition.filters.map((filter) => {
            if (filter.type === "property-select") {
              return (
                <SelectField
                  key={filter.name}
                  label={filter.label}
                  name={filter.name}
                  value={filters[filter.name] ?? ""}
                  onChange={updateFilter(filter.name)}
                  placeholder={`Any ${filter.label.toLowerCase()}`}
                  options={propertyOptions}
                />
              );
            }
            if (filter.type === "landlord-select") {
              return (
                <SelectField
                  key={filter.name}
                  label={filter.label}
                  name={filter.name}
                  value={filters[filter.name] ?? ""}
                  onChange={updateFilter(filter.name)}
                  placeholder={`Any ${filter.label.toLowerCase()}`}
                  options={landlordOptions}
                />
              );
            }
            if (filter.type === "days-ahead") {
              return (
                <SelectField
                  key={filter.name}
                  label={filter.label}
                  name={filter.name}
                  value={filters[filter.name] ?? "30"}
                  onChange={updateFilter(filter.name)}
                  options={DAYS_AHEAD_OPTIONS}
                />
              );
            }
            return (
              <DateField
                key={filter.name}
                label={filter.label}
                name={filter.name}
                value={filters[filter.name] ?? ""}
                onChange={updateFilter(filter.name)}
              />
            );
          })}
        </div>
      )}

      <DataTable
        loading={loading}
        error={error}
        onRetry={loadReport}
        rows={report?.Rows ?? []}
        columns={columns}
        totals={report?.Totals ?? undefined}
        emptyMessage="No results for these filters."
      />

      <p className="no-print">
        <Link to="/reports">← Back to reports</Link>
      </p>
    </div>
  );
}
