# Backend — FastAPI

All game logic lives here. The frontend is a thin client; it never decides
anything that affects scoring.

## Modules

| Path | Responsibility |
|---|---|
| `app/main.py` | App factory, middleware, OTel bootstrap |
| `app/config.py` | `pydantic-settings` — env in, typed settings out |
| `app/api/` | Route handlers only. No business logic. |
| `app/challenge/` | Rules loader, deterministic evaluation, system prompts |
| `app/guardrails/` | Layered prompt filtering |
| `app/llm/` | Provider abstraction — nothing above this layer knows the vendor |
| `app/store/` | Session + leaderboard persistence behind one interface |
| `app/telemetry/` | OTel SDK setup, Langfuse client, span helpers |

## Endpoints

```
POST /api/session      create a player session, start the server-side timer
POST /api/chat         submit one attempt
GET  /api/challenge    public rules only (never the full challenge.yaml)
GET  /api/leaderboard  top N
GET  /api/health       liveness
```

## Rules that hold across sprints

**The timer is server-side.** Never trust a client timestamp. Elapsed time is
`now - session.created_at`, computed at evaluation.

**Score is computed server-side** from `challenge.yaml`. A crafted request must
not be able to submit its own score.

**`store/` is an interface.** S1–S3 use `memory.py`. S4 swaps in `redis.py`.
If a route imports a concrete store, that swap becomes painful — so don't.

**`llm/` returns structured output.** The provider parses the model's JSON and
returns a typed object. If parsing fails, that is a failed attempt with a clear
error — not a guess at what the model meant.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
