// Thin fetch wrapper: attaches the bearer token, normalizes errors.
const TOKEN_KEY = "instabi_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });

  if (res.status === 401) {
    setToken(null);
    if (auth) window.dispatchEvent(new Event("instabi-unauth"));
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (username, password) =>
    request("/api/auth/login", { method: "POST", body: { username, password }, auth: false }),
  me: () => request("/api/auth/me", { auth: true }),

  listHandles: () => request("/api/handles"),
  createHandle: (body) => request("/api/handles", { method: "POST", body }),
  bulkAdd: (body) => request("/api/handles/bulk", { method: "POST", body }),
  updateHandle: (id, body) => request(`/api/handles/${id}`, { method: "PUT", body }),
  deleteHandle: (id) => request(`/api/handles/${id}`, { method: "DELETE" }),
  checkHandle: (id) => request(`/api/handles/${id}/check`, { method: "POST" }),
  checkAll: () => request("/api/handles/check-all", { method: "POST" }),

  overview: () => request("/api/overview"),
  compare: (limit = 50) => request(`/api/compare?limit=${limit}`),
  snapshots: (limit = 200) => request(`/api/snapshots?limit=${limit}`),
  handleSnapshots: (id) => request(`/api/handles/${id}/snapshots`),

  listRuns: (limit = 50) => request(`/api/runs?limit=${limit}`),
  schedulerStatus: () => request("/api/scheduler"),
  runNow: () => request("/api/scheduler/run", { method: "POST" }),
  reschedule: () => request("/api/scheduler/reschedule", { method: "POST" }),

  getSettings: () => request("/api/settings"),
  updateSettings: (patch) => request("/api/settings", { method: "PUT", body: patch }),
};
