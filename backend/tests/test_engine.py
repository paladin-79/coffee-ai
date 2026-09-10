"""Deterministic win evaluation — the core of the challenge."""

from __future__ import annotations

from app.challenge.engine import evaluate
from app.challenge.rules import load_rules
from app.config import REPO_ROOT

RULES = load_rules(REPO_ROOT / "challenge.yaml")


def test_target_recommendation_wins() -> None:
    result = evaluate("iced_milk_coffee", RULES)
    assert result.success is True
    assert result.readable is True
    assert result.recommendation == "iced_milk_coffee"


def test_default_recommendation_loses() -> None:
    result = evaluate("egg_coffee", RULES)
    assert result.success is False
    assert result.readable is True


def test_other_recommendation_loses() -> None:
    result = evaluate("other", RULES)
    assert result.success is False
    assert result.readable is True


def test_value_outside_enum_is_unreadable() -> None:
    result = evaluate("latte", RULES)
    assert result.success is False
    assert result.readable is False
    assert result.recommendation is None


def test_none_is_unreadable() -> None:
    result = evaluate(None, RULES)
    assert result.success is False
    assert result.readable is False


def test_empty_string_is_unreadable() -> None:
    result = evaluate("", RULES)
    assert result.success is False
    assert result.readable is False


def test_target_matches_challenge_yaml() -> None:
    # Guards against a rules edit that silently changes the win condition.
    assert RULES.target == "iced_milk_coffee"
    assert RULES.default == "egg_coffee"
