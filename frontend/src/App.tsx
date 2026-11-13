import clsx from "clsx";
import { Building2, ClipboardList, Copy, FileUp, KanbanSquare, LayoutDashboard, ListChecks, LogOut, Plug, Radar, ScrollText, Search, ShieldCheck, Target } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, getToken, setToken, type Any } from "./api";
import { Toast } from "./components/ui";
import { AppCtx, type Me } from "./ctx";
import Audit from "./pages/Audit";
import Companies, { CompanyDetail } from "./pages/Companies";
import Dashboard from "./pages/Dashboard";
import Discovery from "./pages/Discovery";
import Duplicates from "./pages/Duplicates";
import ImportPage from "./pages/Import";
import Login from "./pages/Login";
import PersonPage from "./pages/Person";
import Pipeline from "./pages/Pipeline";
import Roles from "./pages/Roles";
import ShortlistPage from "./pages/Shortlist";
import Sources from "./pages/Sources";
import Watchlist from "./pages/Watchlist";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/discover", label: "Discovery", icon: Search },
  { to: "/shortlist", label: "Shortlist", icon: ListChecks },
  { to: "/pipeline", label: "Recruiter workspace", icon: KanbanSquare },
  { to: "/companies", label: "Companies", icon: Building2 },
  { to: "/watchlist", label: "Research watchlist", icon: ClipboardList },
  { to: "/import", label: "Import & discover", icon: FileUp },
  { to: "/roles", label: "Cognition roles", icon: Target },
  { to: "/duplicates", label: "Duplicates", icon: Copy },
  { to: "/sources", label: "Sources", icon: Plug },
  { to: "/audit", label: "Audit log", icon: ScrollText, perm: "audit" },
];

export default function App() {
  const loc = useLocation();
  if (loc.pathname === "/login") return <Login />;
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Shell />;
}

function Shell() {
  const [me, setMe] = useState<Me | null>(null);
  const [meta, setMeta] = useState<Any>(null);
  const [t, setT] = useState<{ msg: string; kind: "error" | "ok" } | null>(null);
  const navigate = useNavigate();
  const toast = useCallback((msg: string, kind: "error" | "ok" = "error") => { setT({ msg, kind }); setTimeout(() => setT(null), 5000); }, []);
  useEffect(() => { api.me().then(setMe); api.meta().then(setMeta); }, []);
  if (!me || !meta) return <div className="p-10 text-slate-500">Loading…</div>;
  const can = (p: string) => me.permissions.includes(p);
  return (
    <AppCtx.Provider value={{ me, meta, can, toast }}>
      <div className="flex h-screen overflow-hidden">
        <aside className="hidden md:flex w-64 shrink-0 flex-col bg-ink-900 text-slate-300">
          <div className="flex items-center gap-2.5 px-5 h-16 border-b border-white/5">
            <div className="h-8 w-8 rounded-lg bg-brand-600 flex items-center justify-center"><Radar className="text-white" size={18} /></div>
            <div>
              <div className="text-white font-semibold leading-tight">Founder Radar</div>
              <div className="text-[11px] text-slate-400">Cognition talent intelligence</div>
            </div>
          </div>
          <nav className="px-3 py-3 space-y-0.5 overflow-y-auto">
            {nav.filter((n) => !n.perm || can(n.perm)).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                className={({ isActive }) => clsx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition", isActive ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white")}>
                <n.icon className="h-4 w-4" />{n.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto p-4 m-3 rounded-xl bg-white/5 text-xs space-y-1.5">
            <div className="text-slate-400 font-medium uppercase tracking-wide text-[10px]">Research engine</div>
            <div className="flex items-center gap-2"><span className={clsx("h-1.5 w-1.5 rounded-full", meta.llm ? "bg-emerald-400" : "bg-amber-400")} />{meta.llm ? `AI: ${meta.llm}` : "AI: rules-based mode"}</div>
            <div className="flex items-center gap-2"><ShieldCheck className="h-3 w-3 text-emerald-400" />Human approval before outreach</div>
          </div>
        </aside>
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-16 shrink-0 bg-white border-b border-slate-200 flex items-center px-6 gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input className="input pl-9 bg-slate-50" placeholder="Search people, products, evidence…"
                onKeyDown={(e) => { if (e.key === "Enter") navigate(`/discover?q=${encodeURIComponent((e.target as HTMLInputElement).value)}`); }} />
            </div>
            <div className="ml-auto flex items-center gap-3">
              <span className="chip bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200 hidden lg:inline-flex">Demo data is synthetic</span>
              <div className="text-right leading-tight">
                <div className="text-sm font-medium text-slate-800">{me.name}</div>
                <div className="text-xs text-slate-500 capitalize">{me.role}</div>
              </div>
              <button className="btn-ghost !px-2" title="Sign out" onClick={() => { setToken(null); navigate("/login"); }}><LogOut className="h-4 w-4" /></button>
            </div>
          </header>
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-7xl mx-auto p-6">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/discover" element={<Discovery />} />
                <Route path="/people/:id" element={<PersonPage />} />
                <Route path="/shortlist" element={<ShortlistPage />} />
                <Route path="/pipeline" element={<Pipeline />} />
                <Route path="/companies" element={<Companies />} />
                <Route path="/companies/:id" element={<CompanyDetail />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/import" element={<ImportPage />} />
                <Route path="/roles" element={<Roles />} />
                <Route path="/duplicates" element={<Duplicates />} />
                <Route path="/sources" element={<Sources />} />
                <Route path="/audit" element={<Audit />} />
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
      <Toast msg={t?.msg ?? null} kind={t?.kind} onClose={() => setT(null)} />
    </AppCtx.Provider>
  );
}
