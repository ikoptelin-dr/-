import { indexablePaths } from '../lib/sitemap.mjs';
import { siteUrl } from '../lib/config.mjs';

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

export async function GET() {
  const items = await indexablePaths();
  const body =
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    items.map((i) => `  <url><loc>${esc(siteUrl(i.path))}</loc>${i.lastmod ? `<lastmod>${i.lastmod}</lastmod>` : ''}</url>`).join('\n') +
    '\n</urlset>\n';
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
