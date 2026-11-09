import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useEffect, useState } from "react";

const NAV = [
  { to: "/", icon: "📊", label: "Dashboard", end: true },
  { to: "/handles", icon: "👤", label: "Handles" },
  { to: "/analytics", icon: "📈", label: "Analytics" },
  { to: "/runs", icon: "🕑", label: "Runs" },
  { to: "/settings", icon: "⚙️", label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [provider, setProvider] = useState("");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((j) => setProvider(j.provider))
      .catch(() => {});
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">📸</span>
          <span>InstaBI</span>
        </div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span className="nav-icon">{n.icon}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
        <div className="sidebar-footer">
          <div className="row">
            <span>Provider</span>
            <span>{provider || "—"}</span>
          </div>
          <div className="row">
            <span>User</span>
            <span>{user || "—"}</span>
          </div>
          <button
            className="btn ghost sm"
            style={{ marginTop: 10, width: "100%" }}
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
