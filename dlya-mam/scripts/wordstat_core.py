"""Ядро из сырых ответов Wordstat: чистка, разметка групп, лексическая кластеризация по вложенности лемм.
Вход: inputs/wordstat/<дата>/{rf,nso}/*.json. Выход: zamery/z31-core.csv, zamery/z32-lex-clusters.csv.
Метод кластеров: фразы с частотой >= HEAD (РФ, 30 дней) — кандидаты в статьи. Каждая фраза прикрепляется
к самому «узкому» кандидату, чьи значимые леммы все входят в её леммы. Выдачей НЕ проверено.
Запуск: python3 dlya-mam/scripts/wordstat_core.py [HEAD] [MIN]"""
import json, glob, os, re, csv, sys, collections
import pymorphy3
M = pymorphy3.MorphAnalyzer()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HEAD = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 50
day = sorted(glob.glob(os.path.join(ROOT, 'inputs', 'wordstat', '20*')))[-1]
rf, nso, seed_of = collections.Counter(), collections.Counter(), {}
for f in glob.glob(os.path.join(day, 'rf', '*.json')):
    s = os.path.basename(f)[:-5].replace('_', ' ')
    for r in json.load(open(f, encoding='utf-8'))['results']:
        p = r['phrase'].strip().lower(); c = int(r['count'])
        if c > rf[p]: rf[p] = c; seed_of[p] = s
for f in glob.glob(os.path.join(day, 'nso', '*.json')):
    for r in json.load(open(f, encoding='utf-8'))['results']:
        p = r['phrase'].strip().lower(); nso[p] = max(nso[p], int(r['count']))
RULES = [  # порядок важен: первая сработавшая группа
 ('шум', r'\bмастило|\bмастить|песн|волшебник|мультик|фильм|сериал|книг|игр[аы]\b|аккорд|текст песни'),
 ('животные', r'собак|кош[кеи]|кот[аеу]?\b|котен|котят|щен|коров|тел[её]н|теля|коз[аы]|кролик|попуга|хомяк|свин|овц|лошад'),
 ('взрослые', r'желчн|мкб|карта вызова|зуб мудрости|в школе|взросл|мужчин|у женщин(?! после родов)|подростк|школьник|почечн|печеночн|печёночн|климакс'),
 ('беременность', r'беременн|при беременности|на \d+ неделе'),
 ('старше года', r'\b([2-9]|1[0-7])\s*(лет|года|год)\b|\b(\d+)\s*лет\b|полтора|1[,.]5 года|дошкольн'),
 ('навигация', r'новосибирск|москв|спб|петербург|екатеринбург|казан|красноярск|омск|самар|уф[аеы]\b|ростов|краснодар|челябинск|на дом|клиник|отзыв|запис[ьа]|телефон|адрес|госуслуг|бесплатно\b'),
 ('коммерция', r'купить|цена|стоимост|озон|ozon|wildberries|вайлдберриз|\bвб\b|аптек|интернет магазин|заказать'),
 ('бренд', r'комаровск'),
 ('лечение (вне границ)', r'\bот (кашля|поноса|рвоты|тошноты|колик|коликов|насморка|соплей|запора)|средств|микстур|ингаляц|биога|эффективн|сбить|сбивать|сбива|что дать|от температуры|\bчем\s+(лечить|сбить|сбивать|мазать|помазать|обработать|полоскать|капать|закапать|помочь|снять|убрать|вылечить|кормить при)|лечени|лечить|вылечить|дозировк|\bмг\b|мазь|мази|крем\b|капли|сироп|таблетк|свеч[иа]|антибиотик|препарат|лекарств|сколько давать|нурофен|парацетамол|ибупрофен|панадол|цефекон|амоксиклав|смект|энтерол|регидрон|эспумизан|бобот|саб симплекс|аквадетрим|вигантол|супрастин|зиртек|фенистил|адвантан|бепантен|пантенол|левомеколь|хлоргексидин|мирамистин|виферон|анаферон|деринат|називин|аквамарис|отипакс|ланолин|пурелан|народн'),
]
STOP = set('у в на при и или с со по для от до что как ли не а о об к ко из за под над без же бы то это'.split())
MOD = set('делать почему причина норма нормальный можно если сколько когда какой нужно надо бывать ребёнок ребенок грудничок новорождённый новорожденный младенец малыш дитя детский месяц неделя день год лет мес что то это быть есть весь очень сильно чтобы ли значит может мочь'.split())
def core(L): return frozenset(x for x in L if x not in MOD and not x.isdigit())
def lem(p): return frozenset(M.parse(w)[0].normal_form for w in re.findall(r'[а-яёa-z0-9]+', p) if w not in STOP)
def group(p):
    for g, rx in RULES:
        if re.search(rx, p): return g
    return 'в границах'
rows = []
for p, c in rf.items():
    if c < MIN: continue
    rows.append({'phrase': p, 'rf': c, 'nso': nso.get(p, 0), 'seed': seed_of[p], 'group': group(p), 'L': lem(p)})
for r in rows: r['C'] = core(r['L'])
rows.sort(key=lambda r: -r['rf'])
inscope = [r for r in rows if r['group'] == 'в границах']
heads, seen = [], set()
for r in inscope:
    if r['rf'] >= HEAD and r['C'] and r['C'] not in seen: heads.append(r); seen.add(r['C'])
for r in inscope:
    cand = [h for h in heads if h['C'] <= r['C']]
    best = max(cand, key=lambda h: (len(h['C']), h['rf'])) if cand else None
    r['head'] = best['phrase'] if best else '(без кандидата)'
with open(os.path.join(ROOT, 'zamery', 'z31-core.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['phrase', 'rf_30d', 'nso_30d', 'seed', 'group', 'article_head'])
    for r in rows: w.writerow([r['phrase'], r['rf'], r['nso'], r['seed'], r['group'], r.get('head', '')])
cl = collections.defaultdict(list)
for r in inscope: cl[r['head']].append(r)
with open(os.path.join(ROOT, 'zamery', 'z32-lex-clusters.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['seed', 'article_head', 'head_rf_30d', 'phrases', 'tail_rf_sum', 'top_tail'])
    for h in sorted(heads, key=lambda h: (h['seed'], -h['rf'])):
        t = [x for x in cl[h['phrase']] if x is not h]
        w.writerow([h['seed'], h['phrase'], h['rf'], len(t) + 1, sum(x['rf'] for x in t), ' | '.join(x['phrase'] for x in t[:6])])
g = collections.Counter(r['group'] for r in rows)
print(f'данные: {os.path.basename(day)}; фраз РФ всего {len(rf)}, с частотой >= {MIN}: {len(rows)}')
for k, v in g.most_common(): print(f'  {k}: {v}')
print(f'кандидатов в статьи (голова >= {HEAD}): {len(heads)}; фраз без кандидата: {len(cl["(без кандидата)"])}')
