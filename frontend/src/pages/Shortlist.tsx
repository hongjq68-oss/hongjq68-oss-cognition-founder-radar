import { ListChecks, Save, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import CandidateCard from "../components/CandidateCard";
import { Card, Empty, PageHeader } from "../components/ui";
import { useApp } from "../ctx";

export default function ShortlistPage() {
  const { meta, can, toast } = useApp();
  const [c, setC] = useState<Any>({ countries: [], categories: [], role_id: meta.roles[0]?.id, min_fit: 40, ai: [], founded_from: null, min_score: 35, min_evidence: 2, exclude_unavailable: true, limit: 15 });
  const [res, setRes] = useState<Any>(null);
  const [name, setName] = useState("");
  const [saved, setSaved] = useState<Any[]>([]);
  const [view, setView] = useState<Any>(null);
  const loadSaved = () => api.shortlists().then(setSaved);
  useEffect(() => { loadSaved(); }, []);
  const tog = (k: string, v: string) => setC({ ...c, [k]: c[k].includes(v) ? c[k].filter((x: string) => x !== v) : [...c[k], v] });
  const gen = async () => { try { setView(null); setRes(await api.genShortlist(c)); } catch (e) { toast((e as Error).message); } };
  const save = async () => {
    try { await api.saveShortlist({ name, criteria: c, person_ids: res.people.map((p: Any) => p.id) }); toast("Shortlist saved", "ok"); setName(""); loadSaved(); } catch (e) { toast((e as Error).message); }
  };
  const role = meta.roles.find((r: Any) => r.id === c.role_id);
  const list = view?.people ?? res?.people;
  return (
    <div>
      <PageHeader title="Shortlist generator" subtitle="A focused, explained list — bounded in size, evidence-gated, never hundreds of unqualified profiles." />
      <div className="grid lg:grid-cols-[300px_1fr] gap-6">
        <div className="space-y-5">
          <Card title="Criteria">
            <div className="space-y-4 text-sm">
              <div><div className="label">Target Cognition role</div>
                <select className="input" value={c.role_id ?? ""} onChange={(e) => setC({ ...c, role_id: e.target.value ? +e.target.value : null })}>
                  <option value="">Any</option>{meta.roles.map((r: Any) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></div>
              <Chips label="Markets" opts={meta.countries} sel={c.countries} onT={(v) => tog("countries", v)} />
              <Chips label="Categories" opts={Object.keys(meta.categories)} labels={meta.categories} sel={c.categories} onT={(v) => tog("categories", v)} />
              <Chips label="AI relevance" opts={["High", "Medium", "Low"]} sel={c.ai} onT={(v) => tog("ai", v)} />
              <div className="grid grid-cols-2 gap-2">
                <Num label="Min role fit" v={c.min_fit} on={(v) => setC({ ...c, min_fit: v })} />
                <Num label="Min relevance" v={c.min_score} on={(v) => setC({ ...c, min_score: v })} />
                <Num label="Min evidence" v={c.min_evidence} on={(v) => setC({ ...c, min_evidence: v })} />
                <Num label="Max results" v={c.limit} on={(v) => setC({ ...c, limit: Math.min(50, v) })} />
                <Num label="Founded from" v={c.founded_from ?? ""} on={(v) => setC({ ...c, founded_from: v || null })} />
              </div>
              <label className="flex items-center gap-2"><input type="checkbox" checked={c.exclude_unavailable} onChange={(e) => setC({ ...c, exclude_unavailable: e.target.checked })} />Exclude "Not currently available"</label>
              <button className="btn-primary w-full justify-center" onClick={gen}><Wand2 className="h-4 w-4" />Generate shortlist</button>
            </div>
          </Card>
          <Card title="Saved shortlists">
            {saved.length === 0 && <div className="text-sm text-slate-500">None yet.</div>}
            {saved.map((s) => <button key={s.id} onClick={() => api.shortlist(s.id).then(setView)} className="w-full text-left text-sm py-1.5 hover:text-brand-700"><div className="font-medium">{s.name}</div><div className="text-xs text-slate-400">{s.count} people · {s.created_by} · {s.created_at?.slice(0, 10)}</div></button>)}
          </Card>
        </div>
        <div>
          {!list && <Empty icon={<ListChecks />} title="Set criteria and generate">Each result shows why it was included, its evidence and what still needs validation.</Empty>}
          {list && (
            <>
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <div className="text-sm text-slate-600">{view ? <>Saved shortlist <b>{view.name}</b></> : <>{list.length} candidates{role && <> for <b>{role.name}</b></>}{res.excluded != null && <span className="text-slate-400"> · {res.excluded} excluded by evidence gates</span>}</>}</div>
                {!view && can("research") && list.length > 0 && <div className="ml-auto flex gap-2"><input className="input !w-56" placeholder="Shortlist name" value={name} onChange={(e) => setName(e.target.value)} /><button className="btn-secondary" disabled={!name} onClick={save}><Save className="h-4 w-4" />Save</button></div>}
              </div>
              <div className="space-y-4">{list.map((p: Any, i: number) => (
                <div key={p.id}>
                  {p.shortlist_reasons && <div className="rounded-t-xl bg-brand-50 border border-b-0 border-brand-100 px-5 py-2 text-xs text-brand-800"><b>#{i + 1} — why included:</b> {p.shortlist_reasons.join(" · ")}</div>}
                  <CandidateCard p={p} caps={meta.capabilities} extra={<Link to={`/people/${p.id}`} className="text-xs text-slate-500">Open</Link>} />
                </div>))}</div>
              {list.length === 0 && <div className="text-sm text-slate-500">No candidates pass the evidence gates. Loosen criteria or add evidence.</div>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Chips({ label, opts, labels, sel, onT }: { label: string; opts: string[]; labels?: Record<string, string>; sel: string[]; onT: (v: string) => void }) {
  return <div><div className="label">{label}</div><div className="flex flex-wrap gap-1">{opts.map((o) => <button key={o} onClick={() => onT(o)} className={`chip border ${sel.includes(o) ? "bg-brand-600 text-white border-brand-600" : "border-slate-200 text-slate-600"}`}>{labels?.[o] ?? o}</button>)}</div></div>;
}
function Num({ label, v, on }: { label: string; v: number | string; on: (v: number) => void }) {
  return <div><div className="text-xs text-slate-500 mb-1">{label}</div><input className="input" type="number" value={v} onChange={(e) => on(+e.target.value)} /></div>;
}
