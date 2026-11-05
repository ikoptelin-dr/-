"""Командная строка Proba Intelligence Engine.

  python -m proba first-pass            # импорт → очистка → кластеры → очередь → задания (без сети)
  python -m proba collect --adapter stackexchange --query "acne" --max 100   # живой сбор (нужен открытый хост)
  python -m proba queue-check           # почему черновики нельзя опубликовать
  python -m proba forum-report          # выгрузка форумов → очистка → сегменты → кластеры → отчёт (без сети)
  python -m proba wordstat-masks        # списки масок для ручного сбора в Вордстате + шаблон для частот
  python -m proba wordstat-report       # разбор выгрузки Вордстата: разметка фраз, спрос по кластерам, вопросы
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .pipeline import ROOT, first_pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="proba")
    sub = ap.add_subparsers(dest="cmd", required=True)
    fp = sub.add_parser("first-pass")
    fp.add_argument("--dataset", default=str(ROOT / "data/raw/websearch_discovery_2026-11-02.json"))
    fp.add_argument("--drafts", default=str(ROOT / "content/drafts/2026-11-02.yaml"))
    fp.add_argument("--out", default=str(ROOT / "reports/first_pass_2026-11-02"))
    fp.add_argument("--db", default=str(ROOT / "var/demand.sqlite"))
    co = sub.add_parser("collect")
    co.add_argument("--adapter", required=True, choices=["stackexchange", "reddit", "bluesky", "x", "threads"])
    co.add_argument("--query", action="append", required=True)
    co.add_argument("--max", type=int, default=100)
    co.add_argument("--db", default=str(ROOT / "var/demand.sqlite"))
    qc = sub.add_parser("queue-check")
    qc.add_argument("--queue", default=str(ROOT / "reports/first_pass_2026-11-02/queue/queue.json"))
    fr = sub.add_parser("forum-report")
    fr.add_argument("--data", action="append", help="папка выгрузки; можно несколько раз")
    fr.add_argument("--out", default=str(ROOT / "reports/ru_market_2026-11"))
    fr.add_argument("--lexicon", default=str(ROOT / "config/demand_lexicon.yaml"))
    fr.add_argument("--jtbd", default=str(ROOT / "config/jtbd_ru_2026-11.yaml"))
    wm = sub.add_parser("wordstat-masks")
    wm.add_argument("--masks", default=str(ROOT / "config/wordstat_masks_wave1.yaml"))
    wm.add_argument("--out", default=str(ROOT / "reports/wordstat_wave1"))
    wr = sub.add_parser("wordstat-report")
    wr.add_argument("--csv", default=str(ROOT / "data/raw/wordstat_2026-11/wordstat_wave1.csv"))
    wr.add_argument("--out", default=str(ROOT / "reports/wordstat_wave1/analysis"))
    wr.add_argument("--full", default=str(ROOT / "data/raw/wordstat_2026-11/clustered.csv"))
    args = ap.parse_args(argv)

    if args.cmd == "first-pass":
        report = first_pass(Path(args.out), Path(args.db), Path(args.dataset), Path(args.drafts))
        print(json.dumps({k: report[k] for k in ("ingest", "clusters", "ideas", "drafts", "draft_errors", "briefs", "brief_errors")}, ensure_ascii=False, indent=2))
        return 1 if report["draft_errors"] or report["brief_errors"] else 0
    if args.cmd == "collect":
        from .demand.adapters import live
        from .demand.collect import collect
        from .demand.store import Store
        cls = {"stackexchange": live.StackExchangeAdapter, "reddit": live.RedditAdapter, "bluesky": live.BlueskyAdapter,
               "x": live.XRecentSearchAdapter, "threads": live.ThreadsKeywordSearchAdapter}[args.adapter]
        res = collect(Store(args.db), cls(), args.query, args.max)
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return 0 if res.status in ("ok", "partial") else 2
    if args.cmd == "forum-report":
        from .demand.forum_report import run
        data = args.data or [str(ROOT / "data/raw/forums_ru_2026-11"), str(ROOT / "data/raw/forums_ru_fresh_2026-11")]
        rr = run([Path(d) for d in data], Path(args.out), Path(args.lexicon), Path(args.jtbd))
        print(json.dumps({k: rr[k] for k in ("import", "cleaning", "clusters")}, ensure_ascii=False, indent=2)[:2000])
        return 0
    if args.cmd == "wordstat-masks":
        import yaml
        from .demand.wordstat import load, write
        lex = yaml.safe_load((ROOT / "config/demand_lexicon.yaml").read_text(encoding="utf-8"))
        print(json.dumps(write(load(Path(args.masks), lex), Path(args.out)), ensure_ascii=False))
        return 0
    if args.cmd == "wordstat-report":
        import yaml
        from .demand import wordstat_analysis as wa
        from .demand.wordstat import NAVIGATIONAL
        lex = yaml.safe_load((ROOT / "config/demand_lexicon.yaml").read_text(encoding="utf-8"))
        masks = yaml.safe_load((ROOT / "config/wordstat_masks_wave1.yaml").read_text(encoding="utf-8"))
        a = wa.analyse(Path(args.csv), masks, lex, set(NAVIGATIONAL))
        summary = wa.summarise(a, lex)
        wa.write(a, summary, Path(args.out), Path(args.full))
        print(json.dumps({"rows": a["rows"], "phrases": len(a["phrases"]), "masks": len(a["masks"]), "missing": len(a["missing"])}, ensure_ascii=False))
        return 0
    if args.cmd == "queue-check":
        import yaml
        from .content.publish import Outbox
        cfg = yaml.safe_load((ROOT / "config/channels.yaml").read_text(encoding="utf-8"))
        q = json.loads(Path(args.queue).read_text(encoding="utf-8"))
        ob = Outbox(":memory:", cfg, ROOT)
        for d in q["drafts"]:
            print(d["id"], "→", "; ".join(ob.blockers(d, dict(os.environ))))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
