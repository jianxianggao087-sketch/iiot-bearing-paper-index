import { defineConfig } from 'astro/config';

const repo = process.env.GITHUB_REPOSITORY?.split('/')[1] ?? '';
const base = process.env.BASE_PATH ?? (repo ? `/${repo}/` : '/');

export default defineConfig({
  site: process.env.SITE_URL ?? 'https://example.github.io',
  base,
  output: 'static',
  trailingSlash: 'ignore',
  devToolbar: { enabled: false },
  vite: { optimizeDeps: { disabled: true, noDiscovery: true, include: [], exclude: ['aria-query', 'axobject-query'] } },
});
