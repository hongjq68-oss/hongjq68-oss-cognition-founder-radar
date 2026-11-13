import { AlertTriangle, ArrowLeft, Check, FileSearch, Link2, Mail, MessageSquare, RefreshCw, ShieldCheck, Sparkles, Target, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Any } from "../api";
import { Unknown } from "../components/CandidateCard";
import { availTone, Avatar, Badge, Bar, Card, confTone, CopyButton, List, ScoreRing, SourceLink, statusTone, Synthetic, Tabs, verTone } from "../components/ui";
import { useApp } from "../ctx";

export default function PersonPage() {
  const { id } = useParams();
  const { meta, can, toast } = useApp();
  const [p, setP] = useState<Any>(null);
  const [tab, setTab] = useState("overview");
  const [busy, setBusy] = useState("");
  const load = useCallback(() => api.person(id!).then(setP), [id]);
  useEffect(() => { load(); }, [load]);
  const run = async (key: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(key);
    try { await fn(); await load(); if (ok) toast(ok, "ok"); } catch (e) { toast((e as Error).message); } finally { setBusy(""); }
  };
  if (!p) return <div className="text-slate-500">Loading…</div>;
  const ctx = { p, meta, can, run, busy };
  return (
    <div>
      <Link to="/discover" className="text-sm text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 mb-4"><ArrowLeft className="h-4 w-4" />Discovery</Link>
      <div className="card p-6 mb-5">
        <div className="flex flex-wrap gap-5 items-start">
          <Avatar name={p.full_name} size={64} />
          <div className="flex-1 min-w-[260px]">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold text-slate-900">{p.full_name}</h1>
              <Synthetic show={p.is_synthetic} />
              <Badge tone={statusTone[p.research_status]}>{p.research_status_label}</Badge>
            </div>
            <div className="text-slate-600 mt-1">{p.title || "Unknown title"}{p.company && <> · <Link to={`/companies/${p.company.id}`} className="hover:underline">{p.company.name}</Link></>}</div>
            <div className="text-sm text-slate-500 mt-1">{[p.city, p.country].filter(Boolean).join(", ") || "Location unknown"} · {p.category_label} · {p.builder_type} · Founded {p.founding_year ?? "Unknown"} · {p.venture_status}</div>
            <div className="flex flex-wrap gap-3 mt-2 text-sm">
              {p.profile_url && <SourceLink url={p.profile_url} label="Public profile" />}
              {p.website && <SourceLink url={p.website} label="Website" />}
              <span className="text-xs text-slate-400">Source: {p.source} · Owner: {p.owner?.name ?? "Unassigned"} · Last verified {p.last_verified_at?.slice(0, 10) ?? "never"}</span>
            </div>
          </div>
          <div className="text-center">
            <ScoreRing score={p.score} size={64} />
            <div className="text-[11px] text-slate-500 mt-1">Research relevance</div>
            <Badge tone={confTone[p.confidence]}>{p.confidence} confidence</Badge>
          </div>
          <div className="w-full md:w-auto md:min-w-[220px] rounded-lg bg-slate-50 p-3 text-sm">
            <div className="text-[11px] uppercase text-slate-400 font-medium">Availability · separate from capability</div>
            <Badge tone={availTone[p.availability]} className="mt-1">{p.availability}</Badge>
            {p.availability_note && <div className="text-xs text-slate-500 mt-1">{p.availability_note}</div>}
            <div className="text-[11px] uppercase text-slate-400 font-medium mt-3">Next action</div>
            <div className="text-brand-700 font-medium">{p.recommended_action}</div>
          </div>
        </div>
      </div>
      <Tabs value={tab} onChange={setTab} tabs={[
        { key: "overview", label: "Overview", icon: <Sparkles className="h-4 w-4" /> },
        { key: "evidence", label: "Evidence", icon: <FileSearch className="h-4 w-4" />, count: p.evidence.length },
        { key: "roles", label: "Role match", icon: <Target className="h-4 w-4" />, count: p.matches.length },
        { key: "outreach", label: "Outreach", icon: <Mail className="h-4 w-4" />, count: p.drafts.length },
        { key: "review", label: "Review & workflow", icon: <ShieldCheck className="h-4 w-4" /> },
        { key: "notes", label: "Notes", icon: <MessageSquare className="h-4 w-4" />, count: p.notes.length + p.conversations.length },
        { key: "activity", label: "Activity", count: p.activity.length },
      ]} />
      <div className="mt-5">
        {tab === "overview" && <Overview {...ctx} />}
        {tab === "evidence" && <EvidenceTab {...ctx} />}
        {tab === "roles" && <RolesTab {...ctx} />}
        {tab === "outreach" && <OutreachTab {...ctx} />}
        {tab === "review" && <ReviewTab {...ctx} />}
        {tab === "notes" && <NotesTab {...ctx} />}
        {tab === "activity" && <Card title="Audit trail for this candidate">
          <div className="divide-y divide-slate-100 text-sm">{p.activity.map((a: Any, i: number) => (
            <div key={i} className="py-2 flex gap-3"><span className="text-slate-400 w-40 shrink-0">{a.ts.slice(0, 16).replace("T", " ")}</span><span className="font-medium w-32 shrink-0">{a.user}</span><span className="font-mono text-xs text-brand-700 w-44 shrink-0">{a.action}</span><span className="text-xs text-slate-500 break-all">{JSON.stringify(a.detail)}</span></div>
          ))}{!p.activity.length && <div className="text-slate-500">No activity yet.</div>}</div>
        </Card>}
      </div>
      <p className="text-xs text-slate-400 mt-6">{meta.disclaimer}</p>
    </div>
  );
}

type Ctx = { p: Any; meta: Any; can: (x: string) => boolean; run: (k: string, fn: () => Promise<unknown>, ok?: string) => Promise<void>; busy: string };

function Overview({ p, meta, can, run, busy }: Ctx) {
  const r = p.research || {};
  const sb = p.score_breakdown;
  return (
    <div className="grid lg:grid-cols-3 gap-5">
      <div className="lg:col-span-2 space-y-5">
        <Card title="What they built">
          <dl className="grid sm:grid-cols-2 gap-4 text-sm">
            <Item k="Product / venture">{p.product_built || <Unknown />}</Item>
            <Item k="Problem solved">{p.problem_solved || <Unknown />}</Item>
            <Item k="AI evidence">{p.ai_evidence || <Unknown />}</Item>
            <Item k="Team built">{p.team_built || <Unknown />}</Item>
            <Item k="Previous ventures">{p.previous_ventures?.length ? p.previous_ventures.join(", ") : <Unknown />}</Item>
            <Item k="Transition evidence">{p.transition_evidence || <Unknown />}</Item>
          </dl>
        </Card>
        <Card title="AI research summary" icon={<Sparkles className="h-4 w-4 text-brand-500" />}
          action={can("research") && <button className="btn-secondary !py-1 text-xs" disabled={busy === "research"} onClick={() => run("research", () => api.research(p.id), "Research summary updated")}>
            <RefreshCw className={`h-3.5 w-3.5 ${busy === "research" ? "animate-spin" : ""}`} />{r.generated_at ? "Regenerate" : "Generate"}</button>}>
          {!r.generated_at ? <div className="text-sm text-slate-500">Not generated yet. The research assistant uses only the cited evidence below and flags anything unverified.</div> : (
            <div className="space-y-4 text-sm">
              <div className="text-xs text-slate-400">Generated by {r.generated_by} · {r.generated_at.slice(0, 16).replace("T", " ")} · Advisory only, not a hiring decision</div>
              <p className="text-slate-700">{r.why_interesting}</p>
              <div className="grid sm:grid-cols-2 gap-4">
                <div><div className="label">Entrepreneurial behaviours</div><List items={r.entrepreneurial_behaviours} /></div>
                <div><div className="label">Evidenced capabilities</div><List items={r.evidenced_capabilities} /></div>
                <div><div className="label">Capability gaps</div><List items={r.capability_gaps} /></div>
                <div><div className="label">Questions to validate</div><List items={r.validation_questions} /></div>
              </div>
              {r.categorisation && <div className="text-xs text-slate-500">Categorisation: {r.categorisation.category} / {r.categorisation.builder_type} — {r.categorisation.basis}</div>}
            </div>
          )}
        </Card>
        <Card title="Capabilities — evidenced vs unknown">
          <div className="grid sm:grid-cols-2 gap-2 text-sm">
            {Object.entries(p.capabilities).map(([k, c]: [string, Any]) => (
              <div key={k} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                <span>{c.label}</span>
                <Badge tone={c.status.includes("verified)") ? "green" : c.status === "Unknown" ? "slate" : "amber"}>{c.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="space-y-5">
        <Card title="Score breakdown" action={<span className="text-lg font-semibold">{sb.total}</span>}>
          <div className="space-y-3">
            {sb.dimensions.map((d: Any) => (
              <div key={d.key} className="text-sm">
                <div className="flex justify-between"><span className="text-slate-700">{d.label} <span className="text-slate-400">({Math.round(d.weight * 100)}%)</span></span><span className="font-medium">{d.score}</span></div>
                <Bar value={d.score} tone={d.missing ? "bg-slate-300" : "bg-brand-500"} />
                <div className={`text-[11px] mt-0.5 ${d.missing ? "text-amber-700" : "text-slate-400"}`}>{d.missing ? "No evidence — needs validation" : d.basis}</div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-3">{sb.disclaimer}</p>
        </Card>
        {(p.missing.length > 0 || r.missing_information?.length > 0) && (
          <Card title="Missing or uncertain" icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}>
            <List items={[...new Set([...(p.missing as string[]), ...((r.missing_information as string[]) || [])])]} />
          </Card>
        )}
        <Card title="Company history">
          {p.history.length === 0 ? <Unknown /> : p.history.map((h: Any, i: number) => (
            <div key={i} className="text-sm py-1"><Link to={`/companies/${h.company_id}`} className="font-medium hover:underline">{h.company}</Link><div className="text-xs text-slate-500">{h.relation} · {h.start_year ?? "?"}–{h.end_year ?? "present"}</div></div>
          ))}
        </Card>
        {p.duplicates.length > 0 && (
          <Card title="Possible duplicates" icon={<AlertTriangle className="h-4 w-4 text-rose-500" />} action={<Link to="/duplicates" className="text-xs text-brand-700">Review</Link>}>
            {p.duplicates.map((d: Any) => <div key={d.id} className="text-sm"><Link to={`/people/${d.id}`} className="hover:underline">{d.full_name}</Link> <span className="text-xs text-slate-500">— {d.reason}</span></div>)}
          </Card>
        )}
        <Card title="Suggested roles">
          {p.role_matches.length ? p.role_matches.map((m: Any) => <div key={m.role_id} className="flex justify-between text-sm py-0.5"><span>{m.role}</span><span className="font-medium">{m.fit}</span></div>) : <Unknown text="No evidenced role fit yet" />}
          <div className="text-[11px] text-slate-400 mt-2">{meta.roles.length} Cognition role profiles configured</div>
        </Card>
      </div>
    </div>
  );
}

function Item({ k, children }: { k: string; children: React.ReactNode }) {
  return <div><dt className="text-[11px] uppercase tracking-wide text-slate-400 font-medium">{k}</dt><dd className="text-slate-700 mt-0.5">{children}</dd></div>;
}

const blankEv = { dimension: "built_from_zero", claim: "", source_url: "", source_name: "", source_type: "manual", published_date: "", strength: "Partial", capabilities: [] as string[] };

function EvidenceTab({ p, meta, can, run, busy }: Ctx) {
  const [f, setF] = useState({ ...blankEv });
  const [open, setOpen] = useState(false);
  const fetchUrl = () => run("fetch", async () => {
    const r: Any = await api.evidenceFromUrl(f.source_url);
    setF((x) => ({ ...x, claim: x.claim || r.suggested_claim || "", source_name: r.site_name || r.title || x.source_name, published_date: r.published_date || x.published_date, source_type: "public_page" }));
  }, "Fetched public metadata (robots.txt respected). Edit the claim before saving.");
  const save = () => run("add", async () => {
    await api.addEvidence(p.id, { ...f, published_date: f.published_date || null, source_url: f.source_url || null });
    setF({ ...blankEv }); setOpen(false);
  }, "Evidence added (unverified until a recruiter checks it)");
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="text-sm text-slate-500">Every important claim must cite a source. Unverified claims count for less in scoring until a recruiter verifies them.</div>
        <div className="flex gap-2">
          {can("research") && <button className="btn-secondary" disabled={busy === "refresh"} onClick={() => run("refresh", () => api.refresh(p.id), "Source links re-checked")}><RefreshCw className="h-4 w-4" />Re-check links</button>}
          {can("research") && <button className="btn-primary" onClick={() => setOpen(!open)}>Add evidence</button>}
        </div>
      </div>
      {open && (
        <div className="card p-4 grid md:grid-cols-2 gap-3 text-sm">
          <div className="md:col-span-2 flex gap-2">
            <input className="input" placeholder="Source URL (public page, GitHub, announcement…)" value={f.source_url} onChange={(e) => setF({ ...f, source_url: e.target.value })} />
            <button className="btn-secondary shrink-0" disabled={!f.source_url || busy === "fetch"} onClick={fetchUrl}><Link2 className="h-4 w-4" />Fetch metadata</button>
          </div>
          <textarea className="input md:col-span-2" rows={2} placeholder="Claim — what does this source show they built or did?" value={f.claim} onChange={(e) => setF({ ...f, claim: e.target.value })} />
          <select className="input" value={f.dimension} onChange={(e) => setF({ ...f, dimension: e.target.value })}>{Object.entries(meta.evidence_dimensions).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select>
          <select className="input" value={f.strength} onChange={(e) => setF({ ...f, strength: e.target.value })}>{["Strong", "Partial", "Weak"].map((x) => <option key={x}>{x}</option>)}</select>
          <input className="input" placeholder="Source name" value={f.source_name} onChange={(e) => setF({ ...f, source_name: e.target.value })} />
          <input className="input" type="date" value={f.published_date} onChange={(e) => setF({ ...f, published_date: e.target.value })} />
          <div className="md:col-span-2 flex flex-wrap gap-1">{Object.entries(meta.capabilities).map(([k, v]) => (
            <button key={k} onClick={() => setF({ ...f, capabilities: f.capabilities.includes(k) ? f.capabilities.filter((x) => x !== k) : [...f.capabilities, k] })}
              className={`chip border ${f.capabilities.includes(k) ? "bg-brand-600 text-white border-brand-600" : "border-slate-200"}`}>{v as string}</button>))}</div>
          {f.dimension === "availability" && <div className="md:col-span-2 text-xs text-amber-700">Availability evidence must be an explicit public statement or consent-based. Do not infer it from startup closure, acquisition or restructuring.</div>}
          <div className="md:col-span-2 flex justify-end gap-2"><button className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary" disabled={!f.claim || busy === "add"} onClick={save}>Save evidence</button></div>
        </div>
      )}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr><th className="p-3">Claim</th><th className="p-3">Dimension</th><th className="p-3">Source</th><th className="p-3">Date</th><th className="p-3">Strength</th><th className="p-3">Verification</th><th className="p-3"></th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {p.evidence.map((e: Any) => (
              <tr key={e.id} className="align-top">
                <td className="p-3 max-w-md"><div className="text-slate-800">{e.claim}</div>{e.capabilities.length > 0 && <div className="flex flex-wrap gap-1 mt-1">{e.capabilities.map((c: string) => <Badge key={c} className="!text-[10px]">{meta.capabilities[c] ?? c}</Badge>)}</div>}</td>
                <td className="p-3 text-xs text-slate-600">{meta.evidence_dimensions[e.dimension]}</td>
                <td className="p-3">{e.source_url ? <SourceLink url={e.source_url} label={e.source_name || undefined} /> : <span className="text-rose-600 text-xs">No source</span>}
                  {e.link_status && <div className={`text-[11px] ${e.link_status === "OK" ? "text-emerald-600" : "text-rose-600"}`}>Link: {e.link_status}</div>}</td>
                <td className="p-3 text-xs text-slate-500 whitespace-nowrap">{e.published_date ?? "Unknown"}</td>
                <td className="p-3"><Badge tone={e.strength === "Strong" ? "green" : e.strength === "Partial" ? "amber" : "slate"}>{e.strength}</Badge></td>
                <td className="p-3"><Badge tone={verTone[e.verification]}>{e.verification}</Badge>{e.verified_by && <div className="text-[11px] text-slate-400">by {e.verified_by}</div>}</td>
                <td className="p-3 whitespace-nowrap">
                  {can("verify") && e.verification !== "Verified" && <button title="Mark verified" className="btn-ghost !p-1" onClick={() => run("v" + e.id, () => api.patchEvidence(e.id, { verification: "Verified" }))}><Check className="h-4 w-4 text-emerald-600" /></button>}
                  {can("verify") && e.verification !== "Disputed" && <button title="Dispute" className="btn-ghost !p-1" onClick={() => run("d" + e.id, () => api.patchEvidence(e.id, { verification: "Disputed" }))}><X className="h-4 w-4 text-rose-600" /></button>}
                  {can("research") && <button title="Delete" className="btn-ghost !p-1" onClick={() => confirm("Delete this evidence?") && run("x" + e.id, () => api.deleteEvidence(e.id))}><Trash2 className="h-4 w-4 text-slate-400" /></button>}
                </td>
              </tr>
            ))}
            {!p.evidence.length && <tr><td colSpan={7} className="p-6 text-center text-slate-500">No evidence yet. Add a sourced claim to start building this profile.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RolesTab({ p, meta, can, run, busy }: Ctx) {
  const [rid, setRid] = useState<number>(p.role_matches[0]?.role_id ?? meta.roles[0]?.id);
  return (
    <div className="space-y-4">
      {can("research") && (
        <div className="card p-4 flex flex-wrap gap-2 items-center">
          <span className="text-sm text-slate-600">Match against</span>
          <select className="input !w-auto" value={rid} onChange={(e) => setRid(+e.target.value)}>{meta.roles.map((r: Any) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
          <button className="btn-primary" disabled={busy === "match"} onClick={() => run("match", () => api.match(p.id, rid), "Role match generated")}><Target className="h-4 w-4" />Run match</button>
          <span className="text-xs text-slate-400">Matches transferable capabilities to the role — never decides suitability.</span>
        </div>
      )}
      {p.matches.length === 0 && <div className="text-sm text-slate-500">No role matches run yet.</div>}
      {p.matches.map((m: Any) => {
        const c = m.content;
        return (
          <Card key={m.id} title={m.role} action={<span className="text-lg font-semibold">{m.relevance}<span className="text-xs text-slate-400"> / 100</span></span>}>
            <p className="text-sm text-slate-700 mb-4">{c.why}</p>
            <div className="grid md:grid-cols-2 gap-5 text-sm">
              <div>
                <div className="label">Supported by evidence</div>
                {c.supported.map((s: Any) => (
                  <div key={s.capability} className="mb-2">
                    <div className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-600" />{s.label}<Badge tone={s.status.includes("verified)") ? "green" : "amber"} className="!text-[10px]">{s.status}</Badge></div>
                    {s.evidence.slice(0, 2).map((e: Any) => <div key={e.id} className="ml-6 text-xs text-slate-500">"{e.claim}" — {e.source_url ? <SourceLink url={e.source_url} /> : "no source"}</div>)}
                  </div>
                ))}
              </div>
              <div>
                <div className="label">Gaps / needs validation</div>
                <List items={(c.needs_validation ?? []).map((g: Any) => `${g.label}: ${g.reason}`)} />
                <div className="label mt-4">Questions to validate in conversation</div>
                <List items={c.questions} />
                <div className="label mt-4">Conversation angles</div>
                <List items={c.angle ? [c.angle] : []} />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function OutreachTab({ p, meta, can, run, busy }: Ctx) {
  const [rid, setRid] = useState<number | undefined>(p.role_matches[0]?.role_id);
  const [edit, setEdit] = useState<Record<number, { subject: string; body: string }>>({});
  const gated = p.research_status === "research_identified";
  return (
    <div className="space-y-4">
      <div className="card p-4 text-sm flex flex-wrap items-center gap-2">
        {gated ? <span className="text-amber-700 flex items-center gap-2"><AlertTriangle className="h-4 w-4" />A recruiter must verify this candidate before outreach drafts can be generated.</span> : <>
          <span className="text-slate-600">Draft outreach for</span>
          <select className="input !w-auto" value={rid ?? ""} onChange={(e) => setRid(e.target.value ? +e.target.value : undefined)}>
            <option value="">Best-matching role</option>{meta.roles.map((r: Any) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
          {can("verify") && <button className="btn-primary" disabled={busy === "gen"} onClick={() => run("gen", () => api.outreach(p.id, rid), "Draft generated — review before use")}><Mail className="h-4 w-4" />Generate draft</button>}
        </>}
        <span className="text-xs text-slate-400 ml-auto">Drafts reference a verified project. Nothing is ever sent automatically.</span>
      </div>
      {p.drafts.map((d: Any) => {
        const e = edit[d.id];
        return (
          <Card key={d.id} title={<span className="flex items-center gap-2">{e ? <input className="input" value={e.subject} onChange={(x) => setEdit({ ...edit, [d.id]: { ...e, subject: x.target.value } })} /> : d.subject}</span>}
            action={<Badge tone={d.status === "Approved" ? "green" : d.status === "Rejected" ? "red" : "amber"}>{d.status}</Badge>}>
            {e ? <textarea className="input font-mono text-xs" rows={12} value={e.body} onChange={(x) => setEdit({ ...edit, [d.id]: { ...e, body: x.target.value } })} />
              : <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans">{d.body}</pre>}
            {p.evidence.filter((x: Any) => d.evidence_ids?.includes(x.id)).map((h: Any) => <div key={h.id} className="text-xs text-slate-500 mt-3">Personalised from verified evidence: "{h.claim}" {h.source_url && <SourceLink url={h.source_url} />}</div>)}
            <div className="text-xs text-slate-400 mt-1">{meta.roles.find((r: Any) => r.id === d.role_id)?.name ?? "Role"} · generated by {d.generated_by} {d.reviewed_by && `· reviewed by ${d.reviewed_by}`}</div>
            {can("verify") && (
              <div className="flex gap-2 mt-4">
                {e ? <><button className="btn-primary" onClick={() => run("e" + d.id, async () => { await api.patchOutreach(d.id, e); setEdit({}); }, "Draft saved")}>Save</button><button className="btn-ghost" onClick={() => setEdit({})}>Cancel</button></> : <>
                  <button className="btn-secondary" onClick={() => setEdit({ ...edit, [d.id]: { subject: d.subject, body: d.body } })}>Edit</button>
                  {d.status !== "Approved" && <button className="btn-primary" onClick={() => run("a" + d.id, () => api.patchOutreach(d.id, { status: "Approved" }), "Approved for manual sending")}><Check className="h-4 w-4" />Approve</button>}
                  {d.status !== "Rejected" && <button className="btn-ghost" onClick={() => run("r" + d.id, () => api.patchOutreach(d.id, { status: "Rejected" }))}>Reject</button>}
                  <CopyButton text={`${d.subject}\n\n${d.body}`} label="Copy" />
                </>}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function ReviewTab({ p, meta, can, run }: Ctx) {
  const [av, setAv] = useState(p.availability);
  const statuses = Object.entries(meta.research_statuses) as [string, string][];
  const done = Object.keys(meta.checklist).filter((k) => p.checklist?.[k]?.ok).length;
  return (
    <div className="grid lg:grid-cols-2 gap-5">
      <Card title="Research workflow">
        <div className="flex items-center gap-2 mb-4">
          {statuses.map(([k, l], i) => (
            <div key={k} className="flex items-center gap-2">
              <div className={`rounded-full px-3 py-1 text-xs font-medium ${p.research_status === k ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"}`}>{i + 1}. {l}</div>
              {i < statuses.length - 1 && <span className="text-slate-300">→</span>}
            </div>
          ))}
        </div>
        {can("verify") ? (
          <div className="flex flex-wrap gap-2">
            {statuses.filter(([k]) => k !== p.research_status).map(([k, l]) => (
              <button key={k} className="btn-secondary" onClick={() => run("s", () => api.setStatus(p.id, k), `Moved to ${l}`)}>Move to {l}</button>
            ))}
          </div>
        ) : <div className="text-sm text-slate-500">Only recruiters can change verification status.</div>}
        <p className="text-xs text-slate-400 mt-3">AI identification alone never makes a candidate ready. "Ready for outreach review" requires recruiter verification, at least one recruiter-verified evidence item and all four checks.</p>
        {can("verify") && (
          <div className="mt-5">
            <div className="label">Owner</div>
            <select className="input" value={p.owner?.id ?? ""} onChange={(e) => run("o", () => api.patchPerson(p.id, { owner_id: e.target.value ? +e.target.value : null }), "Owner updated")}>
              <option value="">Unassigned</option>{meta.users.filter((u: Any) => u.role !== "viewer").map((u: Any) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
        )}
      </Card>
      <Card title={`Human review checklist (${done}/4)`} icon={<ShieldCheck className="h-4 w-4 text-emerald-500" />}>
        <div className="space-y-3">
          {Object.entries(meta.checklist).map(([k, l]) => {
            const c = p.checklist?.[k];
            return (
              <label key={k} className="flex items-start gap-3 text-sm">
                <input type="checkbox" className="mt-1" disabled={!can("verify")} checked={!!c?.ok} onChange={(e) => run("c" + k, () => api.setCheck(p.id, k, e.target.checked))} />
                <span><span className="text-slate-800">{l as string}</span>{c?.ok && <span className="block text-[11px] text-slate-400">✓ {c.by} · {c.at?.slice(0, 10)}</span>}</span>
              </label>
            );
          })}
        </div>
      </Card>
      <Card title="Availability" className="lg:col-span-2">
        <div className="flex flex-wrap gap-2 items-center">
          <select className="input !w-auto" value={av} onChange={(e) => setAv(e.target.value)} disabled={!can("research")}>{meta.availability.map((a: string) => <option key={a}>{a}</option>)}</select>
          {can("research") && <button className="btn-secondary" disabled={av === p.availability} onClick={() => run("av", () => api.patchPerson(p.id, { availability: av }), "Availability updated").catch(() => setAv(p.availability))}>Update</button>}
        </div>
        <p className="text-xs text-slate-500 mt-2">Non-"Unknown" values require a cited availability evidence item; "Confirmed publicly available" needs it recruiter-verified. Never infer availability from startup closure, acquisition, employer, title, geography or restructuring news.</p>
      </Card>
    </div>
  );
}

function NotesTab({ p, can, run }: Ctx) {
  const [note, setNote] = useState("");
  const [c, setC] = useState({ channel: "Email", happened_on: new Date().toISOString().slice(0, 10), summary: "", next_step: "" });
  return (
    <div className="grid lg:grid-cols-2 gap-5">
      <Card title="Recruiter notes">
        {can("research") && <div className="flex gap-2 mb-4"><input className="input" placeholder="Add a note…" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn-primary" disabled={!note} onClick={() => run("n", async () => { await api.addNote(p.id, note); setNote(""); })}>Add</button></div>}
        <div className="space-y-3">{p.notes.map((n: Any) => <div key={n.id} className="text-sm border-l-2 border-brand-200 pl-3"><div>{n.body}</div><div className="text-[11px] text-slate-400">{n.author} · {n.created_at?.slice(0, 16).replace("T", " ")}</div></div>)}
          {!p.notes.length && <div className="text-sm text-slate-500">No notes.</div>}</div>
      </Card>
      <Card title="Conversation history">
        {can("verify") && <div className="grid grid-cols-2 gap-2 mb-4">
          <select className="input" value={c.channel} onChange={(e) => setC({ ...c, channel: e.target.value })}>{["Email", "Call", "Meeting", "Event", "Referral"].map((x) => <option key={x}>{x}</option>)}</select>
          <input className="input" type="date" value={c.happened_on} onChange={(e) => setC({ ...c, happened_on: e.target.value })} />
          <input className="input col-span-2" placeholder="Summary" value={c.summary} onChange={(e) => setC({ ...c, summary: e.target.value })} />
          <input className="input" placeholder="Next step" value={c.next_step} onChange={(e) => setC({ ...c, next_step: e.target.value })} />
          <button className="btn-primary" disabled={!c.summary} onClick={() => run("cv", async () => { await api.addConversation(p.id, c); setC({ ...c, summary: "", next_step: "" }); })}>Log conversation</button>
        </div>}
        <div className="space-y-3">{p.conversations.map((x: Any) => <div key={x.id} className="text-sm"><div className="font-medium">{x.channel} · {x.happened_on}</div><div>{x.summary}</div>{x.next_step && <div className="text-xs text-brand-700">Next: {x.next_step}</div>}<div className="text-[11px] text-slate-400">{x.author}</div></div>)}
          {!p.conversations.length && <div className="text-sm text-slate-500">No conversations logged.</div>}</div>
      </Card>
    </div>
  );
}
