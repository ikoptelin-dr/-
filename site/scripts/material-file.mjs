// Разбор Markdown-файла с YAML-фронтматтером так же, как это делает Astro (тело — после второго ---).
import { parse } from 'yaml';

export function parseMaterialFile(text) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/.exec(text);
  if (!m) throw new Error('Нет YAML-фронтматтера между строками ---');
  return { data: parse(m[1]) ?? {}, body: m[2] };
}
