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
 * Only "/" (HomePage) exists as a real business page today - see
 * documentation/progress-log.md for why (Prompt 18 is foundation only).
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { MainLayout } from "./layouts/MainLayout";
import { LoginPage } from "./pages/LoginPage";
import { HomePage } from "./pages/HomePage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { NotFoundPage } from "./pages/NotFoundPage";

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
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
