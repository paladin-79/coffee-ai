"""Request and response shapes for the public API.

Route handlers deal only in these. No game logic here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=40)


class CreateSessionResponse(BaseModel):
    session_id: str
    player_id: str
    max_attempts: int
    attempts_remaining: int


class ChatRequest(BaseModel):
    session_id: str
    prompt: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    #: The enum value the model landed on, or ``None`` if its answer was unreadable.
    recommendation: str | None
    success: bool
    #: ``active`` | ``won`` | ``lost``
    status: str
    #: This attempt's 1-based number.
    attempt: int
    attempts_remaining: int
