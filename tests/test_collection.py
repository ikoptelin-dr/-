"""Сбор: URL-ключи, хранилище без дублей, контрольные точки, HTTP-повторы, живые адаптеры на подменённом транспорте.
Все тестовые ответы площадок ниже — синтетические фикстуры, не собранные данные."""
import json

import pytest

from proba.demand.adapters.base import BaseAdapter, Page
from proba.demand.adapters.live import (RedditAdapter, StackExchangeAdapter, XRecentSearchAdapter, safe_xml)
from proba.demand.collect import collect
from proba.demand.http import HttpClient, Response, SourceBlocked, SourceError
from proba.demand.models import Discussion
from proba.demand.store import Store
from proba.demand.urls import external_id


def disc(i, src="s", **kw):
    return Discussion(source_id=src, external_id=f"e{i}", url=f"https://ex.org/{i}", collected_at="2026-11-02",
                      discovery={"adapter": "test", "q": kw.pop("q", "q")}, is_synthetic=True, **kw)


# --- URL ---------------------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("https://www.woman.ru/beauty/face/thread-ispolzovanie-retinola-v-ukhode-za-kozhey-vash-opyt-id5743923/",
     "https://www.woman.ru/beauty/face/thread/5743923/"),
    ("https://www.woman.ru/beauty/plastic/thread-vsya-pravda-o-biorevitalizatsii-ili-kak-nas-obmanyvayut-id4119901/85/",
     "https://woman.ru/beauty/plastic/thread/4119901/85"),
    ("https://community.sephora.com/t5/Skincare-Aware/Rosacea-and-uneven-skin/m-p/5999648",
     "https://community.sephora.com/t5/Skincare-Aware/Rosacea-and-uneven-skin/m-p/6000305"),
    ("https://www.realself.com/question/tallinn-ee-long-wait-after-chemical-peel-microneedling1",
     "https://www.realself.com/question/tallinn-ee-long-wait-after-chemical-peel-microneedling"),
])
def test_same_thread_same_key(a, b):
    assert external_id(a) == external_id(b)


def test_different_threads_different_keys():
    assert external_id("https://www.woman.ru/beauty/face/thread/5003457/") != external_id("https://www.woman.ru/beauty/face/thread/4236226/")


# --- хранилище -----------------------------------------------------------------
def test_upsert_is_idempotent_and_keeps_provenance(tmp_path):
    st = Store(tmp_path / "d.sqlite")
    assert st.upsert(disc(1, q="first", title="T")) is True
    assert st.upsert(disc(1, q="second", reactions={"replies": 3})) is False
    assert st.count() == 1
    d = next(st.discussions())
    assert d.title == "T" and d.reactions == {"replies": 3}
    assert [h["q"] for h in st.discovery_hits("s", "e1")] == ["first", "second"]


# --- контрольные точки -----------------------------------------------------------
class FakeAdapter(BaseAdapter):
    name, source_id = "fake", "s"

    def __init__(self, pages, fail_on=None):
        super().__init__(env={})
        self.pages, self.fail_on, self.calls = pages, fail_on, []

    def fetch_page(self, query, cursor):
        idx = int(cursor or 0)
        self.calls.append(idx)
        if self.fail_on is not None and idx == self.fail_on:
            self.fail_on = None
            raise SourceError("обрыв")
        nxt = str(idx + 1) if idx + 1 < len(self.pages) else None
        return Page(self.pages[idx], nxt)


def test_resume_after_interruption_without_duplicates(tmp_path):
    st = Store(tmp_path / "d.sqlite")
    pages = [[disc(1), disc(2)], [disc(3)], [disc(4), disc(2)]]
    a = FakeAdapter(pages, fail_on=1)
    r1 = collect(st, a, ["q"], max_records=100)
    assert r1.status in ("partial", "error") and st.count() == 2
    r2 = collect(st, a, ["q"], max_records=100)          # продолжает со страницы 1, а не с начала
    assert a.calls == [0, 1, 1, 2]
    assert r2.new == 2 and r2.seen_again == 1 and st.count() == 4
    r3 = collect(st, a, ["q"], max_records=100)          # запрос исчерпан — повторный запуск ничего не делает
    assert r3.queries == {"q": "done_earlier"} and st.count() == 4


def test_max_records_limit(tmp_path):
    st = Store(tmp_path / "d.sqlite")
    r = collect(st, FakeAdapter([[disc(i) for i in range(10)]]), ["q"], max_records=3)
    assert r.new == 3 and st.count() == 3


def test_blocked_source_is_marked_not_retried(tmp_path):
    class Blocked(FakeAdapter):
        def fetch_page(self, query, cursor):
            self.calls.append(query)
            raise SourceBlocked("сеть закрыта")
    a = Blocked([])
    r = collect(Store(tmp_path / "d.sqlite"), a, ["q1", "q2"], max_records=10)
    assert r.status == "blocked" and a.calls == ["q1"]


# --- HTTP ------------------------------------------------------------------------
def scripted(*responses):
    calls = []

    def t(method, url, headers, body, timeout):
        calls.append(url)
        r = responses[len(calls) - 1]
        return r
    t.calls = calls
    return t


def test_http_retry_after_then_success():
    sleeps = []
    t = scripted(Response(429, {"retry-after": "7"}, b""), Response(200, {}, b'{"ok": 1}'))
    c = HttpClient(t, min_interval_s=0, sleep=sleeps.append)
    assert c.get_json("https://h/x") == {"ok": 1}
    assert 7.0 in sleeps


def test_http_403_is_blocked_and_5xx_exhausts():
    with pytest.raises(SourceBlocked):
        HttpClient(scripted(Response(403, {}, b"")), min_interval_s=0, sleep=lambda s: None).get_json("https://h/x")
    with pytest.raises(SourceError):
        HttpClient(scripted(*[Response(503, {}, b"")] * 4), min_interval_s=0, max_retries=3, sleep=lambda s: None).get_json("https://h/x")


def test_http_throttles_per_host():
    sleeps, clock = [], iter([0.0, 0.5, 0.5])  # первый запрос в t=0, второй через 0.5 с
    c = HttpClient(scripted(Response(200, {}, b"{}"), Response(200, {}, b"{}")), min_interval_s=2.0,
                   sleep=sleeps.append, clock=lambda: next(clock))
    c.get_json("https://h/a")
    c.get_json("https://h/b")
    assert sleeps and abs(sleeps[0] - 1.5) < 1e-9


# --- живые адаптеры (подменённый транспорт) ---------------------------------------
def test_stackexchange_parses_and_paginates():
    payload = {"items": [{"question_id": 1, "link": "https://medicalsciences.stackexchange.com/q/1", "title": "Acne &amp; diet?",
                          "body": "<p>synthetic</p>", "creation_date": 1700000000, "score": 2, "answer_count": 1,
                          "view_count": 10, "tags": ["dermatology"]}], "has_more": True}
    t = scripted(Response(200, {}, json.dumps(payload).encode()))
    page = StackExchangeAdapter(http=HttpClient(t, min_interval_s=0), env={}).fetch_page("acne", None)
    assert page.next_cursor == "2" and page.items[0].title == "Acne & diet?"
    assert page.items[0].external_id == "medicalsciences/q/1" and "CC BY-SA" in page.items[0].flags["license"]


def test_reddit_without_credentials_blocked_before_network():
    t = scripted()
    with pytest.raises(SourceBlocked):
        RedditAdapter(http=HttpClient(t, min_interval_s=0), env={}).fetch_page("SkincareAddiction|retinol", None)
    assert t.calls == []


@pytest.mark.parametrize("env", [
    {"X_BEARER_TOKEN": "t", "X_READ_PRICE_USD": "0.005", "X_READ_BUDGET_USD": "0"},
    {"X_BEARER_TOKEN": "t", "X_READ_PRICE_USD": "0", "X_READ_BUDGET_USD": "5"},
    {"X_BEARER_TOKEN": "t"},
])
def test_x_without_price_or_budget_blocked_before_network(env):
    t = scripted()
    with pytest.raises(SourceBlocked):
        XRecentSearchAdapter(http=HttpClient(t, min_interval_s=0), env=env).fetch_page("retinol", None)
    assert t.calls == []


def test_x_budget_caps_page_size_and_stops():
    body = json.dumps({"data": [{"id": str(i), "text": "synthetic"} for i in range(20)], "meta": {"next_token": "n"}}).encode()
    t = scripted(Response(200, {}, body))
    a = XRecentSearchAdapter(http=HttpClient(t, min_interval_s=0),
                             env={"X_BEARER_TOKEN": "t", "X_READ_PRICE_USD": "0.005", "X_READ_BUDGET_USD": "0.1"})
    a.fetch_page("retinol", None)
    assert "max_results=20" in t.calls[0] and abs(a.spent_usd - 0.1) < 1e-9
    with pytest.raises(SourceBlocked):
        a.fetch_page("retinol", "n")


def test_rss_rejects_entities():
    with pytest.raises(ValueError):
        safe_xml(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "a">]><rss/>')
    assert safe_xml(b"<rss><channel><item><title>t</title></item></channel></rss>").tag == "rss"
