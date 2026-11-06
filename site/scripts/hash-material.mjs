#!/usr/bin/env node
// Печатает SHA-256 контента материала для поля review.content_sha256.
// Использование: npm run hash -- src/content/materials/pro/pamyatki/guby.md
// Рецензент (человек) вносит хеш вместе со статусом approved. Скрипт ничего не одобряет.
import { readFileSync } from 'node:fs';
import { parseMaterialFile } from './material-file.mjs';
import { contentSha256 } from '../src/lib/rules.mjs';

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error('Укажите путь к файлу материала (.md).');
  process.exit(2);
}
for (const file of files) {
  const { data, body } = parseMaterialFile(readFileSync(file, 'utf8'));
  const hash = contentSha256(data, body);
  const stored = data.review?.content_sha256;
  const state = !stored ? 'хеш в рецензии не указан' : stored === hash ? 'совпадает с рецензией' : 'НЕ совпадает с рецензией: нужна новая рецензия';
  console.log(`${hash}  ${file}  (${state})`);
}
