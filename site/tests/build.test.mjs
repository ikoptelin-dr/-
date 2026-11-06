// Интеграционные тесты: настоящая сборка Astro на синтетических фикстурах.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { buildSite, read, exists, htmlFiles } from './helpers/build.mjs';
import { material, nonMedicalSponsored } from './helpers/fixtures.mjs';

const M = 'materials/pro';

const main = buildSite({
  files: {
    [`${M}/pamyatki/test-approved.md`]: material({ slug: 'test-approved' }),
    [`${M}/razbory/test-draft.md`]: material({ slug: 'test-draft', kind: 'razbor', status: 'in_review' }),
    [`${M}/razbory/test-pro-only.md`]: material({ slug: 'test-pro-only', kind: 'razbor', proOnly: true }),
    [`${M}/razbory/test-expired.md`]: material({ slug: 'test-expired', kind: 'razbor', expires: '2026-01-01' }),
    [`${M}/test-sponsored.md`]: nonMedicalSponsored({ slug: 'test-sponsored' }),
    'webinars/test-speaker.md': `---
title: "Синтетический вебинар"
slug: test-speaker
summary: "Синтетический вебинар для теста."
audience: тест
program: [пункт]
speaker:
  name: "Синтетический Спикер Безсогласия"
  title: "тестовая роль"
  consent: false
duration: 1 час
status: waitlist
---
`,
    'people/test-hidden.md': `---\nname: "Синтетический Человек Скрытый"\nrole: тест\nconsent_public: false\n---\n`,
    'people/test-public.md': `---\nname: "Синтетический Человек Публичный"\nrole: тест\nconsent_public: true\n---\n`,
  },
});

test('продакшн-сборка проходит', () => {
  assert.equal(main.code, 0, main.output);
});

test('все MVP-страницы собраны, 404 есть', () => {
  const pages = [
    '/', '/pro/', '/pro/ne-akne/', '/pro/pamyatki/', '/pro/razbory/', '/pro/vebinary/', '/pro/vebinary/ne-akne/', '/pro/klub/',
    '/dlya-vseh/', '/dlya-vseh/posle-procedur/', '/o-proekte/', '/redakciya/', '/redakcionnaya-politika/',
    '/reklama-i-nezavisimost/', '/partneram/', '/kontakty/', '/politika-konfidencialnosti/', '/soglasie-na-obrabotku/',
    '/medicinskaya-ogovorka/', '/pro-dostup/',
  ];
  for (const p of pages) assert.ok(exists(main.out, p), `нет страницы ${p}`);
  assert.ok(existsSync(join(main.out, '404.html')));
  assert.ok(existsSync(join(main.out, 'sitemap.xml')));
  assert.ok(existsSync(join(main.out, 'robots.txt')));
});

test('навигация: все внутренние ссылки ведут на существующие страницы', () => {
  const broken = [];
  for (const file of htmlFiles(main.out)) {
    const html = readFileSync(file, 'utf8');
    for (const [, href] of html.matchAll(/href="(\/[^"#?]*)/g)) {
      const target = href.endsWith('/') ? join(main.out, href, 'index.html') : join(main.out, href);
      if (!existsSync(target)) broken.push(`${relative(main.out, file)} → ${href}`);
    }
  }
  assert.deepEqual(broken, []);
});

test('медицинский материал без approved не попадает в продакшн-сборку', () => {
  assert.ok(exists(main.out, '/pro/pamyatki/test-approved/'));
  assert.ok(!exists(main.out, '/pro/razbory/test-draft/'));
  assert.ok(!exists(main.out, '/pro/razbory/test-expired/'), 'просроченное одобрение');
  // Реальные черновики из src/content тоже не опубликованы.
  for (const p of ['/pro/pamyatki/guby/', '/pro/ne-akne/demodekoz/']) assert.ok(!exists(main.out, p), p);
  const all = htmlFiles(main.out).map((f) => readFileSync(f, 'utf8')).join('\n');
  assert.ok(!all.includes('test-draft'), 'ссылок на черновик нет');
  assert.ok(!all.includes('[ДОСЬЕ]'), 'заглушки досье не попали в продакшн');
});

test('страница одобренного материала: «Проверено», источники «на ком», раскрытие, оговорка, schema.org', () => {
  const html = read(main.out, '/pro/pamyatki/test-approved/');
  assert.match(html, /<h2 id="checked">Проверено<\/h2>/);
  assert.match(html, /Синтетический Рецензент/);
  assert.match(html, /Исследование на ком: <strong>люди<\/strong>/);
  assert.match(html, /Независимый материал/);
  assert.match(html, /не заменяет консультацию врача/);
  assert.match(html, /"@type":"MedicalWebPage"/);
  assert.match(html, /"reviewedBy":\{"@type":"Person","name":"Синтетический Рецензент"/);
  assert.match(html, /"lastReviewed":"2026-11-01"/);
  assert.match(html, /"citation":\[/);
  assert.match(html, /<meta property="og:title"/);
  assert.match(html, /data-start="pamyatka_test-approved"/);
  assert.match(html, /<meta name="robots" content="index, follow">/);
});

test('sitemap не содержит черновиков и pro_only; pro_only — noindex и за подтверждением', () => {
  const sitemap = read(main.out, 'sitemap.xml');
  assert.match(sitemap, /\/pro\/pamyatki\/test-approved\//);
  assert.ok(!sitemap.includes('test-draft'));
  assert.ok(!sitemap.includes('test-pro-only'));
  assert.ok(!sitemap.includes('test-expired'));
  assert.ok(!sitemap.includes('pro-dostup'));
  const pro = read(main.out, '/pro/razbory/test-pro-only/');
  assert.match(pro, /<meta name="robots" content="noindex, nofollow">/);
  assert.match(pro, /data-pro-only="true" hidden/);
  assert.match(pro, /\/pro-dostup\/\?next=/);
});

test('спонсорский материал: плашка «Реклама» и рекламодатель', () => {
  const html = read(main.out, '/pro/materialy/test-sponsored/');
  assert.match(html, /<strong>Реклама\.<\/strong> Рекламодатель: Синтетический Рекламодатель/);
  assert.match(html, /"sponsor":\{"@type":"Organization"/);
});

test('спикер без согласия не выводится по имени', () => {
  const html = read(main.out, '/pro/vebinary/test-speaker/');
  assert.ok(!html.includes('Безсогласия'));
  assert.match(html, /Спикер будет объявлен/);
  assert.ok(!read(main.out, '/pro/vebinary/').includes('Безсогласия'));
  const real = read(main.out, '/pro/vebinary/ne-akne/');
  assert.match(real, /Спикер будет объявлен/);
  assert.match(real, /Запись с предоплатой откроется позже/, 'без URL оплаты кнопка оплаты не выводится');
});

test('люди без согласия не выводятся на странице редакции', () => {
  const html = read(main.out, '/redakciya/');
  assert.ok(!html.includes('Скрытый'));
  assert.match(html, /Синтетический Человек Публичный/);
});

test('формы: обязательное согласие со ссылкой, honeypot, адрес приёма из конфигурации', () => {
  for (const [page, type] of [['/pro/vebinary/ne-akne/', 'webinar_waitlist'], ['/pro/klub/', 'club_waitlist'], ['/partneram/', 'partner']]) {
    const html = read(main.out, page);
    assert.match(html, new RegExp(`action="http://localhost:8787/api/forms/${type}"`));
    assert.match(html, /name="consent" value="yes" required/);
    assert.match(html, /href="\/soglasie-na-obrabotku\/"/);
    assert.match(html, /name="website"/);
  }
});

test('без сторонних трекеров и внешних ресурсов: стили, скрипты и шрифты — со своего сайта', () => {
  for (const file of htmlFiles(main.out)) {
    const html = readFileSync(file, 'utf8');
    for (const [, url] of html.matchAll(/<(?:script|link|img|iframe)[^>]+(?:src|href)="([^"]+)"/g)) {
      assert.ok(url.startsWith('/') || url.startsWith('https://proba.example/'), `внешний ресурс ${url} в ${file}`);
    }
    assert.ok(!/fonts\.googleapis|googletagmanager|google-analytics|mc\.yandex|metrika/i.test(html), `трекер или внешний шрифт в ${file}`);
  }
  const assets = join(main.out, '_astro');
  const css = readdirSync(assets).filter((f) => f.endsWith('.css')).map((f) => readFileSync(join(assets, f), 'utf8')).join('\n');
  assert.ok(css.length > 0, 'стили собраны');
  for (const [, url] of css.matchAll(/url\(([^)]+)\)/g)) {
    assert.ok(!/^["']?https?:/.test(url), `внешний url в CSS: ${url}`);
  }
});

test('robots.txt продакшна указывает sitemap', () => {
  assert.match(read(main.out, 'robots.txt'), /Sitemap: https:\/\/proba\.example\/sitemap\.xml/);
});

test('несовпадение хеша рецензии → понятная ошибка сборки', () => {
  const r = buildSite({ files: { [`${M}/pamyatki/test-mismatch.md`]: material({ slug: 'test-mismatch', hash: 'a'.repeat(64) }) } });
  assert.notEqual(r.code, 0);
  assert.match(r.output, /test-mismatch/);
  assert.match(r.output, /текст изменён после рецензии/);
});

test('спонсорский материал без рекламодателя или в независимом формате → ошибка сборки', () => {
  const noName = buildSite({ files: { [`${M}/test-noname.md`]: nonMedicalSponsored({ slug: 'test-noname', sponsor: '' }) } });
  assert.notEqual(noName.code, 0);
  assert.match(noName.output, /без названия рекламодателя/);
  const inPamyatka = buildSite({ files: { [`${M}/pamyatki/test-sp.md`]: nonMedicalSponsored({ slug: 'test-sp', kind: 'pamyatka' }) } });
  assert.notEqual(inPamyatka.code, 0);
  assert.match(inPamyatka.output, /не может быть kind=pamyatka/);
});

test('предпросмотр: черновики видны с плашкой, всё noindex, sitemap пуст', () => {
  const r = buildSite({ preview: true, files: { [`${M}/razbory/test-draft.md`]: material({ slug: 'test-draft', kind: 'razbor', status: 'draft' }) } });
  assert.equal(r.code, 0, r.output);
  const html = read(r.out, '/pro/razbory/test-draft/');
  assert.match(html, /data-draft-badge>Черновик/);
  assert.match(html, /noindex, nofollow/);
  assert.ok(!read(r.out, 'sitemap.xml').includes('<url>'));
  assert.match(read(r.out, 'robots.txt'), /Disallow: \//);
});
