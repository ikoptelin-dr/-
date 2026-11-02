# Кластеры спроса — первый проход

Дата: 2026-11-02T08:18:38+00:00. Набор: `websearch_discovery_2026-11-02.json`.

**Что это.** Наблюдения по заголовкам и ссылкам реальных обсуждений, найденных веб-поиском. Тексты сообщений, комментарии, даты и реакции (кроме числа ответов в заголовках) не получены. Частота в выборке не равна объёму рынка; рост тем не оценивался.

## Объём выборки

- ссылок в наборе: 241; уникальных записей после точной дедупликации: 231
- близких повторов: 6; помечено как реклама/магазин/спам: 25
- сигналов спроса в кластерах (обсуждения, вопросы, отзывы): 122
- заблокированные поиски: S01 (API Error: 400 The following domains are not accessible to our user agent: ['reddit.com'])
- типы страниц: discussion 79, article_or_blog 39, question 38, shop_or_commercial 24, review 18, listing 9, news_event_edu 8, scientific 8, excluded_profile 4, excluded_third_party_tool 2, spam 1, excluded_mirror 1
- языки: en 105, ru 75, und 30, es 9, de 4, pt 2, fr 2, vi 1, id 1, uk 1, el 1

| Кластер | Обсуждений | Площадок | Языки | Уверенность |
|---|---|---|---|---|
| C01 Ретиноиды: как начать и что считать нормальной реакцией | 23 (основной: 23) | 5 | en 10, ru 10, de 3 | средняя |
| C06 Пилинги и микронидлинг: сочетание, интервалы, восстановление | 17 (основной: 8) | 6 | en 14, ru 3 | средняя |
| C07 Розацеа, покраснение и чувствительная кожа | 15 (основной: 9) | 5 | en 9, ru 6 | средняя |
| C02 Ниацинамид: переносимость и высыпания | 13 (основной: 13) | 3 | ru 8, en 5 | средняя |
| C11 Витамин C и азелаиновая кислота для чувствительной кожи | 13 (основной: 12) | 4 | en 12, ru 1 | средняя |
| C03 Пигментация и мелазма: что помогает и что может ухудшить | 12 (основной: 10) | 6 | en 8, ru 3, de 1 | средняя |
| C08 Акне и постакне | 12 (основной: 5) | 6 | en 7, ru 5 | средняя |
| C09 Биоревитализация, мезотерапия, PRP и экзосомы: «работает ли?» | 12 (основной: 12) | 3 | ru 9, en 3 | средняя |
| C04 Филлеры: отёк, бугорки и сроки восстановления | 11 (основной: 11) | 2 | en 9, ru 2 | низкая |
| C05 Ботулинотерапия: тяжесть бровей, птоз, отёки | 11 (основной: 11) | 2 | en 8, ru 3 | низкая |
| C10 Солнцезащита: выбор SPF, белый след, сочетание с активами | 3 (основной: 3) | 1 | en 3 | низкая |
| C12 Пробиотики и лизаты в косметике: есть ли эффект | 3 (основной: 3) | 1 | ru 3 | низкая |
| C13 Самостоятельные инъекции и «домашние» процедуры | 1 (основной: 1) | 1 | ru 1 | низкая |

## C01. Ретиноиды: как начать и что считать нормальной реакцией

**Наблюдения.**

- обсуждений: 23, площадок: 5 (kosmetista_ru 9, acne_org 8, web:medpex.de 3, woman_ru 2, realself 1)
- аудитория: consumer 19, unknown 3, consumer_question_pro_answer 1
- период: дата известна у 0, неизвестна у 23
- что хотят: описывают проблему или нежелательную реакцию: 7 из 23; задают прямой вопрос: 6 из 23; ищут результат или способ решения: 2 из 23; сомневаются, работает ли это / не обман ли: 1 из 23

Примеры:

- [Ретиноевый пилинг,где же результат?](https://www.woman.ru/beauty/face/thread-retinoeviy-piling-gde-zhe-rezultat-id3861784/) · woman_ru · ru — ответов: 68
- [Использование ретинола в уходе за кожей. Ваш опыт](https://www.woman.ru/beauty/face/thread/5743923/) · woman_ru · ru — ответов: 25
- [Red Marks From Initial Break Out On Tretinoin](https://www.acne.org/forums/79-hyperpigmentation-reddark-marks/328368-red-marks-from-initial-break-out-on-tretinoin) · acne_org · en
- [Tretinoin, 8 Week, Flaming Red Face](https://acne.org/forums/topic/331411-tretinoin-8-week-flaming-red-face) · acne_org · en
- [Retin-A Cream 0.025% Cream](https://www.acne.org/forums/4-prescription-acne-medications/332607-retin-a-cream-0025-cream) · acne_org · en
- [14 Weeks Of Tretinoin. No Improvement. (Pictures Included)](https://www.acne.org/forums/4-prescription-acne-medications/338876-14-weeks-of-tretinoin-no-improvement-pictures-included) · acne_org · en
- [Tretinoin is KILLING my skin](https://www.acne.org/forums/4-prescription-acne-medications/356715-tretinoin-is-killing-my-skin) · acne_org · en
- [Current Tretinoin Users](https://www.acne.org/forums/4-prescription-acne-medications/358945-current-tretinoin-users) · acne_org · en

**Гипотезы (не наблюдения).**

- тема публикации: Раздражение или «пурджинг»: как различать и когда остановиться
- тема публикации: Ретинол, ретиналь, третиноин: в чём разница для кожи и для рецепта
- исследовательский вопрос: Сколько длится и как выглядит ретиноидный дерматит при начале терапии, и какие схемы старта снижают раздражение?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C06. Пилинги и микронидлинг: сочетание, интервалы, восстановление

**Наблюдения.**

- обсуждений: 17, площадок: 6 (realself 12, acne_org 1, kosmetista_ru 1, otzovik 1, sephora_community 1, woman_ru 1)
- аудитория: consumer_question_pro_answer 12, consumer 5
- период: дата известна у 0, неизвестна у 17
- что хотят: задают прямой вопрос: 5 из 17; ищут результат или способ решения: 2 из 17; сомневаются, работает ли это / не обман ли: 2 из 17

Примеры:

- [Ретиноевый пилинг,где же результат?](https://www.woman.ru/beauty/face/thread-retinoeviy-piling-gde-zhe-rezultat-id3861784/) · woman_ru · ru — ответов: 68
- [384275 question about microneedling peels](https://www.acne.org/forums/topic/384275-question-about-microneedling-peels) · acne_org · en
- [Про спикулы и ретинол: крем и сыворотка от Celimax, которые стоит попробовать](https://kosmetista.ru/blog/156135-pro-spikuly-i-retinol-krem-i-syvorotka-ot-celimax.html) · kosmetista_ru · ru
- [Отзыв о Сыворотка-эксфолиант с экзосомами для лица Dr.Melaxin Exosome Peeling Serum](https://otzovik.com/review_17717782.html) · otzovik · ru
- [california ca peels immediately after microneedling](https://www.realself.com/question/california-ca-peels-immediately-after-microneedling) · realself · en
- [Is it ok to get Botox 2 days after getting a Chemical Peel?](https://www.realself.com/question/chandler-az-botox-days-after-chemical-peel) · realself · en
- [Chemical Peel 1 week before Botox ok?](https://www.realself.com/question/chemical-peel-week-b4-botox) · realself · en
- [jackson ms perform chemical peel weeks before weeks after microneedling](https://www.realself.com/question/jackson-ms-perform-chemical-peel-weeks-before-weeks-after-microneedling) · realself · en

**Гипотезы (не наблюдения).**

- тема публикации: Пилинг и микронидлинг: что известно об интервалах между процедурами
- исследовательский вопрос: Какие данные есть о безопасных интервалах и сочетании химических пилингов, микронидлинга и инъекций?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C07. Розацеа, покраснение и чувствительная кожа

**Наблюдения.**

- обсуждений: 15, площадок: 5 (sephora_community 4, acne_org 3, doctu_ru 3, kosmetista_ru 3, gopicky 2)
- аудитория: consumer 12, consumer_question_pro_answer 3
- период: дата известна у 0, неизвестна у 15
- что хотят: задают прямой вопрос: 8 из 15; описывают проблему или нежелательную реакцию: 3 из 15; ищут результат или способ решения: 2 из 15

Примеры:

- [The seborrheic dermatitis thread](https://www.acne.org/forums/52-rosacea-facial-redness/237402-the-seborrheic-dermatitis-thread/paged/2) · acne_org · en
- [Tretinoin, 8 Week, Flaming Red Face](https://acne.org/forums/topic/331411-tretinoin-8-week-flaming-red-face) · acne_org · en
- [REDNESS ON CHEEKS](https://www.acne.org/forums/52-rosacea-facial-redness/361515-redness-on-cheeks) · acne_org · en
- [Что делать с постоянным красным пятном на носу?](https://doctu.ru/consult/question/chto-delat-s-postojannym-krasnym-pjatnom-na-nosu) · doctu_ru · ru — ответов: 2
- [Что может означать белый носогубный треугольник и красные крылья носа?](https://doctu.ru/consult/question/chto-mozhet-oznachat-belyjj-nosogubnyjj-treugolnik-i-krasnye-krylja-nosa) · doctu_ru · ru — ответов: 2
- [Можно ли посещать баню при розацеа или прыщах?](https://doctu.ru/consult/question/mozhno-li-poseshhat-banju-pri-rozacea-ili-pryshhakh) · doctu_ru · ru — ответов: 2
- [Why my skin can't handle niacinamide?](https://www.gopicky.com/discussion/2955/why-my-skin-can-t-handle-niacinamide) · gopicky · en
- [Шелушения на коже. Как убрать?](https://kosmetista.ru/blog/chillout/129003-shelusheniya-na-kozhe-kak-ubrat.html) · kosmetista_ru · ru

**Гипотезы (не наблюдения).**

- тема публикации: Розацеа и уход: какие активы обсуждают и что о них известно
- исследовательский вопрос: Какие местные средства и уход имеют доказательства при розацеа и что может ухудшать покраснение?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C02. Ниацинамид: переносимость и высыпания

**Наблюдения.**

- обсуждений: 13, площадок: 3 (kosmetista_ru 8, acne_org 3, gopicky 2)
- аудитория: consumer 13
- период: дата известна у 0, неизвестна у 13
- что хотят: описывают проблему или нежелательную реакцию: 5 из 13; задают прямой вопрос: 4 из 13; сомневаются, работает ли это / не обман ли: 3 из 13; ищут результат или способ решения: 1 из 13

Примеры:

- [beware niacinamide in new moisturizer](https://www.acne.org/forums/18-acneorg-products/beware-niacinamide-in-new-moisturizer) · acne_org · en
- [warning niacinamide in aha now](https://www.acne.org/forums/18-acneorg-products/warning-niacinamide-in-aha-now) · acne_org · en
- [252903 roll your own nicomide](https://www.acne.org/forums/37-adult-acne/252903-roll-your-own-nicomide) · acne_org · en
- [Why my skin can't handle niacinamide?](https://www.gopicky.com/discussion/2955/why-my-skin-can-t-handle-niacinamide) · gopicky · en
- [Кожа не любит ниацинамид?](https://kosmetista.ru/blog/chillout/139137-kozha-ne-lyubit-niacinamid.html) · kosmetista_ru · ru
- [Ниацинамид, который работает - Face Serum Sebum от Filosofie](https://kosmetista.ru/blog/153637-niacinamid-kotoryj-rabotaet-face-serum-sebum-ot-fi.html) · kosmetista_ru · ru
- [Невидимый результат: Seveki Мультифункциональная сыворотка для лица с ниацинамидом 5%](https://kosmetista.ru/blog/157715-nevidimyj-rezultat-seveki-multifunkcionalnaya-syvo.html) · kosmetista_ru · ru
- [Спорная сыворотка Ниацинамид Seveki](https://kosmetista.ru/blog/165094-spornaya-syvorotka-niacinamid-seveki.html) · kosmetista_ru · ru

**Гипотезы (не наблюдения).**

- тема публикации: Почему одна сыворотка с ниацинамидом «работает», а другая нет: концентрация, формула, ожидания
- исследовательский вопрос: Связан ли местный ниацинамид с раздражением или высыпаниями и от чего это зависит?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C11. Витамин C и азелаиновая кислота для чувствительной кожи

**Наблюдения.**

- обсуждений: 13, площадок: 4 (acne_org 6, sephora_community 5, gopicky 1, kosmetista_ru 1)
- аудитория: consumer 13
- период: дата известна у 0, неизвестна у 13
- что хотят: задают прямой вопрос: 6 из 13; ищут результат или способ решения: 1 из 13; описывают проблему или нежелательную реакцию: 1 из 13; сомневаются, работает ли это / не обман ли: 1 из 13

Примеры:

- [Finacea : Azelaic Acid (15%) Gel](https://www.acne.org/reviews/azelaic-acid-15-gel-reviews-873/2?filters%5B0%5D=star_5) · acne_org · en
- [Azelex : Azelaic Acid (20%) Cream](https://www.acne.org/reviews/azelaic-acid-20-cream-reviews-23/18) · acne_org · en
- [Skinoren : Azelaic Acid (20%) Cream](https://www.acne.org/reviews/azelaic-acid-20-cream-reviews-338/2?filters%5B%5D=star_5) · acne_org · en
- [Azelaic Acid](https://www.acne.org/forums/52-rosacea-facial-redness/306205-azelaic-acid) · acne_org · en
- [My (Loooong) Story And Azelaic Acid For Severe Oily Skin](https://www.acne.org/forums/74-oily-skin/330691-my-loooong-story-and-azelaic-acid-for-severe-oily-skin) · acne_org · en
- [Who has successfully used azelaic acid?](https://www.acne.org/forums/3-over-the-counter-acne-medications-and-products/386534-who-has-successfully-used-azelaic-acid) · acne_org · en
- [Супер-средство или провал? Крем-сыворотка для лица Compliment Обновляющая Ниацинамид + Витамин С](https://kosmetista.ru/blog/170482-krem-syvorotka-dlya-lica-compliment-obnovlyayushay.html) · kosmetista_ru · ru
- [Best vitamin c serum??](https://community.sephora.com/t5/Acne-Prone-Skin/Best-vitamin-c-serum/m-p/6467921) · sephora_community · en

**Гипотезы (не наблюдения).**

- тема публикации: Азелаиновая кислота: при каких задачах её обсуждают и что известно
- исследовательский вопрос: Что известно об эффективности и переносимости азелаиновой кислоты и местного витамина C при чувствительной коже, розацеа и акне?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C03. Пигментация и мелазма: что помогает и что может ухудшить

**Наблюдения.**

- обсуждений: 12, площадок: 6 (realself 6, acne_org 2, doctu_ru 1, health_mail_ru 1, web:medpex.de 1, woman_ru 1)
- аудитория: consumer_question_pro_answer 8, consumer 3, unknown 1
- период: дата известна у 1, неизвестна у 11
- что хотят: задают прямой вопрос: 7 из 12; описывают проблему или нежелательную реакцию: 3 из 12; ищут результат или способ решения: 2 из 12; сомневаются, работает ли это / не обман ли: 1 из 12

Примеры:

- [Крем от ПИГМЕНТАЦИИ](https://www.woman.ru/beauty/face/thread/4236226/) · woman_ru · ru — ответов: 129
- [Acne PIE](https://www.acne.org/forums/79-hyperpigmentation-reddark-marks/acne-pie) · acne_org · en
- [Red Marks From Initial Break Out On Tretinoin](https://www.acne.org/forums/79-hyperpigmentation-reddark-marks/328368-red-marks-from-initial-break-out-on-tretinoin) · acne_org · en
- [Как избавиться от пигментации после депиляции воском?](https://doctu.ru/consult/question/kak-izbavitsja-ot-pigmentacii-posle-depiljacii-voskom) · doctu_ru · ru — ответов: 2
- [Пигментные пятна на лице - Дерматология и косметология - 18 августа 2013 - Здоровье Mail](https://health.mail.ru/consultation/882830/) · health_mail_ru · ru
- [I'm 49 and have severe melasma. I have tried three halo lasers that made it so much worse. What to try now? (photo)](https://www.realself.com/question/49-severe-melasma-halo-lasers-worse-years-prior-peels) · realself · en
- [Tough melasma. Can I use Lytera 2.0 and Hydroquinone to treat it? (Photo)](https://www.realself.com/question/dallas-tx-tough-melasma) · realself · en
- [Please, help me with my horrific melasma. (Photo)](https://www.realself.com/question/el-paso-tx-horrific-malasma) · realself · en

**Гипотезы (не наблюдения).**

- тема публикации: Почему лазер иногда ухудшает мелазму
- тема публикации: Гидрохинон и альтернативы: что известно о пользе и рисках
- исследовательский вопрос: Какие методы лечения мелазмы имеют доказательства пользы, и при каких вмешательствах описано ухудшение?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C08. Акне и постакне

**Наблюдения.**

- обсуждений: 12, площадок: 6 (acne_org 5, gopicky 2, woman_ru 2, doctu_ru 1, kosmetista_ru 1, pikabu 1)
- аудитория: consumer 10, consumer_question_pro_answer 1, mixed 1
- период: дата известна у 0, неизвестна у 12
- что хотят: описывают проблему или нежелательную реакцию: 6 из 12; задают прямой вопрос: 3 из 12; ищут результат или способ решения: 1 из 12

Примеры:

- [Акне. Ничего не помогает!](https://www.woman.ru/beauty/face/thread/5003457/) · woman_ru · ru — ответов: 34
- [Лечение постакне](https://www.woman.ru/beauty/face/thread-lechenie-postakne-id6260885/) · woman_ru · ru — ответов: 17
- [Acne PIE](https://www.acne.org/forums/79-hyperpigmentation-reddark-marks/acne-pie) · acne_org · en
- [Red Marks From Initial Break Out On Tretinoin](https://www.acne.org/forums/79-hyperpigmentation-reddark-marks/328368-red-marks-from-initial-break-out-on-tretinoin) · acne_org · en
- [Tretinoin making acne worse? PLEASE HELP](https://www.acne.org/forums/4-prescription-acne-medications/364390-tretinoin-making-acne-worse-please-help) · acne_org · en
- [Skin purging 3 months into tretinoin?](https://www.acne.org/forums/4-prescription-acne-medications/367304-skin-purging-3-months-into-tretinoin) · acne_org · en
- [Можно ли посещать баню при розацеа или прыщах?](https://doctu.ru/consult/question/mozhno-li-poseshhat-banju-pri-rozacea-ili-pryshhakh) · doctu_ru · ru — ответов: 2
- [Cycle Breakout](https://www.gopicky.com/discussion/41804/cycle-breakout) · gopicky · en

**Гипотезы (не наблюдения).**

- тема публикации: Почему «ничего не помогает» при акне: ожидания, сроки, когда к врачу
- тема публикации: Красные и тёмные следы после акне: в чём разница
- исследовательский вопрос: Какие сроки ответа на типовые схемы лечения акне описаны и чем различаются поствоспалительная эритема и гиперпигментация?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C09. Биоревитализация, мезотерапия, PRP и экзосомы: «работает ли?»

**Наблюдения.**

- обсуждений: 12, площадок: 3 (otzovik 5, woman_ru 4, realself 3)
- аудитория: consumer 9, consumer_question_pro_answer 3
- период: дата известна у 0, неизвестна у 12
- что хотят: сомневаются, работает ли это / не обман ли: 2 из 12; ищут результат или способ решения: 1 из 12; задают прямой вопрос: 1 из 12

Примеры:

- [Вся правда о БИОРЕВИТАЛИЗАЦИИ или как нас обманывают!](https://woman.ru/beauty/plastic/thread/4119901/85) · woman_ru · ru — ответов: 5516
- [Биоревитализация - отзывы...](https://woman.ru/beauty/medley2/thread/4157683/21) · woman_ru · ru — ответов: 1060
- [Кто делал мезонити? Отзывы](https://www.woman.ru/beauty/plastic/thread-kto-delal-mezoniti-otzyvy-id4454589/5/) · woman_ru · ru — ответов: 864
- [Мезотерапия лица отзывы](https://www.woman.ru/beauty/face/thread/4785707/2/) · woman_ru · ru — ответов: 67
- [Отзыв о Мезотерапия для волос с экзосомами ASCE+ HRLV](https://otzovik.com/review_12511412.html) · otzovik · ru
- [Отзыв о Косметологическая процедура GiGi "Биоплазма"](https://otzovik.com/review_12743834.html) · otzovik · ru
- [Отзыв о Сыворотка-эксфолиант с экзосомами для лица Dr.Melaxin Exosome Peeling Serum](https://otzovik.com/review_17717782.html) · otzovik · ru
- [Отзыв о Плазмолифтинг](https://otzovik.com/review_2894717.html) · otzovik · ru

**Гипотезы (не наблюдения).**

- тема публикации: Биоревитализация и мезотерапия: что известно о пользе, а что — маркетинг
- тема публикации: Экзосомы в косметологии: стадия доказательств
- исследовательский вопрос: Какие клинические доказательства есть у биоревитализации, мезотерапии, PRP и экзосом для кожи лица и каковы риски?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C04. Филлеры: отёк, бугорки и сроки восстановления

**Наблюдения.**

- обсуждений: 11, площадок: 2 (realself 9, woman_ru 2)
- аудитория: consumer_question_pro_answer 9, consumer 2
- период: дата известна у 0, неизвестна у 11
- что хотят: задают прямой вопрос: 9 из 11; описывают проблему или нежелательную реакцию: 7 из 11

Примеры:

- [Филлеры для носогубок.](https://www.woman.ru/beauty/plastic/thread-fillery-dlya-nosogubok-id4313068/4/) · woman_ru · ru — ответов: 283
- [Увеличение подбородка филлером](https://www.woman.ru/beauty/plastic/thread/4702771/) · woman_ru · ru — ответов: 17
- [How long after lip fillers should they look and feel normal? (Photos)](https://www.realself.com/question/cannock-ws12-long-after-lip-fillers-after-feel-normal) · realself · en
- [I had lip fillers 5 days ago and my lips feel tight and sore. What do you recommend? (Photos)](https://www.realself.com/question/coventry-gb-i-lip-fillers-days-lips-feel-tight-sore) · realself · en
- [1 day post op lip filler, my lips are now swelling! Is this normal? (photos)](https://www.realself.com/question/douglas-park-au-lip-filler-swelling) · realself · en
- [First time lip fillers, help. Will this go down more in the next couple of days?](https://www.realself.com/question/dunedin-fl-time-lip-fillers) · realself · en
- [How long does cheek filler swelling take to go down and is this normal? (photo)](https://www.realself.com/question/glasgow-gb-long-cheek-filler-swelling-normal) · realself · en
- [I got Hyaluronidase to dissolve my lip fillers. My lips are huge and swollen huge. Is this normal? What do I do? (Photo)](https://www.realself.com/question/hyaluronidase-dissolve-lip-fillers-swollen-huge-normal) · realself · en

**Гипотезы (не наблюдения).**

- тема публикации: Отёк после филлера губ: какие сроки описаны и какие признаки требуют врача
- исследовательский вопрос: Каковы описанные сроки и частота отёка и узелков после введения гиалуроновых филлеров губ, и какие признаки осложнений требуют срочной помощи?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C05. Ботулинотерапия: тяжесть бровей, птоз, отёки

**Наблюдения.**

- обсуждений: 11, площадок: 2 (realself 8, doctu_ru 3)
- аудитория: consumer_question_pro_answer 11
- период: дата известна у 0, неизвестна у 11
- что хотят: задают прямой вопрос: 11 из 11; описывают проблему или нежелательную реакцию: 6 из 11; ищут результат или способ решения: 1 из 11

Примеры:

- [Что делать при птозе верхнего века после ботокса?](https://doctu.ru/consult/question/chto-delat-pri-ptoze-verkhnego-veka-posle-botoksa-2) · doctu_ru · ru — ответов: 2
- [Какая связь между аллергией и инъекциями ботокса?](https://doctu.ru/consult/question/kakaja-svjaz-mezhdu-allergiejj-i-inekcijami-botoksa) · doctu_ru · ru — ответов: 2
- [Почему после ботокса возникли отеки?](https://doctu.ru/consult/question/pochemu-posle-botoksa-voznikli-oteki) · doctu_ru · ru — ответов: 2
- [It's a week after my Botox, and I feel I am scowling all of the time as if I can't relax. Can this be fixed? (Photo)](https://www.realself.com/question/asbury-park-nj-week-after-botox-feel-scowling-time-relax-fixed) · realself · en
- [Botox and emotion: heavy feeling in the forehead -- when will this wear off?](https://www.realself.com/question/calabasas-ca-botox-emotionheavy-feeling-forehead) · realself · en
- [Is it ok to get Botox 2 days after getting a Chemical Peel?](https://www.realself.com/question/chandler-az-botox-days-after-chemical-peel) · realself · en
- [Chemical Peel 1 week before Botox ok?](https://www.realself.com/question/chemical-peel-week-b4-botox) · realself · en
- [Botox: eyes feel heavy, my eyebrows are different? (Photo)](https://www.realself.com/question/michigan-mi-botox-eyes-feel-heavy-eyebrows) · realself · en

**Гипотезы (не наблюдения).**

- тема публикации: Тяжесть во лбу и опущение брови после ботулинотерапии: почему бывает и сколько длится
- исследовательский вопрос: Как часто встречаются птоз и тяжесть бровей после ботулинотерапии верхней трети лица и сколько они длятся?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался.

## C10. Солнцезащита: выбор SPF, белый след, сочетание с активами

**Наблюдения.**

- обсуждений: 3, площадок: 1 (gopicky 3)
- аудитория: consumer 3
- период: дата известна у 0, неизвестна у 3
- что хотят: задают прямой вопрос: 2 из 3; ищут результат или способ решения: 1 из 3; описывают проблему или нежелательную реакцию: 1 из 3

Примеры:

- [Mineral Sunscreen](https://www.gopicky.com/discussion/78020/mineral-sunscreen) · gopicky · en
- [Has anyone switched from a chemical suns...](https://www.gopicky.com/discussion/20951/has-anyone-switched-from-a-chemical-sunscreen-to-a-mineral-one-and-seen-any-improvements) · gopicky · en _(заголовок из URL)_
- [Does anyone else experience a slight whi...](https://www.gopicky.com/discussion/71389/does-anyone-else-experience-a-slight-white-cast-when-using-the-skin1004-sun-serum) · gopicky · en _(заголовок из URL)_

**Гипотезы (не наблюдения).**

- тема публикации: Минеральный или химический SPF: что важно для чувствительной и тёмной кожи
- исследовательский вопрос: Какие данные есть о переносимости и приверженности разным типам солнцезащитных средств?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался; один источник — тема может отражать особенность площадки.

## C12. Пробиотики и лизаты в косметике: есть ли эффект

**Наблюдения.**

- обсуждений: 3, площадок: 1 (kosmetista_ru 3)
- аудитория: consumer 3
- период: дата известна у 0, неизвестна у 3
- что хотят: 

Примеры:

- [137393 lysaterica serum probiotiki dlya krasoty zdorovya](https://kosmetista.ru/blog/137393-lysaterica-serum-probiotiki-dlya-krasoty-zdorovya.html) · kosmetista_ru · ru
- [149979 syvorotka s probiotikami ma nyo bifida biome compl](https://kosmetista.ru/blog/149979-syvorotka-s-probiotikami-ma-nyo-bifida-biome-compl.html) · kosmetista_ru · ru
- [170304 syvorotka dlya lica thinkco pure bifida uvlazhnyay](https://kosmetista.ru/blog/170304-syvorotka-dlya-lica-thinkco-pure-bifida-uvlazhnyay.html) · kosmetista_ru · ru

**Гипотезы (не наблюдения).**

- тема публикации: Лизаты бифидобактерий в косметике: что заявляют и что проверено
- исследовательский вопрос: Какие клинические данные есть о местном применении лизатов и пробиотиков в косметике?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался; один источник — тема может отражать особенность площадки.

## C13. Самостоятельные инъекции и «домашние» процедуры

**Наблюдения.**

- обсуждений: 1, площадок: 1 (woman_ru 1)
- аудитория: consumer 1
- период: дата известна у 0, неизвестна у 1
- что хотят: 

Примеры:

- [Инъекции самой себе](https://www.woman.ru/beauty/plastic/thread/4657582/) · woman_ru · ru — ответов: 54

**Гипотезы (не наблюдения).**

- тема публикации: Почему инъекции «самой себе» обсуждают и в чём риски
- исследовательский вопрос: Какие осложнения описаны при самостоятельном введении инъекционных препаратов в косметических целях?

**Ограничения:** анализ только по заголовкам из поисковой выдачи; тексты и комментарии не прочитаны; выборка определяется поисковыми запросами разработчика и ранжированием поисковика; число обсуждений в выборке не равно объёму спроса на рынке; тренд не оценивался; один источник — тема может отражать особенность площадки.
