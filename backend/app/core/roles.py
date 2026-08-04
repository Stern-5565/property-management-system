"""Role name constants and permission groups.

Centralizing these avoids magic strings scattered across every route file,
and gives permission decisions like "who can manage landlords" one place to
look them up and change them, per documentation/project-scope.md, section 4.
"""

ADMINISTRATOR = "Administrator"
PROPERTY_MANAGER = "PropertyManager"
MAINTENANCE_EMPLOYEE = "MaintenanceEmployee"
READ_ONLY = "ReadOnly"

# Landlords: Administrator and PropertyManager can fully manage them;
# ReadOnly can view but not create/edit/delete. MaintenanceEmployee's
# documented capabilities are a narrow whitelist (their own assigned
# maintenance requests only) that doesn't include landlord data at all.
CAN_VIEW_LANDLORDS = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_LANDLORDS = (ADMINISTRATOR, PROPERTY_MANAGER)

# Properties: same permission shape as Landlords, for the same reasons.
CAN_VIEW_PROPERTIES = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_PROPERTIES = (ADMINISTRATOR, PROPERTY_MANAGER)

# Tenants: same permission shape again.
CAN_VIEW_TENANTS = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_TENANTS = (ADMINISTRATOR, PROPERTY_MANAGER)

# Tenancies: same permission shape again.
CAN_VIEW_TENANCIES = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_TENANCIES = (ADMINISTRATOR, PROPERTY_MANAGER)
