"""D01–D10 -> docx с перечнем источников. Запуск: python3 -I scripts/denisov_docx.py <временная_папка> (из dlya-mam)."""
import re, glob, os, sys, subprocess
TMP = sys.argv[1]
R = {
'REC': 'Денисов М. Ю. Аудиозаписи для проекта «Для мам» (расшифровка; внутренний источник редакции, не публикуется).',
'NG143': 'NICE NG143. Fever in under 5s: assessment and initial management. 2019 (обновл. 2021). https://www.nice.org.uk/guidance/ng143',
'NG9': 'NICE NG9. Bronchiolitis in children: diagnosis and management. 2015 (обновл. 2021). https://www.nice.org.uk/guidance/ng9',
'NG91': 'NICE NG91. Otitis media (acute): antimicrobial prescribing. 2018. https://www.nice.org.uk/guidance/ng91',
'CG84': 'NICE CG84. Diarrhoea and vomiting caused by gastroenteritis in under 5s: diagnosis and management. 2009. https://www.nice.org.uk/guidance/cg84',
'CG98': 'NICE CG98. Jaundice in newborn babies under 28 days. 2010 (обновл. 2023). https://www.nice.org.uk/guidance/cg98',
'NG194': 'NICE NG194. Postnatal care. 2021. https://www.nice.org.uk/guidance/ng194',
'NG120': 'NICE NG120. Cough (acute): antimicrobial prescribing. 2019. https://www.nice.org.uk/guidance/ng120',
'CKS': 'NICE Clinical Knowledge Summaries. Colic — infantile. https://cks.nice.org.uk/topics/colic-infantile/',
'AAPBIL': 'Kemper A. R. et al. Clinical Practice Guideline Revision: Management of Hyperbilirubinemia in the Newborn Infant 35 or More Weeks of Gestation. Pediatrics. 2022;150(3):e2022058859.',
'AAPSLEEP': 'Moon R. Y. et al. Sleep-Related Infant Deaths: Updated 2022 Recommendations for Reducing Infant Deaths in the Sleep Environment. Pediatrics. 2022;150(1):e2022057990.',
'AAPOM': 'Lieberthal A. S. et al. The Diagnosis and Management of Acute Otitis Media. Pediatrics. 2013;131(3):e964–e999.',
'WHOORS': 'ВОЗ. The treatment of diarrhoea: a manual for physicians and other senior health workers. 2005. https://www.who.int/publications/i/item/9241593180',
'WHOPNC': 'ВОЗ. WHO recommendations on maternal and newborn care for a positive postnatal experience. 2022. https://www.who.int/publications/i/item/9789240045989',
'WHOVAX': 'ВОЗ. Vaccine Safety Basics: e-learning course. https://www.who.int/teams/regulation-prequalification/regulation-and-safety/pharmacovigilance/vaccine-safety-basics',
'ERC': 'European Resuscitation Council Guidelines 2021: Paediatric Life Support; First Aid. Resuscitation. 2021;161. https://cprguidelines.eu',
'KRORVI': 'Клинические рекомендации Минздрава России «Острая респираторная вирусная инфекция (ОРВИ)» (дети). Рубрикатор: https://cr.minzdrav.gov.ru — поиск по названию.',
'KROTIT': 'Клинические рекомендации Минздрава России «Отит средний острый». https://cr.minzdrav.gov.ru — поиск по названию.',
'KRASTMA': 'Клинические рекомендации Минздрава России «Бронхиальная астма». https://cr.minzdrav.gov.ru — поиск по названию.',
'KRBRON': 'Клинические рекомендации Минздрава России «Бронхит» и «Острый бронхиолит» (дети). https://cr.minzdrav.gov.ru — поиск по названию.',
'KRGE': 'Клинические рекомендации Минздрава России по острым кишечным инфекциям у детей (ротавирусная, норовирусная инфекция). https://cr.minzdrav.gov.ru — поиск по названию.',
'KRJAUN': 'Клинические рекомендации Минздрава России «Неонатальная желтуха». https://cr.minzdrav.gov.ru — поиск по названию.',
'NKP': 'Приказ Минздрава России от 06.12.2021 № 1122н «Об утверждении национального календаря профилактических прививок…» (сверить действующую редакцию).',
'FZ157': 'Федеральный закон от 17.09.1998 № 157-ФЗ «Об иммунопрофилактике инфекционных болезней».',
'FZ323': 'Федеральный закон от 21.11.2011 № 323-ФЗ «Об основах охраны здоровья граждан в Российской Федерации», ст. 20 (информированное добровольное согласие).',
'MU': 'МУ 3.3.1879-04 «Расследование поствакцинальных осложнений» (сверить действующую редакцию).',
}
MAP = {'D01': ['REC','NG143','KRORVI','ERC'], 'D02': ['REC','NG9','NG143','KRBRON','KRASTMA','ERC'],
       'D03': ['REC','CG84','WHOORS','KRGE','NG143','NKP'], 'D04': ['REC','NG91','AAPOM','KROTIT','NG143'],
       'D05': ['REC','CKS','AAPSLEEP'], 'D06': ['REC','WHOVAX','MU','NKP','FZ157','FZ323'],
       'D07': ['REC','CG98','AAPBIL','KRJAUN'], 'D08': ['REC','WHOPNC','NG194'],
       'D09': ['REC','KRORVI','AAPSLEEP'], 'D10': ['REC','NG120','NG143','KRASTMA','KRORVI']}
OUT = 'seo/articles/denisov/docx'; os.makedirs(OUT, exist_ok=True)
for f in sorted(glob.glob('seo/articles/denisov/D*.md')):
    t = open(f, encoding='utf-8').read(); aid = os.path.basename(f)[:3]
    m = re.match(r'---\n(.*?)\n---\n', t, re.S); fm = m.group(1); body = t[m.end():].lstrip()
    g = lambda k: (re.search(rf'^{k}:\s*"?(.*?)"?\s*$', fm, re.M) or [None, ''])[1]
    note = (f"*Статус: {g('status')}. Автор: {g('author')}. Рецензент: {g('reviewer')}. "
            "Текст написан от первого лица автора: прямые высказывания взяты из его записей, остальное подготовлено редакцией в его манере и публикуется только после его утверждения. Пометка ⚑ — утверждение не сверено с источником; без сверки не публикуется.*\n\n")
    body = re.sub(r'^(# [^\n]*\n)', lambda mm: mm.group(1) + '\n' + note, body, count=1)
    refs = '\n\n## Источники\n\n' + '\n'.join(f'{i}. {R[k]}' for i, k in enumerate(MAP[aid], 1))
    refs += ('\n\n*Перечень составлен редакцией по пометкам ⚑ в таблице утверждений. Рецензент сверяет каждое '
             'утверждение с действующей редакцией документа и указывает номер версии российских клинических рекомендаций.*\n')
    tmp = os.path.join(TMP, aid + '.md'); open(tmp, 'w', encoding='utf-8').write(body + refs)
    subprocess.run(['pandoc', tmp, '-o', f'{OUT}/{os.path.basename(f)[:-3]}.docx'], check=True)
    print(aid)
