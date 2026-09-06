from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    if not db_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "database": False,
                "app": get_settings().app_name,
            },
        )

    return {"status": "ok", "database": True, "app": get_settings().app_name}
