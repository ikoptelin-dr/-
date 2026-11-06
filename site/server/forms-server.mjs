#!/usr/bin/env node
// Запуск сервера форм: npm run forms. Настройки — переменные окружения (см. .env.example).
import { createFormsServer, createStore, telegramNotifier } from './forms.mjs';

const port = Number(process.env.PROBA_FORMS_PORT || 8787);
const host = process.env.PROBA_FORMS_HOST || '127.0.0.1';
const dir = process.env.PROBA_FORMS_DIR || new URL('../var/forms/', import.meta.url).pathname;
const notify = telegramNotifier();

const server = createFormsServer({
  store: createStore(dir),
  notify,
  siteOrigin: process.env.PROBA_SITE_ORIGIN || 'http://localhost:4321',
  trustProxy: process.env.PROBA_TRUST_PROXY === '1',
});

server.listen(port, host, () => {
  console.log(`[forms] listening http://${host}:${port} storage=${dir} telegram=${notify ? 'on' : 'off'}`);
});
server.retryQueue().catch(() => console.log('[forms] retry failed'));
setInterval(() => server.retryQueue().catch(() => console.log('[forms] retry failed')), 5 * 60 * 1000).unref();
