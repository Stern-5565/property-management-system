-- ============================================================
-- 03-create-constraints.sql
-- Adds foreign keys, uniqueness rules and CHECK constraints to the
-- tables created in 02-create-tables.sql.
--
-- Run this after 02-create-tables.sql, connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO

-- Required for filtered indexes / unique constraints later in this
-- script. Set explicitly rather than relying on client defaults,
-- since some connections (including plain sqlcmd) default this OFF.
SET QUOTED_IDENTIFIER ON;
GO
SET ANSI_NULLS ON;
GO

-- ============================================================
-- Foreign keys
-- All foreign keys use NO ACTION on delete/update (the SQL Server
-- default): this system uses soft delete (IsActive flags / status
-- changes), never cascading hard deletes, so ON DELETE CASCADE is
-- intentionally not used anywhere.
-- ============================================================

ALTER TABLE Users
    ADD CONSTRAINT FK_Users_Employees FOREIGN KEY (EmployeeId) REFERENCES Employees (EmployeeId);
GO

ALTER TABLE UserRoles
    ADD CONSTRAINT FK_UserRoles_Users FOREIGN KEY (UserId) REFERENCES Users (UserId);
GO
ALTER TABLE UserRoles
    ADD CONSTRAINT FK_UserRoles_Roles FOREIGN KEY (RoleId) REFERENCES Roles (RoleId);
GO

ALTER TABLE Properties
    ADD CONSTRAINT FK_Properties_Landlords FOREIGN KEY (LandlordId) REFERENCES Landlords (LandlordId);
GO

ALTER TABLE Tenancies
    ADD CONSTRAINT FK_Tenancies_Properties FOREIGN KEY (PropertyId) REFERENCES Properties (PropertyId);
GO
ALTER TABLE Tenancies
    ADD CONSTRAINT FK_Tenancies_Tenants FOREIGN KEY (TenantId) REFERENCES Tenants (TenantId);
GO

ALTER TABLE RentPayments
    ADD CONSTRAINT FK_RentPayments_Tenancies FOREIGN KEY (TenancyId) REFERENCES Tenancies (TenancyId);
GO
ALTER TABLE RentPayments
    ADD CONSTRAINT FK_RentPayments_Employees FOREIGN KEY (CreatedByEmployeeId) REFERENCES Employees (EmployeeId);
GO

ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT FK_MaintenanceRequests_Properties FOREIGN KEY (PropertyId) REFERENCES Properties (PropertyId);
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT FK_MaintenanceRequests_Tenancies FOREIGN KEY (TenancyId) REFERENCES Tenancies (TenancyId);
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT FK_MaintenanceRequests_Tenants FOREIGN KEY (TenantId) REFERENCES Tenants (TenantId);
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT FK_MaintenanceRequests_Employees FOREIGN KEY (AssignedEmployeeId) REFERENCES Employees (EmployeeId);
GO

ALTER TABLE MaintenanceNotes
    ADD CONSTRAINT FK_MaintenanceNotes_MaintenanceRequests FOREIGN KEY (MaintenanceRequestId) REFERENCES MaintenanceRequests (MaintenanceRequestId);
GO
ALTER TABLE MaintenanceNotes
    ADD CONSTRAINT FK_MaintenanceNotes_Employees FOREIGN KEY (EmployeeId) REFERENCES Employees (EmployeeId);
GO

ALTER TABLE AuditLogs
    ADD CONSTRAINT FK_AuditLogs_Users FOREIGN KEY (UserId) REFERENCES Users (UserId);
GO

-- ============================================================
-- Unique constraints (columns that are always required to be unique)
-- ============================================================

ALTER TABLE Roles
    ADD CONSTRAINT UQ_Roles_RoleName UNIQUE (RoleName);
GO

ALTER TABLE Employees
    ADD CONSTRAINT UQ_Employees_Email UNIQUE (Email);
GO

ALTER TABLE Users
    ADD CONSTRAINT UQ_Users_EmployeeId UNIQUE (EmployeeId);   -- one user account per employee
GO
ALTER TABLE Users
    ADD CONSTRAINT UQ_Users_Username UNIQUE (Username);
GO
ALTER TABLE Users
    ADD CONSTRAINT UQ_Users_Email UNIQUE (Email);
GO

ALTER TABLE Properties
    ADD CONSTRAINT UQ_Properties_PropertyReference UNIQUE (PropertyReference);
GO

ALTER TABLE RentPayments
    ADD CONSTRAINT UQ_RentPayments_PaymentReference UNIQUE (PaymentReference);
GO

ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT UQ_MaintenanceRequests_RequestReference UNIQUE (RequestReference);
GO

-- ============================================================
-- Filtered unique indexes
-- These columns are OPTIONAL but must be unique WHEN PROVIDED. A
-- plain UNIQUE constraint only allows one NULL in SQL Server, so a
-- second row with a blank value would fail to insert. A filtered
-- index (WHERE ... IS NOT NULL) excludes NULL rows from the
-- uniqueness check entirely, so any number of NULLs is fine.
-- ============================================================

CREATE UNIQUE INDEX UX_Landlords_Email ON Landlords (Email) WHERE Email IS NOT NULL;
GO

CREATE UNIQUE INDEX UX_Tenants_Email ON Tenants (Email) WHERE Email IS NOT NULL;
GO

CREATE UNIQUE INDEX UX_Tenancies_AgreementReference ON Tenancies (AgreementReference) WHERE AgreementReference IS NOT NULL;
GO

-- ============================================================
-- CHECK constraints
-- Reminder: CHECK constraints cannot call non-deterministic functions
-- (GETDATE(), SYSUTCDATETIME(), etc). Rules that depend on "today's
-- date" (e.g. "date of birth cannot be in the future") are enforced
-- in the application layer instead - see documentation/database-design.md.
-- ============================================================

-- Landlords
ALTER TABLE Landlords
    ADD CONSTRAINT CK_Landlords_NameOrCompany
    CHECK (CompanyName IS NOT NULL OR (FirstName IS NOT NULL AND LastName IS NOT NULL));
GO
ALTER TABLE Landlords
    ADD CONSTRAINT CK_Landlords_ContactMethod
    CHECK (PreferredContactMethod IS NULL OR PreferredContactMethod IN (N'Email', N'Phone', N'Post'));
GO

-- Properties
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_PropertyType
    CHECK (PropertyType IN (N'House', N'Flat', N'Bungalow', N'Studio', N'Maisonette', N'Other'));
GO
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_PropertyStatus
    CHECK (PropertyStatus IN (N'Vacant', N'Occupied', N'Under Maintenance', N'Unavailable', N'Archived'));
GO
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_Bedrooms CHECK (Bedrooms >= 0);
GO
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_Bathrooms CHECK (Bathrooms >= 0);
GO
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_MonthlyRent CHECK (MonthlyRent >= 0);
GO
ALTER TABLE Properties
    ADD CONSTRAINT CK_Properties_DepositAmount CHECK (DepositAmount >= 0);
GO

-- Tenants
ALTER TABLE Tenants
    ADD CONSTRAINT CK_Tenants_EmploymentStatus
    CHECK (EmploymentStatus IS NULL OR EmploymentStatus IN (N'Employed', N'Self-Employed', N'Unemployed', N'Student', N'Retired', N'Other'));
GO

-- Tenancies
ALTER TABLE Tenancies
    ADD CONSTRAINT CK_Tenancies_DateOrder CHECK (EndDate IS NULL OR EndDate > StartDate);
GO
ALTER TABLE Tenancies
    ADD CONSTRAINT CK_Tenancies_MonthlyRent CHECK (MonthlyRent > 0);
GO
ALTER TABLE Tenancies
    ADD CONSTRAINT CK_Tenancies_DepositAmount CHECK (DepositAmount >= 0);
GO
ALTER TABLE Tenancies
    ADD CONSTRAINT CK_Tenancies_PaymentDueDay CHECK (PaymentDueDay BETWEEN 1 AND 28);
GO
ALTER TABLE Tenancies
    ADD CONSTRAINT CK_Tenancies_TenancyStatus
    CHECK (TenancyStatus IN (N'Draft', N'Upcoming', N'Active', N'Ending Soon', N'Ended', N'Cancelled'));
GO

-- RentPayments
ALTER TABLE RentPayments
    ADD CONSTRAINT CK_RentPayments_AmountDue CHECK (AmountDue >= 0);
GO
ALTER TABLE RentPayments
    ADD CONSTRAINT CK_RentPayments_AmountPaid CHECK (AmountPaid >= 0);
GO
ALTER TABLE RentPayments
    ADD CONSTRAINT CK_RentPayments_PaymentMethod
    CHECK (PaymentMethod IS NULL OR PaymentMethod IN (N'Bank Transfer', N'Card', N'Cash', N'Direct Debit', N'Standing Order', N'Other'));
GO
ALTER TABLE RentPayments
    ADD CONSTRAINT CK_RentPayments_PaymentStatus
    CHECK (PaymentStatus IN (N'Pending', N'Partially Paid', N'Paid', N'Overdue', N'Cancelled'));
GO

-- MaintenanceRequests
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_Category
    CHECK (Category IN (N'Plumbing', N'Electrical', N'Heating', N'Appliance', N'Structural', N'Security', N'Cleaning', N'General', N'Other'));
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_Priority
    CHECK (Priority IN (N'Low', N'Medium', N'High', N'Emergency'));
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_MaintenanceStatus
    CHECK (MaintenanceStatus IN (N'Reported', N'Assigned', N'In Progress', N'Waiting for Parts', N'Waiting for Approval', N'Completed', N'Cancelled'));
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_EstimatedCost CHECK (EstimatedCost IS NULL OR EstimatedCost >= 0);
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_ActualCost CHECK (ActualCost IS NULL OR ActualCost >= 0);
GO
ALTER TABLE MaintenanceRequests
    ADD CONSTRAINT CK_MaintenanceRequests_CompletionRequiresDetail
    CHECK (MaintenanceStatus <> N'Completed' OR (CompletedDate IS NOT NULL AND ResolutionNotes IS NOT NULL));
GO
