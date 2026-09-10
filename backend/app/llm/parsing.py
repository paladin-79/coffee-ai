"""Pull the structured fields out of the model's JSON body.

Kept separate from the provider so it can be unit-tested without a client. The
contract the system prompt asks for::

    {"recommendation": "egg_coffee" | "iced_milk_coffee" | "other",
     "reply": "<text>"}
"""

from __future__ import annotations

import json


def parse_completion_body(raw: str) -> tuple[str | None, str]:
    """Return ``(recommendation, reply)``.

    Never raises. Returns ``(None, "")`` when the body isn't a JSON object, and
    ``None`` for ``recommendation`` when the field is missing or not a string.
    A non-string / missing ``reply`` becomes ``""``.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, ""

    if not isinstance(parsed, dict):
        return None, ""

    recommendation = parsed.get("recommendation")
    reply = parsed.get("reply")
    return (
        recommendation if isinstance(recommendation, str) else None,
        reply if isinstance(reply, str) else "",
    )
