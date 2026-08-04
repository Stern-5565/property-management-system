"""SQLAlchemy model for the AuditLogs table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Unicode, UnicodeText
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "AuditLogs"

    # BIGINT, not the usual INT - this table is expected to grow quickly,
    # unlike every other table's identity column in this project.
    AuditLogId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    UserId: Mapped[int | None] = mapped_column(ForeignKey("Users.UserId"))
    Action: Mapped[str] = mapped_column(Unicode(50))
    EntityName: Mapped[str] = mapped_column(Unicode(50))
    EntityId: Mapped[int] = mapped_column()
    OldValues: Mapped[str | None] = mapped_column(UnicodeText)
    NewValues: Mapped[str | None] = mapped_column(UnicodeText)
    IpAddress: Mapped[str | None] = mapped_column(Unicode(45))
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2)

    # Many-to-one, nullable: some audit entries are system-generated with
    # no associated user.
    User: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.AuditLogId}: {self.Action} {self.EntityName}#{self.EntityId}>"
