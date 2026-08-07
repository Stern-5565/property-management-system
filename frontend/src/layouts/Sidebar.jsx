/**
 * Navigation shell. Every item is a real, clickable route - Dashboard
 * (Prompt 24) was the last one still pointing at a placeholder. No
 * role-gating here (every link shows to every logged-in user); a role
 * that can't actually view a module gets bounced to /unauthorized by
 * that route's own ProtectedRoute if they click through - same as every
 * other nav item.
 */
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/" },
  { label: "Landlords", path: "/landlords" },
  { label: "Properties", path: "/properties" },
  { label: "Tenants", path: "/tenants" },
  { label: "Tenancies", path: "/tenancies" },
  { label: "Rent Payments", path: "/rent-payments" },
  { label: "Maintenance", path: "/maintenance" },
  { label: "Employees", path: "/employees" },
  { label: "Reports", path: "/reports" },
];

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="sidebar__brand">PropertyManager</div>
      <ul className="sidebar__list">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <NavLink
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) => "sidebar__link" + (isActive ? " sidebar__link--active" : "")}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
