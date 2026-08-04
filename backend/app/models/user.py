"""SQLAlchemy model for the Users table (authentication identities)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Unicode
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user_role import UserRoles

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role import Role


class User(Base):
    __tablename__ = "Users"

    UserId: Mapped[int] = mapped_column(primary_key=True)
    EmployeeId: Mapped[int] = mapped_column(ForeignKey("Employees.EmployeeId"))
    Username: Mapped[str] = mapped_column(Unicode(50))
    Email: Mapped[str] = mapped_column(Unicode(256))
    # Never a plain-text password - always a hash produced by the auth
    # module (added in a later milestone). This column stores the hash
    # only; nothing in this codebase should ever log or print it.
    PasswordHash: Mapped[str] = mapped_column(Unicode(255))
    IsActive: Mapped[bool] = mapped_column(Boolean)
    LastLoginAt: Mapped[datetime | None] = mapped_column(DATETIME2)
    FailedLoginAttempts: Mapped[int] = mapped_column(Integer)
    CreatedAt: Mapped[datetime] = mapped_column(DATETIME2)
    UpdatedAt: Mapped[datetime] = mapped_column(DATETIME2)

    # One-to-one: exactly one user account per employee (enforced by the
    # UNIQUE constraint on Users.EmployeeId).
    Employee: Mapped["Employee"] = relationship(back_populates="User")

    # Many-to-many: see Role.Users for the other side.
    Roles: Mapped[list["Role"]] = relationship(secondary=UserRoles, back_populates="Users")

    def __repr__(self) -> str:
        return f"<User {self.UserId}: {self.Username}>"
