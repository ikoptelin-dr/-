"""Импорт результатов веб-поиска, выполненного разработчиком (data/raw/websearch_discovery_*.json).

Это не автоматический сбор с площадок: в записи есть только заголовок и URL из поисковой выдачи.
Текст, комментарии, даты и реакции отсутствуют, кроме того, что видно в самом заголовке."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

from ..models import Discussion
from ..urls import external_id, host_of

JUNK_TITLE = re.compile(
    r"^(<style>|please enable javascript|picky logo|doctors note logo|iklan|create a free|··· |www\.|[a-z0-9.-]+\.(ru|com|ua|org)$|review \d+$|may \d+, \d{4}$)",
    re.I,
)
REPLIES = re.compile(r"\s*-\s*([\d\s ]+)\s+ответ\w*\s+на форуме woman\.ru\s*\(\d+\)\s*$", re.I)
ANSWERS = re.compile(r"\s*—\s*(\d+)\s+ответ\w*\s+(врача|косметолога|дерматолога)\w*\s+на вопрос\s*№\d+\s*$", re.I)


def domain_map(sources: list[dict]) -> dict[str, str]:
    out = {}
    for s in sources:
        out[host_of(s["url"])] = s["id"]
    out["community.realself.com"] = "realself"
    out["uk.theinkeylist.com"] = "web:theinkeylist.com"
    return out


def load(path: str | Path, sources: list[dict]) -> Iterator[tuple[dict, Discussion | None]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    dmap = domain_map(sources)
    for search in raw["searches"]:
        if search["status"] != "ok":
            yield search, None
            continue
        for rank, res in enumerate(search["results"], 1):
            url = res["url"]
            host = host_of(url)
            source_id = dmap.get(host) or f"web:{host}"
            title = (res.get("title") or "").strip()
            reactions: dict = {}
            m = REPLIES.search(title)
            if m:
                reactions = {"replies": int(re.sub(r"\D", "", m.group(1))), "replies_source": "title_in_search_result"}
                title = title[: m.start()].strip()
            m = ANSWERS.search(title)
            if m:
                reactions = {"expert_answers": int(m.group(1)), "replies_source": "title_in_search_result"}
                title = title[: m.start()].strip()
            title = re.sub(r"\s*-\s*Beauty Insider Community$|\s*\|\s*Skin Concern$|\s*—\s*Acne\.org$|\s*-\s*Acne\.org$", "", title)
            flags = {}
            if not title or JUNK_TITLE.search(title):
                flags["title_missing"] = True
                title = ""
            yield search, Discussion(
                source_id=source_id,
                external_id=external_id(url),
                url=url,
                collected_at=raw["collected_at"],
                discovery={
                    "adapter": "websearch_import",
                    "dataset": Path(path).name,
                    "search_id": search["id"],
                    "query": search["query"],
                    "allowed_domains": search["allowed_domains"],
                    "rank": rank,
                },
                title=title or None,
                reactions=reactions,
                flags=flags,
                is_synthetic=bool(raw.get("is_synthetic", False)),
            )
