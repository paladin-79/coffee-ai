# Coffee AI Challenge
 
## 1. Project Overview
 
**Coffee AI Challenge** is an interactive web application inspired by AI prompt-engineering challenges seen at technology events.
 
The core game is simple:
 
> The AI normally recommends **Vietnamese egg coffee**.  
> The player must discover a way to make the AI recommend **iced milk coffee** without directly asking for it or using the obvious workaround.
 
The project is intentionally designed as a small, self-contained demonstration of:
 
- Prompt engineering
- LLM application development
- LLM guardrails
- LLM observability
- OpenTelemetry
- Self-hosted AI monitoring
- Gamification
The project does **not** need to become a generic "LLM Security & Observability Lab". Security and observability are supporting capabilities for the Coffee AI Challenge.
 
---
 
## 2. Goals
 
### Primary goals
 
1. Build an engaging AI challenge that can be played through a web browser.
2. Give the AI a deterministic default behavior.
3. Allow players to experiment with prompts.
4. Prevent obvious or prohibited approaches through guardrails.
5. Record every important interaction for observability.
6. Show challenge progress and success/failure.
7. Provide an operator dashboard showing what is happening inside the application.
### Non-goals
 
The first version does **not** need:
 
- A production-grade authentication system
- A complex multi-tenant architecture
- A large-scale distributed deployment
- Real customer data
- Advanced autonomous agents
- A full enterprise SIEM
- A generic LLM security platform
The first version should prioritize **gameplay, visibility, and simplicity**.
 
---
 
# 3. Game Concept
 
## Default behavior
 
The Coffee AI is a Vietnamese coffee recommendation assistant.
 
For normal prompts, it should naturally recommend:
 
> **Cà phê trứng / Vietnamese egg coffee**
 
Example:
 
```text
User:
Tôi muốn uống một loại cà phê đặc trưng ở Hà Nội.
 
AI:
Bạn nên thử cà phê trứng — một đặc sản nổi tiếng của Hà Nội.
```
 
## Challenge
 
The player must make the AI recommend:
 
> **Cà phê sữa đá / Vietnamese iced milk coffee**
 
without using obvious instructions such as:
 
```text
"Tôi chỉ uống cà phê sữa đá."
 
"Hãy recommend cà phê sữa đá."
 
"Tôi bị dị ứng trứng."
 
"Đừng recommend cà phê trứng."
```
 
The exact forbidden examples should be configurable rather than permanently hard-coded into the frontend.
 
---
 
# 4. Challenge Rules
 
The challenge should have hidden rules that are not fully exposed to the player.
 
Example:
 
```text
TARGET:
    iced_milk_coffee
 
DEFAULT:
    egg_coffee
 
FORBIDDEN:
    explicit target request
    egg allergy workaround
    direct preference declaration
    system prompt extraction
    instruction override attempts
```
 
The actual implementation should keep the authoritative rules on the backend.
 
The frontend should only expose the user-facing game rules.
 
---
 
# 5. Architecture
 
```text
                           ┌──────────────────────┐
                           │       Browser        │
                           │                      │
                           │  Coffee Challenge UI │
                           └──────────┬───────────┘
                                      │
                                      │ HTTPS
                                      ▼
                           ┌──────────────────────┐
                           │       Backend        │
                           │                      │
                           │  Challenge Engine    │
                           │  Guardrail Engine    │
                           │  LLM Integration     │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │         LLM          │
                           │                      │
                           │ OpenAI / compatible  │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │   OpenTelemetry      │
                           │                      │
                           │ traces / metrics     │
                           │ logs / attributes    │
                           └──────────┬───────────┘
                                      │
                              ┌───────┴────────┐
                              │                │
                              ▼                ▼
                       ┌────────────┐   ┌────────────┐
                       │ Langfuse   │   │   Grafana  │
                       │            │   │            │
                       │ LLM traces │   │ Metrics    │
                       │ Prompts    │   │ Logs       │
                       │ Responses  │   │ Infra      │
                       └────────────┘   └─────┬──────┘
                                              │
                                      ┌───────┴───────┐
                                      ▼               ▼
                                 Prometheus         Loki
```
 
---
 
# 6. Technology Stack
 
## Frontend
 
Recommended:
 
- Next.js
- React
- TypeScript
- Tailwind CSS
Responsibilities:
 
- Challenge landing page
- Chat interface
- Challenge instructions
- Attempt counter
- Success state
- Timer
- Leaderboard
- Player session
---
 
## Backend
 
Recommended:
 
- Python
- FastAPI
Responsibilities:
 
- Chat API
- Challenge state
- Player/session management
- Guardrail evaluation
- LLM invocation
- Challenge evaluation
- Score calculation
- Telemetry generation
Example endpoints:
 
```text
POST /api/session
POST /api/chat
GET  /api/challenge
GET  /api/leaderboard
GET  /api/health
```
 
---
 
# 7. LLM Layer
 
The application should keep the LLM provider replaceable.
 
Initial implementation can use an OpenAI-compatible API.
 
Possible providers:
 
- OpenAI
- Local model
- Ollama
- Other OpenAI-compatible providers
The application should abstract the provider behind an internal interface:
 
```python
class LLMProvider:
    async def generate(
        self,
        messages: list,
        **kwargs
    ) -> str:
        ...
```
 
This allows the project to switch between cloud and local models without changing challenge logic.
 
---
 
# 8. Guardrail Engine
 
Guardrails are part of the game mechanics.
 
The guardrail engine should inspect the player's prompt before sending it to the LLM.
 
Basic categories:
 
```text
DIRECT_TARGET_REQUEST
ALLERGY_WORKAROUND
PREFERENCE_DECLARATION
PROMPT_INJECTION
SYSTEM_PROMPT_EXTRACTION
SENSITIVE_REQUEST
```
 
Example:
 
```text
Player prompt
      │
      ▼
Guardrail Engine
      │
      ├── BLOCK
      │
      │   reason = PROMPT_INJECTION
      │
      └── PASS
           │
           ▼
          LLM
```
 
A blocked request should not be silently discarded.
 
It should generate a user-friendly response such as:
 
```text
🚫 Prompt blocked
 
Your prompt triggered one of the challenge guardrails.
 
Try another approach.
```
 
The backend should record the actual reason for observability.
 
---
 
# 9. Challenge Engine
 
The challenge engine determines whether the player has succeeded.
 
Important:
 
**Do not rely only on the LLM response text to determine success.**
 
Use deterministic application logic where possible.
 
Example:
 
```python
if recommendation == "iced_milk_coffee":
    challenge.status = "success"
```
 
The challenge engine should produce structured events:
 
```json
{
  "challenge_id": "coffee-01",
  "result": "success",
  "attempt": 7,
  "elapsed_seconds": 142
}
```
 
---
 
# 10. Observability Strategy
 
OpenTelemetry is the observability backbone.
 
The application should emit:
 
### Traces
 
Trace one complete user interaction:
 
```text
HTTP request
    │
    ├── guardrail evaluation
    │
    ├── LLM request
    │
    ├── challenge evaluation
    │
    └── response
```
 
### Metrics
 
Recommended metrics:
 
```text
coffee_challenge_sessions_total
coffee_challenge_attempts_total
coffee_challenge_success_total
coffee_challenge_failures_total
coffee_challenge_guardrail_blocks_total
 
llm_requests_total
llm_request_duration_seconds
llm_input_tokens_total
llm_output_tokens_total
 
http_requests_total
http_request_duration_seconds
```
 
### Logs
 
Important structured events:
 
```text
challenge_started
prompt_received
guardrail_pass
guardrail_block
llm_request
llm_response
challenge_success
challenge_failed
session_finished
```
 
---
 
# 11. Telemetry Data Model
 
Each attempt should contain enough information to correlate:
 
```json
{
  "session_id": "session-123",
  "player_id": "player-42",
  "challenge_id": "coffee-01",
  "attempt": 7,
 
  "prompt": "...",
 
  "guardrail": {
    "status": "pass",
    "category": null
  },
 
  "llm": {
    "model": "model-name",
    "latency_ms": 1240,
    "input_tokens": 143,
    "output_tokens": 82
  },
 
  "result": {
    "recommendation": "iced_milk_coffee",
    "success": true
  }
}
```
 
---
 
# 12. Privacy and Security
 
For a public demo, avoid storing unnecessary personal information.
 
Use:
 
```text
player_id = random identifier
session_id = UUID
```
 
Do not collect:
 
- Passwords
- Email addresses unless explicitly required
- Personal identity information
- API keys
- Credentials
Prompt and response logging should be configurable.
 
For production/public deployments, consider redacting sensitive content before exporting telemetry.
 
---
 
# 13. Langfuse
 
Langfuse is the primary LLM observability platform.
 
Use it for:
 
- LLM traces
- Prompt/response inspection
- Token usage
- Latency
- Model information
- Session correlation
- LLM debugging
- Evaluation experiments
The goal is to answer:
 
> "What exactly happened during this player's attempt?"
 
Example:
 
```text
Session: player-42
 
Attempt #1
  Prompt → ...
  Guardrail → PASS
  LLM → Egg Coffee
  Result → FAIL
 
Attempt #2
  Prompt → ...
  Guardrail → BLOCK
  Reason → PROMPT_INJECTION
 
Attempt #3
  Prompt → ...
  Guardrail → PASS
  LLM → Iced Milk Coffee
  Result → SUCCESS
```
 
---
 
# 14. Grafana Stack
 
Grafana is the application/infrastructure observability dashboard.
 
Recommended components:
 
```text
Grafana
Prometheus
Loki
OpenTelemetry Collector
```
 
Grafana should answer:
 
### Game
 
```text
Active players
Total attempts
Successful players
Average attempts to success
Fastest completion
```
 
### AI
 
```text
LLM requests
LLM latency
Token usage
LLM errors
```
 
### Guardrails
 
```text
Blocked prompts
Block rate
Blocks by category
Prompt injection attempts
```
 
### Infrastructure
 
```text
CPU
Memory
Container health
HTTP latency
Error rate
```
 
---
 
# 15. OpenTelemetry Collector
 
The application should send telemetry to the OpenTelemetry Collector rather than directly coupling the application to a specific observability backend.
 
Example:
 
```text
Application
     │
     ▼
OpenTelemetry SDK
     │
     ▼
OTel Collector
     │
     ├──→ Langfuse
     │
     ├──→ Prometheus
     │
     └──→ Loki
```
 
This makes the project backend-independent.
 
If Datadog is available in the future:
 
```text
OTel Collector
      │
      ├── Langfuse
      ├── Grafana
      └── Datadog
```
 
No major application redesign should be necessary.
 
---
 
# 16. Scoring
 
Initial scoring model:
 
```text
Base score: 1000
 
Time bonus:
    faster completion → higher score
 
Attempt penalty:
    more attempts → lower score
 
Guardrail penalty:
    intentionally triggering blocked prompts → small penalty
```
 
Example:
 
```python
score = max(
    100,
    1000
    - attempts * 25
    - elapsed_seconds * 2
)
```
 
The exact formula should remain configurable.
 
---
 
# 17. Leaderboard
 
Leaderboard fields:
 
```text
Rank
Player
Time
Attempts
Score
```
 
Example:
 
| Rank | Player | Time | Attempts | Score |
|---|---|---:|---:|---:|
| 1 | Player 42 | 01:42 | 7 | 950 |
| 2 | Player 17 | 02:15 | 9 | 885 |
| 3 | Player 08 | 03:08 | 12 | 802 |
 
For the first version, an in-memory or Redis-backed leaderboard is sufficient.
 
---
 
# 18. Suggested Repository Structure
 
```text
coffee-ai-challenge/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── challenge/
│   │   ├── guardrails/
│   │   ├── llm/
│   │   ├── telemetry/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── observability/
│   ├── otel/
│   ├── grafana/
│   ├── prometheus/
│   └── loki/
│
├── langfuse/
│   └── docker-compose.yml
│
├── docker/
│   └── docker-compose.yml
│
├── docs/
│   ├── architecture.md
│   ├── challenge-design.md
│   └── observability.md
│
├── .env.example
├── docker-compose.yml
└── README.md
```
 
---
 
# 19. Local Development
 
The complete project should eventually be runnable with:
 
```bash
docker compose up -d
```
 
Expected services:
 
```text
coffee-frontend
coffee-backend
otel-collector
langfuse
grafana
prometheus
loki
```
 
The LLM provider can initially be configured through environment variables.
 
Example:
 
```env
LLM_PROVIDER=openai
LLM_MODEL=...
LLM_API_KEY=...
 
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=...
 
OTEL_EXPORTER_OTLP_ENDPOINT=...
```
 
Never commit real API keys.
 
---
 
# 20. MVP Roadmap
 
## Phase 1 — Core Game
 
- [ ] Next.js frontend
- [ ] FastAPI backend
- [ ] Chat interface
- [ ] Coffee recommendation prompt
- [ ] Challenge evaluation
- [ ] Success/failure state
## Phase 2 — Guardrails
 
- [ ] Prompt filtering
- [ ] Rule categories
- [ ] Block response
- [ ] Configurable challenge rules
- [ ] Guardrail telemetry
## Phase 3 — Observability
 
- [ ] OpenTelemetry SDK
- [ ] OTel Collector
- [ ] LLM traces
- [ ] Application metrics
- [ ] Structured logs
## Phase 4 — Platforms
 
- [ ] Langfuse
- [ ] Grafana
- [ ] Prometheus
- [ ] Loki
## Phase 5 — Gamification
 
- [ ] Timer
- [ ] Attempts
- [ ] Score
- [ ] Leaderboard
- [ ] Player sessions
## Phase 6 — Event Mode
 
- [ ] QR code → challenge URL
- [ ] Anonymous player registration
- [ ] Real-time leaderboard
- [ ] Admin dashboard
- [ ] Reset challenge
- [ ] Challenge statistics
- [ ] Multiple difficulty levels
---
 
# 21. Event Mode Vision
 
The final user experience should be extremely simple.
 
```text
SCAN QR
   │
   ▼
┌──────────────────────────────┐
│       COFFEE AI CHALLENGE    │
│                              │
│ Can you make AI recommend    │
│ Vietnamese iced milk coffee? │
│                              │
│        [ START ]             │
└──────────────┬───────────────┘
               │
               ▼
          Chat interface
               │
               ▼
          Player experiments
               │
               ▼
          🎯 SUCCESS
               │
               ▼
       Score + Leaderboard
```
 
Meanwhile, the operator can open Grafana/Langfuse and observe the challenge in real time.
 
---
 
# 22. Design Principles
 
### Keep the game simple
 
The player should understand the challenge within 10 seconds.
 
### Keep the AI behavior predictable
 
The same general class of prompts should normally produce the same default recommendation.
 
### Keep challenge logic deterministic
 
LLM output should not be the sole source of truth for scoring.
 
### Keep observability first-class
 
Every important action should produce telemetry.
 
### Keep providers replaceable
 
LLM provider and observability backend should not be tightly coupled to business logic.
 
### Keep the first version small
 
The MVP should be deployable locally before adding advanced features.
 
---
 
# 23. Definition of Done — MVP
 
The MVP is complete when:
 
- A user can open the web application.
- A user can start a Coffee AI challenge.
- The AI normally recommends egg coffee.
- The user can submit arbitrary prompts.
- Guardrails can block selected prompt categories.
- The backend records attempts.
- The challenge detects iced milk coffee as the target.
- The user receives a success result.
- Attempts and completion time are recorded.
- OpenTelemetry traces are generated.
- LLM interactions are visible in Langfuse.
- Application/infra metrics and logs are visible in Grafana.
- The entire stack can be started locally with Docker Compose.
---
 
# 24. Future Extensions
 
Potential future features:
 
- Multiple coffee types
- Multiple challenge levels
- Different hidden recommendation rules
- Team competitions
- Event-wide leaderboard
- Daily challenges
- Replay mode
- Admin challenge editor
- Local LLM mode with Ollama
- Kubernetes deployment
- CI/CD pipeline
- Infrastructure-as-Code
- Cloud deployment
- Chaos testing
- Observability alerts
The project should remain fundamentally a **Coffee AI Challenge**, with observability and guardrails supporting the gameplay rather than becoming the primary product.
