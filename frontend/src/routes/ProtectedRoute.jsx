/**
 * Route guard used as a layout route: <Route element={<ProtectedRoute />}>
 * wraps every child route that requires a logged-in user, rendering them
 * via <Outlet /> only once auth is confirmed.
 *
 * `allowedRoles` is optional and not used by any route yet (no business
 * pages exist this early - see documentation/progress-log.md's Prompt 18
 * note), but the check is built and demonstrated here so each module's
 * frontend (built module-by-module later) can opt into role-gating just by
 * passing the roles it needs, without touching this file again.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LoadingSpinner } from "../components/LoadingSpinner";

export function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, initializing, user } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <LoadingSpinner fullPage label="Checking your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (allowedRoles && !user.Roles.some((role) => allowedRoles.includes(role))) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
