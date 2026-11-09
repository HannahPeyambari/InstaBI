import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Handles from "./pages/Handles.jsx";
import Analytics from "./pages/Analytics.jsx";
import Runs from "./pages/Runs.jsx";
import Settings from "./pages/Settings.jsx";

function RequireAuth({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="loading">Loading…</div>;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/handles" element={<Handles />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/analytics/:id" element={<Analytics />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
