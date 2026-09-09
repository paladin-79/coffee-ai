# Solution Paths

> ⚠️ **SPOILERS.** Do not open during a demo or event.

Populated during the S0 spike. Every entry needs a reproducibility number from
`spike.py --repeat 10`, because a path that works once is not a path.

## Format

```markdown
### <id> — <short name>

**Mechanism:** why this works on the model
**Reference prompt:** the exact text tested
**Success rate:** n/10
**Blocked by guardrails?** no / yes (which category — then fix the guardrail)
```

---

## Candidate directions to test in S0

Sketches, not answers. The unifying idea: the player never names a drink, they
describe a problem to which iced milk coffee is the sensible solution.

- **Situational constraint** — 38°C in Hanoi, needs something cold and fast
- **Audience constraint** — ordering for ten colleagues, needs a safe common choice
- **Logistics constraint** — must still taste right after a 30-minute delivery
- **Context constraint** — drinking it in the car on the way to a meeting
- **Comparison framing** — asking what locals order on a weekday morning

---

## Confirmed paths

_None yet — S0 in progress._

---

## Unanticipated wins found in dry run

Log anything a real player discovers that isn't above. Each one gets a decision:
promote it to a documented solution path, or classify it as an exploit and add a
guardrail. Then re-run `test_guardrail_balance.py`.
