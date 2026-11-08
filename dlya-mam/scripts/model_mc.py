"""Модель вайтпейпера: пилот 8 недель и устойчивый месяц (6-й+), Монте-Карло и торнадо.

    pip install numpy matplotlib
    python3 -I dlya-mam/scripts/model_mc.py

Вход: dlya-mam/10-model.csv (low/base/high по каждому параметру, статус и источник).
Выход: zamery/z10-mc-summary.json, zamery/z10-tornado.csv, 10-tornado.png.
Распределение каждого параметра — треугольное (low, base, high), параметры независимы.
Зерно генератора фиксировано: числа воспроизводятся.
ВНИМАНИЕ: большинство параметров — ДОПУЩЕНИЕ (синтетика). Модель показывает, ЧТО мерить в пилоте,
а не сколько мы заработаем.
"""
import csv
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
N = 10_000
SEED = 20261108


def load():
    rows = list(csv.DictReader(open(ROOT / "10-model.csv", encoding="utf-8")))
    return {r["param"]: (float(r["low"]), float(r["base"]), float(r["high"])) for r in rows}, rows


def model(p):
    """p — словарь параметр -> число или массив numpy. Возвращает метрики."""
    o = {}
    # ---------- пилот: 2 месяца ----------
    qr_cards = p["qr_clinics_pilot"] * p["child_visits_per_clinic"] * p["card_hand_rate"] * 2
    o["pilot_saved_qr"] = qr_cards * p["save_rate_qr"]
    o["pilot_cost_qr"] = qr_cards * p["cost_card"] + p["qr_clinics_pilot"] * p["setup_hours_clinic"] * p["team_hour_rate"]
    # учреждения: при договоре работает 1 месяц из 2
    o["pilot_saved_inst"] = p["p_inst_deal_pilot"] * p["births_month"] * p["inst_coverage"] * p["save_rate_inst"]
    o["pilot_cost_inst"] = p["negotiation_hours"] * p["team_hour_rate"] + \
        p["p_inst_deal_pilot"] * p["births_month"] * p["inst_coverage"] * p["cost_card"]
    o["pilot_saved_clips"] = p["clips_month"] * p["views_per_clip"] * p["view_to_save"] * 2
    o["pilot_cost_clips"] = p["clips_month"] * p["cost_per_clip"] * 2
    o["pilot_saved_publics"] = p["publics_posts_month"] * p["publics_reach_post"] * p["publics_save_rate"] * 2
    o["pilot_cost_publics"] = p["publics_posts_month"] * p["publics_price_post"] * 2
    o["pilot_saved_direct"] = p["direct_clicks_month"] * p["direct_save_rate"] * 2
    o["pilot_cost_direct"] = p["direct_clicks_month"] * p["direct_cpc"] * 2
    ch = ["qr", "inst", "clips", "publics", "direct"]
    o["pilot_saved_total"] = sum(o[f"pilot_saved_{c}"] for c in ch)
    for c in ch:
        o[f"pilot_cac_saved_{c}"] = o[f"pilot_cost_{c}"] / np.maximum(o[f"pilot_saved_{c}"], 1e-9)
    fixed_pilot = p["tech_one_off"] + p["legal_one_off"] + 2 * (p["editor_month"] + p["tech_month"] + p["prof_rate"] * p["prof_hours_month"])
    o["pilot_cost_total"] = fixed_pilot + sum(o[f"pilot_cost_{c}"] for c in ch)
    o["pilot_prepayments"] = o["pilot_saved_total"] * p["presale_conv_pilot"]
    o["pilot_presale_revenue"] = o["pilot_prepayments"] * p["course_price"] * (1 - p["fees_tax"])
    o["pilot_b2b_signed"] = p["b2b_talks"] * p["b2b_p_sign"]

    # ---------- устойчивый месяц (6-й и дальше) ----------
    qr_cards_m = p["qr_clinics_scale"] * p["child_visits_per_clinic"] * p["card_hand_rate"]
    inst_cards_m = p["p_inst_deal_m6"] * p["births_month"] * p["inst_coverage"]
    s = {
        "qr": qr_cards_m * p["save_rate_qr"],
        "inst": inst_cards_m * p["save_rate_inst"],
        "clips": p["clips_month"] * p["views_per_clip"] * p["view_to_save"],
        "publics": p["publics_posts_month"] * p["publics_reach_post"] * p["publics_save_rate"],
        "direct": p["direct_clicks_month"] * p["direct_save_rate"],
        "seo": p["seo_visits_m6"] * p["seo_save_rate"],
    }
    c = {
        "qr": qr_cards_m * p["cost_card"], "inst": inst_cards_m * p["cost_card"],
        "clips": p["clips_month"] * p["cost_per_clip"], "publics": p["publics_posts_month"] * p["publics_price_post"],
        "direct": p["direct_clicks_month"] * p["direct_cpc"], "seo": 0 * p["seo_visits_m6"],
    }
    for k in s:
        o[f"m6_saved_{k}"] = s[k]
    o["m6_saved_total"] = sum(s.values())
    o["m6_active_base"] = o["m6_saved_total"] * p["retention_months"]
    o["m6_buyers"] = o["m6_saved_total"] * p["buyer_conv_6m"]
    o["m6_rev_courses"] = o["m6_buyers"] * p["course_price"] * (1 - p["fees_tax"])
    o["m6_rev_b2b"] = p["b2b_clients_m6"] * p["b2b_value_month"]
    o["m6_rev_ads"] = o["m6_active_base"] * p["ad_pv_per_saved"] * p["ad_cpm"] / 1000
    o["m6_revenue"] = o["m6_rev_courses"] + o["m6_rev_b2b"] + o["m6_rev_ads"]
    o["m6_cost"] = (p["editor_month"] + p["tech_month"] + p["prof_rate"] * p["prof_hours_month"]
                    + sum(c.values()) + p["course_production_one_off"] / 12)
    o["m6_margin"] = o["m6_revenue"] - o["m6_cost"]
    o["m6_cac_buyer_paid_channels"] = (c["clips"] + c["publics"] + c["direct"]) / np.maximum(
        (s["clips"] + s["publics"] + s["direct"]) * p["buyer_conv_6m"], 1e-9)
    return o


def main():
    P, rows = load()
    base = {k: v[1] for k, v in P.items()}
    ob = model(base)
    rng = np.random.default_rng(SEED)
    sample = {}
    for k, (lo, md, hi) in P.items():
        sample[k] = np.full(N, md) if lo == hi else rng.triangular(lo, md, hi, N)
    om = model(sample)

    def q(x):
        x = np.asarray(x)
        return {"p10": round(float(np.percentile(x, 10)), 1), "p50": round(float(np.percentile(x, 50)), 1),
                "p90": round(float(np.percentile(x, 90)), 1)}

    keys = ["pilot_saved_total", "pilot_saved_qr", "pilot_saved_inst", "pilot_saved_clips", "pilot_saved_publics",
            "pilot_saved_direct", "pilot_cost_total", "pilot_prepayments", "pilot_presale_revenue", "pilot_b2b_signed",
            "pilot_cac_saved_qr", "pilot_cac_saved_inst", "pilot_cac_saved_clips", "pilot_cac_saved_publics",
            "pilot_cac_saved_direct", "m6_saved_total", "m6_saved_qr", "m6_saved_inst", "m6_saved_clips",
            "m6_saved_publics", "m6_saved_direct", "m6_saved_seo", "m6_buyers", "m6_rev_courses", "m6_rev_b2b",
            "m6_rev_ads", "m6_revenue", "m6_cost", "m6_margin", "m6_cac_buyer_paid_channels"]
    S = {"runs": N, "seed": SEED,
         "base_point": {k: round(float(ob[k]), 1) for k in keys},
         "monte_carlo": {k: q(om[k]) for k in keys},
         "p_m6_margin_positive": round(float(np.mean(om["m6_margin"] > 0)), 3),
         "p_pilot_prepayments_ge_30": round(float(np.mean(om["pilot_prepayments"] >= 30)), 3),
         "share_m6_revenue": {k: round(float(np.median(om[k] / np.maximum(om["m6_revenue"], 1e-9))), 3)
                              for k in ("m6_rev_courses", "m6_rev_b2b", "m6_rev_ads")}}
    # сценарий «экономный»: профессоров оплачивает НГУ, редактор на полставки, минимальная техника
    lean_over = {"prof_rate": 0, "editor_month": 60000, "tech_one_off": 40000, "legal_one_off": 0}
    ol = model({**base, **lean_over})
    S["scenario_lean"] = {"overrides": lean_over, **{k: round(float(ol[k]), 1) for k in
                          ("pilot_cost_total", "m6_cost", "m6_revenue", "m6_margin")}}
    unit_l = ol["m6_buyers"] * (1 - base["fees_tax"])
    S["scenario_lean"]["breakeven_course_price"] = round(float((ol["m6_cost"] - (ol["m6_revenue"] - ol["m6_rev_courses"])) / unit_l), 0)
    # цена курса, при которой устойчивый месяц выходит в ноль (базовая точка)
    other = ob["m6_revenue"] - ob["m6_rev_courses"]
    unit = ob["m6_buyers"] * (1 - base["fees_tax"])
    S["breakeven_course_price_base"] = round(float((ob["m6_cost"] - other) / unit), 0) if unit > 0 else None

    # торнадо: один параметр в low/high, остальные — base
    tor = []
    for target in ("m6_margin", "pilot_saved_total"):
        for k, (lo, md, hi) in P.items():
            if lo == hi:
                continue
            a = model({**base, k: lo})[target]
            b = model({**base, k: hi})[target]
            tor.append({"target": target, "param": k, "at_low": round(float(a)), "at_high": round(float(b)),
                        "swing": round(float(abs(b - a)))})
    tor.sort(key=lambda r: (r["target"], -r["swing"]))
    with open(ROOT / "zamery" / "z10-tornado.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tor[0]))
        w.writeheader()
        w.writerows(tor)
    S["tornado_top5"] = {t: [(r["param"], r["swing"]) for r in tor if r["target"] == t][:5]
                         for t in ("m6_margin", "pilot_saved_total")}
    json.dump(S, open(ROOT / "zamery" / "z10-mc-summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        for ax, t, title in zip(axes, ("m6_margin", "pilot_saved_total"),
                                ("Маржа устойчивого месяца, ₽", "Сохранивших мам за пилот")):
            rs = [r for r in tor if r["target"] == t][:8][::-1]
            b0 = ob[t]
            for i, r in enumerate(rs):
                lo, hi = sorted((r["at_low"], r["at_high"]))
                ax.barh(i, hi - lo, left=lo, color="#4C78A8")
            ax.axvline(b0, color="#333", lw=1)
            ax.set_yticks(range(len(rs)), [r["param"] for r in rs], fontsize=9)
            ax.set_title(title + " (синтетика)", fontsize=11)
        fig.tight_layout()
        fig.savefig(ROOT / "10-tornado.png", dpi=150)
    except ImportError:
        print("matplotlib нет — картинка не построена, таблица в zamery/z10-tornado.csv")
    print(json.dumps(S, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
