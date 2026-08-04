# PropertyManager — Progress Log & Handoff Notes

Read this first if you're picking this project back up in a new conversation
(new Claude session, different tool, or a human). It captures conventions
and decisions that aren't obvious just from reading the code, so you don't
have to re-derive them.

Last updated: 2026-08-04, after completing the Employees module.

## Where things stand

**Done and verified (tests pass + manually exercised against the live server):**

- Repo scaffold, `.gitignore`, `.env.example` (backend + frontend)
- Database: schema (`database/01-05`), demo data (`06`), 10 MVP SQL reports (`07`)
- FastAPI foundation: config, logging, CORS, centralized error handling, health check
- SQLAlchemy models for all 12 tables
- Authentication: bcrypt hashing, JWT access/refresh tokens, login/refresh/logout/me/change-password, role-based route protection
- Six full vertical modules (repository → service → API → tests), each following the *same* pattern:
  - **Landlords** — duplicate-email handling, safe deactivate (blocks if active properties)
  - **Properties** — landlord validation, unique reference, status changes, safe deactivate (blocks if active tenancies)
  - **Tenants** — date-of-birth validation, safe deactivate (blocks if active tenancy)
  - **Tenancies** — the complex one: Draft→activate→end/cancel lifecycle, overlap prevention (checked only at activation), automatic property status sync, audit logging
  - **RentPayments** — Pending/Partially Paid/Paid/Overdue status computed LIVE on every response (not just trusted from the stored column - see "RentPayment status" below), additive record-payment (supports multiple partial payments), cancel instead of delete, overdue/due-this-month endpoints matching SQL Reports 2/1 exactly
  - **Maintenance** — the first module where MaintenanceEmployee has real write access, not just "no access" (see "Maintenance module: permission shape" below); several independent action endpoints (assign/change-priority/change-status/notes/costs/complete/cancel) instead of one big edit; employee workload aggregation endpoint
  - **Employees** — narrower permission shape than every other simple-CRUD module (Administrator-only management; Administrator+PropertyManager view; ReadOnly and MaintenanceEmployee get neither - see "Employees module: permission shape and the User cascade" below); safe deactivate blocks on open maintenance assignments (reuses `MaintenanceRepository.OPEN_STATUSES`); deactivation cascades to the linked `User.IsActive`, one-way only

**299/299 backend tests passing.** Demo data counts verified intact after every module (5 landlords, 10 properties, 12 tenants, 12 tenancies, 30 rent payments, 20 maintenance requests, 8 maintenance notes, 5 employees/users).

**Not started yet:** Dashboard API; all frontend work; deployment.

## Next steps, in order

Follow `documentation/project-scope.md`'s own sequence (section 57 / the numbered prompts):

1. **Prompt 17: Dashboard API** — aggregates from all the above (active/occupied/vacant properties, occupancy %, active tenancies, rent due/collected this month, outstanding rent, open/emergency maintenance, tenancies ending soon, recent activity, chart data). Efficient SQL, no full-record loads, handle empty DB, avoid division-by-zero.
2. **Then frontend** (Prompt 18+): React foundation, reusable components, one module at a time.
3. **Then testing/deployment** (later milestones).

## Employees module: permission shape and the User cascade

- `app/core/roles.py`: `CAN_MANAGE_EMPLOYEES` is Administrator-only (the scope doc lists "Manage employees" under Administrator only, not PropertyManager - unlike every earlier simple-CRUD module where both roles manage). `CAN_VIEW_EMPLOYEES` adds PropertyManager (they need to see who's available when assigning maintenance work) but not ReadOnly or MaintenanceEmployee - employee records are treated as the "employee administration" MaintenanceEmployee is explicitly barred from, and ReadOnly's documented scope never mentions staff data.
- Role assignment (RoleName, listed in the scope doc's Employees "suggested fields") is deliberately NOT an Employee schema field - the actual implemented schema puts roles on Users/UserRoles (see `auth_service.py`), so it lives in a not-yet-built Users admin module, not here.
- **Deactivating an Employee cascades to their linked `User.IsActive = False`** (if a User account exists) - `EmployeeService._deactivate_linked_user`. This is necessary for "Inactive employees cannot log in" to actually hold: login (`get_current_user`) checks `User.IsActive`, a different row than `Employee.IsActive`, so without this an inactive employee could still log in. **The cascade is one-way** - reactivating an Employee does NOT restore `User.IsActive`. Account access is treated as the more sensitive, separate Administrator capability ("Create and deactivate user accounts") that the scope doc lists apart from "Manage employees" - auto-restoring login on employee reactivation would grant access through a side door around that still-to-be-built, more deliberate control.
- Safe-deactivate blocks on `EmployeeRepository.has_open_maintenance_assignments`, which reuses `MaintenanceRepository.OPEN_STATUSES` as the single source of truth for "open" rather than redefining that status list a second time.

## Maintenance module: permission shape (worth re-reading before touching this module again)

Maintenance is the one module where MaintenanceEmployee has real write access (scope doc section 4), but only a narrow slice of it, and only on their own assigned requests - this needed a data-level check that no route-level role tuple alone can express:

- `app/core/roles.py`: `CAN_MANAGE_MAINTENANCE` (Administrator/PropertyManager - create/edit/assign/change-priority/cancel) is separate from `CAN_UPDATE_MAINTENANCE_WORK` (adds MaintenanceEmployee - change-status/notes/costs/complete). `CAN_ACCESS_MAINTENANCE` (adds MaintenanceEmployee again) gates list/get.
- Passing the role gate is necessary but not sufficient for MaintenanceEmployee: `MaintenanceService._assert_can_update_work` additionally checks `request.AssignedEmployeeId == actor.EmployeeId` and raises `MAINTENANCE_NOT_ASSIGNED_TO_YOU` (403) otherwise. `_is_restricted_to_own_work` does the equivalent for list/get, silently narrowing (never widening) their view to their own assignments.
- Every demo User row has a non-null `EmployeeId` (verified from `06-seed-demo-data.sql`), so `actor.EmployeeId` is always safe to use directly for notes/assignment-comparison - no null-handling needed there.

Completed/Cancelled are terminal (same one-way-door pattern as RentPayment/Tenancy) - `_assert_not_terminal` blocks edit/assign/priority/status changes once either is reached. Cost entry is the one exception: `enter_costs` still works after Completed (correcting an actual cost afterward is legitimate) and only blocks on Cancelled.

`MaintenanceStatus` can never be set to "Completed" or "Cancelled" via `POST /change-status` (schema-level `ChangeableStatusValue` excludes them) - those go through `/complete` and `/cancel` instead, which enforce their own required fields. This mirrors the DB's `CK_MaintenanceRequests_CompletionRequiresDetail` constraint (Completed requires `CompletedDate` + `ResolutionNotes`) by catching the same rule earlier, with a clean 422/409 instead of a raw constraint-violation 500.

## RentPayment status: a subtlety worth knowing before touching this module again

`PaymentStatus` is deliberately recalculated LIVE for every API response (`RentPaymentService.calculate_payment_status`), not just read from the stored DB column - a Pending payment silently becomes Overdue purely by the calendar moving on, with no write ever happening to catch that transition (no scheduled sweep job exists yet, same category as Tenancy's deferred Upcoming→Active sweep).

**A payment can be labeled "Partially Paid" AND still show up in `/api/rent-payments/overdue`, at the same time - this is intentional, not a bug.** The single status label prioritizes "some money was received" over "the date has passed" (matches the demo data's own design), while the overdue list uses a broader, more useful definition matching SQL Report 2 exactly: due date passed AND not fully paid, full stop, regardless of partial payment. If you're ever confused by this while extending the module, re-read `RentPaymentRepository.list_overdue`'s docstring and `test_rent_payment_repository.py::test_list_overdue_matches_report_2` before assuming it's wrong - it already tripped up the test-writing pass once (fixed by correcting the test's expected 2-row assertion to the correct, already-validated 4-row one, not by changing the code).

**Decimal fields serialize as JSON strings** (e.g. `"AmountDue": "1050.00"`), not JSON numbers - true for every module, not just this one. Cast with `float(...)` before comparing in tests, the way `test_property_api.py` already does.

## The established pattern (copy this for every new module)

Each business module gets, in this order:
1. `app/schemas/<module>.py` — Create/Update/Response/ListItem Pydantic schemas. `extra="forbid"` on write schemas. System-controlled fields (IDs, IsActive, timestamps, status) are never client-settable directly — either omitted entirely or behind a dedicated status/action endpoint.
2. `app/repositories/<module>_repository.py` — pure DB access, no business rules. Takes a `Session` in `__init__`.
3. `app/services/<module>_service.py` — business rules, owns the transaction (`self.db.commit()`), raises `AppError` (from `app/core/exceptions.py`) for anything the client did wrong.
4. `app/api/dependencies/<module>.py` — one-liner `get_<module>_service(db=Depends(get_db))`.
5. `app/api/routes/<module>s.py` — HTTP only. Role-gated via `dependencies=[Depends(require_roles(*CAN_...))]`, or `current_user: User = Depends(require_roles(...))` as a real parameter when the route needs the user id (e.g. for audit logging).
6. Register the router in `app/main.py`.
7. Four test files: `test_<module>_repository.py` (read-only against seeded data), `test_<module>_service.py` (throwaway rows + explicit cleanup), `test_<module>_api.py` (same, via `TestClient` + auth), `test_<module>_permissions.py` (role boundaries).
8. Run the full suite, verify demo data counts unchanged via `sqlcmd`, manually exercise key endpoints against the live server, commit.

## Real bugs hit and fixed (don't re-introduce these)

- **SQL Server won't let SQLAlchemy omit a column from INSERT unless `server_default=text(...)` is set on the `mapped_column()`**, even if the DB column has its own `DEFAULT` clause. Without it, SQLAlchemy sends an explicit `NULL` and the NOT NULL constraint rejects it. Already fixed on every model's `CreatedAt`/`UpdatedAt` (and `MaintenanceRequests.ReportedDate`) — keep doing this for any new defaulted column.
- **`Column.is_(True)`/`.is_(False)` compiles to invalid T-SQL (`IS 1`) on BIT columns** — SQL Server's `IS` only accepts `NULL`. Use plain `== True`/`== False` (with `# noqa: E712`) instead.
- **Filtered/unique indexes require `SET QUOTED_IDENTIFIER ON`** for the session — needed when running ad hoc `sqlcmd` DELETEs/INSERTs against tables that have one (Landlords, Tenants, Tenancies, Properties all do).
- **Never name a module-level Pydantic `Literal` type alias the same as the class field that uses it** (e.g. don't name both the alias and the field `PropertyStatus`) — breaks Python 3.14's deferred annotation evaluation with a confusing `NoneType | NoneType` error. Every schema file already uses distinct names (`ContactMethod`, `PropertyTypeValue`, `TenancyStatusValue`, etc.) — keep that convention.
- **`RequestValidationError.errors()` can include a raw Python exception object in each error's `ctx` field** (from custom `model_validator`/`field_validator` failures) — not JSON-serializable, crashes the response. `app/core/exceptions.py`'s handler strips `ctx` before encoding.
- **A tenancy that starts today and is ended "today" (no explicit end date) violates `EndDate > StartDate`.** `TenancyService.end_tenancy` now guards this explicitly (`TENANCY_INVALID_END_DATE`, 409) rather than letting it hit the DB constraint as a raw 500.
- **SQL Server's `GROUP BY` (unlike MySQL) requires every selected column to be aggregated or grouped-by - it will NOT infer that grouping by a primary key determines the rest of that row's columns.** `MaintenanceRepository.list_workload` originally tried `select(Employee, func.count(...), ...).group_by(Employee.EmployeeId, Employee.FirstName, Employee.LastName, Employee.IsActive)` - selecting the whole `Employee` entity pulls in every mapped column (`Email`, `Phone`, `CreatedAt`, ...), none of which were in the `GROUP BY`, and SQL Server rejected it outright (error 8120) rather than silently guessing. Fixed by selecting only the specific columns needed instead of the whole entity - keep this in mind for any future aggregation query that's tempted to `select(SomeModel, func.count(...))`.

## Testing conventions

- **Never mutate the seeded demo data in a test that doesn't clean up after itself.** Other test files assert exact counts (5 landlords, 12 tenancies, etc.) — polluting the shared local dev database breaks them in confusing, hard-to-trace ways. This bit us hard during the Tenancy module: a test that failed mid-way left real committed rows behind (SQLAlchemy commits aren't auto-rolled-back between separate `pytest` runs), which then broke the *next* run with an unrelated-looking "duplicate reference" error. If you ever see a mysterious "already exists" failure, check for orphaned rows first: `SELECT ... WHERE PropertyReference LIKE 'PM-TEST%'` (or similar) and clean up via `sqlcmd` before assuming it's a code bug.
- Explicit `try/finally` cleanup of throwaway rows is used instead of transaction-rollback fixtures — deliberately simpler than intercepting `session.commit()` via SQLAlchemy events to fake a rollback-able nested transaction. See `test_landlord_service.py`'s module docstring.
- `tests/auth_helpers.py` has the 5 demo accounts' emails and a shared `auth_headers()` helper.
- `tests/conftest.py` has an `admin_user_id` fixture (Sarah Mitchell's `UserId`) for any test needing a `user_id` for audit logging without testing auth itself.
- When a test needs a second entity (e.g. a property for a tenancy test), create it via the *other* module's service directly (e.g. `PropertyService(service.db)`), not raw SQL — keeps tests exercising real code paths.

## Demo login (local dev only)

All 5 seeded users share the password `Password123!` (real bcrypt hashes, generated via `app/core/security.py`, baked into `database/06-seed-demo-data.sql`):

| Email | Role |
|---|---|
| sarah.mitchell@propertymanager.example | Administrator |
| james.carter@propertymanager.example | PropertyManager |
| priya.patel@propertymanager.example | PropertyManager |
| daniel.osei@propertymanager.example | MaintenanceEmployee |
| emma.wilson@propertymanager.example | ReadOnly |

## Role permission matrix (so far)

Every module built so far uses the same two groups (`app/core/roles.py`):
- `CAN_VIEW_<X>` = Administrator, PropertyManager, ReadOnly
- `CAN_MANAGE_<X>` = Administrator, PropertyManager

MaintenanceEmployee has **no access** to Landlords/Properties/Tenants/Tenancies — their documented capabilities (scope doc section 4) are a narrow whitelist limited to their own assigned maintenance requests, which doesn't exist as a module yet.

## Deliberately deferred (documented in code, not accidentally missing)

- `GET /api/{landlords,properties,tenants}/{id}/{sub-resource}` (e.g. a landlord's property list, a property's tenancy history) — each needs a schema from a module that didn't exist yet when its parent module was built. Add these once the target module exists.
- Automatic tenancy status transitions (Upcoming → Active when the start date arrives; Active → "Ending Soon" as the end date approaches) — needs a scheduled sweep job, same category as RentPayments' future Pending → Overdue sweep. Not built yet anywhere.
- Refresh token revocation (logout is currently client-side-only; no server-side blacklist/table).
- Login rate limiting / account lockout (failed attempts are tracked in `Users.FailedLoginAttempts` but not enforced).

## Environment / local dev facts

- Local SQL Server: `localhost\SQLEXPRESS`, Windows/trusted auth, DB name `PropertyManagerDb`.
- Backend venv: `backend/venv/` (gitignored). Activate via `backend/venv/Scripts/python.exe`.
- Run tests: `venv\Scripts\python.exe -m pytest -v` from `backend/`.
- Run server: `venv\Scripts\python.exe -m uvicorn app.main:app --reload` from `backend/`.
- To rebuild the DB from scratch: drop `PropertyManagerDb`, then run `database/01` through `06` in order via `sqlcmd`.
- Repo lives at `C:\Users\shmil\Projects\property-management-system` (moved out of OneDrive early on — do NOT put it back under `OneDrive\Desktop`, see git history for why).
- GitHub: `https://github.com/Stern-5565/property-management-system`, branch `main`, always pushed after every module.
