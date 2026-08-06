import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { getDefaultLandingPath } from "../utilities/permissions";

/**
 * Same "/" can't be hardcoded here reasoning as UnauthorizedPage.jsx -
 * "/" (the real Dashboard) is gated to CAN_VIEW_DASHBOARD, which
 * excludes MaintenanceEmployee. This route also renders for a logged-out
 * visitor (it's a top-level sibling of ProtectedRoute in App.jsx, not
 * nested inside it) - getDefaultLandingPath(null) still resolves safely
 * to "/maintenance" in that case, which ProtectedRoute then redirects to
 * /login, same end result as before this fix.
 */
export function NotFoundPage() {
  const { user } = useAuth();

  return (
    <div className="status-page">
      <h1>404 - Page not found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <Link to={getDefaultLandingPath(user)} className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
