# ContractSimplifier

> Paste or upload a legal / rental contract and get a **plain-English explanation + risk rating (LOW / MEDIUM / HIGH)** for every clause, plus an overall summary verdict — powered primarily by **Groq API** (free tier) with **Google Gemini API** as fallback.

**Live AWS App Runner URL**: [https://contractsimplifier.us-east-1.awsapprunner.com](https://contractsimplifier.us-east-1.awsapprunner.com) *(Placeholder - update with your deployed URL)*

---

## Project Structure

```
contractsimplifier-ibm-aicte-alpha1/
├── frontend/          # React + Vite (UI — built by Teammate 2)
├── backend/           # Python FastAPI (LLM integration)
│   ├── main.py        # App entry point, router mount & static file serving
│   ├── routes/
│   │   └── analyze.py # POST /api/analyze endpoint
│   ├── services/
│   │   ├── clause_splitter.py  # Splits raw text into individual clauses
│   │   ├── pdf_extractor.py    # Extracts text from uploaded PDFs
│   │   ├── llm_client.py       # Groq SDK (primary) + Gemini SDK (fallback)
│   │   └── claude_client.py    # Legacy module alias to llm_client
│   ├── prompts.py     # System prompt constant (documented for report)
│   ├── models.py      # Pydantic request / response models
│   └── requirements.txt
├── Dockerfile         # Multi-stage build: Node builder → Python runner
├── .dockerignore      # Excludes .venv, node_modules, secrets from build context
├── .env.example       # Template for required env vars
├── .gitignore
└── README.md
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | ≥ 3.11 |
| pip | latest |
| Node.js | ≥ 18 |
| npm | ≥ 9 |

---

## Running the Backend Locally

### 1 — Clone & enter the repo
```bash
git clone https://github.com/Hassan092-prog/contractsimplifier-ibm-aicte-alpha1.git
cd contractsimplifier-ibm-aicte-alpha1
```

### 2 — Set up environment variables
```bash
cp .env.example .env
# Open .env and set GROQ_API_KEY (Primary) and/or GEMINI_API_KEY (Fallback)
```

### 3 — Install Python dependencies
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4 — Start the FastAPI server

Start the server from the **workspace root**:
```bash
# From the workspace root:
backend/.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Or from within the `backend` directory:
```bash
# From within the backend directory:
PYTHONPATH=.. .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at **http://127.0.0.1:8000**.  
Interactive docs: **http://127.0.0.1:8000/docs**

---

## Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Conditional | — | Primary Groq API key (free at https://console.groq.com) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model ID |
| `GEMINI_API_KEY` | Conditional | — | Fallback Gemini API key (from https://aistudio.google.com) |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model ID |
| `BACKEND_HOST` | No | `0.0.0.0` | Uvicorn bind host |
| `BACKEND_PORT` | No | `8000` | Uvicorn bind port |
| `MAX_INPUT_CHARS` | No | `50000` | Max pasted text length |

> At least one of `GROQ_API_KEY` or `GEMINI_API_KEY` must be configured in `.env`.

---

## API Reference — `POST /api/analyze`

### Request

Send as `multipart/form-data`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `string` | Conditional | Pasted contract text. Required if no `file`. |
| `file` | `file` | Conditional | PDF upload. Required if no `text`. |

> At least one of `text` or `file` must be provided.

#### curl example — pasted text
```bash
curl -N -X POST http://localhost:8000/api/analyze \
  -F "text=1. The tenant shall pay rent of $1,200 on the first of each month.
2. Late payments incur a penalty of 10% per day."
```

#### curl example — PDF upload
```bash
curl -N -X POST http://localhost:8000/api/analyze \
  -F "file=@/path/to/contract.pdf"
```

> **`-N`** disables curl buffering so you see the SSE stream live.

---

### Response — Server-Sent Events (SSE) stream

The endpoint streams **newline-delimited JSON** chunks.  
Each chunk is prefixed with `data: ` per the SSE spec.

#### Chunk types

**1 — Per-clause result** (one per clause, streamed as Claude finishes each):
```json
{
  "type": "clause",
  "index": 0,
  "clause_text": "The tenant shall pay rent of $1,200 on the first of each month.",
  "explanation": "You must pay $1,200 rent every month on the 1st.",
  "risk_level": "LOW",
  "reasoning": "Standard rent obligation with clear terms."
}
```

`risk_level` is always one of: `"LOW"`, `"MEDIUM"`, `"HIGH"`

**2 — Overall summary** (sent last, after all clauses):
```json
{
  "type": "summary",
  "verdict": "This contract is mostly standard with one HIGH-risk clause regarding...",
  "overall_risk": "MEDIUM"
}
```

**3 — Error** (sent if analysis fails):
```json
{
  "type": "error",
  "message": "Could not extract text from PDF — the file may be scanned/image-only."
}
```

#### SSE stream format
```
data: {"type":"clause","index":0,...}\n\n
data: {"type":"clause","index":1,...}\n\n
data: {"type":"summary","verdict":"..."}\n\n
```

---

## Running the Frontend Locally (Teammate 2)

### 1 — Set up environment variables
Copy the template to `.env.local`:
```bash
cd frontend
cp .env.example .env.local
```
Vite will expose `VITE_API_BASE_URL` to the client. In macOS/development, configure it to `http://127.0.0.1:8000` (IPv4 loopback) to avoid connection mismatches on dual-stack hosts.

### 2 — Install Node packages and start Dev Server
```bash
npm install
npm run dev
# Dev server starts at http://localhost:5173 (supporting IPv6 loopback [::1]:5173)
```

The frontend calls the backend at the configured `VITE_API_BASE_URL`.

---

## Running with Docker (Containerized Production)

### 1 — Build the Docker image
Run the following command from the workspace root directory:
```bash
docker build -t contractsimplifier .
```

### 2 — Run the container
Start the container and pass your `ANTHROPIC_API_KEY` as an environment variable at runtime (do not bake it into the image):
```bash
docker run -p 8000:8000 -e ANTHROPIC_API_KEY="your_api_key_here" contractsimplifier
```

The application is now live at **http://localhost:8000** (serving both the React frontend and FastAPI backend APIs from a single container on port 8000).

---

## Integration Details & Troubleshooting

- **CORS Configuration**: We modified `backend/main.py`'s CORS origins to include `http://[::1]:5173` alongside standard loopbacks to support browsers routing requests from IPv6-bound Vite pages.
- **Client-Side File Parsing**: To support `.txt` uploads without modifying teammate 1's backend endpoint (which natively processes `.pdf`), the frontend reads `.txt` files locally using the standard HTML5 `FileReader` API and submits the content via the `text` field.
- **Demo Mode**: To facilitate evaluation and testing when an Anthropic API key is not configured, the frontend provides a **"Try Demo Mode"** button. This fully simulates a live, progressive SSE clause analysis and verdict summary visualization.
- **Single Container serving React + FastAPI**: The React frontend is built in an alpine-node build stage, and the built files are served directly by FastAPI via `StaticFiles` in the final python container. We chose FastAPI `StaticFiles` mounting over Nginx because it simplifies process management (running only Uvicorn/FastAPI, avoiding a multi-process supervisor setup or Nginx config overhead) and results in a lighter container image footprint suitable for simple AWS App Runner deployment.

---

## Git Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Stable, always deployable — merged from all feature branches |
| `feature/backend-core` | Phase 2 backend work (Hassan) |
| `feature/frontend-ui` | Phase 3 frontend UI (Teammate 2) |
| `feature/deployment-docs` | Phase 4b–6 containerization, AWS deployment, and documentation (Teammate 3) |

---

## Team

| Role | Owner |
|------|-------|
| Backend + LLM integration | Hassan (Phase 1–2) |
| Frontend UI | Teammate 2 (Phase 3) |
| Containerization + AWS Deployment + Documentation | Teammate 3 (Phase 4b–6) |
