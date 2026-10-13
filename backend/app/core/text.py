"""Small text helpers shared across seed and admin."""
from __future__ import annotations

import re

_TRANSLIT = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
        "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y",
        "ь": "", "э": "e", "ю": "yu", "я": "ya", " ": "-",
    }
)


def slugify(value: str) -> str:
    """Lowercase, transliterate Cyrillic and reduce to a URL-safe slug.

    Backwards-compatible with the seed's previous ``_slug`` for its inputs
    (simple latin/cyrillic words) — it additionally strips stray punctuation and
    collapses repeated dashes so admin-entered values produce clean slugs.
    """
    base = value.lower().translate(_TRANSLIT)
    base = re.sub(r"[^a-z0-9-]+", "-", base)
    return re.sub(r"-{2,}", "-", base).strip("-")
