"""GitHub public REST API connector: finds builders in a location with AI-related public repositories."""
import os
from datetime import date

import httpx
from sqlalchemy.orm import Session

from ..audit import log
from ..models import Evidence, Person, User

MAX_PAGES = 5
AI_TERMS = ("llm", "gpt", "agent", "ai", "ml", "rag", "langchain", "transformer", "diffusion", "embedding", "copilot", "neural", "inference", "eval")


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _is_ai(repo: dict, extra: list[str]) -> bool:
    text = " ".join([repo.get("name") or "", repo.get("description") or "", " ".join(repo.get("topics") or [])]).lower()
    words = set(text.replace("-", " ").replace("_", " ").split())
    return any(t in words for t in AI_TERMS) or any(k.lower() in text for k in extra)


async def run(db: Session, user: User, country: str = "Singapore", keywords: str = "", limit: int = 8) -> dict:
    limit = max(1, min(int(limit), 15))
    extra = [k.strip() for k in keywords.split(",") if k.strip()]
    q = f'location:"{country}" type:user repos:>3 followers:>20'
    created, skipped, examined = [], 0, 0
    async with httpx.AsyncClient(timeout=20, headers=_headers()) as c:
        for page in range(1, MAX_PAGES + 1):
            if len(created) >= limit:
                break
            r = await c.get("https://api.github.com/search/users", params={"q": q, "sort": "followers", "per_page": 30, "page": page})
            if r.status_code == 403:
                raise RuntimeError("GitHub rate limit reached — set GITHUB_TOKEN on the server and retry.")
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                break
            for u in items:
                if len(created) >= limit:
                    break
                examined += 1
                login = u["login"]
                if db.query(Person).filter_by(external_id=f"github:{login}").first():
                    skipped += 1
                    continue
                repos = (await c.get(f"https://api.github.com/users/{login}/repos", params={"sort": "pushed", "per_page": 50, "type": "owner"})).json()
                if not isinstance(repos, list):
                    continue
                ai_repos = sorted([x for x in repos if not x.get("fork") and x.get("stargazers_count", 0) >= 5 and _is_ai(x, extra)], key=lambda x: x.get("stargazers_count", 0), reverse=True)
                if not ai_repos:
                    continue
                prof = (await c.get(f"https://api.github.com/users/{login}")).json()
                top = ai_repos[0]
                bio = (prof.get("bio") or "").strip()
                person = Person(full_name=prof.get("name") or login, title=(bio[:180] or "GitHub builder"), country=country,
                                city=(prof.get("location") or "")[:80], profile_url=prof.get("html_url"), website=prof.get("blog") or None,
                                category="independent_builder", builder_type="Independent builder", source="github", external_id=f"github:{login}",
                                product_built=f"{top['name']}: {top.get('description') or 'public repository'}"[:400],
                                venture_status="Open-source project", research={"source_note": f"GitHub company field: {prof.get('company') or '—'}"})
                db.add(person)
                db.flush()
                for i, rp in enumerate(ai_repos[:3]):
                    stars = rp.get("stargazers_count", 0)
                    strength = "Strong" if stars >= 200 else "Partial" if stars >= 25 else "Weak"
                    pushed = (rp.get("pushed_at") or "")[:10]
                    db.add(Evidence(person_id=person.id, dimension="built_from_zero" if i == 0 else "ai_technical",
                                    claim=f"Created public repo {rp['full_name']} — {rp.get('description') or 'no description'} ({stars}★, {rp.get('language') or 'n/a'}).",
                                    capabilities=["software_engineering", "ai_ml"] + (["developer_tools"] if "tool" in (rp.get("description") or "").lower() else []),
                                    source_url=rp["html_url"], source_name="GitHub", source_type="github",
                                    published_date=date.fromisoformat(pushed) if pushed else None, strength=strength, created_by="GitHub connector"))
                if bio and any(w in bio.lower() for w in ("founder", "co-founder", "cofounder")):
                    db.add(Evidence(person_id=person.id, dimension="entrepreneurial", claim=f"Public GitHub bio states: \"{bio[:200]}\"",
                                    capabilities=["fundraising_bd"], source_url=prof.get("html_url"), source_name="GitHub profile", source_type="github",
                                    strength="Weak", created_by="GitHub connector"))
                log(db, user, "source.github.create", "person", person.id, login=login)
                created.append({"id": person.id, "name": person.full_name, "repo": top["full_name"]})
    db.commit()
    return {"created": created, "skipped_existing": skipped, "examined": examined, "query": q}
