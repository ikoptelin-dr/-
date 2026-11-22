"""Заменяет тело статьи (от фронтматтера до «## Таблица утверждений») на чистовой текст из файла.
Запуск: python3 -I scripts/apply_clean.py <папка_с_чистовиками>  (файлы D11.md ...)"""
import sys, glob, os, re
src = sys.argv[1]
for p in sorted(glob.glob(os.path.join(src, 'D*.md'))):
    aid = os.path.basename(p)[:3]
    f = glob.glob(f'seo/articles/denisov/{aid}-*.md')[0]
    t = open(f, encoding='utf-8').read()
    m = re.match(r'(---\n.*?\n---\n)', t, re.S)
    fm = m.group(1).replace('version: 1 — от первого лица автора', 'version: 2 — чистовая редакция для автора')
    table = t[t.index('## Таблица утверждений'):]
    body = open(p, encoding='utf-8').read().strip()
    open(f, 'w', encoding='utf-8').write(fm + '\n' + body + '\n\n' + table)
    print(aid, len(body.split()))
