"""Анализ выгрузок прогноза Директа по протоколу research/R01-direct-prompt.md.

Запуск (после parse_direct_forecast.py):
    python3 -I dlya-mam/scripts/analyze_direct.py
Выход: dlya-mam/zamery/z04-direct-analysis.csv и сводка JSON в stdout.
"""
import collections
import csv
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ledger_counts import NIGHT_SCREENS  # noqa: E402

FILES = {"2026-11-08-nsk-aglomeraciya.xls": "aglo", "2026-11-08-nso.xls": "nso", "2026-11-08-rossiya.xls": "rf"}
# Фразы, в которых широкое соответствие ловит взрослых, животных или не-лактацию.
AMBIGUOUS = {
    "мастит", "рвота и понос", "обструктивный бронхит", "уплотнение в груди", "длительный кашель",
    "рвота ночью", "высокая температура ночью", "отит чем лечить", "можно ли греть ухо",
    "изо рта пахнет ацетоном",
}
NUM = ["requests", "imp100", "clk100", "cpc100", "bud100", "clk62", "cpc62", "bud62"]


def norm(s):
    return " ".join(s.lower().replace("ё", "е").split()).split(" -")[0]


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def main():
    keys = {norm(k["paste_phrase"]): k for k in csv.DictReader(open(ROOT / "zamery" / "z02-wordstat-keys.csv", encoding="utf-8"))}
    data = collections.defaultdict(dict)
    raw_phrase = {}
    for r in csv.DictReader(open(ROOT / "zamery" / "z03-direct-forecast.csv", encoding="utf-8")):
        if r["file"] not in FILES:
            continue
        p = norm(r["phrase"])
        raw_phrase[p] = r["phrase"]
        data[p][FILES[r["file"]]] = {k: float(r[k] or 0) for k in NUM}

    cl = json.load(open(ROOT / "inputs" / "job_clusters.json", encoding="utf-8"))
    forum_n = {c["job_id"]: c["n"] for c in cl["clusters"]}
    cards = [json.loads(l) for l in open(ROOT / "inputs" / "all.jsonl", encoding="utf-8") if l.strip()]
    card_ev = {c["job_id"]: len(c["evidence"]) for c in cards}
    screen_of = {j: s for s, js in NIGHT_SCREENS.items() for j in js}
    screen_of["nav-when-doctor"] = "исход (когда к врачу)"
    screen_of["vax-reaction"] = "температура"

    rows = []
    for p, k in keys.items():
        d = data.get(p)
        row = {"phrase": k["paste_phrase"], "direct_phrase": raw_phrase.get(p, ""), "group": k["group"],
               "job_id": k["job_id"], "screen": screen_of.get(k["job_id"], ""),
               "child_specific": int(p not in AMBIGUOUS), "returned": int(bool(d)),
               "forum_cluster_n": forum_n.get(k["job_id"], ""), "card_evidence": card_ev.get(k["job_id"], "")}
        for reg in ("aglo", "nso", "rf"):
            for m in ("requests", "clk100", "cpc100", "bud100"):
                row[f"{reg}_{m}"] = d[reg][m] if d else ""
        if d and d["rf"]["requests"]:
            row["nso_share_of_rf"] = round(d["nso"]["requests"] / d["rf"]["requests"], 4)
        else:
            row["nso_share_of_rf"] = ""
        if d and d["nso"]["requests"]:
            row["aglo_share_of_nso"] = round(d["aglo"]["requests"] / d["nso"]["requests"], 3)
        else:
            row["aglo_share_of_nso"] = ""
        rows.append(row)
    out = ROOT / "zamery" / "z04-direct-analysis.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    ret = [r for r in rows if r["returned"]]
    S = {"missing_phrases": [r["phrase"] for r in rows if not r["returned"]]}

    def agg(rs, reg):
        req = sum(r[f"{reg}_requests"] for r in rs)
        clk = sum(r[f"{reg}_clk100"] for r in rs)
        bud = sum(r[f"{reg}_bud100"] for r in rs)
        return {"phrases": len(rs), "requests": round(req), "clicks100": round(clk), "budget100": round(bud),
                "avg_cpc100": round(bud / clk, 1) if clk else None}

    S["by_group"] = {}
    for g in ["night", "paid", "boundary", "clinic", "intent", "brand"]:
        rs = [r for r in ret if r["group"] == g]
        rsc = [r for r in rs if r["child_specific"]]
        S["by_group"][g] = {reg: {"all": agg(rs, reg), "child_specific": agg(rsc, reg)} for reg in ("nso", "rf")}

    S["night_by_screen_nso"] = {}
    for s in list(NIGHT_SCREENS) + ["исход (когда к врачу)"]:
        rs = [r for r in ret if r["screen"] == s and r["group"] == "night"]
        S["night_by_screen_nso"][s] = {"all": agg(rs, "nso"), "child_specific": agg([r for r in rs if r["child_specific"]], "nso"),
                                       "rf_child_specific_requests": agg([r for r in rs if r["child_specific"]], "rf")["requests"]}

    n = S["by_group"]
    S["boundary_to_night_ratio"] = {
        reg: {kind: round(n["boundary"][reg][kind]["requests"] / n["night"][reg][kind]["requests"], 3)
              for kind in ("all", "child_specific")} for reg in ("nso", "rf")}
    when_doc = [r for r in ret if r["job_id"] == "nav-when-doctor"]
    S["when_to_doctor_phrases"] = {r["phrase"]: {"nso": r["nso_requests"], "rf": r["rf_requests"]} for r in when_doc}

    shares = [r["nso_share_of_rf"] for r in ret if r["nso_share_of_rf"] != "" and r["rf_requests"] >= 1000]
    S["nso_share_of_rf_median_rf_ge_1000"] = round(statistics.median(shares), 4)
    S["nso_share_of_rf_clinic"] = {r["phrase"]: r["nso_share_of_rf"] for r in ret if r["group"] == "clinic"}
    ag = [r["aglo_share_of_nso"] for r in ret if r["aglo_share_of_nso"] != "" and r["nso_requests"] >= 100]
    S["aglo_share_of_nso_median_nso_ge_100"] = round(statistics.median(ag), 3)

    # Форум против сегодняшнего спроса: по работам (только night/paid/boundary).
    per_job = collections.defaultdict(lambda: {"rf": 0, "rf_child": 0})
    for r in ret:
        if r["group"] in ("night", "paid", "boundary"):
            per_job[r["job_id"]]["rf"] += r["rf_requests"]
            if r["child_specific"]:
                per_job[r["job_id"]]["rf_child"] += r["rf_requests"]
    jobs = sorted(per_job)
    S["forum_vs_today"] = {
        "jobs": len(jobs),
        "spearman_cluster_n_vs_rf": spearman([forum_n[j] for j in jobs], [per_job[j]["rf"] for j in jobs]),
        "spearman_card_evidence_vs_rf": spearman([card_ev[j] for j in jobs], [per_job[j]["rf"] for j in jobs]),
        "table": sorted(([j, forum_n[j], card_ev[j], per_job[j]["rf"]] for j in jobs), key=lambda x: -x[3]),
    }
    print(json.dumps(S, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
