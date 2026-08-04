"""SQLAlchemy model for the Roles table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user_role import UserRoles

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    __tablename__ = "Roles"

    RoleId: Mapped[int] = mapped_column(primary_key=True)
    RoleName: Mapped[str] = mapped_column(Unicode(50))
    Description: Mapped[str | None] = mapped_column(Unicode(200))

    # Many-to-many: a role can be held by many users, and a user can hold
    # more than one role (see documentation/database-design.md, section 4).
    Users: Mapped[list["User"]] = relationship(secondary=UserRoles, back_populates="Roles")

    def __repr__(self) -> str:
        return f"<Role {self.RoleId}: {self.RoleName}>"
