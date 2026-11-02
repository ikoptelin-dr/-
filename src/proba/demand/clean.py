"""Очистка и разметка: тип страницы, язык, аудитория, реклама/спам, близкие повторы, намерения, понятия."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .models import Discussion
from .urls import host_of, slug_text

# --- тип страницы ------------------------------------------------------------
# Сигнал спроса дают только: discussion (ветка форума/пост участника), question (вопрос к экспертам), review (отзыв).
KIND_RULES: list[tuple[str, str]] = [
    (r"lr\.[a-z.]*psf\.lt|libreddit|redlib", "excluded_mirror"),
    (r"doctu\.ru/(spb|msk)/doctor/|lyko\.com/en/community/", "excluded_profile"),
    (r"lists\.galaxyproject\.org", "spam"),
    (r"gummysearch\.com|treendly\.com", "excluded_third_party_tool"),
    (r"ncbi\.nlm\.nih\.gov|clinicaltrials\.gov|medrxiv\.org|uspto\.gov|complifegroup\.com", "scientific"),
    (r"woman\.ru/beauty/.+thread|acne\.org/forums/|gopicky\.com/discussion/|community\.sephora\.com/t5/|pricescope\.com/community/|community\.realself\.com/forum|pikabu\.ru/story/", "discussion"),
    (r"kosmetista\.ru/blog/", "discussion"),
    (r"realself\.com/question/|doctu\.ru/consult/question/|health\.mail\.ru/consultation/|doctoralia\.[a-z.]+/pregunta", "question"),
    (r"otzovik\.com/review_|realself\.com/review/|acne\.org/reviews/|medpex\.de/.+/erfahrungen|influenster\.com/reviews/", "review"),
    (r"otzovik\.com/reviews/|realself\.com/reviews/|pikabu\.ru/tag/|doctu\.ru/consult/kosmetolog$|kosmetista\.ru/catalog/|acne\.org/treatment/", "listing"),
    (r"docmorris\.de|medpex\.de|douglas\.de|farmacia|prom\.ua|soin-et-nature\.com|gumroad\.com|marieveronique\.com|my-best\.com|buscape\.com|gopicky\.com/[a-z0-9]+/[a-z0-9]+$|jotform\.com", "shop_or_commercial"),
    (r"kedu\.ru/events|ucheba\.ru|companies\.rbc\.ru|gxpnews\.net|vidal\.ru|styleofeurasia|ascpskincare\.com|timesoftheislands", "news_event_edu"),
]
DEMAND_KINDS = {"discussion", "question", "review"}


def page_kind(url: str) -> str:
    target = url.lower()
    for pattern, kind in KIND_RULES:
        if re.search(pattern, target):
            return kind
    return "article_or_blog"


# --- язык --------------------------------------------------------------------
STOP = {
    "en": {"the", "and", "is", "my", "for", "after", "how", "what", "with", "to", "of", "it", "can", "will", "this", "i", "does", "in", "on", "skin", "why", "who", "long"},
    "es": {"de", "la", "el", "los", "las", "para", "con", "que", "en", "y", "cuáles", "opiniones", "preguntas"},
    "pt": {"para", "de", "do", "da", "opções", "mais", "melhor", "protetor"},
    "de": {"und", "der", "die", "das", "zu", "für", "mit", "erfahrungen", "pflege", "sammeln"},
    "fr": {"le", "les", "une", "des", "et", "qui", "trouvez", "votre"},
    "id": {"kenapa", "pakai", "malah", "untuk", "dan"},
}


def detect_language(text: str, fallback: str | None = None) -> str:
    """Простое определение по алфавиту и служебным словам. Для коротких заголовков без признаков
    возвращает язык площадки (fallback) или 'und'. Ограничение описано в отчёте."""
    if not text:
        return fallback or "und"
    if re.search(r"[іїєґ]", text, re.I):
        return "uk"
    if re.search(r"[а-яё]", text, re.I):
        return "ru"
    if re.search(r"[α-ω]", text, re.I):
        return "el"
    if re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text, re.I):
        return "vi"
    words = set(re.findall(r"[a-zà-ÿ]+", text.lower()))
    scores = {lang: len(words & sw) for lang, sw in STOP.items()}
    best = max(scores, key=scores.get)
    if scores[best] >= 1:
        return best
    return fallback or "und"


# --- нормализация и близкие повторы -------------------------------------------
def norm_tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFC", text.lower())
    return {t for t in re.findall(r"[\w]+", text) if len(t) > 2 and not t.isdigit()}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


@dataclass
class Labeled:
    d: Discussion
    kind: str
    text: str                  # текст для анализа: заголовок, извлечение или слаг URL
    title_from_url: bool
    language: str
    audience: str
    ad: bool
    intents: list[str]
    concepts: list[str]
    duplicate_of: str | None = None

    @property
    def key(self) -> str:
        return f"{self.d.source_id}:{self.d.external_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "source_id": self.d.source_id, "url": self.d.url, "title": self.d.title,
            "analysis_text": self.text, "title_from_url": self.title_from_url, "kind": self.kind,
            "language": self.language, "audience": self.audience, "possible_ad_or_spam": self.ad,
            "intents": self.intents, "concepts": self.concepts, "reactions": self.d.reactions,
            "published_at": self.d.published_at, "collected_at": self.d.collected_at,
            "discovery": self.d.discovery, "duplicate_of": self.duplicate_of, "is_synthetic": self.d.is_synthetic,
        }


def _match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def label(d: Discussion, lexicon: dict, sources: dict[str, dict]) -> Labeled:
    kind = page_kind(d.url)
    title_from_url = False
    text = d.title or d.excerpt or d.text or ""
    if not text:
        text = slug_text(d.url)
        title_from_url = bool(text)
    elif re.search(r"(\.\.\.|…)$", text):
        # заголовок в выдаче усечён — берём слаг URL, если он полнее (помечается)
        slug = slug_text(d.url)
        if len(slug) > len(text) - 3:
            text, title_from_url = slug, True
    low = text.lower()
    src = sources.get(d.source_id, {})
    fallback_lang = src.get("language") if src.get("language") not in (None, "multi") else None
    language = d.language or detect_language(text, fallback_lang if title_from_url or not text else fallback_lang)
    audience = src.get("audience", "unknown")
    if _match_any(lexicon["professional_cues"], low):
        audience = "professional" if audience == "consumer" else audience
    ad = kind in ("shop_or_commercial", "spam") or _match_any(lexicon["ad_cues"], low)
    intents = [name for name, pats in lexicon["intents"].items() if _match_any(pats, low)]
    concepts = [name for name, pats in lexicon["concepts"].items() if _match_any(pats, low)]
    return Labeled(d, kind, text, title_from_url, language, audience, ad, intents, concepts)


def mark_near_duplicates(items: list[Labeled], threshold: float = 0.8) -> int:
    """Помечает близкие повторы внутри одного источника (один вопрос под разными URL). Возвращает число повторов."""
    kept: list[Labeled] = []
    dups = 0
    for it in items:
        toks = norm_tokens(it.text)
        for k in kept:
            if k.d.source_id == it.d.source_id and jaccard(toks, norm_tokens(k.text)) >= threshold:
                it.duplicate_of = k.key
                dups += 1
                break
        else:
            kept.append(it)
    return dups
