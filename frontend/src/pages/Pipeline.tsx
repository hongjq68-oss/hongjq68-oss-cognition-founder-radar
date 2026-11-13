import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { availTone, Avatar, Badge, PageHeader, Synthetic } from "../components/ui";
import { useApp } from "../ctx";

export default function Pipeline() {
  const { meta, me } = useApp();
  const [people, setPeople] = useState<Any[]>([]);
  const [mine, setMine] = useState(false);
  useEffect(() => { api.people({ saved: true, owner_id: mine ? me.id : undefined }).then(setPeople); }, [mine, me.id]);
  const cols = Object.entries(meta.research_statuses) as [string, string][];
  return (
    <div>
      <PageHeader title="Recruiter workspace" subtitle="Shared pipeline of saved candidates, moving from research to human-approved outreach."
        actions={<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />Only mine</label>} />
      <div className="grid md:grid-cols-3 gap-4">
        {cols.map(([k, l]) => {
          const ps = people.filter((p) => p.research_status === k);
          return (
            <div key={k} className="rounded-xl bg-slate-100/70 p-3">
              <div className="flex justify-between px-1 mb-3"><div className="font-semibold text-sm text-slate-700">{l}</div><span className="text-xs text-slate-500">{ps.length}</span></div>
              <div className="space-y-2">
                {ps.map((p) => (
                  <Link key={p.id} to={`/people/${p.id}`} className="block card p-3 hover:border-brand-300">
                    <div className="flex items-center gap-2"><Avatar name={p.full_name} size={28} /><div className="flex-1 min-w-0"><div className="text-sm font-medium truncate">{p.full_name}</div><div className="text-xs text-slate-500 truncate">{p.company?.name ?? p.title}</div></div><span className="text-sm font-semibold">{p.score}</span></div>
                    <div className="flex flex-wrap gap-1 mt-2"><Badge tone="violet" className="!text-[10px]">{p.category_label}</Badge><Badge tone={availTone[p.availability]} className="!text-[10px]">{p.availability}</Badge><Synthetic show={p.is_synthetic} /></div>
                    {p.role_matches[0] && <div className="text-xs text-slate-600 mt-1.5">→ {p.role_matches[0].role}</div>}
                    <div className="text-[11px] text-slate-400 mt-1">{p.owner?.name ?? "Unassigned"} · {p.recommended_action}{p.outreach_reviewed && " · outreach approved"}</div>
                  </Link>
                ))}
                {!ps.length && <div className="text-xs text-slate-400 px-1">Empty</div>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
