"""Разбор выгрузки Яндекс Вордстата (волна 1): разметка каждой фразы, спрос по кластерам, вопросы людей.

Правила:
- ни одна фраза не удаляется: каждая получает поля «кластер / аудитория / интент / релевантность / формат»;
- частоты не суммируются: спрос маски — частота её head-фразы, спрос кластера — максимум head-частот его масок;
- числа — только из выгрузки; вид частоты — та, что дал Вордстат в левой колонке (базовая, регион — как в выгрузке).
Правила — словари регулярных выражений ниже, их легко править."""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

QUESTION = re.compile(r"^(как|что|почему|зачем|можно ли|сколько|чем|когда|какой|какая|какое|какие|нужно ли|правда ли|где|кто|стоит ли|надо ли|бывает ли|опасно ли|вредно ли)\b|\b(можно ли|нужно ли|правда ли|что лучше|что делать|чем отличается|что будет)\b")
CITIES = (r"москв|мск\b|спб|санкт|питер|петербург|екатеринбург|новосибирск|казан|краснодар|нижн\w* новгород|самар|ростов|\bуф[аеы]\b|"
          r"челябинск|омск|перм[ьи]|воронеж|волгоград|красноярск|саратов|тюмен|ижевск|барнаул|ульяновск|иркутск|хабаровск|ярославл|"
          r"владивосток|махачкал|томск|оренбург|кемерово|новокузнецк|рязан|астрахан|пенз|липецк|тул[аеы]\b|киров|чебоксар|калининград|"
          r"курск|сочи|ставропол|белгород|брянск|твер|иваново|сургут|смоленск|минск|алмат|астан|киев|ташкент|бишкек|подольск|химки|"
          r"балаших|мытищ|люберц|королев|зеленоград|пушкино|красногорск|одинцов|адрес|метро|рядом|поблизости|в городе|район")
RULES: list[tuple[str, str]] = [
    # (класс, шаблон) — порядок важен: первое совпадение решает релевантность
    ("job", r"ваканси|\bработа\b|работу\b|зарплат|зарабатыва|резюме|требуется|подработк|сколько получает"),
    ("noise", r"скачать|\bгдз\b|реферат|презентац|раскраск|рисун|картинк|\bмем|песн|фильм|сериал|\bигр[аы]\b|майнкрафт|анекдот|стих|"
              r"для собак|для кошек|для животных|кот[аеу]?\b|собак|лошад|\bавто\b|машин|\bшин|краск[аи] для|для дерева|для металла"),
    ("adjacent_hair", r"волос|кожи головы|\bголов[ыуе]\b|облысен|алопец|ресниц|бров(ей|и)\b.*(ламин|окраш)|кератин|ботокс для волос|шамп"),
    ("adjacent_body", r"сустав|связок|хрящ|костей|\bспорт|похуден|целлюлит|растяжк|\bтела\b|ног[иа]?\b|подмыш|интим|влагалищ|вагин|груд[иь]\b|ягодиц|живот"),
    ("education", r"курс[ыаов]?\b|обучени|учиться|научиться|колледж|диплом|сертификат|переподготов|ординатур|повышени\w* квалификац|"
                  r"\bнмо\b|аккредитац|профстандарт|экзамен|тест[ыа]? (для|по)|лекци|вебинар|семинар|школа косметолог|университет|"
                  r"медицинск\w* образован|без медицинского"),
    ("local", CITIES),
]
INTENT: list[tuple[str, str]] = [
    ("commercial", r"цен[аыуе]\b|стоимост|сколько стоит|купить|заказать|аптек|озон|ozon|wildberries|\bвб\b|недорог|дешев|скидк|акци|прайс|"
                   r"записаться|запись|оптом|магазин|интернет магазин|рассрочк"),
    ("reviews", r"отзыв|рейтинг|лучш|топ\b|какой выбрать|какую выбрать|что выбрать"),
    ("diy", r"в домашних условиях|дома\b|своими руками|самостоятельно|самой\b|самому\b|рецепт|народн|маска из|из подручн"),
    ("question", QUESTION.pattern),
    ("info", r"\bвред|польз|побочн|последстви|осложнен|противопоказ|после\b|до и после|отлич|\bили\b|инструкц|аналог|состав|действи|"
             r"показани|применени|схема|курс лечения|лечени|причин|симптом|признак|фото|что это|это\b"),
]
PRO = re.compile(r"для косметолог|косметолог[уа]м?\b.*(купить|оборудован|аппарат|препарат)|протокол|оборудовани|аппарат для|"
                 r"кабинет косметолог|открыть кабинет|бизнес|оптом|для салон|профессиональн\w* косметик|себестоим|ценообраз|"
                 r"дистрибьют|поставщик|клиент(ов|ам|ы)\b|разведени|гидратац")
FORMAT = {"question": "статья / пост-ответ", "info": "статья / пост", "diy": "пост-разбор мифа (осторожно)", "reviews": "разбор: как выбирать",
          "commercial": "не наш формат (деньги в теме)", "navigational": "статья-разбор препарата / средства", "broad": "опорная статья"}
REL_RU = {"target": "целевая", "noise": "шум", "job": "работа — не клиенты", "education": "обучение (цель для Proba Pro)",
          "local": "локальный поиск (город, «рядом»)", "adjacent_hair": "смежное: волосы", "adjacent_body": "смежное: тело, суставы, интим",
          "navigational": "навигационный (бренд, препарат, клиника)"}


@dataclass
class Phrase:
    q: str
    freq: int
    masks: set[str] = field(default_factory=set)
    cluster: str = ""
    audience: str = "consumer"
    intent: str = "broad"
    relevance: str = "target"
    medical: bool = False
    concepts: list[str] = field(default_factory=list)


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r'[!"+\[\]()|]', " ", t)).strip().lower().replace("ё", "е")


def load_csv(path: Path) -> list[tuple[str, str, int]]:
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        r = csv.reader(f, delimiter=";")
        header = next(r)
        if [h.strip().lower() for h in header[:3]] != ["тема", "запрос", "частота"]:
            raise ValueError(f"ожидались колонки Тема;Запрос;Частота, а не {header}")
        for line in r:
            if len(line) < 3 or not line[2].strip().isdigit():
                raise ValueError(f"плохая строка: {line}")
            rows.append((line[0].strip(), line[1].strip(), int(line[2])))
    return rows


def mask_index(masks_yaml: dict) -> dict[str, dict]:
    idx = {}
    for g in masks_yaml["groups"]:
        for m in g["masks"]:
            idx[norm(m["q"])] = {"group": g["id"], "cluster": g["cluster"], "audience": g["audience"],
                                 "medical": bool(g.get("medical")), "tier": "A" if m.get("star") else "B" if m.get("broad") else "C"}
    return idx


def classify(p: Phrase, lexicon: dict, concept_to: dict[str, list[str]], navigational: set[str], mask_meta: dict) -> None:
    q = p.q
    for name, pat in RULES:
        if re.search(pat, q):
            p.relevance = name
            break
    p.intent = "broad"
    for name, pat in INTENT:
        if re.search(pat, q):
            p.intent = name
            break
    words = set(q.split())
    if words & navigational and p.intent == "broad":
        p.intent = "navigational"
    p.concepts = [c for c, pats in lexicon["concepts"].items() if any(re.search(x, q) for x in pats)]
    order = lexicon.get("primary_order", [])
    hits = {cid for c in p.concepts for cid in concept_to.get(c, [])}
    p.cluster = next((cid for cid in order if cid in hits), "") or mask_meta.get("cluster", "")
    pro = bool(PRO.search(q)) or p.relevance == "education" or mask_meta.get("audience") == "pro"
    p.audience = "pro" if pro else "consumer"
    if p.relevance == "education" and mask_meta.get("audience") != "pro" and not PRO.search(q):
        p.audience = "pro"  # обучение — всегда про специалистов (или будущих)
    p.medical = mask_meta.get("medical", False)


def analyse(csv_path: Path, masks_yaml: dict, lexicon: dict, navigational: set[str]) -> dict[str, Any]:
    rows = load_csv(csv_path)
    idx = mask_index(masks_yaml)
    concept_to: dict[str, list[str]] = defaultdict(list)
    for c in lexicon["clusters"]:
        for k in c["concepts"]:
            concept_to[k].append(c["id"])
    by_mask: dict[str, list[tuple[str, int]]] = defaultdict(list)
    phrases: dict[str, Phrase] = {}
    for t, q, f in rows:
        nt, nq = norm(t), norm(q)
        by_mask[nt].append((nq, f))
        p = phrases.get(nq)
        if p is None:
            p = phrases[nq] = Phrase(nq, f)
        p.freq = max(p.freq, f)
        p.masks.add(nt)
    for p in phrases.values():
        meta = next((idx[m] for m in sorted(p.masks) if m in idx), {})
        classify(p, lexicon, concept_to, navigational, meta)

    masks = []
    for m, items in by_mask.items():
        heads = [f for q, f in items if q == m]
        meta = idx.get(m, {})
        uniq = {q for q, _ in items}
        masks.append({"mask": m, "in_plan": m in idx, "group": meta.get("group", ""), "cluster": meta.get("cluster", ""),
                      "audience": meta.get("audience", ""), "tier": meta.get("tier", ""),
                      "head_freq": max(heads) if heads else None, "head_from": "mask" if heads else "missing",
                      "tails": len(uniq), "capped_2000": len(items) >= 2000,
                      "top_tail": max(((q, f) for q, f in items if q != m), key=lambda x: x[1], default=("", 0))[0]})
    planned = set(idx)
    missing = sorted(planned - set(by_mask))
    return {"rows": len(rows), "phrases": phrases, "masks": masks, "missing": missing, "idx": idx}


def summarise(a: dict[str, Any], lexicon: dict) -> list[dict[str, Any]]:
    names = {c["id"]: c["name"] for c in lexicon["clusters"]} | {"META": "Широкие головы рынка"}
    out = []
    by_cluster: dict[str, list[Phrase]] = defaultdict(list)
    for p in a["phrases"].values():
        by_cluster[p.cluster or "—"].append(p)
    mask_heads: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for m in a["masks"]:
        if m["head_freq"]:
            mask_heads[m["cluster"] or "—"].append((m["head_freq"], m["mask"]))
    for cid, ps in by_cluster.items():
        target = [p for p in ps if p.relevance == "target"]
        heads = sorted(mask_heads.get(cid, []), reverse=True)
        top = lambda pred, n=5: [f"{p.q} ({p.freq})" for p in sorted((x for x in target if pred(x)), key=lambda x: -x.freq)[:n]]
        rel = Counter(p.relevance for p in ps)
        out.append({
            "cluster": cid, "name": names.get(cid, "без кластера"),
            "head_mask": heads[0][1] if heads else "", "head_demand": heads[0][0] if heads else max((p.freq for p in ps), default=0),
            "head_basis": "частота head-фразы маски" if heads else "макс. частота фразы (маски кластера нет)",
            "phrases": len(ps), "target": len(target), "relevance": dict(rel.most_common()),
            "pro_target": sum(1 for p in target if p.audience == "pro"),
            "top_questions": top(lambda p: p.intent == "question", 8),
            "top_info": top(lambda p: p.intent == "info", 5),
            "top_navigational": top(lambda p: p.intent == "navigational", 5),
            "top_commercial": top(lambda p: p.intent == "commercial", 3),
            "top_diy": top(lambda p: p.intent == "diy", 3),
            "top_pro": top(lambda p: p.audience == "pro", 5),
        })
    out.sort(key=lambda r: -r["head_demand"])
    return out


def write(a: dict[str, Any], summary: list[dict], out_dir: Path, full_csv: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    full_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["phrase", "freq", "cluster", "audience", "intent", "relevance", "relevance_ru", "format", "medical", "masks"]
    with full_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for p in sorted(a["phrases"].values(), key=lambda x: -x.freq):
            w.writerow([p.q, p.freq, p.cluster, p.audience, p.intent, p.relevance, REL_RU[p.relevance],
                        FORMAT.get(p.intent, "") if p.relevance == "target" else "", "да" if p.medical else "", " | ".join(sorted(p.masks))])
    with (out_dir / "masks_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(a["masks"][0].keys()), delimiter=";")
        w.writeheader()
        for m in sorted(a["masks"], key=lambda x: -(x["head_freq"] or 0)):
            w.writerow(m)
    with (out_dir / "clusters_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["cluster", "name", "head_mask", "head_demand", "phrases", "target", "pro_target", "top_questions", "top_info", "top_navigational", "top_commercial"])
        for s in summary:
            w.writerow([s["cluster"], s["name"], s["head_mask"], s["head_demand"], s["phrases"], s["target"], s["pro_target"],
                        " ; ".join(s["top_questions"]), " ; ".join(s["top_info"]), " ; ".join(s["top_navigational"]), " ; ".join(s["top_commercial"])])
    # Топ вопросов — главная заготовка для контента
    qs = sorted((p for p in a["phrases"].values() if p.relevance == "target" and p.intent == "question"), key=lambda x: -x.freq)
    with (out_dir / "top_questions.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["question", "freq", "cluster", "audience", "medical"])
        for p in qs[:1000]:
            w.writerow([p.q, p.freq, p.cluster, p.audience, "да" if p.medical else ""])
