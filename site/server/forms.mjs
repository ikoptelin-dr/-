// Приём заявок с форм сайта (ТЗ, раздел 5). Без внешних зависимостей.
// Правила: согласие обязательно; honeypot и ограничение частоты; заявка сначала сохраняется,
// затем уведомление; неотправленное уведомление ставится в очередь; персональные данные не пишутся в логи.
import { createServer } from 'node:http';
import { appendFile, mkdir, readFile, writeFile, rename } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { join } from 'node:path';

export const FORM_TYPES = {
  webinar_waitlist: {
    required: ['name', 'contact', 'role'],
    optional: ['city', 'subject'],
    enums: { role: ['cosmetologist', 'doctor', 'other'] },
  },
  club_waitlist: {
    required: ['name', 'contact', 'role'],
    optional: ['city', 'subject'],
    enums: { role: ['cosmetologist', 'doctor', 'other'] },
  },
  partner: {
    required: ['name', 'organization', 'org_type', 'contact'],
    optional: ['city', 'message'],
    enums: { org_type: ['clinic', 'school', 'brand'] },
  },
};

const MAX_LEN = { message: 2000, organization: 200 };
const MAX_BODY = 16 * 1024;
const HONEYPOT = 'website';

export function validateSubmission(type, fields) {
  const spec = FORM_TYPES[type];
  if (!spec) return { ok: false, error: 'unknown_form' };
  if (fields.consent !== 'yes' && fields.consent !== true && fields.consent !== 'on') {
    return { ok: false, error: 'consent_required' };
  }
  const clean = {};
  for (const key of [...spec.required, ...spec.optional]) {
    const v = typeof fields[key] === 'string' ? fields[key].trim() : '';
    if (v.length > (MAX_LEN[key] ?? 100)) return { ok: false, error: `too_long:${key}` };
    if (spec.required.includes(key) && !v) return { ok: false, error: `required:${key}` };
    if (spec.enums?.[key] && v && !spec.enums[key].includes(v)) return { ok: false, error: `invalid:${key}` };
    if (v) clean[key] = v;
  }
  if (clean.contact && !/^(\S+@\S+\.\S+|@?[A-Za-z0-9_]{5,32})$/.test(clean.contact)) {
    return { ok: false, error: 'invalid:contact' };
  }
  return { ok: true, fields: clean };
}

export function isBot(fields) {
  return typeof fields[HONEYPOT] === 'string' && fields[HONEYPOT].trim() !== '';
}

export function createRateLimiter({ max = 5, windowMs = 10 * 60 * 1000, now = () => Date.now() } = {}) {
  const hits = new Map();
  return function allow(key) {
    const t = now();
    const list = (hits.get(key) ?? []).filter((x) => t - x < windowMs);
    if (list.length >= max) {
      hits.set(key, list);
      return false;
    }
    list.push(t);
    hits.set(key, list);
    if (hits.size > 10000) for (const [k, v] of hits) if (!v.some((x) => t - x < windowMs)) hits.delete(k);
    return true;
  };
}

// Уведомление в Telegram без персональных данных: только тип и номер заявки.
// Без токена уведомление не отправляется (и не считается ошибкой).
export function telegramNotifier({ token = process.env.TELEGRAM_BOT_TOKEN, chatId = process.env.TELEGRAM_CHAT_ID, fetchImpl = fetch } = {}) {
  if (!token || !chatId) return null;
  return async function notify({ id, type }) {
    const res = await fetchImpl(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: `Proba: новая заявка (${type}), № ${id}. Данные — в хранилище заявок.` }),
    });
    if (!res.ok) throw new Error(`telegram_http_${res.status}`);
  };
}

export function createStore(dir) {
  const submissions = join(dir, 'submissions.jsonl');
  const queue = join(dir, 'notify_queue.jsonl');
  return {
    async save(record) {
      await mkdir(dir, { recursive: true, mode: 0o700 });
      await appendFile(submissions, JSON.stringify(record) + '\n', { encoding: 'utf8', mode: 0o600 });
    },
    async enqueue(item) {
      await mkdir(dir, { recursive: true, mode: 0o700 });
      await appendFile(queue, JSON.stringify(item) + '\n', { encoding: 'utf8', mode: 0o600 });
    },
    async readQueue() {
      try {
        return (await readFile(queue, 'utf8')).split('\n').filter(Boolean).map((l) => JSON.parse(l));
      } catch (e) {
        if (e.code === 'ENOENT') return [];
        throw e;
      }
    },
    async writeQueue(items) {
      const tmp = `${queue}.tmp`;
      await writeFile(tmp, items.map((i) => JSON.stringify(i) + '\n').join(''), { mode: 0o600 });
      await rename(tmp, queue);
    },
    async readSubmissions() {
      try {
        return (await readFile(submissions, 'utf8')).split('\n').filter(Boolean).map((l) => JSON.parse(l));
      } catch (e) {
        if (e.code === 'ENOENT') return [];
        throw e;
      }
    },
  };
}

function parseBody(raw, contentType) {
  if ((contentType || '').includes('application/json')) {
    const v = JSON.parse(raw || '{}');
    return v && typeof v === 'object' ? v : {};
  }
  return Object.fromEntries(new URLSearchParams(raw));
}

function readRaw(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY) {
        reject(Object.assign(new Error('too_large'), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

export function createFormsHandler({
  store,
  notify = null,
  allow = createRateLimiter(),
  siteOrigin = 'http://localhost:4321',
  trustProxy = false,
  log = (msg) => console.log(msg),
  now = () => new Date(),
} = {}) {
  async function retryQueue() {
    if (!notify) return;
    const pending = await store.readQueue();
    if (pending.length === 0) return;
    const left = [];
    for (const item of pending) {
      try {
        await notify(item);
      } catch {
        left.push({ ...item, attempts: (item.attempts ?? 1) + 1 });
      }
    }
    await store.writeQueue(left);
    log(`[forms] retry notifications: sent=${pending.length - left.length} pending=${left.length}`);
  }

  async function handler(req, res) {
    const wantsJson = (req.headers.accept || '').includes('application/json') || (req.headers['content-type'] || '').includes('application/json');
    const reply = (status, outcome, extra = {}) => {
      if (wantsJson) {
        res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ ok: outcome === 'ok', ...extra }));
      } else {
        const page = outcome === 'ok' ? '/zayavka-otpravlena/' : '/zayavka-oshibka/';
        res.writeHead(303, { Location: new URL(page, siteOrigin).toString() });
        res.end();
      }
    };

    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && url.pathname === '/health') {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      return res.end('ok');
    }
    const m = /^\/api\/forms\/([a-z_]+)\/?$/.exec(url.pathname);
    if (!m || req.method !== 'POST') return reply(404, 'error', { error: 'not_found' });
    const type = m[1];
    if (!FORM_TYPES[type]) return reply(404, 'error', { error: 'unknown_form' });

    const ip = (trustProxy && String(req.headers['x-forwarded-for'] || '').split(',')[0].trim()) || req.socket.remoteAddress || 'unknown';
    if (!allow(ip)) {
      log(`[forms] rate_limited type=${type}`);
      return reply(429, 'error', { error: 'rate_limited' });
    }

    let fields;
    try {
      fields = parseBody(await readRaw(req), req.headers['content-type']);
    } catch (e) {
      log(`[forms] bad_request type=${type} reason=${e.status === 413 ? 'too_large' : 'parse'}`);
      return reply(e.status === 413 ? 413 : 400, 'error', { error: 'bad_request' });
    }

    if (isBot(fields)) {
      // Боту отвечаем как при успехе, чтобы не подсказывать; заявку не сохраняем.
      log(`[forms] honeypot_dropped type=${type}`);
      return reply(200, 'ok');
    }

    const v = validateSubmission(type, fields);
    if (!v.ok) {
      log(`[forms] rejected type=${type} reason=${v.error}`);
      return reply(422, 'error', { error: v.error });
    }

    const record = { id: randomUUID(), type, received_at: now().toISOString(), consent: true, fields: v.fields };
    try {
      await store.save(record);
    } catch (e) {
      log(`[forms] storage_error type=${type} id=${record.id} code=${e.code ?? 'unknown'}`);
      return reply(500, 'error', { error: 'storage_unavailable' });
    }
    log(`[forms] accepted type=${type} id=${record.id}`);

    if (notify) {
      const item = { id: record.id, type };
      try {
        await notify(item);
      } catch (e) {
        log(`[forms] notify_failed id=${record.id} reason=${String(e.message).slice(0, 60).replace(/bot[^/]*\//, 'bot***/')}`);
        try {
          await store.enqueue({ ...item, attempts: 1 });
        } catch {
          log(`[forms] queue_error id=${record.id}`);
        }
      }
    }
    return reply(200, 'ok', { id: record.id });
  }

  handler.retryQueue = retryQueue;
  return handler;
}

export function createFormsServer(options) {
  const handler = createFormsHandler(options);
  const server = createServer((req, res) => {
    handler(req, res).catch(() => {
      if (!res.headersSent) res.writeHead(500);
      res.end();
    });
  });
  server.retryQueue = handler.retryQueue;
  return server;
}
