"""Статьи 1–3 лет: общий каркас + своё содержание. Запуск: python3 -I dlya-mam/scripts/write_v13.py <файл_данных.py>"""
import os, sys, runpy
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
AUTH = 'Денисов Михаил Юрьевич, доктор медицинских наук профессор кафедры акушерства и гинекологии ИММТ НГУ'
def li(xs): return '\n'.join(f'- {x};' for x in xs[:-1]) + f'\n- {xs[-1]}.'
for a in runpy.run_path(sys.argv[1])['ART']:
    faq = '\n\n'.join(f'**{q}**\n{ans}' for q, ans in a['faq'])
    tab = '\n'.join(f'| {i} | {c} | {s} | {m} | |' for i, (c, s, m) in enumerate(a['claims'], 1))
    t = f"""---
id: {a['id']}
title: {a['title']}
url: {a['url']}
tz: seo/13/karta-13.csv
author: "{AUTH}"
reviewer: "{a.get('reviewer', '[ФИО, должность]')}"
reviewed: "[ДД.ММ.ГГГГ]"
status: черновик для рецензии
voice: {a.get('voice', 'текст редакции в голосе автора; записи по теме нет — автор перерабатывает')}
---

## Коротко

{a['short']}

## {a['sit_h']}

{a['sit']}

## Правило профессора

{a['rule']}

## Скорая сейчас, врач сегодня или наблюдаем дома

**Скорая сейчас — 103 или 112:** {a['ambulance']}

**К врачу:** {a['doctor']}

**Всё в порядке / наблюдаем дома:** {a['home']}

## Что можно сделать и чего делать нельзя

**Допустимо:**
{li(a['can'])}

**Нельзя:**
{li(a['cannot'])}

## Миф: «{a['myth_h']}»

{a['myth']}

## Частые вопросы

{faq}

## Конспект

{chr(10).join(f'{i}. {x}' for i, x in enumerate(a['summary'], 1))}

**Следующий шаг:** сохраните ночного помощника — бот подскажет, что нормально в возрасте вашего ребёнка.

## Таблица утверждений

| № | утверждение | источник | метка | решение рецензента |
|---|---|---|---|---|
{tab}
"""
    open(os.path.join(ROOT, 'seo', 'articles', 'v13', a['id'] + '.md'), 'w', encoding='utf-8').write(t)
    print(a['id'])
