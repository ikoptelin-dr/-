"""Списки масок для ручного сбора в Яндекс Вордстате (волна 1) и шаблон для записи частот.

Частоты здесь не появляются: их снимает владелец вручную и присылает файлом (разбор — следующий шаг).
Интент маски выводится прозрачными правилами ниже; их легко править."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import yaml

# Служебные слова: в точной частоте их фиксируют оператором «+», а не «!».
STOP = {"в", "во", "на", "и", "с", "со", "от", "по", "под", "для", "без", "при", "из", "до", "после", "или", "к", "о", "об", "что", "как", "ли", "у", "за"}
NAVIGATIONAL = {"дифферин", "клензит", "адапален", "акнекутан", "роаккутан", "изотретиноин", "скинорен", "базирон", "эффезел",
                "клиндовит", "зинерит", "азелик", "финацея", "диспорт", "ксеомин", "релатокс", "коллост", "сферогель", "профайло",
                "дермапен", "гиалуронидаза", "гидрохинон", "декспантенол", "бакучиол", "третиноин", "ретиналь"}
INTENT_RULES: list[tuple[str, str]] = [
    ("noise_candidate", r"\b(работа|вакансии|зарплата|рядом)\b"),
    ("professional", r"протокол|обучени|курсы|косметолог(у|ов|а)?\b.*(без|эстетист|медицинск)|для косметолог|разведени|расход\b|расход филлера|"
                     r"себестоим|ценообраз|кабинет|клиентов|продвижен|маркетинг|лицензи|аккредит|нмо|ординатур|переподготов|профстандарт|"
                     r"семинар|вебинар|конференц|дистрибьют|препараты для|расходники|единицы ботокса|аппараты для|как стать|повышение квалификации|"
                     r"бизнес план|самозанят|закон|ограничени|окклюзи|некроз|патч тест|честный знак|поддельн|сочетание процедур|этапы чистки"),
    ("diy", r"в домашних условиях|самостоятельно|самой|своими руками|домашний"),
    ("commercial", r"\bцена\b|стоимост|купить|где купить|недорог|рейтинг|цены\b"),
    ("informational", r"что это|^как |\bкак\b|можно ли|с какого|сколько|побочн|последстви|осложнен|отзывы|до и после|вред|причины|лечение|"
                      r"после|какой|почему|что нельзя|противопоказан|подготовк|или\b|\bи\b|обострение|диета|уход|при беременности|"
                      r"концентрац|результат|летом|зимой|каждый день|с чего начать|определить"),
]


def intent(q: str, audience: str = "consumer") -> str:
    if q in NAVIGATIONAL:
        return "navigational"
    for name, pat in INTENT_RULES:
        if re.search(pat, q):
            return name
    if audience == "pro":
        return "professional"
    return "broad" if len(q.split()) == 1 else "topical"


def phrase_form(q: str) -> str:
    return f'"{q}"'


def exact_form(q: str) -> str:
    words = [("+" if w in STOP else "!") + w for w in q.split()]
    return '"' + " ".join(words) + '"'


def tier(m: dict) -> str:
    return "A" if m.get("star") else "B" if m.get("broad") else "C"


def load(path: Path, lexicon: dict | None = None) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    known = {c["id"] for c in (lexicon or {}).get("clusters", [])} | {"META"}
    rows = []
    for g in data["groups"]:
        if lexicon is not None and g["cluster"] not in known:
            raise ValueError(f"{g['id']}: неизвестный кластер {g['cluster']}")
        for m in g["masks"]:
            q = m["q"].strip().lower()
            if q != m["q"]:
                raise ValueError(f"маска не в нижнем регистре или с пробелами: {m['q']!r}")
            if q in seen:
                raise ValueError(f"повтор маски {q!r} в {g['id']} и {seen[q]}")
            seen[q] = g["id"]
            rows.append({"tier": tier(m), "group": g["id"], "group_title": g["title"], "cluster": g["cluster"],
                         "audience": g["audience"], "medical": bool(g.get("medical")), "intent": intent(q, g["audience"]), "mask": q,
                         "phrase": phrase_form(q), "exact": exact_form(q)})
    data["rows"] = rows
    return data


def write(data: dict[str, Any], out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    rows = data["rows"]
    by_tier = {t: [r for r in rows if r["tier"] == t] for t in "ABC"}
    (out / "masks_all.txt").write_text("\n".join(r["mask"] for r in rows) + "\n", encoding="utf-8")
    (out / "masks_A_star.txt").write_text("\n".join(r["mask"] for r in by_tier["A"]) + "\n", encoding="utf-8")
    (out / "masks_A_star_exact.txt").write_text("\n".join(r["exact"] for r in by_tier["A"]) + "\n", encoding="utf-8")
    (out / "masks_B_broad.txt").write_text("\n".join(r["mask"] for r in by_tier["B"]) + "\n", encoding="utf-8")
    (out / "masks_C_rest.txt").write_text("\n".join(r["mask"] for r in by_tier["C"]) + "\n", encoding="utf-8")
    cols = ["tier", "group", "cluster", "audience", "intent", "medical", "mask", "phrase", "exact",
            "base_russia", "phrase_russia", "exact_russia", "base_region", "exact_region", "tails_copied", "note"]
    with (out / "wordstat_template.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "medical": "да" if r["medical"] else ""})
    (out / "README.md").write_text(render(data, by_tier), encoding="utf-8")
    return {t: len(v) for t, v in by_tier.items()} | {"all": len(rows)}


INTENT_RU = {"broad": "широкий", "topical": "тематический (без уточнения)", "informational": "информационный", "commercial": "коммерческий", "diy": "сделаю сам",
             "navigational": "навигационный", "professional": "профессиональный", "noise_candidate": "вероятный шум"}
AUD_RU = {"consumer": "потребители", "pro": "специалисты", "both": "обе"}


def render(data: dict, by_tier: dict) -> str:
    rows = data["rows"]
    L: list[str] = []
    w = L.append
    w("# Вордстат, волна 1: список масок для ручной проверки")
    w("")
    w(f"Версия списка {data['version']}. Всего масок: **{len(rows)}**: ярус A — {len(by_tier['A'])}, B — {len(by_tier['B'])}, C — {len(by_tier['C'])}.")
    w("Частот в этом файле нет: их снимаете вы. Основа списка — 21 кластер из отчёта `reports/ru_market_2026-11/` и формулировки людей с форумов.")
    w("")
    w("## Как снимать (по ярусам — чтобы не утонуть)")
    w("")
    w("1. Откройте wordstat.yandex.ru и войдите в аккаунт Яндекса.")
    w("2. **Ярус A — ★ главные** (`masks_A_star.txt`). По каждой маске:")
    w("   - **базовая** частота: `маска` как есть;")
    w("   - **фразовая**: `\"маска\"` в кавычках;")
    w("   - **точная**: из файла `masks_A_star_exact.txt` (вид `\"!слово !слово\"`, предлоги с `+`);")
    w("   - регион «Россия», затем ваш регион;")
    w("   - скриншот вкладки «Динамика» (сезонность);")
    w("   - из левой колонки «Что искали со словом…» скопируйте все хвосты с частотой от 10; если частота маски меньше 20 — хвосты не нужны.")
    w("3. **Ярус B — широкие** (`masks_B_broad.txt`): базовая частота по России и вся левая колонка.")
    w("4. **Ярус C — остальное** (`masks_C_rest.txt`): одна базовая частота по России. Если фраза уже попала в левую колонку A или B — пропустите её и поставьте отметку в шаблоне.")
    w("5. Если у Вордстата есть кнопка выгрузки («Скачать», CSV/XLSX), используйте её вместо копирования.")
    w("6. Записывайте в `wordstat_template.csv`, колонки:")
    w("   - `base_russia` — базовая, Россия;")
    w("   - `phrase_russia` — фразовая, Россия;")
    w("   - `exact_russia` — точная, Россия;")
    w("   - `base_region` — базовая, ваш регион;")
    w("   - `exact_region` — точная, ваш регион;")
    w("   - `tails_copied` — хвосты скопированы (да/нет).")
    w("")
    w("   Хвосты из левой колонки присылайте отдельными файлами: одна маска — один файл, или всё в одном CSV `фраза;частота;маска`.")
    w("")
    w("Время [Гипотеза]: A — около 1–1,5 ч, B — около 1–1,5 ч, C — 2–3 ч. Можно прислать A и B, а C — позже.")
    w("")
    w("## Операторы Вордстата")
    w("")
    w("| Оператор | Что делает | Пример |")
    w("|---|---|---|")
    w('| `"..."` | только эти слова, без хвостов | `"ботокс лоб"` |')
    w("| `!` | точная форма слова | `!акнекутан` |")
    w("| `+` | учитывать предлог или союз | `+после !ботокса` |")
    w("| `-слово` | исключить слово | `косметолог -работа -вакансии` |")
    w("| `[...]` | фиксированный порядок слов | `[ретинол для лица]` |")
    w("| `(а\\|б)` | варианты | `(акнекутан\\|роаккутан) отзывы` |")
    w("")
    w("Минус-слова для потребительских масок: " + ", ".join(f"`-{x}`" for x in data["minus_words_consumer"]) + ".")
    w("Для масок Proba Pro не исключайте «курсы» и «обучение» — это целевое. Исключайте: " + ", ".join(f"`-{x}`" for x in data["minus_words_pro"]) + ".")
    w("")
    w("## ★ Главные маски (ярус A)")
    w("")
    w("| Маска | Точная форма | Кластер | Аудитория |")
    w("|---|---|---|---|")
    for r in by_tier["A"]:
        w(f"| ★ {r['mask']} | `{r['exact']}` | {r['cluster']} | {AUD_RU[r['audience']]} |")
    w("")
    w("## Все маски по темам")
    w("")
    w("Обозначения: ★ — ярус A; **жирным** — ярус B (широкая, нужна левая колонка); ⚕ — медицинская тема (тексты только после научного досье и рецензии).")
    w("")
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    for gid, items in groups.items():
        g = items[0]
        med = " ⚕" if g["medical"] else ""
        w(f"### {gid}. {g['group_title']} ({g['cluster']}, {AUD_RU[g['audience']]}){med}")
        w("")
        w("| Маска | Интент |")
        w("|---|---|")
        for r in items:
            mark = "★ " if r["tier"] == "A" else ""
            q = f"**{r['mask']}**" if r["tier"] in ("A", "B") else r["mask"]
            w(f"| {mark}{q} | {INTENT_RU[r['intent']]} |")
        w("")
    w("## Что прислать мне")
    w("")
    w("1. Заполненный `wordstat_template.csv` (можно частично).")
    w("2. Хвосты левой колонки (CSV или текст) для ярусов A и B.")
    w("3. Скриншоты «Динамики» для ★.")
    w("4. Название вашего региона.")
    w("")
    w("Дальше (шаг 2): разметка каждой фразы — тема, аудитория, интент, шум, формат контента, медицинская пометка. "
      "Сравнение с форумами и список тем для двух веток Proba. Частоты не суммируются: спрос кластера — частота его head-фразы.")
    w("")
    return "\n".join(L)
