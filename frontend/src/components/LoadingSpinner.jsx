/**
 * Generic loading indicator - used both as a full-page state (e.g. while
 * AuthContext restores a session) and inline within a page once real data
 * fetching exists. Kept intentionally tiny; the full reusable component
 * library (Prompt 19) can extend this with size/variant props later
 * without any consumer of this component needing to change.
 */
export function LoadingSpinner({ label = "Loading…", fullPage = false }) {
  const spinner = (
    <div className="loading-spinner" role="status" aria-live="polite">
      <span className="loading-spinner__circle" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );

  if (!fullPage) {
    return spinner;
  }

  return <div className="loading-spinner__page">{spinner}</div>;
}
