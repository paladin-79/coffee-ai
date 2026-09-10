"""Parsing the model's JSON body — must never raise, whatever the model returns."""

from __future__ import annotations

from app.llm.parsing import parse_completion_body


def test_well_formed_body() -> None:
    raw = '{"recommendation": "egg_coffee", "reply": "Bạn nên thử cà phê trứng."}'
    assert parse_completion_body(raw) == ("egg_coffee", "Bạn nên thử cà phê trứng.")


def test_malformed_json_yields_none() -> None:
    assert parse_completion_body("this is not json") == (None, "")


def test_missing_recommendation_keeps_reply() -> None:
    assert parse_completion_body('{"reply": "hello"}') == (None, "hello")


def test_non_string_recommendation_is_none() -> None:
    assert parse_completion_body('{"recommendation": 123, "reply": "x"}') == (None, "x")


def test_json_that_is_not_an_object() -> None:
    assert parse_completion_body('["egg_coffee"]') == (None, "")


def test_empty_body() -> None:
    assert parse_completion_body("") == (None, "")
