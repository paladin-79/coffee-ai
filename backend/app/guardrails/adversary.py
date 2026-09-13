"""Per-session adversary signal — an operator-only measure of intent.

Scoring answers *how well did this player do?*. This answers a different
question: *is this player attacking the model rather than playing the game?*

Reaching for `sua da`, an egg allergy, or "tôi chỉ uống…" is naive play and
scores nothing. Trying to override the system prompt, extract it, or steer the
model somewhere unrelated is a different activity, and those are the people
worth talking to after the event.

Hard rules, from ``docs/challenge-design.md`` -> Adversary tracking:

* never shown to the player, in any form, including indirectly;
* never added to or subtracted from the game score;
* never present in an API response.

This module is pure: it reads config and the session's current counters and
returns what should change. Persisting that is ``store/``'s job, reporting it is
``telemetry/``'s.
"""

from __future__ import annotations

from collections.abc import Collection

from app.challenge.rules import AdversaryRules
from app.guardrails.schemas import AdversaryUpdate


class AdversaryTracker:
    def __init__(self, rules: AdversaryRules) -> None:
        self._rules = rules

    @property
    def flag_threshold(self) -> int:
        return self._rules.flag_threshold

    def on_block(
        self,
        *,
        category: str,
        seen_categories: Collection[str],
        current_score: int,
        already_flagged: bool,
    ) -> AdversaryUpdate:
        """Weigh one guardrail block.

        ``seen_categories`` are the signal categories this session has already
        triggered; with ``count_distinct_only`` a repeat still counts as a signal
        for logging but adds no points, so spamming one technique cannot inflate
        the score.
        """
        quiet = AdversaryUpdate(
            is_signal=False,
            points=0,
            label=None,
            total=current_score,
            newly_flagged=False,
        )
        if not self._rules.enabled:
            return quiet

        weight = self._rules.signal_categories.get(category)
        if weight is None:
            return quiet  # naive category — playing the game, not attacking it

        repeat = self._rules.count_distinct_only and category in seen_categories
        points = 0 if repeat else weight
        total = current_score + points
        return AdversaryUpdate(
            is_signal=True,
            points=points,
            label=self._rules.log_label,
            total=total,
            newly_flagged=not already_flagged and total >= self._rules.flag_threshold,
        )
