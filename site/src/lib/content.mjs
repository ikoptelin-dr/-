// Загрузка контента с применением правил публикации. Любая страница получает материалы только отсюда.
import { getCollection } from 'astro:content';
import { config } from './config.mjs';
import { evaluateMaterial, isIndexable, materialPath, publicPeople } from './rules.mjs';

let cache;

export async function getMaterials() {
  if (cache) return cache;
  const entries = await getCollection('materials');
  const result = [];
  for (const entry of entries) {
    const decision = evaluateMaterial(entry.id, entry.data, entry.body, { preview: config.preview });
    if (!decision.include) continue;
    result.push({
      entry,
      data: entry.data,
      decision,
      path: materialPath(entry.data),
      indexable: isIndexable(entry.data, decision, config.preview),
    });
  }
  result.sort((a, b) => b.data.updated_at - a.data.updated_at || a.data.title.localeCompare(b.data.title, 'ru'));
  cache = result;
  return result;
}

// Карточки хаба (без самих вводных текстов хабов).
export async function getHubItems({ section, hub }) {
  const all = await getMaterials();
  return all.filter((m) => m.data.kind !== 'hub' && m.data.section === section && hubOfData(m.data) === hub);
}

// Вводный текст хаба (kind: hub, slug = путь хаба). Может отсутствовать в продакшне, если не одобрен.
export async function getHubIntro({ section, hub }) {
  const all = await getMaterials();
  return all.find((m) => m.data.kind === 'hub' && m.data.section === section && m.data.slug === hub) ?? null;
}

function hubOfData(d) {
  return materialPath(d).split('/')[2];
}

export async function getPublicPeople() {
  const people = await getCollection('people');
  return publicPeople(people.map((p) => ({ ...p.data, id: p.id }))).sort((a, b) => a.name.localeCompare(b.name, 'ru'));
}

export async function getWebinars() {
  const items = await getCollection('webinars');
  return items.sort((a, b) => a.data.title.localeCompare(b.data.title, 'ru'));
}
