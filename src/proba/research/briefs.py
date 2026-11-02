"""Исследовательские задания на доказательные статьи по кластерам спроса.

Цепочка сохраняется: обсуждения (URL) → кластер → задание (topic 0.1.0) → [следующий этап: источники →
утверждения → статья → медицинская рецензия]. Популярность темы не определяет вывод: в задании явно
требуется показать отсутствие или противоречивость доказательств."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def build(tasks_path: Path, clusters: list[dict], schema_path: Path) -> tuple[list[dict], list[str]]:
    cfg = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")), format_checker=FormatChecker())
    by_id = {c["id"]: c for c in clusters}
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    briefs, errors = [], []
    for t in cfg["tasks"]:
        c = by_id.get(t["cluster_id"])
        if not c:
            errors.append(f"{t['id']}: кластер {t['cluster_id']} не найден")
            continue
        topic = {
            "schema_version": "0.1.0", "id": t["id"], "is_synthetic": False, "specialty": "cosmetology",
            "language": "ru", "audience": "professionals", "title": t["title"], "question": t["question"],
            "inclusion_criteria": t["inclusion_criteria"], "exclusion_criteria": t["exclusion_criteria"],
            "status": "queued", "created_at": created,
        }
        for err in validator.iter_errors(topic):
            errors.append(f"{t['id']}: topic не проходит схему: {err.message}")
        o = c["observations"]
        briefs.append({
            "topic": topic,
            "demand_evidence": {
                "cluster_id": c["id"], "cluster_name": c["name"],
                "unique_discussions": o["unique_discussions_any"], "sources": o["sources"], "languages": o["languages"],
                "what_people_want": c["what_people_want"],
                "example_discussions": [{"title": e["title"], "url": e["url"]} for e in o["examples"][:6]],
                "confidence": c["confidence"], "limitations": c["limitations"],
            },
            "audience_expectations": t["audience_expectations"],
            "search_plan": {
                "pubmed_query_draft": c["hypotheses"]["pubmed_query_draft"],
                "also_check": t.get("also_check", []),
                "status": "не выполнен: адаптер научного поиска — следующий этап; eutils.ncbi.nlm.nih.gov закрыт сетевой политикой",
            },
            "must_show": [
                "где доказательств нет или они противоречивы — прямо в тексте",
                "различие in vitro / клинических данных и переносимость на конкретную форму и дозу",
                "что из ожиданий аудитории не подтверждается",
            ],
            "next_stage": ["источники (source 0.1.0)", "карта утверждений", "статья (article 0.1.0)",
                           "медицинская рецензия человеком", "производные посты и видео — только из проверенной статьи"],
            "selection_rationale": t["selection_rationale"],
        })
    return briefs, errors


def to_markdown(briefs: list[dict]) -> str:
    out = ["# Задания на доказательные статьи (проект)", "",
           "Статус: **задания сформированы, источники не искались, статьи не написаны.** Выбор тем — предложение для владельца.", ""]
    for b in briefs:
        t, d = b["topic"], b["demand_evidence"]
        out += [f"## {t['id']}: {t['title']}", "", f"**Исследовательский вопрос.** {t['question']}", "",
                f"**Почему эта тема.** {b['selection_rationale']}", "",
                f"**Спрос (наблюдение).** Кластер {d['cluster_id']} «{d['cluster_name']}»: {d['unique_discussions']} обсуждений, "
                f"площадки: {', '.join(f'{k} ({v})' for k, v in d['sources'].items())}; языки: {', '.join(f'{k} ({v})' for k, v in d['languages'].items())}. "
                f"Уверенность: {d['confidence']}.", "", "Что хотят узнать:", ""]
        out += [f"- {w}" for w in d["what_people_want"]] + ["", "Ожидания аудитории — гипотезы по заголовкам и сводкам поиска; подтвердить по текстам обсуждений, затем сверить с доказательствами:", ""]
        out += [f"- {x}" for x in b["audience_expectations"]] + ["", "Примеры обсуждений:", ""]
        out += [f"- [{e['title']}]({e['url']})" for e in d["example_discussions"]]
        out += ["", "Критерии включения: " + "; ".join(t["inclusion_criteria"]) + ".",
                "Критерии исключения: " + "; ".join(t["exclusion_criteria"]) + ".", "",
                f"Черновая стратегия PubMed: `{b['search_plan']['pubmed_query_draft']}`", "",
                "Обязательно показать: " + "; ".join(b["must_show"]) + ".", ""]
    return "\n".join(out) + "\n"
