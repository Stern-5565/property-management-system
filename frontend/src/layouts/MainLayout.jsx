/**
 * The authenticated app shell: sidebar + header around whatever the
 * current route renders. Used as a layout route in App.jsx, nested inside
 * ProtectedRoute so it only ever renders for a logged-in user (Header
 * assumes `user` is non-null - see useAuth()).
 */
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function MainLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-shell__main">
        <Header />
        <main className="app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
