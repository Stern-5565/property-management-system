/**
 * The Reports hub - a plain list of the 10 MVP reports linking to
 * /reports/:reportKey (ReportViewPage). No API call here at all; the
 * list itself comes straight from constants/reportDefinitions.js, the
 * same "reusable pattern" source ReportViewPage reads from.
 */
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { REPORT_DEFINITIONS } from "../../constants/reportDefinitions";

export function ReportsIndexPage() {
  return (
    <div>
      <PageHeader title="Reports" description="The 10 MVP business reports, each with its own filters and CSV export." />

      <ul className="report-index__list">
        {REPORT_DEFINITIONS.map((report) => (
          <li key={report.key}>
            <Link to={`/reports/${report.key}`} className="report-index__link">
              {report.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
