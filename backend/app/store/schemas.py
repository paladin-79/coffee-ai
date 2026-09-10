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

    @property
    def elapsed_seconds(self) -> float:
        """Server-authoritative. Never trust a client clock (see backend/README)."""
        end = self.finished_at or _utcnow()
        return (end - self.created_at).total_seconds()
