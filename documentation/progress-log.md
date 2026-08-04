# PropertyManager — Progress Log & Handoff Notes

Read this first if you're picking this project back up in a new conversation
(new Claude session, different tool, or a human). It captures conventions
and decisions that aren't obvious just from reading the code, so you don't
have to re-derive them.

Last updated: 2026-08-04, after completing the Reusable Frontend Components (Prompt 19).

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
- **Dashboard API** — read-only, 5 endpoints (`/summary`, `/rent-summary`, `/occupancy`, `/maintenance-summary`, `/recent-activity`), no Create/Update schemas at all. See "Dashboard module" below for the calculation/permission details.

**332/332 backend tests passing.** Demo data counts verified intact after every module (5 landlords, 10 properties, 12 tenants, 12 tenancies, 30 rent payments, 20 maintenance requests, 8 maintenance notes, 5 employees/users).

**Frontend: React foundation + reusable component library done** (`frontend/`, plain React + JavaScript + CSS, Vite, react-router-dom, axios - per the scope doc's explicit "use plain React and readable CSS", no TypeScript/Tailwind/component library). Routing, API client with silent-refresh-on-401, auth context, protected routes, login/home/unauthorized/404 pages, sidebar+header layout, and all 15 of Prompt 19's reusable components. See "Frontend foundation" and "Reusable component library" below for the full breakdown. No business-module pages yet, deliberately (see those sections).

**Not started yet:** frontend business modules (Landlords, Properties, Tenants, Tenancies, Payments, Maintenance, Employees, Dashboard); deployment.

## Next steps, in order

Follow `documentation/project-scope.md`'s own sequence (section 57 / the numbered prompts):

1. **Prompt 20+: one frontend module at a time** — Landlords, Properties, Tenants, Tenancies, Payments, Maintenance, Employees, each following the same repo-established "API service → page → manual test" flow (see `frontend/src/services/authService.js` as the template for a module's API service file, and `frontend/src/components/` for the DataTable/Pagination/FormField/etc. every list/form page should build on rather than reinventing).
2. **Then the Dashboard frontend** (KPI cards, charts, report filters, CSV export) — replaces the placeholder `HomePage.jsx`, and is the first real consumer of `KpiCard`.
3. **Then testing/deployment** (later milestones).

## Frontend foundation: how to run it, and the decisions worth knowing before touching it again

**How to run:**
- Backend: `venv\Scripts\python.exe -m uvicorn app.main:app --reload` from `backend/` (as before).
- Frontend: `npm install` (first time only), then `npm run dev` from `frontend/` - serves on `http://localhost:5173`, matching the backend's `CORS_ALLOWED_ORIGINS` default.
- `frontend/.env` (gitignored, copy from `.env.example`) sets `VITE_API_BASE_URL` - defaults to `http://localhost:8000/api`.
- Demo login: any of the 5 seeded accounts (see the table above), password `Password123!`.

**Folder structure** (`frontend/src/`): `api/` (the one shared Axios instance), `services/` (one file per backend module, each just wrapping that module's endpoints - `authService.js` is the template), `contexts/` (React Context providers - just `AuthContext` so far), `routes/` (routing helpers like `ProtectedRoute`), `layouts/` (the authenticated app shell - `MainLayout`/`Sidebar`/`Header`), `pages/` (one component per route), `components/` (generic, reusable-across-pages pieces - just `LoadingSpinner`/`ErrorBoundary` so far, Prompt 19 adds the rest), `utilities/` (small stateless helpers like `apiError.js`), `styles/global.css` (the only stylesheet - plain CSS with variables, no framework).

**Token storage - a deliberate, documented compromise, not an oversight:** the access token lives in memory only (a module-level variable in `api/client.js`), never in any Web Storage - readable-by-JS storage is readable by an XSS payload too. The refresh token *should* live in an httpOnly cookie the browser attaches automatically, but `backend/app/api/routes/auth.py`'s own docstring already flags that the backend currently issues it as a plain JSON field, not a cookie - there is nothing for the browser to attach automatically yet. Given that backend limitation, the frontend stores the refresh token in `sessionStorage` (cleared when the tab closes, unlike `localStorage`) so a page reload doesn't force a re-login. Upgrading to real httpOnly-cookie delivery needs a backend change and is deferred, same category as the backend's own already-deferred items (refresh token revocation, login rate limiting).

**Session restore on page load:** there's no access token to restore (it's memory-only, gone on reload) - `AuthContext`'s mount effect instead checks for a stored refresh token and, if found, silently calls `/auth/refresh` then `/auth/me` to rebuild the session. Verified working end-to-end via the Browser tool: login → full page reload → still authenticated, with the network log showing `/auth/refresh` + `/auth/me` firing on reload rather than a redirect to `/login`. (You'll see `/auth/refresh` fire twice in dev tools during that check - that's React 18 StrictMode double-invoking the mount effect in development only, not a real bug; production builds don't do this.)

**401 handling:** `api/client.js`'s response interceptor catches a 401, attempts exactly one silent refresh (deduplicated via a shared in-flight promise if multiple requests 401 at once), and retries the original request. Only on refresh failure does it clear the session and notify `AuthContext` (via a registered callback, since an Axios interceptor can't use React hooks) - `/auth/*` requests themselves are excluded from this retry loop to avoid an infinite cycle.

**Sidebar shows every future module already, mostly disabled:** `Sidebar.jsx`'s `NAV_ITEMS` lists all 7 business modules plus Dashboard; only Dashboard (`path: "/"`, currently the placeholder `HomePage`) is a real link today. As each module's frontend gets built, flip its `path: null` to a real route - this was a deliberate choice over omitting the links entirely, so the overall app shape is visible even before every module exists.

**`ProtectedRoute` already supports role-gating (`allowedRoles` prop) even though nothing uses it yet** - no business pages exist this early to need it. Wire it up per-module as role-restricted pages get built (e.g. an Employees page would pass `allowedRoles={["Administrator", "PropertyManager"]}`, matching `CAN_VIEW_EMPLOYEES` on the backend).

## Reusable component library (Prompt 19)

All 15 live in `frontend/src/components/`, flat (no subfolders) to match the existing structure. Verified via the Browser tool at `/dev/components` (see below) - every component renders, and the interactive ones (SearchInput's debounce, Pagination's page change, FormField's validation error, ConfirmationDialog's open/focus/Escape-to-cancel, FilterPanel's collapse) were exercised for real, not just visually inspected.

**Which modules will reuse which** (so the next session doesn't have to re-derive this):
- **Every list page** (Landlords, Properties, Tenants, Tenancies, RentPayments, Maintenance, Employees): `PageHeader` (title + a "+ New X" action), `DataTable` + `Pagination` bound to that module's `PaginatedResponse` shape, `SearchInput` + `FilterPanel` for the search/filter query params every backend list endpoint already accepts, `StatusBadge` for whichever status/priority column it has.
- **Every create/edit form**: `FormField` (most text fields), `SelectField` (PropertyType, TenancyStatus, PaymentMethod, Priority, Category, ...), `DateField` (StartDate/EndDate/DueDate/HireDate/...), `CurrencyField` (MonthlyRent, AmountDue, EstimatedCost/ActualCost, ...), all sharing `FieldShell`'s label/error/aria wiring internally (not itself one of the 15 - see FieldShell.jsx).
- **Every destructive action** (deactivate, cancel): `ConfirmationDialog`.
- **The real Dashboard page** (replacing `HomePage.jsx`): `KpiCard` for the `/api/dashboard/summary` figures.
- **Everywhere a request is in flight or fails**: `LoadingSpinner` (already used by `ProtectedRoute` during session restore) and `ErrorMessage` - both already built into `DataTable` directly, so a list page gets loading/error handling for free just by using `DataTable`.
- **Anywhere a list/section can legitimately be empty**: `EmptyState` (also built into `DataTable` for zero rows).

**Design decisions worth knowing before extending this further:**
- `StatusBadge` infers a color ("tone") from the status text itself via a lowercase keyword map (`TONE_BY_STATUS` in `StatusBadge.jsx`) covering every status/priority string used across all 7 backend modules - so `<StatusBadge status={payment.PaymentStatus} />` just works without the caller thinking about color. An explicit `tone` prop overrides the map for anything a specific module wants to treat differently.
- `FieldShell` (internal, used by `FormField`/`SelectField`/`DateField`/`CurrencyField`, not itself one of Prompt 19's named components) takes its `children` as a **render prop** (`(fieldProps) => <input {...fieldProps} />`), not a plain element cloned via `cloneElement`. This was a deliberate fix mid-build: `CurrencyField` needs to wrap its `<input>` in a currency-symbol `<span>`, and `cloneElement` would have put the generated `id`/`aria-*` props on the wrong (outer) element. The render-prop form works for both the simple fields and the wrapped one.
- `ConfirmationDialog` is intentionally not a full focus-trap implementation (no dependency added for it) - it moves focus to Cancel on open (so an accidental Enter doesn't confirm a destructive action) and closes on Escape or backdrop click, which covers the cases that matter most for a dialog this simple. Revisit if a future module's use case needs real focus trapping.
- `/dev/components` (`ComponentShowcasePage.jsx`) is a dev-only reference page, deliberately not linked from the sidebar - it exists to satisfy Prompt 19's "demonstrate each component with one simple example" concretely (reachable and testable in a real browser), not as a permanent part of the app. Fine to delete once every module is built and exercising these components for real.

## Dashboard module: calculations, permission shape, and one SQL Server gotcha avoided

- `app/core/roles.py`: `CAN_VIEW_DASHBOARD` = Administrator/PropertyManager/ReadOnly - same shape as `CAN_VIEW_MAINTENANCE`. MaintenanceEmployee is excluded because the dashboard mixes financial figures (rent collected, outstanding rent) in with operational ones, and the scope doc explicitly bars MaintenanceEmployee from "financial reports." All 5 routes share one role gate, set once on the `APIRouter(dependencies=[...])` itself in `app/api/routes/dashboard.py`, rather than repeating `dependencies=[Depends(require_roles(...))]` on every individual route.
- **Every count/sum method in `DashboardRepository` returns a pre-aggregated number, not a list of rows** - the scope doc's "avoid loading unnecessary full records." The one exception is `recent_activity`, which is inherently a list to display; it's capped with `limit` and eager-loads `AuditLog.User.Employee` via `joinedload` to avoid an N+1 query per row.
- **Every percentage goes through `DashboardService.safe_percentage`**, a pure function (same testability pattern as `RentPaymentService.calculate_payment_status`) that returns `0.0` for a zero denominator instead of raising - this is what "handle empty databases" / "prevent division by zero" actually means in code here, and it's unit-tested directly with `safe_percentage(0, 0)`.
- **`OutstandingRent` is deliberately broader than SQL Report 2's "Overdue"**: it sums every non-cancelled payment's unpaid balance regardless of whether the due date has passed yet (Pending obligations not yet due still count as "money owed" for this KPI), where Report 2 requires the due date to already be in the past. Don't "fix" `DashboardRepository.outstanding_rent` to match Report 2's stricter filter - they intentionally answer different questions.
- **Avoided repeating the SQL Server `GROUP BY` gotcha from the Maintenance module** (see that section above): every grouped dashboard query selects individual columns (`Property.PropertyStatus`, `MaintenanceRequest.MaintenanceStatus`, etc.), never a whole mapped entity.
- **`DATENAME(MONTH, ...)`'s datepart argument must be a literal T-SQL keyword, not a bindable parameter** - trying to build the "May 2026"-style month label in SQL via `func.datename("month", ...)` doesn't compose through SQLAlchemy (the datepart would be sent as a bound string parameter, which SQL Server rejects). `DashboardRepository.monthly_rent_collection` only returns raw `(Year, Month, ...)` integers; `DashboardService.get_rent_summary` builds the human-readable label in Python with `calendar.month_name` instead.
- Maintenance priority ordering (Emergency first, matching Report 8's `CASE` expression) is done in Python (`DashboardService._PRIORITY_RANK` + `sorted(...)`) rather than duplicated as SQL - the result set is at most ~20 rows, trivial to sort in Python and easier to unit test.

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
