"""Shared column helpers."""
from __future__ import annotations

from sqlalchemy import JSON, Column
from pgvector.sqlalchemy import Vector

from app.core.config import get_settings


def embedding_column() -> Column:
    """pgvector column on PostgreSQL; JSON array fallback on SQLite (tests/dev)."""
    dim = get_settings().embedding_dim
    return Column(Vector(dim).with_variant(JSON(), "sqlite"), nullable=True)


def json_column():
    return Column(JSON, nullable=True, default=dict)
