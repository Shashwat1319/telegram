import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
	loader: glob({ pattern: "**/*.md", base: "./src/content/blog" }),
	schema: z.object({
		title: z.string(),
		description: z.string(),
		pubDate: z.coerce.date(),
		updatedDate: z.coerce.date().optional(),
		heroImage: z.string().optional(),
		buyLink: z.string().optional(),
	}),
});

const deals = defineCollection({
	loader: glob({ pattern: "**/*.md", base: "./src/content/deals" }),
	schema: z.object({
		title: z.string(),
		description: z.string(),
		pubDate: z.coerce.date(),
		price: z.string(),
		mrp: z.string(),
		discount: z.string(),
		image: z.string().optional(),
		buyLink: z.string().url(),
		category: z.string(),
		rating: z.string().optional(),
	}),
});

export const collections = { blog, deals };