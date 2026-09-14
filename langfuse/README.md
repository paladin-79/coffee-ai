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

`docker-compose.yml` here is an optional overlay for running Langfuse
separately from the main stack, adapted from the [official self-host compose
file](https://github.com/langfuse/langfuse). Langfuse v4 needs more than just
Postgres — Postgres, ClickHouse, Redis, and MinIO all run alongside the
`langfuse-web`/`langfuse-worker` services.

```
docker compose -f langfuse/docker-compose.yml up -d
```

Web UI at `http://localhost:3002` (port 3002, not upstream's default 3000 —
this project's frontend already owns 3000). First run: sign up in the UI,
create a project, then generate an API key pair under Settings → API Keys.
Put those in the repo-root `.env` as `LANGFUSE_PUBLIC_KEY` /
`LANGFUSE_SECRET_KEY`, and set `LANGFUSE_BASE_URL=http://localhost:3002` —
the backend reads all three via `app.config.Settings` (see
`app/telemetry/tracing.py`).

The default secrets in `docker-compose.yml` (`mysecret`, `postgres`,
`myredissecret`, ...) are the upstream `# CHANGEME` placeholders — fine for a
local checkout, not for anything exposed beyond your machine.
