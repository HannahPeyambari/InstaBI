import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { api } from "../api.js";
import { StatCard, fmtNum, fmtDelta, fmtTime, timeAgo, useToast } from "../components/common.jsx";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function load() {
    setLoading(true);
    try {
      const o = await api.overview();
      const s = await api.schedulerStatus();
      const f = await api.listFailed();
      setData({ ...o, schedule: s, failed: f });
      setLbVersion(v => v + 1);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  const [period, setPeriod] = useState(7);
  const [sort, setSort] = useState("gained");
  const [lb, setLb] = useState(null);

  const [lbError, setLbError] = useState("");
  const [lbVersion, setLbVersion] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setLb(null);
    setLbError("");
    api.leaderboard(period, sort).then(result => {
      if (!cancelled) setLb(result);
    }).catch(err => {
      if (!cancelled) setLbError(err.message);
    });
    return () => { cancelled = true; };
  }, [period, sort, lbVersion]);

  async function runNow() {
    setBusy(true);
    try {
      await api.runNow();
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function deleteHandle(id, username) {
    if (!confirm(`Remove @${username} and all its history?`)) return;
    try {
      await api.deleteHandle(id);
      toast(`Removed @${username}`, "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function deleteAllFailed() {
    if (!confirm(`Remove all ${data.failed.length} failed handle(s)? This deletes them and their history.`)) return;
    try {
      const res = await api.deleteFailed();
      toast(`Removed ${res.deleted} failed handle(s)`, "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  if (loading) return <div className="loading">Loading dashboard…</div>;

  const series = (data.series || []).map((p) => ({
    ts: new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    followers: p.followers,
    gained: p.gained ?? 0,
  }));
  const lastRun = data.last_run;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p>Aggregate stats across all tracked Instagram handles.</p>
        </div>
        <div className="row">
          <button className="btn secondary" onClick={load}>
            ↻ Refresh
          </button>
          <button className="btn" onClick={runNow} disabled={busy}>
            {busy ? "Running…" : "▶ Run check now"}
          </button>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 18 }}>
        <StatCard label="Tracked handles" value={fmtNum(data.total_handles)} sub={`${data.active_handles} active`} />
        <StatCard
          label="Total followers"
          value={fmtNum(data.followers_total)}
          sub={
            <span className={`delta ${data.followers_change_24h > 0 ? "up" : data.followers_change_24h < 0 ? "down" : ""}`}>
              {fmtDelta(data.followers_change_24h)} (24h)
            </span>
          }
        />
        <StatCard
          label="Last run"
          value={lastRun ? timeAgo(lastRun.started_at) : "never"}
          sub={lastRun ? `${lastRun.ok_count}/${lastRun.handles_total} ok · ${lastRun.trigger}` : undefined}
        />
        <StatCard
          label="Next scheduled run"
          value={
            data.schedule?.jobs?.[0]?.next_run
              ? new Date(data.schedule.jobs[0].next_run).toLocaleString()
              : "—"
          }
          sub={`cron: ${data.schedule?.cron || "—"}`}
        />
      </div>

      {data.failed && data.failed.length > 0 && (
        <div className="card" style={{ marginBottom: 18, borderLeft: "3px solid var(--red)" }}>
          <div className="spread" style={{ marginBottom: 10 }}>
            <strong>⚠ Failed handles ({data.failed.length})</strong>
            <button className="btn secondary sm" onClick={deleteAllFailed}>Delete all failed</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Error</th>
                <th>Last check</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.failed.map((h) => (
                <tr key={h.id}>
                  <td><strong>@{h.username}</strong></td>
                  <td className="faint" style={{ color: "var(--red)", maxWidth: 420 }}>{h.last_error}</td>
                  <td className="faint">{h.last_checked_at ? timeAgo(h.last_checked_at) : "never"}</td>
                  <td>
                    <button className="btn danger sm" onClick={() => deleteHandle(h.id, h.username)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid grid-2" style={{ marginBottom: 18 }}>
        <div className="card chart-card">
          <div className="spread" style={{ marginBottom: 10 }}>
          <strong>Followers &amp; followers gained trend</strong>
          <span className="faint">per run</span>
          </div>
          {series.length < 2 ? (
            <div className="empty">Not enough runs yet to chart a trend. Run a check a few times.</div>
          ) : (
            <ResponsiveContainer width="100%" height="90%">
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                <XAxis dataKey="ts" stroke="#6b7384" fontSize={12} />
                <YAxis stroke="#6b7384" fontSize={12} tickFormatter={fmtNum} />
                <Tooltip
                  contentStyle={{ background: "#1c2029", border: "1px solid #2a3040", borderRadius: 8 }}
                  labelStyle={{ color: "#9aa3b2" }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="followers" name="Followers" stroke="#7c5cff" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="gained" name="Gained" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <div className="spread" style={{ marginBottom: 10 }}>
            <strong>🏆 Top 5 by followers gained (24h)</strong>
          </div>
          {data.top_gainers?.length ? (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 40 }}>#</th>
                  <th>Account</th>
                  <th>Gained</th>
                  <th>Followers</th>
                </tr>
              </thead>
              <tbody>
                {data.top_gainers.map((g, i) => (
                  <tr key={g.username}>
                    <td>
                      <span className={`rank ${i === 0 ? "r1" : i === 1 ? "r2" : i === 2 ? "r3" : ""}`}>{i + 1}</span>
                    </td>
                    <td><strong>@{g.username}</strong></td>
                    <td>
                      <span className={`delta ${g.change >= 0 ? "up" : "down"}`}>{fmtDelta(g.change)}</span>
                    </td>
                    <td className="faint">{fmtNum(g.followers)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">
              No 24h changes yet. Run <strong>Check all</strong> at least twice to build history.
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="spread" style={{ marginBottom: 10, flexWrap: "wrap", gap: 12 }}>
          <strong>🏆 Growth leaderboard · Top 20</strong>
          <div className="row">
            <label>Period {" "}
              <select value={period} onChange={e => setPeriod(Number(e.target.value))}>
                {[1, 7, 14, 30, 90].map(days => <option key={days} value={days}>{days === 1 ? "1 day" : `${days} days`}</option>)}
              </select>
            </label>
            <label>Rank by {" "}
              <select value={sort} onChange={e => setSort(e.target.value)}>
                <option value="gained">Followers gained</option>
                <option value="pct">Percentage growth</option>
              </select>
            </label>
          </div>
        </div>
        <p className="faint">Compared with the last successful snapshot at or before {period} day(s) before each account’s latest check. Hover dates to see exact capture times. Accounts without enough history are omitted; percentage growth from zero is unavailable.</p>
        {lbError ? <div role="alert">Could not load leaderboard: {lbError}</div> : !lb ? (
          <div className="empty">Loading leaderboard…</div>
        ) : lb.entries.length ? (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>#</th><th>Account</th><th>Followers (then)</th><th>Followers (now)</th><th>Gained</th><th>% Growth</th><th>Baseline</th><th>Latest check</th></tr></thead>
              <tbody>{lb.entries.map((entry, i) => (
                <tr key={entry.username}>
                  <td><span className={`rank ${i < 3 ? `r${i + 1}` : ""}`}>{i + 1}</span></td>
                  <td><strong>@{entry.username}</strong></td>
                  <td>{fmtNum(entry.followers_then)}</td><td>{fmtNum(entry.followers_now)}</td>
                  <td className={`delta ${entry.gained > 0 ? "up" : entry.gained < 0 ? "down" : ""}`}>{entry.gained === 0 ? "0" : fmtDelta(entry.gained)}</td>
                  <td className={`delta ${entry.pct > 0 ? "up" : entry.pct < 0 ? "down" : ""}`}>{entry.pct == null ? "—" : `${entry.pct > 0 ? "+" : ""}${entry.pct.toFixed(2)}%`}</td>
                  <td title={fmtTime(entry.baseline_at)}>{fmtTime(entry.baseline_at)}</td>
                  <td title={fmtTime(entry.latest_at)}>{fmtTime(entry.latest_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="empty">No accounts have enough history for this period yet. Keep scheduled checks running or select a shorter period.</div>}
      </div>

      <div className="card">
        <div className="spread" style={{ marginBottom: 10 }}>
          <strong>Recent runs</strong>
          <Link to="/runs">View all →</Link>
        </div>
        {data.recent_runs?.length ? (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Trigger</th>
                <th>Provider</th>
                <th>Result</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_runs.map((r) => (
                <tr key={r.id}>
                  <td>{fmtTime(r.started_at)}</td>
                  <td>{r.trigger}</td>
                  <td>{r.provider}</td>
                  <td>
                    <span className="badge ok">{r.ok_count} ok</span>{" "}
                    {r.failed_count > 0 && <span className="badge error">{r.failed_count} fail</span>}
                  </td>
                  <td className="faint">
                    {r.finished_at
                      ? `${Math.round((new Date(r.finished_at) - new Date(r.started_at)) / 1000)}s`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty">No runs yet. Add some handles and run a check.</div>
        )}
      </div>
    </>
  );
}
