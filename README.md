# AutoShop

AI-powered auto shop management platform. Jetpack Compose Android client, SwiftUI iOS client, Next.js web dashboard, FastAPI/LangGraph backend, PostgreSQL + Redis + Qdrant.

## Components

| Component | Stack | Deploy Guide |
|-----------|-------|--------------|
| Android | Kotlin, Jetpack Compose | [docs/deploy-android.md](docs/deploy-android.md) |
| iOS | Swift, SwiftUI | [docs/deploy-ios.md](docs/deploy-ios.md) |
| Backend | Python, FastAPI, LangGraph | [docs/deploy-backend.md](docs/deploy-backend.md) |
| Web | Next.js 16, Tailwind | [docs/deploy-web.md](docs/deploy-web.md) |
| Infrastructure | Postgres, Redis, Qdrant | [docs/deploy-infrastructure.md](docs/deploy-infrastructure.md) |

## Quick Start (local, all services)

```bash
# 1. Copy and fill in secrets
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum: GEMINI_API_KEY, ANTHROPIC_API_KEY, JWT_SECRET

# 2. Start everything
docker compose up --build

# Services:
#   Backend  → http://localhost:8000
#   Web      → http://localhost:3000
#   Postgres → localhost:5432
#   Redis    → localhost:6379
#   Qdrant   → http://localhost:6333
```

> Docker Compose runs DB migrations and seeds parts data automatically on first boot.

## Environment Variables

All backend secrets live in `backend/.env`. Required keys:

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string |
| `JWT_SECRET` | Token signing — use a long random string |
| `ANTHROPIC_API_KEY` | Claude AI agent |
| `GEMINI_API_KEY` | Text embeddings (parts catalog) |
| `DEEPGRAM_API_KEY` | Audio transcription |

Optional keys (S3/R2, Twilio, SendGrid, ALLDATA): see [docs/deploy-backend.md](docs/deploy-backend.md).

## Repository Layout

```
android/      Kotlin Android app
ios/          Swift iOS app (XcodeGen)
backend/      FastAPI server, LangGraph agents, Alembic migrations
web/          Next.js dashboard
docs/         Deployment guides, research notes
scripts/      Utility scripts
docker-compose.yml
```
