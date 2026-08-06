/**
 * The real Dashboard (Prompt 24) - replaces the Prompt 18 placeholder
 * HomePage.jsx. Every figure here comes straight from the backend's
 * dashboard endpoints (or the same list endpoints their own attention
 * pages use) - the scope doc is explicit that KPIs must never be
 * calculated client-side from an incomplete frontend list, so this page
 * has no arithmetic of its own beyond formatting (£ prefixes, percentage
 * rounding) and aggregating MaintenanceSummaryResponse.StatusBreakdown's
 * per-priority rows into per-status totals for the chart (still just
 * re-summing numbers the backend already computed, not deriving a new
 * figure from a partial list).
 *
 * One Promise.all covers all eight calls (5 dashboard endpoints + the 3
 * attention lists, reusing rentPaymentService/tenancyService/
 * maintenanceService rather than duplicating those queries) - a single
 * loading/error state for the whole page rather than one per section,
 * since every section depends on the same backend being up anyway.
 *
 * The three attention lists reuse each module's own already-built
 * "guaranteed live" endpoint (rent-payments/overdue, tenancies/expiring,
 * maintenance-requests?priority=Emergency) rather than deriving overdue/
 * ending-soon/emergency status from the summary counts - each "View all"
 * link goes to that module's own full attention page (or, for
 * maintenance, a `?priority=Emergency` prefill - see
 * MaintenanceRequestsListPage's own comment on that param).
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { KpiCard } from "../components/KpiCard";
import { BarChart } from "../components/BarChart";
import { Skeleton } from "../components/Skeleton";
import { ErrorMessage } from "../components/ErrorMessage";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../contexts/AuthContext";
import { getSummary, getRentSummary, getOccupancy, getMaintenanceSummary, getRecentActivity } from "../services/dashboardService";
import { listOverduePayments } from "../services/rentPaymentService";
import { listExpiringTenancies } from "../services/tenancyService";
import { listRequests } from "../services/maintenanceService";
import { getErrorMessage } from "../utilities/apiError";

const OPEN_MAINTENANCE_STATUSES = ["Reported", "Assigned", "In Progress", "Waiting for Parts", "Waiting for Approval"];

function toneIfPositive(value, tone) {
  return value > 0 ? tone : "neutral";
}

function KpiSkeletonRow() {
  return (
    <div className="dashboard-kpis">
      {Array.from({ length: 6 }).map((_, index) => (
        <div className="kpi-card" key={index}>
          <Skeleton width="70%" height="0.8rem" />
          <Skeleton width="45%" height="1.6rem" />
        </div>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboard = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getSummary(),
      getRentSummary(6),
      getOccupancy(),
      getMaintenanceSummary(),
      getRecentActivity(10),
      listOverduePayments(),
      listExpiringTenancies(30),
      listRequests({ priority: "Emergency", pageSize: 100 }),
    ])
      .then(([summary, rentSummary, occupancy, maintenanceSummary, recentActivity, overduePayments, endingSoonTenancies, emergencyResult]) => {
        setData({
          summary,
          rentSummary,
          occupancy,
          maintenanceSummary,
          recentActivity,
          overduePayments,
          endingSoonTenancies,
          emergencyRequests: emergencyResult.items.filter((request) => OPEN_MAINTENANCE_STATUSES.includes(request.MaintenanceStatus)),
        });
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (error) {
    return <ErrorMessage message={error} onRetry={loadDashboard} />;
  }

  if (loading || !data) {
    return (
      <div>
        <PageHeader title={`Welcome back, ${user.EmployeeName}`} description="Loading your portfolio overview…" />
        <KpiSkeletonRow />
        <div className="dashboard-grid">
          <div className="dashboard-section">
            <Skeleton height="180px" />
          </div>
          <div className="dashboard-section">
            <Skeleton height="180px" />
          </div>
        </div>
      </div>
    );
  }

  const { summary, rentSummary, occupancy, maintenanceSummary, recentActivity, overduePayments, endingSoonTenancies, emergencyRequests } = data;

  const occupancyBars = occupancy.StatusBreakdown.map((item) => ({
    label: item.PropertyStatus,
    value: item.PropertyCount,
    displayValue: `${item.PropertyCount} (${item.PercentageOfPortfolio.toFixed(1)}%)`,
  }));

  const rentCollectionBars = rentSummary.MonthlyCollection.map((point) => ({
    label: point.MonthLabel,
    value: Number(point.TotalCollected),
    displayValue: `£${point.TotalCollected}`,
  }));

  const maintenanceStatusTotals = {};
  for (const row of maintenanceSummary.StatusBreakdown) {
    maintenanceStatusTotals[row.MaintenanceStatus] = (maintenanceStatusTotals[row.MaintenanceStatus] ?? 0) + row.RequestCount;
  }
  const maintenanceBars = Object.entries(maintenanceStatusTotals).map(([label, value]) => ({ label, value }));

  return (
    <div>
      <PageHeader title={`Welcome back, ${user.EmployeeName}`} description="An overview of the property portfolio." />

      <div className="dashboard-kpis">
        <KpiCard label="Active properties" value={summary.TotalActiveProperties} />
        <KpiCard label="Occupied" value={summary.OccupiedProperties} tone="success" />
        <KpiCard label="Vacant" value={summary.VacantProperties} tone={toneIfPositive(summary.VacantProperties, "warning")} />
        <KpiCard label="Occupancy rate" value={`${summary.OccupancyPercentage.toFixed(1)}%`} />
        <KpiCard label="Active tenancies" value={summary.ActiveTenancies} />
        <KpiCard label="Rent due this month" value={`£${summary.RentDueThisMonth}`} />
        <KpiCard label="Rent collected this month" value={`£${summary.RentCollectedThisMonth}`} tone="success" />
        <KpiCard
          label="Outstanding rent"
          value={`£${summary.OutstandingRent}`}
          tone={toneIfPositive(Number(summary.OutstandingRent), "danger")}
        />
        <KpiCard
          label="Open maintenance requests"
          value={summary.OpenMaintenanceRequests}
          tone={toneIfPositive(summary.OpenMaintenanceRequests, "warning")}
        />
        <KpiCard
          label="Emergency requests"
          value={summary.EmergencyMaintenanceRequests}
          tone={toneIfPositive(summary.EmergencyMaintenanceRequests, "danger")}
        />
        <KpiCard
          label="Tenancies ending soon"
          value={summary.TenanciesEndingSoon}
          tone={toneIfPositive(summary.TenanciesEndingSoon, "warning")}
        />
      </div>

      <div className="dashboard-grid">
        <BarChart title="Occupancy by status" bars={occupancyBars} />
        <BarChart title="Maintenance requests by status" bars={maintenanceBars} />

        <div className="dashboard-grid__full">
          <BarChart
            title={`Rent collected by month (${rentSummary.CollectionRatePercent.toFixed(1)}% collection rate)`}
            bars={rentCollectionBars}
          />
        </div>

        <section className="dashboard-section">
          <div className="dashboard-section__header">
            <h3 className="dashboard-section__title">Overdue rent</h3>
            <Link to="/rent-payments/overdue">View all</Link>
          </div>
          {overduePayments.length === 0 ? (
            <p className="dashboard-section__empty">Nothing overdue right now.</p>
          ) : (
            <ul className="dashboard-section__list">
              {overduePayments.slice(0, 5).map((payment) => (
                <li key={payment.RentPaymentId}>
                  <div className="dashboard-section__row">
                    <Link to={`/rent-payments/${payment.RentPaymentId}`}>
                      {payment.PropertyReference} — {payment.TenantName}
                    </Link>
                    <span>£{payment.AmountOutstanding}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dashboard-section">
          <div className="dashboard-section__header">
            <h3 className="dashboard-section__title">Tenancies ending soon</h3>
            <Link to="/tenancies/ending-soon">View all</Link>
          </div>
          {endingSoonTenancies.length === 0 ? (
            <p className="dashboard-section__empty">No tenancies ending in the next 30 days.</p>
          ) : (
            <ul className="dashboard-section__list">
              {endingSoonTenancies.slice(0, 5).map((tenancy) => (
                <li key={tenancy.TenancyId}>
                  <div className="dashboard-section__row">
                    <Link to={`/tenancies/${tenancy.TenancyId}`}>
                      {tenancy.PropertyReference} — {tenancy.TenantName}
                    </Link>
                    <span>{tenancy.EndDate}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="dashboard-grid__full">
          <section className="dashboard-section">
            <div className="dashboard-section__header">
              <h3 className="dashboard-section__title">Emergency maintenance</h3>
              <Link to="/maintenance?priority=Emergency">View all</Link>
            </div>
            {emergencyRequests.length === 0 ? (
              <p className="dashboard-section__empty">No open emergency requests right now.</p>
            ) : (
              <ul className="dashboard-section__list">
                {emergencyRequests.slice(0, 5).map((request) => (
                  <li key={request.MaintenanceRequestId}>
                    <div className="dashboard-section__row">
                      <Link to={`/maintenance/${request.MaintenanceRequestId}`}>
                        {request.RequestReference} — {request.Title}
                      </Link>
                      <StatusBadge status={request.MaintenanceStatus} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="dashboard-grid__full">
          <section className="dashboard-section">
            <div className="dashboard-section__header">
              <h3 className="dashboard-section__title">Recent activity</h3>
            </div>
            {recentActivity.length === 0 ? (
              <p className="dashboard-section__empty">No recent activity yet.</p>
            ) : (
              <ul className="timeline">
                {recentActivity.map((item) => (
                  <li key={item.AuditLogId} className="timeline__item">
                    <div className="timeline__meta">
                      {item.UserName ?? "System"} — {item.CreatedAt}
                    </div>
                    <p className="timeline__text">
                      {item.Action} {item.EntityName} #{item.EntityId}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
