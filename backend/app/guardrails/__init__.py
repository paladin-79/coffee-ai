"""Prompt guardrails — the layer that closes the obvious shortcuts.

Public surface::

    GuardrailEngine.check(prompt) -> GuardrailDecision
    AdversaryTracker.on_block(...) -> AdversaryUpdate

``GuardrailDecision.category`` is operator-only. The player gets
``GuardrailEngine.block_message()`` and nothing more.
"""

from __future__ import annotations

from app.guardrails.adversary import AdversaryTracker
from app.guardrails.embeddings import Embedder, EmbeddingError, OpenAIEmbedder
from app.guardrails.engine import GuardrailEngine
from app.guardrails.normalize import normalize
from app.guardrails.schemas import AdversaryUpdate, GuardrailDecision

__all__ = [
    "AdversaryTracker",
    "AdversaryUpdate",
    "Embedder",
    "EmbeddingError",
    "GuardrailDecision",
    "GuardrailEngine",
    "OpenAIEmbedder",
    "normalize",
]
