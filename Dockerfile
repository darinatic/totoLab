# Single-container build: compile the Vue SPA, then serve it + the API from FastAPI.

# --- Stage 1: build the frontend ---
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build           # -> /fe/dist

# --- Stage 2: python API that also serves the built SPA ---
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/data/seed_draws.csv ./data/seed_draws.csv
COPY --from=frontend /fe/dist ./static

ENV TOTO_STATIC_DIR=/app/static
ENV TOTO_DISABLE_SCHEDULER=1
# Render provides $PORT; default to 8010 for local runs.
ENV PORT=8010
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
