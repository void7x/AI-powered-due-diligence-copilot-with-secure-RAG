"""Safe on-disk storage for uploads (outside any web-served directory)."""
from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import Settings


def company_upload_dir(settings: Settings, company_id: str) -> Path:
    path = Path(settings.upload_dir) / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_upload(settings: Settings, company_id: str, safe_name: str, data: bytes) -> Path:
    """Store under UPLOAD_DIR/<company>/<uuid>_<name> - never web-served directly."""
    base = company_upload_dir(settings, company_id)
    path = base / f"{uuid.uuid4().hex[:12]}_{safe_name}"
    path.write_bytes(data)
    return path


def delete_stored_file(path: str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
