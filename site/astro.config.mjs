// @ts-check
import { defineConfig } from 'astro/config';
import { readFileSync } from 'node:fs';

const cfg = JSON.parse(readFileSync(new URL('./proba.config.json', import.meta.url), 'utf8'));

export default defineConfig({
  site: cfg.site_url,
  output: 'static',
  trailingSlash: 'always',
  build: { format: 'directory', inlineStylesheets: 'never' },
  outDir: process.env.PROBA_OUT_DIR || './dist',
  cacheDir: process.env.PROBA_CACHE_DIR || './node_modules/.astro',
  devToolbar: { enabled: false },
  // Без внешних счётчиков и телеметрии (ТЗ, раздел 2).
  prefetch: false,
});
