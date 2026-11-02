"""Редакционная очередь X/Threads: идеи из кластеров, черновики, проверка связей и лимитов, экспорт."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .limits import check

IDEA_TYPES = {
    "short_post": "короткий самостоятельный пост",
    "thread": "серия постов / тред",
    "audience_question": "вопрос аудитории для проверки гипотезы",
    "misconception": "объяснение популярного заблуждения",
    "research_first": "тема, требующая сначала научного исследования",
}
# Статусы черновиков. Ни один из них не означает «готово к публикации»:
# готовность появляется только после действий человека (approve) в outbox.
DRAFT_STATUSES = {"research_draft", "draft_no_medical_claims"}


def generate_ideas(clusters: list[dict]) -> list[dict]:
    """Идеи строятся из наблюдений кластера. Темы из гипотез кластера, а не из чужих сообщений."""
    ideas = []
    for c in clusters:
        o = c["observations"]
        if o["unique_discussions_any"] < 3:
            continue
        basis = [e["url"] for e in o["examples"][:3]]
        topics = c["hypotheses"]["publication_topics"] or [c["name"]]
        intents = o["intents"]
        ideas.append(_idea(c, "audience_question", f"Спросить аудиторию: {c['name'].split(':')[0].lower()} — что вызывает больше всего сомнений?", basis, False,
                           "проверяем гипотезу о главном вопросе кластера без медицинских утверждений"))
        if intents.get("objection") or intents.get("problem"):
            ideas.append(_idea(c, "misconception", topics[0], basis, True,
                               "в обсуждениях есть возражения или жалобы; объяснение потребует источников"))
        ideas.append(_idea(c, "thread", topics[-1], basis, True, "серия из 3–6 постов; утверждения — после проверки источников"))
        ideas.append(_idea(c, "research_first", c["hypotheses"]["research_question"], basis, True,
                           "сначала исследовательское задание и источники, затем статья и производные посты"))
    return ideas


def _idea(c: dict, kind: str, title: str, basis: list[str], needs_research: bool, why: str) -> dict:
    return {"id": f"{c['id']}-{kind}", "cluster_id": c["id"], "cluster_name": c["name"], "type": kind,
            "type_label": IDEA_TYPES[kind], "working_title": title, "basis_urls": basis,
            "requires_research_before_publication": needs_research, "why": why, "status": "idea"}


def text_hash(parts: list[str]) -> str:
    return hashlib.sha256("\n␞\n".join(parts).encode("utf-8")).hexdigest()


def resolve(text: str, clusters: dict[str, dict]) -> str:
    """Подставляет числа из кластеров: {C01.n} — уникальных обсуждений, {C01.sources} — площадок."""
    def sub(m: re.Match) -> str:
        c = clusters[m.group(1)]["observations"]
        return str(c["unique_discussions_any"] if m.group(2) == "n" else c["sources_count"])
    return re.sub(r"\{(C\d\d)\.(n|sources)\}", sub, text)


def load_drafts(path: Path, clusters: list[dict], channels_cfg: dict) -> tuple[list[dict], list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in clusters}
    drafts, errors = [], []
    for d in data["drafts"]:
        did = d["id"]
        cid = d["cluster_id"]
        if cid not in by_id:
            errors.append(f"{did}: кластер {cid} отсутствует в выборке")
            continue
        members = set(by_id[cid]["observations"]["member_urls"])
        for url in d.get("basis_urls", []):
            if url not in members:
                errors.append(f"{did}: ссылка-основание не входит в кластер {cid}: {url}")
        if d["status"] not in DRAFT_STATUSES:
            errors.append(f"{did}: недопустимый статус {d['status']}")
        if d.get("medical_claims") and d["status"] != "research_draft":
            errors.append(f"{did}: есть медицинские утверждения — статус должен быть research_draft")
        parts = [resolve(p, by_id) for p in d["parts"]]
        checks = []
        for i, p in enumerate(parts, 1):
            ok, n, limit = check(d["channel"], p, channels_cfg["channels"][d["channel"]])
            checks.append({"part": i, "length": n, "limit": limit, "fits": ok})
            if not ok:
                errors.append(f"{did}: часть {i} длиннее лимита {d['channel']} ({n} > {limit})")
        drafts.append({**d, "parts": parts, "length_checks": checks, "text_sha256": text_hash(parts),
                       "version": 1, "publishable": False,
                       "blocked_by": _blockers(d)})
    return drafts, errors


def _blockers(d: dict) -> list[str]:
    out = ["публикация выключена в config/channels.yaml", "аккаунт не подключён", "нет одобрения редактора"]
    if d.get("medical_claims"):
        out += ["утверждения не проверены по источникам", "нет медицинской рецензии"]
    return out


def export(out: Path, ideas: list[dict], drafts: list[dict], meta: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    queue = {"meta": meta, "ideas": ideas, "drafts": drafts}
    (out / "queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "queue.md").write_text(_markdown(ideas, drafts, meta), encoding="utf-8")
    (out / "preview.html").write_text(_html(drafts, meta), encoding="utf-8")


def _markdown(ideas: list[dict], drafts: list[dict], meta: dict) -> str:
    lines = ["# Редакционная очередь X / Threads — предпросмотр", "",
             f"Сформировано: {meta['generated_at']}. Статус: **исследовательские черновики, не готовы к публикации.**",
             "Публикация выключена; аккаунты не подключены. Утверждения об эффективности и безопасности не проверены.", "",
             "## Черновики", ""]
    for d in drafts:
        lines += [f"### {d['id']} · {d['channel'].upper()} · {d['format']} · кластер {d['cluster_id']}", "",
                  f"Статус: `{d['status']}`. Блокирует выпуск: {'; '.join(d['blocked_by'])}.", ""]
        for i, (p, c) in enumerate(zip(d["parts"], d["length_checks"]), 1):
            lines += [f"**{i}/{len(d['parts'])}** ({c['length']}/{c['limit']})", "", "> " + p.replace("\n", "\n> "), ""]
        if d.get("medical_claims"):
            lines += ["Утверждения, требующие источников и рецензии:", ""] + [f"- {x}" for x in d["medical_claims"]] + [""]
        lines += ["Основание (обсуждения из выборки):", ""] + [f"- <{u}>" for u in d.get("basis_urls", [])] + [""]
    lines += ["## Идеи по кластерам", "", "| Идея | Тип | Рабочая тема | Нужны источники |", "|---|---|---|---|"]
    for i in ideas:
        lines.append(f"| {i['id']} | {i['type_label']} | {i['working_title']} | {'да' if i['requires_research_before_publication'] else 'нет'} |")
    return "\n".join(lines) + "\n"


def _html(drafts: list[dict], meta: dict) -> str:
    cards = []
    for d in drafts:
        parts = "".join(f"<div class='post'><div class='n'>{i}/{len(d['parts'])} · {c['length']}/{c['limit']}</div>{html.escape(p)}</div>"
                        for i, (p, c) in enumerate(zip(d["parts"], d["length_checks"]), 1))
        claims = "".join(f"<li>{html.escape(x)}</li>" for x in d.get("medical_claims", []))
        cards.append(f"<section><h2>{html.escape(d['id'])} · {d['channel'].upper()} · {html.escape(d['format'])}</h2>"
                     f"<p class='status'>{html.escape(d['status'])} — не готово к публикации</p>{parts}"
                     + (f"<p>Требуют проверки:</p><ul>{claims}</ul>" if claims else "") + "</section>")
    return ("<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            "<title>Очередь черновиков</title><style>body{font-family:system-ui;max-width:720px;margin:auto;padding:16px;background:#fff;color:#111}"
            ".post{border:1px solid #ccc;border-radius:12px;padding:12px;margin:8px 0;white-space:pre-wrap}"
            ".n{font-size:12px;color:#666}.status{color:#a40}</style>"
            f"<h1>Черновики X / Threads</h1><p>{html.escape(meta['generated_at'])}. Исследовательские черновики, публикация выключена.</p>"
            + "".join(cards) + "</html>\n")
