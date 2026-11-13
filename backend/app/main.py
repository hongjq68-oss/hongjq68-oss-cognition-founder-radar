import csv
import io
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from . import dedupe, llm, research
from .audit import log
from .auth import PERMISSIONS, current_user, issue_token, require
from .db import Base, SessionLocal, engine, get_db
from .models import (AuditLog, Company, Conversation, Evidence, Note, OutreachDraft, Person, PersonCompany, ResearchTask, RoleMatch,
                     RoleProfile, Shortlist, SourceState, User, WatchCompany, WatchEvent)
from .scoring import DISCLAIMER, ai_relevance, capability_status, role_fit, score
from .seed import seed
from .serializers import evidence as ev_json, iso, person_detail, person_summary
from .sources import BY_KEY, SOURCES, github, url_evidence
from .taxonomy import (AVAILABILITY, AVAILABILITY_REQUIRES_EVIDENCE, BUILDER_TYPES, CAPABILITIES, CATEGORIES, CHECKLIST, DIMENSIONS,
                       EVIDENCE_DIMENSIONS, PRIORITY_COUNTRIES, RESEARCH_STATUSES, SECTORS, VENTURE_STATUSES)

app = FastAPI(title="Cognition Founder Radar")
Base.metadata.create_all(engine)
with SessionLocal() as _db:
    seed(_db)

Read = Depends(require("read"))
Researcher = Depends(require("research"))
Recruiter = Depends(require("verify"))
Admin = Depends(require("admin"))


def roles_all(db: Session) -> list[RoleProfile]:
    return db.query(RoleProfile).order_by(RoleProfile.id).all()


def people_q(db: Session):
    return db.query(Person).options(selectinload(Person.evidence), selectinload(Person.company), selectinload(Person.owner))


def get_person(db: Session, pid: int) -> Person:
    p = people_q(db).filter(Person.id == pid).first()
    if not p:
        raise HTTPException(404, "Person not found")
    return p


# ---------- auth & meta ----------
class LoginIn(BaseModel):
    email: str


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if not u or not u.active:
        raise HTTPException(401, "Unknown user")
    log(db, u, "auth.login", "user", u.id)
    db.commit()
    return {"token": issue_token(u), "user": {"id": u.id, "name": u.name, "email": u.email, "role": u.role}}


@app.get("/api/auth/demo-users")
def demo_users(db: Session = Depends(get_db)):
    return [{"name": u.name, "email": u.email, "role": u.role} for u in db.query(User).filter_by(active=True)]


@app.get("/api/me")
def me(u: User = Depends(current_user)):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "permissions": sorted(k for k, v in PERMISSIONS.items() if u.role in v)}


@app.get("/api/meta")
def meta(db: Session = Depends(get_db), u: User = Read):
    return {"countries": PRIORITY_COUNTRIES, "categories": CATEGORIES, "builder_types": BUILDER_TYPES, "venture_statuses": VENTURE_STATUSES,
            "availability": AVAILABILITY, "research_statuses": RESEARCH_STATUSES, "checklist": CHECKLIST, "capabilities": CAPABILITIES,
            "dimensions": {k: {"label": v[0], "weight": v[1]} for k, v in DIMENSIONS.items()}, "evidence_dimensions": EVIDENCE_DIMENSIONS,
            "sectors": SECTORS, "roles": [{"id": r.id, "name": r.name} for r in roles_all(db)],
            "users": [{"id": x.id, "name": x.name, "role": x.role} for x in db.query(User).filter_by(active=True)],
            "llm": llm.provider(), "disclaimer": DISCLAIMER,
            "extra_countries": sorted({c for (c,) in db.query(Person.country).distinct() if c and c not in PRIORITY_COUNTRIES})}


# ---------- dashboard ----------
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), u: User = Read):
    people = people_q(db).all()
    roles = roles_all(db)
    st = Counter(p.research_status for p in people)
    needs = [p for p in people if p.research_status == "research_identified"]
    needs.sort(key=lambda p: -score(p, roles)["total"])
    return {
        "kpis": {
            "total": len(people),
            "founders": sum(p.category == "early_founder" for p in people),
            "former_founders": sum(p.category == "former_founder" for p in people),
            "independent_builders": sum(p.category == "independent_builder" for p in people),
            "intrapreneurs": sum(p.category == "intrapreneur" for p in people),
            "ai_entrepreneurs": sum(p.category in ("early_founder", "former_founder") and ai_relevance(p) in ("High", "Medium") for p in people),
            "verified": st["recruiter_verified"] + st["ready_for_outreach_review"],
            "ready": st["ready_for_outreach_review"],
            "needs_verification": st["research_identified"],
            "synthetic": sum(p.is_synthetic for p in people),
        },
        "by_country": Counter(p.country or "Unknown" for p in people).most_common(),
        "by_category": [(CATEGORIES.get(k, k), v) for k, v in Counter(p.category for p in people).most_common()],
        "by_status": [(RESEARCH_STATUSES[k], st[k]) for k in RESEARCH_STATUSES],
        "by_availability": Counter(p.availability for p in people).most_common(),
        "by_source": Counter(p.source for p in people).most_common(),
        "needs_verification": [person_summary(p, roles) for p in needs[:6]],
        "recent_events": [{"id": e.id, "company_name": e.company_name, "event_type": e.event_type, "event_date": iso(e.event_date),
                           "is_synthetic": e.is_synthetic} for e in db.query(WatchEvent).order_by(WatchEvent.event_date.desc()).limit(5)],
        "open_tasks": db.query(ResearchTask).filter(ResearchTask.status != "Done").count(),
        "drafts_pending": db.query(OutreachDraft).filter_by(status="Draft").count(),
    }


# ---------- people ----------
def filter_people(people: list[Person], roles: list[RoleProfile], q=None, country=None, category=None, founded_from=None, founded_to=None,
                  ai=None, capability=None, venture_status=None, role_id=None, min_fit=0, availability=None, status=None,
                  saved=None, owner_id=None, min_score=0) -> list[Person]:
    role = next((r for r in roles if r.id == role_id), None)
    out = []
    for p in people:
        if q and q.lower() not in " ".join(filter(None, [p.full_name, p.title, p.product_built, p.company.name if p.company else "",
                                                          " ".join(e.claim for e in p.evidence)])).lower():
            continue
        if country and p.country not in country:
            continue
        if category and p.category not in category:
            continue
        if founded_from and not (p.founding_year and p.founding_year >= founded_from):
            continue
        if founded_to and not (p.founding_year and p.founding_year <= founded_to):
            continue
        if ai and ai_relevance(p) not in ai:
            continue
        if capability and not all(capability_status(p)[c]["status"] != "Unknown" for c in capability):
            continue
        if venture_status and p.venture_status not in venture_status:
            continue
        if role and role_fit(p, role)[0] < max(min_fit, 1):
            continue
        if availability and p.availability not in availability:
            continue
        if status and p.research_status not in status:
            continue
        if saved is not None and p.saved != saved:
            continue
        if owner_id and p.owner_id != owner_id:
            continue
        if min_score and score(p, roles)["total"] < min_score:
            continue
        out.append(p)
    return out


@app.get("/api/people")
def list_people(q: str | None = None, country: list[str] = Query(None), category: list[str] = Query(None), founded_from: int | None = None,
                founded_to: int | None = None, ai: list[str] = Query(None), capability: list[str] = Query(None),
                venture_status: list[str] = Query(None), role_id: int | None = None, min_fit: int = 0, availability: list[str] = Query(None),
                status: list[str] = Query(None), saved: bool | None = None, owner_id: int | None = None, min_score: int = 0,
                sort: str = "score", db: Session = Depends(get_db), u: User = Read):
    roles = roles_all(db)
    ps = filter_people(people_q(db).all(), roles, q, country, category, founded_from, founded_to, ai, capability, venture_status, role_id,
                       min_fit, availability, status, saved, owner_id, min_score)
    out = [person_summary(p, roles) for p in ps]
    key = {"score": lambda x: -x["score"], "recent": lambda x: x["updated_at"] or "", "name": lambda x: x["full_name"]}.get(sort)
    out.sort(key=key, reverse=sort == "recent")
    return out


class PersonIn(BaseModel):
    full_name: str
    title: str | None = None
    company_name: str | None = None
    company_founded_year: int | None = None
    company_website: str | None = None
    country: str | None = None
    city: str | None = None
    category: str = "early_founder"
    builder_type: str = "Unknown"
    founding_year: int | None = None
    profile_url: str | None = None
    website: str | None = None
    product_built: str | None = None
    problem_solved: str | None = None
    venture_status: str = "Unknown"
    is_synthetic: bool = False


def upsert_company(db: Session, name: str | None, **kw) -> Company | None:
    if not name:
        return None
    c = db.query(Company).filter(Company.name.ilike(name.strip())).first()
    if not c:
        c = Company(name=name.strip(), **{k: v for k, v in kw.items() if v is not None})
        db.add(c)
        db.flush()
    return c


@app.post("/api/people")
def create_person(body: PersonIn, db: Session = Depends(get_db), u: User = Researcher):
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    co = upsert_company(db, body.company_name, founded_year=body.company_founded_year, website=body.company_website, country=body.country,
                        is_synthetic=body.is_synthetic, source="manual")
    data = body.model_dump(exclude={"company_name", "company_founded_year", "company_website"})
    p = Person(**data, company=co, source="manual")
    db.add(p)
    db.flush()
    if co:
        db.add(PersonCompany(person_id=p.id, company_id=co.id, relation=body.builder_type, start_year=body.founding_year))
    dups = dedupe.find_for(p, people_q(db).all())
    log(db, u, "person.create", "person", p.id, name=p.full_name, possible_duplicates=[d.id for d, _ in dups])
    db.commit()
    return {"id": p.id, "possible_duplicates": [{"id": d.id, "name": d.full_name, "reason": r} for d, r in dups]}


@app.get("/api/people/{pid}")
def person(pid: int, db: Session = Depends(get_db), u: User = Read):
    p = get_person(db, pid)
    roles = roles_all(db)
    d = person_detail(p, roles)
    d["matches"] = [{"id": m.id, "role_id": m.role_id, "role": m.role.name, "relevance": m.relevance, "content": m.content,
                     "generated_by": m.generated_by, "created_by": m.created_by, "created_at": iso(m.created_at)}
                    for m in db.query(RoleMatch).filter_by(person_id=pid).order_by(RoleMatch.id.desc())]
    d["drafts"] = [{"id": o.id, "role_id": o.role_id, "subject": o.subject, "body": o.body, "status": o.status, "evidence_ids": o.evidence_ids,
                    "generated_by": o.generated_by, "created_by": o.created_by, "reviewed_by": o.reviewed_by, "reviewed_at": iso(o.reviewed_at),
                    "created_at": iso(o.created_at)} for o in db.query(OutreachDraft).filter_by(person_id=pid).order_by(OutreachDraft.id.desc())]
    d["notes"] = [{"id": n.id, "author": n.author, "body": n.body, "created_at": iso(n.created_at)}
                  for n in db.query(Note).filter_by(person_id=pid).order_by(Note.id.desc())]
    d["conversations"] = [{"id": c.id, "author": c.author, "channel": c.channel, "happened_on": iso(c.happened_on), "summary": c.summary,
                           "next_step": c.next_step} for c in db.query(Conversation).filter_by(person_id=pid).order_by(Conversation.happened_on.desc())]
    d["activity"] = [{"ts": iso(a.ts), "user": a.user_name, "action": a.action, "detail": a.detail}
                     for a in db.query(AuditLog).filter_by(entity="person", entity_id=pid).order_by(AuditLog.id.desc()).limit(50)]
    d["duplicates"] = [{"id": x.id, "name": x.full_name, "reason": r} for x, r in dedupe.find_for(p, people_q(db).all())]
    d["history"] = [{"company": db.get(Company, pc.company_id).name, "company_id": pc.company_id, "relation": pc.relation,
                     "start_year": pc.start_year, "end_year": pc.end_year} for pc in db.query(PersonCompany).filter_by(person_id=pid)]
    return d


EDITABLE = {"full_name", "title", "country", "city", "category", "builder_type", "founding_year", "profile_url", "website", "product_built",
            "problem_solved", "team_built", "venture_status", "previous_ventures", "transition_evidence", "saved"}


@app.patch("/api/people/{pid}")
def patch_person(pid: int, body: dict, db: Session = Depends(get_db), u: User = Researcher):
    p = get_person(db, pid)
    changes = {}
    for k, v in body.items():
        if k in EDITABLE:
            changes[k] = v
            setattr(p, k, v)
        elif k == "owner_id":
            if u.role not in PERMISSIONS["verify"]:
                raise HTTPException(403, "Only recruiters can assign ownership")
            p.owner_id = v
            changes[k] = v
        elif k in ("availability", "availability_note"):
            continue
        else:
            raise HTTPException(400, f"Field {k} cannot be edited")
    if "availability" in body:
        av = body["availability"]
        if av not in AVAILABILITY:
            raise HTTPException(400, "Unknown availability value")
        rows = [e for e in p.evidence if e.dimension == "availability" and e.source_url and e.verification != "Disputed"]
        if av in AVAILABILITY_REQUIRES_EVIDENCE and not rows:
            raise HTTPException(400, f"'{av}' needs a cited availability evidence item first. Use 'Unknown' when there is no explicit public evidence.")
        if av == "Confirmed publicly available" and not any(e.verification == "Verified" for e in rows):
            raise HTTPException(400, "'Confirmed publicly available' requires a recruiter-verified availability evidence item (explicit public or consent-based).")
        p.availability = av
        p.availability_note = body.get("availability_note") or (rows[0].claim if rows else None)
        changes["availability"] = av
    log(db, u, "person.update", "person", pid, **changes)
    db.commit()
    return {"ok": True}


@app.delete("/api/people/{pid}")
def delete_person(pid: int, db: Session = Depends(get_db), u: User = Recruiter):
    p = get_person(db, pid)
    log(db, u, "person.delete", "person", pid, name=p.full_name)
    db.query(PersonCompany).filter_by(person_id=pid).delete()
    db.delete(p)
    db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: str


@app.post("/api/people/{pid}/status")
def set_status(pid: int, body: StatusIn, db: Session = Depends(get_db), u: User = Recruiter):
    p = get_person(db, pid)
    if body.status not in RESEARCH_STATUSES:
        raise HTTPException(400, "Unknown status")
    live = [e for e in p.evidence if e.verification != "Disputed"]
    if body.status == "recruiter_verified" and not any(e.source_url for e in live):
        raise HTTPException(400, "Add at least one sourced evidence item before verifying.")
    if body.status == "ready_for_outreach_review":
        if p.research_status == "research_identified":
            raise HTTPException(400, "A recruiter must verify the candidate first.")
        missing = [CHECKLIST[k] for k in CHECKLIST if not (p.checklist or {}).get(k, {}).get("ok")]
        if missing:
            raise HTTPException(400, "Human validation incomplete: " + "; ".join(missing))
        if not any(e.verification == "Verified" for e in live):
            raise HTTPException(400, "At least one evidence item must be verified by a recruiter.")
    prev = p.research_status
    p.research_status = body.status
    if body.status != "research_identified":
        p.last_verified_at = datetime.utcnow()
    if body.status == "research_identified":
        p.outreach_reviewed = False
    log(db, u, "person.status", "person", pid, **{"from": prev, "to": body.status})
    db.commit()
    return {"ok": True}


class CheckIn(BaseModel):
    key: str
    ok: bool


@app.post("/api/people/{pid}/checklist")
def set_check(pid: int, body: CheckIn, db: Session = Depends(get_db), u: User = Recruiter):
    p = get_person(db, pid)
    if body.key not in CHECKLIST:
        raise HTTPException(400, "Unknown checklist item")
    cl = dict(p.checklist or {})
    cl[body.key] = {"ok": body.ok, "by": u.name, "at": datetime.utcnow().isoformat()}
    p.checklist = cl
    if not body.ok and p.research_status == "ready_for_outreach_review":
        p.research_status = "recruiter_verified"
        p.outreach_reviewed = False
    log(db, u, "person.checklist", "person", pid, item=body.key, ok=body.ok)
    db.commit()
    return {"ok": True}


# ---------- evidence ----------
class EvidenceIn(BaseModel):
    dimension: str
    claim: str
    capabilities: list[str] = []
    source_url: str | None = None
    source_name: str | None = None
    source_type: str = "manual"
    published_date: date | None = None
    strength: str = "Partial"


@app.post("/api/people/{pid}/evidence")
def add_evidence(pid: int, body: EvidenceIn, db: Session = Depends(get_db), u: User = Researcher):
    get_person(db, pid)
    if body.dimension not in EVIDENCE_DIMENSIONS:
        raise HTTPException(400, "Unknown dimension")
    if body.strength not in ("Strong", "Partial", "Weak"):
        raise HTTPException(400, "Unknown strength")
    bad = [c for c in body.capabilities if c not in CAPABILITIES]
    if bad:
        raise HTTPException(400, f"Unknown capabilities: {bad}")
    if not body.claim.strip():
        raise HTTPException(400, "Claim is required")
    e = Evidence(person_id=pid, **body.model_dump(), verification="Unverified", created_by=u.name)
    db.add(e)
    db.flush()
    log(db, u, "evidence.add", "person", pid, evidence_id=e.id, claim=e.claim[:120])
    db.commit()
    return ev_json(e)


@app.patch("/api/evidence/{eid}")
def patch_evidence(eid: int, body: dict, db: Session = Depends(get_db), u: User = Researcher):
    e = db.get(Evidence, eid)
    if not e:
        raise HTTPException(404)
    for k, v in body.items():
        if k == "verification":
            if u.role not in PERMISSIONS["verify"]:
                raise HTTPException(403, "Only recruiters can verify evidence")
            if v not in ("Unverified", "Verified", "Disputed"):
                raise HTTPException(400)
            if v == "Verified" and not e.source_url:
                raise HTTPException(400, "Evidence needs a source link before it can be verified")
            e.verification, e.verified_by = v, u.name if v != "Unverified" else None
        elif k in ("claim", "strength", "source_url", "source_name", "capabilities", "dimension"):
            setattr(e, k, v)
            if k in ("claim", "source_url") and e.verification == "Verified":
                e.verification, e.verified_by = "Unverified", None
        elif k == "published_date":
            e.published_date = date.fromisoformat(v) if v else None
        else:
            raise HTTPException(400, f"Field {k} cannot be edited")
    log(db, u, "evidence.update", "person", e.person_id, evidence_id=eid, **{k: str(v)[:80] for k, v in body.items()})
    db.commit()
    return ev_json(e)


@app.delete("/api/evidence/{eid}")
def delete_evidence(eid: int, db: Session = Depends(get_db), u: User = Researcher):
    e = db.get(Evidence, eid)
    if not e:
        raise HTTPException(404)
    log(db, u, "evidence.delete", "person", e.person_id, evidence_id=eid, claim=e.claim[:120])
    db.delete(e)
    db.commit()
    return {"ok": True}


class UrlIn(BaseModel):
    url: str


@app.post("/api/evidence/from-url")
async def evidence_from_url(body: UrlIn, u: User = Researcher):
    try:
        return await url_evidence.fetch(body.url)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not fetch page: {e}")


@app.post("/api/people/{pid}/refresh")
async def refresh_sources(pid: int, db: Session = Depends(get_db), u: User = Researcher):
    p = get_person(db, pid)
    results = []
    for e in p.evidence:
        if not e.source_url:
            continue
        if "example.com/synthetic" in e.source_url:
            e.link_status = "Synthetic — not checked"
        else:
            e.link_status = await url_evidence.check_link(e.source_url)
        e.last_checked_at = datetime.utcnow()
        results.append({"id": e.id, "status": e.link_status})
    log(db, u, "person.refresh_sources", "person", pid, checked=len(results))
    db.commit()
    return results


# ---------- AI research, role match, outreach ----------
@app.post("/api/people/{pid}/research")
async def run_research(pid: int, db: Session = Depends(get_db), u: User = Researcher):
    p = get_person(db, pid)
    out = await research.research(p, roles_all(db))
    out["generated_at"] = datetime.utcnow().isoformat()
    p.research = out
    log(db, u, "person.research", "person", pid, generated_by=out["generated_by"])
    db.commit()
    return out


class MatchIn(BaseModel):
    role_id: int


@app.post("/api/people/{pid}/matches")
async def run_match(pid: int, body: MatchIn, db: Session = Depends(get_db), u: User = Researcher):
    p = get_person(db, pid)
    role = db.get(RoleProfile, body.role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    content, by = await research.match(p, role)
    db.query(RoleMatch).filter_by(person_id=pid, role_id=role.id).delete()
    m = RoleMatch(person_id=pid, role_id=role.id, relevance=content["relevance"], content=content, generated_by=by, created_by=u.name)
    db.add(m)
    log(db, u, "person.role_match", "person", pid, role=role.name, relevance=content["relevance"])
    db.commit()
    return {"id": m.id, "role": role.name, "relevance": m.relevance, "content": content, "generated_by": by}


class OutreachIn(BaseModel):
    role_id: int | None = None


@app.post("/api/people/{pid}/outreach")
async def gen_outreach(pid: int, body: OutreachIn, db: Session = Depends(get_db), u: User = Recruiter):
    p = get_person(db, pid)
    if p.research_status == "research_identified":
        raise HTTPException(400, "Outreach drafts are only generated for recruiter-verified candidates.")
    hook = research.pick_hook(p)
    if not hook:
        raise HTTPException(400, "Verify at least one project/achievement evidence item — drafts must reference verified work.")
    role = db.get(RoleProfile, body.role_id) if body.role_id else None
    content, by = await research.outreach(p, role, hook, u.name)
    d = OutreachDraft(person_id=pid, role_id=role.id if role else None, subject=content["subject"], body=content["body"],
                      evidence_ids=[hook.id], generated_by=by, created_by=u.name)
    db.add(d)
    db.flush()
    log(db, u, "outreach.generate", "person", pid, draft_id=d.id, evidence_id=hook.id)
    db.commit()
    return {"id": d.id}


@app.patch("/api/outreach/{did}")
def patch_outreach(did: int, body: dict, db: Session = Depends(get_db), u: User = Recruiter):
    d = db.get(OutreachDraft, did)
    if not d:
        raise HTTPException(404)
    p = get_person(db, d.person_id)
    if "subject" in body or "body" in body:
        if d.status == "Approved":
            d.status = "Draft"
        d.subject = body.get("subject", d.subject)
        d.body = body.get("body", d.body)
    if "status" in body:
        if body["status"] not in ("Draft", "Approved", "Rejected"):
            raise HTTPException(400)
        if body["status"] == "Approved" and p.research_status != "ready_for_outreach_review":
            raise HTTPException(400, "Candidate must be 'Ready for outreach review' (human checklist complete) before approving outreach.")
        d.status = body["status"]
        d.reviewed_by, d.reviewed_at = u.name, datetime.utcnow()
        p.outreach_reviewed = any(x.status == "Approved" for x in db.query(OutreachDraft).filter_by(person_id=p.id))
    log(db, u, "outreach.update", "person", d.person_id, draft_id=did, status=d.status)
    db.commit()
    return {"ok": True}


# ---------- notes & conversations ----------
class NoteIn(BaseModel):
    body: str


@app.post("/api/people/{pid}/notes")
def add_note(pid: int, body: NoteIn, db: Session = Depends(get_db), u: User = Researcher):
    get_person(db, pid)
    n = Note(person_id=pid, author=u.name, body=body.body)
    db.add(n)
    log(db, u, "note.add", "person", pid)
    db.commit()
    return {"ok": True}


class ConvIn(BaseModel):
    channel: str
    happened_on: date
    summary: str
    next_step: str | None = None


@app.post("/api/people/{pid}/conversations")
def add_conv(pid: int, body: ConvIn, db: Session = Depends(get_db), u: User = Recruiter):
    get_person(db, pid)
    db.add(Conversation(person_id=pid, author=u.name, **body.model_dump()))
    log(db, u, "conversation.add", "person", pid, channel=body.channel)
    db.commit()
    return {"ok": True}


# ---------- companies ----------
@app.get("/api/companies")
def companies(q: str | None = None, db: Session = Depends(get_db), u: User = Read):
    links = Counter(pid for (pid,) in db.query(PersonCompany.company_id))
    out = []
    for c in db.query(Company).order_by(Company.name):
        if q and q.lower() not in f"{c.name} {c.product or ''} {c.sector or ''}".lower():
            continue
        out.append({"id": c.id, "name": c.name, "website": c.website, "country": c.country, "founded_year": c.founded_year, "sector": c.sector,
                    "product": c.product, "venture_status": c.venture_status, "funding": c.funding, "accelerator": c.accelerator,
                    "is_synthetic": c.is_synthetic, "people": links.get(c.id, 0)})
    return out


@app.get("/api/companies/{cid}")
def company(cid: int, db: Session = Depends(get_db), u: User = Read):
    c = db.get(Company, cid)
    if not c:
        raise HTTPException(404)
    roles = roles_all(db)
    pcs = db.query(PersonCompany).filter_by(company_id=cid).all()
    ids = {pc.person_id: pc for pc in pcs}
    ppl = people_q(db).filter(Person.id.in_(ids)).all() if ids else []
    return {"id": c.id, "name": c.name, "website": c.website, "country": c.country, "city": c.city, "founded_year": c.founded_year,
            "sector": c.sector, "product": c.product, "venture_status": c.venture_status, "funding": c.funding, "accelerator": c.accelerator,
            "is_synthetic": c.is_synthetic, "source": c.source,
            "people": [{**person_summary(p, roles), "relation": ids[p.id].relation} for p in ppl],
            "events": [{"id": e.id, "event_type": e.event_type, "event_date": iso(e.event_date), "summary": e.summary}
                       for e in db.query(WatchEvent).filter(WatchEvent.company_name.ilike(f"%{c.name}%"))]}


@app.patch("/api/companies/{cid}")
def patch_company(cid: int, body: dict, db: Session = Depends(get_db), u: User = Researcher):
    c = db.get(Company, cid)
    if not c:
        raise HTTPException(404)
    for k, v in body.items():
        if k not in ("name", "website", "country", "city", "founded_year", "sector", "product", "venture_status", "funding", "accelerator"):
            raise HTTPException(400, f"Field {k} cannot be edited")
        setattr(c, k, v)
    log(db, u, "company.update", "company", cid, **body)
    db.commit()
    return {"ok": True}


# ---------- roles ----------
@app.get("/api/roles")
def roles(db: Session = Depends(get_db), u: User = Read):
    return [{"id": r.id, "name": r.name, "description": r.description, "capabilities": r.capabilities, "angle": r.angle, "custom": r.custom}
            for r in roles_all(db)]


class RoleIn(BaseModel):
    name: str
    description: str
    capabilities: dict[str, int]
    angle: str | None = None


@app.post("/api/roles")
def add_role(body: RoleIn, db: Session = Depends(get_db), u: User = Recruiter):
    if not body.capabilities or any(c not in CAPABILITIES or not 1 <= w <= 3 for c, w in body.capabilities.items()):
        raise HTTPException(400, "Capabilities must be known keys weighted 1-3")
    if db.query(RoleProfile).filter_by(name=body.name).first():
        raise HTTPException(400, "Role already exists")
    r = RoleProfile(**body.model_dump(), custom=True)
    db.add(r)
    db.flush()
    log(db, u, "role.create", "role", r.id, name=r.name)
    db.commit()
    return {"id": r.id}


# ---------- shortlists ----------
class ShortlistCriteria(BaseModel):
    countries: list[str] = []
    categories: list[str] = []
    role_id: int | None = None
    min_fit: int = 40
    ai: list[str] = []
    founded_from: int | None = None
    min_score: int = 35
    min_evidence: int = 2
    exclude_unavailable: bool = True
    limit: int = 15


def shortlist_people(db: Session, c: ShortlistCriteria) -> list[dict]:
    roles = roles_all(db)
    ps = filter_people(people_q(db).all(), roles, country=c.countries or None, category=c.categories or None, founded_from=c.founded_from,
                       ai=c.ai or None, role_id=c.role_id, min_fit=c.min_fit if c.role_id else 0, min_score=c.min_score)
    ps = [p for p in ps if score(p, roles)["evidence_count"] >= c.min_evidence and not (c.exclude_unavailable and p.availability == "Not currently available")]
    role = next((r for r in roles if r.id == c.role_id), None)
    out = []
    for p in ps:
        s = person_summary(p, roles)
        reasons = []
        if role:
            fit, sup, _ = role_fit(p, role)
            s["selected_role_fit"] = fit
            reasons.append(f"{fit}% evidenced capability fit for {role.name} ({', '.join(CAPABILITIES[x] for x in sup)})")
        reasons.append(f"{s['category_label']} with {s['evidence_count']} cited evidence items ({s['verified_count']} verified)")
        if s["ai_relevance"] in ("High", "Medium"):
            reasons.append(f"{s['ai_relevance']} AI relevance: {s['ai_evidence']}")
        if s["missing"]:
            reasons.append("Needs validation: " + ", ".join(s["missing"]))
        s["shortlist_reasons"] = reasons
        out.append(s)
    out.sort(key=lambda x: (-(x.get("selected_role_fit") or 0) * 0.5 - x["score"]))
    return out[: max(1, min(c.limit, 30))]


@app.post("/api/shortlists/generate")
def gen_shortlist(c: ShortlistCriteria, db: Session = Depends(get_db), u: User = Read):
    return {"criteria": c.model_dump(), "people": shortlist_people(db, c), "disclaimer": DISCLAIMER}


class ShortlistSave(BaseModel):
    name: str
    criteria: dict
    person_ids: list[int]


@app.post("/api/shortlists")
def save_shortlist(body: ShortlistSave, db: Session = Depends(get_db), u: User = Researcher):
    s = Shortlist(name=body.name, criteria=body.criteria, person_ids=body.person_ids, created_by=u.name)
    db.add(s)
    db.flush()
    for p in people_q(db).filter(Person.id.in_(body.person_ids)):
        p.saved = True
    log(db, u, "shortlist.save", "shortlist", s.id, name=s.name, count=len(body.person_ids))
    db.commit()
    return {"id": s.id}


@app.get("/api/shortlists")
def shortlists(db: Session = Depends(get_db), u: User = Read):
    return [{"id": s.id, "name": s.name, "criteria": s.criteria, "count": len(s.person_ids), "created_by": s.created_by,
             "created_at": iso(s.created_at)} for s in db.query(Shortlist).order_by(Shortlist.id.desc())]


@app.get("/api/shortlists/{sid}")
def shortlist(sid: int, db: Session = Depends(get_db), u: User = Read):
    s = db.get(Shortlist, sid)
    if not s:
        raise HTTPException(404)
    roles = roles_all(db)
    ppl = {p.id: p for p in people_q(db).filter(Person.id.in_(s.person_ids))}
    return {"id": s.id, "name": s.name, "criteria": s.criteria, "created_by": s.created_by, "created_at": iso(s.created_at),
            "people": [person_summary(ppl[i], roles) for i in s.person_ids if i in ppl]}


# ---------- watchlist ----------
@app.get("/api/watchlist")
def watchlist(db: Session = Depends(get_db), u: User = Read):
    events = db.query(WatchEvent).order_by(WatchEvent.event_date.desc()).all()
    return {
        "companies": [{"id": w.id, "name": w.name, "kind": w.kind, "notes": w.notes,
                       "events": sum(w.name.lower() in e.company_name.lower() for e in events)} for w in db.query(WatchCompany).order_by(WatchCompany.id)],
        "events": [{"id": e.id, "company_name": e.company_name, "event_type": e.event_type, "event_date": iso(e.event_date), "summary": e.summary,
                    "affected_areas": e.affected_areas, "capability_clusters": e.capability_clusters, "opt_in_channels": e.opt_in_channels,
                    "source_url": e.source_url, "is_synthetic": e.is_synthetic, "created_by": e.created_by} for e in events],
        "tasks": [{"id": t.id, "title": t.title, "detail": t.detail, "status": t.status, "event_id": t.event_id, "person_id": t.person_id,
                   "assignee": t.assignee.name if t.assignee else None, "assignee_id": t.assignee_id, "created_at": iso(t.created_at)}
                  for t in db.query(ResearchTask).order_by(ResearchTask.id.desc())],
        "guardrail": "Never infer that a specific person was affected by restructuring from employer, title, location or a company announcement alone.",
    }


class WatchCompanyIn(BaseModel):
    name: str
    kind: str = "Company"
    notes: str | None = None


@app.post("/api/watch-companies")
def add_watch_company(body: WatchCompanyIn, db: Session = Depends(get_db), u: User = Researcher):
    if db.query(WatchCompany).filter(WatchCompany.name.ilike(body.name)).first():
        raise HTTPException(400, "Already on watchlist")
    w = WatchCompany(**body.model_dump())
    db.add(w)
    db.flush()
    log(db, u, "watch.company_add", "watch_company", w.id, name=w.name)
    db.commit()
    return {"id": w.id}


class WatchEventIn(BaseModel):
    company_name: str
    event_type: str
    event_date: date | None = None
    summary: str
    affected_areas: str | None = None
    capability_clusters: list[str] = []
    opt_in_channels: list[str] = []
    source_url: str


@app.post("/api/watch-events")
def add_event(body: WatchEventIn, db: Session = Depends(get_db), u: User = Researcher):
    if not body.source_url.startswith(("http://", "https://")):
        raise HTTPException(400, "An official announcement URL is required.")
    if body.event_type not in ("Startup launch", "Acquisition", "Closure", "Founder transition", "Restructuring"):
        raise HTTPException(400, "Unknown event type")
    e = WatchEvent(**body.model_dump(), created_by=u.name)
    db.add(e)
    db.flush()
    db.add(ResearchTask(title=f"Research: {e.company_name} — {e.event_type.lower()}", event_id=e.id,
                        detail="Review the official announcement and opt-in channels. Do not infer that any individual employee is affected."))
    log(db, u, "watch.event_add", "watch_event", e.id, company=e.company_name, type=e.event_type, url=e.source_url)
    db.commit()
    return {"id": e.id}


class TaskIn(BaseModel):
    title: str
    detail: str | None = None
    person_id: int | None = None
    assignee_id: int | None = None


@app.post("/api/tasks")
def add_task(body: TaskIn, db: Session = Depends(get_db), u: User = Researcher):
    t = ResearchTask(**body.model_dump())
    db.add(t)
    db.flush()
    log(db, u, "task.add", "task", t.id, title=t.title)
    db.commit()
    return {"id": t.id}


@app.patch("/api/tasks/{tid}")
def patch_task(tid: int, body: dict, db: Session = Depends(get_db), u: User = Researcher):
    t = db.get(ResearchTask, tid)
    if not t:
        raise HTTPException(404)
    for k, v in body.items():
        if k == "status" and v not in ("Open", "In progress", "Done"):
            raise HTTPException(400)
        if k not in ("status", "assignee_id", "detail"):
            raise HTTPException(400)
        setattr(t, k, v)
    log(db, u, "task.update", "task", tid, **body)
    db.commit()
    return {"ok": True}


# ---------- sources ----------
@app.get("/api/sources")
def sources(db: Session = Depends(get_db), u: User = Read):
    st = {s.key: s for s in db.query(SourceState)}
    return [{**s.__dict__, "enabled": bool(st.get(s.key) and st[s.key].enabled), "approved_by": st[s.key].approved_by if s.key in st else None,
             "last_run_at": iso(st[s.key].last_run_at) if s.key in st else None, "last_result": st[s.key].last_result if s.key in st else None,
             "people": db.query(Person).filter_by(source=s.key).count()} for s in SOURCES]


class ToggleIn(BaseModel):
    enabled: bool


@app.post("/api/sources/{key}/toggle")
def toggle_source(key: str, body: ToggleIn, db: Session = Depends(get_db), u: User = Admin):
    s = BY_KEY.get(key)
    if not s:
        raise HTTPException(404)
    if body.enabled and s.status in ("Requires approval", "Requires API key", "Not supported"):
        raise HTTPException(400, f"{s.name}: {s.status}. Record the approval/terms review and implement the connector before enabling.")
    row = db.get(SourceState, key) or SourceState(key=key)
    row.enabled, row.approved_by = body.enabled, u.name
    db.merge(row)
    log(db, u, "source.toggle", "source", None, key=key, enabled=body.enabled)
    db.commit()
    return {"ok": True}


class GithubRunIn(BaseModel):
    country: str = "Singapore"
    keywords: str = ""
    limit: int = 8


@app.post("/api/sources/github/run")
async def run_github(body: GithubRunIn, db: Session = Depends(get_db), u: User = Researcher):
    row = db.get(SourceState, "github")
    if not row or not row.enabled:
        raise HTTPException(400, "GitHub source is disabled")
    try:
        res = await github.run(db, u, body.country, body.keywords, body.limit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"GitHub error: {e}")
    row = db.get(SourceState, "github")
    row.last_run_at = datetime.utcnow()
    row.last_result = f"{len(res['created'])} created, {res['skipped_existing']} already known ({body.country})"
    db.commit()
    return res


# ---------- CSV import / export ----------
CSV_COLUMNS = ["full_name", "title", "company", "company_founded_year", "country", "city", "category", "builder_type", "founding_year",
               "profile_url", "website", "product_built", "venture_status", "built_evidence", "built_source_url", "ai_evidence", "ai_source_url",
               "commercial_evidence", "commercial_source_url", "availability_evidence", "availability_source_url", "is_synthetic"]


@app.get("/api/import/template.csv")
def csv_template(u: User = Read):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    w.writerow(["Example Person (synthetic)", "Founder & CEO", "Example AI Pte Ltd", "2025", "Singapore", "Singapore", "early_founder", "Founder",
                "2025", "https://example.com/profile", "https://example.com", "AI agent for invoice processing", "Active",
                "Founded Example AI and built the first product", "https://example.com/about", "Built an LLM invoice agent", "https://example.com/launch",
                "", "", "", "", "true"])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=founder-radar-template.csv"})


def _int(v):
    try:
        return int(str(v).strip()) if str(v).strip() else None
    except ValueError:
        return None


@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), u: User = Researcher):
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    created, skipped, errors = [], [], []
    existing = people_q(db).all()
    for i, row in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        name = row.get("full_name")
        if not name:
            errors.append(f"Row {i}: full_name is required")
            continue
        cat = row.get("category") or "early_founder"
        if cat not in CATEGORIES:
            errors.append(f"Row {i}: unknown category '{cat}'")
            continue
        synthetic = row.get("is_synthetic", "").lower() in ("1", "true", "yes")
        co = upsert_company(db, row.get("company"), founded_year=_int(row.get("company_founded_year")), country=row.get("country") or None,
                            is_synthetic=synthetic, source="csv")
        p = Person(full_name=name, title=row.get("title") or None, company=co, country=row.get("country") or None, city=row.get("city") or None,
                   category=cat, builder_type=row.get("builder_type") if row.get("builder_type") in BUILDER_TYPES else "Unknown",
                   founding_year=_int(row.get("founding_year")), profile_url=row.get("profile_url") or None, website=row.get("website") or None,
                   product_built=row.get("product_built") or None,
                   venture_status=row.get("venture_status") if row.get("venture_status") in VENTURE_STATUSES else "Unknown",
                   source="csv", is_synthetic=synthetic)
        hard = next((x for x in existing if dedupe.similar(p, x) in ("Same profile URL", "Same source id")), None)
        if hard:
            db.expunge(p) if p in db else None
            skipped.append({"row": i, "name": name, "existing_id": hard.id, "reason": "Same profile URL"})
            continue
        db.add(p)
        db.flush()
        if co:
            db.add(PersonCompany(person_id=p.id, company_id=co.id, relation=p.builder_type, start_year=p.founding_year))
        for dim, key, caps in (("built_from_zero", "built", ["product_development"]), ("ai_technical", "ai", ["ai_ml"]),
                               ("commercial", "commercial", ["commercialisation", "customer_engagement"]), ("availability", "availability", [])):
            claim = row.get(f"{key}_evidence")
            if claim:
                db.add(Evidence(person_id=p.id, dimension=dim, claim=claim, capabilities=caps, source_url=row.get(f"{key}_source_url") or None,
                                source_name="CSV import", source_type="csv", strength="Partial", created_by=u.name))
        soft = dedupe.find_for(p, existing)
        existing.append(p)
        created.append({"id": p.id, "name": name, "possible_duplicates": [{"id": d.id, "name": d.full_name, "reason": r} for d, r in soft]})
    log(db, u, "import.csv", "person", None, file=file.filename, created=len(created), skipped=len(skipped), errors=len(errors))
    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors,
            "note": "Imported availability stays 'Unknown' until a recruiter reviews the cited availability evidence."}


@app.get("/api/export/people.csv")
def export_csv(scope: str = "approved", ids: str | None = None, db: Session = Depends(get_db), u: User = Recruiter):
    roles = roles_all(db)
    ps = people_q(db).all()
    if ids:
        wanted = {int(x) for x in ids.split(",") if x.strip().isdigit()}
        ps = [p for p in ps if p.id in wanted]
    elif scope == "approved":
        ps = [p for p in ps if p.research_status == "ready_for_outreach_review" and p.outreach_reviewed]
    elif scope == "verified":
        ps = [p for p in ps if p.research_status != "research_identified"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "full_name", "title", "company", "country", "city", "category", "builder_type", "what_they_built", "ai_evidence",
                "research_relevance_indicator", "confidence", "top_role_match", "availability", "availability_note", "research_status",
                "outreach_reviewed", "owner", "last_verified", "profile_url", "sources", "is_synthetic"])
    for p in ps:
        s = person_summary(p, roles)
        w.writerow([p.id, p.full_name, p.title, s["company"]["name"] if s["company"] else "", p.country, p.city, s["category_label"], p.builder_type,
                    p.product_built, s["ai_evidence"] or "", s["score"], s["confidence"], s["role_matches"][0]["role"] if s["role_matches"] else "",
                    p.availability, p.availability_note or "", s["research_status_label"], p.outreach_reviewed, s["owner"]["name"] if s["owner"] else "",
                    s["last_verified_at"] or "", p.profile_url or "", " | ".join(s["sources"]), p.is_synthetic])
    log(db, u, "export.csv", "person", None, scope=scope, count=len(ps))
    db.commit()
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=founder-radar-{scope}-{date.today()}.csv"})


# ---------- duplicates ----------
@app.get("/api/duplicates")
def duplicates(db: Session = Depends(get_db), u: User = Read):
    ps = people_q(db).all()
    by = {p.id: p for p in ps}
    roles = roles_all(db)
    return [{"reason": d["reason"], "a": person_summary(by[d["a"]], roles), "b": person_summary(by[d["b"]], roles)} for d in dedupe.find_groups(ps)]


class MergeIn(BaseModel):
    primary_id: int
    duplicate_id: int


@app.post("/api/duplicates/merge")
def merge(body: MergeIn, db: Session = Depends(get_db), u: User = Recruiter):
    a, b = get_person(db, body.primary_id), get_person(db, body.duplicate_id)
    if a.id == b.id:
        raise HTTPException(400)
    for col in ("title", "country", "city", "profile_url", "website", "product_built", "problem_solved", "team_built", "founding_year", "company_id",
                "external_id"):
        if not getattr(a, col) and getattr(b, col):
            setattr(a, col, getattr(b, col))
    for model in (Evidence, Note, Conversation, RoleMatch, OutreachDraft, ResearchTask):
        db.query(model).filter_by(person_id=b.id).update({"person_id": a.id})
    db.query(PersonCompany).filter_by(person_id=b.id).delete()
    db.expire(b)
    log(db, u, "person.merge", "person", a.id, merged_id=b.id, merged_name=b.full_name)
    db.delete(db.get(Person, b.id))
    db.commit()
    return {"ok": True, "id": a.id}


# ---------- audit ----------
@app.get("/api/audit")
def audit(limit: int = 200, db: Session = Depends(get_db), u: User = Depends(require("audit"))):
    return [{"id": a.id, "ts": iso(a.ts), "user": a.user_name, "action": a.action, "entity": a.entity, "entity_id": a.entity_id, "detail": a.detail}
            for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))]


# ---------- static UI ----------
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
