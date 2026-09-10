"""OpenAI-compatible provider.

Works against any endpoint that speaks the OpenAI chat-completions API — OpenAI
itself, Ollama, Groq, Together, and so on. The vendor never leaks past this
module.
"""

from __future__ import annotations

from openai import AsyncOpenAI, OpenAIError

from app.challenge.rules import LLMRules
from app.llm.base import LLMProvider
from app.llm.parsing import parse_completion_body
from app.llm.schemas import LLMResponse, LLMTransportError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        llm_rules: LLMRules,
        timeout: float = 20.0,
        max_retries: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._model = model
        self._rules = llm_rules

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                temperature=self._rules.temperature,
                max_tokens=self._rules.max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except OpenAIError as exc:
            raise LLMTransportError(str(exc)) from exc

        raw = resp.choices[0].message.content or ""
        recommendation, reply = parse_completion_body(raw)
        usage = resp.usage
        return LLMResponse(
            recommendation=recommendation,
            reply=reply,
            raw=raw,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
