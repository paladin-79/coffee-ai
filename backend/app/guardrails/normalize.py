"""Text normalisation applied before layer-1 matching.

Players type Vietnamese with or without diacritics, in any case, with any
punctuation. `sữa đá`, `Sữa Đá`, `sua da` and `sữa-đá!!!` are the same attempt
at the same shortcut, so all four have to hit the same rule.

Patterns in ``challenge.yaml`` go through the exact same function, which is why
they are written undiacriticised: normalising both sides means a pattern author
never has to think about accents.
"""

from __future__ import annotations

import re
import unicodedata

# đ / Đ are distinct Vietnamese letters, not a base letter plus a combining
# mark, so NFD decomposition leaves them alone. Map them by hand.
_D_STROKE = str.maketrans({"đ": "d", "Đ": "d"})

# Any run of non-word characters becomes a single space. Unicode-aware, so it
# keeps Vietnamese letters intact when diacritics are being preserved.
_SEPARATORS = re.compile(r"[\W_]+", re.UNICODE)


def strip_diacritics(text: str) -> str:
    """``Cà Phê Sữa Đá`` -> ``Ca Phe Sua Da``."""
    decomposed = unicodedata.normalize("NFD", text.translate(_D_STROKE))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(text: str, *, strip_marks: bool = True) -> str:
    """Lowercase, optionally strip Vietnamese diacritics, and collapse every run
    of punctuation and whitespace into a single space.

    Collapsing punctuation is what lets the literal pattern ``egg free`` match
    ``egg-free`` and ``sua da`` match ``sữa đá!!!``.

    ``strip_marks`` follows ``guardrails.normalize_vietnamese`` in the rules
    file; with it off, accented text is matched as typed.
    """
    text = text.lower()
    if strip_marks:
        text = strip_diacritics(text)
    return _SEPARATORS.sub(" ", text).strip()
