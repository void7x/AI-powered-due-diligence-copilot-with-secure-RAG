"""Initial schema: users, companies, documents, chunks (pgvector), financials,
risks, opportunities, inconsistencies, questions, reports, citations, chats.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.core.config import get_settings

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_DIM = get_settings().embedding_dim


def upgrade() -> None:
    is_pg = op.get_bind().dialect.name == "postgresql"
    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False, server_default=""),
        sa.Column("industry", sa.String(120), nullable=False, server_default=""),
        sa.Column("country", sa.String(120), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_companies_user", "companies", ["user_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False, server_default="other"),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPLOADED"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("company_id", "file_hash", name="uq_documents_company_hash"),
    )
    op.create_index("ix_documents_company", "documents", ["company_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_fiscal_year", "documents", ["fiscal_year"])

    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_pages_doc_page", "document_pages", ["document_id", "page_number"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(255), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("document_type", sa.String(40), nullable=False, server_default="other"),
        sa.Column("embedding", Vector(_DIM).with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_chunks_company", "document_chunks", ["company_id"])
    op.create_index("ix_chunks_document", "document_chunks", ["document_id"])
    op.create_index("ix_chunks_company_year", "document_chunks", ["company_id", "fiscal_year"])
    op.create_index("ix_chunks_company_type", "document_chunks", ["company_id", "document_type"])
    op.create_index("ix_chunks_fiscal_year", "document_chunks", ["fiscal_year"])
    op.create_index("ix_chunks_document_type", "document_chunks", ["document_type"])
    # ANN index for pgvector cosine distance (HNSW, pgvector >= 0.5) — Postgres only
    if is_pg:
        op.execute("CREATE INDEX ix_chunks_embedding_hnsw ON document_chunks "
                   "USING hnsw (embedding vector_cosine_ops)")

    op.create_table(
        "financial_periods",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_label", sa.String(32), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("unit", sa.String(24), nullable=False, server_default="million"),
        sa.Column("source_document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "period_label", name="uq_period_company_label"),
    )

    op.create_table(
        "financial_metrics",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_id", sa.String(32), sa.ForeignKey("financial_periods.id"), nullable=False),
        sa.Column("period_label", sa.String(32), nullable=False),
        sa.Column("metric", sa.String(48), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("unit", sa.String(24), nullable=False, server_default="million"),
        sa.Column("source_document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_metrics_company_metric", "financial_metrics", ["company_id", "metric"])
    op.create_index("ix_financial_metrics_period_label", "financial_metrics", ["period_label"])
    op.create_index("ix_financial_metrics_metric", "financial_metrics", ["metric"])

    op.create_table(
        "risks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category", sa.String(48), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("why_it_matters", sa.Text(), nullable=False, server_default=""),
        sa.Column("potential_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("detected_signals", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risks_company", "risks", ["company_id"])
    op.create_index("ix_risks_category", "risks", ["category"])
    op.create_index("ix_risks_severity", "risks", ["severity"])

    op.create_table(
        "risk_evidence",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("risk_id", sa.String(32), sa.ForeignKey("risks.id"), nullable=False),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(255), nullable=False, server_default=""),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_risk_evidence_risk", "risk_evidence", ["risk_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category", sa.String(48), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("potential_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunities_company", "opportunities", ["company_id"])
    op.create_index("ix_opportunities_category", "opportunities", ["category"])

    op.create_table(
        "opportunity_evidence",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("opportunity_id", sa.String(32), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("document_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(255), nullable=False, server_default=""),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_opportunity_evidence_opp", "opportunity_evidence", ["opportunity_id"])

    op.create_table(
        "inconsistencies",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("topic", sa.String(120), nullable=False, server_default=""),
        sa.Column("claim_a", sa.Text(), nullable=False, server_default=""),
        sa.Column("claim_b", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_a_document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("source_a_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_b_document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("source_b_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inconsistencies_company", "inconsistencies", ["company_id"])

    op.create_table(
        "management_questions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("topic", sa.String(120), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_company", "management_questions", ["company_id"])
    op.create_index("ix_management_questions_priority", "management_questions", ["priority"])

    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False,
                  server_default="Executive Due Diligence Summary"),
        sa.Column("status", sa.String(20), nullable=False, server_default="complete"),
        sa.Column("period_from", sa.String(32), nullable=True),
        sa.Column("period_to", sa.String(32), nullable=True),
        sa.Column("overall_risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_company", "analysis_reports", ["company_id"])
    op.create_index("ix_analysis_reports_status", "analysis_reports", ["status"])
    op.create_index("ix_analysis_reports_created_at", "analysis_reports", ["created_at"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("company_id", sa.String(32), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_sessions_company", "chat_sessions", ["company_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("session_id", sa.String(32), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_session", "chat_messages", ["session_id"])

    op.create_table(
        "citations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("report_id", sa.String(32), sa.ForeignKey("analysis_reports.id"), nullable=True),
        sa.Column("message_id", sa.String(32), sa.ForeignKey("chat_messages.id"), nullable=True),
        sa.Column("evidence_id", sa.String(24), nullable=False, server_default=""),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("document_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(255), nullable=False, server_default=""),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_citations_message", "citations", ["message_id"])
    op.create_index("ix_citations_report", "citations", ["report_id"])


def downgrade() -> None:
    for table in ("citations", "chat_messages", "chat_sessions", "analysis_reports",
                  "management_questions", "inconsistencies", "opportunity_evidence",
                  "opportunities", "risk_evidence", "risks", "financial_metrics",
                  "financial_periods", "document_chunks", "document_pages",
                  "documents", "companies", "users"):
        op.drop_table(table)  # table drops cascade to their indexes
