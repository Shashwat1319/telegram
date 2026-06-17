import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const posts = await getCollection('blog');
  const deals = await getCollection('deals');
  
  const items = [
    ...posts.map(post => ({
      title: post.data.title,
      link: `/blog/${post.slug}/`,
      pubDate: post.data.pubDate,
      description: post.data.description,
    })),
    ...deals.map(deal => ({
      title: deal.data.title,
      link: `/deal/${deal.slug}/`,
      pubDate: deal.data.pubDate,
      description: `${deal.data.price} (was ${deal.data.mrp}) - ${deal.data.category}`,
    }))
  ].sort((a, b) => new Date(b.pubDate).valueOf() - new Date(a.pubDate).valueOf());

  return rss({
    title: 'BudgetDeals India',
    description: 'Best budget deals for Indian students - Amazon loot, price drops & hostel hacks',
    site: context.site,
    items: items.slice(0, 50),
    customData: `<language>en-in</language>`,
  });
}