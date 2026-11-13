"""Clearly-labelled SYNTHETIC demo dataset. All people, companies, URLs and events here are fictional."""
import re
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import Company, Evidence, Person, PersonCompany, ResearchTask, RoleProfile, SourceState, User, WatchCompany, WatchEvent
from .taxonomy import CHECKLIST, DEFAULT_ROLES, DEFAULT_WATCHLIST

TODAY = date(2026, 11, 13)

USERS = [("Alex Tan", "admin@radar.demo", "admin"), ("Priya Raman", "priya@radar.demo", "recruiter"),
         ("Daniel Okafor", "daniel@radar.demo", "recruiter"), ("Mei Lin", "mei@radar.demo", "researcher"),
         ("Sam Viewer", "viewer@radar.demo", "viewer")]

# strength string order: built_from_zero, ai_technical, product_execution, commercial, entrepreneurial  (S/P/W, '-' = no evidence)
P = [
    dict(n="Wei Jie Lim", c="Singapore", city="Singapore", cat="early_founder", bt="Co-founder", t="Co-founder & CTO", co=("Tessellate AI", 2024, "Agentic AI", "Agent platform that automates back-office reconciliation for SME finance teams", "Active", "Pre-seed (synthetic)", "Antler"),
         caps="ai_ml software_engineering product_development enterprise_tech customer_engagement fundraising_bd", s="SSPPS",
         ai="multi-agent planner built on LLM tool-calling with an eval harness of 2,000 reconciliation cases", pe="took the agent from prototype to 14 paying pilots in 9 months", cm="14 paying SME pilots across Singapore and Malaysia", en="raised a pre-seed round through an accelerator programme and hired the first 6 engineers", status="ready_for_outreach_review"),
    dict(n="Aisha Rahman", c="Singapore", city="Singapore", cat="early_founder", bt="Founder", t="Founder & CEO", co=("Ledgerline", 2025, "B2B technology", "Procurement copilot for mid-market manufacturers", "Active", "Seed (synthetic)", "Entrepreneur First"),
         caps="ai_ml product_development commercialisation customer_engagement fundraising_bd enterprise_tech", s="SPSSP",
         ai="RAG pipeline over supplier contracts and an LLM negotiation assistant", pe="shipped v1 in 10 weeks and owns the product roadmap", cm="signed 3 enterprise design partners with published case study", en="formed the company through a talent-investor programme", status="recruiter_verified"),
    dict(n="Marcus Goh", c="Singapore", city="Singapore", cat="former_founder", bt="Founder", t="Advisor (former founder)", co=("Shiplane", 2019, "Developer tools", "CI pipeline optimiser for mobile teams", "Acquired", "Series A (synthetic)", None),
         caps="software_engineering developer_tools product_development commercialisation customer_engagement fundraising_bd", s="SPSSS",
         ai="added ML-based flaky-test detection in 2023", pe="grew product from side project to 40 enterprise customers", cm="40 enterprise customers before acquisition", en="raised Series A and led the acquisition process", av=("Publicly exploring opportunities", "Public post: 'wrapping up my earn-out, exploring what to build next in AI dev tools'"), status="recruiter_verified"),
    dict(n="Hui Min Teo", c="Singapore", city="Singapore", cat="intrapreneur", bt="Intrapreneur", t="Head of AI Products", co=("Meridian Bank", 1972, "Enterprise software", "Retail and commercial bank", "Active", None, None),
         caps="ai_ml enterprise_tech product_development customer_engagement", s="SSP-P",
         ai="GenAI document-processing service used by 3 business lines", pe="took the internal AI platform from prototype to production in 2024", cm=None, en="built and hired a 12-person internal AI team from scratch", status="research_identified"),
    dict(n="Ravi Menon", c="Singapore", city="Singapore", cat="independent_builder", bt="Independent builder", t="Independent developer", co=("agentkit-sg (open source)", 2024, "Developer tools", "Open-source framework for testing LLM agents", "Open-source project", None, None),
         caps="ai_ml software_engineering developer_tools", s="SS-W-",
         ai="framework for deterministic replay testing of LLM agents", pe=None, cm="sponsored by 2 companies via public sponsorship page", en=None, status="research_identified"),
    dict(n="Olivia Chen", c="Australia", city="Sydney", cat="early_founder", bt="Co-founder", t="Co-founder & CEO", co=("Quokka Code", 2024, "Software engineering productivity", "AI code review assistant for regulated industries", "Active", "Pre-seed (synthetic)", "Y Combinator"),
         caps="ai_ml software_engineering developer_tools product_development commercialisation fundraising_bd", s="SSSPS",
         ai="fine-tuned code-review models with on-prem deployment", pe="launched publicly with a waitlist of 1,200 teams", cm="first 5 paying customers in fintech", en="went through an accelerator batch and raised a pre-seed", status="recruiter_verified"),
    dict(n="Jack Thornton", c="Australia", city="Melbourne", cat="former_founder", bt="Founder", t="Founder (company closed)", co=("Paddock Data", 2020, "Data platforms", "Data pipeline platform for agritech", "Closed", "Seed (synthetic)", None),
         caps="software_engineering product_development customer_engagement commercialisation fundraising_bd enterprise_tech", s="SPPPS",
         ai="added ML yield forecasting module", pe="ran product and engineering for 3 years", cm="served 25 farm-management customers", en="raised seed and managed wind-down publicly", av=("Potential transition signal", "Public blog post announcing company closure; no statement about next steps"), status="research_identified"),
    dict(n="Priyanka Shah", c="Australia", city="Sydney", cat="intrapreneur", bt="Intrapreneur", t="Product Lead, New Ventures", co=("Southern Cross Telco", 1990, "B2B technology", "Telecommunications provider", "Active", None, None),
         caps="product_development enterprise_tech commercialisation customer_engagement partnerships", s="SWSSP",
         ai="evaluated LLM triage for support tickets (pilot only)", pe="launched an IoT business line from zero to production", cm="business line reached multi-million revenue (company announcement)", en="built a cross-functional venture team of 20", status="research_identified"),
    dict(n="Liam Nguyen", c="Australia", city="Brisbane", cat="independent_builder", bt="Independent builder", t="Indie hacker", co=("PromptDock", 2025, "Developer tools", "Desktop app to version and test prompts", "Active", None, None),
         caps="ai_ml software_engineering developer_tools product_development", s="SSPW-",
         ai="local LLM evaluation runner with diffing", pe="launched on a product directory and reached top 5 of the day", cm="~300 paying users (self-reported)", en=None, status="research_identified"),
    dict(n="Arjun Iyer", c="India", city="Bengaluru", cat="early_founder", bt="Founder", t="Founder & CEO", co=("Kaveri Labs", 2024, "AI infrastructure", "GPU inference scheduler for Indian-language models", "Active", "Seed (synthetic)", "500 Global"),
         caps="ai_ml software_engineering enterprise_tech commercialisation fundraising_bd", s="SSSPS",
         ai="custom inference scheduler cutting serving cost 40% for Indic LLMs", pe="owns architecture and shipped 3 major releases", cm="contracts with 2 public-sector pilots", en="raised seed from an accelerator portfolio", status="research_identified"),
    dict(n="Sneha Kulkarni", c="India", city="Pune", cat="early_founder", bt="Co-founder", t="Co-founder & CPO", co=("FlowSutra", 2023, "Automation", "Workflow automation agents for logistics", "Active", "Pre-seed (synthetic)", "Iterative"),
         caps="ai_ml product_development customer_engagement commercialisation", s="SPSS-",
         ai="LLM agents that parse shipping documents", pe="led product from MVP to 60 customers", cm="60 logistics customers", en=None, status="research_identified"),
    dict(n="Rohan Mehta", c="India", city="Mumbai", cat="former_founder", bt="Co-founder", t="VP Engineering (post-acquisition)", co=("Chakra Pay", 2018, "Fintech", "Payments API for SMEs", "Acquired", "Series B (synthetic)", None),
         caps="software_engineering enterprise_tech product_development partnerships", s="SPSPS",
         ai="fraud-scoring models in payments pipeline", pe="scaled API to millions of daily transactions", cm="bank partnerships announced publicly", en="co-founded and led engineering through acquisition", av=("Not currently available", "Public announcement of new VP role after acquisition (2026)"), status="research_identified"),
    dict(n="Kavya Reddy", c="India", city="Hyderabad", cat="independent_builder", bt="Independent builder", t="Open-source maintainer", co=("evalforge (open source)", 2024, "Developer tools", "LLM evaluation toolkit", "Open-source project", None, None),
         caps="ai_ml software_engineering developer_tools", s="SS-P-",
         ai="maintains an LLM eval toolkit with ~4k stars (synthetic)", pe=None, cm="used by several startups (public adopters list)", en=None, status="research_identified"),
    dict(n="Vikram Joshi", c="India", city="Bengaluru", cat="intrapreneur", bt="Intrapreneur", t="Director, AI Engineering", co=("Indus Consulting Group", 2001, "Enterprise software", "Technology consulting firm", "Active", None, None),
         caps="ai_ml software_engineering enterprise_tech partnerships customer_engagement", s="PSSPP",
         ai="built an internal GenAI code-modernisation accelerator", pe="took accelerator from prototype to 8 client deployments", cm="8 client deployments referenced in company blog", en="built a 30-person practice", status="research_identified"),
    dict(n="Yuki Tanaka", c="Japan", city="Tokyo", cat="early_founder", bt="Founder", t="Founder & CEO", co=("Kintsugi Systems", 2024, "Enterprise software", "AI agents for legacy COBOL migration", "Active", "Seed (synthetic)", None),
         caps="ai_ml software_engineering enterprise_tech commercialisation customer_engagement", s="SSPS-",
         ai="LLM-assisted COBOL-to-Java translation with test generation", pe="released product to 4 enterprise pilots", cm="pilots with 4 Japanese enterprises", en=None, status="research_identified"),
    dict(n="Haruto Sato", c="Japan", city="Osaka", cat="independent_builder", bt="Independent builder", t="AI maker", co=("Shiori (side project)", 2025, "Agentic AI", "Browser agent that automates research workflows", "Active", None, None),
         caps="ai_ml software_engineering product_development", s="SSW--",
         ai="browser automation agent with vision model", pe="public demo video and changelog", cm=None, en=None, status="research_identified"),
    dict(n="Emi Nakamura", c="Japan", city="Tokyo", cat="former_founder", bt="Co-founder", t="Co-founder (pivoted)", co=("Tsumiki", 2021, "B2B technology", "No-code internal tools builder (pivoted to AI forms)", "Pivoted", "Seed (synthetic)", None),
         caps="product_development customer_engagement commercialisation fundraising_bd", s="SWPPS",
         ai=None, pe="relaunched product after pivot", cm="~100 SMB customers before pivot", en="raised seed and led pivot", status="research_identified"),
    dict(n="Ji-ho Park", c="South Korea", city="Seoul", cat="early_founder", bt="Co-founder", t="Co-founder & CTO", co=("Hanbit Agents", 2024, "Agentic AI", "Customer-support agents for Korean e-commerce", "Active", "Pre-seed (synthetic)", "Antler"),
         caps="ai_ml software_engineering product_development customer_engagement", s="SSSP-",
         ai="Korean-language support agents with retrieval and tool use", pe="shipped to 20 merchants", cm="20 merchants live", en=None, status="research_identified"),
    dict(n="Seo-yeon Kim", c="South Korea", city="Seoul", cat="intrapreneur", bt="Intrapreneur", t="Lead, Internal Developer Platform", co=("Daehan Electronics", 1969, "Enterprise software", "Electronics manufacturer", "Active", None, None),
         caps="software_engineering developer_tools enterprise_tech product_development", s="PPS--",
         ai="piloted AI code assistants across 400 engineers", pe="built internal developer platform from zero", cm=None, en=None, status="research_identified"),
    dict(n="Min-jun Lee", c="South Korea", city="Busan", cat="independent_builder", bt="Independent builder", t="Independent developer", co=("kimchi-llm (open source)", 2024, "AI infrastructure", "Korean tokenizer and fine-tuning recipes", "Open-source project", None, None),
         caps="ai_ml software_engineering", s="PS---",
         ai="published Korean fine-tuning recipes", pe=None, cm=None, en=None, status="research_identified"),
    dict(n="Chloe Wong", c="Hong Kong", city="Hong Kong", cat="early_founder", bt="Founder", t="Founder", co=("HarbourStack", 2025, "Data platforms", "Data-room AI for private-equity due diligence", "Stealth", None, None),
         caps="ai_ml product_development commercialisation fundraising_bd", s="PP-P-",
         ai="LLM document Q&A over data rooms", pe=None, cm="2 design partners (founder interview)", en=None, status="research_identified"),
    dict(n="Kelvin Ho", c="Hong Kong", city="Hong Kong", cat="former_founder", bt="Founder", t="Former founder", co=("Dim Sum Analytics", 2017, "Data platforms", "Restaurant analytics SaaS", "Acquired", "Series A (synthetic)", None),
         caps="product_development commercialisation customer_engagement partnerships fundraising_bd", s="SWSSS",
         ai=None, pe="ran product for 6 years", cm="800 restaurant customers", en="exited via acquisition (public press release)", av=("Unknown", None), status="research_identified"),
    dict(n="Putri Wijaya", c="Indonesia", city="Jakarta", cat="early_founder", bt="Co-founder", t="Co-founder & CEO", co=("Sahabat AI Ops", 2024, "Automation", "AI agents for SME bookkeeping in Bahasa", "Active", "Pre-seed (synthetic)", "Iterative"),
         caps="ai_ml product_development commercialisation customer_engagement fundraising_bd", s="SPSSS",
         ai="Bahasa-language bookkeeping agent", pe="launched mobile app with 5k MAU", cm="5k monthly active SMEs", en="raised pre-seed through an accelerator", status="research_identified"),
    dict(n="Budi Santoso", c="Indonesia", city="Bandung", cat="independent_builder", bt="Independent builder", t="Developer & content creator", co=("NusantaraDev", 2023, "Developer tools", "Tutorials and open-source starter kits for AI apps", "Active", None, None),
         caps="ai_ml software_engineering developer_tools customer_engagement", s="PPPW-",
         ai="open-source starter kits for agent apps", pe="maintains 6 public repos", cm="community of 10k developers (public channel)", en=None, status="research_identified"),
    dict(n="Dewi Lestari", c="Indonesia", city="Jakarta", cat="intrapreneur", bt="Intrapreneur", t="VP, Digital Ventures", co=("Garuda Retail Group", 1985, "B2B technology", "Retail conglomerate", "Active", None, None),
         caps="product_development commercialisation enterprise_tech partnerships", s="S-SSP",
         ai=None, pe="launched a B2B marketplace inside the group", cm="marketplace with 2,000 merchants", en="built venture team of 25", status="research_identified"),
    dict(n="Farah Aziz", c="Malaysia", city="Kuala Lumpur", cat="early_founder", bt="Founder", t="Founder & CTO", co=("Rimba Robotics Software", 2024, "AI startup", "Computer-vision QA for palm-oil processing", "Active", "Grant (synthetic)", None),
         caps="ai_ml software_engineering product_development customer_engagement", s="SSPP-",
         ai="edge computer-vision models", pe="deployed at 3 mills", cm="3 paying mill operators", en=None, status="research_identified"),
    dict(n="Daniel Lee", c="Malaysia", city="Penang", cat="former_founder", bt="Co-founder", t="Co-founder (exited)", co=("TestPilot MY", 2019, "Developer tools", "QA automation platform", "Acquired", "Seed (synthetic)", None),
         caps="software_engineering developer_tools customer_engagement commercialisation", s="SPSPP",
         ai="added AI test-generation feature", pe="led product and engineering", cm="regional enterprise customers", en="co-founded and exited", av=("Confirmed publicly available", "Public post on personal site: 'available for new roles from Dec 2026'"), status="research_identified"),
    dict(n="Nattapong Srisuk", c="Thailand", city="Bangkok", cat="early_founder", bt="Co-founder", t="Co-founder & CTO", co=("SiamScribe", 2025, "AI startup", "Thai speech-to-text and meeting agents", "Active", None, None),
         caps="ai_ml software_engineering product_development", s="SSP--",
         ai="Thai ASR fine-tuned models", pe="public beta launched", cm=None, en=None, status="research_identified"),
    dict(n="Ploy Chaiyaporn", c="Thailand", city="Bangkok", cat="intrapreneur", bt="Intrapreneur", t="Head of Innovation Lab", co=("Chao Phraya Bank", 1945, "Enterprise software", "Commercial bank", "Active", None, None),
         caps="ai_ml enterprise_tech product_development partnerships", s="PPS-P",
         ai="GenAI customer-service pilot", pe="took 2 lab prototypes into production", cm=None, en="founded the innovation lab", status="research_identified"),
    dict(n="Miguel Santos", c="Philippines", city="Manila", cat="early_founder", bt="Founder", t="Founder & CEO", co=("Bayanihan Support AI", 2024, "Agentic AI", "AI support agents for BPO teams", "Active", "Pre-seed (synthetic)", "Y Combinator"),
         caps="ai_ml product_development customer_engagement commercialisation enterprise_tech fundraising_bd", s="SSSSS",
         ai="agent copilots used by BPO agents", pe="launched to 3 BPO operators", cm="3 BPO contracts", en="went through an accelerator and raised pre-seed", status="recruiter_verified"),
    dict(n="Andrea Reyes", c="Philippines", city="Cebu", cat="independent_builder", bt="Independent builder", t="Freelance AI engineer", co=("Tala Tools", 2025, "Automation", "Zapier-style automations powered by LLMs", "Active", None, None),
         caps="ai_ml software_engineering", s="PP---",
         ai="LLM automation templates", pe=None, cm=None, en=None, status="research_identified"),
]

SRC = {"built_from_zero": ("company_website", "Company website"), "ai_technical": ("launch_post", "Product launch announcement"),
       "product_execution": ("founder_interview", "Founder interview"), "commercial": ("company_website", "Customer case study"),
       "entrepreneurial": ("accelerator_directory", "Accelerator directory"), "availability": ("public_post", "Public post")}
DIM_CAPS = {"built_from_zero": {"product_development", "software_engineering"}, "ai_technical": {"ai_ml", "software_engineering", "developer_tools"},
            "product_execution": {"product_development", "developer_tools", "enterprise_tech"},
            "commercial": {"customer_engagement", "commercialisation", "enterprise_tech"},
            "entrepreneurial": {"fundraising_bd", "partnerships"}}
STRENGTH = {"S": "Strong", "P": "Partial", "W": "Weak"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _built_claim(p: dict, co: tuple) -> str:
    if p["cat"] == "intrapreneur":
        return f"Started and led a new initiative from zero inside {co[0]}: {p['pe'] or p['ai']}."
    if p["cat"] == "independent_builder":
        return f"Created {co[0]} independently — {co[3]}."
    return f"{p['bt']} of {co[0]} (founded {co[1]}); built {co[3][0].lower() + co[3][1:]} from zero."


def seed(db: Session) -> None:
    if db.query(User).count():
        return
    for name, email, role in USERS:
        db.add(User(name=name, email=email, role=role))
    for name, desc, caps, angle in DEFAULT_ROLES:
        db.add(RoleProfile(name=name, description=desc, capabilities=caps, angle=angle))
    for name in DEFAULT_WATCHLIST:
        db.add(WatchCompany(name=name, kind="Company", notes="Monitor official announcements only. No events recorded yet."))
    db.add(WatchCompany(name="Relevant AI startups", kind="Segment", notes="APAC AI startups: launches, acquisitions, closures."))
    db.flush()
    recruiter = db.query(User).filter_by(email="priya@radar.demo").one()

    for i, p in enumerate(P):
        co_t = p["co"]
        co = Company(name=co_t[0], founded_year=co_t[1], sector=co_t[2], product=co_t[3], venture_status=co_t[4], funding=co_t[5],
                     accelerator=co_t[6], country=p["c"], city=p["city"], website=f"https://example.com/synthetic/{slug(co_t[0])}",
                     is_synthetic=True, source="demo")
        db.add(co)
        db.flush()
        corp = p["cat"] == "intrapreneur"
        person = Person(
            full_name=p["n"], title=p["t"], company=co, country=p["c"], city=p["city"], category=p["cat"], builder_type=p["bt"],
            founding_year=None if corp else co_t[1], product_built=co_t[3] if not corp else (p["pe"] or co_t[3]),
            problem_solved=co_t[3], team_built=p["en"] if p["en"] and "team" in p["en"] else None, venture_status=co_t[4] if not corp else "Internal venture",
            profile_url=f"https://example.com/synthetic/profile/{slug(p['n'])}", website=co.website,
            previous_ventures=[], is_synthetic=True, source="demo", research_status=p["status"],
            transition_evidence=p.get("av", (None, None))[1] if p["cat"] == "former_founder" else None,
        )
        if p["cat"] == "former_founder":
            person.previous_ventures = [f"{co_t[0]} ({co_t[1]}–{'2025' if co_t[4] != 'Pivoted' else 'present'}, {co_t[4].lower()})"]
        db.add(person)
        db.flush()
        db.add(PersonCompany(person_id=person.id, company_id=co.id, relation="Employee" if corp else p["bt"], start_year=co_t[1] if not corp else 2021))
        caps = set(p["caps"].split())
        claims = {"built_from_zero": _built_claim(p, co_t), "ai_technical": p["ai"] and f"Built {p['ai']}.",
                  "product_execution": p["pe"] and f"Product ownership: {p['pe']}.", "commercial": p["cm"] and f"Commercial traction: {p['cm']}.",
                  "entrepreneurial": p["en"] and f"Operating experience: {p['en']}."}
        verified_flow = p["status"] in ("recruiter_verified", "ready_for_outreach_review")
        for j, (dim, code) in enumerate(zip(claims, p["s"])):
            if code == "-" or not claims[dim]:
                continue
            st, sn = SRC[dim]
            db.add(Evidence(person_id=person.id, dimension=dim, claim=claims[dim], capabilities=sorted(caps & DIM_CAPS[dim]) or sorted(caps)[:1],
                            source_url=f"https://example.com/synthetic/{slug(co_t[0])}/{st}", source_name=f"{sn} (synthetic)", source_type=st,
                            published_date=TODAY - timedelta(days=30 + 41 * ((i + j) % 11)), strength=STRENGTH[code],
                            verification="Verified" if verified_flow and code == "S" else "Unverified",
                            verified_by=recruiter.name if verified_flow and code == "S" else None, created_by="Demo dataset"))
        av = p.get("av")
        if av and av[1]:
            db.add(Evidence(person_id=person.id, dimension="availability", claim=av[1], capabilities=[],
                            source_url=f"https://example.com/synthetic/profile/{slug(p['n'])}/post", source_name="Public post (synthetic)",
                            source_type="public_post", published_date=TODAY - timedelta(days=20 + i), strength="Strong", verification="Unverified",
                            created_by="Demo dataset"))
            person.availability, person.availability_note = av
        if verified_flow:
            person.last_verified_at = datetime(2026, 11, 1 + i % 10, 10, 0)
            person.owner_id = recruiter.id
            person.saved = True
            person.checklist = {k: {"ok": p["status"] == "ready_for_outreach_review" or k in ("identity", "relevance"), "by": recruiter.name,
                                    "at": person.last_verified_at.isoformat()} for k in CHECKLIST}

    # A near-duplicate imported record to exercise duplicate detection.
    dup_co = db.query(Company).filter_by(name="Kaveri Labs").one()
    db.add(Person(full_name="Arjun S. Iyer", title="CEO", company=dup_co, country="India", city="Bengaluru", category="early_founder",
                  builder_type="Founder", founding_year=2024, profile_url="https://example.com/synthetic/profile/arjun-iyer",
                  is_synthetic=True, source="csv", product_built="GPU inference scheduler"))

    events = [
        ("Northwind Cloud (synthetic)", "Acquisition", date(2026, 9, 18), "Synthetic example: Northwind Cloud announced the acquisition of an agent-observability startup; integration of the product team announced.",
         "Agent observability product; developer relations", ["AI infrastructure", "Developer tools", "Developer relations"], ["Official alumni opt-in form (synthetic)"]),
        ("Lumora AI (synthetic)", "Closure", date(2026, 10, 2), "Synthetic example: Lumora AI publicly announced it is winding down operations after 3 years.",
         "Whole company (founders publicly announced next steps are TBD)", ["Agentic AI", "Applied ML", "Enterprise sales"], ["Founders' public announcement post (synthetic)"]),
        ("Pelican Robotics (synthetic)", "Founder transition", date(2026, 10, 21), "Synthetic example: co-founder publicly announced stepping back from day-to-day role.",
         "Founder role only", ["Robotics software", "Product leadership"], []),
        ("Batch W26 AI startups (synthetic)", "Startup launch", date(2026, 11, 5), "Synthetic example: accelerator demo day featured 12 APAC AI startups.",
         "N/A", ["Agentic AI", "Developer tools"], ["Accelerator public directory (synthetic)"]),
    ]
    for name, typ, d, summ, areas, clusters, channels in events:
        ev = WatchEvent(company_name=name, event_type=typ, event_date=d, summary=summ, affected_areas=areas, capability_clusters=clusters,
                        opt_in_channels=channels, source_url=f"https://example.com/synthetic/announcements/{slug(name)}", is_synthetic=True, created_by="Demo dataset")
        db.add(ev)
        db.flush()
        db.add(ResearchTask(title=f"Research: {name} — {typ.lower()}", event_id=ev.id, status="Open",
                            detail="Review the official announcement and opt-in channels. Do not infer that any individual employee is affected."))
    for key in ("demo", "manual", "csv", "url_evidence", "github"):
        db.add(SourceState(key=key, enabled=True, approved_by="System default"))
    db.commit()
