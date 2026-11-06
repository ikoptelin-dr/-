import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  contentSha256, evaluateMaterial, ContentRuleError, isIndexable, publicSpeakerName, publicPeople,
  botStartParam, botStartForMaterial, materialPath,
} from '../src/lib/rules.mjs';

const base = () => ({
  title: 'Синтетический заголовок',
  slug: 'syn',
  section: 'pro',
  kind: 'pamyatka',
  summary: 'Синтетический анонс',
  medical: true,
  pro_only: false,
  sources: [{ title: 'Синтетический источник', url: 'https://example.org/s', year: 2025, type: 'обзор', on_whom: 'люди' }],
  disclosure: 'Независимый материал',
  sponsored: null,
  updated_at: new Date('2026-11-05'),
  changelog: [],
});
const BODY = 'Синтетический текст.';
const approved = (d = base(), body = BODY) => ({
  ...d,
  review: { reviewer_name: 'Синтетический Рецензент', reviewer_title: 'роль', reviewed_at: new Date('2026-11-01'), version: 1, status: 'approved', content_sha256: contentSha256(d, body) },
});

test('медицинский материал без approved не попадает в продакшн, в предпросмотре — как черновик', () => {
  for (const status of ['draft', 'in_review']) {
    const d = { ...base(), review: { status } };
    assert.equal(evaluateMaterial('x', d, BODY).include, false);
    const p = evaluateMaterial('x', d, BODY, { preview: true });
    assert.equal(p.include, true);
    assert.equal(p.draft, true);
  }
});

test('одобренный материал с верным хешем публикуется', () => {
  const r = evaluateMaterial('x', approved(), BODY);
  assert.deepEqual([r.include, r.draft], [true, false]);
});

test('несовпадение хеша → понятная ошибка «текст изменён после рецензии»', () => {
  const d = approved();
  assert.throws(() => evaluateMaterial('pamyatki/syn', d, BODY + ' Правка.'), (e) => {
    assert.ok(e instanceof ContentRuleError);
    assert.match(e.message, /pamyatki\/syn/);
    assert.match(e.message, /текст изменён после рецензии/);
    return true;
  });
});

test('изменение заголовка, анонса, ссылки источника, раскрытия или спонсорства меняет хеш', () => {
  const h = contentSha256(base(), BODY);
  const mutations = [
    (d) => (d.title += '!'),
    (d) => (d.summary += '!'),
    (d) => (d.sources[0].url = 'https://example.org/other'),
    (d) => (d.sources[0].on_whom = 'животные'),
    (d) => (d.disclosure = 'Другое раскрытие'),
    (d) => (d.sponsored = { sponsor: 'Синтетический Рекламодатель' }),
  ];
  for (const mutate of mutations) {
    const d = structuredClone(base());
    mutate(d);
    assert.notEqual(contentSha256(d, BODY), h);
  }
  // Переводы строк и крайние пробелы не считаются изменением текста.
  assert.equal(contentSha256(base(), `\n${BODY.replace(/\n/g, '\r\n')}\n\n`), h);
});

test('одобрение без хеша, рецензента или источников — ошибка', () => {
  const noHash = approved();
  delete noHash.review.content_sha256;
  assert.throws(() => evaluateMaterial('x', noHash, BODY), /без content_sha256/);
  const noReviewer = approved();
  delete noReviewer.review.reviewer_name;
  assert.throws(() => evaluateMaterial('x', noReviewer, BODY), /без имени и должности рецензента/);
  const d = { ...base(), sources: [] };
  assert.throws(() => evaluateMaterial('x', approved(d), BODY), /без источников/);
});

test('просроченное одобрение не публикуется', () => {
  const d = approved();
  d.review.expires_at = new Date('2026-11-02');
  const r = evaluateMaterial('x', d, BODY, { now: new Date('2026-11-06') });
  assert.equal(r.include, false);
  assert.match(r.reason, /срок одобрения истёк/);
});

test('спонсорский материал без рекламодателя — ошибка; в независимых форматах pro — ошибка', () => {
  const noSponsor = { ...base(), medical: false, kind: 'article', disclosure: 'Партнёрский материал', sponsored: { sponsor: ' ' } };
  assert.throws(() => evaluateMaterial('x', noSponsor, BODY), /без названия рекламодателя/);
  for (const kind of ['razbor', 'ne-akne', 'pamyatka']) {
    const d = { ...base(), medical: false, kind, disclosure: 'Партнёрский материал', sponsored: { sponsor: 'Синтетический Рекламодатель' } };
    assert.throws(() => evaluateMaterial('x', d, BODY), /не может быть kind=/);
  }
  const independent = { ...base(), medical: false, kind: 'article', sponsored: { sponsor: 'Синтетический Рекламодатель' } };
  assert.throws(() => evaluateMaterial('x', independent, BODY), /«Независимый материал»/);
  const ok = { ...noSponsor, sponsored: { sponsor: 'Синтетический Рекламодатель' } };
  assert.equal(evaluateMaterial('x', ok, BODY).include, true);
});

test('pro_only и черновики не индексируются', () => {
  const d = approved({ ...base(), pro_only: true });
  assert.equal(isIndexable(d, evaluateMaterial('x', d, BODY)), false);
  assert.equal(isIndexable(approved(), { draft: false }), true);
  assert.equal(isIndexable(approved(), { draft: true }), false);
  assert.equal(isIndexable(approved(), { draft: false }, true), false);
});

test('спикер и люди без согласия не выводятся по имени', () => {
  assert.equal(publicSpeakerName({ name: 'Синтетический Спикер', consent: false }), null);
  assert.equal(publicSpeakerName({ name: 'Синтетический Спикер' }), null);
  assert.deepEqual(publicSpeakerName({ name: 'Синтетический Спикер', title: 'роль', consent: true }), { name: 'Синтетический Спикер', title: 'роль' });
  assert.deepEqual(publicPeople([{ name: 'А', consent_public: false }, { name: 'Б', consent_public: true }, { name: 'В' }]).map((p) => p.name), ['Б']);
});

test('URL материалов по карте сайта и параметр бота', () => {
  assert.equal(materialPath({ section: 'pro', kind: 'pamyatka', slug: 'guby' }), '/pro/pamyatki/guby/');
  assert.equal(materialPath({ section: 'pro', kind: 'razbor', slug: 'x' }), '/pro/razbory/x/');
  assert.equal(materialPath({ section: 'pro', kind: 'ne-akne', slug: 'demodekoz' }), '/pro/ne-akne/demodekoz/');
  assert.equal(materialPath({ section: 'dlya-vseh', kind: 'article', hub: 'posle-procedur', slug: 'guby' }), '/dlya-vseh/posle-procedur/guby/');
  assert.equal(materialPath({ section: 'pro', kind: 'hub', slug: 'ne-akne' }), '/pro/ne-akne/');
  assert.equal(botStartForMaterial({ kind: 'pamyatka', slug: 'guby' }), 'pamyatka_guby');
  assert.equal(botStartParam('a', 'б в'), 'a____');
  assert.ok(botStartParam('x', 'y'.repeat(100)).length <= 64);
});
