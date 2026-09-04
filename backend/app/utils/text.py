"""Text utilities shared by extraction, chunking and retrieval."""
from __future__ import annotations

import re

_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[.'-][A-Za-z0-9]+)*")
_STOPWORDS = {
    "the", "and", "for", "with", "what", "was", "were", "are", "is", "of", "to",
    "in", "on", "a", "an", "did", "does", "how", "why", "which", "who", "that",
    "this", "from", "by", "at", "as", "be", "has", "have", "had", "it", "its",
}


def normalize_ws(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = _WS_RE.sub(" ", text)
    return _MULTI_NL.sub("\n\n", text).strip()


def approx_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token). Keeps us dependency-free."""
    return max(1, len(text) // 4)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def keywords(text: str, min_len: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokenize(text):
        if len(tok) >= min_len and tok not in _STOPWORDS and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\u201c(])", text)
    return [p.strip() for p in parts if p.strip()]


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rsplit(" ", 1)[0] + "…"


def excerpt_around(text: str, needle: str, width: int = 320) -> str:
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return truncate(text, width)
    start = max(0, idx - width // 3)
    return ("…" if start else "") + text[start : start + width].strip() + ("…" if start + width < len(text) else "")


def pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"
