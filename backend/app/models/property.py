"""SQLAlchemy model for the Properties table."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, Unicode
from sqlalchemy.dialects.mssql import DATETIME2, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.landlord import Landlord
    from app.models.maintenance_request import MaintenanceRequest
    from app.models.tenancy import Tenancy


class Property(Base):
    __tablename__ = "Properties"

    PropertyId: Mapped[int] = mapped_column(primary_key=True)
    LandlordId: Mapped[int] = mapped_column(ForeignKey("Landlords.LandlordId"))
    PropertyReference: Mapped[str] = mapped_column(Unicode(30))
    AddressLine1: Mapped[str] = mapped_column(Unicode(150))
    AddressLine2: Mapped[str | None] = mapped_column(Unicode(150))
    City: Mapped[str] = mapped_column(Unicode(100))
    Postcode: Mapped[str] = mapped_column(Unicode(20))
    Country: Mapped[str] = mapped_column(Unicode(100))
    PropertyType: Mapped[str] = mapped_column(Unicode(30))
    Bedrooms: Mapped[int] = mapped_column(TINYINT)
    Bathrooms: Mapped[int] = mapped_column(TINYINT)
    MonthlyRent: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    DepositAmount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    PropertyStatus: Mapped[str] = mapped_column(Unicode(20))
    DateAcquired: Mapped[date | None] = mapped_column()
    Notes: Mapped[str | None] = mapped_column(Unicode(1000))
    IsActive: Mapped[bool] = mapped_column(Boolean)
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2)
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2)

    # Many-to-one: every property belongs to exactly one landlord.
    Landlord: Mapped["Landlord"] = relationship(back_populates="Properties")

    # One-to-many: a property has many tenancies over time. No delete
    # cascade - ending/replacing a tenancy is a status change, not a
    # deletion, and old tenancy rows are kept as history.
    Tenancies: Mapped[list["Tenancy"]] = relationship(back_populates="Property")

    # One-to-many: a property has many maintenance requests over time.
    MaintenanceRequests: Mapped[list["MaintenanceRequest"]] = relationship(back_populates="Property")

    def __repr__(self) -> str:
        return f"<Property {self.PropertyId}: {self.PropertyReference}>"
