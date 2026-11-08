"""Сбор пабликов ВКонтакте по R02. СТАТУС: реализовано без проверки на живом API.

Нужен пользовательский токен ВК в переменной окружения VK_TOKEN
(groups.search с сервисным ключом не работает). Токен не коммитить.

    python3 dlya-mam/scripts/publics/vk_collect.py search
    python3 dlya-mam/scripts/publics/vk_collect.py posts --ids dlya-mam/_raw/vk_included.txt

Собирает только публичные данные сообществ и посты от имени сообщества.
Участников, комментарии и авторов не собирает (R02, раздел 7).
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from keywords import FEDERAL, LOCAL  # noqa: E402

API = "https://api.vk.com/method/"
V = "5.199"
RAW = pathlib.Path(__file__).resolve().parents[2] / "_raw"
PAUSE = 0.4  # не больше 3 запросов в секунду
DAYS = 90
MAX_POSTS = 300


def call(method, **params):
    token = os.environ.get("VK_TOKEN")
    if not token:
        sys.exit("Нет VK_TOKEN в окружении")
    params.update(access_token=token, v=V)
    url = API + method + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        time.sleep(PAUSE)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
        if "error" not in data:
            return data["response"]
        code = data["error"].get("error_code")
        if code in (6, 9, 29):  # слишком часто: ждём и повторяем
            time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"{method}: {data['error']}")
    raise RuntimeError(f"{method}: лимит запросов не отпустил")


def city_id():
    resp = call("database.getCities", country_id=1, q="Новосибирск", count=5)
    items = resp.get("items", [])
    for it in items:
        if it.get("title") == "Новосибирск":
            return it["id"]
    sys.exit(f"Не нашёл Новосибирск в database.getCities: {items}")


def search():
    RAW.mkdir(exist_ok=True)
    nsk = city_id()
    found = {}
    runs = [(kw, "А", nsk) for kw in LOCAL] + [(kw, "А", None) for kw in LOCAL] + [(kw, "Б", None) for kw in FEDERAL]
    for kw, sample, cid in runs:
        params = {"q": kw, "count": 100}
        if cid:
            params["city_id"] = cid
        for g in call("groups.search", **params).get("items", []):
            rec = found.setdefault(g["id"], {"found_by": set(), "sample_hint": set()})
            rec["found_by"].add(kw)
            rec["sample_hint"].add(sample)
    ids = list(found)
    rows = []
    for i in range(0, len(ids), 400):
        resp = call("groups.getById", group_ids=",".join(map(str, ids[i:i + 400])),
                    fields="members_count,activity,city,description,verified,is_closed")
        groups = resp["groups"] if isinstance(resp, dict) else resp
        for g in groups:
            rec = found[g["id"]]
            rows.append({
                "platform": "vk", "id": g["id"], "screen_name": g.get("screen_name", ""),
                "url": f"https://vk.com/{g.get('screen_name') or 'club' + str(g['id'])}",
                "name": g.get("name", ""), "members": g.get("members_count", ""),
                "activity": g.get("activity", ""), "city": (g.get("city") or {}).get("title", ""),
                "is_closed": g.get("is_closed", ""), "verified": g.get("verified", ""),
                "description": (g.get("description") or "")[:300].replace("\n", " "),
                "sample_hint": "/".join(sorted(rec["sample_hint"])), "found_by": "; ".join(sorted(rec["found_by"])),
            })
    out = RAW / "vk_found.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -(r["members"] or 0)))
    print(f"найдено {len(rows)} сообществ → {out}")


def is_ad(post):
    t = (post.get("text") or "").lower()
    return int(bool(post.get("marked_as_ads")) or "erid" in t or t.startswith("реклама") or "#реклама" in t)


def posts(ids_file):
    RAW.mkdir(exist_ok=True)
    since = time.time() - DAYS * 86400
    ids = [l.strip() for l in open(ids_file, encoding="utf-8") if l.strip() and not l.startswith("#")]
    out = RAW / "vk_posts.csv"
    fields = ["platform", "community_id", "post_id", "date", "text", "views", "likes", "comments_count",
              "reposts", "is_ad", "has_video", "has_photo", "is_repost", "is_pinned"]
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for gid in ids:
            gid = gid.lstrip("-")
            offset = 0
            while offset < MAX_POSTS:
                items = call("wall.get", owner_id=f"-{gid}", filter="owner", count=100, offset=offset).get("items", [])
                if not items:
                    break
                stop = False
                for p in items:
                    if p.get("date", 0) < since:
                        if p.get("is_pinned"):
                            continue
                        stop = True
                        break
                    att = {a.get("type") for a in p.get("attachments", [])}
                    w.writerow({
                        "platform": "vk", "community_id": gid, "post_id": p["id"],
                        "date": time.strftime("%Y-%m-%d", time.gmtime(p["date"])),
                        "text": (p.get("text") or "")[:1000],
                        "views": (p.get("views") or {}).get("count", ""),
                        "likes": (p.get("likes") or {}).get("count", 0),
                        "comments_count": (p.get("comments") or {}).get("count", 0),
                        "reposts": (p.get("reposts") or {}).get("count", 0),
                        "is_ad": is_ad(p), "has_video": int("video" in att), "has_photo": int("photo" in att),
                        "is_repost": int(bool(p.get("copy_history"))), "is_pinned": int(bool(p.get("is_pinned"))),
                    })
                    n += 1
                if stop:
                    break
                offset += 100
    print(f"постов: {n} → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "posts"])
    ap.add_argument("--ids", help="файл с id сообществ, по одному в строке (после ручного фильтра)")
    a = ap.parse_args()
    if a.cmd == "search":
        search()
    else:
        if not a.ids:
            sys.exit("нужен --ids")
        posts(a.ids)
