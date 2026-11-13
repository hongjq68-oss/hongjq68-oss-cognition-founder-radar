import { AlertTriangle, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { Badge, Card, PageHeader, SourceLink, Synthetic } from "../components/ui";
import { useApp } from "../ctx";

export default function Watchlist() {
  const { can, toast, meta } = useApp();
  const [d, setD] = useState<Any>(null);
  const [open, setOpen] = useState(false);
  const [wc, setWc] = useState("");
  const [ev, setEv] = useState({ company_name: "", event_type: "Restructuring", event_date: "", summary: "", affected_areas: "", capability_clusters: "", opt_in_channels: "", source_url: "" });
  const load = () => api.watchlist().then(setD);
  useEffect(() => { load(); }, []);
  const go = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok, "ok"); load(); } catch (e) { toast((e as Error).message); } };
  if (!d) return <div className="text-slate-500">Loading…</div>;
  const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
  return (
    <div>
      <PageHeader title="Research watchlist" subtitle="Monitor official company announcements and accelerator batches to create research tasks — not to label individuals." />
      <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 flex gap-2"><AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />{d.guardrail} Use these signals to research opt-in channels (alumni communities, public "open to work" posts, events).</div>
      <div className="grid lg:grid-cols-3 gap-5">
        <Card title="Monitored companies" action={can("research") && <div className="flex gap-1"><input className="input !py-1 !w-32 text-xs" placeholder="Add company" value={wc} onChange={(e) => setWc(e.target.value)} /><button className="btn-ghost !p-1" disabled={!wc} onClick={() => go(async () => { await api.addWatchCompany({ name: wc }); setWc(""); }, "Added")}><Plus className="h-4 w-4" /></button></div>}>
          <div className="divide-y divide-slate-100 -my-2">{d.companies.map((c: Any) => <div key={c.id} className="py-2 text-sm flex justify-between"><div><div className="font-medium">{c.name}</div><div className="text-xs text-slate-500">{c.kind}</div></div><span className="text-xs text-slate-500">{c.events} events</span></div>)}</div>
        </Card>
        <div className="lg:col-span-2 space-y-5">
          <Card title="Official events" action={can("research") && <button className="btn-secondary !py-1 text-xs" onClick={() => setOpen(!open)}><Plus className="h-3.5 w-3.5" />Log event</button>}>
            {open && (
              <div className="grid sm:grid-cols-2 gap-2 mb-4 text-sm">
                <input className="input" placeholder="Company / segment" value={ev.company_name} onChange={(e) => setEv({ ...ev, company_name: e.target.value })} />
                <select className="input" value={ev.event_type} onChange={(e) => setEv({ ...ev, event_type: e.target.value })}>{(meta.watch_event_types as string[]).map((x) => <option key={x}>{x}</option>)}</select>
                <input className="input sm:col-span-2" placeholder="Official source URL (required)" value={ev.source_url} onChange={(e) => setEv({ ...ev, source_url: e.target.value })} />
                <input className="input" type="date" value={ev.event_date} onChange={(e) => setEv({ ...ev, event_date: e.target.value })} />
                <input className="input" placeholder="Affected functions/regions (as stated)" value={ev.affected_areas} onChange={(e) => setEv({ ...ev, affected_areas: e.target.value })} />
                <textarea className="input sm:col-span-2" rows={2} placeholder="Summary of the official announcement" value={ev.summary} onChange={(e) => setEv({ ...ev, summary: e.target.value })} />
                <input className="input" placeholder="Capability clusters (comma-separated)" value={ev.capability_clusters} onChange={(e) => setEv({ ...ev, capability_clusters: e.target.value })} />
                <input className="input" placeholder="Opt-in channels (comma-separated)" value={ev.opt_in_channels} onChange={(e) => setEv({ ...ev, opt_in_channels: e.target.value })} />
                <div className="sm:col-span-2 flex justify-end"><button className="btn-primary" disabled={!ev.company_name || !ev.summary} onClick={() => go(async () => { await api.addEvent({ ...ev, event_date: ev.event_date || null, capability_clusters: split(ev.capability_clusters), opt_in_channels: split(ev.opt_in_channels) }); setOpen(false); }, "Event logged and research task created")}>Save event</button></div>
              </div>
            )}
            <div className="space-y-4">
              {d.events.length === 0 && <div className="text-sm text-slate-500">No events. Add only from official announcements.</div>}
              {d.events.map((e: Any) => (
                <div key={e.id} className="text-sm border-l-2 border-brand-200 pl-3">
                  <div className="flex items-center gap-2 font-medium">{e.company_name} <Badge>{e.event_type}</Badge> <Synthetic show={e.is_synthetic} /><span className="text-xs text-slate-400 font-normal">{e.event_date}</span></div>
                  <div className="text-slate-700 mt-1">{e.summary}</div>
                  <div className="text-xs text-slate-500 mt-1">Affected areas: {e.affected_areas || "Unknown"} · Clusters: {e.capability_clusters.join(", ") || "—"} · Opt-in channels: {e.opt_in_channels.join(", ") || "—"}</div>
                  <SourceLink url={e.source_url} />
                </div>
              ))}
            </div>
          </Card>
          <Card title="Research tasks">
            <div className="divide-y divide-slate-100 -my-2">
              {d.tasks.map((t: Any) => (
                <div key={t.id} className="py-2.5 flex items-start gap-3 text-sm">
                  <input type="checkbox" className="mt-1" disabled={!can("research")} checked={t.status === "Done"} onChange={(e) => go(() => api.patchTask(t.id, { status: e.target.checked ? "Done" : "Open" }), "Task updated")} />
                  <div className="flex-1"><div className={t.status === "Done" ? "line-through text-slate-400" : "font-medium"}>{t.title}</div><div className="text-xs text-slate-500">{t.detail}</div>{t.person_id && <Link to={`/people/${t.person_id}`} className="text-xs text-brand-700">Open candidate</Link>}</div>
                  <select className="input !w-36 !py-1 text-xs" disabled={!can("research")} value={t.assignee_id ?? ""} onChange={(e) => go(() => api.patchTask(t.id, { assignee_id: e.target.value ? +e.target.value : null }), "Assigned")}>
                    <option value="">Unassigned</option>{meta.users.map((u: Any) => <option key={u.id} value={u.id}>{u.name}</option>)}</select>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
