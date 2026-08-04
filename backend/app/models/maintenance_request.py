"""SQLAlchemy model for the MaintenanceRequests table."""

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
    from app.models.maintenance_note import MaintenanceNote
    from app.models.property import Property
    from app.models.tenancy import Tenancy
    from app.models.tenant import Tenant


class MaintenanceRequest(Base):
    __tablename__ = "MaintenanceRequests"

    MaintenanceRequestId: Mapped[int] = mapped_column(primary_key=True)
    PropertyId: Mapped[int] = mapped_column(ForeignKey("Properties.PropertyId"))
    TenancyId: Mapped[int | None] = mapped_column(ForeignKey("Tenancies.TenancyId"))
    TenantId: Mapped[int | None] = mapped_column(ForeignKey("Tenants.TenantId"))
    AssignedEmployeeId: Mapped[int | None] = mapped_column(ForeignKey("Employees.EmployeeId"))
    RequestReference: Mapped[str] = mapped_column(Unicode(30))
    Title: Mapped[str] = mapped_column(Unicode(150))
    Description: Mapped[str | None] = mapped_column(Unicode(2000))
    Category: Mapped[str] = mapped_column(Unicode(30))
    Priority: Mapped[str] = mapped_column(Unicode(20))
    MaintenanceStatus: Mapped[str] = mapped_column(Unicode(30))
    ReportedDate: Mapped[date] = mapped_column(server_default=text("CAST(SYSUTCDATETIME() AS DATE)"))
    ScheduledDate: Mapped[date | None] = mapped_column()
    CompletedDate: Mapped[date | None] = mapped_column()
    EstimatedCost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ActualCost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ResolutionNotes: Mapped[str | None] = mapped_column(Unicode(2000))
    # See landlord.py for why server_default (not a Python-side default) is
    # required here for the database's SYSUTCDATETIME() default to apply.
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # Many-to-one: every request belongs to exactly one property, and is
    # optionally linked to the tenancy/tenant who reported it and the
    # employee currently assigned to it.
    Property: Mapped["Property"] = relationship(back_populates="MaintenanceRequests")
    Tenancy: Mapped["Tenancy | None"] = relationship()
    Tenant: Mapped["Tenant | None"] = relationship()
    AssignedEmployee: Mapped["Employee | None"] = relationship(back_populates="AssignedMaintenanceRequests")

    # One-to-many: a request can have many notes logged against it.
    MaintenanceNotes: Mapped[list["MaintenanceNote"]] = relationship(back_populates="MaintenanceRequest")

    def __repr__(self) -> str:
        return f"<MaintenanceRequest {self.MaintenanceRequestId}: {self.RequestReference}>"
