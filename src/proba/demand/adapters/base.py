"""Общий интерфейс адаптеров сбора."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from ..http import HttpClient, SourceBlocked
from ..models import Discussion


@dataclass
class Page:
    items: list[Discussion]
    next_cursor: str | None  # None — запрос исчерпан


class Adapter(Protocol):
    name: str
    source_id: str
    required_env: tuple[str, ...]

    def fetch_page(self, query: str, cursor: str | None) -> Page: ...


class BaseAdapter:
    name = "base"
    source_id = "unknown"
    required_env: tuple[str, ...] = ()

    def __init__(self, http: HttpClient | None = None, env: dict[str, str] | None = None):
        self.http = http or HttpClient()
        self.env = dict(os.environ) if env is None else env

    def check_credentials(self) -> None:
        missing = [k for k in self.required_env if not self.env.get(k)]
        if missing:
            raise SourceBlocked(f"{self.name}: не заданы переменные окружения {', '.join(missing)}")
