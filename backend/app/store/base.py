"""Persistence interface.

S1–S3 use :class:`~app.store.memory.InMemoryStore`. S4 swaps in a Redis
implementation behind this same interface — so nothing above ``store/`` may
import a concrete store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.store.schemas import Session, SessionStatus


class SessionNotFound(KeyError):
    """No session with that id."""


class Store(ABC):
    @abstractmethod
    async def create_session(self, *, player_id: str, nickname: str | None) -> Session:
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None:
        ...

    @abstractmethod
    async def add_attempt(self, session_id: str) -> Session:
        """Increment the attempt counter and return the updated session."""

    @abstractmethod
    async def finish(self, session_id: str, status: SessionStatus) -> Session:
        """Mark the session ``won`` or ``lost`` and stamp ``finished_at``."""

    @abstractmethod
    async def record_block(
        self,
        session_id: str,
        *,
        category: str,
        points: int,
        flagged: bool,
        embedding: Sequence[float] | None = None,
    ) -> Session:
        """Record one guardrail block against the session.

        Deliberately dumb: the caller has already decided how many ``points`` the
        block is worth and whether the session is now ``flagged``. Weighing is
        ``guardrails/``'s job (it owns the config); this layer only persists.
        """
