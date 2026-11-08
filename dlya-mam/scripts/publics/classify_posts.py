"""Метки тем постов и сводка по пабликам (R02, разделы 5–6).

    python3 -I dlya-mam/scripts/publics/classify_posts.py _raw/vk_posts.csv _raw/tg_posts.csv
    python3 -I dlya-mam/scripts/publics/classify_posts.py --selftest

Выход:
  dlya-mam/_raw/posts_labeled.csv          — посты с метками (НЕ в git: тексты)
  dlya-mam/_raw/blind_sample.csv, blind_key.csv — 100 постов для слепой проверки словаря
  dlya-mam/zamery/z20-topics-by-community.csv — агрегаты без текстов (в git)
  stdout — П2: отношение ER «плановое / ночь» внутри пабликов + бутстрэп 95%
"""
import csv
import pathlib
import random
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "_raw"

LABELS = {
    "night:температура": r"температур|\bжар\b|жаропониж|\b3[89][,.]\d\b",
    "night:дыхание": r"задыха|тяжело дыш|одышк|свистящ|хрип|обструкц|бронхоспазм|\bкруп|ларингит|стеноз",
    "night:грудь": r"лактостаз|мастит|застой молока|уплотнени\w* в груди|трещин\w* (на )?сос",
    "night:рвота": r"\bрвот|\bрв[её]т|тошн|понос|диаре|отравлени|ацетон",
    "night:сыпь": r"\bсып[ьи]\b|\bсыпью|высыпани|высыпал|обсыпал|крапивниц",
    "night:ухо": r"\bушк|\bух[оа]\b|\bушах|\bушей|отит",
    "night:живот": r"колик|газик|животик|вздути|пучит",
    "planned:гв": r"грудн\w* вскармл|\bгв\b|лактаци|прикладыва|сцежива|молокоотсос|корм\w* грудью|отлучени",
    "planned:прикорм": r"прикорм|\bпюре\b|первый продукт|педприкорм",
    "planned:сон": r"\bсон\b|\bсна\b|засыпа|укладыва|режим сна|ночн\w* пробужд",
    "planned:прививки": r"привив|вакцин|манту|акдс|\bбцж",
    "planned:атопия": r"атопич|дерматит|диатез|экзем",
    "planned:смеси": r"\bсмес[ьиейю]|искусственн\w* вскармл|бутылочк",
    "planned:зубы": r"\bзуб|прорезыва|кариес|\bдесн",
    "planned:развитие": r"развити[ея]|моторик|\bречь|\bречи\b|задержк\w* речи|\bползать|первые шаги|невролог|массаж",
    "commerce": r"\berid\b|реклама|розыгрыш|конкурс|скидк|промокод|\bпродам|\bпродаю|\bкуплю|\bотдам|\bакци[яи]\b",
}
RX = {k: re.compile(v, re.I) for k, v in LABELS.items()}
CLEAN = [(re.compile(r"https?://\S+|t\.me/\S+|vk\.com/\S+"), "[ссылка]"),
         (re.compile(r"@\w+"), "[упоминание]"),
         (re.compile(r"\+?\d[\d\s()\-]{8,}\d"), "[телефон]")]


def labels(text):
    return sorted(k for k, rx in RX.items() if rx.search(text or ""))


def group(lbls, is_ad):
    if is_ad or "commerce" in lbls:
        return "commerce"
    n = any(l.startswith("night:") for l in lbls)
    p = any(l.startswith("planned:") for l in lbls)
    return "mixed" if n and p else "night" if n else "planned" if p else "other"


def clean(text):
    for rx, rep in CLEAN:
        text = rx.sub(rep, text)
    return text


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def er(r):
    v = num(r["views"])
    if not v:
        return None
    return sum(num(r[k]) or 0 for k in ("likes", "comments_count", "reposts")) / v


def bootstrap_median(vals, n=2000, seed=1):
    rnd = random.Random(seed)
    meds = sorted(statistics.median(rnd.choices(vals, k=len(vals))) for _ in range(n))
    return meds[int(0.025 * n)], meds[int(0.975 * n)]


def run(paths):
    rows = []
    for p in paths:
        rows += list(csv.DictReader(open(p, encoding="utf-8")))
    for r in rows:
        r["labels"] = "|".join(labels(r["text"]))
        r["group"] = group(r["labels"].split("|") if r["labels"] else [], r.get("is_ad") == "1")
        r["er"] = er(r)
    RAW.mkdir(exist_ok=True)
    with open(RAW / "posts_labeled.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    sample = random.Random(7).sample(rows, min(100, len(rows)))
    with open(RAW / "blind_sample.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "text", "human_group (night/planned/mixed/commerce/other)"])
        for i, r in enumerate(sample, 1):
            w.writerow([i, clean(r["text"]), ""])
    with open(RAW / "blind_key.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "platform", "community_id", "post_id", "script_group", "labels"])
        for i, r in enumerate(sample, 1):
            w.writerow([i, r["platform"], r["community_id"], r["post_id"], r["group"], r["labels"]])

    agg = []
    ratios = []
    by_c = {}
    for r in rows:
        by_c.setdefault((r["platform"], r["community_id"]), []).append(r)
    for (pl, cid), rs in sorted(by_c.items()):
        for g in ("all", "night", "planned", "mixed", "commerce", "other"):
            sub = rs if g == "all" else [r for r in rs if r["group"] == g]
            views = [num(r["views"]) for r in sub if num(r["views"]) is not None]
            ers = [r["er"] for r in sub if r["er"] is not None]
            agg.append({"platform": pl, "community_id": cid, "group": g, "posts": len(sub),
                        "median_views": round(statistics.median(views)) if views else "",
                        "median_er": round(statistics.median(ers), 5) if ers else "",
                        "ad_share": round(sum(r.get("is_ad") == "1" for r in sub) / len(sub), 3) if sub else ""})
        ne = [r["er"] for r in rs if r["group"] == "night" and r["er"] is not None]
        pe = [r["er"] for r in rs if r["group"] == "planned" and r["er"] is not None]
        if len(ne) >= 5 and len(pe) >= 5 and statistics.median(ne) > 0:
            ratios.append(statistics.median(pe) / statistics.median(ne))
    out = ROOT / "zamery" / "z20-topics-by-community.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(agg[0]))
        w.writeheader()
        w.writerows(agg)
    print(f"постов {len(rows)}, пабликов {len(by_c)} → {out}")
    if len(ratios) >= 3:
        lo, hi = bootstrap_median(ratios)
        verdict = ("подтверждено" if statistics.median(ratios) >= 1.3 and lo > 1 else
                   "отклонено" if statistics.median(ratios) <= 1.0 else "не решено")
        print(f"П2: пабликов с ≥5 ночными и ≥5 плановыми постами: {len(ratios)}; "
              f"медиана отношения ER плановое/ночь = {statistics.median(ratios):.2f}, 95% [{lo:.2f}; {hi:.2f}] → {verdict}")
    else:
        print(f"П2: мало пабликов для сравнения ({len(ratios)}), нужно ≥3")


def selftest():
    # СИНТЕТИЧЕСКИЕ примеры, не данные: проверяем только словарь.
    cases = {
        "Температура 38,5 ночью, чем сбить?": "night",
        "Высыпания на щеках после прикорма": "mixed",
        "Как наладить грудное вскармливание после роддома": "planned",
        "Подушка для кормления, продам недорого": "commerce",
        "Ребёнок не может уснуть, засыпает только на руках": "planned",
        "Прогулка в парке в субботу": "other",
        "Болит ушко, ночью плачет": "night",
        "Хорошо высыпаюсь, когда малыш спит": "other",
    }
    bad = []
    for text, want in cases.items():
        got = group(labels(text), False)
        if got != want:
            bad.append((text, want, got, labels(text)))
    assert clean("пишите @mama_nsk или +7 913 123-45-67, https://vk.com/x") == "пишите [упоминание] или [телефон], [ссылка]"
    if bad:
        for b in bad:
            print("ОШИБКА:", b)
        sys.exit(1)
    print(f"selftest: {len(cases)} синтетических примеров, все метки верны")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif len(sys.argv) > 1:
        run(sys.argv[1:])
    else:
        sys.exit(__doc__)
