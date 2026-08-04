"""Protected-route dependencies: get_current_user and require_roles.

How these work in FastAPI's dependency-injection system:

- get_current_user is itself a dependency (it takes Depends(...) params).
  A route that declares `current_user: User = Depends(get_current_user)`
  causes FastAPI to run get_current_user BEFORE the route body: it pulls
  the bearer token out of the Authorization header (via the HTTPBearer
  security scheme), decodes and validates it, loads the User row, and
  confirms the account is still active. If any of that fails, it raises
  AppError and the route body never runs at all.
- require_roles(*allowed_roles) is a dependency FACTORY, not a dependency
  itself - calling it returns a new dependency function with the allowed
  roles baked in via closure. That's why routes use
  `dependencies=[Depends(require_roles(roles.ADMINISTRATOR, ...))]`
  rather than `Depends(require_roles)`: they need the *result* of calling
  it, configured for that specific route.
- Both build on the SAME underlying check (get_current_user), so a route
  requiring specific roles automatically also requires a valid, active
  login - there's no way to satisfy require_roles without first passing
  get_current_user.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import decode_token
from app.database.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# HTTPBearer (not OAuth2PasswordBearer): our login endpoint takes a JSON
# body ({"Email": ..., "Password": ...}), not OAuth2's form-encoded
# username/password, so the OAuth2 password-flow scheme would misrepresent
# how this API actually works. HTTPBearer just means "read the token out
# of an `Authorization: Bearer <token>` header" - an accurate description
# regardless of how the token was obtained.
_security_scheme = HTTPBearer()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials, expected_type="access")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401) from None

    user = db.get(User, user_id)
    # Re-checked on every request, not just at login: a token issued while
    # the account was active must stop working the moment the account is
    # deactivated, not just the next time someone tries to log in.
    if user is None or not user.IsActive:
        raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401)

    return user


def require_roles(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_names = {role.RoleName for role in current_user.Roles}
        if not user_role_names.intersection(allowed_roles):
            raise AppError(
                "FORBIDDEN", "You do not have permission to perform this action.", status_code=403
            )
        return current_user

    return dependency
