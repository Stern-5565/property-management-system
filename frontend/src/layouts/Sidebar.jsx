/**
 * Navigation shell. Dashboard, Landlords, Properties, Tenants, and
 * Employees are real, clickable routes; the remaining modules are listed
 * (so the overall app shape is visible) but rendered disabled, since they
 * don't have a frontend yet. As each module gets its own frontend built,
 * flip its entry here from `path: null` to a real path (see
 * documentation/progress-log.md for build order).
 */
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/" },
  { label: "Landlords", path: "/landlords" },
  { label: "Properties", path: "/properties" },
  { label: "Tenants", path: "/tenants" },
  { label: "Tenancies", path: "/tenancies" },
  { label: "Rent Payments", path: "/rent-payments" },
  { label: "Maintenance", path: null },
  { label: "Employees", path: "/employees" },
];

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="sidebar__brand">PropertyManager</div>
      <ul className="sidebar__list">
        {NAV_ITEMS.map((item) =>
          item.path ? (
            <li key={item.label}>
              <NavLink
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) => "sidebar__link" + (isActive ? " sidebar__link--active" : "")}
              >
                {item.label}
              </NavLink>
            </li>
          ) : (
            <li key={item.label}>
              <span className="sidebar__link sidebar__link--disabled" aria-disabled="true" title="Coming soon">
                {item.label}
              </span>
            </li>
          ),
        )}
      </ul>
    </nav>
  );
}
