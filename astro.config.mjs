// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// NOTE: update `site` once a custom domain is connected, and drop `base`
// (GitHub Pages project sites are served from /<repo-name>/ until then).
export default defineConfig({
	site: 'https://goldenlife4us.github.io',
	base: '/goldenpage/',
	integrations: [sitemap()],
});
