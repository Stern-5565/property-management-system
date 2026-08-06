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
 * "/" (HomePage) and "/dev/components" (the dev-only Prompt 19 component
 * reference - see ComponentShowcasePage.jsx) need only a login. The
 * Landlords routes are the first to use ProtectedRoute's `allowedRoles`
 * for real: nested ProtectedRoutes narrow access twice - once so only
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
import { HomePage } from "./pages/HomePage";
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
                <Route path="/" element={<HomePage />} />
                {/* Dev-only component library reference - see ComponentShowcasePage.jsx. Deliberately not in the sidebar. */}
                <Route path="/dev/components" element={<ComponentShowcasePage />} />

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
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
