"""Pydantic schemas for the auth module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import User


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Email: EmailStr
    Password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    CurrentPassword: str = Field(min_length=1)
    NewPassword: str = Field(min_length=8, max_length=255)

    @field_validator("NewPassword")
    @classmethod
    def require_letter_and_digit(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("New password must contain at least one letter and one digit.")
        return value


class CurrentUserResponse(BaseModel):
    """Response for GET /api/auth/me.

    Not built via from_attributes=True like the Landlord response schemas:
    Roles here is a list of role NAMES, but User.Roles (the SQLAlchemy
    relationship) is a list of Role ORM objects - Pydantic can't coerce one
    into the other automatically. from_user() does that transformation
    explicitly instead, which is clearer than fighting the ORM-conversion
    machinery for a field that needs real reshaping.
    """

    UserId: int
    Username: str
    Email: str
    EmployeeId: int
    EmployeeName: str
    IsActive: bool
    LastLoginAt: datetime | None
    Roles: list[str]

    @classmethod
    def from_user(cls, user: User) -> CurrentUserResponse:
        return cls(
            UserId=user.UserId,
            Username=user.Username,
            Email=user.Email,
            EmployeeId=user.EmployeeId,
            EmployeeName=f"{user.Employee.FirstName} {user.Employee.LastName}",
            IsActive=user.IsActive,
            LastLoginAt=user.LastLoginAt,
            Roles=sorted(role.RoleName for role in user.Roles),
        )
