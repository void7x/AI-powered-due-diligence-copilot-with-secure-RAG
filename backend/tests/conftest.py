"""Test fixtures: SQLite DB (pgvector column stored as JSON), TestClient, helpers."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("CREATE_DEMO_USER", "false")
os.environ.setdefault("AI_PROVIDER", "offline")
os.environ.setdefault("EMBEDDING_PROVIDER", "offline")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="dd-uploads-"))

import app.core.db as dbmod  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import Base  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import User  # noqa: E402
from app.sample_data.generator import generate_sample_documents  # noqa: E402

# Background jobs open their own sessions; point them at the test engine too.
dbmod.SessionLocal = None  # set after TestSession below

_test_engine = create_engine(
    "sqlite://",  # in-memory
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=_test_engine, autoflush=False, expire_on_commit=False)
dbmod.SessionLocal = TestSession


@pytest.fixture(scope="session")
def sample_files(tmp_path_factory) -> list[tuple[str, Path, str, int]]:
    return generate_sample_documents(tmp_path_factory.mktemp("samples"))


@pytest.fixture()
def db_session():
    Base.metadata.create_all(_test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(_test_engine)


@pytest.fixture()
def client(db_session):
    from app.core.db import get_db
    from app.main import app

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Registers a fresh user, returns Authorization headers."""
    import secrets
    email = f"user-{secrets.token_hex(4)}@example.com"
    resp = client.post("/api/auth/register", json={
        "email": email, "password": "password123", "name": "Test User"})
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_company(client, auth_headers, name: str = "TestCo") -> str:
    resp = client.post("/api/companies", headers=auth_headers, json={
        "name": name, "ticker": "TST", "industry": "Testing", "country": "US",
        "description": "test company"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def upload_and_process(client, auth_headers, company_id: str, path: Path,
                       document_type: str = "other", fiscal_year: int | None = None) -> dict:
    with open(path, "rb") as fh:
        params = {"document_type": document_type}
        if fiscal_year:
            params["fiscal_year"] = fiscal_year
        resp = client.post(f"/api/companies/{company_id}/documents",
                           headers=auth_headers,
                           files={"files": (path.name, fh, "application/pdf")},
                           params=params)
    assert resp.status_code == 201, resp.text
    doc = resp.json()[0]
    return doc


def wait_ready(client, auth_headers, company_id: str, doc_id: str,
               timeout_s: float = 30.0) -> str:
    import time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
        status = resp.json()["status"]
        if status in ("READY", "FAILED"):
            return status
        time.sleep(0.2)
    return "TIMEOUT"
