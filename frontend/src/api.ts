/* eslint-disable @typescript-eslint/no-explicit-any */
export type Any = any;

const TOKEN_KEY = "radar_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string | null) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

async function req<T = Any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  const r = await fetch(path, { ...init, headers });
  if (r.status === 401 && !path.startsWith("/api/auth")) { setToken(null); window.location.href = "/login"; }
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail ?? msg; } catch { /* ignore */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  const ct = r.headers.get("content-type") || "";
  return (ct.includes("json") ? r.json() : r.text()) as Promise<T>;
}
const body = (method: string, b: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });

export function qs(params: Record<string, unknown>) {
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && !v.length)) return;
    (Array.isArray(v) ? v : [v]).forEach((x) => u.append(k, String(x)));
  });
  return u.toString();
}

export async function download(path: string, filename: string) {
  const r = await fetch(path, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail; } catch { /* */ } throw new Error(m); }
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  demoUsers: () => req("/api/auth/demo-users"),
  login: (email: string, access_code?: string) => req("/api/auth/login", body("POST", { email, access_code: access_code || undefined })),
  me: () => req("/api/me"),
  meta: () => req("/api/meta"),
  dashboard: () => req("/api/dashboard"),
  people: (params: Record<string, unknown>) => req(`/api/people?${qs(params)}`),
  person: (id: number | string) => req(`/api/people/${id}`),
  createPerson: (b: Any) => req("/api/people", body("POST", b)),
  patchPerson: (id: number, b: Any) => req(`/api/people/${id}`, body("PATCH", b)),
  setStatus: (id: number, status: string) => req(`/api/people/${id}/status`, body("POST", { status })),
  setCheck: (id: number, key: string, ok: boolean) => req(`/api/people/${id}/checklist`, body("POST", { key, ok })),
  addEvidence: (id: number, b: Any) => req(`/api/people/${id}/evidence`, body("POST", b)),
  patchEvidence: (id: number, b: Any) => req(`/api/evidence/${id}`, body("PATCH", b)),
  deleteEvidence: (id: number) => req(`/api/evidence/${id}`, { method: "DELETE" }),
  evidenceFromUrl: (url: string) => req("/api/evidence/from-url", body("POST", { url })),
  refresh: (id: number) => req(`/api/people/${id}/refresh`, { method: "POST" }),
  research: (id: number) => req(`/api/people/${id}/research`, { method: "POST" }),
  match: (id: number, role_id: number) => req(`/api/people/${id}/matches`, body("POST", { role_id })),
  outreach: (id: number, role_id?: number) => req(`/api/people/${id}/outreach`, body("POST", { role_id })),
  patchOutreach: (id: number, b: Any) => req(`/api/outreach/${id}`, body("PATCH", b)),
  addNote: (id: number, text: string) => req(`/api/people/${id}/notes`, body("POST", { body: text })),
  addConversation: (id: number, b: Any) => req(`/api/people/${id}/conversations`, body("POST", b)),
  companies: (q?: string) => req(`/api/companies?${qs({ q })}`),
  company: (id: number | string) => req(`/api/companies/${id}`),
  roles: () => req("/api/roles"),
  addRole: (b: Any) => req("/api/roles", body("POST", b)),
  genShortlist: (b: Any) => req("/api/shortlists/generate", body("POST", b)),
  saveShortlist: (b: Any) => req("/api/shortlists", body("POST", b)),
  shortlists: () => req("/api/shortlists"),
  shortlist: (id: number | string) => req(`/api/shortlists/${id}`),
  watchlist: () => req("/api/watchlist"),
  addWatchCompany: (b: Any) => req("/api/watch-companies", body("POST", b)),
  addEvent: (b: Any) => req("/api/watch-events", body("POST", b)),
  addTask: (b: Any) => req("/api/tasks", body("POST", b)),
  patchTask: (id: number, b: Any) => req(`/api/tasks/${id}`, body("PATCH", b)),
  sources: () => req("/api/sources"),
  toggleSource: (key: string, enabled: boolean) => req(`/api/sources/${key}/toggle`, body("POST", { enabled })),
  runGithub: (b: Any) => req("/api/sources/github/run", body("POST", b)),
  importCsv: (file: File) => { const fd = new FormData(); fd.append("file", file); return req("/api/import/csv", { method: "POST", body: fd }); },
  duplicates: () => req("/api/duplicates"),
  merge: (primary_id: number, duplicate_id: number) => req("/api/duplicates/merge", body("POST", { primary_id, duplicate_id })),
  audit: () => req("/api/audit"),
};
