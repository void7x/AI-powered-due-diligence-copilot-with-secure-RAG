"""API integration: auth, companies CRUD, upload -> process -> chat -> analyze -> report."""
import time

from tests.conftest import make_company, upload_and_process, wait_ready


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_me(client):
    resp = client.post("/api/auth/register", json={
        "email": "flow@example.com", "password": "password123", "name": "F"})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"email": "flow@example.com", "password": "password123"})
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "flow@example.com"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "x@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "x@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_requires_auth(client):
    assert client.get("/api/companies").status_code == 401


def test_company_crud_and_tenant_isolation(client, auth_headers):
    company_id = make_company(client, auth_headers)
    resp = client.get(f"/api/companies/{company_id}", headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["name"] == "TestCo"

    resp = client.patch(f"/api/companies/{company_id}", headers=auth_headers,
                        json={"name": "TestCo2", "ticker": "TT2", "industry": "i",
                              "country": "c", "description": "d"})
    assert resp.json()["name"] == "TestCo2"

    # another tenant must not see it
    import secrets
    email = f"other-{secrets.token_hex(3)}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    token = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/companies/{company_id}", headers=other_headers).status_code == 403
    assert client.get("/api/companies", headers=other_headers).json() == []

    assert client.delete(f"/api/companies/{company_id}", headers=auth_headers).status_code == 204


def test_upload_validation_errors(client, auth_headers, tmp_path):
    company_id = make_company(client, auth_headers)
    exe = tmp_path / "malware.exe"
    exe.write_bytes(b"MZ fake binary")
    resp = client.post(f"/api/companies/{company_id}/documents", headers=auth_headers,
                       files={"files": ("malware.exe", open(exe, "rb"), "application/octet-stream")})
    assert resp.status_code == 415

    fake_pdf = tmp_path / "not_a_pdf.pdf"
    fake_pdf.write_bytes(b"just text, not a pdf")
    resp = client.post(f"/api/companies/{company_id}/documents", headers=auth_headers,
                       files={"files": ("not_a_pdf.pdf", open(fake_pdf, "rb"), "application/pdf")})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "malformed_document"


def test_duplicate_upload_rejected(client, auth_headers, sample_files):
    company_id = make_company(client, auth_headers)
    _, path, doc_type, year = sample_files[0]
    first = upload_and_process(client, auth_headers, company_id, path, doc_type, year)
    assert wait_ready(client, auth_headers, company_id, first["id"]) == "READY"
    with open(path, "rb") as fh:
        resp = client.post(f"/api/companies/{company_id}/documents", headers=auth_headers,
                           files={"files": (path.name, fh, "application/pdf")})
    assert resp.status_code == 409


def test_full_document_pipeline(client, auth_headers, sample_files):
    company_id = make_company(client, auth_headers)
    _, path, doc_type, year = sample_files[0]
    doc = upload_and_process(client, auth_headers, company_id, path, doc_type, year)
    status = wait_ready(client, auth_headers, company_id, doc["id"])
    assert status == "READY"

    detail = client.get(f"/api/documents/{doc['id']}", headers=auth_headers).json()
    assert detail["page_count"] == 10
    assert detail["document_type"] == doc_type

    pages = client.get(f"/api/documents/{doc['id']}/pages", headers=auth_headers).json()
    assert len(pages) == 10
    assert any("Total revenue" in p["text"] for p in pages)

    status_resp = client.get(f"/api/documents/{doc['id']}/status", headers=auth_headers).json()
    assert status_resp["status"] == "READY" and status_resp["progress"] == 100


def test_chat_with_citations_end_to_end(client, auth_headers, sample_files):
    company_id = make_company(client, auth_headers)
    _, path, doc_type, year = sample_files[0]
    doc = upload_and_process(client, auth_headers, company_id, path, doc_type, year)
    assert wait_ready(client, auth_headers, company_id, doc["id"]) == "READY"

    resp = client.post(f"/api/companies/{company_id}/chat", headers=auth_headers,
                       json={"question": "What percentage of revenue comes from the top three customers?"})
    assert resp.status_code == 200, resp.text
    answer = resp.json()
    assert answer["citations"], "expected citations"
    citation = answer["citations"][0]
    assert citation["page_number"] >= 1
    assert citation["source_id"].startswith("SOURCE_")
    assert answer["session_id"]

    # session history retrievable
    sessions = client.get(f"/api/companies/{company_id}/chat/sessions", headers=auth_headers).json()
    assert len(sessions) == 1
    assert len(sessions[0]["messages"]) == 2


def test_chat_insufficient_evidence(client, auth_headers):
    company_id = make_company(client, auth_headers)
    resp = client.post(f"/api/companies/{company_id}/chat", headers=auth_headers,
                       json={"question": "What was revenue in FY2025?"})
    assert resp.status_code == 200
    assert resp.json()["insufficient_evidence"] is True


def test_analysis_and_report_flow(client, auth_headers, sample_files):
    company_id = make_company(client, auth_headers)
    for _name, path, doc_type, year in sample_files:
        doc = upload_and_process(client, auth_headers, company_id, path, doc_type, year)
        assert wait_ready(client, auth_headers, company_id, doc["id"]) == "READY"

    # analyze via job endpoint
    resp = client.post(f"/api/companies/{company_id}/analyze", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    deadline = time.time() + 60
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}", headers=auth_headers).json()
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.3)
    assert job["status"] == "succeeded", job

    risks = client.get(f"/api/companies/{company_id}/risks", headers=auth_headers).json()
    categories = {r["category"] for r in risks}
    assert "customer_concentration" in categories
    assert "leverage" in categories
    concentration = next(r for r in risks if r["category"] == "customer_concentration")
    assert concentration["evidence"], "risk must carry evidence"
    assert concentration["evidence"][0]["page_number"] >= 1

    opportunities = client.get(f"/api/companies/{company_id}/opportunities", headers=auth_headers).json()
    assert any(o["category"] == "revenue_growth" for o in opportunities)

    inconsistencies = client.get(f"/api/companies/{company_id}/inconsistencies", headers=auth_headers).json()
    assert any("diversified" in i["claim_a"].lower() for i in inconsistencies)

    questions = client.get(f"/api/companies/{company_id}/questions", headers=auth_headers).json()
    assert len(questions) >= 3

    financials = client.get(f"/api/companies/{company_id}/financials", headers=auth_headers).json()
    periods = {p["period_label"] for p in financials["periods"]}
    assert {"FY2023", "FY2024", "FY2025"} <= periods

    changes = client.get(f"/api/companies/{company_id}/financials/changes",
                         headers=auth_headers, params={"base": "FY2024", "target": "FY2025"}).json()
    debt = next(i for i in changes["items"] if i["metric"] == "total_debt")
    assert debt["direction"] == "up" and debt["sentiment"] == "negative"

    # generate report (synchronous convenience endpoint)
    report = client.post(f"/api/companies/{company_id}/report", headers=auth_headers)
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]

    detail = client.get(f"/api/reports/{report_id}", headers=auth_headers).json()
    assert detail["content"]["risks"]
    html = client.get(f"/api/reports/{report_id}/html", headers=auth_headers)
    assert html.status_code == 200 and "Executive Due Diligence Summary" in html.text

    overview = client.get(f"/api/companies/{company_id}/overview", headers=auth_headers).json()
    labels = {c["label"] for c in overview["scorecards"]}
    assert "Overall Risk" in labels and "Financial Health" in labels

    dashboard = client.get("/api/dashboard", headers=auth_headers).json()
    assert dashboard["companies"][0]["risk_level"] in ("low", "moderate", "elevated", "high")

    search = client.get(f"/api/companies/{company_id}/search", headers=auth_headers,
                        params={"q": "top three customers"}).json()
    assert search["total"] >= 1
    assert any("44" in h["excerpt"] for h in search["hits"])
