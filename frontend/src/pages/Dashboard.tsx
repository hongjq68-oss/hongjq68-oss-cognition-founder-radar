import { AlertTriangle, ArrowRight, Bell, CheckCircle2, ClipboardList, Mail } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { Avatar, Badge, Bar, Card, PageHeader, Synthetic } from "../components/ui";
import { useApp } from "../ctx";

export default function Dashboard() {
  const [d, setD] = useState<Any>(null);
  const { meta } = useApp();
  useEffect(() => { api.dashboard().then(setD); }, []);
  if (!d) return <div className="text-slate-500">Loading…</div>;
  const k = d.kpis;
  const kpis = [
    ["Candidates tracked", k.total, "/discover"],
    ["Early-stage founders", k.founders, "/discover?category=early_founder"],
    ["Former founders", k.former_founders, "/discover?category=former_founder"],
    ["Independent builders", k.independent_builders, "/discover?category=independent_builder"],
    ["Intrapreneurs", k.intrapreneurs, "/discover?category=intrapreneur"],
    ["High AI relevance", k.ai_entrepreneurs, "/discover?ai=High"],
    ["Recruiter verified", k.verified, "/discover?status=recruiter_verified"],
    ["Ready for outreach review", k.ready, "/discover?status=ready_for_outreach_review"],
  ];
  return (
    <div>
      <PageHeader title="Founder Radar" subtitle="Exceptional founders, former founders and builders across APAC — ranked by what they have built."
        actions={<><Link to="/shortlist" className="btn-secondary">Generate shortlist</Link><Link to="/discover" className="btn-primary">Discover <ArrowRight className="h-4 w-4" /></Link></>} />
      {k.synthetic > 0 && (
        <div className="mb-5 rounded-lg border border-fuchsia-200 bg-fuchsia-50 px-4 py-2.5 text-sm text-fuchsia-800 flex items-center gap-2">
          <Synthetic /> {k.synthetic} of {k.total} records are fictional demo data. Real candidates arrive via approved sources, CSV import or manual entry.
        </div>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpis.map(([label, v, to]) => (
          <Link key={label as string} to={to as string} className="card p-4 hover:border-brand-300">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="text-2xl font-semibold text-slate-900 mt-1">{v}</div>
          </Link>
        ))}
      </div>
      <div className="grid lg:grid-cols-3 gap-5">
        <Card title="Needs recruiter verification" icon={<AlertTriangle className="h-4 w-4 text-amber-500" />} className="lg:col-span-2"
          action={<Link to="/discover?status=research_identified" className="text-xs text-brand-700">View all {k.needs_verification}</Link>}>
          <div className="divide-y divide-slate-100 -my-2">
            {d.needs_verification.map((p: Any) => (
              <Link key={p.id} to={`/people/${p.id}`} className="flex items-center gap-3 py-2.5 hover:bg-slate-50 -mx-2 px-2 rounded">
                <Avatar name={p.full_name} size={32} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 flex items-center gap-2">{p.full_name} <Synthetic show={p.is_synthetic} /></div>
                  <div className="text-xs text-slate-500 truncate">{p.product_built || p.title} · {p.country}</div>
                </div>
                <Badge tone="violet">{p.category_label}</Badge>
                <div className="text-sm font-semibold w-8 text-right">{p.score}</div>
              </Link>
            ))}
          </div>
        </Card>
        <div className="space-y-5">
          <Card title="Workflow" icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />}>
            <Dist rows={d.by_status} />
            <div className="flex gap-4 mt-4 text-sm">
              <Link to="/watchlist" className="flex items-center gap-1.5 text-slate-600 hover:text-brand-700"><ClipboardList className="h-4 w-4" />{d.open_tasks} open tasks</Link>
              <Link to="/pipeline" className="flex items-center gap-1.5 text-slate-600 hover:text-brand-700"><Mail className="h-4 w-4" />{d.drafts_pending} drafts pending</Link>
            </div>
          </Card>
          <Card title="Availability (evidence-only)"><Dist rows={d.by_availability} tone="bg-cyan-500" /></Card>
        </div>
        <Card title="By market"><Dist rows={d.by_country} link={(c) => `/discover?country=${encodeURIComponent(c)}`} /></Card>
        <Card title="By category"><Dist rows={d.by_category} tone="bg-violet-500" /></Card>
        <Card title="Recent research signals" icon={<Bell className="h-4 w-4 text-brand-500" />} action={<Link to="/watchlist" className="text-xs text-brand-700">Watchlist</Link>}>
          <div className="space-y-3">
            {d.recent_events.length === 0 && <div className="text-sm text-slate-500">No events yet. Events are only added from official announcements.</div>}
            {d.recent_events.map((e: Any) => (
              <div key={e.id} className="text-sm">
                <div className="font-medium text-slate-800 flex items-center gap-2">{e.company_name} <Synthetic show={e.is_synthetic} /></div>
                <div className="text-xs text-slate-500">{e.event_type} · {e.event_date}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <p className="text-xs text-slate-400 mt-6">{meta.disclaimer}</p>
    </div>
  );
}

function Dist({ rows, tone, link }: { rows: [string, number][]; tone?: string; link?: (k: string) => string }) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <div className="space-y-2">
      {rows.map(([k, v]) => (
        <div key={k} className="text-sm">
          <div className="flex justify-between mb-0.5">{link ? <Link to={link(k)} className="text-slate-700 hover:text-brand-700">{k}</Link> : <span className="text-slate-700">{k}</span>}<span className="text-slate-500">{v}</span></div>
          <Bar value={v} max={max} tone={tone} />
        </div>
      ))}
    </div>
  );
}
