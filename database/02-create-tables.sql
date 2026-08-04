-- ============================================================
-- 02-create-tables.sql
-- Creates all PropertyManager tables: columns, data types, defaults
-- and primary keys only.
--
-- Foreign keys, CHECK constraints and unique rules are added in
-- 03-create-constraints.sql. Performance indexes are added in
-- 04-create-indexes.sql. Tables are created in dependency order so
-- each one only references tables that already exist.
--
-- Run this after 01-create-database.sql, connected to PropertyManagerDb.
-- ============================================================

USE PropertyManagerDb;
GO

-- ---------- Roles ----------
CREATE TABLE Roles (
    RoleId          INT IDENTITY(1,1) NOT NULL,
    RoleName        NVARCHAR(50)      NOT NULL,
    Description     NVARCHAR(200)     NULL,
    CONSTRAINT PK_Roles PRIMARY KEY (RoleId)
);
GO

-- ---------- Employees ----------
CREATE TABLE Employees (
    EmployeeId      INT IDENTITY(1,1) NOT NULL,
    FirstName       NVARCHAR(50)      NOT NULL,
    LastName        NVARCHAR(50)      NOT NULL,
    Email           NVARCHAR(256)     NOT NULL,
    Phone           NVARCHAR(30)      NULL,
    JobTitle        NVARCHAR(100)     NULL,
    Department      NVARCHAR(100)     NULL,
    HireDate        DATE              NOT NULL,
    IsActive        BIT               NOT NULL CONSTRAINT DF_Employees_IsActive DEFAULT (1),
    CreatedAt       DATETIME2         NOT NULL CONSTRAINT DF_Employees_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt       DATETIME2         NOT NULL CONSTRAINT DF_Employees_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Employees PRIMARY KEY (EmployeeId)
);
GO

-- ---------- Users ----------
CREATE TABLE Users (
    UserId               INT IDENTITY(1,1) NOT NULL,
    EmployeeId           INT               NOT NULL,
    Username             NVARCHAR(50)      NOT NULL,
    Email                NVARCHAR(256)     NOT NULL,
    PasswordHash         NVARCHAR(255)     NOT NULL,
    IsActive             BIT               NOT NULL CONSTRAINT DF_Users_IsActive DEFAULT (1),
    LastLoginAt          DATETIME2         NULL,
    FailedLoginAttempts  INT               NOT NULL CONSTRAINT DF_Users_FailedLoginAttempts DEFAULT (0),
    CreatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Users_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Users_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Users PRIMARY KEY (UserId)
);
GO

-- ---------- UserRoles ----------
CREATE TABLE UserRoles (
    UserId   INT NOT NULL,
    RoleId   INT NOT NULL,
    CONSTRAINT PK_UserRoles PRIMARY KEY (UserId, RoleId)
);
GO

-- ---------- Landlords ----------
CREATE TABLE Landlords (
    LandlordId              INT IDENTITY(1,1) NOT NULL,
    FirstName               NVARCHAR(50)      NULL,
    LastName                NVARCHAR(50)      NULL,
    CompanyName             NVARCHAR(150)     NULL,
    Email                   NVARCHAR(256)     NULL,
    Phone                   NVARCHAR(30)      NULL,
    AddressLine1            NVARCHAR(150)     NOT NULL,
    AddressLine2            NVARCHAR(150)     NULL,
    City                    NVARCHAR(100)     NOT NULL,
    Postcode                NVARCHAR(20)      NOT NULL,
    Country                 NVARCHAR(100)     NOT NULL,
    PreferredContactMethod  NVARCHAR(20)      NULL,
    IsActive                BIT               NOT NULL CONSTRAINT DF_Landlords_IsActive DEFAULT (1),
    CreatedAt               DATETIME2         NOT NULL CONSTRAINT DF_Landlords_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt               DATETIME2         NOT NULL CONSTRAINT DF_Landlords_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Landlords PRIMARY KEY (LandlordId)
);
GO

-- ---------- Properties ----------
CREATE TABLE Properties (
    PropertyId          INT IDENTITY(1,1) NOT NULL,
    LandlordId          INT               NOT NULL,
    PropertyReference   NVARCHAR(30)      NOT NULL,
    AddressLine1        NVARCHAR(150)     NOT NULL,
    AddressLine2        NVARCHAR(150)     NULL,
    City                NVARCHAR(100)     NOT NULL,
    Postcode            NVARCHAR(20)      NOT NULL,
    Country              NVARCHAR(100)     NOT NULL,
    PropertyType         NVARCHAR(30)      NOT NULL,
    Bedrooms             TINYINT           NOT NULL CONSTRAINT DF_Properties_Bedrooms DEFAULT (0),
    Bathrooms            TINYINT           NOT NULL CONSTRAINT DF_Properties_Bathrooms DEFAULT (0),
    MonthlyRent          DECIMAL(10,2)     NOT NULL,
    DepositAmount        DECIMAL(10,2)     NOT NULL CONSTRAINT DF_Properties_DepositAmount DEFAULT (0),
    PropertyStatus       NVARCHAR(20)      NOT NULL CONSTRAINT DF_Properties_PropertyStatus DEFAULT (N'Vacant'),
    DateAcquired         DATE              NULL,
    Notes                NVARCHAR(1000)    NULL,
    IsActive             BIT               NOT NULL CONSTRAINT DF_Properties_IsActive DEFAULT (1),
    CreatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Properties_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Properties_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Properties PRIMARY KEY (PropertyId)
);
GO

-- ---------- Tenants ----------
CREATE TABLE Tenants (
    TenantId                 INT IDENTITY(1,1) NOT NULL,
    FirstName                NVARCHAR(50)      NOT NULL,
    LastName                 NVARCHAR(50)      NOT NULL,
    Email                    NVARCHAR(256)     NULL,
    Phone                    NVARCHAR(30)      NULL,
    DateOfBirth              DATE              NULL,
    PreviousAddress          NVARCHAR(250)     NULL,
    EmergencyContactName     NVARCHAR(100)     NULL,
    EmergencyContactPhone    NVARCHAR(30)      NULL,
    IdentificationReference  NVARCHAR(50)      NULL,
    EmploymentStatus         NVARCHAR(30)      NULL,
    Notes                    NVARCHAR(1000)    NULL,
    IsActive                 BIT               NOT NULL CONSTRAINT DF_Tenants_IsActive DEFAULT (1),
    CreatedAt                DATETIME2         NOT NULL CONSTRAINT DF_Tenants_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt                DATETIME2         NOT NULL CONSTRAINT DF_Tenants_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Tenants PRIMARY KEY (TenantId)
);
GO

-- ---------- Tenancies ----------
CREATE TABLE Tenancies (
    TenancyId            INT IDENTITY(1,1) NOT NULL,
    PropertyId           INT               NOT NULL,
    TenantId             INT               NOT NULL,
    StartDate            DATE              NOT NULL,
    EndDate              DATE              NULL,
    MonthlyRent          DECIMAL(10,2)     NOT NULL,
    DepositAmount        DECIMAL(10,2)     NOT NULL CONSTRAINT DF_Tenancies_DepositAmount DEFAULT (0),
    PaymentDueDay        TINYINT           NOT NULL,
    TenancyStatus        NVARCHAR(20)      NOT NULL CONSTRAINT DF_Tenancies_TenancyStatus DEFAULT (N'Draft'),
    CheckInDate          DATE              NULL,
    CheckOutDate         DATE              NULL,
    AgreementReference   NVARCHAR(30)      NULL,
    Notes                NVARCHAR(1000)    NULL,
    CreatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Tenancies_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt            DATETIME2         NOT NULL CONSTRAINT DF_Tenancies_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Tenancies PRIMARY KEY (TenancyId)
);
GO

-- ---------- RentPayments ----------
CREATE TABLE RentPayments (
    RentPaymentId        INT IDENTITY(1,1) NOT NULL,
    TenancyId            INT               NOT NULL,
    PaymentReference     NVARCHAR(30)      NOT NULL,
    DueDate              DATE              NOT NULL,
    AmountDue            DECIMAL(10,2)     NOT NULL,
    AmountPaid           DECIMAL(10,2)     NOT NULL CONSTRAINT DF_RentPayments_AmountPaid DEFAULT (0),
    PaymentDate          DATE              NULL,
    PaymentMethod        NVARCHAR(20)      NULL,
    PaymentStatus        NVARCHAR(20)      NOT NULL CONSTRAINT DF_RentPayments_PaymentStatus DEFAULT (N'Pending'),
    ExternalReference    NVARCHAR(100)     NULL,
    Notes                NVARCHAR(1000)    NULL,
    CreatedByEmployeeId  INT               NULL,
    CreatedAt            DATETIME2         NOT NULL CONSTRAINT DF_RentPayments_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt            DATETIME2         NOT NULL CONSTRAINT DF_RentPayments_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_RentPayments PRIMARY KEY (RentPaymentId)
);
GO

-- ---------- MaintenanceRequests ----------
CREATE TABLE MaintenanceRequests (
    MaintenanceRequestId   INT IDENTITY(1,1) NOT NULL,
    PropertyId             INT               NOT NULL,
    TenancyId              INT               NULL,
    TenantId               INT               NULL,
    AssignedEmployeeId     INT               NULL,
    RequestReference       NVARCHAR(30)      NOT NULL,
    Title                  NVARCHAR(150)     NOT NULL,
    Description            NVARCHAR(2000)    NULL,
    Category               NVARCHAR(30)      NOT NULL,
    Priority               NVARCHAR(20)      NOT NULL CONSTRAINT DF_MaintenanceRequests_Priority DEFAULT (N'Medium'),
    MaintenanceStatus      NVARCHAR(30)      NOT NULL CONSTRAINT DF_MaintenanceRequests_MaintenanceStatus DEFAULT (N'Reported'),
    ReportedDate           DATE              NOT NULL CONSTRAINT DF_MaintenanceRequests_ReportedDate DEFAULT (CAST(SYSUTCDATETIME() AS DATE)),
    ScheduledDate          DATE              NULL,
    CompletedDate          DATE              NULL,
    EstimatedCost          DECIMAL(10,2)     NULL,
    ActualCost             DECIMAL(10,2)     NULL,
    ResolutionNotes        NVARCHAR(2000)    NULL,
    CreatedAt              DATETIME2         NOT NULL CONSTRAINT DF_MaintenanceRequests_CreatedAt DEFAULT (SYSUTCDATETIME()),
    UpdatedAt              DATETIME2         NOT NULL CONSTRAINT DF_MaintenanceRequests_UpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_MaintenanceRequests PRIMARY KEY (MaintenanceRequestId)
);
GO

-- ---------- MaintenanceNotes ----------
CREATE TABLE MaintenanceNotes (
    MaintenanceNoteId      INT IDENTITY(1,1) NOT NULL,
    MaintenanceRequestId   INT               NOT NULL,
    EmployeeId             INT               NOT NULL,
    NoteText               NVARCHAR(2000)    NOT NULL,
    CreatedAt              DATETIME2         NOT NULL CONSTRAINT DF_MaintenanceNotes_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_MaintenanceNotes PRIMARY KEY (MaintenanceNoteId)
);
GO

-- ---------- AuditLogs ----------
CREATE TABLE AuditLogs (
    AuditLogId    BIGINT IDENTITY(1,1) NOT NULL,
    UserId        INT                  NULL,
    Action        NVARCHAR(50)         NOT NULL,
    EntityName    NVARCHAR(50)         NOT NULL,
    EntityId      INT                  NOT NULL,
    OldValues     NVARCHAR(MAX)        NULL,
    NewValues     NVARCHAR(MAX)        NULL,
    IpAddress     NVARCHAR(45)         NULL,
    CreatedAt     DATETIME2            NOT NULL CONSTRAINT DF_AuditLogs_CreatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_AuditLogs PRIMARY KEY (AuditLogId)
);
GO
