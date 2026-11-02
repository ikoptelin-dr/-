"""Адаптеры живых API площадок.

СТАТУС: реализовано по описанию API, проверено только тестами с подменённым транспортом.
Против живых площадок НЕ запускалось: сетевая политика окружения закрывает хосты (2026-11-02).
Каждый адаптер сохраняет только необходимое: без профилей авторов, без контактов; автор — не сохраняется.
"""
from __future__ import annotations

import base64
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode

from ..http import SourceBlocked
from ..models import Discussion
from ..urls import external_id
from .base import BaseAdapter, Page


def _today() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


MAX_FEED_BYTES = 5_000_000


def safe_xml(body: bytes) -> ET.Element:
    """Внешняя лента — недоверенные данные: ограничиваем размер и отвергаем DOCTYPE/ENTITY
    (защита от XXE и «billion laughs» без дополнительной зависимости)."""
    if len(body) > MAX_FEED_BYTES:
        raise ValueError("лента больше допустимого размера")
    head = body[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in body.lower():
        raise ValueError("лента содержит DOCTYPE/ENTITY — отклонено")
    return ET.fromstring(body)


def _excerpt(text: str | None, limit: int = 500) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", html.unescape(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


class StackExchangeAdapter(BaseAdapter):
    """Stack Exchange API 2.3, /search/advanced. Ключ необязателен (без ключа квота меньше).
    Контент под CC BY-SA: сохраняем ссылку и краткое извлечение с атрибуцией площадки."""
    name = "stackexchange"
    source_id = "stackexchange_medsci"
    site = "medicalsciences"

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        page = int(cursor or 1)
        params = {"order": "desc", "sort": "activity", "q": query, "site": self.site,
                  "page": page, "pagesize": 50, "filter": "withbody"}
        if self.env.get("STACKEXCHANGE_KEY"):
            params["key"] = self.env["STACKEXCHANGE_KEY"]
        data = self.http.get_json("https://api.stackexchange.com/2.3/search/advanced?" + urlencode(params))
        if data.get("backoff"):
            self.http.sleep(float(data["backoff"]))  # требование API: выдержать backoff
        items = []
        for q in data.get("items", []):
            items.append(Discussion(
                source_id=self.source_id,
                external_id=f"{self.site}/q/{q['question_id']}",
                url=q["link"],
                collected_at=_today(),
                discovery={"adapter": self.name, "query": query, "page": page},
                title=html.unescape(q.get("title", "")),
                excerpt=_excerpt(q.get("body")),
                published_at=datetime.fromtimestamp(q["creation_date"], timezone.utc).isoformat() if q.get("creation_date") else None,
                reactions={"score": q.get("score"), "answers": q.get("answer_count"), "views": q.get("view_count")},
                flags={"tags": q.get("tags", []), "license": "CC BY-SA (атрибуция Stack Exchange)"},
            ))
        return Page(items, str(page + 1) if data.get("has_more") else None)


class RedditAdapter(BaseAdapter):
    """Reddit Data API (OAuth, client credentials). Требует зарегистрированное приложение и соблюдение условий
    Reddit. Запрос: <subreddit>|<текст поиска>. Зеркала Reddit не используются."""
    name = "reddit"
    source_id = "reddit"
    required_env = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT")
    _token: str | None = None

    def _auth(self) -> str:
        self.check_credentials()
        if self._token:
            return self._token
        basic = base64.b64encode(f"{self.env['REDDIT_CLIENT_ID']}:{self.env['REDDIT_CLIENT_SECRET']}".encode()).decode()
        resp = self.http.request("POST", "https://www.reddit.com/api/v1/access_token",
                                 {"Authorization": f"Basic {basic}", "User-Agent": self.env["REDDIT_USER_AGENT"],
                                  "Content-Type": "application/x-www-form-urlencoded"},
                                 b"grant_type=client_credentials")
        if resp.status != 200:
            raise SourceBlocked(f"reddit: получение токена не удалось ({resp.status})")
        self._token = resp.json()["access_token"]
        return self._token

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        sub, _, text = query.partition("|")
        token = self._auth()
        params = {"q": text, "restrict_sr": 1, "sort": "new", "limit": 100, "raw_json": 1}
        if cursor:
            params["after"] = cursor
        data = self.http.get_json(f"https://oauth.reddit.com/r/{sub}/search?" + urlencode(params),
                                  {"Authorization": f"Bearer {token}", "User-Agent": self.env["REDDIT_USER_AGENT"]})
        items = []
        for child in data.get("data", {}).get("children", []):
            p = child["data"]
            url = "https://www.reddit.com" + p["permalink"]
            items.append(Discussion(
                source_id=self.source_id, external_id=f"reddit/{p['id']}", url=url, collected_at=_today(),
                discovery={"adapter": self.name, "query": query},
                title=p.get("title"), excerpt=_excerpt(p.get("selftext")),
                published_at=datetime.fromtimestamp(p["created_utc"], timezone.utc).isoformat() if p.get("created_utc") else None,
                reactions={"score": p.get("score"), "comments": p.get("num_comments")},
                flags={"subreddit": p.get("subreddit"), "flair": p.get("link_flair_text")},
            ))
        return Page(items, data.get("data", {}).get("after"))


class BlueskyAdapter(BaseAdapter):
    """AT Protocol app.bsky.feed.searchPosts. Нужна ли авторизация на публичном AppView — не подтверждено."""
    name = "bluesky"
    source_id = "bluesky"

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        params = {"q": query, "limit": 100}
        if cursor:
            params["cursor"] = cursor
        data = self.http.get_json("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?" + urlencode(params))
        items = []
        for post in data.get("posts", []):
            rkey = post["uri"].rsplit("/", 1)[-1]
            handle = post.get("author", {}).get("handle", "")
            items.append(Discussion(
                source_id=self.source_id, external_id=post["uri"],
                url=f"https://bsky.app/profile/{handle}/post/{rkey}", collected_at=_today(),
                discovery={"adapter": self.name, "query": query},
                text=post.get("record", {}).get("text"),  # короткий публичный пост; автор отдельно не сохраняется
                published_at=post.get("record", {}).get("createdAt"),
                language=(post.get("record", {}).get("langs") or [None])[0],
                reactions={"likes": post.get("likeCount"), "replies": post.get("replyCount"), "reposts": post.get("repostCount")},
            ))
        return Page(items, data.get("cursor"))


class RssAdapter(BaseAdapter):
    """Публичная RSS/Atom-лента форума или раздела. Запрос = URL ленты. Пагинации нет."""
    name = "rss"

    def __init__(self, source_id: str, **kw):
        super().__init__(**kw)
        self.source_id = source_id

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        resp = self.http.request("GET", query, {"Accept": "application/rss+xml, application/atom+xml, application/xml"})
        root = safe_xml(resp.body)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = root.findall(".//item") or root.findall(".//a:entry", ns)
        items = []
        for e in entries:
            link = e.findtext("link") or (e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else "")
            title = e.findtext("title") or e.findtext("a:title", namespaces=ns)
            items.append(Discussion(
                source_id=self.source_id, external_id=external_id(link), url=link, collected_at=_today(),
                discovery={"adapter": self.name, "feed": query},
                title=title, excerpt=_excerpt(e.findtext("description") or e.findtext("a:summary", namespaces=ns)),
                published_at=e.findtext("pubDate") or e.findtext("a:updated", namespaces=ns),
            ))
        return Page(items, None)


class XRecentSearchAdapter(BaseAdapter):
    """X API v2 recent search. Чтение оплачивается по факту за каждую запись — поэтому обязателен бюджет:
    без X_READ_PRICE_USD (цена за пост из вашего кабинета) и положительного лимита вызов запрещён до сети."""
    name = "x_recent_search"
    source_id = "x"
    required_env = ("X_BEARER_TOKEN", "X_READ_PRICE_USD", "X_READ_BUDGET_USD")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.spent_usd = 0.0

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        self.check_credentials()
        price = float(self.env["X_READ_PRICE_USD"])
        budget = float(self.env["X_READ_BUDGET_USD"])
        if price <= 0 or budget <= 0:
            raise SourceBlocked("x: цена или бюджет не положительные — чтение запрещено")
        max_results = 100
        if self.spent_usd + price * max_results > budget:
            max_results = int((budget - self.spent_usd) // price)
            if max_results < 10:  # минимальный размер страницы recent search
                raise SourceBlocked(f"x: бюджет исчерпан ({self.spent_usd:.3f} из {budget} USD)")
        params = {"query": query, "max_results": max_results,
                  "tweet.fields": "created_at,lang,public_metrics,conversation_id"}
        if cursor:
            params["next_token"] = cursor
        data = self.http.get_json("https://api.x.com/2/tweets/search/recent?" + urlencode(params),
                                  {"Authorization": f"Bearer {self.env['X_BEARER_TOKEN']}"})
        posts = data.get("data", [])
        self.spent_usd += price * len(posts)
        items = [Discussion(
            source_id=self.source_id, external_id=f"x/{p['id']}", url=f"https://x.com/i/web/status/{p['id']}",
            collected_at=_today(), discovery={"adapter": self.name, "query": query},
            text=p.get("text"), published_at=p.get("created_at"), language=p.get("lang"),
            reactions=p.get("public_metrics", {}), flags={"conversation_id": p.get("conversation_id")},
        ) for p in posts]
        return Page(items, data.get("meta", {}).get("next_token"))


class ThreadsKeywordSearchAdapter(BaseAdapter):
    """Threads API keyword search. Чужие публичные посты возвращаются только при разрешении
    threads_keyword_search (проверка приложения Meta); без него — только собственные посты."""
    name = "threads_keyword_search"
    source_id = "threads"
    required_env = ("THREADS_ACCESS_TOKEN",)

    def fetch_page(self, query: str, cursor: str | None) -> Page:
        self.check_credentials()
        params = {"q": query, "search_type": "RECENT", "fields": "id,text,timestamp,permalink",
                  "access_token": self.env["THREADS_ACCESS_TOKEN"]}
        if cursor:
            params["after"] = cursor
        data = self.http.get_json("https://graph.threads.net/v1.0/keyword_search?" + urlencode(params))
        items = [Discussion(
            source_id=self.source_id, external_id=f"threads/{p['id']}", url=p.get("permalink", ""),
            collected_at=_today(), discovery={"adapter": self.name, "query": query},
            text=p.get("text"), published_at=p.get("timestamp"),
        ) for p in data.get("data", [])]
        return Page(items, data.get("paging", {}).get("cursors", {}).get("after"))
