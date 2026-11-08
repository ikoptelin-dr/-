"""Анализ выдач Яндекса (после parse_serp.py).

    python3 -I dlya-mam/scripts/analyze_serp.py
Выход: zamery/z12-serp-summary.json и z12-domain-types.csv (разметка доменов для проверки).
"""
import collections
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from serp_domain_types import domain_type, is_local  # noqa: E402

Z = ROOT / "zamery"
ALIAS = {  # формулировки в выдаче, которые отличаются от списка ключей
    "высокая температура ночью у ребенка": "высокая температура ночью",
    "изо рта пахнет ацетоном у ребенка": "изо рта пахнет ацетоном",
    "ебенок часто срыгивает": "ребенок часто срыгивает",
    "надо ли сбивать температуру 37,5": "надо ли сбивать температуру 37 5",
    "плачет по вечерам, болит животик": "плачет по вечерам болит животик",
}
TREAT = re.compile(r"лечени|лечить|препарат|таблет|сироп|капл|мазь|крем|дозиров|\bмг\b|парацетамол|ибупрофен|нурофен|антибиот", re.I)
WHEN = re.compile(r"когда (обращ|к врачу|вызыва|срочно|нужн\w* врач)|скор\w* помощ|\b103\b|\b112\b|к врачу|обратит\w* к|немедленно|срочно", re.I)


def norm(s):
    return " ".join(s.lower().replace("ё", "е").replace(",", " ").split())


def read(name):
    return list(csv.DictReader(open(Z / name, encoding="utf-8")))


def main():
    keys = {norm(k["paste_phrase"]): k for k in read("z02-wordstat-keys.csv")}
    pages = read("z12-serp-pages.csv")
    org = read("z12-serp-organic.csv")
    paid = read("z12-serp-paid.csv")
    alice = {a["page"]: a for a in read("z12-serp-alice.csv")}
    grp = {}
    for p in pages:
        q = norm(p["query"])
        q = norm(ALIAS.get(q, q))
        k = keys.get(q)
        grp[p["page"]] = (k["group"], k["job_id"]) if k else ("?", "?")
    S = {"unmapped": [p["query"] for p in pages if grp[p["page"]][0] == "?"],
         "regions": dict(collections.Counter(p["lr"] for p in pages))}

    # разметка доменов — для ручной проверки
    doms = collections.Counter(o["domain"] for o in org) + collections.Counter(p["domain"] for p in paid)
    with open(Z / "z12-domain-types.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "type", "is_local_nsk", "mentions"])
        for d, n in doms.most_common():
            w.writerow([d, domain_type(d), is_local(d), n])

    top10 = [o for o in org if int(o["pos"]) <= 10]
    by_g = collections.defaultdict(list)
    for o in top10:
        by_g[grp[o["page"]][0]].append(o)
    S["top10_type_share"] = {}
    for g, rs in sorted(by_g.items()):
        c = collections.Counter(domain_type(o["domain"]) for o in rs)
        n = len(rs)
        S["top10_type_share"][g] = {"results": n, **{t: round(v / n, 3) for t, v in c.most_common()},
                                    "local_nsk_share": round(sum(is_local(o["domain"], o["url"]) for o in rs) / n, 3)}

    # кто чаще всего в топ-10 ночных и плановых
    for g in ("night", "paid"):
        c = collections.Counter(o["domain"] for o in top10 if grp[o["page"]][0] == g)
        S[f"top_domains_{g}"] = [(d, n, domain_type(d)) for d, n in c.most_common(15)]

    # государственные и научные источники
    S["state_in_top10"] = sorted({(o["query"], o["pos"], o["domain"]) for o in top10 if domain_type(o["domain"]) == "state"},
                                 key=lambda x: (x[0], int(x[1])))
    S["pages_with_state_top10_by_group"] = {}
    for g in set(v[0] for v in grp.values()):
        pg = [p["page"] for p in pages if grp[p["page"]][0] == g]
        has = {o["page"] for o in top10 if domain_type(o["domain"]) == "state" and o["page"] in pg}
        S["pages_with_state_top10_by_group"][g] = f"{len(has)}/{len(pg)}"

    # местные игроки в органике по неклиничным запросам
    S["local_in_top10_nonclinic"] = sorted({(o["query"], o["pos"], o["domain"]) for o in top10
                                            if is_local(o["domain"], o["url"]) and grp[o["page"]][0] not in ("clinic",)},
                                           key=lambda x: (x[0], int(x[1])))
    # Комаровский
    S["komarovsky_in_organic"] = sorted({(o["query"], o["pos"], o["domain"]) for o in org
                                         if "komarov" in o["url"].lower() or "комаровск" in o["title"].lower()})

    # Алиса
    S["alice_by_group"] = {}
    for g in sorted(set(v[0] for v in grp.values())):
        pg = [p for p in pages if grp[p["page"]][0] == g]
        S["alice_by_group"][g] = f"{sum(int(p['alice']) for p in pg)}/{len(pg)}"
    S["alice_texts"] = []
    src = collections.Counter()
    for pid, a in alice.items():
        if not a["alice_text"]:
            continue
        t = a["alice_text"]
        S["alice_texts"].append({"query": a["query"], "group": grp[pid][0], "chars": len(t),
                                 "treatment_terms": len(TREAT.findall(t)), "when_to_doctor_terms": len(WHEN.findall(t)),
                                 "sources": a["alice_sources"]})
        src.update(s for s in a["alice_sources"].split("; ") if s)
    S["alice_source_domains"] = [(d, n, domain_type(d)) for d, n in src.most_common(25)]
    S["alice_source_types"] = dict(collections.Counter(domain_type(d) for d in src.elements()))

    # формулировка органики: «лечение» против «когда к врачу» (заголовок + сниппет)
    S["organic_framing_by_group"] = {}
    for g, rs in sorted(by_g.items()):
        n = len(rs)
        tr = sum(bool(TREAT.search(o["title"] + " " + o["snippet"])) for o in rs)
        wh = sum(bool(WHEN.search(o["title"] + " " + o["snippet"])) for o in rs)
        S["organic_framing_by_group"][g] = {"results": n, "treatment_share": round(tr / n, 3), "when_share": round(wh / n, 3)}

    # платное: промо по запросам группы и кто рекламируется
    S["paid_by_group"] = {}
    for g in sorted(set(v[0] for v in grp.values())):
        ps = [p for p in paid if grp[p["page"]][0] == g]
        promo = [p for p in ps if p["kind"] == "promo"]
        S["paid_by_group"][g] = {"pages": sum(1 for p in pages if grp[p["page"]][0] == g),
                                 "promo": len(promo), "ad_or_other": len(ps) - len(promo),
                                 "promo_types": dict(collections.Counter(domain_type(p["domain"]) for p in promo))}
    ad_doms = collections.Counter(p["domain"] for p in paid if p["kind"] != "promo")
    S["ad_block_top_domains"] = [(d, n, domain_type(d)) for d, n in ad_doms.most_common(12)]
    S["promo_examples_night"] = [(p["query"], p["domain"], domain_type(p["domain"]), p["title"][:90])
                                 for p in paid if p["kind"] == "promo" and grp[p["page"]][0] == "night"][:40]
    S["wizards"] = {"doctors": [p["query"] for p in pages if p["doctors_wizard"] == "1"],
                    "orgs": sum(int(p["orgs_block"]) for p in pages)}
    json.dump(S, open(Z / "z12-serp-summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(S, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
