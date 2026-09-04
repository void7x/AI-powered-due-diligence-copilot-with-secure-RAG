"""AI Due Diligence Copilot - FastAPI application entrypoint."""
from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger, request_id_ctx

log = get_logger("app.main")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered due-diligence workspace: document intelligence, evidence-backed RAG, "
                    "deterministic financial analysis, risk/opportunity engines and executive reports.",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        import uuid
        rid = uuid.uuid4().hex[:12]
        request_id_ctx.set(rid)
        import time
        start = time.perf_counter()
        response = await call_next(request)
        latency = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        log.info("request", extra={"endpoint": request.url.path, "method": request.method,
                                   "status_code": response.status_code,
                                   "latency_ms": round(latency, 1)})
        return response

    register_error_handlers(app)

    from app.api.router import api_router
    app.include_router(api_router)

    @app.on_event("startup")
    def startup() -> None:
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        if settings.create_demo_user:
            _ensure_demo_user()

    @app.get("/", include_in_schema=False)
    def root():
        return {"app": settings.app_name, "docs": "/docs", "api": "/api"}

    return app


def _ensure_demo_user() -> None:
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.models import User
    settings = get_settings()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.demo_email.lower()).first()
        if existing is None:
            db.add(User(email=settings.demo_email.lower(), name="Demo Analyst",
                        password_hash=hash_password(settings.demo_password)))
            db.commit()
            log.info("demo user created", extra={"processing_status": settings.demo_email})
    finally:
        db.close()


app = create_app()
