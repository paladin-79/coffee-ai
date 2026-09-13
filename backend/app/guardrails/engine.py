"""Layered prompt filtering, cheapest layer first.

    normalise  ->  layer 1 (keyword / regex)  ->  layer 2 (embedding similarity)

Layer 1 is a handful of regex scans over a short string: free, and it catches
most of what players actually type. Layer 2 costs a network round trip, so it
only runs on prompts layer 1 let through.

This is a **game mechanic**, not a security control. It closes the obvious
shortcuts so that winning takes an idea rather than a keyword. Treat a block as
"that move doesn't count", not as "that request was dangerous".

The engine decides *whether* to block. Who gets flagged for it is
``adversary.py``; what the player is told is ``block_message``.
"""

from __future__ import annotations

import logging
import re

from app.challenge.rules import GuardrailRules, RulesError
from app.guardrails.embeddings import Embedder, EmbeddingError, cosine
from app.guardrails.normalize import normalize
from app.guardrails.schemas import DEGRADED, PASS, GuardrailDecision, Vector

logger = logging.getLogger(__name__)

#: A pattern starting with this is compiled as a regex against the *normalised*
#: prompt. Everything else is a literal phrase.
REGEX_PREFIX = "re:"


def _compile(pattern: str, *, strip_marks: bool) -> tuple[re.Pattern[str], str]:
    """Return ``(compiled, display)``. ``display`` is the pattern as the rules
    file wrote it, so a log line points back at an editable line of YAML."""
    if pattern.startswith(REGEX_PREFIX):
        body = pattern[len(REGEX_PREFIX) :].strip()
        try:
            return re.compile(body), pattern
        except re.error as exc:
            raise RulesError(f"invalid guardrail regex {pattern!r}: {exc}") from exc

    literal = normalize(pattern, strip_marks=strip_marks)
    if not literal:
        raise RulesError(f"guardrail pattern {pattern!r} normalises to nothing")
    # Lookarounds rather than \b so a pattern with leading/trailing punctuation
    # still anchors on word edges: "sua da" must not fire inside "casua dat".
    return re.compile(rf"(?<!\w){re.escape(literal)}(?!\w)"), pattern


class GuardrailEngine:
    """Built once at startup from the parsed rules.

    ``embedder`` may be ``None`` — layer 2 is then skipped entirely and a
    warning is logged once. That is the deliberate degraded mode for a local run
    with no API key.
    """

    def __init__(self, rules: GuardrailRules, embedder: Embedder | None = None) -> None:
        self._rules = rules
        self._embedder = embedder
        strip = rules.normalize_vietnamese

        # Categories keep their declaration order from the YAML, so the file
        # reads top-to-bottom in the same order the engine evaluates.
        self._layer1: list[tuple[str, list[tuple[re.Pattern[str], str]]]] = []
        self._layer2: list[tuple[str, list[str], float]] = []
        for name, category in rules.categories.items():
            if not category.enabled:
                continue
            if category.layer == 1:
                compiled = [_compile(p, strip_marks=strip) for p in category.patterns]
                if compiled:
                    self._layer1.append((name, compiled))
            else:
                self._layer2.append(
                    (name, list(category.examples), category.similarity_threshold)
                )

        self._strip_marks = strip
        #: example sentence -> vector, filled on the first layer-2 evaluation.
        self._example_vectors: dict[str, Vector] = {}

        if self._layer2 and embedder is None:
            logger.warning(
                "guardrail layer 2 disabled: no embedder configured, categories %s "
                "will never fire",
                [name for name, _, _ in self._layer2],
            )

    @property
    def layer2_active(self) -> bool:
        return bool(self._layer2) and self._embedder is not None

    def block_message(self, lang: str = "vi") -> str:
        return self._rules.message(lang)

    async def check(self, prompt: str) -> GuardrailDecision:
        """Evaluate one prompt. Never raises — a layer that cannot run is
        skipped, because a broken guardrail must not take the game down with it.
        """
        decision = self._check_layer1(prompt)
        if decision.blocked:
            return decision
        return await self._check_layer2(prompt)

    def _check_layer1(self, prompt: str) -> GuardrailDecision:
        text = normalize(prompt, strip_marks=self._strip_marks)
        for name, patterns in self._layer1:
            for compiled, display in patterns:
                if compiled.search(text):
                    return GuardrailDecision(
                        blocked=True, category=name, layer=1, matched=display
                    )
        return PASS

    async def _check_layer2(self, prompt: str) -> GuardrailDecision:
        if not self.layer2_active:
            return PASS
        assert self._embedder is not None

        try:
            await self._load_example_vectors()
            (vector,) = await self._embedder.embed([prompt])
        except EmbeddingError as exc:
            # Fail open. A player getting a prompt through because the embedding
            # endpoint was down is a far better outcome than the game refusing
            # to play. The gap is visible in telemetry.
            logger.warning("guardrail layer 2 skipped: %s", exc)
            return DEGRADED

        for name, examples, threshold in self._layer2:
            best_example, best_score = "", -1.0
            for example in examples:
                score = cosine(vector, self._example_vectors[example])
                if score > best_score:
                    best_example, best_score = example, score
            if best_score >= threshold:
                return GuardrailDecision(
                    blocked=True,
                    category=name,
                    layer=2,
                    matched=best_example,
                    similarity=round(best_score, 4),
                    embedding=vector,
                )
        return PASS

    async def _load_example_vectors(self) -> None:
        """Embed every layer-2 example once, on first use.

        Not done in ``__init__`` because that is synchronous, and not at startup
        because a cold embedding endpoint should delay the first block decision,
        not the whole app boot.
        """
        missing = [
            example
            for _, examples, _ in self._layer2
            for example in examples
            if example not in self._example_vectors
        ]
        if not missing:
            return
        assert self._embedder is not None
        vectors = await self._embedder.embed(missing)
        self._example_vectors.update(zip(missing, vectors))
