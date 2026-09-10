"""Deterministic win evaluation.

Reads the model's ``recommendation`` enum and nothing else — never the prose.
A value the model returns that isn't one of ``recommendation_enum`` is treated
as unreadable output, not as a loss with a guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.challenge.rules import Rules


@dataclass(frozen=True)
class Evaluation:
    success: bool
    #: The enum value the model returned, or ``None`` if it wasn't readable.
    recommendation: str | None
    #: ``False`` when the model's output could not be mapped to the enum.
    readable: bool


def evaluate(recommendation: str | None, rules: Rules) -> Evaluation:
    if recommendation not in rules.recommendation_enum:
        return Evaluation(success=False, recommendation=None, readable=False)
    return Evaluation(
        success=recommendation == rules.target,
        recommendation=recommendation,
        readable=True,
    )
