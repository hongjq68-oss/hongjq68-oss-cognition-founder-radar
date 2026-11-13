import { Bookmark, BookmarkCheck, ExternalLink, MapPin, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import type { Any } from "../api";
import { availTone, Avatar, Badge, confTone, ScoreRing, SourceLink, statusTone, Synthetic } from "./ui";

export default function CandidateCard({ p, caps, onSave, extra }: { p: Any; caps: Record<string, string>; onSave?: (p: Any) => void; extra?: React.ReactNode }) {
  const top = p.role_matches?.[0];
  return (
    <div className="card p-5 hover:shadow-md transition">
      <div className="flex gap-4">
        <Avatar name={p.full_name} size={44} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/people/${p.id}`} className="font-semibold text-slate-900 hover:text-brand-700">{p.full_name}</Link>
            <Synthetic show={p.is_synthetic} />
            <Badge tone={statusTone[p.research_status]}>{p.research_status_label}</Badge>
            <Badge tone="violet">{p.category_label}</Badge>
          </div>
          <div className="text-sm text-slate-600 mt-0.5">
            {p.title || "Unknown title"}{p.company && <> · <Link className="hover:underline" to={`/companies/${p.company.id}`}>{p.company.name}</Link>{p.founding_year && ` (founded ${p.founding_year})`}</>}
          </div>
          <div className="text-xs text-slate-500 mt-0.5 flex items-center gap-1"><MapPin className="h-3 w-3" />{[p.city, p.country].filter(Boolean).join(", ") || "Unknown"} · {p.builder_type} · {p.venture_status}</div>
        </div>
        <div className="flex flex-col items-center gap-1">
          <ScoreRing score={p.score} />
          <Badge tone={confTone[p.confidence]} className="!text-[10px]">{p.confidence} confidence</Badge>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-x-6 gap-y-3 mt-4 text-sm">
        <Field label="What they built">{p.product_built || <Unknown />}</Field>
        <Field label={<span className="flex items-center gap-1"><Sparkles className="h-3 w-3" />AI evidence · {p.ai_relevance}</span>}>{p.ai_evidence || <Unknown />}</Field>
        <Field label="Why shortlisted">{p.why}</Field>
        <Field label="Potential Cognition role">{top ? <>{top.role} <span className="text-slate-400">· fit {top.fit}</span></> : <Unknown text="No role match yet" />}</Field>
        <Field label="Availability (separate from capability)">
          <Badge tone={availTone[p.availability]}>{p.availability}</Badge>
          {p.availability_note && <div className="text-xs text-slate-500 mt-1">{p.availability_note}</div>}
        </Field>
        <Field label="Technical capability">
          <div className="flex flex-wrap gap-1">{p.technical_capabilities.length ? p.technical_capabilities.map((c: string) => <Badge key={c}>{caps[c] ?? c}</Badge>) : <Unknown />}</div>
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
        <span>{p.evidence_count} evidence · {p.verified_count} verified</span>
        <span>Last verified: {p.last_verified_at ? p.last_verified_at.slice(0, 10) : "Never"}</span>
        {p.sources.slice(0, 2).map((s: string) => <SourceLink key={s} url={s} />)}
        {p.missing.length > 0 && <span className="text-amber-700">Needs validation: {p.missing.join(", ")}</span>}
        <span className="ml-auto flex items-center gap-2">
          {extra}
          <span className="font-medium text-brand-700">→ {p.recommended_action}</span>
          {onSave && (
            <button className="btn-ghost !px-2 !py-1" title={p.saved ? "Saved to pipeline" : "Save to pipeline"} onClick={() => onSave(p)}>
              {p.saved ? <BookmarkCheck className="h-4 w-4 text-brand-600" /> : <Bookmark className="h-4 w-4" />}
            </button>
          )}
          <Link to={`/people/${p.id}`} className="btn-ghost !px-2 !py-1"><ExternalLink className="h-4 w-4" /></Link>
        </span>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return <div><div className="text-[11px] uppercase tracking-wide text-slate-400 font-medium mb-0.5">{label}</div><div className="text-slate-700">{children}</div></div>;
}
export function Unknown({ text = "Unknown" }: { text?: string }) {
  return <span className="text-slate-400 italic">{text}</span>;
}
