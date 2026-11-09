import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api } from "../api.js";
import { StatCard, fmtNum, fmtDelta, fmtTime, timeAgo } from "../components/common.jsx";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const o = await api.overview();
      const s = await api.schedulerStatus();
      setData({ ...o, schedule: s });
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function runNow() {
    setBusy(true);
    try {
      await api.runNow();
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="loading">Loading dashboard…</div>;

  const series = (data.series || []).map((p) => ({
    ts: new Date(p.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    followers: p.followers,
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

      <div className="grid grid-2" style={{ marginBottom: 18 }}>
        <div className="card chart-card">
          <div className="spread" style={{ marginBottom: 10 }}>
            <strong>Followers trend</strong>
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
                <Line type="monotone" dataKey="followers" stroke="#7c5cff" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <div className="spread" style={{ marginBottom: 10 }}>
            <strong>Top gainers (24h)</strong>
          </div>
          {data.top_gainers?.length ? (
            <table>
              <tbody>
                {data.top_gainers.map((g) => (
                  <tr key={g.username}>
                    <td>@{g.username}</td>
                    <td>
                      <span className={`delta ${g.change >= 0 ? "up" : "down"}`}>{fmtDelta(g.change)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">No 24h changes recorded yet.</div>
          )}
        </div>
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
