/**
 * Simple horizontal bar chart - built for the real Dashboard's
 * occupancy/monthly-rent-collection/maintenance-status charts (Prompt
 * 24), generic enough for any "compare a handful of labeled values"
 * spot. No charting library added - same "avoid unnecessary complexity"
 * reasoning as ConfirmationDialog's hand-rolled focus handling and
 * csvExport.js's hand-rolled download; this project has no chart
 * dependency in package.json and Prompt 18 asked for "plain React and
 * readable CSS".
 *
 * `bars` shape: [{ label, value, displayValue? }]. `value` drives the
 * bar's width (relative to the largest value in the set); `displayValue`
 * is what's actually printed next to the bar (defaults to `value`) so a
 * caller can show "£1,200.00" or "12 (34.5%)" while still sorting/scaling
 * on the plain number.
 */
export function BarChart({ title, bars, emptyMessage = "No data yet." }) {
  const max = Math.max(1, ...bars.map((bar) => bar.value));

  return (
    <div className="bar-chart">
      {title && <h3 className="bar-chart__title">{title}</h3>}
      {bars.length === 0 ? (
        <p className="bar-chart__empty">{emptyMessage}</p>
      ) : (
        <div className="bar-chart__rows">
          {bars.map((bar) => (
            <div className="bar-chart__row" key={bar.label}>
              <span className="bar-chart__label">{bar.label}</span>
              <div className="bar-chart__track">
                <div className="bar-chart__fill" style={{ width: `${(bar.value / max) * 100}%` }} />
              </div>
              <span className="bar-chart__value">{bar.displayValue ?? bar.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
