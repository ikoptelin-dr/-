"""Канонизация URL и устойчивые внешние идентификаторы обсуждений."""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse


def host_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def external_id(url: str) -> str:
    """Ключ одной и той же ветки независимо от страницы пагинации, параметров и формы URL."""
    p = urlparse(url)
    host = host_of(url)
    path = unquote(p.path).rstrip("/")
    if host == "woman.ru":
        m = re.search(r"(?:thread/|-id)(\d+)", path)
        if m:
            return f"woman.ru/thread/{m.group(1)}"
    if host == "community.sephora.com":
        # /t5/<board>/<thread-slug>/m-p/<msg> — ответы «Re:» относятся к той же ветке
        m = re.match(r"/t5/[^/]+/([^/]+)/m-p/\d+", path)
        if m:
            return f"community.sephora.com/{m.group(1).lower()}"
    if host == "acne.org":
        m = re.search(r"/forums/(?:topic/|\d+-[^/]+/)(\d+)-", path)
        if m:
            return f"acne.org/topic/{m.group(1)}"
        path = re.sub(r"/paged/\d+$", "", path)
    if host == "realself.com" and path.startswith("/question/"):
        # одинаковые вопросы иногда отличаются только цифрой на конце слага
        return "realself.com" + re.sub(r"\d+$", "", path)
    if host in ("gopicky.com",):
        m = re.search(r"/discussion/(\d+)", path)
        if m:
            return f"gopicky.com/discussion/{m.group(1)}"
    if host == "kosmetista.ru":
        m = re.search(r"/(\d+)(?:-[^/]*)?\.html$", path)
        if m:
            return f"kosmetista.ru/blog/{m.group(1)}"
    path = re.sub(r"/(amp|highlight/true)$", "", path)
    return host + path


def slug_text(url: str) -> str:
    """Текст из последнего осмысленного сегмента URL — запасной заголовок, помечается title_from_url."""
    parts = [s for s in unquote(urlparse(url).path).split("/") if s]
    for seg in reversed(parts):
        seg = re.sub(r"\.(html?|php)$", "", seg)
        if re.fullmatch(r"[\d_-]*|m-p|paged|amp|highlight|true", seg):
            continue
        seg = re.sub(r"-id\d+$|^\d+-|^review_|_\d+$", "", seg)
        text = re.sub(r"[-_]+", " ", seg).strip()
        if len(text) >= 6 and not text.replace(" ", "").isdigit():
            return text
    return ""
