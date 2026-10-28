FROM node:22-alpine AS frontend-builder

ARG VITE_MAP_STYLE_URL
ENV VITE_MAP_STYLE_URL=${VITE_MAP_STYLE_URL}

WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
