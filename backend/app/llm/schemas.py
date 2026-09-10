"""Types crossing the ``llm/`` boundary.

Nothing above this layer knows the vendor. A provider either returns an
:class:`LLMResponse` or raises :class:`LLMTransportError`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """A completed call. ``recommendation`` is the raw string from the model's
    JSON body — it may be ``None`` (missing / wrong type) or a value that isn't
    in the enum. Mapping that to a game outcome is the challenge engine's job.
    """

    recommendation: str | None
    reply: str
    raw: str
    input_tokens: int | None
    output_tokens: int | None


class LLMError(Exception):
    """Base class for provider failures."""


class LLMTransportError(LLMError):
    """The call did not complete — network, timeout, auth, rate limit.

    The attempt is NOT consumed; the player retries for free.
    """
