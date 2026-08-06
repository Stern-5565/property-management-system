/**
 * Mirrors backend/app/core/roles.py - role name constants plus, per
 * module, which roles can view vs. manage it. Built incrementally as each
 * module's frontend gets built (same order as the backend), not all at
 * once, so this file only has what's actually used so far.
 */
export const ADMINISTRATOR = "Administrator";
export const PROPERTY_MANAGER = "PropertyManager";
export const MAINTENANCE_EMPLOYEE = "MaintenanceEmployee";
export const READ_ONLY = "ReadOnly";

// Landlords: Administrator and PropertyManager can fully manage them;
// ReadOnly can view but not create/edit/deactivate. MaintenanceEmployee
// has no access at all - see backend/app/core/roles.py's own comment.
export const CAN_VIEW_LANDLORDS = [ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY];
export const CAN_MANAGE_LANDLORDS = [ADMINISTRATOR, PROPERTY_MANAGER];

// Properties: same shape as Landlords.
export const CAN_VIEW_PROPERTIES = [ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY];
export const CAN_MANAGE_PROPERTIES = [ADMINISTRATOR, PROPERTY_MANAGER];

// Tenants: same shape as Landlords.
export const CAN_VIEW_TENANTS = [ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY];
export const CAN_MANAGE_TENANTS = [ADMINISTRATOR, PROPERTY_MANAGER];

// Employees: narrower than every module above (mirrors
// backend/app/core/roles.py exactly). CAN_MANAGE_EMPLOYEES is
// Administrator-only - PropertyManager can view (needed to pick an
// employee when assigning maintenance work) but not create/edit/
// deactivate. ReadOnly and MaintenanceEmployee get neither - employee
// records are treated as "employee administration".
export const CAN_VIEW_EMPLOYEES = [ADMINISTRATOR, PROPERTY_MANAGER];
export const CAN_MANAGE_EMPLOYEES = [ADMINISTRATOR];

// Tenancies: same shape as Landlords.
export const CAN_VIEW_TENANCIES = [ADMINISTRATOR, PROPERTY_MANAGER, READ_ONLY];
export const CAN_MANAGE_TENANCIES = [ADMINISTRATOR, PROPERTY_MANAGER];
