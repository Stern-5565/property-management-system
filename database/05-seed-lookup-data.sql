-- ============================================================
-- 05-seed-lookup-data.sql
-- Seeds fixed lookup data (the four permission roles). This is NOT
-- demo/sample business data - landlords, properties, tenants etc.
-- are seeded separately later (database/06-seed-demo-data.sql).
--
-- Safe to re-run: each insert is guarded so it will not create
-- duplicate rows.
--
-- Run this after 04-create-indexes.sql, connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO

IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName = N'Administrator')
    INSERT INTO Roles (RoleName, Description)
    VALUES (N'Administrator', N'Full access to all records, employees, and system settings.');
GO

IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName = N'PropertyManager')
    INSERT INTO Roles (RoleName, Description)
    VALUES (N'PropertyManager', N'Manages landlords, properties, tenants, tenancies, payments and maintenance. Cannot manage employee accounts.');
GO

IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName = N'MaintenanceEmployee')
    INSERT INTO Roles (RoleName, Description)
    VALUES (N'MaintenanceEmployee', N'Views and updates maintenance requests assigned to them. No access to financial reports or employee administration.');
GO

IF NOT EXISTS (SELECT 1 FROM Roles WHERE RoleName = N'ReadOnly')
    INSERT INTO Roles (RoleName, Description)
    VALUES (N'ReadOnly', N'Can view records, search and filter, and view permitted reports. Cannot create, edit or delete.');
GO

-- Verify
SELECT RoleId, RoleName, Description FROM Roles ORDER BY RoleId;
GO
