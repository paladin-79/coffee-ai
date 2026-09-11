# ☕ Coffee AI Challenge

> Can you make an AI recommend **cà phê sữa đá** — without ever asking for it?

A small, self-contained prompt-engineering game. The Coffee AI is a Vietnamese
coffee assistant that reliably recommends **cà phê trứng** (egg coffee). Your job
as a player is to change its mind using nothing but the shape of your question.

The obvious routes are closed. A guardrail engine blocks direct requests, egg
allergy excuses, preference declarations, and prompt-injection attempts. What's
left is the interesting part: describing a situation where iced milk coffee is
simply the better answer.

Everything the player does is traced end-to-end, so an operator can watch the
whole event unfold in Langfuse and Grafana in real time.

---

## Status

🚧 **Alpha — playable end-to-end.** `docker compose up -d` brings up a working
game at `localhost:3000`.

Current sprint: **S2 — Guardrails** (see [Roadmap](#roadmap)).

| Sprint | Goal | Status |
|---|---|---|
| S0 | Game design spike — prove the game is winnable and fun | ✅ Done (2026-09-10) |
| S1 | Vertical slice — playable end-to-end on localhost | ✅ Done (2026-09-11) |
| S2 | Guardrails — close the obvious shortcuts | 🟡 In progress |
| S3 | Observability — traces, metrics, Langfuse (**= MVP**) | ⬜ Not started |
| S4 | Gamification — timer, score, leaderboard | ⬜ Not started |
| S5 | Event hardening — survive 50 concurrent players | ⬜ Not started |
| S6 | Dry run + polish | ⬜ Not started |

---

## How the game works

```
Player prompt
     │
     ▼
Guardrail Engine ──── BLOCK ──▶ friendly refusal, attempt still counted
     │                          (real category logged for observability)
   PASS
     │
     ▼
   LLM  ──▶ structured JSON: { recommendation, reply }
     │
     ▼
Challenge Engine ──▶ reads the `recommendation` enum, never the prose
     │
     ▼
  SUCCESS / FAIL ──▶ score + leaderboard
```

Two design decisions carry most of the weight:

**The LLM returns structured output.** It replies with a JSON object containing a
`recommendation` enum (`egg_coffee` / `iced_milk_coffee` / `other`) alongside the
natural-language `reply` shown to the player. The challenge engine only ever reads
the enum. Scoring never depends on parsing prose, so a player cannot win by
getting the model to *say* the words.

**The authoritative rules live on the backend.** `challenge.yaml` holds the target,
the default, the forbidden categories, and the scoring formula. `GET /api/challenge`
exposes only the `public` block. Nothing in the frontend bundle tells a player
what they're up against.

---

## Repository layout

```
coffee-ai/
├── challenge.yaml              # authoritative game rules (backend-only)
├── docker-compose.yml          # full local stack
├── .env.example
│
├── backend/                    # FastAPI — game logic lives here
│   ├── app/
│   │   ├── api/                # route handlers
│   │   ├── challenge/          # rules loader + deterministic evaluation
│   │   ├── guardrails/         # layered prompt filtering
│   │   ├── llm/                # provider abstraction (OpenAI-compatible)
│   │   ├── store/              # session + leaderboard (memory → Redis)
│   │   └── telemetry/          # OTel + Langfuse setup
│   └── tests/
│
├── frontend/                   # Next.js + TypeScript + Tailwind
│   ├── app/                    # landing page + /play chat interface
│   ├── components/
│   └── lib/
│
├── observability/
│   ├── otel/                   # collector config — the single egress point
│   ├── prometheus/
│   ├── loki/
│   └── grafana/                # datasources + dashboards, provisioned as code
│
├── langfuse/                   # self-hosted Langfuse compose overlay
├── scripts/                    # spike.py and other dev tooling
└── docs/
    ├── architecture.md
    ├── challenge-design.md
    ├── observability.md
    └── solution-paths.md       # ⚠️ spoilers — the intended ways to win
```

Each directory has its own `README.md` describing what belongs there.

---

## Quick start

### Prerequisites

- Docker + Docker Compose v2
- An API key for any OpenAI-compatible endpoint (or a local Ollama instance)
- Node 20+ and Python 3.11+ if you want to run services outside Docker

### Run the stack

```bash
git clone https://github.com/paladin-79/coffee-ai.git
cd coffee-ai
cp .env.example .env
# edit .env — at minimum set LLM_API_KEY
docker compose up -d
```

Stop it with `docker compose down` (removes the containers; images and
`node_modules`/`pip` layers stay cached, so the next `up -d` is fast). Use
`docker compose stop` instead if you just want to pause without tearing the
containers down.

> **Linux: `permission denied … docker.sock`?** Your user isn't in the
> `docker` group yet.
> ```bash
> sudo usermod -aG docker $USER
> newgrp docker   # or log out and back in — group changes need a fresh shell
> ```

Live since S1:

| Service | URL | Purpose |
|---|---|---|
| coffee-frontend | http://localhost:3000 | The game |
| coffee-backend | http://localhost:8000/docs | API + OpenAPI explorer |

Arriving in S3 (observability):

| Service | URL | Purpose |
|---|---|---|
| grafana | http://localhost:3001 | Game / LLM / guardrail dashboards |
| langfuse | http://localhost:3002 | Per-attempt LLM trace inspection |
| prometheus | http://localhost:9090 | Metrics store |
| loki | http://localhost:3100 | Log store |
| otel-collector | :4317 / :4318 | Telemetry ingest |

### Run without Docker

Useful for backend/frontend development with hot reload. Needs Python 3.11+
and Node 20+. Run both in separate terminals, backend first:

```bash
# terminal 1 — backend, http://localhost:8000
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend, http://localhost:3000
cd frontend
npm install
npm run dev
```

`challenge.yaml` is read from the repo root by default (no `CHALLENGE_CONFIG_PATH`
needed outside Docker — see `backend/app/config.py`). Details:
[`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md).

### Run the design spike (available now)

S0 needs no stack at all:

```bash
cd backend
pip install -r requirements.txt
python ../scripts/spike.py --prompt "Trời Hà Nội hôm nay 38 độ, tôi cần gì đó uống nhanh."
python ../scripts/spike.py --suite   # replay every prompt in tests/fixtures/
```

Record what you learn in `docs/solution-paths.md`.

---

## Configuration

All runtime config comes from environment variables — see `.env.example` for the
full annotated list. Game rules are separate, in `challenge.yaml`, so tuning
difficulty never means touching code or redeploying.

**Never commit real keys.** `.env` is gitignored. If you leak one, rotate it
rather than rewriting history.

---

## Roadmap

Detail lives in [`docs/challenge-design.md`](docs/challenge-design.md) and
[`docs/architecture.md`](docs/architecture.md). The short version:

**S0 — Game Design Spike.** Write the system prompt. Play 30–50 prompts by hand.
Find at least three distinct ways to win, each reproducible ≥70% of the time,
while ordinary prompts still return egg coffee ≥90% of the time. If those numbers
don't hold, keep tuning the prompt — do not start S1. This is the cheapest place
in the whole project to discover the game isn't fun.

**S1 — Vertical Slice.** FastAPI + Next.js, chat working, structured output
wired, challenge engine reading the enum. No guardrails, no score, no dashboards.
One person can open a browser and win.

**S2 — Guardrails.** Six categories, layered: normalised keyword/regex first
(Vietnamese diacritics stripped so `sua da` is caught alongside `sữa đá`), then
embedding similarity for paraphrases. LLM-as-judge is explicitly out of scope.

The critical artefact here is `tests/test_guardrail_balance.py`, which asserts
three things at once: every forbidden prompt is blocked, every intended solution
path still passes, and every neutral prompt still passes. Guardrails that block
the intended solutions are worse than no guardrails, and only a test catches it.

S2 also introduces **adversary tracking**: an operator-only score that flags
sessions attempting prompt injection or system-prompt extraction, kept entirely
separate from the player's game score and never shown to the player. See
[`docs/challenge-design.md`](docs/challenge-design.md) → Adversary tracking.

**S3 — Observability → MVP complete.** Langfuse first (fastest debugging payoff),
then OTel SDK with `gen_ai.*` semantic conventions, then collector →
Prometheus/Loki → Grafana. Dashboards are provisioned from JSON in the repo, not
clicked together by hand — otherwise one `docker compose down -v` erases them.

**S4 — Gamification.** Backend-authoritative timer, configurable score formula,
Redis sorted-set leaderboard.

**S5 — Event Hardening.** Attempt caps, rate limiting, retry with backoff, a
circuit breaker for LLM outages, budget alerting, and a Locust run at 50
concurrent players.

**S6 — Dry Run.** Ten real humans. Target a 40–70% win rate and a 3–8 minute
median. Anyone who finds an unanticipated way to win either gets documented as a
solution path or blocked as an exploit.

---

## Design principles

**Keep the game simple.** A player should understand the challenge in ten seconds.

**Keep AI behaviour predictable.** The same class of prompt should produce the
same default recommendation. Low temperature, strong-but-plausible bias toward
egg coffee — reasoned, not hard-coded.

**Keep challenge logic deterministic.** LLM output is never the sole source of
truth for scoring.

**Keep observability first-class.** Every meaningful action emits telemetry.

**Keep providers replaceable.** Neither the LLM provider nor the observability
backend may leak into game logic. All telemetry egresses through the OTel
collector, so adding a backend later is a config change.

**Keep the first version small.** This stays a *Coffee AI Challenge*. Guardrails
and observability support the gameplay; they are not the product. Resist the
drift toward a generic LLM security lab.

---

## Privacy

The game collects a random `player_id`, a UUID `session_id`, and an optional
self-chosen nickname. Nothing else — no emails, no accounts, no identity data.
Prompt and response logging is toggleable via `LOG_PROMPTS`, and public
deployments should redact before telemetry export.

---

## Contributing

Sprints ship in order and each has explicit exit criteria in
`docs/challenge-design.md`. Two rules matter more than the rest:

1. Changing anything in `guardrails/` or `challenge.yaml` means re-running
   `test_guardrail_balance.py` before pushing.
2. `docs/solution-paths.md` contains spoilers. Keep it out of demos.

---

## License

TBD.
