"""Typed runtime configuration — environment in, settings out.

Game rules are NOT here. They live in ``challenge.yaml`` and are loaded by
``app.challenge.rules``. This module only knows infrastructure: the LLM
endpoint, CORS, and where the rules file is.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM provider -------------------------------------------------------
    llm_provider: str = "openai"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 20.0
    llm_max_retries: int = 2

    # --- Backend ----------------------------------------------------------
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    challenge_config_path: Path = REPO_ROOT / "challenge.yaml"
    cors_allow_origins: str = "http://localhost:3000"

    # --- Privacy --------------------------------------------------------
    log_prompts: bool = True
    log_responses: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def rules_path(self) -> Path:
        """The configured path if it exists, otherwise the repo-root fallback.

        Lets a Docker-oriented value (``CHALLENGE_CONFIG_PATH=/app/challenge.yaml``)
        coexist with a local ``uvicorn`` run from a checkout.
        """
        configured = self.challenge_config_path
        return configured if configured.exists() else REPO_ROOT / "challenge.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
