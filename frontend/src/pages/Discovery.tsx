import { Download, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, download, qs, type Any } from "../api";
import CandidateCard from "../components/CandidateCard";
import { Empty, PageHeader } from "../components/ui";
import { useApp } from "../ctx";

const MULTI = ["country", "category", "ai", "capability", "venture_status", "availability", "status"];

export default function Discovery() {
  const { meta, can, toast } = useApp();
  const [sp, setSp] = useSearchParams();
  const [people, setPeople] = useState<Any[] | null>(null);
  const params = useMemo(() => {
    const o: Record<string, unknown> = {};
    sp.forEach((v, k) => { if (MULTI.includes(k)) o[k] = [...((o[k] as string[]) || []), v]; else o[k] = v; });
    return o;
  }, [sp]);
  const load = () => api.people(params).then(setPeople);
  useEffect(() => { load(); }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k: string, v: string | string[] | null) => {
    const n = new URLSearchParams(sp);
    n.delete(k);
    if (Array.isArray(v)) v.forEach((x) => n.append(k, x)); else if (v) n.set(k, v);
    setSp(n);
  };
  const toggle = (k: string, v: string) => {
    const cur = sp.getAll(k);
    set(k, cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]);
  };
  const save = async (p: Any) => {
    try { await api.patchPerson(p.id, { saved: !p.saved }); load(); } catch (e) { toast((e as Error).message); }
  };

  return (
    <div>
      <PageHeader title="Discovery" subtitle="Search founders, former founders, intrapreneurs and independent builders by evidence of what they built."
        actions={can("audit") && <button className="btn-secondary" onClick={() => download(`/api/export/people.csv?${qs({ ...params, scope: "filtered" })}`, "founder-radar.csv").catch((e) => toast(e.message))}><Download className="h-4 w-4" />Export CSV</button>} />
      <div className="grid lg:grid-cols-[260px_1fr] gap-6">
        <aside className="card p-4 h-fit space-y-4 text-sm lg:sticky lg:top-0">
          <div className="flex items-center justify-between"><div className="font-semibold flex items-center gap-2"><SlidersHorizontal className="h-4 w-4" />Filters</div>
            {sp.toString() && <button className="text-xs text-brand-700" onClick={() => setSp(new URLSearchParams())}>Clear</button>}</div>
          <input className="input" placeholder="Keyword (product, claim, name)" defaultValue={sp.get("q") ?? ""} key={sp.get("q") ?? ""}
            onKeyDown={(e) => e.key === "Enter" && set("q", (e.target as HTMLInputElement).value)} />
          <Group title="Category" opts={Object.entries(meta.categories)} sel={sp.getAll("category")} onToggle={(v) => toggle("category", v)} />
          <Group title="Country" opts={meta.countries.map((c: string) => [c, c])} sel={sp.getAll("country")} onToggle={(v) => toggle("country", v)} />
          <div>
            <div className="label">Founding year</div>
            <div className="flex gap-2">
              <input className="input" placeholder="From" defaultValue={sp.get("founded_from") ?? ""} onBlur={(e) => set("founded_from", e.target.value)} />
              <input className="input" placeholder="To" defaultValue={sp.get("founded_to") ?? ""} onBlur={(e) => set("founded_to", e.target.value)} />
            </div>
          </div>
          <Group title="AI relevance" opts={["High", "Medium", "Low", "Unknown"].map((x) => [x, x])} sel={sp.getAll("ai")} onToggle={(v) => toggle("ai", v)} />
          <Group title="Capability evidenced" opts={Object.entries(meta.capabilities)} sel={sp.getAll("capability")} onToggle={(v) => toggle("capability", v)} />
          <Group title="Venture status" opts={meta.venture_statuses.map((c: string) => [c, c])} sel={sp.getAll("venture_status")} onToggle={(v) => toggle("venture_status", v)} />
          <div>
            <div className="label">Role match</div>
            <select className="input" value={sp.get("role_id") ?? ""} onChange={(e) => { set("role_id", e.target.value); }}>
              <option value="">Any role</option>
              {meta.roles.map((r: Any) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
            {sp.get("role_id") && <select className="input mt-2" value={sp.get("min_fit") ?? "40"} onChange={(e) => set("min_fit", e.target.value)}>
              {[0, 40, 60, 80].map((x) => <option key={x} value={x}>Fit ≥ {x}</option>)}
            </select>}
          </div>
          <Group title="Availability" opts={meta.availability.map((c: string) => [c, c])} sel={sp.getAll("availability")} onToggle={(v) => toggle("availability", v)} />
          <Group title="Verification status" opts={Object.entries(meta.research_statuses)} sel={sp.getAll("status")} onToggle={(v) => toggle("status", v)} />
          <label className="flex items-center gap-2"><input type="checkbox" checked={sp.get("saved") === "true"} onChange={(e) => set("saved", e.target.checked ? "true" : null)} />Saved to pipeline only</label>
        </aside>
        <div>
          <div className="flex items-center justify-between mb-3 text-sm">
            <div className="text-slate-600">{people ? `${people.length} candidates` : "Loading…"}
              {[...sp.entries()].map(([k, v]) => <button key={k + v} onClick={() => MULTI.includes(k) ? toggle(k, v) : set(k, null)} className="chip bg-brand-50 text-brand-700 ml-2">{meta.categories[v] ?? meta.research_statuses[v] ?? meta.capabilities[v] ?? (k === "role_id" ? meta.roles.find((r: Any) => String(r.id) === v)?.name : v)}<X className="h-3 w-3" /></button>)}
            </div>
            <select className="input !w-auto" value={sp.get("sort") ?? "score"} onChange={(e) => set("sort", e.target.value)}>
              <option value="score">Sort: research relevance</option><option value="recent">Sort: recently updated</option><option value="name">Sort: name</option>
            </select>
          </div>
          <div className="space-y-4">
            {people?.length === 0 && <Empty icon={<SlidersHorizontal />} title="No candidates match">Loosen filters, or import candidates from an approved source.</Empty>}
            {people?.map((p) => <CandidateCard key={p.id} p={p} caps={meta.capabilities} onSave={can("research") ? save : undefined} />)}
          </div>
          <p className="text-xs text-slate-400 mt-6">{meta.disclaimer}</p>
        </div>
      </div>
    </div>
  );
}

function Group({ title, opts, sel, onToggle }: { title: string; opts: [string, string][]; sel: string[]; onToggle: (v: string) => void }) {
  return (
    <div>
      <div className="label">{title}</div>
      <div className="flex flex-wrap gap-1">
        {opts.map(([v, l]) => (
          <button key={v} onClick={() => onToggle(v)} className={`chip border ${sel.includes(v) ? "bg-brand-600 text-white border-brand-600" : "bg-white text-slate-600 border-slate-200 hover:border-brand-300"}`}>{l}</button>
        ))}
      </div>
    </div>
  );
}
