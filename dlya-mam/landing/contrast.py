"""WCAG-контраст пар «текст/фон» для обеих тем лендинга. Запуск: python3 -I landing/contrast.py > landing/contrast-report.md"""
def lin(c):
    c/=255
    return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16) for i in (0,2,4)]
    return 0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b)
def ratio(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb); return (hi+0.05)/(lo+0.05)
L=dict(bg='#fff9f4',surface='#ffffff',surface2='#fef1e4',fg='#372c22',fg2='#4f453c',muted='#6b645d',coral='#ff8c6d',coral_ink='#372c22',
  accent='#b4482a',okbg='#dff2e1',okfg='#1f5a2c',wipbg='#ffe7b8',wipfg='#6b4300',planbg='#ece4dc',planfg='#4f453c',peach='#fed9b3',err='#b3261e',focus='#1c6fd1',field='#8a7a6c')
D=dict(bg='#1d1815',surface='#2a231f',surface2='#332a24',fg='#f6ede5',fg2='#e2d5c9',muted='#c2b3a6',coral='#ff8c6d',coral_ink='#2a1d14',
  accent='#ff9d82',okbg='#1f3a27',okfg='#bfe8c6',wipbg='#4a3510',wipfg='#ffd98a',planbg='#3a312b',planfg='#d9ccbf',peach='#fed9b3',err='#ff9d92',focus='#7db4ff',field='#a8937f')
pairs=[('Заголовок и текст','fg','bg',4.5),('Основной текст на карточке','fg2','surface',4.5),('Текст на карточке на тёмной плашке','fg2','surface2',4.5),
 ('Подписи (muted) на фоне','muted','bg',4.5),('Подписи (muted) на карточке','muted','surface',4.5),('Подписи (muted) на плашке','muted','surface2',4.5),
 ('Кнопка и пилюля: текст на коралловом','coral_ink','coral',4.5),('Ссылки и акцент-текст на фоне','accent','bg',4.5),('Ссылки на плашке','accent','surface2',4.5),
 ('Статус «есть»','okfg','okbg',4.5),('Статус «в работе»','wipfg','wipbg',4.5),('Статус «план»','planfg','planbg',4.5),
 ('Коралловая полоса: текст','#2a1d14','#ff8c6d',4.5),('Коралловая полоса: кнопка','#fff9f4','#2a1d14',4.5),('Коралловая полоса: кнопка к фону (не-текст)','#2a1d14','#ff8c6d',3.0),
 ('Ошибка формы на карточке','err','surface',4.5),('Номер шага: чернила на персиковом','#372c22','peach',4.5),
 ('Граница поля формы к карточке (не-текст)','field','surface',3.0),('Фокус к фону (не-текст)','focus','bg',3.0)]
def get(t,k): return t.get(k,k)
print("# Отчёт по контрасту\n\nДата: 2026-11-13. Метод: формула WCAG 2.x (относительная яркость sRGB). Порог: 4.5:1 для обычного текста, 3:1 для не-текста (границы, фокус). Считает `landing/contrast.py` по токенам из `index.html`.\n")
print("Статус: **ЗАМЕР по токенам**. Реальный рендер в браузере и проверку программой для чтения с экрана этот расчёт не заменяет.\n")
fails=0
for name,t in (('Светлая тема',L),('Тёмная тема',D)):
    print(f"## {name}\n\n| пара | текст | фон | контраст | порог | итог |\n|---|---|---|---:|---:|---|")
    for lab,fgk,bgk,th in pairs:
        a,b=get(t,fgk),get(t,bgk); r=ratio(a,b); ok=r>=th; fails+=0 if ok else 1
        print(f"| {lab} | `{a}` | `{b}` | {r:.2f} | {th} | {'проходит' if ok else '**не проходит**'} |")
    print()
print("## Что не проходит и что сделано\n")
print(f"- Не прошло пар: **{fails}**.")
print("- Исходный серый из скрина `#7f7972` на `#fff9f4`: %.2f (меньше 4.5). В лендинге заменён на `#6b645d` (%.2f), см. `tokens.json`." % (ratio('#7f7972','#fff9f4'),ratio('#6b645d','#fff9f4')))
print("- Коралловый `#ff8c6d` как цвет текста на светлом фоне не используется (%.2f); для текста-ссылок взят `#b4482a`." % ratio('#ff8c6d','#fff9f4'))
print("- Макет экрана пациента показан как на скрине, в обеих темах одинаково; его внутренние пары: чернила `#372c22` на `#fff9f4` = %.2f, подписи `#6b645d` = %.2f, чернила на коралловой пилюле = %.2f." % (ratio('#372c22','#fff9f4'),ratio('#6b645d','#fff9f4'),ratio('#372c22','#ff8c6d')))
