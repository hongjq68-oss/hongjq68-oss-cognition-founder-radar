# Architecture

```
React (Vite, Tailwind)  ──/api──▶  FastAPI
                                    ├── auth.py        role-based access (viewer < researcher < recruiter < admin), signed bearer tokens
                                    ├── audit.py       every write → audit_log
                                    ├── models.py      SQLAlchemy schema (SQLite locally, any SQL DB via DATABASE_URL)
                                    ├── scoring.py     transparent, evidence-only research relevance score
                                    ├── research.py    AI research layer: summaries, role matching, outreach drafts (LLM w/ guardrail prompt, rules fallback)
                                    ├── llm.py         optional OpenAI / Anthropic JSON client
                                    ├── dedupe.py      duplicate detection + merge
                                    └── sources/       source integration registry (plugins)
                                         ├── url_evidence.py  public-page metadata fetcher (honours robots.txt)
                                         └── github.py        GitHub public REST API discovery
```

## Data model

`users`, `companies`, `people`, `person_companies` (company history), `evidence` (claim, dimension, capabilities, source URL/name/type, published date, strength, verification, verifier, link status), `role_profiles` (capability weights), `role_matches`, `outreach_drafts`, `notes`, `conversations`, `shortlists`, `watch_companies`, `watch_events`, `research_tasks`, `source_states`, `audit_log`.

## Scoring (research relevance indicator — not a hiring decision)

| Dimension | Weight |
| --- | --- |
| Built something from zero | 25% |
| AI / technical relevance | 20% |
| Product execution and ownership | 20% |
| Customer or commercial evidence | 15% |
| Entrepreneurial operating experience | 10% |
| Cognition role relevance | 10% |

Each dimension is computed only from cited evidence rows (strength × verification). A dimension with no evidence scores 0 and is surfaced as *needs validation*. Confidence reflects evidence volume and the verified share.

## Guardrails (enforced server-side)

- Availability is stored separately from capability. Any value other than `Unknown` / `Not currently available` needs a cited availability evidence item; `Confirmed publicly available` needs it recruiter-verified.
- Workflow: `Research identified` → `Recruiter verified` (recruiter only) → `Ready for outreach review` (requires the 4-point human checklist and ≥1 recruiter-verified evidence item). AI output never advances status.
- Outreach drafts are only generated for recruiter-verified people and must reference verified work; approval requires `Ready for outreach review`. Nothing is sent automatically.
- Watchlist events require an official source URL and create research tasks; they are never linked to individuals.
- No LinkedIn scraping (registered as *Not supported* — authorised partner integration only). Sources that need agreements/API keys stay disabled until an admin approves them.
- The LLM prompt forbids inventing facts, judging personality/age/protected characteristics, or deciding hiring.

## Phases

1. Dashboard, candidate & company databases, manual/CSV import, filters, evidence profiles ✅
2. AI research, categorisation, role matching, shortlist generation, outreach drafts ✅ (rules mode; LLM when a key is set)
3. Approved source integrations (GitHub live; others registered), watchlist/transition signals, dedupe, link refresh ✅ partial
4. Recruiter workflow ✅, reporting/analytics, more APAC markets — next
