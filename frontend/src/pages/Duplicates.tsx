import { Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { Badge, Card, Empty, PageHeader, Synthetic } from "../components/ui";
import { useApp } from "../ctx";

export default function Duplicates() {
  const { can, toast } = useApp();
  const [rows, setRows] = useState<Any[] | null>(null);
  const load = () => api.duplicates().then(setRows);
  useEffect(() => { load(); }, []);
  const merge = async (a: Any, b: Any) => {
    if (!confirm(`Merge ${b.full_name} into ${a.full_name}? Evidence, notes and matches move to the primary record.`)) return;
    try { await api.merge(a.id, b.id); toast("Merged", "ok"); load(); } catch (e) { toast((e as Error).message); }
  };
  return (
    <div>
      <PageHeader title="Duplicate review" subtitle="Possible duplicates across sources. Merging is a human decision and is audit-logged." />
      {rows?.length === 0 && <Empty icon={<Copy />} title="No suspected duplicates" />}
      <div className="space-y-4">
        {rows?.map((d, i) => (
          <Card key={i} title={<Badge tone="amber">{d.reason}</Badge>}>
            <div className="grid md:grid-cols-2 gap-4">
              {[[d.a, d.b], [d.b, d.a]].map(([x, y]) => (
                <div key={x.id} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <Link to={`/people/${x.id}`} className="font-medium hover:text-brand-700">{x.full_name}</Link> <Synthetic show={x.is_synthetic} />
                  <div className="text-xs text-slate-500">{x.title} · {x.company?.name ?? "No company"} · {x.city}, {x.country}</div>
                  <div className="text-xs text-slate-500">{x.evidence_count} evidence · source {x.source} · score {x.score}</div>
                  {can("verify") && <button className="btn-secondary !py-1 text-xs mt-2" onClick={() => merge(x, y)}>Keep this, merge other into it</button>}
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
