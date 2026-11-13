"""Controlled vocabularies shared by the backend and exposed to the UI via /api/meta."""

PRIORITY_COUNTRIES = ["Singapore", "Australia", "India", "Japan", "South Korea", "Hong Kong",
                      "Indonesia", "Malaysia", "Thailand", "Philippines"]

CATEGORIES = {
    "early_founder": "Early-stage founder",
    "former_founder": "Former founder / transition",
    "intrapreneur": "Corporate entrepreneur",
    "independent_builder": "Independent builder / AI maker",
}

BUILDER_TYPES = ["Founder", "Co-founder", "Early employee", "Independent builder", "Intrapreneur", "Unknown"]

VENTURE_STATUSES = ["Active", "Acquired", "Closed", "Pivoted", "Stealth", "Internal venture", "Open-source project", "Unknown"]

AVAILABILITY = [
    "Confirmed publicly available",
    "Publicly exploring opportunities",
    "Potential transition signal",
    "Unknown",
    "Not currently available",
]
# Availability levels that may only be set when backed by an explicit availability evidence row.
AVAILABILITY_REQUIRES_EVIDENCE = {"Confirmed publicly available", "Publicly exploring opportunities", "Potential transition signal"}

RESEARCH_STATUSES = {
    "research_identified": "Research identified",
    "recruiter_verified": "Recruiter verified",
    "ready_for_outreach_review": "Ready for outreach review",
}

CHECKLIST = {
    "identity": "Identity confirmed (the profile, sources and person are the same individual)",
    "relevance": "Relevance confirmed (evidence supports why they are on the list)",
    "source_quality": "Source quality acceptable (claims backed by credible public sources)",
    "contact_appropriateness": "Contact is appropriate (public/consented channel, no sensitive inference)",
}

CAPABILITIES = {
    "ai_ml": "AI & machine learning",
    "software_engineering": "Software engineering",
    "product_development": "Product development",
    "developer_tools": "Developer tools",
    "enterprise_tech": "Enterprise technology",
    "customer_engagement": "Customer engagement",
    "commercialisation": "Commercialisation",
    "partnerships": "Partnerships",
    "fundraising_bd": "Fundraising / business development",
}
TECHNICAL_CAPABILITIES = {"ai_ml", "software_engineering", "developer_tools"}

DIMENSIONS = {
    "built_from_zero": ("Built something from zero", 0.25),
    "ai_technical": ("AI / technical relevance", 0.20),
    "product_execution": ("Product execution and ownership", 0.20),
    "commercial": ("Customer or commercial evidence", 0.15),
    "entrepreneurial": ("Entrepreneurial operating experience", 0.10),
    "role_relevance": ("Cognition role relevance", 0.10),
}
EVIDENCE_DIMENSIONS = {**{k: v[0] for k, v in DIMENSIONS.items()}, "availability": "Availability", "identity": "Identity / profile"}

STRENGTH_POINTS = {"Strong": 85, "Partial": 60, "Weak": 35}
VERIFIED_BONUS = 15

SECTORS = ["AI startup", "Agentic AI", "Developer tools", "Enterprise software", "AI infrastructure", "Data platforms",
           "Automation", "Software engineering productivity", "B2B technology", "Fintech", "Other"]

DEFAULT_ROLES = [
    ("Forward Deployed Engineer",
     "Embeds with enterprise customers to deploy Devin, build integrations and turn real workflows into production outcomes.",
     {"software_engineering": 3, "ai_ml": 2, "customer_engagement": 2, "enterprise_tech": 1, "product_development": 1},
     "You have shipped products end-to-end for real users — FDEs do that inside the world's largest engineering orgs, with Devin as the lever."),
    ("Partner Deployed Engineer",
     "Works with SI and cloud partners to design and deliver Devin-powered engineering transformations.",
     {"software_engineering": 3, "ai_ml": 2, "partnerships": 2, "customer_engagement": 1},
     "Your experience building with and through partners maps to helping global SIs reinvent software delivery with autonomous agents."),
    ("Applied AI Engineer",
     "Builds agentic systems, evals and tooling that push what an AI software engineer can do.",
     {"ai_ml": 3, "software_engineering": 3, "developer_tools": 2, "product_development": 1},
     "You have built AI products from scratch — Cognition is building the frontier of AI that writes software."),
    ("AI Support Engineer",
     "Technical first line for customers adopting Devin: debugging, enablement and feedback into product.",
     {"software_engineering": 2, "customer_engagement": 2, "developer_tools": 2, "ai_ml": 1},
     "Your hands-on developer-tools experience and customer empathy are exactly what early Devin adopters need."),
    ("Applied AI Transformation Manager",
     "Leads enterprise programmes that move engineering organisations to AI-native ways of working.",
     {"enterprise_tech": 3, "customer_engagement": 2, "ai_ml": 2, "commercialisation": 1, "product_development": 1},
     "You have driven change from zero inside complex organisations — help enterprises redesign how software gets built."),
    ("Account Director",
     "Owns strategic enterprise relationships and grows Devin adoption across APAC accounts.",
     {"commercialisation": 3, "customer_engagement": 3, "enterprise_tech": 2, "fundraising_bd": 1},
     "As a founder you sold a vision before it existed — Cognition is doing that at the frontier of AI software engineering."),
    ("Partner Director",
     "Builds Cognition's partner ecosystem with GSIs, clouds and resellers in APAC.",
     {"partnerships": 3, "commercialisation": 2, "fundraising_bd": 2, "enterprise_tech": 1},
     "You have built ecosystems and alliances from scratch — help shape how APAC's largest partners bring AI engineers to market."),
]

DEFAULT_WATCHLIST = ["Canva", "Netflix", "Grab", "Sea", "Google", "Microsoft", "Amazon"]

WATCH_EVENT_TYPES = ["Restructuring", "Acquisition", "Closure", "Founder transition", "Startup launch", "Accelerator batch"]
