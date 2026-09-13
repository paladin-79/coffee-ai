"""Named events the rest of the app emits.

S2 needs three facts on the record — which category really fired, which blocks
look adversarial, and when a session crosses the flag threshold — but S3 owns
the actual pipeline (OTel spans, structlog JSON, Loki). So this module is the
seam: call sites use these names now, and S3 swaps the sink underneath without
touching a single caller.

Every event carries ``session_id``. Prompt text is included only when
``LOG_PROMPTS`` is on, so the redaction path S3 has to verify already exists.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger("coffee_ai.events")


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "event": getattr(record, "event", record.getMessage()),
                **getattr(record, "fields", {}),
            },
            ensure_ascii=False,
        )


def configure() -> None:
    """Make events visible on stdout (``docker compose logs``). Python's root
    logger defaults to WARNING and uvicorn only configures its own loggers, so
    without this every event here is silently dropped. Idempotent. S3 replaces
    it with structlog + the OTel exporter."""
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonLineFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True  # keep pytest's caplog working


#: Names are stable — S3 dashboards and Loki queries key off them.
GUARDRAIL_BLOCK = "guardrail_block"
GUARDRAIL_DEGRADED = "guardrail_degraded"
ADVERSARY_SIGNAL = "adversary_signal"
SESSION_FLAGGED = "session_flagged"

REDACTED = "[redacted]"


def emit(event: str, **fields: Any) -> None:
    """One structured line. Fields live under a single ``fields`` key so they
    can never collide with a :class:`logging.LogRecord` attribute."""
    logger.info(event, extra={"event": event, "fields": fields})


def _prompt_field(prompt: str) -> str:
    return prompt if get_settings().log_prompts else REDACTED


def guardrail_block(
    *,
    session_id: str,
    category: str,
    layer: int,
    matched: str | None,
    similarity: float | None,
    prompt: str,
    label: str | None = None,
) -> None:
    """A prompt was stopped. ``category`` is recorded here and *only* here —
    the response the player gets names no category."""
    emit(
        GUARDRAIL_BLOCK,
        session_id=session_id,
        category=category,
        layer=layer,
        matched=matched,
        similarity=similarity,
        prompt=_prompt_field(prompt),
        label=label,
    )


def guardrail_degraded(*, session_id: str, layer: int, reason: str) -> None:
    """A layer could not be evaluated and the prompt was let through. Worth an
    alert in S3: it is the one path where a block silently does not happen."""
    emit(GUARDRAIL_DEGRADED, session_id=session_id, layer=layer, reason=reason)


def adversary_signal(
    *, session_id: str, category: str, points: int, total: int, label: str
) -> None:
    """A signal-category block. ``points`` is 0 for a repeat under
    ``count_distinct_only``; the event still fires so the technique is visible."""
    emit(
        ADVERSARY_SIGNAL,
        session_id=session_id,
        category=category,
        points=points,
        total=total,
        label=label,
    )


def session_flagged(*, session_id: str, score: int, threshold: int) -> None:
    """The session crossed ``flag_threshold``. Fires once per session, and feeds
    the S3 "Potential adversaries" panel."""
    emit(SESSION_FLAGGED, session_id=session_id, score=score, threshold=threshold)
