import { Download, FileUp, UserPlus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, download, type Any } from "../api";
import { Card, GithubIcon, PageHeader } from "../components/ui";
import { useApp } from "../ctx";

export default function ImportPage() {
  const { meta, can, toast } = useApp();
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [res, setRes] = useState<Any>(null);
  const [gh, setGh] = useState({ country: "Singapore", keywords: "", limit: 5 });
  const [ghRes, setGhRes] = useState<Any>(null);
  const [busy, setBusy] = useState("");
  const [p, setP] = useState<Any>({ full_name: "", title: "", company_name: "", company_founded_year: "", country: "Singapore", city: "", category: "early_founder", builder_type: "Founder", profile_url: "", website: "", product_built: "", problem_solved: "", venture_status: "Active" });
  if (!can("research")) return <div className="text-slate-500">Your role is read-only. Ask a researcher or recruiter to import candidates.</div>;
  const run = async (k: string, fn: () => Promise<void>) => { setBusy(k); try { await fn(); } catch (e) { toast((e as Error).message); } finally { setBusy(""); } };
  return (
    <div>
      <PageHeader title="Import & discover" subtitle="Add candidates only from approved public or authorised sources. Every record starts as 'Research identified'." />
      <div className="grid lg:grid-cols-2 gap-5">
        <Card title="CSV import" icon={<FileUp className="h-4 w-4" />} action={<button className="btn-ghost !py-1 text-xs" onClick={() => download("/api/import/template.csv", "founder-radar-template.csv")}><Download className="h-3.5 w-3.5" />Template</button>}>
          <p className="text-sm text-slate-500 mb-3">One row per person. Optional evidence columns (claim, source URL, dimension) become unverified evidence. Duplicates are flagged and skipped.</p>
          <div className="flex gap-2"><input type="file" accept=".csv" className="input" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <button className="btn-primary" disabled={!file || busy === "csv"} onClick={() => run("csv", async () => { setRes(await api.importCsv(file!)); })}>Import</button></div>
          {res && <div className="mt-3 text-sm space-y-1">
            <div className="text-emerald-700">{res.created.length} created{res.created.some((c: Any) => c.possible_duplicates?.length) && " — some look like possible duplicates; review on the Duplicates page"}</div>
            {res.skipped.length > 0 && <div className="text-amber-700">{res.skipped.length} skipped: {res.skipped.map((s: Any) => typeof s === "string" ? s : `${s.name ?? s.row} (${s.reason})`).join("; ")}</div>}
            {res.errors.length > 0 && <div className="text-rose-700">{res.errors.length} errors: {res.errors.map((s: Any) => typeof s === "string" ? s : `row ${s.row}: ${s.error}`).join("; ")}</div>}
          </div>}
        </Card>
        <Card title="GitHub public API discovery" icon={<GithubIcon />}>
          <p className="text-sm text-slate-500 mb-3">Finds public developers by location with AI-related public repositories. Uses the official API; no emails or private data are collected.</p>
          <div className="grid grid-cols-3 gap-2">
            <select className="input" value={gh.country} onChange={(e) => setGh({ ...gh, country: e.target.value })}>{meta.countries.map((c: string) => <option key={c}>{c}</option>)}</select>
            <input className="input" placeholder="Keywords (e.g. agents)" value={gh.keywords} onChange={(e) => setGh({ ...gh, keywords: e.target.value })} />
            <input className="input" type="number" min={1} max={20} value={gh.limit} onChange={(e) => setGh({ ...gh, limit: +e.target.value })} />
          </div>
          <button className="btn-primary mt-3" disabled={busy === "gh"} onClick={() => run("gh", async () => { setGhRes(await api.runGithub(gh)); })}>{busy === "gh" ? "Searching…" : "Run discovery"}</button>
          {ghRes && <div className="mt-3 text-sm">
            <div className="text-slate-600">Examined {ghRes.examined} · created {ghRes.created.length} · already known {ghRes.skipped_existing}</div>
            {ghRes.created.map((c: Any) => <button key={c.id} onClick={() => nav(`/people/${c.id}`)} className="block text-brand-700 hover:underline">{c.name} — {c.repo}</button>)}
          </div>}
        </Card>
        <Card title="Manual entry" icon={<UserPlus className="h-4 w-4" />} className="lg:col-span-2">
          <div className="grid md:grid-cols-3 gap-3 text-sm">
            {[["full_name", "Full name *"], ["title", "Current title"], ["company_name", "Company / venture"], ["company_founded_year", "Founded year"], ["city", "City"], ["profile_url", "Public profile URL"], ["website", "Product / company website"], ["product_built", "What they built"], ["problem_solved", "Problem solved"]].map(([k, l]) => (
              <input key={k} className="input" placeholder={l} value={p[k]} onChange={(e) => setP({ ...p, [k]: e.target.value })} />
            ))}
            <select className="input" value={p.country} onChange={(e) => setP({ ...p, country: e.target.value })}>{[...meta.countries, ...meta.extra_countries].map((c: string) => <option key={c}>{c}</option>)}</select>
            <select className="input" value={p.category} onChange={(e) => setP({ ...p, category: e.target.value })}>{Object.entries(meta.categories).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select>
            <select className="input" value={p.builder_type} onChange={(e) => setP({ ...p, builder_type: e.target.value })}>{meta.builder_types.map((c: string) => <option key={c}>{c}</option>)}</select>
            <select className="input" value={p.venture_status} onChange={(e) => setP({ ...p, venture_status: e.target.value })}>{meta.venture_statuses.map((c: string) => <option key={c}>{c}</option>)}</select>
          </div>
          <div className="flex justify-between items-center mt-4">
            <span className="text-xs text-slate-400">Availability starts as "Unknown". Add sourced evidence on the profile next.</span>
            <button className="btn-primary" disabled={!p.full_name || busy === "p"} onClick={() => run("p", async () => {
              const r: Any = await api.createPerson({ ...p, company_founded_year: p.company_founded_year ? +p.company_founded_year : null, founding_year: p.company_founded_year ? +p.company_founded_year : null });
              toast("Candidate created", "ok"); nav(`/people/${r.id}`);
            })}>Create candidate</button>
          </div>
        </Card>
      </div>
    </div>
  );
}
