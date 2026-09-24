"""The decoy prompts must actually be traps.

``public.decoy_prompts`` is shown to every player as a suggestion. The whole
point is that taking the suggestion trips a guardrail. Two things can quietly
break that:

* someone edits ``decoy_prompts`` and adds a phrasing no pattern catches;
* someone edits a guardrail pattern and stops catching one that used to be.

Either way the bait stops being bait. Worse, "tôi không thể uống cà phê trứng"
is the allergy excuse in disguise — unblocked, it is a plausible *winning*
prompt, so a broken decoy hands players the answer.

The engine here is built with ``embedder=None`` on purpose: that is layer 1
only. Layer 2 fails open when the embeddings API is unavailable, so a decoy
that relies on it would sail through to the model during an outage.
"""

from __future__ import annotations

import asyncio

from app.challenge.rules import load_rules
from app.config import REPO_ROOT
from app.guardrails.engine import GuardrailEngine


def _rules():
    return load_rules(str(REPO_ROOT / "challenge.yaml"))


def test_decoy_prompts_are_configured() -> None:
    assert _rules().public.decoy_prompts, "no decoys configured — the trap is gone"


def test_every_decoy_is_blocked_by_layer_one() -> None:
    rules = _rules()
    engine = GuardrailEngine(rules.guardrails, embedder=None)

    async def check_all() -> list[tuple[str, object, object]]:
        out = []
        for prompt in rules.public.decoy_prompts:
            decision = await engine.check(prompt)
            out.append((prompt, decision.blocked, decision.layer))
        return out

    results = asyncio.run(check_all())
    escaped = [p for p, blocked, _ in results if not blocked]
    assert not escaped, f"decoys reach the model instead of being blocked: {escaped}"

    wrong_layer = [(p, layer) for p, _, layer in results if layer != 1]
    assert not wrong_layer, (
        "decoys must be caught by layer 1, not by the fail-open embedding "
        f"layer: {wrong_layer}"
    )


def test_decoys_are_not_leaked_with_their_categories() -> None:
    """Showing the bait is fine; naming which guardrail it trips is not."""
    payload = _rules().public_payload
    assert "decoy_prompts" in payload
    for key in ("guardrails", "target", "solution_paths"):
        assert key not in payload
