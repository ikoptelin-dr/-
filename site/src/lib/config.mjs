// Единая точка чтения конфигурации сайта. Секретов здесь нет и быть не должно.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const path = fileURLToPath(new URL('../../proba.config.json', import.meta.url));
const raw = JSON.parse(readFileSync(path, 'utf8'));

export const config = {
  ...raw,
  // Режим предпросмотра: черновики видны с плашкой «Черновик», всё noindex.
  preview: process.env.PROBA_PREVIEW === '1',
  forms_endpoint: process.env.PROBA_FORMS_ENDPOINT || raw.forms_endpoint,
};

export function siteUrl(path = '/') {
  return new URL(path, config.site_url).toString();
}
