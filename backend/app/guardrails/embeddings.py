"""Sentence embeddings for guardrail layer 2.

Layer 2 exists because ``PREFERENCE_DECLARATION`` has no vocabulary to match on
— "tôi không thích cà phê trứng" and "xin đừng nhắc tới món trứng" share almost
no words but are the same move. Keyword rules cannot see that; vectors can.

Production uses :class:`OpenAIEmbedder` (``text-embedding-3-small`` through the
endpoint already configured for chat). That keeps the image small and costs
roughly $0.000001 per prompt, at the price of one network round trip on the
attempt path — which is why :meth:`~app.guardrails.engine.GuardrailEngine.check`
fails **open** when this layer errors.

Two offline implementations exist for tests; neither is ever wired in
production. See ``docs/architecture.md`` -> Guardrails.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.guardrails.normalize import normalize
from app.guardrails.schemas import Vector


class EmbeddingError(RuntimeError):
    """The vectors could not be produced. Layer 2 is skipped, not failed."""


class Embedder(ABC):
    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        """Return one **unit-length** vector per input, in the same order.

        Raises :class:`EmbeddingError` if the call did not complete.
        """


def cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity. Both arguments must already be unit-length, which
    every :class:`Embedder` here guarantees, so this is just a dot product."""
    return sum(x * y for x, y in zip(a, b))


def _unit(values: Sequence[float]) -> Vector:
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return tuple(values)
    return tuple(v / norm for v in values)


class OpenAIEmbedder(Embedder):
    """Any endpoint speaking the OpenAI embeddings API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = "text-embedding-3-small",
        timeout: float = 10.0,
        max_retries: int = 1,
    ) -> None:
        # Imported here so the offline embedders stay importable without the SDK.
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries
        )
        self._model = model

    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        from openai import OpenAIError

        if not texts:
            return []
        try:
            resp = await self._client.embeddings.create(
                model=self._model, input=list(texts)
            )
        except OpenAIError as exc:
            raise EmbeddingError(str(exc)) from exc
        # The API preserves input order, but it also returns `index` — sort by it
        # rather than trusting the order, since a block decision rides on it.
        ordered = sorted(resp.data, key=lambda item: item.index)
        return [_unit(item.embedding) for item in ordered]


class HashingEmbedder(Embedder):
    """Deterministic, offline, no dependencies — character n-grams hashed into a
    fixed-width vector.

    This is **not** a semantic model. It separates near-duplicates from
    unrelated text, which is exactly what an offline guardrail-balance run
    needs, but it cannot see that two differently-worded sentences mean the same
    thing. Tests that need real semantics are marked ``live``.
    """

    def __init__(self, *, dim: int = 512, ngram: int = 4) -> None:
        self._dim = dim
        self._ngram = ngram

    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> Vector:
        cleaned = normalize(text)
        counts = [0.0] * self._dim
        for i in range(max(1, len(cleaned) - self._ngram + 1)):
            gram = cleaned[i : i + self._ngram]
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=4).digest()
            counts[int.from_bytes(digest, "big") % self._dim] += 1.0
        return _unit(counts)


class StaticEmbedder(Embedder):
    """Returns vectors from a lookup table. For unit tests that need to pin an
    exact similarity; unknown text raises, so a test can't silently drift."""

    def __init__(self, table: dict[str, Sequence[float]]) -> None:
        self._table = {text: _unit(vec) for text, vec in table.items()}

    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        try:
            return [self._table[t] for t in texts]
        except KeyError as exc:
            raise EmbeddingError(f"no vector registered for {exc.args[0]!r}") from exc


class FailingEmbedder(Embedder):
    """Always raises — used to prove layer 2 fails open."""

    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        raise EmbeddingError("simulated embedding outage")
