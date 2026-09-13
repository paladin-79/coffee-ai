"""Request and response shapes for the public API.

Route handlers deal only in these. No game logic here.
"""

from __future__ import annotations

from typing import Literal

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
    #: Which ``block_message_*`` to use if a guardrail fires.
    lang: Literal["vi", "en"] = "vi"


class ChatResponse(BaseModel):
    reply: str
    #: The enum value the model landed on, or ``None`` if its answer was
    #: unreadable — also ``None`` on a guardrail block, where no model ran.
    recommendation: str | None
    success: bool
    #: A guardrail stopped this prompt. Which guardrail is **never** disclosed:
    #: the category is operator-only telemetry, and naming it would turn the
    #: challenge into a lookup table. ``reply`` holds the vague block message.
    blocked: bool = False
    #: ``active`` | ``won`` | ``lost``
    status: str
    #: This attempt's 1-based number.
    attempt: int
    attempts_remaining: int
