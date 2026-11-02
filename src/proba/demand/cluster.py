"""Тематические кластеры спроса по многоязычному словарю понятий (детерминированно, объяснимо).

Наблюдения (числа, ссылки, языки) отделены от гипотез (темы публикаций, исследовательский вопрос).
Частота в выборке — не объём рынка; тренд не утверждается без сравнения периодов."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .clean import DEMAND_KINDS, Labeled

DATE_IN_TITLE = re.compile(r"(\d{2}\.\d{2}\.\d{2,4}|\d{1,2} [а-я]+ \d{4}|\b(19|20)\d{2}\b)")


def eligible(it: Labeled) -> tuple[bool, str]:
    if it.duplicate_of:
        return False, "near_duplicate"
    if it.kind not in DEMAND_KINDS:
        return False, f"kind:{it.kind}"
    if it.ad:
        return False, "possible_ad_or_spam"
    if not it.text:
        return False, "no_text"
    if not it.concepts:
        return False, "no_concept_match"
    return True, "ok"


def confidence(n_unique: int, n_sources: int) -> str:
    # В проходе только по заголовкам уверенность «высокая» не присваивается.
    if n_unique >= 8 and n_sources >= 3:
        return "средняя"
    return "низкая"


def build_clusters(items: list[Labeled], lexicon: dict) -> tuple[list[dict[str, Any]], dict[str, int]]:
    defs = {c["id"]: c for c in lexicon["clusters"]}
    order = lexicon.get("primary_order") or list(defs)
    concept_to_clusters: dict[str, list[str]] = {}
    for c in lexicon["clusters"]:
        for concept in c["concepts"]:
            concept_to_clusters.setdefault(concept, []).append(c["id"])

    excluded: Counter[str] = Counter()
    members: dict[str, list[tuple[Labeled, bool]]] = {cid: [] for cid in defs}
    for it in items:
        ok, reason = eligible(it)
        if not ok:
            excluded[reason] += 1
            continue
        matched = {cid for concept in it.concepts for cid in concept_to_clusters.get(concept, [])}
        if not matched:
            excluded["no_cluster"] += 1
            continue
        primary = next(cid for cid in order if cid in matched)
        for cid in matched:
            members[cid].append((it, cid == primary))

    clusters = []
    for cid in order:
        c = defs[cid]
        mem = members[cid]
        primaries = [it for it, is_primary in mem if is_primary]
        if not mem:
            continue
        all_items = [it for it, _ in mem]
        sources = Counter(it.d.source_id for it in all_items)
        langs = Counter(it.language for it in all_items)
        audiences = Counter(it.audience for it in all_items)
        intents = Counter(i for it in all_items for i in it.intents)
        dated = [it for it in all_items if it.d.published_at or DATE_IN_TITLE.search(it.text)]
        replies = [it.d.reactions.get("replies") for it in all_items if it.d.reactions.get("replies")]
        examples = sorted(all_items, key=lambda it: (-(it.d.reactions.get("replies") or 0), it.title_from_url, it.key))[:8]
        clusters.append({
            "id": cid,
            "name": c["name"],
            "observations": {
                "unique_discussions_primary": len(primaries),
                "unique_discussions_any": len(all_items),
                "sources_count": len(sources),
                "sources": dict(sources.most_common()),
                "languages": dict(langs.most_common()),
                "audience": dict(audiences.most_common()),
                "intents": dict(intents.most_common()),
                "period": {
                    "with_known_date": len(dated),
                    "without_date": len(all_items) - len(dated),
                    "note": "даты публикации в первом проходе почти не получены (только заголовки и URL)",
                },
                "replies_visible_in_titles": {"threads": len(replies), "max": max(replies) if replies else None},
                "member_urls": sorted(it.d.url for it in all_items),
                "examples": [{"title": it.d.title or it.text, "url": it.d.url, "source": it.d.source_id,
                              "language": it.language, "title_from_url": it.title_from_url,
                              "replies": it.d.reactions.get("replies") or it.d.reactions.get("expert_answers")}
                             for it in examples],
            },
            "what_people_want": _wants(intents, all_items),
            "hypotheses": {
                "publication_topics": c.get("publication_topics", []),
                "research_question": c.get("research_question"),
                "pubmed_query_draft": c.get("pubmed_query_draft"),
            },
            "confidence": confidence(len(all_items), len(sources)),
            "limitations": [
                "анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны",
                "выборка определяется поисковыми запросами разработчика и ранжированием поисковика",
                "число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался",
            ] + (["один источник — тема может отражать особенность площадки"] if len(sources) == 1 else []),
        })
    return clusters, dict(excluded)


def _wants(intents: Counter, items: list[Labeled]) -> list[str]:
    out = []
    labels = {"question": "задают прямой вопрос", "problem": "описывают проблему или нежелательную реакцию",
              "desired_outcome": "ищут результат или способ решения", "objection": "сомневаются, работает ли это / не обман ли"}
    for key, n in intents.most_common():
        out.append(f"{labels.get(key, key)}: {n} из {len(items)}")
    return out
