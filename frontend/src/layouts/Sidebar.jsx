/**
 * Navigation shell. "Dashboard" and "Landlords" are real, clickable
 * routes; every other module is listed (so the overall app shape is
 * visible) but rendered disabled, since none of them have a frontend
 * yet. As each module gets its own frontend built, flip its entry here
 * from `path: null` to a real path (see documentation/progress-log.md
 * for build order).
 */
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/" },
  { label: "Landlords", path: "/landlords" },
  { label: "Properties", path: "/properties" },
  { label: "Tenants", path: null },
  { label: "Tenancies", path: null },
  { label: "Rent Payments", path: null },
  { label: "Maintenance", path: null },
  { label: "Employees", path: null },
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
