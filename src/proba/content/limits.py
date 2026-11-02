"""Длина постов для X и Threads."""
from __future__ import annotations

import re

URL_RE = re.compile(r"https?://\S+")
# twitter-text v3: символы из этих диапазонов весят 1, остальные — 2 (шкала 100/200).
_LIGHT = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]


def x_weighted_length(text: str, url_weight: int = 23) -> int:
    total = 0
    pos = 0
    for m in URL_RE.finditer(text):
        total += _weight(text[pos:m.start()]) + url_weight
        pos = m.end()
    return total + _weight(text[pos:])


def _weight(chunk: str) -> int:
    n = 0
    for ch in chunk:
        cp = ord(ch)
        n += 1 if any(a <= cp <= b for a, b in _LIGHT) else 2
    return n


def threads_length(text: str) -> int:
    return len(text)


def check(channel: str, text: str, cfg: dict) -> tuple[bool, int, int]:
    """Возвращает (помещается, длина, лимит)."""
    if channel == "x":
        n, limit = x_weighted_length(text, cfg["url_weight"]), cfg["post_max_weighted"]
    elif channel == "threads":
        n, limit = threads_length(text), cfg["post_max_chars"]
    else:
        raise ValueError(f"неизвестный канал {channel}")
    return n <= limit, n, limit
