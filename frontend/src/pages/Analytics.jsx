import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { api } from "../api.js";
import { fmtNum, fmtPct, fmtTime, Avatar, StatCard } from "../components/common.jsx";

export default function Analytics() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [snaps, setSnaps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const p = id ? Promise.all([api.compare(200), api.handleSnapshots(id)]) : api.compare(200);
    p.then((res) => {
      if (id) {
        setRows([res[0]]);
        setSnaps(res[1]);
      } else {
        setRows(res);
        setSnaps([]);
      }
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">Loading analytics…</div>;

  if (!id) {
    return (
      <>
        <div className="page-head">
          <div>
            <h1>Analytics</h1>
            <p>Pick an account to view its stats history.</p>
          </div>
        </div>
        {rows.length === 0 ? (
          <div className="card empty">No handles to analyze yet.</div>
        ) : (
          <div className="card table-wrap">
            <table>
              <thead>
                <tr><th>Account</th><th>Followers</th><th>Engagement</th><th>Posts</th><th></th></tr>
              </thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.handle.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/analytics/${item.handle.id}`)}>
                    <td>
                      <div className="row">
                        <Avatar src={item.snapshot?.avatar_url} username={item.handle.username} />
                        <strong>@{item.handle.username}</strong>
                        {item.snapshot?.is_verified && <span style={{ color: "var(--blue)" }}>✔️</span>}
                      </div>
                    </td>
                    <td>{item.snapshot ? fmtNum(item.snapshot.follower_count) : "—"}</td>
                    <td>{item.snapshot ? fmtPct(item.snapshot.engagement_rate) : "—"}</td>
                    <td className="faint">{item.snapshot ? fmtNum(item.snapshot.media_count) : "—"}</td>
                    <td><span className="faint">›</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </>
    );
  }

  const handle = rows[0]?.handle;
  const latest = snaps.length ? snaps[snaps.length - 1] : null;
  const chartData = snaps.map((s) => ({
    ts: new Date(s.captured_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    followers: s.follower_count,
    following: s.following_count,
    posts: s.media_count,
    engagement: Number(s.engagement_rate.toFixed(3)),
  }));
  const first = snaps[0];
  const followersDelta = first && latest ? latest.follower_count - first.follower_count : 0;

  return (
    <>
      <div className="page-head">
        <div>
          <Link to="/analytics" className="muted" style={{ fontSize: 13 }}>← All accounts</Link>
          <h1 style={{ marginTop: 6 }}>
            <Avatar src={latest?.avatar_url} username={handle?.username} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 10 }} />
            @{handle?.username}
          </h1>
          <p>{latest?.full_name || handle?.display_name || ""}</p>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 18 }}>
        <StatCard
          label="Followers"
          value={fmtNum(latest?.follower_count)}
          sub={snaps.length > 1 ? <span className={`delta ${followersDelta >= 0 ? "up" : "down"}`}>{fmtDelta(followersDelta)} (all-time)</span> : undefined}
        />
        <StatCard label="Following" value={fmtNum(latest?.following_count)} />
        <StatCard label="Posts" value={fmtNum(latest?.media_count)} />
        <StatCard label="Engagement rate" value={fmtPct(latest?.engagement_rate)} sub="per post (recent)" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 18 }}>
        <div className="card chart-card">
          <strong>Followers &amp; following</strong>
          {snaps.length < 2 ? (
            <div className="empty">Only one snapshot. Run checks over time to build history.</div>
          ) : (
            <ResponsiveContainer width="100%" height="90%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                <XAxis dataKey="ts" stroke="#6b7384" fontSize={12} />
                <YAxis stroke="#6b7384" fontSize={12} tickFormatter={fmtNum} />
                <Tooltip contentStyle={{ background: "#1c2029", border: "1px solid #2a3040", borderRadius: 8 }} />
                <Legend />
                <Line type="monotone" dataKey="followers" stroke="#7c5cff" strokeWidth={2.5} />
                <Line type="monotone" dataKey="following" stroke="#4aa3ff" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card chart-card">
          <strong>Engagement rate (%)</strong>
          {snaps.length < 2 ? (
            <div className="empty">Need multiple snapshots.</div>
          ) : (
            <ResponsiveContainer width="100%" height="90%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="er" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2ecc71" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#2ecc71" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                <XAxis dataKey="ts" stroke="#6b7384" fontSize={12} />
                <YAxis stroke="#6b7384" fontSize={12} />
                <Tooltip contentStyle={{ background: "#1c2029", border: "1px solid #2a3040", borderRadius: 8 }} />
                <Area type="monotone" dataKey="engagement" stroke="#2ecc71" strokeWidth={2.5} fill="url(#er)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card">
        <strong>Snapshot history</strong>
        {snaps.length === 0 ? (
          <div className="empty">No snapshots recorded yet.</div>
        ) : (
          <table>
            <thead>
              <tr><th>When</th><th>Followers</th><th>Following</th><th>Posts</th><th>Engagement</th><th>Recent likes</th><th>Status</th></tr>
            </thead>
            <tbody>
              {[...snaps].reverse().map((s) => (
                <tr key={s.id}>
                  <td>{fmtTime(s.captured_at)}</td>
                  <td>{fmtNum(s.follower_count)}</td>
                  <td className="faint">{fmtNum(s.following_count)}</td>
                  <td className="faint">{fmtNum(s.media_count)}</td>
                  <td>{fmtPct(s.engagement_rate)}</td>
                  <td className="faint">{fmtNum(s.recent_likes)}</td>
                  <td>{s.status === "ok" ? <span className="badge ok">OK</span> : <span className="badge error">{s.error}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function fmtDelta(n) {
  return n > 0 ? `+${fmtNum(n)}` : `${fmtNum(n)}`;
}
