"""Duplicate detection: profile URL, external id, or similar name + same company/country."""
import re
import unicodedata
from difflib import SequenceMatcher

from .models import Person


def norm_name(n: str) -> str:
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return " ".join(t for t in re.sub(r"[^a-z ]", " ", n).split() if len(t) > 1)


def norm_url(u: str | None) -> str | None:
    if not u:
        return None
    return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/")


def similar(a: Person, b: Person) -> str | None:
    if a.external_id and a.external_id == b.external_id:
        return "Same source id"
    if norm_url(a.profile_url) and norm_url(a.profile_url) == norm_url(b.profile_url):
        return "Same profile URL"
    na, nb = norm_name(a.full_name), norm_name(b.full_name)
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    subset = len(ta & tb) >= 2 and (ta <= tb or tb <= ta)
    same_ctx = (a.company_id and a.company_id == b.company_id) or (a.country and a.country == b.country and a.city == b.city)
    if (ratio >= 0.88 or subset) and same_ctx:
        return f"Similar name ({round(ratio * 100)}%) and same {'company' if a.company_id == b.company_id else 'location'}"
    return None


def find_groups(people: list[Person]) -> list[dict]:
    pairs = []
    for i, a in enumerate(people):
        for b in people[i + 1:]:
            reason = similar(a, b)
            if reason:
                pairs.append({"a": a.id, "b": b.id, "reason": reason})
    return pairs


def find_for(candidate: Person, people: list[Person]) -> list[tuple[Person, str]]:
    return [(p, r) for p in people if p.id != candidate.id and (r := similar(candidate, p))]
