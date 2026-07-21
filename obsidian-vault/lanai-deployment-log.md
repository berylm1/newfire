
## 2026-07-07 02:37 — Frontend VITE_ANALYTICS Fix

Fixed the "TypeError: Invalid URL" by removing the unprocessed `%VITE_ANALYTICS_ENDPOINT%` analytics script tags from:
- Source: `/home/newwaveclaw/projects/lanai-official/lanai-portal/client/index.html`
- Built: container `/app/dist/public/index.html` (via sed)

Rebuilt frontend with `npm run build` and copied new assets (CSS + JS bundles) + server index.js into container. Restarted `lanai-server`. All health checks passing, Cloudflare tunnel returning 200.
## 2026-07-07 02:45 — Frontend Fully Fixed

Two issues resolved:
1. Analytics script tags: removed from HTML
2. Missing VITE_OAUTH_PORTAL_URL: added to .env
Frontend now loads correctly.
