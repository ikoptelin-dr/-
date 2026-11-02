"""Локальное хранилище SQLite: обсуждения без дублей, журнал запусков, контрольные точки адаптеров."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import Discussion

SCHEMA = """
CREATE TABLE IF NOT EXISTS discussions (
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    data TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    seen_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (source_id, external_id)
);
CREATE TABLE IF NOT EXISTS discovery_hits (
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    discovery TEXT NOT NULL,
    seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
    adapter TEXT NOT NULL,
    query TEXT NOT NULL,
    cursor TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (adapter, query)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    report TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # --- обсуждения -------------------------------------------------------
    def upsert(self, d: Discussion) -> bool:
        """Сохраняет запись. Возвращает True, если запись новая. Повторный сбор не создаёт дубль,
        а увеличивает seen_count и добавляет ещё один след обнаружения (происхождение не теряется)."""
        ts = now()
        cur = self.db.execute(
            "SELECT data FROM discussions WHERE source_id=? AND external_id=?",
            (d.source_id, d.external_id),
        )
        row = cur.fetchone()
        self.db.execute(
            "INSERT INTO discovery_hits VALUES (?,?,?,?)",
            (d.source_id, d.external_id, json.dumps(d.discovery, ensure_ascii=False), ts),
        )
        if row is None:
            self.db.execute(
                "INSERT INTO discussions VALUES (?,?,?,?,?,1)",
                (d.source_id, d.external_id, json.dumps(d.to_dict(), ensure_ascii=False), ts, ts),
            )
            self.db.commit()
            return True
        old = json.loads(row[0])
        merged = _merge(old, d.to_dict())
        self.db.execute(
            "UPDATE discussions SET data=?, last_seen=?, seen_count=seen_count+1 WHERE source_id=? AND external_id=?",
            (json.dumps(merged, ensure_ascii=False), ts, d.source_id, d.external_id),
        )
        self.db.commit()
        return False

    def discussions(self) -> Iterator[Discussion]:
        for (data,) in self.db.execute("SELECT data FROM discussions ORDER BY source_id, external_id"):
            yield Discussion.from_dict(json.loads(data))

    def discovery_hits(self, source_id: str, external_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT discovery FROM discovery_hits WHERE source_id=? AND external_id=? ORDER BY rowid",
            (source_id, external_id),
        )
        return [json.loads(r[0]) for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM discussions").fetchone()[0]

    # --- контрольные точки ------------------------------------------------
    def get_checkpoint(self, adapter: str, query: str) -> tuple[str | None, bool]:
        row = self.db.execute(
            "SELECT cursor, done FROM checkpoints WHERE adapter=? AND query=?", (adapter, query)
        ).fetchone()
        return (row[0], bool(row[1])) if row else (None, False)

    def set_checkpoint(self, adapter: str, query: str, cursor: str | None, done: bool) -> None:
        self.db.execute(
            "INSERT INTO checkpoints VALUES (?,?,?,?,?) ON CONFLICT(adapter, query) "
            "DO UPDATE SET cursor=excluded.cursor, done=excluded.done, updated_at=excluded.updated_at",
            (adapter, query, cursor, int(done), now()),
        )
        self.db.commit()

    # --- запуски ----------------------------------------------------------
    def start_run(self, run_id: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,NULL,NULL)", (run_id, now()))
        self.db.commit()

    def finish_run(self, run_id: str, report: dict[str, Any]) -> None:
        self.db.execute(
            "UPDATE runs SET finished_at=?, report=? WHERE run_id=?",
            (now(), json.dumps(report, ensure_ascii=False), run_id),
        )
        self.db.commit()


def _merge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Не затирает известные значения пустыми; заголовок из страницы предпочтительнее заголовка из URL."""
    out = dict(old)
    for key, value in new.items():
        if key in ("discovery", "collected_at"):
            continue  # первое обнаружение остаётся в записи, остальные — в discovery_hits
        if value in (None, "", [], {}):
            continue
        if key == "title" and old.get("title") and not old.get("flags", {}).get("title_from_url"):
            continue
        if key in ("reactions", "flags"):
            out[key] = {**old.get(key, {}), **value}
            continue
        out[key] = value
    return out
