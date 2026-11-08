# Go / No-Go к Claude

Дата: 2026-09-02. Внешний Claude **не вызывался** (P6 — замок промпта).

## Вердикт: **Go**

Готов заход человека: `00-prompt` + `schema.json` + `fewshot.jsonl` + **один** `gold/claude/{pack}.jsonl`.

Ядро для первой волны: `gv.jsonl`, `feed.jsonl`, `ped-orvi.jsonl`, `ped-baby.jsonl`. Беременность — отдельный P7. Сплошной докач id — не делать (P8 только по запросу).

## Definition of Done

| критерий | статус |
|---|---|
| `gold/jobs.yaml` есть (кодовая книга; в чате P2 было «ок») | да |
| `status: approved` в jobs.yaml | да |
| `gold/tagged.jsonl` с весом 1 | да |
| Кухня-клуб не в пакетах (`kuhnya` / флешмобы) | да |
| Педиатрия разбита (`ped-orvi` + `ped-baby`), нет `pediatria.jsonl` | да |
| Одна JSON-схема `gold/claude/schema.json` | да |
| 10 few-shot `gold/claude/fewshot.jsonl` | да |
| Промпт `packs/claude-kernel/00-prompt-dlya-claude.md` под схему | да |
| Пакеты ≤80k токенов | да |

## Пакеты на диске

| файл | работ | ≈токенов |
|---|---:|---:|
| `allergy.jsonl` | 4 | 1782 |
| `dent.jsonl` | 5 | 2968 |
| `eye.jsonl` | 2 | 892 |
| `feed.jsonl` | 10 | 4118 |
| `gv.jsonl` | 16 | 8231 |
| `mom.jsonl` | 1 | 229 |
| `nav.jsonl` | 1 | 319 |
| `neuro.jsonl` | 3 | 1901 |
| `ped-baby.jsonl` | 11 | 5812 |
| `ped-orvi.jsonl` | 8 | 3972 |
| `table.jsonl` | 1 | 240 |
| `vax.jsonl` | 5 | 2550 |

## Как вставлять в Claude (человек)

1. Система / первый месседж: содержимое `packs/claude-kernel/00-prompt-dlya-claude.md`.
2. Затем `gold/claude/schema.json`.
3. Затем `gold/claude/fewshot.jsonl`.
4. Затем **один** пакет, например `gold/claude/gv.jsonl`.
5. Не прикладывать `packs/medicina/md/pack-*.md`, кухню, сырой `dialogue_graph`.

Ожидаемый выход: JSONL карточек по схеме. Вес evidence = 1.

## Это всё ещё No-Go, если

- в чат кладут педиатрию одним файлом 110k или кулинарный клуб;
- просят пересказать треды / рейтинг ДГКБ 2006 как истину;
- ждут протоколы 2026, Госуслуги, выплаты — этого нет в корпусе;
- агент сам вызывает внешний Claude без «Go» человека.

## Не блокер

- Часть карточек P5 содержит шумный evidence — few-shot учит **вычищать**, не добивать до 15 мусором.
- Пустые работы кодовой книги (семейный стол без кластера) в пакеты не входили.
- P7 беременность и P8 докач не начаты.
