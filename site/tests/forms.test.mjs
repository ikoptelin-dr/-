import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createFormsServer, createStore, createRateLimiter, validateSubmission, telegramNotifier } from '../server/forms.mjs';

// Синтетические данные формы.
const PERSON = { name: 'Синтетическая Тестова', contact: 'synthetic.test@example.org', role: 'cosmetologist', city: 'Тестовск' };
const PII = [PERSON.name, PERSON.contact, PERSON.city];

async function start(opts = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'proba-forms-'));
  const logs = [];
  const server = createFormsServer({ store: createStore(dir), log: (m) => logs.push(m), siteOrigin: 'http://site.test', ...opts });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const post = (type, fields, { json = false } = {}) =>
    fetch(`${base}/api/forms/${type}`, {
      method: 'POST',
      redirect: 'manual',
      headers: json ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: json ? JSON.stringify(fields) : new URLSearchParams(fields).toString(),
    });
  const stored = () => (existsSync(join(dir, 'submissions.jsonl')) ? readFileSync(join(dir, 'submissions.jsonl'), 'utf8').split('\n').filter(Boolean).map(JSON.parse) : []);
  return { server, dir, logs, post, stored, close: () => new Promise((r) => server.close(r)) };
}

test('форма без согласия не отправляется', async () => {
  assert.equal(validateSubmission('webinar_waitlist', { ...PERSON }).error, 'consent_required');
  assert.equal(validateSubmission('webinar_waitlist', { ...PERSON, consent: 'no' }).error, 'consent_required');
  const s = await start();
  try {
    const res = await s.post('webinar_waitlist', PERSON, { json: true });
    assert.equal(res.status, 422);
    assert.equal((await res.json()).error, 'consent_required');
    const html = await s.post('club_waitlist', PERSON);
    assert.equal(html.status, 303);
    assert.equal(html.headers.get('location'), 'http://site.test/zayavka-oshibka/');
    assert.equal(s.stored().length, 0);
  } finally {
    await s.close();
  }
});

test('honeypot отсекает бота: ответ как при успехе, заявка не сохраняется', async () => {
  const s = await start();
  try {
    const res = await s.post('webinar_waitlist', { ...PERSON, consent: 'yes', website: 'http://spam.example' });
    assert.equal(res.status, 303);
    assert.equal(res.headers.get('location'), 'http://site.test/zayavka-otpravlena/');
    assert.equal(s.stored().length, 0);
    assert.ok(s.logs.some((l) => l.includes('honeypot_dropped')));
  } finally {
    await s.close();
  }
});

test('корректная заявка сохраняется, в логах нет персональных данных', async () => {
  const s = await start();
  try {
    const res = await s.post('webinar_waitlist', { ...PERSON, consent: 'yes', subject: 'ne-akne' });
    assert.equal(res.status, 303);
    assert.equal(res.headers.get('location'), 'http://site.test/zayavka-otpravlena/');
    const [rec] = s.stored();
    assert.equal(rec.type, 'webinar_waitlist');
    assert.equal(rec.consent, true);
    assert.equal(rec.fields.name, PERSON.name);
    assert.equal(rec.fields.subject, 'ne-akne');
    const partner = await s.post('partner', { name: PERSON.name, organization: 'Синтетическая клиника', org_type: 'clinic', contact: '@synthetic_test', message: 'Тест', consent: 'yes' }, { json: true });
    assert.equal(partner.status, 200);
    assert.equal(s.stored().length, 2);
    const logText = s.logs.join('\n');
    for (const v of [...PII, 'Синтетическая клиника', '@synthetic_test']) assert.ok(!logText.includes(v), `в логах найдено: ${v}`);
  } finally {
    await s.close();
  }
});

test('обязательные поля и допустимые значения проверяются на сервере', () => {
  assert.equal(validateSubmission('partner', { name: 'А', contact: 'a@example.org', org_type: 'clinic', consent: 'yes' }).error, 'required:organization');
  assert.equal(validateSubmission('club_waitlist', { ...PERSON, role: 'admin', consent: 'yes' }).error, 'invalid:role');
  assert.equal(validateSubmission('club_waitlist', { ...PERSON, contact: 'не контакт', consent: 'yes' }).error, 'invalid:contact');
  assert.equal(validateSubmission('club_waitlist', { ...PERSON, name: 'я'.repeat(101), consent: 'yes' }).error, 'too_long:name');
  assert.equal(validateSubmission('unknown', {}).error, 'unknown_form');
});

test('ограничение частоты: после лимита — 429', async () => {
  const s = await start({ allow: createRateLimiter({ max: 2, windowMs: 60_000 }) });
  try {
    const f = { ...PERSON, consent: 'yes' };
    assert.equal((await s.post('club_waitlist', f, { json: true })).status, 200);
    assert.equal((await s.post('club_waitlist', f, { json: true })).status, 200);
    assert.equal((await s.post('club_waitlist', f, { json: true })).status, 429);
    assert.equal(s.stored().length, 2);
  } finally {
    await s.close();
  }
  let t = 0;
  const allow = createRateLimiter({ max: 1, windowMs: 1000, now: () => t });
  assert.equal(allow('ip'), true);
  assert.equal(allow('ip'), false);
  t = 1001;
  assert.equal(allow('ip'), true);
});

test('сбой уведомления не теряет заявку: она сохранена, уведомление в очереди и уходит при повторе', async () => {
  let fail = true;
  const sent = [];
  const notify = async (item) => {
    if (fail) throw new Error('network down');
    sent.push(item);
  };
  const s = await start({ notify });
  try {
    const res = await s.post('club_waitlist', { ...PERSON, consent: 'yes' }, { json: true });
    assert.equal(res.status, 200);
    const { id } = await res.json();
    assert.equal(s.stored()[0].id, id);
    const queue = readFileSync(join(s.dir, 'notify_queue.jsonl'), 'utf8');
    assert.match(queue, new RegExp(id));
    for (const v of PII) assert.ok(!queue.includes(v), 'в очереди уведомлений нет персональных данных');
    fail = false;
    await s.server.retryQueue();
    assert.deepEqual(sent, [{ id, type: 'club_waitlist', attempts: 1 }]);
    assert.equal(readFileSync(join(s.dir, 'notify_queue.jsonl'), 'utf8'), '');
  } finally {
    await s.close();
  }
});

test('ошибка хранилища — пользователь видит ошибку, а не ложный успех', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'proba-forms-fail-'));
  const failing = { ...createStore(dir), save: async () => { throw Object.assign(new Error('EACCES'), { code: 'EACCES' }); } };
  const s = await start({ store: failing });
  try {
    const res = await s.post('club_waitlist', { ...PERSON, consent: 'yes' }, { json: true });
    assert.equal(res.status, 500);
    assert.ok(s.logs.some((l) => l.includes('storage_error')));
    for (const v of PII) assert.ok(!s.logs.join('\n').includes(v));
  } finally {
    await s.close();
  }
});

test('уведомление Telegram: без токена выключено, сообщение без персональных данных', async () => {
  assert.equal(telegramNotifier({ token: '', chatId: '' }), null);
  const calls = [];
  const notify = telegramNotifier({ token: 'TEST', chatId: '1', fetchImpl: async (url, init) => { calls.push({ url, init }); return { ok: true }; } });
  await notify({ id: 'abc', type: 'partner' });
  const body = JSON.parse(calls[0].init.body);
  assert.match(body.text, /partner/);
  assert.match(body.text, /abc/);
});
