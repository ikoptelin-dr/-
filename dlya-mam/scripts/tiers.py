"""Порядок написания и рецензии: 300 статей → Tier 1–6 (месяц 1–6, по 50 статей).
Правило: хаб относится к своему месяцу по ценности для продукта и сезону; внутри — по спросу; переполнение уходит в следующий месяц.
Сезонные статьи (пик в дек–мар) поднимаются в Tier 1–2, чтобы выйти до пика. Выход: колонка tier в seo/05-karta-300.csv."""
import csv, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(ROOT, 'seo', '05-karta-300.csv')
HUB_TIER = {'Ночью и скорая': 1, 'Плач и поведение': 1, 'Температура': 1, 'Кашель и дыхание': 1, 'Нос, горло, уши, глаза': 1,
 'Живот и стул': 2, 'Новорождённый и уход': 3, 'Неврология и ортопедия': 3, 'Грудное вскармливание': 4, 'Искусственное вскармливание': 4,
 'Прикорм': 4, 'Развитие по месяцам': 5, 'Сон и режим': 5, 'Вес и рост': 5, 'Зубы и рот': 5, 'Кожа': 6, 'Прививки': 6, 'Анализы и показатели': 6}
ILL = {'Живот и стул', 'Кожа', 'Нос, горло, уши, глаза', 'Кашель и дыхание', 'Температура'}
WINTER = {'дек', 'янв', 'фев', 'мар'}
rows = list(csv.DictReader(open(P, encoding='utf-8')))
for r in rows:
    t = HUB_TIER[r['hub']]
    if t > 2 and r['hub'] in ILL and set(r.get('peak_months', '').split(', ')) & WINTER: t = 2
    r['_t'] = t
FIRST = {'Ночью и скорая', 'Плач и поведение'}  # продуктовые темы — первыми при любом спросе
rows.sort(key=lambda r: (r['_t'], r['hub'] not in FIRST, -int(r['demand_rf_30d'])))
for i, r in enumerate(rows):
    r['tier'] = min(6, i // 50 + 1); del r['_t']
rows.sort(key=lambda r: (r['tier'], -int(r['demand_rf_30d'])))
fields = [f for f in rows[0].keys()]
with open(P, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
import collections
for t in range(1, 7):
    x = [r for r in rows if r['tier'] == t]
    print(f'Tier {t}: {len(x)} статей, спрос {sum(int(r["demand_rf_30d"]) for r in x):,}', dict(collections.Counter(r['hub'] for r in x)))
