"""FastAPI app factory.

``create_app`` takes optional ``llm_provider`` / ``store`` overrides so tests
can inject fakes; production leaves them ``None`` and the lifespan handler
builds the real ones from settings.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.challenge.rules import load_rules
from app.config import Settings, get_settings
from app.guardrails.adversary import AdversaryTracker
from app.guardrails.embeddings import Embedder, OpenAIEmbedder
from app.guardrails.engine import GuardrailEngine
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAICompatibleProvider
from app.store.base import Store
from app.store.memory import InMemoryStore
from app.telemetry import events, tracing

logger = logging.getLogger(__name__)


def _build_embedder(settings: Settings) -> Embedder | None:
    """Guardrail layer 2 needs an embedding endpoint. Without a key, return
    ``None`` and let the engine run layer 1 only — a local checkout with no
    credentials should still boot and be playable."""
    if not settings.llm_api_key:
        logger.warning("LLM_API_KEY is empty — guardrail layer 2 will be inactive")
        return None
    return OpenAIEmbedder(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.embedding_model,
        timeout=settings.embedding_timeout_seconds,
    )


def create_app(
    *,
    llm_provider: LLMProvider | None = None,
    store: Store | None = None,
    embedder: Embedder | None = None,
) -> FastAPI:
    settings = get_settings()
    events.configure()
    tracing.configure()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        rules = load_rules(settings.rules_path)
        app.state.settings = settings
        app.state.rules = rules
        app.state.llm = llm_provider or OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            llm_rules=rules.llm,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        app.state.guardrails = GuardrailEngine(
            rules.guardrails, embedder or _build_embedder(settings)
        )
        app.state.adversary = AdversaryTracker(rules.adversary_tracking)
        app.state.store = store or InMemoryStore()
        yield

    app = FastAPI(title="Coffee AI Challenge", version="1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
