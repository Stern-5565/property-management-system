/**
 * Routing flow, explained:
 * - "/login" and "/unauthorized" are public.
 * - Everything else is nested under <ProtectedRoute />, which blocks
 *   rendering until AuthContext confirms whether the user is logged in
 *   (see ProtectedRoute.jsx) and redirects to /login if not.
 * - Authenticated routes are further nested under <MainLayout />, which
 *   renders the sidebar/header shell once, around whichever page is
 *   active (see layouts/MainLayout.jsx).
 * - "*" catches any URL that doesn't match one of the routes above.
 *
 * "/dev/components" (the dev-only Prompt 19 component reference - see
 * ComponentShowcasePage.jsx) needs only a login. "/" (DashboardPage) is
 * the first route to gate the landing page itself: CAN_VIEW_DASHBOARD
 * excludes MaintenanceEmployee (the dashboard mixes in financial
 * figures), so LoginPage's post-login redirect uses
 * getDefaultLandingPath (utilities/permissions.js) instead of hardcoding
 * "/", sending that one role to /maintenance instead. The Landlords
 * routes are the first to use ProtectedRoute's `allowedRoles` for real:
 * nested ProtectedRoutes narrow access twice - once so only
 * CAN_VIEW_LANDLORDS roles can see the module at all, again so only
 * CAN_MANAGE_LANDLORDS roles reach the create/edit forms (matching the
 * backend's own CAN_VIEW_LANDLORDS/CAN_MANAGE_LANDLORDS split in
 * app/core/roles.py). Every future module follows this same nesting
 * shape.
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { MainLayout } from "./layouts/MainLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ComponentShowcasePage } from "./pages/ComponentShowcasePage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { LandlordsListPage } from "./pages/landlords/LandlordsListPage";
import { LandlordDetailPage } from "./pages/landlords/LandlordDetailPage";
import { LandlordFormPage } from "./pages/landlords/LandlordFormPage";
import { PropertiesListPage } from "./pages/properties/PropertiesListPage";
import { PropertyDetailPage } from "./pages/properties/PropertyDetailPage";
import { PropertyFormPage } from "./pages/properties/PropertyFormPage";
import { TenantsListPage } from "./pages/tenants/TenantsListPage";
import { TenantDetailPage } from "./pages/tenants/TenantDetailPage";
import { TenantFormPage } from "./pages/tenants/TenantFormPage";
import { EmployeesListPage } from "./pages/employees/EmployeesListPage";
import { EmployeeDetailPage } from "./pages/employees/EmployeeDetailPage";
import { EmployeeFormPage } from "./pages/employees/EmployeeFormPage";
import { TenanciesListPage } from "./pages/tenancies/TenanciesListPage";
import { TenancyDetailPage } from "./pages/tenancies/TenancyDetailPage";
import { TenancyFormPage } from "./pages/tenancies/TenancyFormPage";
import { TenancyEndingSoonPage } from "./pages/tenancies/TenancyEndingSoonPage";
import { RentPaymentsListPage } from "./pages/rent-payments/RentPaymentsListPage";
import { RentPaymentDetailPage } from "./pages/rent-payments/RentPaymentDetailPage";
import { RentPaymentFormPage } from "./pages/rent-payments/RentPaymentFormPage";
import { RentPaymentOverduePage } from "./pages/rent-payments/RentPaymentOverduePage";
import { RentPaymentDueThisMonthPage } from "./pages/rent-payments/RentPaymentDueThisMonthPage";
import { MaintenanceRequestsListPage } from "./pages/maintenance/MaintenanceRequestsListPage";
import { MaintenanceRequestDetailPage } from "./pages/maintenance/MaintenanceRequestDetailPage";
import { MaintenanceRequestFormPage } from "./pages/maintenance/MaintenanceRequestFormPage";
import { MaintenanceWorkloadPage } from "./pages/maintenance/MaintenanceWorkloadPage";
import {
  CAN_VIEW_LANDLORDS,
  CAN_MANAGE_LANDLORDS,
  CAN_VIEW_PROPERTIES,
  CAN_MANAGE_PROPERTIES,
  CAN_VIEW_TENANTS,
  CAN_MANAGE_TENANTS,
  CAN_VIEW_EMPLOYEES,
  CAN_MANAGE_EMPLOYEES,
  CAN_VIEW_TENANCIES,
  CAN_MANAGE_TENANCIES,
  CAN_VIEW_RENT_PAYMENTS,
  CAN_MANAGE_RENT_PAYMENTS,
  CAN_ACCESS_MAINTENANCE,
  CAN_MANAGE_MAINTENANCE,
  CAN_VIEW_MAINTENANCE,
  CAN_VIEW_DASHBOARD,
} from "./constants/roles";

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                {/* Dev-only component library reference - see ComponentShowcasePage.jsx. Deliberately not in the sidebar. */}
                <Route path="/dev/components" element={<ComponentShowcasePage />} />

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_DASHBOARD} />}>
                  <Route path="/" element={<DashboardPage />} />
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_LANDLORDS} />}>
                  <Route path="/landlords" element={<LandlordsListPage />} />
                  <Route path="/landlords/:id" element={<LandlordDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_LANDLORDS} />}>
                    <Route path="/landlords/new" element={<LandlordFormPage />} />
                    <Route path="/landlords/:id/edit" element={<LandlordFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_PROPERTIES} />}>
                  <Route path="/properties" element={<PropertiesListPage />} />
                  <Route path="/properties/:id" element={<PropertyDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_PROPERTIES} />}>
                    <Route path="/properties/new" element={<PropertyFormPage />} />
                    <Route path="/properties/:id/edit" element={<PropertyFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_TENANTS} />}>
                  <Route path="/tenants" element={<TenantsListPage />} />
                  <Route path="/tenants/:id" element={<TenantDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_TENANTS} />}>
                    <Route path="/tenants/new" element={<TenantFormPage />} />
                    <Route path="/tenants/:id/edit" element={<TenantFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_EMPLOYEES} />}>
                  <Route path="/employees" element={<EmployeesListPage />} />
                  <Route path="/employees/:id" element={<EmployeeDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_EMPLOYEES} />}>
                    <Route path="/employees/new" element={<EmployeeFormPage />} />
                    <Route path="/employees/:id/edit" element={<EmployeeFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_TENANCIES} />}>
                  <Route path="/tenancies" element={<TenanciesListPage />} />
                  <Route path="/tenancies/ending-soon" element={<TenancyEndingSoonPage />} />
                  <Route path="/tenancies/:id" element={<TenancyDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_TENANCIES} />}>
                    <Route path="/tenancies/new" element={<TenancyFormPage />} />
                    <Route path="/tenancies/:id/edit" element={<TenancyFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_RENT_PAYMENTS} />}>
                  <Route path="/rent-payments" element={<RentPaymentsListPage />} />
                  <Route path="/rent-payments/overdue" element={<RentPaymentOverduePage />} />
                  <Route path="/rent-payments/due-this-month" element={<RentPaymentDueThisMonthPage />} />
                  <Route path="/rent-payments/:id" element={<RentPaymentDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_RENT_PAYMENTS} />}>
                    <Route path="/rent-payments/new" element={<RentPaymentFormPage />} />
                    <Route path="/rent-payments/:id/edit" element={<RentPaymentFormPage />} />
                  </Route>
                </Route>

                <Route element={<ProtectedRoute allowedRoles={CAN_ACCESS_MAINTENANCE} />}>
                  <Route path="/maintenance" element={<MaintenanceRequestsListPage />} />
                  <Route path="/maintenance/:id" element={<MaintenanceRequestDetailPage />} />

                  <Route element={<ProtectedRoute allowedRoles={CAN_VIEW_MAINTENANCE} />}>
                    <Route path="/maintenance/workload" element={<MaintenanceWorkloadPage />} />
                  </Route>

                  <Route element={<ProtectedRoute allowedRoles={CAN_MANAGE_MAINTENANCE} />}>
                    <Route path="/maintenance/new" element={<MaintenanceRequestFormPage />} />
                    <Route path="/maintenance/:id/edit" element={<MaintenanceRequestFormPage />} />
                  </Route>
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
