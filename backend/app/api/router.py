from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    analysis, auth, chat, companies, dashboard, documents, health, jobs, reports, search,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(analysis.router)
api_router.include_router(reports.router)
api_router.include_router(search.router)
api_router.include_router(jobs.router)
api_router.include_router(dashboard.router)
api_router.include_router(health.router)
