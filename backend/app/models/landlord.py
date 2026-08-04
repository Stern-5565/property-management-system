"""SQLAlchemy model for the Landlords table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Unicode, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.property import Property


class Landlord(Base):
    __tablename__ = "Landlords"

    LandlordId: Mapped[int] = mapped_column(primary_key=True)
    FirstName: Mapped[str | None] = mapped_column(Unicode(50))
    LastName: Mapped[str | None] = mapped_column(Unicode(50))
    CompanyName: Mapped[str | None] = mapped_column(Unicode(150))
    Email: Mapped[str | None] = mapped_column(Unicode(256))
    Phone: Mapped[str | None] = mapped_column(Unicode(30))
    AddressLine1: Mapped[str] = mapped_column(Unicode(150))
    AddressLine2: Mapped[str | None] = mapped_column(Unicode(150))
    City: Mapped[str] = mapped_column(Unicode(100))
    Postcode: Mapped[str] = mapped_column(Unicode(20))
    Country: Mapped[str] = mapped_column(Unicode(100))
    PreferredContactMethod: Mapped[str | None] = mapped_column(Unicode(20))
    IsActive: Mapped[bool] = mapped_column(Boolean)
    # CreatedAt/UpdatedAt have no Python-side default. server_default tells
    # SQLAlchemy the column already has a SYSUTCDATETIME() default in the
    # database (see database/02-create-tables.sql) - without it, SQLAlchemy
    # has no way to know it's safe to leave the column out of the INSERT
    # when unset, and will send an explicit NULL instead (which the
    # database then rejects, since the column is NOT NULL). With it,
    # leaving the attribute unset on a new instance correctly omits the
    # column so the database default fires, rather than the ORM racing the
    # database to decide "now".
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # One landlord has many properties. No delete cascade: a landlord with
    # active properties must not be deletable at all (enforced in the
    # service layer) - cascading the delete here would silently defeat
    # that business rule at the ORM level.
    Properties: Mapped[list["Property"]] = relationship(back_populates="Landlord")

    def __repr__(self) -> str:
        return f"<Landlord {self.LandlordId}: {self.CompanyName or f'{self.FirstName} {self.LastName}'}>"
