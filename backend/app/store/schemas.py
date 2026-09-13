"""Session model. One row per player attempt at the challenge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["active", "won", "lost"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(BaseModel):
    session_id: str
    player_id: str
    nickname: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    attempts: int = 0
    status: SessionStatus = "active"

    # --- Guardrails (S2) ----------------------------------------------------
    #: How many attempts were stopped before reaching the LLM. S4 prices these
    #: into the score via ``scoring.guardrail_block_penalty``.
    guardrail_blocks: int = 0

    # --- Adversary tracking (S2) — OPERATOR ONLY ----------------------------
    # None of the four fields below may appear in an API response, on the
    # leaderboard, or anywhere the player can see. See docs/challenge-design.md.
    adversary_score: int = 0
    #: Distinct categories this session has triggered, in first-hit order. Feeds
    #: ``count_distinct_only``; naive categories land here too, which is useful
    #: context for an operator even though they score nothing.
    #: A list rather than a set because S4 persists this to Redis as JSON.
    adversary_categories: list[str] = Field(default_factory=list)
    flagged: bool = False
    #: Embeddings of prompts blocked at layer 2. S3 bypass detection scores each
    #: later *passing* prompt against these to catch a rephrased retry.
    blocked_embeddings: list[list[float]] = Field(default_factory=list, repr=False)

    @property
    def elapsed_seconds(self) -> float:
        """Server-authoritative. Never trust a client clock (see backend/README)."""
        end = self.finished_at or _utcnow()
        return (end - self.created_at).total_seconds()
