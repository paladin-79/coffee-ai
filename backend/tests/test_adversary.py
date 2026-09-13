"""Adversary tracking — the operator-only signal.

The invariants that matter most are negative ones: naive play scores nothing,
spamming one technique scores nothing extra, and none of this ever reaches the
player. The last one is asserted in ``test_api.py``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from app.challenge.rules import AdversaryRules, RulesError, load_rules
from app.config import REPO_ROOT
from app.guardrails.adversary import AdversaryTracker

WEIGHTS = {"PROMPT_INJECTION": 3, "SYSTEM_PROMPT_EXTRACTION": 3, "SENSITIVE_REQUEST": 2}

DEFAULTS = {
    "enabled": True,
    "signal_categories": WEIGHTS,
    "count_distinct_only": True,
    "flag_threshold": 6,
    "log_label": "unsafe",
}


def tracker(**overrides) -> AdversaryTracker:  # type: ignore[no-untyped-def]
    return AdversaryTracker(AdversaryRules(**{**DEFAULTS, **overrides}))


def block(t: AdversaryTracker, category: str, *, seen=(), score=0, flagged=False):  # type: ignore[no-untyped-def]
    return t.on_block(
        category=category,
        seen_categories=seen,
        current_score=score,
        already_flagged=flagged,
    )


# --- naive categories score nothing -----------------------------------------


@pytest.mark.parametrize(
    "category",
    ["DIRECT_TARGET_REQUEST", "ALLERGY_WORKAROUND", "PREFERENCE_DECLARATION"],
)
def test_naive_category_scores_zero_and_raises_no_signal(category: str) -> None:
    update = block(tracker(), category)
    assert update.points == 0
    assert update.is_signal is False
    assert update.label is None
    assert update.newly_flagged is False


def test_naive_blocks_never_accumulate() -> None:
    t = tracker()
    score = 0
    for _ in range(20):
        score = block(t, "DIRECT_TARGET_REQUEST", score=score).total
    assert score == 0


# --- signal categories score their configured weight ------------------------


@pytest.mark.parametrize("category,weight", sorted(WEIGHTS.items()))
def test_signal_category_scores_its_weight(category: str, weight: int) -> None:
    update = block(tracker(), category)
    assert update.is_signal is True
    assert update.points == weight
    assert update.total == weight
    assert update.label == "unsafe"


def test_points_add_to_the_running_total() -> None:
    update = block(tracker(), "SENSITIVE_REQUEST", score=3, seen=("PROMPT_INJECTION",))
    assert update.total == 5


# --- count_distinct_only -----------------------------------------------------


def test_a_repeated_category_still_signals_but_scores_nothing() -> None:
    """Spamming one technique must not inflate the score — but the event still
    fires, so the operator sees the technique was used again."""
    update = block(tracker(), "PROMPT_INJECTION", seen=("PROMPT_INJECTION",), score=3)
    assert update.is_signal is True
    assert update.label == "unsafe"
    assert update.points == 0
    assert update.total == 3


def test_distinct_only_off_accumulates_every_hit() -> None:
    update = block(
        tracker(count_distinct_only=False),
        "PROMPT_INJECTION",
        seen=("PROMPT_INJECTION",),
        score=3,
    )
    assert update.points == 3
    assert update.total == 6


def test_three_distinct_techniques_reach_the_default_threshold() -> None:
    """The threshold is tuned so one technique is not enough, but a player
    working through several is flagged."""
    t = tracker()
    seen: list[str] = []
    score, flagged = 0, False
    for category in ("PROMPT_INJECTION", "SENSITIVE_REQUEST", "SYSTEM_PROMPT_EXTRACTION"):
        update = block(t, category, seen=seen, score=score, flagged=flagged)
        seen.append(category)
        score, flagged = update.total, flagged or update.newly_flagged
    assert score == 8
    assert flagged is True


# --- flagging ----------------------------------------------------------------


def test_one_naive_technique_does_not_flag() -> None:
    assert block(tracker(), "PROMPT_INJECTION").newly_flagged is False


def test_flag_fires_exactly_once() -> None:
    """``session_flagged`` is a one-per-session event; a session already over
    the line must not re-raise it on every later block."""
    crossing = block(tracker(), "SYSTEM_PROMPT_EXTRACTION", score=3)
    assert crossing.total == 6
    assert crossing.newly_flagged is True

    after = block(
        tracker(),
        "SENSITIVE_REQUEST",
        seen=("PROMPT_INJECTION", "SYSTEM_PROMPT_EXTRACTION"),
        score=6,
        flagged=True,
    )
    assert after.total == 8
    assert after.newly_flagged is False


def test_flagging_is_inclusive_of_the_threshold() -> None:
    assert block(tracker(flag_threshold=3), "PROMPT_INJECTION").newly_flagged is True
    assert block(tracker(flag_threshold=4), "PROMPT_INJECTION").newly_flagged is False


# --- kill switch -------------------------------------------------------------


def test_disabled_tracking_scores_nothing_at_all() -> None:
    update = block(tracker(enabled=False), "PROMPT_INJECTION")
    assert (update.is_signal, update.points, update.newly_flagged) == (False, 0, False)


def test_an_unconfigured_category_is_treated_as_naive() -> None:
    update = block(tracker(signal_categories={}), "PROMPT_INJECTION")
    assert update.is_signal is False
    assert update.points == 0


# --- the shipped configuration ----------------------------------------------


def test_challenge_yaml_weights_match_the_design_doc() -> None:
    rules = load_rules(REPO_ROOT / "challenge.yaml")
    assert rules.adversary_tracking.signal_categories == WEIGHTS
    assert rules.adversary_tracking.count_distinct_only is True
    assert rules.adversary_tracking.visibility == "operator_only"


def test_signal_categories_must_name_real_guardrails() -> None:
    """A typo here would silently mean "this attack is worth nothing", so the
    rules loader rejects it at startup rather than at the event."""
    raw = yaml.safe_load((REPO_ROOT / "challenge.yaml").read_text(encoding="utf-8"))
    raw["adversary_tracking"]["signal_categories"] = {"PROMT_INJECTION": 3}

    with tempfile.TemporaryDirectory() as tmp:
        broken = Path(tmp) / "challenge.yaml"
        broken.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
        with pytest.raises(RulesError, match="do not exist under guardrails.categories"):
            load_rules(broken)
