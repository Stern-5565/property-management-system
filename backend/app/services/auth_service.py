"""Business rules for authentication.

Security limitations of this initial implementation (worth knowing before
relying on this in anything beyond a portfolio/demo context):

- Refresh tokens are stateless JWTs with no server-side revocation list.
  A refresh token that has been issued stays valid until it naturally
  expires (JWT_REFRESH_TOKEN_EXPIRE_DAYS), even after "logout" - there is
  no database table tracking which refresh tokens are still legitimate, so
  there is nothing to revoke. POST /api/auth/logout exists for API
  completeness and to make the frontend's flow explicit, but the real
  logout happens client-side (discarding the stored tokens). A production
  system handling anything sensitive would add a refresh-token table (or a
  short blacklist of revoked token IDs) to make logout and "revoke this
  device" actually effective server-side.
- FailedLoginAttempts is tracked (incremented on failure, reset on
  success) but not yet enforced - there is no lockout after N failures.
  The scope doc calls this out explicitly as a later addition ("Login rate
  limiting later").
- Role changes take effect on the next request (roles are loaded fresh
  from the database in get_current_user, not embedded in the JWT), so
  there's no token-staleness issue there - but note this does mean every
  authenticated request costs a database round trip to check IsActive and
  load roles. Fine at this scale; worth knowing if it ever needs to scale
  up.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utilities.datetime_utils import utc_now


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)

    def authenticate(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.user_repository.get_by_email(email)

        # Deliberately the SAME generic error for "no such user", "wrong
        # password", and "account deactivated" - telling an unauthenticated
        # caller which of those is true is itself an information leak
        # (confirms an email is registered, or that an account exists but
        # is disabled).
        invalid_credentials = AppError("INVALID_CREDENTIALS", "Incorrect email or password.", status_code=401)

        if user is None:
            raise invalid_credentials

        if not verify_password(password, user.PasswordHash):
            user.FailedLoginAttempts += 1
            self.db.commit()
            raise invalid_credentials

        if not user.IsActive:
            raise invalid_credentials

        user.FailedLoginAttempts = 0
        user.LastLoginAt = utc_now()
        self.db.commit()
        self.db.refresh(user)

        access_token = create_access_token(user.UserId)
        refresh_token = create_refresh_token(user.UserId)
        return user, access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = self._load_active_user_from_token_payload(payload)
        return create_access_token(user.UserId)

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.PasswordHash):
            raise AppError("INVALID_CURRENT_PASSWORD", "Current password is incorrect.", status_code=400)

        user.PasswordHash = hash_password(new_password)
        user.UpdatedAt = utc_now()
        self.db.commit()

    def _load_active_user_from_token_payload(self, payload: dict) -> User:
        try:
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError):
            raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401) from None

        user = self.user_repository.get_by_id(user_id)
        if user is None or not user.IsActive:
            raise AppError("INVALID_TOKEN", "Could not validate credentials.", status_code=401)
        return user
