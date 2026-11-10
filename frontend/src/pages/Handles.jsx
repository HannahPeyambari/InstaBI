import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import {
  fmtNum,
  fmtPct,
  Avatar,
  StatusBadge,
  useToast,
  timeAgo,
} from "../components/common.jsx";

export default function Handles() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [busyDelete, setBusyDelete] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const toast = useToast();

  async function load() {
    setLoading(true);
    try {
      const rows = await api.compare(200);
      setItems(rows);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function addOne(e) {
    e.preventDefault();
    const username = newUsername.trim().replace(/^@/, "");
    if (!username) return;
    try {
      await api.createHandle({ username });
      setNewUsername("");
      toast(`Added @${username}`, "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function addBulk(e) {
    e.preventDefault();
    try {
      const res = await api.bulkAdd({ text: bulkText });
      toast(`Added ${res.added}, skipped ${res.skipped}`, "success");
      setBulkText("");
      setShowBulk(false);
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function check(id) {
    setBusyId(id);
    try {
      await api.checkHandle(id);
      toast("Check complete", "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusyId(null);
    }
  }

  async function checkAll() {
    setBusyId("all");
    try {
      const res = await api.checkAll();
      toast(`${res.run.ok_count} ok, ${res.run.failed_count} failed`, res.run.failed_count ? "error" : "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteFailed() {
    const failed = items.filter((i) => i.handle.last_status === "error");
    const names = failed.map((i) => "@" + i.handle.username).join(", ");
    if (!confirm(`Remove ${failed.length} failed handle(s)?\n\n${names}\n\nThis deletes the handle and all its history.`)) return;
    setBusyDelete(true);
    try {
      const res = await api.deleteFailed();
      toast(res.deleted ? `Removed ${res.deleted} failed handle(s)` : "No failed handles to remove", "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusyDelete(false);
    }
  }

  async function toggle(item) {
    try {
      await api.updateHandle(item.handle.id, { active: !item.handle.active });
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function remove(item) {
    if (!confirm(`Remove @${item.handle.username} and all its history?`)) return;
    try {
      await api.deleteHandle(item.handle.id);
      toast(`Removed @${item.handle.username}`, "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Handles</h1>
          <p>Manage the Instagram accounts you track.</p>
        </div>
        <div className="row">
          <button className="btn secondary" onClick={deleteFailed} disabled={busyDelete}>
            {busyDelete ? "Deleting…" : "🗑 Delete failed"}
          </button>
          <button className="btn" onClick={checkAll} disabled={busyId === "all" || items.length === 0}>
            {busyId === "all" ? "Checking…" : "▶ Check all"}
          </button>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 22 }}>
        <form className="card" onSubmit={addOne}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Add a single handle</label>
            <div className="row">
              <input
                placeholder="username (e.g. natgeo)"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                style={{ minWidth: 0 }}
              />
              <button className="btn" type="submit" disabled={!newUsername.trim()}>
                Add
              </button>
            </div>
          </div>
        </form>
        <div className="card">
          <div className="spread">
            <div>
              <label style={{ display: "block", marginBottom: 6, color: "var(--text-dim)", fontWeight: 600, fontSize: 13 }}>
                Bulk import
              </label>
              <p className="hint">Paste a list — one per line or comma-separated. Lines with spaces/punctuation are skipped.</p>
            </div>
            <button className="btn secondary" onClick={() => setShowBulk((s) => !s)}>
              {showBulk ? "Hide" : "Expand"}
            </button>
          </div>
          {showBulk && (
            <form onSubmit={addBulk} style={{ marginTop: 12 }}>
              <textarea
                placeholder={"natgeo\nnasa\nchrissyteigen\nleomessi"}
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
              />
              <button className="btn" type="submit" style={{ marginTop: 10 }} disabled={!bulkText.trim()}>
                Import handles
              </button>
            </form>
          )}
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading handles…</div>
      ) : items.length === 0 ? (
        <div className="card empty">
          No handles yet. Add one above or use bulk import to get started.
        </div>
      ) : (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Followers</th>
                <th>Following</th>
                <th>Posts</th>
                <th>Engagement</th>
                <th>Last check</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const h = item.handle;
                const s = item.snapshot;
                return (
                  <tr key={h.id}>
                    <td>
                      <div className="row">
                        <Avatar src={s?.avatar_url} username={h.username} />
                        <div>
                          <div className="row" style={{ gap: 6 }}>
                            <strong>@{h.username}</strong>
                            {s?.is_verified && <span title="Verified" style={{ color: "var(--blue)" }}>✔️</span>}
                            {s?.is_private && <span className="badge private">Private</span>}
                            {!h.active && <span className="badge neutral">Paused</span>}
                          </div>
                          <div className="faint" style={{ fontSize: 12 }}>{s?.full_name || h.display_name || "—"}</div>
                        </div>
                      </div>
                    </td>
                    <td>{s ? fmtNum(s.follower_count) : "—"}</td>
                    <td className="faint">{s ? fmtNum(s.following_count) : "—"}</td>
                    <td className="faint">{s ? fmtNum(s.media_count) : "—"}</td>
                    <td>{s ? fmtPct(s.engagement_rate) : "—"}</td>
                    <td className="faint">{h.last_checked_at ? timeAgo(h.last_checked_at) : "never"}</td>
                    <td><StatusBadge status={h.last_status || s?.status} /></td>
                    <td>
                      <div className="row" style={{ gap: 6 }}>
                        <Link to={`/analytics/${h.id}`} className="btn ghost sm">Stats</Link>
                        <button className="btn secondary sm" onClick={() => check(h.id)} disabled={busyId === h.id}>
                          {busyId === h.id ? "…" : "Check"}
                        </button>
                        <button className="btn ghost sm" onClick={() => toggle(item)}>{h.active ? "Pause" : "Resume"}</button>
                        <button className="btn danger sm" onClick={() => remove(item)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
