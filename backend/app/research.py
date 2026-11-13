"""AI research & summarisation layer. Rules-based by default; uses an LLM when configured, constrained to cited evidence."""
import json

from . import llm
from .models import Evidence, Person, RoleProfile
from .scoring import capability_status, role_fit, score
from .taxonomy import CAPABILITIES, CATEGORIES

GUARDRAIL = ("You are a research assistant for recruiters. Use ONLY the evidence provided. Never invent facts, employers, dates, "
             "metrics or availability. If something is not evidenced, say it needs validation. Do not judge suitability, personality, "
             "age or any protected characteristic. Do not decide whether someone should be hired.")

QUESTIONS = {
    "ai_ml": "Walk me through the hardest AI/LLM problem you solved in {product}. How did you evaluate quality?",
    "software_engineering": "Which parts of {product} did you personally build, and what would you re-architect today?",
    "product_development": "How did you decide what to build first for {product}, and what did you cut?",
    "developer_tools": "What did you learn about developer adoption while building {product}?",
    "enterprise_tech": "Tell me about deploying into a large organisation — what blocked you and how did you get through it?",
    "customer_engagement": "Describe a customer you won over after a rough start. What changed?",
    "commercialisation": "How did you find and close your first paying customers?",
    "partnerships": "Which partnership moved the needle most, and how did you structure it?",
    "fundraising_bd": "What did fundraising or business development teach you about telling a technical story?",
}

CATEGORY_ANGLE = {
    "early_founder": "Talk founder-to-builder: Cognition is building the future of software engineering and wants people who have shipped from zero. No assumption they are looking to leave.",
    "former_founder": "Acknowledge the journey with {company}; explore what they want to build next and whether shaping AI software engineering at Cognition resonates.",
    "intrapreneur": "Lead with the venture they built inside {company}; Cognition offers the same zero-to-one energy at the frontier of AI engineering.",
    "independent_builder": "Engage on the work itself ({product}); invite a technical conversation about agents and developer tooling rather than a job pitch.",
}


def _ev_view(e: Evidence) -> dict:
    return {"id": e.id, "claim": e.claim, "source_url": e.source_url, "verification": e.verification, "strength": e.strength,
            "published_date": e.published_date.isoformat() if e.published_date else None, "dimension": e.dimension}


def _product(p: Person) -> str:
    return (p.product_built or (p.company.name if p.company else "your project")).rstrip(".")


def rules_research(p: Person, roles: list[RoleProfile]) -> dict:
    sc = score(p, roles)
    caps = capability_status(p)
    evidenced = [CAPABILITIES[c] for c, v in caps.items() if v["status"] != "Unknown"]
    built = [e for e in p.evidence if e.dimension == "built_from_zero" and e.verification != "Disputed"]
    behaviours = []
    dims = {d["key"]: d for d in sc["dimensions"]}
    if dims["built_from_zero"]["score"]:
        behaviours.append("Built something from zero")
    if dims["commercial"]["score"]:
        behaviours.append("Found customers / commercial traction")
    if dims["entrepreneurial"]["score"]:
        behaviours.append("Operated as a founder or venture lead (team, funding or partnerships)")
    if dims["product_execution"]["score"]:
        behaviours.append("Owned product execution from prototype to launch")
    why = []
    if built:
        why.append(built[0].claim)
    ai = [e for e in p.evidence if e.dimension == "ai_technical" and e.verification != "Disputed"]
    if ai:
        why.append(ai[0].claim)
    if not why:
        why.append("Limited public evidence so far — included for research only.")
    best = sorted(((role_fit(p, r)[0], r.name) for r in roles), reverse=True)[:2]
    gaps = [f"{CAPABILITIES[c]}: no public evidence" for c, v in caps.items() if v["status"] == "Unknown"][:5]
    gaps += [f"{d['label']}: needs validation" for d in sc["dimensions"] if d["missing"] and d["key"] != "role_relevance"]
    unknown_caps = [c for c, v in caps.items() if v["status"] == "Unknown"]
    qs = [QUESTIONS[c].format(product=_product(p)) for c in ([c for c, v in caps.items() if v["status"] == "Evidenced (unverified)"][:2] + unknown_caps[:2])]
    if p.availability == "Unknown":
        qs.append("(Recruiter) Availability is unknown — confirm interest respectfully; do not assume they are looking.")
    cat_reason = {"Founder": "Founder", "Co-founder": "Co-founder"}.get(p.builder_type, p.builder_type)
    return {
        "generated_by": "rules",
        "why_interesting": " ".join(why),
        "entrepreneurial_behaviours": behaviours,
        "evidenced_capabilities": evidenced,
        "capability_gaps": gaps,
        "validation_questions": qs,
        "categorisation": {"category": CATEGORIES.get(p.category, p.category), "builder_type": p.builder_type,
                           "basis": f"{cat_reason} per {len(built)} built-from-zero evidence item(s)" if built else "Category from source record; no built-from-zero evidence yet"},
        "suggested_roles": [{"role": n, "fit": f} for f, n in best if f],
        "missing_information": sc["missing"] + (["Availability"] if p.availability == "Unknown" else []),
    }


async def research(p: Person, roles: list[RoleProfile]) -> dict:
    base = rules_research(p, roles)
    if not llm.provider() or not p.evidence:
        return base
    try:
        out = await llm.complete_json(GUARDRAIL, json.dumps({
            "task": "Summarise why this person may be interesting to Cognition (AI software engineering company). Return JSON with keys "
                    "why_interesting (<=3 sentences citing evidence ids like [E12]), entrepreneurial_behaviours (list), capability_gaps (list), "
                    "validation_questions (list of 4-6).",
            "person": {"name": p.full_name, "title": p.title, "company": p.company.name if p.company else None, "category": p.category},
            "evidence": [_ev_view(e) for e in p.evidence]}))
        for k in ("why_interesting", "entrepreneurial_behaviours", "capability_gaps", "validation_questions"):
            if out.get(k):
                base[k] = out[k]
        base["generated_by"] = f"llm:{llm.provider()}"
    except Exception as exc:  # noqa: BLE001 - fall back to rules
        base["llm_error"] = str(exc)[:200]
    return base


def rules_match(p: Person, role: RoleProfile) -> dict:
    fit, supported, gaps = role_fit(p, role)
    caps = capability_status(p)
    ev = {e.id: e for e in p.evidence}
    sup = [{"capability": c, "label": CAPABILITIES[c], "status": caps[c]["status"],
            "evidence": [_ev_view(ev[i]) for i in caps[c]["evidence_ids"]][:3]} for c in supported]
    need = [{"capability": c, "label": CAPABILITIES[c],
             "reason": "Evidence exists but is unverified" if caps[c]["status"] == "Evidenced (unverified)" else "No public evidence found"} for c in gaps]
    built = next((e.claim for e in p.evidence if e.dimension == "built_from_zero" and e.verification != "Disputed"), None)
    why = (f"{role.name} needs {', '.join(CAPABILITIES[c].lower() for c in role.capabilities)}. "
           f"Evidence supports {len(supported)} of {len(role.capabilities)}" + (f" — notably: {built}" if built else ".") )
    qs = list(dict.fromkeys([QUESTIONS[c].format(product=_product(p)) for c in gaps[:3]] + [QUESTIONS[c].format(product=_product(p)) for c in supported[:2]]))
    angle = (role.angle or "") + " " + CATEGORY_ANGLE.get(p.category, "").format(company=p.company.name if p.company else "their venture", product=_product(p))
    return {"relevance": fit, "why": why, "supported": sup, "needs_validation": need, "questions": qs, "angle": angle.strip(),
            "note": "Decision support only — the recruiter decides whether to engage."}


async def match(p: Person, role: RoleProfile) -> tuple[dict, str]:
    base = rules_match(p, role)
    if not llm.provider():
        return base, "rules"
    try:
        out = await llm.complete_json(GUARDRAIL, json.dumps({
            "task": f"Explain why this person may be relevant to the Cognition role '{role.name}' ({role.description}). Return JSON with keys "
                    "why (<=3 sentences, cite evidence ids [E#]), questions (5 interview questions), angle (1-2 sentence conversation angle).",
            "supported": base["supported"], "needs_validation": base["needs_validation"],
            "person": {"title": p.title, "company": p.company.name if p.company else None, "category": p.category}}))
        base.update({k: out[k] for k in ("why", "questions", "angle") if out.get(k)})
        return base, f"llm:{llm.provider()}"
    except Exception:  # noqa: BLE001
        return base, "rules"


def pick_hook(p: Person) -> Evidence | None:
    order = ["built_from_zero", "product_execution", "ai_technical", "commercial", "entrepreneurial"]
    verified = [e for e in p.evidence if e.verification == "Verified" and e.dimension in order]
    return sorted(verified, key=lambda e: order.index(e.dimension))[0] if verified else None


def rules_outreach(p: Person, role: RoleProfile | None, hook: Evidence, sender: str) -> dict:
    first = p.full_name.split()[0]
    what = hook.claim.rstrip(".")
    role_line = (f" We're building out our {role.name} team in APAC, and the way you approached it maps closely to the work." if role else "")
    body = (f"Hi {first},\n\n"
            f"I came across your work — {what[0].lower() + what[1:]}. It's a genuinely hard thing to build from scratch, and it stood out.\n\n"
            f"I'm on the team at Cognition, where we build Devin, an autonomous AI software engineer. We're a small group of builders working on how software gets made, "
            f"and many of us have founded or built products from zero ourselves.{role_line}\n\n"
            f"I'm not assuming you're looking for anything — I'd simply value a conversation about what you've learned building "
            f"{_product(p)} and where you think AI-assisted engineering is going. If it's interesting, happy to share more about what we're building.\n\n"
            f"Best,\n{sender}")
    return {"subject": f"Your work on {_product(p)[:60]}", "body": body}


async def outreach(p: Person, role: RoleProfile | None, hook: Evidence, sender: str) -> tuple[dict, str]:
    base = rules_outreach(p, role, hook, sender)
    if not llm.provider():
        return base, "rules"
    try:
        out = await llm.complete_json(GUARDRAIL + " Write warm, specific, non-generic outreach. Do not assume they are job-seeking.", json.dumps({
            "task": "Write a short outreach email (<=150 words) from the sender at Cognition (makers of Devin, an AI software engineer). "
                    "Reference ONLY the verified achievement below. Focus on the opportunity to build and shape the future of AI software engineering. "
                    "Return JSON {subject, body}.",
            "first_name": p.full_name.split()[0], "verified_achievement": hook.claim, "role": role.name if role else None, "sender": sender}))
        if out.get("body"):
            return {"subject": out.get("subject") or base["subject"], "body": out["body"]}, f"llm:{llm.provider()}"
    except Exception:  # noqa: BLE001
        pass
    return base, "rules"
