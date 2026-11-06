// Правила публикации материалов (ТЗ, раздел 3). Чистые функции без Astro:
// используются при сборке, в CLI `npm run hash` и в тестах.
import { createHash } from 'node:crypto';

export const KINDS_FORBIDDEN_FOR_SPONSORED_PRO = ['razbor', 'ne-akne', 'pamyatka'];

// Путь хаба для материала. Для pro хаб следует из kind; для «Для всех» задаётся полем hub.
const PRO_HUB_BY_KIND = { 'ne-akne': 'ne-akne', pamyatka: 'pamyatki', razbor: 'razbory', article: 'materialy' };

export function hubOf(data) {
  if (data.section === 'pro') return PRO_HUB_BY_KIND[data.kind];
  return data.hub || 'materialy';
}

export function materialPath(data) {
  if (data.kind === 'hub') return `/${data.section}/${data.slug}/`;
  return `/${data.section}/${hubOf(data)}/${data.slug}/`;
}

export function normalizeBody(body) {
  return String(body ?? '').replace(/\r\n?/g, '\n').trim();
}

// Канонический вид контента, к которому привязана рецензия.
// Любое изменение текста, заголовка, анонса, источников (ссылок) или раскрытия
// спонсорства меняет хеш → одобрение перестаёт быть актуальным (CLAUDE.md).
export function canonicalContent(data, body) {
  const sources = (data.sources ?? []).map((s) => ({
    title: s.title ?? null,
    url: s.url ?? null,
    year: s.year ?? null,
    type: s.type ?? null,
    on_whom: s.on_whom ?? null,
  }));
  const sponsored = data.sponsored
    ? { sponsor: data.sponsored.sponsor ?? null, marking_erid: data.sponsored.marking_erid ?? null }
    : null;
  return JSON.stringify({
    title: data.title,
    summary: data.summary,
    body: normalizeBody(body),
    sources,
    disclosure: data.disclosure,
    sponsored,
  });
}

export function contentSha256(data, body) {
  return createHash('sha256').update(canonicalContent(data, body), 'utf8').digest('hex');
}

export class ContentRuleError extends Error {
  constructor(id, message) {
    super(`Материал «${id}»: ${message}`);
    this.name = 'ContentRuleError';
    this.materialId = id;
  }
}

// Структурные правила, которые не зависят от режима сборки. Нарушение → ошибка сборки.
export function structuralErrors(data) {
  const errors = [];
  if (data.medical && !data.review) errors.push('медицинский материал без блока review');
  if (data.medical && !Array.isArray(data.sources)) errors.push('медицинский материал без списка sources');
  if (data.sponsored) {
    if (!data.sponsored.sponsor || !String(data.sponsored.sponsor).trim()) {
      errors.push('спонсорский материал без названия рекламодателя (плашка «Реклама» невозможна)');
    }
    if (data.section === 'pro' && KINDS_FORBIDDEN_FOR_SPONSORED_PRO.includes(data.kind)) {
      errors.push(`спонсорский материал не может быть kind=${data.kind} в разделе pro: это независимый формат`);
    }
    if (/^\s*независимый материал\s*$/i.test(data.disclosure ?? '')) {
      errors.push('спонсорский материал не может иметь раскрытие «Независимый материал»');
    }
  }
  if (data.section === 'dlya-vseh' && data.kind !== 'hub' && !data.hub) {
    errors.push('для раздела dlya-vseh нужно поле hub');
  }
  return errors;
}

export function isApproved(data, now = new Date()) {
  const r = data.review;
  if (!r || r.status !== 'approved') return false;
  if (r.expires_at && new Date(r.expires_at) <= now) return false;
  return true;
}

// Проверка одобренного медицинского материала. Нарушение → ошибка сборки.
export function approvalErrors(data, body) {
  const errors = [];
  const r = data.review;
  if (!data.medical || !r || r.status !== 'approved') return errors;
  if (!r.reviewer_name || !r.reviewer_title) errors.push('одобрение без имени и должности рецензента');
  if (!r.reviewed_at) errors.push('одобрение без даты рецензии');
  if (!r.version) errors.push('одобрение без версии');
  if (!data.sources || data.sources.length === 0) errors.push('одобренный медицинский материал без источников');
  const actual = contentSha256(data, body);
  if (!r.content_sha256) {
    errors.push(`одобрение без content_sha256 (текущий хеш: ${actual})`);
  } else if (r.content_sha256 !== actual) {
    errors.push(
      `текст изменён после рецензии: в рецензии ${r.content_sha256}, у текущего текста ${actual}. ` +
        'Нужна новая рецензия этой версии.',
    );
  }
  return errors;
}

// Решение о включении в сборку. Бросает ContentRuleError при нарушении правил.
// Возвращает { include, draft, reason }.
export function evaluateMaterial(id, data, body, { preview = false, now = new Date() } = {}) {
  const errors = [...structuralErrors(data), ...approvalErrors(data, body)];
  if (errors.length) throw new ContentRuleError(id, errors.join('; '));
  if (!data.medical) return { include: true, draft: false, reason: 'немедицинский' };
  if (isApproved(data, now)) return { include: true, draft: false, reason: 'одобрен' };
  const reason = data.review?.status === 'approved' ? 'срок одобрения истёк' : `статус рецензии: ${data.review?.status}`;
  return preview ? { include: true, draft: true, reason } : { include: false, draft: true, reason };
}

// Индексировать ли страницу материала.
export function isIndexable(data, decision, preview = false) {
  return !preview && !decision.draft && !data.pro_only;
}

// Публичное имя спикера/человека: только при явном согласии.
export function publicSpeakerName(speaker) {
  if (speaker && speaker.consent === true && speaker.name) {
    return { name: speaker.name, title: speaker.title || '' };
  }
  return null;
}

export function publicPeople(people) {
  return people.filter((p) => p.consent_public === true);
}

// Параметр start для Telegram-бота: [A-Za-z0-9_-], не длиннее 64 символов.
export function botStartParam(prefix, slug) {
  return `${prefix}_${slug}`.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 64);
}

const PREFIX_BY_KIND = { pamyatka: 'pamyatka', 'ne-akne': 'neakne', razbor: 'razbor', hub: 'hub', article: 'article' };
export function botStartForMaterial(data) {
  return botStartParam(PREFIX_BY_KIND[data.kind] ?? 'material', data.slug);
}
