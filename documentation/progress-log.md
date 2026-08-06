# PropertyManager — Progress Log & Handoff Notes

Read this first if you're picking this project back up in a new conversation
(new Claude session, different tool, or a human). It captures conventions
and decisions that aren't obvious just from reading the code, so you don't
have to re-derive them.

Last updated: 2026-08-06, after completing the Tenancy frontend module (Prompt 21).

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

**Frontend: React foundation + reusable component library + all four repeatable-CRUD modules + Tenancies done** (`frontend/`, plain React + JavaScript + CSS, Vite, react-router-dom, axios - per the scope doc's explicit "use plain React and readable CSS", no TypeScript/Tailwind/component library). Routing, API client with silent-refresh-on-401, auth context, protected routes, sidebar+header layout, all 15 of Prompt 19's reusable components, Prompt 20's four CRUD modules, and now Prompt 21 (Tenancies - the first module with its own bespoke lifecycle, not the generic CRUD shape). See "Frontend foundation", "Reusable component library", "Landlords frontend module (Prompt 20)", "Properties frontend module (Prompt 20)", "Tenants frontend module (Prompt 20)", "Employees frontend module (Prompt 20)", and "Tenancy frontend module (Prompt 21)" below.

**Not started yet:** the remaining frontend business modules (Payments, Maintenance) and the real Dashboard page; deployment.

## Next steps, in order

Follow `documentation/project-scope.md`'s own sequence (section 57 / the numbered prompts):

1. **Prompt 22: Payments frontend**, then **Prompt 23: Maintenance frontend** (see the doc for each's specific requirements - both have their own bespoke shape like Tenancies did, not the generic CRUD template).
2. **Then the Dashboard frontend** (KPI cards, charts, report filters, CSV export) — replaces the placeholder `HomePage.jsx`, and is the first real consumer of `KpiCard`.
3. **Then testing/deployment** (later milestones).

## Landlords frontend module (Prompt 20) - the template every other CRUD module should copy

**File/route shape**, now established as the convention:
- `frontend/src/services/<module>Service.js` - one file per module wrapping its REST endpoints (see `landlordService.js`).
- `frontend/src/pages/<module>/` - a **subfolder** per module (not flat in `pages/` - that only held single-file pages like `LoginPage.jsx` before this). Three files: `<Module>sListPage.jsx`, `<Module>DetailPage.jsx`, `<Module>FormPage.jsx` (one form component shared by create AND edit - branches on whether `useParams()` has an `:id`).
- Routes nest two `ProtectedRoute`s inside `MainLayout` (see `App.jsx`): the outer narrows to `CAN_VIEW_<MODULE>`, an inner one (wrapping only `/new` and `/:id/edit`) narrows further to `CAN_MANAGE_<MODULE>` - matching the backend's own view/manage role split exactly (`frontend/src/constants/roles.js` mirrors `backend/app/core/roles.py`, built up module by module as each frontend module is built, not all at once).
- Every module-specific role check (`hasAnyRole(user, CAN_MANAGE_X)`) drives which action buttons even render, not just route access - "role-based action buttons" is a real per-button check, route gating is just the defense-in-depth backstop for someone navigating directly to a URL they can't act on.

**New cross-module pieces added alongside Landlords** (not Landlords-specific, reused by every module after this):
- `frontend/src/components/Toast.jsx` - the "success notification" Prompt 20 asks for, that Prompt 19's component list didn't yet include. A page owns its own toast state (`useState`), no global store.
- The toast-across-navigation pattern: `navigate(path, { state: { toast: "..." } })` after a create/edit/action, and the receiving page reads `location.state?.toast` as its initial toast state, then immediately fires a `navigate(location.pathname, { replace: true, state: {} })` in a mount-only effect to scrub it from history (so an F5 refresh doesn't re-show it forever - `location.state` persists across reloads via the History API). See `LandlordsListPage.jsx`/`LandlordDetailPage.jsx` for the exact shape to copy.
- `frontend/src/constants/roles.js` + `frontend/src/utilities/permissions.js` (`hasAnyRole(user, allowedRoles)`) - add each module's `CAN_VIEW_X`/`CAN_MANAGE_X` pair to `roles.js` as that module's frontend gets built.
- `ConfirmationDialog` gained a `confirmDisabled` prop (prevents double-submit while an action's promise is in flight) - a Prompt 19 component extended in place, not duplicated.

**A real bug caught and fixed during manual verification** (worth remembering for every future module's detail-page action pattern): when `LandlordDetailPage`'s deactivate action failed server-side (`LANDLORD_HAS_ACTIVE_PROPERTIES`), the original code only closed `ConfirmationDialog` on the *success* path, leaving it open on error. The `ErrorMessage` banner rendered underneath the dialog's `position: fixed` backdrop (z-index), so the error was in the DOM and even in the accessibility tree, but **invisible** - the kind of bug a text-only check misses and only shows up checking real rendered visibility (`element.offsetParent !== null`) or a screenshot. Fixed by closing the dialog in a `.finally()` so it closes on both outcomes, error banner rendering visibly on the underlying page. Apply this same "close the dialog before/regardless of showing the error" shape to every other module's action-with-a-dialog flow.

**Client-side vs. server-side validation split** (`LandlordFormPage.jsx`): client-side checks only the cheap, obviously-wrong cases - required fields and the company-or-full-name rule (mirroring `LandlordWriteBase.require_company_or_full_name` in the backend schema) - so the user gets instant feedback without a round trip. Duplicate-email detection is NOT duplicated client-side; that error only ever comes from the server's response message. This is the balance to strike for every future module's form: mirror simple, static backend rules client-side; never re-implement anything that requires a database lookup.

## Properties frontend module (Prompt 20) - second module, first to expose a real backend API gap

Followed the Landlords file/route shape exactly (`services/propertyService.js`, `pages/properties/{List,Detail,Form}Page.jsx`, nested `ProtectedRoute`s with `CAN_VIEW_PROPERTIES`/`CAN_MANAGE_PROPERTIES`). Two things worth knowing that are specific to this module:

- **PropertyStatus (Vacant/Occupied/Under Maintenance/Unavailable/Archived) and IsActive (active/deactivated) are two completely separate actions on `PropertyDetailPage`**, because they're two separate backend concepts: `PropertyStatus` changes via `PATCH /status` and is freely reversible (a direct "Change status" `SelectField` + button, no confirmation dialog needed - nothing destructive about marking a property "Under Maintenance"); `IsActive` only ever goes false, via `DELETE` (blocked if the property has an active/upcoming/draft tenancy), behind the same `ConfirmationDialog` pattern as Landlords.
- **There is no "reactivate" endpoint for Properties**, unlike Landlords (`PATCH /api/landlords/{id}/status` accepts `IsActive: bool` either direction; `PropertyStatusUpdate` only ever carries the `PropertyStatus` enum, never `IsActive` - see `backend/app/services/property_service.py`, which has no `set_active_status` method at all). This is an existing, already-tested backend gap, not something introduced now - `PropertyDetailPage.jsx` reflects it honestly: once a property is deactivated, its action buttons disappear entirely and a plain "This property has been deactivated" note shows instead, rather than a client-side reactivate button that would call an endpoint that doesn't exist. **If a real reactivate capability is ever wanted, it needs a new backend endpoint first** (`PropertyService.set_active_status`, mirroring `LandlordService`'s), not a frontend-only fix.
- The landlord dropdown in `PropertyFormPage` (and the landlord filter in `PropertiesListPage`) both call `landlordService.listLandlords({ isActive: true, pageSize: 100 })` directly - no new shared "options loader" abstraction was introduced for just two call sites. `PropertyDetailPage` also does one extra `getLandlord(property.LandlordId)` call to show the owning landlord's display name (linked to `/landlords/{id}`) since `PropertyResponse` only carries the bare `LandlordId`.

## Tenants frontend module (Prompt 20) - third module, back to the simple shape

Third CRUD module (`services/tenantService.js`, `pages/tenants/{List,Detail,Form}Page.jsx`, nested `ProtectedRoute`s with `CAN_VIEW_TENANTS`/`CAN_MANAGE_TENANTS`). Tenant's `PATCH /api/tenants/{id}/status` accepts `IsActive` either direction (like Landlords, unlike Properties - see `backend/app/services/tenant_service.py`'s `set_active_status`), so `TenantDetailPage` copies `LandlordDetailPage`'s activate/deactivate-with-`ConfirmationDialog` pattern exactly, not Property's split status/active pattern - **check which shape a module's backend actually supports before copying either template**, don't assume every module works like the most recently built one.

Nothing new introduced at the cross-module level this time (`Toast`, `roles.js`/`permissions.js`, `ConfirmationDialog`'s `confirmDisabled` all reused as-is) - this module was the first "pure copy" of the established pattern, which is the point of having established it. The one field-level addition: `TenantFormPage`'s client-side validation mirrors `TenantWriteBase.date_of_birth_not_in_future` (a `DateField` with `max={TODAY}` plus an explicit check in `validate()`, same reasoning as `LandlordFormPage`'s company-or-full-name check - simple static backend rules get a client-side mirror, anything needing a DB lookup doesn't).

## Employees frontend module (Prompt 20) - fourth and last of the repeatable CRUD group

Same file/route shape as the other three (`services/employeeService.js`, `pages/employees/{List,Detail,Form}Page.jsx`), but the first frontend module with a **narrower permission pair than every module before it**: `CAN_VIEW_EMPLOYEES = [Administrator, PropertyManager]` (no ReadOnly, no MaintenanceEmployee) and `CAN_MANAGE_EMPLOYEES = [Administrator]` only (no PropertyManager) - mirrors `backend/app/core/roles.py` exactly, added to `constants/roles.js` alongside the existing `CAN_VIEW_X`/`CAN_MANAGE_X` pairs. Verified live for all three tiers: Administrator (Sarah Mitchell) gets full create/edit/deactivate/reactivate; PropertyManager (Priya Patel) sees the list and detail pages with no `+ New`/Edit/Deactivate buttons rendered, and is bounced to `/unauthorized` if she navigates to `/employees/new` directly (route-level `ProtectedRoute` backstop, not just the button-level check); ReadOnly (Emma Wilson) is bounced to `/unauthorized` from `/employees` itself - she has no view access at all, unlike every earlier module where ReadOnly could at least view.

`EmployeeDetailPage` copies `TenantDetailPage`'s activate/deactivate-with-`ConfirmationDialog` pattern (Employee's `PATCH /api/employees/{id}/status` also accepts `IsActive` either direction - see `employeeService.js`), not Property's split status/active pattern. The confirmation dialog's message for deactivating spells out both backend consequences up front rather than letting the user hit a 409 blind: it's blocked if the employee still has open maintenance assignments (`EMPLOYEE_HAS_OPEN_MAINTENANCE_ASSIGNMENTS`), and - the one genuinely new piece of information a user needs here that no other module's dialog has to convey - deactivating also disables their linked login account one-way (`employee_service.py`'s `_deactivate_linked_user`; reactivating the Employee does NOT restore it).

`EmployeeFormPage` differs from every other module's form in one way worth remembering: **`Email` and `HireDate` are both required fields** in `EmployeeWriteBase` (no optional-email escape hatch like Landlord/Tenant have), so client-side `validate()` rejects blank Email/HireDate up front instead of only checking shape - don't copy `LandlordFormPage`'s "empty email is fine" assumption here. `HireDate` gets the same `DateField max={TODAY}` + explicit check pattern as `TenantFormPage`'s `DateOfBirth`, mirroring `EmployeeWriteBase.hire_date_not_in_future`.

Nothing new introduced at the cross-module level (`Toast`, `ConfirmationDialog`'s `confirmDisabled`, the toast-across-navigation pattern all reused as-is) - only `roles.js` gained the new, narrower `CAN_VIEW_EMPLOYEES`/`CAN_MANAGE_EMPLOYEES` pair, and `Sidebar.jsx`'s `Employees` entry flipped from `path: null` to `/employees` (now every Prompt-20 module's nav link is live; only Tenancies/Rent Payments/Maintenance remain disabled). Manually created and fully deactivated/reactivated a throwaway employee via the browser to verify the round trip, then deleted it directly via `sqlcmd` (`DELETE FROM Employees WHERE EmployeeId = <id>`, `SET QUOTED_IDENTIFIER ON` first) to restore the seeded count of 5 - the UI itself never hard-deletes (`deactivateEmployee` is a soft-delete via `DELETE /api/employees/{id}`, which is `EmployeeService.deactivate_employee` under the hood, not a real SQL delete).

## Tenancy frontend module (Prompt 21) - the first module with its own bespoke shape, not the generic CRUD template

Unlike every Prompt 20 module, Tenancy has no `PATCH /status` and no free-text `search` param on its list endpoint (`TenancyRepository.list` only filters by `property_id`/`tenant_id`/`tenancy_status` - see `tenancyService.js`'s docstring), so `TenanciesListPage` uses three `SelectField` dropdown filters instead of a `SearchInput`. Property/Tenant filter and form-selector options are loaded the same direct `pageSize:100` way `PropertyFormPage`'s landlord dropdown already does - no new shared "options loader" abstraction introduced for these extra call sites.

**Four new files, mirroring the file/route shape but not the Prompt-20 page template**: `services/tenancyService.js`, `pages/tenancies/{TenanciesList,TenancyDetail,TenancyForm,TenancyEndingSoon}Page.jsx`, `constants/tenancyOptions.js` (`TENANCY_STATUS_OPTIONS`, filter-only - never a form field, since status only ever changes through the lifecycle actions below). `roles.js` gained `CAN_VIEW_TENANCIES`/`CAN_MANAGE_TENANCIES` (same Administrator+PropertyManager+ReadOnly / Administrator+PropertyManager shape as Landlords), and `Sidebar.jsx`'s `Tenancies` entry went live.

**`TenancyDetailPage` is the first detail page with THREE conditionally-available lifecycle actions instead of one toggle**, gated on the tenancy's current `TenancyStatus` exactly like `tenancy_service.py`'s own transition checks: Edit link and "Activate" only show for `Draft`; "End tenancy" only shows for `Active`/`Ending Soon`; "Cancel tenancy" shows for anything not already `Ended`/`Cancelled` (so Draft can be both Activated or Cancelled, Active can be both Ended or Cancelled). All three share ONE `ConfirmationDialog` instance via a `pendingAction` state (`"activate" | "end" | "cancel" | null`) with a `dialogConfig` lookup for each action's title/message/confirmLabel, rather than three separate dialog instances - only one action is ever in flight at a time regardless of how many buttons are visible. "End tenancy" is the one action needing extra input: since `ConfirmationDialog`'s `message` prop renders inside a `<p>` (no children slot for embedded form controls - putting a `DateField` in there would be invalid HTML, a `<div>` inside a `<p>`), the optional end-date `DateField` sits next to the button BEFORE the dialog opens, and the dialog's message text interpolates the chosen date (or explains it'll default to today) - never both.

**Manually verified the full lifecycle live via the Browser tool**, catching a genuinely useful real behavior along the way: ending a freshly-activated same-day tenancy with no end date chosen correctly surfaced the backend's `TENANCY_INVALID_END_DATE` error (`end_date <= StartDate` when both are "today"), confirming the error-display pattern works for this module's business rules exactly as it does elsewhere, and that a Draft→Active→Ended tenancy correctly flips its property Occupied→Vacant at each transition (verified by cross-checking `PropertyDetailPage` after each action). Also confirmed role-gating end-to-end: Administrator sees all three actions; PropertyManager (same `CAN_MANAGE_TENANCIES` shape) would too (not separately re-tested, since the role list is identical to Landlords', already proven); MaintenanceEmployee is bounced to `/unauthorized` from `/tenancies` itself, matching `CAN_VIEW_TENANCIES` excluding them. Cleaned up the manually-created test tenancy via `sqlcmd` (`DELETE FROM Tenancies WHERE TenancyId = <id>`) to restore the seeded count of 12 - confirmed `AuditLogs.EntityId` has no FK constraint back to `Tenancies`, so the delete needed no extra cleanup there.

**`TenancyEndingSoonPage`** (`/tenancies/ending-soon`, linked from a button in `TenanciesListPage`'s `PageHeader` actions, not a separate sidebar entry) hits `GET /api/tenancies/expiring?days=N` with a 30/60/90-day `SelectField` toggle. It's the first list-shaped page in the app with no `Pagination` component - the endpoint isn't paginated (see `tenancyService.js`), since it's meant to be a short attention list, not a full browse.

**`TenancyFormPage`** only ever creates/edits a Draft (`PUT` is rejected server-side once a tenancy leaves Draft - `TENANCY_NOT_EDITABLE`, 409 - which is exactly why `TenancyDetailPage` only shows the Edit link in that state). Client-side validation covers only the cheap static rules (required fields, `MonthlyRent > 0`, `PaymentDueDay` 1-28, `EndDate` after `StartDate` - mirroring `TenancyCreate.validate_date_order`); overlap conflicts and inactive-property/tenant checks are deliberately left to the server, since those only apply at Activate time, not at Draft creation - the scope doc's Prompt 21 explicitly says not to duplicate backend business-rule validation here.

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
