"""
backend/main.py
===============
FastAPI application entry point.

Run locally
-----------
  cd backend
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

API docs available at http://localhost:8000/docs
"""

import logging
import os
from contextlib import asynccontextmanager


# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes.analyze import router as analyze_router

# ── Load .env before anything else touches os.environ ─────────────────────────
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown hooks) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ContractSimplifier backend starting up…")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning(
            "ANTHROPIC_API_KEY is not set! "
            "The /api/analyze endpoint will return errors until it is configured."
        )
    yield
    logger.info("ContractSimplifier backend shutting down.")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="ContractSimplifier API",
    description=(
        "Analyse legal/rental contract clauses and receive plain-English "
        "explanations with risk ratings, powered by Anthropic Claude."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In development the Vite frontend runs on port 5173.
# Tighten this list before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA / alternative dev server
        "http://127.0.0.1:5173",
        "http://[::1]:5173",       # IPv6 loopback origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(analyze_router, prefix="/api")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"], summary="Health check")
async def health():
    """Returns OK if the server is running. Does not check Claude connectivity."""
    return {"status": "ok", "version": app.version}


# ── Static Files serving ──────────────────────────────────────────────────────
# Serve the built React frontend. In production, the build files are copied
# to /app/static. We mount it at / so it is accessible at the root URL.
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(parent_dir, "static")

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning(
        f"Static files directory not found at {static_dir}. "
        "Frontend will not be served from backend."
    )
