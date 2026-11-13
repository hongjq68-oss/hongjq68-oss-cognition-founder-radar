import { ArrowLeft, Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Any } from "../api";
import CandidateCard, { Unknown } from "../components/CandidateCard";
import { Badge, Card, Empty, PageHeader, SourceLink, Synthetic } from "../components/ui";
import { useApp } from "../ctx";

export default function Companies() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Any[] | null>(null);
  useEffect(() => { const t = setTimeout(() => api.companies(q).then(setRows), 200); return () => clearTimeout(t); }, [q]);
  return (
    <div>
      <PageHeader title="Company database" subtitle="Ventures our candidates founded or built — linked to the people behind them." />
      <input className="input max-w-sm mb-4" placeholder="Search name, product, sector…" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Company", "Product", "Country", "Founded", "Sector", "Status", "Funding / accelerator", "People"].map((h) => <th key={h} className="p-3">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">
            {rows?.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="p-3"><Link to={`/companies/${c.id}`} className="font-medium text-slate-900 hover:text-brand-700">{c.name}</Link> <Synthetic show={c.is_synthetic} /></td>
                <td className="p-3 text-slate-600 max-w-xs">{c.product || <Unknown />}</td>
                <td className="p-3">{c.country || <Unknown />}</td>
                <td className="p-3">{c.founded_year ?? <Unknown />}</td>
                <td className="p-3">{c.sector || <Unknown />}</td>
                <td className="p-3"><Badge>{c.venture_status}</Badge></td>
                <td className="p-3 text-xs text-slate-600">{[c.funding, c.accelerator].filter(Boolean).join(" · ") || <Unknown />}</td>
                <td className="p-3">{c.people}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows?.length === 0 && <Empty icon={<Building2 />} title="No companies" />}
      </div>
    </div>
  );
}

export function CompanyDetail() {
  const { id } = useParams();
  const { meta } = useApp();
  const [c, setC] = useState<Any>(null);
  useEffect(() => { api.company(id!).then(setC); }, [id]);
  if (!c) return <div className="text-slate-500">Loading…</div>;
  return (
    <div>
      <Link to="/companies" className="text-sm text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 mb-4"><ArrowLeft className="h-4 w-4" />Companies</Link>
      <PageHeader title={c.name} subtitle={<span className="flex items-center gap-2">{c.sector ?? "Sector unknown"} · {[c.city, c.country].filter(Boolean).join(", ") || "Location unknown"} <Synthetic show={c.is_synthetic} /></span>} />
      <div className="grid lg:grid-cols-3 gap-5">
        <Card title="Venture">
          <dl className="space-y-3 text-sm">
            {[["Product", c.product], ["Founded", c.founded_year], ["Status", c.venture_status], ["Funding", c.funding], ["Accelerator", c.accelerator], ["Source", c.source]].map(([k, v]) => (
              <div key={k}><dt className="text-[11px] uppercase text-slate-400 font-medium">{k}</dt><dd>{v ?? <Unknown />}</dd></div>
            ))}
            {c.website && <SourceLink url={c.website} label="Website" />}
          </dl>
          {c.events.length > 0 && <div className="mt-4"><div className="label">Official events</div>{c.events.map((e: Any) => <div key={e.id} className="text-xs text-slate-600 mb-1">{e.event_date} · {e.event_type}: {e.summary}</div>)}</div>}
        </Card>
        <div className="lg:col-span-2 space-y-4">
          <div className="font-semibold text-slate-800">People ({c.people.length})</div>
          {c.people.map((p: Any) => <CandidateCard key={p.id} p={p} caps={meta.capabilities} extra={<Badge tone="cyan">{p.relation}</Badge>} />)}
        </div>
      </div>
    </div>
  );
}
