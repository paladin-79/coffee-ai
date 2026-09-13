"""The balance test: do the guardrails block the shortcuts *without* breaking
the game?

Every guardrail change trades one against the other. Tightening a pattern to
catch a new shortcut is easy; noticing that it now also blocks a legitimate way
to win is not. So all three populations run in one file:

    forbidden.yaml   must be BLOCKED, in the right category
    solutions.yaml   must PASS  — these are the intended ways to win
    neutral.yaml     must PASS  — ordinary players must never see a block
    challenge.yaml   must PASS  — every solution_paths[].reference_prompt

A false positive here is worse than a false negative. A missed shortcut makes
the game slightly easier; a blocked solution path makes it unwinnable, and the
player is told only "try another approach".

**Run this after every edit to `guardrails/` or `challenge.yaml`.**

Layer 2 offline
---------------
Layer 2 needs an embedding model. The default run uses :class:`HashingEmbedder`
— deterministic, offline, no API key — which recognises near-duplicates but not
genuine paraphrase. It proves the *mechanism* and catches pattern regressions in
CI; it does not prove that layer 2 generalises.

For that, set ``RUN_LIVE_TESTS=1`` (plus ``LLM_API_KEY``) and the same assertions
re-run against the real embedder and the real threshold from ``challenge.yaml``.
Do that before an event, not on every commit — it costs an API call per prompt.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from app.challenge.rules import Rules, load_rules
from app.config import REPO_ROOT, get_settings
from app.guardrails.embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from app.guardrails.engine import GuardrailEngine

FIXTURES = Path(__file__).parent / "fixtures"

#: The hashing embedder's similarity scale is not the real model's, so the
#: offline run carries its own threshold. The live run uses challenge.yaml's.
OFFLINE_THRESHOLD = 0.72

LIVE = os.getenv("RUN_LIVE_TESTS") == "1"
live_only = pytest.mark.skipif(
    not LIVE, reason="set RUN_LIVE_TESTS=1 to hit the real embedder (key from .env)"
)


def _load(name: str) -> list[dict]:
    raw = yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8")) or []
    return [item if isinstance(item, dict) else {"prompt": item} for item in raw]


FORBIDDEN = _load("forbidden.yaml")
SOLUTIONS = _load("solutions.yaml")
NEUTRAL = _load("neutral.yaml")


@pytest.fixture(scope="module")
def rules() -> Rules:
    return load_rules(REPO_ROOT / "challenge.yaml")


def _engine(rules: Rules, embedder: Embedder, *, threshold: float | None) -> GuardrailEngine:
    guardrails = rules.guardrails
    if threshold is not None:
        guardrails = guardrails.model_copy(
            update={
                "categories": {
                    name: category.model_copy(update={"similarity_threshold": threshold})
                    if category.layer == 2
                    else category
                    for name, category in guardrails.categories.items()
                }
            }
        )
    return GuardrailEngine(guardrails, embedder)


@pytest.fixture(scope="module")
def engine(rules: Rules) -> GuardrailEngine:
    return _engine(rules, HashingEmbedder(), threshold=OFFLINE_THRESHOLD)


@pytest.fixture(scope="module")
def live_engine(rules: Rules) -> GuardrailEngine:
    # Same settings path as the backend, so the repo-root .env is honoured.
    settings = get_settings()
    if not settings.llm_api_key:
        pytest.skip("LLM_API_KEY not set (env or .env)")
    return _engine(
        rules,
        OpenAIEmbedder(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.embedding_model,
        ),
        threshold=None,
    )


# --- the shortcuts must close ------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", FORBIDDEN, ids=[f"{c['category']}-{i}" for i, c in enumerate(FORBIDDEN)]
)
async def test_forbidden_prompt_is_blocked(case: dict, engine: GuardrailEngine) -> None:
    decision = await engine.check(case["prompt"])
    assert decision.blocked, f"shortcut got through: {case['prompt']!r}"
    assert decision.category == case["category"], (
        f"{case['prompt']!r} blocked as {decision.category}, "
        f"expected {case['category']} — check category order in challenge.yaml"
    )


def test_every_category_has_at_least_five_cases(rules: Rules) -> None:
    """Exit criterion: six categories live, ≥ 5 test cases each."""
    counts = {name: 0 for name in rules.guardrails.categories}
    for case in FORBIDDEN:
        counts[case["category"]] += 1
    assert len(counts) == 6
    thin = {name: n for name, n in counts.items() if n < 5}
    assert not thin, f"categories with fewer than 5 fixtures: {thin}"


# --- the game must stay winnable --------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SOLUTIONS, ids=range(len(SOLUTIONS)))
async def test_solution_prompt_still_passes(case: dict, engine: GuardrailEngine) -> None:
    decision = await engine.check(case["prompt"])
    assert not decision.blocked, (
        f"a solution path is blocked by {decision.category} "
        f"(matched {decision.matched!r}): {case['prompt']!r}"
    )


@pytest.mark.asyncio
async def test_every_reference_prompt_still_passes(
    rules: Rules, engine: GuardrailEngine
) -> None:
    """The canonical prompt for each ``solution_paths[]`` entry, straight from
    the rules file rather than the fixtures — these are the paths S0 measured."""
    for path in rules.solution_paths:
        decision = await engine.check(path.reference_prompt)
        assert not decision.blocked, (
            f"solution path {path.id!r} is blocked by {decision.category} "
            f"(matched {decision.matched!r})"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", NEUTRAL, ids=range(len(NEUTRAL)))
async def test_neutral_prompt_still_passes(case: dict, engine: GuardrailEngine) -> None:
    decision = await engine.check(case["prompt"])
    assert not decision.blocked, (
        f"an ordinary prompt is blocked by {decision.category} "
        f"(matched {decision.matched!r}): {case['prompt']!r}"
    )


# --- same three populations, real embedding model ----------------------------


@live_only
@pytest.mark.asyncio
async def test_live_balance(live_engine: GuardrailEngine) -> None:
    """One run over all three populations against the real embedder and the
    real ``similarity_threshold``. This is the one that says whether layer 2
    actually generalises; the offline run only says the wiring works."""
    failures: list[str] = []

    for case in FORBIDDEN:
        decision = await live_engine.check(case["prompt"])
        if not decision.blocked:
            failures.append(f"NOT BLOCKED [{case['category']}] {case['prompt']!r}")
        elif decision.category != case["category"]:
            failures.append(
                f"WRONG CATEGORY {decision.category} != {case['category']} "
                f"{case['prompt']!r}"
            )

    for case in SOLUTIONS + NEUTRAL:
        decision = await live_engine.check(case["prompt"])
        if decision.blocked:
            failures.append(
                f"FALSE POSITIVE [{decision.category} "
                f"sim={decision.similarity}] {case['prompt']!r}"
            )

    assert not failures, "\n".join(failures)
