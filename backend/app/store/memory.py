"""In-memory session store. Fine for S1–S3; a restart wipes it."""

from __future__ import annotations

import asyncio
import uuid

from app.store.base import SessionNotFound, Store
from app.store.schemas import Session, SessionStatus, _utcnow


class InMemoryStore(Store):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, *, player_id: str, nickname: str | None) -> Session:
        session = Session(
            session_id=str(uuid.uuid4()),
            player_id=player_id,
            nickname=nickname or None,
        )
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def add_attempt(self, session_id: str) -> Session:
        async with self._lock:
            session = self._require(session_id)
            session.attempts += 1
            return session

    async def finish(self, session_id: str, status: SessionStatus) -> Session:
        async with self._lock:
            session = self._require(session_id)
            session.status = status
            session.finished_at = _utcnow()
            return session

    def _require(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFound(session_id) from exc
