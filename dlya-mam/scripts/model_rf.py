"""Федеральная модель «Для мам»: месяц 18 и деньги за 18 месяцев.

    python3 -I dlya-mam/scripts/model_rf.py

Как устроено (простыми словами):
1. Считаем, сколько мам в месяц сохраняют продукт к 18-му месяцу из пяти источников:
   ролики, платное продвижение, блогеры, поиск/Алиса, карточки в клиниках-клиентах.
2. Из этих мам часть покупает курс, часть оставляет заявки в программы клиник, они смотрят дневные страницы (реклама).
3. Отдельно от аудитории считаются деньги организаций: клиники, страховые, работодатели, курсы для врачей через НГУ,
   бренды, госзаказ, книга.
4. Вычитаем расходы месяца 18. Затем строим путь за 18 месяцев: пилот (месяцы 1–2), рост с 3-го по 18-й
   (выручка медленно на старте: доля (k²) от уровня месяца 18; расходы линейно от 40% до 100%). Отсюда — «глубина ямы»:
   сколько денег нужно вложить до выхода в плюс.
5. Монте-Карло: 10 000 прогонов, каждый параметр — треугольное распределение (low, base, high).
   Торнадо: какой параметр сильнее всего двигает выручку. «Что должно быть правдой»: чем отличаются прогоны,
   где выручка месяца 18 ≥ 10 млн ₽.
Все ДОПУЩЕНИЯ помечены в 11-model-rf.csv. Это модель для выбора, что мерить, а не прогноз прибыли.
"""
import csv
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
N, SEED, TARGET = 10_000, 20261108, 10_000_000
# «Осторожный» прогон: для этих параметров берём нижнюю половину диапазона (треугольник low, low, base).
# Это объёмы аудитории и число сделок — то, что в таблице по сути записано как цель, а не как прогноз.
CAUTIOUS = {"clips_month", "views_per_clip", "view_to_save", "blogger_integrations_month", "saves_per_integration",
            "seo_visits_m18", "seo_save_rate", "b2b2c_clinics_m18", "card_hand_rate", "save_rate_qr", "retention_months",
            "course_conv_6m", "insurers_contracts", "employers", "pro_course_sales_month", "brand_partners",
            "gov_contracts_year", "leadgen_rate", "book_copies_month"}
CAUTIOUS_UP = {"cost_per_saved_paid"}  # для цены сохранившей мамы «осторожно» — это верхняя половина


def load():
    rows = list(csv.DictReader(open(ROOT / "11-model-rf.csv", encoding="utf-8")))
    return {r["param"]: (float(r["low"]), float(r["base"]), float(r["high"])) for r in rows}


def model(p):
    o = {}
    # 1. аудитория месяца 18
    s = {
        "ролики": p["clips_month"] * p["views_per_clip"] * p["view_to_save"],
        "продвижение": p["promo_budget_month"] / p["cost_per_saved_paid"],
        "блогеры": p["blogger_integrations_month"] * p["saves_per_integration"],
        "поиск_алиса": p["seo_visits_m18"] * p["seo_save_rate"],
        "клиники_qr": p["b2b2c_clinics_m18"] * p["child_visits_per_clinic"] * p["card_hand_rate"] * p["save_rate_qr"],
    }
    for k, v in s.items():
        o[f"saved_{k}"] = v
    saved = sum(s.values())
    o["saved_month"] = saved
    o["share_of_rf_births"] = saved / p["births_rf_month"]
    active = saved * p["retention_months"]
    o["active_base"] = active
    # 2–3. деньги
    r = {
        "курсы_мам": saved * p["course_conv_6m"] * p["course_price"] * (1 - p["fees_tax"]),
        "клиники_подписка": p["b2b2c_clinics_m18"] * p["b2b2c_price_month"],
        "страховые": p["insurers_contracts"] * p["insurer_value_month"],
        "работодатели": p["employers"] * p["employer_value_month"],
        "курсы_врачей_НГУ": p["pro_course_sales_month"] * p["pro_course_price"] * p["pro_share"],
        "бренды": p["brand_partners"] * p["brand_value_month"],
        "госзаказ": p["gov_contracts_year"] * p["gov_value_contract"] / 12,
        "реклама": active * p["ad_pv_per_active"] * p["ad_cpm"] / 1000,
        "заявки_в_клиники": active * p["leadgen_rate"] * p["lead_price"],
        "книга": p["book_copies_month"] * p["book_royalty"],
    }
    for k, v in r.items():
        o[f"rev_{k}"] = v
    rev = sum(r.values())
    o["revenue_m18"] = rev
    # 4. расходы месяца 18
    cards = p["b2b2c_clinics_m18"] * p["child_visits_per_clinic"] * p["card_hand_rate"] * p["cost_card"]
    cost = (p["clips_month"] * p["cost_per_clip"] + p["promo_budget_month"]
            + p["blogger_integrations_month"] * p["blogger_cost"] + cards
            + p["prof_rate"] * p["prof_hours_month"] + p["editors"] * p["editor_salary"]
            + p["sales_team"] * p["sales_cost"] + p["tech_month"] + p["legal_month"] + p["overhead_month"]
            + p["course_production_month"])
    o["cost_m18"] = cost
    o["margin_m18"] = rev - cost
    # путь за 18 месяцев
    cum, cum_min, month_positive = -p["pilot_cost_total"], -p["pilot_cost_total"], np.full(np.shape(rev), np.nan)
    for m in range(3, 19):
        k = (m - 2) / 16
        mm = rev * (k ** 2) - cost * (0.4 + 0.6 * k)  # продажи B2B и аудитория набираются медленно
        cum = cum + mm
        cum_min = np.minimum(cum_min, cum)
        month_positive = np.where(np.isnan(month_positive) & (mm > 0), m, month_positive)
    o["cum_18"] = cum
    o["max_drawdown"] = -cum_min
    o["first_positive_month"] = month_positive
    return o


def main():
    P = load()
    base = {k: v[1] for k, v in P.items()}
    ob = model({k: np.array(v) for k, v in base.items()})
    rng = np.random.default_rng(SEED)
    S = {k: (np.full(N, m) if lo == hi else rng.triangular(lo, m, hi, N)) for k, (lo, m, hi) in P.items()}
    om = model(S)
    rng2 = np.random.default_rng(SEED + 1)
    SC = {}
    for k, (lo, m, hi) in P.items():
        if lo == hi:
            SC[k] = np.full(N, m)
        elif k in CAUTIOUS:
            SC[k] = rng2.triangular(lo, lo, m, N) if lo < m else np.full(N, lo)
        elif k in CAUTIOUS_UP:
            SC[k] = rng2.triangular(m, hi, hi, N)
        else:
            SC[k] = rng2.triangular(lo, m, hi, N)
    oc = model(SC)

    def q(x):
        x = np.asarray(x, dtype=float)
        x = x[~np.isnan(x)]
        if not len(x):
            return None
        return {t: round(float(np.percentile(x, v)), 3 if abs(np.median(x)) < 1 else 0) for t, v in (("p10", 10), ("p50", 50), ("p90", 90))}

    keys = [k for k in om if k.startswith(("saved_", "rev_"))] + ["saved_month", "share_of_rf_births", "active_base",
                                                                  "revenue_m18", "cost_m18", "margin_m18", "cum_18", "max_drawdown"]
    out = {
        "runs": N, "seed": SEED,
        "base_point": {k: round(float(ob[k]), 3) for k in keys},
        "monte_carlo": {k: q(om[k]) for k in keys},
        "first_positive_month": q(om["first_positive_month"]),
        "p_never_positive_by_m18": round(float(np.mean(np.isnan(om["first_positive_month"]))), 3),
        "p_revenue_ge_10m": round(float(np.mean(om["revenue_m18"] >= TARGET)), 3),
        "p_margin_m18_positive": round(float(np.mean(om["margin_m18"] > 0)), 3),
        "p_cum18_positive": round(float(np.mean(om["cum_18"] > 0)), 3),
        "revenue_mix_median_share": {k[4:]: round(float(np.median(om[k] / om["revenue_m18"])), 3)
                                     for k in om if k.startswith("rev_")},
    }
    out["cautious"] = {
        "monte_carlo": {k: q(oc[k]) for k in keys},
        "first_positive_month": q(oc["first_positive_month"]),
        "p_never_positive_by_m18": round(float(np.mean(np.isnan(oc["first_positive_month"]))), 3),
        "p_revenue_ge_10m": round(float(np.mean(oc["revenue_m18"] >= TARGET)), 3),
        "p_margin_m18_positive": round(float(np.mean(oc["margin_m18"] > 0)), 3),
        "p_cum18_positive": round(float(np.mean(oc["cum_18"] > 0)), 3),
        "revenue_mix_median_share": {k[4:]: round(float(np.median(oc[k] / oc["revenue_m18"])), 3)
                                     for k in oc if k.startswith("rev_")},
    }
    om_full = om
    # торнадо по выручке месяца 18
    tor = []
    for k, (lo, md, hi) in P.items():
        if lo == hi:
            continue
        a = float(model({**{x: np.array(v) for x, v in base.items()}, k: np.array(lo)})["revenue_m18"])
        b = float(model({**{x: np.array(v) for x, v in base.items()}, k: np.array(hi)})["revenue_m18"])
        tor.append({"param": k, "at_low": round(a), "at_high": round(b), "swing": round(abs(b - a))})
    tor.sort(key=lambda r: -r["swing"])
    with open(ROOT / "zamery" / "z11-tornado-rf.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tor[0]))
        w.writeheader()
        w.writerows(tor)
    out["tornado_top8"] = [(r["param"], r["swing"]) for r in tor[:8]]
    # что должно быть правдой для 10 млн
    # «Что должно быть правдой»: объединяем оба прогона (20 000) и смотрим, при каком охвате
    # и скольких клиниках выручка месяца 18 достигает 10 млн ₽.
    pen = np.concatenate([om["share_of_rf_births"], oc["share_of_rf_births"]])
    revp = np.concatenate([om["revenue_m18"], oc["revenue_m18"]])
    clin = np.concatenate([S["b2b2c_clinics_m18"], SC["b2b2c_clinics_m18"]])
    bins = [0, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 1.0]
    table = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (pen >= a) & (pen < b)
        if m.sum() < 50:
            continue
        hit = revp[m] >= TARGET
        table.append({"share_of_rf_births": f"{a:.1%}–{b:.1%}", "runs": int(m.sum()),
                      "p_revenue_ge_10m": round(float(hit.mean()), 3),
                      "median_revenue_m18": round(float(np.median(revp[m]))),
                      "median_clinics_when_10m": round(float(np.median(clin[m][hit]))) if hit.sum() >= 20 else None})
    out["what_must_be_true_by_penetration"] = table
    with open(ROOT / "zamery" / "z11-what-must-be-true.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    S, om = SC, oc
    hit = om["revenue_m18"] >= TARGET
    mbt = []
    if False:  # заменено таблицей по охвату выше
        for k, (lo, md, hi) in P.items():
            if lo == hi:
                continue
            m_all, m_hit = float(np.median(S[k])), float(np.median(S[k][hit]))
            pos = (m_hit - lo) / (hi - lo)  # где медиана «успешных» прогонов внутри диапазона: 0 = low, 1 = high
            mbt.append({"param": k, "median_all": round(m_all, 4), "median_when_10m": round(m_hit, 4),
                        "position_in_range_when_10m": round(pos, 2),
                        "shift": round((m_hit - m_all) / (hi - lo), 3)})
        mbt.sort(key=lambda r: -abs(r["shift"]))
        with open(ROOT / "zamery" / "z11-what-must-be-true.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(mbt[0]))
            w.writeheader()
            w.writerows(mbt)
        out["what_must_be_true_top8_cautious"] = [(r["param"], r["median_all"], r["median_when_10m"]) for r in mbt[:8]]
        out["share_of_rf_births_when_10m_cautious"] = q(om["share_of_rf_births"][hit])
        out["saved_month_when_10m_cautious"] = q(om["saved_month"][hit])
        out["clinics_when_10m_cautious"] = q(S["b2b2c_clinics_m18"][hit])
    json.dump(out, open(ROOT / "zamery" / "z11-rf-summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
        rs = tor[:10][::-1]
        b0 = float(ob["revenue_m18"])
        for i, r in enumerate(rs):
            lo, hi = sorted((r["at_low"], r["at_high"]))
            axes[0].barh(i, (hi - lo) / 1e6, left=lo / 1e6, color="#4C78A8")
        axes[0].axvline(b0 / 1e6, color="#333", lw=1)
        axes[0].set_yticks(range(len(rs)), [r["param"] for r in rs], fontsize=9)
        axes[0].set_title("Выручка месяца 18, млн ₽: что сильнее всего двигает (синтетика)", fontsize=10)
        axes[1].hist(om_full["revenue_m18"] / 1e6, bins=60, color="#4C78A8", alpha=0.6, label="как в таблице")
        axes[1].hist(oc["revenue_m18"] / 1e6, bins=60, color="#F58518", alpha=0.6, label="осторожно")
        axes[1].axvline(TARGET / 1e6, color="#E45756", lw=2, label="цель 10 млн ₽")
        axes[1].set_title("Выручка месяца 18, млн ₽: 10 000 прогонов (синтетика)", fontsize=10)
        axes[1].legend()
        fig.tight_layout()
        fig.savefig(ROOT / "11-model-rf.png", dpi=150)
    except ImportError:
        pass
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
