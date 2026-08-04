# PropertyManager — Database Design (Review Draft)

SQL Server database design for the PropertyManager MVP. This is a **design for review** — no SQL scripts have been generated yet (that's Prompt 3, next). Tables are listed in the order they must be created in, so each table only references tables already defined.

Conventions used throughout:

- Primary keys: `INT IDENTITY(1,1)` unless noted otherwise.
- Timestamps: `DATETIME2` in UTC, default `SYSUTCDATETIME()`.
- Currency: `DECIMAL(10,2)`.
- Booleans: `BIT`.
- Short codes/status values: `NVARCHAR` + `CHECK` constraint (no separate lookup tables for statuses — kept simple for the MVP; can be normalized in Phase 2 if needed).
- All foreign keys use `ON DELETE NO ACTION` / `ON UPDATE NO ACTION` — the system uses soft delete (`IsActive` flags / status changes), never cascading hard deletes.
- Naming: `PK_Table`, `FK_Child_Parent`, `UQ_Table_Column`, `CK_Table_Description`, `IX_Table_Column`.

---

## 0. Two SQL Server gotchas that shape this design

These aren't obvious if you haven't hit them before, so calling them out up front:

1. **`CHECK` constraints must be deterministic.** SQL Server rejects a `CHECK` constraint that calls `GETDATE()`/`SYSUTCDATETIME()`. So a rule like "date of birth cannot be in the future" **cannot** be a table constraint — it has to be enforced in the Pydantic schema / service layer instead. Rules that only compare columns to each other (e.g. `StartDate < EndDate`) are fine as `CHECK` constraints.
2. **A standard `UNIQUE` constraint/index only allows one `NULL` total**, not "any number of NULLs are exempt" like some other databases. For optional-but-unique columns (e.g. `Landlord.Email`), we need a **filtered unique index** (`WHERE Email IS NOT NULL`) instead of a plain `UNIQUE` constraint, or a second landlord with a blank email would fail to insert.

---

## 1. Roles

**Purpose:** Fixed list of permission roles used for authorization checks.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| RoleId | INT IDENTITY | No | — | PK |
| RoleName | NVARCHAR(50) | No | — | Unique |
| Description | NVARCHAR(200) | Yes | — | |

- **PK:** RoleId
- **Unique:** RoleName
- **Seed values:** `Administrator`, `PropertyManager`, `MaintenanceEmployee`, `ReadOnly` (loaded in the lookup-data script, not here).

---

## 2. Employees

**Purpose:** People who work for the property management company. Not all employees necessarily have a login (a `Users` row is separate and optional 1:1).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| EmployeeId | INT IDENTITY | No | — | PK |
| FirstName | NVARCHAR(50) | No | — | |
| LastName | NVARCHAR(50) | No | — | |
| Email | NVARCHAR(256) | No | — | Unique |
| Phone | NVARCHAR(30) | Yes | — | |
| JobTitle | NVARCHAR(100) | Yes | — | Descriptive title, e.g. "Senior Property Manager" |
| Department | NVARCHAR(100) | Yes | — | |
| HireDate | DATE | No | — | |
| IsActive | BIT | No | 1 | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** EmployeeId
- **Unique:** Email
- **Indexes:** `IX_Employees_IsActive`
- **Design flag:** The scope doc's suggested `RoleName` field on Employees is **dropped** here. Permission role is governed entirely by `Users` → `UserRoles` → `Roles`, so there's one source of truth instead of two fields that could disagree. `JobTitle` stays as free-text descriptive info only (no bearing on permissions).
- **Business rules:** Inactive employees cannot log in (enforced via the linked `Users.IsActive`, checked at auth time). An employee with open assigned maintenance requests should be reassigned before deactivation (service-layer check, not a DB constraint).

---

## 3. Users

**Purpose:** Authentication identity, one per employee who needs system access.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| UserId | INT IDENTITY | No | — | PK |
| EmployeeId | INT | No | — | FK → Employees.EmployeeId, unique (1:1) |
| Username | NVARCHAR(50) | No | — | Unique |
| Email | NVARCHAR(256) | No | — | Unique; mirrors Employees.Email at creation time |
| PasswordHash | NVARCHAR(255) | No | — | Never plain text |
| IsActive | BIT | No | 1 | |
| LastLoginAt | DATETIME2 | Yes | — | |
| FailedLoginAttempts | INT | No | 0 | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** UserId
- **FK:** EmployeeId → Employees.EmployeeId
- **Unique:** EmployeeId (enforces 1:1), Username, Email
- **Indexes:** `IX_Users_IsActive`

---

## 4. UserRoles

**Purpose:** Many-to-many join between Users and Roles (a user can hold more than one role, e.g. Administrator who also does maintenance triage).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| UserId | INT | No | FK → Users.UserId |
| RoleId | INT | No | FK → Roles.RoleId |

- **PK:** composite (UserId, RoleId)
- **FKs:** UserId → Users.UserId, RoleId → Roles.RoleId

---

## 5. Landlords

**Purpose:** Property owners the company manages properties on behalf of.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| LandlordId | INT IDENTITY | No | — | PK |
| FirstName | NVARCHAR(50) | Yes | — | Nullable — a landlord can be a company only |
| LastName | NVARCHAR(50) | Yes | — | |
| CompanyName | NVARCHAR(150) | Yes | — | |
| Email | NVARCHAR(256) | Yes | — | Unique when provided (filtered index) |
| Phone | NVARCHAR(30) | Yes | — | |
| AddressLine1 | NVARCHAR(150) | No | — | |
| AddressLine2 | NVARCHAR(150) | Yes | — | |
| City | NVARCHAR(100) | No | — | |
| Postcode | NVARCHAR(20) | No | — | |
| Country | NVARCHAR(100) | No | — | |
| PreferredContactMethod | NVARCHAR(20) | Yes | — | CHECK IN ('Email','Phone','Post') |
| IsActive | BIT | No | 1 | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** LandlordId
- **Unique:** Email (filtered, `WHERE Email IS NOT NULL`)
- **Check constraints:**
  - `CK_Landlords_NameOrCompany`: `CompanyName IS NOT NULL OR (FirstName IS NOT NULL AND LastName IS NOT NULL)` — a landlord must be identifiable as a person or a company.
  - `CK_Landlords_ContactMethod`: `PreferredContactMethod IN ('Email','Phone','Post')` (when not null).
- **Indexes:** `IX_Landlords_IsActive`, `IX_Landlords_LastName`
- **Business rules:** A landlord with active properties should not be permanently deleted — enforced at the service layer (block delete, offer deactivation instead) plus the natural protection of the `Properties.LandlordId` FK.

---

## 6. Properties

**Purpose:** One rentable house, flat, or unit.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| PropertyId | INT IDENTITY | No | — | PK |
| LandlordId | INT | No | — | FK → Landlords.LandlordId |
| PropertyReference | NVARCHAR(30) | No | — | Unique |
| AddressLine1 | NVARCHAR(150) | No | — | |
| AddressLine2 | NVARCHAR(150) | Yes | — | |
| City | NVARCHAR(100) | No | — | |
| Postcode | NVARCHAR(20) | No | — | |
| Country | NVARCHAR(100) | No | — | |
| PropertyType | NVARCHAR(30) | No | — | CHECK IN ('House','Flat','Bungalow','Studio','Maisonette','Other') |
| Bedrooms | TINYINT | No | 0 | CHECK >= 0 |
| Bathrooms | TINYINT | No | 0 | CHECK >= 0 |
| MonthlyRent | DECIMAL(10,2) | No | — | CHECK >= 0 |
| DepositAmount | DECIMAL(10,2) | No | 0 | CHECK >= 0 |
| PropertyStatus | NVARCHAR(20) | No | 'Vacant' | CHECK IN ('Vacant','Occupied','Under Maintenance','Unavailable','Archived') |
| DateAcquired | DATE | Yes | — | |
| Notes | NVARCHAR(1000) | Yes | — | |
| IsActive | BIT | No | 1 | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** PropertyId
- **FK:** LandlordId → Landlords.LandlordId
- **Unique:** PropertyReference
- **Check constraints:** PropertyType, PropertyStatus, Bedrooms/Bathrooms ≥ 0, MonthlyRent ≥ 0, DepositAmount ≥ 0
- **Indexes:** `IX_Properties_LandlordId`, `IX_Properties_PropertyStatus`, `IX_Properties_City`
- **Business rules:** `PropertyStatus` must stay consistent with tenancy state — handled in the tenancy service layer (activating a tenancy sets the property to Occupied; ending one sets it back to Vacant unless another tenancy starts immediately). Not a DB constraint, since it depends on related-table state.

---

## 7. Tenants

**Purpose:** People who rent (or have rented) a property.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| TenantId | INT IDENTITY | No | — | PK |
| FirstName | NVARCHAR(50) | No | — | |
| LastName | NVARCHAR(50) | No | — | |
| Email | NVARCHAR(256) | Yes | — | Unique when provided (filtered index) |
| Phone | NVARCHAR(30) | Yes | — | |
| DateOfBirth | DATE | Yes | — | "Not in the future" enforced in Pydantic, not DB (see gotcha #1 above) |
| PreviousAddress | NVARCHAR(250) | Yes | — | |
| EmergencyContactName | NVARCHAR(100) | Yes | — | |
| EmergencyContactPhone | NVARCHAR(30) | Yes | — | |
| IdentificationReference | NVARCHAR(50) | Yes | — | A reference only — never a full ID document |
| EmploymentStatus | NVARCHAR(30) | Yes | — | CHECK IN ('Employed','Self-Employed','Unemployed','Student','Retired','Other') |
| Notes | NVARCHAR(1000) | Yes | — | |
| IsActive | BIT | No | 1 | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** TenantId
- **Unique:** Email (filtered, `WHERE Email IS NOT NULL`)
- **Check constraints:** EmploymentStatus
- **Indexes:** `IX_Tenants_IsActive`, `IX_Tenants_LastName`
- **Business rules:** A tenant with an active tenancy cannot be permanently deleted — service-layer check plus natural FK protection from `Tenancies.TenantId`.

---

## 8. Tenancies

**Purpose:** A tenant's lease of a specific property for a period of time.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| TenancyId | INT IDENTITY | No | — | PK |
| PropertyId | INT | No | — | FK → Properties.PropertyId |
| TenantId | INT | No | — | FK → Tenants.TenantId |
| StartDate | DATE | No | — | |
| EndDate | DATE | Yes | — | Nullable for open-ended/periodic tenancies — see flag below |
| MonthlyRent | DECIMAL(10,2) | No | — | CHECK > 0 |
| DepositAmount | DECIMAL(10,2) | No | 0 | CHECK >= 0 |
| PaymentDueDay | TINYINT | No | — | CHECK BETWEEN 1 AND 28 |
| TenancyStatus | NVARCHAR(20) | No | 'Draft' | CHECK IN ('Draft','Upcoming','Active','Ending Soon','Ended','Cancelled') |
| CheckInDate | DATE | Yes | — | |
| CheckOutDate | DATE | Yes | — | |
| AgreementReference | NVARCHAR(30) | Yes | — | Unique when provided (filtered index) |
| Notes | NVARCHAR(1000) | Yes | — | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** TenancyId
- **FKs:** PropertyId → Properties.PropertyId, TenantId → Tenants.TenantId
- **Unique:** AgreementReference (filtered, `WHERE AgreementReference IS NOT NULL`)
- **Check constraints:**
  - `CK_Tenancies_DateOrder`: `EndDate IS NULL OR EndDate > StartDate`
  - `CK_Tenancies_Rent`: `MonthlyRent > 0`
  - `CK_Tenancies_PaymentDueDay`: `PaymentDueDay BETWEEN 1 AND 28`
  - `CK_Tenancies_Status`: status in the allowed list
- **Indexes:** `IX_Tenancies_PropertyId`, `IX_Tenancies_TenantId`, `IX_Tenancies_TenancyStatus`, `IX_Tenancies_Property_Dates` on `(PropertyId, StartDate, EndDate)` — supports the overlap check below.
- **Design flag — overlap prevention is NOT a DB constraint.** "No two overlapping active tenancies for the same property" spans multiple rows and depends on live status, which SQL Server can't express as a `CHECK` constraint or a simple filtered unique index (a property can legitimately have one Active tenancy and one Upcoming tenancy scheduled for later, so "one row per status" isn't right either). This is enforced by the **service layer inside a transaction**: before activating/creating a tenancy, query for existing Active/Upcoming tenancies on the same property with overlapping date ranges, inside the same transaction that inserts the new row (using an appropriate isolation level to prevent a race). The `IX_Tenancies_Property_Dates` index keeps that check fast. A DB trigger could be added later as defense-in-depth, but isn't necessary for the MVP.
- **Design flag — should `EndDate` really be nullable?** I made it nullable to support rolling/periodic tenancies with no fixed end. If your company only ever writes fixed-term agreements, we can make it `NOT NULL` instead and simplify some downstream logic (e.g. "tenancies ending in 30/60/90 days"). Let me know which matches how the business actually works.

---

## 9. RentPayments

**Purpose:** One rent obligation (and its payment progress) for a tenancy, typically one per due date.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| RentPaymentId | INT IDENTITY | No | — | PK |
| TenancyId | INT | No | — | FK → Tenancies.TenancyId |
| PaymentReference | NVARCHAR(30) | No | — | Unique |
| DueDate | DATE | No | — | |
| AmountDue | DECIMAL(10,2) | No | — | CHECK >= 0 |
| AmountPaid | DECIMAL(10,2) | No | 0 | CHECK >= 0 |
| PaymentDate | DATE | Yes | — | |
| PaymentMethod | NVARCHAR(20) | Yes | — | CHECK IN ('Bank Transfer','Card','Cash','Direct Debit','Standing Order','Other') |
| PaymentStatus | NVARCHAR(20) | No | 'Pending' | CHECK IN ('Pending','Partially Paid','Paid','Overdue','Cancelled') |
| ExternalReference | NVARCHAR(100) | Yes | — | e.g. bank transaction ID |
| Notes | NVARCHAR(1000) | Yes | — | |
| CreatedByEmployeeId | INT | Yes | — | FK → Employees.EmployeeId; nullable to allow future automated/recurring generation (Phase 2) |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** RentPaymentId
- **FKs:** TenancyId → Tenancies.TenancyId, CreatedByEmployeeId → Employees.EmployeeId
- **Unique:** PaymentReference
- **Check constraints:** AmountDue ≥ 0, AmountPaid ≥ 0, PaymentMethod list, PaymentStatus list
- **Indexes:** `IX_RentPayments_TenancyId`, `IX_RentPayments_PaymentStatus`, `IX_RentPayments_DueDate`, `IX_RentPayments_Tenancy_Due` on `(TenancyId, DueDate)`
- **Design flag:** `PaymentStatus` is a plain column, not a computed one — per the scope doc's own instruction to keep the Pending/Partial/Paid/Overdue calculation centralized in the service layer (it depends on `AmountDue` vs `AmountPaid` vs `DueDate` vs today's date, and "today" can't drive a computed column or CHECK constraint either — same gotcha #1 as above). The service must update this column whenever a payment is recorded, and a scheduled/manual sweep will need to flip Pending → Overdue as due dates pass.
- **Business rules:** Payments are never hard-deleted — cancellation is a status change (`Cancelled`), excluded from totals in reporting queries.

---

## 10. MaintenanceRequests

**Purpose:** A reported issue at a property, tracked through to resolution.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| MaintenanceRequestId | INT IDENTITY | No | — | PK |
| PropertyId | INT | No | — | FK → Properties.PropertyId |
| TenancyId | INT | Yes | — | FK → Tenancies.TenancyId (null if reported while vacant/by landlord) |
| TenantId | INT | Yes | — | FK → Tenants.TenantId |
| AssignedEmployeeId | INT | Yes | — | FK → Employees.EmployeeId |
| RequestReference | NVARCHAR(30) | No | — | Unique |
| Title | NVARCHAR(150) | No | — | |
| Description | NVARCHAR(2000) | Yes | — | |
| Category | NVARCHAR(30) | No | — | CHECK IN ('Plumbing','Electrical','Heating','Appliance','Structural','Security','Cleaning','General','Other') |
| Priority | NVARCHAR(20) | No | 'Medium' | CHECK IN ('Low','Medium','High','Emergency') |
| MaintenanceStatus | NVARCHAR(30) | No | 'Reported' | CHECK IN ('Reported','Assigned','In Progress','Waiting for Parts','Waiting for Approval','Completed','Cancelled') |
| ReportedDate | DATE | No | CAST(SYSUTCDATETIME() AS DATE) | |
| ScheduledDate | DATE | Yes | — | |
| CompletedDate | DATE | Yes | — | |
| EstimatedCost | DECIMAL(10,2) | Yes | — | CHECK >= 0 |
| ActualCost | DECIMAL(10,2) | Yes | — | CHECK >= 0 |
| ResolutionNotes | NVARCHAR(2000) | Yes | — | Required when Completed |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |
| UpdatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** MaintenanceRequestId
- **FKs:** PropertyId → Properties.PropertyId, TenancyId → Tenancies.TenancyId, TenantId → Tenants.TenantId, AssignedEmployeeId → Employees.EmployeeId
- **Unique:** RequestReference
- **Check constraints:**
  - Category, Priority, MaintenanceStatus lists
  - EstimatedCost ≥ 0, ActualCost ≥ 0
  - `CK_MaintenanceRequests_CompletionRequiresDetail`: `MaintenanceStatus <> 'Completed' OR (CompletedDate IS NOT NULL AND ResolutionNotes IS NOT NULL)` — this one *can* be a real `CHECK` constraint since it only compares columns to each other, not to the current date.
- **Indexes:** `IX_MaintenanceRequests_PropertyId`, `IX_MaintenanceRequests_AssignedEmployeeId`, `IX_MaintenanceRequests_MaintenanceStatus`, `IX_MaintenanceRequests_Priority`
- **Business rules:** Inactive employees cannot receive new assignments (service-layer check at assignment time). Emergency priority should be easy to query/highlight — covered by the `Priority` index.

---

## 11. MaintenanceNotes

**Purpose:** A running log of notes/updates on a maintenance request (separate from the final `ResolutionNotes`).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| MaintenanceNoteId | INT IDENTITY | No | — | PK |
| MaintenanceRequestId | INT | No | — | FK → MaintenanceRequests.MaintenanceRequestId |
| EmployeeId | INT | No | — | FK → Employees.EmployeeId |
| NoteText | NVARCHAR(2000) | No | — | |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** MaintenanceNoteId
- **FKs:** MaintenanceRequestId → MaintenanceRequests.MaintenanceRequestId, EmployeeId → Employees.EmployeeId
- **Indexes:** `IX_MaintenanceNotes_MaintenanceRequestId`

---

## 12. AuditLogs

**Purpose:** Record of who changed what, for accountability on financially/legally sensitive records.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| AuditLogId | BIGINT IDENTITY | No | — | PK — BIGINT since this table grows fast |
| UserId | INT | Yes | — | FK → Users.UserId; nullable for system-generated actions |
| Action | NVARCHAR(50) | No | — | e.g. 'CREATE','UPDATE','STATUS_CHANGE','CANCEL' |
| EntityName | NVARCHAR(50) | No | — | e.g. 'Tenancy','RentPayment' |
| EntityId | INT | No | — | ID of the affected row |
| OldValues | NVARCHAR(MAX) | Yes | — | JSON snapshot before change |
| NewValues | NVARCHAR(MAX) | Yes | — | JSON snapshot after change |
| IpAddress | NVARCHAR(45) | Yes | — | Sized for IPv6 |
| CreatedAt | DATETIME2 | No | SYSUTCDATETIME() | |

- **PK:** AuditLogId
- **FK:** UserId → Users.UserId
- **Indexes:** `IX_AuditLogs_EntityName_EntityId` on `(EntityName, EntityId)`, `IX_AuditLogs_CreatedAt`, `IX_AuditLogs_UserId`

---

## Relationship summary

```text
Roles ─┬─< UserRoles >─┬─ Users ── Employees
       │               │
       └───────────────┘

Landlords ──< Properties ──< Tenancies >── Tenants
                  │               │
                  │               └──< RentPayments
                  │
                  └──< MaintenanceRequests >── Employees (assigned)
                                │
                                └──< MaintenanceNotes ── Employees

AuditLogs ── Users (nullable)
```

- One landlord → many properties.
- One property → many tenancies (over time), and many maintenance requests.
- One tenant → many tenancies (over time).
- One tenancy → many rent payments.
- One employee → many assigned maintenance requests, many maintenance notes.
- One employee → at most one user account (1:1, optional).
- One user → one or more roles (many:many via UserRoles).

---

## Open questions for your review before I generate SQL scripts

1. **Employees.RoleName removed** — permissions come only from Users → UserRoles → Roles. OK, or did you want RoleName kept as a quick-reference column too (with the risk it can drift out of sync)?
2. **Tenancy.EndDate nullable** — allows open-ended tenancies. If your company always writes fixed-term agreements, I'll make it `NOT NULL` instead.
3. **Overlap prevention lives in the service layer**, not the database, for the reasons above. Fine for MVP, but flagging it since it's the one core business rule the database itself doesn't guarantee — the API and its tests are what actually enforce it.
4. **Status values as `NVARCHAR` + `CHECK`** rather than separate lookup tables (e.g. `PropertyStatuses`, `TenancyStatuses`) — simpler for the MVP and matches your "keep it practical" note. We can normalize to lookup tables in Phase 2 if you want statuses manageable without a code change.
5. **DateOfBirth / "not in the future"** and the **rent payment status calculation** cannot be database `CHECK` constraints (SQL Server disallows non-deterministic functions there) — both will be enforced in Pydantic/service code instead. Just flagging so it's not a surprise when you don't see them in the `CHECK` constraint list of the SQL script.

Let me know if any of the five points above should change — otherwise this is what I'll turn into the actual `CREATE TABLE` scripts next (Prompt 3).
