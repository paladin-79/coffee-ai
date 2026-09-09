# Langfuse

Self-hosted LLM observability. This is the first thing to wire up in S3 — the
SDK is quick to integrate and it pays for itself immediately while tuning
prompts and guardrails.

It answers one question well: *what exactly happened during this player's
attempt?*

```
Session: player-42

Attempt #1   Prompt → ...   Guardrail → PASS    LLM → egg_coffee         FAIL
Attempt #2   Prompt → ...   Guardrail → BLOCK   PROMPT_INJECTION           —
Attempt #3   Prompt → ...   Guardrail → PASS    LLM → iced_milk_coffee  SUCCESS
```

`docker-compose.yml` here is an optional overlay for running Langfuse and its
Postgres separately from the main stack. It needs `LANGFUSE_PUBLIC_KEY` and
`LANGFUSE_SECRET_KEY` in your `.env` — generate them in the Langfuse UI on
first run.
