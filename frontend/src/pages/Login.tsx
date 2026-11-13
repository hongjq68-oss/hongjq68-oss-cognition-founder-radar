import { Radar } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken, type Any } from "../api";

const roleInfo: Record<string, string> = {
  admin: "Everything, incl. source approval", recruiter: "Verify, approve outreach, export", researcher: "Discover, add evidence, research", viewer: "Read-only",
};

export default function Login() {
  const [users, setUsers] = useState<Any[]>([]);
  const [err, setErr] = useState("");
  const nav = useNavigate();
  useEffect(() => { api.demoUsers().then(setUsers); }, []);
  const go = async (email: string) => {
    try { const r = await api.login(email); setToken(r.token); nav("/"); window.location.reload(); } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center bg-ink-900 p-6">
      <div className="w-full max-w-lg card p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-brand-600 flex items-center justify-center"><Radar className="text-white" /></div>
          <div><div className="text-xl font-semibold text-slate-900">Cognition Founder Radar</div><div className="text-sm text-slate-500">Find people by what they have built.</div></div>
        </div>
        <div className="text-sm text-slate-600 mb-3">Demo sign-in — choose a role (SSO replaces this in production):</div>
        <div className="space-y-2">
          {users.map((u) => (
            <button key={u.email} onClick={() => go(u.email)} className="w-full flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 hover:border-brand-400 hover:bg-brand-50 text-left">
              <div><div className="font-medium text-slate-900">{u.name}</div><div className="text-xs text-slate-500">{u.email}</div></div>
              <div className="text-right"><div className="chip bg-slate-100 text-slate-700 capitalize">{u.role}</div><div className="text-[11px] text-slate-400 mt-1">{roleInfo[u.role]}</div></div>
            </button>
          ))}
        </div>
        {err && <div className="text-sm text-rose-600 mt-3">{err}</div>}
        <p className="text-xs text-slate-400 mt-6">All people, companies and events in the demo dataset are fictional and labelled SYNTHETIC.</p>
      </div>
    </div>
  );
}
