"""Модель по плану владельца (2026-11-08): помесячно на 18 месяцев.

    python3 -I dlya-mam/scripts/model_owner.py

Расходы — только профессора (150 тыс.) и реклама с блогерами (300 тыс.), плюс налог и эквайринг от выручки.
Карточки печатает клиника (вариант «печатаем мы» считается отдельно).
Клиники: N к концу 3-го месяца, дальше +M в месяц, уход клиник — доля в месяц, первый месяц бесплатный.
Мамы: из карточек клиник + органика (растёт линейно к 18-му месяцу) + реклама.
Деньги: подписка клиник, платный курс (с месяца запуска), платные эфиры (с 4-го месяца).
Монте-Карло: 10 000 прогонов, треугольные распределения (low, base, high). Всё, кроме бюджетов, — ДОПУЩЕНИЕ.
"""
import csv
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
N, SEED, MONTHS = 10_000, 20261108, 18


def load():
    return {r["param"]: (float(r["low"]), float(r["base"]), float(r["high"]))
            for r in csv.DictReader(open(ROOT / "15-model-owner.csv", encoding="utf-8"))}


def simulate(p, we_print=False):
    shape = np.shape(p["price_clinic"])
    clinics = np.zeros(shape)
    paying = np.zeros(shape)
    cum = np.zeros(shape)
    cum_min = np.zeros(shape)
    first_pos = np.full(shape, np.nan)
    cohorts = []  # сохранившие по месяцам — для курса
    active = np.zeros(shape)
    rows = []
    for m in range(1, MONTHS + 1):
        # клиники
        if m <= 3:
            target = p["clinics_first3"] * m / 3
            new = np.maximum(target - clinics, 0)
        else:
            new = p["clinics_per_month"]
        clinics = clinics * (1 - p["churn_month"]) + new
        paying = np.maximum(clinics - new * p["free_month"], 0)  # новые клиники в первый месяц бесплатно
        # мамы
        cards = clinics * p["child_visits_per_clinic"] * p["card_hand_rate"]
        saved_qr = cards * p["save_rate_qr"]
        saved_org = p["organic_saved_m18"] * m / MONTHS
        saved_ad = p["ad_budget"] / p["cost_per_saved_paid"]
        saved = saved_qr + saved_org + saved_ad
        cohorts.append(saved)
        active = active * (1 - 1 / p["retention_months"]) + saved
        # деньги
        rev_clin = paying * p["price_clinic"]
        if m >= 1:
            buyers = sum(cohorts[-6:]) * p["course_conv_6m"] / 6
            rev_course = np.where(m >= p["course_start_month"], buyers * p["course_price"], 0)
        rev_web = np.where(m >= 4, active * p["webinar_rate"] * p["webinar_price"], 0)
        rev = rev_clin + rev_course + rev_web
        cost = p["prof_budget"] + p["ad_budget"] + rev * p["fees_tax"] + (cards * p["card_cost"] if we_print else 0)
        profit = rev - cost
        cum = cum + profit
        cum_min = np.minimum(cum_min, cum)
        first_pos = np.where(np.isnan(first_pos) & (profit > 0), m, first_pos)
        rows.append({"month": m, "clinics": clinics, "paying": paying, "saved": saved, "active": active,
                     "rev_clinics": rev_clin, "rev_course": rev_course, "rev_webinars": rev_web,
                     "revenue": rev, "cost": cost, "profit": profit, "cum": cum})
    return rows, cum_min, first_pos


def main():
    P = load()
    base = {k: np.array(v[1]) for k, v in P.items()}
    rb, dd_b, fp_b = simulate(base)
    rng = np.random.default_rng(SEED)
    S = {k: (np.full(N, m) if lo == hi else rng.triangular(lo, m, hi, N)) for k, (lo, m, hi) in P.items()}
    rs, dd, fp = simulate(S)
    rs_print, dd_p, _ = simulate(S, we_print=True)

    def q(x):
        x = np.asarray(x, float)
        x = x[~np.isnan(x)]
        return {t: round(float(np.percentile(x, v))) for t, v in (("p10", 10), ("p50", 50), ("p90", 90))}

    table = [{k: (round(float(v)) if k != "month" else v) for k, v in r.items()} for r in rb]
    with open(ROOT / "zamery" / "z15-owner-monthly-base.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    m18 = rs[-1]
    out = {
        "base_m18": table[-1],
        "base_max_drawdown": round(float(-dd_b)), "base_first_profit_month": float(fp_b),
        "mc_m18": {k: q(m18[k]) for k in ("clinics", "paying", "saved", "active", "rev_clinics", "rev_course",
                                           "rev_webinars", "revenue", "cost", "profit", "cum")},
        "mc_max_drawdown": q(-dd), "mc_first_profit_month": q(fp),
        "mc_m6": {k: q(rs[5][k]) for k in ("paying", "revenue", "profit")},
        "mc_m12": {k: q(rs[11][k]) for k in ("paying", "revenue", "profit")},
        "if_we_print_cards": {"m18_profit": q(rs_print[-1]["profit"]), "cum18": q(rs_print[-1]["cum"]),
                              "max_drawdown": q(-dd_p)},
        "p_profit_m18_ge_3m": round(float(np.mean(m18["profit"] >= 3e6)), 3),
        "p_cum18_positive": round(float(np.mean(m18["cum"] > 0)), 3),
    }
    # чувствительность: что если сарафан слабее
    for name, over in {"по_5_клиник_в_месяц": {"clinics_per_month": np.array(5.0)},
                       "за_3_месяца_10_клиник": {"clinics_first3": np.array(10.0)},
                       "цена_15_тыс": {"price_clinic": np.array(15000.0)},
                       "уход_5%_в_месяц": {"churn_month": np.array(0.05)}}.items():
        r, d, f = simulate({**base, **over})
        out[f"base_if_{name}"] = {"m18_revenue": round(float(r[-1]["revenue"])), "m18_profit": round(float(r[-1]["profit"])),
                                  "cum18": round(float(r[-1]["cum"])), "paying_m18": round(float(r[-1]["paying"]))}
    json.dump(out, open(ROOT / "zamery" / "z15-owner-summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
