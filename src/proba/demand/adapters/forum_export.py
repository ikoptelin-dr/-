"""Импорт готовой выгрузки форумов (формат «forum corpus» от 2026-11-04: threads.jsonl + messages_all.jsonl).

Это не сбор с площадок: адаптер читает локальные файлы, которые владелец положил в data/raw/forums_*/
(каталог не коммитится). Одна Discussion = одна тема; сообщения лежат в comments со связью сообщение → тема.

Что сохраняется: источник, ссылка на тему и на сообщение, заголовок, даты, родитель/цитаты (только ID),
текст сообщения (локально, для разметки) и метки подготовителя выгрузки (как отдельное мнение, не истина).
Что НЕ сохраняется: ники, профили, аватары, контакты. Берём только поля из белого списка;
в тексте дополнительно маскируются e-mail, телефоны и @упоминания."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models import Discussion

ADAPTER = "forum_export"

# Белый список полей. Всё остальное (в том числе любые поля автора, если появятся в новых выгрузках) отбрасывается.
THREAD_FIELDS = ("source_id", "thread_id", "canonical_url", "title_original", "published_at", "last_observed_message_at",
                 "language_original", "audience", "completeness_status", "expected_message_count",
                 "collected_message_count", "all_pages_followed", "pages_collected")
MESSAGE_FIELDS = ("message_id", "record_id", "message_url", "published_at", "fetched_at", "parent_message_id",
                  "quoted_message_ids", "quotes_removed", "language_original", "text_status")
# Метки подготовителя выгрузки: храним под ключом export_labels, сравниваем со своей разметкой.
EXPORT_LABEL_FIELDS = ("content_role", "role_basis", "cluster_ids", "assignment_method", "audience", "audience_basis",
                       "source_audience", "duplicate_of", "possible_promotion", "analysis_eligible",
                       "counts_as_curated_need")
# Поля, которые адаптер знает (используются или осознанно не нужны). Неизвестные поля попадают в отчёт.
KNOWN_FIELDS = set(THREAD_FIELDS + MESSAGE_FIELDS + EXPORT_LABEL_FIELDS) | {
    "text_original", "thread_key", "text_sha256", "normalized_text_sha256", "page_url", "language_source_label",
    "error", "listed_reply_count", "section_url"}
PII_FIELD_HINTS = re.compile(r"author|user|nick|login|profile|avatar|email|phone|contact", re.I)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s\-()]*){10,13}(?!\d)")
MENTION = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{3,}")


class ExportFormatError(ValueError):
    pass


def scrub(text: str) -> str:
    """Маскирует контакты в тексте сообщения. Ссылки уже заменены подготовителем на [EXTERNAL_LINK]."""
    text = EMAIL.sub("[EMAIL]", text)
    text = PHONE.sub("[PHONE]", text)
    return MENTION.sub("[MENTION]", text)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ExportFormatError(f"{path.name}:{n}: не JSON ({e})") from e
    return rows


def _pick(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: row.get(k) for k in fields if k in row}


def load_export(directory: str | Path) -> tuple[list[Discussion], dict[str, Any]]:
    """Возвращает темы с сообщениями и отчёт об импорте (числа, отброшенные поля, ошибки связности)."""
    d = Path(directory)
    threads_path, messages_path = d / "threads.jsonl", d / "messages_all.jsonl"
    for p in (threads_path, messages_path):
        if not p.exists():
            raise ExportFormatError(f"нет файла {p}")
    threads = _read_jsonl(threads_path)
    messages = _read_jsonl(messages_path)

    dropped_fields = {k for row in threads + messages for k in row if k not in KNOWN_FIELDS}
    pii_like = sorted(k for k in dropped_fields if PII_FIELD_HINTS.search(k))

    by_key: dict[str, Discussion] = {}
    for t in threads:
        for req in ("source_id", "thread_id", "canonical_url"):
            if not t.get(req):
                raise ExportFormatError(f"тема без поля {req}: {t.get('thread_id')}")
        key = f"{t['source_id']}:{t['thread_id']}"
        if key in by_key:
            raise ExportFormatError(f"повтор темы {key}")
        meta = _pick(t, THREAD_FIELDS)
        by_key[key] = Discussion(
            source_id=t["source_id"],
            external_id=str(t["thread_id"]),
            url=t["canonical_url"],
            collected_at=max((m.get("fetched_at") or "" for m in messages if m.get("thread_key") == key), default="") or "unknown",
            discovery={"adapter": ADAPTER, "dataset": d.name, "thread_meta": meta},
            title=t.get("title_original"),
            published_at=t.get("published_at"),
            language=t.get("language_original"),
            flags={"audience_source": t.get("audience"), "completeness": t.get("completeness_status")},
            is_synthetic=False,
        )

    orphans = []
    seen_ids: set[str] = set()
    for m in messages:
        key = m.get("thread_key") or f"{m.get('source_id')}:{m.get('thread_id')}"
        disc = by_key.get(key)
        if disc is None:
            orphans.append(m.get("record_id"))
            continue
        rid = m.get("record_id") or f"{key}:{m.get('message_id')}"
        if rid in seen_ids:
            raise ExportFormatError(f"повтор сообщения {rid}")
        seen_ids.add(rid)
        c = _pick(m, MESSAGE_FIELDS)
        c["record_id"] = rid
        c["thread_key"] = key
        c["text"] = scrub(m.get("text_original") or "")
        c["export_labels"] = _pick(m, EXPORT_LABEL_FIELDS)
        disc.comments.append(c)
    if orphans:
        raise ExportFormatError(f"сообщения без темы: {orphans[:5]} (всего {len(orphans)})")

    for disc in by_key.values():
        disc.comments.sort(key=lambda c: (c.get("published_at") or "", c["record_id"]))
        disc.reactions = {"messages_collected": len(disc.comments)}

    report = {
        "adapter": ADAPTER,
        "dataset": d.name,
        "threads": len(by_key),
        "messages": len(seen_ids),
        "sources": sorted({x.source_id for x in by_key.values()}),
        "dropped_fields": sorted(dropped_fields),
        "dropped_pii_like_fields": pii_like,
    }
    return list(by_key.values()), report
