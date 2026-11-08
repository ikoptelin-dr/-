"""Разбор сохранённых выдач Яндекса (inputs/serp/*.txt — корпус из 71 страницы).

    python3 -I dlya-mam/scripts/parse_serp.py

Выход (zamery/):
  z12-serp-pages.csv     — по выдаче: регион, ответ Алисы, число органики, промо, рекламы, колдунщики
  z12-serp-organic.csv   — органика по порядку: позиция, домен, URL, заголовок, сниппет
  z12-serp-paid.csv      — промо и реклама: домен, текст, тип (promo / ad)
  z12-serp-alice.csv     — текст быстрого ответа Алисы (если сохранился) и его источники
  z12-related.csv        — блок «Люди ищут»
Ограничения корпуса (из его шапки): одна страница выдачи, без JS, номера страниц — порядок
файлов, а не позиции. Позиция органики = порядок в DOM.
"""
import csv
import pathlib
import re
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = sorted((ROOT / "inputs" / "serp").glob("*.txt"))
OUT = ROOT / "zamery"
DOM_RE = re.compile(r"^((?:[\w\-]+\.)+[a-zа-я\-]{2,})(›| )")
URL_RE = re.compile(r"<(https?://[^>]+)>")
SKIP_DOMAINS = {"ya.ru"}
OPAQUE = "Непрозрачная служебная ссылка"


def pages(text):
    for pid, body in re.findall(r"===== BEGIN_PAGE (PAGE_\d+) =====\n(.*?)\n===== END_PAGE \1 =====", text, re.S):
        title = re.search(r"Заголовок og:title: (.*)", body)
        url = re.search(r"URL из og:url: (\S+)", body)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url.group(1) if url else "").query)
        lines = re.findall(r"^L(\d+): (.*)$", body, re.M)
        yield pid, (title.group(1).strip() if title else ""), q.get("lr", [""])[0], [(int(n), l) for n, l in lines]


def parse(pid, query, lr, lines):
    texts = [l for _, l in lines]
    page = {"page": pid, "query": query, "lr": lr}
    # --- Алиса ---
    alice = "Быстрый ответ Алисы AI" in texts
    a_text, a_src = "", []
    if "Содержимое ответа" in texts:
        i = texts.index("Содержимое ответа")
        j = next((k for k in range(i, len(texts)) if texts[k] == "Оценить ответ"), min(i + 40, len(texts)))
        a_text = " ".join(URL_RE.sub("", t) for t in texts[i + 1:j] if OPAQUE not in t and t not in ("Промо", "Подробнее"))
        k = j + 1
        if k < len(texts) and re.match(r"^\d+ источник", texts[k]):
            k += 1
            while k < len(texts) and not texts[k].startswith("Алиса старается"):
                if not texts[k].startswith("<") and re.match(r"^[\w.\-]+\.[a-zа-я]{2,}$", texts[k]):
                    a_src.append(texts[k])
                k += 1
    # Блок Алисы не вырезаем: строки его текста не начинаются с домена, а промо внутри него
    # (непрозрачные ссылки) честно считаются как промо.
    end_alice = 0
    page.update(alice=int(alice), alice_text_saved=int(bool(a_text)), alice_sources=len(set(a_src)))
    # --- органика, промо, реклама ---
    organic, paid = [], []
    in_ads = False
    for idx, (n, l) in enumerate(lines):
        if idx < end_alice:
            continue
        if l == "Реклама":
            in_ads = True
            continue
        if l == "Страницы результатов поиска":
            break
        m = DOM_RE.match(l)
        if not m:
            continue
        dom = m.group(1).lower().removeprefix("www.")
        if OPAQUE in l:
            nxt = " ".join(texts[idx + 1: idx + 3])
            kind = "promo" if "Промо" in nxt else ("ad" if in_ads else "promo_or_ad")
            title = texts[idx - 2] if idx >= 2 else ""
            snippet = next((t for t in texts[idx + 1: idx + 4] if t not in ("Промо",) and OPAQUE not in t
                            and t != "Сайт специализируется на продаже товаров"), "")
            paid.append({"page": pid, "query": query, "line": n, "kind": kind, "domain": dom,
                         "title": title[:200], "text": snippet[:300]})
            continue
        u = URL_RE.search(l)
        if not u or dom in SKIP_DOMAINS:
            continue
        in_ads = False
        title = texts[idx - 2] if idx >= 2 and not texts[idx - 2].startswith("<") else ""
        snippet = next((t for t in texts[idx + 1: idx + 4] if not t.startswith("<") and not DOM_RE.match(t)
                        and t not in ("Опубликовано позавчера",)), "")
        shop = int("Сайт специализируется на продаже товаров" in texts[idx + 1: idx + 3])
        organic.append({"page": pid, "query": query, "pos": len(organic) + 1, "line": n, "domain": dom,
                        "url": u.group(1), "title": title[:200], "snippet": snippet[:300], "shop_label": shop})
    page.update(n_organic=len(organic), n_promo=sum(p["kind"] == "promo" for p in paid),
                n_ad=sum(p["kind"] != "promo" for p in paid),
                doctors_wizard=int("Учёная степень" in texts and "Цена приёма" in texts),
                orgs_block=int("Время работы" in texts and "Телефон" in texts))
    rel = []
    if "Люди ищут" in texts:
        i = texts.index("Люди ищут")
        for t in texts[i + 1:i + 30]:
            if t == "Страницы результатов поиска":
                break
            if not t.startswith("<"):
                rel.append(t)
    alice_row = {"page": pid, "query": query, "alice_text": a_text, "alice_sources": "; ".join(dict.fromkeys(a_src))}
    return page, organic, paid, alice_row, [{"page": pid, "query": query, "related": r} for r in rel]


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    P, O, PA, A, R = [], [], [], [], []
    for src in SRC:
        for pid, q, lr, lines in pages(open(src, encoding="utf-8").read()):
            p, o, pa, a, r = parse(pid, q, lr, lines)
            P.append(p); O += o; PA += pa; A.append(a); R += r
    write("z12-serp-pages.csv", P)
    write("z12-serp-organic.csv", O)
    write("z12-serp-paid.csv", PA)
    write("z12-serp-alice.csv", A)
    write("z12-related.csv", R)
    print(f"выдач {len(P)}, органика {len(O)}, промо/реклама {len(PA)}, «Люди ищут» {len(R)}")


if __name__ == "__main__":
    main()
