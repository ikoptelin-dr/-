"""Импорт выгрузки форумов, очистка, периоды, сегменты, кластеры, отчёт.
Все сообщения ниже — СИНТЕТИЧЕСКИЕ фикстуры, не собранные данные."""
import json
import re
from pathlib import Path

import pytest
import yaml

from proba.demand import forum_analysis as fa
from proba.demand.adapters.forum_export import ExportFormatError, load_export, scrub
from proba.demand.forum_report import run

ROOT = Path(__file__).resolve().parents[1]
LEX = yaml.safe_load((ROOT / "config/demand_lexicon.yaml").read_text(encoding="utf-8"))
JTBD = yaml.safe_load((ROOT / "config/jtbd_ru_2026-11.yaml").read_text(encoding="utf-8"))


def thread(src, tid, title, created="2015-01-01T00:00:00Z"):
    return {"source_id": src, "thread_id": tid, "canonical_url": f"https://forum.example/{src}/t{tid}",
            "title_original": title, "published_at": created, "language_original": "ru", "audience": "professional",
            "completeness_status": "count_matched", "author_name": "НЕ ДОЛЖНО ПОПАСТЬ"}


def msg(src, tid, mid, text, date="2015-02-01T00:00:00Z", role="discussion", **kw):
    d = {"source_id": src, "thread_id": tid, "thread_key": f"{src}:{tid}", "message_id": mid, "record_id": f"{src}:{mid}",
         "message_url": f"https://forum.example/{src}/t{tid}#c{mid}", "published_at": date, "text_original": text,
         "language_original": "ru", "content_role": role, "cluster_ids": [], "audience": "unknown",
         "audience_basis": "not_individually_inferred", "author": "nick123", "profile_url": "https://forum.example/u/1"}
    d.update(kw)
    return d


def write(tmp: Path, threads, messages, needs=()):
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "threads.jsonl").write_text("\n".join(json.dumps(t, ensure_ascii=False) for t in threads), encoding="utf-8")
    (tmp / "messages_all.jsonl").write_text("\n".join(json.dumps(m, ensure_ascii=False) for m in messages), encoding="utf-8")
    (tmp / "needs.jsonl").write_text("\n".join(json.dumps(n, ensure_ascii=False) for n in needs), encoding="utf-8")
    return tmp


PF = "ru_pf_k"
IT = "it_alfemminile"


@pytest.fixture
def corpus(tmp_path):
    threads = [thread(PF, "1", "Чистка лица на линии X"), thread(PF, "2", "Где купить проф. косметику"),
               thread(IT, "9", "Acne e pillola", "2024-02-01T00:00:00Z")]
    long_q = "Коллеги, подскажите последовательность этапов атравматической чистки, у моих клиентов комедоны плохо выходят после маски?"
    messages = [
        msg(PF, "1", "10", long_q),
        msg(PF, "1", "11", long_q, date="2016-01-01T00:00:00Z"),                       # точный повтор, позже
        msg(PF, "1", "12", "", text_status="empty_after_quote_and_media_removal"),
        msg(PF, "1", "13", "Купить лосьон оригинал любое количество, прямые поставки, звоните"),
        msg(PF, "1", "14", "Прикольно"),
        msg(PF, "1", "15", "Отвечаем как представитель марки: маска подходит", role="brand_answer"),
        msg(PF, "1", "16", "Всем привет, погода сегодня отличная", role="off_topic"),
        msg(PF, "2", "20", "Где закупка у официального поставщика? В работу нужна цена набора, пишите mail@example.com или +7 912 345 67 89",
            date="2025-07-13T00:00:00Z"),
        msg(PF, "2", "21", "Мой косметолог посоветовал этот крем, у меня кожа сухая, где его купить?", date="2017-03-01T00:00:00Z"),
        msg(PF, "2", "22", "Магазин в центре, доставка быстрая, всё нормально было у меня?", date="2018-03-01T00:00:00Z"),
        msg(IT, "9", "90", "Soffro di acne da anni, la pillola non aiuta, cosa fare?", date="2024-02-28T00:00:00Z"),
    ]
    needs = [{"need_id": "N1", "record_id": f"{PF}:10", "need_ru": "Как выстроить этапы чистки?", "is_counterexample": False}]
    return write(tmp_path / "forums_test", threads, messages, needs)


def analysed(d):
    threads, rep = load_export(d)
    ms = fa.build_messages(threads)
    cl = fa.clean(ms)
    fa.segment(ms, LEX, {IT: "consumer"})
    fa.tag_concepts(ms, LEX)
    return threads, rep, ms, cl


# --- адаптер ----------------------------------------------------------------------
def test_import_keeps_links_and_drops_personal_fields(corpus):
    threads, rep, _, _ = analysed(corpus)
    assert rep["threads"] == 3 and rep["messages"] == 11
    assert {"author", "author_name", "profile_url"} <= set(rep["dropped_pii_like_fields"])
    dump = json.dumps([t.to_dict() for t in threads], ensure_ascii=False)
    assert "nick123" not in dump and "НЕ ДОЛЖНО ПОПАСТЬ" not in dump and "/u/1" not in dump
    t2 = next(t for t in threads if t.external_id == "2")
    c = next(x for x in t2.comments if x["message_id"] == "20")
    assert c["thread_key"] == f"{PF}:2" and c["message_url"].endswith("#c20") and t2.url.endswith("/t2")
    assert "mail@example.com" not in c["text"] and "912" not in c["text"]
    assert t2.is_synthetic is False  # флаг про данные адаптера; сами фикстуры теста синтетические


def test_scrub():
    assert scrub("пишите a.b@c.ru или +7 (912) 345-67-89, @user_name") == "пишите [EMAIL] или [PHONE], [MENTION]"


def test_orphan_message_rejected(tmp_path):
    d = write(tmp_path / "x", [thread(PF, "1", "t")], [msg(PF, "404", "1", "текст")])
    with pytest.raises(ExportFormatError, match="без темы"):
        load_export(d)


def test_duplicate_thread_rejected(tmp_path):
    d = write(tmp_path / "x", [thread(PF, "1", "t"), thread(PF, "1", "t")], [])
    with pytest.raises(ExportFormatError, match="повтор темы"):
        load_export(d)


def test_missing_file_rejected(tmp_path):
    with pytest.raises(ExportFormatError):
        load_export(tmp_path)


# --- очистка ------------------------------------------------------------------------
def test_cleaning_statuses(corpus):
    _, _, ms, cl = analysed(corpus)
    st = {m.record_id.split(":")[1]: m.status for m in ms}
    assert st["10"] == "ok"
    assert st["11"] == "duplicate" and next(m for m in ms if m.record_id.endswith(":11")).duplicate_of == f"{PF}:10"
    assert st["12"] == "empty"
    assert st["13"] == "ad_or_spam_own"
    assert st["14"] == "short_context"
    assert st["15"] == "brand_answer"
    assert st["16"] == "off_topic_export"
    assert sum(cl["statuses"].values()) == 11


def test_contacts_alone_are_not_ad(corpus):
    _, _, ms, _ = analysed(corpus)
    assert next(m for m in ms if m.record_id.endswith(":20")).status == "ok"


def test_near_duplicate_across_threads(tmp_path):
    base = "подскажите пожалуйста какой крем выбрать для чувствительной кожи после пилинга чтобы не было покраснения и шелушения"
    d = write(tmp_path / "x", [thread(PF, "1", "a"), thread(PF, "2", "b")],
              [msg(PF, "1", "1", base), msg(PF, "2", "2", base + " спасибо", date="2016-01-01T00:00:00Z")])
    _, _, ms, _ = analysed(d)
    assert ms[1].status == "duplicate"


# --- период и сегмент ---------------------------------------------------------------
@pytest.mark.parametrize("date,period", [("2023-12-31T23:59:59Z", "historical"), ("2024-01-01T00:00:00Z", "actual"),
                                         ("2026-10-29T00:00:00Z", "actual"), ("2009-01-01T00:00:00Z", "historical"), ("", "unknown")])
def test_period(date, period):
    m = fa.Msg("r", "t", PF, "u", date, "ru", "x", {}, "")
    assert m.period == period


def test_segments(corpus):
    _, _, ms, _ = analysed(corpus)
    seg = {m.record_id.split(":")[1]: (m.segment, m.segment_basis) for m in ms}
    assert seg["10"] == ("professional", "text_cues")
    assert seg["21"] == ("consumer", "text_cues")
    assert seg["22"][0] == "unclear"          # профессиональный форум без признаков — не угадываем
    assert seg["90"] == ("consumer", "consumer_only_source")


# --- кластеры -------------------------------------------------------------------------
def test_clusters_split_periods_and_segments(corpus):
    threads, _, ms, _ = analysed(corpus)
    cl = {c["id"]: c for c in fa.build_clusters(threads, ms, LEX, [])}
    o = cl["C15"]["observations"]          # поставщики
    assert o["messages_direct_by_period"]["actual"] >= 1 and o["messages_direct_by_period"]["historical"] >= 1
    assert o["threads_by_segment"]["professional"] >= 1
    o8 = cl["C08"]["observations"]          # акне: итальянский потребитель (2024) + «комедоны» специалиста PF-K (2015)
    assert o8["sources"] == {IT: 1, PF: 1}
    assert o8["threads_by_segment_period"]["consumer|actual"] == 1 and o8["threads_by_segment_period"]["professional|actual"] == 0
    assert cl["C08"]["confidence"] == "низкая"
    # исключённые сообщения не считаются
    all_examples = [e["message_url"] for c in cl.values() for e in c["observations"]["examples"]]
    assert not any(u.endswith(("#c11", "#c13", "#c15", "#c16")) for u in all_examples)


def test_rank_is_per_segment(corpus):
    threads, _, ms, _ = analysed(corpus)
    cl = fa.build_clusters(threads, ms, LEX, [])
    prof = fa.rank(cl, "professional")
    assert all(r["threads_by_source"].get(IT, 0) == 0 for r in prof)
    assert all(r["confidence"] in ("низкая", "средняя") for r in prof + fa.rank(cl, "consumer"))


# --- отчёт ----------------------------------------------------------------------------
def test_report_has_no_message_text(corpus, tmp_path):
    out = tmp_path / "report"
    rr = run(corpus, out, ROOT / "config/demand_lexicon.yaml", ROOT / "config/jtbd_ru_2026-11.yaml")
    assert rr["external_calls"] == 0
    for name in ("README.md", "clusters.json", "run_report.json", "input_manifest.json"):
        body = (out / name).read_text(encoding="utf-8")
        assert "комедоны плохо выходят" not in body and "Soffro di acne" not in body and "nick123" not in body
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "Как выстроить этапы чистки?" in readme          # пересказ вместо текста
    assert "гипотеза" in readme and "заблокировано" in readme


# --- конфигурация ---------------------------------------------------------------------
def test_lexicon_consistent():
    for pats in list(LEX["concepts"].values()) + list(LEX["intents"].values()):
        for p in pats:
            re.compile(p)
    ids = [c["id"] for c in LEX["clusters"]]
    assert len(ids) == len(set(ids)) and set(LEX["primary_order"]) == set(ids)
    for c in LEX["clusters"]:
        assert set(c["concepts"]) <= set(LEX["concepts"]), c["id"]


def test_jtbd_refers_to_known_clusters_and_format():
    ids = {c["id"] for c in LEX["clusters"]}
    assert set(JTBD["clusters"]) <= ids
    for cid, sides in JTBD["clusters"].items():
        for side in ("consumer", "specialist"):
            s = sides.get(side)
            if s:
                assert s["jtbd"].startswith("Когда ") and ", я хочу " in s["jtbd"] and ", чтобы " in s["jtbd"], cid
                assert s["action"]["format"] in ("пост", "статья на сайт", "вебинар Proba Pro", "гайд")
    assert "гипотеза" in JTBD["status"]


def test_raw_forum_data_ignored_by_git():
    assert "data/raw/forums_*/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


# --- реальная выгрузка (только если лежит локально; в git её нет) ------------------------
REAL = ROOT / "data/raw/forums_ru_2026-11"


@pytest.mark.skipif(not (REAL / "messages_all.jsonl").exists(), reason="сырые данные не в репозитории")
def test_real_export_matches_manifest():
    import hashlib
    meta = ROOT / "data/meta/forums_ru_2026-11"
    summary = json.loads((meta / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((meta / "MANIFEST.sha256.json").read_text(encoding="utf-8"))
    threads, rep = load_export(REAL)
    assert rep["threads"] == summary["threads"] and rep["messages"] == summary["messages_total"]
    assert rep["dropped_pii_like_fields"] == []
    files = manifest.get("files", manifest)
    items = files.items() if isinstance(files, dict) else ((f.get("path"), f.get("sha256")) for f in files)
    checked = 0
    for path, sha in items:
        p = REAL / Path(str(path)).name
        if isinstance(sha, str) and p.suffix == ".jsonl" and p.exists():
            assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, p.name
            checked += 1
    assert checked >= 3


def test_two_datasets_merge_and_reject_overlap(corpus, tmp_path):
    other = write(tmp_path / "fresh", [thread("pikabu", "77", "Розацеа: что помогает?", "2026-01-01T00:00:00+03:00")],
                  [msg("pikabu", "77", "story:1", "Годами краснеет лицо и жжёт, что провоцирует обострение?", date="2026-01-01T00:00:00+03:00")])
    rr = run([corpus, other], tmp_path / "out", ROOT / "config/demand_lexicon.yaml", ROOT / "config/jtbd_ru_2026-11.yaml")
    assert rr["import"]["threads"] == 4 and rr["datasets"] == ["forums_test", "fresh"]
    with pytest.raises(ValueError, match="нескольких выгрузках"):
        run([corpus, corpus], tmp_path / "out2", ROOT / "config/demand_lexicon.yaml", ROOT / "config/jtbd_ru_2026-11.yaml")


def test_brand_blog_voice_is_ad():
    m = fa.Msg("pikabu:1", "pikabu:t", "pikabu", "u", "2026-01-01", "ru",
               "Мы в Компании регулярно сталкиваемся с вопросом, в каком порядке наносить средства", {}, "")
    fa.clean([m])
    assert m.status == "ad_or_spam_own"


def test_price_concept_ignores_scars_and_dear():
    low = "дорогая, у меня рубцы после акне"
    assert not any(re.search(p, low) for p in LEX["concepts"]["price_value"])
    assert any(re.search(p, "процедура стоит 5000 руб") for p in LEX["concepts"]["price_value"])


# --- Вордстат: списки масок ---------------------------------------------------------------
def test_wordstat_masks_valid_and_rendered(tmp_path):
    from proba.demand.wordstat import exact_form, intent, load, write
    data = load(ROOT / "config/wordstat_masks_wave1.yaml", LEX)
    counts = write(data, tmp_path / "ws")
    assert counts["all"] >= 300 and 15 <= counts["A"] <= 25
    assert exact_form("осложнения в косметологии") == '"!осложнения +в !косметологии"'
    assert intent("акнекутан") == "navigational" and intent("ботокс цена") == "commercial"
    assert intent("работа косметологом", "pro") == "noise_candidate"
    body = (tmp_path / "ws" / "README.md").read_text(encoding="utf-8")
    assert "Частот в этом файле нет" in body
    assert not re.search(r"\|\s*\d{2,}\s*\|", body)        # никаких выдуманных частот в таблицах
    assert len((tmp_path / "ws" / "masks_all.txt").read_text(encoding="utf-8").split("\n")) - 1 == counts["all"]


def test_wordstat_duplicate_mask_rejected(tmp_path):
    from proba.demand.wordstat import load
    p = tmp_path / "m.yaml"
    p.write_text('version: "x"\nminus_words_consumer: []\nminus_words_pro: []\ngroups:\n'
                 '  - {id: G1, cluster: C01, title: t, audience: consumer, masks: [{q: "ретинол"}, {q: "ретинол"}]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="повтор"):
        load(p, LEX)


# --- Вордстат: разбор выгрузки (СИНТЕТИЧЕСКИЕ строки) ------------------------------------
def test_wordstat_analysis_marks_noise_and_keeps_all(tmp_path):
    from proba.demand import wordstat_analysis as wa
    from proba.demand.wordstat import NAVIGATIONAL
    csv_path = tmp_path / "ws.csv"
    csv_path.write_text("Тема;Запрос;Частота\n"
                        "ботокс;ботокс;1000\nботокс;ботокс для волос;300\nботокс;что нельзя после ботокса;50\n"
                        "!косметолог;косметолог;900\n!косметолог;косметолог москва;200\n!косметолог;курсы косметолога;100\n"
                        "!косметолог;косметолог вакансии;40\nакне;почему прыщи;80\nакне;акнекутан;70\n", encoding="utf-8")
    masks = yaml.safe_load((ROOT / "config/wordstat_masks_wave1.yaml").read_text(encoding="utf-8"))
    a = wa.analyse(csv_path, masks, LEX, set(NAVIGATIONAL))
    P = a["phrases"]
    assert len(P) == 9                                            # ни одна фраза не удалена
    assert P["ботокс для волос"].relevance == "adjacent_hair"
    assert P["косметолог москва"].relevance == "local"
    assert P["косметолог вакансии"].relevance == "job"
    assert P["курсы косметолога"].relevance == "education" and P["курсы косметолога"].audience == "pro"
    assert P["почему прыщи"].intent == "question" and P["почему прыщи"].cluster == "C08"
    assert P["акнекутан"].intent == "navigational"
    heads = {m["mask"]: m["head_freq"] for m in a["masks"]}
    assert heads["косметолог"] == 900 and heads["ботокс"] == 1000   # !косметолог склеен с «косметолог»
    s = {x["cluster"]: x for x in wa.summarise(a, LEX)}
    assert s["C05"]["head_demand"] == 1000                        # спрос = head, частоты не суммируются


def test_wordstat_csv_header_checked(tmp_path):
    from proba.demand import wordstat_analysis as wa
    p = tmp_path / "bad.csv"
    p.write_text("a;b;c\nx;y;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Тема;Запрос;Частота"):
        wa.load_csv(p)


def test_jtbd_codebook_valid():
    jobs = yaml.safe_load((ROOT / "config/jtbd_jobs.yaml").read_text(encoding="utf-8"))["jobs"]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids))
    clusters = {c["id"] for c in LEX["clusters"]}
    modes = {"after", "treat", "decide", "routine", "check", "navigate", "pro_buy", "pro_do", "pro_safe", "pro_money", "pro_career"}
    for j in jobs:
        assert j["segment"] in ("consumer", "pro") and j["mode"] in modes and j["cluster"] in clusters, j["id"]
        assert j["job"].startswith("Когда ") and ", я хочу " in j["job"] and ", чтобы " in j["job"], j["id"]
        for p in j["patterns"]:
            re.compile(p)
