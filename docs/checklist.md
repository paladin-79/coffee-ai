# Project Checklist

One list per sprint. Sprints ship in order — do not start a sprint until every
box under the previous sprint's **Exit criteria** is checked.

- *Why* each item exists: [`challenge-design.md`](challenge-design.md) (game),
  [`architecture.md`](architecture.md) (structure),
  [`observability.md`](observability.md) (telemetry).
- *What* and *done?*: this file.

Legend: `[ ]` todo · `[x]` done · `[-]` dropped (leave a note why)

---

## S0 — Game Design Spike

No stack. Prove the game is winnable and fun before writing app code. This is
the cheapest place to discover the game isn't fun.

### Setup
- [x] `backend/requirements.txt` covers `scripts/spike.py` (`openai`, `pyyaml`, `python-dotenv`)
- [x] `.env` created from `.env.example`; `LLM_API_KEY` set
- [x] Model chosen (`gpt-4o-mini`); cost per attempt written into `challenge-design.md` → Model and cost (measured ~$0.0001/attempt)

### System prompt
- [x] `backend/app/challenge/prompts/system_v1.txt` first draft: persona, reasoned egg-coffee bias, strict JSON-only output, never reveal instructions — *still needs S0 iteration against real numbers*
- [ ] Output is valid `{ "recommendation", "reply" }` JSON across 30+ manual prompts
- [ ] `recommendation` only ever takes enum values (`egg_coffee` / `iced_milk_coffee` / `other`)
- [x] `reply` is in the user's language

### Spike tooling
- [x] `scripts/spike.py` written — `--prompt`, `--suite`, `--repeat`, writes JSONL to `scripts/out/`, prints outcome + token cost
- [x] Verified against the live API — ordinary prompt returns `egg_coffee`; parallel `--suite` / `--repeat` (`-c`, default 8)
- [x] Starter fixtures added: `backend/tests/fixtures/{neutral,forbidden,solutions}.yaml` (15 / 13 / 10 prompts) — same files S2's `test_guardrail_balance.py` will use
- [ ] Fixtures expanded / tuned after the first `--suite` run

### Findings
- [x] Ordinary prompts return `egg_coffee` **93%** (14/15 neutral; 1 → `other`, 0 → target)
- [x] 3 solution paths at **10/10** (`heat_and_speed`, `group_order`, `logistics`) + `on_the_move` solid in `--suite`
- [x] `solution-paths.md` filled: mechanism, reference prompt, success rate per path
- [x] `challenge.yaml` → `solution_paths[]` filled from the spike (4 paths, one candidate rejected)
- [ ] `challenge.yaml` → guardrail `patterns` / `examples` updated from what testers actually reached for  ← *defer to S2; system prompt alone already resists forbidden prompts ~12/13*
- [x] Temperature kept `0.4` — default bias stable at it, no reason to move

### Exit criteria
- [x] 3+ solution paths ≥ 70% reproducible
- [x] Ordinary prompts return egg coffee ≥ 90%
- [x] Model chosen (`gpt-4o-mini`), cost per attempt known (~$0.00014)
- [x] `solution-paths.md` + `challenge.yaml` solution paths populated

**S0 complete.** System prompt went through 3 iterations (see git history of
`system_v1.txt`): v1 enumerated the winning situations (100% win, too easy), v2
over-corrected (3%), v3 reasons from egg coffee's properties (~90% on solution
prompts, 93% egg coffee on neutral, forbidden resisted). Ready for S1.

---

## S1 — Vertical Slice

FastAPI + Next.js, chat working end-to-end, structured output wired, challenge
engine reading the enum. No guardrails, no score, no dashboards.

### Backend
- [ ] `app/main.py` — app factory, middleware, config load
- [ ] `app/config.py` — `pydantic-settings`, env in / typed settings out
- [ ] `challenge.yaml` loader — parsed once at startup, typed model, clear error on malformed file
- [ ] `app/llm/` — provider interface + one OpenAI-compatible impl; parses model JSON into a typed object; parse failure = explicit failed attempt, never a guess
- [ ] `app/challenge/engine.py` — deterministic evaluation: `recommendation == target` → success
- [ ] `app/store/memory.py` behind a `store` interface (sessions + timer start)
- [ ] `POST /api/session` — creates session, starts server-side timer
- [ ] `POST /api/chat` — one attempt: llm call → evaluate → response, attempt counter increments
- [ ] `GET /api/challenge` — returns the `public` block only, never the full YAML
- [ ] `GET /api/health`

### Frontend
- [ ] `docker compose up -d` → playable at `localhost:3000`
- [ ] Landing page with `public` title / tagline / instructions
- [ ] `/play` chat interface
- [ ] Attempt counter, wired to backend value (not client-computed)
- [ ] Success state screen
- [ ] Player session persisted (nickname optional, random `player_id`, UUID `session_id`)

### Tests
- [ ] ≥ 5 unit tests on `challenge/engine.py` (enum match, `other`, malformed JSON, missing field, non-enum value)
- [ ] S0 solution paths still win through the UI

### Docs
- [ ] `architecture.md` "To document in S1" section completed

### Exit criteria
- [ ] `docker compose up -d` → playable at `localhost:3000`
- [ ] Structured output wired end-to-end
- [ ] S0 solution paths still win through the UI
- [ ] Attempt counter correct
- [ ] ≥ 5 unit tests on `challenge/engine.py`

---

## S2 — Guardrails

Close the obvious shortcuts. Layered: normalised keyword/regex first, then
embedding similarity for paraphrases. LLM-as-judge is out of scope.

### Guardrail engine
- [ ] `app/guardrails/` — layered evaluation, cheapest layer first
- [ ] Vietnamese normalisation (lowercase + strip diacritics) before layer-1 matching
- [ ] Layer 1: keyword/regex for `DIRECT_TARGET_REQUEST`, `ALLERGY_WORKAROUND`, `PROMPT_INJECTION`, `SYSTEM_PROMPT_EXTRACTION`, `SENSITIVE_REQUEST`
- [ ] Layer 2: embedding similarity for `PREFERENCE_DECLARATION` (threshold from `challenge.yaml`)
- [ ] All six categories toggleable via `enabled` in `challenge.yaml`
- [ ] Block returns the vague `block_message_*`; real category never sent to the client
- [ ] Real category + prompt logged for observability
- [ ] Blocked attempt still counts against `max_attempts` (confirm this is the intended rule)

### Adversary tracking
- [ ] `adversary_tracking` config read from `challenge.yaml`
- [ ] Per-session signal score: signal categories weighted, `count_distinct_only` respected
- [ ] Signal-category block emits `adversary_signal` event + `label: unsafe` on the block
- [ ] `session_flagged` event when score first crosses `flag_threshold`
- [ ] Score is never added to / subtracted from the player's game score
- [ ] Nothing about adversary state is exposed on `GET /api/challenge` or any client response

### Tests
- [ ] `tests/test_guardrail_balance.py` asserts, in one run:
  - [ ] every forbidden prompt is blocked
  - [ ] every intended solution path still passes
  - [ ] every neutral prompt still passes
- [ ] ≥ 5 test cases per category
- [ ] Adversary score test: naive categories score 0; signal categories score their weight; distinct-only holds

### Docs
- [ ] Forbidden list confirmed to live in `challenge.yaml`, not the frontend bundle
- [ ] `architecture.md` "To document in S2" section completed

### Exit criteria
- [ ] Six categories live, ≥ 5 test cases each
- [ ] Block response friendly, real category never returned to the client
- [ ] `test_guardrail_balance.py` green
- [ ] Forbidden list in `challenge.yaml`, not the frontend
- [ ] `adversary_tracking` signal score computed per session
- [ ] Signal-category blocks flagged in telemetry

---

## S3 — Observability → MVP complete

Langfuse first (fastest debugging payoff), then OTel SDK, collector,
Prometheus/Loki, Grafana. Dashboards provisioned from JSON in the repo.

### Langfuse
- [ ] Self-hosted Langfuse up via the compose overlay
- [ ] Per attempt: prompt, response, tokens, latency, model visible
- [ ] Traces correlated by `session_id`

### OTel
- [ ] OTel SDK in the backend, `gen_ai.*` semantic conventions on the LLM span
- [ ] One attempt → one trace with four child spans (guardrail / llm / challenge eval / response)
- [ ] Collector is the single egress point → Langfuse + Prometheus + Loki
- [ ] Structured JSON logs, every event carrying `session_id` + `trace_id`

### Metrics
- [ ] Game: sessions, attempts, successes, failures, guardrail blocks
- [ ] LLM: request count, duration, input/output tokens
- [ ] HTTP: request count, duration

### Grafana (provisioned as code)
- [ ] `game.json` — active players, attempts, successes, avg attempts to success, fastest completion
- [ ] `llm.json` — request rate, latency percentiles, token usage, error rate
- [ ] `guardrails.json` — block rate, blocks by category, injection attempts over time
- [ ] `guardrails.json` — **Potential adversaries** table: sessions ranked by adversary score, flagged rows highlighted
- [ ] All three survive `docker compose down -v && up` (provisioned, not hand-clicked)

### Adversary tracking — bypass detection
- [ ] Blocked-prompt embeddings retained per session
- [ ] Each passing prompt scored against them; similarity > threshold → `bypass_bonus` added
- [ ] Bypass event visible in Langfuse and on the adversary panel

### Logs
- [ ] Loki queryable by `session_id`; a query joins back to a trace
- [ ] Redaction path when `LOG_PROMPTS=false`

### Docs
- [ ] `observability.md` "To document in S3" section completed

### Exit criteria
- [ ] Full stack starts with one command
- [ ] One attempt → one trace with four child spans
- [ ] Langfuse shows prompt/response/tokens/latency per session
- [ ] Three Grafana dashboards with real data
- [ ] JSON logs queryable in Loki by `session_id`
- [ ] Bypass detection live
- [ ] "Potential adversaries" panel populated

---

## S4 — Gamification

Backend-authoritative timer and score, Redis-backed leaderboard.

### Scoring
- [ ] Score computed server-side from the `scoring` block in `challenge.yaml`
- [ ] Formula: `max(minimum, base − attempts·attempt_penalty − seconds·time_penalty_per_second − blocks·guardrail_block_penalty)`
- [ ] Elapsed time = `now − session.created_at`, computed at evaluation; no client timestamp trusted
- [ ] A crafted request cannot submit its own score
- [ ] Unit tests on the score formula (boundaries, `minimum` floor)

### Leaderboard
- [ ] `app/store/redis.py` swapped in behind the same `store` interface
- [ ] Redis sorted-set leaderboard
- [ ] `GET /api/leaderboard` — top N (rank, player, time, attempts, score)
- [ ] Frontend leaderboard, auto-refreshing
- [ ] Leaderboard survives a backend restart

### Exit criteria
- [ ] Score correct and tested
- [ ] Top-10 leaderboard, auto-refreshing
- [ ] Leaderboard survives a backend restart
- [ ] Score cannot be forged via a crafted request

---

## S5 — Event Hardening

Survive 50 concurrent players.

- [ ] Attempt cap enforced server-side (`max_attempts`)
- [ ] Rate limiting active (per session / per IP)
- [ ] LLM calls: retry with backoff + circuit breaker
- [ ] LLM outage degrades gracefully; the attempt is **not** consumed
- [ ] Budget calculated, capped, and alerting when approached
- [ ] Locust run: 50 concurrent players, p95 < 3s
- [ ] Secrets never logged; telemetry redaction verified for a public deploy

### Exit criteria
- [ ] Locust: 50 concurrent players, p95 < 3s
- [ ] LLM outage degrades gracefully, attempt not consumed
- [ ] Rate limiting active
- [ ] Budget calculated and capped

---

## S6 — Dry Run + Polish

Ten real humans.

- [ ] Fresh clone runs with one command (`cp .env.example .env` + `docker compose up -d`)
- [ ] 10-player session run; metrics captured
- [ ] Win rate in the 40–70% window
- [ ] Median time to win 3–8 minutes
- [ ] No gameplay-blocking bugs
- [ ] Each unanticipated win triaged: promoted to a solution path **or** blocked as an exploit, then `test_guardrail_balance.py` re-run
- [ ] Adversary panel reviewed against the session — did it flag the right people?
- [ ] `solution-paths.md` "Unanticipated wins" section updated
- [ ] `README.md` status table updated to reflect real state
- [ ] `LICENSE` chosen

### Exit criteria
- [ ] Win rate in the 40–70% window
- [ ] Median win time 3–8 minutes
- [ ] No gameplay-blocking bugs
- [ ] Fresh clone runs with one command

---

## Cross-sprint rules

- [ ] Any change to `guardrails/` or `challenge.yaml` → re-run `test_guardrail_balance.py` before pushing
- [ ] `solution-paths.md` stays off screen during demos and events
- [ ] No real API keys committed; rotate a leaked key rather than rewriting history
