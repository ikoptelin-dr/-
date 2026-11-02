"""Публикация в собственные аккаунты X/Threads через outbox.

СТАТУС: реализовано и проверено только тестами с подменённым транспортом. Живые вызовы не выполнялись:
публикация выключена, аккаунты не подключены, сеть закрыта. Публиковать — только с явного разрешения владельца.

Защиты: глобальный выключатель и стоп-файл; ключ идемпотентности draft:version:channel; одобрение редактора
привязано к SHA-256 текста; черновик с медицинскими утверждениями требует отдельной отметки медицинского
рецензента (другой человек); тайм-аут не считается успехом — запись уходит на сверку, слепого повтора нет.
Локальные отметки approve/review — не аутентификация; продакшн-авторизация — отдельный этап backlog."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..demand.http import Response
from ..demand.store import now

Transport = Callable[[str, str, dict[str, str], bytes | None, float], Response]

SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    draft_id TEXT, version INTEGER, text_sha256 TEXT, role TEXT, person TEXT, at TEXT,
    PRIMARY KEY (draft_id, version, role)
);
CREATE TABLE IF NOT EXISTS outbox (
    idem_key TEXT PRIMARY KEY, draft_id TEXT, version INTEGER, channel TEXT, text_sha256 TEXT,
    parts TEXT, scheduled_at TEXT, status TEXT, external_ids TEXT, attempts INTEGER DEFAULT 0,
    last_error TEXT, updated_at TEXT
);
"""


class PublishRefused(Exception):
    pass


class Outbox:
    def __init__(self, path: str | Path, channels_cfg: dict, root: Path):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self.cfg = channels_cfg
        self.root = root

    # --- действия людей -----------------------------------------------------
    def approve(self, draft: dict, role: str, person: str) -> None:
        if role not in ("editor", "medical_reviewer"):
            raise PublishRefused(f"неизвестная роль {role}")
        other = "medical_reviewer" if role == "editor" else "editor"
        row = self.db.execute("SELECT person FROM approvals WHERE draft_id=? AND version=? AND role=?",
                              (draft["id"], draft["version"], other)).fetchone()
        if row and row[0] == person:
            raise PublishRefused("редактор и медицинский рецензент должны быть разными людьми")
        self.db.execute("INSERT OR REPLACE INTO approvals VALUES (?,?,?,?,?,?)",
                        (draft["id"], draft["version"], draft["text_sha256"], role, person, now()))
        self.db.commit()

    def enqueue(self, draft: dict, scheduled_at: str) -> str:
        key = f"{draft['id']}:{draft['version']}:{draft['channel']}"
        self.db.execute(
            "INSERT OR IGNORE INTO outbox VALUES (?,?,?,?,?,?,?,'scheduled',NULL,0,NULL,?)",
            (key, draft["id"], draft["version"], draft["channel"], draft["text_sha256"],
             json.dumps(draft["parts"], ensure_ascii=False), scheduled_at, now()))
        self.db.commit()
        return key

    # --- проверки -------------------------------------------------------------
    def blockers(self, draft: dict, env: dict[str, str]) -> list[str]:
        out = []
        if not self.cfg.get("publishing_enabled"):
            out.append("публикация выключена (publishing_enabled: false)")
        if (self.root / self.cfg["stop_file"]).exists():
            out.append("очередь остановлена стоп-файлом")
        ch = self.cfg["channels"].get(draft["channel"], {})
        if not ch.get("enabled"):
            out.append(f"канал {draft['channel']} выключен")
        if not all(c["fits"] for c in draft["length_checks"]):
            out.append("текст длиннее лимита площадки")
        if draft.get("is_synthetic"):
            out.append("синтетический материал не публикуется")
        need = ["editor"] + (["medical_reviewer"] if draft.get("medical_claims") else [])
        for role in need:
            row = self.db.execute("SELECT text_sha256 FROM approvals WHERE draft_id=? AND version=? AND role=?",
                                  (draft["id"], draft["version"], role)).fetchone()
            if not row:
                out.append(f"нет отметки {role}")
            elif row[0] != draft["text_sha256"]:
                out.append(f"отметка {role} относится к другому тексту — нужна повторная проверка")
        creds = {"x": ["X_USER_ACCESS_TOKEN"], "threads": ["THREADS_USER_ID", "THREADS_PUBLISH_TOKEN"]}[draft["channel"]]
        missing = [k for k in creds if not env.get(k)]
        if missing:
            out.append("не подключён аккаунт: " + ", ".join(missing))
        return out

    # --- выполнение -------------------------------------------------------------
    def publish_due(self, drafts: dict[str, dict], env: dict[str, str], transport: Transport, at: str | None = None) -> list[dict[str, Any]]:
        at = at or datetime.now(timezone.utc).isoformat()
        results = []
        rows = self.db.execute("SELECT idem_key, draft_id, channel FROM outbox WHERE status='scheduled' AND scheduled_at<=?", (at,)).fetchall()
        for key, draft_id, channel in rows:
            draft = drafts[draft_id]
            reasons = self.blockers(draft, env)
            if reasons:
                results.append({"key": key, "status": "blocked", "reasons": reasons})
                continue
            self._set(key, "sending")
            try:
                ids = (_publish_x if channel == "x" else _publish_threads)(draft["parts"], env, transport)
                self._set(key, "published", external_ids=ids)
                results.append({"key": key, "status": "published", "external_ids": ids})
            except TimeoutError as e:
                # результат неизвестен: не повторяем вслепую, требуется сверка с аккаунтом
                self._set(key, "needs_reconciliation", error=str(e))
                results.append({"key": key, "status": "needs_reconciliation"})
            except Exception as e:  # noqa: BLE001 — ошибка площадки сохраняется в outbox
                self._set(key, "failed", error=str(e))
                results.append({"key": key, "status": "failed", "error": str(e)})
        return results

    def _set(self, key: str, status: str, external_ids: list[str] | None = None, error: str | None = None) -> None:
        self.db.execute("UPDATE outbox SET status=?, external_ids=COALESCE(?, external_ids), attempts=attempts+1, last_error=?, updated_at=? WHERE idem_key=?",
                        (status, json.dumps(external_ids) if external_ids else None, error, now(), key))
        self.db.commit()

    def status(self) -> list[tuple]:
        return self.db.execute("SELECT idem_key, status, attempts, last_error FROM outbox ORDER BY idem_key").fetchall()


def _publish_x(parts: list[str], env: dict[str, str], transport: Transport) -> list[str]:
    ids: list[str] = []
    for p in parts:
        body: dict[str, Any] = {"text": p}
        if ids:
            body["reply"] = {"in_reply_to_tweet_id": ids[-1]}
        r = transport("POST", "https://api.x.com/2/tweets",
                      {"Authorization": f"Bearer {env['X_USER_ACCESS_TOKEN']}", "Content-Type": "application/json"},
                      json.dumps(body).encode(), 30)
        if r.status not in (200, 201):
            raise RuntimeError(f"x: статус {r.status}")
        ids.append(r.json()["data"]["id"])
    return ids


def _publish_threads(parts: list[str], env: dict[str, str], transport: Transport) -> list[str]:
    from urllib.parse import urlencode
    uid, token = env["THREADS_USER_ID"], env["THREADS_PUBLISH_TOKEN"]
    ids: list[str] = []
    for p in parts:
        params = {"media_type": "TEXT", "text": p, "access_token": token}
        if ids:
            params["reply_to_id"] = ids[-1]
        r = transport("POST", f"https://graph.threads.net/v1.0/{uid}/threads?" + urlencode(params), {}, None, 30)
        if r.status != 200:
            raise RuntimeError(f"threads: контейнер не создан ({r.status})")
        creation_id = r.json()["id"]
        r = transport("POST", f"https://graph.threads.net/v1.0/{uid}/threads_publish?" +
                      urlencode({"creation_id": creation_id, "access_token": token}), {}, None, 30)
        if r.status != 200:
            raise RuntimeError(f"threads: публикация не выполнена ({r.status})")
        ids.append(r.json()["id"])
    return ids
