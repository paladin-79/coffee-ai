# Observability

> Status: Langfuse tracing done and verified end-to-end. OTel SDK / Collector
> / Prometheus / Loki / Grafana **dropped** for this event (scope call,
> 2026-09-14 — see below), not merely deferred.

## Scope: Langfuse-only for this event

The event this app runs is ~20 players, each playing for 3-4 minutes, with
the presenter reviewing what the AI did *after* everyone has played — not a
service anyone monitors live while it's running. That need is fully answered
by Langfuse alone: open a session in the Langfuse UI and see every prompt a
player sent, what the guardrails did with it, what the model replied, token
cost, latency — per player, filterable, searchable.

The rest of the originally-planned pipeline (OpenTelemetry SDK → Collector →
Prometheus/Loki → Grafana dashboards) solves a different problem: live
operational monitoring under concurrent load — request-rate/error-rate/latency
dashboards, alerting, log aggregation across many simultaneous
players. None of that is needed to review a ~20-player event after the fact,
and standing up four more services (Collector, Prometheus, Loki, Grafana) has
a real cost: each one is something to explain if asked "why is this here" in
a presentation, without answering the actual question the app needs to
answer. See `checklist.md` S3 for the itemized drop list.

**Revisit this if the format changes** — many simultaneous rooms, an
unattended/long-running deployment, or a genuine need to watch the event live
rather than review it afterward would each bring back the original need for
Prometheus/Loki/Grafana.

## Order of work (historical — Langfuse is now the whole plan for S3)

Langfuse first. Its SDK integrates fastest and gives immediate debugging value
while S2 guardrails are still being tuned — which is exactly when you most need
to see what the model actually did.

~~Then OTel SDK, then collector, then Prometheus/Loki, then Grafana
dashboards.~~ Dropped — see "Scope: Langfuse-only for this event" above.

## Langfuse tracing (done)

`app/telemetry/tracing.py` builds the process-wide Langfuse client at startup
(`main.py`'s `create_app`). Credentials go through `Settings`
(`langfuse_public_key`/`langfuse_secret_key`/`langfuse_base_url`, sourced from
`.env`) rather than the SDK's own `os.environ` lookup — pydantic-settings
parses `.env` into `Settings` only, it never populates the process
environment, so the SDK would otherwise see nothing and silently trace with a
disabled client.

One `/api/chat` attempt is one trace (`process-chat-attempt`), with
`session_id`/`user_id` propagated to every child observation:

```
process-chat-attempt          (span, root)
├── check-guardrails          (guardrail)
│   └── embed-guardrail-prompt (embedding, layer-2 only)
├── generate-completion       (generation — via langfuse.openai, skipped on a block)
└── evaluate-challenge        (span, skipped on a block)
```

`check-guardrails` uses Langfuse's dedicated `guardrail` observation type
(added in SDK v4), not a generic `span` — this is what the best-practices
guidance means by "give each call its most specific type" and is what makes
the Agent Graph / observation-type filters in the Langfuse UI useful.

`app/llm/openai_provider.py` and `app/guardrails/embeddings.py` both use
`langfuse.openai`'s drop-in `AsyncOpenAI` in place of the bare SDK, so model,
token usage, and cost land on the `generation`/`embedding` observations
automatically.

Every trace also carries an `environment` attribute (`app.config.Settings.app_env`,
`APP_ENV` in `.env`; default `development`) — set explicitly on the `Langfuse()`
client rather than left to the SDK's own `LANGFUSE_TRACING_ENVIRONMENT` lookup,
for the same reason credentials are: pydantic-settings owns `.env`, not
`os.environ`.

Redaction: `tracing._mask_otel_spans` (a Langfuse `mask_otel_spans` hook) wipes
the `input`/`output` attributes on every exported span when
`LOG_PROMPTS`/`LOG_RESPONSES` are off, matching the flags `telemetry/events.py`
already uses for structured logs. It's a coarse, whole-attribute redaction
(the entire input or output object, not per-field) — verified by toggling both
flags off and confirming a trace's `input`/`output` both come back
`[redacted]` via `langfuse-cli api observations list`.

### Docker networking: two separate compose projects, and two run contexts

`langfuse/docker-compose.yml` runs as its own compose project (`langfuse`), on
its own Docker network (`langfuse_default`) — deliberately not joined to this
project's `coffee-ai_default` network, so either stack can run without the
other. That means `LANGFUSE_BASE_URL` can't be a compose service name
(`http://langfuse-web:3000`) from inside `coffee-backend`.

The repo also runs the backend two ways — `make test` / a host-run `uvicorn`
read `.env` directly via pydantic-settings, while `docker compose up` reads it
through `env_file` into the container — and those two contexts need different
values for the same host machine:

- **Bare host process**: `.env` has `LANGFUSE_BASE_URL=http://localhost:3002`,
  which is correct — Langfuse's `langfuse-web` container publishes 3002 to the
  host's loopback interface.
- **`coffee-backend` container**: `localhost` there means the container
  itself, not the host, so `docker-compose.yml` overrides just that one var to
  the Docker Desktop host gateway, `http://host.docker.internal:3002`
  (`extra_hosts: host.docker.internal:host-gateway` makes that also resolve on
  Linux, where it isn't automatic). The reverse value doesn't work either:
  `host.docker.internal` resolves from the bare host but doesn't accept a
  connection back to itself, so it can't just replace the `.env` default.

Getting either wrong fails silently — the Langfuse SDK batches and retries in
a background thread, so a misrouted `LANGFUSE_BASE_URL` produces no error in
`docker compose logs` or `pytest`, just an empty project in the Langfuse UI.
Confirm delivery with `langfuse-cli api observations list --session-id <id>`
after an attempt.

**Also remember to rebuild, not just restart**, after touching `backend/app/**`
— `docker-compose.yml` bakes app code into the image at build time (only
`challenge.yaml` is a live-mounted volume), so `docker compose up -d
coffee-backend` alone redeploys whatever image was last built, silently.
`docker compose build coffee-backend && docker compose up -d coffee-backend`
picks up source changes.

## Structured log events

Actual events implemented in `telemetry/events.py` (this list was originally
written ahead of the code and had drifted — corrected 2026-09-14):

```
guardrail_block    guardrail_degraded    adversary_signal    session_flagged
```

All JSON (via `_JsonLineFormatter`), all carrying `session_id`. **Not**
`trace_id` — that was written for the Loki-correlation use case, which is
dropped along with Loki (see "Scope" above); these logs stand alone now,
readable via `docker compose logs coffee-backend`. A `trace_id` field could
still be added cheaply later (`langfuse.get_client().get_current_trace_id()`)
if a future need reintroduces log↔trace correlation without needing all of
Loki back.

`guardrail_block` on a signal category (`PROMPT_INJECTION`,
`SYSTEM_PROMPT_EXTRACTION`, `SENSITIVE_REQUEST`) also carries `adversary: true`
and `label: unsafe`. `adversary_signal` fires whenever the session's score
changes (category first seen, or bypass detected) and carries the running
total. `session_flagged` fires once, when the total first crosses
`flag_threshold`.

## Dashboard intent (dropped with Grafana — kept here as design record)

Three dashboards were planned, each answering a distinct question. Dropped
along with OTel/Prometheus/Loki/Grafana (see "Scope" above) since none of
these are "is it going well *right now*" questions this event needs answered
live — but the questions themselves are worth keeping on record in case the
format changes later.

**game.json** — *Is the event going well?*
Active players, total attempts, successes, average attempts to success, fastest
completion.

**llm.json** — *Is the AI healthy and affordable?*
Request rate, latency percentiles, token usage, error rate.

**guardrails.json** — *What are players trying? Who is attacking?*
Block rate, blocks by category, injection attempts over time, and a **Potential
adversaries** table — sessions ranked by `adversary_tracking` score, flagged
rows highlighted. See `challenge-design.md` → Adversary tracking.

Without Grafana, the **Potential adversaries** need a different, lighter-weight
surface — not yet decided, see `checklist.md` S3 "Adversary tracking" open
question. Two candidates: filter Langfuse traces by a tag/metadata field, or a
small script/endpoint reading `session.adversary_score` / `flagged` directly
from the `store` (already computed today, just has no reviewable view).

## To document in S3

- [-] Collector pipeline diagram with actual processor list — dropped with the Collector
- [-] Sampling decision — dropped, no collector to sample at
- [x] Redaction approach when `LOG_PROMPTS=false` — done for Langfuse (see
      above) and independently for structured JSON logs
      (`events._prompt_field`); the OTel/Loki path this was originally left
      open for is dropped, so this is now fully closed
- [-] Cardinality review — dropped, no Prometheus labels to worry about
- [ ] Adversary panel replacement: the exact query, the threshold, and how a
      flagged session gets reviewed after the event — still open, now without
      Grafana as the assumed surface (see "Dashboard intent" above)
