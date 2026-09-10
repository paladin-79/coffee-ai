"""The four S1 endpoints.

    POST /api/session    create a session, start the server-side timer
    POST /api/chat       submit one attempt
    GET  /api/challenge  public rules only
    GET  /api/health     liveness

Handlers pull the rules / store / provider off ``request.app.state``, which
``main.create_app`` populates in the lifespan handler.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
)
from app.challenge.engine import evaluate
from app.llm.schemas import LLMTransportError

router = APIRouter(prefix="/api")

# Shown when the model's answer couldn't be mapped to the enum and it gave us
# no usable prose either. Deliberately not an error page — the attempt counted.
UNREADABLE_REPLY = (
    "Xin lỗi, mình chưa hiểu rõ câu hỏi lắm. Bạn thử diễn đạt lại theo cách khác nhé."
)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/challenge")
async def challenge(request: Request) -> dict:
    return request.app.state.rules.public_payload


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest, request: Request
) -> CreateSessionResponse:
    rules = request.app.state.rules
    store = request.app.state.store

    session = await store.create_session(
        player_id=f"player-{uuid.uuid4().hex[:8]}",
        nickname=body.nickname,
    )
    return CreateSessionResponse(
        session_id=session.session_id,
        player_id=session.player_id,
        max_attempts=rules.public.max_attempts,
        attempts_remaining=rules.public.max_attempts,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    rules = request.app.state.rules
    store = request.app.state.store
    provider = request.app.state.llm
    max_attempts = rules.public.max_attempts

    session = await store.get_session(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail=f"session already {session.status}")
    if session.attempts >= max_attempts:
        raise HTTPException(status_code=409, detail="no attempts remaining")

    # Transport failure: the attempt is not consumed, the player retries free.
    try:
        llm_response = await provider.complete(rules.system_prompt, body.prompt)
    except LLMTransportError:
        raise HTTPException(
            status_code=503,
            detail="the AI is unavailable right now — this attempt was not counted, try again",
        )

    session = await store.add_attempt(body.session_id)
    result = evaluate(llm_response.recommendation, rules)

    if result.readable:
        reply = llm_response.reply
    else:
        reply = llm_response.reply or UNREADABLE_REPLY

    status = "active"
    if result.success:
        session = await store.finish(body.session_id, "won")
        status = "won"
    elif session.attempts >= max_attempts:
        session = await store.finish(body.session_id, "lost")
        status = "lost"

    return ChatResponse(
        reply=reply,
        recommendation=result.recommendation,
        success=result.success,
        status=status,
        attempt=session.attempts,
        attempts_remaining=max(0, max_attempts - session.attempts),
    )
