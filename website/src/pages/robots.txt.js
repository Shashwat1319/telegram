export async function GET({ site }) {
  const baseUrl = site?.toString().replace(/\/$/, '') || 'https://budgetdealsindia.com';
  
  const robots = `User-agent: *
Allow: /

Sitemap: ${baseUrl}/sitemap-index.xml

# Crawl-delay for respectful crawling
Crawl-delay: 10

# Disallow admin/private areas
Disallow: /admin/
Disallow: /api/
Disallow: /_astro/
Disallow: /*.json$`;
  
  return new Response(robots, {
    headers: {
      'Content-Type': 'text/plain',
      'Cache-Control': 'public, max-age=86400'
    }
  });
}