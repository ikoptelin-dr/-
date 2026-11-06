// Список индексируемых адресов. Черновики, pro_only и служебные страницы сюда не попадают.
import { config } from './config.mjs';
import { getMaterials, getWebinars } from './content.mjs';

export const STATIC_INDEXABLE = [
  '/', '/pro/', '/pro/ne-akne/', '/pro/pamyatki/', '/pro/razbory/', '/pro/vebinary/', '/pro/klub/',
  '/dlya-vseh/', '/dlya-vseh/posle-procedur/',
  '/o-proekte/', '/redakciya/', '/redakcionnaya-politika/', '/reklama-i-nezavisimost/', '/partneram/', '/kontakty/',
  '/politika-konfidencialnosti/', '/soglasie-na-obrabotku/', '/medicinskaya-ogovorka/',
];

export async function indexablePaths() {
  if (config.preview) return [];
  const materials = (await getMaterials()).filter((m) => m.indexable && m.data.kind !== 'hub');
  const webinars = await getWebinars();
  const lastmod = new Map(materials.map((m) => [m.path, m.data.updated_at.toISOString().slice(0, 10)]));
  const paths = [...STATIC_INDEXABLE, ...materials.map((m) => m.path), ...webinars.map((w) => `/pro/vebinary/${w.data.slug}/`)];
  return [...new Set(paths)].map((path) => ({ path, lastmod: lastmod.get(path) ?? null }));
}
