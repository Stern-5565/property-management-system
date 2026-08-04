"""SQLAlchemy model for the Employees table."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Unicode, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.maintenance_request import MaintenanceRequest
    from app.models.rent_payment import RentPayment
    from app.models.user import User


class Employee(Base):
    __tablename__ = "Employees"

    EmployeeId: Mapped[int] = mapped_column(primary_key=True)
    FirstName: Mapped[str] = mapped_column(Unicode(50))
    LastName: Mapped[str] = mapped_column(Unicode(50))
    Email: Mapped[str] = mapped_column(Unicode(256))
    Phone: Mapped[str | None] = mapped_column(Unicode(30))
    JobTitle: Mapped[str | None] = mapped_column(Unicode(100))
    Department: Mapped[str | None] = mapped_column(Unicode(100))
    HireDate: Mapped[date] = mapped_column()
    IsActive: Mapped[bool] = mapped_column(Boolean)
    # See landlord.py for why server_default (not a Python-side default) is
    # required here for the database's SYSUTCDATETIME() default to apply.
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # One employee can be recorded as having created many rent payments,
    # and assigned many maintenance requests.
    RentPaymentsCreated: Mapped[list["RentPayment"]] = relationship(back_populates="CreatedByEmployee")
    AssignedMaintenanceRequests: Mapped[list["MaintenanceRequest"]] = relationship(back_populates="AssignedEmployee")

    # One-to-one: an employee may have one user account (enforced by the
    # UNIQUE constraint on Users.EmployeeId).
    User: Mapped["User | None"] = relationship(back_populates="Employee")

    def __repr__(self) -> str:
        return f"<Employee {self.EmployeeId}: {self.FirstName} {self.LastName}>"
