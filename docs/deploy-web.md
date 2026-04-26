# Web Deployment

← [Back to README](../README.md)

Next.js 16 dashboard with React 19 and Tailwind CSS 4.

## Prerequisites

- Node.js 20+
- A running backend (see [deploy-backend.md](deploy-backend.md))

## Local Development

```bash
cd web
npm install
npm run dev
# → http://localhost:3000
```

Set the backend URL via environment variable if it differs from the default:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

For production, set `NEXT_PUBLIC_API_URL` to your deployed backend URL (e.g. `https://api.yourdomain.com`).

> `NEXT_PUBLIC_` prefix means this value is embedded in the browser bundle at build time. Rebuild the app after changing it.

## Production Build

```bash
cd web
npm run build    # type-check + compile
npm start        # serve on port 3000
```

## Deploy with Docker (via Docker Compose)

The root `docker-compose.yml` builds and runs the web service:

```bash
docker compose up web
# → http://localhost:3000
```

To rebuild after code changes:

```bash
docker compose up --build web
```

## Deploy to Vercel

```bash
npm install -g vercel
cd web
vercel
```

Set `NEXT_PUBLIC_API_URL` in the Vercel project's environment variables dashboard. Vercel detects Next.js automatically — no config file needed.

## Deploy to Other Platforms

```bash
# Build a standalone output (e.g. for Fly.io, Railway, Render)
# Add to web/next.config.ts:
#   output: 'standalone'

npm run build
# Serve with: node .next/standalone/server.js
```

## Key Details

| Property | Value |
|----------|-------|
| Framework | Next.js 16.2.4 |
| React | 19.2.4 |
| Styling | Tailwind CSS 4 |
| Data fetching | TanStack Query v5 + Axios |
| TypeScript | Yes |
