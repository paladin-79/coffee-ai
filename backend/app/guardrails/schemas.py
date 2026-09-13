"""Types crossing the ``guardrails/`` boundary.

The route handler sees a :class:`GuardrailDecision` and nothing else. Note what
is on it: ``category`` is for the log, never for the player. Leaking it turns
the guessing game into a lookup table.
"""

from __future__ import annotations

from dataclasses import dataclass

Vector = tuple[float, ...]


@dataclass(frozen=True)
class GuardrailDecision:
    blocked: bool
    #: Which category fired. **Operator-only** — never put this in a response.
    category: str | None = None
    #: 1 = keyword/regex, 2 = embedding similarity.
    layer: int | None = None
    #: The pattern (layer 1) or example sentence (layer 2) that fired, for logs.
    matched: str | None = None
    #: Cosine similarity that triggered a layer-2 block.
    similarity: float | None = None
    #: The prompt's embedding, present only when layer 2 ran and blocked. S3
    #: bypass detection compares later passing prompts against these.
    embedding: Vector | None = None
    #: A layer could not be evaluated and was skipped (fail open). Never set
    #: together with ``blocked``. The route turns this into ``guardrail_degraded``.
    degraded: bool = False


#: The common case, allocated once.
PASS = GuardrailDecision(blocked=False)
DEGRADED = GuardrailDecision(blocked=False, layer=2, degraded=True)


@dataclass(frozen=True)
class AdversaryUpdate:
    """What one block means for the session's operator-only adversary score."""

    #: The category carries an adversary weight — log it as ``unsafe`` even when
    #: it scores 0 because ``count_distinct_only`` already counted it.
    is_signal: bool
    #: Points to add to the session total for this block. Often 0.
    points: int
    #: ``adversary_tracking.log_label``, set only for a signal category.
    label: str | None
    #: The session total after adding ``points``.
    total: int
    #: This block is what pushed the session over ``flag_threshold``.
    newly_flagged: bool
