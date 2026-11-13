from .models import Company, Evidence, Person, RoleProfile
from .research import rules_research
from .scoring import ai_relevance, capability_status, role_fit, score, technical_capabilities
from .taxonomy import CATEGORIES, RESEARCH_STATUSES


def iso(d):
    return d.isoformat() if d else None


def evidence(e: Evidence) -> dict:
    return {"id": e.id, "person_id": e.person_id, "dimension": e.dimension, "claim": e.claim, "capabilities": e.capabilities or [],
            "source_url": e.source_url, "source_name": e.source_name, "source_type": e.source_type, "published_date": iso(e.published_date),
            "strength": e.strength, "verification": e.verification, "verified_by": e.verified_by, "link_status": e.link_status,
            "last_checked_at": iso(e.last_checked_at), "created_by": e.created_by, "created_at": iso(e.created_at)}


def company_brief(c: Company | None) -> dict | None:
    if not c:
        return None
    return {"id": c.id, "name": c.name, "website": c.website, "founded_year": c.founded_year, "sector": c.sector,
            "venture_status": c.venture_status, "is_synthetic": c.is_synthetic}


def recommended_action(p: Person, sc: dict) -> str:
    if p.research_status == "research_identified":
        if sc["evidence_count"] == 0:
            return "Find at least one public source before reviewing"
        return "Recruiter: verify identity and evidence"
    if p.research_status == "recruiter_verified":
        missing = [k for k, v in (p.checklist or {}).items() if not v.get("ok")]
        if not sc["verified_count"]:
            return "Verify at least one evidence item"
        return "Complete outreach checklist" if missing or len(p.checklist or {}) < 4 else "Move to Ready for outreach review"
    return "Review outreach draft" if not p.outreach_reviewed else "Approved — recruiter may reach out manually"


def person_summary(p: Person, roles: list[RoleProfile]) -> dict:
    sc = score(p, roles)
    fits = sorted(((role_fit(p, r)[0], r) for r in roles), key=lambda x: -x[0])
    rr = p.research or {}
    why = rr.get("why_interesting") or rules_research(p, roles)["why_interesting"]
    ai_ev = next((e.claim for e in p.evidence if e.dimension == "ai_technical" and e.verification != "Disputed"), None)
    av_ev = next((e for e in p.evidence if e.dimension == "availability" and e.verification != "Disputed"), None)
    return {
        "id": p.id, "full_name": p.full_name, "title": p.title, "company": company_brief(p.company), "country": p.country, "city": p.city,
        "category": p.category, "category_label": CATEGORIES.get(p.category, p.category), "builder_type": p.builder_type,
        "founding_year": p.founding_year, "venture_status": p.venture_status, "product_built": p.product_built,
        "ai_evidence": ai_ev, "ai_relevance": ai_relevance(p), "technical_capabilities": technical_capabilities(p),
        "why": why, "role_matches": [{"role_id": r.id, "role": r.name, "fit": f} for f, r in fits[:3] if f],
        "availability": p.availability, "availability_note": p.availability_note,
        "availability_source": av_ev.source_url if av_ev else None,
        "sources": sorted({e.source_url for e in p.evidence if e.source_url})[:6],
        "score": sc["total"], "confidence": sc["confidence"], "evidence_count": sc["evidence_count"], "verified_count": sc["verified_count"],
        "missing": sc["missing"], "research_status": p.research_status, "research_status_label": RESEARCH_STATUSES.get(p.research_status),
        "recommended_action": recommended_action(p, sc), "last_verified_at": iso(p.last_verified_at),
        "owner": {"id": p.owner.id, "name": p.owner.name} if p.owner else None, "saved": p.saved, "outreach_reviewed": p.outreach_reviewed,
        "is_synthetic": p.is_synthetic, "source": p.source, "profile_url": p.profile_url, "website": p.website,
        "created_at": iso(p.created_at), "updated_at": iso(p.updated_at),
    }


def person_detail(p: Person, roles: list[RoleProfile]) -> dict:
    d = person_summary(p, roles)
    d.update({
        "problem_solved": p.problem_solved, "team_built": p.team_built, "previous_ventures": p.previous_ventures or [],
        "transition_evidence": p.transition_evidence, "checklist": p.checklist or {}, "research": p.research or {},
        "score_breakdown": score(p, roles), "capabilities": capability_status(p), "evidence": [evidence(e) for e in p.evidence],
    })
    return d
