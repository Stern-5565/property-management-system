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

# Rent payments: same permission shape again.
CAN_VIEW_RENT_PAYMENTS = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_RENT_PAYMENTS = (ADMINISTRATOR, PROPERTY_MANAGER)

# Maintenance requests: the one module MaintenanceEmployee actually has a
# documented role in (scope doc section 4), so its shape differs from
# every other module above.
#
# - CAN_VIEW_MAINTENANCE: full visibility across every request - anyone
#   who can see the whole list/workload/history, not just their own work.
# - CAN_MANAGE_MAINTENANCE: create/edit a request, assign an employee,
#   change priority, cancel - all "who works on what and why" decisions,
#   which the scope doc reserves for Administrator/PropertyManager.
# - CAN_UPDATE_MAINTENANCE_WORK: change status, add notes, enter costs,
#   complete - the hands-on-the-job actions. MaintenanceEmployee is
#   included here, but MaintenanceService additionally restricts them to
#   only the requests currently assigned to them (see
#   MaintenanceService._assert_can_update_work) - this tuple alone is not
#   the full permission check for that role.
CAN_VIEW_MAINTENANCE = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
CAN_MANAGE_MAINTENANCE = (ADMINISTRATOR, PROPERTY_MANAGER)
CAN_UPDATE_MAINTENANCE_WORK = (ADMINISTRATOR, PROPERTY_MANAGER, MAINTENANCE_EMPLOYEE)
# List/get only: MaintenanceEmployee passes this route-level check but
# MaintenanceService then narrows what they actually see to their own
# assigned requests - see MaintenanceService._is_restricted_to_own_work.
CAN_ACCESS_MAINTENANCE = CAN_VIEW_MAINTENANCE + (MAINTENANCE_EMPLOYEE,)

# Employees: "Manage employees" is listed under Administrator only
# (scope doc section 4) - unlike every module above, PropertyManager does
# NOT get a matching CAN_MANAGE tuple here. They can still VIEW employees
# (they need to know who's available when assigning maintenance work via
# CAN_MANAGE_MAINTENANCE), but employee administration itself - creating,
# editing, deactivating - stays Administrator-only. ReadOnly and
# MaintenanceEmployee get neither: employee records are exactly the
# "employee administration" the scope doc explicitly excludes
# MaintenanceEmployee from, and ReadOnly's documented scope ("view
# records", "view permitted reports") is never said to extend to staff data.
CAN_VIEW_EMPLOYEES = (ADMINISTRATOR, PROPERTY_MANAGER)
CAN_MANAGE_EMPLOYEES = (ADMINISTRATOR,)

# Dashboard: read-only aggregates, same view shape as Maintenance -
# Administrator/PropertyManager/ReadOnly ("View the full dashboard" /
# "View reports" / "View permitted reports" - scope doc section 4).
# MaintenanceEmployee is excluded: the dashboard surfaces financial
# figures (rent collected, outstanding rent) alongside operational ones,
# and MaintenanceEmployee is explicitly barred from "financial reports".
CAN_VIEW_DASHBOARD = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)

# Reports: same Administrator/PropertyManager/ReadOnly shape as
# Dashboard, applied uniformly to all 10 MVP reports rather than
# splitting "financial" from "operational" ones. The scope doc's wording
# is genuinely ambiguous here - Administrator "view[s] all reports" and
# "export[s] data" while PropertyManager only "view[s] reports" and
# "export[s] operational data" - but PropertyManager already has full
# read/write access to RentPayments (CAN_MANAGE_RENT_PAYMENTS) and every
# other financial record in the system, so reading a financial *report*
# they can already see the underlying rows for would be an inconsistent,
# not-actually-safer restriction. Reading "operational data" as a
# stricter subset isn't supported by anything else in the role model, so
# every report shares this one gate; export uses the same tuple as view
# (a CSV of a report is the same data, not a separate access level -
# matches RentPayments' own CSV export, which needed no permission beyond
# CAN_VIEW_RENT_PAYMENTS). MaintenanceEmployee is excluded, same
# "financial reports" reasoning as CAN_VIEW_DASHBOARD - several of the 10
# reports carry rent/cost figures and there's no clean way to split
# MaintenanceEmployee into "sees only the non-financial reports" without
# inventing a second reports-specific role split the scope doc never
# describes.
CAN_VIEW_REPORTS = (ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY)
