// СИНТЕТИЧЕСКИЕ ДАННЫЕ ДЛЯ ТЕСТОВ. Не медицинские тексты, не реальные люди и не реальные источники.
import { withHash } from './build.mjs';

const SYN_SOURCE = `sources:
  - title: "Синтетический источник для теста (не существует)"
    url: https://example.org/synthetic-source
    year: 2025
    type: обзор
    on_whom: люди`;

export function material({ slug, section = 'pro', kind = 'pamyatka', status = 'approved', proOnly = false, hash = '__HASH__', title, body = 'Синтетический текст для теста. Не медицинская информация.', extra = '', sponsored = '', disclosure = 'Независимый материал', expires = '' }) {
  const review =
    status === 'approved'
      ? `review:
  reviewer_name: "Синтетический Рецензент"
  reviewer_title: "тестовая роль"
  reviewed_at: 2026-11-01
  version: 1
  content_sha256: "${hash}"
  status: approved${expires ? `\n  expires_at: ${expires}` : ''}`
      : `review:
  status: ${status}`;
  const text = `---
title: "${title ?? `Синтетический материал ${slug}`}"
slug: ${slug}
section: ${section}
kind: ${kind}
summary: "Синтетический анонс ${slug} для теста."
medical: true
pro_only: ${proOnly}
${review}
${SYN_SOURCE}
disclosure: "${disclosure}"
${sponsored}
updated_at: 2026-11-05
${extra}
---
${body}
`;
  return hash === '__HASH__' ? withHash(text) : text;
}

export const nonMedicalSponsored = ({ slug, section = 'pro', kind = 'article', sponsor = 'Синтетический Рекламодатель' }) => `---
title: "Синтетический партнёрский материал ${slug}"
slug: ${slug}
section: ${section}
kind: ${kind}
summary: "Синтетический партнёрский анонс."
medical: false
disclosure: "Партнёрский материал. Оплачен рекламодателем."
sponsored:
  sponsor: "${sponsor}"
updated_at: 2026-11-05
---
Синтетический текст партнёрского материала.
`;
