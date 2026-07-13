# ── ContractSimplifier — Root Dockerfile (placeholder) ─────────────────────────
# This is a placeholder for a future multi-stage build.
# Phase 3 will add a production-ready Docker setup.
#
# Planned stages:
#   1. frontend-builder — npm install + vite build
#   2. backend          — Python 3.12-slim, copies /frontend/dist into FastAPI
#                         static files, exposes port 8000
#
# TODO (Phase 3):
# FROM node:20-slim AS frontend-builder
# WORKDIR /app/frontend
# COPY frontend/package*.json ./
# RUN npm ci
# COPY frontend/ ./
# RUN npm run build
#
# FROM python:3.12-slim AS backend
# WORKDIR /app
# COPY backend/requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt
# COPY backend/ ./backend/
# COPY --from=frontend-builder /app/frontend/dist ./static/
# ENV PYTHONUNBUFFERED=1
# EXPOSE 8000
# CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
