"""Provider interface. Everything above ``llm/`` depends only on this."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Run one completion.

        Raises :class:`~app.llm.schemas.LLMTransportError` if the call did not
        finish. A finished call always yields an :class:`LLMResponse`, even when
        the body wasn't the expected JSON (``recommendation`` is then ``None``).
        """
