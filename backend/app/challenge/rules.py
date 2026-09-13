"""Loader for ``challenge.yaml`` — the authoritative game rules.

The backend reads this once at startup. Only :meth:`Rules.public_payload` is
ever sent to the browser; everything else stays server-side.

S1 modelled ``public`` / ``target`` / ``recommendation_enum`` / ``llm``. S2 adds
``guardrails``, ``adversary_tracking`` and ``solution_paths``. ``scoring`` is
still left in the YAML and ignored until S4.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

PROMPTS_DIR = Path(__file__).parent / "prompts"


class RulesError(RuntimeError):
    """Raised when ``challenge.yaml`` is missing, unparseable, or invalid."""


class PublicRules(BaseModel):
    """Exactly what ``GET /api/challenge`` returns."""

    title: str
    tagline: str
    instructions_vi: str
    instructions_en: str
    max_attempts: int


class LLMRules(BaseModel):
    temperature: float = 0.4
    max_tokens: int = 400
    system_prompt_file: str = "system_v1.txt"


class GuardrailCategoryRules(BaseModel):
    enabled: bool = True
    layer: int = 1
    #: Layer 1. Literal phrases by default; a ``re:`` prefix makes one a regex.
    patterns: list[str] = Field(default_factory=list)
    #: Layer 2. Representative sentences the prompt is compared against.
    examples: list[str] = Field(default_factory=list)
    similarity_threshold: float = 0.82


class GuardrailRules(BaseModel):
    normalize_vietnamese: bool = True
    categories: dict[str, GuardrailCategoryRules]
    block_message_vi: str
    block_message_en: str

    @model_validator(mode="after")
    def _layers_have_what_they_need(self) -> GuardrailRules:
        for name, category in self.categories.items():
            if category.layer not in (1, 2):
                raise ValueError(f"category {name}: layer must be 1 or 2")
            if category.enabled and category.layer == 2 and not category.examples:
                raise ValueError(f"category {name}: layer 2 needs at least one example")
            if not 0.0 < category.similarity_threshold <= 1.0:
                raise ValueError(
                    f"category {name}: similarity_threshold must be in (0, 1]"
                )
        return self

    def message(self, lang: str) -> str:
        return self.block_message_en if lang == "en" else self.block_message_vi


class BypassDetectionRules(BaseModel):
    """Configured now, consumed in S3 — see ``docs/architecture.md``."""

    enabled: bool = True
    similarity_threshold: float = 0.80
    bypass_bonus: int = 5


class AdversaryRules(BaseModel):
    enabled: bool = True
    visibility: str = "operator_only"
    #: Category name -> weight. Categories absent here score nothing.
    signal_categories: dict[str, int] = Field(default_factory=dict)
    count_distinct_only: bool = True
    bypass_detection: BypassDetectionRules = Field(default_factory=BypassDetectionRules)
    flag_threshold: int = 6
    log_label: str = "unsafe"


class SolutionPath(BaseModel):
    """A SPOILER. Used by ``test_guardrail_balance.py`` to assert the guardrails
    never block an intended way to win."""

    id: str
    description: str
    reference_prompt: str
    expected_success_rate: float = 0.7


class Rules(BaseModel):
    challenge_id: str
    version: int
    public: PublicRules
    target: str
    default: str
    recommendation_enum: list[str]
    llm: LLMRules
    guardrails: GuardrailRules
    adversary_tracking: AdversaryRules
    solution_paths: list[SolutionPath] = Field(default_factory=list)
    # Resolved from ``llm.system_prompt_file`` at load time, not from the YAML.
    system_prompt: str

    @model_validator(mode="after")
    def _target_and_default_are_enum_values(self) -> Rules:
        for name, value in (("target", self.target), ("default", self.default)):
            if value not in self.recommendation_enum:
                raise ValueError(f"{name} {value!r} is not in recommendation_enum")
        return self

    @model_validator(mode="after")
    def _signal_categories_exist(self) -> Rules:
        """A typo in ``signal_categories`` would silently mean "this attack is
        worth nothing", so it fails the startup instead."""
        unknown = set(self.adversary_tracking.signal_categories) - set(
            self.guardrails.categories
        )
        if unknown:
            raise ValueError(
                "adversary_tracking.signal_categories names categories that do not "
                f"exist under guardrails.categories: {sorted(unknown)}"
            )
        return self

    @property
    def public_payload(self) -> dict:
        return self.public.model_dump()


def load_rules(path: Path) -> Rules:
    """Parse and validate the rules file. Raises :class:`RulesError` on any
    problem, with a message that says what and where."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RulesError(f"cannot read challenge rules at {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise RulesError(f"challenge rules at {path} are not a YAML mapping")

    try:
        llm = LLMRules(**(raw.get("llm") or {}))
        system_prompt = (PROMPTS_DIR / llm.system_prompt_file).read_text(encoding="utf-8")
        return Rules(
            challenge_id=raw["challenge_id"],
            version=raw["version"],
            public=PublicRules(**raw["public"]),
            target=raw["target"],
            default=raw["default"],
            recommendation_enum=raw["recommendation_enum"],
            llm=llm,
            guardrails=GuardrailRules(**raw["guardrails"]),
            adversary_tracking=AdversaryRules(**(raw.get("adversary_tracking") or {})),
            solution_paths=[SolutionPath(**p) for p in raw.get("solution_paths") or []],
            system_prompt=system_prompt,
        )
    except (KeyError, TypeError, OSError, ValidationError) as exc:
        raise RulesError(f"challenge rules at {path} are invalid: {exc}") from exc
