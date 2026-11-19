"""Кластеризация запросов по совпадению выдачи Яндекса (топ-10 органики).
Правило: две фразы в одной статье, если у них >= MIN_COMMON общих URL в топ-10.
Метод: «жёсткий» кластер — каждая пара внутри кластера проходит порог (жадно, от самых частотных).
Вход: zamery/z12-serp-organic.csv (выдача), zamery/z04-direct-analysis.csv (частоты).
Выход: zamery/z30-serp-clusters.csv. Запуск: python3 -I dlya-mam/scripts/serp_cluster.py"""
import csv, os, collections, sys
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'zamery')
MIN_COMMON = int(sys.argv[1]) if len(sys.argv) > 1 else 3
import re
def key(q): return re.sub(r'[^а-яa-z0-9 ]','',q.lower().replace('ё','е')).replace('  ',' ').strip()
def norm(u): return u.split('?')[0].split('#')[0].rstrip('/').lower().replace('://www.', '://')
top = collections.defaultdict(set)
for r in csv.DictReader(open(os.path.join(D, 'z12-serp-organic.csv'), encoding='utf-8')):
    if int(r['pos']) <= 10 and r['url']: top[r['query']].add(norm(r['url']))
freq, grp = {}, {}
for r in csv.DictReader(open(os.path.join(D, 'z04-direct-analysis.csv'), encoding='utf-8')):
    for k in {key(r['phrase']), key(r['direct_phrase'])}:
        try: freq[k] = float(r['rf_requests'] or 0)
        except ValueError: freq[k] = 0
        grp[k] = (r['group'], r['job_id'], r['child_specific'])
F = lambda q: freq.get(key(q), freq.get(key(q).replace('ебенок','ребенок'), 0))
G = lambda q: grp.get(key(q), grp.get(key(q).replace('ебенок','ребенок'), ('', '', '')))
qs = sorted(top, key=lambda q: -F(q))
common = lambda a, b: len(top[a] & top[b])
left, clusters = list(qs), []
while left:
    head = left.pop(0); cl = [head]
    for q in list(left):
        if all(common(q, m) >= MIN_COMMON for m in cl): cl.append(q); left.remove(q)
    clusters.append(cl)
with open(os.path.join(D, 'z30-serp-clusters.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['cluster', 'head_query', 'query', 'group', 'job_id', 'rf_requests_month', 'common_with_head', 'cluster_size', 'cluster_rf_sum'])
    for i, cl in enumerate(sorted(clusters, key=lambda c: -sum(F(q) for q in c)), 1):
        s = sum(F(q) for q in cl)
        for q in cl:
            g = G(q)
            w.writerow([f'K{i:02d}', cl[0], q, g[0], g[1], int(F(q)), len(top[q] & top[cl[0]]), len(cl), int(s)])
multi = [c for c in clusters if len(c) > 1]
print(f'запросов с выдачей: {len(top)}; кластеров: {len(clusters)}; из них объединённых (>1 фразы): {len(multi)}; одиночек: {len(clusters)-len(multi)}')
for c in sorted(multi, key=lambda c: -len(c)): print(len(c), '|', ' / '.join(c))
