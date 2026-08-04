"""SQLAlchemy model for the Tenants table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Unicode
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.tenancy import Tenancy


class Tenant(Base):
    __tablename__ = "Tenants"

    TenantId: Mapped[int] = mapped_column(primary_key=True)
    FirstName: Mapped[str] = mapped_column(Unicode(50))
    LastName: Mapped[str] = mapped_column(Unicode(50))
    Email: Mapped[str | None] = mapped_column(Unicode(256))
    Phone: Mapped[str | None] = mapped_column(Unicode(30))
    # "Date of birth cannot be in the future" is enforced in the Pydantic
    # schema, not here - SQL Server CHECK constraints can't call
    # non-deterministic functions like GETDATE(), so the database itself
    # can't enforce it either. See database-design.md, section 0.
    DateOfBirth: Mapped[date | None] = mapped_column()
    PreviousAddress: Mapped[str | None] = mapped_column(Unicode(250))
    EmergencyContactName: Mapped[str | None] = mapped_column(Unicode(100))
    EmergencyContactPhone: Mapped[str | None] = mapped_column(Unicode(30))
    IdentificationReference: Mapped[str | None] = mapped_column(Unicode(50))
    EmploymentStatus: Mapped[str | None] = mapped_column(Unicode(30))
    Notes: Mapped[str | None] = mapped_column(Unicode(1000))
    IsActive: Mapped[bool] = mapped_column(Boolean)
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2)
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2)

    # One tenant has many tenancies over time. No delete cascade - a tenant
    # with an active tenancy must not be deletable at all.
    Tenancies: Mapped[list["Tenancy"]] = relationship(back_populates="Tenant")

    def __repr__(self) -> str:
        return f"<Tenant {self.TenantId}: {self.FirstName} {self.LastName}>"
