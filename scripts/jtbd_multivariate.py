"""Многомерный статистический анализ JTBD по двум источникам: Вордстат (фразы) и форумы (сообщения).

Запуск (нужны numpy, scipy, scikit-learn — не входят в обязательные зависимости MVP):
  PYTHONPATH=src python3 scripts/jtbd_multivariate.py

Вход: config/jtbd_jobs.yaml, data/raw/wordstat_2026-11/clustered.csv, data/raw/forums_ru_*/ (локально, не в git).
Выход: reports/ru_market_2026-11/jtbd/{all.jsonl, jobs_stats.csv, multivariate.json}.
Тексты сообщений в выход не попадают — только счётчики, годы, ссылки на темы и поисковые фразы (агрегаты Вордстата)."""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import yaml
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import chi2_contingency, spearmanr
from sklearn.decomposition import NMF, PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from proba.demand import forum_analysis as fa
from proba.demand.adapters.forum_export import load_export

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ru_market_2026-11/jtbd"
INTENTS = ["broad", "question", "info", "reviews", "commercial", "navigational", "diy"]
RNG = 20261106


def load_jobs():
    jobs = yaml.safe_load((ROOT / "config/jtbd_jobs.yaml").read_text(encoding="utf-8"))["jobs"]
    for j in jobs:
        j["rx"] = [re.compile(p) for p in j["patterns"]]
    return jobs


def match(jobs, text):
    return [j["id"] for j in jobs if any(r.search(text) for r in j["rx"])]


def wordstat(jobs):
    rows = list(csv.DictReader(open(ROOT / "data/raw/wordstat_2026-11/clustered.csv", encoding="utf-8"), delimiter=";"))
    keep = [r for r in rows if r["relevance"] in ("target", "education")]
    hits = defaultdict(list)          # job -> [(phrase, freq, intent)]
    phrase_jobs = {}
    for r in keep:
        js = match(jobs, r["phrase"])
        if js:
            phrase_jobs[r["phrase"]] = js
        for j in js:
            hits[j].append((r["phrase"], int(r["freq"]), r["intent"]))
    return keep, hits, phrase_jobs


def forums(jobs, lex):
    threads = []
    for d in ("forums_ru_2026-11", "forums_ru_fresh_2026-11"):
        threads += load_export(ROOT / "data/raw" / d)[0]
    msgs = fa.build_messages(threads)
    fa.clean(msgs)
    fa.segment(msgs, lex, {"pikabu": "consumer", "it_alfemminile": "consumer"})
    turl = {f"{t.source_id}:{t.external_id}": t.url for t in threads}
    hits = defaultdict(list)          # job -> [Msg]
    for m in msgs:
        if not m.demand_signal or m.source_id == "it_alfemminile":   # российский рынок: Италию не берём
            continue
        for j in match(jobs, m.text.lower()):
            hits[j].append(m)
    return msgs, hits, turl


def correspondence_analysis(N):
    P = N / N.sum()
    r, c = P.sum(1), P.sum(0)
    S = (P - np.outer(r, c)) / np.sqrt(np.outer(r, c))
    U, s, Vt = np.linalg.svd(S, full_matrices=False)
    inertia = s ** 2
    F = (U * s) / np.sqrt(r)[:, None]          # координаты строк
    G = (Vt.T * s) / np.sqrt(c)[:, None]       # координаты столбцов
    return F, G, inertia / inertia.sum()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs()
    lex = yaml.safe_load((ROOT / "config/demand_lexicon.yaml").read_text(encoding="utf-8"))
    keep, ws, phrase_jobs = wordstat(jobs)
    msgs, fo, turl = forums(jobs, lex)
    ids = [j["id"] for j in jobs]
    by = {j["id"]: j for j in jobs}

    # ---- метрики по работам
    records = []
    for j in jobs:
        h = ws.get(j["id"], [])
        m = fo.get(j["id"], [])
        head = max(h, key=lambda x: x[1]) if h else ("", 0, "")
        ic = Counter(i for _, f, i in h)
        icw = defaultdict(float)
        for _, f, i in h:
            icw[i] += math.log1p(f)
        tot_w = sum(icw.values()) or 1
        years = sorted(x.year for x in m if x.year)
        seg = Counter(x.segment for x in m)
        thr = Counter(x.thread_key for x in m)
        rec = {
            "id": j["id"], "segment": j["segment"], "mode": j["mode"], "cluster": j["cluster"], "job": j["job"],
            "content": j["content"],
            "ws_phrases": len(h), "ws_head_phrase": head[0], "ws_head_freq": head[1],
            "ws_mass_rough": sum(f for _, f, _ in h),
            "ws_top": [f"{p} ({f})" for p, f, _ in sorted(h, key=lambda x: -x[1])[:6]],
            "ws_top_questions": [f"{p} ({f})" for p, f, i in sorted(h, key=lambda x: -x[1]) if i == "question"][:5],
            "intent_share": {i: round(icw[i] / tot_w, 3) for i in INTENTS},
            "forum_messages": len(m), "forum_threads": len(thr),
            "forum_sources": dict(Counter(x.source_id for x in m)),
            "forum_years": {"min": years[0], "median": years[len(years) // 2], "max": years[-1]} if years else None,
            "forum_actual_share": round(sum(1 for x in m if x.period == "actual") / len(m), 3) if m else None,
            "forum_segment": dict(seg),
            "forum_threads_top": [turl[k] for k, _ in thr.most_common(3)],
        }
        records.append(rec)

    # ---- 1. Анализ соответствий: работа × интент (веса log1p частоты)
    N = np.array([[sum(math.log1p(f) for _, f, i in ws.get(jid, []) if i == it) for it in INTENTS] for jid in ids]) + 1e-9
    ok = N.sum(1) > 1
    F, G, expl = correspondence_analysis(N[ok])
    ca = {"explained": [round(float(x), 3) for x in expl[:3]],
          "intents": {it: [round(float(G[k, 0]), 3), round(float(G[k, 1]), 3)] for k, it in enumerate(INTENTS)},
          "jobs": {jid: [round(float(F[n, 0]), 3), round(float(F[n, 1]), 3)] for n, jid in enumerate([i for i, o in zip(ids, ok) if o])}}

    # ---- 2. PCA + иерархическая кластеризация работ (режимы из данных)
    cons = [r for r in records if r["segment"] == "consumer" and r["ws_phrases"] > 0]
    X = np.array([[r["intent_share"][i] for i in INTENTS] +
                  [math.log1p(r["ws_mass_rough"]), math.log1p(r["forum_messages"]),
                   math.log1p(r["forum_messages"]) - math.log1p(r["ws_mass_rough"]) / 3,
                   (r["forum_actual_share"] or 0)] for r in cons])
    feat = INTENTS + ["log_search_mass", "log_forum_msgs", "forum_vs_search", "forum_fresh_share"]
    Z = StandardScaler().fit_transform(X)
    pca = PCA(n_components=3, random_state=RNG).fit(Z)
    L = linkage(Z, "ward")
    best = max(range(3, 8), key=lambda k: silhouette_score(Z, fcluster(L, k, "maxclust")))
    lab = fcluster(L, best, "maxclust")
    modes = [r["mode"] for r in cons]
    hc = {"k": best, "silhouette": round(float(silhouette_score(Z, lab)), 3),
          "ari_vs_modes": round(float(adjusted_rand_score(modes, lab)), 3),
          "groups": {int(g): [r["id"] for r, l in zip(cons, lab) if l == g] for g in sorted(set(lab))},
          "pca_explained": [round(float(x), 3) for x in pca.explained_variance_ratio_],
          "pca_loadings": {f"PC{k+1}": {f: round(float(v), 2) for f, v in sorted(zip(feat, pca.components_[k]), key=lambda x: -abs(x[1]))[:5]} for k in range(2)}}

    # ---- 3. NMF: латентные темы поиска без словаря
    texts = [r["phrase"] for r in keep]
    w = np.array([math.log1p(int(r["freq"])) for r in keep])
    vec = TfidfVectorizer(min_df=30, ngram_range=(1, 2), token_pattern=r"(?u)\b[а-яёa-z]{3,}\b",
                          stop_words=["для", "что", "как", "это", "или", "при", "после", "можно", "лица", "отзывы", "цена", "какой"])
    T = vec.fit_transform(texts).multiply(w[:, None]).tocsr()
    nmf = NMF(n_components=14, init="nndsvda", random_state=RNG, max_iter=400)
    W = nmf.fit_transform(T)
    terms = np.array(vec.get_feature_names_out())
    topics = []
    tw = W.argmax(1)
    for k, comp in enumerate(nmf.components_):
        top = terms[comp.argsort()[::-1][:8]].tolist()
        members = np.where(tw == k)[0]
        mass = float(sum(int(keep[i]["freq"]) for i in members))
        topics.append({"topic": k, "top_terms": top, "phrases": int(len(members)), "mass_rough": int(mass)})
    # согласие тем с работами (только фразы, попавшие ровно в одну работу)
    single = [(i, phrase_jobs[keep[i]["phrase"]][0]) for i in range(len(keep)) if len(phrase_jobs.get(keep[i]["phrase"], [])) == 1]
    nmi = normalized_mutual_info_score([tw[i] for i, _ in single], [jid for _, jid in single]) if single else None
    coverage = sum(1 for r in keep if r["phrase"] in phrase_jobs) / len(keep)
    cov_mass = sum(int(r["freq"]) for r in keep if r["phrase"] in phrase_jobs) / sum(int(r["freq"]) for r in keep)

    # ---- 4. Форумы: работа × сегмент, работа × период (χ², V Крамера, стандартизованные остатки)
    def chi(rows_ids, cols, getter):
        M = np.array([[sum(1 for m in fo.get(jid, []) if getter(m) == c) for c in cols] for jid in rows_ids])
        keep_r = M.sum(1) >= 5
        M = M[keep_r]
        rid = [jid for jid, k in zip(rows_ids, keep_r) if k]
        chi2, p, dof, E = chi2_contingency(M)
        V = math.sqrt(chi2 / (M.sum() * (min(M.shape) - 1)))
        R = (M - E) / np.sqrt(E)
        top = sorted(((rid[a], cols[b], round(float(R[a, b]), 1)) for a in range(len(rid)) for b in range(len(cols))), key=lambda x: -x[2])[:8]
        return {"chi2": round(float(chi2), 1), "dof": int(dof), "p": float(p), "cramers_v": round(V, 3), "n": int(M.sum()), "top_positive_residuals": top}
    seg_test = chi(ids, ["consumer", "professional", "unclear"], lambda m: m.segment)
    pfk = lambda m: m.period if m.source_id == "ru_pf_k" else None
    per_test = chi(ids, ["actual", "historical"], pfk)

    # ---- 5. Совместная встречаемость работ в темах форумов (lift)
    thread_jobs = defaultdict(set)
    for jid, ms in fo.items():
        for m in ms:
            thread_jobs[m.thread_key].add(jid)
    nT = len(thread_jobs)
    single_c = Counter(j for s in thread_jobs.values() for j in s)
    pair_c = Counter(p for s in thread_jobs.values() for p in combinations(sorted(s), 2))
    lifts = sorted(((a, b, n, round(n * nT / (single_c[a] * single_c[b]), 2)) for (a, b), n in pair_c.items() if n >= 4), key=lambda x: -x[3])[:12]

    # ---- 6. Поиск против форумов (потребительские работы)
    cr = [r for r in records if r["segment"] == "consumer"]
    rho, pval = spearmanr([r["ws_mass_rough"] for r in cr], [r["forum_messages"] for r in cr])

    multi = {"correspondence_analysis": ca, "job_clustering": hc,
             "nmf_topics": {"k": 14, "topics": topics, "nmi_topics_vs_jobs": round(float(nmi), 3) if nmi is not None else None,
                            "job_coverage_phrases": round(coverage, 3), "job_coverage_mass": round(cov_mass, 3)},
             "forum_segment_test": seg_test, "pfk_period_test": per_test, "cooccurrence_lift": lifts,
             "search_vs_forum_spearman": {"rho": round(float(rho), 3), "p": round(float(pval), 4), "n": len(cr)},
             "n": {"wordstat_phrases_used": len(keep), "forum_messages_used": sum(1 for m in msgs if m.demand_signal and m.source_id != "it_alfemminile")}}
    with (OUT / "all.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / "multivariate.json").write_text(json.dumps(multi, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "jobs_stats.csv").open("w", encoding="utf-8", newline="") as f:
        cols = ["id", "segment", "mode", "cluster", "ws_head_phrase", "ws_head_freq", "ws_phrases", "ws_mass_rough", "forum_messages", "forum_threads", "forum_actual_share"]
        wr = csv.writer(f, delimiter=";")
        wr.writerow(cols + ["q_share", "after_like"])
        for r in records:
            wr.writerow([r[c] for c in cols] + [r["intent_share"]["question"], ""])
    print(json.dumps({k: multi[k] for k in ("n", "search_vs_forum_spearman")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
