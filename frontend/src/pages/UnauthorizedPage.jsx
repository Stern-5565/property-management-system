import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { getDefaultLandingPath } from "../utilities/permissions";

/**
 * "Back to dashboard" can't just hardcode "/" - now that "/" (the real
 * Dashboard) is itself gated to CAN_VIEW_DASHBOARD, a MaintenanceEmployee
 * landing here (e.g. by clicking the sidebar's Dashboard link, which
 * isn't role-gated) would click straight back into another 403. Same
 * getDefaultLandingPath fix as LoginPage's post-login redirect.
 */
export function UnauthorizedPage() {
  const { user } = useAuth();

  return (
    <div className="status-page">
      <h1>403 - Not permitted</h1>
      <p>Your account doesn't have access to this page.</p>
      <Link to={getDefaultLandingPath(user)} className="button">
        Back to dashboard
      </Link>
    </div>
  );
}
