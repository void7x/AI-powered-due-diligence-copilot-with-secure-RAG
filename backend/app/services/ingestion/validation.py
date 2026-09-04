"""Upload validation: extension + MIME + magic bytes + size + filename sanitizing."""
from __future__ import annotations

import re
import unicodedata

from app.core.config import Settings
from app.core.errors import BadRequestError, UnsupportedFileTypeError

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "application/octet-stream", ""},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation",
             "application/octet-stream", ""},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             "application/octet-stream", ""},
    "csv": {"text/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream", ""},
    "txt": {"text/plain", "text/markdown", "application/octet-stream", ""},
}

_MAGIC: dict[str, bytes] = {
    "pdf": b"%PDF",
    "docx": b"PK", "pptx": b"PK", "xlsx": b"PK",
}


def sanitize_filename(filename: str) -> str:
    """Strip paths/unsafe chars; never trust client filenames (no traversal)."""
    name = unicodedata.normalize("NFKC", filename or "upload")
    name = re.sub(r"[^\w.\- ]+", "_", name).strip(". ")
    name = re.sub(r"\s+", "_", name)
    return (name or "upload")[:180]


def detect_extension(safe_name: str) -> str:
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    return ext


def validate_upload(filename: str, content_type: str | None, size_bytes: int,
                    settings: Settings) -> tuple[str, str]:
    """Returns (safe_filename, extension). Raises AppError on any violation."""
    if size_bytes <= 0:
        raise BadRequestError("Uploaded file is empty.")
    if size_bytes > settings.max_upload_bytes:
        raise BadRequestError(
            f"File exceeds the {settings.max_upload_mb} MB upload limit.",
            code="file_too_large", status_code=413)
    safe_name = sanitize_filename(filename)
    ext = detect_extension(safe_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")
    if content_type and content_type not in ALLOWED_EXTENSIONS[ext]:
        raise UnsupportedFileTypeError(
            f"MIME type '{content_type}' is not accepted for '.{ext}' files.",
            details={"received": content_type})
    return safe_name, ext


def validate_magic_bytes(ext: str, head: bytes) -> None:
    expected = _MAGIC.get(ext)
    if expected and not head.startswith(expected):
        raise BadRequestError(
            f"File content does not look like a valid {ext.upper()} document.",
            code="malformed_document", status_code=422)
