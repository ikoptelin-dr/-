"""Сбор Wordstat через Yandex Cloud Search API (topRequests, последние 30 дней).
Ключ подставляет прокси окружения; в коде и git его нет.
Выход: inputs/wordstat/<дата>/<регион>/<seed>.json — сырые ответы без изменений.
Запуск: python3 -I dlya-mam/scripts/wordstat_collect.py"""
import json, os, time, urllib.request, datetime, sys
SEEDS = ["температура ребенок","сыпь ребенок","рвота ребенок","понос ребенок","кашель ребенок","насморк грудничок",
 "колики","срыгивание","желтушка новорожденный","прикорм","грудное вскармливание","мало молока","лактостаз","мастит",
 "сцеживание","трещины соски","прививка ребенок","реакция на прививку","атопический дерматит ребенок","крапивница ребенок",
 "потница","пеленочный дерматит","зубы режутся","сон грудничок","вес грудничок","стул грудничка","отит ребенок",
 "обструктивный бронхит","скорая ребенку","новорожденный уход"]
REGIONS = {"rf": "225", "nso": "11316"}
day = datetime.date.today().isoformat()
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'inputs', 'wordstat', day)
def call(phrase, region):
    body = json.dumps({"phrase": phrase, "numPhrases": "2000", "regions": [region], "devices": ["DEVICE_ALL"]}).encode()
    req = urllib.request.Request("https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
for rk, rid in REGIONS.items():
    os.makedirs(os.path.join(base, rk), exist_ok=True)
    for s in SEEDS:
        out = os.path.join(base, rk, s.replace(' ', '_') + '.json')
        if os.path.exists(out): continue
        for attempt in range(4):
            try:
                d = call(s, rid); json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False); break
            except Exception as e:
                print('retry', rk, s, e, file=sys.stderr); time.sleep(2 * (attempt + 1))
        time.sleep(0.4)
    print(rk, 'готово')
