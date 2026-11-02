"""Сквозной проход: сбор/импорт → очистка → кластеры → очередь контента → задания на статьи → выгрузка."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from .demand.adapters.websearch_import import load as load_websearch
from .demand.clean import label, mark_near_duplicates
from .demand.cluster import build_clusters
from .demand.store import Store

ROOT = Path(__file__).resolve().parents[2]


def load_config() -> tuple[dict, dict]:
    sources = yaml.safe_load((ROOT / "config/sources.yaml").read_text(encoding="utf-8"))
    lexicon = yaml.safe_load((ROOT / "config/demand_lexicon.yaml").read_text(encoding="utf-8"))
    return sources, lexicon


def import_websearch(store: Store, dataset: Path, sources: dict) -> dict[str, Any]:
    stats: Counter[str] = Counter()
    blocked = []
    for search, d in load_websearch(dataset, sources["sources"]):
        if d is None:
            blocked.append({"search_id": search["id"], "query": search["query"], "error": search.get("error")})
            continue
        stats["links"] += 1
        stats["new" if store.upsert(d) else "seen_again"] += 1
    return {"links_in_dataset": stats["links"], "new_records": stats["new"],
            "repeat_hits_merged": stats["seen_again"], "blocked_searches": blocked}


def analyze(store: Store, sources: dict, lexicon: dict) -> tuple[list, list[dict], dict]:
    src_index = {s["id"]: s for s in sources["sources"]}
    items = [label(d, lexicon, src_index) for d in store.discussions()]
    near_dups = mark_near_duplicates(items)
    clusters, excluded = build_clusters(items, lexicon)
    summary = {
        "records_after_exact_dedup": len(items),
        "near_duplicates": near_dups,
        "by_kind": dict(Counter(i.kind for i in items).most_common()),
        "by_language": dict(Counter(i.language for i in items).most_common()),
        "demand_records_in_clusters": len({i.key for i in items if not i.duplicate_of and i.concepts and i.kind in ("discussion", "question", "review") and not i.ad and i.text}),
        "excluded_from_clustering": excluded,
        "possible_ad_or_spam": sum(1 for i in items if i.ad),
        "title_from_url": sum(1 for i in items if i.title_from_url),
    }
    return items, clusters, summary


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clusters_markdown(clusters: list[dict], summary: dict, ingest: dict, meta: dict) -> str:
    clusters = sorted(clusters, key=lambda c: (-c["observations"]["unique_discussions_any"], c["id"]))
    L = ["# Кластеры спроса — первый проход", "",
         f"Дата: {meta['generated_at']}. Набор: `{meta['dataset']}`.", "",
         "**Что это.** Наблюдения по заголовкам и ссылкам реальных обсуждений, найденных веб-поиском. "
         "Тексты сообщений, комментарии, даты и реакции (кроме числа ответов в заголовках) не получены. "
         "Частота в выборке не равна объёму рынка; рост тем не оценивался.", "",
         "## Объём выборки", "",
         f"- ссылок в наборе: {ingest['links_in_dataset']}; уникальных записей после точной дедупликации: {summary['records_after_exact_dedup']}",
         f"- близких повторов: {summary['near_duplicates']}; помечено как реклама/магазин/спам: {summary['possible_ad_or_spam']}",
         f"- сигналов спроса в кластерах (обсуждения, вопросы, отзывы): {summary['demand_records_in_clusters']}",
         f"- заблокированные поиски: " + ("; ".join(f"{b['search_id']} ({b['error']})" for b in ingest["blocked_searches"]) or "нет"),
         f"- типы страниц: " + ", ".join(f"{k} {v}" for k, v in summary["by_kind"].items()),
         f"- языки: " + ", ".join(f"{k} {v}" for k, v in summary["by_language"].items()),
         "", "| Кластер | Обсуждений | Площадок | Языки | Уверенность |", "|---|---|---|---|---|"]
    for c in clusters:
        o = c["observations"]
        L.append(f"| {c['id']} {c['name']} | {o['unique_discussions_any']} (основной: {o['unique_discussions_primary']}) | {o['sources_count']} | "
                 + ", ".join(f"{k} {v}" for k, v in o["languages"].items()) + f" | {c['confidence']} |")
    for c in clusters:
        o = c["observations"]
        L += ["", f"## {c['id']}. {c['name']}", "", "**Наблюдения.**", "",
              f"- обсуждений: {o['unique_discussions_any']}, площадок: {o['sources_count']} ({', '.join(f'{k} {v}' for k, v in o['sources'].items())})",
              f"- аудитория: " + ", ".join(f"{k} {v}" for k, v in o["audience"].items()),
              f"- период: дата известна у {o['period']['with_known_date']}, неизвестна у {o['period']['without_date']}",
              "- что хотят: " + "; ".join(c["what_people_want"]), "", "Примеры:", ""]
        for e in o["examples"]:
            mark = " _(заголовок из URL)_" if e["title_from_url"] else ""
            rep = f" — ответов: {e['replies']}" if e.get("replies") else ""
            L.append(f"- [{e['title']}]({e['url']}) · {e['source']} · {e['language']}{rep}{mark}")
        L += ["", "**Гипотезы (не наблюдения).**", ""]
        L += [f"- тема публикации: {t}" for t in c["hypotheses"]["publication_topics"]]
        L += [f"- исследовательский вопрос: {c['hypotheses']['research_question']}", "",
              "**Ограничения:** " + "; ".join(c["limitations"]) + "."]
    return "\n".join(L) + "\n"


def first_pass(out_dir: Path, db_path: Path, dataset: Path, drafts_path: Path | None) -> dict:
    from datetime import datetime, timezone
    from .content.queue import export, generate_ideas, load_drafts
    from .research.briefs import build, to_markdown

    sources, lexicon = load_config()
    channels = yaml.safe_load((ROOT / "config/channels.yaml").read_text(encoding="utf-8"))
    store = Store(db_path)
    run_id = "first-pass-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    store.start_run(run_id)
    ingest = import_websearch(store, dataset, sources)
    items, clusters, summary = analyze(store, sources, lexicon)
    meta = {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "run_id": run_id,
            "dataset": dataset.name, "is_synthetic": False}
    write_json(out_dir / "discussions.json", [i.to_dict() for i in items])
    write_json(out_dir / "clusters.json", {"meta": meta, "summary": summary, "clusters": clusters})
    (out_dir / "clusters.md").write_text(clusters_markdown(clusters, summary, ingest, meta), encoding="utf-8")
    ideas = generate_ideas(clusters)
    drafts, draft_errors = (load_drafts(drafts_path, clusters, channels) if drafts_path and drafts_path.exists() else ([], []))
    export(out_dir / "queue", ideas, drafts, meta)
    briefs, brief_errors = build(ROOT / "content/research_tasks.yaml", clusters, ROOT / "schemas/topic.schema.json")
    write_json(out_dir / "research_briefs.json", briefs)
    (out_dir / "research_briefs.md").write_text(to_markdown(briefs), encoding="utf-8")
    report = {"meta": meta, "ingest": ingest, "summary": summary, "clusters": len(clusters), "ideas": len(ideas),
              "drafts": len(drafts), "draft_errors": draft_errors, "briefs": len(briefs), "brief_errors": brief_errors,
              "live_sources": "не запускались в этом проходе: хосты закрыты сетевой политикой окружения (см. config/sources.yaml access_now)",
              "costs_measured": {"llm_usd": 0, "paid_api_usd": 0, "note": "платные API и модели приложения не вызывались; стоимость веб-поиска в сессии разработки не измеряется инструментом"}}
    write_json(out_dir / "run_report.json", report)
    store.finish_run(run_id, report)
    store.close()
    return report
