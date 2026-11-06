// Сборка сайта во временный каталог с подменённым контентом (копия src/content + синтетические фикстуры).
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseMaterialFile } from '../../scripts/material-file.mjs';
import { contentSha256 } from '../../src/lib/rules.mjs';

export const SITE = fileURLToPath(new URL('../..', import.meta.url));

// Подставляет в фикстуру хеш текущего текста вместо __HASH__ (как сделал бы рецензент через npm run hash).
export function withHash(text) {
  const { data, body } = parseMaterialFile(text.replace('__HASH__', '0'.repeat(64)));
  return text.replace('__HASH__', contentSha256(data, body));
}

export function buildSite({ files = {}, preview = false, keepRealContent = true } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'proba-site-test-'));
  const content = join(root, 'content');
  if (keepRealContent) cpSync(join(SITE, 'src/content'), content, { recursive: true });
  for (const [rel, text] of Object.entries(files)) {
    const p = join(content, rel);
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, text);
  }
  const out = join(root, 'dist');
  const res = spawnSync(process.execPath, [join(SITE, 'node_modules/astro/astro.js'), 'build'], {
    cwd: SITE,
    encoding: 'utf8',
    env: {
      ...process.env,
      ASTRO_TELEMETRY_DISABLED: '1',
      PROBA_CONTENT_DIR: content,
      PROBA_OUT_DIR: out,
      PROBA_CACHE_DIR: join(root, 'cache'),
      PROBA_PREVIEW: preview ? '1' : '0',
    },
  });
  return { code: res.status, output: `${res.stdout}\n${res.stderr}`, out };
}

export function read(out, path) {
  const p = path.endsWith('.xml') || path.endsWith('.txt') || path.endsWith('.html') ? join(out, path) : join(out, path, 'index.html');
  return readFileSync(p, 'utf8');
}

export function exists(out, path) {
  return existsSync(join(out, path, 'index.html'));
}

export function htmlFiles(dir) {
  const result = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) result.push(...htmlFiles(p));
    else if (name.endsWith('.html')) result.push(p);
  }
  return result;
}
