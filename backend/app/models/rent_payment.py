"""SQLAlchemy model for the RentPayments table."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Unicode, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenancy import Tenancy


class RentPayment(Base):
    __tablename__ = "RentPayments"

    RentPaymentId: Mapped[int] = mapped_column(primary_key=True)
    TenancyId: Mapped[int] = mapped_column(ForeignKey("Tenancies.TenancyId"))
    PaymentReference: Mapped[str] = mapped_column(Unicode(30))
    DueDate: Mapped[date] = mapped_column()
    AmountDue: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    AmountPaid: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    PaymentDate: Mapped[date | None] = mapped_column()
    PaymentMethod: Mapped[str | None] = mapped_column(Unicode(20))
    # PaymentStatus is a plain, application-maintained column (not a SQL
    # computed column) - the service layer recalculates it whenever a
    # payment is recorded, or a due date passes. See database-design.md,
    # Report 2's note on why reports also recompute "overdue" live rather
    # than trusting this column alone.
    PaymentStatus: Mapped[str] = mapped_column(Unicode(20))
    ExternalReference: Mapped[str | None] = mapped_column(Unicode(100))
    Notes: Mapped[str | None] = mapped_column(Unicode(1000))
    CreatedByEmployeeId: Mapped[int | None] = mapped_column(ForeignKey("Employees.EmployeeId"))
    # See landlord.py for why server_default (not a Python-side default) is
    # required here for the database's SYSUTCDATETIME() default to apply.
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # Many-to-one: every payment belongs to exactly one tenancy, and was
    # (optionally) created by one employee.
    Tenancy: Mapped["Tenancy"] = relationship(back_populates="RentPayments")
    CreatedByEmployee: Mapped["Employee | None"] = relationship(back_populates="RentPaymentsCreated")

    def __repr__(self) -> str:
        return f"<RentPayment {self.RentPaymentId}: {self.PaymentReference}>"
