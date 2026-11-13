import io
import os
import tempfile

os.environ["RADAR_DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def login(email):
    t = c.post("/api/auth/login", json={"email": email}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


REC, RES, VIEW = login("priya@radar.demo"), login("mei@radar.demo"), login("viewer@radar.demo")


def test_requires_auth():
    assert c.get("/api/people").status_code == 401


def test_dashboard_and_search():
    d = c.get("/api/dashboard", headers=VIEW).json()
    assert d["kpis"]["total"] >= 30 and d["kpis"]["ready"] >= 1
    ppl = c.get("/api/people", params={"category": "early_founder", "ai": ["High"], "country": ["Singapore", "India"]}, headers=VIEW).json()
    assert ppl and all(p["category"] == "early_founder" and p["ai_relevance"] == "High" for p in ppl)
    assert all(p["sources"] for p in ppl)


def test_score_is_evidence_backed():
    pid = c.get("/api/people", params={"q": "Andrea Reyes"}, headers=VIEW).json()[0]["id"]
    p = c.get(f"/api/people/{pid}", headers=VIEW).json()
    dims = {d["key"]: d for d in p["score_breakdown"]["dimensions"]}
    assert dims["commercial"]["score"] == 0 and dims["commercial"]["missing"]
    assert "Customer or commercial evidence" in p["missing"]
    for d in dims.values():
        if d["score"] and d["key"] != "role_relevance":
            assert d["evidence_ids"]


def test_viewer_cannot_write_and_researcher_cannot_verify():
    pid = c.get("/api/people", headers=VIEW).json()[0]["id"]
    assert c.post(f"/api/people/{pid}/notes", json={"body": "x"}, headers=VIEW).status_code == 403
    assert c.post(f"/api/people/{pid}/status", json={"status": "recruiter_verified"}, headers=RES).status_code == 403


def test_availability_needs_evidence():
    pid = c.get("/api/people", params={"q": "Andrea Reyes"}, headers=VIEW).json()[0]["id"]
    r = c.patch(f"/api/people/{pid}", json={"availability": "Publicly exploring opportunities"}, headers=REC)
    assert r.status_code == 400


def test_full_workflow_to_approved_outreach_and_export():
    r = c.post("/api/people", json={"full_name": "Test Founder", "company_name": "Test AI", "country": "Singapore", "category": "early_founder",
                                    "builder_type": "Founder", "founding_year": 2025, "is_synthetic": True}, headers=RES)
    pid = r.json()["id"]
    assert c.post(f"/api/people/{pid}/status", json={"status": "recruiter_verified"}, headers=REC).status_code == 400
    e = c.post(f"/api/people/{pid}/evidence", json={"dimension": "built_from_zero", "claim": "Founded Test AI and shipped an invoice agent.",
                                                    "capabilities": ["product_development", "ai_ml"], "source_url": "https://example.com/x",
                                                    "strength": "Strong"}, headers=RES).json()
    assert c.post(f"/api/people/{pid}/outreach", json={}, headers=REC).status_code == 400
    assert c.post(f"/api/people/{pid}/status", json={"status": "recruiter_verified"}, headers=REC).status_code == 200
    assert c.post(f"/api/people/{pid}/outreach", json={}, headers=REC).status_code == 400  # no verified evidence
    assert c.patch(f"/api/evidence/{e['id']}", json={"verification": "Verified"}, headers=RES).status_code == 403
    assert c.patch(f"/api/evidence/{e['id']}", json={"verification": "Verified"}, headers=REC).status_code == 200
    role = c.get("/api/roles", headers=VIEW).json()[2]
    m = c.post(f"/api/people/{pid}/matches", json={"role_id": role["id"]}, headers=RES).json()
    assert {"why", "supported", "needs_validation", "questions", "angle"} <= set(m["content"])
    assert c.post(f"/api/people/{pid}/outreach", json={"role_id": role["id"]}, headers=REC).status_code == 200
    draft = c.get(f"/api/people/{pid}", headers=REC).json()["drafts"][0]
    assert "invoice agent" in draft["body"]
    assert c.patch(f"/api/outreach/{draft['id']}", json={"status": "Approved"}, headers=REC).status_code == 400
    assert c.post(f"/api/people/{pid}/status", json={"status": "ready_for_outreach_review"}, headers=REC).status_code == 400
    for k in ("identity", "relevance", "source_quality", "contact_appropriateness"):
        c.post(f"/api/people/{pid}/checklist", json={"key": k, "ok": True}, headers=REC)
    assert c.post(f"/api/people/{pid}/status", json={"status": "ready_for_outreach_review"}, headers=REC).status_code == 200
    assert c.patch(f"/api/outreach/{draft['id']}", json={"status": "Approved"}, headers=REC).status_code == 200
    csv_text = c.get("/api/export/people.csv", params={"scope": "approved"}, headers=REC).text
    assert "Test Founder" in csv_text
    assert any(a["action"] == "outreach.update" for a in c.get("/api/audit", headers=REC).json())


def test_csv_import_and_duplicates():
    csv_body = ("full_name,company,country,category,profile_url,built_evidence,built_source_url\n"
                "Imported Builder,Imp Co,Japan,independent_builder,https://example.com/imp,Built a thing,https://example.com/thing\n"
                "Wei Jie Lim,Tessellate AI,Singapore,early_founder,https://example.com/synthetic/profile/wei-jie-lim,,\n")
    r = c.post("/api/import/csv", files={"file": ("x.csv", io.BytesIO(csv_body.encode()), "text/csv")}, headers=RES).json()
    assert len(r["created"]) == 1 and len(r["skipped"]) == 1
    groups = c.get("/api/duplicates", headers=VIEW).json()
    assert any({g["a"]["full_name"], g["b"]["full_name"]} == {"Arjun Iyer", "Arjun S. Iyer"} for g in groups)


def test_shortlist_is_bounded_and_explained():
    s = c.post("/api/shortlists/generate", json={"countries": [], "min_score": 30, "limit": 10}, headers=VIEW).json()
    assert 0 < len(s["people"]) <= 10 and all(p["shortlist_reasons"] for p in s["people"])


def test_watch_event_requires_url():
    r = c.post("/api/watch-events", json={"company_name": "Grab", "event_type": "Restructuring", "summary": "x", "source_url": ""}, headers=RES)
    assert r.status_code == 400


def _ready_candidate(name):
    pid = c.post("/api/people", json={"full_name": name, "country": "Japan", "city": "Tokyo"}, headers=REC).json()["id"]
    eid = c.post(f"/api/people/{pid}/evidence", json={"dimension": "built_from_zero", "claim": "Built a thing", "capabilities": ["ai_ml"],
                                                       "source_url": "https://example.com/a", "strength": "Strong"}, headers=RES).json()["id"]
    assert c.patch(f"/api/evidence/{eid}", json={"verification": "Verified"}, headers=REC).status_code == 200
    assert c.post(f"/api/people/{pid}/status", json={"status": "recruiter_verified"}, headers=REC).status_code == 200
    for k in c.get("/api/meta", headers=REC).json()["checklist"]:
        c.post(f"/api/people/{pid}/checklist", json={"key": k, "ok": True}, headers=REC)
    assert c.post(f"/api/people/{pid}/status", json={"status": "ready_for_outreach_review"}, headers=REC).status_code == 200
    return pid, eid


def test_evidence_changes_reopen_gates():
    pid, eid = _ready_candidate("Gate Tester")
    did = c.post(f"/api/people/{pid}/outreach", json={}, headers=REC).json()["id"]
    assert c.patch(f"/api/outreach/{did}", json={"status": "Approved"}, headers=REC).status_code == 200
    c.patch(f"/api/outreach/{did}", json={"body": "edited"}, headers=REC)
    assert c.get(f"/api/people/{pid}", headers=REC).json()["outreach_reviewed"] is False
    c.patch(f"/api/evidence/{eid}", json={"strength": "Weak"}, headers=RES)
    p = c.get(f"/api/people/{pid}", headers=REC).json()
    assert p["research_status"] == "recruiter_verified"
    assert c.patch(f"/api/outreach/{did}", json={"status": "Approved"}, headers=REC).status_code == 400


def test_unsourced_evidence_not_scored():
    pid = c.post("/api/people", json={"full_name": "Uncited Person"}, headers=REC).json()["id"]
    c.post(f"/api/people/{pid}/evidence", json={"dimension": "built_from_zero", "claim": "Says so", "strength": "Strong"}, headers=RES)
    assert c.get(f"/api/people/{pid}", headers=REC).json()["score"] == 0


def test_cjk_names_not_duplicates_and_delete_cleans_up():
    a = c.post("/api/people", json={"full_name": "山田太郎", "country": "Japan", "city": "Osaka"}, headers=REC).json()
    b = c.post("/api/people", json={"full_name": "佐藤花子", "country": "Japan", "city": "Osaka"}, headers=REC).json()
    assert not b["possible_duplicates"]
    c.post(f"/api/people/{a['id']}/notes", json={"body": "note"}, headers=REC)
    assert c.delete(f"/api/people/{a['id']}", headers=REC).status_code == 200


def test_export_filtered_and_formula_safe():
    c.post("/api/people", json={"full_name": "=HYPERLINK(\"x\")", "country": "Thailand"}, headers=REC)
    r = c.get("/api/export/people.csv", params={"scope": "filtered", "country": ["Thailand"]}, headers=REC).text
    rows = r.strip().splitlines()[1:]
    assert rows and all("Thailand" in x for x in rows) and "'=HYPERLINK" in r


def test_spa_and_watch_event_and_ssrf():
    assert "root:" not in c.get("//etc/passwd").text
    ok = c.post("/api/watch-events", json={"company_name": "X", "event_type": "Restructuring", "event_date": "2026-01-01", "summary": "s",
                                            "source_url": "https://example.com/news"}, headers=RES)
    assert ok.status_code == 200
    assert c.post("/api/evidence/from-url", json={"url": "http://127.0.0.1:8000/api/meta"}, headers=RES).status_code == 400
