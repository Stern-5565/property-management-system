import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="header">
      <div />
      <div className="header__user">
        <span className="header__name">{user.EmployeeName}</span>
        <span className="header__roles">{user.Roles.join(", ")}</span>
        <button type="button" className="button button--secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
