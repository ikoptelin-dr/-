"""Модель записи обсуждения. Одна запись = одно обсуждение (ветка, вопрос, отзыв) на площадке."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Discussion:
    source_id: str                 # id из config/sources.yaml
    external_id: str               # устойчивый ключ на площадке (id ветки или канонический URL)
    url: str                       # исходная ссылка, как получена
    collected_at: str              # дата/время сбора (RFC 3339 или дата)
    discovery: dict[str, Any]      # как найдено: адаптер, запрос, id поиска
    title: str | None = None
    text: str | None = None        # полный текст хранится только если это разрешено условиями площадки
    excerpt: str | None = None     # разрешённое краткое извлечение
    published_at: str | None = None
    language: str | None = None
    comments: list[dict[str, Any]] = field(default_factory=list)  # структура обсуждения, без профилей авторов
    reactions: dict[str, Any] = field(default_factory=dict)       # например {"replies": 25, "replies_source": "title"}
    flags: dict[str, Any] = field(default_factory=dict)           # kind, audience, ad, title_from_url и т.п.
    is_synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Discussion":
        return cls(**data)
