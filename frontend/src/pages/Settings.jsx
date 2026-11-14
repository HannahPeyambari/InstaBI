import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../components/common.jsx";

const PROVIDERS = [
  { id: "mock", label: "Mock (demo data, no login)" },
  { id: "instagrapi", label: "instagrapi (real Instagram — needs login)" },
];

export default function Settings() {
  const [cfg, setCfg] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [health, setHealth] = useState({ ok: false, message: "" });
  const toast = useToast();

  async function load() {
    try {
      const res = await api.getSettings();
      setCfg(res.settings);
      setHealth(res.health);
      setForm({ ...res.settings });
    } catch (err) {
      toast(err.message, "error");
    }
  }
  useEffect(() => {
    load();
  }, []);

  function set(key, val) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await api.updateSettings(form);
      toast("Settings saved", "success");
      await load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setSaving(false);
    }
  }

  async function reschedule() {
    try {
      await api.reschedule();
      toast("Scheduler restarted", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  if (!cfg) return <div className="loading">Loading settings…</div>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Tune the scraper and scheduler. Changes apply immediately.</p>
        </div>
      </div>

      <div className={`banner ${health.ok ? "info" : "warn"}`}>
        <strong>Provider health:</strong> {health.ok ? "OK" : "NOT READY"} — {health.message}
      </div>

      <form onSubmit={save} style={{ maxWidth: 640 }}>
        <div className="card" style={{ marginBottom: 16 }}>
          <strong>Scraper</strong>
          <div className="field" style={{ marginTop: 14 }}>
            <label>Provider</label>
            <select value={form.scraper_provider || "mock"} onChange={(e) => set("scraper_provider", e.target.value)}>
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            <div className="hint">
              Switch to <code>instagrapi</code> for real data, then provide Instagram login below. The
              session is cached so you won't re-log in every run.
            </div>
          </div>
          <div className="field">
            <label>Recent media to sample for engagement</label>
            <input
              type="number"
              min={1}
              max={50}
              value={form.recent_media_count ?? 12}
              onChange={(e) => set("recent_media_count", Number(e.target.value))}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <strong>Instagram credentials</strong>
          <div className="hint" style={{ marginBottom: 12 }}>
            Used only by the <code>instagrapi</code> provider. Stored in the DB, never in the repo.
          </div>
          <div className="grid grid-2">
            <div className="field">
              <label>Username</label>
              <input
                value={form.insta_username || ""}
                onChange={(e) => set("insta_username", e.target.value)}
                placeholder="your instagram username"
                autoComplete="username"
              />
            </div>
            <div className="field">
              <label>Password</label>
              <input
                type="password"
                value={form.insta_password === "********" ? "" : form.insta_password || ""}
                onChange={(e) => set("insta_password", e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
              {form.insta_password === "********" && <div className="hint">Leave blank to keep current password.</div>}
            </div>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Proxy (optional)</label>
            <input
              value={form.insta_proxy || ""}
              onChange={(e) => set("insta_proxy", e.target.value)}
              placeholder="http://user:pass@host:port"
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <strong>Scheduler</strong>
          <div className="field" style={{ marginTop: 14 }}>
            <label>Enabled</label>
            <select
              value={form.schedule_enabled ? "true" : "false"}
              onChange={(e) => set("schedule_enabled", e.target.value === "true")}
            >
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>
          <div className="field">
            <label>Schedule (cron, 5 fields, UTC)</label>
            <input
              value={form.schedule_cron || "0 3 * * *"}
              onChange={(e) => set("schedule_cron", e.target.value)}
              placeholder="0 3 * * *"
            />
            <div className="hint">Default <code>0 3 * * *</code> = every day at 03:00 UTC. e.g. every 6h: <code>0 */6 * * *</code></div>
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Delay between handles (seconds)</label>
            <input
              type="number"
              min={0}
              step={0.5}
              value={form.per_handle_delay ?? 2}
              onChange={(e) => set("per_handle_delay", Number(e.target.value))}
            />
            <div className="hint">Pacing helps avoid Instagram rate limits. 0 disables delay.</div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <strong>Telegram daily report</strong>
          <p className="hint">Posts the trend chart and both growth leaderboards every 24 hours while this app is running. First automatic send is 24 hours after enabling. Restarting the app or saving settings restarts the interval. Reports use stored data; keep scheduled checks enabled.</p>
          <div className="field">
            <label>Bot token (private)</label>
            <input type="password" autoComplete="off" value={form.telegram_bot_token === "********" ? "" : form.telegram_bot_token || ""}
              placeholder={form.telegram_bot_token === "********" ? "Token saved — leave unchanged to keep" : "Enter your replacement bot token"}
              onChange={e => set("telegram_bot_token", e.target.value)} />
            <div className="hint">Stored in the local database, masked in API responses. Protect your data folder and backups. Never share your token.</div>
          </div>
          <div className="field"><label>Group chat ID</label>
            <input value={form.telegram_chat_id || ""} onChange={e => set("telegram_chat_id", e.target.value)} />
          </div>
          <div className="field"><label>Topic ID (0 for no topic)</label>
            <input type="number" min="0" value={form.telegram_thread_id ?? 0} onChange={e => set("telegram_thread_id", Number(e.target.value))} />
          </div>
          <div className="field"><label>Leaderboard period</label>
            <select value={form.telegram_period || 1} onChange={e => set("telegram_period", Number(e.target.value))}>
              {[1,7,14,30,90].map(n => <option key={n} value={n}>{n} day(s)</option>)}
            </select>
          </div>
          <div className="field"><label>Automatic delivery</label>
            <select value={form.telegram_enabled ? "true" : "false"} onChange={e => set("telegram_enabled", e.target.value === "true")}>
              <option value="false">Disabled</option><option value="true">Every 24 hours</option>
            </select>
          </div>
          <button className="btn secondary" type="button" disabled={sending || saving} onClick={async () => {
            setSending(true);
            try { await api.telegramTest(); toast("Report sent to Telegram", "success"); }
            catch (err) { toast(err.message, "error"); }
            finally { setSending(false); }
          }}>{sending ? "Sending…" : "Send test report"}</button>
          <p className="hint">Save settings before testing. At least two days of successful captures are required. Destination: GCC and EcoAuto → Ecoauto - Instagram Scraper.</p>
        </div>

        <div className="row">
          <button className="btn" type="submit" disabled={saving}>{saving ? "Saving…" : "Save settings"}</button>
          <button className="btn secondary" type="button" onClick={reschedule}>Restart scheduler now</button>
        </div>
      </form>
    </>
  );
}
