import { getCollection } from 'astro:content';

export async function GET({ site }) {
  const posts = await getCollection('blog');
  const deals = await getCollection('deals');
  
  const baseUrl = site?.toString().replace(/\/$/, '') || 'https://budgetdealsindia.com';
  
  const staticPages = [
    '',
    '/deals',
    '/blog',
    '/categories',
    '/privacy',
  ];
  
  const blogUrls = posts.map(post => `/blog/${post.slug}/`);
  const dealUrls = deals.map(deal => `/deal/${deal.slug}/`);
  
  const allUrls = [...staticPages, ...blogUrls, ...dealUrls];
  
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allUrls.map(url => `  <url>
    <loc>${baseUrl}${url}</loc>
    <changefreq>daily</changefreq>
    <priority>${url === '' ? '1.0' : '0.8'}</priority>
  </url>`).join('\n')}
</urlset>`;
  
  return new Response(sitemap, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, max-age=3600'
    }
  });
}