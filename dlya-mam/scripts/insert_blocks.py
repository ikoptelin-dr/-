"""Вставляет дополнительные блоки в статьи перед '## Частые вопросы' и доп. FAQ перед '## Конспект'.
Формат файла дополнений: ===ID=== затем BODY, разделитель ---FAQ--- затем доп. вопросы."""
import sys, re, glob, os
src = open(sys.argv[1], encoding='utf-8').read()
for part in re.split(r'^===(D\d\d)===\n', src, flags=re.M)[1:]:
    pass
parts = re.split(r'^===(D\d\d)===\n', src, flags=re.M)
for i in range(1, len(parts), 2):
    aid, blk = parts[i], parts[i+1]
    body, faq = (blk.split('---FAQ---\n') + [''])[:2]
    f = glob.glob(f'seo/articles/denisov/{aid}-*.md')[0]
    t = open(f, encoding='utf-8').read()
    body = '::: {custom-style="Редакция"}\n' + body.strip() + '\n:::\n\n'
    t = t.replace('## Частые вопросы\n', body + '## Частые вопросы\n', 1)
    if faq.strip():
        t = t.replace('\n## Конспект\n', '\n::: {custom-style="Редакция"}\n' + faq.strip() + '\n:::\n\n## Конспект\n', 1)
    open(f, 'w', encoding='utf-8').write(t)
    print(aid, len(t.split()))
