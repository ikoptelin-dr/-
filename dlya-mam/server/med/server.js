// Сайт for-mom.ru: раздача папки site и приём заявок. Без внешних библиотек, нужен только node.exe.
// Слушает 127.0.0.1:SITE_PORT; наружу его выводит общий Caddy (HTTPS).
'use strict';
const http = require('http'), https = require('https'), tls = require('tls');
const fs = require('fs'), path = require('path'), url = require('url');

const ROOT = __dirname, SITE = path.join(ROOT, 'site');
function readSettings() {
  const cfg = {};
  try {
    for (const line of fs.readFileSync(path.join(ROOT, 'nastrojki.txt'), 'utf8').split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/); if (m) cfg[m[1]] = m[2];
    }
  } catch (e) { console.error('[XX] Не найден nastrojki.txt'); }
  return cfg;
}
const C = readSettings();
const PORT = parseInt(C.SITE_PORT || '8081', 10);
const DOMAIN = C.SITE_DOMAIN || 'for-mom.ru';
const LOG_ON = (C.LEAD_LOG || 'on').toLowerCase() !== 'off';

const TYPES = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8',
  '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg',
  '.webp':'image/webp', '.ico':'image/x-icon', '.txt':'text/plain; charset=utf-8', '.xml':'application/xml', '.pdf':'application/pdf',
  '.mp4':'video/mp4', '.woff2':'font/woff2' };
const SEC = { 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'strict-origin-when-cross-origin', 'X-Frame-Options':'SAMEORIGIN' };

function log(msg) { console.log(new Date().toISOString() + ' ' + msg); }
function send(res, code, body, type) { res.writeHead(code, Object.assign({ 'Content-Type': type || 'text/plain; charset=utf-8' }, SEC)); res.end(body); }
function json(res, code, obj) { send(res, code, JSON.stringify(obj), 'application/json; charset=utf-8'); }

function serveStatic(req, res) {
  let p = decodeURIComponent(url.parse(req.url).pathname || '/');
  if (p.endsWith('/')) p += 'index.html';
  const file = path.normalize(path.join(SITE, p));
  if (!file.startsWith(SITE + path.sep)) return send(res, 403, 'Forbidden');
  fs.stat(file, (err, st) => {
    let f = file;
    if (!err && st.isDirectory()) f = path.join(file, 'index.html');
    else if (err && !path.extname(file)) f = file + '.html';
    fs.readFile(f, (e2, data) => {
      if (e2) return fs.readFile(path.join(SITE, '404.html'), (e3, d404) => send(res, 404, e3 ? 'Страница не найдена' : d404, 'text/html; charset=utf-8'));
      const ext = path.extname(f).toLowerCase();
      res.writeHead(200, Object.assign({ 'Content-Type': TYPES[ext] || 'application/octet-stream',
        'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=86400' }, SEC));
      res.end(req.method === 'HEAD' ? undefined : data);
    });
  });
}

// --- приём заявок ---
const hits = new Map();
function tooMany(ip) {
  const now = Date.now(), arr = (hits.get(ip) || []).filter(t => now - t < 10 * 60 * 1000);
  arr.push(now); hits.set(ip, arr); return arr.length > 5;
}
function clean(v, max) { return String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max || 200); }

function smtpSend(subject, text) {
  return new Promise((resolve, reject) => {
    const host = C.SMTP_HOST || 'smtp.yandex.ru', port = parseInt(C.SMTP_PORT || '465', 10);
    const user = C.SMTP_USER, pass = C.SMTP_PASS, to = (C.MAIL_TO || user || '').split(/[,;]\s*/).filter(Boolean);
    if (!user || !pass || !to.length) return reject(new Error('почта не настроена'));
    const b64 = s => Buffer.from(s, 'utf8').toString('base64');
    const steps = [
      ['EHLO ' + DOMAIN, 250], ['AUTH LOGIN', 334], [b64(user), 334], [b64(pass), 235], ['MAIL FROM:<' + user + '>', 250],
      ...to.map(t => ['RCPT TO:<' + t + '>', 250]), ['DATA', 354],
      [['From: =?UTF-8?B?' + b64('Сайт ' + DOMAIN) + '?= <' + user + '>', 'To: ' + to.join(', '),
        'Subject: =?UTF-8?B?' + b64(subject) + '?=', 'Date: ' + new Date().toUTCString(), 'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '',
        b64(text).replace(/.{1,76}/g, '$&\r\n'), '.'].join('\r\n'), 250], ['QUIT', 221]];
    let i = -1, buf = '', done = false;
    const sock = tls.connect({ host, port, servername: host }, () => {});
    const fail = e => { if (!done) { done = true; sock.destroy(); reject(e); } };
    sock.setTimeout(20000, () => fail(new Error('SMTP: таймаут')));
    sock.on('error', fail);
    sock.on('data', d => {
      buf += d.toString('utf8');
      const lines = buf.split('\r\n'); if (lines[lines.length - 1] !== '') return;
      const last = lines[lines.length - 2]; if (!/^\d{3} /.test(last)) return;
      buf = ''; const code = parseInt(last, 10);
      const expect = i < 0 ? 220 : steps[i][1];
      if (code !== expect) return fail(new Error('SMTP ответил ' + last.slice(0, 80)));
      i++; if (i >= steps.length) { done = true; sock.end(); return resolve(); }
      sock.write(steps[i][0] + '\r\n');
    });
  });
}

function bitrixSend(l) {
  return new Promise((resolve, reject) => {
    if (!C.B24_WEBHOOK) return reject(new Error('Битрикс не настроен'));
    const base = C.B24_WEBHOOK.replace(/\/?$/, '/');
    const body = JSON.stringify({ fields: {
      TITLE: 'Лист ожидания for-mom.ru: ' + l.clinic, NAME: l.name, COMPANY_TITLE: l.clinic, ADDRESS_CITY: l.city,
      POST: l.role, SOURCE_ID: 'WEB', SOURCE_DESCRIPTION: DOMAIN,
      PHONE: [{ VALUE: l.contact, VALUE_TYPE: 'WORK' }],
      COMMENTS: 'Педиатрических приёмов в месяц: ' + l.visits + '<br>Контакт: ' + l.contact,
      UTM_SOURCE: l.utm_source, UTM_MEDIUM: l.utm_medium, UTM_CAMPAIGN: l.utm_campaign, UTM_CONTENT: l.utm_content } });
    const r = https.request(base + 'crm.lead.add.json', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }, timeout: 15000 }, resp => {
      let d = ''; resp.on('data', c => d += c); resp.on('end', () => (resp.statusCode === 200 && /"result"/.test(d)) ? resolve() : reject(new Error('Битрикс ответил ' + resp.statusCode)));
    });
    r.on('timeout', () => r.destroy(new Error('Битрикс: таймаут'))); r.on('error', reject); r.end(body);
  });
}

function handleLead(req, res) {
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
  if (tooMany(ip)) return json(res, 429, { ok: false, error: 'Слишком много заявок подряд. Попробуйте через 10 минут.' });
  let raw = '';
  req.on('data', c => { raw += c; if (raw.length > 10000) req.destroy(); });
  req.on('end', async () => {
    let b; try { b = JSON.parse(raw); } catch (e) { return json(res, 400, { ok: false, error: 'Неверный формат' }); }
    if (b.site) return json(res, 200, { ok: true }); // ловушка для ботов
    const l = { time: new Date().toISOString(), name: clean(b.name, 100), role: clean(b.role, 60), clinic: clean(b.clinic, 150),
      city: clean(b.city, 80), contact: clean(b.contact, 80), visits: clean(b.visits, 40), consent: b.consent === true,
      utm_source: clean(b.utm_source, 100), utm_medium: clean(b.utm_medium, 100), utm_campaign: clean(b.utm_campaign, 100), utm_content: clean(b.utm_content, 100) };
    if (!l.name || !l.role || !l.clinic || !l.city || !l.contact || !l.visits) return json(res, 400, { ok: false, error: 'Заполните все поля' });
    if (!l.consent) return json(res, 400, { ok: false, error: 'Нужно согласие на обработку данных' });
    const text = ['Новая заявка в лист ожидания (' + DOMAIN + ')', '', 'Имя: ' + l.name, 'Роль: ' + l.role, 'Клиника: ' + l.clinic,
      'Город: ' + l.city, 'Телефон или Telegram: ' + l.contact, 'Педиатрических приёмов в месяц: ' + l.visits,
      'Согласие на обработку ПД: да, ' + l.time, '', 'UTM: ' + [l.utm_source, l.utm_medium, l.utm_campaign, l.utm_content].filter(Boolean).join(' / ')].join('\n');
    let okCount = 0; const errs = [];
    if (LOG_ON) { try { fs.mkdirSync(path.join(ROOT, 'leads'), { recursive: true }); fs.appendFileSync(path.join(ROOT, 'leads', 'leads.jsonl'), JSON.stringify(l) + '\n'); okCount++; } catch (e) { errs.push('журнал: ' + e.message); } }
    await Promise.all([
      smtpSend('Заявка: ' + l.clinic + ', ' + l.city, text).then(() => okCount++, e => errs.push('почта: ' + e.message)),
      bitrixSend(l).then(() => okCount++, e => errs.push(e.message)) ]);
    log('заявка ' + (okCount ? 'принята' : 'НЕ ДОСТАВЛЕНА') + (errs.length ? ' | ' + errs.join(' | ') : ''));
    if (!okCount) return json(res, 500, { ok: false, error: 'Заявка не отправилась. Попробуйте ещё раз позже.' });
    json(res, 200, { ok: true });
  });
}

http.createServer((req, res) => {
  const p = url.parse(req.url).pathname;
  if (p === '/api/lead' && req.method === 'POST') return handleLead(req, res);
  if (p === '/api/health') return json(res, 200, { ok: true, site: DOMAIN });
  if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, 'Method not allowed');
  serveStatic(req, res);
}).listen(PORT, '127.0.0.1', () => log('[OK] Сайт ' + DOMAIN + ' работает: http://localhost:' + PORT + (LOG_ON ? ' (копии заявок: leads\\leads.jsonl)' : '')))
  .on('error', e => { console.error('[XX] Не удалось занять порт ' + PORT + ': ' + e.message); process.exit(1); });
