/**
 * Inline error display for a failed request - pass it whatever string
 * utilities/apiError.js's getErrorMessage(err) returns. Deliberately takes
 * a plain string rather than the raw error object, so this component
 * doesn't need to know anything about Axios/the backend's error shape;
 * that translation happens once, at the call site.
 */
export function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
