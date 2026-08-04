import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="status-page">
      <h1>404 - Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to="/" className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
