// Разметка schema.org для материалов (ТЗ, раздел 7).
import { config, siteUrl } from './config.mjs';

export function materialJsonLd(m) {
  const d = m.data;
  const ld = {
    '@context': 'https://schema.org',
    '@type': d.medical ? 'MedicalWebPage' : 'Article',
    headline: d.title,
    name: d.title,
    description: d.summary,
    inLanguage: 'ru',
    url: siteUrl(m.path),
    dateModified: d.updated_at.toISOString().slice(0, 10),
    publisher: { '@type': 'Organization', name: config.name, url: config.site_url },
  };
  if (d.medical && !m.decision.draft && d.review) {
    ld.reviewedBy = { '@type': 'Person', name: d.review.reviewer_name, jobTitle: d.review.reviewer_title };
    ld.lastReviewed = d.review.reviewed_at.toISOString().slice(0, 10);
  }
  if (d.sources?.length) {
    ld.citation = d.sources.map((s) => ({ '@type': 'CreativeWork', name: s.title, url: s.url, datePublished: String(s.year) }));
  }
  if (d.sponsored) ld.sponsor = { '@type': 'Organization', name: d.sponsored.sponsor };
  return ld;
}
