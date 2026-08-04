"""SQLAlchemy model for the MaintenanceNotes table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Unicode, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.maintenance_request import MaintenanceRequest


class MaintenanceNote(Base):
    __tablename__ = "MaintenanceNotes"

    MaintenanceNoteId: Mapped[int] = mapped_column(primary_key=True)
    MaintenanceRequestId: Mapped[int] = mapped_column(ForeignKey("MaintenanceRequests.MaintenanceRequestId"))
    EmployeeId: Mapped[int] = mapped_column(ForeignKey("Employees.EmployeeId"))
    NoteText: Mapped[str] = mapped_column(Unicode(2000))
    # See landlord.py for why server_default (not a Python-side default) is
    # required here for the database's SYSUTCDATETIME() default to apply.
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2, server_default=text("SYSUTCDATETIME()"))

    # Many-to-one: every note belongs to exactly one request, written by
    # one employee.
    MaintenanceRequest: Mapped["MaintenanceRequest"] = relationship(back_populates="MaintenanceNotes")
    Employee: Mapped["Employee"] = relationship()

    def __repr__(self) -> str:
        return f"<MaintenanceNote {self.MaintenanceNoteId} on request {self.MaintenanceRequestId}>"
