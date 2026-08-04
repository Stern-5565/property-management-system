"""Association table for the many-to-many UserRoles relationship.

UserRoles has no columns of its own beyond the two foreign keys that form
its composite primary key, so it is modeled as a plain sqlalchemy.Table
(the standard "association table" pattern) rather than a mapped class -
User.Roles / Role.Users use it as their `secondary` table.
"""

from sqlalchemy import Column, ForeignKey, Table

from app.database.session import Base

UserRoles = Table(
    "UserRoles",
    Base.metadata,
    Column("UserId", ForeignKey("Users.UserId"), primary_key=True),
    Column("RoleId", ForeignKey("Roles.RoleId"), primary_key=True),
)
