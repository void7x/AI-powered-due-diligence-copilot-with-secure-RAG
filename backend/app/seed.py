"""Seed the database with a synthetic demo company and full analysis.

Usage:  python -m app.seed [--force]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from app.core.config import ROOT_DIR, get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.models import ChatMessage, ChatSession, Company, Document, User
from app.sample_data.generator import SAMPLE_COMPANY, generate_sample_documents
from app.services.analysis.orchestrator import run_company_analysis
from app.services.ingestion.pipeline import process_document_sync

log = get_logger("app.seed")


def seed(force: bool = False) -> None:
    settings = get_settings()
    configure_logging()
    # In production, migrations run first (alembic upgrade head). For lightweight
    # SQLite dev setups, ensure the schema exists so the seed works standalone.
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        demo = db.query(User).filter(User.email == settings.demo_email.lower()).first()
        if demo is None:
            demo = User(email=settings.demo_email.lower(), name="Demo Analyst",
                        password_hash=hash_password(settings.demo_password))
            db.add(demo)
            db.commit()
            db.refresh(demo)

        existing = db.query(Company).filter(Company.name == SAMPLE_COMPANY["name"],
                                            Company.user_id == demo.id).first()
        if existing is not None:
            if not force:
                print(f"Demo company '{SAMPLE_COMPANY['name']}' already exists (id={existing.id}). "
                      "Use --force to recreate it.")
                return
            for doc in db.query(Document).filter(Document.company_id == existing.id).all():
                try:
                    Path(doc.storage_path).unlink(missing_ok=True)
                except OSError:
                    pass
            db.delete(existing)
            db.commit()

        company = Company(user_id=demo.id, **SAMPLE_COMPANY)
        db.add(company)
        db.commit()
        db.refresh(company)

        sample_dir = ROOT_DIR / "data" / "sample"
        shutil.rmtree(sample_dir, ignore_errors=True)
        docs_meta = generate_sample_documents(sample_dir)

        for filename, path, doc_type, year in docs_meta:
            data = path.read_bytes()
            import hashlib
            storage_dir = Path(settings.upload_dir) / company.id
            storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = storage_dir / f"sample_{filename}"
            storage_path.write_bytes(data)
            doc = Document(
                company_id=company.id, filename=filename, document_type=doc_type,
                fiscal_year=year, file_hash=hashlib.sha256(data).hexdigest(),
                storage_path=str(storage_path), mime_type="application/pdf",
                file_size=len(data), status="UPLOADED",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            process_document_sync(doc.id)
            print(f"  processed {filename}")

        report_id = run_company_analysis(db, company)
        db.refresh(company)
        print(f"Seeded demo company '{company.name}' (id={company.id})")
        print(f"Login: {settings.demo_email} / {settings.demo_password}")
        print(f"Report: {report_id}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the demo workspace")
    parser.add_argument("--force", action="store_true", help="Recreate the demo company")
    args = parser.parse_args()
    seed(force=args.force)
