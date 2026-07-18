# ── Stage 1: Build the React frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy dependencies manifest files and install
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build the static assets
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

# ── Stage 2: Serve React + FastAPI backend ─────────────────────────────────────
FROM python:3.12-slim AS backend
WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY backend/ ./backend/

# Copy the built frontend static files from the builder stage
COPY --from=frontend-builder /app/frontend/dist ./static/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
