"""Source integration layer. Each source declares its access model; only approved + enabled sources can run.

To add an approved source: implement a module exposing `async def run(db, user, **params) -> dict`, then register it in SOURCES.
"""
from dataclasses import dataclass, field


@dataclass
class SourceDef:
    key: str
    name: str
    kind: str          # Directory | API | Import | Fetcher | Community
    access: str        # how access is authorised
    status: str        # Live | Live (manual URL) | Requires approval | Requires API key | Not supported
    description: str
    runnable: bool = False
    params: list[str] = field(default_factory=list)


SOURCES = [
    SourceDef("demo", "Synthetic demo dataset", "Import", "Built-in", "Live", "Clearly-labelled fictional people and companies for development."),
    SourceDef("manual", "Manual entry", "Import", "Recruiter input", "Live", "Add a person by hand with cited evidence."),
    SourceDef("csv", "CSV import", "Import", "Recruiter upload", "Live", "Bulk import from approved exports (e.g. opt-in community lists)."),
    SourceDef("url_evidence", "Public page evidence fetcher", "Fetcher", "Public pages; honours robots.txt",
              "Live (manual URL)", "Paste a company website, launch post, founder interview or announcement URL; extracts title/date for human review."),
    SourceDef("github", "GitHub (public REST API)", "API", "Official API; optional GITHUB_TOKEN", "Live",
              "Finds public builders by location with AI-related repositories. Stores public profile + repo links only — no emails.", True,
              ["country", "keywords", "limit"]),
    SourceDef("producthunt", "Product Hunt", "API", "Official GraphQL API token + terms review", "Requires API key", "Launches and makers."),
    SourceDef("yc", "Y Combinator company directory", "Directory", "Needs approved access / data agreement", "Requires approval", "Company + founder listings."),
    SourceDef("antler", "Antler portfolio", "Directory", "Needs approved access", "Requires approval", "Portfolio companies and founders."),
    SourceDef("ef", "Entrepreneur First network & portfolio", "Directory", "Needs approved access", "Requires approval", "Portfolio companies and founders."),
    SourceDef("500global", "500 Global portfolio", "Directory", "Needs approved access", "Requires approval", "Portfolio companies."),
    SourceDef("iterative", "Iterative portfolio", "Directory", "Needs approved access", "Requires approval", "Portfolio companies."),
    SourceDef("announcements", "Official restructuring / M&A announcements", "Fetcher", "Public press releases via URL", "Live (manual URL)",
              "Add events to the research watchlist from an official announcement URL."),
    SourceDef("alumni", "Voluntary alumni & founder communities", "Community", "Opt-in / consent-based lists only", "Requires approval",
              "Import via CSV once the community has consented."),
    SourceDef("linkedin", "Professional profiles (LinkedIn)", "API", "Authorised partner integration only", "Not supported",
              "No scraping of private or logged-in data. Public profile URLs may be stored as references."),
]
BY_KEY = {s.key: s for s in SOURCES}
