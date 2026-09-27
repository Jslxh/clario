# Clario — Enterprise Knowledge Intelligence Platform

**Clario** is a production-oriented Enterprise Knowledge Intelligence and Retrieval-Augmented Generation (RAG) platform. It enables authenticated enterprise users to upload, index, and query enterprise documents securely against authorized knowledge sources.

---

## 1. Phase 1 Architecture Overview

This phase establishes the monorepo foundation for Clario, configuring the core services, environment parameters, API standards, and containerized data infrastructure:

```
clario/
├── frontend/             # React + Vite web application (JavaScript)
├── backend/              # FastAPI application & REST endpoints
│   ├── app/
│   │   ├── main.py       # FastAPI application entrypoint & health route
│   │   ├── api/          # API routers (v1 endpoints)
│   │   ├── core/         # Settings & configuration management
│   │   └── services/     # Business logic services
│   ├── tests/            # Test suite (pytest)
│   └── requirements.txt  # Python dependencies
├── docker/               # Container configurations & docs
├── .env.example          # Environment variable template
├── .gitignore            # Version control exclusions
├── docker-compose.yml    # PostgreSQL and Qdrant database orchestration
└── README.md             # Project documentation
```

---

## 2. Technology Stack

- **Frontend**: React 19, Vite, Vanilla CSS design system, JavaScript (ES module standard).
- **Backend**: Python 3.14+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn.
- **Data & Vector Layer**: PostgreSQL 16 (Relational DB), Qdrant v1.10 (Vector Database).
- **AI / RAG Framework (Prepared for Phase 2+)**: LangChain, Sentence Transformers.
- **Infrastructure & Tooling**: Docker, Docker Compose, Git.

---

## 3. Local Setup Instructions

### Prerequisites
- **Node.js**: v18+ (v26 tested)
- **Python**: 3.10+ (3.14 tested)
- **Docker**: Docker Desktop or Engine with `docker compose` plugin

### Environment Setup
Copy the example environment configuration to `.env`:
```bash
cp .env.example .env
```

---

## 4. Starting Infrastructure (PostgreSQL & Qdrant)

Run Docker Compose from the root directory to spin up PostgreSQL and Qdrant:

```bash
docker compose up -d
```

Verify that the services are healthy:
```bash
docker compose ps
```

- **PostgreSQL**: Listening on `localhost:5432`
- **Qdrant Vector DB**: Listening on `http://localhost:6333` (HTTP) and `6334` (gRPC)

---

## 5. Starting Backend (FastAPI)

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Launch the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Run test suite:
   ```bash
   pytest
   ```

---

## 6. Starting Frontend (React + Vite)

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open `http://localhost:5173` in your browser.

---

## 7. Health-Check Endpoint Verification

The backend exposes a lightweight health check endpoint at `GET /health` (and `GET /api/v1/health`).

### Request:
```bash
curl -X GET http://localhost:8000/health
```

### Expected Response:
```json
{
  "status": "healthy",
  "service": "clario-backend"
}
```

Interactive API documentation is accessible at `http://localhost:8000/docs`.
