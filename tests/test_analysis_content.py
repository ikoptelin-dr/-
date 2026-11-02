"""Разметка, кластеры, очередь, лимиты, публикация, задания на статьи и сквозной проход на реальном наборе."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from proba.content.limits import x_weighted_length
from proba.content.publish import Outbox, PublishRefused
from proba.content.queue import load_drafts
from proba.demand.clean import detect_language, label, mark_near_duplicates, page_kind
from proba.demand.cluster import build_clusters
from proba.demand.http import Response
from proba.demand.models import Discussion
from proba.pipeline import ROOT, first_pass, load_config

SOURCES, LEX = load_config()
SRC = {s["id"]: s for s in SOURCES["sources"]}
CHANNELS = yaml.safe_load((ROOT / "config/channels.yaml").read_text(encoding="utf-8"))


def d(url, title, src="realself"):
    return Discussion(source_id=src, external_id=url, url=url, collected_at="2026-11-02", discovery={}, title=title, is_synthetic=True)


# --- разметка -----------------------------------------------------------------
@pytest.mark.parametrize("url,kind", [
    ("https://doctu.ru/spb/doctor/ivanov-ivan", "excluded_profile"),
    ("https://lr.us.psf.lt/r/SkincareAddiction/comments/x", "excluded_mirror"),
    ("https://www.docmorris.de/x/1", "shop_or_commercial"),
    ("https://www.realself.com/question/x", "question"),
    ("https://www.woman.ru/beauty/face/thread/1/", "discussion"),
    ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1/", "scientific"),
])
def test_page_kind(url, kind):
    assert page_kind(url) == kind


@pytest.mark.parametrize("text,lang", [("Ретинол. С чего начать?", "ru"), ("How long after lip fillers?", "en"),
                                       ("¿Cuáles son las mejores cremas para el melasma?", "es"), ("", "und")])
def test_language(text, lang):
    assert detect_language(text) == lang


def test_ads_profiles_and_dups_excluded_from_clusters():
    items = [label(x, LEX, SRC) for x in [
        d("https://www.realself.com/question/a", "Will laser make melasma worse?"),
        d("https://www.realself.com/question/b", "Will a laser make melasma worse?"),       # близкий повтор
        d("https://farmaciajimenez.com/x", "Heliocare melasma PACK Descuento", "web:farmaciajimenez.com"),
        d("https://doctu.ru/spb/doctor/x", "Пигментация, дерматолог", "doctu_ru"),
        d("https://www.woman.ru/beauty/face/thread/9/", "Крем от пигментации", "woman_ru"),
    ]]
    assert mark_near_duplicates(items) == 1
    clusters, excluded = build_clusters(items, LEX)
    c03 = next(c for c in clusters if c["id"] == "C03")
    assert c03["observations"]["unique_discussions_any"] == 2
    assert c03["observations"]["sources_count"] == 2 and set(c03["observations"]["languages"]) == {"en", "ru"}
    assert excluded["near_duplicate"] == 1 and excluded["kind:shop_or_commercial"] == 1 and excluded["kind:excluded_profile"] == 1


def test_primary_cluster_prefers_specific_ingredient():
    items = [label(d("https://www.acne.org/forums/4-x/1-y", "Red marks from initial breakout on tretinoin", "acne_org"), LEX, SRC)]
    clusters, _ = build_clusters(items, LEX)
    prim = {c["id"]: c["observations"]["unique_discussions_primary"] for c in clusters}
    assert prim["C01"] == 1 and prim.get("C08", 0) == 0


# --- лимиты и очередь ----------------------------------------------------------
def test_x_weighting():
    assert x_weighted_length("абв") == 3
    assert x_weighted_length("日本") == 4
    assert x_weighted_length("см. https://example.org/a/very/long/path?x=1") == 4 + 23


def _clusters():
    return [{"id": "C01", "observations": {"member_urls": ["https://ok/1"], "unique_discussions_any": 5, "sources_count": 2}}]


def _write(tmp_path, draft):
    p = tmp_path / "d.yaml"
    p.write_text(yaml.safe_dump({"drafts": [draft]}, allow_unicode=True), encoding="utf-8")
    return p


BASE = {"id": "X-T", "channel": "x", "format": "f", "cluster_id": "C01", "idea_type": "short_post",
        "status": "draft_no_medical_claims", "parts": ["Вопрос {C01.n}?"], "medical_claims": [], "basis_urls": ["https://ok/1"]}


def test_draft_resolves_numbers(tmp_path):
    drafts, errors = load_drafts(_write(tmp_path, BASE), _clusters(), CHANNELS)
    assert errors == [] and drafts[0]["parts"] == ["Вопрос 5?"] and drafts[0]["publishable"] is False


@pytest.mark.parametrize("change,needle", [
    ({"cluster_id": "C99"}, "кластер C99"),
    ({"basis_urls": ["https://not-in-cluster"]}, "не входит в кластер"),
    ({"medical_claims": ["эффективно"]}, "research_draft"),
    ({"status": "ready"}, "недопустимый статус"),
    ({"parts": ["я" * 281]}, "длиннее лимита"),
])
def test_draft_validation_negative(tmp_path, change, needle):
    _, errors = load_drafts(_write(tmp_path, {**BASE, **change}), _clusters(), CHANNELS)
    assert any(needle in e for e in errors)


# --- публикация ------------------------------------------------------------------
def draft(**kw):
    base = {"id": "T-1", "version": 1, "channel": "threads", "parts": ["a", "b"], "text_sha256": "h1",
            "length_checks": [{"fits": True}, {"fits": True}], "medical_claims": ["claim"], "is_synthetic": False}
    return {**base, **kw}


ENV = {"THREADS_USER_ID": "u", "THREADS_PUBLISH_TOKEN": "t"}
ENABLED = {**CHANNELS, "publishing_enabled": True,
           "channels": {**CHANNELS["channels"], "threads": {**CHANNELS["channels"]["threads"], "enabled": True}}}


def fake_threads():
    calls, n = [], [0]

    def t(method, url, headers, body, timeout):
        calls.append(url)
        n[0] += 1
        return Response(200, {}, json.dumps({"id": f"id{n[0]}"}).encode())
    t.calls = calls
    return t


def test_default_config_blocks_everything(tmp_path):
    ob = Outbox(tmp_path / "o.sqlite", CHANNELS, tmp_path)
    reasons = ob.blockers(draft(), {})
    assert any("выключена" in r for r in reasons) and any("medical_reviewer" in r for r in reasons)
    assert any("не подключён аккаунт" in r for r in reasons)


def test_publish_requires_both_approvals_and_is_idempotent(tmp_path):
    ob = Outbox(tmp_path / "o.sqlite", ENABLED, tmp_path)
    dr = draft()
    ob.enqueue(dr, "2026-01-01T00:00:00+00:00")
    ob.enqueue(dr, "2026-01-01T00:00:00+00:00")                      # повторная постановка — та же запись
    t = fake_threads()
    assert ob.publish_due({"T-1": dr}, ENV, t)[0]["status"] == "blocked"   # нет одобрений
    ob.approve(dr, "editor", "anna")
    assert ob.publish_due({"T-1": dr}, ENV, t)[0]["status"] == "blocked"   # нет медицинского рецензента
    with pytest.raises(PublishRefused):
        ob.approve(dr, "medical_reviewer", "anna")                       # один человек в двух ролях
    ob.approve(dr, "medical_reviewer", "dr_boris")
    res = ob.publish_due({"T-1": dr}, ENV, t)
    assert res[0]["status"] == "published" and len(t.calls) == 4 and "reply_to_id=id2" in t.calls[2]
    assert ob.publish_due({"T-1": dr}, ENV, t) == [] and len(t.calls) == 4   # повтор не публикует второй раз


def test_text_change_invalidates_approval(tmp_path):
    ob = Outbox(tmp_path / "o.sqlite", ENABLED, tmp_path)
    ob.approve(draft(), "editor", "anna")
    ob.approve(draft(), "medical_reviewer", "dr_boris")
    reasons = ob.blockers(draft(text_sha256="h2"), ENV)
    assert any("другому тексту" in r for r in reasons)


def test_timeout_goes_to_reconciliation_and_stop_file_blocks(tmp_path):
    ob = Outbox(tmp_path / "o.sqlite", ENABLED, tmp_path)
    dr = draft(medical_claims=[])
    ob.approve(dr, "editor", "anna")
    ob.enqueue(dr, "2026-01-01T00:00:00+00:00")

    def timeout(*a):
        raise TimeoutError("нет ответа")
    assert ob.publish_due({"T-1": dr}, ENV, timeout)[0]["status"] == "needs_reconciliation"
    assert ob.publish_due({"T-1": dr}, ENV, timeout) == []               # не повторяет вслепую
    (tmp_path / "var/queue").mkdir(parents=True)
    (tmp_path / "var/queue/STOP").write_text("stop")
    assert any("стоп-файлом" in r for r in ob.blockers(dr, ENV))


def test_synthetic_never_published(tmp_path):
    ob = Outbox(tmp_path / "o.sqlite", ENABLED, tmp_path)
    assert any("синтетический" in r for r in ob.blockers(draft(is_synthetic=True), ENV))


# --- сквозной проход на реальном наборе ---------------------------------------------
def test_first_pass_on_real_dataset(tmp_path):
    rep = first_pass(tmp_path / "out", tmp_path / "db.sqlite", ROOT / "data/raw/websearch_discovery_2026-11-02.json",
                     ROOT / "content/drafts/2026-11-02.yaml")
    assert rep["ingest"]["links_in_dataset"] == 241 and len(rep["ingest"]["blocked_searches"]) == 1
    assert rep["draft_errors"] == [] and rep["brief_errors"] == [] and rep["briefs"] == 3 and rep["drafts"] == 12
    assert rep["clusters"] >= 10
    again = first_pass(tmp_path / "out2", tmp_path / "db.sqlite", ROOT / "data/raw/websearch_discovery_2026-11-02.json", None)
    assert again["ingest"]["new_records"] == 0                          # повторный импорт без дублей
    disc = json.loads((tmp_path / "out/discussions.json").read_text(encoding="utf-8"))
    clusters = json.loads((tmp_path / "out/clusters.json").read_text(encoding="utf-8"))["clusters"]
    member = {u for c in clusters for u in c["observations"]["member_urls"]}
    profiles = {x["url"] for x in disc if x["kind"] == "excluded_profile"}
    assert profiles and not (profiles & member)                        # профили людей не попадают в кластеры
    briefs = json.loads((tmp_path / "out/research_briefs.json").read_text(encoding="utf-8"))
    for b in briefs:                                                   # цепочка обсуждение → кластер → задание
        assert b["demand_evidence"]["example_discussions"] and b["topic"]["is_synthetic"] is False


def test_starter_validator_still_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/validate.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
