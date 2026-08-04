/**
 * Placeholder landing page - stands in for the real dashboard, which is
 * its own later prompt (documentation/project-scope.md, "Build the
 * PropertyManager React dashboard"). This just proves the authenticated
 * shell (routing + layout + auth context) actually works end to end.
 */
import { useAuth } from "../contexts/AuthContext";

export function HomePage() {
  const { user } = useAuth();

  return (
    <div>
      <h1>Welcome back, {user.EmployeeName}</h1>
      <p>
        You're signed in as <strong>{user.Roles.join(", ")}</strong>. The real dashboard (KPI cards, charts, recent
        activity) lands in a later milestone - see documentation/progress-log.md.
      </p>
    </div>
  );
}
