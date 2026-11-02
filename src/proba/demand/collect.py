"""Запуск сбора: контрольные точки, продолжение после остановки, лимит записей, статус «заблокировано»."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .adapters.base import Adapter
from .http import SourceBlocked, SourceError
from .store import Store


@dataclass
class SourceResult:
    adapter: str
    source_id: str
    status: str = "ok"            # ok | blocked | error | partial
    new: int = 0
    seen_again: int = 0
    pages: int = 0
    reason: str | None = None
    queries: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def collect(store: Store, adapter: Adapter, queries: list[str], max_records: int, max_pages: int = 20) -> SourceResult:
    """Собирает по запросам до max_records новых записей. Курсор сохраняется после каждой страницы,
    поэтому прерванный запуск продолжится с места остановки, а повторный — не создаст дублей."""
    res = SourceResult(adapter.name, adapter.source_id)
    for query in queries:
        cursor, done = store.get_checkpoint(adapter.name, query)
        if done:
            res.queries[query] = "done_earlier"
            continue
        pages = 0
        try:
            while pages < max_pages and res.new < max_records:
                page = adapter.fetch_page(query, cursor)
                pages += 1
                res.pages += 1
                for item in page.items:
                    if res.new >= max_records:
                        break
                    if store.upsert(item):
                        res.new += 1
                    else:
                        res.seen_again += 1
                cursor = page.next_cursor
                store.set_checkpoint(adapter.name, query, cursor, done=cursor is None)
                if cursor is None:
                    break
            res.queries[query] = "done" if cursor is None else "paused"
        except SourceBlocked as e:
            res.status, res.reason = "blocked", str(e)
            res.queries[query] = "blocked"
            break  # не повторяем и не обходим блокировку
        except SourceError as e:
            res.status, res.reason = ("partial" if res.new else "error"), str(e)
            res.queries[query] = "error"
    if res.status == "ok" and any(v == "paused" for v in res.queries.values()):
        res.status = "partial"
    return res
