import { createContext, useCallback, useContext, useState } from "react";

// ---- Number formatting ----
export function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}
export function fmtDelta(n) {
  if (n === null || n === undefined || n === 0) return null;
  return n > 0 ? `+${fmtNum(n)}` : `${fmtNum(n)}`;
}
export function fmtPct(n) {
  if (n === null || n === undefined) return "—";
  return `${Number(n).toFixed(2)}%`;
}
export function timeAgo(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
export function fmtTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function Avatar({ src, username }) {
  const url = src || `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(username || "?")}`;
  return <img className="avatar" src={url} alt={username || "avatar"} onError={(e) => (e.target.style.visibility = "hidden")} />;
}

export function StatusBadge({ status }) {
  if (status === "ok") return <span className="badge ok">OK</span>;
  if (status === "error") return <span className="badge error">ERROR</span>;
  return <span className="badge neutral">—</span>;
}

export function ProviderBadge({ provider }) {
  if (!provider) return null;
  return <span className={`badge ${provider}`}>{provider}</span>;
}

// ---- Stat card ----
export function StatCard({ label, value, sub, children }) {
  return (
    <div className="card stat-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
      {children}
    </div>
  );
}

// ---- Toast ----
const ToastCtx = createContext(null);
export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const show = useCallback((message, kind = "info") => {
    setToast({ message, kind });
    setTimeout(() => setToast(null), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && (
        <div className={`toast ${toast.kind}`} onClick={() => setToast(null)}>
          {toast.message}
        </div>
      )}
    </ToastCtx.Provider>
  );
}
export function useToast() {
  const ctx = useContext(ToastCtx);
  return ctx || (() => {});
}
