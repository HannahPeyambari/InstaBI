import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await login(username, password);
      navigate("/");
    } catch (e) {
      setErr(e.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand" style={{ padding: "0 0 18px" }}>
          <span className="logo">📸</span>
          <span>InstaBI</span>
        </div>
        <div className="field">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="See backend/data/admin_password.txt"
          />
        </div>
        {err && <div className="banner error">{err}</div>}
        <button className="btn" style={{ width: "100%", marginTop: 4 }} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="hint">
          If you didn't set an admin password, one was generated on first boot and saved to
          <code> backend/data/admin_password.txt</code>.
        </p>
      </form>
    </div>
  );
}
