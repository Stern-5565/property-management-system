/**
 * `user.Roles` (from AuthContext, ultimately GET /api/auth/me) is a plain
 * array of role name strings - this just checks whether any of them is in
 * an allowed-roles list, so every module's "should this button/route be
 * visible" check reads the same way instead of each page reimplementing
 * `.some(...)`.
 */
export function hasAnyRole(user, allowedRoles) {
  if (!user) {
    return false;
  }
  return user.Roles.some((role) => allowedRoles.includes(role));
}
