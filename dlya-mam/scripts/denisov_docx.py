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

R.update({
'ISPAD': 'ISPAD Clinical Practice Consensus Guidelines 2022 (сахарный диабет и диабетический кетоацидоз у детей). Pediatric Diabetes. 2022;23(7). https://www.ispad.org',
'WHOGROWTH': 'ВОЗ. Child Growth Standards (кривые роста). 2006. https://www.who.int/tools/child-growth-standards',
'NG75': 'NICE NG75. Faltering growth: recognition and management of faltering growth in children. 2017. https://www.nice.org.uk/guidance/ng75',
'NG1': 'NICE NG1. Gastro-oesophageal reflux disease in children and young people: diagnosis and management. 2015. https://www.nice.org.uk/guidance/ng1',
'CG99': 'NICE CG99. Constipation in children and young people: diagnosis and management. 2010. https://www.nice.org.uk/guidance/cg99',
'VITD': 'Национальная программа «Недостаточность витамина D у детей и подростков Российской Федерации: современные подходы к коррекции». Союз педиатров России, 2018 (сверить актуальную редакцию).',
'PROF': 'Приказ Минздрава России от 10.08.2017 № 514н «О Порядке проведения профилактических медицинских осмотров несовершеннолетних» (сверить действующую редакцию).',
'CDCMIL': 'Zubler J. M. et al. Evidence-Informed Milestones for Developmental Surveillance Tools. Pediatrics. 2022;149(3):e2021052138; CDC «Learn the Signs. Act Early». https://www.cdc.gov/ncbddd/actearly',
'NG224': 'NICE NG224. Urinary tract infection in under 16s: diagnosis and management. 2022. https://www.nice.org.uk/guidance/ng224',
'GINA': 'Global Initiative for Asthma (GINA). Global Strategy for Asthma Management and Prevention. 2024. https://ginasthma.org',
'KRGERD': 'Клинические рекомендации Минздрава России «Гастроэзофагеальная рефлюксная болезнь» (дети). https://cr.minzdrav.gov.ru — поиск по названию.',
'KRZAP': 'Клинические рекомендации Минздрава России «Запор» (дети). https://cr.minzdrav.gov.ru — поиск по названию.',
'KRANEM': 'Клинические рекомендации Минздрава России «Железодефицитная анемия». https://cr.minzdrav.gov.ru — поиск по названию.',
})
MAP.update({'D11': ['REC','ERC','AAPSLEEP'][:2], 'D12': ['REC','ISPAD','CG84'], 'D13': ['REC','WHOGROWTH','NG75'],
 'D14': ['REC','NG1','KRGERD','AAPSLEEP'], 'D15': ['REC','CG99','KRZAP'], 'D16': ['REC','VITD'],
 'D17': ['REC','PROF','CDCMIL','NG143'], 'D18': ['REC','PROF','KRANEM','NG224'], 'D19': ['REC','GINA','KRASTMA','NG9','ERC'],
 'D20': ['REC','NKP','MU','FZ157','FZ323','WHOVAX']})

R.update({
'KRLTI': 'Клинические рекомендации Минздрава России «Латентная туберкулёзная инфекция у детей» и «Туберкулёз у детей». https://cr.minzdrav.gov.ru — поиск по названию.',
'TBORD': 'Приказ Минздрава России от 21.03.2017 № 124н «Об утверждении порядка и сроков проведения профилактических медицинских осмотров граждан в целях выявления туберкулёза» (сверить действующую редакцию).',
'WHOTB': 'ВОЗ. Roadmap towards ending TB in children and adolescents, 3rd ed. 2023. https://www.who.int/publications',
'KRCROUP': 'Клинические рекомендации Минздрава России «Острый обструктивный ларингит [круп] и эпиглоттит у детей». https://cr.minzdrav.gov.ru — поиск по названию.',
'CKSCROUP': 'NICE Clinical Knowledge Summaries. Croup. https://cks.nice.org.uk/topics/croup/',
'NG240': 'NICE NG240. Meningitis (bacterial) and meningococcal disease: recognition, diagnosis and management. 2024. https://www.nice.org.uk/guidance/ng240',
'CG134': 'NICE CG134. Anaphylaxis: assessment and referral after emergency treatment. 2011. https://www.nice.org.uk/guidance/cg134',
'KRBURN': 'Клинические рекомендации Минздрава России «Ожоги термические и химические. Ожоги солнечные. Ожоги дыхательных путей». https://cr.minzdrav.gov.ru — поиск по названию.',
'CKSBURN': 'NICE Clinical Knowledge Summaries. Burns and scalds. https://cks.nice.org.uk/topics/burns-scalds/',
'AAPD': 'American Academy of Pediatric Dentistry. Policy on Early Childhood Caries; Guideline on Fluoride Therapy. https://www.aapd.org/research/oral-health-policies--recommendations/',
'FDATEETH': 'U.S. FDA. Safety communication: teething jewelry and benzocaine teething products (2018). https://www.fda.gov',
'PROGVSK': 'Программа оптимизации вскармливания детей первого года жизни в Российской Федерации. Союз педиатров России, 2019 (сверить актуальную редакцию).',
'WHOIYCF': 'ВОЗ. Infant and young child feeding (информационный бюллетень). https://www.who.int/news-room/fact-sheets/detail/infant-and-young-child-feeding',
'ESPGHAN': 'Fewtrell M. et al. Complementary Feeding: A Position Paper by the ESPGHAN Committee on Nutrition. J Pediatr Gastroenterol Nutr. 2017;64(1):119–132.',
'ABM36': 'Academy of Breastfeeding Medicine. Clinical Protocol #36: The Mastitis Spectrum. Breastfeed Med. 2022;17(5):360–376.',
'LACTMED': 'NIH. Drugs and Lactation Database (LactMed). https://www.ncbi.nlm.nih.gov/books/NBK501922/',
'WHOPIF': 'ВОЗ/ФАО. Safe preparation, storage and handling of powdered infant formula: guidelines. 2007. https://www.who.int/publications/i/item/9789241595414',
'TRTS033': 'Технический регламент Таможенного союза ТР ТС 033/2013 «О безопасности молока и молочной продукции» (в части детского питания) (сверить).',
})
MAP.update({'D21': ['REC','TBORD','KRLTI','WHOTB'], 'D22': ['REC','KRCROUP','CKSCROUP','NKP'], 'D23': ['REC','NG240','NG143','CG134'],
 'D24': ['ERC','KRBURN','CKSBURN'], 'D25': ['AAPSLEEP'], 'D26': ['REC','CG84','WHOORS','KRGE','NKP'], 'D27': ['REC','AAPD','FDATEETH'],
 'D28': ['REC','PROGVSK','WHOIYCF','ESPGHAN','ERC'], 'D29': ['REC','WHOIYCF','PROGVSK','ABM36','LACTMED','AAPSLEEP'], 'D30': ['REC','PROGVSK','WHOPIF','TRTS033']})

OUT = 'seo/articles/denisov/docx'; os.makedirs(OUT, exist_ok=True)
for f in sorted(glob.glob('seo/articles/denisov/D*.md')):
    t = open(f, encoding='utf-8').read(); aid = os.path.basename(f)[:3]
    m = re.match(r'---\n(.*?)\n---\n', t, re.S); fm = m.group(1); body = t[m.end():].lstrip()
    g = lambda k: (re.search(rf'^{k}:\s*"?(.*?)"?\s*$', fm, re.M) or [None, ''])[1]
    note = (f"*Статус: {g('status')}. Автор: {g('author')}. Рецензент: {g('reviewer')}. "
            "Текст написан от первого лица автора: прямые высказывания взяты из его записей, остальное подготовлено редакцией в его манере и публикуется только после его утверждения. Серый текст — дописано редакцией, чёрный — по записи автора. Пометка ⚑ — утверждение не сверено с источником; без сверки не публикуется.*\n\n")
    body = re.sub(r'^(# [^\n]*\n)', lambda mm: mm.group(1) + '\n' + note, body, count=1)
    refs = '\n\n## Источники\n\n' + '\n'.join(f'{i}. {R[k]}' for i, k in enumerate(MAP[aid], 1))
    refs += ('\n\n*Перечень составлен редакцией по пометкам ⚑ в таблице утверждений. Рецензент сверяет каждое '
             'утверждение с действующей редакцией документа и указывает номер версии российских клинических рекомендаций.*\n')
    tmp = os.path.join(TMP, aid + '.md'); open(tmp, 'w', encoding='utf-8').write(body + refs)
    subprocess.run(['pandoc', tmp, '--lua-filter=scripts/redakciya.lua', '--reference-doc=scripts/reference-redakciya.docx', '-o', f'{OUT}/{os.path.basename(f)[:-3]}.docx'], check=True)
    print(aid)
