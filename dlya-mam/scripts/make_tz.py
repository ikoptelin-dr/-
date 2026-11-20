"""ТЗ на каждую статью карты (seo/05-karta-300.csv) → seo/tz/T<tier>/<rank>-<slug>.md + seo/tz/00-index.csv.
Данные: z31-core (фразы и привязка к статье), склейки MERGE из article_map_auto.py, справки seo/sources.
Частые вопросы — реальные фразы Wordstat с вопросительными словами. Запуск: python3 -I dlya-mam/scripts/make_tz.py"""
import ast, csv, os, re, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
src = open(os.path.join(ROOT, 'scripts', 'article_map_auto.py'), encoding='utf-8').read()
m = re.search(r'MERGE = (\{.*?\n\})', src, re.S); MERGE = ast.literal_eval(m.group(1))
children = collections.defaultdict(list)
for k, v in MERGE.items():
    if k != v: children[v].append(k)
core = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(ROOT, 'zamery', 'z31-core.csv'), encoding='utf-8')):
    if r['group'] == 'в границах' and r['article_head']: core[r['article_head']].append((int(r['rf_30d']), r['phrase']))
art = list(csv.DictReader(open(os.path.join(ROOT, 'seo', '05-karta-300.csv'), encoding='utf-8')))
byhub = collections.defaultdict(list)
for a in art: byhub[a['hub']].append(a)
SRC = {  # хаб → (источники из реестра, справка Tier 1)
 'Температура': ('NICE-NG143, NICE-NG143-TL, RU-ORVI, PROF', 'С1'),
 'Ночью и скорая': ('PROF, NICE-NG143, NICE-NG9, RU-LARINGIT', 'С5'),
 'Кашель и дыхание': ('NICE-NG9, AAP-BRONCH-2014, RU-BRONCHIOLIT, RU-LARINGIT, RU-ORVI; RU-PNEUMO — сверить', 'С2'),
 'Нос, горло, уши, глаза': ('RU-ORVI; AAP-AOM-2013, RU-OTIT, RU-KONJ — сверить', 'С3'),
 'Плач и поведение': ('NICE-NG143; NICE-CKS — сверить', 'С4'),
 'Живот и стул': ('NICE-CG84; КР по кишечным инфекциям у детей — подобрать', ''),
 'Кожа': ('КР «Атопический дерматит» (Минздрав), КР «Крапивница» — подобрать и внести в реестр; NICE-NG143 (сыпь, не бледнеющая при надавливании)', ''),
 'Прививки': ('Национальный календарь профилактических прививок (приказ Минздрава — номер и редакцию внести в реестр); ВОЗ — позиционные документы по вакцинам', ''),
}
DEFAULT_SRC = ('источники подобрать до написания: КР Минздрава по теме, ВОЗ, NICE или AAP; внести в реестр', '')
NIGHT = {'Температура', 'Ночью и скорая', 'Кашель и дыхание', 'Нос, горло, уши, глаза', 'Плач и поведение', 'Живот и стул'}
QW = re.compile(r'\b(как|почему|можно ли|можно|когда|сколько|что делать|нужно ли|надо ли|стоит ли|во сколько|чем опасн|норма|что если|что значит)\b')
def slug(s):
    t = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', ''.join(t.get(c, c) for c in s.lower()))).strip('-')[:60]
os.makedirs(os.path.join(ROOT, 'seo', 'tz'), exist_ok=True)
idx = []
for a in art:
    h = a['article_head']; phr = sorted(core[h] + [p for c in children[h] for p in core[c]], reverse=True)
    phr = [p for p in phr if p[1] != h]
    faq = [p for p in phr if QW.search(p[1])][:8]
    sibl = [x['article_head'] for x in byhub[a['hub']] if x['article_head'] != h][:4]
    srcs, spr = SRC.get(a['hub'], DEFAULT_SRC)
    intent = 'ночь / симптом: «звонить или нет, что делать сейчас»' if a['hub'] in NIGHT else 'план: «как правильно, что нормально»'
    t = a['tier']; d = os.path.join(ROOT, 'seo', 'tz', f'T{t}'); os.makedirs(d, exist_ok=True)
    fn = f"{int(a['rank']):03d}-{slug(h)}.md"; path = os.path.join(d, fn)
    L = [f"# ТЗ: {h}", '', f"Tier {t} · хаб «{a['hub']}» · рецензент: {a['reviewer']} · статус: **ТЗ готово, статья не написана**", '',
         '| поле | значение |', '|---|---|',
         f"| Главный запрос | {h} |",
         f"| Спрос | {int(a['demand_rf_30d']):,} запросов за 30 дней, Россия, широкое соответствие (Wordstat, 2026-11-19); фраз в статье: {a['phrases']} |".replace(',', ' ', 1),
         f"| Сезон | пик: {a.get('peak_months') or 'нет данных'}; коэффициент {a.get('season_ratio') or '—'} |",
         f"| Намерение | {intent} |",
         f"| Склеенные дубли | {', '.join(children[h]) or '—'} |",
         f"| URL | /{slug(a['hub'])}/{slug(h)} |",
         '', '## Фразы для текста и подзаголовков (топ по частоте)', '']
    L += [f"- {p} — {n}" for n, p in phr[:15]] or ['- (хвост мал — опора на главный запрос)']
    L += ['', '## Частые вопросы мам (реальные фразы Wordstat → блок «Частые вопросы» и разметка FAQPage)', '']
    L += [f"- {p} — {n}" for n, p in faq] or ['- вопросы подобрать из подсказок «Люди ищут» при написании']
    L += ['', '## Разбор топ-10 Яндекса', '', '- заполнить при написании: тип каждого сайта (клиника, портал, аптека, производитель), есть ли автор-врач, рецензент, дата, блок «когда к врачу», ответ сразу; источник ответа Алисы', '- наше отличие: голос профессора, проверка рецензентом, «когда к врачу» в первом экране, конспект, без рекламы лекарств',
          '', '## План', '',
          '1. **Коротко** — ответ в 2–3 фразах (идёт в ответ Алисы и в бот)',
          '2. **Ситуация мамы** — узнавание, без страха', '3. **Главное правило** профессора',
          '4. **Когда скорая сразу / к врачу сегодня / наблюдаем дома** — одна формулировка с «Исходом»' if a['hub'] in NIGHT else '4. **Когда к врачу** — признаки, при которых нужен осмотр',
          '5. **Что можно сделать** и **чего делать нельзя**', '6. **Миф** — самое частое заблуждение по теме', '7. **Частые вопросы** — 4–6 из списка выше', '8. **Конспект** — 5–7 пунктов',
          '', '## Источники', '', f"- {srcs}", f"- справка: `seo/sources/01-tier1-spravki.md`, раздел {spr}" if spr else '- справка по теме — подготовить к своему Tier', '- только источники из `seo/sources/00-reestr-istochnikov.md`; статус «сверить» — не использовать до проверки',
          '', '## Запреты', '', '- названия лекарств, дозировки, схемы лечения, «чем лечить», «как сбить»', '- страх, ложная срочность, обещания «секретов врачей»', '- ругать врачей, форумы, других мам', '- выдуманные цифры, случаи, цитаты, источники', '- фото больных детей и лица детей',
          '', '## Перелинковка', '', f"- страница хаба «{a['hub']}»", *[f"- {s}" for s in sibl], '- кнопка «Сохранить ночного помощника» → бот с меткой статьи',
          '', '## Видео и карточка', '', '- подобрать карточку профессора из `shoot/` по теме; если записи нет — пометить «текст редакции, требует переработки профессором»',
          '', '## Сдача', '', '- статья + таблица утверждений (утверждение → источник → место → решение рецензента)', '- поля: автор, рецензент, дата проверки; разметка MedicalWebPage + FAQPage']
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    idx.append([t, a['rank'], a['hub'], h, a['reviewer'], a['demand_rf_30d'], f"seo/tz/T{t}/{fn}", 'ТЗ готово'])
with open(os.path.join(ROOT, 'seo', 'tz', '00-index.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['tier', 'rank', 'hub', 'article', 'reviewer', 'demand_rf_30d', 'tz_file', 'status']); w.writerows(sorted(idx, key=lambda x: (int(x[0]), int(x[1]))))
print('ТЗ:', len(idx), dict(collections.Counter(x[0] for x in idx)))
