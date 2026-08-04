"""Pydantic schemas for the Landlord module.

Why three separate families of schema (Create / Update / Response) instead
of one shared model:

- LandlordCreate and LandlordUpdate describe what a CLIENT is allowed to
  send. They deliberately exclude system-controlled fields (LandlordId,
  IsActive, CreatedAt, UpdatedAt) - a client cannot invent its own ID,
  reactivate itself, or forge a creation timestamp. `extra="forbid"` makes
  the API reject a request that tries to sneak an unexpected field in,
  rather than silently dropping it.
- LandlordResponse (and the lighter LandlordListItem) describe what the
  SERVER sends back, and legitimately include those system-controlled
  fields, because the client needs to see them even though it can't set
  them.
- Keeping Create and Update as separate classes - even though their field
  set is identical today - means they can diverge later without disturbing
  each other, and it keeps FastAPI's generated OpenAPI docs honest about
  which endpoint expects what.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, model_validator

from app.schemas.common import PaginatedResponse

ContactMethod = Literal["Email", "Phone", "Post"]


class LandlordWriteBase(BaseModel):
    """Fields a client can set when creating or fully replacing a landlord."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    FirstName: str | None = Field(default=None, max_length=50)
    LastName: str | None = Field(default=None, max_length=50)
    CompanyName: str | None = Field(default=None, max_length=150)
    Email: EmailStr | None = Field(default=None, max_length=256)
    Phone: str | None = Field(default=None, max_length=30)
    AddressLine1: str = Field(min_length=1, max_length=150)
    AddressLine2: str | None = Field(default=None, max_length=150)
    City: str = Field(min_length=1, max_length=100)
    Postcode: str = Field(min_length=1, max_length=20)
    Country: str = Field(min_length=1, max_length=100)
    PreferredContactMethod: ContactMethod | None = None

    @model_validator(mode="after")
    def require_company_or_full_name(self) -> "LandlordWriteBase":
        """Mirrors the database's CK_Landlords_NameOrCompany constraint.

        Checking this in the API too means a bad request gets a clear 422
        with a helpful message, instead of surfacing as a raw SQL Server
        constraint-violation error that the frontend would have to parse.
        """
        has_company = bool(self.CompanyName)
        has_full_name = bool(self.FirstName) and bool(self.LastName)
        if not has_company and not has_full_name:
            raise ValueError("A landlord must have either a CompanyName, or both FirstName and LastName.")
        return self


class LandlordCreate(LandlordWriteBase):
    """Request body for POST /api/landlords."""


class LandlordUpdate(LandlordWriteBase):
    """Request body for PUT /api/landlords/{id}.

    A PUT replaces the landlord's editable fields wholesale, so this
    intentionally mirrors LandlordCreate's required fields rather than
    making everything optional (that would make it a PATCH). Activating or
    deactivating a landlord is a separate, single-purpose action - see
    LandlordStatusUpdate - not something bundled into a general edit.
    """


class LandlordStatusUpdate(BaseModel):
    """Request body for PATCH /api/landlords/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    IsActive: bool


class LandlordResponse(BaseModel):
    """Full landlord representation returned by detail and write endpoints."""

    # from_attributes=True lets this be built directly from a SQLAlchemy
    # Landlord instance, e.g. LandlordResponse.model_validate(landlord_row).
    model_config = ConfigDict(from_attributes=True)

    LandlordId: int
    FirstName: str | None
    LastName: str | None
    CompanyName: str | None
    # Plain str here, not EmailStr: this value already passed EmailStr
    # validation on the way in (LandlordWriteBase.Email). Re-validating
    # trusted data read back from the database on every response would
    # only add risk of a future validator change breaking old records that
    # were valid when stored - strict validation belongs on the write path.
    Email: str | None
    Phone: str | None
    AddressLine1: str
    AddressLine2: str | None
    City: str
    Postcode: str
    Country: str
    PreferredContactMethod: str | None
    IsActive: bool
    CreatedAt: datetime
    UpdatedAt: datetime

    @computed_field
    @property
    def DisplayName(self) -> str:
        """CompanyName if set, otherwise "FirstName LastName".

        Matches the COALESCE(...) pattern used throughout
        database/07-report-queries.sql, so the frontend never has to
        reimplement that fallback logic itself.
        """
        return self.CompanyName or f"{self.FirstName} {self.LastName}"


class LandlordListItem(BaseModel):
    """Lighter-weight representation used in GET /api/landlords list results."""

    model_config = ConfigDict(from_attributes=True)

    LandlordId: int
    FirstName: str | None
    LastName: str | None
    CompanyName: str | None
    Email: str | None
    Phone: str | None
    City: str
    IsActive: bool

    @computed_field
    @property
    def DisplayName(self) -> str:
        return self.CompanyName or f"{self.FirstName} {self.LastName}"


LandlordListResponse = PaginatedResponse[LandlordListItem]
