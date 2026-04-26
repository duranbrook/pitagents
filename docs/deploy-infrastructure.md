# Infrastructure Deployment

← [Back to README](../README.md)

Covers PostgreSQL 16, Redis 7, and Qdrant 1.9 — the three stateful services the backend depends on.

## Local (Docker Compose)

The easiest path. All three services plus migrations and seeding run with one command:

```bash
docker compose up
```

On first boot, Docker Compose:
1. Starts Postgres, Redis, and Qdrant
2. Runs `alembic upgrade head` (the `migrate` service)
3. Seeds the parts catalog into Qdrant (the `seed` service — requires `GEMINI_API_KEY` in `backend/.env`)
4. Starts the backend and web

Data is persisted in named Docker volumes (`postgres_data`, `qdrant_data`). They survive `docker compose down` but are removed by `docker compose down -v`.

## Ports

| Service | Port |
|---------|------|
| Postgres | 5432 |
| Redis | 6379 |
| Qdrant HTTP | 6333 |
| Qdrant gRPC | 6334 |

## PostgreSQL

### Local (no Docker)

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

createdb autoshop
createuser user --pwprompt   # set password to "password" or update DATABASE_URL

# Then run migrations
cd backend && alembic upgrade head
```

### Connection string format

```
postgresql+asyncpg://user:password@localhost:5432/autoshop
```

### Managed (production)

Any Postgres-compatible managed service works:

- **Railway** — add a Postgres plugin, copy the `DATABASE_URL` it provides
- **Supabase** — use the `postgresql+asyncpg://...` connection string from Project Settings
- **Neon** — same; add `?ssl=require` if the provider requires TLS

### Backups

```bash
# Dump
pg_dump -U user autoshop > autoshop-$(date +%Y%m%d).sql

# Restore
psql -U user autoshop < autoshop-20260101.sql
```

## Redis

Redis is used for caching and background task queues.

### Local (no Docker)

```bash
brew install redis
brew services start redis
# Runs on localhost:6379
```

### Managed (production)

- **Railway** — add a Redis plugin
- **Upstash** — serverless Redis; copy the `REDIS_URL` (format: `redis://...` or `rediss://...` for TLS)

### Verify connection

```bash
redis-cli ping   # should return PONG
```

## Qdrant

Qdrant stores vector embeddings for the parts catalog, enabling semantic search.

### Local (no Docker)

```bash
# Docker single container
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.9.2
```

Or download the binary from [qdrant.tech/documentation/guides/installation](https://qdrant.tech/documentation/guides/installation/).

### Managed (production)

- **Qdrant Cloud** — create a free cluster at cloud.qdrant.io. Set:
  ```
  QDRANT_URL=https://<cluster-id>.<region>.aws.cloud.qdrant.io
  QDRANT_API_KEY=<your-api-key>
  ```

### Re-seeding the parts catalog

The seed script ingests `backend/data/parts_seed.csv` into Qdrant using Gemini embeddings:

```bash
cd backend
python -m src.scripts.ingest_parts \
  --file data/parts_seed.csv \
  --qdrant-url http://localhost:6333 \
  --gemini-api-key $GEMINI_API_KEY
```

This is safe to re-run; it upserts by part ID.

### Inspect collections

```bash
# List collections
curl http://localhost:6333/collections

# Collection info
curl http://localhost:6333/collections/parts
```

## Health Checks

```bash
# Postgres
pg_isready -U user -d autoshop

# Redis
redis-cli ping

# Qdrant
curl http://localhost:6333/healthz
```

All three are also wired into the Docker Compose `healthcheck` blocks, so dependent services wait until they're ready.
