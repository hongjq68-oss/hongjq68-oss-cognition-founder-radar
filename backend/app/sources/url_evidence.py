"""Fetch a public page (respecting robots.txt) and propose an evidence row for human review. Never auto-verifies."""
import asyncio
import ipaddress
import re
import socket
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

UA = "CognitionFounderRadar/0.1 (+research; respects robots.txt)"


class _Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.meta, self._in_title = "", {}, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            k = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if k and a.get("content"):
                self.meta.setdefault(k, a["content"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


MAX_REDIRECTS = 5


async def assert_public(url: str) -> None:
    """Reject URLs that resolve to loopback, private, link-local or otherwise non-public addresses."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("URL must be a public http(s) address")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
    except socket.gaierror as e:
        raise ValueError("Host could not be resolved") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
            raise ValueError("URL must point to a public internet host")


async def safe_request(client: httpx.AsyncClient, method: str, url: str) -> httpx.Response:
    for _ in range(MAX_REDIRECTS + 1):
        await assert_public(url)
        r = await client.request(method, url)
        if not r.is_redirect:
            return r
        url = str(r.next_request.url) if r.next_request else urljoin(url, r.headers.get("location", ""))
    raise ValueError("Too many redirects")


async def robots_allowed(client: httpx.AsyncClient, url: str) -> bool:
    u = urlparse(url)
    try:
        r = await safe_request(client, "GET", f"{u.scheme}://{u.netloc}/robots.txt")
        if r.status_code >= 400:
            return True
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url)
    except (httpx.HTTPError, ValueError):
        return True


async def fetch(url: str) -> dict:
    if not re.match(r"^https?://", url):
        raise ValueError("URL must start with http:// or https://")
    await assert_public(url)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers={"User-Agent": UA}) as c:
        if not await robots_allowed(c, url):
            raise PermissionError("robots.txt disallows fetching this page — add the evidence manually instead.")
        r = await safe_request(c, "GET", url)
        r.raise_for_status()
    m = _Meta()
    m.feed(r.text[:500_000])
    pub = m.meta.get("article:published_time") or m.meta.get("datepublished") or m.meta.get("date") or m.meta.get("og:updated_time")
    pd = None
    if pub and (mm := re.match(r"(\d{4})-(\d{2})-(\d{2})", pub)):
        pd = date(int(mm[1]), int(mm[2]), int(mm[3])).isoformat()
    title = (m.meta.get("og:title") or m.title or "").strip()
    desc = (m.meta.get("og:description") or m.meta.get("description") or "").strip()
    return {"source_url": str(r.url), "source_name": m.meta.get("og:site_name") or urlparse(str(r.url)).netloc,
            "title": title[:300], "description": desc[:600], "published_date": pd,
            "suggested_claim": (title + (" — " + desc if desc else ""))[:600],
            "note": "Suggested from page metadata. Edit the claim to what the page actually evidences before saving; it stays Unverified until a recruiter verifies it."}


async def check_link(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, headers={"User-Agent": UA}) as c:
            r = await safe_request(c, "HEAD", url)
            if r.status_code in (403, 405):
                r = await safe_request(c, "GET", url)
            return "OK" if r.status_code < 400 else f"HTTP {r.status_code}"
    except ValueError as e:
        return f"Blocked: {e}"
    except httpx.HTTPError as e:
        return f"Error: {type(e).__name__}"
