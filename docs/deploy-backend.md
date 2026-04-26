# Backend Deployment

← [Back to README](../README.md)

FastAPI server with LangGraph AI agents. Runs on Python 3.12.

## Prerequisites

- Python 3.12+
- Docker (for containerised deploys)
- A running Postgres, Redis, and Qdrant instance (see [deploy-infrastructure.md](deploy-infrastructure.md))

## Local Development

```bash
cd backend

# Install dependencies
pip install -e ".[dev]"

# Copy and fill env file
cp .env.example .env   # or create from the table below

# Run migrations
alembic upgrade head

# Start the server (hot reload)
uvicorn src.api.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

## Environment Variables

Create `backend/.env` with the following. Required fields have no default and the server will not start without them.

```dotenv
# --- Required ---
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/autoshop
JWT_SECRET=<long-random-string>           # e.g. openssl rand -hex 32

# --- AI Services ---
ANTHROPIC_API_KEY=sk-ant-...              # Claude agent
GEMINI_API_KEY=...                        # text-embedding-004 (parts catalog)
DEEPGRAM_API_KEY=...                      # audio transcription

# --- Infrastructure ---
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                           # leave blank for local Qdrant

# --- Storage (S3 or Cloudflare R2) ---
S3_BUCKET=
S3_ENDPOINT_URL=                          # R2: https://<account>.r2.cloudflarestorage.com
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=auto                           # use "auto" for R2

# --- Messaging (optional) ---
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_PHONE=
TWILIO_WHATSAPP_FROM=
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=

# --- Parts Pricing (optional) ---
ALLDATA_API_KEY=
ALLDATA_API_URL=
DEFAULT_PRICING_SOURCE=shop               # "shop" or "alldata"
```

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Roll back one step
alembic downgrade -1
```

## Running with Docker

```bash
cd backend
docker build -t autoshop-backend .
docker run --env-file .env -p 8000:8000 autoshop-backend
```

The Docker image runs `alembic upgrade head` then starts `uvicorn` automatically.

## Deploying to Railway

The repo includes `backend/railway.toml` pre-configured for Railway.

1. Install the Railway CLI: `npm install -g @railway/cli`
2. Link the project: `railway link`
3. Set env vars in the Railway dashboard (or `railway variables set KEY=value`)
4. Deploy: `railway up`

Railway builds from the `backend/Dockerfile`. The health check hits `/docs`.

## Tests

```bash
cd backend
pytest                    # all tests
pytest --cov=src          # with coverage
```

## Source Layout

```
backend/
  src/
    api/        FastAPI routes and app entry point
    agents/     LangGraph ReAct agent definitions
    models/     SQLAlchemy ORM models
    db/         Database session and helpers
    tools/      Agent tools (parts lookup, etc.)
    scripts/    One-off scripts (parts catalog ingest)
    config.py   Pydantic settings (reads from .env)
  alembic/      Migration scripts
  data/         Seed data (parts_seed.csv)
  tests/
```
