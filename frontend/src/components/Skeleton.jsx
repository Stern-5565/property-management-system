/**
 * Loading placeholder - a pulsing grey block standing in for a KPI
 * figure, chart, or list row while its data is still in flight. Built
 * for the real Dashboard (Prompt 24 explicitly asks for "loading
 * skeletons", distinct from the spinner `LoadingSpinner` already covers
 * elsewhere), but generic enough for any module wanting a skeleton
 * instead of a spinner for a specific piece of layout.
 */
export function Skeleton({ width = "100%", height = "1rem" }) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />;
}
