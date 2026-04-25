FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cached layer unless pyproject.toml changes)
COPY pyproject.toml .
# hatchling needs the src package to exist for editable install metadata
COPY src/ src/
RUN pip install --no-cache-dir -e ".[dev]"

# Copy the rest of the project
COPY . .

CMD sh -c "alembic upgrade head && uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
