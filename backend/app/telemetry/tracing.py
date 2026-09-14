"""Langfuse client setup.

Must run before any request touches ``langfuse.openai`` — the first
``Langfuse(...)`` construction wins the process-wide singleton that
``langfuse.get_client()`` returns everywhere else, so this is where the
redaction hook gets wired in rather than at the SDK's own default.

Credentials and endpoint are passed in explicitly from ``app.config.Settings``
rather than left to the SDK's own environment lookup: pydantic-settings parses
``.env`` into ``Settings`` only, it never populates ``os.environ``, so the SDK
would otherwise see nothing and silently run with tracing disabled.
"""

from __future__ import annotations

import re

from langfuse import Langfuse
from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch

from app.config import get_settings

#: Matches an attribute key whose *last dot-separated segment* is exactly one
#: of these words — not a substring hit, so ``langfuse.observation.usage_details``
#: (token counts) is left alone while ``langfuse.observation.input`` and
#: ``langfuse.trace.output`` are caught. Content-bearing keys observed on this
#: SDK version: ``langfuse.trace.{input,output}`` and
#: ``langfuse.observation.{input,output}`` (manual spans and the OpenAI
#: wrapper both funnel through the same attributes).
_CONTENT_SEGMENT = re.compile(r"(?:^|\.)(input|output|prompt|completion)$")

REDACTED = "[redacted]"


def _mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult | None:
    settings = get_settings()
    if settings.log_prompts and settings.log_responses:
        return None

    redact_words: set[str] = set()
    if not settings.log_prompts:
        redact_words.update(("input", "prompt"))
    if not settings.log_responses:
        redact_words.update(("output", "completion"))

    patches = {}
    for identifier, span in params.spans.items():
        replacements = {}
        for key in span.attributes:
            match = _CONTENT_SEGMENT.search(key)
            if match and match.group(1) in redact_words:
                replacements[key] = REDACTED
        if replacements:
            patches[identifier] = OtelSpanPatch(set_attributes=replacements)
    return MaskOtelSpansResult(span_patches=patches) if patches else None


def configure() -> Langfuse:
    """Build the process-wide Langfuse client. Idempotent: a second call
    from e.g. a test fixture just returns the existing singleton.

    No public key means no credentials configured (e.g. a bare local
    checkout) — the SDK degrades to a disabled client rather than erroring,
    matching how ``_build_embedder`` treats a missing ``LLM_API_KEY``.
    """
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key or None,
        secret_key=settings.langfuse_secret_key or None,
        base_url=settings.langfuse_base_url,
        mask_otel_spans=_mask_otel_spans,
    )
