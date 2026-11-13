# Cognition Founder Radar

Internal talent-intelligence app for finding exceptional founders, former founders, intrapreneurs and independent AI builders across APAC — **based on what they have built, not where they work or their job title**.

> Demo data is **synthetic**: every person, company, URL and event in the seed dataset is fictional and labelled SYNTHETIC in the UI.

## Run

```bash
./start.sh            # builds the UI, serves UI + API on http://localhost:8000
```

Dev mode: `cd backend && .venv/bin/uvicorn app.main:app --reload` and `cd frontend && npm run dev` (Vite on :5173 proxies `/api`).

Tests: `cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q tests`

Demo sign-in (email-only, replace with SSO in production): `admin@`, `priya@` / `daniel@` (recruiters), `mei@` (researcher), `viewer@` — all `@radar.demo`.

### Optional environment variables

| Variable | Purpose |
| --- | --- |
| `GITHUB_TOKEN` / `GH_TOKEN` | Higher GitHub API rate limit for the GitHub discovery connector |
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | LLM-written research summaries, role matches and outreach drafts (falls back to deterministic rules) |
| `RADAR_SECRET` | Token signing secret (auto-generated into `backend/data/.secret` otherwise) |
| `RADAR_DATA_DIR` | SQLite location (default `backend/data`) |
| `DATABASE_URL` | Use Postgres etc. instead of SQLite |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design, data model, scoring and guardrails.
