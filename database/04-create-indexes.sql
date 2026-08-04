-- ============================================================
-- 04-create-indexes.sql
-- Non-unique indexes to support common lookups, filters and joins.
--
-- SQL Server does NOT automatically index foreign key columns (only
-- the primary key side of a relationship gets an index for free), so
-- we add them explicitly here for every FK that will be searched or
-- joined on regularly.
--
-- Run this after 03-create-constraints.sql, connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO

SET QUOTED_IDENTIFIER ON;
GO
SET ANSI_NULLS ON;
GO

-- Employees / Users
CREATE INDEX IX_Employees_IsActive ON Employees (IsActive);
GO
CREATE INDEX IX_Users_IsActive ON Users (IsActive);
GO

-- Landlords
CREATE INDEX IX_Landlords_IsActive ON Landlords (IsActive);
GO
CREATE INDEX IX_Landlords_LastName ON Landlords (LastName);
GO

-- Properties
CREATE INDEX IX_Properties_LandlordId ON Properties (LandlordId);
GO
CREATE INDEX IX_Properties_PropertyStatus ON Properties (PropertyStatus);
GO
CREATE INDEX IX_Properties_City ON Properties (City);
GO

-- Tenants
CREATE INDEX IX_Tenants_IsActive ON Tenants (IsActive);
GO
CREATE INDEX IX_Tenants_LastName ON Tenants (LastName);
GO

-- Tenancies
CREATE INDEX IX_Tenancies_PropertyId ON Tenancies (PropertyId);
GO
CREATE INDEX IX_Tenancies_TenantId ON Tenancies (TenantId);
GO
CREATE INDEX IX_Tenancies_TenancyStatus ON Tenancies (TenancyStatus);
GO
-- Supports the overlapping-tenancy check the service layer runs
-- before creating/activating a tenancy for a property (see
-- documentation/database-design.md, section 8).
CREATE INDEX IX_Tenancies_Property_Dates ON Tenancies (PropertyId, StartDate, EndDate);
GO

-- RentPayments
CREATE INDEX IX_RentPayments_TenancyId ON RentPayments (TenancyId);
GO
CREATE INDEX IX_RentPayments_PaymentStatus ON RentPayments (PaymentStatus);
GO
CREATE INDEX IX_RentPayments_DueDate ON RentPayments (DueDate);
GO
CREATE INDEX IX_RentPayments_Tenancy_Due ON RentPayments (TenancyId, DueDate);
GO

-- MaintenanceRequests
CREATE INDEX IX_MaintenanceRequests_PropertyId ON MaintenanceRequests (PropertyId);
GO
CREATE INDEX IX_MaintenanceRequests_AssignedEmployeeId ON MaintenanceRequests (AssignedEmployeeId);
GO
CREATE INDEX IX_MaintenanceRequests_MaintenanceStatus ON MaintenanceRequests (MaintenanceStatus);
GO
CREATE INDEX IX_MaintenanceRequests_Priority ON MaintenanceRequests (Priority);
GO

-- MaintenanceNotes
CREATE INDEX IX_MaintenanceNotes_MaintenanceRequestId ON MaintenanceNotes (MaintenanceRequestId);
GO

-- AuditLogs
CREATE INDEX IX_AuditLogs_EntityName_EntityId ON AuditLogs (EntityName, EntityId);
GO
CREATE INDEX IX_AuditLogs_CreatedAt ON AuditLogs (CreatedAt);
GO
CREATE INDEX IX_AuditLogs_UserId ON AuditLogs (UserId);
GO
