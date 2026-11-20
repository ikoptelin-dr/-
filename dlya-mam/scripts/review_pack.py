"""Пакет на рецензию: статьи разложены по рецензентам. Запуск из dlya-mam/seo."""
import os,re,glob,shutil,csv
OUT='../REVIEW'; shutil.rmtree(OUT,ignore_errors=True)
def fm(t,k):
    m=re.search(rf'^{k}:\s*"?(.*?)"?\s*$',t,re.M); return m.group(1) if m else ''
files=sorted(glob.glob('articles/**/*.md',recursive=True)+glob.glob('pilot/*.md'))
files=[f for f in files if not os.path.basename(f).startswith('0')]
rows=[]
for f in files:
    t=open(f,encoding='utf-8').read(); rv=fm(t,'reviewer')+' '+fm(t,'reviewer_hint'); d=f.split('/')[-2]; b=os.path.basename(f)
    if 'дерматолог' in rv: g='05-дерматолог'
    elif 'гинеколог' in rv: g='06-гинеколог'
    elif 'юрист' in rv: g='07-юрист'
    elif 'психолог' in rv or 'логопед' in rv or 'ГВ' in rv: g='08-педиатр+психолог-логопед-ГВ'
    elif d=='pp': g='04-первая-помощь (инструктор ERC)'
    elif d=='v13': g='03-педиатр/03-дети-1-3-года'
    elif d=='denisov': g='02-проф-Денисов (по его записям)'
    elif d in('articles','pilot'): g='03-педиатр/00-неотложное-и-пилот'
    else: g=f'03-педиатр/{d.upper()}'
    os.makedirs(f'{OUT}/{g}',exist_ok=True); shutil.copy(f,f'{OUT}/{g}/{b}')
    flags=t.count('⚑'); rows.append([g,b,fm(t,'title'),fm(t,'status'),flags,rv.strip()])
os.makedirs(f'{OUT}/01-СНАЧАЛА-ПРОЧИТАТЬ',exist_ok=True)
for s in ['articles/00-README-i-test-mam.md','articles/01-voprosy-avtoru.md','sources/00-reestr-istochnikov.md','sources/01-tier1-spravki.md','voice/00-slovar-golosa.md','01-tz-shablon.md']:
    if os.path.exists(s): shutil.copy(s,f'{OUT}/01-СНАЧАЛА-ПРОЧИТАТЬ/')
with open(f'{OUT}/00-РЕЕСТР-РЕЦЕНЗИИ.csv','w',encoding='utf-8-sig',newline='') as h:
    w=csv.writer(h,delimiter=';'); w.writerow(['папка','файл','заголовок','статус','пометок ⚑','рецензент','решение','дата','ФИО рецензента']); w.writerows(rows)
from collections import Counter
c=Counter(r[0] for r in rows)
open(f'{OUT}/00-КАК-РЕЦЕНЗИРОВАТЬ.md','w',encoding='utf-8').write(f"""# Пакет на рецензию — проект «Для мам»

Всего статей: {len(rows)}. Все — **черновики**: ни одна не одобрена и не опубликована.

## Порядок
1. Папка `01-СНАЧАЛА-ПРОЧИТАТЬ`: вопросы автору Д1–Д18, реестр источников, словарь голоса.
2. Свою папку: каждая статья заканчивается **таблицей утверждений** — в колонке «решение рецензента» ставьте: принято / исправить / удалить.
3. Пометка ⚑ — источник не сверен; без сверки утверждение не публикуется.
4. Итог по статье — в `00-РЕЕСТР-РЕЦЕНЗИИ.csv` (открывается в Excel): решение, дата, ФИО.
5. Любая правка текста после одобрения отменяет одобрение — нужна новая рецензия.

## Папки
""" + '\n'.join(f'- `{k}` — {v}' for k,v in sorted(c.items())) + "\n\nСтатьи с двумя рецензентами (папки 05–08) сначала читает профильный специалист, затем педиатр.\n")
print(len(rows)); [print(k,v) for k,v in sorted(c.items())]
