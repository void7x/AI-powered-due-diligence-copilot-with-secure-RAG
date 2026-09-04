"""Configurable embedding service.

* openai  - OpenAI embeddings API (model from env)
* offline - deterministic feature-hashing embedder so the whole pipeline runs
            with zero API keys / zero network (dev, tests, CI).

Vector dimensionality comes from settings (EMBEDDING_DIM) and is applied
consistently at storage time.
"""
from __future__ import annotations

import hashlib
import math
import re

from app.core.cache import TTLCache
from app.core.config import Settings
from app.core.logging import get_logger
from app.utils.text import tokenize

log = get_logger("app.embeddings")


class BaseEmbedder:
    name = "base"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbedder(BaseEmbedder):
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: int = 60) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self._cache: TTLCache = TTLCache(max_size=1024, ttl_seconds=3600)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), 100):
            batch = [t[:8000] for t in texts[start : start + 100]]
            resp = self._client.embeddings.create(model=self.model, input=batch)
            out.extend(d.embedding for d in resp.data)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashingEmbedder(BaseEmbedder):
    """Deterministic bag-of-features hashing embedding (offline mode).

    Captures tokens + character trigrams so lexical similarity is preserved;
    suitable for development/demo and deterministic tests, not for production
    semantic quality.
    """

    name = "offline"

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _index(self, feature: str) -> int:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = tokenize(text)
        for tok in toks:
            vec[self._index(f"w:{tok}")] += 1.0
        lower = re.sub(r"\s+", " ", text.lower())
        for i in range(len(lower) - 2):
            vec[self._index(f"g:{lower[i : i + 3]}")] += 0.35
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)


def get_embedding_service(settings: Settings) -> BaseEmbedder:
    provider = settings.embedding_provider
    if provider == "offline":
        return HashingEmbedder(settings.embedding_dim)
    if provider == "openai" or (provider == "auto" and settings.openai_api_key):
        try:
            return OpenAIEmbedder(settings.openai_api_key or "", settings.openai_embedding_model)
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI embedder unavailable (%s); falling back to offline", exc)
    return HashingEmbedder(settings.embedding_dim)
