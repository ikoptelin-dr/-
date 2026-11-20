"""Ядро Wordstat для детей 1–3 лет (РФ, 30 дней). Ключ — через прокси окружения. Выход: inputs/wordstat/<дата>-13/rf/*.json"""
import json, os, time, urllib.request, datetime, sys
SEEDS = ["ребенок 1 год","ребенок 1.5 года","ребенок 2 года","ребенок 2.5 года","ребенок 3 года","развитие ребенка 2 лет","что умеет ребенок в 2 года",
 "речь ребенка 2 года","ребенок не говорит в 2 года","истерики у ребенка","кризис 3 лет","ребенок кусается","ребенок дерется",
 "приучение к горшку","горшок ребенок","адаптация в детском саду","ребенок часто болеет","детский сад болеет",
 "питание ребенка 1 год","меню ребенка 2 года","ребенок плохо ест","коровье молоко ребенку","отлучение от груди",
 "сон ребенка 2 года","ребенок плохо спит ночью","дневной сон 2 года","ребенок боится","зубы у ребенка 2 года","кариес у ребенка",
 "температура у ребенка 2 года","кашель у ребенка 2 года","сопли у ребенка 2 года","понос у ребенка 2 года","аллергия у ребенка 2 года",
 "мультики ребенку","гаджеты ребенку","прививки после года","анемия у ребенка","рост ребенка 2 года","вес ребенка 2 года"]
day = datetime.date.today().isoformat() + '-13'
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'inputs', 'wordstat', day, 'rf'); os.makedirs(base, exist_ok=True)
for s in SEEDS:
    out = os.path.join(base, s.replace(' ', '_') + '.json')
    if os.path.exists(out): continue
    body = json.dumps({"phrase": s, "numPhrases": "2000", "regions": ["225"], "devices": ["DEVICE_ALL"]}).encode()
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests", body, {"Content-Type": "application/json"}), timeout=60) as r:
                json.dump(json.load(r), open(out, 'w', encoding='utf-8'), ensure_ascii=False); break
        except Exception as e:
            print('retry', s, e, file=sys.stderr); time.sleep(6 * (a + 1))
    time.sleep(1.2)
print('готово', len(os.listdir(base)), 'из', len(SEEDS))
