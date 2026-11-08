"""Собирает dlya-mam/zamery/z02-wordstat-keys.csv.

Фразы с job_id сверяются дословно с query_mom в inputs/all.jsonl (иначе ошибка).
Фразы с job_id=control не из карты: они нужны для цены клика клиник,
платного намерения и веса конкурента. Частотности здесь НЕТ — их вносит человек.
Запуск: python3 -I dlya-mam/scripts/make_wordstat_keys.py
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# (группа, job_id, фраза)
# night    — ночное ядро (7 экранов + исход)
# paid     — кандидаты в платное (плановое, долгое)
# boundary — «чем лечить»: спрос, который продукт по границе НЕ обслуживает
# clinic   — цена клика клиник в НСО (для сравнения с рекламным местом)
# intent   — платное намерение (ищут ли курс/консультацию вообще)
# brand    — вес бесплатного конкурента
KEYS = [
    ("night", "ped-fever-night", "высокая температура ночью"),
    ("night", "ped-fever-night", "температура 39 у ребёнка"),
    ("night", "ped-fever-when", "надо ли сбивать температуру 37,5"),
    ("night", "ped-fever-when", "температура держится неделю"),
    ("night", "vax-reaction", "температура после прививки"),
    ("night", "ped-wheeze", "ребёнок тяжело дышит"),
    ("night", "ped-wheeze", "свистящее дыхание у ребёнка"),
    ("night", "ped-wheeze", "обструктивный бронхит"),
    ("night", "gv-latch-pain", "больно кормить грудью"),
    ("night", "gv-latch-pain", "трещина на соске"),
    ("night", "gv-lactostasis", "лактостаз"),
    ("night", "gv-lactostasis", "уплотнение в груди"),
    ("night", "gv-lactostasis", "застой молока"),
    ("night", "gv-mastitis", "мастит"),
    ("night", "gv-mastitis", "мастит или застой"),
    ("night", "ped-vomit", "рвота у ребёнка что делать"),
    ("night", "ped-vomit", "рвота ночью"),
    ("night", "ped-vomit", "рвота и понос"),
    ("night", "ped-acetone", "изо рта пахнет ацетоном"),
    ("night", "ped-acetone", "ацетонемическая рвота"),
    ("night", "table-poisoning", "пищевое отравление у ребёнка"),
    ("night", "all-rash", "сыпь у ребёнка"),
    ("night", "all-rash", "сыпь после температуры"),
    ("night", "all-rash", "крапивница у ребёнка"),
    ("night", "ped-otitis", "болит ухо у ребёнка"),
    ("night", "ped-otitis", "можно ли греть ухо"),
    ("night", "ped-gas", "колики у новорожденного"),
    ("night", "ped-gas", "плачет по вечерам, болит животик"),
    ("night", "nav-when-doctor", "когда вызывать скорую ребёнку"),
    ("night", "nav-when-doctor", "когда к врачу с ребёнком"),
    ("paid", "all-atopy", "атопический дерматит у ребёнка"),
    ("paid", "all-atopy", "диатез или атопический дерматит"),
    ("paid", "all-asthma", "астма у ребёнка"),
    ("paid", "feed-first", "когда начинать прикорм"),
    ("paid", "feed-first", "ребёнок не ест прикорм"),
    ("paid", "feed-puree-vs-table", "банки или домашнее пюре"),
    ("paid", "feed-allergy", "как вводить прикорм при аллергии"),
    ("paid", "gv-low-supply", "мало молока"),
    ("paid", "gv-low-supply", "пропадает молоко"),
    ("paid", "gv-weaning", "как закончить гв"),
    ("paid", "gv-sleep-nursing", "как отучить засыпать без груди"),
    ("paid", "gv-pumping", "сцеживание грудного молока"),
    ("paid", "ped-weight", "мало прибавляет в весе"),
    ("paid", "neuro-tone", "гипотонус у грудничка"),
    ("paid", "neuro-tone", "кривошея у новорождённого"),
    ("paid", "ped-jaundice", "желтушка у новорожденного"),
    ("paid", "ped-spit-up", "ребёнок часто срыгивает"),
    ("paid", "ped-cough", "длительный кашель"),
    ("paid", "vax-schedule", "календарь прививок по возрасту"),
    ("paid", "dent-caries", "кариес на молочных зубах"),
    ("boundary", "ped-fever-night", "чем сбивать температуру ребёнку"),
    ("boundary", "ped-otitis", "отит чем лечить"),
    ("boundary", "all-atopy", "чем мазать атопический дерматит"),
    ("boundary", "ped-vitamins", "аквадетрим дозировка"),
    ("boundary", "ped-cold", "что капать в нос ребёнку до года"),
    ("boundary", "dent-teething", "режутся зубы чем помочь"),
    ("clinic", "control", "педиатр на дом новосибирск"),
    ("clinic", "control", "детский дерматолог новосибирск"),
    ("clinic", "control", "детский лор новосибирск"),
    ("clinic", "control", "детский аллерголог новосибирск"),
    ("clinic", "control", "детская клиника новосибирск"),
    ("clinic", "control", "консультант по грудному вскармливанию новосибирск"),
    ("intent", "control", "курс по прикорму"),
    ("intent", "control", "курс по грудному вскармливанию"),
    ("intent", "control", "курсы для молодых мам"),
    ("intent", "control", "школа молодых мам новосибирск"),
    ("intent", "control", "онлайн консультация педиатра"),
    ("intent", "control", "курс атопический дерматит"),
    ("brand", "control", "комаровский температура"),
    ("brand", "control", "комаровский прикорм"),
    ("brand", "control", "комаровский"),
]

WHY = {
    "night": "есть ли сегодня спрос на ночной экран; объём бесплатного входа",
    "paid": "объём плановой темы — кандидата в платный продукт",
    "boundary": "доля спроса, которую мы по границе продукта не обслуживаем",
    "clinic": "цена клика клиники в НСО — потолок цены рекламного места",
    "intent": "ищут ли вообще платное обучение/консультацию",
    "brand": "вес бесплатного конкурента",
}


def main():
    cards = [json.loads(l) for l in open(ROOT / "inputs" / "all.jsonl", encoding="utf-8") if l.strip()]
    qm = {c["job_id"]: set(c["query_mom"]) for c in cards}
    seen = set()
    rows = []
    for i, (g, job, ph) in enumerate(KEYS, 1):
        assert ph not in seen, ph
        seen.add(ph)
        if job != "control":
            assert ph in qm.get(job, set()), f"нет в all.jsonl: {job} / {ph}"
        # Директ режет фразы по запятой («37,5» превращается в «37» и «5»),
        # а длиннее 7 слов фразу не принимает.
        paste = " ".join(ph.replace(",", " ").split())
        assert len(paste.split()) <= 7, paste
        rows.append([i, ph, paste, g, job, "all.jsonl" if job != "control" else "контроль, не из карты",
                     WHY[g], "", "", "", "", ""])
    out = ROOT / "zamery" / "z02-wordstat-keys.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "phrase", "paste_phrase", "group", "job_id", "source", "why",
                    "ws_nso_12m", "ws_rf_12m", "direct_cpc_nso_rub", "direct_clicks_month_nso", "direct_budget_month_nso_rub"])
        w.writerows(rows)
    paste_file = ROOT / "zamery" / "z03-direct-paste.txt"
    paste_file.write_text("\n".join(r[2] for r in rows) + "\n", encoding="utf-8")
    print(len(rows), "фраз записано в", out, "и", paste_file)


if __name__ == "__main__":
    main()
