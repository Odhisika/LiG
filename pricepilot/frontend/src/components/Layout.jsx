import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/suppliers", label: "Suppliers" },
  { to: "/products", label: "Products" },
  { to: "/discoveries", label: "Discoveries" },
  { to: "/pricing-rules", label: "Pricing Rules" },
  { to: "/history", label: "History" },
  { to: "/notifications", label: "Notifications" },
  { to: "/analytics", label: "Analytics" },
  { to: "/activity", label: "Activity" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function handleNavClick() {
    setNavOpen(false);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">PricePilot</div>
        <button
          className="nav-toggle"
          onClick={() => setNavOpen(!navOpen)}
          aria-label="Toggle navigation"
        >
          {navOpen ? "\u2715" : "\u2630"}
        </button>
        <nav className={navOpen ? "open" : ""}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "active" : "")}
              onClick={handleNavClick}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="user">
          <span>{user?.email}</span>
          <button className="btn btn-sm" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
