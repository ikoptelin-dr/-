"""Отчёт по выгрузке форумов: импорт → очистка → сегменты → кластеры → reports/<name>/.

В отчёт попадают только агрегаты, ID, ссылки, заголовки тем и редакционные пересказы. Тексты сообщений — нет.
Повтор: python -m proba forum-report --data data/raw/forums_ru_2026-11 --data data/raw/forums_ru_fresh_2026-11"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from . import forum_analysis as fa
from .adapters.forum_export import load_export

SOURCE_INFO = {
    "ru_pf_k": {"name": "PF-K (pf-k.ru), форум косметологов", "language": "ru", "audience": "professional_mixed",
                "note": "профессиональная площадка, но пишут и потребители, и продавцы"},
    "pikabu": {"name": "Пикабу (pikabu.ru), посты и комментарии по тегам", "language": "ru", "audience": "consumer",
               "note": "потребительская площадка; среди постов есть статьи и реклама косметологов"},
    "it_alfemminile": {"name": "Alfemminile (forum.alfemminile.com)", "language": "it", "audience": "consumer",
                       "note": "итальянский потребительский форум — не российский рынок"},
}
SEG_RU = {"professional": "специалисты", "consumer": "потребители", "unclear": "не определено"}
STATUS_RU = {
    "ok": "учтено как сигнал спроса", "ad_or_spam_own": "реклама/спам (своя разметка)",
    "ad_or_spam_export": "реклама (метка выгрузки)", "possible_ad_export": "возможная реклама (метка выгрузки)",
    "off_topic_export": "постороннее (метка выгрузки)", "administrative_export": "служебное (метка выгрузки)",
    "brand_answer": "ответ представителя бренда — контекст, не спрос", "short_context": "короткая реплика без вопроса",
    "empty": "пустое после удаления цитат/медиа", "duplicate": "повтор (точный или близкий)",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyse(data_dirs: list[Path], lexicon: dict) -> dict[str, Any]:
    """Несколько выгрузок объединяются; повтор темы или сообщения между выгрузками — ошибка."""
    threads, imp_all, needs = [], [], []
    for d in data_dirs:
        t, imp = load_export(d)
        threads += t
        imp_all.append(imp)
        needs_path = d / "needs.jsonl"
        if needs_path.exists():
            needs += [json.loads(x) for x in needs_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    keys = [f"{t.source_id}:{t.external_id}" for t in threads]
    if len(keys) != len(set(keys)):
        raise ValueError("одна и та же тема в нескольких выгрузках")
    imp = {"datasets": [i["dataset"] for i in imp_all], "threads": sum(i["threads"] for i in imp_all),
           "messages": sum(i["messages"] for i in imp_all), "sources": sorted({s for i in imp_all for s in i["sources"]}),
           "dropped_fields": sorted({f for i in imp_all for f in i["dropped_fields"]}),
           "dropped_pii_like_fields": sorted({f for i in imp_all for f in i["dropped_pii_like_fields"]}), "per_dataset": imp_all}
    msgs = fa.build_messages(threads)
    cleaning = fa.clean(msgs)
    fa.segment(msgs, lexicon, {k: v["audience"] for k, v in SOURCE_INFO.items()})
    fa.tag_concepts(msgs, lexicon)
    clusters = fa.build_clusters(threads, msgs, lexicon, needs)
    return {"threads": threads, "import": imp, "msgs": msgs, "cleaning": cleaning, "clusters": clusters, "needs": needs}


def source_table(threads, msgs) -> list[dict[str, Any]]:
    rows = []
    for src in sorted({t.source_id for t in threads}):
        ts = [t for t in threads if t.source_id == src]
        ms = [m for m in msgs if m.source_id == src]
        ok = [m for m in ms if m.demand_signal]
        dates = sorted(m.published_at[:10] for m in ms if m.published_at)
        rows.append({
            "source_id": src, **SOURCE_INFO.get(src, {}),
            "threads": len(ts), "messages": len(ms), "messages_signal": len(ok),
            "threads_created": {"first": min(t.published_at[:10] for t in ts), "last": max(t.published_at[:10] for t in ts)},
            "messages_period": {"first": dates[0], "last": dates[-1]},
            "messages_signal_by_period": dict(Counter(m.period for m in ok)),
            "threads_with_actual_signal": len({m.thread_key for m in ok if m.period == "actual"}),
            "messages_by_year": dict(sorted(Counter(m.published_at[:4] for m in ms).items())),
            "signal_by_segment": dict(Counter(m.segment for m in ok)),
            "segment_basis": dict(Counter(m.segment_basis for m in ok)),
        })
    return rows


def run(data_dirs: list[Path] | Path, out_dir: Path, lexicon_path: Path, jtbd_path: Path) -> dict[str, Any]:
    data_dirs = [data_dirs] if isinstance(data_dirs, Path) else list(data_dirs)
    lexicon = yaml.safe_load(lexicon_path.read_text(encoding="utf-8"))
    jtbd = yaml.safe_load(jtbd_path.read_text(encoding="utf-8"))
    a = analyse(data_dirs, lexicon)
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = source_table(a["threads"], a["msgs"])
    for c in a["clusters"]:
        c["jtbd"] = jtbd["clusters"].get(c["id"])
        c["limitations"] = _limitations(c)
    top = {seg: fa.rank(a["clusters"], seg) for seg in ("professional", "consumer")}
    manifest = {
        "datasets": [d.name for d in data_dirs],
        "input_files": {f"{d.name}/{p.name}": _sha(p) for d in data_dirs for p in sorted(d.glob("*"))
                        if p.is_file() and p.suffix in (".jsonl", ".json")},
        "threads": [{"thread_key": f"{t.source_id}:{t.external_id}", "url": t.url, "title": t.title,
                     "created": (t.published_at or "")[:10], "messages": len(t.comments),
                     "completeness": t.flags.get("completeness")} for t in a["threads"]],
        "note": "Сырые тексты не публикуются и не коммитятся. Источник выгрузки — репозиторий ikoptelin-dr/Analys_cosmetology.",
    }
    run_report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "datasets": [d.name for d in data_dirs], "lexicon_version": lexicon["version"], "jtbd_version": jtbd["version"],
        "import": a["import"], "cleaning": a["cleaning"], "sources": sources,
        "actual_years": list(fa.ACTUAL_YEARS), "clusters": len(a["clusters"]),
        "messages_signal_without_concept": sum(1 for m in a["msgs"] if m.demand_signal and not m.concepts),
        "external_calls": 0, "is_synthetic": False,
    }
    (out_dir / "clusters.json").write_text(json.dumps({"clusters": a["clusters"], "top": top}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "run_report.json").write_text(json.dumps(run_report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "input_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "README.md").write_text(render(run_report, a["clusters"], top, jtbd, {f"{t.source_id}:{t.external_id}": t.url for t in a["threads"]}), encoding="utf-8")
    return run_report


def _limitations(c: dict) -> list[str]:
    o = c["observations"]
    out = ["разметка по словарю понятий: возможны пропуски и ложные совпадения",
           "частота в выборке — не объём рынка; тренд не оценивался"]
    if o["messages_direct_by_period"]["actual"] == 0:
        out.append("нет сообщений 2024–2026: только исторические данные")
    if o["sources_count"] == 1:
        out.append("один источник — может отражать особенность площадки")
    if set(o["sources"]) == {"it_alfemminile"}:
        out.append("только итальянский форум — к российскому рынку не переносится без проверки")
    if o["threads"] < 3:
        out.append("меньше трёх тем — наблюдение единичное")
    return out


# --- README ---------------------------------------------------------------------
def _p(n: int, total: int) -> str:
    return f"{n} ({round(100 * n / total)}%)" if total else str(n)


def render(rr: dict, clusters: list[dict], top: dict, jtbd: dict, thread_urls: dict[str, str]) -> str:
    by_id = {c["id"]: c for c in clusters}
    L: list[str] = []
    w = L.append
    total_msgs = rr["import"]["messages"]
    ok = rr["cleaning"]["statuses"].get("ok", 0)
    w("# Анализ рынка по форумам: Россия (выгрузка 2026-11)")
    w("")
    w(f"Сформировано: {rr['generated_at'][:10]}. Словарь понятий {rr['lexicon_version']}, гипотезы JTBD {rr['jtbd_version']}. "
      "Внешних вызовов и моделей не было, тексты никуда не отправлялись.")
    w("")
    w("## Статус результатов")
    w("")
    w("| Результат | Статус |")
    w("|---|---|")
    w("| Импорт, очистка, периоды, сегменты, кластеры, числа и ссылки | сделано и проверено (тесты, сверка с манифестом выгрузки) |")
    w("| JTBD, вопросы, страхи, возражения, «что сделать», «что болит» | не проверено: черновик-гипотеза разработчика, нужна проверка автором |")
    w(f"| Выводы о **текущем** российском спросе | {jtbd['narrative']['status_current']} |")
    w("| Тренды | заблокировано: нет сравнения периодов |")
    w("")
    w("## Главное за 30 секунд")
    w("")
    for line in jtbd["narrative"]["summary"]:
        w(f"- {line}")
    w("")
    w("## 1. Данные")
    w("")
    w("| Источник | Язык | Тем | Сообщений | Сигнал спроса после очистки | Сообщения: период | Темы созданы | Сигнал 2024–2026 |")
    w("|---|---|---|---|---|---|---|---|")
    for s in rr["sources"]:
        w(f"| {s.get('name', s['source_id'])} | {s.get('language')} | {s['threads']} | {s['messages']} | {s['messages_signal']} | "
          f"{s['messages_period']['first']} — {s['messages_period']['last']} | {s['threads_created']['first'][:4]}–{s['threads_created']['last'][:4]} | "
          f"{s['messages_signal_by_period'].get('actual', 0)} сообщ. в {s['threads_with_actual_signal']} темах |")
    w("")
    w("Сообщения по годам (все, до очистки):")
    w("")
    for s in rr["sources"]:
        w(f"- {s['source_id']}: " + ", ".join(f"{y} — {n}" for y, n in s["messages_by_year"].items()))
    w("")
    w("### Очистка")
    w("")
    w("| Статус сообщения | Число |")
    w("|---|---|")
    for k, v in rr["cleaning"]["statuses"].items():
        w(f"| {STATUS_RU.get(k, k)} | {_p(v, total_msgs)} |")
    ag = rr["cleaning"]["ad_agreement"]
    w("")
    w(f"Сверка рекламы: совпало со своей разметкой — {ag['both']}, только метка выгрузки — {ag['export_only']}, "
      f"только своя разметка — {ag['own_only']}. Исключаем по любой из двух меток. "
      "Восторженные «отзывы» со ссылками на магазины, не помеченные как реклама, вероятно, тоже частично реклама — это ограничение.")
    w("")
    w("### Сегменты (только сигналы спроса)")
    w("")
    w("| Источник | Специалисты | Потребители | Не определено |")
    w("|---|---|---|---|")
    for s in rr["sources"]:
        seg = s["signal_by_segment"]
        n = s["messages_signal"]
        w(f"| {s['source_id']} | {_p(seg.get('professional', 0), n)} | {_p(seg.get('consumer', 0), n)} | {_p(seg.get('unclear', 0), n)} |")
    w("")
    w("Как определяли: признаки в тексте («мои клиенты», «в работе», «в кабинет», «коллеги» → специалист; "
      "«мой косметолог», «у меня кожа», «для себя» → потребитель), затем редакционная метка выгрузки, затем площадка. "
      "На PF-K без признаков сегмент не угадываем — «не определено».")
    w("")
    w("## 2. Топ тем для специалистов")
    w("")
    w(jtbd["narrative"]["top_professional_note"])
    w("")
    _top_table(w, top["professional"], by_id, "specialist")
    w("")
    w("## 3. Топ тем для потребителей")
    w("")
    w(jtbd["narrative"]["top_consumer_note"])
    w("")
    _top_table(w, top["consumer"], by_id, "consumer")
    w("")
    w("## 4. Что болит у косметологов (PF-K)")
    w("")
    w(jtbd["narrative"]["pain_intro"])
    w("")
    for i, p in enumerate(jtbd["pain_points_professionals"], 1):
        cl = ", ".join(p["clusters"])
        links = " · ".join(f"[{k.split(':')[1]}]({thread_urls[k]})" for k in p["threads"] if k in thread_urls)
        w(f"{i}. **{p['title']}** ({cl}). {p['summary']} Темы: {links}")
    w("")
    w(jtbd["narrative"]["pain_fresh"])
    w("")
    w("## 4б. Что волнует потребителей (Пикабу 2024–2026)")
    w("")
    w("Пересказ своими словами; ссылки — на посты. Комментарии на Пикабу в большинстве — шутки и споры, поэтому опора — сами посты-вопросы и дневники.")
    w("")
    for i, p in enumerate(jtbd.get("pain_points_consumers", []), 1):
        links = " · ".join(f"[{k.split(':')[1]}]({thread_urls[k]})" for k in p["threads"] if k in thread_urls)
        w(f"{i}. **{p['title']}** ({', '.join(p['clusters'])}). {p['summary']} Темы: {links}")
    if jtbd.get("observations_market"):
        w("")
        w("Наблюдение о рынке контента:")
        for o in jtbd["observations_market"]:
            w(f"- {o}")
    w("")
    w("## 5. Кластеры подробно")
    w("")
    w("Наблюдения — числа и ссылки. Гипотезы — JTBD, вопросы, страхи, возражения, «что сделать».")
    w("Тем — темы, где кластер найден в тексте сообщения или в заголовке. Сообщений — прямые совпадения в тексте; "
      "«по контексту» — сообщения в теме с подходящим заголовком без собственного совпадения.")
    w("")
    for c in sorted(clusters, key=lambda c: (-c["observations"]["threads"], -c["observations"]["messages_direct"], c["id"])):
        _cluster(w, c)
    w("## 6. Пробелы данных и что докачать")
    w("")
    w(f"- Сообщений-сигналов без единого понятия из словаря: {rr['messages_signal_without_concept']} из {ok} — их тема словарём не распознана.")
    for g in jtbd["data_gaps"]:
        w(f"- {g}")
    w("")
    w("| Приоритет | Что докачать | Зачем |")
    w("|---|---|---|")
    for d in jtbd["download_next"]:
        w(f"| {d['priority']} | {d['what']} | {d['why']} |")
    w("")
    for line in jtbd["narrative"].get("gaps_tail", []):
        w(line)
    w("")
    w("## 7. Как воспроизвести")
    w("")
    w("```bash")
    w("python -m proba forum-report " + " ".join(f"--data data/raw/{d}" for d in rr["datasets"]) + " --out <папка отчёта>")
    w("```")
    w("")
    w("Сырые данные лежат локально в " + ", ".join(f"`data/raw/{d}/`" for d in rr["datasets"]) + " (в git не попадают). Список тем, ссылки и SHA-256 входных файлов — "
      "`input_manifest.json`; все числа — `clusters.json` и `run_report.json`.")
    w("")
    return "\n".join(L)


def _top_table(w, rows: list[dict], by_id: dict, side: str) -> None:
    if not rows:
        w("Данных нет.")
        return
    w("| # | Тема (кластер) | Тем | Сообщений | RU / IT тем | Темы сегмента с 2024–2026 | Уверенность | Что сделать |")
    w("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        j = (by_id[r["id"]].get("jtbd") or {}).get(side) or {}
        act = j.get("action") or {}
        todo = f"**{act['format']}**: {act['note']}" if act else "данных мало — не формулируем"
        src = r["threads_by_source"]
        w(f"| {i} | {r['name']} ({r['id']}) | {r['threads']} | {r['messages']} | {sum(v for k, v in src.items() if SOURCE_INFO.get(k, {}).get('language') == 'ru')} / {src.get('it_alfemminile', 0)} | "
          f"{r['threads_actual']} | {r['confidence']} | {todo} |")
    if len(rows) < 10:
        w("")
        w(f"Кластеров с данными для этого сегмента — {len(rows)}, до десяти не добираем искусственно.")


def _cluster(w, c: dict) -> None:
    o = c["observations"]
    w(f"### {c['id']}. {c['name']}")
    w("")
    w(f"- Тем: {o['threads']} (с сообщениями 2024–2026: {o['threads_by_period']['actual']}; исторических: {o['threads_by_period']['historical']}).")
    w(f"- Сообщений: {o['messages_direct']} — 2024–2026: {o['messages_direct_by_period']['actual']}, исторических: "
      f"{o['messages_direct_by_period']['historical']}; по контексту темы ещё {o['messages_thread_context']}.")
    seg = o["messages_direct_by_segment"]
    w(f"- По сегментам (сообщения): специалисты {seg['professional']}, потребители {seg['consumer']}, не определено {seg['unclear']}.")
    w(f"- Источников: {o['sources_count']} ({', '.join(f'{k} — {v} тем' for k, v in o['sources'].items())}). "
      f"Период: {o['period']['first']} — {o['period']['last']}.")
    if o["export_cluster_crosswalk"]:
        w(f"- Соответствие группам выгрузки (K01–K12): {', '.join(f'{k} — {v}' for k, v in list(o['export_cluster_crosswalk'].items())[:4])}.")
    w("- Примеры (3; до 5 — в `clusters.json`):")
    for e in o["examples"][:3]:
        what = e["paraphrase_ru"] or f"тема «{e['thread_title']}»"
        w(f"  - [{e['date']}, {e['source']}, {SEG_RU[e['segment']]}]({e['message_url']}) — {what}")
    j = c.get("jtbd") or {}
    for side, title in (("consumer", "Потребитель"), ("specialist", "Специалист")):
        s = j.get(side)
        if not s:
            continue
        w(f"- **{title} — JTBD (гипотеза):** {s['jtbd']}")
        for key, label in (("questions", "вопросы"), ("fears", "страхи"), ("objections", "возражения")):
            if s.get(key):
                w(f"  - {label}: " + "; ".join(s[key]))
        if s.get("action"):
            w(f"  - что сделать: **{s['action']['format']}** — {s['action']['note']}")
    if j.get("note"):
        w(f"- {j['note']}")
    w(f"- Уверенность: **{c['confidence']}**. Ограничения: " + "; ".join(c["limitations"]) + ".")
    w("")
