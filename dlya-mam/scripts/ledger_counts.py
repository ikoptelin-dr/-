"""Пересчёт всех чисел со статусом ФАКТ из dlya-mam/00-evidence-ledger.md.

Запуск из корня репозитория:
    python3 -I dlya-mam/scripts/ledger_counts.py
Вход: только файлы dlya-mam/inputs/ и dlya-mam/zamery/z01-night-title-precision.csv.
Выход: JSON в stdout. Сеть не нужна, внешние модели не вызываются.
"""
import collections
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
INP = ROOT / "inputs"

# Соответствие ночных экранов v2 работам кодовой книги — ДОПУЩЕНИЕ (файла ia-v2 в репо нет).
NIGHT_SCREENS = {
    "температура": ["ped-fever-night", "ped-fever-when"],
    "тяжело дышит": ["ped-wheeze"],
    "грудь болит": ["gv-latch-pain", "gv-lactostasis", "gv-mastitis"],
    "рвота": ["ped-vomit", "ped-acetone", "table-poisoning"],
    "сыпь": ["all-rash"],
    "болит ухо": ["ped-otitis"],
    "кричит/живот": ["ped-gas", "ped-sleep-cry"],
}
# «Чем лечить»-запросы: продукт на них по границе не отвечает.
TREAT_RE = re.compile(r"чем (лечить|мазать|сбивать|обезболить|промывать|помочь|нельзя сбивать|капать)|дозировк|что капать|отказ от прививк", re.I)


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    cl = json.load(open(INP / "job_clusters.json", encoding="utf-8"))
    cards = load_jsonl(INP / "all.jsonl")
    q = json.load(open(INP / "quarantine.json", encoding="utf-8"))
    out = {}

    # --- кластеры (слой до Claude) ---
    clusters = cl["clusters"]
    topics = [t for c in clusters for t in c["topics"]]
    years = collections.Counter(t["year"] for t in topics)
    out["clusters"] = {
        "jobs": len(clusters),
        "jobs_n_ge_1": sum(c["n"] > 0 for c in clusters),
        "jobs_n_ge_3": sum(c["n"] >= 3 for c in clusters),
        "assigned_topics": len(topics),
        "topics_2002_2008": sum(v for y, v in years.items() if 2002 <= y <= 2008),
        "topics_2012_plus": sum(v for y, v in years.items() if y >= 2012),
        "topic_acuity": dict(collections.Counter(t["acuity"] for t in topics)),
        "topic_era": dict(collections.Counter(t["era"] for t in topics)),
        "topic_keys": sorted({k for t in topics for k in t}),
        "unassigned": len(cl["unassigned"]),
        "by_prefix": dict(collections.Counter(
            c["job_id"].split("-")[0] for c in clusters for _ in c["topics"])),
    }

    # --- итоговые карточки all.jsonl ---
    ev = [e for c in cards for e in c["evidence"]]
    eyears = collections.Counter(e["year"] for e in ev)
    qm = [x for c in cards for x in c["query_mom"]]
    treat = [x for x in qm if TREAT_RE.search(x)]
    card_ids = {c["job_id"] for c in cards}
    out["cards"] = {
        "cards": len(cards),
        "acuity": dict(collections.Counter(c["acuity"] for c in cards)),
        "era": dict(collections.Counter(c["era"] for c in cards)),
        "out_of_scope": [c["job_id"] for c in cards if c["out_of_scope"]],
        "evidence_rows": len(ev),
        "evidence_2002_2008": sum(v for y, v in eyears.items() if y and 2002 <= y <= 2008),
        "evidence_2012_plus": sum(v for y, v in eyears.items() if y and y >= 2012),
        "query_mom_total": len(qm),
        "query_mom_treatment_like": len(treat),
        "query_mom_treatment_examples": treat[:12],
        "see_doctor_if_total": sum(len(c["see_doctor_if"]) for c in cards),
        "codebook_jobs_missing": sorted({c["job_id"] for c in clusters} - card_ids),
    }

    # --- пакеты P5 (вход для Claude): see_doctor_if шаблонные? ---
    packs = {}
    for f in sorted((INP / "p5-packs").glob("*.jsonl")):
        rows = load_jsonl(f)
        packs[f.stem] = {"cards": len(rows),
                         "distinct_see_doctor_if_lists": len({tuple(r["see_doctor_if"]) for r in rows})}
    out["p5_packs"] = packs
    out["p5_cards_total"] = sum(v["cards"] for v in packs.values())

    # --- ночные экраны ---
    n_by_job = {c["job_id"]: c["n"] for c in clusters}
    ev_by_job = {c["job_id"]: len(c["evidence"]) for c in cards}
    prec = collections.defaultdict(collections.Counter)
    pfile = ROOT / "zamery" / "z01-night-title-precision.csv"
    if pfile.exists():
        for r in csv.DictReader(open(pfile, encoding="utf-8")):
            prec[r["job_id"]][r["verdict"]] += 1
    screens = {}
    for s, jobs in NIGHT_SCREENS.items():
        screens[s] = {
            "jobs": jobs,
            "cluster_topics": sum(n_by_job.get(j, 0) for j in jobs),
            "card_evidence": sum(ev_by_job.get(j, 0) for j in jobs),
            "jobs_without_card": [j for j in jobs if j not in card_ids],
            "title_on": sum(prec[j]["on"] for j in jobs),
            "title_partial": sum(prec[j]["partial"] for j in jobs),
            "title_off": sum(prec[j]["off"] for j in jobs),
        }
    out["night_screens"] = screens
    out["night_totals"] = {k: sum(v[k] for v in screens.values())
                           for k in ("cluster_topics", "card_evidence", "title_on", "title_partial", "title_off")}

    # --- карантин: что выкинуто из ночных тем ---
    night_drop_ids = {2506, 8861, 15092, 7367, 41662, 1241}
    out["quarantine"] = {
        "dropped": q["stats"]["dropped"],
        "by_reason": q["stats"]["by_reason"],
        "night_relevant_dropped": [
            {"t": d["topic_id"], "title": d["title"], "reasons": d["reasons"], "n_posts": d["n_posts"]}
            for d in q["dropped"] if d["topic_id"] in night_drop_ids],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
