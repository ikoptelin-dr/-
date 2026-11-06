import { config, siteUrl } from '../lib/config.mjs';

export function GET() {
  const body = config.preview
    ? 'User-agent: *\nDisallow: /\n'
    : `User-agent: *\nDisallow: /pro-dostup/\nDisallow: /zayavka-otpravlena/\nDisallow: /zayavka-oshibka/\n\nSitemap: ${siteUrl('/sitemap.xml')}\n`;
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
