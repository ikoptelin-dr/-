"""Сбор Telegram-каналов по R02. СТАТУС: реализовано без проверки на живом API.

Нужны TG_API_ID и TG_API_HASH (my.telegram.org) в окружении и pip install telethon.
При первом запуске Telethon спросит телефон и код. Файл сессии лежит в dlya-mam/_raw/ (в .gitignore).

    python3 dlya-mam/scripts/publics/tg_collect.py search
    python3 dlya-mam/scripts/publics/tg_collect.py posts --usernames dlya-mam/_raw/tg_included.txt

Читает только посты каналов (broadcast). Группы-чаты (megagroup) — только название и число
участников: сообщения в них пишут люди, это персональные данные (R02, раздел 7).
"""
import argparse
import asyncio
import csv
import datetime as dt
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from keywords import FEDERAL, LOCAL  # noqa: E402

RAW = pathlib.Path(__file__).resolve().parents[2] / "_raw"
DAYS = 90
MAX_POSTS = 300


def client():
    from telethon import TelegramClient
    api_id, api_hash = os.environ.get("TG_API_ID"), os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        sys.exit("Нет TG_API_ID / TG_API_HASH в окружении")
    RAW.mkdir(exist_ok=True)
    c = TelegramClient(str(RAW / "tg"), int(api_id), api_hash)
    c.flood_sleep_threshold = 120  # короткие FloodWait Telethon переждёт сам
    return c


async def search():
    from telethon import functions
    from telethon.tl.types import Channel
    rows = {}
    async with client() as c:
        for sample, kws in (("А", LOCAL), ("Б", FEDERAL)):
            for kw in kws:
                res = await c(functions.contacts.SearchRequest(q=kw, limit=100))
                for ch in res.chats:
                    if not isinstance(ch, Channel) or not ch.username:
                        continue
                    rec = rows.get(ch.id)
                    if rec is None:
                        full = await c(functions.channels.GetFullChannelRequest(ch))
                        rec = rows[ch.id] = {
                            "platform": "tg", "id": ch.id, "username": ch.username,
                            "url": f"https://t.me/{ch.username}", "name": ch.title,
                            "kind": "channel" if ch.broadcast else "chat",
                            "members": full.full_chat.participants_count or "",
                            "description": (full.full_chat.about or "")[:300].replace("\n", " "),
                            "sample_hint": set(), "found_by": set(),
                        }
                        await asyncio.sleep(1)
                    rec["sample_hint"].add(sample)
                    rec["found_by"].add(kw)
                await asyncio.sleep(2)
    out = RAW / "tg_found.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        fields = ["platform", "id", "username", "url", "name", "kind", "members", "description", "sample_hint", "found_by"]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: -(r["members"] or 0)):
            r = dict(r, sample_hint="/".join(sorted(r["sample_hint"])), found_by="; ".join(sorted(r["found_by"])))
            w.writerow(r)
    print(f"найдено {len(rows)} каналов и чатов → {out}")


def is_ad(text):
    t = (text or "").lower()
    return int("erid" in t or t.startswith("реклама") or "#реклама" in t)


async def posts(usernames_file):
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)
    names = [l.strip().lstrip("@") for l in open(usernames_file, encoding="utf-8") if l.strip() and not l.startswith("#")]
    out = RAW / "tg_posts.csv"
    fields = ["platform", "community_id", "post_id", "date", "text", "views", "likes", "comments_count",
              "reposts", "is_ad", "has_video", "has_photo", "is_repost", "is_pinned"]
    n = 0
    async with client() as c:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for u in names:
                ent = await c.get_entity(u)
                if getattr(ent, "megagroup", False) or not getattr(ent, "broadcast", False):
                    print(f"пропускаю {u}: это чат, а не канал")
                    continue
                async for m in c.iter_messages(ent, limit=MAX_POSTS):
                    if m.date < since:
                        break
                    if m.action:  # служебные сообщения
                        continue
                    reactions = sum(r.count for r in m.reactions.results) if m.reactions else 0
                    w.writerow({
                        "platform": "tg", "community_id": u, "post_id": m.id, "date": m.date.strftime("%Y-%m-%d"),
                        "text": (m.message or "")[:1000], "views": m.views or "", "likes": reactions,
                        "comments_count": m.replies.replies if m.replies else 0, "reposts": m.forwards or 0,
                        "is_ad": is_ad(m.message), "has_video": int(m.video is not None),
                        "has_photo": int(m.photo is not None), "is_repost": int(m.fwd_from is not None),
                        "is_pinned": int(bool(m.pinned)),
                    })
                    n += 1
                await asyncio.sleep(2)
    print(f"постов: {n} → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "posts"])
    ap.add_argument("--usernames", help="файл с username каналов, по одному в строке (после ручного фильтра)")
    a = ap.parse_args()
    if a.cmd == "search":
        asyncio.run(search())
    else:
        if not a.usernames:
            sys.exit("нужен --usernames")
        asyncio.run(posts(a.usernames))
