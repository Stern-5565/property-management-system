/**
 * One headline number - built for the real Dashboard page (which will
 * replace pages/HomePage.jsx) to render the /api/dashboard/summary
 * figures (TotalActiveProperties, OccupancyPercentage, RentDueThisMonth,
 * ...) as a row of cards, but generic enough for any "one number, one
 * label" spot in any module.
 */
export function KpiCard({ label, value, hint, tone = "neutral" }) {
  return (
    <div className={`kpi-card kpi-card--${tone}`}>
      <span className="kpi-card__label">{label}</span>
      <span className="kpi-card__value">{value}</span>
      {hint && <span className="kpi-card__hint">{hint}</span>}
    </div>
  );
}
