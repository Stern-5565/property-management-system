"""SQLAlchemy model for the Tenancies table."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Unicode, text
from sqlalchemy.dialects.mssql import DATETIME2, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.rent_payment import RentPayment
    from app.models.tenant import Tenant
    # MaintenanceRequests relationship is added once that model exists -
    # see Batch 4.


class Tenancy(Base):
    __tablename__ = "Tenancies"

    TenancyId: Mapped[int] = mapped_column(primary_key=True)
    PropertyId: Mapped[int] = mapped_column(ForeignKey("Properties.PropertyId"))
    TenantId: Mapped[int] = mapped_column(ForeignKey("Tenants.TenantId"))
    StartDate: Mapped[date] = mapped_column()
    EndDate: Mapped[date | None] = mapped_column()
    MonthlyRent: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    DepositAmount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    PaymentDueDay: Mapped[int] = mapped_column(TINYINT)
    TenancyStatus: Mapped[str] = mapped_column(Unicode(20))
    CheckInDate: Mapped[date | None] = mapped_column()
    CheckOutDate: Mapped[date | None] = mapped_column()
    AgreementReference: Mapped[str | None] = mapped_column(Unicode(30))
    Notes: Mapped[str | None] = mapped_column(Unicode(1000))
    # See landlord.py for why server_default (not a Python-side default) is
    # required here for the database's SYSUTCDATETIME() default to apply.
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # Many-to-one: every tenancy belongs to exactly one property and one
    # (main) tenant.
    Property: Mapped["Property"] = relationship(back_populates="Tenancies")
    Tenant: Mapped["Tenant"] = relationship(back_populates="Tenancies")

    # One-to-many: a tenancy has many rent payment records over its life.
    RentPayments: Mapped[list["RentPayment"]] = relationship(back_populates="Tenancy")

    # MaintenanceRequests relationship (one-to-many) is added once that
    # model exists - see Batch 4.

    def __repr__(self) -> str:
        return f"<Tenancy {self.TenancyId}: {self.AgreementReference}>"
