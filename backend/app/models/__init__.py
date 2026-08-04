"""Import every model here so SQLAlchemy's mapper registry always sees the
full set of mapped classes before any relationship (which reference each
other by string, e.g. relationship(back_populates="Properties")) needs to
be resolved. app/main.py imports this package on startup for that reason.
"""

from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.landlord import Landlord
from app.models.maintenance_note import MaintenanceNote
from app.models.maintenance_request import MaintenanceRequest
from app.models.property import Property
from app.models.rent_payment import RentPayment
from app.models.role import Role
from app.models.tenancy import Tenancy
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRoles

__all__ = [
    "AuditLog",
    "Employee",
    "Landlord",
    "MaintenanceNote",
    "MaintenanceRequest",
    "Property",
    "RentPayment",
    "Role",
    "Tenancy",
    "Tenant",
    "User",
    "UserRoles",
]
