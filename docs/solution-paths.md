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

S0 spike, 2026-09-10 — `system_v1.txt`, `gpt-4o-mini`, `temperature: 0.4`,
measured with `spike.py --repeat 10` (or the `--suite` run where noted). The
unifying trick: none of these prompts name a drink; each describes a situation
that genuinely conflicts with what egg coffee *is* (warm, slow to make, sipped
seated, rich).

### heat_and_speed — too hot, in a hurry

**Mechanism:** egg coffee is served warm and takes minutes to prepare; "38°C and
in a rush" conflicts with both. The model switches to something cold and quick.
**Reference prompt:** `Hà Nội đang nắng 38 độ, tôi đang vội, cần thứ gì đó uống thật nhanh cho tỉnh táo.`
**Success rate:** 10/10
**Blocked by guardrails?** no

### group_order — ordering for a group

**Mechanism:** framed as needing a "safe common denominator" for ten people, the
model treats cà phê sữa đá as the universally acceptable choice and egg coffee
as the acquired taste.
**Reference prompt:** `Tôi đặt cà phê cho 10 đồng nghiệp trong phòng, cần một loại mà hầu như ai cũng uống được.`
**Success rate:** 10/10
**Blocked by guardrails?** no

### logistics — must survive a long delivery

**Mechanism:** egg foam is best fresh; "30-minute delivery, still tastes right"
makes egg coffee a poor fit and iced milk coffee the robust option.
**Reference prompt:** `Tôi đặt ship cà phê, khoảng 30 phút nữa mới tới nơi, loại nào để lâu vẫn còn ngon?`
**Success rate:** 10/10
**Blocked by guardrails?** no

### on_the_move — drinking it in transit

**Mechanism:** "in the car, on the way to a meeting, easy to hold" cues
portability, which egg coffee (sipped seated, from a small cup) does not offer.
**Reference prompt:** `Tôi sẽ uống trên xe khi đang di chuyển tới cuộc họp, cần loại gọn gàng, dễ cầm.`
**Success rate:** wins consistently in `--suite`; not yet run at `--repeat 10`
**Blocked by guardrails?** no

### Rejected candidate — "what do locals drink daily?"

`Người địa phương uống cà phê gì hằng ngày…` hedges between cà phê đen and cà
phê sữa đá and often lands on egg coffee anyway (~1/2). "What locals order" is
not a *conflict* with egg coffee, just a comparison, so the model has no reason
to switch. Not promoted. Keep it in `solutions.yaml` as a guardrail-balance
check only.

---

## Unanticipated wins found in dry run

Log anything a real player discovers that isn't above. Each one gets a decision:
promote it to a documented solution path, or classify it as an exploit and add a
guardrail. Then re-run `test_guardrail_balance.py`.
