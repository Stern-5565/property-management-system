import { Link } from "react-router-dom";

export function UnauthorizedPage() {
  return (
    <div className="status-page">
      <h1>403 - Not permitted</h1>
      <p>Your account doesn't have access to this page.</p>
      <Link to="/" className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
