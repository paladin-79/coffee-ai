"""Loader for ``challenge.yaml`` — the authoritative game rules.

The backend reads this once at startup. Only :meth:`Rules.public_payload` is
ever sent to the browser; everything else stays server-side.

S1 models only the fields the vertical slice needs (``public``, ``target``,
``recommendation_enum``, ``llm``). Guardrails, scoring, adversary tracking, and
solution paths are left in the YAML and ignored until later sprints.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, model_validator

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


class Rules(BaseModel):
    challenge_id: str
    version: int
    public: PublicRules
    target: str
    default: str
    recommendation_enum: list[str]
    llm: LLMRules
    # Resolved from ``llm.system_prompt_file`` at load time, not from the YAML.
    system_prompt: str

    @model_validator(mode="after")
    def _target_and_default_are_enum_values(self) -> Rules:
        for name, value in (("target", self.target), ("default", self.default)):
            if value not in self.recommendation_enum:
                raise ValueError(f"{name} {value!r} is not in recommendation_enum")
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
            system_prompt=system_prompt,
        )
    except (KeyError, TypeError, OSError, ValidationError) as exc:
        raise RulesError(f"challenge rules at {path} are invalid: {exc}") from exc
