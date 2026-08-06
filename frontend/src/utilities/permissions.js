/**
 * `user.Roles` (from AuthContext, ultimately GET /api/auth/me) is a plain
 * array of role name strings - this just checks whether any of them is in
 * an allowed-roles list, so every module's "should this button/role be
 * visible" check reads the same way instead of each page reimplementing
 * `.some(...)`.
 */
import { CAN_VIEW_DASHBOARD } from "../constants/roles";

export function hasAnyRole(user, allowedRoles) {
  if (!user) {
    return false;
  }
  return user.Roles.some((role) => allowedRoles.includes(role));
}

/**
 * "/" is both the Dashboard route and the default post-login landing
 * page (see LoginPage.jsx) - but the Dashboard is gated to
 * CAN_VIEW_DASHBOARD, which excludes MaintenanceEmployee. Without this,
 * a MaintenanceEmployee logging in would land on "/" only to be
 * immediately bounced to /unauthorized.
 */
export function getDefaultLandingPath(user) {
  return hasAnyRole(user, CAN_VIEW_DASHBOARD) ? "/" : "/maintenance";
}
