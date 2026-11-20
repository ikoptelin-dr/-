"""Проверка статей seo/articles/*.md и сборка разметки JSON-LD (MedicalWebPage + FAQPage) в seo/articles/jsonld/.
Проверки: обязательные разделы; запрещённые слова (лекарства, «самка», гормоны, страх); длина предложений; наличие таблицы утверждений.
Запуск: python3 -I dlya-mam/scripts/article_check.py"""
import glob, json, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = os.path.join(ROOT, 'seo', 'articles'); os.makedirs(os.path.join(A, 'jsonld'), exist_ok=True)
NEED = ['## Коротко', '## Правило', 'Скорая сейчас', '## Что можно сделать', '## Миф', '## Частые вопросы', '## Конспект', '## Таблица утверждений', 'Следующий шаг']
BAN = r'нурофен|парацетамол|ибупрофен|панадол|цефекон|амоксиклав|смект|регидрон|эспумизан|бобот|аквадетрим|називин|отипакс|виферон|анаферон|деринат|аквамарис|\bмг\b|\bдозировк|самк|инстинкт обязыв|гормон|дофамин|окситоцин|кортизол|может убить|смертельн|секрет[ыа]? врач|срочно купите'
rep = []
for f in sorted([x for x in glob.glob(os.path.join(A, '*.md')) + glob.glob(os.path.join(A, 'denisov', '*.md')) + glob.glob(os.path.join(A, 't1', '*.md')) + glob.glob(os.path.join(A, 't2', '*.md')) + glob.glob(os.path.join(A, 't3', '*.md')) if not os.path.basename(x).startswith('0')]):
    t = open(f, encoding='utf-8').read(); name = os.path.basename(f)
    meta = dict(re.findall(r'^(\w+): (.*)$', t.split('---')[1], re.M))
    body = t.split('## Таблица утверждений')[0]
    miss = [n for n in NEED if n not in t]
    ban = sorted(set(m.group(0) for m in re.finditer(BAN, body.lower())))
    sents = [s for s in re.split(r'(?<=[.!?])\s+', re.sub(r'[#*|>-]', ' ', body.split('---', 2)[2])) if len(s.split()) > 3]
    long = sum(1 for s in sents if len(s.split()) > 25)
    claims = len(re.findall(r'^\| \d+ \|', t, re.M))
    faq_block = t.split('## Частые вопросы')[1].split('## Конспект')[0]
    qa = re.findall(r'\*\*(.+?\?)\*\*\s*\n(.+?)(?=\n\n|\Z)', faq_block, re.S)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "MedicalWebPage", "name": meta.get('title', ''), "inLanguage": "ru", "url": "https://for-mom.ru" + meta.get('url', ''),
         "audience": {"@type": "PeopleAudience", "audienceType": "Родители детей до года"},
         "author": {"@type": "Person", "name": meta.get('author', '').strip('"'), "affiliation": {"@type": "CollegeOrUniversity", "name": "Новосибирский государственный университет"}},
         "reviewedBy": {"@type": "Person", "name": meta.get('reviewer', '').strip('"')}, "lastReviewed": meta.get('reviewed', '').strip('"')},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q.strip(), "acceptedAnswer": {"@type": "Answer", "text": " ".join(a.split())}} for q, a in qa]}]}
    json.dump(ld, open(os.path.join(A, 'jsonld', name[:-3] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    words = len(re.findall(r'\w+', body))
    rep.append((name, words, len(qa), claims, long, miss, ban))
    print(f"{name:34} слов {words:4} | вопросов {len(qa)} | утверждений {claims:2} | длинных предлож. {long} | нет разделов: {miss or '—'} | запреты: {ban or '—'}")
bad = [r for r in rep if r[5] or r[6]]
print('ИТОГ:', len(rep), 'статей; с замечаниями:', len(bad))
