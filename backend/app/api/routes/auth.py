"""HTTP routes for authentication.

Where the frontend should store authentication state: the access token in
memory (e.g. a React context/store), NOT localStorage or a plain cookie -
anything readable by JavaScript is readable by an XSS payload too. The
refresh token is longer-lived and more sensitive; the safer place for it is
an httpOnly cookie the browser attaches automatically and JavaScript can
never read at all (this backend issues it as a plain JSON field for now -
see the frontend milestones for wiring up httpOnly-cookie delivery
instead). On page reload, the frontend calls POST /api/auth/refresh to get
a new access token rather than persisting the access token itself.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    _user, access_token, refresh_token = service.authenticate(data.Email, data.Password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(data: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> RefreshResponse:
    access_token = service.refresh_access_token(data.refresh_token)
    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user)) -> None:
    """Requires a valid access token (so at minimum this confirms the
    caller was actually logged in), but there is no server-side session or
    refresh-token record to clear - see AuthService's module docstring for
    why. The frontend is responsible for discarding both stored tokens;
    that discard is what actually "logs the user out" here.
    """
    return None


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.from_user(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    service.change_password(current_user, data.CurrentPassword, data.NewPassword)
