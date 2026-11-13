"""Transparent research-relevance indicator. Every point traces back to a cited evidence row; no evidence -> 0."""
from .models import Evidence, Person, RoleProfile
from .taxonomy import CAPABILITIES, DIMENSIONS, STRENGTH_POINTS, TECHNICAL_CAPABILITIES, VERIFIED_BONUS

DISCLAIMER = ("Research relevance indicator based only on cited public evidence. "
              "It is not a hiring decision, suitability judgement or prediction of performance.")


def cited(e: Evidence) -> bool:
    return e.verification != "Disputed" and bool(e.source_url)


def evidence_points(e: Evidence) -> int:
    if not cited(e):
        return 0
    return STRENGTH_POINTS.get(e.strength, 35) + (VERIFIED_BONUS if e.verification == "Verified" else 0)


def capability_status(person: Person) -> dict[str, dict]:
    out = {}
    for cap, label in CAPABILITIES.items():
        rows = [e for e in person.evidence if cap in (e.capabilities or []) and cited(e)]
        verified = [e for e in rows if e.verification == "Verified"]
        status = "Evidenced (verified)" if verified else "Evidenced (unverified)" if rows else "Unknown"
        out[cap] = {"label": label, "status": status, "evidence_ids": [e.id for e in rows]}
    return out


def role_fit(person: Person, role: RoleProfile) -> tuple[int, list[str], list[str]]:
    caps = capability_status(person)
    total = sum(role.capabilities.values()) or 1
    got, supported, gaps = 0.0, [], []
    for cap, w in role.capabilities.items():
        st = caps.get(cap, {"status": "Unknown"})["status"]
        if st == "Evidenced (verified)":
            got += w
            supported.append(cap)
        elif st == "Evidenced (unverified)":
            got += w * 0.6
            supported.append(cap)
            gaps.append(cap)
        else:
            gaps.append(cap)
    return round(100 * got / total), supported, gaps


def score(person: Person, roles: list[RoleProfile]) -> dict:
    dims = []
    total = 0.0
    for key, (label, weight) in DIMENSIONS.items():
        if key == "role_relevance":
            best = max(((role_fit(person, r)[0], r) for r in roles), key=lambda x: x[0], default=(0, None))
            role_ev = [e for e in person.evidence if e.dimension == "role_relevance" and cited(e)]
            pts = max([best[0]] + [evidence_points(e) for e in role_ev])
            cap_ids = sorted({i for c in (best[1].capabilities if best[1] else {}) for i in capability_status(person)[c]["evidence_ids"]}) if best[1] else []
            ev_ids = [e.id for e in role_ev] + cap_ids
            basis = f"Best capability fit: {best[1].name} ({best[0]}%)" if best[1] and best[0] else "No evidenced capabilities match a Cognition role yet"
        else:
            rows = [e for e in person.evidence if e.dimension == key and cited(e)]
            pts = min(100, max([evidence_points(e) for e in rows], default=0) + 5 * max(0, len(rows) - 1)) if rows else 0
            ev_ids = [e.id for e in rows]
            basis = f"{len(rows)} evidence item(s), {sum(e.verification == 'Verified' for e in rows)} verified" if rows else "No evidence — needs validation"
        pts = min(100, pts)
        total += pts * weight
        dims.append({"key": key, "label": label, "weight": weight, "score": pts, "evidence_ids": ev_ids, "basis": basis,
                     "missing": pts == 0})
    live = [e for e in person.evidence if e.verification != "Disputed"]
    ev = [e for e in live if cited(e)]
    verified = sum(e.verification == "Verified" for e in ev)
    confidence = ("High" if verified >= 3 and len(ev) == len(live) else
                  "Medium" if ev and len(ev) >= max(1, len(live) // 2) else "Low")
    return {"total": round(total), "dimensions": dims, "confidence": confidence, "disclaimer": DISCLAIMER,
            "missing": [d["label"] for d in dims if d["missing"]], "evidence_count": len(ev), "verified_count": verified}


def ai_relevance(person: Person) -> str:
    rows = [e for e in person.evidence if cited(e) and ("ai_ml" in (e.capabilities or []) or e.dimension == "ai_technical")]
    if not rows:
        return "Unknown"
    best = max(evidence_points(e) for e in rows)
    return "High" if best >= 85 else "Medium" if best >= 60 else "Low"


def technical_capabilities(person: Person) -> list[str]:
    caps = capability_status(person)
    return [c for c in TECHNICAL_CAPABILITIES if caps[c]["status"] != "Unknown"]
