"""Pydantic schemas for the Property module.

Same Create/Update/Response split as Landlord (see schemas/landlord.py for
the full reasoning) - one addition here: PropertyStatus is NOT settable via
PropertyCreate/PropertyUpdate at all, only via the dedicated
PropertyStatusUpdate + PATCH /api/properties/{id}/status. A brand-new
property has no tenancy yet, so it always starts life as "Vacant" - letting
a client set an arbitrary status at creation would let it claim "Occupied"
for a property with nothing actually renting it.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse

# Named PropertyTypeValue/PropertyStatusValue, not PropertyType/PropertyStatus:
# a module-level type alias with the SAME name as a class field below broke
# Python 3.14's deferred annotation evaluation in the Landlord schemas
# (see schemas/landlord.py's git history) - avoiding the collision entirely
# here rather than relying on remembering why it's risky.
PropertyTypeValue = Literal["House", "Flat", "Bungalow", "Studio", "Maisonette", "Other"]
PropertyStatusValue = Literal["Vacant", "Occupied", "Under Maintenance", "Unavailable", "Archived"]


class PropertyWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    LandlordId: int
    PropertyReference: str = Field(min_length=1, max_length=30)
    AddressLine1: str = Field(min_length=1, max_length=150)
    AddressLine2: str | None = Field(default=None, max_length=150)
    City: str = Field(min_length=1, max_length=100)
    Postcode: str = Field(min_length=1, max_length=20)
    Country: str = Field(min_length=1, max_length=100)
    PropertyType: PropertyTypeValue
    Bedrooms: int = Field(ge=0, le=50)
    Bathrooms: int = Field(ge=0, le=50)
    MonthlyRent: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    DepositAmount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    DateAcquired: date | None = None
    Notes: str | None = Field(default=None, max_length=1000)


class PropertyCreate(PropertyWriteBase):
    """Request body for POST /api/properties."""


class PropertyUpdate(PropertyWriteBase):
    """Request body for PUT /api/properties/{id} - a full replace of the
    editable fields, same convention as LandlordUpdate."""


class PropertyStatusUpdate(BaseModel):
    """Request body for PATCH /api/properties/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    PropertyStatus: PropertyStatusValue


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    PropertyId: int
    LandlordId: int
    PropertyReference: str
    AddressLine1: str
    AddressLine2: str | None
    City: str
    Postcode: str
    Country: str
    PropertyType: str
    Bedrooms: int
    Bathrooms: int
    MonthlyRent: Decimal
    DepositAmount: Decimal
    PropertyStatus: str
    DateAcquired: date | None
    Notes: str | None
    IsActive: bool
    CreatedAt: datetime
    UpdatedAt: datetime


class PropertyListItem(BaseModel):
    """Lighter-weight representation used in GET /api/properties list results."""

    model_config = ConfigDict(from_attributes=True)

    PropertyId: int
    LandlordId: int
    PropertyReference: str
    AddressLine1: str
    City: str
    Postcode: str
    PropertyType: str
    Bedrooms: int
    MonthlyRent: Decimal
    PropertyStatus: str
    IsActive: bool


PropertyListResponse = PaginatedResponse[PropertyListItem]
