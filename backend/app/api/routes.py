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
from app.guardrails.adversary import AdversaryTracker
from app.guardrails.engine import GuardrailEngine
from app.guardrails.schemas import GuardrailDecision
from app.llm.schemas import LLMTransportError
from app.store.base import Store
from app.store.schemas import Session
from app.telemetry import events

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
    guardrails = request.app.state.guardrails
    adversary = request.app.state.adversary
    max_attempts = rules.public.max_attempts

    session = await store.get_session(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail=f"session already {session.status}")
    if session.attempts >= max_attempts:
        raise HTTPException(status_code=409, detail="no attempts remaining")

    decision = await guardrails.check(body.prompt)
    if decision.degraded:
        events.guardrail_degraded(
            session_id=session.session_id,
            layer=decision.layer or 0,
            reason="embedding unavailable",
        )
    if decision.blocked:
        return await _handle_block(
            body, decision, session, store, adversary, guardrails, max_attempts
        )

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
        blocked=False,
        status=status,
        attempt=session.attempts,
        attempts_remaining=max(0, max_attempts - session.attempts),
    )


async def _handle_block(
    body: ChatRequest,
    decision: GuardrailDecision,
    session: Session,
    store: Store,
    adversary: AdversaryTracker,
    guardrails: GuardrailEngine,
    max_attempts: int,
) -> ChatResponse:
    """A guardrail stopped the prompt before any model call.

    The block **costs an attempt** (confirmed 2026-09-13, `docs/checklist.md`
    S2): the LLM outage path gives the attempt back because nothing the player
    did caused it, whereas a block is a move that didn't work. Without this,
    probing the guardrails would be free and unlimited — score (S4) and rate
    limiting (S5) don't exist yet, so the attempt cap is the only cost there is.
    """
    assert decision.category is not None
    session = await store.add_attempt(body.session_id)

    update = adversary.on_block(
        category=decision.category,
        seen_categories=session.adversary_categories,
        current_score=session.adversary_score,
        already_flagged=session.flagged,
    )
    session = await store.record_block(
        body.session_id,
        category=decision.category,
        points=update.points,
        flagged=update.newly_flagged,
        embedding=decision.embedding,
    )

    events.guardrail_block(
        session_id=session.session_id,
        category=decision.category,
        layer=decision.layer or 0,
        matched=decision.matched,
        similarity=decision.similarity,
        prompt=body.prompt,
        label=update.label,
    )
    if update.is_signal:
        events.adversary_signal(
            session_id=session.session_id,
            category=decision.category,
            points=update.points,
            total=update.total,
            label=update.label or "unsafe",
        )
    if update.newly_flagged:
        events.session_flagged(
            session_id=session.session_id,
            score=update.total,
            threshold=adversary.flag_threshold,
        )

    status = "active"
    if session.attempts >= max_attempts:
        session = await store.finish(body.session_id, "lost")
        status = "lost"

    # Everything identifying about the block stays on the server side of this
    # return: no category, no matched pattern, no similarity, no adversary state.
    return ChatResponse(
        reply=guardrails.block_message(body.lang),
        recommendation=None,
        success=False,
        blocked=True,
        status=status,
        attempt=session.attempts,
        attempts_remaining=max(0, max_attempts - session.attempts),
    )
