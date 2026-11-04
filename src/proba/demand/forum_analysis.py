"""Анализ сообщений форумов: очистка, период, сегмент (специалист / потребитель), понятия и кластеры.

Работает по сообщениям (Discussion.comments из адаптера forum_export), детерминированно и без сети.
Наблюдения (числа, ссылки, даты) отделены от гипотез (JTBD, темы контента — config/jtbd_ru_2026-11.yaml).
Частота в выборке — не объём рынка. Тренд не утверждается: периоды только показываются рядом.
Тексты сообщений в отчёты не попадают: только ID, ссылки, числа и редакционные пересказы."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .clean import jaccard, norm_tokens
from .models import Discussion

ACTUAL_YEARS = (2024, 2026)  # «актуальные» по заданию владельца; остальное — «исторические»

# Сильные признаки рекламы/спама в тексте сообщения (собственная разметка, сравнивается с меткой выгрузки).
AD_PATTERNS = [
    r"\bкупить\b.{0,60}\b(оригинал|в наличии|любое количество|опт)", r"гаранти\w* (самой )?низкой цен", r"прямые поставки",
    r"\bзвоните\b", r"пишите (в )?(личк|лс|whatsapp|ватсап|директ|вайбер|телеграм)", r"промокод", r"\bскидк\w* до\b",
    r"\d[\d\s]*\s?(руб(лей|\.)?|₽)\b", r"\bоптом\b", r"казино", r"\bставк\w* на спорт", r"турнир\w* .{0,40}призов",
    r"приглашаем\b", r"приглашает\b", r"\bнаш(а|ей|и|у)? (компани|магазин|интернет-магазин|клиник|учебн)",
    r"\bзаказывайте\b", r"бесплатн\w* доставк", r"мы являемся официальн", r"\bпредлагаем\b", r"готовы предложить",
    r"\bновинк[аи] (в|от)\b", r"компания [«\"]?\w+.{0,40}(разрабатывает|является|основанн|производит)",
]
EXPORT_EXCLUDE_ROLES = {"promotion": "ad_or_spam_export", "possible_promotion": "possible_ad_export",
                        "off_topic": "off_topic_export", "administrative": "administrative_export"}
CONSUMER_CUES = [r"\bмой косметолог", r"хожу к косметолог", r"\bмне (посоветовал|назначил|сделал)", r"у меня (кожа|проблем|пигмент|акне|прыщ|сух|жирн)",
                 r"\bмоя кожа", r"для себя", r"я не косметолог", r"купила себе", r"\bмне \d{2} (год|лет)", r"\bмоей кож"]
SHORT_CHARS = 25


@dataclass
class Msg:
    record_id: str
    thread_key: str
    source_id: str
    url: str
    published_at: str
    language: str
    text: str
    export: dict[str, Any]
    thread_title: str
    status: str = "ok"                    # ok | short_context | brand_answer | <причина исключения>
    own_ad: bool = False
    duplicate_of: str | None = None
    segment: str = "unclear"              # professional | consumer | unclear
    segment_basis: str = ""
    concepts: list[str] = field(default_factory=list)

    @property
    def year(self) -> int | None:
        return int(self.published_at[:4]) if self.published_at[:4].isdigit() else None

    @property
    def period(self) -> str:
        y = self.year
        if y is None:
            return "unknown"
        return "actual" if ACTUAL_YEARS[0] <= y <= ACTUAL_YEARS[1] else "historical"

    @property
    def demand_signal(self) -> bool:
        """Сообщение учитывается в спросе: не исключено, не короткая реплика, не ответ представителя бренда."""
        return self.status == "ok"


def _norm_text(text: str) -> str:
    t = unicodedata.normalize("NFC", text.lower()).replace("[external_link]", " ")
    return re.sub(r"[\W_]+", " ", t).strip()


def _match(patterns: list[str], text: str) -> list[str]:
    return [p for p in patterns if re.search(p, text)]


def build_messages(threads: list[Discussion]) -> list[Msg]:
    out = []
    for t in threads:
        for c in t.comments:
            out.append(Msg(record_id=c["record_id"], thread_key=c["thread_key"], source_id=t.source_id,
                           url=c.get("message_url") or t.url, published_at=c.get("published_at") or "",
                           language=c.get("language_original") or t.language or "und", text=c.get("text") or "",
                           export=c.get("export_labels") or {}, thread_title=t.title or ""))
    out.sort(key=lambda m: (m.published_at, m.record_id))
    return out


def clean(msgs: list[Msg], near_threshold: float = 0.85) -> dict[str, Any]:
    """Пустые, реклама/спам, посторонние, точные и близкие повторы. Порядок — по дате: оригинал старше повтора."""
    exact: dict[str, str] = {}
    kept_tokens: list[tuple[set[str], Msg]] = []
    for m in msgs:
        norm = _norm_text(m.text)
        m.own_ad = bool(_match(AD_PATTERNS, m.text.lower()))
        role = m.export.get("content_role")
        if not norm:
            m.status = "empty"
            continue
        if m.own_ad:
            m.status = "ad_or_spam_own"
        elif role in EXPORT_EXCLUDE_ROLES:
            m.status = EXPORT_EXCLUDE_ROLES[role]
        if len(norm) >= 40:
            h = hashlib.sha256(norm.encode()).hexdigest()
            if h in exact:
                m.duplicate_of = exact[h]
            else:
                exact[h] = m.record_id
                toks = norm_tokens(norm)
                if len(toks) >= 12:
                    for kt, k in kept_tokens:
                        if jaccard(toks, kt) >= near_threshold:
                            m.duplicate_of = k.record_id
                            break
                    else:
                        kept_tokens.append((toks, m))
        if m.status != "ok":
            continue
        if m.duplicate_of:
            m.status = "duplicate"
        elif role == "brand_answer":
            m.status = "brand_answer"      # ответ, вероятно, представителя бренда: контекст, не спрос
        elif len(norm) < SHORT_CHARS and "?" not in m.text:
            m.status = "short_context"

    statuses = Counter(m.status for m in msgs)
    # Сверка собственной метки рекламы с меткой подготовителя выгрузки.
    exp_ad = {m.record_id for m in msgs if m.export.get("content_role") in ("promotion", "possible_promotion")}
    own_ad = {m.record_id for m in msgs if m.own_ad}
    return {
        "statuses": dict(statuses.most_common()),
        "ad_agreement": {"both": len(exp_ad & own_ad), "export_only": len(exp_ad - own_ad), "own_only": len(own_ad - exp_ad)},
        "duplicates": [{"record_id": m.record_id, "duplicate_of": m.duplicate_of} for m in msgs if m.duplicate_of],
    }


def segment(msgs: list[Msg], lexicon: dict, sources_audience: dict[str, str]) -> None:
    """Сегмент автора сообщения. Профессия не предполагается по площадке: на PF-K без признаков — unclear."""
    prof = lexicon["professional_cues"]
    for m in msgs:
        low = m.text.lower()
        p, c = _match(prof, low), _match(CONSUMER_CUES, low)
        exp_aud, exp_basis = m.export.get("audience"), m.export.get("audience_basis")
        if p and not c:
            m.segment, m.segment_basis = "professional", "text_cues"
        elif c and not p:
            m.segment, m.segment_basis = "consumer", "text_cues"
        elif exp_basis == "curated_text_context" and exp_aud in ("professional", "consumer"):
            m.segment, m.segment_basis = exp_aud, "export_curated_label"
        elif sources_audience.get(m.source_id) == "consumer":
            m.segment, m.segment_basis = "consumer", "consumer_only_source"
        else:
            m.segment, m.segment_basis = "unclear", "mixed_cues" if (p and c) else "no_cues"


def tag_concepts(msgs: list[Msg], lexicon: dict) -> None:
    for m in msgs:
        low = m.text.lower()
        m.concepts = [name for name, pats in lexicon["concepts"].items() if _match(pats, low)]


def title_concepts(title: str, lexicon: dict) -> list[str]:
    low = title.lower()
    return [name for name, pats in lexicon["concepts"].items() if _match(pats, low)]


def _confidence(threads: int, sources: int, actual_threads: int) -> str:
    # «Высокая» не присваивается: выборка мала, неслучайна и в основном историческая.
    if threads >= 5 and sources >= 2 and actual_threads >= 2:
        return "средняя"
    return "низкая"


def build_clusters(threads: list[Discussion], msgs: list[Msg], lexicon: dict, needs: list[dict] | None = None) -> list[dict[str, Any]]:
    defs = {c["id"]: c for c in lexicon["clusters"]}
    concept_to = defaultdict(list)
    for c in lexicon["clusters"]:
        for concept in c["concepts"]:
            concept_to[concept].append(c["id"])
    tconcepts = {f"{t.source_id}:{t.external_id}": title_concepts(t.title or "", lexicon) for t in threads}
    turl = {f"{t.source_id}:{t.external_id}": t.url for t in threads}
    ttitle = {f"{t.source_id}:{t.external_id}": t.title for t in threads}
    need_by_record = defaultdict(list)
    for n in needs or []:
        if not n.get("is_counterexample"):
            need_by_record[n["record_id"]].append(n)

    direct: dict[str, list[Msg]] = defaultdict(list)
    for m in msgs:
        if not m.demand_signal:
            continue
        for cid in {cid for con in m.concepts for cid in concept_to.get(con, [])}:
            direct[cid].append(m)
    title_threads: dict[str, set[str]] = defaultdict(set)
    for key, cons in tconcepts.items():
        for cid in {cid for con in cons for cid in concept_to.get(con, [])}:
            title_threads[cid].add(key)

    out = []
    for cid in lexicon.get("primary_order") or list(defs):
        mem = direct.get(cid, [])
        thread_keys = {m.thread_key for m in mem} | title_threads.get(cid, set())
        if not thread_keys:
            continue
        # Сообщения из тем с подходящим заголовком без собственного совпадения — отдельный счёт «по контексту темы».
        ctx = [m for m in msgs if m.demand_signal and m.thread_key in title_threads.get(cid, set()) and m not in mem]
        all_m = mem + ctx
        by_period = Counter(m.period for m in mem)
        threads_by_period = {p: len({m.thread_key for m in all_m if m.period == p}) for p in ("actual", "historical")}
        seg_threads = {s: len({m.thread_key for m in all_m if m.segment == s}) for s in ("professional", "consumer", "unclear")}
        seg_msgs = Counter(m.segment for m in mem)
        seg_src_threads = {f"{s}|{src}": n for (s, src), n in Counter(
            (s, k.split(":")[0]) for s in ("professional", "consumer") for k in {m.thread_key for m in all_m if m.segment == s}).items()}
        sources = Counter(k.split(":")[0] for k in thread_keys)
        dates = sorted(m.published_at[:10] for m in all_m if m.published_at)
        export_k = Counter(k for m in all_m for k in m.export.get("cluster_ids") or [])

        def ex_rank(m: Msg) -> tuple:
            return (m.period != "actual", not need_by_record.get(m.record_id), m not in mem, -len(m.text))
        examples, seen_threads = [], set()
        for m in sorted(all_m, key=ex_rank):
            if m.thread_key in seen_threads:
                continue
            seen_threads.add(m.thread_key)
            nd = need_by_record.get(m.record_id)
            examples.append({
                "message_url": m.url, "thread_url": turl[m.thread_key], "thread_title": ttitle[m.thread_key],
                "date": m.published_at[:10], "period": m.period, "segment": m.segment, "source": m.source_id,
                "paraphrase_ru": nd[0]["need_ru"] if nd else None,
                "paraphrase_basis": "редакционный пересказ подготовителя выгрузки (needs.jsonl)" if nd else None,
            })
            if len(examples) == 5:
                break
        out.append({
            "id": cid,
            "name": defs[cid]["name"],
            "concepts": defs[cid]["concepts"],
            "observations": {
                "threads": len(thread_keys),
                "threads_by_period": threads_by_period,
                "threads_by_segment": seg_threads,
                "threads_by_segment_source": seg_src_threads,
                "threads_by_segment_period": {f"{s}|{p}": len({m.thread_key for m in all_m if m.segment == s and m.period == p})
                                              for s in ("professional", "consumer", "unclear") for p in ("actual", "historical")},
                "messages_direct": len(mem),
                "messages_direct_by_period": {p: by_period.get(p, 0) for p in ("actual", "historical")},
                "messages_direct_by_segment": {s: seg_msgs.get(s, 0) for s in ("professional", "consumer", "unclear")},
                "messages_thread_context": len(ctx),
                "sources_count": len(sources),
                "sources": dict(sources.most_common()),
                "period": {"first": dates[0] if dates else None, "last": dates[-1] if dates else None},
                "curated_needs": sum(1 for m in all_m if need_by_record.get(m.record_id)),
                "export_cluster_crosswalk": dict(export_k.most_common()),
                "examples": examples,
            },
            "hypotheses": {
                "publication_topics": defs[cid].get("publication_topics", []),
                "research_question": defs[cid].get("research_question"),
            },
            "confidence": _confidence(len(thread_keys), len(sources), threads_by_period["actual"]),
        })
    return out


def rank(clusters: list[dict], seg: str, limit: int = 10) -> list[dict]:
    """Частые в выборке темы для сегмента: по числу тем, затем сообщений. Это не «горячие тренды».
    Свежие темы и уверенность считаются внутри сегмента."""
    rows = []
    for c in clusters:
        o = c["observations"]
        n_threads = o["threads_by_segment"][seg]
        n_msgs = o["messages_direct_by_segment"][seg]
        if n_threads == 0 and n_msgs == 0:
            continue
        by_src = {k.split("|")[1]: v for k, v in o["threads_by_segment_source"].items() if k.startswith(seg + "|")}
        actual = o["threads_by_segment_period"][f"{seg}|actual"]
        rows.append({"id": c["id"], "name": c["name"], "threads": n_threads, "messages": n_msgs, "threads_by_source": by_src,
                     "threads_actual": actual, "confidence": _confidence(n_threads, len(by_src), actual)})
    rows.sort(key=lambda r: (-r["threads"], -r["messages"], r["id"]))
    return rows[:limit]
