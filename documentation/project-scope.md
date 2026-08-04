# Property Management Software

## Full Project Scope and AI Prompt Library

## 1. Project Overview

### Working project name

**PropertyManager**

The name can be changed later.

### Project objective

Build a complete web-based property management system that allows a property management company to manage:

* Landlords
* Properties
* Tenants
* Tenancies
* Rent payments
* Maintenance requests
* Employees
* Reports and dashboard statistics

The finished application should demonstrate:

* SQL database design
* Python development
* REST API development
* Authentication and authorization
* React frontend development
* Business logic
* Testing
* Git and GitHub
* Deployment
* Professional documentation

### Intended user

The first version is designed for a **small or medium-sized property management company**.

### MVP architecture decision

The MVP will support **one property management company with multiple employees**.

It will not initially be a fully multi-company SaaS platform. Multi-company functionality can be added after the main system works.

This keeps the project realistic and prevents the first version from becoming too complicated.

---

# 2. Technology Stack

## Database

* SQL Server
* SQL Server Management Studio or Azure Data Studio
* Alembic for database migrations later

## Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* JWT authentication
* Pytest

## Frontend

* React
* JavaScript
* HTML
* CSS
* React Router
* Axios or another API client
* A reusable component library can be added later

## Development tools

* Visual Studio Code or Visual Studio
* Git
* GitHub
* Postman or FastAPI Swagger documentation
* Environment variables for secrets

## Deployment

A suitable final deployment could use:

* Azure SQL for the database
* Azure App Service, Render, Railway or another backend host
* Vercel, Netlify or another frontend host

The deployment provider can be selected when the application is ready.

---

# 3. Project Scope

## Phase 1: Minimum Viable Product

The MVP must include:

1. User login
2. Employee roles and permissions
3. Landlord management
4. Property management
5. Tenant management
6. Tenancy management
7. Rent payment tracking
8. Maintenance request tracking
9. Dashboard
10. Business reports
11. Search and filters
12. CSV export
13. Audit information
14. Error handling
15. Automated backend testing
16. Online deployment
17. GitHub documentation

## Phase 2: Advanced features

These should only be built after the MVP works:

* Multiple property management companies
* Landlord portal
* Tenant portal
* Document uploads
* Tenancy agreement storage
* Email notifications
* SMS notifications
* Recurring rent generation
* Automated overdue reminders
* Online rent payments
* Contractor management
* Property inspections
* Expenses and invoices
* Mobile application
* Calendar integration
* PDF landlord statements
* Accounting software integration

---

# 4. User Roles

## Administrator

An administrator can:

* View the full dashboard
* Manage employees
* Create and deactivate user accounts
* Manage landlords
* Manage properties
* Manage tenants
* Manage tenancies
* Record rent payments
* Manage maintenance requests
* View all reports
* Export data
* View audit records

## Property Manager

A property manager can:

* Manage landlords
* Manage properties
* Manage tenants
* Manage tenancies
* Record rent payments
* Manage maintenance requests
* View reports
* Export operational data

A property manager cannot manage administrator accounts.

## Maintenance Employee

A maintenance employee can:

* View maintenance requests assigned to them
* Update maintenance request status
* Add maintenance notes
* Enter estimated and actual costs
* Mark work as completed

They should not have access to financial reports or employee administration.

## Read-only user

A read-only user can:

* View records
* View permitted reports
* Search and filter

They cannot create, edit or delete records.

---

# 5. Core Database Design

The original seven business tables remain the centre of the system:

1. Landlords
2. Properties
3. Tenants
4. Tenancies
5. RentPayments
6. MaintenanceRequests
7. Employees

Supporting security and system tables will also be required.

---

## 5.1 Landlords

### Suggested fields

* `LandlordId`
* `FirstName`
* `LastName`
* `CompanyName`
* `Email`
* `Phone`
* `AddressLine1`
* `AddressLine2`
* `City`
* `Postcode`
* `Country`
* `PreferredContactMethod`
* `IsActive`
* `CreatedAt`
* `UpdatedAt`

### Main rules

* A landlord may own multiple properties.
* Email should be unique when provided.
* A landlord with active properties should not be permanently deleted.
* Inactive landlords should normally be deactivated rather than deleted.

---

## 5.2 Properties

For the MVP, each property record represents one rentable house, flat or unit.

### Suggested fields

* `PropertyId`
* `LandlordId`
* `PropertyReference`
* `AddressLine1`
* `AddressLine2`
* `City`
* `Postcode`
* `Country`
* `PropertyType`
* `Bedrooms`
* `Bathrooms`
* `MonthlyRent`
* `DepositAmount`
* `PropertyStatus`
* `DateAcquired`
* `Notes`
* `IsActive`
* `CreatedAt`
* `UpdatedAt`

### Property statuses

* Vacant
* Occupied
* Under Maintenance
* Unavailable
* Archived

### Main rules

* Every property must belong to a landlord.
* `PropertyReference` must be unique.
* Monthly rent cannot be negative.
* A property cannot have two active tenancies covering the same period.
* An occupied property should have an active tenancy.

---

## 5.3 Tenants

### Suggested fields

* `TenantId`
* `FirstName`
* `LastName`
* `Email`
* `Phone`
* `DateOfBirth`
* `PreviousAddress`
* `EmergencyContactName`
* `EmergencyContactPhone`
* `IdentificationReference`
* `EmploymentStatus`
* `Notes`
* `IsActive`
* `CreatedAt`
* `UpdatedAt`

### Main rules

* Email should be unique when provided.
* Date of birth cannot be in the future.
* A tenant with an active tenancy cannot be permanently deleted.
* Sensitive identification data should be limited and protected.

---

## 5.4 Tenancies

### Suggested fields

* `TenancyId`
* `PropertyId`
* `TenantId`
* `StartDate`
* `EndDate`
* `MonthlyRent`
* `DepositAmount`
* `PaymentDueDay`
* `TenancyStatus`
* `CheckInDate`
* `CheckOutDate`
* `AgreementReference`
* `Notes`
* `CreatedAt`
* `UpdatedAt`

### Tenancy statuses

* Draft
* Upcoming
* Active
* Ending Soon
* Ended
* Cancelled

### Main rules

* Start date must be before end date.
* Monthly rent must be greater than zero.
* Payment due day must be between 1 and 28.
* Only one active tenancy is allowed for the same property during overlapping dates.
* An active tenancy must have an active tenant and property.
* Ending a tenancy should update the property to Vacant unless another tenancy begins immediately.

### Future improvement

A later version can support multiple tenants on one tenancy using a joining table such as `TenancyTenants`.

For the first version, one main tenant per tenancy is acceptable.

---

## 5.5 Rent Payments

### Suggested fields

* `RentPaymentId`
* `TenancyId`
* `PaymentReference`
* `DueDate`
* `AmountDue`
* `AmountPaid`
* `PaymentDate`
* `PaymentMethod`
* `PaymentStatus`
* `ExternalReference`
* `Notes`
* `CreatedByEmployeeId`
* `CreatedAt`
* `UpdatedAt`

### Payment statuses

* Pending
* Partially Paid
* Paid
* Overdue
* Cancelled

### Payment methods

* Bank Transfer
* Card
* Cash
* Direct Debit
* Standing Order
* Other

### Main rules

* Amount due cannot be negative.
* Amount paid cannot be negative.
* A payment is Paid when the full amount has been received.
* A payment is Partially Paid when some but not all rent has been received.
* A payment is Overdue when the due date has passed and the full amount has not been received.
* Payment reference must be unique.
* Payments should not be permanently deleted after being recorded; they should be cancelled or corrected through an audit-controlled process.

---

## 5.6 Maintenance Requests

### Suggested fields

* `MaintenanceRequestId`
* `PropertyId`
* `TenancyId`
* `TenantId`
* `AssignedEmployeeId`
* `RequestReference`
* `Title`
* `Description`
* `Category`
* `Priority`
* `MaintenanceStatus`
* `ReportedDate`
* `ScheduledDate`
* `CompletedDate`
* `EstimatedCost`
* `ActualCost`
* `ResolutionNotes`
* `CreatedAt`
* `UpdatedAt`

### Categories

* Plumbing
* Electrical
* Heating
* Appliance
* Structural
* Security
* Cleaning
* General
* Other

### Priorities

* Low
* Medium
* High
* Emergency

### Statuses

* Reported
* Assigned
* In Progress
* Waiting for Parts
* Waiting for Approval
* Completed
* Cancelled

### Main rules

* Every request must relate to a property.
* Completed requests must have a completion date.
* Actual cost cannot be negative.
* Emergency requests should be clearly highlighted.
* A request should not be marked Completed without resolution notes.

---

## 5.7 Employees

### Suggested fields

* `EmployeeId`
* `FirstName`
* `LastName`
* `Email`
* `Phone`
* `JobTitle`
* `Department`
* `HireDate`
* `RoleName`
* `IsActive`
* `CreatedAt`
* `UpdatedAt`

### Main rules

* Employee email must be unique.
* Inactive employees cannot log in.
* An employee assigned to open maintenance requests should normally be reassigned before deactivation.

---

# 6. Supporting Tables

## Users

Used for authentication.

Suggested fields:

* `UserId`
* `EmployeeId`
* `Username`
* `Email`
* `PasswordHash`
* `IsActive`
* `LastLoginAt`
* `FailedLoginAttempts`
* `CreatedAt`
* `UpdatedAt`

Never store plain-text passwords.

## Roles

Suggested fields:

* `RoleId`
* `RoleName`
* `Description`

## UserRoles

Suggested fields:

* `UserId`
* `RoleId`

## AuditLogs

Suggested fields:

* `AuditLogId`
* `UserId`
* `Action`
* `EntityName`
* `EntityId`
* `OldValues`
* `NewValues`
* `IpAddress`
* `CreatedAt`

## MaintenanceNotes

Suggested fields:

* `MaintenanceNoteId`
* `MaintenanceRequestId`
* `EmployeeId`
* `NoteText`
* `CreatedAt`

---

# 7. Main Relationships

* One landlord has many properties.
* One property belongs to one landlord.
* One property has many tenancies over time.
* One tenant has many tenancies over time.
* One tenancy belongs to one property.
* One tenancy belongs to one main tenant.
* One tenancy has many rent payments.
* One property has many maintenance requests.
* One employee can be assigned many maintenance requests.
* One maintenance request can have many maintenance notes.
* One employee may have one user account.
* One user may have one or more roles.

---

# 8. Backend API Scope

The API should use a route structure similar to:

```text
/api/auth
/api/users
/api/employees
/api/landlords
/api/properties
/api/tenants
/api/tenancies
/api/rent-payments
/api/maintenance-requests
/api/dashboard
/api/reports
/api/exports
```

## Authentication endpoints

```text
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/change-password
```

## Landlord endpoints

```text
GET    /api/landlords
GET    /api/landlords/{id}
POST   /api/landlords
PUT    /api/landlords/{id}
PATCH  /api/landlords/{id}/status
DELETE /api/landlords/{id}
```

The delete operation should normally perform a soft delete or reject deletion when connected records exist.

## Property endpoints

```text
GET    /api/properties
GET    /api/properties/{id}
POST   /api/properties
PUT    /api/properties/{id}
PATCH  /api/properties/{id}/status
DELETE /api/properties/{id}
GET    /api/properties/{id}/tenancies
GET    /api/properties/{id}/maintenance
GET    /api/properties/{id}/payments
```

## Tenant endpoints

```text
GET    /api/tenants
GET    /api/tenants/{id}
POST   /api/tenants
PUT    /api/tenants/{id}
PATCH  /api/tenants/{id}/status
DELETE /api/tenants/{id}
GET    /api/tenants/{id}/tenancies
GET    /api/tenants/{id}/payment-history
```

## Tenancy endpoints

```text
GET    /api/tenancies
GET    /api/tenancies/{id}
POST   /api/tenancies
PUT    /api/tenancies/{id}
POST   /api/tenancies/{id}/activate
POST   /api/tenancies/{id}/end
POST   /api/tenancies/{id}/cancel
GET    /api/tenancies/expiring
```

## Rent payment endpoints

```text
GET    /api/rent-payments
GET    /api/rent-payments/{id}
POST   /api/rent-payments
PUT    /api/rent-payments/{id}
POST   /api/rent-payments/{id}/record-payment
POST   /api/rent-payments/{id}/cancel
GET    /api/rent-payments/overdue
GET    /api/rent-payments/due
```

## Maintenance endpoints

```text
GET    /api/maintenance-requests
GET    /api/maintenance-requests/{id}
POST   /api/maintenance-requests
PUT    /api/maintenance-requests/{id}
POST   /api/maintenance-requests/{id}/assign
POST   /api/maintenance-requests/{id}/change-status
POST   /api/maintenance-requests/{id}/notes
POST   /api/maintenance-requests/{id}/complete
```

## Dashboard endpoints

```text
GET /api/dashboard/summary
GET /api/dashboard/rent-summary
GET /api/dashboard/occupancy
GET /api/dashboard/maintenance-summary
GET /api/dashboard/recent-activity
```

---

# 9. Search, Filtering and Pagination

List endpoints should support:

* Page number
* Page size
* Search text
* Sort field
* Sort direction
* Status
* Date range
* Property
* Landlord
* Tenant
* Assigned employee

Example:

```text
GET /api/properties?page=1&page_size=20&status=Vacant&search=London
```

API responses should include:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total_items": 0,
  "total_pages": 0
}
```

---

# 10. Frontend Pages

## Public pages

* Login
* Forgotten password placeholder
* Unauthorized
* Page not found

## Main application pages

### Dashboard

Display:

* Total properties
* Occupied properties
* Vacant properties
* Occupancy percentage
* Active tenancies
* Rent due this month
* Rent collected this month
* Outstanding rent
* Open maintenance requests
* Emergency maintenance requests
* Tenancies ending soon
* Recent activity

### Landlords

* Landlord list
* Add landlord
* Edit landlord
* Landlord details
* Landlord properties
* Landlord income summary

### Properties

* Property list
* Add property
* Edit property
* Property details
* Current tenancy
* Tenancy history
* Payment history
* Maintenance history

### Tenants

* Tenant list
* Add tenant
* Edit tenant
* Tenant details
* Current tenancy
* Tenancy history
* Payment history

### Tenancies

* Tenancy list
* Add tenancy
* Edit tenancy
* Tenancy details
* Activate tenancy
* End tenancy
* Cancel tenancy
* Expiring tenancies

### Rent payments

* Payment list
* Outstanding payments
* Overdue payments
* Record payment
* Payment details
* Payment history

### Maintenance

* Maintenance request list
* Add request
* Edit request
* Assign employee
* Change status
* Add notes
* Complete request

### Employees

* Employee list
* Add employee
* Edit employee
* Assign role
* Activate or deactivate employee

### Reports

* Report selection
* Filters
* Results table
* CSV export
* Print-friendly view

### Settings

* Current user profile
* Change password
* Basic system settings

---

# 11. Dashboard Design

The dashboard should contain:

## KPI cards

* Total Properties
* Occupied
* Vacant
* Occupancy Rate
* Rent Due
* Rent Collected
* Outstanding Rent
* Open Maintenance

## Charts

* Rent collected by month
* Occupied versus vacant properties
* Maintenance requests by status
* Maintenance requests by category

## Attention lists

* Overdue rent
* Tenancies expiring in the next 30 days
* Emergency maintenance
* Unassigned maintenance requests

---

# 12. Reports

To resolve the earlier difference between 10 and 15 reports, build **10 MVP reports** and then add **5 advanced reports**.

## Ten MVP reports

1. Rent due this month
2. Overdue rent
3. Monthly rent collected
4. Rent collected by landlord
5. Occupancy report
6. Vacant properties
7. Tenancies ending within 30, 60 or 90 days
8. Open maintenance by status and priority
9. Maintenance costs by property
10. Property income and performance

## Five advanced reports

11. Tenant payment history
12. Employee maintenance workload
13. Average maintenance completion time
14. Full rent roll
15. Landlord statement

Each report should support relevant filters and CSV export.

---

# 13. Validation Rules

## General validation

* Required fields cannot be empty.
* Email addresses must have valid formatting.
* Telephone numbers should have sensible length validation.
* Currency values cannot be negative unless the field specifically permits a credit.
* Dates must follow logical ordering.
* Text lengths should be limited.
* Duplicate references should be rejected.
* Invalid foreign keys should be rejected.

## API validation

The API should return appropriate status codes:

* `200` for successful reads and updates
* `201` for successful creation
* `204` for successful operations with no response body
* `400` for invalid business operations
* `401` for unauthenticated users
* `403` for users without permission
* `404` for missing records
* `409` for duplicate or conflicting records
* `422` for request validation errors
* `500` for unexpected errors

Errors should use a consistent format:

```json
{
  "error": {
    "code": "TENANCY_DATE_CONFLICT",
    "message": "This property already has a tenancy covering those dates.",
    "details": {}
  }
}
```

---

# 14. Security Requirements

The project must include:

* Password hashing
* JWT access tokens
* Refresh tokens
* Role-based permissions
* Protected backend routes
* Protected frontend routes
* Environment variables
* CORS configuration
* Input validation
* Parameterized database queries
* No secrets committed to GitHub
* Login rate limiting later
* Audit logs for important changes
* Secure error messages
* User deactivation
* Password change functionality

Do not store:

* Plain-text passwords
* Full payment card details
* Unnecessary identification documents
* Database passwords inside source files

---

# 15. Suggested Repository Structure

```text
property-management-system/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── dependencies/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── security/
│   │   ├── utilities/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── utilities/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env.example
│   └── package.json
│
├── database/
│   ├── 01-create-database.sql
│   ├── 02-create-tables.sql
│   ├── 03-create-constraints.sql
│   ├── 04-seed-lookup-data.sql
│   ├── 05-seed-demo-data.sql
│   ├── 06-create-views.sql
│   └── 07-report-queries.sql
│
├── documentation/
│   ├── project-scope.md
│   ├── database-design.md
│   ├── api-documentation.md
│   ├── business-rules.md
│   └── deployment-guide.md
│
├── .gitignore
├── README.md
└── LICENSE
```

---

# 16. Development Milestones

## 1: Planning and SQL design

* Finalize scope
* Create GitHub repository
* Design entity relationship diagram
* Create SQL Server database
* Create the seven core business tables
* Create supporting authentication tables
* Add constraints
* Add indexes
* Add demo data

## 2: SQL queries and Python foundation

* Write CRUD SQL
* Write joins and grouped queries
* Write 10 MVP reports
* Learn Python project structure
* Learn functions, classes, modules and exceptions
* Create the FastAPI project

## 3: Backend database integration

* Configure SQLAlchemy
* Create database models
* Create Pydantic schemas
* Create repository and service layers
* Build landlord and property APIs
* Add validation and error handling

## 4: Complete backend CRUD

* Tenant APIs
* Tenancy APIs
* Rent payment APIs
* Maintenance APIs
* Employee APIs
* Pagination
* Search
* Filtering

## 5: Authentication and business logic

* User accounts
* Password hashing
* Login
* JWT
* Roles
* Permissions
* Tenancy date validation
* Rent status calculation
* Maintenance workflow
* Audit logging

## 6: React frontend foundation

* React project
* Routing
* Login page
* Main layout
* Sidebar
* Header
* Reusable tables
* Reusable forms
* API client
* Authentication context

## 7: Frontend modules

* Landlords
* Properties
* Tenants
* Tenancies
* Payments
* Maintenance
* Employees

## 8: Dashboard and reports

* KPI cards
* Charts
* Report filters
* CSV export
* Advanced reports
* Loading and error states

## 9: Testing and deployment

* Backend tests
* Frontend testing
* Security review
* Demo data
* Deployment
* Production configuration
* Fix deployment issues

## 10: Portfolio preparation

* Professional README
* Screenshots
* Architecture diagram
* Demo account
* Project video
* Interview explanation
* Final code cleanup

---

# 17. Weekly Study Structure

For approximately nine hours per week:

* Two hours learning
* Five hours building
* One hour debugging
* One hour reviewing and documenting

Use roughly:

* 20% learning
* 80% building

Do not spend several months completing courses before beginning the project.

---

# 18. Definition of Done

The project is complete when:

* Users can log in securely.
* Permissions are enforced by the backend.
* All seven business modules work.
* Users can create, view, edit and deactivate records.
* Tenancy conflicts are prevented.
* Rent payments and overdue amounts are calculated correctly.
* Maintenance requests follow a controlled workflow.
* Dashboard values come from real database data.
* Ten business reports work.
* CSV export works.
* Validation messages are understandable.
* Backend tests cover important business rules.
* Secrets are stored in environment variables.
* The frontend and backend are deployed.
* The deployed application connects to a deployed database.
* Demo data and a demo account are available.
* GitHub contains setup instructions and screenshots.
* The application can be demonstrated in an interview.

---

# 19. Master AI Prompt

Paste this before beginning a new major phase.

```text
Act as my senior full-stack software development mentor.

I am building a portfolio-quality property management web application called PropertyManager.

My stack is:

- SQL Server
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication
- React
- JavaScript
- HTML and CSS
- Git and GitHub

The core business tables are:

- Landlords
- Properties
- Tenants
- Tenancies
- RentPayments
- MaintenanceRequests
- Employees

The application is initially for one property management company with multiple employee users. It is not yet a multi-company SaaS application.

I am learning while building, so follow these rules:

1. Work on one small feature at a time.
2. Do not generate the entire application in one response.
3. Use simple, readable and professional code.
4. Explain the purpose of each file before showing its code.
5. Always show the full file path.
6. Do not use unexplained advanced patterns.
7. Keep business logic outside route functions where practical.
8. Use database constraints as well as application validation.
9. Use SQL Server-compatible code.
10. Use Windows-compatible terminal commands.
11. Include error handling.
12. Include tests for important business rules.
13. Do not leave placeholder code that appears complete but does not work.
14. Never store secrets or passwords in source code.
15. Do not change existing architecture without explaining why.
16. At the end of every task, provide:
   - files created or changed;
   - commands to run;
   - how to test it;
   - expected result;
   - common errors;
   - a Git commit message.
17. Stop after completing the requested task so that I can test it before continuing.

When code depends on an existing file, ask me to paste that file or use the exact content I provide. Do not guess what is inside my project.
```

---

# 20. Prompt 1: Architecture and Setup

```text
Using the PropertyManager project context, design the initial application architecture.

Create:

1. The recommended repository structure.
2. The backend folder structure.
3. The frontend folder structure.
4. The database scripts folder.
5. The documentation folder.
6. A development environment checklist.
7. A suitable .gitignore.
8. A safe .env.example for the backend.
9. A safe .env.example for the frontend.
10. The first Git commits I should make.

Do not build any business features yet.

Use Windows-compatible commands and explain each setup command before I run it. Stop after the initial structure is ready.
```

---

# 21. Prompt 2: Database Design Review

```text
Design the SQL Server database for PropertyManager.

Use these core tables:

- Landlords
- Properties
- Tenants
- Tenancies
- RentPayments
- MaintenanceRequests
- Employees

Also include supporting tables where necessary for:

- Users
- Roles
- UserRoles
- AuditLogs
- MaintenanceNotes

For every table provide:

1. Purpose.
2. Columns.
3. SQL Server data types.
4. Primary key.
5. Foreign keys.
6. Required and optional fields.
7. Unique constraints.
8. Check constraints.
9. Default values.
10. Recommended indexes.
11. Relationships.
12. Business rules.

Keep the first design practical rather than overly complicated.

For the MVP, each tenancy has one main tenant and each property record represents one rentable property or unit.

Do not generate the SQL scripts yet. First provide the design for review.
```

---

# 22. Prompt 3: Create SQL Scripts

```text
Using the approved PropertyManager database design, generate the SQL Server scripts.

Separate the work into these files:

database/01-create-database.sql
database/02-create-tables.sql
database/03-create-constraints.sql
database/04-create-indexes.sql
database/05-seed-lookup-data.sql

Requirements:

- Use clear and simple T-SQL.
- Use GO between suitable sections.
- Use meaningful constraint names.
- Use IDENTITY primary keys where appropriate.
- Use DATETIME2 for timestamps.
- Use DECIMAL for currency.
- Use BIT for true or false values.
- Add CreatedAt and UpdatedAt where appropriate.
- Add check constraints for dates and financial values.
- Prevent duplicate reference values.
- Make scripts safe and easy to test independently.
- Explain the order in which I should run them.

Do not add demo landlords, properties or tenants yet.
```

---

# 23. Prompt 4: Demo Data

```text
Create realistic demo data for the PropertyManager SQL Server database.

Create:

- 5 landlords
- 10 properties
- 12 tenants
- 12 tenancies
- 30 rent payment records
- 20 maintenance requests
- 5 employees
- suitable users and roles

The data must contain realistic scenarios:

- occupied properties;
- vacant properties;
- active tenancies;
- ended tenancies;
- tenancies ending soon;
- fully paid rent;
- partially paid rent;
- overdue rent;
- open maintenance;
- emergency maintenance;
- completed maintenance.

Respect every foreign key, unique constraint and check constraint.

Put all data in:

database/06-seed-demo-data.sql

Use clear INSERT statements rather than an unnecessarily complicated data generator.

At the end, provide SELECT queries that verify the number of records inserted.
```

---

# 24. Prompt 5: SQL Report Queries

```text
Create the first 10 PropertyManager SQL Server business reports.

Reports:

1. Rent due this month.
2. Overdue rent.
3. Monthly rent collected.
4. Rent collected by landlord.
5. Occupancy report.
6. Vacant properties.
7. Tenancies ending within 30, 60 or 90 days.
8. Open maintenance by status and priority.
9. Maintenance costs by property.
10. Property income and performance.

For each report:

- explain the business question;
- write the SQL query;
- explain every JOIN;
- explain grouping and filtering;
- include sensible column aliases;
- handle NULL values;
- recommend useful parameters;
- provide a simple test using the demo data.

Put the final queries in:

database/07-report-queries.sql
```

---

# 25. Prompt 6: FastAPI Backend Foundation

```text
Create the initial FastAPI backend foundation for PropertyManager.

Set up:

- application entry point;
- settings and environment configuration;
- database connection;
- SQLAlchemy session management;
- API router structure;
- health-check endpoint;
- centralized exception handling;
- logging;
- CORS configuration;
- requirements file;
- development start command;
- first backend test.

Do not create all business models or CRUD routes yet.

Use a structure that is professional but still understandable to someone learning Python.

Explain:

- what every file does;
- how the application starts;
- how dependency injection works;
- how to verify the SQL Server connection;
- how to open FastAPI Swagger documentation.

Stop once the health check and database connectivity test work.
```

---

# 26. Prompt 7: SQLAlchemy Models

```text
Create SQLAlchemy models for PropertyManager based exactly on my approved SQL Server schema.

Work in this order:

1. Landlord
2. Property
3. Tenant
4. Tenancy
5. RentPayment
6. Employee
7. MaintenanceRequest
8. Supporting authentication tables

For each model:

- show the full file path;
- map every column correctly;
- add relationships;
- explain relationship direction;
- avoid unnecessary cascading deletes;
- preserve SQL Server naming and constraints;
- use readable type annotations.

Do one or two connected models at a time rather than generating every model at once.

Also create a simple test that confirms SQLAlchemy can query the mapped table.
```

---

# 27. Prompt 8: Pydantic Schemas

```text
Create the Pydantic request and response schemas for the next PropertyManager module.

For the module, include:

- create request;
- update request;
- list response;
- detailed response;
- status update request where required.

Requirements:

- distinguish required and optional fields;
- validate email addresses;
- validate positive currency values;
- validate date relationships;
- prevent clients from directly setting system-controlled fields;
- support ORM model conversion;
- use clear validation messages.

Explain why separate create, update and response schemas are useful.

Only implement schemas for one module at a time.
```

---

# 28. Prompt 9: Repository and Service Pattern

```text
Implement the repository and service layers for the next PropertyManager module.

The repository should handle database access.

The service should handle business rules.

The API route should handle HTTP concerns only.

Include:

- list with pagination;
- search;
- filtering;
- get by ID;
- create;
- update;
- activate or deactivate;
- safe delete behaviour;
- duplicate validation;
- not-found handling;
- tests.

Keep the pattern simple and consistent.

Explain the full request flow:

React request -> FastAPI route -> service -> repository -> SQL Server -> response.

Complete only one module in this response.
```

---

# 29. Prompt 10: Authentication

```text
Implement secure authentication for PropertyManager.

Requirements:

- Users table connected to Employees.
- Password hashing.
- Login with email and password.
- JWT access token.
- Refresh token.
- Current-user endpoint.
- Active-user validation.
- Role-based permissions.
- Administrator, PropertyManager, MaintenanceEmployee and ReadOnly roles.
- Protected routes.
- Change-password functionality.
- Safe authentication error messages.
- Environment-based secret keys.
- Automated tests.

Explain:

- hashing versus encryption;
- access tokens versus refresh tokens;
- how protected dependencies work;
- where the frontend should store authentication state;
- security limitations of the initial implementation.

Never store or log plain-text passwords or tokens.
```

---

# 30. Prompt 11: Landlord Module

```text
Build the complete PropertyManager landlord backend module.

Include:

- SQLAlchemy model review;
- Pydantic schemas;
- repository;
- service;
- API routes;
- pagination;
- search by name, company, email or phone;
- active and inactive filter;
- duplicate email handling;
- landlord details;
- landlord property list;
- safe deactivation;
- role permissions;
- automated tests.

Do not permanently delete a landlord who owns active properties.

At the end, give me manual Swagger tests for every endpoint.
```

---

# 31. Prompt 12: Property Module

```text
Build the complete PropertyManager property backend module.

Include:

- create property;
- edit property;
- list properties;
- property details;
- search by reference or address;
- filter by landlord, city, type and status;
- pagination and sorting;
- landlord validation;
- unique property reference;
- monthly rent validation;
- property status changes;
- current tenancy information;
- tenancy history;
- maintenance history;
- payment summary;
- permissions;
- tests.

Do not allow a property with active records to be permanently deleted.

Explain how property status should stay consistent with tenancy status.
```

---

# 32. Prompt 13: Tenant Module

```text
Build the complete PropertyManager tenant backend module.

Include:

- create tenant;
- edit tenant;
- tenant list;
- tenant details;
- search by name, email or phone;
- active and inactive filtering;
- date-of-birth validation;
- duplicate email handling;
- tenancy history;
- current tenancy;
- payment history;
- safe deactivation;
- permissions;
- tests.

Do not permanently delete a tenant with an active tenancy.
```

---

# 33. Prompt 14: Tenancy Module

```text
Build the complete PropertyManager tenancy backend module.

This module requires strong business validation.

Include:

- create draft tenancy;
- update tenancy;
- activate tenancy;
- end tenancy;
- cancel tenancy;
- tenancy details;
- list and filtering;
- tenancies ending within 30, 60 and 90 days;
- property and tenant validation;
- start-date and end-date validation;
- monthly rent validation;
- payment due day validation;
- prevention of overlapping property tenancies;
- automatic property status updates;
- role permissions;
- audit entries;
- automated tests.

Write tests for at least:

1. valid tenancy creation;
2. invalid date ordering;
3. overlapping tenancy;
4. inactive property;
5. inactive tenant;
6. tenancy activation;
7. tenancy ending;
8. property status update.

Explain the transaction handling used when tenancy and property records change together.
```

---

# 34. Prompt 15: Rent Payment Module

```text
Build the PropertyManager rent payment backend module.

Include:

- create rent obligation;
- record full payment;
- record partial payment;
- list payments;
- filter by property, tenant, tenancy, status and date;
- payment history;
- overdue payment endpoint;
- amount outstanding calculation;
- automatic payment status;
- payment reference validation;
- cancellation rather than permanent deletion;
- permissions;
- audit logging;
- tests.

Business rules:

- Pending when nothing has been paid and the due date has not passed.
- Partially Paid when the amount paid is greater than zero but below the amount due.
- Paid when the amount paid is equal to or greater than the amount due.
- Overdue when the due date has passed and the full amount has not been paid.
- Cancelled records are excluded from normal totals.

Keep calculations centralized in the service layer.
```

---

# 35. Prompt 16: Maintenance Module

```text
Build the complete PropertyManager maintenance request backend module.

Include:

- create request;
- edit request;
- assign employee;
- change priority;
- change status;
- add notes;
- enter estimated cost;
- enter actual cost;
- complete request;
- cancel request;
- search and filtering;
- employee workload;
- maintenance history by property;
- permissions;
- audit logging;
- tests.

Business rules:

- Every request belongs to a property.
- Completed requests require completion date and resolution notes.
- Costs cannot be negative.
- Emergency requests must be easy to identify.
- Maintenance employees may only update permitted fields.
- Inactive employees cannot receive new assignments.
```

---

# 36. Prompt 17: Dashboard API

```text
Create the PropertyManager dashboard API.

Return:

- total active properties;
- occupied properties;
- vacant properties;
- occupancy percentage;
- active tenancies;
- rent due this month;
- rent collected this month;
- outstanding rent;
- open maintenance requests;
- emergency maintenance requests;
- tenancies ending soon;
- recent activity;
- monthly rent collection chart data;
- maintenance status chart data.

Requirements:

- use efficient SQL queries;
- avoid loading unnecessary full records;
- explain each calculation;
- handle empty databases;
- prevent division by zero;
- return predictable response schemas;
- add tests using the demo data.
```

---

# 37. Prompt 18: React Foundation

```text
Create the initial React frontend for PropertyManager.

Set up:

- folder structure;
- routing;
- API client;
- environment configuration;
- authentication context;
- protected routes;
- login page;
- main application layout;
- sidebar navigation;
- header;
- loading indicator;
- global error handling;
- unauthorized page;
- not-found page.

Use plain React and readable CSS.

Do not create all business pages yet.

Explain:

- component responsibilities;
- routing flow;
- authentication flow;
- API request flow;
- how to run the frontend;
- how to connect it to FastAPI.
```

---

# 38. Prompt 19: Reusable Frontend Components

```text
Create reusable React components for PropertyManager.

Include:

- PageHeader
- DataTable
- Pagination
- SearchInput
- FilterPanel
- StatusBadge
- LoadingSpinner
- ErrorMessage
- ConfirmationDialog
- FormField
- SelectField
- DateField
- CurrencyField
- EmptyState
- KPI card

Requirements:

- keep components generic;
- support loading and error states;
- support accessibility;
- avoid unnecessary complexity;
- demonstrate each component with one simple example;
- explain which components will be reused across modules.
```

---

# 39. Prompt 20: Frontend CRUD Module

Use this prompt separately for landlords, properties, tenants and employees.

```text
Build the complete React frontend for the [MODULE NAME] module.

Include:

- list page;
- search;
- filters;
- pagination;
- loading state;
- empty state;
- error state;
- details page;
- create form;
- edit form;
- client-side validation;
- server validation messages;
- activation and deactivation;
- confirmation dialog;
- success notification;
- role-based action buttons;
- API service functions.

Use the existing reusable PropertyManager components.

Show every file path and explain how the page communicates with FastAPI.

Stop after this module works.
```

---

# 40. Prompt 21: Tenancy Frontend

```text
Build the PropertyManager React tenancy module.

Include:

- tenancy list;
- search and filters;
- tenancy details;
- create draft tenancy form;
- property selector;
- tenant selector;
- start and end dates;
- rent and deposit fields;
- payment due day;
- activate action;
- end action;
- cancel action;
- clear tenancy status badges;
- ending-soon page;
- display of backend business-rule errors;
- confirmation dialogs;
- role permissions.

Do not duplicate backend validation logic unnecessarily. The backend remains the final authority.
```

---

# 41. Prompt 22: Payments Frontend

```text
Build the PropertyManager React rent payment module.

Include:

- payment list;
- overdue page;
- due-this-month page;
- filters;
- payment details;
- record-payment form;
- partial payment support;
- outstanding balance;
- payment status badges;
- payment history by tenancy;
- cancel-payment action for authorized users;
- confirmation dialog;
- CSV export button;
- loading and error states.

Display currency consistently and clearly distinguish amount due, amount paid and amount outstanding.
```

---

# 42. Prompt 23: Maintenance Frontend

```text
Build the PropertyManager React maintenance module.

Include:

- maintenance request list;
- filters by status, priority, category, property and employee;
- create request form;
- request details;
- assign employee;
- update status;
- add notes;
- cost fields;
- complete request form;
- maintenance timeline;
- emergency highlighting;
- employee-specific assigned-work view;
- permission-based controls;
- loading and error states.

Use confirmation for completion and cancellation.
```

---

# 43. Prompt 24: Dashboard Frontend

```text
Build the PropertyManager React dashboard.

Include:

- KPI cards;
- occupancy chart;
- monthly rent collection chart;
- maintenance status chart;
- overdue rent attention list;
- tenancies ending soon;
- emergency maintenance list;
- recent activity;
- loading skeletons;
- empty states;
- API error state;
- responsive layout.

Use the existing dashboard API.

Every KPI must come from backend data. Do not calculate important financial totals from incomplete frontend lists.
```

---

# 44. Prompt 25: Reports and CSV Export

```text
Build the PropertyManager reporting feature.

Implement the 10 MVP reports.

For each report include:

- report title;
- description;
- filters;
- results table;
- loading state;
- no-results state;
- error state;
- totals where relevant;
- CSV export;
- print-friendly layout.

The backend must apply filters and create export data.

Do not export information the logged-in role is not allowed to view.

Start with one report and create a reusable reporting pattern before implementing the remaining reports.
```

---

# 45. Prompt 26: Automated Tests

```text
Review the PropertyManager backend and create a complete testing plan.

Separate tests into:

- unit tests;
- service tests;
- repository tests;
- API integration tests;
- authentication tests;
- permission tests;
- database constraint tests.

Prioritize these business risks:

- overlapping tenancies;
- incorrect property status;
- incorrect overdue rent;
- unauthorized access;
- invalid status transitions;
- duplicate references;
- inactive users;
- deleting connected records;
- incorrect dashboard totals.

Create tests one module at a time.

For each test explain:

- what risk it covers;
- test setup;
- action;
- expected result;
- cleanup requirements.

Do not write meaningless tests that only confirm that mocked code returns the mocked value.
```

---

# 46. Prompt 27: Security Review

```text
Perform a security review of my PropertyManager application.

Review:

- authentication;
- password storage;
- JWT handling;
- refresh tokens;
- authorization;
- role checks;
- environment variables;
- CORS;
- SQL injection risk;
- user input;
- error responses;
- audit logs;
- sensitive data exposure;
- inactive users;
- frontend token handling;
- secrets in Git history;
- production configuration.

For every issue provide:

1. Severity.
2. File or area affected.
3. Why it matters.
4. Exact recommended fix.
5. A test that confirms the fix.

Do not rewrite the whole application. Prioritize the highest-risk issues first.
```

---

# 47. Prompt 28: Code Review

```text
Review the following PropertyManager code as a senior developer.

Check for:

- correctness;
- security;
- business-rule errors;
- database transaction problems;
- unnecessary complexity;
- repeated code;
- naming;
- error handling;
- performance;
- test coverage;
- maintainability.

Use this format:

1. Critical problems.
2. Important improvements.
3. Minor improvements.
4. What is already good.
5. Corrected code.
6. Tests I should run.

Do not change the architecture merely because another approach is fashionable.

Here is the file:

[PASTE FILE]
```

---

# 48. Prompt 29: Debugging

```text
Help me debug this PropertyManager problem.

Do not guess.

First analyze:

- the complete error message;
- the command or action that caused it;
- the relevant file;
- the expected result;
- the actual result.

Then provide:

1. Most likely cause.
2. Evidence supporting that cause.
3. Smallest safe fix.
4. Exact code changes.
5. Test steps.
6. What to check if the fix fails.

Do not rewrite unrelated files.

Error message:

[PASTE COMPLETE ERROR]

Relevant code:

[PASTE CODE]

Action that caused it:

[DESCRIBE ACTION]
```

---

# 49. Prompt 30: Database Performance Review

```text
Review the PropertyManager SQL Server database for performance.

Check:

- missing indexes;
- unnecessary indexes;
- foreign-key indexes;
- report query performance;
- search performance;
- pagination;
- sorting;
- functions applied to indexed columns;
- unnecessary SELECT * usage;
- repeated queries;
- ORM N+1 queries;
- dashboard query efficiency.

Do not recommend indexes without explaining which query benefits.

For each recommendation provide:

- affected query;
- current problem;
- proposed index or query change;
- expected benefit;
- possible disadvantage;
- how to compare execution plans.
```

---

# 50. Prompt 31: Deployment

```text
Create a deployment plan for PropertyManager.

The application contains:

- React frontend;
- FastAPI backend;
- SQL database;
- environment variables;
- JWT authentication.

Provide:

1. Recommended deployment architecture.
2. Production database setup.
3. Backend deployment.
4. Frontend deployment.
5. CORS configuration.
6. HTTPS requirements.
7. Environment variables.
8. Database migration process.
9. Demo data process.
10. Logging.
11. Health checks.
12. Backup considerations.
13. Rollback plan.
14. Post-deployment testing checklist.

Do not assume that local development secrets can be reused in production.

Give me one deployment step at a time, beginning with preparing the repository.
```

---

# 51. Prompt 32: Professional README

```text
Write a professional GitHub README for PropertyManager.

Include:

- project overview;
- business problem;
- main features;
- screenshots section with placeholders;
- technology stack;
- architecture;
- database structure;
- installation;
- environment variables;
- backend setup;
- frontend setup;
- running tests;
- demo login placeholder;
- API documentation;
- project roadmap;
- known limitations;
- lessons learned;
- author section.

Make it suitable for recruiters and software development interviews.

Do not make false claims about features that are not implemented. Mark unfinished features clearly.
```

---

# 52. Prompt 33: Final Project Audit

```text
Perform a final release audit of PropertyManager.

Check whether it is ready for:

- live deployment;
- GitHub publication;
- recruiter review;
- technical interviews;
- demonstration to users.

Review:

- feature completeness;
- broken workflows;
- authentication;
- permissions;
- validation;
- database integrity;
- testing;
- security;
- accessibility;
- responsiveness;
- error handling;
- performance;
- documentation;
- demo data;
- deployment configuration.

Produce a release checklist divided into:

- release blockers;
- should fix;
- optional improvements;
- completed items.

Do not mark an item complete unless the evidence I provide confirms it.
```

---

# 53. Prompt 34: Interview Preparation

```text
Help me prepare to explain PropertyManager in a software developer interview.

Ask me to explain:

- the business problem;
- application architecture;
- database relationships;
- why I selected FastAPI;
- authentication;
- role permissions;
- overlapping tenancy prevention;
- rent payment logic;
- database transactions;
- testing;
- deployment;
- difficult bugs;
- decisions and trade-offs;
- what I would build next.

After each answer:

1. Score it from 1 to 10.
2. Explain what was good.
3. Explain what was missing.
4. Give an improved interview answer.
5. Ask one realistic follow-up question.

Keep the interview suitable for a junior software developer position.
```

---

# 54. Prompt 35: Daily Development Session

Use this at the start of each coding session.

```text
I have approximately [TIME AVAILABLE] for today's PropertyManager development session.

My current milestone is:

[CURRENT MILESTONE]

What I completed last time:

[COMPLETED WORK]

Current problems:

[PROBLEMS]

Create a focused session plan containing:

1. One main objective.
2. No more than three development tasks.
3. Files likely to change.
4. Tests to run.
5. Definition of done.
6. Suggested Git commit message.

Keep the work achievable within the available time.

Do not introduce a new feature until the current feature is tested.
```

---

# 55. Prompt 36: Continue From Existing Work

```text
Continue helping me build PropertyManager from its current state.

Current repository tree:

[PASTE REPOSITORY TREE]

Last completed feature:

[PASTE FEATURE]

Files relevant to the next task:

[PASTE FILES]

Tests currently passing:

[PASTE TEST RESULTS]

Next task:

[DESCRIBE ONE TASK]

Preserve all working functionality.

Before changing code:

1. Explain the proposed change.
2. Identify the files affected.
3. Identify possible risks.

Then provide the smallest complete implementation and its tests.
```

---

# 56. Rules for Using the Prompts

## Do not ask AI to build everything at once

Avoid prompts such as:

```text
Build me a complete property management application.
```

That normally produces:

* incomplete files;
* mismatched code;
* missing business logic;
* insecure authentication;
* difficult debugging;
* code you do not understand.

## Work one vertical feature at a time

A good order is:

1. Database table
2. SQLAlchemy model
3. Pydantic schemas
4. Repository
5. Service
6. API route
7. Backend tests
8. Frontend API service
9. React page
10. Manual test
11. Git commit

## Always test before continuing

After every feature:

* Start the backend.
* Open Swagger.
* Test successful requests.
* Test invalid requests.
* Test unauthorized requests.
* Check the database.
* Run automated tests.
* Commit working code.

## Always provide the AI with the real file

Do not say:

```text
Fix my tenancy service.
```

Instead paste:

* the exact error;
* the relevant file;
* related schemas;
* the expected behaviour;
* test results.

## Keep Git commits small

Examples:

```text
feat: add landlord database model
feat: implement landlord CRUD API
test: add landlord service tests
feat: add property listing page
fix: prevent overlapping tenancies
docs: add local setup instructions
```

---

# 57. Recommended Starting Sequence

Begin with these steps:

## Step 1

Create a new GitHub repository named:

```text
property-management-system
```

## Step 2

Save this project scope inside:

```text
documentation/project-scope.md
```

## Step 3

Use **Prompt 1: Architecture and Setup**.

## Step 4

Use **Prompt 2: Database Design Review**.

## Step 5

Review the database design before generating SQL.

## Step 6

Use **Prompt 3: Create SQL Scripts**.

## Step 7

Run every database script manually and fix all errors.

## Step 8

Use **Prompt 4: Demo Data**.

## Step 9

Use **Prompt 5: SQL Report Queries**.

## Step 10

Only then begin the FastAPI backend.

---

# 58. First Prompt to Use Now

Copy and paste this prompt first:

```text
Act as my senior full-stack software development mentor.

I am beginning a portfolio-quality property management system called PropertyManager.

My stack will be:

- SQL Server
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication
- React
- JavaScript
- Git and GitHub

The application will initially support one property management company with multiple employees.

The core business modules are:

- Landlords
- Properties
- Tenants
- Tenancies
- Rent payments
- Maintenance requests
- Employees
- Dashboard
- Reports

I use Windows and I am learning while building.

Help me create the initial project architecture and local development setup.

Create:

1. The repository structure.
2. The backend folder structure.
3. The frontend folder structure.
4. The database scripts folder.
5. The documentation folder.
6. A suitable .gitignore.
7. Backend and frontend .env.example files.
8. A development setup checklist.
9. Windows-compatible commands to create the folders.
10. The first Git commit.

Do not build any business features yet.

Explain each command and file simply. Stop once the initial project structure is ready so that I can test it before continuing.
```
