FROM python:3.14-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models \
    HF_HUB_CACHE=/models/hub

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /models \
    && chown -R appuser:appuser /app/data /models
USER appuser

EXPOSE 8000
CMD ["uvicorn", "clipscribe.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM node:24-alpine AS frontend-build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:1.29-alpine AS frontend
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /web/dist /usr/share/nginx/html
EXPOSE 8080
