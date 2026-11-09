import { Fragment, useEffect, useState } from "react";
import { api } from "../api.js";
import { fmtTime, useToast } from "../components/common.jsx";

export default function Runs() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function load() {
    setLoading(true);
    try {
      setRuns(await api.listRuns(100));
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
      const res = await api.runNow();
      toast(`Done — ${res.run.ok_count} ok, ${res.run.failed_count} failed`, "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Runs</h1>
          <p>Every scheduled and manual check, with per-handle results.</p>
        </div>
        <div className="row">
          <button className="btn secondary" onClick={load}>↻ Refresh</button>
          <button className="btn" onClick={runNow} disabled={busy}>{busy ? "Running…" : "▶ Run now"}</button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading runs…</div>
      ) : runs.length === 0 ? (
        <div className="card empty">No runs yet.</div>
      ) : (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr>
                <th>Started</th>
                <th>Trigger</th>
                <th>Provider</th>
                <th>Handles</th>
                <th>Result</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <Fragment key={r.id}>
                  <tr>
                    <td>{fmtTime(r.started_at)}</td>
                    <td><span className="badge neutral">{r.trigger}</span></td>
                    <td>{r.provider}</td>
                    <td>{r.handles_total}</td>
                    <td>
                      <span className="badge ok">{r.ok_count} ok</span>{" "}
                      {r.failed_count > 0 && <span className="badge error">{r.failed_count} fail</span>}
                    </td>
                    <td className="faint">
                      {r.finished_at ? `${Math.round((new Date(r.finished_at) - new Date(r.started_at)) / 1000)}s` : "—"}
                    </td>
                    <td>
                      {r.detail && (
                        <button className="btn ghost sm" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
                          {expanded === r.id ? "Hide" : "Details"}
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded === r.id && r.detail && (
                    <tr>
                      <td colSpan={7} style={{ background: "var(--bg-soft)" }}>
                        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, color: "var(--red)", margin: 0 }}>{r.detail}</pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
