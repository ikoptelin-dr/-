"""Сезонность: помесячная динамика Wordstat (24 мес., РФ) по главной фразе каждой статьи из seo/03-karta-statej.csv.
Сырые ответы: inputs/wordstat/<дата>/dynamics/. Дописывает колонки в seo/03-karta-statej.csv.
Пиковые месяцы — по последним 12 полным месяцам; коэффициент = max/min за эти 12 месяцев."""
import csv, json, os, time, glob, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
day = sorted(glob.glob(os.path.join(ROOT, 'inputs', 'wordstat', '20*')))[-1]
dd = os.path.join(day, 'dynamics'); os.makedirs(dd, exist_ok=True)
MON = 'янв фев мар апр май июн июл авг сен окт ноя дек'.split()
path = os.path.join(ROOT, 'seo', '03-karta-statej.csv')
rows = list(csv.DictReader(open(path, encoding='utf-8')))
for r in rows:
    head = r['heads'].split(' | ')[0]; f = os.path.join(dd, head.replace(' ', '_') + '.json')
    if not os.path.exists(f):
        body = json.dumps({"phrase": head, "period": "PERIOD_MONTHLY", "fromDate": "2024-11-01T00:00:00Z", "toDate": "2026-10-31T23:59:59Z", "regions": ["225"], "devices": ["DEVICE_ALL"]}).encode()
        for a in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request("https://searchapi.api.cloud.yandex.net/v2/wordstat/dynamics", body, {"Content-Type": "application/json"}), timeout=60) as resp:
                    json.dump(json.load(resp), open(f, 'w', encoding='utf-8'), ensure_ascii=False); break
            except Exception as e: time.sleep(5 * (a + 1))
        time.sleep(1.5)
    try: res = json.load(open(f, encoding='utf-8'))['results'][-12:]
    except Exception: r['peak_months'] = r['season_ratio'] = 'нет данных'; continue
    c = [int(x['count']) for x in res]; m = [int(x['date'][5:7]) for x in res]
    top = sorted(range(12), key=lambda i: -c[i])[:2]
    r['season_ratio'] = round(max(c) / max(1, min(c)), 1); r['peak_months'] = ', '.join(MON[m[i] - 1] for i in sorted(top, key=lambda i: m[i]))
with open(path, 'w', newline='', encoding='utf-8') as fo:
    w = csv.DictWriter(fo, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('готово:', sum(1 for r in rows if r['peak_months'] != 'нет данных'), 'из', len(rows))
