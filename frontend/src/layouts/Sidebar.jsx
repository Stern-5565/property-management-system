/**
 * Navigation shell. Every business module is now a real, clickable
 * route - Maintenance (Prompt 23) was the last one left disabled. Only
 * the Dashboard link still points at the Prompt 18 placeholder HomePage,
 * to be replaced once the real Dashboard (Prompt 24) is built.
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
