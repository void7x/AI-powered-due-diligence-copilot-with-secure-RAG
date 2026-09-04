"""Structured application errors surfaced as clean JSON: {"error": {code, message, details}}."""
from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger("app.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, status_code: int | None = None,
                 code: str | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details or {}


class BadRequestError(AppError):
    status_code, code = 400, "bad_request"


class UnsupportedFileTypeError(BadRequestError):
    status_code, code = 415, "unsupported_file_type"


class MalformedDocumentError(BadRequestError):
    status_code, code = 422, "malformed_document"


class UnauthorizedError(AppError):
    status_code, code = 401, "unauthorized"


class ForbiddenError(AppError):
    status_code, code = 403, "forbidden"


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class ConflictError(AppError):
    status_code, code = 409, "conflict"


class InsufficientEvidenceError(AppError):
    status_code, code = 422, "insufficient_evidence"


class AIServiceUnavailableError(AppError):
    status_code, code = 503, "ai_service_unavailable"


def _payload(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app) -> None:  # pragma: no cover - wiring
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=_payload(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_payload(
            "validation_error", "Request validation failed.",
            {"fields": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()[:10]]}))

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error: %s", exc)
        return JSONResponse(status_code=500, content=_payload(
            "internal_error", "An unexpected error occurred. Please try again."))
